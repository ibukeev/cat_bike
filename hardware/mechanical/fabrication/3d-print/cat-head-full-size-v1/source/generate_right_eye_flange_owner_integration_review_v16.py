#!/usr/bin/env python3
"""Build the V16 right-side owner-integration review from frozen sources."""

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
DEFAULT_CONFIG = PACKAGE_ROOT / "config/right-eye-flange-owner-integration-review-v16.json"
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


def import_obj(path: Path, name: str) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path), forward_axis="Y", up_axis="Z")
    imported = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    if len(imported) != 1:
        raise RuntimeError(f"Expected one mesh from {path}, got {len(imported)}")
    obj = imported[0]
    obj.name = name
    obj.data.name = f"{name}_MESH"
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return obj


def append_upper_head_components(blend_path: Path, expected_count: int) -> list[bpy.types.Object]:
    prefix = "PROPOSED__RIGHT_UPPER_HEAD_REPAIRED_COMPONENT__"
    with bpy.data.libraries.load(str(blend_path), link=False) as (data_from, data_to):
        names = sorted(name for name in data_from.objects if name.startswith(prefix))
        if len(names) != expected_count:
            raise RuntimeError(f"Expected {expected_count} V3 upper-head components, got {len(names)}")
        data_to.objects = names
    result = []
    for obj in data_to.objects:
        if obj is None or obj.type != "MESH":
            raise RuntimeError("V3 upper-head library contained a non-mesh object")
        bpy.context.scene.collection.objects.link(obj)
        result.append(obj)
    return result


def duplicate(obj: bpy.types.Object, name: str) -> bpy.types.Object:
    copy = obj.copy()
    copy.data = obj.data.copy()
    copy.name = name
    copy.data.name = f"{name}_MESH"
    bpy.context.scene.collection.objects.link(copy)
    return copy


def join(objects: list[bpy.types.Object], name: str) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    result = objects[0]
    result.name = name
    result.data.name = f"{name}_MESH"
    return result


def boolean_union(target: bpy.types.Object, tool: bpy.types.Object, label: str, solver: str) -> None:
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    modifier = target.modifiers.new(label, "BOOLEAN")
    modifier.operation = "UNION"
    modifier.solver = solver
    modifier.object = tool
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def topology(obj: bpy.types.Object) -> dict[str, float | int]:
    return v14.v10.v9.v3.topology(obj)


def nonadjacent_self_intersections(obj: bpy.types.Object) -> list[dict[str, object]]:
    """Describe overlapping triangles that do not share a mesh vertex."""
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
        records: list[dict[str, object]] = []
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
            points = [vertex.co.copy() for face in (first, second) for vertex in face.verts]
            minimum = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
            maximum = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
            records.append(
                {
                    "triangles": list(pair),
                    "first_centroid_mm": [round(value, 4) for value in first.calc_center_median()],
                    "second_centroid_mm": [round(value, 4) for value in second.calc_center_median()],
                    "pair_bbox_min_mm": [round(value, 4) for value in minimum],
                    "pair_bbox_max_mm": [round(value, 4) for value in maximum],
                }
            )
        return sorted(records, key=lambda record: record["triangles"])
    finally:
        bm.free()


def weld_diagnostic(obj: bpy.types.Object, distance_mm: float) -> dict[str, object]:
    """Test a coordinate-preserving coincident-vertex weld on a disposable copy."""
    candidate = duplicate(obj, f"AUDIT__WELD_{distance_mm:.0e}_V16")
    before = topology(candidate)
    bm = bmesh.new()
    bm.from_mesh(candidate.data)
    try:
        result = bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=distance_mm)
        bm.to_mesh(candidate.data)
        candidate.data.update()
    finally:
        bm.free()
    after = topology(candidate)
    intersections = nonadjacent_self_intersections(candidate)
    bpy.data.objects.remove(candidate, do_unlink=True)
    return {
        "distance_mm": distance_mm,
        "removed_vertex_count": before["vertices"] - after["vertices"],
        "topology": after,
        "self_intersection_count": len(intersections),
    }


def export_obj(
    obj: bpy.types.Object,
    path: Path,
    *,
    triangulated: bool = False,
) -> str:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.obj_export(
        filepath=str(path),
        export_selected_objects=True,
        export_triangulated_mesh=triangulated,
        forward_axis="Y",
        up_axis="Z",
    )
    return sha256(path)


def main() -> None:
    config_path = parse_args().config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    contract = config["locked_contract"]
    output = repo_path(config["output_dir"])
    review = output / "review"
    objects_dir = output / "objects"
    review.mkdir(parents=True, exist_ok=True)
    objects_dir.mkdir(parents=True, exist_ok=True)

    locked_sources = (
        ("source_v14_blend", "source_v14_blend_sha256"),
        ("source_v14_validation", "source_v14_validation_sha256"),
        ("source_upper_head_v3_blend", "source_upper_head_v3_blend_sha256"),
        ("source_component_inventory", "source_component_inventory_sha256"),
        ("source_component_001_v13", "source_component_001_v13_sha256"),
    )
    for path_key, hash_key in locked_sources:
        path = repo_path(config[path_key])
        actual = sha256(path)
        if actual != config[hash_key]:
            raise RuntimeError(f"Frozen input changed: {path} -> {actual}")

    source_v14 = repo_path(config["source_v14_blend"])
    bpy.ops.wm.open_mainfile(filepath=str(source_v14))
    names = config["source_objects"]
    legacy_upper = bpy.data.objects.get(names["legacy_upper_head_to_replace"])
    if legacy_upper is None:
        raise RuntimeError("Incomplete V15/V14 legacy upper-head context is missing")
    bpy.data.objects.remove(legacy_upper, do_unlink=True)

    upper_components = append_upper_head_components(
        repo_path(config["source_upper_head_v3_blend"]),
        int(contract["complete_upper_head_component_count"]),
    )
    complete_upper = join(
        upper_components,
        "FROZEN__RIGHT_UPPER_HEAD_COMPLETE_V3__V16",
    )

    inventory = json.loads(repo_path(config["source_component_inventory"]).read_text())
    if inventory["component_count"] != int(contract["lower_face_component_count"]):
        raise RuntimeError("Frozen lower-face component inventory changed")
    lower_context_parts = [
        import_obj(repo_path(record["path"]), f"FROZEN__{record['name']}__V16")
        for record in inventory["components"][1:]
    ]
    lower_context = join(
        lower_context_parts,
        "FROZEN__RIGHT_LOWER_FACE_COMPONENTS_002_060__CONTEXT_V16",
    )
    component_001 = import_obj(
        repo_path(config["source_component_001_v13"]),
        "FROZEN__RIGHT_LOWER_FACE_COMPONENT001_REPAIRED_V13__V16",
    )

    source = {key: bpy.data.objects.get(value) for key, value in names.items() if key != "legacy_upper_head_to_replace"}
    missing = [key for key, obj in source.items() if obj is None]
    if missing:
        raise RuntimeError(f"Missing frozen V14 objects: {missing}")

    pair_gaps = {}
    for role in ("outer", "second"):
        gap = v14.v10.v9.v3.distance(source[f"{role}_head_flange"], source[f"{role}_eye_flange"])
        if abs(gap - float(contract["mating_gap_mm"])) > float(contract["maximum_pair_gap_error_mm"]):
            raise RuntimeError(f"Frozen {role} pair gap changed: {gap}")
        pair_gaps[role] = round(gap, 4)

    upper_owner_review = join(
        [duplicate(complete_upper, "TMP__UPPER_OWNER_V16"), duplicate(source["outer_head_flange"], "TMP__OUTER_HEAD_FLANGE_V16")],
        "PROPOSED__RIGHT_UPPER_HEAD_WITH_OUTER_HEAD_FLANGE__V16_REVIEW_MESH",
    )
    lower_owner_review = join(
        [
            component_001,
            duplicate(source["second_head_flange"], "TMP__SECOND_HEAD_FLANGE_V16"),
            duplicate(source["c046"], "TMP__C046_V16"),
            duplicate(source["c048"], "TMP__C048_V16"),
        ],
        "PROPOSED__RIGHT_LOWER_FACE_COMPONENT001_WITH_SECOND_HEAD_C046_C048__V16_REVIEW_MESH",
    )

    eye_owner = duplicate(source["eye_bucket"], "PROPOSED__RIGHT_EYE_BUCKET_WITH_BOTH_EYE_FLANGES__V16")
    eye_source_topology = topology(eye_owner)
    eye_intersection_stages = {
        "source_eye_bucket": nonadjacent_self_intersections(eye_owner),
    }
    for role in ("outer", "second"):
        near = duplicate(source[f"{role}_eye_flange"], f"TMP__{role.upper()}_EYE_FLANGE_EPSILON_V16")
        inward = duplicate(source[f"{role}_eye_flange"], f"TMP__{role.upper()}_EYE_FLANGE_INWARD_V16")
        vector = Vector(contract[f"{role}_eye_inward_vector_mm"])
        if abs(vector.length - float(contract["eye_flange_interior_extension_mm"])) > 0.002:
            raise RuntimeError(f"{role} inward vector length changed: {vector.length}")
        near.location += vector.normalized() * float(contract["boolean_epsilon_inset_mm"])
        inward.location += vector
        boolean_union(eye_owner, near, f"V16_{role}_epsilon_owner_union", "EXACT")
        eye_intersection_stages[f"after_{role}_epsilon_union"] = nonadjacent_self_intersections(eye_owner)
        boolean_union(eye_owner, inward, f"V16_{role}_inward_owner_union", "EXACT")
        eye_intersection_stages[f"after_{role}_inward_union"] = nonadjacent_self_intersections(eye_owner)

    eye_topology = topology(eye_owner)
    if eye_topology["boundary_edges"] != 0 or eye_topology["nonmanifold_edges"] != 0:
        raise RuntimeError(f"V16 eye owner is not closed/manifold: {eye_topology}")
    eye_component_count = len(v14.v10.v9.components(eye_owner))
    if eye_component_count != 1:
        raise RuntimeError(f"V16 eye owner is not one connected component: {eye_component_count}; topology={eye_topology}")
    eye_self_intersections = nonadjacent_self_intersections(eye_owner)
    eye_self_intersection_count = len(eye_self_intersections)
    eye_weld_diagnostics = [
        weld_diagnostic(eye_owner, distance)
        for distance in (0.000001, 0.00001, 0.0001, 0.001)
    ]

    c046_clearance = v14.v10.v9.v3.distance(source["c046"], source["eye_bucket"])
    c048_clearance = v14.v10.v9.v3.distance(source["c048"], source["eye_bucket"])
    for label, actual, expected in (
        ("C046", c046_clearance, contract["c046_eye_clearance_mm"]),
        ("C048", c048_clearance, contract["c048_eye_clearance_mm"]),
    ):
        if abs(actual - float(expected)) > 0.01:
            raise RuntimeError(f"{label} eye clearance changed: {actual}")

    grey = v14.v10.v9.v3.material("FROZEN__V16_GREY", (0.34, 0.38, 0.43, 1.0))
    blue = v14.v10.v9.v3.material("PROPOSED__V16_OWNER_BLUE", (0.10, 0.45, 0.82, 1.0))
    cyan = v14.v10.v9.v3.material("PROPOSED__V16_EYE_CYAN", (0.05, 0.82, 0.92, 1.0))
    v14.v10.v9.v3.assign(lower_context, grey)
    v14.v10.v9.v3.assign(upper_owner_review, blue)
    v14.v10.v9.v3.assign(lower_owner_review, blue)
    v14.v10.v9.v3.assign(eye_owner, cyan)

    visible = {upper_owner_review, lower_owner_review, lower_context, eye_owner}
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_set(obj not in visible)
            obj.hide_render = obj not in visible

    scene = bpy.context.scene
    scene.name = "Right_Eye_Flange_Owner_Integration_Review_V16"
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
    camera_data = bpy.data.cameras.new("V16_REVIEW_CAMERA")
    camera = bpy.data.objects.new("V16_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 66
    renders = [
        v14.v10.v9.v3.render(camera, output, "01-v16-complete-right-owner-context", (390, -500, 300), (55, 105, 140), visible),
        v14.v10.v9.v3.render(camera, output, "02-v16-eye-two-owner-pairs-interior", (145, 135, 110), (63, 70, 130), visible),
        v14.v10.v9.v3.render(camera, output, "03-v16-complete-upper-head-owner", (260, -290, 275), (55, 145, 190), {upper_owner_review}),
        v14.v10.v9.v3.render(camera, output, "04-v16-lower-owner-and-eye", (175, 150, 85), (65, 80, 115), {lower_owner_review, lower_context, eye_owner}),
    ]

    scene["REVIEW_ONLY"] = True
    scene["RIGHT_SIDE_ONLY"] = True
    scene["COMPLETE_V3_UPPER_HEAD_USED"] = True
    scene["FREECAD_UPPER_AND_LOWER_OWNER_BOOLEANS_VALIDATED"] = True
    scene["BLENDER_EYE_OWNER_BOOLEAN_PERFORMED"] = True
    scene["MIRROR_PERFORMED"] = False
    scene["PRINT_RELEASE"] = False

    blend_path = output / "CAT_HEAD_RIGHT_EYE_FLANGE_OWNER_INTEGRATION_REVIEW_V16.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    eye_obj = objects_dir / "right_eye_bucket_with_both_eye_flange_roots_v16.obj"
    eye_freecad_transfer_obj = (
        objects_dir
        / "right_eye_bucket_with_both_eye_flange_roots_freecad_transfer_v16.obj"
    )
    lower_context_obj = objects_dir / "right_lower_face_components_002_060_context_v16.obj"
    generated = {
        "blend": str(blend_path.relative_to(REPO_ROOT)),
        "blend_sha256": sha256(blend_path),
        "eye_owner_obj": str(eye_obj.relative_to(REPO_ROOT)),
        "eye_owner_obj_sha256": export_obj(eye_owner, eye_obj),
        "eye_owner_freecad_transfer_obj": str(
            eye_freecad_transfer_obj.relative_to(REPO_ROOT)
        ),
        "eye_owner_freecad_transfer_obj_sha256": export_obj(
            eye_owner,
            eye_freecad_transfer_obj,
            triangulated=True,
        ),
        "lower_context_obj": str(lower_context_obj.relative_to(REPO_ROOT)),
        "lower_context_obj_sha256": export_obj(lower_context, lower_context_obj),
        "renders": renders,
    }
    report = {
        "status": (
            "PASS_BLENDER_RIGHT_OWNER_INTEGRATION_PROOF"
            if eye_self_intersection_count == 0
            else "HOLD_RIGHT_EYE_OWNER_SELF_INTERSECTIONS"
        ),
        "scope": "right side only; complete V3 upper head, repaired lower component001, unchanged lower components002-060, and both eye roots",
        "complete_upper_head_component_count": int(contract["complete_upper_head_component_count"]),
        "lower_face_component_count": int(contract["lower_face_component_count"]),
        "source_pair_gaps_mm": pair_gaps,
        "proposed_integrated_pair_gaps_mm": {
            role: round(gap - float(contract["boolean_epsilon_inset_mm"]), 4)
            for role, gap in pair_gaps.items()
        },
        "mating_leaf_shape_retained": True,
        "mating_leaf_position_inset_mm": float(contract["boolean_epsilon_inset_mm"]),
        "eye_source_topology": eye_source_topology,
        "eye_integrated_topology": eye_topology,
        "eye_integrated_connected_components": eye_component_count,
        "eye_integrated_nonadjacent_self_intersections": eye_self_intersection_count,
        "eye_integrated_self_intersection_records": eye_self_intersections,
        "eye_self_intersection_stage_counts": {
            stage: len(records) for stage, records in eye_intersection_stages.items()
        },
        "eye_self_intersection_stage_records": eye_intersection_stages,
        "eye_weld_diagnostics": eye_weld_diagnostics,
        "c046_eye_clearance_mm": round(c046_clearance, 4),
        "c048_eye_clearance_mm": round(c048_clearance, 4),
        "freecad_completed_owner_objects": contract["freecad_completed_owner_objects"],
        "freecad_eye_boolean_status": contract["freecad_eye_boolean_status"],
        "rear_cassette_c006_aluminum_changed": False,
        "mirror_performed": False,
        "no_stl_or_gcode_exported": True,
        "locked_contract": contract,
        "holds": config["holds"],
        "generated_files": generated,
    }
    (output / "validation-v16.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
