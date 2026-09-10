from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import contracts, players, teams
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description=(
        "Cap Ledger — an independent, portfolio salary-cap and contract analytics platform for "
        "NFL front offices. DEMO DATA — NOT OFFICIAL NFL DATA. All figures returned by this API in "
        "demo mode are synthetically generated and do not represent real players, teams, or "
        "contracts. Cap Ledger is not affiliated with the NFL or any NFL team."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(teams.router)
app.include_router(players.router)
app.include_router(contracts.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "demo_mode": settings.demo_mode}


@app.get("/api/meta")
def meta():
    from app.seed.demo_data import CURRENT_SEASON, PROJECTION_SEASONS

    return {
        "demo_mode": settings.demo_mode,
        "demo_disclaimer": "DEMO DATA — NOT OFFICIAL NFL DATA. All players and contract figures are "
        "synthetically generated for demonstration purposes.",
        "current_season": CURRENT_SEASON,
        "projection_seasons": PROJECTION_SEASONS,
    }
