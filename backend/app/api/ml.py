from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.ml.contract_value_model import get_or_train_model
from app.schemas.ml import ContractValueProjectionOut, ModelMetadataOut

router = APIRouter(prefix="/api/ml", tags=["ml"])

DISCLAIMER = (
    "This is a machine-learning ESTIMATE trained on Cap Ledger's own synthetic demo dataset (see "
    "docs/data_sources.md and docs/ml_documentation.md) — it re-derives the simple rules used to "
    "generate that demo data, and is not a claim about real-world NFL contract value. A prediction, "
    "not a fact; never treat it as one."
)


@router.get("/model-info", response_model=ModelMetadataOut)
def model_info(db: Session = Depends(get_db)):
    model = get_or_train_model(db)
    return ModelMetadataOut(**model.metadata.__dict__)


@router.get("/contract-value-projection", response_model=ContractValueProjectionOut)
def contract_value_projection(
    position: str,
    age: int = Query(..., ge=18, le=50),
    contract_length_years: int = Query(..., ge=1, le=7),
    db: Session = Depends(get_db),
):
    try:
        model = get_or_train_model(db)
        result = model.predict(position=position, age=age, contract_length_years=contract_length_years)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return ContractValueProjectionOut(
        position=position,
        age=age,
        contract_length_years=contract_length_years,
        predicted_aav=result.predicted_aav,
        baseline_aav=result.baseline_aav,
        drivers=result.drivers,
        model=ModelMetadataOut(**result.metadata.__dict__),
        disclaimer=DISCLAIMER,
    )
