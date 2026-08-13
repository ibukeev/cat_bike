#!/usr/bin/env python3
"""Assemble the approved right V3 eye flanges against current owners.

This is a non-destructive alignment proposal.  It appends the exact accepted
V3 flange meshes into the frozen V10 full-head scene, replaces the stale eye
bucket/cap visual references with the promoted V9 owners, validates the four
owner-root contacts, and writes an evidence pack.  It performs no owner fuse.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/right-eye-flange-owner-alignment-review-v1.json"


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def material(name: str, rgba: tuple[float, float, float, float]):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    return mat


def assign(obj: bpy.types.Object, mat: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj.color = mat.diffuse_color


def fingerprint(obj: bpy.types.Object) -> str:
    vertices = [tuple(round(v, 6) for v in vertex.co) for vertex in obj.data.vertices]
    faces = [tuple(poly.vertices) for poly in obj.data.polygons]
    payload = json.dumps({"vertices": vertices, "faces": faces}, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def append_exact_objects(blend: Path, names: list[str]) -> dict[str, bpy.types.Object]:
    with bpy.data.libraries.load(str(blend), link=False) as (source, target):
        missing = sorted(set(names) - set(source.objects))
        if missing:
            raise RuntimeError(f"accepted V3 objects missing: {missing}")
        target.objects = names
    result = {}
    for obj in target.objects:
        if obj is None:
            raise RuntimeError("failed to append an accepted V3 flange")
        bpy.context.scene.collection.objects.link(obj)
        result[obj.name] = obj
    return result


def import_freecad_obj(path: Path, name: str) -> bpy.types.Object:
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path))
    imported = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if len(imported) != 1:
        raise RuntimeError(f"expected one mesh from {path}, got {len(imported)}")
    obj = imported[0]
    obj.name = name
    # Restore repository Z-up from FreeCAD OBJ's Y-up exchange coordinates.
    for vertex in obj.data.vertices:
        x, y, z = vertex.co
        vertex.co = (x, z, -y)
    return obj


def evaluated_mesh(obj: bpy.types.Object):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    return obj.evaluated_get(depsgraph).to_mesh()


def topology(obj: bpy.types.Object) -> dict[str, int]:
    mesh = evaluated_mesh(obj)
    try:
        edge_counts = {edge.index: 0 for edge in mesh.edges}
        for polygon in mesh.polygons:
            for edge_index in polygon.edge_keys:
                # edge_keys are vertex pairs; count explicitly below.
                pass
        counts: dict[tuple[int, int], int] = {}
        for poly in mesh.polygons:
            for a, b in poly.edge_keys:
                key = tuple(sorted((a, b)))
                counts[key] = counts.get(key, 0) + 1
        return {
            "vertices": len(mesh.vertices),
            "edges": len(mesh.edges),
            "faces": len(mesh.polygons),
            "boundary_edges": sum(count == 1 for count in counts.values()),
            "nonmanifold_edges": sum(count > 2 for count in counts.values()),
        }
    finally:
        obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()


def objects_overlap(first: bpy.types.Object, second: bpy.types.Object) -> bool:
    # Exact Boolean intersection on duplicates avoids altering either owner.
    first_copy = first.copy()
    first_copy.data = first.data.copy()
    second_copy = second.copy()
    second_copy.data = second.data.copy()
    bpy.context.scene.collection.objects.link(first_copy)
    bpy.context.scene.collection.objects.link(second_copy)
    try:
        bpy.context.view_layer.objects.active = first_copy
        first_copy.select_set(True)
        modifier = first_copy.modifiers.new("REVIEW_ONLY__INTERSECTION", "BOOLEAN")
        modifier.operation = "INTERSECT"
        modifier.solver = "EXACT"
        modifier.object = second_copy
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        return len(first_copy.data.polygons) > 0 and abs(first_copy.dimensions.x * first_copy.dimensions.y * first_copy.dimensions.z) > 1e-7
    finally:
        bpy.data.objects.remove(first_copy, do_unlink=True)
        bpy.data.objects.remove(second_copy, do_unlink=True)


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def camera() -> bpy.types.Object:
    data = bpy.data.cameras.new("HS11_RIGHT_REVIEW_CAMERA")
    obj = bpy.data.objects.new("HS11_RIGHT_REVIEW_CAMERA", data)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.scene.camera = obj
    return obj


def render(cam: bpy.types.Object, output: Path, name: str, location, target, visible, lens=60.0):
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_render = obj not in visible
            obj.hide_set(obj not in visible)
    cam.location = Vector(location)
    cam.data.lens = lens
    look_at(cam, Vector(target))
    path = output / "review" / f"{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path.relative_to(REPO_ROOT))


def export_obj(obj: bpy.types.Object, path: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.obj_export(
        filepath=str(path),
        export_selected_objects=True,
        export_materials=False,
        export_triangulated_mesh=True,
        forward_axis="Y",
        up_axis="Z",
    )


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    baseline = repo_path(config["frozen_context_blend"])
    accepted = repo_path(config["accepted_flange_blend"])
    output = repo_path(config["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "review").mkdir(exist_ok=True)
    if Path(bpy.data.filepath).resolve() != baseline:
        raise RuntimeError(f"open frozen V10 baseline: {baseline}")

    stale_eye_names = {
        "right_eye_bucket",
        "right_eye_led_rear_cap",
        "left_eye_bucket",
        "left_eye_led_rear_cap",
    }
    for name in stale_eye_names:
        obj = bpy.data.objects.get(name)
        if obj:
            obj.hide_render = True
            obj.hide_set(True)

    flange_names = list(config["right_flange_objects"].values())
    flanges = append_exact_objects(accepted, flange_names)
    right_bucket = import_freecad_obj(
        repo_path(config["current_right_bucket_obj"]),
        config["right_owner_objects"]["eye_bucket"],
    )
    right_cap = import_freecad_obj(
        repo_path(config["current_right_cap_obj"]),
        config["right_owner_objects"]["eye_rear_cap"],
    )
    upper = bpy.data.objects[config["right_owner_objects"]["outer_head"]]
    lower = bpy.data.objects[config["right_owner_objects"]["lower_head"]]

    context_mat = material("HS11_FROZEN_CONTEXT", (0.48, 0.52, 0.57, 1.0))
    upper_mat = material("HS11_CURRENT_UPPER_OWNER", (0.52, 0.57, 0.63, 1.0))
    lower_mat = material("HS11_CURRENT_LOWER_OWNER", (0.34, 0.47, 0.42, 1.0))
    bucket_mat = material("HS11_CURRENT_V9_BUCKET", (0.04, 0.48, 0.95, 1.0))
    cap_mat = material("HS11_CURRENT_V9_CAP", (0.02, 0.20, 0.56, 1.0))
    head_mat = material("HS11_ACCEPTED_HEAD_FLANGE", (0.73, 0.20, 0.93, 1.0))
    eye_mat = material("HS11_ACCEPTED_EYE_FLANGE", (1.0, 0.35, 0.04, 1.0))
    for obj in bpy.data.objects:
        if obj.type == "MESH" and obj.name not in stale_eye_names:
            assign(obj, context_mat)
    assign(upper, upper_mat)
    assign(lower, lower_mat)
    assign(right_bucket, bucket_mat)
    assign(right_cap, cap_mat)
    for key, name in config["right_flange_objects"].items():
        assign(flanges[name], head_mat if key.endswith("head") else eye_mat)
        flanges[name].show_in_front = True
        flanges[name]["review_only"] = True
        flanges[name]["accepted_source"] = "eye-all-eight-flange-broad-base-review-v3"

    owner_by_key = {
        "outer_head": upper,
        "lower_head": lower,
        "outer_eye": right_bucket,
        "lower_eye": right_bucket,
    }
    records = []
    for key, name in config["right_flange_objects"].items():
        obj = flanges[name]
        owner = owner_by_key[key]
        topo = topology(obj)
        record = {
            "role": key,
            "candidate": name,
            "owner": owner.name,
            "mesh_fingerprint": fingerprint(obj),
            "bounds_mm": {
                "min": [round(v, 4) for v in obj.bound_box[0]],
                "dimensions": [round(v, 4) for v in obj.dimensions],
            },
            "topology": topo,
            "overlaps_current_owner": objects_overlap(obj, owner),
        }
        if topo["boundary_edges"] or topo["nonmanifold_edges"]:
            raise RuntimeError(f"accepted flange is not manifold: {name}: {topo}")
        if not record["overlaps_current_owner"]:
            raise RuntimeError(f"accepted flange misses current owner: {name} -> {owner.name}")
        records.append(record)

    scene = bpy.context.scene
    scene.name = "HS11_Right_Eye_Flange_Owner_Alignment_Review_V1"
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
    cam = camera()

    all_context = {o for o in bpy.data.objects if o.type == "MESH" and o.name not in stale_eye_names}
    review_core = {upper, lower, right_bucket, right_cap, *flanges.values()}
    outer = {upper, right_bucket, flanges[config["right_flange_objects"]["outer_head"]], flanges[config["right_flange_objects"]["outer_eye"]]}
    lower_pair = {lower, right_bucket, flanges[config["right_flange_objects"]["lower_head"]], flanges[config["right_flange_objects"]["lower_eye"]]}
    renders = [
        render(cam, output, "01-right-flanges-whole-head", (330, -410, 225), (55, 70, 145), all_context, 58),
        render(cam, output, "02-right-four-flanges-interior", (250, 305, 190), (82, 78, 138), review_core, 64),
        render(cam, output, "03-right-outer-pair", (175, 170, 170), (103, 85, 147), outer, 72),
        render(cam, output, "04-right-lower-pair", (155, 165, 100), (72, 69, 120), lower_pair, 72),
        render(cam, output, "05-right-four-flanges-side", (305, 45, 155), (82, 78, 138), review_core, 70),
    ]

    review_objs = {}
    export_items = {
        "right_upper_head_context": upper,
        "right_lower_face_context": lower,
        "right_eye_bucket_v9": right_bucket,
        **{key: flanges[name] for key, name in config["right_flange_objects"].items()},
    }
    for key, obj in export_items.items():
        path = output / "review" / f"{key}.obj"
        export_obj(obj, path)
        review_objs[key] = str(path.relative_to(REPO_ROOT))

    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_render = obj not in review_core
            obj.hide_set(obj not in review_core)
    scene["HS11_REVIEW_ONLY"] = True
    scene["RIGHT_FLANGE_COUNT"] = 4
    scene["PRODUCTION_BOOLEAN_PERFORMED"] = False
    scene["MIRROR_PERFORMED"] = False
    scene["PRINT_RELEASE"] = False
    blend_path = output / "CAT_HEAD_RIGHT_EYE_FLANGE_OWNER_ALIGNMENT_REVIEW_V1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "config": str(CONFIG_PATH.relative_to(REPO_ROOT)),
        "source_context": config["frozen_context_blend"],
        "accepted_flange_source": config["accepted_flange_blend"],
        "current_right_bucket_source": config["current_right_bucket_obj"],
        "locked_contract": config["locked_contract"],
        "right_flange_count": len(records),
        "candidate_records": records,
        "all_four_flange_roots_overlap_current_owners": all(r["overlaps_current_owner"] for r in records),
        "all_four_flange_meshes_closed_and_manifold": all(not r["topology"]["boundary_edges"] and not r["topology"]["nonmanifold_edges"] for r in records),
        "forbidden_source_mounts_present": any(name in bpy.data.objects for name in ("R1_UNCL__R__C002__eye_mount", "R1_RET__R__C004__eye_mount")),
        "production_boolean_performed": False,
        "mirror_performed": False,
        "no_stl_or_gcode_exported": True,
        "holds": config["holds"],
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": renders,
            "review_objs": review_objs,
        },
    }
    if report["forbidden_source_mounts_present"]:
        raise RuntimeError("forbidden C002/C004 source mount resurrected")
    validation = output / "validation-v1.json"
    validation.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
