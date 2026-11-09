"""Load configuration files. Model name and API key come from the environment only."""
from __future__ import annotations

import tomllib
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "synthetic" / "store.db"


@lru_cache(maxsize=None)
def decision_config() -> dict:
    with open(CONFIG_DIR / "decision.toml", "rb") as f:
        return tomllib.load(f)
