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
    FlexibilityForecastOut,
    FlexibilityForecastSeasonOut,
    FreeAgentPlanningOut,
    FreeAgentPlanningRequest,
    PositionSpendingOut,
    RookiePickImpact,
    RookiePlanningOut,
    RookiePlanningRequest,
    TeamCapOut,
    TeamOut,
)
from app.seed.demo_data import CURRENT_SEASON, DEMO_LEAGUE_CAP, PROJECTION_SEASONS
from app.services.cap_engine import (
    ContractYearInput,
    calculate_dead_cap,
    estimate_rookie_contract_terms,
    structure_contract_years,
    summarize_team_cap,
)
from app.services.financial_intelligence import calculate_financial_concentration, calculate_financial_flexibility

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


def _active_cap_hits(db: Session, team_id: int, season: int) -> list[float]:
    return [
        float(cy.cap_hit)
        for cy in (
            db.query(ContractYear)
            .join(Contract)
            .filter(Contract.team_id == team_id, Contract.contract_status == "active", ContractYear.season == season)
        )
    ]


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


def _flexibility_score_for_season(
    db: Session, team_id: int, season: int, salary_cap: float, extra_cap_hits: list[float] | None = None
) -> tuple[float, list]:
    active_hits = _active_cap_hits(db, team_id, season) + (extra_cap_hits or [])
    dead_cap_rows = (
        db.query(ContractYear)
        .join(Contract)
        .filter(Contract.team_id == team_id, ContractYear.season == season)
        .with_entities(ContractYear.dead_cap_value)
        .all()
    )
    dead_cap_total = float(sum(v for (v,) in dead_cap_rows))
    summary = summarize_team_cap(season=season, salary_cap=salary_cap, active_cap_hits=active_hits, dead_cap=dead_cap_total)

    cap_space_pct = summary.available_cap_space / salary_cap if salary_cap else 0.0
    dead_cap_pct = dead_cap_total / salary_cap if salary_cap else 0.0

    future_guaranteed_rows = (
        db.query(ContractYear)
        .join(Contract)
        .filter(Contract.team_id == team_id, Contract.contract_status == "active", ContractYear.season > season)
        .with_entities(ContractYear.guaranteed_base_salary)
        .all()
    )
    future_guaranteed_pct = float(sum(v for (v,) in future_guaranteed_rows)) / salary_cap if salary_cap else 0.0

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
    expiring_pct = expiring_total / summary.full_roster_commitments if summary.full_roster_commitments else 0.0

    concentration = calculate_financial_concentration(active_hits)

    result = calculate_financial_flexibility(
        cap_space_pct=cap_space_pct, dead_cap_pct=dead_cap_pct, future_guaranteed_pct=future_guaranteed_pct,
        expiring_pct=expiring_pct, top5_concentration_pct=concentration.top5_pct / 100,
    )
    return result.score, result.factors


@router.get("/{team_id}/financial-flexibility-forecast", response_model=FlexibilityForecastOut)
def financial_flexibility_forecast(
    team_id: int,
    growth_rate: float = Query(0.06),
    sensitivity_delta: float = Query(0.03, description="+/- growth rate used for the sensitivity comparison"),
    db: Session = Depends(get_db),
):
    """Financial Flexibility Score projected across the multi-year window
    (project brief section 28), plus a sensitivity comparison at a lower and
    higher assumed cap-growth rate (section 33) and an automatically
    generated "what would change our mind" note (section 34).
    """
    _get_team_or_404(db, team_id)
    base_row = _team_cap_row(db, team_id, CURRENT_SEASON)
    base_cap = float(base_row.salary_cap) if base_row else DEMO_LEAGUE_CAP.get(CURRENT_SEASON, 270_000_000.0)

    def run(rate: float) -> list[tuple[int, float, list]]:
        out = []
        for season in PROJECTION_SEASONS:
            years_from_base = season - CURRENT_SEASON
            projected_cap = base_cap * ((1 + rate) ** years_from_base)
            score, factors = _flexibility_score_for_season(db, team_id, season, projected_cap)
            out.append((season, score, factors))
        return out

    base_run = run(growth_rate)
    low_run = run(max(0.0, growth_rate - sensitivity_delta))
    high_run = run(growth_rate + sensitivity_delta)

    seasons_out: list[FlexibilityForecastSeasonOut] = []
    narrative: list[str] = []
    prev_score = None
    prev_factors = None
    for season, score, factors in base_run:
        top_positive = max((f for f in factors if f.direction == "+"), key=lambda f: f.score, default=None)
        top_negative = min((f for f in factors if f.direction == "-"), key=lambda f: f.score, default=None)
        seasons_out.append(
            FlexibilityForecastSeasonOut(
                season=season, score=score,
                top_positive_factor=top_positive.label if top_positive else None,
                top_negative_factor=top_negative.label if top_negative else None,
            )
        )
        if prev_score is not None and abs(score - prev_score) >= 8:
            direction_word = "increases" if score > prev_score else "decreases"
            driver = None
            if prev_factors is not None:
                deltas = [(f.label, f.score - pf.score) for f, pf in zip(factors, prev_factors)]
                driver = min(deltas, key=lambda d: d[1]) if direction_word == "decreases" else max(deltas, key=lambda d: d[1])
            driver_text = f" — driven mainly by a change in {driver[0].lower()}" if driver else ""
            narrative.append(f"Flexibility {direction_word} in {season} (from {prev_score:.0f} to {score:.0f}){driver_text}.")
        prev_score, prev_factors = score, factors

    # Pick the season where the growth-rate assumption actually moves the score, rather than
    # always the final season (which is often already at the clamped ceiling either way).
    sensitivity_by_season = [
        (base_run[i][0], base_run[i][1], low_run[i][1], high_run[i][1])
        for i in range(len(base_run))
    ]
    season_num, base_val, low_val, high_val = max(
        sensitivity_by_season, key=lambda row: abs(row[3] - row[2])
    )
    if abs(high_val - low_val) < 1:
        what_would_change = [
            "Flexibility in this forecast is not very sensitive to the cap-growth assumption within "
            f"±{sensitivity_delta * 100:.1f} points — scores stay within a point or two across the "
            "range tested."
        ]
    else:
        what_would_change = [
            f"A lower cap-growth assumption ({(growth_rate - sensitivity_delta) * 100:.1f}%/year instead "
            f"of {growth_rate * 100:.1f}%/year) would put {season_num} flexibility at {low_val:.0f} "
            f"instead of {base_val:.0f}.",
            f"A higher cap-growth assumption ({(growth_rate + sensitivity_delta) * 100:.1f}%/year) would "
            f"put {season_num} flexibility at {high_val:.0f} instead of {base_val:.0f}.",
        ]
    if not narrative:
        narrative.append("Flexibility stays relatively stable across the projection window under this assumption.")

    return FlexibilityForecastOut(
        team_id=team_id,
        growth_rate=growth_rate,
        seasons=seasons_out,
        narrative=narrative,
        what_would_change_our_mind=what_would_change,
        disclaimer=(
            "Projected seasons use only currently-signed contracts and an assumed cap growth rate — "
            "not a guarantee. Real teams continuously sign new players, so this likely overstates future "
            "flexibility (see docs/data_sources.md)."
        ),
    )


@router.post("/{team_id}/free-agent-planning", response_model=FreeAgentPlanningOut)
def free_agent_planning(team_id: int, body: FreeAgentPlanningRequest, db: Session = Depends(get_db)):
    """Model signing a hypothetical free agent: what would this contract's
    cap hit be, and what does it leave the team with. Contract figures are
    hypothetical unless drawn from an actual reported contract."""
    _get_team_or_404(db, team_id)
    team_cap_row = _team_cap_row(db, team_id, body.start_season)
    if team_cap_row is None:
        raise HTTPException(status_code=404, detail=f"No cap data for season {body.start_season}")

    total_value = round(body.target_aav * body.contract_length, 2)
    new_years = structure_contract_years(
        start_season=body.start_season, length_years=body.contract_length, total_value=total_value,
        signing_bonus=round(body.guaranteed_money * 0.7, 2), guaranteed_money=body.guaranteed_money,
    )
    year_by_year = {y.season: y.cap_hit for y in new_years}

    active_hits = _active_cap_hits(db, team_id, body.start_season)
    new_hit = year_by_year.get(body.start_season, 0.0)
    salary_cap = float(team_cap_row.salary_cap)
    after_summary = summarize_team_cap(
        season=body.start_season, salary_cap=salary_cap,
        active_cap_hits=active_hits + [new_hit], dead_cap=float(team_cap_row.dead_cap),
    )

    before_score, _ = _flexibility_score_for_season(db, team_id, body.start_season, salary_cap)
    after_score, _ = _flexibility_score_for_season(db, team_id, body.start_season, salary_cap, extra_cap_hits=[new_hit])

    return FreeAgentPlanningOut(
        team_id=team_id,
        position=body.position,
        start_season=body.start_season,
        projected_total_value=total_value,
        projected_signing_bonus=round(body.guaranteed_money * 0.7, 2),
        year_by_year_cap_hit=year_by_year,
        cap_space_before=float(team_cap_row.cap_space),
        cap_space_after=after_summary.available_cap_space,
        flexibility_score_before=before_score,
        flexibility_score_after=after_score,
        assumptions=[
            "Contract terms are hypothetical inputs you supplied, not an actual reported contract.",
            "Signing bonus is assumed to be 70% of guaranteed money, matching the structuring "
            "assumption used elsewhere in Cap Ledger (see docs/cap_engine.md).",
            "This is a planning estimate. No roster or contract data is changed by this endpoint.",
        ],
    )


@router.post("/{team_id}/rookie-planning", response_model=RookiePlanningOut)
def rookie_planning(team_id: int, body: RookiePlanningRequest, db: Session = Depends(get_db)):
    """Model the cap consequence of drafting several rookies in a given
    season, using a simplified per-round rookie-contract estimate (see
    docs/cap_engine.md — this is NOT the real NFL rookie wage scale)."""
    _get_team_or_404(db, team_id)
    team_cap_row = _team_cap_row(db, team_id, body.season)
    if team_cap_row is None:
        raise HTTPException(status_code=404, detail=f"No cap data for season {body.season}")

    pick_impacts: list[RookiePickImpact] = []
    total_first_year = 0.0
    for pick in body.picks:
        terms = estimate_rookie_contract_terms(pick.draft_round)
        years = structure_contract_years(
            start_season=body.season, length_years=terms.length_years, total_value=terms.total_value,
            signing_bonus=terms.signing_bonus, guaranteed_money=terms.guaranteed_money,
        )
        first_year_hit = years[0].cap_hit if years else 0.0
        total_first_year = round(total_first_year + first_year_hit, 2)
        pick_impacts.append(
            RookiePickImpact(
                draft_round=pick.draft_round, position=pick.position,
                total_value=terms.total_value, signing_bonus=terms.signing_bonus,
                first_year_cap_hit=first_year_hit,
            )
        )

    active_hits = _active_cap_hits(db, team_id, body.season)
    after_summary = summarize_team_cap(
        season=body.season, salary_cap=float(team_cap_row.salary_cap),
        active_cap_hits=active_hits + [p.first_year_cap_hit for p in pick_impacts],
        dead_cap=float(team_cap_row.dead_cap),
    )

    return RookiePlanningOut(
        team_id=team_id,
        season=body.season,
        picks=pick_impacts,
        total_first_year_cap_impact=total_first_year,
        cap_space_before=float(team_cap_row.cap_space),
        cap_space_after=after_summary.available_cap_space,
        assumptions=[
            "Rookie contract terms are a SIMPLIFIED, per-round flat estimate — not the real NFL rookie "
            "wage scale, which varies continuously by exact pick under a CBA-defined formula.",
            "All rookie contracts are assumed to be standard 4-year deals (no fifth-year option modeled).",
            "This is a planning estimate. No roster or contract data is changed by this endpoint.",
        ],
    )
