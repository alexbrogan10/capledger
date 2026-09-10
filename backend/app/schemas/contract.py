from pydantic import BaseModel, ConfigDict, Field


class ContractOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    player_id: int
    team_id: int
    contract_start: int
    contract_end: int
    total_value: float
    annual_value: float
    guaranteed_money: float
    signing_bonus: float
    current_salary: float
    current_cap_hit: float
    contract_status: str


class ContractListItem(BaseModel):
    id: int
    player_id: int
    player_name: str
    position: str
    team_id: int
    team_abbreviation: str
    contract_start: int
    contract_end: int
    years_remaining: int
    annual_value: float
    guaranteed_money: float
    current_cap_hit: float
    contract_status: str
    age: int


class ReleaseRequest(BaseModel):
    release_season: int = Field(..., description="The season the release would take effect.")
    june1: bool = Field(False, description="Model this as a post-June 1 designated release.")


class ReleaseImpactOut(BaseModel):
    player_id: int
    player_name: str
    contract_id: int
    release_season: int
    june1: bool

    before_cap_hit: float
    after_dead_cap_current_year: float
    after_dead_cap_next_year: float
    current_year_cap_savings: float
    total_dead_cap: float
    next_year_cap_hit_removed: float

    team_id: int
    team_cap_before: float | None
    team_cap_after: float | None

    assumptions: list[str]


class RestructureRequest(BaseModel):
    restructure_season: int
    amount_to_convert: float = Field(..., gt=0)


class RestructureImpactOut(BaseModel):
    player_id: int
    player_name: str
    contract_id: int
    season: int
    original_cap_hit: float
    new_cap_hit: float
    current_year_savings: float
    converted_amount: float
    future_cap_hit_increases: dict[int, float]
    assumptions: list[str]
