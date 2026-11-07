#!/usr/bin/env python3
"""
Alfred — Dependency Auditor
Inventories requirements.txt / pyproject.toml files across the ecosystem and
detects version conflicts for the same package declared differently.

Usage:
    python scripts/audit_dependencies.py --self-test
    python scripts/audit_dependencies.py --json > deps_report.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ECOSYSTEM_ROOT = Path("D:/DO/WEB/TOOLS")
INTENT_HASH = "0xBRG_GENERATE_RULES_20260526"

# Regex to parse a requirement line: package_name [extras] version_specifier
# Examples: requests==2.28.0, flask>=2.0, numpy, package[extra]~=1.2
_REQ_RE = re.compile(
    r"^\s*([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)"  # package name
    r"(?:\[[^\]]*\])?"                                    # optional extras
    r"\s*(==|!=|<=|>=|<|>|~=|===)?\s*"                   # optional operator
    r"([A-Za-z0-9._*+-]+)?"                               # optional version
    r"\s*$"
)


# --- Discovery --------------------------------------------------------------------------

_EXCLUDED_DIRS = {".git", ".venv", "venv", "__pycache__", "node_modules", ".kilo", ".kilocode"}

# Valid strata directories directly under the ecosystem root
STRATA_DIRS = ["L0-CANON", "L1-INFRA", "L2-PLATFORM", "L3-CITIZENS", "L4-TOOLS", "L5-ARCHIVE", "L6-WORK"]


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


def find_requirements(root: Path = ECOSYSTEM_ROOT) -> List[Path]:
    """Find requirements.txt and pyproject.toml files inside each repo.

    Uses os.walk with directory pruning, scoped to repos only.
    """
    found: List[Path] = []
    for repo in find_repos(root):
        for dirpath, dirnames, filenames in os.walk(repo):
            dirnames[:] = [d for d in dirnames if d not in _EXCLUDED_DIRS]
            for name in filenames:
                if name in ("requirements.txt", "pyproject.toml"):
                    found.append(Path(dirpath) / name)
    return sorted(found)


# --- Parsing ----------------------------------------------------------------------------


def _parse_requirement_line(line: str) -> Optional[Tuple[str, str]]:
    """Parse a single requirements.txt line. Returns (package, version_spec) or None."""
    line = line.strip()
    if not line or line.startswith("#") or line.startswith("-"):
        return None
    m = _REQ_RE.match(line)
    if not m:
        return None
    package = m.group(1)
    operator = m.group(3) or ""
    version = m.group(4) or ""
    if operator and version:
        spec = f"{operator}{version}"
    elif version:
        spec = version
    else:
        spec = "*"
    return package.lower(), spec


def parse_requirements_txt(path: Path) -> Dict[str, str]:
    """Parse a requirements.txt file into {package: version_spec}."""
    deps: Dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                parsed = _parse_requirement_line(line)
                if parsed:
                    pkg, spec = parsed
                    # Keep the most specific spec if duplicated
                    if pkg not in deps or deps[pkg] == "*":
                        deps[pkg] = spec
    except (OSError, UnicodeDecodeError):
        pass
    return deps


def parse_pyproject_toml(path: Path) -> Dict[str, str]:
    """Parse [project.dependencies] from a pyproject.toml file."""
    deps: Dict[str, str] = {}
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return deps

    # Minimal TOML parsing without external library: look for [project.dependencies]
    in_deps = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped == "[project.dependencies]":
            in_deps = True
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            in_deps = False
            continue
        if in_deps and "=" in stripped:
            key, _, val = stripped.partition("=")
            key = key.strip().strip('"').strip("'")
            val = val.strip().strip('"').strip("'")
            if key and val:
                parsed = _parse_requirement_line(f"{key}{val}")
                if parsed:
                    pkg, spec = parsed
                    deps[pkg] = spec
    return deps


def parse_file(path: Path) -> Dict[str, str]:
    """Parse a requirements.txt or pyproject.toml file."""
    if path.name == "requirements.txt":
        return parse_requirements_txt(path)
    if path.name == "pyproject.toml":
        return parse_pyproject_toml(path)
    return {}


# --- Conflict detection -----------------------------------------------------------------


def find_conflicts(all_deps: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
    """Detect packages declared with incompatible version specs across files.

    all_deps: {file_path_str: {package: version_spec}}
    Returns list of {package, occurrences: [{file, spec}]}.
    """
    package_occurrences: Dict[str, List[Dict[str, str]]] = {}
    for file_path, deps in all_deps.items():
        for pkg, spec in deps.items():
            package_occurrences.setdefault(pkg, []).append({"file": file_path, "spec": spec})

    conflicts: List[Dict[str, Any]] = []
    for pkg, occurrences in sorted(package_occurrences.items()):
        if len(occurrences) < 2:
            continue
        specs = {occ["spec"] for occ in occurrences}
        # Filter out '*' (unspecified) when comparing
        concrete_specs = {s for s in specs if s != "*"}
        if len(concrete_specs) > 1:
            conflicts.append({"package": pkg, "occurrences": occurrences})
    return conflicts


# --- Self-test --------------------------------------------------------------------------


def run_self_test() -> bool:
    """Create fake requirements files with a conflict and verify detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # File 1: requests==2.28.0
        repo1 = tmp / "L0-CANON" / "repo1"
        repo1.mkdir(parents=True)
        (repo1 / ".git").mkdir()
        f1 = repo1 / "requirements.txt"
        f1.write_text("requests==2.28.0\nflask>=2.0\nnumpy\n")

        # File 2: requests==2.25.0 (conflict), flask>=2.0 (compatible)
        repo2 = tmp / "L0-CANON" / "repo2"
        repo2.mkdir(parents=True)
        (repo2 / ".git").mkdir()
        f2 = repo2 / "requirements.txt"
        f2.write_text("requests==2.25.0\nflask>=2.0\n")

        # File 3: no conflict, just requests>=2.0 (compatible with nothing concrete)
        f3 = repo2 / "pyproject.toml"
        f3.write_text('[project.dependencies]\nrequests=">=2.0"\n')

        all_deps: Dict[str, Dict[str, str]] = {}
        for fp in find_requirements(tmp):
            all_deps[str(fp)] = parse_file(fp)

        conflicts = find_conflicts(all_deps)

        # Verify: requests conflict detected
        request_conflicts = [c for c in conflicts if c["package"] == "requests"]
        if not request_conflicts:
            print("[SELF-TEST] FAIL: requests version conflict not detected")
            print(f"[SELF-TEST] conflicts={conflicts}")
            return 1

        # Verify: flask >=2.0 appears twice but same spec, no conflict
        flask_conflicts = [c for c in conflicts if c["package"] == "flask"]
        if flask_conflicts:
            print("[SELF-TEST] FAIL: flask should not be a conflict (same spec >=2.0)")
            return 1

        print("[SELF-TEST] PASS : dependency audit detects version conflicts correctly.")
        print("[SELF-TEST] Sceau : WAL-0x243-ALFRED-DEPS-AUDIT-SELFTEST")
        return 0


# --- CLI --------------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Alfred Dependency Auditor")
    parser.add_argument("--self-test", action="store_true", help="Run built-in self-test")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--root", type=str, default=str(ECOSYSTEM_ROOT), help="Ecosystem root path")
    parser.add_argument(
        "--max-files", type=int, default=5000, help="Maximum files to scan (safety limit)"
    )
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    all_files = find_requirements(Path(args.root))
    truncated = len(all_files) > args.max_files
    files = all_files[: args.max_files]
    all_deps: Dict[str, Dict[str, str]] = {}
    total_deps = 0
    for fp in files:
        deps = parse_file(fp)
        if deps:
            all_deps[str(fp)] = deps
            total_deps += len(deps)

    conflicts = find_conflicts(all_deps)

    report = {
        "intent_hash": INTENT_HASH,
        "total_files": len(files),
        "files_with_deps": len(all_deps),
        "total_deps": total_deps,
        "conflicts": conflicts,
        "truncated": truncated,
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"[DEPS] Files scanned: {len(files)}")
        print(f"[DEPS] Files with dependencies: {len(all_deps)}")
        print(f"[DEPS] Total dependency declarations: {total_deps}")
        print(f"[DEPS] Version conflicts: {len(conflicts)}")
        for c in conflicts:
            print(f"  CONFLICT {c['package']}:")
            for occ in c["occurrences"]:
                print(f"    {occ['file']}: {occ['spec']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
