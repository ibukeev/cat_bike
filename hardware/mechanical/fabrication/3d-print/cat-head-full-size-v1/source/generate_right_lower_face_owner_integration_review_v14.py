#!/usr/bin/env python3
"""Substitute the approved V13 component 001 into a frozen V11 right owner copy."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import bpy

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/right-lower-face-owner-integration-review-v14.json"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_right_eye_outer_neck_removal_upper_head_owner_review_v10 as v10


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


def world_bounds(obj: bpy.types.Object) -> tuple[list[float], list[float]]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return (
        [min(point[axis] for point in points) for axis in range(3)],
        [max(point[axis] for point in points) for axis in range(3)],
    )


def import_obj(path: Path, name: str) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    # These controlled OBJ artifacts were exported in the source Blender XYZ frame.
    # Import without the generic OBJ Y-up rotation so their locked world coordinates remain exact.
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="Y", up_axis="Z")
    selected = [obj for obj in bpy.context.selected_objects if obj.type == "MESH"]
    if len(selected) != 1:
        raise RuntimeError(f"Expected one imported mesh from {path}, got {len(selected)}")
    obj = selected[0]
    obj.name = name
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return obj


def extract_component(
    source: bpy.types.Object,
    indices: set[int],
    name: str,
) -> bpy.types.Object:
    ordered = sorted(indices)
    remap = {old: new for new, old in enumerate(ordered)}
    world = [source.matrix_world @ source.data.vertices[index].co for index in ordered]
    faces = [
        tuple(remap[index] for index in polygon.vertices)
        for polygon in source.data.polygons
        if set(polygon.vertices).issubset(indices)
    ]
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(world, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def assert_component_matches_inventory(
    obj: bpy.types.Object,
    record: dict[str, Any],
    expected_obj_sha256: str,
    tolerance: float = 0.00002,
) -> dict[str, Any]:
    source_path = repo_path(record["path"])
    if sha256(source_path) != expected_obj_sha256:
        raise RuntimeError(f"{record['name']} frozen OBJ SHA-256 changed")
    actual_topology = v10.v9.v3.topology(obj)
    expected_topology = record["topology"]
    for key in ("vertices", "edges", "faces", "boundary_edges", "nonmanifold_edges"):
        if actual_topology[key] != expected_topology[key]:
            raise RuntimeError(
                f"{record['name']} topology changed at {key}: "
                f"{actual_topology[key]} != {expected_topology[key]}"
            )
    actual_fingerprint = v10.v9.v3.fingerprint(obj)
    if actual_fingerprint != record["fingerprint"]:
        raise RuntimeError(f"{record['name']} fingerprint changed")
    low, high = world_bounds(obj)
    for actual, expected in zip(low, record["bbox_min_mm"]):
        if abs(actual - expected) > tolerance:
            raise RuntimeError(
                f"{record['name']} minimum bound changed: {low} != {record['bbox_min_mm']}"
            )
    for actual, expected in zip(high, record["bbox_max_mm"]):
        if abs(actual - expected) > tolerance:
            raise RuntimeError(
                f"{record['name']} maximum bound changed: {high} != {record['bbox_max_mm']}"
            )
    return {
        "name": record["name"],
        "source_obj": record["path"],
        "source_obj_sha256": expected_obj_sha256,
        "fingerprint": actual_fingerprint,
        "topology": actual_topology,
        "bbox_min_mm": [round(value, 5) for value in low],
        "bbox_max_mm": [round(value, 5) for value in high],
        "unchanged": True,
    }


def main() -> None:
    config_path = parse_args().config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    contract = config["locked_contract"]
    names = config["objects"]
    output = repo_path(config["output_dir"])
    review = output / "review"
    review.mkdir(parents=True, exist_ok=True)

    v11_blend = repo_path(config["source_v11_blend"])
    inventory_path = repo_path(config["source_v12_inventory"])
    component_manifest_path = repo_path(config["source_v12_component_sha_manifest"])
    v13_path = repo_path(config["source_v13_component"])
    for path, expected in (
        (v11_blend, config["source_v11_blend_sha256"]),
        (inventory_path, config["source_v12_inventory_sha256"]),
        (component_manifest_path, config["source_v12_component_sha_manifest_sha256"]),
        (v13_path, config["source_v13_component_sha256"]),
    ):
        if sha256(path) != expected:
            raise RuntimeError(f"Frozen input changed: {path}")
    v11_validation = json.loads(repo_path(config["source_v11_validation"]).read_text())
    v13_validation = json.loads(repo_path(config["source_v13_validation"]).read_text())
    inventory = json.loads(inventory_path.read_text())
    component_manifest = json.loads(component_manifest_path.read_text())["components"]
    if inventory["component_count"] != int(contract["source_component_count"]):
        raise RuntimeError("V12 inventory component count changed")
    if v13_validation["status"] != "PASS_BLENDER_ISOLATED":
        raise RuntimeError("V13 is not a passing isolated candidate")
    if v13_validation["proposal_obj_sha256"] != config["source_v13_component_sha256"]:
        raise RuntimeError("V13 validation does not identify the locked proposal OBJ")

    bpy.ops.wm.open_mainfile(filepath=str(v11_blend))
    lower_source = bpy.data.objects[names["v11_lower_face"]]
    expected_lower_fingerprint = v11_validation["lower_face_after_stale_rib_removal"]["fingerprint"]
    if v10.v9.v3.fingerprint(lower_source) != expected_lower_fingerprint:
        raise RuntimeError("Frozen V11 lower-face fingerprint changed")
    context = {
        "upper_head": bpy.data.objects[names["upper_head"]],
        "eye_bucket": bpy.data.objects[names["eye_bucket"]],
        "c046": bpy.data.objects[names["c046"]],
        "c048": bpy.data.objects[names["c048"]],
        "outer_head_flange": bpy.data.objects[names["outer_head_flange"]],
        "outer_eye_flange": bpy.data.objects[names["outer_eye_flange"]],
        "second_head_flange": bpy.data.objects[names["second_head_flange"]],
        "second_eye_flange": bpy.data.objects[names["second_eye_flange"]],
    }
    context_before = {key: v10.v9.v3.fingerprint(obj) for key, obj in context.items()}
    for key in ("outer_head", "outer_eye", "second_head", "second_eye"):
        if context_before[f"{key}_flange"] != v11_validation["retained_flanges"][key]["fingerprint"]:
            raise RuntimeError(f"Frozen V11 {key} flange fingerprint changed")

    source_components = v10.v9.components(lower_source)
    if len(source_components) != int(contract["source_component_count"]):
        raise RuntimeError("Frozen V11 lower-face component count changed")
    component_objects: list[bpy.types.Object] = []
    unchanged_records: list[dict[str, Any]] = []
    component_001 = import_obj(v13_path, "APPROVED__RIGHT_LOWER_FACE__COMPONENT_001_V13_IN_V14")
    if v10.v9.v3.topology(component_001)["vertices"] != v13_validation["candidate_topology"]["vertices"]:
        raise RuntimeError("Imported V13 component topology changed")
    component_objects.append(component_001)
    for indices, record in zip(source_components[1:], inventory["components"][1:]):
        obj = extract_component(lower_source, indices, f"FROZEN__{record['name']}__V14")
        unchanged_records.append(
            assert_component_matches_inventory(
                obj, record, component_manifest[record["name"]]
            )
        )
        component_objects.append(obj)
    bpy.data.objects.remove(lower_source, do_unlink=True)
    if len(component_objects) != int(contract["source_component_count"]):
        raise RuntimeError("V14 owner substitution did not retain 60 components")

    bpy.ops.object.select_all(action="DESELECT")
    for obj in component_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = component_001
    bpy.ops.object.join()
    lower = component_001
    lower.name = "PROPOSED__RIGHT_LOWER_FACE__V13_COMPONENT_001_INTEGRATED_V14"
    lower_topology = v10.v9.v3.topology(lower)
    expected_topology = {
        key: v11_validation["lower_face_after_stale_rib_removal"]["topology"][key]
        - inventory["components"][0]["topology"][key]
        + v13_validation["candidate_topology"][key]
        for key in ("vertices", "edges", "faces", "boundary_edges", "nonmanifold_edges")
    }
    for key, expected in expected_topology.items():
        if lower_topology[key] != expected:
            raise RuntimeError(f"Integrated lower-face topology changed at {key}: {lower_topology[key]} != {expected}")
    if len(v10.v9.components(lower)) != int(contract["source_component_count"]):
        raise RuntimeError("Integrated lower-face owner no longer contains exactly 60 loose solids")

    context_after = {key: v10.v9.v3.fingerprint(obj) for key, obj in context.items()}
    if context_after != context_before:
        raise RuntimeError("A frozen V11 context object changed during V14 integration")
    c046_clearance = v10.v9.v3.distance(context["c046"], context["eye_bucket"])
    c048_clearance = v10.v9.v3.distance(context["c048"], context["eye_bucket"])
    for key, actual, expected in (
        ("C046", c046_clearance, float(contract["approved_c046_eye_clearance_mm"])),
        ("C048", c048_clearance, float(contract["approved_c048_eye_clearance_mm"])),
    ):
        if abs(actual - expected) > float(contract["maximum_clearance_difference_mm"]):
            raise RuntimeError(f"{key} eye clearance changed: {actual}")
    if not v10.v9.components(lower):
        raise RuntimeError("Integrated lower-face owner is empty")

    pair_records: dict[str, Any] = {}
    for role in ("outer", "second"):
        head = context[f"{role}_head_flange"]
        eye = context[f"{role}_eye_flange"]
        gap = v10.v9.v3.distance(head, eye)
        interference = v10.v9.v3.intersection_volume(head, eye)
        if abs(gap - float(contract["mating_gap_mm"])) > float(contract["maximum_pair_gap_error_mm"]):
            raise RuntimeError(f"{role} flange gap changed: {gap}")
        if interference > float(contract["maximum_interference_mm3"]):
            raise RuntimeError(f"{role} flange pair interferes: {interference}")
        pair_records[role] = {
            "minimum_clearance_mm": round(gap, 4),
            "interference_mm3": round(interference, 6),
            "head_fingerprint": context_after[f"{role}_head_flange"],
            "eye_fingerprint": context_after[f"{role}_eye_flange"],
        }

    lower_material = v10.v9.v3.material("PROPOSED__V14_LOWER_FACE_BLUE", (0.08, 0.38, 0.78, 1.0))
    frozen_material = v10.v9.v3.material("FROZEN__V14_CONTEXT_GREY", (0.36, 0.40, 0.45, 1.0))
    clearance_material = v10.v9.v3.material("FROZEN__V14_C046_C048_CYAN", (0.02, 0.86, 1.0, 1.0))
    flange_material = v10.v9.v3.material("FROZEN__V14_FLANGES_ORANGE", (0.95, 0.55, 0.10, 1.0))
    v10.v9.v3.assign(lower, lower_material)
    for key, obj in context.items():
        if key in {"c046", "c048"}:
            v10.v9.v3.assign(obj, clearance_material)
        elif key.endswith("flange"):
            v10.v9.v3.assign(obj, flange_material)
        else:
            v10.v9.v3.assign(obj, frozen_material)

    full = {lower, *context.values()}
    scene = bpy.context.scene
    scene.name = "Right_Lower_Face_Owner_Integration_Review_V14"
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
    camera_data = bpy.data.cameras.new("V14_REVIEW_CAMERA")
    camera = bpy.data.objects.new("V14_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 66
    renders = [
        v10.v9.v3.render(camera, output, "01-v14-full-right-owner-context", (400, -500, 300), (50, 100, 130), full),
        v10.v9.v3.render(camera, output, "02-v14-eye-flange-c046-c048-close-up", (155, 148, 112), (64, 63, 119), full),
        v10.v9.v3.render(camera, output, "03-v14-lower-face-isolated", (400, -500, 300), (50, 100, 130), {lower}),
    ]
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_set(obj not in full)
            obj.hide_render = obj not in full
    scene["REVIEW_ONLY"] = True
    scene["V13_COMPONENT_001_VISUALLY_APPROVED"] = True
    scene["V13_COMPONENT_001_SUBSTITUTED"] = True
    scene["OTHER_59_COMPONENTS_FROZEN"] = True
    scene["OWNER_BOOLEAN_PERFORMED"] = False
    scene["MIRROR_PERFORMED"] = False
    scene["PRINT_RELEASE"] = False

    blend_path = output / "CAT_HEAD_RIGHT_LOWER_FACE_OWNER_INTEGRATION_REVIEW_V14.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.object.select_all(action="DESELECT")
    lower.select_set(True)
    bpy.context.view_layer.objects.active = lower
    obj_path = output / "right_lower_face_v14_owner_review.obj"
    bpy.ops.wm.obj_export(filepath=str(obj_path), export_selected_objects=True)
    report = {
        "status": "PASS_BLENDER_RIGHT_OWNER_INTEGRATION_REVIEW",
        "scope": "right side only; approved V13 component 001 substituted into frozen V11 lower-face owner",
        "source_v11_lower_face_fingerprint": expected_lower_fingerprint,
        "approved_component_001": {
            "source": config["source_v13_component"],
            "sha256": config["source_v13_component_sha256"],
            "topology": v13_validation["candidate_topology"],
            "surface_deviation_mm": v13_validation["maximum_candidate_to_source_surface_deviation_mm"],
            "bbox_deviation_mm": v13_validation["maximum_bbox_deviation_mm"],
            "visual_approval": "user approved V13 on 2026-08-14",
        },
        "unchanged_components_002_through_060": unchanged_records,
        "integrated_lower_face": {
            "component_count": len(v10.v9.components(lower)),
            "topology": lower_topology,
            "fingerprint": v10.v9.v3.fingerprint(lower),
            "owner_boolean_performed": False,
        },
        "frozen_context_fingerprints": context_after,
        "c046_eye_clearance_mm": round(c046_clearance, 4),
        "c048_eye_clearance_mm": round(c048_clearance, 4),
        "flange_pairs": pair_records,
        "eye_geometry_changed": False,
        "flange_geometry_changed": False,
        "flange_location_changed": False,
        "c046_c048_changed": False,
        "upper_head_changed": False,
        "mirror_performed": False,
        "no_stl_or_gcode_exported": True,
        "locked_contract": contract,
        "holds": config["holds"],
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "owner_obj": str(obj_path.relative_to(REPO_ROOT)),
            "owner_obj_sha256": sha256(obj_path),
            "renders": renders,
        },
    }
    (output / "validation-v14.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
