"""Identifies analytical decision points on a contract's timeline.

These are ANALYTICAL FLAGS, not predictions of what a team will do. Every
label follows the project rule of never asserting team intent.
"""
from __future__ import annotations

from app.services.cap_engine import ContractYearInput, calculate_dead_cap

LARGE_CAP_HIT_THRESHOLD_PCT = 0.12  # cap hit exceeding 12% of an assumed $270M cap
_ASSUMED_CAP_FOR_THRESHOLD = 270_000_000.0


def identify_decision_points(
    contract_start: int,
    contract_end: int,
    years: list[ContractYearInput],
) -> list[dict]:
    points: list[dict] = []

    points.append(
        {
            "season": contract_end + 1,
            "kind": "expiration",
            "label": "Contract expires",
            "detail": f"Player is scheduled to become a free agent for the {contract_end + 1} season "
            "unless extended before then.",
        }
    )

    if contract_end >= contract_start:
        points.append(
            {
                "season": contract_end,
                "kind": "potential_extension_window",
                "label": "Possible extension window",
                "detail": "Final contract year — organizations commonly evaluate an extension around "
                "this point, though this is not a prediction of team intent.",
            }
        )

    for cy in years:
        if cy.cap_hit >= LARGE_CAP_HIT_THRESHOLD_PCT * _ASSUMED_CAP_FOR_THRESHOLD:
            points.append(
                {
                    "season": cy.season,
                    "kind": "large_cap_hit",
                    "label": "Large cap-hit year",
                    "detail": f"Cap hit of ${cy.cap_hit:,.0f} represents a significant share of a "
                    "typical team's cap in this season.",
                }
            )

    for cy in years:
        if cy.season == contract_end:
            continue  # releasing in the final year is just "let the contract expire"
        dead_cap = calculate_dead_cap(years, release_season=cy.season, june1=False)
        if dead_cap.current_year_cap_savings > 0:
            points.append(
                {
                    "season": cy.season,
                    "kind": "potential_release",
                    "label": "Potential release decision point",
                    "detail": f"A standard release before {cy.season} would create an estimated "
                    f"${dead_cap.current_year_cap_savings:,.0f} in current-year cap savings "
                    f"(model estimate, not a recommendation).",
                }
            )

    return sorted(points, key=lambda p: (p["season"], p["kind"]))
