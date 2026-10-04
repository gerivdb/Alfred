"""
Alfred Agent Manager FastAPI.
Expose les capacités de coordination et de synchronisation d'Alfred via HTTP.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, Query
from pydantic import BaseModel

_ALFRED_REPO = Path(__file__).resolve().parents[1]
if str(_ALFRED_REPO) not in sys.path:
    sys.path.insert(0, str(_ALFRED_REPO))
if str(_ALFRED_REPO.parent) not in sys.path:
    sys.path.insert(0, str(_ALFRED_REPO.parent))

from Alfred.runners.coordination_runner import CoordinationRunner
from Alfred.src.gitex import resolve_conflict_strategy, run_git_command
from Alfred.src.syncx import robust_sync_push

app = FastAPI(
    title="Alfred Agent Manager API",
    description="API de coordination et d'automatisation Git/Sync pour l'agent Alfred sur ENV2",
    version="1.1.0",
)

runner = CoordinationRunner()


class PullRequest(BaseModel):
    remote: str = "origin"
    branch: str = "main"
    strategy: str = "ours"


class PushRequest(BaseModel):
    remote: str = "origin"
    branch: str = "main"
    retries: int = 3


@app.get("/alfred/health")
def api_health() -> Dict[str, Any]:
    """Vérifie l'intégrité de l'agent Alfred."""
    return {"status": "healthy", "agent": "Alfred", "environment": "ENV2"}


@app.get("/alfred/check")
def api_check() -> Dict[str, Any]:
    """Évaluation rapide de la posture du dépôt local."""
    ctx = runner.verify_and_clean_branch_context(".")
    return {"check": "posture", "result": ctx}


@app.post("/alfred/fetch")
def api_fetch(remote: str = Query("origin"), prune: bool = Query(True)) -> Dict[str, Any]:
    """Exécute un fetch robuste via le coordinateur."""
    return runner.coordinated_fetch(remote=remote, prune=prune)


@app.post("/alfred/pull")
def api_pull(payload: PullRequest) -> Dict[str, Any]:
    """Exécute un pull robuste avec résolution automatique de conflit."""
    return runner.coordinated_pull_and_resolve(
        remote=payload.remote,
        branch=payload.branch,
        conflict_strategy=payload.strategy,
    )


@app.post("/alfred/push")
def api_push(payload: PushRequest) -> Dict[str, Any]:
    """Exécute un push robuste avec retry et gestion des états bloqués."""
    result = robust_sync_push(
        remote=payload.remote,
        branch=payload.branch,
        retries=payload.retries,
    )
    return {"coordination_action": "push_only", "push_status": result.get("status"), "details": result}


@app.get("/alfred/wal-status")
def api_wal_status() -> Dict[str, Any]:
    """Statut du WAL (Write-Ahead Logging) d'Alfred."""
    return runner.wal_status()


@app.get("/alfred/branches")
def api_branches() -> Dict[str, Any]:
    """Analyse et classifie l'état des branches via le runner de cycle de vie."""
    return runner.run_branch_lifecycle(".")


@app.post("/alfred/merge")
def api_merge(branch: str = Query(...), strategy: str = Query("ours")) -> Dict[str, Any]:
    """Exécute un merge sécurisé avec gestion de stratégie de conflit."""
    merge_res = run_git_command(["merge", "--no-commit", "--no-ff", branch], cwd=".")
    if merge_res.get("conflict", False) or not merge_res["ok"]:
        resolution = resolve_conflict_strategy(strategy, path=".", cwd=".")
        return {
            "status": "resolved_with_strategy" if resolution["ok"] else "conflict_failed",
            "strategy": strategy,
            "merge_result": merge_res,
            "resolution_result": resolution,
        }
    return {"status": "success", "merge_result": merge_res}
