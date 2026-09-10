"""Application configuration, loaded from environment variables / .env."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Cap Ledger API"
    environment: str = "development"
    debug: bool = True

    database_url: str = (
        "postgresql+psycopg2://capledger:capledger_dev_pw@localhost:5432/capledger"
    )

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Default league salary cap assumptions used when a season has no
    # explicit team_cap row and no user-supplied projection override.
    # These are ANALYTICAL ASSUMPTIONS, not official NFL figures, and are
    # surfaced to the user as such wherever they are used.
    default_league_cap_growth_rate: float = 0.06

    demo_mode: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
