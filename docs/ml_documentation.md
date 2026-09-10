# ML Documentation

**Status: no ML models are used in this Phase 1 release.** Per the project's
analytical rules, machine learning is optional and secondary to the
deterministic cap engine, and is never used for core cap-mechanics
calculations (cap hits, dead cap, release/restructure math) — those are
always plain, auditable arithmetic (`docs/cap_engine.md`).

Later phases of the roadmap describe optional ML applications — contract
value/efficiency projection, contract risk classification, historical
contract similarity — reserved for Phase 5. `scikit-learn`, `pandas`, and
`numpy` are included in `backend/requirements.txt` in anticipation of that
work but are not yet wired into any endpoint.

When ML components are added, this document will record, per model:

- **Features** used and their source tables.
- **Target** variable and how it is defined.
- **Training data** window and any known class imbalance.
- **Validation approach**, with explicit attention to preventing data leakage
  (e.g., a performance-projection model must only use information available
  at the time a contract decision would actually have been made).
- **Evaluation metrics** and their values.
- **Limitations**, and the plain-language "primary drivers" explanation shown
  alongside any prediction in the UI (predictions are never presented as
  facts — see the project's analytical rules).
- **Model version**, training date, and dataset version, so historical
  scenarios that used a given model remain reproducible.
