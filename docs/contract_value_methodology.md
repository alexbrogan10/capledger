# Contract Value / Market Analysis Methodology

Implemented in `app/services/financial_intelligence.calculate_market_comparison()`,
exposed via `GET /api/analytics/contract-value` (one contract) and
`GET /api/analytics/position-spending-comparison` (team-level, vs. league
average — see `docs/cap_engine.md` for the underlying cap-hit figures it
aggregates).

## What it compares

A contract's AAV against every other **active** contract at the same
position in Cap Ledger's own dataset:

- **Position percentile** — this contract's AAV rank among all same-position
  contracts (0–100).
- **Age-band percentile/median** — the same rank, narrowed to contracts
  within ±3 years of this player's age (falls back to the full position set
  if the age band is empty).
- **Cost vs. position median** — `aav - position_median_aav`. A
  `discrepancy_label` flags contracts paid 15%+ above (`potential cost
  discrepancy`) or below (`potential value discrepancy`) the position
  median.

## Why this is not "player value"

The product brief's Contract Value Analysis (section 14) and Contract Value
Discrepancy (section 32) describe comparing financial commitment to
*player-performance-derived* value. Cap Ledger's dataset has no performance
or production data — inventing it would violate the project's "never
fabricate" rule (see `docs/data_sources.md` and `docs/limitations.md`).

This implementation instead answers an honestly-computable question: **how
does this contract's cost compare to what other players at the position are
actually paid, in this dataset** — an internal market/positional comparison,
matching section 31's Contract Market Analysis. It never claims to know a
player's true on-field value, and every response carries a disclaimer to
that effect. A future phase with real performance data could extend this
into a genuine value-vs-cost comparison without changing this endpoint's
shape.
