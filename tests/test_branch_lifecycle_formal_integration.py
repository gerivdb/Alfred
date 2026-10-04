"""
Tests d'intégration Alfred — branch-lifecycle formel + contrôles G0/G-PERIMETER.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest import mock

import pytest

ALFRED = Path(__file__).resolve().parents[1]
COORDINATION_RUNNER_PATH = ALFRED / "runners" / "coordination_runner.py"
GITEX_MODULE_NAME = "Alfred.src.gitex"


def _import_coordination_runner_with_mock(git_mock):
    if GITEX_MODULE_NAME in sys.modules:
        del sys.modules[GITEX_MODULE_NAME]
    sys.modules[GITEX_MODULE_NAME] = git_mock
    spec = importlib.util.spec_from_file_location("coordination_runner", COORDINATION_RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_run_branch_lifecycle_returns_recommendations() -> None:
    coordination_runner = importlib.util.spec_from_file_location(
        "coordination_runner", COORDINATION_RUNNER_PATH
    )
    module = importlib.util.module_from_spec(coordination_runner)
    coordination_runner.loader.exec_module(module)
    runner = module.CoordinationRunner()
    result = runner.run_branch_lifecycle(str(ALFRED), default_branch="main")
    assert result["action"] == "run_branch_lifecycle"
    assert "recommendations" in result
    assert result["gate"] == "G0"
    assert "correlation_id" in result


def test_run_branch_lifecycle_blocks_on_dirty_worktree() -> None:
    gitex_mock = mock.MagicMock()
    gitex_mock.run_git_command.side_effect = lambda args, cwd=None: {
        "ok": False,
        "error": "dirty",
        "stdout": "",
        "stderr": "dirty",
        "conflict": False,
    }
    module = _import_coordination_runner_with_mock(gitex_mock)
    runner = module.CoordinationRunner()
    result = runner.run_branch_lifecycle(str(ALFRED), default_branch="main")
    assert result["status"] == "blocked"
    assert result["gate"] == "G-PERIMETER"
