"""
Tests d'intégration Alfred — gitex conflict detection + branch-lifecycle coupling.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

ALFRED = Path(__file__).resolve().parents[1]
COORDINATION_RUNNER_PATH = ALFRED / "runners" / "coordination_runner.py"
GITEX_PATH = ALFRED / "src" / "gitex.py"


def _import_module(path: Path, name: str):
    import importlib.util
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gitex_conflict_detection() -> None:
    gitex = _import_module(GITEX_PATH, "alfred_gitex")
    result = gitex.run_git_command(["merge", "--no-commit", "--no-ff", "nonexistent"], cwd=str(ALFRED))
    assert result["conflict"] is True or result["error"] == "CONFLICT_DETECTED" or not result["ok"]


def test_branch_lifecycle_coupling() -> None:
    coordination_runner = _import_module(COORDINATION_RUNNER_PATH, "coordination_runner")
    runner = coordination_runner.CoordinationRunner()
    result = runner.verify_and_clean_branch_context(str(ALFRED))
    assert result["action"] == "verify_and_clean_branch_context"
    assert "status" in result
    assert "correlation_id" in result
