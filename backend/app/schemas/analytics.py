from pydantic import BaseModel


class FlexibilityFactorOut(BaseModel):
    key: str
    label: str
    score: float
    weight: float
    direction: str
    detail: str


class FinancialFlexibilityOut(BaseModel):
    team_id: int
    season: int
    score: float
    factors: list[FlexibilityFactorOut]
    weights_used: dict[str, float]
    disclaimer: str


class ConcentrationOut(BaseModel):
    team_id: int
    season: int
    total_commitments: float
    top1_pct: float
    top3_pct: float
    top5_pct: float
    top10_pct: float
    top1_dollars: float
    top3_dollars: float
    top5_dollars: float
    top10_dollars: float
    interpretation: str


class RiskFactorOut(BaseModel):
    label: str
    contributes_risk: bool
    detail: str


class ContractRiskOut(BaseModel):
    contract_id: int
    player_id: int
    player_name: str
    risk_score: float
    category: str
    factors: list[RiskFactorOut]
    disclaimer: str


class ContractValueOut(BaseModel):
    contract_id: int
    player_id: int
    player_name: str
    position: str
    age: int
    aav: float
    position_median_aav: float
    percentile: float
    age_band_median_aav: float
    age_band_percentile: float
    sample_size: int
    cost_vs_position_median: float
    discrepancy_label: str
    disclaimer: str


class PositionSpendingComparisonRow(BaseModel):
    position_group: str
    team_cap_spending: float
    team_cap_percentage: float
    league_avg_cap_percentage: float
    difference: float


class PositionSpendingComparisonOut(BaseModel):
    team_id: int
    season: int
    rows: list[PositionSpendingComparisonRow]
