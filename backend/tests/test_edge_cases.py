"""Additional edge-case coverage per the project brief's testing
requirements (section 45): boundary contract structures, malformed
requests, and unusual-but-valid inputs not covered by the main suites."""
import pytest

from app.seed.demo_data import CURRENT_SEASON
from app.services.cap_engine import structure_contract_years


class TestCapEngineEdgeCases:
    def test_signing_bonus_equal_to_total_value_zeroes_base_salary(self):
        # An all-bonus, no-base-salary contract is a legal (if unusual) structure.
        years = structure_contract_years(
            start_season=2026, length_years=2, total_value=4_000_000,
            signing_bonus=4_000_000, guaranteed_money=4_000_000,
        )
        assert sum(y.base_salary for y in years) == pytest.approx(0.0, abs=0.01)
        assert all(y.signing_bonus_proration == 2_000_000.0 for y in years)

    def test_zero_signing_bonus_contract_has_no_proration(self):
        years = structure_contract_years(
            start_season=2026, length_years=3, total_value=9_000_000,
            signing_bonus=0, guaranteed_money=0,
        )
        assert all(y.signing_bonus_proration == 0.0 for y in years)
        assert sum(y.base_salary for y in years) == pytest.approx(9_000_000, abs=0.01)

    def test_one_year_contract_structures_cleanly(self):
        years = structure_contract_years(
            start_season=2026, length_years=1, total_value=2_000_000,
            signing_bonus=500_000, guaranteed_money=2_000_000,
        )
        assert len(years) == 1
        assert years[0].signing_bonus_proration == 500_000.0
        assert years[0].guaranteed_base_salary == pytest.approx(1_500_000, abs=0.01)

    def test_rejects_zero_length_contract(self):
        with pytest.raises(ValueError):
            structure_contract_years(start_season=2026, length_years=0, total_value=1, signing_bonus=0, guaranteed_money=0)


class TestAPIMalformedRequests:
    def test_extend_missing_required_field_returns_422(self, client):
        contracts = client.get("/api/contracts", params={"team_id": 1, "contract_status": "active"}).json()
        contract_id = contracts[0]["id"]
        resp = client.post(
            f"/api/contracts/{contract_id}/extend",
            json={"extension_start_season": CURRENT_SEASON + 1, "new_length_years": 3},
        )
        assert resp.status_code == 422

    def test_free_agent_planning_missing_field_returns_422(self, client):
        resp = client.post(
            "/api/teams/1/free-agent-planning",
            json={"position": "WR", "target_aav": 1_000_000},
        )
        assert resp.status_code == 422

    def test_restructure_negative_amount_returns_422(self, client):
        contracts = client.get("/api/contracts", params={"team_id": 1, "contract_status": "active"}).json()
        contract_id = contracts[0]["id"]
        resp = client.post(
            f"/api/contracts/{contract_id}/restructure",
            json={"restructure_season": CURRENT_SEASON, "amount_to_convert": -1000},
        )
        assert resp.status_code == 422

    def test_rookie_planning_negative_round_returns_422(self, client):
        resp = client.post(
            "/api/teams/1/rookie-planning",
            json={"season": CURRENT_SEASON, "picks": [{"draft_round": -1}]},
        )
        assert resp.status_code == 422

    def test_contract_value_projection_missing_position_returns_422(self, client):
        resp = client.get("/api/ml/contract-value-projection", params={"age": 27, "contract_length_years": 3})
        assert resp.status_code == 422


class TestSingleYearAndFutureContracts:
    def test_release_on_contract_with_one_year_remaining_has_no_future_dead_cap(self, client):
        contracts = client.get("/api/contracts", params={"team_id": 1, "contract_status": "active"}).json()
        one_year = [c for c in contracts if c["years_remaining"] == 1]
        if not one_year:
            pytest.skip("no one-year-remaining contract in this demo dataset")
        contract_id = one_year[0]["id"]
        resp = client.post(
            f"/api/contracts/{contract_id}/release",
            json={"release_season": CURRENT_SEASON, "june1": True},
        )
        assert resp.status_code == 200
        assert resp.json()["after_dead_cap_next_year"] == 0.0

    def test_negative_growth_rate_still_produces_a_valid_projection(self, client):
        resp = client.post("/api/teams/1/projections", json={"growth_rate": -0.02})
        assert resp.status_code == 200
        body = resp.json()
        # A shrinking cap assumption should not increase projected cap over time.
        caps = [s["projected_cap"] for s in body["seasons"]]
        assert caps == sorted(caps, reverse=True)
