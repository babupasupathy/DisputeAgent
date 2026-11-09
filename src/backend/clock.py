"""Simulation clock. Eval runs are pinned to the dataset's as_of time so deadlines are
deterministic. Override with SIM_NOW=2026-10-15T12:00:00Z if needed."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from src.backend.generator import AS_OF


def now() -> datetime:
    v = os.environ.get("SIM_NOW")
    if v:
        return datetime.strptime(v, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return AS_OF
