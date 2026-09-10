import pytest

from app.services.financial_intelligence import (
    calculate_contract_risk,
    calculate_financial_concentration,
    calculate_financial_flexibility,
    calculate_market_comparison,
    find_comparable_contracts,
)


class TestFinancialConcentration:
    def test_top_n_percentages(self):
        hits = [50, 30, 10, 5, 5] + [2] * 40  # total = 100 + 80 = 180
        result = calculate_financial_concentration(hits)
        assert result.total_commitments == 180
        assert result.top1_pct == pytest.approx(50 / 180 * 100, abs=0.01)
        assert result.top5_pct == pytest.approx(100 / 180 * 100, abs=0.01)

    def test_empty_roster_no_division_by_zero(self):
        result = calculate_financial_concentration([])
        assert result.top1_pct == 0.0
        assert result.total_commitments == 0.0

    def test_fewer_than_ten_contracts(self):
        hits = [10, 8, 6]
        result = calculate_financial_concentration(hits)
        assert result.top10_dollars == 24.0
        assert result.top10_pct == 100.0


class TestFinancialFlexibility:
    def test_favorable_inputs_yield_high_score(self):
        result = calculate_financial_flexibility(
            cap_space_pct=0.20, dead_cap_pct=0.0, future_guaranteed_pct=0.0,
            expiring_pct=0.25, top5_concentration_pct=0.25,
        )
        assert result.score > 90

    def test_unfavorable_inputs_yield_low_score(self):
        result = calculate_financial_flexibility(
            cap_space_pct=0.0, dead_cap_pct=0.15, future_guaranteed_pct=0.30,
            expiring_pct=0.0, top5_concentration_pct=0.70,
        )
        assert result.score < 15

    def test_score_bounded_0_to_100(self):
        result = calculate_financial_flexibility(
            cap_space_pct=-0.5, dead_cap_pct=1.0, future_guaranteed_pct=1.0,
            expiring_pct=0.0, top5_concentration_pct=1.0,
        )
        assert 0 <= result.score <= 100

    def test_custom_weights_change_score(self):
        kwargs = dict(
            cap_space_pct=0.20, dead_cap_pct=0.15, future_guaranteed_pct=0.0,
            expiring_pct=0.0, top5_concentration_pct=0.30,
        )
        default = calculate_financial_flexibility(**kwargs)
        # Weight dead_cap heavily; since dead_cap_pct=0.15 gives a low dead-cap
        # sub-score, weighting it more should pull the overall score down.
        weighted = calculate_financial_flexibility(**kwargs, weights={"dead_cap": 5.0})
        assert weighted.score < default.score

    def test_rejects_zero_weight_sum(self):
        with pytest.raises(ValueError):
            calculate_financial_flexibility(
                cap_space_pct=0.1, dead_cap_pct=0, future_guaranteed_pct=0,
                expiring_pct=0, top5_concentration_pct=0.3,
                weights={"cap_space": 0, "dead_cap": 0, "future_guaranteed": 0, "expiring_contracts": 0, "concentration": 0},
            )

    def test_factor_directions_match_scores(self):
        result = calculate_financial_flexibility(
            cap_space_pct=0.20, dead_cap_pct=0.0, future_guaranteed_pct=0.0,
            expiring_pct=0.25, top5_concentration_pct=0.25,
        )
        for factor in result.factors:
            if factor.score >= 60:
                assert factor.direction == "+"
            elif factor.score < 40:
                assert factor.direction == "-"


class TestContractRisk:
    def test_young_short_low_guarantee_is_low_risk(self):
        result = calculate_contract_risk(
            age=24, position="WR", years_remaining=1,
            guaranteed_pct_of_total=0.1, future_cap_hit_pct_of_cap=0.02,
        )
        assert result.category == "Low"

    def test_old_long_high_guarantee_is_very_high_risk(self):
        result = calculate_contract_risk(
            age=34, position="RB", years_remaining=5,
            guaranteed_pct_of_total=0.8, future_cap_hit_pct_of_cap=0.2,
        )
        assert result.category == "Very High"
        assert result.risk_score == 100.0

    def test_position_specific_decline_age(self):
        # Age 31 is past decline risk for RB (27) but not for QB (33).
        rb_result = calculate_contract_risk(
            age=31, position="RB", years_remaining=1, guaranteed_pct_of_total=0.1, future_cap_hit_pct_of_cap=0.02
        )
        qb_result = calculate_contract_risk(
            age=31, position="QB", years_remaining=1, guaranteed_pct_of_total=0.1, future_cap_hit_pct_of_cap=0.02
        )
        assert rb_result.risk_score > qb_result.risk_score

    def test_rejects_negative_age(self):
        with pytest.raises(ValueError):
            calculate_contract_risk(age=-1, position="QB", years_remaining=1, guaranteed_pct_of_total=0, future_cap_hit_pct_of_cap=0)

    def test_never_asserts_certainty_in_factor_text(self):
        result = calculate_contract_risk(
            age=34, position="RB", years_remaining=5, guaranteed_pct_of_total=0.8, future_cap_hit_pct_of_cap=0.2
        )
        for f in result.factors:
            assert "will decline" not in f.detail.lower()


class TestMarketComparison:
    def _league(self):
        return [
            {"position": "WR", "age": 24, "aav": 5_000_000},
            {"position": "WR", "age": 26, "aav": 15_000_000},
            {"position": "WR", "age": 27, "aav": 20_000_000},
            {"position": "WR", "age": 29, "aav": 25_000_000},
            {"position": "WR", "age": 31, "aav": 10_000_000},
            {"position": "QB", "age": 28, "aav": 40_000_000},
        ]

    def test_percentile_reflects_rank_within_position(self):
        result = calculate_market_comparison(25_000_000, "WR", 29, self._league())
        assert result.percentile == 100.0  # highest-paid WR in the set
        assert result.sample_size == 5

    def test_lowest_paid_has_low_percentile(self):
        result = calculate_market_comparison(5_000_000, "WR", 24, self._league())
        assert result.percentile == 20.0  # 1 of 5 values <= it

    def test_cost_vs_median_sign(self):
        result = calculate_market_comparison(25_000_000, "WR", 29, self._league())
        assert result.cost_vs_position_median > 0

    def test_raises_for_position_with_no_comparisons(self):
        with pytest.raises(ValueError):
            calculate_market_comparison(1_000_000, "TE", 25, self._league())

    def test_age_band_narrows_comparison_set(self):
        result = calculate_market_comparison(20_000_000, "WR", 27, self._league(), age_band=1)
        # Only ages 26,27,29(no, |29-27|=2>1) -> ages within 1 of 27: 26,27 -> aavs 15M,20M
        assert result.age_band_median_aav in (15_000_000.0, 20_000_000.0)


class TestComparableContracts:
    def _candidates(self):
        return [
            {"contract_id": 1, "player_name": "A", "position": "WR", "age": 27, "aav": 20_000_000, "years_remaining": 2, "guaranteed_money": 10_000_000},
            {"contract_id": 2, "player_name": "B", "position": "WR", "age": 28, "aav": 19_500_000, "years_remaining": 3, "guaranteed_money": 12_000_000},
            {"contract_id": 3, "player_name": "C", "position": "WR", "age": 35, "aav": 2_000_000, "years_remaining": 1, "guaranteed_money": 0},
            {"contract_id": 4, "player_name": "D", "position": "QB", "age": 27, "aav": 20_000_000, "years_remaining": 2, "guaranteed_money": 10_000_000},
        ]

    def test_only_same_position_returned(self):
        results = find_comparable_contracts(position="WR", age=27, aav=20_000_000, candidates=self._candidates())
        assert all(r.position == "WR" for r in results)
        assert not any(r.contract_id == 4 for r in results)

    def test_closest_match_ranks_first(self):
        results = find_comparable_contracts(position="WR", age=27, aav=20_000_000, candidates=self._candidates())
        assert results[0].contract_id == 1  # exact match
        assert results[0].similarity_score == 100.0

    def test_far_away_candidate_excluded_by_age_gap(self):
        results = find_comparable_contracts(
            position="WR", age=27, aav=20_000_000, candidates=self._candidates(), max_age_diff=5
        )
        # Player C is 8 years older than the query -> excluded.
        assert not any(r.contract_id == 3 for r in results)

    def test_limit_respected(self):
        results = find_comparable_contracts(position="WR", age=27, aav=20_000_000, candidates=self._candidates(), limit=1)
        assert len(results) == 1

    def test_no_candidates_returns_empty(self):
        results = find_comparable_contracts(position="TE", age=27, aav=1, candidates=self._candidates())
        assert results == []
