#!/usr/bin/env python3
"""Mirror the approved V14 right lower-face/eye interface exactly across X=0."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Matrix

SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/lower-face-bilateral-exact-mirror-review-v15.json"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_right_lower_face_owner_integration_review_v14 as v14


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


def mirror_object(source: bpy.types.Object, name: str) -> bpy.types.Object:
    source_world_points = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    mirrored = source.copy()
    mirrored.data = source.data.copy()
    mirrored.name = name
    mirrored.data.name = f"{name}_MESH"
    mirrored.parent = None
    mirrored.matrix_world = Matrix.Identity(4)
    for vertex, point in zip(mirrored.data.vertices, source_world_points):
        vertex.co = (-point.x, point.y, point.z)
    mirrored.data.flip_normals()
    bpy.context.scene.collection.objects.link(mirrored)
    mirrored["EXACT_X0_MIRROR_OF"] = source.name
    mirrored.hide_set(False)
    mirrored.hide_render = False
    return mirrored


def world_vertex_tokens(obj: bpy.types.Object, reflect_x: bool = False) -> list[tuple[float, float, float]]:
    tokens = []
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        x = -point.x if reflect_x else point.x
        tokens.append((round(x, 5), round(point.y, 5), round(point.z, 5)))
    return sorted(tokens)


def world_bounds(obj: bpy.types.Object) -> tuple[list[float], list[float]]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return (
        [min(point[axis] for point in points) for axis in range(3)],
        [max(point[axis] for point in points) for axis in range(3)],
    )


def mirror_bounds_error(right: bpy.types.Object, left: bpy.types.Object) -> float:
    rlo, rhi = world_bounds(right)
    llo, lhi = world_bounds(left)
    expected_lo = [-rhi[0], rlo[1], rlo[2]]
    expected_hi = [-rlo[0], rhi[1], rhi[2]]
    return max(abs(a - b) for a, b in zip(llo + lhi, expected_lo + expected_hi))


def maximum_indexed_vertex_mirror_error(
    right: bpy.types.Object, left: bpy.types.Object
) -> float:
    if len(right.data.vertices) != len(left.data.vertices):
        return float("inf")
    maximum = 0.0
    for right_vertex, left_vertex in zip(right.data.vertices, left.data.vertices):
        right_point = right.matrix_world @ right_vertex.co
        left_point = left.matrix_world @ left_vertex.co
        maximum = max(
            maximum,
            abs(left_point.x + right_point.x),
            abs(left_point.y - right_point.y),
            abs(left_point.z - right_point.z),
        )
    return maximum


def export_obj(obj: bpy.types.Object, path: Path) -> str:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.obj_export(
        filepath=str(path),
        export_selected_objects=True,
        forward_axis="Y",
        up_axis="Z",
    )
    return sha256(path)


def append_mesh_object(blend_path: Path, source_name: str, name: str) -> bpy.types.Object:
    with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
        if source_name not in data_from.objects:
            raise RuntimeError(f"Missing approved library object {source_name}")
        data_to.objects = [source_name]
    obj = data_to.objects[0]
    if obj is None or obj.type != "MESH":
        raise RuntimeError(f"Approved library object {source_name} is not a mesh")
    bpy.context.scene.collection.objects.link(obj)
    obj.name = name
    obj.data.name = f"{name}_MESH"
    return obj


def import_single_obj(path: Path, name: str) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="Y", up_axis="Z")
    imported = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    if len(imported) != 1:
        raise RuntimeError(f"Expected one mesh from {path}, got {len(imported)}")
    obj = imported[0]
    obj.name = name
    obj.data.name = f"{name}_MESH"
    return obj


def maximum_bounds_error(actual: tuple[list[float], list[float]], expected: list[list[float]]) -> float:
    return max(abs(a - b) for a, b in zip(actual[0] + actual[1], expected[0] + expected[1]))


def main() -> None:
    config_path = parse_args().config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    contract = config["locked_contract"]
    output = repo_path(config["output_dir"])
    review = output / "review"
    objects_dir = output / "objects"
    review.mkdir(parents=True, exist_ok=True)
    objects_dir.mkdir(parents=True, exist_ok=True)

    source_blend = repo_path(config["source_v14_blend"])
    source_validation_path = repo_path(config["source_v14_validation"])
    source_v9_eye_blend = repo_path(config["source_v9_bilateral_eye_blend"])
    source_left_upper_fcstd = repo_path(config["source_left_upper_head_fcstd"])
    source_left_upper_step = repo_path(config["source_left_upper_head_step"])
    source_left_upper_obj = repo_path(config["source_left_upper_head_obj"])
    locked_sources = (
        (source_blend, "source_v14_blend_sha256", "Approved V14 blend"),
        (source_validation_path, "source_v14_validation_sha256", "Approved V14 validation"),
        (source_v9_eye_blend, "source_v9_bilateral_eye_blend_sha256", "Approved V9 bilateral eye blend"),
        (source_left_upper_fcstd, "source_left_upper_head_current_container_sha256", "Current approved left upper-head container"),
        (source_left_upper_step, "source_left_upper_head_step_sha256", "Approved left upper-head STEP extract"),
        (source_left_upper_obj, "source_left_upper_head_obj_sha256", "Approved left upper-head OBJ extract"),
    )
    for path, config_key, label in locked_sources:
        actual = sha256(path)
        if actual != config[config_key]:
            raise RuntimeError(f"{label} changed: {actual}")

    source_validation = json.loads(source_validation_path.read_text())
    if source_validation["status"] != "PASS_BLENDER_RIGHT_OWNER_INTEGRATION_REVIEW":
        raise RuntimeError("V14 source is not passing")

    bpy.ops.wm.open_mainfile(filepath=str(source_blend))
    right: dict[str, bpy.types.Object] = {}
    for role, name in config["right_objects"].items():
        obj = bpy.data.objects.get(name)
        if obj is None or obj.type != "MESH":
            raise RuntimeError(f"Missing approved V14 object {name}")
        right[role] = obj

    expected_fingerprints = {
        "lower_face": source_validation["integrated_lower_face"]["fingerprint"],
        **source_validation["frozen_context_fingerprints"],
    }
    right_fingerprints = {
        role: v14.v10.v9.v3.fingerprint(obj) for role, obj in right.items()
    }
    if right_fingerprints != expected_fingerprints:
        raise RuntimeError("Approved V14 right-side fingerprints changed")

    mirror_roles = list(config["exact_mirror_roles"])
    left: dict[str, bpy.types.Object] = {
        role: mirror_object(
            right[role], f"PROPOSED__LEFT_{role.upper()}__EXACT_X0_MIRROR_V15"
        )
        for role in mirror_roles
    }
    left["eye_bucket"] = append_mesh_object(
        source_v9_eye_blend,
        config["left_context_objects"]["eye_bucket_source_name"],
        config["left_context_objects"]["eye_bucket"],
    )
    left["upper_head"] = import_single_obj(
        source_left_upper_obj,
        config["left_context_objects"]["upper_head"],
    )

    mirror_records: dict[str, Any] = {}
    tolerance = float(contract["mirror_coordinate_tolerance_mm"])
    for role in mirror_roles:
        rtop = v14.v10.v9.v3.topology(right[role])
        ltop = v14.v10.v9.v3.topology(left[role])
        exact_topology_keys = ("vertices", "edges", "faces", "boundary_edges", "nonmanifold_edges")
        if any(rtop[key] != ltop[key] for key in exact_topology_keys):
            raise RuntimeError(f"{role} mirrored topology changed: {rtop} != {ltop}")
        volume_difference = abs(rtop["volume_mm3"] - ltop["volume_mm3"])
        if volume_difference > float(contract["maximum_mirrored_volume_difference_mm3"]):
            raise RuntimeError(f"{role} mirrored volume difference {volume_difference}")
        vertex_error = maximum_indexed_vertex_mirror_error(right[role], left[role])
        if vertex_error > tolerance:
            raise RuntimeError(f"{role} mirrored vertex error {vertex_error}")
        bounds_error = mirror_bounds_error(right[role], left[role])
        if bounds_error > tolerance:
            raise RuntimeError(f"{role} mirrored bounds error {bounds_error}")
        mirror_records[role] = {
            "right_name": right[role].name,
            "left_name": left[role].name,
            "right_topology": rtop,
            "left_topology": ltop,
            "volume_difference_mm3": round(volume_difference, 6),
            "maximum_indexed_vertex_error_mm": round(vertex_error, 8),
            "maximum_bounds_error_mm": round(bounds_error, 8),
            "exact_vertex_mirror": True,
        }

    right_eye_topology = v14.v10.v9.v3.topology(right["eye_bucket"])
    left_eye_topology = v14.v10.v9.v3.topology(left["eye_bucket"])
    eye_bounds_error = mirror_bounds_error(right["eye_bucket"], left["eye_bucket"])
    eye_exact_vertices = (
        world_vertex_tokens(right["eye_bucket"], reflect_x=True)
        == world_vertex_tokens(left["eye_bucket"])
    )
    if right_eye_topology != left_eye_topology or not eye_exact_vertices or eye_bounds_error > tolerance:
        raise RuntimeError("Approved V9 left eye no longer exactly mirrors the frozen V14 right eye")

    left_upper_components = len(v14.v10.v9.components(left["upper_head"]))
    left_upper_bounds = world_bounds(left["upper_head"])
    left_upper_bounds_error = maximum_bounds_error(
        left_upper_bounds, contract["left_upper_head_expected_bounds_mm"]
    )
    if left_upper_components != int(contract["required_left_upper_head_obj_connected_components"]):
        raise RuntimeError(f"Approved left upper-head OBJ connectivity changed: {left_upper_components}")
    if left_upper_bounds_error > float(contract["left_upper_head_maximum_bounds_error_mm"]):
        raise RuntimeError(f"Approved left upper head bounds changed: {left_upper_bounds_error}")
    left_context_validation = {
        "approved_v9_left_eye": {
            "name": left["eye_bucket"].name,
            "topology": left_eye_topology,
            "exact_x0_mirror_of_frozen_right_eye": True,
            "maximum_bounds_error_mm": round(eye_bounds_error, 8),
            "source_blend_sha256": config["source_v9_bilateral_eye_blend_sha256"],
        },
        "approved_left_upper_head": {
            "name": left["upper_head"].name,
            "mesh_topology": v14.v10.v9.v3.topology(left["upper_head"]),
            "obj_connected_components": left_upper_components,
            "verified_source_occt_metrics": contract["approved_left_upper_head_occt_metrics"],
            "bounds_mm": [[round(v, 6) for v in row] for row in left_upper_bounds],
            "maximum_checkpoint_bounds_error_mm": round(left_upper_bounds_error, 8),
            "checkpoint_container_sha256": config["source_left_upper_head_checkpoint_sha256"],
            "current_container_sha256": config["source_left_upper_head_current_container_sha256"],
            "container_hash_drift_explicitly_recorded": True,
            "object_step_sha256": config["source_left_upper_head_step_sha256"],
            "object_obj_sha256": config["source_left_upper_head_obj_sha256"],
        },
    }

    lower_face_component_counts: dict[str, int] = {}
    for side, objs in (("right", right), ("left", left)):
        count = len(v14.v10.v9.components(objs["lower_face"]))
        if count != int(contract["required_lower_face_component_count_each_side"]):
            raise RuntimeError(f"{side} lower face component count changed: {count}")
        lower_face_component_counts[side] = count

    pair_records: dict[str, Any] = {}
    clearance_records: dict[str, Any] = {}
    owner_records: dict[str, Any] = {}
    engagement_map = {
        "outer_head_flange_to_upper_head": ("outer_head_flange", "upper_head"),
        "outer_eye_flange_to_eye_bucket": ("outer_eye_flange", "eye_bucket"),
        "second_head_flange_to_lower_face": ("second_head_flange", "lower_face"),
        "second_eye_flange_to_eye_bucket": ("second_eye_flange", "eye_bucket"),
    }
    for side, objs in (("right", right), ("left", left)):
        pair_records[side] = {}
        for role in ("outer", "second"):
            head = objs[f"{role}_head_flange"]
            eye = objs[f"{role}_eye_flange"]
            gap = v14.v10.v9.v3.distance(head, eye)
            interference = v14.v10.v9.v3.intersection_volume(head, eye)
            if abs(gap - float(contract["mating_gap_mm"])) > float(contract["maximum_pair_gap_error_mm"]):
                raise RuntimeError(f"{side} {role} flange gap changed: {gap}")
            if interference > float(contract["maximum_interference_mm3"]):
                raise RuntimeError(f"{side} {role} flange pair interferes")
            pair_records[side][role] = {
                "minimum_clearance_mm": round(gap, 4),
                "interference_mm3": round(interference, 6),
            }
        clearance_records[side] = {}
        for rib_role, expected in (
            ("c046", float(contract["approved_c046_eye_clearance_mm"])),
            ("c048", float(contract["approved_c048_eye_clearance_mm"])),
        ):
            value = v14.v10.v9.v3.distance(objs[rib_role], objs["eye_bucket"])
            if abs(value - expected) > float(contract["maximum_clearance_difference_mm"]):
                raise RuntimeError(f"{side} {rib_role} eye clearance changed: {value}")
            clearance_records[side][f"{rib_role}_eye_clearance_mm"] = round(value, 4)
        owner_records[side] = {}
        for record_name, (feature_role, owner_role) in engagement_map.items():
            value = v14.v10.v9.v3.intersection_volume(objs[feature_role], objs[owner_role])
            expected = float(contract["approved_owner_engagement_mm3"][record_name])
            difference = abs(value - expected)
            asymmetric_approved_owner = side == "left" and record_name == "outer_head_flange_to_upper_head"
            if asymmetric_approved_owner:
                validation_mode = "minimum direct-root engagement against approved asymmetric left upper-head owner"
                passed = value >= float(contract["minimum_direct_owner_root_engagement_mm3"])
            else:
                validation_mode = "exact preserved or exact-mirrored approved-right engagement"
                passed = difference <= float(contract["maximum_owner_engagement_difference_mm3"])
            if not passed:
                raise RuntimeError(
                    f"{side} {record_name} owner engagement failed: {value} vs {expected}"
                )
            owner_records[side][record_name] = {
                "owner_role": owner_role,
                "engagement_mm3": round(value, 4),
                "approved_right_reference_mm3": expected,
                "difference_from_approved_right_mm3": round(difference, 6),
                "validation_mode": validation_mode,
                "pass": True,
            }

    cross_side_interference: dict[str, float] = {}
    for role in mirror_roles:
        value = v14.v10.v9.v3.intersection_volume(right[role], left[role])
        allowed = (
            float(contract["maximum_inherited_lower_face_center_seam_overlap_mm3"])
            if role == "lower_face"
            else float(contract["maximum_interference_mm3"])
        )
        if value > allowed:
            raise RuntimeError(f"{role} left/right mirror objects interfere by {value}")
        cross_side_interference[role] = round(value, 6)

    mats = {
        "right": v14.v10.v9.v3.material("V15_RIGHT_BLUE", (0.08, 0.38, 0.78, 1.0)),
        "left": v14.v10.v9.v3.material("V15_LEFT_TEAL", (0.02, 0.68, 0.58, 1.0)),
        "right_flange": v14.v10.v9.v3.material("V15_RIGHT_FLANGE_ORANGE", (0.95, 0.46, 0.08, 1.0)),
        "left_flange": v14.v10.v9.v3.material("V15_LEFT_FLANGE_YELLOW", (0.95, 0.82, 0.08, 1.0)),
        "rib": v14.v10.v9.v3.material("V15_RIB_CYAN", (0.05, 0.88, 1.0, 1.0)),
    }
    for side, objs in (("right", right), ("left", left)):
        for role, obj in objs.items():
            if role.endswith("flange"):
                mat = mats[f"{side}_flange"]
            elif role in {"c046", "c048"}:
                mat = mats["rib"]
            else:
                mat = mats[side]
            v14.v10.v9.v3.assign(obj, mat)

    all_review = {*right.values(), *left.values()}
    scene = bpy.context.scene
    scene.name = "Lower_Face_Bilateral_Exact_Mirror_Review_V15"
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.035, 0.045, 0.06)
    scene.render.resolution_x = 1500
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    camera_data = bpy.data.cameras.new("V15_REVIEW_CAMERA")
    camera = bpy.data.objects.new("V15_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 62
    for obj in bpy.data.objects:
        if obj.type not in {"MESH", "CAMERA"}:
            obj.hide_set(True)
            obj.hide_render = True
    renders = [
        v14.v10.v9.v3.render(camera, output, "01-v15-bilateral-front-context", (0, -590, 280), (0, 100, 130), all_review),
        v14.v10.v9.v3.render(camera, output, "02-v15-bilateral-rear-interior", (0, 500, 250), (0, 95, 130), all_review),
        v14.v10.v9.v3.render(camera, output, "03-v15-left-owner-isolated", (-400, -500, 300), (-50, 100, 130), set(left.values())),
        v14.v10.v9.v3.render(camera, output, "04-v15-right-four-flange-owner-roots", (0, 115, 135), (82, 75, 135), set(right.values())),
        v14.v10.v9.v3.render(camera, output, "05-v15-left-four-flange-owner-roots", (0, 115, 135), (-82, 75, 135), set(left.values())),
    ]
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_set(obj not in all_review)
            obj.hide_render = obj not in all_review

    exports: dict[str, dict[str, str]] = {"right": {}, "left": {}}
    for side, objs in (("right", right), ("left", left)):
        for role, obj in objs.items():
            path = objects_dir / f"{side}_{role}_v15.obj"
            exports[side][role] = export_obj(obj, path)

    scene["REVIEW_ONLY"] = True
    scene["SOURCE_V14_VISUALLY_APPROVED"] = True
    scene["LEFT_CONTEXTS_REUSED_APPROVED"] = True
    scene["MIRROR_PLANE"] = "X=0 / YZ"
    scene["EXACT_LOWER_FEATURE_MIRROR_VALIDATED"] = True
    scene["PRODUCTION_BOOLEAN_PERFORMED"] = False
    scene["PRINT_RELEASE"] = False
    blend_path = output / "CAT_HEAD_LOWER_FACE_BILATERAL_EXACT_MIRROR_REVIEW_V15.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": "PASS_BLENDER_BILATERAL_EXACT_MIRROR_REVIEW",
        "scope": "approved V14 right interface; exact X=0 mirror of lower-face-owned roles; approved HS-08 left upper head and HS-10 V9 left eye reused",
        "source_v14_blend_sha256": config["source_v14_blend_sha256"],
        "source_v14_validation_sha256": config["source_v14_validation_sha256"],
        "source_v9_bilateral_eye_blend_sha256": config["source_v9_bilateral_eye_blend_sha256"],
        "right_fingerprints_unchanged": True,
        "exact_mirror_roles": mirror_roles,
        "mirror_records": mirror_records,
        "left_context_validation": left_context_validation,
        "lower_face_component_count_each_side": lower_face_component_counts,
        "flange_pairs": pair_records,
        "owner_engagement": owner_records,
        "eye_clearances": clearance_records,
        "cross_side_interference_mm3": cross_side_interference,
        "inherited_lower_face_center_seam_overlap_retained": True,
        "rear_cassette_c006_aluminum_changed": False,
        "production_boolean_performed": False,
        "no_stl_or_gcode_exported": True,
        "locked_contract": contract,
        "holds": config["holds"],
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": renders,
            "object_obj_sha256": exports,
        },
    }
    (output / "validation-v15.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
