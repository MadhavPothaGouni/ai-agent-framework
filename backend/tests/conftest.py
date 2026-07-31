import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import pytest
from fastapi.testclient import TestClient

from app.db.session import Base, SessionLocal, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def db_session():
    """A raw DB session for tests that talk to the memory/DB layer directly."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()