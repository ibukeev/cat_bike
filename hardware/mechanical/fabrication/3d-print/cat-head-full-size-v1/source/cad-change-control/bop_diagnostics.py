#!/usr/bin/env python3
"""Pure helpers for parsing deterministic OCCT BOP diagnostics."""

from __future__ import annotations

import re
from typing import Any


BOP_DIAGNOSTIC_RE = re.compile(
    r"^Error in (?P<subshape>Face|Edge|Vertex): BOPAlgo (?P<error>[A-Za-z0-9_]+)$"
)


def parse_bop_diagnostics(messages: list[str]) -> list[dict[str, Any]]:
    """Extract ordered BOP diagnostics from FreeCAD check messages."""
    diagnostics: list[dict[str, Any]] = []
    for message_index, message in enumerate(messages, start=1):
        for line_index, raw_line in enumerate(str(message).splitlines(), start=1):
            match = BOP_DIAGNOSTIC_RE.match(raw_line.strip())
            if match is None:
                continue
            diagnostics.append(
                {
                    "message_index": message_index,
                    "line_index": line_index,
                    "subshape_type": match.group("subshape"),
                    "error": match.group("error"),
                }
            )
    return diagnostics
