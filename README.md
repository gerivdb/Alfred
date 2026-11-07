# Alfred — Operational Coordination Assistant

## Overview

ALFRED is a **citizen** in the gerivdb ecosystem responsible for operational coordination across all 102 active repositories.

## Responsibilities

- Branch lifecycle coordination (creation, merge, cleanup)
- Meta-coherence validation across repos
- WAL orchestration
- Pre-push hook coordination

## Structure

```
Alfred/
├── src/
│   ├── __init__.py
│   ├── coordination.py
│   └── meta_coherence.py
├── tests/
│   └── test_alfred_coordination.py
├── config/
│   └── settings.yaml
├── docs/
│   └── README.md
└── README.md
```

## Usage

```python
from src import AlfredCoordinator, MetaCoherenceChecker

coordinator = AlfredCoordinator()
tasks = coordinator.coordinate_branches("gerivdb/GOVERNANCE-HUB")
coordinator.dispatch_tasks(tasks)
coordinator.verify_meta_coherence(["gerivdb/GOVERNANCE-HUB"])

checker = MetaCoherenceChecker()
reports = checker.check_repos(["gerivdb/GOVERNANCE-HUB", "gerivdb/CTULU"])
```

## Governance

- **PRD-MOC**: `GOVERNANCE-HUB/PRD-MOC/PRD-MOC-ALFRED-MASTER-20261004.md`
- **MOC**: `GOVERNANCE-HUB/MOC/MOC-ALFRED.md`
- **IntentHash**: `0xPRD_MOC_ALFRED_ECOSYSTEM_INTEGRATION_20261004`

## Status

- **Repo**: `gerivdb/Alfred` (L0-CANON)
- **Entity Type**: CITIZEN
- **Status**: active

## Capacités opérationnelles (V1.1.0)

- `src/coordination.py` : `coordinate_branches()` retourne une liste réelle de `CoordinationTask` avec recommandations DELETE / PR_MERGE / CHERRY_PICK.
- `src/meta_coherence.py` : `check_repo()` vérifie README.md, .gitignore, remote configuré et branche main/master.
- `src/wal_writer.py` : WAL persistante sur disque (`.swarm/wal.jsonl`).
- `src/cli.py` : commandes `alfred coordinate`, `alfred check`, `alfred wal-status`.
- `runners/coordination_runner.py` : exécuteur de coordination avec WAL, gitex, syncx.
- `runners/cross_repo_audit_runner.py` : audit inter-dépôts (GOVERNANCE-HUB, TOPOS, BRAIN, CTULU, KG-L).
- `runners/agent_manager_fastapi.py` : API FastAPI (endpoints /alfred/*).

## Limitations connues

- `verify_meta_coherence()` dans `AlfredCoordinator` vérifie les repos passés en argument mais ne scanne pas automatiquement l'écosystème.
- Aucun mécanisme de planification (cron-like) n'est encore implémenté.
- L'API FastAPI n'est pas encore exposée en tant que service permanent.
