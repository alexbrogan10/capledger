# Data Pipeline Directories

Reserved for a future CSV-based ingestion pipeline (raw → processed →
outputs), as described in the project brief. **Phase 1 does not use this
directory** — the demo dataset is generated directly by
`backend/app/seed/demo_data.py` and loaded into PostgreSQL by
`backend/app/seed/seed.py` (see `docs/data_sources.md`).

- `raw/` — would hold unmodified source files (e.g. `players.csv`,
  `contracts.csv`).
- `processed/` — would hold cleaned/standardized versions after name,
  team, and position normalization.
- `outputs/` — would hold derived datasets (e.g. computed cap projections)
  for inspection outside the database.

These directories are kept (with `.gitkeep`) so a future data-loading phase
has a place to land without restructuring the repository.
