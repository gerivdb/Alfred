"""
Tests d'intégration Alfred — gestion fine des conflits gitex.
"""
from __future__ import annotations

from pathlib import Path

import pytest

ALFRED = Path(__file__).resolve().parents[1]
GITEX_PATH = ALFRED / "src" / "gitex.py"


def _import_module(path: Path, name: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_resolve_conflict_invalid_strategy() -> None:
    gitex = _import_module(GITEX_PATH, "alfred_gitex")
    result = gitex.resolve_conflict_strategy("invalid_strat", cwd=str(ALFRED))
    assert result["ok"] is False
    assert result["error"] == "INVALID_CONFLICT_STRATEGY"


def test_resolve_conflict_ours_and_theirs_are_valid_strategies() -> None:
    gitex = _import_module(GITEX_PATH, "alfred_gitex")
    for strategy in ("ours", "theirs"):
        result = gitex.resolve_conflict_strategy(strategy, cwd=str(ALFRED))
        assert "error" != "INVALID_CONFLICT_STRATEGY"
