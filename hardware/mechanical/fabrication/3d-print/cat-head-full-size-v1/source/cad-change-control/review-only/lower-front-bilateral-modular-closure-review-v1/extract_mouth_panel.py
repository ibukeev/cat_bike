#!/usr/bin/env python3
"""Read-only extraction of the two accepted mouth-opening source facets.

This script performs no CAD construction and writes no files.  It resolves
TRI005/TRI006 from the accepted Gate-1 OBJ, applies the pinned 330 mm master
transform, and prints ordered world-space vertices and outward normals.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
GATE1_GENERATOR = PROJECT_ROOT / "source/generate_gate1_master.py"
MOUTH_PANEL_IDS = ("TRI005", "TRI006")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def subtract(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return tuple(float(a[index]) - float(b[index]) for index in range(3))


def cross(a: Sequence[float], b: Sequence[float]) -> tuple[float, float, float]:
    return (
        float(a[1]) * float(b[2]) - float(a[2]) * float(b[1]),
        float(a[2]) * float(b[0]) - float(a[0]) * float(b[2]),
        float(a[0]) * float(b[1]) - float(a[1]) * float(b[0]),
    )


def dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(float(a[index]) * float(b[index]) for index in range(3))


def unit(values: Sequence[float]) -> tuple[float, float, float]:
    length = math.sqrt(dot(values, values))
    if length <= 1.0e-12:
        raise RuntimeError("zero-length vector")
    return tuple(float(value) / length for value in values)


def center(points: Iterable[Sequence[float]]) -> tuple[float, float, float]:
    values = list(points)
    return tuple(
        sum(float(point[index]) for point in values) / len(values)
        for index in range(3)
    )


def rounded_point(point: Sequence[float]) -> tuple[float, float, float]:
    return tuple(round(float(value), 12) for value in point)


def main() -> int:
    gate1 = load_module(GATE1_GENERATOR, "gate1_for_mouth_extraction")
    model = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    metadata = gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV)
    gate1.panel_units(model, metadata)
    source_bounds = gate1.bounds(model.vertices)
    scale, source_origin, _ = gate1.make_transform(source_bounds, 330.0)
    world_vertices = [
        gate1.transform_point(point, scale, source_origin)
        for point in model.vertices
    ]
    head_center = center(world_vertices)

    panels: dict[str, Any] = {}
    edge_owners: dict[tuple[tuple[float, float, float], tuple[float, float, float]], list[str]] = {}
    for panel_id in MOUTH_PANEL_IDS:
        faces = [
            face for face in model.faces
            if gate1.canonical_source_panel_id(face.group) == panel_id
        ]
        if len(faces) != 1 or len(faces[0].indices) != 3:
            raise RuntimeError(f"{panel_id} is not exactly one accepted triangle")
        points = [world_vertices[index] for index in faces[0].indices]
        panel_center = center(points)
        normal = unit(cross(subtract(points[1], points[0]), subtract(points[2], points[0])))
        away = subtract(panel_center, head_center)
        if dot(normal, away) < 0.0:
            normal = tuple(-value for value in normal)
        panels[panel_id] = {
            "ordered_vertices_world_mm": [list(map(float, point)) for point in points],
            "center_world_mm": list(map(float, panel_center)),
            "outward_normal": list(map(float, normal)),
            "inward_normal": [float(-value) for value in normal],
            "area_mm2": float(gate1.polygon_area(points)),
        }
        for first, second in zip(points, points[1:] + points[:1]):
            key = tuple(sorted((rounded_point(first), rounded_point(second))))
            edge_owners.setdefault(key, []).append(panel_id)

    shared = [
        {"endpoints_world_mm": [list(key[0]), list(key[1])], "owners": owners}
        for key, owners in edge_owners.items()
        if len(owners) == 2
    ]
    boundary = [
        {"endpoints_world_mm": [list(key[0]), list(key[1])], "owner": owners[0]}
        for key, owners in edge_owners.items()
        if len(owners) == 1
    ]
    if len(shared) != 1 or len(boundary) != 4:
        raise RuntimeError(
            f"unexpected two-facet mouth topology: shared={len(shared)}, boundary={len(boundary)}"
        )
    result = {
        "schema_version": "cat-head-mouth-panel-extraction-v1",
        "source_hashes": {
            "gate1_generator": sha256(GATE1_GENERATOR),
            "accepted_surface_obj": sha256(gate1.SOURCE_SURFACE_OBJ),
            "panel_metadata_csv": sha256(gate1.SOURCE_PANEL_CSV),
        },
        "target_height_mm": 330.0,
        "scale": float(scale),
        "source_origin_mm": list(map(float, source_origin)),
        "head_center_world_mm": list(map(float, head_center)),
        "panels": panels,
        "shared_edge": shared[0],
        "outer_boundary_edges": boundary,
        "io_trace": {
            "cad_opened": False,
            "geometry_created": False,
            "file_written": False,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
