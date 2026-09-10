# Trade Methodology

Implemented in `app/services/cap_engine.calculate_trade_impact()`, exposed
via `POST /api/contracts/{id}/trade`.

- **Trading team**: identical dead-cap mechanics to a standard (non-June-1)
  release — all remaining signing-bonus proration accelerates into the trade
  season. The NFL does not offer a June-1 designation for trades, so this
  path is not modeled for the trading team.
- **Acquiring team**: inherits only the remaining base salary, roster bonus,
  and incentives for each remaining season, at face value. No signing-bonus
  proration carries over — that money was already paid by, and remains the
  dead-cap obligation of, the trading team.
- **Not modeled**: trade compensation (draft picks, other players exchanged)
  and whether any team would actually agree to the trade. This endpoint
  answers "what does this contract cost/save if traded," not "should this
  trade happen."
- Every trade run is recorded to `contract_scenarios` for audit.
- The calculator is a hypothetical scenario tool only — it does not change
  any stored contract, roster, or team data. It is designed to work
  standalone but with a clean interface that a future Trade Block
  integration could call (project brief section 51).
