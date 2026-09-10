from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.contract import Contract
from app.models.contract_year import ContractYear
from app.models.player import Player
from app.models.team import Team
from app.models.team_cap import TeamCap
from app.schemas.contract import (
    ContractListItem,
    ContractOut,
    ReleaseImpactOut,
    ReleaseRequest,
    RestructureImpactOut,
    RestructureRequest,
)
from app.seed.demo_data import CURRENT_SEASON
from app.services.cap_engine import ContractYearInput, calculate_dead_cap, calculate_restructure

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


@router.get("", response_model=list[ContractListItem])
def search_contracts(
    team_id: int | None = None,
    position: str | None = None,
    search: str | None = None,
    min_aav: float | None = None,
    max_aav: float | None = None,
    min_guaranteed: float | None = None,
    contract_status: str | None = None,
    season: int = Query(CURRENT_SEASON),
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = (
        db.query(Contract, Player, Team)
        .join(Player, Player.id == Contract.player_id)
        .join(Team, Team.id == Contract.team_id)
    )
    if team_id is not None:
        query = query.filter(Contract.team_id == team_id)
    if position is not None:
        query = query.filter(Player.position == position)
    if search:
        query = query.filter(Player.name.ilike(f"%{search}%"))
    if min_aav is not None:
        query = query.filter(Contract.annual_value >= min_aav)
    if max_aav is not None:
        query = query.filter(Contract.annual_value <= max_aav)
    if min_guaranteed is not None:
        query = query.filter(Contract.guaranteed_money >= min_guaranteed)
    if contract_status is not None:
        query = query.filter(Contract.contract_status == contract_status)

    rows = query.order_by(Contract.annual_value.desc()).offset(offset).limit(limit).all()

    out = []
    for contract, player, team in rows:
        cy = (
            db.query(ContractYear)
            .filter(ContractYear.contract_id == contract.id, ContractYear.season == season)
            .one_or_none()
        )
        out.append(
            ContractListItem(
                id=contract.id,
                player_id=player.id,
                player_name=player.name,
                position=player.position,
                team_id=team.id,
                team_abbreviation=team.abbreviation,
                contract_start=contract.contract_start,
                contract_end=contract.contract_end,
                years_remaining=max(0, contract.contract_end - season + 1),
                annual_value=float(contract.annual_value),
                guaranteed_money=float(contract.guaranteed_money),
                current_cap_hit=float(cy.cap_hit) if cy else 0.0,
                contract_status=contract.contract_status,
                age=player.age,
            )
        )
    return out


@router.get("/{contract_id}", response_model=ContractOut)
def get_contract(contract_id: int, db: Session = Depends(get_db)):
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    return ContractOut.model_validate(contract)


def _year_inputs(db: Session, contract_id: int) -> list[ContractYearInput]:
    years = (
        db.query(ContractYear)
        .filter(ContractYear.contract_id == contract_id)
        .order_by(ContractYear.season)
        .all()
    )
    return [
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


@router.post("/{contract_id}/release", response_model=ReleaseImpactOut)
def simulate_release(contract_id: int, body: ReleaseRequest, db: Session = Depends(get_db)):
    """Model-only scenario: computes the cap consequence of releasing this
    player. Does NOT mutate any stored contract or roster data — Cap
    Ledger's release calculator is a decision-support simulator, not a
    transaction system."""
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    player = db.get(Player, contract.player_id)

    years = _year_inputs(db, contract_id)
    result = calculate_dead_cap(years, release_season=body.release_season, june1=body.june1)

    team_cap_before = (
        db.query(TeamCap)
        .filter(TeamCap.team_id == contract.team_id, TeamCap.season == body.release_season)
        .one_or_none()
    )
    team_cap_after = None
    if team_cap_before is not None:
        # Available cap space after: remove this player's cap hit, add the dead cap charge instead.
        team_cap_after = round(
            float(team_cap_before.cap_space) + result.current_year_cap_savings, 2
        )

    return ReleaseImpactOut(
        player_id=player.id,
        player_name=player.name,
        contract_id=contract.id,
        release_season=body.release_season,
        june1=body.june1,
        before_cap_hit=result.pre_release_cap_hit,
        after_dead_cap_current_year=result.current_year_dead_cap,
        after_dead_cap_next_year=result.next_year_dead_cap,
        current_year_cap_savings=result.current_year_cap_savings,
        total_dead_cap=result.total_dead_cap,
        next_year_cap_hit_removed=result.next_year_cap_hit_removed,
        team_id=contract.team_id,
        team_cap_before=float(team_cap_before.cap_space) if team_cap_before else None,
        team_cap_after=team_cap_after,
        assumptions=[
            "Standard release accelerates all remaining signing-bonus proration into the release "
            "season; a post-June 1 designation splits it between the release season and the next.",
            "Only signing-bonus proration and season-specific guaranteed base salary are modeled as "
            "dead cap; incentive and offset provisions are not modeled in this version.",
            "This is a hypothetical scenario. No contract or roster data is changed by this endpoint.",
        ],
    )


@router.post("/{contract_id}/restructure", response_model=RestructureImpactOut)
def simulate_restructure(contract_id: int, body: RestructureRequest, db: Session = Depends(get_db)):
    """Model-only scenario: simulates converting base salary into
    signing-bonus-style proration. Does NOT mutate stored data."""
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    player = db.get(Player, contract.player_id)

    years = _year_inputs(db, contract_id)
    try:
        result = calculate_restructure(
            years, restructure_season=body.restructure_season, amount_to_convert=body.amount_to_convert
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RestructureImpactOut(
        player_id=player.id,
        player_name=player.name,
        contract_id=contract.id,
        season=result.season,
        original_cap_hit=result.original_cap_hit,
        new_cap_hit=result.new_cap_hit,
        current_year_savings=result.current_year_savings,
        converted_amount=result.converted_amount,
        future_cap_hit_increases=result.future_cap_hit_increases,
        assumptions=[
            "Restructuring moves cap obligations into future seasons; it never reduces total money "
            "owed, only when it is recognized against the cap.",
            "Converted salary is assumed to prorate evenly over the remaining contract years, capped "
            "at 5 league years, matching signing-bonus proration rules.",
            "This is a hypothetical scenario. No contract or roster data is changed by this endpoint.",
        ],
    )
