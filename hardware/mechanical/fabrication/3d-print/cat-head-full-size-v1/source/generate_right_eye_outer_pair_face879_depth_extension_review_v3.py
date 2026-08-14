#!/usr/bin/env python3
"""Extend the accepted right outer eye/head flanges inward by one tab depth."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_eye_all_eight_flange_broad_base_review_v3 as flange_v3  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate6_eye_modules as gate6  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/right-eye-outer-pair-face879-depth-extension-review-v3.json"


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def append_objects(blend: Path, names: list[str]) -> dict[str, bpy.types.Object]:
    with bpy.data.libraries.load(str(blend), link=False) as (source, target):
        missing = sorted(set(names) - set(source.objects))
        if missing:
            raise RuntimeError(f"accepted flange objects missing: {missing}")
        target.objects = names
    result = {}
    for obj in target.objects:
        bpy.context.scene.collection.objects.link(obj)
        result[obj.name] = obj
    return result


def import_freecad_obj(path: Path, name: str) -> bpy.types.Object:
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path))
    imported = [obj for obj in bpy.data.objects if obj not in before and obj.type == "MESH"]
    if len(imported) != 1:
        raise RuntimeError(f"expected one mesh from {path}, got {len(imported)}")
    obj = imported[0]
    obj.name = name
    for vertex in obj.data.vertices:
        x, y, z = vertex.co
        vertex.co = (x, z, -y)
    return obj


def duplicate(source: bpy.types.Object, name: str) -> bpy.types.Object:
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = name
    bpy.context.scene.collection.objects.link(obj)
    obj.hide_set(False)
    obj.hide_render = False
    return obj


def topology(obj: bpy.types.Object) -> dict[str, float | int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        return {
            "vertices": len(bm.verts),
            "edges": len(bm.edges),
            "faces": len(bm.faces),
            "boundary_edges": sum(1 for edge in bm.edges if len(edge.link_faces) == 1),
            "nonmanifold_edges": sum(1 for edge in bm.edges if len(edge.link_faces) > 2),
            "volume_mm3": round(abs(bm.calc_volume(signed=True)), 4),
        }
    finally:
        bm.free()


def fingerprint(obj: bpy.types.Object) -> str:
    vertices = [[round(value, 6) for value in obj.matrix_world @ vertex.co] for vertex in obj.data.vertices]
    faces = [list(poly.vertices) for poly in obj.data.polygons]
    return hashlib.sha256(json.dumps({"vertices": vertices, "faces": faces}, separators=(",", ":")).encode()).hexdigest()


def bvh(obj: bpy.types.Object) -> BVHTree:
    vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    polygons = [tuple(poly.vertices) for poly in obj.data.polygons]
    return BVHTree.FromPolygons(vertices, polygons, all_triangles=False)


def intersection_volume(first: bpy.types.Object, second: bpy.types.Object) -> float:
    target = duplicate(first, f"TMP_INTERSECTION_{first.name}")
    tool = duplicate(second, f"TMP_INTERSECTION_{second.name}")
    try:
        bpy.context.view_layer.objects.active = target
        modifier = target.modifiers.new("TMP_COMMON", "BOOLEAN")
        modifier.operation = "INTERSECT"
        modifier.solver = "EXACT"
        modifier.object = tool
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        return topology(target)["volume_mm3"] if target.data.polygons else 0.0
    finally:
        bpy.data.objects.remove(target, do_unlink=True)
        bpy.data.objects.remove(tool, do_unlink=True)


def distance(first: bpy.types.Object, second: bpy.types.Object) -> float:
    first_bvh, second_bvh = bvh(first), bvh(second)
    first_vertices = [first.matrix_world @ vertex.co for vertex in first.data.vertices]
    second_vertices = [second.matrix_world @ vertex.co for vertex in second.data.vertices]
    values = [second_bvh.find_nearest(point)[3] for point in first_vertices if second_bvh.find_nearest(point)]
    values += [first_bvh.find_nearest(point)[3] for point in second_vertices if first_bvh.find_nearest(point)]
    return float(min(values))


def material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    value = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    value.diffuse_color = color
    return value


def assign(obj: bpy.types.Object, assigned: bpy.types.Material) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(assigned)
    obj.color = assigned.diffuse_color


def create_extension(
    name: str,
    center: Vector,
    frame: dict,
    added_depth: float,
    overlap: float,
    assigned: bpy.types.Material,
    direction_sign: float = 1.0,
) -> bpy.types.Object:
    extension_axis = frame["inward"] * direction_sign
    owner_face = center + extension_axis * frame["dimensions"][1] / 2.0
    start = owner_face - extension_axis * overlap
    end = owner_face + extension_axis * added_depth
    return gate5.box(
        name,
        (start + end) / 2.0,
        (frame["tangent"], extension_axis, frame["radial"]),
        (frame["dimensions"][0], added_depth + overlap, frame["dimensions"][2]),
        assigned,
    )


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render(camera, output: Path, name: str, location: tuple[float, float, float], target: tuple[float, float, float], visible: set[bpy.types.Object]) -> str:
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_render = obj not in visible
            obj.hide_set(obj not in visible)
    camera.location = Vector(location)
    look_at(camera, Vector(target))
    path = output / "review" / f"{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path.relative_to(REPO_ROOT))


def export_obj(obj: bpy.types.Object, path: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.obj_export(filepath=str(path), export_selected_objects=True, export_materials=False, export_triangulated_mesh=True, forward_axis="Y", up_axis="Z")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source = repo_path(config["source_reinforcement_blend"])
    if Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError(f"open controlled source: {source}")
    output = repo_path(config["output_dir"])
    (output / "review").mkdir(parents=True, exist_ok=True)
    contract = config["locked_contract"]
    names = config["objects"]

    bucket = import_freecad_obj(repo_path(config["current_right_bucket_obj"]), "FROZEN__RIGHT_EYE_BUCKET_V9_V3")
    cap = import_freecad_obj(repo_path(config["current_right_cap_obj"]), "FROZEN__RIGHT_EYE_REAR_CAP_V9_V3")
    flanges = append_objects(repo_path(config["accepted_flange_blend"]), list(names.values()))
    frame = flange_v3.mount_frames(next(item for item in gate6.eye_geometry() if item["side"] == "right"))["outer"]
    purple = material("PROPOSED__FACE879_DEPTH_EXTENSION", (0.72, 0.1, 0.82, 1.0))
    gray = material("FROZEN__UNCHANGED", (0.32, 0.36, 0.4, 1.0))

    eye_extension = create_extension(
        "PROPOSED__RIGHT_OUTER_EYE__FACE879_DEPTH_EXTENSION_V3",
        frame["eye_center"], frame,
        float(contract["added_inward_depth_mm"]), float(contract["union_overlap_mm"]), purple,
    )
    head_extension = create_extension(
        "PROPOSED__RIGHT_OUTER_HEAD__MATCHING_DEPTH_EXTENSION_V3",
        frame["head_center"], frame,
        float(contract["added_inward_depth_mm"]), float(contract["union_overlap_mm"]), purple,
        -1.0,
    )
    outer_eye = flanges[names["outer_eye_flange"]]
    outer_head = flanges[names["outer_head_flange"]]
    lower_eye = flanges[names["lower_eye_flange"]]
    lower_head = flanges[names["lower_head_flange"]]
    for obj in (bucket, cap, outer_eye, outer_head, lower_eye, lower_head):
        assign(obj, gray)
    for obj in (eye_extension, head_extension):
        assign(obj, purple)

    eye_owner_overlap = intersection_volume(eye_extension, bucket)
    head_owner = bpy.data.objects["right_upper_head"]
    head_owner_overlap = intersection_volume(head_extension, head_owner)
    extension_pair_overlap = intersection_volume(eye_extension, head_extension)
    if eye_owner_overlap <= 0.0 or head_owner_overlap <= 0.0:
        raise RuntimeError(f"depth extensions miss owners: eye={eye_owner_overlap}, head={head_owner_overlap}")
    if extension_pair_overlap > 0.001:
        raise RuntimeError(f"mating extensions collide: {extension_pair_overlap} mm3")
    eye_topology = topology(eye_extension)
    head_topology = topology(head_extension)
    if any(record["boundary_edges"] or record["nonmanifold_edges"] for record in (eye_topology, head_topology)):
        raise RuntimeError("extension topology is not closed and manifold")

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.035, 0.045, 0.06)
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    camera_data = bpy.data.cameras.new("V3_REVIEW_CAMERA")
    camera = bpy.data.objects.new("V3_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 72

    context = {bucket, outer_head, eye_extension, head_extension, head_owner}
    renders = [
        render(camera, output, "01-outer-pair-owner-context", (155, 175, 185), (101, 85, 147), context),
        render(camera, output, "02-face879-depth-extensions-highlighted", (136, 128, 170), (101, 85, 147), {bucket, outer_head, eye_extension, head_extension}),
        render(camera, output, "03-extensions-isolated", (135, 125, 165), (101, 85, 147), {eye_extension, head_extension}),
    ]
    export_obj(bucket, output / "review/right_eye_bucket_v9.obj")
    export_obj(head_owner, output / "review/right_upper_head_context.obj")
    export_obj(outer_eye, output / "review/accepted_outer_eye_flange.obj")
    export_obj(outer_head, output / "review/accepted_outer_head_flange.obj")
    export_obj(eye_extension, output / "review/eye_face879_depth_extension.obj")
    export_obj(head_extension, output / "review/head_matching_depth_extension.obj")

    validation = {
        "status": config["status"],
        "locked_contract": contract,
        "approved_outer_eye_flange_fingerprint": fingerprint(outer_eye),
        "approved_outer_head_flange_fingerprint": fingerprint(outer_head),
        "lower_eye_flange_fingerprint_unchanged": fingerprint(lower_eye),
        "lower_head_flange_fingerprint_unchanged": fingerprint(lower_head),
        "eye_extension_topology": eye_topology,
        "head_extension_topology": head_topology,
        "eye_extension_owner_overlap_mm3": eye_owner_overlap,
        "head_extension_owner_overlap_mm3": head_owner_overlap,
        "extension_pair_overlap_mm3": extension_pair_overlap,
        "accepted_pair_clearance_mm": round(distance(outer_eye, outer_head), 4),
        "v2_outer_rectangular_base_present": False,
        "lower_pair_modified": False,
        "owner_boolean_performed": False,
        "mirror_performed": False,
        "no_stl_or_gcode_exported": True,
        "holds": config["holds"],
        "generated_files": {"renders": renders},
    }
    (output / "validation-v3.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "CAT_HEAD_RIGHT_EYE_OUTER_PAIR_FACE879_DEPTH_EXTENSION_REVIEW_V3.blend"))


if __name__ == "__main__":
    main()
