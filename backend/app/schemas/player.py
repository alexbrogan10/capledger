from pydantic import BaseModel, ConfigDict


class PlayerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    position: str
    team_id: int | None
    age: int
    experience: int
    status: str


class PlayerListItem(PlayerOut):
    team_abbreviation: str | None = None
    current_cap_hit: float | None = None
    years_remaining: int | None = None
    contract_status: str | None = None


class ContractYearOut(BaseModel):
    season: int
    base_salary: float
    signing_bonus_proration: float
    roster_bonus: float
    incentives: float
    cap_hit: float
    cash_value: float
    dead_cap_value: float
    guaranteed_base_salary: float


class DecisionPoint(BaseModel):
    season: int
    kind: str  # expiration | large_cap_hit | potential_release | potential_extension_window
    label: str
    detail: str


class PlayerContractProfile(BaseModel):
    player: PlayerOut
    team_abbreviation: str | None
    contract_id: int
    contract_start: int
    contract_end: int
    total_value: float
    annual_value: float
    guaranteed_money: float
    signing_bonus: float
    contract_status: str
    financial_timeline: list[ContractYearOut]
    decision_points: list[DecisionPoint]
