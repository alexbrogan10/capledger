# Contract Risk Methodology

Implemented in `app/services/financial_intelligence.calculate_contract_risk()`,
exposed via `GET /api/analytics/contract-risk`. An additive, transparent
0–100 score built from four factors — never an ML prediction, and never a
claim that any player *will* decline.

## Factors

1. **Age relative to position.** Each position has a modeled decline-risk
   age (`POSITION_DECLINE_AGE` — e.g. RB 27, WR/CB/S 29–30, offensive/
   defensive line 30–31, QB/specialists 33–34). A player at or past that age
   adds `clamp(20 + 8 × years_over, 0, 35)` points. This is a simplifying,
   documented assumption about typical position aging curves — not a
   prediction about any individual.
2. **Contract length.** 4+ years remaining adds 25 points; 2–3 years adds
   10; 0–1 years adds 0 (less long-term exposure).
3. **Guaranteed money.** 60%+ of the contract guaranteed adds 25 points;
   35–59% adds 10; below 35% adds 0.
4. **Future cap concentration.** If any remaining season's cap hit reaches
   12%+ of an assumed league cap, adds 15 points.

`risk_score = clamp(sum of points, 0, 100)`. Category thresholds: **Low**
(<25), **Moderate** (25–49), **High** (50–74), **Very High** (75+).

## What this is not

- Not a performance or health prediction — Cap Ledger's dataset has no such
  data (see `docs/data_sources.md`), and the score never uses it.
- Not a claim that a player will decline — every factor description in the
  API response is phrased as increased/decreased *financial* risk from
  contract structure, per the project's analytical rules.
- Not position-value-adjusted beyond the decline-age table — a premium
  position with the same structural risk factors scores identically to a
  non-premium one.

See `backend/tests/test_financial_intelligence.py::TestContractRisk` for
worked examples (e.g., a 34-year-old RB with a 5-year, 80%-guaranteed deal
scores the maximum 100/Very High; a 24-year-old WR on a 1-year, lightly
guaranteed deal scores Low).
