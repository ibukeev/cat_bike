#!/usr/bin/env python3
"""Read-only localization of the V2 repair-to-shell zero-clearance contact."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
V2_PATH = PROJECT_ROOT / "source/cad-change-control/review-only/right-eye-carrier-full-depth-seam-repair-v2/generate_review.py"
V2_SHA256 = "c49e6f6cb87b06f5f997e424dabfe922d8be0e82d684432884414f319c8d6a9d"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def vector_record(vector: Any) -> list[float]:
    return [float(vector.x), float(vector.y), float(vector.z)]


def bbox_record(shape: Any) -> dict[str, list[float]] | None:
    if shape.isNull() or (not shape.Vertexes and not shape.Edges and not shape.Faces):
        return None
    box = shape.BoundBox
    return {
        "minimum_mm": [float(box.XMin), float(box.YMin), float(box.ZMin)],
        "maximum_mm": [float(box.XMax), float(box.YMax), float(box.ZMax)],
    }


def main() -> int:
    actual = sha256(V2_PATH)
    if actual != V2_SHA256:
        raise RuntimeError(f"V2 generator hash mismatch: {actual}")
    v2 = load_module(V2_PATH, "_pinned_v2_corner_contact_measurement")
    context = v2.prepare()
    v2.construct(context)
    added = context["added"]
    components = {
        "source_carrier": context["final_shapes"]["carrier"],
        "full_depth_spine": context["full_depth_spine"],
        "structural_backing": context["structural_backing"],
        "reinforcement": context["reinforcement"],
        "added": added,
    }
    near: list[dict[str, Any]] = []
    for owner_name, owner in context["shell_records"]:
        if not context["v3_module"].aabb_near(added, owner, 2.0):
            continue
        result = added.distToShape(owner)
        distance = float(result[0])
        if distance > 2.0:
            continue
        pairs = [
            {"repair_mm": vector_record(pair[0]), "shell_mm": vector_record(pair[1])}
            for pair in result[1][:12]
        ]
        section = added.section(owner)
        component_distances = {}
        for component_name, component in components.items():
            component_result = component.distToShape(owner)
            component_distances[component_name] = {
                "distance_mm": float(component_result[0]),
                "positive_common_mm3": float(component.common(owner).Volume),
            }
        near.append({
            "owner": str(owner_name),
            "distance_mm": distance,
            "positive_common_mm3": float(added.common(owner).Volume),
            "closest_pairs": pairs,
            "section_edge_count": len(section.Edges) if not section.isNull() else 0,
            "section_vertex_count": len(section.Vertexes) if not section.isNull() else 0,
            "section_bbox": bbox_record(section),
            "section_vertices_mm": [vector_record(vertex.Point) for vertex in section.Vertexes[:24]],
            "component_distances": component_distances,
        })
    near.sort(key=lambda item: (item["distance_mm"], item["owner"]))
    report = {
        "schema_version": "cat-head-right-eye-carrier-v2-corner-contact-measurement-v1",
        "status": "MEASUREMENT_COMPLETE__NO_GEOMETRY_WRITE",
        "v2_generator_sha256": actual,
        "shell_owner_count": len(context["shell_records"]),
        "owners_within_2mm": near,
        "minimum_distance_mm": min((item["distance_mm"] for item in near), default=None),
        "io_trace": {
            "source_saved": False,
            "review_saved": False,
            "geometry_export_created": False,
            "production_output_created": False,
        },
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
