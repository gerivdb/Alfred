#!/usr/bin/env python3
"""
Alfred — Topology Scanner
Cross-checks known_repositories.yaml (SOT) against physical disk to detect
repos absent from disk, repos absent from SOT, and strate mismatches.

Usage:
    python scripts/scan_topology.py --self-test
    python scripts/scan_topology.py --json > topology_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- Configuration -----------------------------------------------------------------------

try:
    import yaml
    HAS_YAML = True
except ImportError:  # pragma: no cover
    HAS_YAML = False

STRATA_DIRS = ["L0-CANON", "L1-INFRA", "L2-PLATFORM", "L3-CITIZENS", "L4-TOOLS"]
ECOSYSTEM_ROOT = Path("D:/DO/WEB/TOOLS")
SOT_PATH = Path("D:/DO/WEB/TOOLS/L0-CANON/GOVERNANCE-HUB/known_repositories.yaml")
INTENT_HASH = "0xBRG_GENERATE_RULES_20260526"


# --- SOT loading ------------------------------------------------------------------------


def load_sot(sot_path: Path = SOT_PATH) -> Dict[str, Dict[str, str]]:
    """Parse known_repositories.yaml and return {repo_name: {local_path, strate}}."""
    if not HAS_YAML:
        raise RuntimeError("PyYAML is required to parse known_repositories.yaml")
    if not sot_path.exists():
        raise FileNotFoundError(f"SOT not found: {sot_path}")

    try:
        with open(sot_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as exc:
        print(f"[ERROR] Failed to parse SOT YAML: {sot_path}", file=sys.stderr)
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(2)

    repos: Dict[str, Dict[str, str]] = {}
    for item in data.get("repos", []):
        repo_name = item.get("repo", "")
        local_path = item.get("local_path", "")
        strate = item.get("strate", "")
        # Extract directory name from repo name (gerivdb/repo_a -> repo_a)
        dir_name = repo_name.split("/")[-1] if repo_name else ""
        if repo_name:
            repos[repo_name] = {
                "local_path": local_path,
                "strate": strate,
                "dir_name": dir_name,
            }
    return repos


# --- Disk scanning ----------------------------------------------------------------------


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").is_dir()


def _strate_from_path(path: Path) -> Optional[str]:
    """Return the strate name from a path like .../L4-TOOLS/CTULU -> 'L4-TOOLS'."""
    parts = path.parts
    for i, part in enumerate(parts):
        if part in STRATA_DIRS and i + 1 < len(parts):
            return part
    return None


def scan_disk(root: Path = ECOSYSTEM_ROOT) -> Dict[str, Dict[str, str]]:
    """Scan physical disk for git repos under valid strata.

    Returns {repo_dir_name: {path, strate}}.
    """
    repos: Dict[str, Dict[str, str]] = {}
    if not root.exists():
        return repos

    for stratum in STRATA_DIRS:
        stratum_dir = root / stratum
        if not stratum_dir.is_dir():
            continue
        for entry in stratum_dir.iterdir():
            if entry.is_dir() and _is_git_repo(entry):
                repos[entry.name] = {"path": str(entry), "strate": stratum}
    return repos


# --- Diff -------------------------------------------------------------------------------


def diff(sot: Dict[str, Dict[str, str]], disk: Dict[str, Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    """Compare SOT and disk, returning three lists: absent_from_disk, absent_from_sot, strate_mismatch."""
    # Build lookup by dir_name from SOT
    sot_by_dir: Dict[str, Dict[str, str]] = {}
    for repo_name, info in sot.items():
        dir_name = info.get("dir_name", "")
        if dir_name:
            sot_by_dir[dir_name] = {"repo": repo_name, **info}

    sot_dirs = set(sot_by_dir.keys())
    disk_dirs = set(disk.keys())

    absent_from_disk = [
        {
            "repo": sot_by_dir[name]["repo"],
            "local_path": sot_by_dir[name]["local_path"],
            "strate": sot_by_dir[name]["strate"],
        }
        for name in sorted(sot_dirs - disk_dirs)
    ]

    absent_from_sot = [
        {"repo": name, "path": disk[name]["path"], "strate": disk[name]["strate"]}
        for name in sorted(disk_dirs - sot_dirs)
    ]

    strate_mismatch = []
    for name in sorted(sot_dirs & disk_dirs):
        sot_strate = sot_by_dir[name]["strate"]
        disk_strate = disk[name]["strate"]
        if sot_strate != disk_strate:
            strate_mismatch.append({
                "repo": sot_by_dir[name]["repo"],
                "sot_strate": sot_strate,
                "disk_strate": disk_strate,
                "disk_path": disk[name]["path"],
            })

    return {
        "absent_from_disk": absent_from_disk,
        "absent_from_sot": absent_from_sot,
        "strate_mismatch": strate_mismatch,
    }


# --- Self-test --------------------------------------------------------------------------


def run_self_test() -> bool:
    """Create fake SOT and fake disk, verify diff() returns correct lists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Fake SOT: 2 repos
        sot_dir = tmp / "L0-CANON" / "GOVERNANCE-HUB"
        sot_dir.mkdir(parents=True, exist_ok=True)
        sot_data = {
            "schema_version": "1.0.0",
            "intent_hash": INTENT_HASH,
            "repos": [
                {"repo": "gerivdb/repo_a", "local_path": str(tmp / "L0-CANON" / "repo_a"), "strate": "L0-CANON"},
                {"repo": "gerivdb/repo_b", "local_path": str(tmp / "L4-TOOLS" / "repo_b"), "strate": "L4-TOOLS"},
                {"repo": "gerivdb/repo_c", "local_path": str(tmp / "L0-CANON" / "repo_c"), "strate": "L0-CANON"},
            ],
        }
        sot_file = sot_dir / "known_repositories.yaml"
        with open(sot_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(sot_data, f)

        # Fake disk:
        # - repo_a exists in L0-CANON (matches SOT)
        # - repo_b exists in L4-TOOLS but strate mismatch (SOT says L4-TOOLS but let's put it in L0-CANON to test mismatch)
        # - repo_d exists but not in SOT (absent_from_sot)
        # - repo_c missing from disk (absent_from_disk)
        (tmp / "L0-CANON" / "repo_a" / ".git").mkdir(parents=True, exist_ok=True)
        (tmp / "L0-CANON" / "repo_b" / ".git").mkdir(parents=True, exist_ok=True)  # mismatch: SOT says L4-TOOLS, disk says L0-CANON
        (tmp / "L4-TOOLS" / "repo_d" / ".git").mkdir(parents=True, exist_ok=True)  # absent_from_sot

        # Load SOT and scan disk
        sot = load_sot(sot_file)
        disk = scan_disk(tmp)

        result = diff(sot, disk)

        # Assertions
        absent_disk_repos = {e["repo"] for e in result["absent_from_disk"]}
        absent_sot_repos = {e["repo"] for e in result["absent_from_sot"]}
        mismatch_repos = {e["repo"] for e in result["strate_mismatch"]}

        ok = True
        if "gerivdb/repo_c" not in absent_disk_repos:
            print("[SELF-TEST] FAIL: repo_c should be absent_from_disk")
            ok = False
        if "repo_d" not in absent_sot_repos:
            print("[SELF-TEST] FAIL: repo_d should be absent_from_sot")
            ok = False
        if "gerivdb/repo_b" not in mismatch_repos:
            print("[SELF-TEST] FAIL: repo_b should be strate_mismatch")
            ok = False
        if "gerivdb/repo_a" in absent_disk_repos or "repo_a" in absent_sot_repos or "gerivdb/repo_a" in mismatch_repos:
            print("[SELF-TEST] FAIL: repo_a should not appear in any diff list")
            ok = False

        if ok:
            print("[SELF-TEST] PASS : topology scan diff correctly detects absent_from_disk, absent_from_sot, strate_mismatch.")
            print("[SELF-TEST] Sceau : WAL-0x243-ALFRED-TOPOLOGY-SCAN-SELFTEST")
            return 0
        print("[SELF-TEST] FAIL : topology scan diff returned unexpected results.")
        print(f"[SELF-TEST] absent_from_disk={absent_disk_repos}")
        print(f"[SELF-TEST] absent_from_sot={absent_sot_repos}")
        print(f"[SELF-TEST] strate_mismatch={mismatch_repos}")
        return 1


# --- CLI --------------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Alfred Topology Scanner")
    parser.add_argument("--self-test", action="store_true", help="Run built-in self-test")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--sot", type=str, default=str(SOT_PATH), help="Path to known_repositories.yaml")
    parser.add_argument("--root", type=str, default=str(ECOSYSTEM_ROOT), help="Ecosystem root path")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    sot = load_sot(Path(args.sot))
    disk = scan_disk(Path(args.root))
    result = diff(sot, disk)

    report = {
        "intent_hash": INTENT_HASH,
        "sot_count": len(sot),
        "disk_count": len(disk),
        "absent_from_disk": result["absent_from_disk"],
        "absent_from_sot": result["absent_from_sot"],
        "strate_mismatch": result["strate_mismatch"],
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"[TOPOLOGY] SOT repos: {len(sot)}, disk repos: {len(disk)}")
        print(f"[TOPOLOGY] Absent from disk: {len(result['absent_from_disk'])}")
        print(f"[TOPOLOGY] Absent from SOT: {len(result['absent_from_sot'])}")
        print(f"[TOPOLOGY] Strate mismatches: {len(result['strate_mismatch'])}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
