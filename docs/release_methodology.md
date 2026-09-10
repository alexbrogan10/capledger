# Release Methodology

Implemented in `app/services/cap_engine.calculate_dead_cap()` and exposed via
`POST /api/contracts/{id}/release`. See `docs/cap_engine.md` for the exact
formulas. Summary:

- **Standard release**: all remaining signing-bonus proration for the
  contract accelerates into the release season, plus any guaranteed base
  salary owed for that season.
- **Post-June 1 release**: the release season only bears its own season's
  proration (plus guaranteed salary due); the rest of the remaining proration
  shifts to the following league year. Total dead cap across both seasons is
  identical to the standard-release total — only the timing differs.
- **Cap savings** = the player's pre-release cap hit minus the resulting
  dead-cap charge for that season. This can be negative (a release can cost
  more than keeping the player, in a season with heavy remaining proration).

## What is not modeled

- Offset language (whether a new contract elsewhere reduces the releasing
  team's dead-cap obligation) is not modeled — see `docs/limitations.md`.
- The calculator is purely a hypothetical scenario tool: calling the release
  endpoint does not change any stored contract, roster, or team-cap data.
