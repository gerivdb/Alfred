"""
Alfred — Operational Coordination Assistant
Core coordination module for gerivdb ecosystem.
"""

from __future__ import annotations

import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional

try:
    from .wal_writer import WALWriter
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from wal_writer import WALWriter


class CoordinationState(str, Enum):
    IDLE = "IDLE"
    COORDINATION = "COORDINATION"
    EXECUTION = "EXECUTION"
    VERIFICATION = "VERIFICATION"


@dataclass
class CoordinationTask:
    """Atomic coordination task."""

    task_id: str
    repo: str
    action: str
    payload: dict
    created_at: datetime
    state: CoordinationState = CoordinationState.IDLE


class AlfredCoordinator:
    """Main coordinator for ALFRED citizen."""

    def __init__(self, wal_path: Optional[Path] = None) -> None:
        self.wal = WALWriter(wal_path)
        self.current_state: CoordinationState = CoordinationState.IDLE

    def _run_git(self, repo: str, args: List[str]) -> dict:
        """Exécute une commande git dans le repo donné."""
        repo_path = Path(repo)
        if not repo_path.exists() or not (repo_path / ".git").exists():
            return {"ok": False, "stdout": "", "stderr": "", "error": f"Invalid git repo: {repo}"}
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            return {
                "ok": result.returncode == 0,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            }
        except Exception as exc:
            return {"ok": False, "stdout": "", "stderr": str(exc), "error": "EXECUTION_EXCEPTION"}

    def coordinate_branches(self, repo: str) -> List[CoordinationTask]:
        """Coordinate branch lifecycle for a repo.

        Returns a list of CoordinationTask with real branch recommendations:
        - DELETE if branch has no commits ahead of default branch
        - PR_MERGE if branch is ahead of default and default is not ahead of branch
        - CHERRY_PICK otherwise
        """
        tasks: List[CoordinationTask] = []
        self._append_wal("COORDINATE_BRANCHES", repo=repo)

        repo_path = Path(repo)
        if not repo_path.exists() or not (repo_path / ".git").exists():
            self._append_wal("COORDINATE_BRANCHES_ERROR", repo=repo, error="not a git repo")
            return tasks

        # Détecter la branche par défaut (main ou master)
        default_branch = "main"
        branches_res = self._run_git(repo, ["branch", "--list"])
        if branches_res["ok"]:
            branch_lines = [b.strip("* ") for b in branches_res["stdout"].splitlines() if b.strip()]
            if "master" in branch_lines and "main" not in branch_lines:
                default_branch = "master"

        # Lister les branches autres que la défaut
        if branches_res["ok"]:
            for branch in branch_lines:
                if branch == default_branch:
                    continue
                ahead = self._run_git(repo, ["log", "--oneline", f"{default_branch}..{branch}"])
                behind = self._run_git(repo, ["log", "--oneline", f"{branch}..{default_branch}"])
                ahead_count = len([l for l in (ahead.get("stdout") or "").splitlines() if l.strip()])
                behind_count = len([l for l in (behind.get("stdout") or "").splitlines() if l.strip()])

                if ahead_count == 0:
                    recommendation = "DELETE"
                elif behind_count == 0 and ahead_count > 0:
                    recommendation = "PR_MERGE"
                else:
                    recommendation = "CHERRY_PICK"

                tasks.append(CoordinationTask(
                    task_id=uuid.uuid4().hex[:8],
                    repo=repo,
                    action="branch_recommendation",
                    payload={
                        "branch_name": branch,
                        "recommendation": recommendation,
                        "ahead_count": ahead_count,
                        "behind_count": behind_count,
                    },
                    created_at=datetime.now(timezone.utc),
                ))

        return tasks

    def verify_meta_coherence(self, repos: List[str]) -> bool:
        """Verify meta-coherence across repos.

        Returns True only if every repo passes structural checks:
        README.md, .gitignore, remote configured, main/master branch exists.
        """
        all_coherent = True
        for repo in repos:
            issues = self._check_repo_coherence(repo)
            if issues:
                all_coherent = False
            self._append_wal("VERIFY_META_COHERENCE_REPO", repo=repo, issues=issues)
        self._append_wal("VERIFY_META_COHERENCE", repos=repos, coherent=all_coherent)
        return all_coherent

    def _check_repo_coherence(self, repo: str) -> List[str]:
        """Check a single repo for structural coherence."""
        issues: List[str] = []
        repo_path = Path(repo)

        if not repo_path.exists():
            return [f"Repo path does not exist: {repo}"]

        # Check README.md
        if not (repo_path / "README.md").exists():
            issues.append("missing README.md")

        # Check .gitignore
        if not (repo_path / ".gitignore").exists():
            issues.append("missing .gitignore")

        # Check remote
        remote_res = self._run_git(repo, ["remote", "-v"])
        if not remote_res["ok"] or not remote_res.get("stdout"):
            issues.append("no remote configured")

        # Check default branch
        branch_res = self._run_git(repo, ["branch", "--list"])
        if branch_res["ok"]:
            branches = [b.strip("* ") for b in branch_res["stdout"].splitlines() if b.strip()]
            if "main" not in branches and "master" not in branches:
                issues.append("no main/master branch")

        return issues

    def dispatch_tasks(self, tasks: List[CoordinationTask]) -> None:
        """Dispatch atomic tasks to citizens."""
        self._append_wal("DISPATCH_TASKS", count=len(tasks))
        for task in tasks:
            task.state = CoordinationState.COORDINATION

    def _append_wal(self, action: str, **kwargs: object) -> None:
        """Append entry to WAL (persisted on disk via WALWriter)."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "state": self.current_state.value,
            **kwargs,
        }
        self.wal.append(action, **kwargs)


def run_self_test() -> bool:
    """Self-test: create a fake git repo, call coordinate_branches(), verify results and WAL persistence."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir) / "fake_repo"
        repo_path.mkdir(parents=True)

        # Init git repo
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_path, capture_output=True)

        # Create a file and commit on main
        (repo_path / "README.md").write_text("# Test\n")
        subprocess.run(["git", "add", "README.md"], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo_path, capture_output=True)

        # Create a feature branch and commit
        subprocess.run(["git", "checkout", "-b", "feature/test"], cwd=repo_path, capture_output=True)
        (repo_path / "feature.py").write_text("print('feature')\n")
        subprocess.run(["git", "add", "feature.py"], cwd=repo_path, capture_output=True)
        subprocess.run(["git", "commit", "-m", "feature"], cwd=repo_path, capture_output=True)

        # Return to main
        subprocess.run(["git", "checkout", "main"], cwd=repo_path, capture_output=True)

        # Run coordinator with explicit WAL path
        wal_path = Path(tmpdir) / ".swarm" / "wal.jsonl"
        coordinator = AlfredCoordinator(wal_path=wal_path)
        tasks = coordinator.coordinate_branches(str(repo_path))

        # Verify: 1 feature branch, ahead of main by 1 commit → PR_MERGE
        if len(tasks) != 1:
            print(f"[SELF-TEST] FAIL: expected 1 task, got {len(tasks)}")
            return False

        task = tasks[0]
        if task.payload.get("recommendation") != "PR_MERGE":
            print(f"[SELF-TEST] FAIL: expected PR_MERGE, got {task.payload.get('recommendation')}")
            return False

        if task.payload.get("ahead_count", 0) < 1:
            print(f"[SELF-TEST] FAIL: expected ahead_count >= 1, got {task.payload.get('ahead_count')}")
            return False

        # Verify WAL persistence
        wal_entries = coordinator.wal.read()
        if not any(e.get("action") == "COORDINATE_BRANCHES" for e in wal_entries):
            print("[SELF-TEST] FAIL: COORDINATE_BRANCHES not found in WAL")
            return False

        print("[SELF-TEST] PASS : coordinate_branches() returns real task with PR_MERGE recommendation.")
        print("[SELF-TEST] PASS : WAL entry persisted on disk.")
        print("[SELF-TEST] Sceau : WAL-0x243-ALFRED-COORDINATE-REAL-SELFTEST")
        return True


if __name__ == "__main__":
    import sys

    if "--self-test" in sys.argv:
        ok = run_self_test()
        sys.exit(0 if ok else 1)
    else:
        print("Usage: python src/coordination.py --self-test")
        sys.exit(1)
