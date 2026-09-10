# Methodology Overview

This document indexes Cap Ledger's methodology docs and defines the core
salary-cap terminology used throughout the application.

## Terminology

- **Salary cap**: the league-wide limit on a team's total cap-countable
  spending for a season.
- **Cap hit**: a player's cap-countable charge for one season (base salary +
  signing-bonus proration + roster bonus + incentives).
- **Dead cap / dead money**: cap charges that remain from a player no longer
  on the roster (from accelerated signing-bonus proration and/or guaranteed
  salary owed regardless of release).
- **Top-51 rule**: the NFL's offseason accounting rule under which only a
  team's 51 highest cap hits count against the cap.
- **AAV (Average Annual Value)**: a contract's total value divided by its
  length — a standardized way to compare contracts of different lengths.
- **Guaranteed money**: the portion of a contract's value the team owes the
  player regardless of whether he remains on the roster.
- **Cap space**: `salary_cap − commitments − dead_cap` (see `docs/cap_engine.md`
  for the exact top-51 vs. full-roster variants Cap Ledger reports).
- **Financial flexibility**: a broader concept than cap space — it accounts
  for future commitments, dead-cap exposure, expiring contracts, and
  restructuring potential. Cap Ledger deliberately treats this as distinct
  from cap space (see `docs/cap_engine.md` and the Cap Overview page); a
  dedicated Financial Flexibility score is reserved for a later phase.

## Where to look

| Topic | Document |
|---|---|
| Cap-hit, dead-cap, restructure math | `docs/cap_engine.md` |
| Release scenario mechanics | `docs/release_methodology.md` |
| Restructure scenario mechanics | `docs/restructure_methodology.md` |
| Contract extension modeling | `docs/extension_methodology.md` |
| Financial flexibility scoring | `docs/financial_flexibility.md` |
| Demo data provenance | `docs/data_sources.md` |
| ML usage and constraints | `docs/ml_documentation.md` |
| Known simplifications | `docs/limitations.md` |
