#!/usr/bin/env python3
"""
Alfred TOPOS Ops Bridge v1.0
Reads TOPOS EECS matrix and exposes operational view.

Bridge: TOPOS-ALFRED-OPS (active - consumer side)
IntentHash: 0xTOPOS_ALFRED_BRIDGE_20260603
"""

__version__ = "1.0.0"

import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ToposOpsBridge:
    """Reads TOPOS EECS matrix for Alfred operational view."""

    def __init__(self):
        self._matrices: List[Dict] = []
        self._ops_views: List[Dict] = []

    def read_matrix(self, matrix_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Read TOPOS EECS matrix and produce operational view.

        Matrix format:
        {
            "matrix_id": "eecs-v1",
            "timestamp": "2026-06-11T04:00:00Z",
            "axes": ["repo", "layer", "status"],
            "entries": [
                {"repo": "NEXUS", "layer": "L0", "status": "active"}
            ]
        }
        """
        matrix_id = matrix_data.get("matrix_id", "unknown")
        timestamp = matrix_data.get("timestamp", "")
        axes = matrix_data.get("axes", [])
        entries = matrix_data.get("entries", [])

        # Build operational view
        by_status: Dict[str, List[str]] = {}
        by_layer: Dict[str, List[str]] = {}

        for entry in entries:
            status = entry.get("status", "unknown")
            layer = entry.get("layer", "unknown")
            repo = entry.get("repo", "unknown")

            by_status.setdefault(status, []).append(repo)
            by_layer.setdefault(layer, []).append(repo)

        ops_view = {
            "matrix_id": matrix_id,
            "timestamp": timestamp,
            "total_entries": len(entries),
            "axes": axes,
            "by_status": {k: v for k, v in by_status.items()},
            "by_layer": {k: v for k, v in by_layer.items()},
            "active_count": len(by_status.get("active", [])),
            "dormant_count": len(by_status.get("dormant", [])),
            "deprecated_count": len(by_status.get("deprecated", []))
        }

        self._matrices.append(matrix_data)
        self._ops_views.append(ops_view)

        logger.info("Alfred read matrix %s: %d entries, %d active",
                     matrix_id, len(entries), ops_view["active_count"])
        return ops_view

    @property
    def matrix_count(self) -> int:
        return len(self._matrices)
