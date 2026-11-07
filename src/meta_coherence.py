"""
Alfred — Meta-Coherence Checker
Validates cross-repo consistency for gerivdb ecosystem.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional


@dataclass
class CoherenceReport:
    """Meta-coherence validation report."""

    repo: str
    is_coherent: bool
    checked_at: datetime
    issues: List[str]

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "is_coherent": self.is_coherent,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "issues": self.issues,
        }


class MetaCoherenceChecker:
    """Cross-repo meta-coherence validator."""

    def __init__(self) -> None:
        self.reports: List[CoherenceReport] = []

    def check_repo(self, repo: str) -> CoherenceReport:
        """Check coherence for a single repo.

        Verifies: README.md exists, .gitignore exists, remote configured,
        main/master branch exists.
        """
        issues: List[str] = []
        repo_path = Path(repo)

        if not repo_path.exists():
            issues.append(f"Repo path does not exist: {repo}")
        else:
            # Check README.md
            if not (repo_path / "README.md").exists():
                issues.append("missing README.md")

            # Check .gitignore
            if not (repo_path / ".gitignore").exists():
                issues.append("missing .gitignore")

            # Check remote
            try:
                result = subprocess.run(
                    ["git", "remote", "-v"],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if result.returncode != 0 or not result.stdout.strip():
                    issues.append("no remote configured")
            except Exception:
                issues.append("cannot check remote")

            # Check default branch
            try:
                result = subprocess.run(
                    ["git", "branch", "--list"],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                branches = [b.strip("* ") for b in result.stdout.splitlines() if b.strip()]
                if "main" not in branches and "master" not in branches:
                    issues.append("no main/master branch")
            except Exception:
                issues.append("cannot check branches")

        report = CoherenceReport(
            repo=repo,
            is_coherent=len(issues) == 0,
            checked_at=datetime.now(timezone.utc),
            issues=issues,
        )
        self.reports.append(report)
        return report

    def check_repos(self, repos: List[str]) -> List[CoherenceReport]:
        """Check coherence for multiple repos."""
        return [self.check_repo(repo) for repo in repos]
