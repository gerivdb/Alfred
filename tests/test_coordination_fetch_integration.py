"""
Tests d'intégration Alfred — coordination fetch integration.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ALFRED = Path(__file__).resolve().parents[1]
COORDINATION_RUNNER_PATH = ALFRED / "runners" / "coordination_runner.py"


def _import_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_coordinated_fetch_invalid_remote() -> None:
    coordination_runner = _import_module(COORDINATION_RUNNER_PATH, "coordination_runner")
    runner = coordination_runner.CoordinationRunner()
    result = runner.coordinated_fetch(remote="invalid_remote_dummy", prune=True, repo_path=str(ALFRED))
    assert result["action"] == "coordinated_fetch"
    assert result["fetch_status"] in ("failed", "blocked")
    assert result["success"] is False
