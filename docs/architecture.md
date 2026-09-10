# Architecture

Cap Ledger is a two-tier application: a FastAPI backend backed by PostgreSQL, and a
React/TypeScript frontend. It is the first component of a planned larger "NFL Front
Office Analytics Suite"; this repository implements Cap Ledger only.

## Component overview

```
┌─────────────────────┐        HTTP/JSON        ┌──────────────────────────┐
│   React + Vite SPA  │  ───────────────────▶   │  FastAPI application     │
│   (TypeScript,      │  ◀───────────────────   │  (app/main.py + routers) │
│    Tailwind CSS,     │                         │                          │
│    Recharts)         │                         └────────────┬─────────────┘
└─────────────────────┘                                       │
                                                                │ SQLAlchemy ORM
                                                                ▼
                                                     ┌──────────────────────┐
                                                     │      PostgreSQL      │
                                                     └──────────────────────┘
```

## Backend layout (`backend/app`)

- `config.py` — `pydantic-settings`-based configuration, loaded from environment
  variables / `.env`.
- `database.py` — SQLAlchemy engine, session factory, declarative base.
- `models/` — ORM models for the Phase 1 schema: `Team`, `Player`, `Contract`,
  `ContractYear`, `TeamCap`, `TeamRoster`.
- `services/cap_engine.py` — **the deterministic, rule-based salary-cap engine.**
  This is the single source of truth for every cap-mechanics calculation
  (signing-bonus proration, cap hits, dead money, release/restructure impact,
  team-cap rollups). It has no database or web-framework dependency and is
  covered by an extensive hand-verified unit-test suite
  (`backend/tests/test_cap_engine.py`).
- `services/decision_points.py` — analytical (non-predictive) flags on a
  contract's timeline: expiration, large cap-hit years, potential release
  points, possible extension windows.
- `schemas/` — Pydantic request/response models.
- `api/` — FastAPI routers (`teams`, `players`, `contracts`).
- `seed/` — the synthetic demo-data generator (see `docs/data_sources.md`).

## Frontend layout (`frontend/src`)

- `api/client.ts`, `api/types.ts` — a small typed fetch wrapper around the
  backend's REST API.
- `lib/AppState.tsx` — global team/season selection, shared across pages.
- `components/` — shared UI primitives (`Card`, `StatTile`, `Badge`, layout
  shell) and the top navigation.
- `pages/` — one component per major section: Dashboard, Cap Overview, Roster
  Ledger, Contract Explorer, Player Contract Profile, Release Calculator.

## Why a deterministic cap engine

Section 40/41 of the product brief calls for ML to be optional and secondary to
a transparent, rule-based core. Every dollar figure Cap Ledger displays for
Phase 1 (cap hits, dead cap, release/restructure impact, team cap space) is
produced by plain arithmetic functions in `cap_engine.py` that can be
hand-verified — there is no model in the loop for these calculations. See
`docs/cap_engine.md` for the exact rules implemented.

## What's implemented vs. reserved for later phases

The product brief describes a much larger platform (see the repository's task
history / roadmap). This repository implements **Phase 1 (MVP)**:

- Teams, players, contracts, contract-years, team cap sheets, rosters.
- Executive Dashboard, Cap Overview, Roster Ledger, Contract Explorer, Player
  Contract Profile, Release Calculator.
- A release *and* restructure simulator (restructure was pulled forward from
  Phase 2 because it shares the same engine and rounds out the "what should we
  do with this contract" workflow cheaply).

Tables and endpoints for later phases (historical contracts, contract
scenarios stored to a database, cap projections with adjustable assumptions,
team needs, position-spending as a persisted table, ML-driven contract value /
risk models) are intentionally **not** built yet, per the roadmap's phased
approach and the project's build-quality rule against building ahead of
validated need. The schema and API are structured so those phases can be
added without reworking Phase 1.
