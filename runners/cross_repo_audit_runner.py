"""
Alfred Cross-Repo Audit Runner.
Vérifie la cohérence inter-dépôts : registres GOVERNANCE-HUB et TOPOS.
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
        self.gov_hub = Path("D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB")
        self.topos = Path("D:/DO/WEB/TOOLS/L1-INFRA/TOPOS")

    def audit(self) -> Dict[str, Any]:
        """Exécute l'audit complet et retourne un rapport structuré."""
        report: Dict[str, Any] = {
            "agent": "Alfred",
            "audit": "cross_repo",
            "manifest_present": self.manifest_path.exists(),
            "manifest_valid": False,
            "modules_present": self._check_modules(),
            "endpoints_present": self._check_endpoints(),
            "governance_hub": self._audit_governance_hub(),
            "topos": self._audit_topos(),
            "overall": "OK",
        }

        if report["manifest_present"]:
            report["manifest_valid"] = self._validate_manifest()

        if not report["manifest_present"] or not report["manifest_valid"]:
            report["overall"] = "BLOCKED"

        if report["governance_hub"].get("status") != "OK" or report["topos"].get("status") != "OK":
            report["overall"] = "BLOCKED"

        return report

    def _check_modules(self) -> Dict[str, bool]:
        """Vérifie la présence des modules core d'Alfred."""
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

    def _audit_governance_hub(self) -> Dict[str, Any]:
        """Audit des registres de GOVERNANCE-HUB."""
        result: Dict[str, Any] = {"status": "OK", "files": {}}
        if not self.gov_hub.exists():
            result["status"] = "BLOCKED"
            result["reason"] = "GOVERNANCE-HUB path not found"
            return result
        for name in ["known_repositories.yaml", "AGENT_RAM.yaml", "BRIDGES.yaml"]:
            path = self.gov_hub / name
            result["files"][name] = path.exists()
            if not path.exists():
                result["status"] = "BLOCKED"
                result.setdefault("missing", []).append(name)
        return result

    def _audit_topos(self) -> Dict[str, Any]:
        """Audit du registre TOPOS."""
        result: Dict[str, Any] = {"status": "OK", "files": {}}
        if not self.topos.exists():
            result["status"] = "BLOCKED"
            result["reason"] = "TOPOS path not found"
            return result
        for name in ["registry/repos.json"]:
            path = self.topos / name
            result["files"][name] = path.exists()
            if not path.exists():
                result["status"] = "BLOCKED"
                result.setdefault("missing", []).append(name)
        if result["status"] == "OK":
            try:
                data = json.loads((self.topos / "registry/repos.json").read_text(encoding="utf-8"))
                result["repos_count"] = len(data) if isinstance(data, list) else len(data.get("repos", []))
            except (json.JSONDecodeError, OSError):
                result["status"] = "BLOCKED"
                result["reason"] = "repos.json invalid"
        return result
