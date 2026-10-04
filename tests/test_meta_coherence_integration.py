"""
Tests d'intégration Alfred — meta-coherence formel.
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


def test_run_meta_coherence_check_success() -> None:
    runner = _import_module(COORDINATION_RUNNER_PATH, "coordination_runner").CoordinationRunner()
    result = runner.run_meta_coherence_check(str(ALFRED))
    assert result["action"] == "run_meta_coherence_check"
    assert result["local_status"] == "success"
    assert result["missing_structures"] == []
    assert result["gate"] == "G0"


def test_run_meta_coherence_check_failure_on_missing_dirs(tmp_path: Path) -> None:
    runner = _import_module(COORDINATION_RUNNER_PATH, "coordination_runner").CoordinationRunner()
    result = runner.run_meta_coherence_check(str(tmp_path))
    assert result["local_status"] == "failed"
    assert "MOC" in result["missing_structures"]
    assert "PRD-MOC" in result["missing_structures"]
    assert "INTENTS" in result["missing_structures"]
    assert result["gate"] == "G-PERIMETER"
