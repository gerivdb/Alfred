"""
Tests d'intégration — Cross-Repo Audit Runner Alfred.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ALFRED = Path(__file__).resolve().parents[1]
VAULT_RUNNER_PATH = ALFRED / "runners" / "vault_sync_runner.py"
AUDIT_RUNNER_PATH = ALFRED / "runners" / "cross_repo_audit_runner.py"


def _import_module(path: Path):
    if str(ALFRED) not in sys.path:
        sys.path.insert(0, str(ALFRED))
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cross_repo_audit_reports_ok_when_manifest_valid() -> None:
    vault_module = _import_module(VAULT_RUNNER_PATH)
    vault_module.generate_alfred_manifest()

    audit_module = _import_module(AUDIT_RUNNER_PATH)
    runner = audit_module.CrossRepoAuditRunner(ALFRED)
    report = runner.audit()
    assert report["agent"] == "Alfred"
    assert report["manifest_present"] is True
    assert report["manifest_valid"] is True
    assert report["overall"] == "OK"
    assert report["modules_present"]["gitex"] is True
    assert report["modules_present"]["syncx"] is True
    assert report["endpoints_present"]["/alfred/health"] is True
    assert report["endpoints_present"]["/alfred/branches"] is True
    assert report["endpoints_present"]["/alfred/merge"] is True
