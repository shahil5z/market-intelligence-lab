"""Load JSON artifacts written by the pipeline (models/*.json)."""

import json
from functools import cache

from app.config import MODELS_DIR


class ArtifactMissing(RuntimeError):
    pass


@cache
def load(name: str) -> dict:
    path = MODELS_DIR / f"{name}.json"
    if not path.exists():
        raise ArtifactMissing(f"{path.name} not found - run `python scripts/run_pipeline.py` first")
    return json.loads(path.read_text())
