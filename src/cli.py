"""
Alfred — CLI entry point
Command-line interface for ALFRED citizen.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from .coordination import AlfredCoordinator
from .meta_coherence import MetaCoherenceChecker
from .wal_writer import WALWriter


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
def topology() -> None:
    """Scan SOT vs physical disk for topology drifts."""
    from scripts.scan_topology import main as topology_main
    sys.exit(topology_main())


@cli.command()
def deps() -> None:
    """Audit dependency version conflicts across requirements files."""
    from scripts.audit_dependencies import main as deps_main
    sys.exit(deps_main())


@cli.command()
def hygiene() -> None:
    """Scan workspace for junk files, orphan node_modules, stubs, and TODOs."""
    from scripts.clean_workspace import main as hygiene_main
    sys.exit(hygiene_main())


if __name__ == "__main__":
    sys.exit(cli())
