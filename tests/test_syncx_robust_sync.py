"""
Tests d'intégration Alfred — syncx robust synchronization.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ALFRED = Path(__file__).resolve().parents[1]
SYNCX_PATH = ALFRED / "src" / "syncx.py"


def _import_module(path: Path, name: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_robust_sync_push_invalid_remote() -> None:
    syncx = _import_module(SYNCX_PATH, "alfred_syncx")
    result = syncx.robust_sync_push(remote="invalid_remote_dummy_target", branch="main", retries=1, delay=0, cwd=str(ALFRED))
    assert result["status"] in ("failed", "blocked")
    assert result["attempt"] >= 1
