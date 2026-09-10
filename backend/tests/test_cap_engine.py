"""Unit tests for the deterministic cap engine, using hand-calculated
scenarios so every assertion can be independently verified."""
import pytest

from app.services.cap_engine import (
    ContractYearInput,
    calculate_dead_cap,
    calculate_restructure,
    compute_cap_hit,
    signing_bonus_proration,
    summarize_team_cap,
)


class TestSigningBonusProration:
    def test_even_split_within_five_years(self):
        assert signing_bonus_proration(20_000_000, 4) == 5_000_000.0

    def test_capped_at_five_years_for_longer_contracts(self):
        # A 7-year contract still only prorates over 5 league years.
        assert signing_bonus_proration(25_000_000, 7) == 5_000_000.0

    def test_one_year_contract(self):
        assert signing_bonus_proration(1_000_000, 1) == 1_000_000.0

    def test_zero_bonus(self):
        assert signing_bonus_proration(0, 4) == 0.0

    def test_rejects_zero_or_negative_years(self):
        with pytest.raises(ValueError):
            signing_bonus_proration(1_000_000, 0)

    def test_rejects_negative_bonus(self):
        with pytest.raises(ValueError):
            signing_bonus_proration(-100, 4)

    def test_rounds_to_cents(self):
        # 10M / 3 = 3,333,333.333...
        assert signing_bonus_proration(10_000_000, 3) == 3333333.33


class TestComputeCapHit:
    def test_basic_sum(self):
        assert compute_cap_hit(base_salary=1_000_000, bonus_proration=5_000_000) == 6_000_000.0

    def test_all_components(self):
        result = compute_cap_hit(
            base_salary=1_000_000, bonus_proration=5_000_000, roster_bonus=500_000, incentives=250_000
        )
        assert result == 6_750_000.0

    def test_rejects_negative_component(self):
        with pytest.raises(ValueError):
            compute_cap_hit(base_salary=-1, bonus_proration=0)


class TestDeadCap:
    """Scenario: 4-year, $20M contract, $20M signing bonus -> $5M/yr proration.
    Base salaries: Y1 $1M, Y2 $2M, Y3 $3M, Y4 $4M. Contract runs 2024-2027.
    """

    def _contract_years(self):
        return [
            ContractYearInput(season=2024, base_salary=1_000_000, signing_bonus_proration=5_000_000),
            ContractYearInput(season=2025, base_salary=2_000_000, signing_bonus_proration=5_000_000),
            ContractYearInput(season=2026, base_salary=3_000_000, signing_bonus_proration=5_000_000),
            ContractYearInput(season=2027, base_salary=4_000_000, signing_bonus_proration=5_000_000),
        ]

    def test_standard_release_after_two_years_accelerates_remaining_proration(self):
        # Released before 2026: 2026 + 2027 proration ($5M + $5M = $10M)
        # accelerates entirely into 2026 dead cap.
        result = calculate_dead_cap(self._contract_years(), release_season=2026, june1=False)
        assert result.pre_release_cap_hit == 8_000_000.0  # 3M base + 5M proration
        assert result.current_year_dead_cap == 10_000_000.0
        assert result.next_year_dead_cap == 0.0
        assert result.total_dead_cap == 10_000_000.0
        assert result.current_year_cap_savings == pytest.approx(8_000_000.0 - 10_000_000.0)

    def test_post_june1_release_splits_proration_across_two_seasons(self):
        result = calculate_dead_cap(self._contract_years(), release_season=2026, june1=True)
        # Current year only bears its own $5M proration.
        assert result.current_year_dead_cap == 5_000_000.0
        # The remaining $5M (2027's proration) pushes to next year.
        assert result.next_year_dead_cap == 5_000_000.0
        assert result.total_dead_cap == 10_000_000.0
        # Current-year savings should now be positive (release cheaper now).
        assert result.current_year_cap_savings == pytest.approx(8_000_000.0 - 5_000_000.0)

    def test_release_in_final_contract_year_has_no_future_dead_cap(self):
        result = calculate_dead_cap(self._contract_years(), release_season=2027, june1=False)
        assert result.current_year_dead_cap == 5_000_000.0  # only final year's proration left
        assert result.next_year_dead_cap == 0.0

    def test_release_after_contract_expired_has_no_dead_cap(self):
        result = calculate_dead_cap(self._contract_years(), release_season=2028, june1=False)
        assert result.total_dead_cap == 0.0
        assert result.pre_release_cap_hit == 0.0

    def test_guaranteed_base_salary_adds_to_dead_cap(self):
        years = [
            ContractYearInput(
                season=2024,
                base_salary=1_000_000,
                signing_bonus_proration=5_000_000,
                guaranteed_base_salary=1_000_000,
            ),
            ContractYearInput(season=2025, base_salary=2_000_000, signing_bonus_proration=5_000_000),
        ]
        result = calculate_dead_cap(years, release_season=2024, june1=False)
        # Remaining proration (5M + 5M = 10M) + guaranteed base salary due (1M)
        assert result.current_year_dead_cap == 11_000_000.0

    def test_next_year_cap_hit_removed_is_informational_not_dead_cap(self):
        result = calculate_dead_cap(self._contract_years(), release_season=2025, june1=False)
        # 2026's cap hit (3M base + 5M proration = 8M) would have been owed;
        # it's simply removed from the books, not double counted as dead cap.
        assert result.next_year_cap_hit_removed == 8_000_000.0


class TestRestructure:
    def test_moving_base_salary_into_proration_trades_current_for_future(self):
        # 3 years remaining (2025-2027), convert $9M of 2025 base salary.
        years = [
            ContractYearInput(season=2025, base_salary=10_000_000, signing_bonus_proration=0),
            ContractYearInput(season=2026, base_salary=12_000_000, signing_bonus_proration=0),
            ContractYearInput(season=2027, base_salary=14_000_000, signing_bonus_proration=0),
        ]
        result = calculate_restructure(years, restructure_season=2025, amount_to_convert=9_000_000)
        # $9M / 3 years = $3M/yr new proration.
        assert result.new_proration_per_year == 3_000_000.0
        assert result.original_cap_hit == 10_000_000.0
        assert result.new_cap_hit == pytest.approx(10_000_000 - 9_000_000 + 3_000_000)  # 4M
        assert result.current_year_savings == pytest.approx(6_000_000.0)
        assert result.future_seasons_affected == [2026, 2027]
        assert result.future_cap_hit_increases == {2026: 3_000_000.0, 2027: 3_000_000.0}

    def test_total_dollars_never_created_or_destroyed(self):
        years = [
            ContractYearInput(season=2025, base_salary=10_000_000, signing_bonus_proration=0),
            ContractYearInput(season=2026, base_salary=12_000_000, signing_bonus_proration=0),
        ]
        result = calculate_restructure(years, restructure_season=2025, amount_to_convert=5_000_000)
        # Savings this year must exactly equal the total future increase.
        total_future_increase = sum(result.future_cap_hit_increases.values())
        assert result.current_year_savings == pytest.approx(total_future_increase)

    def test_cannot_convert_more_than_base_salary(self):
        years = [ContractYearInput(season=2025, base_salary=5_000_000, signing_bonus_proration=0)]
        with pytest.raises(ValueError):
            calculate_restructure(years, restructure_season=2025, amount_to_convert=6_000_000)

    def test_cannot_convert_non_positive_amount(self):
        years = [ContractYearInput(season=2025, base_salary=5_000_000, signing_bonus_proration=0)]
        with pytest.raises(ValueError):
            calculate_restructure(years, restructure_season=2025, amount_to_convert=0)

    def test_proration_still_capped_at_five_years(self):
        years = [
            ContractYearInput(season=2025 + i, base_salary=10_000_000, signing_bonus_proration=0)
            for i in range(6)
        ]
        result = calculate_restructure(years, restructure_season=2025, amount_to_convert=5_000_000)
        # 6 years remaining, but proration still caps at 5.
        assert result.new_proration_per_year == 1_000_000.0
        assert len(result.future_seasons_affected) == 4  # 5 proration years - the restructure year itself


class TestTeamCapSummary:
    def test_small_roster_uses_full_roster_not_top51(self):
        hits = [1_000_000.0] * 10
        summary = summarize_team_cap(season=2026, salary_cap=250_000_000, active_cap_hits=hits, dead_cap=0)
        assert summary.top51_commitments == 10_000_000.0
        assert summary.full_roster_commitments == 10_000_000.0
        assert summary.available_cap_space == summary.effective_cap_space

    def test_roster_over_51_only_counts_top_51(self):
        # 55 players at $1M each, plus one $10M player.
        hits = [10_000_000.0] + [1_000_000.0] * 55
        summary = summarize_team_cap(season=2026, salary_cap=250_000_000, active_cap_hits=hits, dead_cap=0)
        assert summary.full_roster_commitments == 10_000_000.0 + 55_000_000.0
        # Top 51 = the $10M player + top 50 of the $1M players.
        assert summary.top51_commitments == 10_000_000.0 + 50_000_000.0
        assert summary.available_cap_space > summary.effective_cap_space

    def test_dead_cap_reduces_space(self):
        summary = summarize_team_cap(
            season=2026, salary_cap=250_000_000, active_cap_hits=[100_000_000.0], dead_cap=20_000_000.0
        )
        assert summary.available_cap_space == 250_000_000 - 100_000_000 - 20_000_000

    def test_negative_cap_space_when_overcommitted(self):
        summary = summarize_team_cap(
            season=2026, salary_cap=200_000_000, active_cap_hits=[210_000_000.0], dead_cap=0
        )
        assert summary.available_cap_space == -10_000_000.0

    def test_rejects_negative_salary_cap(self):
        with pytest.raises(ValueError):
            summarize_team_cap(season=2026, salary_cap=-1, active_cap_hits=[], dead_cap=0)
