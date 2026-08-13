#!/usr/bin/env python3
"""Give C046 and C048 a common 4 mm clearance envelope around the V9 eye."""

from __future__ import annotations

import json
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/right-eye-reinforcement-clearance-review-v2.json"


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def world_geometry(obj):
    return ([obj.matrix_world @ v.co for v in obj.data.vertices], [tuple(p.vertices) for p in obj.data.polygons])


def bvh(obj):
    return BVHTree.FromPolygons(*world_geometry(obj), all_triangles=False)


def overlaps(a, b) -> bool:
    return bool(bvh(a).overlap(bvh(b)))


def distance(a, b) -> float:
    av, _ = world_geometry(a)
    bv, _ = world_geometry(b)
    ab, bb = bvh(a), bvh(b)
    values = [bb.find_nearest(p)[3] for p in av if bb.find_nearest(p)]
    values += [ab.find_nearest(p)[3] for p in bv if ab.find_nearest(p)]
    return float(min(values))


def import_freecad_obj(path: Path, name: str):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=str(path))
    imported = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if len(imported) != 1:
        raise RuntimeError(f"expected one mesh from {path}, got {len(imported)}")
    obj = imported[0]
    obj.name = name
    for vertex in obj.data.vertices:
        x, y, z = vertex.co
        vertex.co = (x, z, -y)
    return obj


def append_object(blend: Path, name: str):
    with bpy.data.libraries.load(str(blend), link=False) as (source, target):
        if name not in source.objects:
            raise RuntimeError(f"missing accepted object: {name}")
        target.objects = [name]
    obj = target.objects[0]
    bpy.context.scene.collection.objects.link(obj)
    return obj


def create_trimmed(source, fraction: float, name: str):
    world = [source.matrix_world @ v.co for v in source.data.vertices]
    vertices = [world[i].lerp(world[i + 3], fraction) for i in range(3)] + world[3:]
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(vertices, [], [tuple(p.vertices) for p in source.data.polygons])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def create_offset(source, offset: Vector, name: str):
    world, faces = world_geometry(source)
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata([p + offset for p in world], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def topology(obj):
    counts = {}
    for poly in obj.data.polygons:
        for edge in poly.edge_keys:
            key = tuple(sorted(edge))
            counts[key] = counts.get(key, 0) + 1
    return {
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "faces": len(obj.data.polygons),
        "boundary_edges": sum(v == 1 for v in counts.values()),
        "nonmanifold_edges": sum(v > 2 for v in counts.values()),
    }


def center(points):
    return sum(points, Vector()) / len(points)


def material(name, color):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def assign(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj.color = mat.diffuse_color


def look_at(obj, target):
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def render(camera, output, name, location, target, visible):
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


def export_obj(obj, path):
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.hide_viewport = False
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.obj_export(filepath=str(path), export_selected_objects=True, export_materials=False,
                          export_triangulated_mesh=True, forward_axis="Y", up_axis="Z")


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    source = repo_path(config["source_reinforcement_blend"])
    if Path(bpy.data.filepath).resolve() != source:
        raise RuntimeError(f"open controlled reinforcement source: {source}")
    output = repo_path(config["output_dir"])
    (output / "review").mkdir(parents=True, exist_ok=True)

    original_c046 = bpy.data.objects[config["triangular_reinforcement"]]
    original_c048 = bpy.data.objects[config["long_reinforcement"]]
    owner = bpy.data.objects[config["lower_face_owner"]]
    eye = import_freecad_obj(repo_path(config["current_right_bucket_obj"]), "CURRENT_RIGHT_EYE_BUCKET_V9")
    lower_eye = append_object(repo_path(config["accepted_flange_blend"]), config["lower_eye_flange"])
    lower_head = append_object(repo_path(config["accepted_flange_blend"]), config["lower_head_flange"])

    c048_world = [original_c048.matrix_world @ v.co for v in original_c048.data.vertices]
    c048_start, c048_end = center(c048_world[:3]), center(c048_world[3:])
    c048_length = (c048_end - c048_start).length
    eye_bvh = bvh(eye)
    closest = min(((p, eye_bvh.find_nearest(p)) for p in world_geometry(original_c046)[0]), key=lambda item: item[1][3])
    away = (closest[0] - closest[1][0]).normalized()
    target = float(config["minimum_eye_clearance_mm"])

    chosen = None
    fraction_step = float(config["search_step_fraction"])
    offset_step = float(config["search_step_offset_mm"])
    for fraction_index in range(1, int(1.0 / fraction_step)):
        fraction = fraction_index * fraction_step
        if c048_length * (1.0 - fraction) < float(config["minimum_remaining_c048_length_mm"]):
            break
        c048 = create_trimmed(original_c048, fraction, "PROPOSED__R1_RET__R__C048__RIB_EYE_CLEARANCE_V2")
        if overlaps(c048, eye) or distance(c048, eye) < target:
            bpy.data.objects.remove(c048, do_unlink=True)
            continue
        for offset_index in range(1, int(float(config["maximum_c046_offset_mm"]) / offset_step) + 1):
            offset_mm = offset_index * offset_step
            c046 = create_offset(original_c046, away * offset_mm, "PROPOSED__R1_RET__R__C046__TRIANGULAR_RIB_EYE_CLEARANCE_V2")
            if (not overlaps(c046, eye) and distance(c046, eye) >= target and overlaps(c046, owner)
                    and overlaps(c048, owner) and overlaps(c046, c048)):
                chosen = (fraction, offset_mm, c046, c048)
                break
            bpy.data.objects.remove(c046, do_unlink=True)
        if chosen:
            break
        bpy.data.objects.remove(c048, do_unlink=True)
    if not chosen:
        raise RuntimeError("no joint C046+C048 proposal satisfies 4 mm clearance and structural contacts")

    fraction, offset_mm, c046, c048 = chosen
    c046_topo, c048_topo = topology(c046), topology(c048)
    if any(c046_topo[k] or c048_topo[k] for k in ("boundary_edges", "nonmanifold_edges")):
        raise RuntimeError("proposal topology is not closed/manifold")

    gray = material("FROZEN_CONTEXT_GRAY", (0.40, 0.44, 0.49, 1))
    red = material("REJECTED_REINFORCEMENT_RED", (0.95, 0.04, 0.02, 1))
    cyan = material("PROPOSED_REINFORCEMENT_CYAN", (0.02, 0.86, 1.0, 1))
    blue = material("CURRENT_V9_EYE_BLUE", (0.03, 0.46, 0.96, 1))
    purple = material("ACCEPTED_HEAD_FLANGE_PURPLE", (0.72, 0.16, 0.92, 1))
    orange = material("ACCEPTED_EYE_FLANGE_ORANGE", (1.0, 0.34, 0.03, 1))
    for obj in (owner,): assign(obj, gray)
    for obj in (original_c046, original_c048): assign(obj, red)
    for obj in (c046, c048): assign(obj, cyan)
    assign(eye, blue); assign(lower_head, purple); assign(lower_eye, orange)

    scene = bpy.context.scene
    scene.name = "Right_Eye_Reinforcement_Clearance_Review_V2"
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.035, 0.045, 0.06)
    scene.render.resolution_x = 1400; scene.render.resolution_y = 1100; scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    cam_data = bpy.data.cameras.new("REINFORCEMENT_CLEARANCE_CAMERA")
    cam = bpy.data.objects.new("REINFORCEMENT_CLEARANCE_CAMERA", cam_data)
    scene.collection.objects.link(cam); scene.camera = cam; cam.data.lens = 72
    context = {owner, eye, lower_head, lower_eye}
    renders = [
        render(cam, output, "01-rejected-original-clearance", (155, 148, 112), (64, 63, 119), context | {original_c046, original_c048}),
        render(cam, output, "02-proposed-four-mm-clearance", (155, 148, 112), (64, 63, 119), context | {c046, c048}),
        render(cam, output, "03-proposed-side-clearance", (160, 30, 120), (64, 63, 119), context | {c046, c048}),
        render(cam, output, "04-proposed-reinforcement-isolated", (145, 125, 105), (55, 56, 112), {c046, c048}),
    ]

    review_objs = {}
    for key, obj in {
        "right_lower_face_context": owner, "current_right_eye_bucket_v9": eye,
        "rejected_c046_original": original_c046, "rejected_c048_original": original_c048,
        "proposed_c046_clearance_v2": c046, "proposed_c048_clearance_v2": c048,
        "accepted_right_lower_head_flange_v3": lower_head, "accepted_right_lower_eye_flange_v3": lower_eye,
    }.items():
        path = output / "review" / f"{key}.obj"
        export_obj(obj, path)
        review_objs[key] = str(path.relative_to(REPO_ROOT))

    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_render = obj not in context | {c046, c048}
            obj.hide_set(obj not in context | {c046, c048})
    original_c046.hide_set(True); original_c048.hide_set(True)
    scene["REVIEW_ONLY"] = True; scene["PRODUCTION_BOOLEAN_PERFORMED"] = False
    scene["MIRROR_PERFORMED"] = False; scene["PRINT_RELEASE"] = False
    blend_path = output / "CAT_HEAD_RIGHT_EYE_REINFORCEMENT_CLEARANCE_REVIEW_V2.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    result = {
        "status": config["status"],
        "selected_anchors": {
            "c046_object": original_c046.name,
            "c046_closest_vertex_mm": [round(v, 4) for v in closest[0]],
            "c046_away_unit": [round(v, 6) for v in away],
            "c048_eye_side_vertices": [0, 1, 2],
            "c048_far_end_vertices": [3, 4, 5],
        },
        "minimum_required_eye_clearance_mm": target,
        "c046_original_eye_clearance_mm": round(distance(original_c046, eye), 4),
        "c046_rigid_offset_mm": round(offset_mm, 4),
        "c046_proposed_eye_clearance_mm": round(distance(c046, eye), 4),
        "c046_topology": c046_topo,
        "c046_overlaps_lower_face_owner": overlaps(c046, owner),
        "c048_original_length_mm": round(c048_length, 4),
        "c048_trim_fraction": round(fraction, 4),
        "c048_removed_eye_side_length_mm": round(c048_length * fraction, 4),
        "c048_remaining_length_mm": round(c048_length * (1.0 - fraction), 4),
        "c048_proposed_eye_clearance_mm": round(distance(c048, eye), 4),
        "c048_far_end_preserved_exactly": all((world_geometry(c048)[0][i] - c048_world[i]).length <= 1e-9 for i in range(3, 6)),
        "c048_topology": c048_topo,
        "c048_overlaps_lower_face_owner": overlaps(c048, owner),
        "proposed_c046_overlaps_proposed_c048": overlaps(c046, c048),
        "c046_eye_overlap": overlaps(c046, eye),
        "c048_eye_overlap": overlaps(c048, eye),
        "production_boolean_performed": False, "mirror_performed": False, "no_stl_or_gcode_exported": True,
        "holds": config["holds"],
        "generated_files": {"blend": str(blend_path.relative_to(REPO_ROOT)), "renders": renders, "review_objs": review_objs},
    }
    (output / "validation-v2.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
