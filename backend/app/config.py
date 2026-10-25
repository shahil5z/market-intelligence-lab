"""Paths and settings. Everything is relative to the repository root so the project is portable."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("MIL_DB_PATH", ROOT / "data" / "processed" / "mil.duckdb"))
MODELS_DIR = ROOT / "models"
FRONTEND_ORIGINS = os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
