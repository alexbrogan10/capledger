"""Synthetic demo-data generator for Cap Ledger.

Everything produced here — player names, ages, and every dollar figure —
is SYNTHETIC. It is generated with a fixed random seed so the demo dataset
is reproducible, not because it represents any real player or real
contract. Team names/divisions (teams_data.py) are the only real-world
facts used.

DEMO DATA — NOT OFFICIAL NFL DATA.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.seed.teams_data import TEAMS
from app.services.cap_engine import signing_bonus_proration

CURRENT_SEASON = 2026
PROJECTION_SEASONS = [2026, 2027, 2028, 2029, 2030]

# Synthetic league salary-cap assumption, NOT an official NFL figure.
# A starting baseline plus a fixed assumed year-over-year growth rate,
# reproduced here (rather than imported from app.config) so the seed
# module stays a pure, standalone generator.
_BASE_YEAR = 2024
_BASE_CAP = 238_000_000.0
_GROWTH_RATE = 0.06

DEMO_LEAGUE_CAP: dict[int, float] = {}
_cap = _BASE_CAP
for _year in range(_BASE_YEAR, 2031):
    DEMO_LEAGUE_CAP[_year] = round(_cap, 2)
    _cap *= 1 + _GROWTH_RATE

FIRST_NAMES = [
    "Marcus", "Jalen", "Trevon", "Dax", "Kellen", "Bryce", "Tyrell", "Colt", "Andre", "Darius",
    "Grant", "Malik", "Shane", "Deshawn", "Isaiah", "Cade", "Roman", "Xavier", "Mason", "Cordell",
    "Elijah", "Trent", "Jordy", "Kavon", "Nathaniel", "Reggie", "Sawyer", "Tobias", "Wade", "Zachary",
    "Amir", "Beau", "Cyrus", "Dalton", "Emmett", "Fabian", "Gavin", "Harlan", "Ivan", "Jasper",
    "Keenan", "Lamar", "Miles", "Nico", "Orlando", "Preston", "Quentin", "Rashad", "Silas", "Tucker",
    "Victor", "Wesley", "Yusuf", "Zane", "Aiden", "Brody", "Caleb", "Dominic", "Ezra", "Finn",
]

LAST_NAMES = [
    "Whitfield", "Barlow", "Sarkis", "Monroe", "Boateng", "Castellano", "Reeves", "Okafor", "Lindqvist",
    "Marchetti", "Pruitt", "Danforth", "Kingsley", "Vance", "Holloway", "Esparza", "Nakamura", "Girard",
    "Broussard", "Callahan", "Delgado", "Fenwick", "Grosso", "Hartwell", "Isaacs", "Jernigan", "Kowalski",
    "Landry", "Mercer", "Nowak", "Osei", "Pemberton", "Quintero", "Rourke", "Stackhouse", "Thibodeaux",
    "Underwood", "Villanueva", "Wagner", "Yancey", "Zeigler", "Ashford", "Beaumont", "Crenshaw", "Duvall",
    "Ekwueme", "Farrow", "Gallardo", "Huxley", "Ibarra",
]

POSITION_ROSTER_TEMPLATE: list[tuple[str, int]] = [
    ("QB", 3), ("RB", 4), ("FB", 1), ("WR", 6), ("TE", 3),
    ("LT", 2), ("LG", 2), ("C", 2), ("RG", 2), ("RT", 2),
    ("EDGE", 4), ("DT", 4), ("LB", 5), ("CB", 6), ("S", 4),
    ("K", 1), ("P", 1), ("LS", 1),
]

# (starter_aav_low, starter_aav_high, depth_aav_low, depth_aav_high) in dollars.
POSITION_AAV_RANGES: dict[str, tuple[float, float, float, float]] = {
    "QB": (28_000_000, 52_000_000, 1_200_000, 3_500_000),
    "RB": (6_000_000, 12_500_000, 1_000_000, 2_600_000),
    "FB": (2_000_000, 3_500_000, 1_000_000, 1_400_000),
    "WR": (16_000_000, 28_000_000, 1_100_000, 4_000_000),
    "TE": (9_000_000, 15_000_000, 1_100_000, 3_000_000),
    "LT": (16_000_000, 24_000_000, 1_200_000, 4_500_000),
    "LG": (10_000_000, 17_000_000, 1_100_000, 3_200_000),
    "C": (10_000_000, 16_000_000, 1_100_000, 3_000_000),
    "RG": (10_000_000, 17_000_000, 1_100_000, 3_200_000),
    "RT": (13_000_000, 20_000_000, 1_200_000, 4_000_000),
    "EDGE": (17_000_000, 30_000_000, 1_200_000, 4_500_000),
    "DT": (11_000_000, 22_000_000, 1_100_000, 3_800_000),
    "LB": (9_000_000, 17_000_000, 1_000_000, 3_000_000),
    "CB": (13_000_000, 22_000_000, 1_100_000, 3_500_000),
    "S": (9_000_000, 16_000_000, 1_000_000, 2_800_000),
    "K": (3_500_000, 5_500_000, 900_000, 1_400_000),
    "P": (2_500_000, 4_000_000, 900_000, 1_300_000),
    "LS": (900_000, 1_400_000, 800_000, 1_100_000),
}


@dataclass
class GeneratedPlayer:
    name: str
    position: str
    age: int
    experience: int
    status: str = "active"


@dataclass
class GeneratedContractYear:
    season: int
    base_salary: float
    signing_bonus_proration: float
    roster_bonus: float
    incentives: float
    guaranteed_base_salary: float


@dataclass
class GeneratedContract:
    contract_start: int
    contract_end: int
    total_value: float
    annual_value: float
    guaranteed_money: float
    signing_bonus: float
    contract_status: str
    years: list[GeneratedContractYear] = field(default_factory=list)


@dataclass
class GeneratedRosterEntry:
    player: GeneratedPlayer
    contract: GeneratedContract
    is_starter: bool


def _build_contract(
    rng: random.Random,
    *,
    start: int,
    length: int,
    aav_low: float,
    aav_high: float,
    guarantee_pct: tuple[float, float],
    status: str = "active",
) -> GeneratedContract:
    end = start + length - 1
    aav = round(rng.uniform(aav_low, aav_high), 2)
    total_value = round(aav * length, 2)

    guarantee_fraction = rng.uniform(*guarantee_pct)
    guaranteed_money = round(min(total_value, total_value * guarantee_fraction), 2)

    # Signing bonus is the portion of the guarantee typically paid up front;
    # assume ~70% of guaranteed money is structured as signing bonus.
    signing_bonus = round(guaranteed_money * 0.7, 2)
    proration_per_year = signing_bonus_proration(signing_bonus, length) if signing_bonus > 0 else 0.0

    non_bonus_cash = round(total_value - signing_bonus, 2)

    # Base salaries escalate roughly linearly across the contract.
    weights = [1.0 + 0.18 * i for i in range(length)]
    weight_sum = sum(weights)
    base_salaries = [round(non_bonus_cash * (w / weight_sum), 2) for w in weights]
    # Fix any rounding drift onto the final year.
    drift = round(non_bonus_cash - sum(base_salaries), 2)
    base_salaries[-1] = round(base_salaries[-1] + drift, 2)

    guaranteed_base_remaining = round(max(0.0, guaranteed_money - signing_bonus), 2)

    years: list[GeneratedContractYear] = []
    for i in range(length):
        season = start + i
        base_salary = max(0.0, base_salaries[i])
        proration = proration_per_year if i < min(length, 5) else 0.0
        guaranteed_here = round(min(base_salary, guaranteed_base_remaining), 2)
        guaranteed_base_remaining = round(guaranteed_base_remaining - guaranteed_here, 2)
        years.append(
            GeneratedContractYear(
                season=season,
                base_salary=base_salary,
                signing_bonus_proration=proration,
                roster_bonus=0.0,
                incentives=0.0,
                guaranteed_base_salary=guaranteed_here,
            )
        )

    return GeneratedContract(
        contract_start=start,
        contract_end=end,
        total_value=total_value,
        annual_value=aav,
        guaranteed_money=guaranteed_money,
        signing_bonus=signing_bonus,
        contract_status=status,
        years=years,
    )


def _scale_contract(contract: GeneratedContract, factor: float) -> None:
    """Uniformly scale every dollar figure on a contract. Cap-hit math is
    linear in all of its inputs, so scaling every component by the same
    factor preserves the contract's internal consistency (proration still
    equals scaled signing bonus / proration years, etc.)."""
    contract.total_value = round(contract.total_value * factor, 2)
    contract.annual_value = round(contract.annual_value * factor, 2)
    contract.guaranteed_money = round(contract.guaranteed_money * factor, 2)
    contract.signing_bonus = round(contract.signing_bonus * factor, 2)
    for cy in contract.years:
        cy.base_salary = round(cy.base_salary * factor, 2)
        cy.signing_bonus_proration = round(cy.signing_bonus_proration * factor, 2)
        cy.roster_bonus = round(cy.roster_bonus * factor, 2)
        cy.incentives = round(cy.incentives * factor, 2)
        cy.guaranteed_base_salary = round(cy.guaranteed_base_salary * factor, 2)


def generate_team_roster(team_abbr: str, seed_offset: int) -> list[GeneratedRosterEntry]:
    """Generate a full ~53-man roster with contracts for one team, scaled
    so the team's current-season commitments land at a realistic (and cap
    -compliant, with some variation) fraction of the assumed league cap."""
    rng = random.Random(f"capledger-demo-{team_abbr}-{seed_offset}")
    roster: list[GeneratedRosterEntry] = []

    for position, count in POSITION_ROSTER_TEMPLATE:
        aav_low, aav_high, depth_low, depth_high = POSITION_AAV_RANGES[position]
        for slot in range(count):
            is_starter = slot == 0 or (slot == 1 and position in {"WR", "CB", "EDGE", "DT"})
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"

            if is_starter:
                age = rng.randint(24, 31)
                length = rng.randint(3, 5)
                guarantee_pct = (0.45, 0.72)
                low, high = aav_low, aav_high
            else:
                age = rng.randint(22, 33)
                length = rng.randint(1, 3)
                guarantee_pct = (0.0, 0.22)
                low, high = depth_low, depth_high

            experience = max(0, age - rng.randint(21, 23))
            start = CURRENT_SEASON - rng.randint(0, max(0, min(2, length - 1)))
            # Keep the contract covering the current season.
            if start + length - 1 < CURRENT_SEASON:
                start = CURRENT_SEASON

            player = GeneratedPlayer(name=name, position=position, age=age, experience=experience)
            contract = _build_contract(
                rng, start=start, length=length, aav_low=low, aav_high=high, guarantee_pct=guarantee_pct
            )
            roster.append(GeneratedRosterEntry(player=player, contract=contract, is_starter=is_starter))

    current_season_total = 0.0
    for entry in roster:
        cy = next((y for y in entry.contract.years if y.season == CURRENT_SEASON), None)
        if cy:
            current_season_total += cy.base_salary + cy.signing_bonus_proration + cy.roster_bonus + cy.incentives

    target_ratio = rng.uniform(0.80, 0.99)
    target_total = DEMO_LEAGUE_CAP[CURRENT_SEASON] * target_ratio
    if current_season_total > 0:
        scale_factor = target_total / current_season_total
        for entry in roster:
            _scale_contract(entry.contract, scale_factor)

    return roster


def generate_released_players(team_abbr: str, seed_offset: int, count: int = 2) -> list[GeneratedRosterEntry]:
    """A handful of already-released players with realized dead-cap charges
    hitting the current season, so team dead-cap figures aren't all zero."""
    rng = random.Random(f"capledger-demo-released-{team_abbr}-{seed_offset}")
    out: list[GeneratedRosterEntry] = []
    for _ in range(count):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        position = rng.choice(list(POSITION_AAV_RANGES.keys()))
        age = rng.randint(26, 33)
        experience = max(1, age - 22)
        player = GeneratedPlayer(name=name, position=position, age=age, experience=experience, status="released")

        length = 4
        start = CURRENT_SEASON - 2
        aav_low, aav_high, *_ = POSITION_AAV_RANGES[position]
        contract = _build_contract(
            rng, start=start, length=length, aav_low=aav_low * 0.6, aav_high=aav_high, guarantee_pct=(0.3, 0.55)
        )
        # Zero out cap hit for the released season onward, and park the
        # remaining unamortized proration as realized dead cap this season.
        remaining_proration = sum(
            cy.signing_bonus_proration for cy in contract.years if cy.season >= CURRENT_SEASON
        )
        for cy in contract.years:
            if cy.season >= CURRENT_SEASON:
                cy.base_salary = 0.0
                cy.signing_bonus_proration = 0.0
                cy.roster_bonus = 0.0
                cy.guaranteed_base_salary = 0.0
        # Store the realized dead cap on the current season's row.
        current_year_row = next((cy for cy in contract.years if cy.season == CURRENT_SEASON), None)
        if current_year_row is not None:
            current_year_row.incentives = 0.0
        contract.contract_status = "released"
        out.append(
            GeneratedRosterEntry(player=player, contract=contract, is_starter=False)
        )
        # Stash the realized dead-cap amount on the dataclass via a dynamic
        # attribute so seed.py can write it into the ContractYear row.
        out[-1].contract.years_dead_cap_override = {CURRENT_SEASON: round(remaining_proration, 2)}  # type: ignore[attr-defined]
    return out
