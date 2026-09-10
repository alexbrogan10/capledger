from pydantic import BaseModel, ConfigDict, Field


class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    abbreviation: str
    conference: str
    division: str


class TeamCapOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    team_id: int
    season: int
    salary_cap: float
    cap_commitments: float
    top51_commitments: float
    dead_cap: float
    cap_space: float
    effective_cap_space: float

    definitions: dict[str, str] = {
        "salary_cap": "The league-wide salary-cap limit assumed for this season. Historical seasons "
        "use the actual reported league cap; future seasons are a labeled assumption "
        "(see /api/teams/{id}/cap and the growth-rate setting).",
        "cap_commitments": "Sum of cap hits for every player on the active roster ('full 53-man' "
        "accounting) for this season.",
        "top51_commitments": "Sum of only the 51 highest cap hits on the roster — the NFL's offseason "
        "accounting rule, used whenever a team's charged roster exceeds 51 players.",
        "dead_cap": "Cap charges from players no longer on the roster (released or traded) whose "
        "signing-bonus proration or guaranteed money still counts this season.",
        "cap_space": "salary_cap - top51_commitments - dead_cap. The commonly reported offseason "
        "'cap space' figure.",
        "effective_cap_space": "salary_cap - cap_commitments - dead_cap. Cap space once the full "
        "roster (not just top 51) counts against the cap.",
    }


class PositionSpendingOut(BaseModel):
    position_group: str
    cap_spending: float
    cap_percentage: float
    player_count: int


class FinancialAlert(BaseModel):
    severity: str  # info | watch | high
    category: str
    message: str
    player_id: int | None = None
    player_name: str | None = None
    season: int | None = None
    amount: float | None = None


class CapProjectionRequest(BaseModel):
    growth_rate: float = Field(0.06, description="Assumed year-over-year league cap growth rate.")
    seasons: list[int] | None = Field(
        None, description="Seasons to project; defaults to the standard projection window."
    )


class CapProjectionSeasonOut(BaseModel):
    season: int
    projected_cap: float
    projected_commitments: float
    projected_space: float


class CapProjectionOut(BaseModel):
    team_id: int
    base_season: int
    base_cap: float
    growth_rate: float
    run_id: str
    seasons: list[CapProjectionSeasonOut]
    assumptions: list[str]


class DeadCapPlayerRow(BaseModel):
    player_id: int
    player_name: str
    position: str
    season: int
    dead_cap_value: float
    contract_status: str


class DeadCapSeasonRow(BaseModel):
    season: int
    dead_cap: float


class DeadCapDashboardOut(BaseModel):
    team_id: int
    current_season: int
    total_dead_cap_current_season: float
    by_player: list[DeadCapPlayerRow]
    by_season: list[DeadCapSeasonRow]


class DashboardOut(BaseModel):
    team: TeamOut
    season: int
    current_cap: TeamCapOut
    future_cap: list[TeamCapOut]
    position_spending: list[PositionSpendingOut]
    alerts: list[FinancialAlert]
    top_commitments: list[dict]
