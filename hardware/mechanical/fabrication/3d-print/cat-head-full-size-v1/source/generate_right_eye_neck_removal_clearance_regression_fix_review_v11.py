#!/usr/bin/env python3
"""Carry the accepted V10 neck removal onto the approved V2 eye-clearance state."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_right_eye_outer_neck_removal_upper_head_owner_review_v10 as v10
import generate_right_eye_reinforcement_clearance_review_v2 as v2

PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/right-eye-neck-removal-clearance-regression-fix-review-v11.json"


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def create_trimmed(source: bpy.types.Object, fraction: float, name: str) -> bpy.types.Object:
    world = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    vertices = [world[index].lerp(world[index + 3], fraction) for index in range(3)] + world[3:]
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(vertices, [], [tuple(polygon.vertices) for polygon in source.data.polygons])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def create_offset(source: bpy.types.Object, offset: Vector, name: str) -> bpy.types.Object:
    vertices = [source.matrix_world @ vertex.co + offset for vertex in source.data.vertices]
    faces = [tuple(polygon.vertices) for polygon in source.data.polygons]
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def component_record(obj: bpy.types.Object, indices: set[int]) -> dict[str, Any]:
    faces = v10.component_faces(obj, indices)
    low, high = v10.v9.world_bbox(obj, indices)
    return {
        "vertex_count": len(indices),
        "face_count": len(faces),
        "bbox_min_mm": [round(value, 5) for value in low],
        "bbox_max_mm": [round(value, 5) for value in high],
    }


def remove_locked_component(
    obj: bpy.types.Object,
    definition: dict[str, Any],
    tolerance: float,
) -> dict[str, Any]:
    indices, record = v10.component_matching_bbox(
        obj,
        int(definition["vertex_count"]),
        int(definition["face_count"]),
        definition["bbox_min_mm"],
        definition["bbox_max_mm"],
        tolerance,
    )
    v10.v9.delete_vertices(obj, indices)
    return record


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source = repo_path(config["source_v10_blend"])
    if Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError(f"open controlled V10 source: {source}")

    output = repo_path(config["output_dir"])
    review = output / "review"
    review.mkdir(parents=True, exist_ok=True)
    names = config["objects"]
    contract = config["locked_contract"]

    source_lower = bpy.data.objects[names["v10_lower_face"]]
    upper = bpy.data.objects[names["upper_head"]]
    eye = bpy.data.objects[names["eye_bucket"]]
    c046_source = bpy.data.objects[names["c046_source"]]
    c048_source = bpy.data.objects[names["c048_source"]]
    source_flanges = {
        "outer_head": bpy.data.objects[names["outer_head_flange"]],
        "outer_eye": bpy.data.objects[names["outer_eye_flange"]],
        "second_head": bpy.data.objects[names["second_head_flange"]],
        "second_eye": bpy.data.objects[names["second_eye_flange"]],
    }

    lower = v10.v9.v3.duplicate(
        source_lower,
        "PROPOSED__RIGHT_LOWER_FACE__V10_NECK_REMOVAL_WITH_V2_CLEARANCE_RESTORED_V11",
    )
    flanges = {
        key: v10.v9.v3.duplicate(obj, f"RETAINED__V11__{key.upper()}__UNCHANGED")
        for key, obj in source_flanges.items()
    }

    v10_validation = json.loads(repo_path(config["source_v10_validation"]).read_text(encoding="utf-8"))
    v2_validation = json.loads(repo_path(config["source_v2_validation"]).read_text(encoding="utf-8"))
    source_lower_topology = v10.v9.v3.topology(source_lower)
    source_lower_fingerprint = v10.v9.v3.fingerprint(source_lower)
    if source_lower_topology != v10_validation["lower_face_after"]["topology"]:
        raise RuntimeError("V10 lower-face topology no longer matches its accepted validation")

    tolerance = float(contract["bbox_tolerance_mm"])
    removed_c046 = remove_locked_component(lower, contract["stale_c046"], tolerance)
    removed_c048 = remove_locked_component(lower, contract["stale_c048"], tolerance)
    lower_topology = v10.v9.v3.topology(lower)
    if source_lower_topology["vertices"] - lower_topology["vertices"] != 12:
        raise RuntimeError("regression repair removed an unexpected number of vertices")
    if source_lower_topology["faces"] - lower_topology["faces"] != 12:
        raise RuntimeError("regression repair removed an unexpected number of faces")
    if len(v10.v9.components(source_lower)) - len(v10.v9.components(lower)) != 2:
        raise RuntimeError("regression repair removed anything other than the two stale rib components")

    c046 = create_offset(
        c046_source,
        Vector(contract["c046_away_unit"]) * float(contract["c046_rigid_offset_mm"]),
        "RESTORED__R1_RET__R__C046__APPROVED_CLEARANCE_V2__V11",
    )
    c048 = create_trimmed(
        c048_source,
        float(contract["c048_trim_fraction"]),
        "RESTORED__R1_RET__R__C048__APPROVED_CLEARANCE_V2__V11",
    )
    c046_clearance = v10.v9.v3.distance(c046, eye)
    c048_clearance = v10.v9.v3.distance(c048, eye)
    for key, actual, expected in (
        ("C046", c046_clearance, float(contract["approved_c046_eye_clearance_mm"])),
        ("C048", c048_clearance, float(contract["approved_c048_eye_clearance_mm"])),
    ):
        if abs(actual - expected) > float(contract["maximum_clearance_difference_mm"]):
            raise RuntimeError(f"{key} approved clearance changed: {actual} vs {expected}")
    if v10.v9.v3.intersection_volume(c046, eye) > 0.001:
        raise RuntimeError("restored C046 intersects the accepted eye")
    if v10.v9.v3.intersection_volume(c048, eye) > 0.001:
        raise RuntimeError("restored C048 intersects the accepted eye")
    if not v2.overlaps(c046, lower):
        raise RuntimeError("restored C046 lost lower-face structural contact")
    if not v2.overlaps(c048, lower):
        raise RuntimeError("restored C048 lost lower-face structural contact")
    if not v2.overlaps(c046, c048):
        raise RuntimeError("restored C046/C048 lost their mutual structural contact")

    flange_records: dict[str, Any] = {}
    for key, retained in flanges.items():
        source_fingerprint = v10.v9.v3.fingerprint(source_flanges[key])
        retained_fingerprint = v10.v9.v3.fingerprint(retained)
        if source_fingerprint != retained_fingerprint:
            raise RuntimeError(f"{key} flange changed in V11")
        flange_records[key] = {
            "fingerprint": retained_fingerprint,
            "topology": v10.v9.v3.topology(retained),
        }
    pair_records: dict[str, Any] = {}
    for role in ("outer", "second"):
        head = flanges[f"{role}_head"]
        paired_eye = flanges[f"{role}_eye"]
        gap = v10.v9.v3.distance(head, paired_eye)
        interference = v10.v9.v3.intersection_volume(head, paired_eye)
        if interference > 0.001:
            raise RuntimeError(f"{role} flange pair interferes")
        if abs(gap - float(contract["mating_gap_mm"])) > float(contract["maximum_pair_gap_error_mm"]):
            raise RuntimeError(f"{role} flange gap changed: {gap}")
        pair_records[role] = {
            "minimum_clearance_mm": round(gap, 4),
            "interference_mm3": round(interference, 6),
        }

    v10_material = v10.v9.v3.material("FROZEN__V10_ACCEPTED_CONTEXT", (0.36, 0.40, 0.45, 1.0))
    lower_material = v10.v9.v3.material("PROPOSED__V11_V10_NECK_REMOVAL", (0.16, 0.56, 0.34, 1.0))
    clearance_material = v10.v9.v3.material("RESTORED__V2_CLEARANCE", (0.02, 0.86, 1.0, 1.0))
    flange_material = v10.v9.v3.material("RETAINED__V11_FLANGES", (0.95, 0.55, 0.10, 1.0))
    for obj in (upper, eye):
        v10.v9.v3.assign(obj, v10_material)
    v10.v9.v3.assign(lower, lower_material)
    for obj in (c046, c048):
        v10.v9.v3.assign(obj, clearance_material)
    for obj in flanges.values():
        v10.v9.v3.assign(obj, flange_material)

    exported = {
        "right_lower_face_v10_neck_removed_stale_ribs_removed_v11": lower,
        "right_upper_head_frozen_v11": upper,
        "right_eye_bucket_frozen_v11": eye,
        "restored_c046_approved_clearance_v2_v11": c046,
        "restored_c048_approved_clearance_v2_v11": c048,
        **{f"{key}_unchanged_v11": obj for key, obj in flanges.items()},
    }
    review_objs: dict[str, str] = {}
    for key, obj in exported.items():
        path = review / f"{key}.obj"
        v10.v9.v3.export_obj(obj, path)
        review_objs[key] = str(path.relative_to(REPO_ROOT))

    scene = bpy.context.scene
    scene.name = "Right_Eye_Neck_Removal_Clearance_Regression_Fix_Review_V11"
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.035, 0.045, 0.06)
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    camera_data = bpy.data.cameras.new("V11_REVIEW_CAMERA")
    camera = bpy.data.objects.new("V11_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 66
    full = {lower, upper, eye, c046, c048, *flanges.values()}
    renders = [
        v10.v9.v3.render(camera, output, "01-v11-restored-clearance-close-up", (155, 148, 112), (64, 63, 119), full),
        v10.v9.v3.render(camera, output, "02-v11-restored-clearance-side", (250, -120, 180), (64, 63, 119), full),
        v10.v9.v3.render(camera, output, "03-v11-full-right-owner-context", (400, -500, 300), (50, 100, 130), full),
        v10.v9.v3.render(camera, output, "04-v11-eye-and-restored-ribs-isolated", (145, 125, 105), (55, 56, 112), {eye, c046, c048}),
    ]
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_set(obj not in full)
            obj.hide_render = obj not in full
    scene["REVIEW_ONLY"] = True
    scene["V10_NECK_REMOVAL_PRESERVED"] = True
    scene["V2_REINFORCEMENT_CLEARANCE_RESTORED"] = True
    scene["OWNER_BOOLEAN_PERFORMED"] = False
    scene["MIRROR_PERFORMED"] = False
    scene["PRINT_RELEASE"] = False
    blend_path = output / "CAT_HEAD_RIGHT_EYE_NECK_REMOVAL_CLEARANCE_REGRESSION_FIX_REVIEW_V11.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "regression_cause": "V10 rebuilt the lower-face review from V7 and therefore retained the original C046/C048 components instead of the user-approved V2 clearance geometry.",
        "v10_neck_removal_preserved": {
            "source_lower_face_fingerprint": source_lower_fingerprint,
            "source_lower_face_topology": source_lower_topology,
            "accepted_v10_removed_actual_neck_component": v10_validation["removed_actual_neck_component"],
            "accepted_v10_restored_component": v10_validation["restored_v9_wrongly_deleted_component"],
        },
        "stale_components_removed": {"c046": removed_c046, "c048": removed_c048},
        "lower_face_after_stale_rib_removal": {
            "fingerprint": v10.v9.v3.fingerprint(lower),
            "topology": lower_topology,
            "component_count": len(v10.v9.components(lower)),
        },
        "restored_approved_v2_reinforcements": {
            "c046": {
                "topology": v10.v9.v3.topology(c046),
                "eye_clearance_mm": round(c046_clearance, 4),
                "expected_eye_clearance_mm": v2_validation["c046_proposed_eye_clearance_mm"],
                "overlaps_lower_face_owner": True,
            },
            "c048": {
                "topology": v10.v9.v3.topology(c048),
                "eye_clearance_mm": round(c048_clearance, 4),
                "expected_eye_clearance_mm": v2_validation["c048_proposed_eye_clearance_mm"],
                "overlaps_lower_face_owner": True,
                "far_end_preserved_exactly": v2_validation["c048_far_end_preserved_exactly"],
            },
            "mutual_structural_contact": True,
            "eye_interference": False,
        },
        "retained_flanges": flange_records,
        "retained_pairs": pair_records,
        "eye_geometry_changed": False,
        "flange_geometry_changed": False,
        "flange_location_changed": False,
        "other_reinforcement_changed": False,
        "owner_boolean_performed": False,
        "mirror_performed": False,
        "no_stl_or_gcode_exported": True,
        "locked_contract": contract,
        "holds": config["holds"],
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": renders,
            "review_objs": review_objs,
        },
    }
    (output / "validation-v11.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
