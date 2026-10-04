"""
Alfred Git Execution Adapter (gitex).
Encapsule les commandes Git avec retour typé et détection de conflits.
"""
from __future__ import annotations

import subprocess
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
        has_conflict = False
        if "merge" in args and result.returncode != 0:
            status = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=U"],
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
            )
            has_conflict = bool(status.stdout.strip())
        return {
            "ok": result.returncode == 0 and not has_conflict,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "error": None
            if (result.returncode == 0 and not has_conflict)
            else ("CONFLICT_DETECTED" if has_conflict else result.stderr.strip()),
            "conflict": has_conflict,
        }
    except Exception as exc:
        return {
            "ok": False,
            "stdout": "",
            "stderr": str(exc),
            "error": "EXECUTION_EXCEPTION",
            "conflict": False,
        }


def run_git_command(args: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
    """Exécute une commande git et retourne un dictionnaire structuré."""
    return _run_git(cwd or ".", args)


def resolve_conflict_strategy(strategy: str, path: str = ".", cwd: Optional[str] = None) -> Dict[str, Any]:
    """Applique une stratégie de résolution de conflits : 'ours' ou 'theirs'."""
    if strategy not in ("ours", "theirs"):
        return {
            "ok": False,
            "stdout": "",
            "stderr": "",
            "error": "INVALID_CONFLICT_STRATEGY",
            "conflict": False,
        }
    repo_path = cwd or "."
    checkout = _run_git(repo_path, ["checkout", f"--{strategy}", path])
    if not checkout.get("ok"):
        return {
            "ok": False,
            "stdout": "",
            "stderr": checkout.get("stderr") or checkout.get("error"),
            "error": "STRATEGY_CHECKOUT_FAILED",
            "conflict": False,
        }
    add = _run_git(repo_path, ["add", path])
    return {
        "ok": add.get("ok", False),
        "stdout": add.get("stdout") or f"Conflict resolved using strategy '{strategy}' for path '{path}'.",
        "stderr": add.get("stderr") or "",
        "error": None if add.get("ok") else "STAGING_FAILED",
        "conflict": False,
    }
