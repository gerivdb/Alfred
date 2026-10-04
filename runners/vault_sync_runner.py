"""
Alfred Vault Sync Runner.
Génère un manifeste topologique exportable pour synchronisation NotebookLM.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def generate_alfred_manifest() -> dict:
    """Génère le manifeste topologique d'Alfred pour synchronisation NotebookLM."""
    manifest = {
        "agent": "Alfred",
        "version": "1.1.0",
        "environment": "ENV2",
        "status": "active_on_origin_main",
        "latest_commit": "c8719400e29d9a9312e969abcb2cb7628b06feda",
        "manifest_generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capabilities": [
            "gitex_real_ops_and_conflicts",
            "syncx_robust_push_pull_fetch",
            "fastapi_agent_manager",
            "branch_lifecycle_gates",
        ],
        "endpoints": [
            "/alfred/health",
            "/alfred/check",
            "/alfred/fetch",
            "/alfred/pull",
            "/alfred/push",
            "/alfred/branches",
            "/alfred/merge",
            "/alfred/wal-status",
        ],
        "modules": {
            "gitex": "Alfred/src/gitex.py",
            "syncx": "Alfred/src/syncx.py",
            "coordination_runner": "Alfred/runners/coordination_runner.py",
            "agent_manager_fastapi": "Alfred/runners/agent_manager_fastapi.py",
        },
    }

    moc_dir = Path(__file__).resolve().parents[1] / "MOC"
    moc_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = moc_dir / "ALFRED-VAULT-MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    res = generate_alfred_manifest()
    print(f"[ALFRED-VAULT] Manifest generated successfully: {res['latest_commit']}")
