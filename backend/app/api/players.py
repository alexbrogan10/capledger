from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.contract import Contract
from app.models.contract_year import ContractYear
from app.models.player import Player
from app.models.team import Team
from app.schemas.player import (
    ContractYearOut,
    DecisionPoint,
    PlayerContractProfile,
    PlayerListItem,
    PlayerOut,
)
from app.seed.demo_data import CURRENT_SEASON
from app.services.cap_engine import ContractYearInput
from app.services.decision_points import identify_decision_points

router = APIRouter(prefix="/api/players", tags=["players"])


@router.get("", response_model=list[PlayerListItem])
def list_players(
    team_id: int | None = None,
    position: str | None = None,
    search: str | None = None,
    season: int = Query(CURRENT_SEASON),
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Player, Team.abbreviation, Contract, ContractYear).join(
        Team, Team.id == Player.team_id, isouter=True
    ).join(Contract, Contract.player_id == Player.id, isouter=True).join(
        ContractYear,
        (ContractYear.contract_id == Contract.id) & (ContractYear.season == season),
        isouter=True,
    )

    if team_id is not None:
        query = query.filter(Player.team_id == team_id)
    if position is not None:
        query = query.filter(Player.position == position)
    if search:
        query = query.filter(Player.name.ilike(f"%{search}%"))

    rows = query.order_by(Player.name).offset(offset).limit(limit).all()

    out = []
    for player, team_abbr, contract, cy in rows:
        out.append(
            PlayerListItem(
                id=player.id,
                name=player.name,
                position=player.position,
                team_id=player.team_id,
                age=player.age,
                experience=player.experience,
                status=player.status,
                team_abbreviation=team_abbr,
                current_cap_hit=float(cy.cap_hit) if cy else None,
                years_remaining=(contract.contract_end - season + 1) if contract else None,
                contract_status=contract.contract_status if contract else None,
            )
        )
    return out


@router.get("/{player_id}", response_model=PlayerContractProfile)
def get_player_profile(player_id: int, db: Session = Depends(get_db)):
    player = db.get(Player, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player not found")

    contract = (
        db.query(Contract)
        .filter(Contract.player_id == player_id)
        .order_by(Contract.contract_start.desc())
        .first()
    )
    if contract is None:
        raise HTTPException(status_code=404, detail="Player has no contract on file")

    team = db.get(Team, contract.team_id)
    years = (
        db.query(ContractYear)
        .filter(ContractYear.contract_id == contract.id)
        .order_by(ContractYear.season)
        .all()
    )

    timeline = [
        ContractYearOut(
            season=y.season,
            base_salary=float(y.base_salary),
            signing_bonus_proration=float(y.signing_bonus_proration),
            roster_bonus=float(y.roster_bonus),
            incentives=float(y.incentives),
            cap_hit=float(y.cap_hit),
            cash_value=float(y.cash_value),
            dead_cap_value=float(y.dead_cap_value),
            guaranteed_base_salary=float(y.guaranteed_base_salary),
        )
        for y in years
    ]

    year_inputs = [
        ContractYearInput(
            season=y.season,
            base_salary=float(y.base_salary),
            signing_bonus_proration=float(y.signing_bonus_proration),
            roster_bonus=float(y.roster_bonus),
            incentives=float(y.incentives),
            guaranteed_base_salary=float(y.guaranteed_base_salary),
        )
        for y in years
    ]
    raw_points = identify_decision_points(contract.contract_start, contract.contract_end, year_inputs)
    decision_points = [DecisionPoint(**p) for p in raw_points]

    return PlayerContractProfile(
        player=PlayerOut.model_validate(player),
        team_abbreviation=team.abbreviation if team else None,
        contract_id=contract.id,
        contract_start=contract.contract_start,
        contract_end=contract.contract_end,
        total_value=float(contract.total_value),
        annual_value=float(contract.annual_value),
        guaranteed_money=float(contract.guaranteed_money),
        signing_bonus=float(contract.signing_bonus),
        contract_status=contract.contract_status,
        financial_timeline=timeline,
        decision_points=decision_points,
    )
