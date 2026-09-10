# Extension Methodology

**Status: not yet implemented.** The Contract Extension Simulator is part of
Phase 2 of the project roadmap (see `docs/architecture.md`) and is not present
in this Phase 1 release.

When implemented, it is expected to reuse the same cap-engine primitives as
the release and restructure simulators (`docs/cap_engine.md`): a hypothetical
new contract (years, AAV, guaranteed money, signing bonus) would be run
through the same proration and cap-hit functions, and compared year-by-year
against the player's current contract. All extension terms would be clearly
labeled as hypothetical, per the project's analytical rules — Cap Ledger never
presents a modeled extension as an actual signed contract.
