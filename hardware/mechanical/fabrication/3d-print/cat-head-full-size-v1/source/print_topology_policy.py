#!/usr/bin/env python3
"""Shared production-topology acceptance policy for cat-head print parts."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def is_single_closed_body(metrics: Mapping[str, Any]) -> bool:
    """Return true only for one connected, closed, manifold printable body."""

    return (
        int(metrics["connected_components"]) == 1
        and int(metrics["boundary_edges"]) == 0
        and int(metrics["nonmanifold_edges"]) == 0
    )


def all_single_closed_bodies(
    metrics: Iterable[Mapping[str, Any]],
) -> bool:
    """Apply the production topology contract to every supplied part."""

    values = list(metrics)
    return bool(values) and all(is_single_closed_body(value) for value in values)


def has_minimum_xy_boundary_clearance(
    orientation: Mapping[str, Any],
    per_side_clearance_mm: float,
) -> bool:
    """Check the two bed-plane dimensions against a per-side edge reserve.

    Gate 2 reports dimensions and the printer envelope in sorted order. The
    first two values therefore represent the two limiting bed-plane axes for
    the selected orientation; the largest axis remains the printer Z axis.
    This geometric reserve is measured before brim and support generation, so
    passing it is necessary but not sufficient for production slicing.
    """

    dimensions = [float(value) for value in orientation["oriented_dimensions_mm_sorted"]]
    envelope = [float(value) for value in orientation["envelope_mm_sorted"]]
    required_total_margin = 2.0 * float(per_side_clearance_mm)
    return (
        bool(orientation["fits"])
        and len(dimensions) == 3
        and len(envelope) == 3
        and all(envelope[index] - dimensions[index] >= required_total_margin for index in (0, 1))
    )


def require_all_acceptance(
    stage: str,
    acceptance: Mapping[str, bool],
) -> None:
    """Raise with every failed gate so generation exits nonzero."""

    failed = [name for name, passed in acceptance.items() if not passed]
    if failed:
        raise ValueError(f"{stage} validation failed: {failed}")
