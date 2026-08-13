#!/usr/bin/env python3
"""Trim only C048's eye-side end to clear the current V9 eye assembly."""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/right-eye-c048-clearance-review-v1.json"


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def world_geometry(obj: bpy.types.Object):
    return (
        [obj.matrix_world @ vertex.co for vertex in obj.data.vertices],
        [tuple(poly.vertices) for poly in obj.data.polygons],
    )


def world_bvh(obj: bpy.types.Object) -> BVHTree:
    return BVHTree.FromPolygons(*world_geometry(obj), all_triangles=False)


def overlaps(first: bpy.types.Object, second: bpy.types.Object) -> bool:
    return bool(world_bvh(first).overlap(world_bvh(second)))


def distance(first: bpy.types.Object, second: bpy.types.Object) -> float:
    first_vertices, _ = world_geometry(first)
    second_vertices, _ = world_geometry(second)
    first_bvh = world_bvh(first)
    second_bvh = world_bvh(second)
    best = float("inf")
    for point in first_vertices:
        nearest = second_bvh.find_nearest(point)
        if nearest:
            best = min(best, nearest[3])
    for point in second_vertices:
        nearest = first_bvh.find_nearest(point)
        if nearest:
            best = min(best, nearest[3])
    return float(best)


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


def append_object(blend: Path, name: str) -> bpy.types.Object:
    with bpy.data.libraries.load(str(blend), link=False) as (source, target):
        if name not in source.objects:
            raise RuntimeError(f"missing accepted object: {name}")
        target.objects = [name]
    obj = target.objects[0]
    bpy.context.scene.collection.objects.link(obj)
    return obj


def material(name: str, color):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def assign(obj: bpy.types.Object, mat) -> None:
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj.color = mat.diffuse_color


def create_trimmed(source: bpy.types.Object, fraction: float) -> bpy.types.Object:
    if len(source.data.vertices) != 6:
        raise RuntimeError("C048 topology changed: expected six prism vertices")
    world = [source.matrix_world @ vertex.co for vertex in source.data.vertices]
    vertices = [world[i].lerp(world[i + 3], fraction) for i in range(3)] + world[3:]
    faces = [tuple(poly.vertices) for poly in source.data.polygons]
    mesh = bpy.data.meshes.new("PROPOSED_C048_CLEARANCE_TRIM_MESH")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new("PROPOSED__R1_RET__R__C048__RIB_EYE_CLEARANCE_V1", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def topology(obj: bpy.types.Object) -> dict[str, int]:
    counts = {}
    for poly in obj.data.polygons:
        for a, b in poly.edge_keys:
            key = tuple(sorted((a, b)))
            counts[key] = counts.get(key, 0) + 1
    return {
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "faces": len(obj.data.polygons),
        "boundary_edges": sum(value == 1 for value in counts.values()),
        "nonmanifold_edges": sum(value > 2 for value in counts.values()),
    }


def center(vertices: list[Vector]) -> Vector:
    return sum(vertices, Vector()) / len(vertices)


def look_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render(camera, output: Path, name: str, location, target, visible) -> str:
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
    """Export one review mesh in FreeCAD-compatible OBJ coordinates."""
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.hide_viewport = False
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
    source = repo_path(config["source_reinforcement_blend"])
    if Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError(f"open the controlled reinforcement source: {source}")
    output = repo_path(config["output_dir"])
    output.mkdir(parents=True, exist_ok=True)
    (output / "review").mkdir(exist_ok=True)

    original = bpy.data.objects[config["offending_rib"]]
    owner = bpy.data.objects[config["lower_face_owner"]]
    bucket = import_freecad_obj(repo_path(config["current_right_bucket_obj"]), "CURRENT_RIGHT_EYE_BUCKET_V9")
    lower_eye = append_object(repo_path(config["accepted_flange_blend"]), config["lower_eye_flange"])
    lower_head = append_object(repo_path(config["accepted_flange_blend"]), config["lower_head_flange"])

    original_world = [original.matrix_world @ vertex.co for vertex in original.data.vertices]
    original_start = center(original_world[:3])
    original_end = center(original_world[3:])
    original_length = (original_end - original_start).length
    minimum_clearance = float(config["minimum_eye_clearance_mm"])
    minimum_length = float(config["minimum_remaining_rib_length_mm"])
    step = float(config["search_step_fraction"])

    candidate = None
    chosen_fraction = None
    bucket_gap = None
    eye_flange_gap = None
    for index in range(1, int(1.0 / step)):
        fraction = index * step
        remaining = original_length * (1.0 - fraction)
        if remaining < minimum_length:
            break
        trial = create_trimmed(original, fraction)
        bucket_overlap = overlaps(trial, bucket)
        eye_flange_overlap = overlaps(trial, lower_eye)
        bgap = 0.0 if bucket_overlap else distance(trial, bucket)
        egap = 0.0 if eye_flange_overlap else distance(trial, lower_eye)
        if not bucket_overlap and not eye_flange_overlap and bgap >= minimum_clearance and egap >= minimum_clearance:
            candidate = trial
            chosen_fraction = fraction
            bucket_gap = bgap
            eye_flange_gap = egap
            break
        bpy.data.objects.remove(trial, do_unlink=True)
    if candidate is None:
        raise RuntimeError("no C048 axial trim satisfies the clearance and remaining-length gates")

    new_world = [candidate.matrix_world @ vertex.co for vertex in candidate.data.vertices]
    new_start = center(new_world[:3])
    remaining_length = (original_end - new_start).length
    removed_length = (new_start - original_start).length
    topo = topology(candidate)
    owner_overlap = overlaps(candidate, owner)
    lower_head_overlap = overlaps(candidate, lower_head)
    if topo["boundary_edges"] or topo["nonmanifold_edges"]:
        raise RuntimeError(f"trimmed C048 is not closed/manifold: {topo}")
    if not owner_overlap:
        raise RuntimeError("trimmed C048 is no longer rooted in right_lower_face")

    frozen_mat = material("FROZEN_CONTEXT_GRAY", (0.40, 0.44, 0.49, 1.0))
    original_mat = material("REJECTED_COLLIDING_C048_RED", (0.95, 0.04, 0.02, 1.0))
    proposal_mat = material("PROPOSED_TRIMMED_C048_CYAN", (0.02, 0.86, 1.0, 1.0))
    bucket_mat = material("CURRENT_V9_EYE_BLUE", (0.03, 0.46, 0.96, 1.0))
    head_flange_mat = material("ACCEPTED_HEAD_FLANGE_PURPLE", (0.72, 0.16, 0.92, 1.0))
    eye_flange_mat = material("ACCEPTED_EYE_FLANGE_ORANGE", (1.0, 0.34, 0.03, 1.0))
    assign(owner, frozen_mat)
    assign(original, original_mat)
    assign(candidate, proposal_mat)
    assign(bucket, bucket_mat)
    assign(lower_head, head_flange_mat)
    assign(lower_eye, eye_flange_mat)
    original.show_in_front = True
    candidate.show_in_front = True

    scene = bpy.context.scene
    scene.name = "Right_Eye_C048_Clearance_Review_V1"
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
    camera_data = bpy.data.cameras.new("C048_REVIEW_CAMERA")
    camera = bpy.data.objects.new("C048_REVIEW_CAMERA", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 72

    common = {owner, bucket, lower_head, lower_eye}
    renders = [
        render(camera, output, "01-rejected-original-collision", (155, 148, 112), (64, 63, 119), common | {original}),
        render(camera, output, "02-proposed-trimmed-clearance", (155, 148, 112), (64, 63, 119), common | {candidate}),
        render(camera, output, "03-proposed-side-clearance", (160, 30, 120), (64, 63, 119), common | {candidate}),
        render(camera, output, "04-proposed-rib-isolated", (145, 125, 105), (60, 57, 107), {candidate}),
    ]

    review_objs = {}
    export_items = {
        "right_lower_face_context": owner,
        "current_right_eye_bucket_v9": bucket,
        "rejected_colliding_c048_original": original,
        "proposed_trimmed_c048_clearance_v1": candidate,
        "accepted_right_lower_head_flange_v3": lower_head,
        "accepted_right_lower_eye_flange_v3": lower_eye,
    }
    for key, obj in export_items.items():
        path = output / "review" / f"{key}.obj"
        export_obj(obj, path)
        review_objs[key] = str(path.relative_to(REPO_ROOT))

    original.hide_render = True
    original.hide_set(True)
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_render = obj not in common | {candidate}
            obj.hide_set(obj not in common | {candidate})
    scene["REVIEW_ONLY"] = True
    scene["PRODUCTION_BOOLEAN_PERFORMED"] = False
    scene["MIRROR_PERFORMED"] = False
    scene["PRINT_RELEASE"] = False
    blend_path = output / "CAT_HEAD_RIGHT_EYE_C048_CLEARANCE_REVIEW_V1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    validation = {
        "status": config["status"],
        "offending_object": original.name,
        "selected_anchor": {
            "eye_side_end_face_vertices": [0, 1, 2],
            "eye_side_centroid_mm": [round(v, 4) for v in original_start],
            "far_end_face_vertices": [3, 4, 5],
            "far_end_centroid_mm": [round(v, 4) for v in original_end],
            "original_axis_unit": [round(v, 6) for v in (original_end - original_start).normalized()],
        },
        "original_length_mm": round(original_length, 4),
        "trim_fraction": round(chosen_fraction, 4),
        "removed_eye_side_length_mm": round(removed_length, 4),
        "remaining_rib_length_mm": round(remaining_length, 4),
        "minimum_required_remaining_length_mm": minimum_length,
        "v9_bucket_clearance_mm": round(bucket_gap, 4),
        "lower_eye_flange_clearance_mm": round(eye_flange_gap, 4),
        "minimum_required_clearance_mm": minimum_clearance,
        "candidate_topology": topo,
        "candidate_overlaps_lower_face_owner": owner_overlap,
        "candidate_overlaps_lower_head_flange": lower_head_overlap,
        "v9_bucket_overlap": overlaps(candidate, bucket),
        "lower_eye_flange_overlap": overlaps(candidate, lower_eye),
        "far_end_preserved_exactly": all((new_world[i] - original_world[i]).length <= 1e-9 for i in range(3, 6)),
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
    report_path = output / "validation-v1.json"
    report_path.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(validation, indent=2))


if __name__ == "__main__":
    main()
