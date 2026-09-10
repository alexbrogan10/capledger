import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg2://capledger:capledger_dev_pw@localhost:5432/capledger_test"
)

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.seed.seed import run as run_seed


@pytest.fixture(scope="session", autouse=True)
def seeded_database():
    get_settings.cache_clear()
    run_seed()
    yield


@pytest.fixture()
def client():
    from app.main import app

    return TestClient(app)


@pytest.fixture()
def db_session():
    from app.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
