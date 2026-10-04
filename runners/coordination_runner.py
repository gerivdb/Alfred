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
