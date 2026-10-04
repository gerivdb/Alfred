"""Tests for Alfred coordination and meta-coherence."""

from __future__ import annotations

from datetime import datetime, timezone

from src.coordination import AlfredCoordinator, CoordinationState, CoordinationTask
from src.meta_coherence import CoherenceReport, MetaCoherenceChecker


def test_alfred_coordinator_initializes_idle() -> None:
    coordinator = AlfredCoordinator()
    assert coordinator.current_state == CoordinationState.IDLE


def test_coordinate_branches_returns_tasks() -> None:
    coordinator = AlfredCoordinator()
    tasks = coordinator.coordinate_branches("gerivdb/GOVERNANCE-HUB")
    assert isinstance(tasks, list)


def test_dispatch_tasks_sets_coordination_state() -> None:
    coordinator = AlfredCoordinator()
    tasks = [
        CoordinationTask(
            task_id="T1",
            repo="gerivdb/GOVERNANCE-HUB",
            action="create_branch",
            payload={},
            created_at=datetime.now(timezone.utc),
        )
    ]
    coordinator.dispatch_tasks(tasks)
    assert tasks[0].state == CoordinationState.COORDINATION


def test_verify_meta_coherence_returns_true() -> None:
    coordinator = AlfredCoordinator()
    assert coordinator.verify_meta_coherence(["gerivdb/GOVERNANCE-HUB"]) is True


def test_wal_entries_are_appended() -> None:
    coordinator = AlfredCoordinator()
    coordinator.coordinate_branches("gerivdb/GOVERNANCE-HUB")
    assert len(coordinator.wal_entries) == 1
    assert coordinator.wal_entries[0]["action"] == "COORDINATE_BRANCHES"


def test_meta_coherence_checker_reports_coherent_repo() -> None:
    checker = MetaCoherenceChecker()
    report = checker.check_repo("gerivdb/GOVERNANCE-HUB")
    assert report.is_coherent is True
    assert report.repo == "gerivdb/GOVERNANCE-HUB"


def test_meta_coherence_checker_multiple_repos() -> None:
    checker = MetaCoherenceChecker()
    reports = checker.check_repos(["gerivdb/GOVERNANCE-HUB", "gerivdb/CTULU"])
    assert len(reports) == 2
    assert all(report.is_coherent for report in reports)


def test_coherence_report_to_dict() -> None:
    report = CoherenceReport(
        repo="gerivdb/GOVERNANCE-HUB",
        is_coherent=True,
        checked_at=datetime.now(timezone.utc),
        issues=[],
    )
    data = report.to_dict()
    assert data["repo"] == "gerivdb/GOVERNANCE-HUB"
    assert data["is_coherent"] is True
    assert isinstance(data["issues"], list)
