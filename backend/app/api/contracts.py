from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.contract import Contract
from app.models.contract_scenario import CAP_ENGINE_VERSION, ContractScenario
from app.models.contract_year import ContractYear
from app.models.player import Player
from app.models.team import Team
from app.models.team_cap import TeamCap
from app.schemas.contract import (
    ContractListItem,
    ContractOut,
    ExtensionImpactOut,
    ExtensionRequest,
    ExtensionYearOut,
    ReleaseImpactOut,
    ReleaseRequest,
    RestructureImpactOut,
    RestructureRequest,
    ScenarioComparisonOut,
    ScenarioOption,
    TradeImpactOut,
    TradeRequest,
)
from app.seed.demo_data import CURRENT_SEASON, DEMO_LEAGUE_CAP
from app.services.cap_engine import (
    ContractYearInput,
    calculate_dead_cap,
    calculate_extension,
    calculate_restructure,
    calculate_trade_impact,
)

router = APIRouter(prefix="/api/contracts", tags=["contracts"])


def _record_scenario(
    db: Session,
    *,
    player_id: int,
    team_id: int,
    contract_id: int,
    scenario_type: str,
    assumptions: dict,
    results: dict,
) -> int:
    scenario = ContractScenario(
        player_id=player_id,
        team_id=team_id,
        contract_id=contract_id,
        scenario_type=scenario_type,
        model_version=CAP_ENGINE_VERSION,
        assumptions=assumptions,
        results=results,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario.id


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

    assumptions_dict = {"release_season": body.release_season, "june1": body.june1}
    results_dict = {
        "before_cap_hit": result.pre_release_cap_hit,
        "current_year_dead_cap": result.current_year_dead_cap,
        "next_year_dead_cap": result.next_year_dead_cap,
        "current_year_cap_savings": result.current_year_cap_savings,
        "total_dead_cap": result.total_dead_cap,
    }
    scenario_id = _record_scenario(
        db,
        player_id=player.id,
        team_id=contract.team_id,
        contract_id=contract.id,
        scenario_type="release",
        assumptions=assumptions_dict,
        results=results_dict,
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
        scenario_id=scenario_id,
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

    scenario_id = _record_scenario(
        db,
        player_id=player.id,
        team_id=contract.team_id,
        contract_id=contract.id,
        scenario_type="restructure",
        assumptions={"restructure_season": body.restructure_season, "amount_to_convert": body.amount_to_convert},
        results={
            "original_cap_hit": result.original_cap_hit,
            "new_cap_hit": result.new_cap_hit,
            "current_year_savings": result.current_year_savings,
            "future_cap_hit_increases": result.future_cap_hit_increases,
        },
    )

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
        scenario_id=scenario_id,
    )


@router.post("/{contract_id}/trade", response_model=TradeImpactOut)
def simulate_trade(contract_id: int, body: TradeRequest, db: Session = Depends(get_db)):
    """Model-only scenario: computes the cap consequence of trading this
    player away, for both the trading and (hypothetical) acquiring team.
    Does NOT mutate stored data."""
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    player = db.get(Player, contract.player_id)

    years = _year_inputs(db, contract_id)
    result = calculate_trade_impact(years, trade_season=body.trade_season)

    scenario_id = _record_scenario(
        db,
        player_id=player.id,
        team_id=contract.team_id,
        contract_id=contract.id,
        scenario_type="trade",
        assumptions={"trade_season": body.trade_season},
        results={
            "trading_team_dead_cap": result.trading_team_dead_cap,
            "trading_team_cap_savings": result.trading_team_cap_savings,
            "acquiring_team_cap_hits": result.acquiring_team_cap_hits,
        },
    )

    return TradeImpactOut(
        player_id=player.id,
        player_name=player.name,
        contract_id=contract.id,
        trade_season=body.trade_season,
        trading_team_id=contract.team_id,
        trading_team_pre_trade_cap_hit=result.trading_team_pre_trade_cap_hit,
        trading_team_dead_cap=result.trading_team_dead_cap,
        trading_team_cap_savings=result.trading_team_cap_savings,
        acquiring_team_cap_hits=result.acquiring_team_cap_hits,
        acquiring_team_total_remaining_commitment=result.acquiring_team_total_remaining_commitment,
        assumptions=[
            "The trading team's dead-cap mechanics match a standard (non-June-1) release — the NFL "
            "does not offer a June-1 designation for trades.",
            "The acquiring team is assumed to inherit only remaining base salary, roster bonus, and "
            "incentives — no signing-bonus proration carries over, since that money was already paid "
            "by (and stays the dead-cap obligation of) the trading team.",
            "This models the contract's cap consequences only, not trade compensation (draft picks, "
            "other players) or whether any team would actually agree to the trade.",
            "This is a hypothetical scenario. No contract, roster, or team data is changed by this endpoint.",
        ],
        scenario_id=scenario_id,
    )


def _to_extension_year_out(y: ContractYearInput) -> ExtensionYearOut:
    return ExtensionYearOut(
        season=y.season,
        base_salary=y.base_salary,
        signing_bonus_proration=y.signing_bonus_proration,
        cap_hit=y.cap_hit,
        guaranteed_base_salary=y.guaranteed_base_salary,
    )


@router.post("/{contract_id}/extend", response_model=ExtensionImpactOut)
def simulate_extension(contract_id: int, body: ExtensionRequest, db: Session = Depends(get_db)):
    """Model-only scenario: appends a hypothetical extension after the
    player's current contract. All new-contract terms are user-supplied
    hypothetical inputs — Cap Ledger does not predict or infer extension
    terms. Does NOT mutate stored data."""
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    player = db.get(Player, contract.player_id)

    years = _year_inputs(db, contract_id)
    try:
        result = calculate_extension(
            years,
            extension_start_season=body.extension_start_season,
            new_length_years=body.new_length_years,
            new_total_value=body.new_total_value,
            new_signing_bonus=body.new_signing_bonus,
            new_guaranteed_money=body.new_guaranteed_money,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    scenario_id = _record_scenario(
        db,
        player_id=player.id,
        team_id=contract.team_id,
        contract_id=contract.id,
        scenario_type="extension",
        assumptions=body.model_dump(),
        results={
            "total_new_commitment": result.total_new_commitment,
            "total_new_guaranteed": result.total_new_guaranteed,
            "first_year_cap_hit_change": result.first_year_cap_hit_change,
        },
    )

    return ExtensionImpactOut(
        player_id=player.id,
        player_name=player.name,
        contract_id=contract.id,
        extension_start_season=body.extension_start_season,
        current_contract_years=[_to_extension_year_out(y) for y in result.current_contract_years],
        new_contract_years=[_to_extension_year_out(y) for y in result.new_contract_years],
        combined_years=[_to_extension_year_out(y) for y in result.combined_years],
        total_new_commitment=result.total_new_commitment,
        total_new_guaranteed=result.total_new_guaranteed,
        first_year_cap_hit_change=result.first_year_cap_hit_change,
        assumptions=[
            "All extension terms (length, total value, signing bonus, guaranteed money) are "
            "hypothetical inputs you supplied — not a prediction of what the player or team would "
            "actually agree to.",
            "The new contract's year-by-year schedule is structured using the same escalating-salary, "
            "prorated-bonus approach documented in docs/cap_engine.md — an assumption for turning "
            "summary terms into a plausible timeline, not a specific negotiated structure.",
            "This is a hypothetical scenario. No contract or roster data is changed by this endpoint.",
        ],
        scenario_id=scenario_id,
    )


@router.get("/{contract_id}/scenarios", response_model=ScenarioComparisonOut)
def compare_scenarios(contract_id: int, season: int = Query(CURRENT_SEASON), db: Session = Depends(get_db)):
    """"What should we do with this contract?" — automatically evaluates
    Keep / Restructure / Release / Trade side by side for the given season,
    using the same deterministic cap-engine functions as the dedicated
    simulators. Every assessment is a transparent, threshold-based label,
    not a black-box recommendation — see the reasoning bullets on each
    option and docs/cap_engine.md for the exact math.
    """
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")
    player = db.get(Player, contract.player_id)

    years = _year_inputs(db, contract_id)
    current_year = next((y for y in years if y.season == season), None)
    keep_cap_hit = current_year.cap_hit if current_year else 0.0

    options: list[ScenarioOption] = []

    assumed_cap = DEMO_LEAGUE_CAP.get(season, 270_000_000.0)
    cap_hit_pct = keep_cap_hit / assumed_cap if assumed_cap else 0.0
    keep_assessment = "Strong" if cap_hit_pct < 0.08 else "Moderate" if cap_hit_pct < 0.15 else "Conditional"

    options.append(
        ScenarioOption(
            scenario_type="keep",
            label="Keep",
            current_year_cap_impact=0.0,
            future_year_impact="Unchanged — future cap hits proceed as currently structured.",
            dead_cap=0.0,
            assessment=keep_assessment,
            reasoning=[
                f"Current cap hit for {season}: ${keep_cap_hit:,.0f} (~{cap_hit_pct * 100:.1f}% of an "
                f"assumed ${assumed_cap:,.0f} league cap).",
                "No transaction costs, no dead cap, no change to future flexibility.",
            ],
        )
    )

    # Restructure: default to converting 50% of the season's base salary, if any.
    if current_year and current_year.base_salary > 0:
        convert_amount = round(current_year.base_salary * 0.5, 2)
        try:
            restructure = calculate_restructure(years, restructure_season=season, amount_to_convert=convert_amount)
            future_total = sum(restructure.future_cap_hit_increases.values())
            options.append(
                ScenarioOption(
                    scenario_type="restructure",
                    label="Restructure",
                    current_year_cap_impact=restructure.current_year_savings,
                    future_year_impact=f"Adds ${future_total:,.0f} total across "
                    f"{len(restructure.future_cap_hit_increases)} future season(s).",
                    dead_cap=0.0,
                    assessment="Favorable" if restructure.current_year_savings > 0 else "Unfavorable",
                    reasoning=[
                        f"Converting ${convert_amount:,.0f} of base salary creates "
                        f"${restructure.current_year_savings:,.0f} in {season} cap space.",
                        "That exact amount is added back across future seasons — restructuring "
                        "shifts cost, it does not remove it.",
                        "Reduces future flexibility, particularly if the player is released or traded "
                        "before the added proration is fully paid down.",
                    ],
                )
            )
        except ValueError:
            pass

    release = calculate_dead_cap(years, release_season=season, june1=False)
    release_assessment = (
        "Favorable" if release.current_year_cap_savings > 0.15 * max(release.pre_release_cap_hit, 1)
        else "Conditional" if release.current_year_cap_savings > 0
        else "Unfavorable"
    )
    options.append(
        ScenarioOption(
            scenario_type="release",
            label="Release",
            current_year_cap_impact=release.current_year_cap_savings,
            future_year_impact=(
                f"Removes ${release.next_year_cap_hit_removed:,.0f} in future-season cap hits the "
                "team no longer owes."
            ),
            dead_cap=release.total_dead_cap,
            assessment=release_assessment,
            reasoning=[
                f"Standard release creates ${release.current_year_cap_savings:,.0f} in {season} cap "
                f"savings against ${release.total_dead_cap:,.0f} in dead cap.",
                "Ends the team's obligation for all future seasons on this contract.",
                "Loses the player's on-field production — a football decision this model does not "
                "evaluate.",
            ],
        )
    )

    trade = calculate_trade_impact(years, trade_season=season)
    options.append(
        ScenarioOption(
            scenario_type="trade",
            label="Trade",
            current_year_cap_impact=trade.trading_team_cap_savings,
            future_year_impact="Future cap obligations on this contract transfer to the acquiring team.",
            dead_cap=trade.trading_team_dead_cap,
            assessment="Conditional",
            reasoning=[
                f"Cap mechanics mirror a standard release (${trade.trading_team_cap_savings:,.0f} "
                f"savings against ${trade.trading_team_dead_cap:,.0f} dead cap) plus whatever "
                "compensation is negotiated.",
                "Requires a trade partner willing to take on the remaining contract — not modeled "
                "here, so this option is always labeled Conditional rather than scored outright.",
            ],
        )
    )

    return ScenarioComparisonOut(
        player_id=player.id,
        player_name=player.name,
        contract_id=contract.id,
        season=season,
        options=options,
        disclaimer=(
            "Assessments are transparent, threshold-based labels derived from the cap-engine "
            "calculations shown above — not a black-box recommendation, and not aware of roster needs, "
            "player performance, or competitive timeline. Review the reasoning for each option before "
            "drawing a conclusion."
        ),
    )
