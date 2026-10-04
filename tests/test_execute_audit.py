"""
Tests d'intégration — Execute Audit Runner Alfred.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ALFRED = Path(__file__).resolve().parents[1]
EXECUTE_AUDIT_PATH = ALFRED / "runners" / "execute_audit.py"


def _import_execute_audit():
    if str(ALFRED) not in sys.path:
        sys.path.insert(0, str(ALFRED))
    spec = importlib.util.spec_from_file_location("Alfred.runners.execute_audit", EXECUTE_AUDIT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_execute_audit_runs_successfully() -> None:
    module = _import_execute_audit()
    report = module.run_ecosystem_audit()
    assert report["overall"] == "OK"
    assert report["manifest_present"] is True
    assert report["governance_hub"]["status"] == "OK"
    assert report["topos"]["status"] == "OK"
    assert "executed_at_utc" in report
