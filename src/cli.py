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


if __name__ == "__main__":
    sys.exit(cli())
