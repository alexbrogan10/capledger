from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.contract import Contract
from app.models.contract_year import ContractYear
from app.models.player import POSITION_GROUPS, Player
from app.models.team import Team
from app.models.team_cap import TeamCap
from app.schemas.analytics import (
    ConcentrationOut,
    ContractRiskOut,
    ContractValueOut,
    FinancialFlexibilityOut,
    FlexibilityFactorOut,
    PositionSpendingComparisonOut,
    PositionSpendingComparisonRow,
    RiskFactorOut,
)
from app.seed.demo_data import CURRENT_SEASON, DEMO_LEAGUE_CAP
from app.services.financial_intelligence import (
    calculate_contract_risk,
    calculate_financial_concentration,
    calculate_financial_flexibility,
    calculate_market_comparison,
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def _active_cap_hits(db: Session, team_id: int, season: int) -> list[float]:
    return [
        float(cy.cap_hit)
        for cy in (
            db.query(ContractYear)
            .join(Contract)
            .filter(Contract.team_id == team_id, Contract.contract_status == "active", ContractYear.season == season)
        )
    ]


@router.get("/financial-flexibility", response_model=FinancialFlexibilityOut)
def financial_flexibility(
    team_id: int,
    season: int = Query(CURRENT_SEASON),
    w_cap_space: float | None = Query(None),
    w_dead_cap: float | None = Query(None),
    w_future_guaranteed: float | None = Query(None),
    w_expiring_contracts: float | None = Query(None),
    w_concentration: float | None = Query(None),
    db: Session = Depends(get_db),
):
    """Financial Flexibility Score (0-100) — deliberately distinct from cap
    space. Weighting is configurable via query params (``w_cap_space``,
    ``w_dead_cap``, ``w_future_guaranteed``, ``w_expiring_contracts``,
    ``w_concentration``); any omitted weight falls back to the documented
    default (see docs/financial_flexibility.md).
    """
    team_cap = db.query(TeamCap).filter(TeamCap.team_id == team_id, TeamCap.season == season).one_or_none()
    if team_cap is None:
        raise HTTPException(status_code=404, detail=f"No cap data for team {team_id}, season {season}")

    salary_cap = float(team_cap.salary_cap)
    cap_space_pct = float(team_cap.cap_space) / salary_cap if salary_cap else 0.0
    dead_cap_pct = float(team_cap.dead_cap) / salary_cap if salary_cap else 0.0

    future_guaranteed = (
        db.query(ContractYear)
        .join(Contract)
        .filter(Contract.team_id == team_id, Contract.contract_status == "active", ContractYear.season > season)
        .with_entities(ContractYear.guaranteed_base_salary)
        .all()
    )
    future_guaranteed_total = float(sum(v for (v,) in future_guaranteed))
    future_guaranteed_pct = future_guaranteed_total / salary_cap if salary_cap else 0.0

    expiring_rows = (
        db.query(ContractYear)
        .join(Contract)
        .filter(
            Contract.team_id == team_id, Contract.contract_status == "active",
            Contract.contract_end == season, ContractYear.season == season,
        )
        .with_entities(ContractYear.cap_hit)
        .all()
    )
    expiring_total = float(sum(v for (v,) in expiring_rows))
    full_roster_commitments = float(team_cap.cap_commitments)
    expiring_pct = expiring_total / full_roster_commitments if full_roster_commitments else 0.0

    active_hits = _active_cap_hits(db, team_id, season)
    concentration = calculate_financial_concentration(active_hits)
    top5_concentration_pct = concentration.top5_pct / 100

    weights: dict[str, float] = {}
    if w_cap_space is not None:
        weights["cap_space"] = w_cap_space
    if w_dead_cap is not None:
        weights["dead_cap"] = w_dead_cap
    if w_future_guaranteed is not None:
        weights["future_guaranteed"] = w_future_guaranteed
    if w_expiring_contracts is not None:
        weights["expiring_contracts"] = w_expiring_contracts
    if w_concentration is not None:
        weights["concentration"] = w_concentration

    try:
        result = calculate_financial_flexibility(
            cap_space_pct=cap_space_pct, dead_cap_pct=dead_cap_pct,
            future_guaranteed_pct=future_guaranteed_pct, expiring_pct=expiring_pct,
            top5_concentration_pct=top5_concentration_pct, weights=weights or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    weights_used = {f.key: f.weight for f in result.factors}

    return FinancialFlexibilityOut(
        team_id=team_id,
        season=season,
        score=result.score,
        factors=[FlexibilityFactorOut(**f.__dict__) for f in result.factors],
        weights_used=weights_used,
        disclaimer=(
            "Financial Flexibility is a transparent, weighted combination of cap-structure factors — "
            "not the same thing as cap space, and not aware of roster needs, player performance, or "
            "competitive timeline. Adjust the weights to reflect your own priorities."
        ),
    )


@router.get("/concentration", response_model=ConcentrationOut)
def concentration(team_id: int, season: int = Query(CURRENT_SEASON), db: Session = Depends(get_db)):
    """What share of a team's cap sits in its largest few contracts."""
    active_hits = _active_cap_hits(db, team_id, season)
    if not active_hits:
        raise HTTPException(status_code=404, detail=f"No active contracts for team {team_id}, season {season}")
    result = calculate_financial_concentration(active_hits)

    if result.top5_pct >= 55:
        interpretation = (
            "High concentration: over half the cap rides on five contracts. This can mean less "
            "flexibility and more dependence on those players staying productive and healthy."
        )
    elif result.top5_pct >= 35:
        interpretation = "Moderate concentration — a common range for teams built around a few core players."
    else:
        interpretation = "Low concentration: spending is spread broadly across the roster."

    return ConcentrationOut(
        team_id=team_id, season=season,
        total_commitments=result.total_commitments,
        top1_pct=result.top1_pct, top3_pct=result.top3_pct, top5_pct=result.top5_pct, top10_pct=result.top10_pct,
        top1_dollars=result.top1_dollars, top3_dollars=result.top3_dollars,
        top5_dollars=result.top5_dollars, top10_dollars=result.top10_dollars,
        interpretation=interpretation + " High concentration is not automatically bad, nor is low "
        "concentration automatically good — it depends on team-building strategy and timeline.",
    )


@router.get("/contract-risk", response_model=ContractRiskOut)
def contract_risk(contract_id: int, season: int = Query(CURRENT_SEASON), db: Session = Depends(get_db)):
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    player = db.get(Player, contract.player_id)

    years_remaining = max(0, contract.contract_end - season + 1)
    guaranteed_pct = float(contract.guaranteed_money) / float(contract.total_value) if float(contract.total_value) else 0.0

    future_hits = (
        db.query(ContractYear)
        .filter(ContractYear.contract_id == contract_id, ContractYear.season > season)
        .with_entities(ContractYear.cap_hit)
        .all()
    )
    assumed_cap = DEMO_LEAGUE_CAP.get(season, 270_000_000.0)
    max_future_hit = max((float(v) for (v,) in future_hits), default=0.0)
    future_cap_hit_pct = max_future_hit / assumed_cap if assumed_cap else 0.0

    result = calculate_contract_risk(
        age=player.age, position=player.position, years_remaining=years_remaining,
        guaranteed_pct_of_total=guaranteed_pct, future_cap_hit_pct_of_cap=future_cap_hit_pct,
    )

    return ContractRiskOut(
        contract_id=contract.id, player_id=player.id, player_name=player.name,
        risk_score=result.risk_score, category=result.category,
        factors=[RiskFactorOut(**f.__dict__) for f in result.factors],
        disclaimer=(
            "Model identifies increased or decreased FINANCIAL risk from contract structure — this is "
            "not a prediction that any player will decline or underperform."
        ),
    )


@router.get("/contract-value", response_model=ContractValueOut)
def contract_value(contract_id: int, db: Session = Depends(get_db)):
    """Model-estimated contract-value comparison — how this contract's AAV
    compares to other active contracts at the same position (and a similar
    age) in Cap Ledger's own dataset. This is an internal market comparison,
    not a claim about real-world market value or player performance."""
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    player = db.get(Player, contract.player_id)

    league_rows = (
        db.query(Player.position, Player.age, Contract.annual_value)
        .join(Contract, Contract.player_id == Player.id)
        .filter(Contract.contract_status == "active")
        .all()
    )
    league_contracts = [{"position": p, "age": a, "aav": float(v)} for p, a, v in league_rows]

    try:
        result = calculate_market_comparison(
            aav=float(contract.annual_value), position=player.position, age=player.age,
            league_contracts=league_contracts,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if result.cost_vs_position_median > 0.15 * result.position_median_aav:
        label = "Potential cost discrepancy: paid well above the position median in this dataset."
    elif result.cost_vs_position_median < -0.15 * result.position_median_aav:
        label = "Potential value discrepancy: paid well below the position median in this dataset."
    else:
        label = "Close to the position median in this dataset."

    return ContractValueOut(
        contract_id=contract.id, player_id=player.id, player_name=player.name,
        position=result.position, age=player.age, aav=result.aav,
        position_median_aav=result.position_median_aav, percentile=result.percentile,
        age_band_median_aav=result.age_band_median_aav, age_band_percentile=result.age_band_percentile,
        sample_size=result.sample_size, cost_vs_position_median=result.cost_vs_position_median,
        discrepancy_label=label,
        disclaimer=(
            "This compares AAV against other contracts at the same position in Cap Ledger's own "
            "(synthetic, demo) dataset only — it does not use player performance or production data, "
            "and is not a claim about real-world market value. See docs/data_sources.md."
        ),
    )


@router.get("/position-spending-comparison", response_model=PositionSpendingComparisonOut)
def position_spending_comparison(team_id: int, season: int = Query(CURRENT_SEASON), db: Session = Depends(get_db)):
    """A team's position-group cap spending vs. the league average for that
    season — answers "how does our WR spending compare to the rest of the
    league," not just "how much do we spend on WRs.\""""
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")

    all_rows = (
        db.query(Player.position, Player.team_id, ContractYear.cap_hit)
        .join(Contract, Contract.player_id == Player.id)
        .join(ContractYear, ContractYear.contract_id == Contract.id)
        .filter(Contract.contract_status == "active", ContractYear.season == season)
        .all()
    )

    team_totals: dict[str, float] = {}
    league_totals_by_team: dict[int, dict[str, float]] = {}
    team_cap_totals: dict[int, float] = {}

    for position, t_id, cap_hit in all_rows:
        group = POSITION_GROUPS.get(position, "OTHER")
        cap_hit = float(cap_hit)
        team_cap_totals[t_id] = team_cap_totals.get(t_id, 0.0) + cap_hit
        league_totals_by_team.setdefault(t_id, {})
        league_totals_by_team[t_id][group] = league_totals_by_team[t_id].get(group, 0.0) + cap_hit
        if t_id == team_id:
            team_totals[group] = team_totals.get(group, 0.0) + cap_hit

    team_cap_row = db.query(TeamCap).filter(TeamCap.team_id == team_id, TeamCap.season == season).one_or_none()
    team_total_cap = float(team_cap_row.cap_commitments) if team_cap_row else team_cap_totals.get(team_id, 0.0)

    all_groups = sorted({g for totals in league_totals_by_team.values() for g in totals})
    rows: list[PositionSpendingComparisonRow] = []
    n_teams = len(league_totals_by_team) or 1
    for group in all_groups:
        team_spending = team_totals.get(group, 0.0)
        team_pct = round(team_spending / team_total_cap * 100, 2) if team_total_cap else 0.0

        league_pcts = []
        for t_id, totals in league_totals_by_team.items():
            t_cap = team_cap_totals.get(t_id, 0.0)
            if t_cap:
                league_pcts.append(totals.get(group, 0.0) / t_cap * 100)
        league_avg_pct = round(sum(league_pcts) / len(league_pcts), 2) if league_pcts else 0.0

        rows.append(
            PositionSpendingComparisonRow(
                position_group=group,
                team_cap_spending=round(team_spending, 2),
                team_cap_percentage=team_pct,
                league_avg_cap_percentage=league_avg_pct,
                difference=round(team_pct - league_avg_pct, 2),
            )
        )

    return PositionSpendingComparisonOut(
        team_id=team_id, season=season, rows=sorted(rows, key=lambda r: r.team_cap_spending, reverse=True)
    )
