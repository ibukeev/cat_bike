#!/usr/bin/env python3
"""Remove only the disconnected legacy lower-face eye-flange neck component."""

from __future__ import annotations

import json
import sys
from collections import deque
from pathlib import Path
from typing import Any

import bmesh
import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_right_eye_outer_pair_face879_depth_extension_review_v3 as v3

PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/right-eye-second-pair-neck-removal-review-v9.json"

LOWER_FACE = "right_lower_face"
UPPER_HEAD = "right_upper_head"
EYE_BUCKET = "FROZEN__RIGHT_EYE_BUCKET_V9_V6"
FLANGE_NAMES = {
    "outer_head": "PROPOSED__RIGHT_OUTER_HEAD__PLAIN_FLANGE_4P8MM_LOCAL_SKIN_CLIPPED_V7",
    "outer_eye": "PROPOSED__RIGHT_OUTER_EYE__PLAIN_FLANGE_4P8MM_LOCAL_SKIN_CLIPPED_V7",
    "second_head": "PROPOSED__RIGHT_LOWER_HEAD__PLAIN_FLANGE_4P8MM_LOCAL_SKIN_CLIPPED_V7",
    "second_eye": "PROPOSED__RIGHT_LOWER_EYE__PLAIN_FLANGE_4P8MM_LOCAL_SKIN_CLIPPED_V7",
}


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def components(obj: bpy.types.Object) -> list[set[int]]:
    adjacency: list[set[int]] = [set() for _ in obj.data.vertices]
    for edge in obj.data.edges:
        first, second = edge.vertices
        adjacency[first].add(second)
        adjacency[second].add(first)
    unseen = set(range(len(obj.data.vertices)))
    result: list[set[int]] = []
    while unseen:
        seed = unseen.pop()
        current = {seed}
        queue = deque([seed])
        while queue:
            index = queue.popleft()
            for neighbor in adjacency[index]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    current.add(neighbor)
                    queue.append(neighbor)
        result.append(current)
    return result


def world_bbox(obj: bpy.types.Object, indices: set[int]) -> tuple[Vector, Vector]:
    points = [obj.matrix_world @ obj.data.vertices[index].co for index in indices]
    low = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    return low, high


def minimum_vertex_distance(
    first: bpy.types.Object,
    indices: set[int],
    second: bpy.types.Object,
) -> float:
    first_points = [first.matrix_world @ first.data.vertices[index].co for index in indices]
    second_points = [second.matrix_world @ vertex.co for vertex in second.data.vertices]
    return min((a - b).length for a in first_points for b in second_points)


def matching_component(
    lower: bpy.types.Object,
    flange: bpy.types.Object,
    contract: dict[str, Any],
) -> tuple[set[int], dict[str, Any]]:
    tolerance = float(contract["bbox_tolerance_mm"])
    expected_low = Vector(contract["removed_component_bbox_min_mm"])
    expected_high = Vector(contract["removed_component_bbox_max_mm"])
    matches = []
    for indices in components(lower):
        faces = [
            polygon for polygon in lower.data.polygons
            if all(index in indices for index in polygon.vertices)
        ]
        low, high = world_bbox(lower, indices)
        distance = minimum_vertex_distance(lower, indices, flange)
        if (
            len(indices) == int(contract["removed_component_vertex_count"])
            and len(faces) == int(contract["removed_component_face_count"])
            and all(abs(low[i] - expected_low[i]) <= tolerance for i in range(3))
            and all(abs(high[i] - expected_high[i]) <= tolerance for i in range(3))
            and distance <= float(contract["maximum_component_distance_to_lower_head_flange_mm"])
        ):
            matches.append((indices, {
                "vertex_count": len(indices),
                "face_count": len(faces),
                "bbox_min_mm": [round(value, 5) for value in low],
                "bbox_max_mm": [round(value, 5) for value in high],
                "minimum_vertex_distance_to_flange_mm": round(distance, 6),
            }))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one locked neck component; found {len(matches)}")
    return matches[0]


def delete_vertices(obj: bpy.types.Object, indices: set[int]) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        bm.verts.ensure_lookup_table()
        bmesh.ops.delete(bm, geom=[bm.verts[index] for index in sorted(indices)], context="VERTS")
        bm.to_mesh(obj.data)
        obj.data.update()
    finally:
        bm.free()


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source = repo_path(config["source_v7_blend"])
    if Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError(f"open controlled V7 source: {source}")
    output = repo_path(config["output_dir"])
    review = output / "review"
    review.mkdir(parents=True, exist_ok=True)
    contract = config["locked_contract"]

    source_lower = bpy.data.objects[LOWER_FACE]
    upper = bpy.data.objects[UPPER_HEAD]
    bucket = bpy.data.objects[EYE_BUCKET]
    source_flanges = {key: bpy.data.objects[name] for key, name in FLANGE_NAMES.items()}

    revised_lower = v3.duplicate(source_lower, "PROPOSED__RIGHT_LOWER_FACE__LEGACY_EYE_NECK_REMOVED_V9")
    retained_flanges = {
        key: v3.duplicate(obj, f"RETAINED__V9__{key.upper()}__UNCHANGED")
        for key, obj in source_flanges.items()
    }
    before_topology = v3.topology(revised_lower)
    before_fingerprint = v3.fingerprint(revised_lower)
    before_component_count = len(components(revised_lower))
    target, removed_record = matching_component(
        revised_lower, retained_flanges["second_head"], contract
    )
    delete_vertices(revised_lower, target)
    after_topology = v3.topology(revised_lower)
    after_fingerprint = v3.fingerprint(revised_lower)
    after_component_count = len(components(revised_lower))

    if before_topology["vertices"] - after_topology["vertices"] != int(contract["removed_component_vertex_count"]):
        raise RuntimeError("unexpected lower-face vertex deletion count")
    if before_topology["faces"] - after_topology["faces"] != int(contract["removed_component_face_count"]):
        raise RuntimeError("unexpected lower-face face deletion count")
    if before_component_count - after_component_count != 1:
        raise RuntimeError("lower-face component count did not decrease by exactly one")

    flange_records = {}
    for key in retained_flanges:
        source_obj = source_flanges[key]
        retained_obj = retained_flanges[key]
        source_fingerprint = v3.fingerprint(source_obj)
        retained_fingerprint = v3.fingerprint(retained_obj)
        if retained_fingerprint != source_fingerprint:
            raise RuntimeError(f"{key} flange changed")
        flange_records[key] = {
            "source_object": source_obj.name,
            "review_object": retained_obj.name,
            "fingerprint": retained_fingerprint,
            "topology": v3.topology(retained_obj),
        }

    head = retained_flanges["second_head"]
    eye = retained_flanges["second_eye"]
    pair_interference = v3.intersection_volume(head, eye)
    pair_gap = v3.distance(head, eye)
    if pair_interference > 0.001:
        raise RuntimeError(f"retained second pair interferes: {pair_interference}")
    if abs(pair_gap - float(contract["mating_gap_mm"])) > float(contract["maximum_pair_gap_error_mm"]):
        raise RuntimeError(f"retained second pair gap changed: {pair_gap}")

    lower_overlap = v3.intersection_volume(head, revised_lower)
    upper_overlap = v3.intersection_volume(head, upper)

    frozen_material = v3.material("FROZEN__V9_CONTEXT", (0.36, 0.40, 0.45, 1.0))
    revised_material = v3.material("PROPOSED__V9_NECK_REMOVED", (0.12, 0.64, 0.32, 1.0))
    retained_material = v3.material("RETAINED__V9_FLANGES", (0.95, 0.55, 0.10, 1.0))
    v3.assign(source_lower, frozen_material)
    v3.assign(upper, frozen_material)
    v3.assign(bucket, frozen_material)
    v3.assign(revised_lower, revised_material)
    for obj in retained_flanges.values():
        v3.assign(obj, retained_material)

    v3.export_obj(revised_lower, review / "right_lower_face_neck_removed_v9.obj")
    v3.export_obj(upper, review / "right_upper_head_context_v9.obj")
    v3.export_obj(bucket, review / "right_eye_bucket_context_v9.obj")
    for key, obj in retained_flanges.items():
        v3.export_obj(obj, review / f"{key}_unchanged_v9.obj")

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    camera_data = bpy.data.cameras.new("V9_REVIEW_CAMERA")
    camera = bpy.data.objects.new("V9_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 58
    second_pair = {retained_flanges["second_head"], retained_flanges["second_eye"]}
    renders = [
        v3.render(camera, output, "01-v9-before-neck-removal", (20, 100, 150), (67, 65, 120), {source_lower, *second_pair}),
        v3.render(camera, output, "02-v9-after-neck-removal", (20, 100, 150), (67, 65, 120), {revised_lower, *second_pair}),
        v3.render(camera, output, "03-v9-after-full-owner-context", (110, 100, 150), (67, 65, 120), {upper, revised_lower, bucket, *second_pair}),
    ]

    validation = {
        "status": config["status"],
        "locked_contract": contract,
        "removed_component": removed_record,
        "lower_face_before": {
            "topology": before_topology,
            "component_count": before_component_count,
            "fingerprint": before_fingerprint,
        },
        "lower_face_after": {
            "topology": after_topology,
            "component_count": after_component_count,
            "fingerprint": after_fingerprint,
        },
        "flanges": flange_records,
        "retained_second_pair": {
            "minimum_clearance_mm": round(pair_gap, 4),
            "interference_mm3": round(pair_interference, 6),
            "head_leaf_overlap_revised_lower_face_mm3": round(lower_overlap, 4),
            "head_leaf_overlap_upper_head_mm3": round(upper_overlap, 4),
        },
        "geometry_changed": [revised_lower.name],
        "flange_geometry_changed": False,
        "flange_location_changed": False,
        "owner_boolean_performed": False,
        "mirror_performed": False,
        "no_stl_or_gcode_exported": True,
        "holds": config["holds"],
        "generated_files": {"renders": renders},
    }
    (output / "validation-v9.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "CAT_HEAD_RIGHT_EYE_SECOND_PAIR_NECK_REMOVAL_REVIEW_V9.blend"))


if __name__ == "__main__":
    main()
