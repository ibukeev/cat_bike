#!/usr/bin/env python3
"""Controlled right lower/rear V5 production-repartition review tooling.

The inventory mode is deliberately read-only.  It verifies immutable inputs
and measures the already-approved MANQ007 seam and named reinforcement owners.
Construction and review-save modes are added only after this source inventory
passes; neither STL nor G-code export is permitted by this lineage.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import bmesh
import bpy
from mathutils import Vector


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
CONTRACT_PATH = HERE / "contract.json"
SOURCE_DIR = PROJECT_ROOT / "source"
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

import generate_rear_cassette_seam_review_v2 as seam_v2  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    return (PROJECT_ROOT / value).resolve()


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schema_version") != "cat-head-right-lower-rear-v5-production-repartition-review-v1":
        raise RuntimeError("unexpected contract schema")
    return contract


def verify_inputs(contract: dict[str, Any]) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for key, item in contract["inputs"].items():
        path = project_path(item["path"])
        if not path.is_file():
            raise RuntimeError(f"missing input {key}: {path}")
        actual = sha256(path)
        expected = item.get("sha256")
        if expected and actual != expected:
            raise RuntimeError(f"input hash mismatch for {key}: {actual} != {expected}")
        records[key] = {"path": item["path"], "sha256": actual}
    return records


def mesh_metrics(obj: bpy.types.Object) -> dict[str, Any]:
    if obj.type != "MESH":
        raise RuntimeError(f"expected mesh object: {obj.name}")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    volume = abs(float(bm.calc_volume(signed=True)))
    boundary = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    nonmanifold = sum(1 for edge in bm.edges if not edge.is_manifold)
    bm.free()
    world = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    minimum = [min(point[index] for point in world) for index in range(3)]
    maximum = [max(point[index] for point in world) for index in range(3)]
    material_names = [material.name if material else "<none>" for material in obj.data.materials]
    material_faces = Counter(
        material_names[polygon.material_index] if polygon.material_index < len(material_names) else "<invalid>"
        for polygon in obj.data.polygons
    )
    return {
        "vertex_count": len(obj.data.vertices),
        "edge_count": len(obj.data.edges),
        "face_count": len(obj.data.polygons),
        "volume_mm3": volume,
        "boundary_edge_count": boundary,
        "nonmanifold_edge_count": nonmanifold,
        "world_bbox_minimum_mm": minimum,
        "world_bbox_maximum_mm": maximum,
        "matrix_world": [list(row) for row in obj.matrix_world],
        "material_face_count": dict(sorted(material_faces.items())),
    }


def require_object(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise RuntimeError(f"required accepted object missing: {name}")
    return obj


def inventory() -> dict[str, Any]:
    contract = load_contract()
    inputs = verify_inputs(contract)
    opened = Path(bpy.data.filepath).resolve()
    expected_blend = project_path(contract["inputs"]["accepted_structural_blend"]["path"])
    if opened != expected_blend:
        raise RuntimeError(f"wrong Blender source opened: {opened} != {expected_blend}")

    ownership = json.loads(
        project_path(contract["inputs"]["ownership_validation"]["path"]).read_text(encoding="utf-8")
    )
    right_records = {
        record["review_object"]: record
        for record in ownership["component_records"]
        if record["section"] == "right_lower_face"
    }
    expected_crossing = contract["right_reinforcement"]["crossing_objects"]
    if any(right_records.get(name, {}).get("classification") != "crossing" for name in expected_crossing):
        raise RuntimeError("crossing-object contract no longer matches ownership ledger")
    excluded = contract["right_reinforcement"]["excluded_rejected_objects"]
    if any(right_records.get(name, {}).get("classification") != "unclassified" for name in excluded):
        raise RuntimeError("excluded-object contract no longer matches ownership ledger")

    required_names = (
        expected_crossing
        + excluded
        + contract["right_reinforcement"]["accepted_additions"]
    )
    object_metrics = {name: mesh_metrics(require_object(name)) for name in required_names}
    v5_config = json.loads(
        project_path(contract["inputs"]["approved_v5_config"]["path"]).read_text(encoding="utf-8")
    )
    interface = json.loads(
        project_path(contract["inputs"]["shared_interface"]["path"]).read_text(encoding="utf-8")
    )
    selection_config = dict(v5_config)
    selection_config["rear_cassette_cut"] = dict(v5_config["repartition"])
    _model, _assignments, points, _selected, seam_edges = seam_v2.source_selection(
        selection_config, interface
    )
    right_edges = [
        edge for edge in seam_edges
        if sum(float(points[index][0]) for index in edge) / 2.0 > 0.0
    ]
    if len(right_edges) != 1:
        raise RuntimeError(f"expected one approved right diagonal seam edge, found {right_edges}")
    seam_edge = right_edges[0]
    seam_endpoints = [Vector(points[index]) for index in seam_edge]
    seam_length = float((seam_endpoints[1] - seam_endpoints[0]).length)
    expected_length = float(contract["approved_v5_ownership"]["expected_diagonal_seam_length_mm"])
    if abs(seam_length - expected_length) > 0.01:
        raise RuntimeError(f"approved seam length drift: {seam_length} != {expected_length}")

    return {
        "schema_version": "cat-head-right-lower-rear-v5-production-repartition-inventory-v1",
        "status": "PASS__SOURCE_INVENTORY_ONLY__NO_GEOMETRY_OUTPUT",
        "authority": contract["authority"],
        "input_records": inputs,
        "opened_blend": str(opened),
        "right_crossing_count": len(expected_crossing),
        "right_excluded_count": len(excluded),
        "right_accepted_addition_count": len(contract["right_reinforcement"]["accepted_additions"]),
        "object_metrics": object_metrics,
        "seam_interface": {
            "definition": contract["approved_v5_ownership"]["seam_definition"],
            "display_object": contract["approved_v5_ownership"]["seam_display_object"],
            "edge_vertex_indices": list(seam_edge),
            "world_endpoints_mm": [list(point) for point in seam_endpoints],
            "length_mm": seam_length,
        },
        "io_trace": {
            "source_blend_saved": False,
            "review_blend_saved": False,
            "geometry_export_created": False,
            "production_output_created": False,
        },
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("inventory",), required=True)
    parser.add_argument("--report", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[sys.argv.index("--") + 1 :] if argv is None and "--" in sys.argv else (argv or []))
    result = inventory()
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.report:
        if not str(args.report.resolve()).startswith("/tmp/"):
            raise RuntimeError("inventory report must remain under /tmp")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
