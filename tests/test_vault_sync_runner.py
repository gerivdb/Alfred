"""
Tests d'intégration — Vault Sync Runner Alfred.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ALFRED = Path(__file__).resolve().parents[1]
VAULT_RUNNER_PATH = ALFRED / "runners" / "vault_sync_runner.py"


def _import_module():
    if str(ALFRED) not in sys.path:
        sys.path.insert(0, str(ALFRED))
    spec = importlib.util.spec_from_file_location("Alfred.runners.vault_sync_runner", VAULT_RUNNER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_alfred_manifest_creates_json() -> None:
    module = _import_module()
    manifest = module.generate_alfred_manifest()
    assert manifest["agent"] == "Alfred"
    assert manifest["status"] == "active_on_origin_main"
    assert "endpoints" in manifest
    assert len(manifest["endpoints"]) >= 6

    manifest_path = ALFRED / "MOC" / "ALFRED-VAULT-MANIFEST.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["agent"] == "Alfred"
    assert data["latest_commit"] == manifest["latest_commit"]
