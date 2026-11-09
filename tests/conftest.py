import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def committed_cases():
    return [json.loads(l) for l in open(ROOT / "evals/cases/cases.jsonl")]


@pytest.fixture(scope="session")
def fresh_build(tmp_path_factory):
    """Regenerate DB + labels from scratch into a temp dir."""
    from evals.labeling.build_cases import build_all
    db = tmp_path_factory.mktemp("db") / "store.db"
    return db, build_all(db)
