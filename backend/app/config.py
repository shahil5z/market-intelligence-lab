"""Settings from environment variables. Paths are relative to the backend folder, so the same code runs
locally and on Vercel (where only backend/ is deployed)."""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = Path(os.getenv("MIL_ARTIFACTS_DIR", BACKEND_DIR / "artifacts"))
DB_PATH = Path(os.getenv("MIL_DB_PATH", ARTIFACTS_DIR / "mil.duckdb"))
MODELS_DIR = ARTIFACTS_DIR  # JSON results written by the pipeline
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def allowed_origins() -> list[str]:
    """Explicit CORS allow-list: FRONTEND_URL (production site) + FRONTEND_ORIGINS (comma list, dev default)."""
    raw = [os.getenv("FRONTEND_URL", ""), *os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")]
    origins = [o.strip().rstrip("/") for o in raw if o.strip()]
    if "*" in origins:
        raise RuntimeError("Wildcard CORS origin is not allowed; list explicit origins in FRONTEND_URL / FRONTEND_ORIGINS")
    return list(dict.fromkeys(origins))


FRONTEND_ORIGINS = allowed_origins()
