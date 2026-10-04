"""
Tests d'intégration FastAPI — endpoints Alfred.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ALFRED = Path(__file__).resolve().parents[1]
FASTAPI_MODULE = "Alfred.runners.agent_manager_fastapi"


def _import_app():
    if str(ALFRED) not in sys.path:
        sys.path.insert(0, str(ALFRED))
    importlib.import_module("Alfred")
    module = importlib.import_module(FASTAPI_MODULE)
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
