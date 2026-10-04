"""
Alfred Cross-Repo Audit Runner.
Vérifie la cohérence inter-dépôts : manifeste, intégrité des statuts d'environnement.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


class CrossRepoAuditRunner:
    """Runner d'audit de cohérence inter-dépôts pour Alfred."""

    def __init__(self, alfred_repo: Path | None = None) -> None:
        self.alfred_repo = alfred_repo or Path(__file__).resolve().parents[1]
        self.moc_dir = self.alfred_repo / "MOC"
        self.manifest_path = self.moc_dir / "ALFRED-VAULT-MANIFEST.json"

    def audit(self) -> Dict[str, Any]:
        """Exécute l'audit complet et retourne un rapport structuré."""
        report: Dict[str, Any] = {
            "agent": "Alfred",
            "audit": "cross_repo",
            "manifest_present": self.manifest_path.exists(),
            "manifest_valid": False,
            "modules_present": self._check_modules(),
            "endpoints_present": self._check_endpoints(),
            "overall": "OK",
        }

        if report["manifest_present"]:
            report["manifest_valid"] = self._validate_manifest()

        if not report["manifest_present"] or not report["manifest_valid"]:
            report["overall"] = "BLOCKED"

        return report

    def _check_modules(self) -> Dict[str, bool]:
        """Vérifie la présence des modules core."""
        modules = {
            "gitex": self.alfred_repo / "src" / "gitex.py",
            "syncx": self.alfred_repo / "src" / "syncx.py",
            "coordination_runner": self.alfred_repo / "runners" / "coordination_runner.py",
            "agent_manager_fastapi": self.alfred_repo / "runners" / "agent_manager_fastapi.py",
            "vault_sync_runner": self.alfred_repo / "runners" / "vault_sync_runner.py",
            "cross_repo_audit_runner": self.alfred_repo / "runners" / "cross_repo_audit_runner.py",
        }
        return {name: path.exists() for name, path in modules.items()}

    def _check_endpoints(self) -> Dict[str, bool]:
        """Vérifie la présence des endpoints FastAPI dans le fichier."""
        fastapi_path = self.alfred_repo / "runners" / "agent_manager_fastapi.py"
        if not fastapi_path.exists():
            return {}
        content = fastapi_path.read_text(encoding="utf-8")
        expected = [
            "/alfred/health",
            "/alfred/check",
            "/alfred/fetch",
            "/alfred/pull",
            "/alfred/push",
            "/alfred/branches",
            "/alfred/merge",
            "/alfred/wal-status",
        ]
        return {endpoint: endpoint in content for endpoint in expected}

    def _validate_manifest(self) -> bool:
        """Valide le manifeste NotebookLM."""
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
            return (
                data.get("agent") == "Alfred"
                and "latest_commit" in data
                and "capabilities" in data
                and "endpoints" in data
            )
        except (json.JSONDecodeError, OSError):
            return False
