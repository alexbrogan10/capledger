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

## Financial Flexibility Forecast & Sensitivity (Phase 4)

`GET /api/teams/{id}/financial-flexibility-forecast` projects the same
scoring formula across the multi-year window (project brief section 28),
using each future season's projected league cap (`base_cap × (1 +
growth_rate) ^ years_from_base`) and that season's already-committed
contracts, dead cap, and guarantees. Because the current season's
`years_from_base` is 0, its score is unaffected by the growth-rate
assumption — only future seasons move.

**Sensitivity analysis** (section 33): the endpoint also runs the forecast
at `growth_rate - sensitivity_delta` and `growth_rate + sensitivity_delta`
(default ±3 points) and reports whichever season shows the largest score
swing between the two. When every season's factors are already at their
scored ceiling or floor (a real, observed outcome for teams whose demo-data
commitments taper off quickly in later years — see
`docs/data_sources.md`), the score is genuinely insensitive to the growth
assumption in that range, and the endpoint says so plainly rather than
reporting a misleading non-zero difference.

**"What would change our mind"** (section 34): phrased directly from that
sensitivity comparison — e.g. "a lower cap-growth assumption would put 2027
flexibility at 84 instead of 89." The **narrative** field separately
explains season-over-season *changes* within the base forecast (≥8-point
swings), naming the single factor whose delta moved most between the two
seasons.

## Related: Financial Concentration

`calculate_financial_concentration()` (`GET /api/analytics/concentration`)
reports what share of a team's cap sits in its top 1/3/5/10 contracts. High
concentration is not automatically labeled bad, nor low concentration good
— the endpoint's `interpretation` field notes it depends on team-building
strategy and competitive timeline, per the project's analytical rules.
