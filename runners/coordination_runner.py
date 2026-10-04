"""
Alfred — Coordination Runner
Exécutant natif de coordination de branches, dispatch de tâches et vérification
de méta-coherence, utilisable comme runner indépendant ou depuis Agent Manager.
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_ALFRED_REPO = Path(__file__).resolve().parents[1]
for _candidate in (_ALFRED_REPO, _ALFRED_REPO.parent):
    _str = str(_candidate)
    if _str not in sys.path:
        sys.path.insert(0, _str)

from Alfred.src.coordination import AlfredCoordinator, CoordinationState
from Alfred.src.meta_coherence import MetaCoherenceChecker
from Alfred.src.wal_writer import WALWriter
from Alfred.src.gitex import run_git_command


class CoordinationRunner:
    """Runner de coordination Alfred."""

    runner_id = "alfred-coordination"
    runner_name = "ALFRED-COORDINATION"
    version = "1.0.0"
    strate = "L0-CANON"
    runner_type = "orchestrator"
    status = "active"

    def __init__(self, wal_path: Optional[Path] = None) -> None:
        self.coordinator = AlfredCoordinator()
        self.checker = MetaCoherenceChecker()
        self.wal = WALWriter(wal_path)

    def coordinate_branches(self, repo: str) -> Dict[str, Any]:
        """Coordonne le cycle de vie des branches pour un repo."""
        correlation_id = uuid.uuid4().hex[:8]
        self.wal.append("coordinate_branches", repo=repo, correlation_id=correlation_id)
        tasks = self.coordinator.coordinate_branches(repo)
        return {
            "runner": self.runner_name,
            "action": "coordinate_branches",
            "repo": repo,
            "correlation_id": correlation_id,
            "task_count": len(tasks),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def dispatch_tasks(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Dispatch des tâches atomiques vers les citoyens."""
        correlation_id = uuid.uuid4().hex[:8]
        self.wal.append("dispatch_tasks", task_count=len(tasks), correlation_id=correlation_id)
        self.coordinator.dispatch_tasks([])
        return {
            "runner": self.runner_name,
            "action": "dispatch_tasks",
            "task_count": len(tasks),
            "correlation_id": correlation_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def verify_meta_coherence(self, repos: List[str]) -> Dict[str, Any]:
        """Vérifie la méta-coherence cross-repo."""
        correlation_id = uuid.uuid4().hex[:8]
        self.wal.append(
            "verify_meta_coherence",
            repo_count=len(repos),
            correlation_id=correlation_id,
        )
        reports = self.checker.check_repos(repos)
        return {
            "runner": self.runner_name,
            "action": "verify_meta_coherence",
            "repos": repos,
            "correlation_id": correlation_id,
            "results": [report.to_dict() for report in reports],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def run_meta_coherence_check(self, repo: str) -> Dict[str, Any]:
        """Vérifie la méta-coherence locale et cross-repo avant mutation critique."""
        correlation_id = uuid.uuid4().hex[:8]
        self.wal.append(
            "run_meta_coherence_check",
            repo=repo,
            correlation_id=correlation_id,
        )
        required_dirs = ["MOC", "PRD-MOC", "INTENTS"]
        missing_structures = [d for d in required_dirs if not Path(repo, d).is_dir()]
        local_status = "success" if not missing_structures else "failed"
        cross_repo = self.checker.check_repos([repo])
        cross_results = [report.to_dict() for report in cross_repo]
        overall_ok = local_status == "success" and all(r.get("is_coherent") for r in cross_results)
        return {
            "runner": self.runner_name,
            "action": "run_meta_coherence_check",
            "repo": repo,
            "correlation_id": correlation_id,
            "status": "success" if overall_ok else "failed",
            "gate": "G0" if overall_ok else "G-PERIMETER",
            "local_status": local_status,
            "missing_structures": missing_structures,
            "cross_repo_results": cross_results,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def wal_status(self) -> Dict[str, Any]:
        """Retourne le statut WAL."""
        return {
            "runner": self.runner_name,
            "action": "wal_status",
            "wal_path": str(self.wal.wal_path),
            "entry_count": self.wal.count(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def verify_and_clean_branch_context(self, repo: str) -> Dict[str, Any]:
        """Vérifie l'état de la branche avant mutation et nettoie les worktrees orphelins."""
        correlation_id = uuid.uuid4().hex[:8]
        self.wal.append(
            "verify_and_clean_branch_context",
            repo=repo,
            correlation_id=correlation_id,
        )
        status = run_git_command(["status", "--short"], cwd=repo)
        if not status["ok"]:
            return {
                "runner": self.runner_name,
                "action": "verify_and_clean_branch_context",
                "repo": repo,
                "correlation_id": correlation_id,
                "status": "blocked",
                "reason": status.get("error") or status.get("stderr") or "Dirty worktree or git error",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        prune_res = run_git_command(["worktree", "prune"], cwd=repo)
        return {
            "runner": self.runner_name,
            "action": "verify_and_clean_branch_context",
            "repo": repo,
            "correlation_id": correlation_id,
            "status": "success",
            "worktree_pruned": prune_res["ok"],
            "details": status.get("stdout", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def run_branch_lifecycle(self, repo: str, default_branch: str = "main") -> Dict[str, Any]:
        """Intègre le skill branch-lifecycle : analyse, classification et préconisations avant mutation."""
        correlation_id = uuid.uuid4().hex[:8]
        self.wal.append(
            "run_branch_lifecycle",
            repo=repo,
            default_branch=default_branch,
            correlation_id=correlation_id,
        )
        context_check = self.verify_and_clean_branch_context(repo)
        if context_check.get("status") == "blocked":
            return {
                "runner": self.runner_name,
                "action": "run_branch_lifecycle",
                "repo": repo,
                "correlation_id": correlation_id,
                "status": "blocked",
                "reason": context_check.get("reason"),
                "gate": "G-PERIMETER",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        branches_res = run_git_command(["branch", "--list"], cwd=repo)
        branches = [b.strip("* ") for b in (branches_res.get("stdout") or "").splitlines() if b.strip()]
        recommendations = []
        for branch in branches:
            if branch == default_branch:
                continue
            ahead = run_git_command(["log", "--oneline", f"{default_branch}..{branch}"], cwd=repo)
            behind = run_git_command(["log", "--oneline", f"{branch}..{default_branch}"], cwd=repo)
            ahead_count = len((ahead.get("stdout") or "").splitlines())
            behind_count = len((behind.get("stdout") or "").splitlines())
            if ahead_count == 0:
                recommendation = "DELETE"
            elif behind_count == 0 and ahead_count > 0:
                recommendation = "PR_MERGE"
            else:
                recommendation = "CHERRY_PICK"
            recommendations.append({
                "branch": branch,
                "ahead": ahead_count,
                "behind": behind_count,
                "recommendation": recommendation,
            })
        return {
            "runner": self.runner_name,
            "action": "run_branch_lifecycle",
            "repo": repo,
            "correlation_id": correlation_id,
            "status": "success",
            "gate": "G0",
            "default_branch": default_branch,
            "branch_count": len(recommendations),
            "recommendations": recommendations,
            "worktree_pruned": context_check.get("worktree_pruned"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def coordinated_pull_and_resolve(
        self,
        remote: str = "origin",
        branch: str = "main",
        conflict_strategy: str = "ours",
        repo_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Exécute un pull robuste et applique une stratégie de résolution si conflit."""
        from Alfred.src.syncx import robust_sync_pull
        from Alfred.src.gitex import resolve_conflict_strategy

        correlation_id = uuid.uuid4().hex[:8]
        self.wal.append(
            "coordinated_pull_and_resolve",
            remote=remote,
            branch=branch,
            conflict_strategy=conflict_strategy,
            repo=repo_path,
            correlation_id=correlation_id,
        )
        pull_res = robust_sync_pull(remote=remote, branch=branch, cwd=repo_path)
        if pull_res.get("status") == "conflict":
            resolution = resolve_conflict_strategy(conflict_strategy, path=".", cwd=repo_path)
            return {
                "runner": self.runner_name,
                "action": "coordinated_pull_and_resolve",
                "repo": repo_path,
                "correlation_id": correlation_id,
                "coordination_action": "pull_and_resolve",
                "pull_status": "conflict",
                "resolved": resolution.get("ok", False),
                "resolution_details": resolution,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return {
            "runner": self.runner_name,
            "action": "coordinated_pull_and_resolve",
            "repo": repo_path,
            "correlation_id": correlation_id,
            "coordination_action": "pull_only",
            "pull_status": pull_res.get("status"),
            "resolved": True,
            "details": pull_res,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def coordinated_fetch(
        self,
        remote: str = "origin",
        prune: bool = True,
        repo_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Exécute un fetch robuste et retourne un statut de coordination structuré."""
        from Alfred.src.syncx import robust_sync_fetch

        correlation_id = uuid.uuid4().hex[:8]
        self.wal.append(
            "coordinated_fetch",
            remote=remote,
            prune=prune,
            repo=repo_path,
            correlation_id=correlation_id,
        )
        fetch_res = robust_sync_fetch(remote=remote, prune=prune, cwd=repo_path)
        return {
            "runner": self.runner_name,
            "action": "coordinated_fetch",
            "repo": repo_path,
            "correlation_id": correlation_id,
            "coordination_action": "fetch_only",
            "fetch_status": fetch_res.get("status"),
            "success": fetch_res.get("status") == "success",
            "details": fetch_res,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
