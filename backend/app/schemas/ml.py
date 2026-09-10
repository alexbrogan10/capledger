from pydantic import BaseModel


class ModelMetadataOut(BaseModel):
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
    positions_seen: list[str]


class ContractValueProjectionOut(BaseModel):
    position: str
    age: int
    contract_length_years: int
    predicted_aav: float
    baseline_aav: float
    drivers: list[str]
    model: ModelMetadataOut
    disclaimer: str


class ComparableContractOut(BaseModel):
    contract_id: int
    player_name: str
    position: str
    age: int
    aav: float
    years_remaining: int
    guaranteed_money: float
    similarity_score: float
    age_difference: int
    aav_difference: float


class ComparableContractsOut(BaseModel):
    query_position: str
    query_age: int
    query_aav: float
    results: list[ComparableContractOut]
    methodology: str
