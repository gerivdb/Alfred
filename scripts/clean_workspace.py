#!/usr/bin/env python3
"""
Alfred — Workspace Hygiene Scanner
Detects (read-only, no deletion) junk files, orphan node_modules, stub .py files,
and TODO/FIXME markers across all repos under the ecosystem root.

Usage:
    python scripts/clean_workspace.py --self-test
    python scripts/clean_workspace.py --json > hygiene_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

ECOSYSTEM_ROOT = Path("D:/DO/WEB/TOOLS")
INTENT_HASH = "0xBRG_GENERATE_RULES_20260526"

JUNK_EXTENSIONS = {".bak", "~", ".tmp", ".swp", ".orig", ".rej"}
TODO_MARKERS = {"TODO", "FIXME", "HACK", "XXX"}
STUB_PATTERNS = {"pass", "TODO", "FIXME", "NotImplemented"}
MIN_STUB_LINES = 10

_EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".kilo", ".kilocode"}

STRATA_DIRS = ["L0-CANON", "L1-INFRA", "L2-PLATFORM", "L3-CITIZENS", "L4-TOOLS", "L5-ARCHIVE", "L6-WORK"]


# --- Discovery --------------------------------------------------------------------------


def _is_git_repo(path: Path) -> bool:
    return (path / ".git").is_dir()


def find_repos(root: Path = ECOSYSTEM_ROOT) -> List[Path]:
    """Find git repos directly under each stratum directory.

    Only looks at root/L*/*, not the entire tree, for performance.
    """
    repos: List[Path] = []
    if not root.exists():
        return repos
    for stratum in STRATA_DIRS:
        stratum_dir = root / stratum
        if not stratum_dir.is_dir():
            continue
        for entry in stratum_dir.iterdir():
            if entry.is_dir() and _is_git_repo(entry):
                repos.append(entry)
    return sorted(repos)


# --- Junk files -------------------------------------------------------------------------


def scan_for_junk(repos: List[Path], max_files: int = 10000) -> List[Dict[str, str]]:
    """Detect junk files (.bak, ~, .tmp, .swp, .orig, .rej) in repos."""
    junk: List[Dict[str, str]] = []
    files_seen = 0
    for repo in repos:
        for dirpath, dirnames, filenames in os.walk(repo):
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
            for name in filenames:
                files_seen += 1
                if files_seen > max_files:
                    return junk
                if any(name.endswith(ext) for ext in JUNK_EXTENSIONS):
                    junk.append({
                        "file": str(Path(dirpath) / name),
                        "repo": repo.name,
                        "type": "junk_file",
                    })
    return junk


# --- Orphan node_modules ----------------------------------------------------------------


def scan_for_orphan_node_modules(repos: List[Path], max_files: int = 10000) -> List[Dict[str, str]]:
    """Detect node_modules/ directories without a package.json in the same repo."""
    orphans: List[Dict[str, str]] = []
    files_seen = 0
    for repo in repos:
        # First check if package.json exists anywhere in the repo
        has_package_json = False
        for dirpath, dirnames, filenames in os.walk(repo):
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS - {"node_modules"}]
            files_seen += len(filenames)
            if files_seen > max_files:
                return orphans
            if "package.json" in filenames:
                has_package_json = True
                break

        if has_package_json:
            continue

        # No package.json: find all node_modules directories
        for dirpath, dirnames, _ in os.walk(repo):
            if "node_modules" in dirnames:
                nm_path = Path(dirpath) / "node_modules"
                orphans.append({
                    "path": str(nm_path),
                    "repo": repo.name,
                    "type": "orphan_node_modules",
                })
                dirnames.remove("node_modules")
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
    return orphans


# --- Stub .py files ---------------------------------------------------------------------


def _is_stub_py(path: Path) -> bool:
    """Check if a .py file is a stub (few lines, only pass/TODO/NotImplemented/imports)."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return False

    lines = [l.strip() for l in content.splitlines() if l.strip()]
    if not lines:
        return True  # Empty file is a stub
    if len(lines) >= MIN_STUB_LINES:
        return False

    # All non-empty lines must be pass, TODO, FIXME, NotImplemented, comments, or imports
    for line in lines:
        if line.startswith("#"):
            continue
        if line.startswith("import ") or line.startswith("from "):
            continue
        stripped_lower = line.lower()
        if any(p in stripped_lower for p in STUB_PATTERNS):
            continue
        return False  # Has real code
    return True


def scan_for_stub_py(repos: List[Path], max_files: int = 10000) -> List[Dict[str, str]]:
    """Detect stub .py files (under 10 lines, only pass/TODO/NotImplemented/imports)."""
    stubs: List[Dict[str, str]] = []
    files_seen = 0
    for repo in repos:
        for dirpath, dirnames, filenames in os.walk(repo):
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
            for name in filenames:
                files_seen += 1
                if files_seen > max_files:
                    return stubs
                if not name.endswith(".py"):
                    continue
                path = Path(dirpath) / name
                if _is_stub_py(path):
                    stubs.append({"file": str(path), "repo": repo.name, "type": "stub_py"})
    return stubs


# --- TODO/FIXME markers -----------------------------------------------------------------


def scan_for_todos(repos: List[Path], max_files: int = 10000) -> List[Dict[str, str]]:
    """Detect TODO/FIXME/HACK/XXX markers in all .py files."""
    todos: List[Dict[str, str]] = []
    files_seen = 0
    for repo in repos:
        for dirpath, dirnames, filenames in os.walk(repo):
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
            for name in filenames:
                files_seen += 1
                if files_seen > max_files:
                    return todos
                if not name.endswith(".py"):
                    continue
                path = Path(dirpath) / name
                try:
                    lines = path.read_text(encoding="utf-8").splitlines()
                except (OSError, UnicodeDecodeError):
                    continue
                for i, line in enumerate(lines, 1):
                    upper = line.upper()
                    for marker in TODO_MARKERS:
                        if marker in upper:
                            todos.append({
                                "file": str(path),
                                "repo": repo.name,
                                "line": i,
                                "marker": marker,
                                "content": line.strip()[:120],
                            })
                            break
    return todos


# --- Self-test --------------------------------------------------------------------------


def run_self_test() -> bool:
    """Create a fake repo with junk, orphan node_modules, stub .py, and TODO."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        repo = tmp / "L0-CANON" / "fake_repo"
        repo.mkdir(parents=True)
        (repo / ".git").mkdir()

        # Junk file
        (repo / "temp.bak").write_text("old backup\n")

        # Orphan node_modules (no package.json in repo)
        (repo / "node_modules").mkdir()

        # Stub .py (only pass)
        stub = repo / "stub.py"
        stub.write_text("pass\n")

        # Real .py with TODO
        real = repo / "real.py"
        real.write_text("# TODO: fix this\nx = 1\n")

        repos = find_repos(tmp)

        junk = scan_for_junk(repos)
        orphans = scan_for_orphan_node_modules(repos)
        stubs = scan_for_stub_py(repos)
        todo_list = scan_for_todos(repos)

        ok = True
        if not any("temp.bak" in j["file"] for j in junk):
            print("[SELF-TEST] FAIL: temp.bak not detected as junk")
            ok = False
        if not any("node_modules" in o["path"] for o in orphans):
            print("[SELF-TEST] FAIL: orphan node_modules not detected")
            ok = False
        if not any("stub.py" in s["file"] for s in stubs):
            print("[SELF-TEST] FAIL: stub.py not detected as stub")
            ok = False
        if not any("real.py" in t["file"] for t in todo_list):
            print("[SELF-TEST] FAIL: TODO in real.py not detected")
            ok = False

        if ok:
            print("[SELF-TEST] PASS : workspace hygiene detects junk, orphan node_modules, stub .py, and TODOs.")
            print("[SELF-TEST] Sceau : WAL-0x243-ALFRED-CLEAN-WORKSPACE-SELFTEST")
            return 0
        print("[SELF-TEST] FAIL : workspace hygiene detection incomplete.")
        print(f"[SELF-TEST] junk={junk}")
        print(f"[SELF-TEST] orphans={orphans}")
        print(f"[SELF-TEST] stubs={stubs}")
        print(f"[SELF-TEST] todos={todo_list}")
        return 1


# --- CLI --------------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Alfred Workspace Hygiene Scanner")
    parser.add_argument("--self-test", action="store_true", help="Run built-in self-test")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--root", type=str, default=str(ECOSYSTEM_ROOT), help="Ecosystem root path")
    parser.add_argument(
        "--max-repos", type=int, default=50, help="Maximum repos to scan (safety limit)"
    )
    parser.add_argument(
        "--max-files", type=int, default=2000, help="Maximum files per scan type (safety limit)"
    )
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    all_repos = find_repos(Path(args.root))
    truncated_repos = len(all_repos) > args.max_repos
    repos = all_repos[: args.max_repos]

    junk = scan_for_junk(repos, args.max_files)
    orphans = scan_for_orphan_node_modules(repos, args.max_files)
    stubs = scan_for_stub_py(repos, args.max_files)
    todos = scan_for_todos(repos, args.max_files)

    report = {
        "intent_hash": INTENT_HASH,
        "repos_scanned": len(repos),
        "total_repos_found": len(all_repos),
        "repos_truncated": truncated_repos,
        "junk_files": junk,
        "orphan_node_modules": orphans,
        "stub_py_files": stubs,
        "todo_fixme_markers": todos,
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"[HYGIENE] Repos found: {len(all_repos)}, scanned: {len(repos)}")
        print(f"[HYGIENE] Junk files: {len(junk)}")
        print(f"[HYGIENE] Orphan node_modules: {len(orphans)}")
        print(f"[HYGIENE] Stub .py files: {len(stubs)}")
        print(f"[HYGIENE] TODO/FIXME markers: {len(todos)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
