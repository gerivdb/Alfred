#!/usr/bin/env python3
"""
Alfred — Scheduler Runner
Exécute les 3 scripts de diagnostic (topology, deps, hygiene) à intervalle régulier,
écrit les rapports dans .swarm/reports/YYYY-MM-DD/ et ajoute une entrée WAL à chaque
exécution.

Usage:
    python runners/scheduler_runner.py --run-once
    python runners/scheduler_runner.py --interval 60
    python runners/scheduler_runner.py --interval 1440  # 24h par défaut
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_ALFRED_REPO = Path(__file__).resolve().parents[1]
for _candidate in (_ALFRED_REPO, _ALFRED_REPO.parent):
    _str = str(_candidate)
    if _str not in sys.path:
        sys.path.insert(0, _str)

from Alfred.src.wal_writer import WALWriter  # noqa: E402

INTENT_HASH = "0xBRG_GENERATE_RULES_20260526"
DEFAULT_INTERVAL_SECONDS = 24 * 60 * 60  # 24h

SCRIPTS: List[str] = ["scan_topology.py", "audit_dependencies.py", "clean_workspace.py"]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _report_dir() -> Path:
    """Répertoire des rapports : .swarm/reports/YYYY-MM-DD/."""
    d = _ALFRED_REPO / ".swarm" / "reports" / datetime.now(timezone.utc).strftime("%Y-%m-%d")
    d.mkdir(parents=True, exist_ok=True)
    return d


def _run_script(script_name: str) -> Dict[str, Any]:
    """Exécute un script Alfred et retourne son résultat."""
    script_path = _ALFRED_REPO / "scripts" / script_name
    if not script_path.exists():
        return {
            "script": script_name,
            "status": "ERROR",
            "error": f"Script introuvable: {script_path}",
            "timestamp": _timestamp(),
        }
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), "--json"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            try:
                return {
                    "script": script_name,
                    "status": "OK",
                    "data": json.loads(result.stdout),
                    "timestamp": _timestamp(),
                }
            except json.JSONDecodeError:
                return {
                    "script": script_name,
                    "status": "PARSE_ERROR",
                    "stdout": result.stdout[:500],
                    "stderr": result.stderr[:500],
                    "timestamp": _timestamp(),
                }
        return {
            "script": script_name,
            "status": "ERROR",
            "returncode": result.returncode,
            "stdout": result.stdout[:500],
            "stderr": result.stderr[:500],
            "timestamp": _timestamp(),
        }
    except subprocess.TimeoutExpired:
        return {
            "script": script_name,
            "status": "TIMEOUT",
            "error": "Script expired après 300s",
            "timestamp": _timestamp(),
        }
    except Exception as exc:  # pragma: no cover - défensif
        return {
            "script": script_name,
            "status": "EXCEPTION",
            "error": str(exc),
            "timestamp": _timestamp(),
        }


def run_once() -> Dict[str, Any]:
    """Exécute les 3 scripts une seule fois et sauvegarde le rapport."""
    report_dir = _report_dir()
    report_path = report_dir / f"diagnostic_{datetime.now(timezone.utc).strftime('%H%M%S')}.json"

    results: Dict[str, Any] = {
        "intent_hash": INTENT_HASH,
        "run_at": _timestamp(),
        "scheduler": "Alfred Scheduler Runner",
        "scripts": {},
    }

    for script in SCRIPTS:
        results["scripts"][script] = _run_script(script)

    # Sauvegarde JSON
    report_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # Entrée WAL
    wal = WALWriter()
    wal.append(
        "SCHEDULER_RUN",
        run_at=results["run_at"],
        scripts=list(results["scripts"].keys()),
        report_path=str(report_path),
    )

    # Résumé console
    ok_count = sum(1 for r in results["scripts"].values() if r.get("status") == "OK")
    total = len(results["scripts"])
    print(
        f"[SCHEDULER] Run completed: {ok_count}/{total} scripts OK"
    )
    print(f"[SCHEDULER] Report saved: {report_path}")
    print(f"[SCHEDULER] WAL entry appended.")

    return results


def run_loop(interval_seconds: int) -> None:
    """Boucle de planification : exécute tous les `interval_seconds` secondes."""
    print(f"[SCHEDULER] Démarrage de la boucle (intervalle: {interval_seconds}s)")
    print("[SCHEDULER] Appuyez sur Ctrl+C pour arrêter.")
    try:
        while True:
            run_once()
            print(f"[SCHEDULER] Prochaine exécution dans {interval_seconds}s...")
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("\n[SCHEDULER] Arrêt demandé par l'utilisateur.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Alfred Scheduler Runner")
    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Exécute une seule fois les 3 diagnostics puis quitte.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_SECONDS,
        help="Intervalle en secondes entre deux exécutions (défaut: 86400 = 24h).",
    )
    args = parser.parse_args()

    if args.run_once:
        run_once()
        return 0

    run_loop(args.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
