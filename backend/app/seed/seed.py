"""Populate the database with synthetic demo data.

Run with: `python -m app.seed.seed` (from backend/, with the venv active
and DATABASE_URL pointing at a reachable Postgres instance).

DEMO DATA — NOT OFFICIAL NFL DATA. All player identities and dollar
figures are synthetically generated (see app/seed/demo_data.py).
"""
from __future__ import annotations

from sqlalchemy import delete

from app.database import Base, SessionLocal, engine
from app.models.contract import Contract
from app.models.contract_year import ContractYear
from app.models.player import Player
from app.models.team import Team
from app.models.team_cap import TeamCap
from app.models.team_roster import TeamRoster
from app.seed.demo_data import (
    CURRENT_SEASON,
    DEMO_LEAGUE_CAP,
    PROJECTION_SEASONS,
    generate_released_players,
    generate_team_roster,
)
from app.seed.teams_data import TEAMS
from app.services.cap_engine import summarize_team_cap


def reset_schema() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def run() -> None:
    reset_schema()
    db = SessionLocal()
    try:
        team_objs: dict[str, Team] = {}
        for name, abbr, conf, division in TEAMS:
            team = Team(name=name, abbreviation=abbr, conference=conf, division=division)
            db.add(team)
            team_objs[abbr] = team
        db.flush()

        for idx, (_, abbr, _, _) in enumerate(TEAMS):
            team = team_objs[abbr]
            roster_entries = generate_team_roster(abbr, idx)
            released_entries = generate_released_players(abbr, idx, count=2)

            for entry in roster_entries + released_entries:
                gp = entry.player
                player = Player(
                    name=gp.name,
                    position=gp.position,
                    team_id=team.id,
                    age=gp.age,
                    experience=gp.experience,
                    status=gp.status,
                )
                db.add(player)
                db.flush()

                gc = entry.contract
                latest_year = gc.years[-1] if gc.years else None
                current_year_row = next((y for y in gc.years if y.season == CURRENT_SEASON), None)
                contract = Contract(
                    player_id=player.id,
                    team_id=team.id,
                    contract_start=gc.contract_start,
                    contract_end=gc.contract_end,
                    total_value=gc.total_value,
                    annual_value=gc.annual_value,
                    guaranteed_money=gc.guaranteed_money,
                    signing_bonus=gc.signing_bonus,
                    current_salary=(current_year_row.base_salary if current_year_row else 0.0),
                    current_cap_hit=(
                        current_year_row.base_salary + current_year_row.signing_bonus_proration
                        + current_year_row.roster_bonus + current_year_row.incentives
                        if current_year_row else 0.0
                    ),
                    contract_status=gc.contract_status,
                )
                db.add(contract)
                db.flush()

                dead_cap_overrides = getattr(gc, "years_dead_cap_override", {})
                for gy in gc.years:
                    cap_hit = round(
                        gy.base_salary + gy.signing_bonus_proration + gy.roster_bonus + gy.incentives, 2
                    )
                    db.add(
                        ContractYear(
                            contract_id=contract.id,
                            season=gy.season,
                            base_salary=gy.base_salary,
                            signing_bonus_proration=gy.signing_bonus_proration,
                            roster_bonus=gy.roster_bonus,
                            incentives=gy.incentives,
                            cap_hit=cap_hit,
                            cash_value=round(gy.base_salary + gy.roster_bonus + gy.incentives, 2),
                            dead_cap_value=dead_cap_overrides.get(gy.season, 0.0),
                            guaranteed_base_salary=gy.guaranteed_base_salary,
                        )
                    )

                roster_status = "active" if gc.contract_status == "active" else "released"
                db.add(
                    TeamRoster(
                        team_id=team.id,
                        player_id=player.id,
                        season=CURRENT_SEASON,
                        roster_status=roster_status,
                    )
                )

        db.flush()

        # Roll up team_cap for each team across the projection window.
        for abbr, team in team_objs.items():
            for season in PROJECTION_SEASONS:
                active_hits = [
                    cy.cap_hit
                    for cy in (
                        db.query(ContractYear)
                        .join(Contract)
                        .filter(
                            Contract.team_id == team.id,
                            Contract.contract_status == "active",
                            ContractYear.season == season,
                        )
                    )
                ]
                dead_cap = (
                    db.query(ContractYear)
                    .join(Contract)
                    .filter(Contract.team_id == team.id, ContractYear.season == season)
                    .with_entities(ContractYear.dead_cap_value)
                    .all()
                )
                dead_cap_total = round(float(sum(v for (v,) in dead_cap)), 2)

                summary = summarize_team_cap(
                    season=season,
                    salary_cap=DEMO_LEAGUE_CAP[season],
                    active_cap_hits=active_hits,
                    dead_cap=dead_cap_total,
                )
                db.add(
                    TeamCap(
                        team_id=team.id,
                        season=season,
                        salary_cap=summary.salary_cap,
                        cap_commitments=summary.full_roster_commitments,
                        top51_commitments=summary.top51_commitments,
                        dead_cap=summary.dead_cap,
                        cap_space=summary.available_cap_space,
                        effective_cap_space=summary.effective_cap_space,
                        carryover=0.0,
                    )
                )

        db.commit()
        n_teams = db.query(Team).count()
        n_players = db.query(Player).count()
        n_contracts = db.query(Contract).count()
        print(f"Seeded {n_teams} teams, {n_players} players, {n_contracts} contracts.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
