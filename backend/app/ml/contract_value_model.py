"""Phase 5 — an optional, clearly-scoped ML model for contract-value
projection.

Per the project's analytical rules, ML is used only where it adds
meaningful predictive value beyond the deterministic cap engine, and never
for core cap-mechanics math (see app/services/cap_engine.py). This module
is the one place in Cap Ledger that trains and serves a model.

WHAT THIS MODEL IS: a linear regression predicting a contract's AAV from
position, age, and contract length, trained on Cap Ledger's own SYNTHETIC
demo dataset (see docs/data_sources.md). Because the training data was
itself generated from simple per-position/per-tier rules
(app/seed/demo_data.py), this model largely re-derives those generation
rules — it is a genuine demonstration of a trained, versioned, explainable
ML pipeline, NOT a claim about real-world NFL contract value. See
docs/ml_documentation.md for the full writeup, including why a
performance-based contract-risk model was deliberately NOT built (no real
performance/outcome labels exist in this dataset to train one against).

The model is trained lazily (on first request, against whatever data is
currently in the database) and cached in memory for the life of the
process, rather than shipped as a committed binary artifact — so it always
reflects the live demo dataset rather than going stale. See
get_or_train_model().
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split
from sqlalchemy.orm import Session

MODEL_NAME = "contract_value_linear_v1"
MODEL_VERSION = "1.0.0"
FEATURES = ["position", "age", "contract_length_years"]
TARGET = "annual_value"


@dataclass(frozen=True)
class ModelMetadata:
    name: str
    version: str
    trained_at: str
    dataset_size: int
    train_size: int
    test_size: int
    features: list[str]
    target: str
    r2_score: float
    mean_absolute_error: float
    positions_seen: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ContractValuePrediction:
    predicted_aav: float
    baseline_aav: float
    """The model's intercept — a league-average baseline before position/age/length adjustments."""
    drivers: list[str]
    metadata: ModelMetadata


class ContractValueModel:
    def __init__(self, pipeline_model: LinearRegression, position_columns: list[str], metadata: ModelMetadata):
        self._model = pipeline_model
        self._position_columns = position_columns
        self.metadata = metadata

    def predict(self, position: str, age: int, contract_length_years: int) -> ContractValuePrediction:
        row = {col: 0 for col in self._position_columns}
        col_name = f"position_{position}"
        if col_name in row:
            row[col_name] = 1
        elif position not in self.metadata.positions_seen:
            # Position wasn't in the training data at all (e.g. LS with a tiny sample) —
            # predict from the baseline + age/length only, and say so via drivers.
            pass
        row["age"] = age
        row["contract_length_years"] = contract_length_years

        x = pd.DataFrame([row])[["age", "contract_length_years"] + self._position_columns]
        predicted = float(self._model.predict(x)[0])
        predicted = max(0.0, round(predicted, 2))

        coefs = dict(zip(["age", "contract_length_years"] + self._position_columns, self._model.coef_))
        drivers = []
        pos_coef = coefs.get(col_name)
        if pos_coef is not None:
            direction = "above" if pos_coef >= 0 else "below"
            drivers.append(f"Position ({position}): {direction} the baseline position by ${abs(pos_coef):,.0f}/year.")
        else:
            drivers.append(f"Position ({position}) had too few training examples to get its own adjustment; using the baseline position.")
        age_coef = coefs["age"]
        drivers.append(f"Age: each additional year is associated with ${age_coef:,.0f}/year in AAV in this dataset.")
        length_coef = coefs["contract_length_years"]
        drivers.append(f"Contract length: each additional year is associated with ${length_coef:,.0f}/year in AAV in this dataset.")

        return ContractValuePrediction(
            predicted_aav=predicted,
            baseline_aav=round(float(self._model.intercept_), 2),
            drivers=drivers,
            metadata=self.metadata,
        )


_CACHED_MODEL: ContractValueModel | None = None


def _load_training_frame(db: Session) -> pd.DataFrame:
    from app.models.contract import Contract
    from app.models.player import Player

    rows = (
        db.query(Player.position, Player.age, Contract.contract_start, Contract.contract_end, Contract.annual_value)
        .join(Contract, Contract.player_id == Player.id)
        .filter(Contract.contract_status == "active")
        .all()
    )
    data = [
        {
            "position": position,
            "age": age,
            "contract_length_years": max(1, end - start + 1),
            "annual_value": float(aav),
        }
        for position, age, start, end, aav in rows
    ]
    return pd.DataFrame(data)


def train_contract_value_model(db: Session) -> ContractValueModel:
    """Trains (or retrains) the contract-value model against whatever
    active-contract data is currently in the database."""
    df = _load_training_frame(db)
    if len(df) < 20:
        raise ValueError("not enough training data to fit a contract-value model")

    dummies = pd.get_dummies(df["position"], prefix="position", drop_first=True)
    position_columns = list(dummies.columns)
    X = pd.concat([df[["age", "contract_length_years"]], dummies], axis=1)
    y = df[TARGET]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    metadata = ModelMetadata(
        name=MODEL_NAME,
        version=MODEL_VERSION,
        trained_at=datetime.now(timezone.utc).isoformat(),
        dataset_size=len(df),
        train_size=len(X_train),
        test_size=len(X_test),
        features=FEATURES,
        target=TARGET,
        r2_score=round(float(r2_score(y_test, y_pred)), 4),
        mean_absolute_error=round(float(mean_absolute_error(y_test, y_pred)), 2),
        positions_seen=sorted(df["position"].unique().tolist()),
    )

    return ContractValueModel(model, position_columns, metadata)


def get_or_train_model(db: Session, force_retrain: bool = False) -> ContractValueModel:
    global _CACHED_MODEL
    if _CACHED_MODEL is None or force_retrain:
        _CACHED_MODEL = train_contract_value_model(db)
    return _CACHED_MODEL
