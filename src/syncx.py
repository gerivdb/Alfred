"""
Alfred Synchronization Adapter (syncx).
Coordinates push/pull with retry and blocked-state detection.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


def _run_git(repo_path: str, args: List[str]) -> Dict[str, Any]:
    repo = Path(repo_path)
    if not repo.exists() or not (repo / ".git").exists():
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "error": f"Invalid git repo: {repo_path}",
            "conflict": False,
        }
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        return {
            "ok": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "command": cmd,
        }
    except Exception as exc:
        return {
            "ok": False,
            "stdout": "",
            "stderr": str(exc),
            "error": "EXECUTION_EXCEPTION",
            "conflict": False,
        }


def robust_sync_push(
    remote: str = "origin",
    branch: str = "main",
    retries: int = 3,
    delay: int = 2,
    cwd: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a push with retry policy for transient failures.
    Returns explicit status: success | failed | blocked.
    """
    cmd = ["git", "push", remote, branch]
    last_stderr = ""
    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return {
                    "status": "success",
                    "attempt": attempt,
                    "stdout": result.stdout.strip(),
                    "stderr": "",
                    "error": None,
                }
            last_stderr = result.stderr.strip()
            if "rejected" in last_stderr or "non-fast-forward" in last_stderr:
                return {
                    "status": "blocked",
                    "attempt": attempt,
                    "stdout": result.stdout.strip(),
                    "stderr": last_stderr,
                    "error": "REMOTE_REJECTED_NON_FAST_FORWARD",
                }
            if attempt < retries:
                time.sleep(delay)
        except Exception as exc:
            last_stderr = str(exc)
            if attempt < retries:
                time.sleep(delay)
    return {
        "status": "failed",
        "attempt": retries,
        "stdout": "",
        "stderr": last_stderr,
        "error": "MAX_RETRIES_EXCEEDED",
    }


def robust_sync_pull(
    remote: str = "origin",
    branch: str = "main",
    retries: int = 3,
    delay: int = 2,
    cwd: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a pull with retry policy and merge-conflict detection.
    Returns explicit status: success | failed | blocked | conflict.
    """
    cmd = ["git", "pull", remote, branch]
    last_stderr = ""
    for attempt in range(1, retries + 1):
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode == 0:
                return {
                    "status": "success",
                    "attempt": attempt,
                    "stdout": result.stdout.strip(),
                    "stderr": "",
                    "error": None,
                }
            combined_msg = "\n".join(filter(None, [result.stdout.strip(), result.stderr.strip()])).lower()
            if "conflict" in combined_msg or "automatic merge failed" in combined_msg:
                return {
                    "status": "conflict",
                    "attempt": attempt,
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                    "error": "PULL_MERGE_CONFLICT",
                }
            if "refusing to merge unrelated histories" in combined_msg:
                return {
                    "status": "blocked",
                    "attempt": attempt,
                    "stdout": result.stdout.strip(),
                    "stderr": result.stderr.strip(),
                    "error": "UNRELATED_HISTORIES_BLOCKED",
                }
            last_stderr = result.stderr.strip()
            if attempt < retries:
                time.sleep(delay)
        except Exception as exc:
            last_stderr = str(exc)
            if attempt < retries:
                time.sleep(delay)
    return {
        "status": "failed",
        "attempt": retries,
        "stdout": "",
        "stderr": last_stderr,
        "error": "MAX_RETRIES_EXCEEDED",
    }
