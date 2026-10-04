"""
Alfred — Configuration schema
Pydantic-based configuration validation.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from pydantic import BaseModel, Field


class AlfredConfig(BaseModel):
    """Alfred configuration model."""

    name: str = "alfred"
    version: str = "1.0.0"
    status: str = "active"
    layer: str = "L0"
    type: str = "citizen"
    profile: str = "STANDARD"
    intent_hash: str = "0xALFRED_CONFIG_20261004"
    role: str = "Operational Coordination Assistant"
    capabilities: List[str] = Field(
        default_factory=lambda: [
            "branch-lifecycle",
            "pre-push-coordination",
            "meta-coherence-check",
            "wal-orchestration",
        ]
    )
    dependencies: List[str] = Field(
        default_factory=lambda: [
            "bat-family-agents",
            "session-boot-sequence",
            "pr-merge-strategy",
        ]
    )
    wal_path: Path = Path(".swarm/wal.jsonl")
    governance: dict = Field(
        default_factory=lambda: {
            "prd_moc": "PRD-MOC/PRD-MOC-ALFRED-MASTER-20261004.md",
            "moc": "MOC/MOC-ALFRED.md",
            "intent_hash": "0xPRD_MOC_ALFRED_ECOSYSTEM_INTEGRATION_20261004",
        }
    )

    class Config:
        frozen = True
