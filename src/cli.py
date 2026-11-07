"""
Alfred — CLI entry point
Command-line interface for ALFRED citizen.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

try:
    from .coordination import AlfredCoordinator
    from .meta_coherence import MetaCoherenceChecker
    from .wal_writer import WALWriter
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent))
    from coordination import AlfredCoordinator  # noqa: E402
    from meta_coherence import MetaCoherenceChecker  # noqa: E402
    from wal_writer import WALWriter  # noqa: E402

# Racine d'Alfred pour les imports scripts.* en exécution directe
_ALFRED_ROOT = Path(__file__).resolve().parents[1]
if str(_ALFRED_ROOT) not in sys.path:
    sys.path.insert(0, str(_ALFRED_ROOT))


@click.group()
@click.version_option("1.0.0")
def cli() -> None:
    """Alfred — Operational Coordination Assistant."""


@cli.command()
@click.argument("repo")
def coordinate(repo: str) -> None:
    """Coordinate branches for REPO."""
    coordinator = AlfredCoordinator()
    tasks = coordinator.coordinate_branches(repo)
    click.echo(f"Coordination complete for {repo}: {len(tasks)} tasks")


@cli.command()
@click.argument("repos", nargs=-1, required=True)
def check(repos: tuple[str, ...]) -> None:
    """Check meta-coherence for REPOS."""
    checker = MetaCoherenceChecker()
    reports = checker.check_repos(list(repos))
    for report in reports:
        status = "OK" if report.is_coherent else "FAIL"
        click.echo(f"[{status}] {report.repo}")


@cli.command()
def wal_status() -> None:
    """Show WAL status."""
    wal = WALWriter()
    count = wal.count()
    click.echo(f"WAL entries: {count}")


@cli.command()
@click.option("--json", is_flag=True, help="Sortie JSON (toujours activée pour les scripts)")
def topology(json: bool) -> None:
    """Scan SOT vs physical disk for topology drifts."""
    from scripts.scan_topology import main as topology_main
    _old_argv = sys.argv[:]
    sys.argv = ["scan_topology.py", "--json"]
    try:
        sys.exit(topology_main())
    except SystemExit:
        raise
    finally:
        sys.argv = _old_argv


@cli.command()
@click.option("--json", is_flag=True, help="Sortie JSON (toujours activée pour les scripts)")
def deps(json: bool) -> None:
    """Audit dependency version conflicts across requirements files."""
    from scripts.audit_dependencies import main as deps_main
    _old_argv = sys.argv[:]
    sys.argv = ["audit_dependencies.py", "--json"]
    try:
        sys.exit(deps_main())
    except SystemExit:
        raise
    finally:
        sys.argv = _old_argv


@cli.command()
@click.option("--json", is_flag=True, help="Sortie JSON (toujours activée pour les scripts)")
def hygiene(json: bool) -> None:
    """Scan workspace for junk files, orphan node_modules, stubs, and TODOs."""
    from scripts.clean_workspace import main as hygiene_main
    _old_argv = sys.argv[:]
    sys.argv = ["clean_workspace.py", "--json"]
    try:
        sys.exit(hygiene_main())
    except SystemExit:
        raise
    finally:
        sys.argv = _old_argv


if __name__ == "__main__":
    sys.exit(cli())
