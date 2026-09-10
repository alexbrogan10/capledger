# Financial Flexibility Methodology

**Status: not yet implemented as a scored metric.** A dedicated Financial
Flexibility Score (0–100, with configurable weighting) is part of Phase 3 of
the project roadmap (see `docs/architecture.md`).

Cap Ledger's Phase 1 Cap Overview page already draws the conceptual
distinction the eventual score will formalize: **cap space is not the same
as financial flexibility.** Cap space answers "how much room is there right
now?"; flexibility additionally depends on future commitments, dead-cap
exposure, expiring contracts, guaranteed-money concentration, and
restructuring potential. See the "Cap Space vs. Financial Flexibility" card
on that page.

When implemented, the score is expected to be a transparent, configurably
weighted combination of factors already computable from the Phase 1 schema
(current cap space, dead-cap exposure, guaranteed-money totals, contracts
expiring soon, cap concentration in top contracts) — not an opaque ML output.
Per the project's analytical rules, the score's contributing factors (the
"Why" breakdown) will always be shown alongside the number itself.
