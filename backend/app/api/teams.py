import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.cap_projection import CapProjection
from app.models.contract import Contract
from app.models.contract_year import ContractYear
from app.models.player import POSITION_GROUPS, Player
from app.models.team import Team
from app.models.team_cap import TeamCap
from app.schemas.team import (
    CapProjectionOut,
    CapProjectionRequest,
    CapProjectionSeasonOut,
    DashboardOut,
    DeadCapDashboardOut,
    DeadCapPlayerRow,
    DeadCapSeasonRow,
    FinancialAlert,
    PositionSpendingOut,
    TeamCapOut,
    TeamOut,
)
from app.seed.demo_data import CURRENT_SEASON, DEMO_LEAGUE_CAP, PROJECTION_SEASONS
from app.services.cap_engine import ContractYearInput, calculate_dead_cap, summarize_team_cap

router = APIRouter(prefix="/api/teams", tags=["teams"])


def _get_team_or_404(db: Session, team_id: int) -> Team:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.get("", response_model=list[TeamOut])
def list_teams(db: Session = Depends(get_db)):
    return db.query(Team).order_by(Team.conference, Team.division, Team.name).all()


@router.get("/{team_id}", response_model=TeamOut)
def get_team(team_id: int, db: Session = Depends(get_db)):
    return _get_team_or_404(db, team_id)


def _team_cap_row(db: Session, team_id: int, season: int) -> TeamCap | None:
    return (
        db.query(TeamCap)
        .filter(TeamCap.team_id == team_id, TeamCap.season == season)
        .one_or_none()
    )


@router.get("/{team_id}/cap", response_model=TeamCapOut)
def get_team_cap(team_id: int, season: int = Query(CURRENT_SEASON), db: Session = Depends(get_db)):
    _get_team_or_404(db, team_id)
    row = _team_cap_row(db, team_id, season)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No cap data for season {season}")
    return TeamCapOut.model_validate(row)


@router.get("/{team_id}/roster")
def get_team_roster(team_id: int, season: int = Query(CURRENT_SEASON), db: Session = Depends(get_db)):
    _get_team_or_404(db, team_id)
    team_cap = _team_cap_row(db, team_id, season)
    salary_cap = team_cap.salary_cap if team_cap else None

    rows = (
        db.query(Player, Contract, ContractYear)
        .join(Contract, Contract.player_id == Player.id)
        .join(ContractYear, ContractYear.contract_id == Contract.id)
        .filter(Player.team_id == team_id, ContractYear.season == season)
        .order_by(ContractYear.cap_hit.desc())
        .all()
    )

    out = []
    for player, contract, cy in rows:
        all_years = (
            db.query(ContractYear)
            .filter(ContractYear.contract_id == contract.id)
            .order_by(ContractYear.season)
            .all()
        )
        year_inputs = [
            ContractYearInput(
                season=y.season,
                base_salary=float(y.base_salary),
                signing_bonus_proration=float(y.signing_bonus_proration),
                roster_bonus=float(y.roster_bonus),
                incentives=float(y.incentives),
                guaranteed_base_salary=float(y.guaranteed_base_salary),
            )
            for y in all_years
        ]
        dead_cap_if_released = None
        if contract.contract_status == "active":
            dead_cap_if_released = calculate_dead_cap(
                year_inputs, release_season=season, june1=False
            ).total_dead_cap

        out.append(
            {
                "player_id": player.id,
                "player_name": player.name,
                "position": player.position,
                "age": player.age,
                "contract_status": contract.contract_status,
                "contract_years_remaining": max(0, contract.contract_end - season + 1),
                "annual_value": float(contract.annual_value),
                "current_salary": float(cy.base_salary),
                "current_cap_hit": float(cy.cap_hit),
                "guaranteed_money": float(contract.guaranteed_money),
                "dead_cap_if_released": dead_cap_if_released,
                "cash_this_year": float(cy.cash_value),
                "pct_of_team_cap": (
                    round(float(cy.cap_hit) / float(salary_cap) * 100, 2) if salary_cap else None
                ),
            }
        )
    return out


@router.get("/{team_id}/spending", response_model=list[PositionSpendingOut])
def get_position_spending(team_id: int, season: int = Query(CURRENT_SEASON), db: Session = Depends(get_db)):
    _get_team_or_404(db, team_id)
    team_cap = _team_cap_row(db, team_id, season)
    salary_cap = float(team_cap.salary_cap) if team_cap else None

    rows = (
        db.query(Player.position, func.sum(ContractYear.cap_hit), func.count(Player.id))
        .join(Contract, Contract.player_id == Player.id)
        .join(ContractYear, ContractYear.contract_id == Contract.id)
        .filter(Player.team_id == team_id, ContractYear.season == season, Contract.contract_status == "active")
        .group_by(Player.position)
        .all()
    )

    grouped: dict[str, dict] = {}
    for position, cap_sum, count in rows:
        group = POSITION_GROUPS.get(position, "OTHER")
        entry = grouped.setdefault(group, {"cap_spending": 0.0, "player_count": 0})
        entry["cap_spending"] += float(cap_sum)
        entry["player_count"] += count

    out = [
        PositionSpendingOut(
            position_group=group,
            cap_spending=round(data["cap_spending"], 2),
            cap_percentage=(round(data["cap_spending"] / salary_cap * 100, 2) if salary_cap else 0.0),
            player_count=data["player_count"],
        )
        for group, data in grouped.items()
    ]
    return sorted(out, key=lambda x: x.cap_spending, reverse=True)


@router.get("/{team_id}/dashboard", response_model=DashboardOut)
def get_dashboard(team_id: int, season: int = Query(CURRENT_SEASON), db: Session = Depends(get_db)):
    team = _get_team_or_404(db, team_id)
    current_cap_row = _team_cap_row(db, team_id, season)
    if current_cap_row is None:
        raise HTTPException(status_code=404, detail=f"No cap data for season {season}")

    future_rows = (
        db.query(TeamCap)
        .filter(TeamCap.team_id == team_id, TeamCap.season > season, TeamCap.season.in_(PROJECTION_SEASONS))
        .order_by(TeamCap.season)
        .all()
    )

    spending = get_position_spending(team_id, season, db)

    top_commitments_rows = (
        db.query(Player.name, Player.position, ContractYear.cap_hit)
        .join(Contract, Contract.player_id == Player.id)
        .join(ContractYear, ContractYear.contract_id == Contract.id)
        .filter(Player.team_id == team_id, ContractYear.season == season, Contract.contract_status == "active")
        .order_by(ContractYear.cap_hit.desc())
        .limit(5)
        .all()
    )
    top_commitments = [
        {"player_name": name, "position": position, "cap_hit": float(cap_hit)}
        for name, position, cap_hit in top_commitments_rows
    ]

    alerts: list[FinancialAlert] = []
    if current_cap_row.cap_space < 0:
        alerts.append(
            FinancialAlert(
                severity="high",
                category="cap_compliance",
                message=f"Team is currently over the assumed cap by ${abs(current_cap_row.cap_space):,.0f} "
                "on a top-51 basis; moves will be required before the season.",
                season=season,
                amount=float(current_cap_row.cap_space),
            )
        )
    elif current_cap_row.cap_space < 5_000_000:
        alerts.append(
            FinancialAlert(
                severity="watch",
                category="cap_compliance",
                message=f"Available cap space (${current_cap_row.cap_space:,.0f}) is thin for {season}.",
                season=season,
                amount=float(current_cap_row.cap_space),
            )
        )
    if current_cap_row.dead_cap > 15_000_000:
        alerts.append(
            FinancialAlert(
                severity="watch",
                category="dead_cap",
                message=f"Dead-cap exposure of ${current_cap_row.dead_cap:,.0f} in {season} is significant.",
                season=season,
                amount=float(current_cap_row.dead_cap),
            )
        )
    for row in top_commitments:
        if row["cap_hit"] > 0.15 * float(current_cap_row.salary_cap):
            alerts.append(
                FinancialAlert(
                    severity="info",
                    category="large_cap_hit",
                    message=f"{row['player_name']} ({row['position']}) carries a cap hit of "
                    f"${row['cap_hit']:,.0f}, over 15% of the assumed cap.",
                    player_name=row["player_name"],
                    season=season,
                    amount=row["cap_hit"],
                )
            )

    return DashboardOut(
        team=TeamOut.model_validate(team),
        season=season,
        current_cap=TeamCapOut.model_validate(current_cap_row),
        future_cap=[TeamCapOut.model_validate(r) for r in future_rows],
        position_spending=spending,
        alerts=alerts,
        top_commitments=top_commitments,
    )


@router.post("/{team_id}/projections", response_model=CapProjectionOut)
def recompute_projections(team_id: int, body: CapProjectionRequest, db: Session = Depends(get_db)):
    """Multi-year cap projection under a user-adjustable league-cap growth
    assumption (project brief section 11). Only currently-signed contracts
    are counted — see docs/data_sources.md for why future-season
    commitments trend down as contracts expire. Every figure returned here
    is clearly a projection, not a guarantee; each run is persisted to
    ``cap_projections`` for later audit.
    """
    _get_team_or_404(db, team_id)

    base_row = _team_cap_row(db, team_id, CURRENT_SEASON)
    base_cap = float(base_row.salary_cap) if base_row else DEMO_LEAGUE_CAP.get(CURRENT_SEASON, 270_000_000.0)

    seasons = body.seasons or [s for s in PROJECTION_SEASONS if s >= CURRENT_SEASON]
    run_id = uuid.uuid4().hex[:12]

    out_seasons: list[CapProjectionSeasonOut] = []
    for season in sorted(set(seasons)):
        years_from_base = season - CURRENT_SEASON
        projected_cap = round(base_cap * ((1 + body.growth_rate) ** years_from_base), 2)

        active_hits = [
            float(cy.cap_hit)
            for cy in (
                db.query(ContractYear)
                .join(Contract)
                .filter(
                    Contract.team_id == team_id,
                    Contract.contract_status == "active",
                    ContractYear.season == season,
                )
            )
        ]
        dead_cap_rows = (
            db.query(ContractYear)
            .join(Contract)
            .filter(Contract.team_id == team_id, ContractYear.season == season)
            .with_entities(ContractYear.dead_cap_value)
            .all()
        )
        dead_cap_total = round(float(sum(v for (v,) in dead_cap_rows)), 2)

        summary = summarize_team_cap(
            season=season, salary_cap=projected_cap, active_cap_hits=active_hits, dead_cap=dead_cap_total
        )

        db.add(
            CapProjection(
                team_id=team_id,
                season=season,
                run_id=run_id,
                projected_cap=summary.salary_cap,
                projected_commitments=summary.full_roster_commitments,
                projected_space=summary.available_cap_space,
                assumptions={"growth_rate": body.growth_rate, "base_season": CURRENT_SEASON, "base_cap": base_cap},
            )
        )
        out_seasons.append(
            CapProjectionSeasonOut(
                season=season,
                projected_cap=summary.salary_cap,
                projected_commitments=summary.full_roster_commitments,
                projected_space=summary.available_cap_space,
            )
        )
    db.commit()

    return CapProjectionOut(
        team_id=team_id,
        base_season=CURRENT_SEASON,
        base_cap=round(base_cap, 2),
        growth_rate=body.growth_rate,
        run_id=run_id,
        seasons=out_seasons,
        assumptions=[
            f"League cap growth of {body.growth_rate * 100:.1f}%/year is a user-supplied assumption, "
            "not an official NFL projection.",
            "Only contracts already on the books are counted — real teams continuously sign new "
            "players, so this understates real future commitments (see docs/data_sources.md).",
            "This is a projection, not a guarantee. Re-run with a different growth rate to see how "
            "sensitive the outlook is to that assumption.",
        ],
    )


@router.get("/{team_id}/dead-cap", response_model=DeadCapDashboardOut)
def dead_cap_dashboard(team_id: int, season: int = Query(CURRENT_SEASON), db: Session = Depends(get_db)):
    """Dead-money dashboard: current-season dead cap by player, plus a
    multi-season timeline of total dead cap already on the books from
    released/traded contracts."""
    _get_team_or_404(db, team_id)

    player_rows = (
        db.query(Player.id, Player.name, Player.position, ContractYear.season, ContractYear.dead_cap_value, Contract.contract_status)
        .join(Contract, Contract.player_id == Player.id)
        .join(ContractYear, ContractYear.contract_id == Contract.id)
        .filter(Player.team_id == team_id, ContractYear.season == season, ContractYear.dead_cap_value > 0)
        .order_by(ContractYear.dead_cap_value.desc())
        .all()
    )
    by_player = [
        DeadCapPlayerRow(
            player_id=pid, player_name=name, position=position, season=s,
            dead_cap_value=float(dcv), contract_status=status,
        )
        for pid, name, position, s, dcv, status in player_rows
    ]

    season_rows = (
        db.query(ContractYear.season, func.sum(ContractYear.dead_cap_value))
        .join(Contract)
        .filter(Contract.team_id == team_id, ContractYear.season.in_(PROJECTION_SEASONS))
        .group_by(ContractYear.season)
        .order_by(ContractYear.season)
        .all()
    )
    by_season = [DeadCapSeasonRow(season=s, dead_cap=float(total or 0)) for s, total in season_rows]

    return DeadCapDashboardOut(
        team_id=team_id,
        current_season=season,
        total_dead_cap_current_season=round(sum(r.dead_cap_value for r in by_player), 2),
        by_player=by_player,
        by_season=by_season,
    )
