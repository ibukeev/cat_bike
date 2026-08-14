#!/usr/bin/env python3
"""Build an isolated exact self-union candidate for V12 lower-face component 001."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/right-lower-face-topology-repair-review-v12.json"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def bounds(obj: bpy.types.Object) -> dict[str, list[float]]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return {
        "min": [min(point[axis] for point in points) for axis in range(3)],
        "max": [max(point[axis] for point in points) for axis in range(3)],
    }


def topology(obj: bpy.types.Object) -> dict[str, int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        return {
            "vertices": len(bm.verts),
            "edges": len(bm.edges),
            "faces": len(bm.faces),
            "boundary_edges": sum(1 for edge in bm.edges if edge.is_boundary),
            "nonmanifold_edges": sum(1 for edge in bm.edges if not edge.is_manifold),
        }
    finally:
        bm.free()


def self_intersection_count(obj: bpy.types.Object) -> int:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        bm.verts.index_update()
        bm.faces.index_update()
        tree = BVHTree.FromBMesh(bm, epsilon=0.0)
        pairs: set[tuple[int, int]] = set()
        for first_index, second_index in tree.overlap(tree):
            if first_index == second_index:
                continue
            pair = tuple(sorted((first_index, second_index)))
            if pair in pairs:
                continue
            first = bm.faces[pair[0]]
            second = bm.faces[pair[1]]
            if {vertex.index for vertex in first.verts} & {
                vertex.index for vertex in second.verts
            }:
                continue
            pairs.add(pair)
        return len(pairs)
    finally:
        bm.free()


def max_candidate_to_source_surface_deviation(
    candidate: bpy.types.Object,
    reference: bpy.types.Object,
) -> float:
    depsgraph = bpy.context.evaluated_depsgraph_get()
    reference_tree = BVHTree.FromObject(reference, depsgraph)
    distances: list[float] = []
    for polygon in candidate.data.polygons:
        coordinates = [
            candidate.matrix_world @ candidate.data.vertices[index].co
            for index in polygon.vertices
        ]
        samples = coordinates + [sum(coordinates, Vector()) / len(coordinates)]
        for point in samples:
            nearest = reference_tree.find_nearest(point)
            if nearest is None:
                raise RuntimeError("Surface-deviation query failed")
            distances.append(float(nearest[3]))
    return max(distances, default=0.0)


def main() -> None:
    config = json.loads(parse_args().config.resolve().read_text())
    locked = config["locked_contract"]
    output_dir = repo_path(config["output_dir"])
    inventory_path = output_dir / "component-inventory-v12.json"
    inventory = json.loads(inventory_path.read_text())
    record = inventory["components"][0]
    source_path = repo_path(record["path"])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.wm.obj_import(filepath=str(source_path))
    source = bpy.context.selected_objects[0]
    source.name = "FROZEN__RIGHT_LOWER_FACE__COMPONENT_001_V12"
    if sha256(source_path) != locked["component_001_obj_sha256"]:
        raise RuntimeError("Frozen component 001 OBJ SHA-256 changed")
    reference = source.copy()
    reference.data = source.data.copy()
    reference.name = "VALIDATION_ONLY__COMPONENT_001_REFERENCE_V12"
    bpy.context.scene.collection.objects.link(reference)

    candidate = source.copy()
    candidate.data = source.data.copy()
    candidate.name = "PROPOSED__RIGHT_LOWER_FACE__COMPONENT_001_SELF_UNION_V12"
    bpy.context.scene.collection.objects.link(candidate)
    tool = candidate.copy()
    tool.data = candidate.data.copy()
    tool.name = "TOOL__COMPONENT_001_SELF_UNION_V12"
    bpy.context.scene.collection.objects.link(tool)

    bpy.context.view_layer.objects.active = candidate
    candidate.select_set(True)
    modifier = candidate.modifiers.new("MANIFOLD_SELF_UNION_V12", "BOOLEAN")
    modifier.operation = "UNION"
    modifier.solver = "MANIFOLD"
    modifier.object = tool
    if hasattr(modifier, "use_self"):
        modifier.use_self = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(tool, do_unlink=True)

    bm = bmesh.new()
    bm.from_mesh(candidate.data)
    try:
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(candidate.data)
    finally:
        bm.free()
    candidate.data.update(calc_edges=True)
    bpy.context.view_layer.update()

    source_bounds = bounds(source)
    candidate_bounds = bounds(candidate)
    bbox_deviation = max(
        abs(source_bounds[key][axis] - candidate_bounds[key][axis])
        for key in ("min", "max")
        for axis in range(3)
    )
    deviation = max_candidate_to_source_surface_deviation(candidate, reference)
    result = {
        "status": "PASS_BLENDER_ISOLATED" if (
            topology(candidate)["boundary_edges"] == 0
            and topology(candidate)["nonmanifold_edges"] == 0
            and self_intersection_count(candidate) == 0
            and deviation <= float(locked["maximum_surface_deviation_mm"])
            and bbox_deviation <= float(locked["maximum_bbox_deviation_mm"])
        ) else "FAIL",
        "source": str(source_path.relative_to(REPO_ROOT)),
        "source_sha256": record["fingerprint"],
        "source_topology": topology(source),
        "candidate_topology": topology(candidate),
        "source_self_intersections": self_intersection_count(source),
        "candidate_self_intersections": self_intersection_count(candidate),
        "maximum_candidate_to_source_surface_deviation_mm": deviation,
        "maximum_bbox_deviation_mm": bbox_deviation,
        "source_bounds": source_bounds,
        "candidate_bounds": candidate_bounds,
        "production_union_performed": False,
        "scope": "component 001 only; no other component or interface changed",
    }
    candidate_dir = output_dir / "component-001-self-union-manifold"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    validation_path = candidate_dir / "validation.json"
    validation_path.write_text(json.dumps(result, indent=2) + "\n")

    for obj in bpy.context.scene.objects:
        obj.hide_render = obj not in {candidate}
        obj.hide_viewport = obj not in {candidate}
    blend_path = candidate_dir / "CAT_HEAD_RIGHT_LOWER_FACE_COMPONENT_001_SELF_UNION_REVIEW_V12.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.context.view_layer.objects.active = candidate
    candidate.select_set(True)
    obj_path = candidate_dir / "right_lower_face_component_001_self_union_v12.obj"
    bpy.ops.wm.obj_export(filepath=str(obj_path), export_selected_objects=True)
    result["proposal_blend"] = str(blend_path.relative_to(REPO_ROOT))
    result["proposal_obj"] = str(obj_path.relative_to(REPO_ROOT))
    result["proposal_obj_sha256"] = sha256(obj_path)
    validation_path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result["status"] != "PASS_BLENDER_ISOLATED":
        raise RuntimeError("Component 001 exact self-union failed locked V12 gates")


if __name__ == "__main__":
    main()
