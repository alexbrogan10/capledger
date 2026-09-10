# Cap Engine Methodology

`backend/app/services/cap_engine.py` implements a simplified but internally
consistent model of NFL salary-cap accounting. This document states exactly
which rules are modeled, which are simplified, and why — so every number the
application shows can be traced back to an explicit assumption.

## Signing-bonus proration

A signing bonus is spread evenly across the life of the contract, **capped at
5 league years**, matching the real CBA rule that proration cannot exceed 5
years regardless of contract length.

```
proration_per_year = signing_bonus / min(contract_length_years, 5)
```

A 7-year contract with a $25M bonus still prorates at $5M/year for 5 years,
with $0 incremental bonus recognition in years 6–7.

## Cap hit

```
cap_hit = base_salary + signing_bonus_proration + roster_bonus + incentives
```

Incentive types are not differentiated (LTBE vs. NLTBE) in this version — see
`docs/limitations.md`.

## Dead cap / release impact

- **Standard ("pre-June 1") release**: all remaining, not-yet-amortized
  signing-bonus proration accelerates immediately into the release season's
  dead cap, along with any guaranteed base salary for that season.
- **Post-June 1 release**: only the release season's own proration (plus that
  season's guaranteed salary) counts against the release-season cap; the rest
  of the remaining proration is pushed to the **following** league year.

Both paths are implemented in `calculate_dead_cap()` and produce identical
*total* dead cap — post-June 1 only changes *when* it is recognized, never how
much.

## Restructuring

`calculate_restructure()` models converting a slice of a player's base salary
in a given season into bonus-style proration, spread evenly across the
remaining contract years (capped at 5 total proration years, same rule as a
signing bonus). This always trades current-year cap room for future-year cap
obligations — the engine asserts (and tests verify) that current-year savings
exactly equal the sum of the future-year increases. **Restructuring never
creates or destroys money — only when it counts against the cap.**

## Team-cap rollups

- **Top-51 rule**: during the offseason, only a team's 51 highest cap hits
  count. `summarize_team_cap()` sorts active cap hits descending and sums the
  top 51 (or all of them, if the roster has 51 or fewer charged players).
- **Available cap space** = `salary_cap − top51_commitments − dead_cap` (the
  commonly reported offseason figure).
- **Effective cap space** = `salary_cap − full_roster_commitments − dead_cap`
  (space once every roster spot counts, not just the top 51).

## Rookie contract estimation (Phase 4)

`estimate_rookie_contract_terms()` provides a **simplified, per-round flat
estimate** of a rookie contract's top-line terms (length, total value,
signing bonus, guaranteed money) — used by the Rookie Contract Planning
endpoint (`POST /api/teams/{id}/rookie-planning`). This is explicitly **not**
the real NFL rookie wage scale, which is set by a CBA-defined formula that
varies continuously by exact draft pick, not just round. All rookie deals
are modeled as standard 4-year contracts (no fifth-year option). The
resulting terms are run through `structure_contract_years()` just like any
other hypothetical contract.

## What is intentionally simplified

See `docs/limitations.md` for the full list. In short: no void years, no
split contracts, no LTBE/NLTBE incentive distinction, no offset language on
released contracts, no per-player cash-flow vs. cap distinction beyond the
base fields modeled here. These are documented simplifications of real CBA
mechanics, not a claim to proprietary or perfectly accurate NFL accounting.
