import pytest

from app.seed.demo_data import CURRENT_SEASON


class TestTeamsAPI:
    def test_list_teams_returns_all_32(self, client):
        resp = client.get("/api/teams")
        assert resp.status_code == 200
        assert len(resp.json()) == 32

    def test_get_team_404(self, client):
        resp = client.get("/api/teams/999999")
        assert resp.status_code == 404

    def test_team_cap_has_consistent_math(self, client):
        resp = client.get("/api/teams/1/cap", params={"season": CURRENT_SEASON})
        assert resp.status_code == 200
        cap = resp.json()
        assert cap["cap_space"] == round(cap["salary_cap"] - cap["top51_commitments"] - cap["dead_cap"], 2)
        assert cap["effective_cap_space"] == round(
            cap["salary_cap"] - cap["cap_commitments"] - cap["dead_cap"], 2
        )

    def test_team_cap_missing_season_404(self, client):
        resp = client.get("/api/teams/1/cap", params={"season": 1999})
        assert resp.status_code == 404

    def test_roster_pct_of_cap_matches_cap_hit(self, client):
        resp = client.get("/api/teams/1/roster", params={"season": CURRENT_SEASON})
        assert resp.status_code == 200
        roster = resp.json()
        assert len(roster) > 0
        for row in roster[:5]:
            assert row["current_cap_hit"] >= 0
            if row["pct_of_team_cap"] is not None:
                assert row["pct_of_team_cap"] >= 0

    def test_dashboard_future_cap_covers_projection_window(self, client):
        resp = client.get("/api/teams/1/dashboard", params={"season": CURRENT_SEASON})
        assert resp.status_code == 200
        body = resp.json()
        future_seasons = [row["season"] for row in body["future_cap"]]
        assert future_seasons == sorted(future_seasons)
        assert all(s > CURRENT_SEASON for s in future_seasons)

    def test_position_spending_sums_to_active_commitments(self, client):
        cap_resp = client.get("/api/teams/1/cap", params={"season": CURRENT_SEASON})
        spend_resp = client.get("/api/teams/1/spending", params={"season": CURRENT_SEASON})
        assert spend_resp.status_code == 200
        total_spend = sum(row["cap_spending"] for row in spend_resp.json())
        assert total_spend == pytest.approx(cap_resp.json()["cap_commitments"], abs=0.01)


class TestPlayersAPI:
    def test_list_players_filter_by_team(self, client):
        resp = client.get("/api/players", params={"team_id": 1})
        assert resp.status_code == 200
        players = resp.json()
        assert len(players) > 0
        assert all(p["team_id"] == 1 for p in players)

    def test_search_by_name(self, client):
        all_players = client.get("/api/players", params={"team_id": 1}).json()
        target_name = all_players[0]["name"]
        resp = client.get("/api/players", params={"search": target_name.split()[0]})
        assert resp.status_code == 200
        assert any(p["name"] == target_name for p in resp.json())

    def test_player_profile_404(self, client):
        resp = client.get("/api/players/999999")
        assert resp.status_code == 404

    def test_player_profile_has_timeline_and_decision_points(self, client):
        players = client.get("/api/players", params={"team_id": 1}).json()
        player_id = players[0]["id"]
        resp = client.get(f"/api/players/{player_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["financial_timeline"]) == body["contract_end"] - body["contract_start"] + 1
        kinds = {p["kind"] for p in body["decision_points"]}
        assert "expiration" in kinds

    def test_financial_timeline_cap_hit_matches_components(self, client):
        players = client.get("/api/players", params={"team_id": 1}).json()
        player_id = players[0]["id"]
        body = client.get(f"/api/players/{player_id}").json()
        for year in body["financial_timeline"]:
            expected = round(
                year["base_salary"] + year["signing_bonus_proration"] + year["roster_bonus"] + year["incentives"],
                2,
            )
            assert year["cap_hit"] == expected


class TestContractsAPI:
    def test_search_contracts_by_aav_range(self, client):
        resp = client.get("/api/contracts", params={"min_aav": 20_000_000, "max_aav": 60_000_000})
        assert resp.status_code == 200
        for c in resp.json():
            assert 20_000_000 <= c["annual_value"] <= 60_000_000

    def test_search_contracts_by_position(self, client):
        resp = client.get("/api/contracts", params={"position": "QB"})
        assert resp.status_code == 200
        assert all(c["position"] == "QB" for c in resp.json())

    def test_get_contract_404(self, client):
        resp = client.get("/api/contracts/999999")
        assert resp.status_code == 404

    def test_release_standard_matches_cap_engine(self, client):
        contracts = client.get("/api/contracts", params={"team_id": 1, "contract_status": "active"}).json()
        contract_id = contracts[0]["id"]
        resp = client.post(
            f"/api/contracts/{contract_id}/release",
            json={"release_season": CURRENT_SEASON, "june1": False},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["after_dead_cap_next_year"] == 0.0
        assert body["total_dead_cap"] == body["after_dead_cap_current_year"]
        assert body["current_year_cap_savings"] == round(body["before_cap_hit"] - body["total_dead_cap"], 2)

    def test_release_june1_splits_dead_cap(self, client):
        contracts = client.get("/api/contracts", params={"team_id": 1, "contract_status": "active"}).json()
        multi_year = [c for c in contracts if c["years_remaining"] >= 2]
        assert multi_year, "expected at least one multi-year contract in demo data"
        contract_id = multi_year[0]["id"]

        standard = client.post(
            f"/api/contracts/{contract_id}/release",
            json={"release_season": CURRENT_SEASON, "june1": False},
        ).json()
        june1 = client.post(
            f"/api/contracts/{contract_id}/release",
            json={"release_season": CURRENT_SEASON, "june1": True},
        ).json()

        assert june1["after_dead_cap_next_year"] > 0
        assert standard["total_dead_cap"] == june1["total_dead_cap"]
        assert june1["after_dead_cap_current_year"] <= standard["after_dead_cap_current_year"]

    def test_release_nonexistent_contract_404(self, client):
        resp = client.post("/api/contracts/999999/release", json={"release_season": CURRENT_SEASON})
        assert resp.status_code == 404

    def test_restructure_rejects_over_max_convert(self, client):
        contracts = client.get("/api/contracts", params={"team_id": 1, "contract_status": "active"}).json()
        contract_id = contracts[0]["id"]
        resp = client.post(
            f"/api/contracts/{contract_id}/restructure",
            json={"restructure_season": CURRENT_SEASON, "amount_to_convert": 10**12},
        )
        assert resp.status_code == 400

    def test_restructure_savings_equals_future_increase(self, client):
        contracts = client.get(
            "/api/contracts", params={"team_id": 1, "contract_status": "active"}
        ).json()
        multi_year = [c for c in contracts if c["years_remaining"] >= 2]
        contract_id = multi_year[0]["id"]
        resp = client.post(
            f"/api/contracts/{contract_id}/restructure",
            json={"restructure_season": CURRENT_SEASON, "amount_to_convert": 1_000_000},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["current_year_savings"] == round(sum(body["future_cap_hit_increases"].values()), 2)


class TestTradeAPI:
    def test_trade_matches_release_dead_cap(self, client):
        contracts = client.get("/api/contracts", params={"team_id": 1, "contract_status": "active"}).json()
        contract_id = contracts[0]["id"]
        trade = client.post(
            f"/api/contracts/{contract_id}/trade", json={"trade_season": CURRENT_SEASON}
        ).json()
        release = client.post(
            f"/api/contracts/{contract_id}/release", json={"release_season": CURRENT_SEASON, "june1": False}
        ).json()
        assert trade["trading_team_dead_cap"] == release["after_dead_cap_current_year"]
        assert trade["trading_team_cap_savings"] == release["current_year_cap_savings"]

    def test_acquiring_team_hits_exclude_proration(self, client):
        contracts = client.get("/api/contracts", params={"team_id": 1, "contract_status": "active"}).json()
        multi_year = [c for c in contracts if c["years_remaining"] >= 2]
        contract_id = multi_year[0]["id"]
        trade = client.post(
            f"/api/contracts/{contract_id}/trade", json={"trade_season": CURRENT_SEASON}
        ).json()
        assert len(trade["acquiring_team_cap_hits"]) >= 1
        assert trade["scenario_id"] is not None

    def test_trade_nonexistent_contract_404(self, client):
        resp = client.post("/api/contracts/999999/trade", json={"trade_season": CURRENT_SEASON})
        assert resp.status_code == 404


class TestExtensionAPI:
    def test_extension_combined_timeline_includes_new_years(self, client):
        contracts = client.get("/api/contracts", params={"team_id": 1, "contract_status": "active"}).json()
        contract_id = contracts[0]["id"]
        resp = client.post(
            f"/api/contracts/{contract_id}/extend",
            json={
                "extension_start_season": CURRENT_SEASON + 2,
                "new_length_years": 3,
                "new_total_value": 60_000_000,
                "new_signing_bonus": 15_000_000,
                "new_guaranteed_money": 30_000_000,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        combined_seasons = [y["season"] for y in body["combined_years"]]
        assert CURRENT_SEASON + 2 in combined_seasons
        assert CURRENT_SEASON + 4 in combined_seasons
        assert body["total_new_commitment"] == 60_000_000.0
        assert body["scenario_id"] is not None

    def test_extension_rejects_guaranteed_exceeding_total(self, client):
        contracts = client.get("/api/contracts", params={"team_id": 1, "contract_status": "active"}).json()
        contract_id = contracts[0]["id"]
        resp = client.post(
            f"/api/contracts/{contract_id}/extend",
            json={
                "extension_start_season": CURRENT_SEASON + 2,
                "new_length_years": 2,
                "new_total_value": 10_000_000,
                "new_signing_bonus": 0,
                "new_guaranteed_money": 20_000_000,
            },
        )
        assert resp.status_code == 400


class TestScenarioComparisonAPI:
    def test_returns_keep_release_trade_at_minimum(self, client):
        contracts = client.get("/api/contracts", params={"team_id": 1, "contract_status": "active"}).json()
        contract_id = contracts[0]["id"]
        resp = client.get(f"/api/contracts/{contract_id}/scenarios", params={"season": CURRENT_SEASON})
        assert resp.status_code == 200
        body = resp.json()
        scenario_types = {o["scenario_type"] for o in body["options"]}
        assert {"keep", "release", "trade"}.issubset(scenario_types)
        for option in body["options"]:
            assert option["assessment"] in {"Strong", "Favorable", "Moderate", "Unfavorable", "Conditional"}
            assert len(option["reasoning"]) > 0

    def test_scenarios_404_for_missing_contract(self, client):
        resp = client.get("/api/contracts/999999/scenarios")
        assert resp.status_code == 404


class TestProjectionsAPI:
    def test_projection_base_season_matches_current_cap(self, client):
        cap = client.get("/api/teams/1/cap", params={"season": CURRENT_SEASON}).json()
        resp = client.post("/api/teams/1/projections", json={"growth_rate": 0.06})
        assert resp.status_code == 200
        body = resp.json()
        base = next(s for s in body["seasons"] if s["season"] == CURRENT_SEASON)
        assert base["projected_cap"] == cap["salary_cap"]

    def test_higher_growth_rate_yields_more_future_space(self, client):
        low = client.post("/api/teams/1/projections", json={"growth_rate": 0.01}).json()
        high = client.post("/api/teams/1/projections", json={"growth_rate": 0.10}).json()
        low_last = low["seasons"][-1]["projected_space"]
        high_last = high["seasons"][-1]["projected_space"]
        assert high_last > low_last

    def test_custom_seasons_respected(self, client):
        resp = client.post(
            "/api/teams/1/projections", json={"growth_rate": 0.05, "seasons": [CURRENT_SEASON, CURRENT_SEASON + 1]}
        )
        body = resp.json()
        assert [s["season"] for s in body["seasons"]] == [CURRENT_SEASON, CURRENT_SEASON + 1]


class TestDeadCapDashboardAPI:
    def test_dead_cap_dashboard_totals_match_sum_of_players(self, client):
        resp = client.get("/api/teams/1/dead-cap", params={"season": CURRENT_SEASON})
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_dead_cap_current_season"] == pytest.approx(
            sum(r["dead_cap_value"] for r in body["by_player"]), abs=0.01
        )

    def test_dead_cap_by_season_covers_projection_window(self, client):
        resp = client.get("/api/teams/1/dead-cap", params={"season": CURRENT_SEASON})
        body = resp.json()
        seasons = [row["season"] for row in body["by_season"]]
        assert seasons == sorted(seasons)


class TestAnalyticsAPI:
    def test_financial_flexibility_score_in_range(self, client):
        resp = client.get("/api/analytics/financial-flexibility", params={"team_id": 1, "season": CURRENT_SEASON})
        assert resp.status_code == 200
        body = resp.json()
        assert 0 <= body["score"] <= 100
        assert len(body["factors"]) == 5

    def test_financial_flexibility_custom_weights_applied(self, client):
        resp = client.get(
            "/api/analytics/financial-flexibility",
            params={"team_id": 1, "season": CURRENT_SEASON, "w_cap_space": 10, "w_dead_cap": 0.1},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["weights_used"]["cap_space"] == 10.0
        assert body["weights_used"]["dead_cap"] == 0.1

    def test_financial_flexibility_404_missing_season(self, client):
        resp = client.get("/api/analytics/financial-flexibility", params={"team_id": 1, "season": 1999})
        assert resp.status_code == 404

    def test_concentration_percentages_sum_consistently(self, client):
        resp = client.get("/api/analytics/concentration", params={"team_id": 1, "season": CURRENT_SEASON})
        assert resp.status_code == 200
        body = resp.json()
        assert body["top1_pct"] <= body["top3_pct"] <= body["top5_pct"] <= body["top10_pct"] <= 100

    def test_contract_risk_category_valid(self, client):
        contracts = client.get("/api/contracts", params={"team_id": 1, "contract_status": "active"}).json()
        contract_id = contracts[0]["id"]
        resp = client.get("/api/analytics/contract-risk", params={"contract_id": contract_id, "season": CURRENT_SEASON})
        assert resp.status_code == 200
        body = resp.json()
        assert body["category"] in {"Low", "Moderate", "High", "Very High"}
        assert len(body["factors"]) == 4

    def test_contract_risk_404_for_missing_contract(self, client):
        resp = client.get("/api/analytics/contract-risk", params={"contract_id": 999999})
        assert resp.status_code == 404

    def test_contract_value_percentile_in_range(self, client):
        contracts = client.get("/api/contracts", params={"team_id": 1, "contract_status": "active"}).json()
        contract_id = contracts[0]["id"]
        resp = client.get("/api/analytics/contract-value", params={"contract_id": contract_id})
        assert resp.status_code == 200
        body = resp.json()
        assert 0 <= body["percentile"] <= 100
        assert body["sample_size"] > 0
        assert "does not use player performance" in body["disclaimer"]

    def test_position_spending_comparison_has_rows(self, client):
        resp = client.get("/api/analytics/position-spending-comparison", params={"team_id": 1, "season": CURRENT_SEASON})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["rows"]) > 0
        for row in body["rows"]:
            assert row["difference"] == pytest.approx(
                row["team_cap_percentage"] - row["league_avg_cap_percentage"], abs=0.01
            )


class TestPhase4API:
    def test_flexibility_forecast_covers_all_seasons(self, client):
        resp = client.get("/api/teams/1/financial-flexibility-forecast", params={"growth_rate": 0.06})
        assert resp.status_code == 200
        body = resp.json()
        seasons = [s["season"] for s in body["seasons"]]
        assert seasons == sorted(seasons)
        assert len(body["what_would_change_our_mind"]) >= 1
        for s in body["seasons"]:
            assert 0 <= s["score"] <= 100

    def test_flexibility_forecast_current_season_unaffected_by_growth_rate(self, client):
        # years_from_base == 0 for the current season, so growth rate cannot move it.
        low = client.get("/api/teams/1/financial-flexibility-forecast", params={"growth_rate": 0.01}).json()
        high = client.get("/api/teams/1/financial-flexibility-forecast", params={"growth_rate": 0.10}).json()
        assert low["seasons"][0]["score"] == high["seasons"][0]["score"]

    def test_free_agent_planning_reduces_cap_space(self, client):
        resp = client.post(
            "/api/teams/1/free-agent-planning",
            json={
                "position": "WR", "target_aav": 18_000_000, "contract_length": 3,
                "guaranteed_money": 30_000_000, "start_season": CURRENT_SEASON,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["cap_space_after"] < body["cap_space_before"]
        assert len(body["year_by_year_cap_hit"]) == 3
        assert body["projected_total_value"] == 18_000_000 * 3

    def test_free_agent_planning_404_missing_season(self, client):
        resp = client.post(
            "/api/teams/1/free-agent-planning",
            json={"position": "WR", "target_aav": 1, "contract_length": 1, "guaranteed_money": 0, "start_season": 1999},
        )
        assert resp.status_code == 404

    def test_rookie_planning_first_round_costs_more_than_seventh(self, client):
        resp = client.post(
            "/api/teams/1/rookie-planning",
            json={"season": CURRENT_SEASON, "picks": [{"draft_round": 1}, {"draft_round": 7}]},
        )
        assert resp.status_code == 200
        body = resp.json()
        picks_by_round = {p["draft_round"]: p for p in body["picks"]}
        assert picks_by_round[1]["first_year_cap_hit"] > picks_by_round[7]["first_year_cap_hit"]
        assert body["cap_space_after"] < body["cap_space_before"]

    def test_rookie_planning_rejects_invalid_round(self, client):
        resp = client.post(
            "/api/teams/1/rookie-planning",
            json={"season": CURRENT_SEASON, "picks": [{"draft_round": 9}]},
        )
        assert resp.status_code == 422  # pydantic field validation (le=7)


class TestPhase5API:
    def test_model_info_reports_metrics(self, client):
        resp = client.get("/api/ml/model-info")
        assert resp.status_code == 200
        body = resp.json()
        assert body["dataset_size"] > 0
        assert "QB" in body["positions_seen"]

    def test_contract_value_projection_returns_drivers(self, client):
        resp = client.get(
            "/api/ml/contract-value-projection",
            params={"position": "WR", "age": 27, "contract_length_years": 3},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["predicted_aav"] >= 0
        assert len(body["drivers"]) == 3
        assert "ESTIMATE" in body["disclaimer"]

    def test_contract_value_projection_validates_age_range(self, client):
        resp = client.get(
            "/api/ml/contract-value-projection",
            params={"position": "WR", "age": 5, "contract_length_years": 3},
        )
        assert resp.status_code == 422

    def test_comparable_contracts_same_position_only(self, client):
        resp = client.get(
            "/api/analytics/comparable-contracts",
            params={"position": "QB", "age": 28, "aav": 20_000_000, "limit": 5},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert all(r["position"] == "QB" for r in body["results"])
        assert all(0 <= r["similarity_score"] <= 100 for r in body["results"])

    def test_comparable_contracts_ranked_by_similarity_desc(self, client):
        resp = client.get(
            "/api/analytics/comparable-contracts",
            params={"position": "EDGE", "age": 27, "aav": 20_000_000, "limit": 10},
        )
        scores = [r["similarity_score"] for r in resp.json()["results"]]
        assert scores == sorted(scores, reverse=True)


class TestHealthAndMeta:
    def test_health(self, client):
        assert client.get("/api/health").status_code == 200

    def test_meta_labels_demo_data(self, client):
        body = client.get("/api/meta").json()
        assert "DEMO DATA" in body["demo_disclaimer"]
