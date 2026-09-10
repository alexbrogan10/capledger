"""Deterministic, rule-based salary-cap calculation engine.

This module is the single source of truth for every cap-mechanics
calculation in Cap Ledger: signing-bonus proration, cap hits, dead money,
and release/team-cap rollups. It intentionally contains no machine
learning and no team- or player-specific special casing — every number it
produces should be reproducible by hand from the same inputs.

Modeled rules (see docs/cap_engine.md for full detail and citations):

* Signing bonus proration: an NFL signing bonus is spread evenly across the
  life of the contract, up to a maximum of 5 league years, per the CBA.
* Standard ("pre-June 1") release: all remaining, not-yet-amortized
  signing-bonus proration accelerates immediately onto the current season's
  cap, along with any guaranteed base salary for that season.
* Post-June 1 release: only the current season's own proration (plus any
  guaranteed salary due that season) counts against the current season's
  cap; all remaining future proration is pushed onto the *following*
  league year instead.
* Top-51 rule: during the offseason (before a team's roster is finalized
  to 53), only a team's 51 highest cap hits count against the cap.

These are simplifications of real, more intricate CBA mechanics (e.g. void
years, LTBE/NLTBE incentive rules, split contracts, option bonuses). They
are documented assumptions, not a claim of proprietary NFL accounting.
"""
from __future__ import annotations

from dataclasses import dataclass

MAX_PRORATION_YEARS = 5


def round2(value: float) -> float:
    return round(float(value) + 0.0, 2)


def signing_bonus_proration(signing_bonus: float, contract_length_years: int) -> float:
    """Annual signing-bonus proration for a contract of the given length.

    Proration is spread evenly over the contract, capped at
    ``MAX_PRORATION_YEARS`` league years regardless of how long the
    contract actually runs.
    """
    if contract_length_years <= 0:
        raise ValueError("contract_length_years must be positive")
    if signing_bonus < 0:
        raise ValueError("signing_bonus cannot be negative")
    proration_years = min(contract_length_years, MAX_PRORATION_YEARS)
    return round2(signing_bonus / proration_years)


def compute_cap_hit(
    base_salary: float,
    bonus_proration: float,
    roster_bonus: float = 0.0,
    incentives: float = 0.0,
) -> float:
    """A single season's cap hit."""
    for name, val in (
        ("base_salary", base_salary),
        ("bonus_proration", bonus_proration),
        ("roster_bonus", roster_bonus),
        ("incentives", incentives),
    ):
        if val < 0:
            raise ValueError(f"{name} cannot be negative")
    return round2(base_salary + bonus_proration + roster_bonus + incentives)


@dataclass(frozen=True)
class ContractYearInput:
    """Minimal per-season shape the engine needs; decoupled from the ORM
    so the engine can be unit tested without a database."""

    season: int
    base_salary: float
    signing_bonus_proration: float
    roster_bonus: float = 0.0
    incentives: float = 0.0
    guaranteed_base_salary: float = 0.0

    @property
    def cap_hit(self) -> float:
        return compute_cap_hit(
            self.base_salary, self.signing_bonus_proration, self.roster_bonus, self.incentives
        )


@dataclass(frozen=True)
class DeadCapResult:
    """Result of a release-impact calculation for one contract."""

    release_season: int
    june1: bool

    pre_release_cap_hit: float
    """What the player's cap hit would have been this season had they stayed."""

    current_year_dead_cap: float
    next_year_dead_cap: float
    """0.0 unless this was a June 1 release."""

    current_year_cap_charge: float
    """Net cap charge this season after release (== current_year_dead_cap)."""

    current_year_cap_savings: float
    """pre_release_cap_hit - current_year_cap_charge. Can be negative if a
    release costs *more* than keeping the player this season (common with
    large remaining bonus proration)."""

    next_year_cap_hit_removed: float
    """The cap hit the player would have carried next season, now zeroed
    out (informational: shows the future-year cap the team no longer owes,
    separate from next_year_dead_cap)."""

    total_dead_cap: float
    """current_year_dead_cap + next_year_dead_cap."""


def calculate_dead_cap(
    contract_years: list[ContractYearInput],
    release_season: int,
    june1: bool = False,
) -> DeadCapResult:
    """Compute the dead-cap consequence of releasing a player before
    ``release_season``.

    ``contract_years`` must include every remaining season of the contract
    from ``release_season`` onward (seasons before ``release_season`` are
    ignored). If ``release_season`` is not itself present in
    ``contract_years`` (e.g. it's already past the contract), all
    remaining proration is treated as already fully amortized.
    """
    remaining = sorted((cy for cy in contract_years if cy.season >= release_season), key=lambda c: c.season)

    if not remaining:
        return DeadCapResult(
            release_season=release_season,
            june1=june1,
            pre_release_cap_hit=0.0,
            current_year_dead_cap=0.0,
            next_year_dead_cap=0.0,
            current_year_cap_charge=0.0,
            current_year_cap_savings=0.0,
            next_year_cap_hit_removed=0.0,
            total_dead_cap=0.0,
        )

    release_year_cy = remaining[0]
    pre_release_cap_hit = release_year_cy.cap_hit

    total_remaining_proration = round2(sum(cy.signing_bonus_proration for cy in remaining))
    guaranteed_due_this_season = release_year_cy.guaranteed_base_salary

    if not june1:
        current_year_dead_cap = round2(total_remaining_proration + guaranteed_due_this_season)
        next_year_dead_cap = 0.0
    else:
        current_year_dead_cap = round2(release_year_cy.signing_bonus_proration + guaranteed_due_this_season)
        next_year_dead_cap = round2(total_remaining_proration - release_year_cy.signing_bonus_proration)

    current_year_cap_charge = current_year_dead_cap
    current_year_cap_savings = round2(pre_release_cap_hit - current_year_cap_charge)

    next_year_cy = remaining[1] if len(remaining) > 1 else None
    next_year_cap_hit_removed = next_year_cy.cap_hit if next_year_cy else 0.0

    return DeadCapResult(
        release_season=release_season,
        june1=june1,
        pre_release_cap_hit=pre_release_cap_hit,
        current_year_dead_cap=current_year_dead_cap,
        next_year_dead_cap=next_year_dead_cap,
        current_year_cap_charge=current_year_cap_charge,
        current_year_cap_savings=current_year_cap_savings,
        next_year_cap_hit_removed=next_year_cap_hit_removed,
        total_dead_cap=round2(current_year_dead_cap + next_year_dead_cap),
    )


@dataclass(frozen=True)
class RestructureResult:
    season: int
    original_cap_hit: float
    new_cap_hit: float
    current_year_savings: float
    converted_amount: float
    new_proration_per_year: float
    future_seasons_affected: list[int]
    future_cap_hit_increases: dict[int, float]


def calculate_restructure(
    contract_years: list[ContractYearInput],
    restructure_season: int,
    amount_to_convert: float,
    remaining_contract_years_after: int | None = None,
) -> RestructureResult:
    """Simulate converting ``amount_to_convert`` of a player's *base
    salary* in ``restructure_season`` into signing-bonus-style proration,
    spread evenly across the remaining seasons of the contract (this
    season plus every later season still on the books, capped at 5 years
    total per the standard proration rule).

    This always trades current-year cap space for future-year cap
    obligations — it never reduces the total money owed, only when it
    counts against the cap.
    """
    remaining = sorted((cy for cy in contract_years if cy.season >= restructure_season), key=lambda c: c.season)
    if not remaining:
        raise ValueError("restructure_season is not within the contract's remaining years")

    target = remaining[0]
    if amount_to_convert <= 0:
        raise ValueError("amount_to_convert must be positive")
    if amount_to_convert > target.base_salary:
        raise ValueError("amount_to_convert cannot exceed the season's base salary")

    years_remaining = len(remaining)
    proration_years = min(years_remaining, MAX_PRORATION_YEARS)
    new_proration_per_year = round2(amount_to_convert / proration_years)

    original_cap_hit = target.cap_hit
    new_cap_hit = round2(
        (target.base_salary - amount_to_convert)
        + target.signing_bonus_proration
        + new_proration_per_year
        + target.roster_bonus
        + target.incentives
    )
    current_year_savings = round2(original_cap_hit - new_cap_hit)

    future_seasons = [cy.season for cy in remaining[1:proration_years]]
    future_increases = {season: new_proration_per_year for season in future_seasons}

    return RestructureResult(
        season=restructure_season,
        original_cap_hit=original_cap_hit,
        new_cap_hit=new_cap_hit,
        current_year_savings=current_year_savings,
        converted_amount=round2(amount_to_convert),
        new_proration_per_year=new_proration_per_year,
        future_seasons_affected=future_seasons,
        future_cap_hit_increases=future_increases,
    )


@dataclass(frozen=True)
class TeamCapSummary:
    season: int
    salary_cap: float
    full_roster_commitments: float
    top51_commitments: float
    dead_cap: float
    available_cap_space: float
    effective_cap_space: float


def summarize_team_cap(
    season: int,
    salary_cap: float,
    active_cap_hits: list[float],
    dead_cap: float,
) -> TeamCapSummary:
    """Roll up a team's cap sheet for one season.

    * ``full_roster_commitments`` sums every active contract's cap hit
      (the number that applies once the 53-man roster is locked in).
    * ``top51_commitments`` sums only the 51 highest cap hits, the rule
      that governs offseason accounting whenever a team carries fewer than
      51 charged players (typical pre-June roster).
    * ``available_cap_space`` = salary_cap - top51_commitments - dead_cap
      (the commonly reported offseason "cap space" figure).
    * ``effective_cap_space`` = salary_cap - full_roster_commitments -
      dead_cap (the cap space that remains once the full roster counts,
      i.e. what's left after every remaining roster spot is accounted for).
    """
    if salary_cap < 0:
        raise ValueError("salary_cap cannot be negative")

    full_roster_commitments = round2(sum(active_cap_hits))
    sorted_hits = sorted(active_cap_hits, reverse=True)
    top51_hits = sorted_hits[:51] if len(sorted_hits) > 51 else sorted_hits
    top51_commitments = round2(sum(top51_hits))

    available_cap_space = round2(salary_cap - top51_commitments - dead_cap)
    effective_cap_space = round2(salary_cap - full_roster_commitments - dead_cap)

    return TeamCapSummary(
        season=season,
        salary_cap=round2(salary_cap),
        full_roster_commitments=full_roster_commitments,
        top51_commitments=top51_commitments,
        dead_cap=round2(dead_cap),
        available_cap_space=available_cap_space,
        effective_cap_space=effective_cap_space,
    )
