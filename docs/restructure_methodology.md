# Restructure Methodology

Implemented in `app/services/cap_engine.calculate_restructure()` and exposed
via `POST /api/contracts/{id}/restructure`. See `docs/cap_engine.md` for the
exact formulas. Summary:

- A user-specified amount of a player's base salary in a given season is
  converted into signing-bonus-style proration.
- That amount is spread evenly across the remaining contract years, capped at
  5 total proration years (the same rule that governs an actual signing
  bonus).
- Current-year cap savings always exactly equal the sum of the future-year
  cap-hit increases — restructuring **never** creates or destroys total money
  owed, only shifts when it counts against the cap. This invariant is
  enforced by a dedicated unit test
  (`test_total_dollars_never_created_or_destroyed`).

## What is not modeled

- Restructuring a signing bonus that is itself already prorated (only base
  salary can be converted in this version).
- Voidable/void-year mechanics that some real restructures use to extend
  proration further into the future without adding real contract years.
- The simulator is a hypothetical scenario tool only — it does not change any
  stored contract data.
