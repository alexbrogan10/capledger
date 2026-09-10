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
- `models/` — ORM models: `Team`, `Player`, `Contract`, `ContractYear`,
  `TeamCap`, `TeamRoster` (Phase 1); `ContractScenario` (an audit row for
  every simulated release/restructure/extension/trade) and `CapProjection`
  (a stored multi-year projection run under a given growth-rate assumption)
  (Phase 2).
- `services/cap_engine.py` — **the deterministic, rule-based salary-cap engine.**
  This is the single source of truth for every cap-mechanics calculation
  (signing-bonus proration, cap hits, dead money, release/restructure impact,
  team-cap rollups). It has no database or web-framework dependency and is
  covered by an extensive hand-verified unit-test suite
  (`backend/tests/test_cap_engine.py`).
- `services/decision_points.py` — analytical (non-predictive) flags on a
  contract's timeline: expiration, large cap-hit years, potential release
  points, possible extension windows.
- `services/financial_intelligence.py` — Phase 3/5 deterministic scoring:
  financial flexibility, financial concentration, contract risk,
  contract-vs-market comparison, and comparable-contract search. No ML;
  every score is a documented, hand-verifiable formula (see
  `docs/financial_flexibility.md`, `docs/contract_risk_methodology.md`,
  `docs/contract_value_methodology.md`).
- `ml/contract_value_model.py` — the one place Cap Ledger trains and serves
  an ML model (Phase 5): a linear regression estimating AAV from
  position/age/contract length, trained lazily against the live database
  and fully documented in `docs/ml_documentation.md`.
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

The product brief describes a much larger platform. This repository
implements **Phase 1 (MVP)** and **Phase 2 (Contract Strategy)**:

**Phase 1** — Teams, players, contracts, contract-years, team cap sheets,
rosters; Executive Dashboard, Cap Overview, Roster Ledger, Contract Explorer,
Player Contract Profile, Release Calculator.

**Phase 2** — Restructure Simulator, Extension Simulator, Trade Contract
Calculator, a Contract Scenario Builder ("What should we do with this
contract?" — Keep/Restructure/Release/Trade compared side by side),
adjustable-assumption Cap Projections, and a Dead-Cap Dashboard. Every
simulated scenario (release/restructure/extension/trade) is persisted to a
`contract_scenarios` audit table with its exact assumptions, results, and
cap-engine version — see `docs/cap_engine.md`'s "Auditability" note and
section 43 of the product brief.

**Phase 3** — Financial Intelligence: a Financial Flexibility Score
(deliberately distinct from cap space, configurable weighting — see
`docs/financial_flexibility.md`), Financial Concentration (top-1/3/5/10
share of cap), Contract Risk (a transparent, non-ML structural risk score —
`docs/contract_risk_methodology.md`), Contract Value/Market Analysis (AAV
vs. same-position contracts in the dataset — `docs/contract_value_methodology.md`,
deliberately scoped away from fabricated performance data), and Position
Spending vs. league average. All Phase 3 scoring lives in
`app/services/financial_intelligence.py`, following the same
deterministic-and-tested pattern as the cap engine.

**Phase 4** — Scenario Analysis: a Financial Flexibility Forecast across the
full projection window with growth-rate sensitivity and an automatic "what
would change our mind" comparison (`GET /api/teams/{id}/financial-flexibility-forecast`);
Free-Agent Planning (`POST /api/teams/{id}/free-agent-planning`, hypothetical
signing → before/after cap space and flexibility); and Rookie Contract
Planning (`POST /api/teams/{id}/rookie-planning`, a simplified per-round
rookie-cost estimate → cap impact of drafting several players). All three
reuse the same `cap_engine` and `financial_intelligence` primitives rather
than introducing new calculation logic.

**Phase 5** — Historical Analytics & ML: a comparable-contract search
(`GET /api/analytics/comparable-contracts`, a transparent distance formula —
not ML) and one genuine, versioned ML model, `contract_value_linear_v1`
(`backend/app/ml/contract_value_model.py`, `GET /api/ml/contract-value-projection`,
`GET /api/ml/model-info`) — a linear regression trained on Cap Ledger's own
synthetic dataset, fully documented in `docs/ml_documentation.md` including
why a contract-risk ML model was deliberately *not* built (no real outcome
labels to train against).

**Phase 6** — Production polish: a Contract Decision Report page
(`/contract-report/:playerId`, matching the exact report format in the
product brief) with a print stylesheet for PDF export; CSV export on the
Roster Ledger and Contract Explorer; route-level code-splitting
(`React.lazy`/`Suspense` per page, with Recharts split into its own chunk)
that cut the initial JS bundle from ~613KB to ~180KB gzip; a GitHub Actions
CI workflow (`.github/workflows/ci.yml`) running the backend test suite
against a real Postgres service container and the frontend typecheck/build
on every push and PR; and additional edge-case test coverage
(`tests/test_edge_cases.py`) for boundary contract structures and malformed
API requests.

Tables and endpoints for later phases (a genuine multi-season historical
contract archive, team needs, competitive-timeline classification) are
intentionally **not** built yet, per the roadmap's phased approach and the
project's build-quality rule against building ahead of validated need. The
schema and API are structured so those phases can be added without
reworking earlier ones.
