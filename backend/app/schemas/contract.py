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
    scenario_id: int | None = None


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
    scenario_id: int | None = None


class TradeRequest(BaseModel):
    trade_season: int = Field(..., description="The season the trade would take effect.")


class TradeImpactOut(BaseModel):
    player_id: int
    player_name: str
    contract_id: int
    trade_season: int

    trading_team_id: int
    trading_team_pre_trade_cap_hit: float
    trading_team_dead_cap: float
    trading_team_cap_savings: float

    acquiring_team_cap_hits: dict[int, float]
    acquiring_team_total_remaining_commitment: float

    assumptions: list[str]
    scenario_id: int | None = None


class ExtensionRequest(BaseModel):
    extension_start_season: int = Field(..., description="First season of the new contract terms.")
    new_length_years: int = Field(..., gt=0)
    new_total_value: float = Field(..., gt=0)
    new_signing_bonus: float = Field(..., ge=0)
    new_guaranteed_money: float = Field(..., ge=0)


class ExtensionYearOut(BaseModel):
    season: int
    base_salary: float
    signing_bonus_proration: float
    cap_hit: float
    guaranteed_base_salary: float


class ExtensionImpactOut(BaseModel):
    player_id: int
    player_name: str
    contract_id: int
    extension_start_season: int

    current_contract_years: list[ExtensionYearOut]
    new_contract_years: list[ExtensionYearOut]
    combined_years: list[ExtensionYearOut]

    total_new_commitment: float
    total_new_guaranteed: float
    first_year_cap_hit_change: float

    assumptions: list[str]
    scenario_id: int | None = None


class ScenarioOption(BaseModel):
    scenario_type: str  # keep | restructure | release | trade
    label: str
    current_year_cap_impact: float
    """Positive = cap savings this season vs. keeping the player as-is."""
    future_year_impact: str
    dead_cap: float
    assessment: str  # Strong | Favorable | Moderate | Unfavorable | Conditional
    reasoning: list[str]


class ScenarioComparisonOut(BaseModel):
    player_id: int
    player_name: str
    contract_id: int
    season: int
    options: list[ScenarioOption]
    disclaimer: str
