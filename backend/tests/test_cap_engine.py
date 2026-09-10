"""Unit tests for the deterministic cap engine, using hand-calculated
scenarios so every assertion can be independently verified."""
import pytest

from app.services.cap_engine import (
    ContractYearInput,
    calculate_dead_cap,
    calculate_extension,
    calculate_restructure,
    calculate_trade_impact,
    compute_cap_hit,
    signing_bonus_proration,
    structure_contract_years,
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


class TestStructureContractYears:
    def test_total_cash_matches_total_value(self):
        years = structure_contract_years(
            start_season=2026, length_years=4, total_value=40_000_000,
            signing_bonus=8_000_000, guaranteed_money=20_000_000,
        )
        total_base = sum(y.base_salary for y in years)
        assert round(total_base + 8_000_000, 2) == 40_000_000.0

    def test_proration_capped_at_five_years(self):
        years = structure_contract_years(
            start_season=2026, length_years=7, total_value=70_000_000,
            signing_bonus=35_000_000, guaranteed_money=35_000_000,
        )
        assert years[0].signing_bonus_proration == 7_000_000.0  # 35M / 5
        assert years[5].signing_bonus_proration == 0.0
        assert years[6].signing_bonus_proration == 0.0

    def test_base_salaries_increase_across_years(self):
        years = structure_contract_years(
            start_season=2026, length_years=4, total_value=40_000_000,
            signing_bonus=8_000_000, guaranteed_money=8_000_000,
        )
        base_salaries = [y.base_salary for y in years]
        assert base_salaries == sorted(base_salaries)

    def test_guaranteed_money_cannot_exceed_total_value(self):
        with pytest.raises(ValueError):
            structure_contract_years(
                start_season=2026, length_years=2, total_value=10_000_000,
                signing_bonus=0, guaranteed_money=20_000_000,
            )

    def test_signing_bonus_cannot_exceed_total_value(self):
        with pytest.raises(ValueError):
            structure_contract_years(
                start_season=2026, length_years=2, total_value=10_000_000,
                signing_bonus=20_000_000, guaranteed_money=0,
            )


class TestTradeImpact:
    def _years(self):
        return [
            ContractYearInput(season=2026, base_salary=5_000_000, signing_bonus_proration=4_000_000),
            ContractYearInput(season=2027, base_salary=7_000_000, signing_bonus_proration=4_000_000),
            ContractYearInput(season=2028, base_salary=9_000_000, signing_bonus_proration=4_000_000),
        ]

    def test_trading_team_dead_cap_matches_standard_release(self):
        trade = calculate_trade_impact(self._years(), trade_season=2027)
        release = calculate_dead_cap(self._years(), release_season=2027, june1=False)
        assert trade.trading_team_dead_cap == release.current_year_dead_cap
        assert trade.trading_team_cap_savings == release.current_year_cap_savings

    def test_acquiring_team_excludes_bonus_proration(self):
        trade = calculate_trade_impact(self._years(), trade_season=2027)
        # Acquiring team pays base salary only, no proration.
        assert trade.acquiring_team_cap_hits == {2027: 7_000_000.0, 2028: 9_000_000.0}
        assert trade.acquiring_team_total_remaining_commitment == 16_000_000.0

    def test_trade_after_contract_ends_is_a_no_op(self):
        trade = calculate_trade_impact(self._years(), trade_season=2030)
        assert trade.trading_team_dead_cap == 0.0
        assert trade.acquiring_team_cap_hits == {}


class TestExtension:
    def test_combined_timeline_preserves_existing_years(self):
        current = [
            ContractYearInput(season=2026, base_salary=10_000_000, signing_bonus_proration=2_000_000),
            ContractYearInput(season=2027, base_salary=12_000_000, signing_bonus_proration=2_000_000),
        ]
        result = calculate_extension(
            current, extension_start_season=2028, new_length_years=3,
            new_total_value=60_000_000, new_signing_bonus=15_000_000, new_guaranteed_money=30_000_000,
        )
        assert [y.season for y in result.current_contract_years] == [2026, 2027]
        assert [y.season for y in result.new_contract_years] == [2028, 2029, 2030]
        assert [y.season for y in result.combined_years] == [2026, 2027, 2028, 2029, 2030]

    def test_total_new_commitment_matches_input(self):
        current = [ContractYearInput(season=2026, base_salary=10_000_000, signing_bonus_proration=0)]
        result = calculate_extension(
            current, extension_start_season=2027, new_length_years=2,
            new_total_value=30_000_000, new_signing_bonus=10_000_000, new_guaranteed_money=15_000_000,
        )
        assert result.total_new_commitment == 30_000_000.0
        assert result.total_new_guaranteed == 15_000_000.0

    def test_extension_replacing_final_current_season(self):
        # extension_start_season equal to an existing season drops that
        # season from "current" (it's superseded by the new deal).
        current = [ContractYearInput(season=2026, base_salary=10_000_000, signing_bonus_proration=0)]
        result = calculate_extension(
            current, extension_start_season=2026, new_length_years=1,
            new_total_value=20_000_000, new_signing_bonus=5_000_000, new_guaranteed_money=10_000_000,
        )
        assert result.current_contract_years == []
        assert len(result.combined_years) == 1
