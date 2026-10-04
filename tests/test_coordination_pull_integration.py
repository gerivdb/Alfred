"""
Tests d'intégration Alfred — coordination pull integration.
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


def test_coordinated_pull_invalid_remote() -> None:
    coordination_runner = _import_module(COORDINATION_RUNNER_PATH, "coordination_runner")
    runner = coordination_runner.CoordinationRunner()
    result = runner.coordinated_pull_and_resolve(remote="invalid_remote_dummy", branch="main", repo_path=str(ALFRED))
    assert result["action"] == "coordinated_pull_and_resolve"
    assert result["pull_status"] in ("failed", "blocked")
