import pytest
from fastapi.testclient import TestClient

from app.db import resolve_db_path
from app.main import app


@pytest.fixture(scope="session")
def client():
    try:
        resolve_db_path()
    except FileNotFoundError:
        pytest.skip("Run `python scripts/run_pipeline.py` before the tests")
    return TestClient(app)


@pytest.fixture(autouse=True)
def no_openai(monkeypatch):
    # Tests must be deterministic and never call a paid API.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
