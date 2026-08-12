#!/usr/bin/env python3
"""Required-source retention gate for cat-head Boolean owner builds."""

from __future__ import annotations

from collections.abc import Mapping


def all_required_sources_retained(
    retained_volume_mm3_by_source: Mapping[str, float],
    minimum_retained_volume_mm3: float = 1.0e-6,
) -> bool:
    """Return true only when every required source survives the final owner.

    A CAD Boolean can report one valid solid while silently dropping a tangent
    or sub-tolerance source. Callers must measure the common volume between the
    final owner and each required source and provide the complete source ledger.
    """

    minimum = float(minimum_retained_volume_mm3)
    if minimum <= 0.0:
        raise ValueError("minimum_retained_volume_mm3 must be positive")
    values = list(retained_volume_mm3_by_source.values())
    return bool(values) and all(float(value) >= minimum for value in values)
