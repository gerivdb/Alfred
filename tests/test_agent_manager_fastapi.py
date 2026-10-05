"""
Tests d'intégration FastAPI — endpoints Alfred.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ALFRED = Path(__file__).resolve().parents[1]
FASTAPI_PATH = ALFRED / "runners" / "agent_manager_fastapi.py"


def _import_app():
    if str(ALFRED) not in sys.path:
        sys.path.insert(0, str(ALFRED))
    spec = importlib.util.spec_from_file_location("Alfred.runners.agent_manager_fastapi", FASTAPI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


client = TestClient(_import_app())


def test_alfred_health_endpoint() -> None:
    response = client.get("/alfred/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["agent"] == "Alfred"


def test_alfred_wal_status_endpoint() -> None:
    response = client.get("/alfred/wal-status")
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "wal_status"
    assert "wal_path" in body


def test_alfred_audit_endpoint() -> None:
    response = client.get("/alfred/audit")
    assert response.status_code == 200
    body = response.json()
    assert body["agent"] == "Alfred"
    assert "overall" in body
    assert "governance_hub" in body
    assert "topos" in body
    assert "brain" in body
    assert "ctulu" in body
    assert "kg_l" in body
    assert body["intent_hash"] == "0xH0_ALFRED_API_AUDIT_20261005T014800Z"


def test_alfred_vault_sync_endpoint() -> None:
    response = client.post("/alfred/vault-sync")
    assert response.status_code == 200
    body = response.json()
    assert body["coordination_action"] == "vault_sync"
    assert body["status"] == "success"
    assert "manifest" in body
    assert body["intent_hash"] == "0xH0_ALFRED_VAULT_SYNC_20261005T020300Z"
