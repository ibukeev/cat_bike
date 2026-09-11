#!/usr/bin/env python3
"""Deterministic micron-scale conditioning for the right-eye print mesh.

This is not a generic mesh repair routine.  It applies the exact operation
proven against the accepted conditioned front-carrier BRep:

* weld vertices no farther apart than 0.00002 mm;
* discard facets that collapse to zero area after that weld; and
* discard orientation-independent duplicate facets.

No smoothing, hole filling, remeshing, scaling, decimation, or coordinate
search is permitted.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
import math
from typing import Any


ALGORITHM_ID = "micron-weld-and-zero-area-filter-v1"
WELD_DISTANCE_MM = 0.00002
AREA2_EPSILON = 1.0e-12


def _subtract(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> tuple[float, float, float]:
    return tuple(first[index] - second[index] for index in range(3))


def _cross(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _length(value: tuple[float, float, float]) -> float:
    return math.sqrt(sum(component * component for component in value))


def facet_normal(
    points: list[tuple[float, float, float]],
    facet: tuple[int, int, int],
) -> tuple[tuple[float, float, float], float]:
    first, second, third = (points[index] for index in facet)
    value = _cross(_subtract(second, first), _subtract(third, first))
    magnitude = _length(value)
    if magnitude <= AREA2_EPSILON:
        return (0.0, 0.0, 0.0), magnitude
    return tuple(component / magnitude for component in value), magnitude


def weld_points(
    points: list[tuple[float, float, float]],
) -> tuple[
    list[tuple[float, float, float]],
    list[int],
    float,
    list[list[int]],
]:
    """Cluster vertices deterministically in original index order."""

    groups: list[list[int]] = []
    representatives: list[tuple[float, float, float]] = []
    mapping = [-1] * len(points)
    for point_index, point in enumerate(points):
        selected = None
        for group_index, representative in enumerate(representatives):
            if _length(_subtract(point, representative)) <= WELD_DISTANCE_MM:
                selected = group_index
                break
        if selected is None:
            selected = len(groups)
            groups.append([point_index])
            representatives.append(point)
        else:
            groups[selected].append(point_index)
            members = [points[index] for index in groups[selected]]
            representatives[selected] = tuple(
                sum(member[axis] for member in members) / len(members)
                for axis in range(3)
            )
        mapping[point_index] = selected
    maximum = max(
        (
            _length(_subtract(point, representatives[mapping[index]]))
            for index, point in enumerate(points)
        ),
        default=0.0,
    )
    return representatives, mapping, maximum, groups


def mesh_topology(mesh: Any) -> dict[str, Any]:
    """Return fail-closed topology and orientation measurements."""

    raw_points, raw_facets = mesh.Topology
    points = [
        (float(item.x), float(item.y), float(item.z))
        for item in raw_points
    ]
    facets = [tuple(map(int, item)) for item in raw_facets]
    edges: Counter[tuple[int, int]] = Counter()
    edge_facets: dict[tuple[int, int], list[int]] = defaultdict(list)
    adjacency: dict[int, set[int]] = defaultdict(set)
    degenerates = 0
    duplicates = 0
    seen: set[tuple[int, int, int]] = set()
    signed_volume = 0.0
    for facet_index, facet in enumerate(facets):
        if len(facet) != 3:
            raise RuntimeError(f"non-triangular facet at index {facet_index}")
        _, magnitude = facet_normal(points, facet)
        if len(set(facet)) < 3 or magnitude <= AREA2_EPSILON:
            degenerates += 1
        key = tuple(sorted(facet))
        if key in seen:
            duplicates += 1
        seen.add(key)
        first, second, third = (points[index] for index in facet)
        signed_volume += (
            first[0] * (second[1] * third[2] - second[2] * third[1])
            + first[1] * (second[2] * third[0] - second[0] * third[2])
            + first[2] * (second[0] * third[1] - second[1] * third[0])
        ) / 6.0
        for start, finish in (
            (facet[0], facet[1]),
            (facet[1], facet[2]),
            (facet[2], facet[0]),
        ):
            edge = tuple(sorted((start, finish)))
            edges[edge] += 1
            edge_facets[edge].append(facet_index)
    for linked in edge_facets.values():
        for facet_index in linked:
            adjacency[facet_index].update(
                other for other in linked if other != facet_index
            )
    unseen = set(range(len(facets)))
    component_count = 0
    while unseen:
        component_count += 1
        queue = deque([unseen.pop()])
        while queue:
            for neighbor in adjacency[queue.popleft()]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
    intersection_count: int | None = None
    getter = getattr(mesh, "getSelfIntersections", None)
    if callable(getter):
        intersection_count = len(getter())
    else:
        checker = getattr(mesh, "hasSelfIntersections", None)
        if callable(checker):
            intersection_count = 1 if bool(checker()) else 0
    box = mesh.BoundBox
    return {
        "algorithm_id": ALGORITHM_ID,
        "vertices": len(points),
        "facets": len(facets),
        "connected_components": component_count,
        "boundary_edges": sum(1 for count in edges.values() if count == 1),
        "nonmanifold_edges": sum(1 for count in edges.values() if count > 2),
        "degenerate_facets": degenerates,
        "duplicate_facets": duplicates,
        "self_intersection_count": intersection_count,
        "signed_volume_mm3": signed_volume,
        "outward_normals": signed_volume > 0.0,
        "bounds_mm": {
            "minimum": [float(box.XMin), float(box.YMin), float(box.ZMin)],
            "maximum": [float(box.XMax), float(box.YMax), float(box.ZMax)],
        },
    }


def condition_mesh(mesh: Any, Mesh: Any, App: Any) -> tuple[Any, dict[str, Any]]:
    """Apply only the pinned weld/filter operation and return fresh mesh."""

    raw_points, raw_facets = mesh.Topology
    original_points = [
        (float(item.x), float(item.y), float(item.z))
        for item in raw_points
    ]
    original_facets = [tuple(map(int, item)) for item in raw_facets]
    points, mapping, maximum_weld, groups = weld_points(original_points)
    facets: list[tuple[int, int, int]] = []
    removed_degenerate: list[int] = []
    removed_duplicate: list[int] = []
    seen: set[tuple[int, int, int]] = set()
    for facet_index, original in enumerate(original_facets):
        facet = tuple(mapping[index] for index in original)
        _, magnitude = facet_normal(points, facet)
        if len(set(facet)) < 3 or magnitude <= AREA2_EPSILON:
            removed_degenerate.append(facet_index)
            continue
        key = tuple(sorted(facet))
        if key in seen:
            removed_duplicate.append(facet_index)
            continue
        seen.add(key)
        facets.append(facet)
    conditioned = Mesh.Mesh([
        tuple(App.Vector(*points[index]) for index in facet)
        for facet in facets
    ])
    report = {
        "algorithm_id": ALGORITHM_ID,
        "automatic_repair_used": False,
        "coordinate_search_used": False,
        "smoothing_used": False,
        "hole_filling_used": False,
        "remeshing_used": False,
        "scaling_used": False,
        "maximum_allowed_weld_distance_mm": WELD_DISTANCE_MM,
        "maximum_weld_displacement_mm": maximum_weld,
        "weld_groups": [group for group in groups if len(group) > 1],
        "removed_degenerate_source_facets": removed_degenerate,
        "removed_duplicate_source_facets": removed_duplicate,
        "raw": mesh_topology(mesh),
        "conditioned": mesh_topology(conditioned),
    }
    return conditioned, report


def clean_manifold_mesh(metrics: dict[str, Any]) -> bool:
    return bool(
        metrics["connected_components"] == 1
        and metrics["boundary_edges"] == 0
        and metrics["nonmanifold_edges"] == 0
        and metrics["degenerate_facets"] == 0
        and metrics["duplicate_facets"] == 0
        and metrics["self_intersection_count"] == 0
        and metrics["outward_normals"]
        and float(metrics["signed_volume_mm3"]) > 0.0
    )

