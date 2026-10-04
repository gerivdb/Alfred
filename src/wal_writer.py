"""
Alfred — WAL Writer
Write-ahead log for coordination actions.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class WALWriter:
    """Write-ahead log for Alfred coordination actions."""

    def __init__(self, wal_path: Path | None = None) -> None:
        self.wal_path = Path(wal_path or ".swarm/wal.jsonl")
        self.wal_path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, action: str, **kwargs: Any) -> dict:
        """Append entry to WAL and return it."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            **kwargs,
        }
        with open(self.wal_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def count(self) -> int:
        """Count entries in WAL."""
        if not self.wal_path.exists():
            return 0
        return sum(1 for _ in open(self.wal_path, encoding="utf-8"))

    def read(self, limit: int | None = None) -> list[dict]:
        """Read entries from WAL."""
        if not self.wal_path.exists():
            return []
        entries = []
        with open(self.wal_path, encoding="utf-8") as f:
            for i, line in enumerate(f):
                if limit and i >= limit:
                    break
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return entries
