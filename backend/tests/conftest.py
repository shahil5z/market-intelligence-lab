import pytest
from fastapi.testclient import TestClient

from app.config import DB_PATH
from app.main import app


@pytest.fixture(scope="session")
def client():
    if not DB_PATH.exists():
        pytest.skip("Run `python scripts/run_pipeline.py` before the tests")
    return TestClient(app)


@pytest.fixture(autouse=True)
def no_openai(monkeypatch):
    # Tests must be deterministic and never call a paid API.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
