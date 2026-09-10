# Financial Flexibility Methodology

Implemented in `app/services/financial_intelligence.calculate_financial_flexibility()`,
exposed via `GET /api/analytics/financial-flexibility`. **Cap space is not
the same as financial flexibility** — cap space answers "how much room is
there right now?"; flexibility additionally accounts for dead-cap exposure,
future guaranteed commitments, contracts about to come off the books, and
how concentrated spending is in a handful of contracts.

## The five factors

Each factor is scored 0–100 on its own transparent scale, then combined into
a single weighted score:

| Factor | Sub-score formula | Rationale |
|---|---|---|
| Current cap space | `clamp(cap_space_pct / 0.15 * 100)` | 15%+ of the cap available scores 100; negative space scores 0. |
| Dead-cap exposure | `clamp(100 - dead_cap_pct / 0.10 * 100)` | 10%+ of the cap tied up in dead money scores 0. |
| Future guaranteed commitments | `clamp(100 - future_guaranteed_pct / 0.20 * 100)` | Guaranteed base salary owed in *future* seasons, as a % of the current cap; 20%+ scores 0. |
| Contracts expiring soon | `clamp(expiring_pct / 0.20 * 100)` | Share of this season's commitments on contracts ending this season; 20%+ scores 100 (more flexibility coming). |
| Cap concentration | `clamp(100 - (top5_pct - 0.30) / 0.30 * 100)` | Share of total commitments in the team's 5 largest contracts; 30% or less scores 100, 60%+ scores 0. |

`cap_space_pct`, `dead_cap_pct`, and `future_guaranteed_pct` are expressed as
fractions of the league salary cap; `top5_pct` is a fraction of the team's
own total commitments (see `calculate_financial_concentration()`).

## Combining factors

```
score = Σ(sub_score_i × weight_i) / Σ(weight_i)
```

Default weights: cap space 0.30, dead cap 0.15, future guaranteed 0.20,
expiring contracts 0.15, concentration 0.20 (sum to 1.0, but the formula
normalizes regardless — **weights are configurable** via query params on the
endpoint, or the sliders on the Financial Flexibility page).

Every response includes a `factors` breakdown with each factor's score,
weight, a `+`/`-`/`~` direction, and a plain-language detail sentence — the
"Why" shown alongside the score, per the project's analytical rules. This is
a transparent, hand-verifiable formula, not an opaque or ML-driven output;
see `backend/tests/test_financial_intelligence.py` for worked examples.

## Related: Financial Concentration

`calculate_financial_concentration()` (`GET /api/analytics/concentration`)
reports what share of a team's cap sits in its top 1/3/5/10 contracts. High
concentration is not automatically labeled bad, nor low concentration good
— the endpoint's `interpretation` field notes it depends on team-building
strategy and competitive timeline, per the project's analytical rules.
