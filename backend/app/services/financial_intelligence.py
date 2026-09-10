"""Phase 3 — Financial Intelligence.

Deterministic, transparent scoring for financial flexibility, contract risk,
financial concentration, and contract-vs-market comparison. Per the
project's analytical rules, none of this is machine-learned: every score is
a documented, hand-verifiable formula over inputs already in the schema, and
every score ships with a breakdown explaining its drivers. See
docs/financial_flexibility.md and docs/contract_risk_methodology.md.

None of these scores use player performance/production data — Cap Ledger's
demo dataset has no such data, and inventing it would violate the project's
"never fabricate" rule. Contract risk and market comparison are therefore
scoped to what is honestly computable from cap/contract structure and
league-wide contract data, not on-field value.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Age at which position-typical decline risk begins to be modeled. A
# simplifying assumption, not a claim about any individual player.
POSITION_DECLINE_AGE = {
    "RB": 27, "FB": 28,
    "WR": 30, "CB": 29, "S": 30,
    "TE": 30, "LB": 30,
    "QB": 33, "K": 34, "P": 34, "LS": 34,
    "LT": 31, "LG": 31, "C": 31, "RG": 31, "RT": 31,
    "EDGE": 30, "DT": 30,
}
DEFAULT_DECLINE_AGE = 29


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Financial Concentration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConcentrationResult:
    total_commitments: float
    top1_pct: float
    top3_pct: float
    top5_pct: float
    top10_pct: float
    top1_dollars: float
    top3_dollars: float
    top5_dollars: float
    top10_dollars: float


def calculate_financial_concentration(active_cap_hits: list[float]) -> ConcentrationResult:
    """What share of a team's cap is committed to its N largest contracts."""
    sorted_hits = sorted(active_cap_hits, reverse=True)
    total = sum(sorted_hits)

    def top_n_dollars(n: int) -> float:
        return round(sum(sorted_hits[:n]), 2)

    def pct(dollars: float) -> float:
        return round(dollars / total * 100, 2) if total else 0.0

    top1 = top_n_dollars(1)
    top3 = top_n_dollars(3)
    top5 = top_n_dollars(5)
    top10 = top_n_dollars(10)

    return ConcentrationResult(
        total_commitments=round(total, 2),
        top1_pct=pct(top1), top3_pct=pct(top3), top5_pct=pct(top5), top10_pct=pct(top10),
        top1_dollars=top1, top3_dollars=top3, top5_dollars=top5, top10_dollars=top10,
    )


# ---------------------------------------------------------------------------
# Financial Flexibility Score
# ---------------------------------------------------------------------------

DEFAULT_FLEXIBILITY_WEIGHTS = {
    "cap_space": 0.30,
    "dead_cap": 0.15,
    "future_guaranteed": 0.20,
    "expiring_contracts": 0.15,
    "concentration": 0.20,
}


@dataclass(frozen=True)
class FlexibilityFactor:
    key: str
    label: str
    score: float
    weight: float
    direction: str  # "+" | "-" | "~"
    detail: str


@dataclass(frozen=True)
class FlexibilityResult:
    score: float
    factors: list[FlexibilityFactor]


def calculate_financial_flexibility(
    *,
    cap_space_pct: float,
    dead_cap_pct: float,
    future_guaranteed_pct: float,
    expiring_pct: float,
    top5_concentration_pct: float,
    weights: dict[str, float] | None = None,
) -> FlexibilityResult:
    """Financial Flexibility is deliberately distinct from cap space: it
    weighs current cap space alongside dead-cap exposure, future guaranteed
    commitments, how much cap is about to come off the books, and how
    concentrated spending is in a handful of contracts.

    All percentages are expressed as fractions of the league salary cap
    (e.g. 0.10 = 10%), except ``top5_concentration_pct`` which is a fraction
    of the team's own total commitments.
    """
    w = {**DEFAULT_FLEXIBILITY_WEIGHTS, **(weights or {})}
    total_weight = sum(w.values())
    if total_weight <= 0:
        raise ValueError("weights must sum to a positive number")

    cap_space_score = clamp(cap_space_pct / 0.15 * 100)
    dead_cap_score = clamp(100 - dead_cap_pct / 0.10 * 100)
    future_guaranteed_score = clamp(100 - future_guaranteed_pct / 0.20 * 100)
    expiring_score = clamp(expiring_pct / 0.20 * 100)
    concentration_score = clamp(100 - (top5_concentration_pct - 0.30) / 0.30 * 100)

    factors: list[FlexibilityFactor] = [
        FlexibilityFactor(
            "cap_space", "Current cap space", cap_space_score, w["cap_space"],
            "+" if cap_space_score >= 60 else "-" if cap_space_score < 40 else "~",
            f"Available cap space is {cap_space_pct * 100:.1f}% of the league cap.",
        ),
        FlexibilityFactor(
            "dead_cap", "Dead-cap exposure", dead_cap_score, w["dead_cap"],
            "+" if dead_cap_score >= 60 else "-" if dead_cap_score < 40 else "~",
            f"Dead cap is {dead_cap_pct * 100:.1f}% of the league cap.",
        ),
        FlexibilityFactor(
            "future_guaranteed", "Future guaranteed commitments", future_guaranteed_score, w["future_guaranteed"],
            "+" if future_guaranteed_score >= 60 else "-" if future_guaranteed_score < 40 else "~",
            f"Guaranteed money owed in future seasons is {future_guaranteed_pct * 100:.1f}% of the league cap.",
        ),
        FlexibilityFactor(
            "expiring_contracts", "Contracts expiring soon", expiring_score, w["expiring_contracts"],
            "+" if expiring_score >= 60 else "-" if expiring_score < 40 else "~",
            f"{expiring_pct * 100:.1f}% of current commitments are on contracts ending this season.",
        ),
        FlexibilityFactor(
            "concentration", "Cap concentration in top contracts", concentration_score, w["concentration"],
            "+" if concentration_score >= 60 else "-" if concentration_score < 40 else "~",
            f"Top-5 contracts hold {top5_concentration_pct * 100:.1f}% of total commitments.",
        ),
    ]

    weighted_sum = sum(f.score * w[f.key] for f in factors)
    score = round(weighted_sum / total_weight, 1)

    return FlexibilityResult(score=score, factors=factors)


# ---------------------------------------------------------------------------
# Contract Risk
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RiskFactor:
    label: str
    contributes_risk: bool
    detail: str


@dataclass(frozen=True)
class ContractRiskResult:
    risk_score: float
    category: str  # Low | Moderate | High | Very High
    factors: list[RiskFactor]


def calculate_contract_risk(
    *,
    age: int,
    position: str,
    years_remaining: int,
    guaranteed_pct_of_total: float,
    future_cap_hit_pct_of_cap: float,
) -> ContractRiskResult:
    """A transparent, additive risk score (0-100) built from four factors.
    Never asserts a player *will* decline — only that the model identifies
    increased financial risk from age, term length, guarantee structure, or
    future cap concentration.
    """
    if age < 0:
        raise ValueError("age cannot be negative")
    if years_remaining < 0:
        raise ValueError("years_remaining cannot be negative")

    decline_age = POSITION_DECLINE_AGE.get(position, DEFAULT_DECLINE_AGE)
    factors: list[RiskFactor] = []
    points = 0.0

    age_over = age - decline_age
    if age_over >= 0:
        age_points = clamp(20 + age_over * 8, 0, 35)
        points += age_points
        factors.append(
            RiskFactor(
                "Age relative to position", True,
                f"Player is {age_over} year(s) past the modeled decline-risk age ({decline_age}) for {position}.",
            )
        )
    else:
        factors.append(
            RiskFactor("Age relative to position", False, f"Player is below the modeled decline-risk age ({decline_age}) for {position}.")
        )

    if years_remaining >= 4:
        points += 25
        factors.append(RiskFactor("Contract length", True, f"{years_remaining} years remaining is a long-term commitment."))
    elif years_remaining >= 2:
        points += 10
        factors.append(RiskFactor("Contract length", False, f"{years_remaining} years remaining is a moderate-term commitment."))
    else:
        factors.append(RiskFactor("Contract length", False, f"Only {years_remaining} year(s) remaining limits long-term exposure."))

    if guaranteed_pct_of_total >= 0.6:
        points += 25
        factors.append(RiskFactor("Guaranteed money", True, f"{guaranteed_pct_of_total * 100:.0f}% of the contract is guaranteed."))
    elif guaranteed_pct_of_total >= 0.35:
        points += 10
        factors.append(RiskFactor("Guaranteed money", False, f"{guaranteed_pct_of_total * 100:.0f}% of the contract is guaranteed."))
    else:
        factors.append(RiskFactor("Guaranteed money", False, f"Only {guaranteed_pct_of_total * 100:.0f}% of the contract is guaranteed."))

    if future_cap_hit_pct_of_cap >= 0.12:
        points += 15
        factors.append(RiskFactor("Future cap concentration", True, f"A future cap hit reaches {future_cap_hit_pct_of_cap * 100:.1f}% of an assumed league cap."))
    else:
        factors.append(RiskFactor("Future cap concentration", False, "No future cap hit represents an outsized share of the cap."))

    risk_score = clamp(points, 0, 100)
    category = "Very High" if risk_score >= 75 else "High" if risk_score >= 50 else "Moderate" if risk_score >= 25 else "Low"

    return ContractRiskResult(risk_score=risk_score, category=category, factors=factors)


# ---------------------------------------------------------------------------
# Contract Market Comparison / Value Discrepancy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MarketComparisonResult:
    aav: float
    position: str
    position_median_aav: float
    percentile: float
    """This contract's percentile rank among same-position contracts in the
    comparison set (0-100)."""
    age_band_median_aav: float
    age_band_percentile: float
    sample_size: int
    cost_vs_position_median: float
    """aav - position_median_aav. Positive = paid above the position median."""


def calculate_market_comparison(
    aav: float,
    position: str,
    age: int,
    league_contracts: list[dict],
    age_band: int = 3,
) -> MarketComparisonResult:
    """Compares one contract's AAV to same-position (and age-band) contracts
    already in the dataset — i.e. an internal market comparison, not a claim
    about the true external market. ``league_contracts`` is a list of
    ``{"position": str, "age": int, "aav": float}`` dicts.
    """
    same_position = [c for c in league_contracts if c["position"] == position]
    if not same_position:
        raise ValueError(f"no comparison contracts found for position {position}")

    position_aavs = sorted(c["aav"] for c in same_position)
    position_median = position_aavs[len(position_aavs) // 2]
    percentile = round(sum(1 for v in position_aavs if v <= aav) / len(position_aavs) * 100, 1)

    age_band_contracts = [c for c in same_position if abs(c["age"] - age) <= age_band]
    band = age_band_contracts if age_band_contracts else same_position
    band_aavs = sorted(c["aav"] for c in band)
    band_median = band_aavs[len(band_aavs) // 2]
    band_percentile = round(sum(1 for v in band_aavs if v <= aav) / len(band_aavs) * 100, 1)

    return MarketComparisonResult(
        aav=round(aav, 2),
        position=position,
        position_median_aav=round(position_median, 2),
        percentile=percentile,
        age_band_median_aav=round(band_median, 2),
        age_band_percentile=band_percentile,
        sample_size=len(same_position),
        cost_vs_position_median=round(aav - position_median, 2),
    )


# ---------------------------------------------------------------------------
# Comparable Contract Search (Phase 5)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ComparableContract:
    contract_id: int
    player_name: str
    position: str
    age: int
    aav: float
    years_remaining: int
    guaranteed_money: float
    similarity_score: float
    """0-100; 100 = identical age and AAV to the query, within the same position."""
    age_difference: int
    aav_difference: float


def find_comparable_contracts(
    *,
    position: str,
    age: int,
    aav: float,
    candidates: list[dict],
    limit: int = 10,
    max_age_diff: int = 5,
) -> list[ComparableContract]:
    """Finds the most similar contracts to a hypothetical or real
    (position, age, aav) query, restricted to the same position. Similarity
    is a simple, transparent inverse-distance score over normalized age and
    AAV gaps — not a machine-learned similarity metric.

    ``candidates`` items: {"contract_id", "player_name", "position", "age",
    "aav", "years_remaining", "guaranteed_money"}.
    """
    same_position = [c for c in candidates if c["position"] == position and abs(c["age"] - age) <= max_age_diff]
    if not same_position:
        return []

    max_aav = max(c["aav"] for c in same_position) or 1.0

    scored: list[ComparableContract] = []
    for c in same_position:
        age_diff = abs(c["age"] - age)
        aav_diff = abs(c["aav"] - aav)
        # Normalize each gap to 0-1 and combine; age weighted less than AAV.
        age_component = min(1.0, age_diff / max(max_age_diff, 1))
        aav_component = min(1.0, aav_diff / max_aav)
        distance = 0.35 * age_component + 0.65 * aav_component
        similarity = round(clamp((1 - distance) * 100), 1)
        scored.append(
            ComparableContract(
                contract_id=c["contract_id"], player_name=c["player_name"], position=c["position"],
                age=c["age"], aav=c["aav"], years_remaining=c["years_remaining"],
                guaranteed_money=c["guaranteed_money"], similarity_score=similarity,
                age_difference=c["age"] - age, aav_difference=round(c["aav"] - aav, 2),
            )
        )

    scored.sort(key=lambda c: c.similarity_score, reverse=True)
    return scored[:limit]
