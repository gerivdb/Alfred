"""
Tests d'intégration FastAPI — endpoints de cycle de vie des branches Alfred.
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


def test_alfred_branches_endpoint() -> None:
    response = client.get("/alfred/branches")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data or "action" in data


def test_alfred_merge_endpoint() -> None:
    response = client.post("/alfred/merge", json={"branch": "main", "strategy": "ours"})
    assert response.status_code in (200, 422)
