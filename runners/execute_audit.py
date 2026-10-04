"""
Alfred Audit Execution.
Déclenche l'audit inter-dépôts étendu et écrit un rapport horodaté.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ALFRED = Path(__file__).resolve().parents[1]
AUDIT_RUNNER_PATH = ALFRED / "runners" / "cross_repo_audit_runner.py"
if str(ALFRED) not in sys.path:
    sys.path.insert(0, str(ALFRED))
_spec = importlib.util.spec_from_file_location("Alfred.runners.cross_repo_audit_runner", AUDIT_RUNNER_PATH)
_audit_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_audit_module)
CrossRepoAuditRunner = _audit_module.CrossRepoAuditRunner


def run_ecosystem_audit() -> dict:
    print("[AUDIT EXECUTION] Starting extended cross-repo ecosystem audit (GOVERNANCE-HUB, TOPOS, BRAIN, CTULU, KG-L)...")
    runner = CrossRepoAuditRunner(ALFRED)
    report = runner.audit()
    report["timestamp_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report["intent_hash"] = "0xH0_ALFRED_EXTENDED_AUDIT_EXECUTION_20261005T014300Z"
    report_path = ALFRED / "MOC" / "ALFRED-EXTENDED-ECOSYSTEM-AUDIT-REPORT.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"[AUDIT EXECUTION] Report saved to {report_path}")
    return report


if __name__ == "__main__":
    report = run_ecosystem_audit()
    status = report.get("overall", "BLOCKED")
    if status == "OK":
        print("[AUDIT EXECUTION] Status: SUCCESS - All core registries and structural pillars aligned.")
        sys.exit(0)
    else:
        print("[AUDIT EXECUTION] Status: WARNING/FAILED - Discrepancies detected across extended repos.")
        sys.exit(1)
