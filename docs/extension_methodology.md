# Extension Methodology

Implemented in `app/services/cap_engine.calculate_extension()` /
`structure_contract_years()`, exposed via `POST /api/contracts/{id}/extend`.

- All new-contract terms (extension start season, length, total value,
  signing bonus, guaranteed money) are **user-supplied hypothetical inputs**
  — Cap Ledger never predicts or infers what a real negotiation would
  produce.
- `structure_contract_years()` turns those summary terms into a year-by-year
  schedule using the same general approach as the demo-data generator:
  signing bonus prorates evenly (capped at 5 years), remaining cash
  escalates across the contract, and guaranteed money is front-loaded as
  guaranteed base salary. This is a structuring *assumption*, not a claim
  about how any specific real deal would be built.
- The simulator returns the player's existing contract years (truncated at
  the extension start season), the new hypothetical years, and the combined
  timeline — so the UI can show "current vs. extension" side by side (see
  the Contract Extension Simulator page).
- Every extension run is recorded to `contract_scenarios` for audit
  (`docs/architecture.md`, section 43 of the product brief).
- The simulator is a hypothetical scenario tool only — it does not change
  any stored contract data.
