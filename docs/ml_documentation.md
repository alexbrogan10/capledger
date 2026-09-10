# ML Documentation

Per the project's analytical rules, ML is optional and secondary to the
deterministic cap engine (`docs/cap_engine.md`), and is never used for core
cap-mechanics calculations (cap hits, dead cap, release/restructure/trade
math). This document covers the one model Cap Ledger trains and serves:
`contract_value_linear_v1`, implemented in
`backend/app/ml/contract_value_model.py`.

## What it is

A linear regression predicting a contract's AAV from three features:
**position** (one-hot encoded), **age**, and **contract length (years)**.
Exposed via `GET /api/ml/contract-value-projection` and shown on the
Analytics & Models page alongside a transparent, non-ML comparable-contract
search (`docs/contract_value_methodology.md`).

## Training data

The model trains on every **active** contract in Cap Ledger's own
**synthetic demo dataset** (see `docs/data_sources.md`) — currently ~1,700
rows across 32 teams. There is no other data source. Because that dataset
was itself generated from simple per-position/per-tier AAV ranges
(`app/seed/demo_data.py`), this model substantially **re-derives its own
training data's generation rules** rather than learning anything about
real-world NFL contracts. It is a genuine, working ML pipeline — trained,
evaluated, versioned, and explainable — but a demonstration of that pipeline,
not a real market-value predictor. **Never present its output as fact.**

## Features, target, and preprocessing

- **Features**: `position` (one-hot, drop-first), `age`, `contract_length_years`
  (`contract_end - contract_start + 1`).
- **Target**: `annual_value` (AAV).
- **Preprocessing**: none beyond one-hot encoding — no scaling, since linear
  regression coefficients stay directly interpretable in dollar terms this way.

## Training and validation

- 80/20 train/test split, `random_state=42` (deterministic — see
  `tests/test_ml_contract_value.py::test_deterministic_given_same_data`).
- No temporal leakage concern applies here: this is a cross-sectional
  regression on contemporaneous, already-known contract terms, not a
  forecast of a future outcome from past-only information. A future
  performance-based model (see "What was deliberately not built" below)
  would need to enforce a strict past-only feature cutoff to avoid leakage;
  this document will be updated if/when such a model is added.
- **Evaluation metrics** (recomputed on each retrain; typical values on the
  current demo dataset): R² ≈ 0.53, mean absolute error ≈ $2.7M. An R² this
  far from 1.0 is expected and correctly reported — the demo dataset's
  biggest AAV driver is "starter vs. depth" tier, which isn't a feature
  available to the model, so a meaningful share of variance is left
  unexplained. This is reported plainly via `GET /api/ml/model-info`, not
  hidden.

## Explainability

Every prediction returns its `drivers`: the position coefficient (in
dollars/year relative to the model's baseline position) and the age and
contract-length coefficients (dollars/year of AAV per additional year),
read directly off the fitted linear model — not a post-hoc approximation.
Every prediction also carries an explicit disclaimer that it is an estimate
from a model trained on synthetic data, not a fact.

## Model versioning & auditability

`GET /api/ml/model-info` and every projection response include: model name
and version, training timestamp, dataset size, train/test split sizes,
features, target, R², MAE, and the positions actually seen in training.
The model is **trained lazily on first request per process** (and cached
for that process's lifetime) rather than shipped as a committed binary
artifact — so it always reflects whatever is currently in the database
rather than going stale relative to the live demo dataset. Retraining
(`get_or_train_model(db, force_retrain=True)`) produces a fresh
`trained_at` timestamp and recomputed metrics.

## What was deliberately NOT built

- **A contract-risk ML model.** The product brief describes estimating "the
  probability of a contract becoming financially inefficient based on
  historical patterns." Cap Ledger's dataset has no real outcome/performance
  labels to train such a classifier against — building one would mean
  fitting to synthetic noise and presenting it as signal, which violates the
  project's "never fabricate" rule. Contract Risk therefore stays fully
  deterministic (`docs/contract_risk_methodology.md`), consistent with
  analytical rule #12: use ML only where it adds meaningful predictive
  value.
- **A genuine multi-season historical archive.** Comparable-contract search
  (`docs/contract_value_methodology.md`) runs against the current synthetic
  roster snapshot, not a true historical database spanning past seasons —
  see `docs/data_sources.md` for why.
