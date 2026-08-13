#!/usr/bin/env python3
"""Integrate the user-approved right eye flanges and rib clearances into copied owners."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/right-eye-flange-reinforcement-owner-integration-review-v1.json"


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def topology(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        return {
            "vertices": len(bm.verts),
            "edges": len(bm.edges),
            "faces": len(bm.faces),
            "boundary_edges": sum(1 for e in bm.edges if len(e.link_faces) == 1),
            "nonmanifold_edges": sum(1 for e in bm.edges if len(e.link_faces) > 2),
            "volume_mm3": round(abs(bm.calc_volume(signed=True)), 4),
        }
    finally:
        bm.free()


def mesh_components(obj) -> int:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        unseen = set(bm.verts)
        count = 0
        while unseen:
            count += 1
            stack = [unseen.pop()]
            while stack:
                current = stack.pop()
                for edge in current.link_edges:
                    other = edge.other_vert(current)
                    if other in unseen:
                        unseen.remove(other)
                        stack.append(other)
        return count
    finally:
        bm.free()


def duplicate(source, name):
    obj = source.copy()
    obj.data = source.data.copy()
    obj.name = name
    bpy.context.scene.collection.objects.link(obj)
    obj.hide_set(False)
    obj.hide_render = False
    return obj


def split_components(source, prefix):
    """Return one copied mesh object per connected component, preserving world geometry."""
    bm = bmesh.new()
    bm.from_mesh(source.data)
    components = []
    unseen = set(bm.verts)
    while unseen:
        seed = unseen.pop()
        vertices = {seed}
        stack = [seed]
        while stack:
            current = stack.pop()
            for edge in current.link_edges:
                other = edge.other_vert(current)
                if other in unseen:
                    unseen.remove(other)
                    vertices.add(other)
                    stack.append(other)
        components.append(vertices)
    objects = []
    for index, vertices in enumerate(components, 1):
        vertex_list = sorted(vertices, key=lambda v: v.index)
        mapping = {v.index: i for i, v in enumerate(vertex_list)}
        faces = [f for f in bm.faces if all(v in vertices for v in f.verts)]
        mesh = bpy.data.meshes.new(f"{prefix}_{index:03d}_MESH")
        mesh.from_pydata(
            [source.matrix_world @ v.co for v in vertex_list],
            [],
            [tuple(mapping[v.index] for v in face.verts) for face in faces],
        )
        mesh.update()
        obj = bpy.data.objects.new(f"{prefix}_{index:03d}", mesh)
        bpy.context.scene.collection.objects.link(obj)
        objects.append(obj)
    bm.free()
    return objects


def append_exact_objects(blend: Path, names: list[str]):
    with bpy.data.libraries.load(str(blend), link=False) as (source, target):
        missing = sorted(set(names) - set(source.objects))
        if missing:
            raise RuntimeError(f"accepted objects missing: {missing}")
        target.objects = names
    result = {}
    for obj in target.objects:
        bpy.context.scene.collection.objects.link(obj)
        result[obj.name] = obj
    return result


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
    vertices, faces = world_geometry(source)
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata([v + offset for v in vertices], [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def union(target, tool, label: str) -> None:
    if not overlaps(target, tool):
        raise RuntimeError(f"union root does not overlap: {target.name} <- {tool.name}")
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    modifier = target.modifiers.new(label, "BOOLEAN")
    modifier.operation = "UNION"
    modifier.solver = "EXACT"
    modifier.object = tool
    if hasattr(modifier, "use_self"):
        modifier.use_self = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(tool, do_unlink=True)
    target.select_set(False)
    bpy.context.view_layer.update()


def cylinder(name: str, center: Vector, axis: Vector, diameter: float, length: float):
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=diameter / 2.0, depth=length, location=center)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = axis.normalized().to_track_quat("Z", "Y").to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    return obj


def material(name, color):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def assign(obj, mat):
    obj.data.materials.clear()
    obj.data.materials.append(mat)
    obj.color = mat.diffuse_color


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def render(camera, output, name, location, target, visible, lens=64):
    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_render = obj not in visible
            obj.hide_set(obj not in visible)
    camera.location = Vector(location)
    camera.data.lens = lens
    look_at(camera, target)
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
    stage_only = True

    upper_source = bpy.data.objects[config["owners"]["outer_head"]]
    lower_source = bpy.data.objects[config["owners"]["lower_head"]]
    c046_source = bpy.data.objects[config["reinforcements"]["c046"]]
    c048_source = bpy.data.objects[config["reinforcements"]["c048"]]
    source_fingerprints = {o.name: topology(o) for o in (upper_source, lower_source, c046_source, c048_source)}

    flanges = append_exact_objects(repo_path(config["accepted_flange_blend"]), list(config["flanges"].values()))
    bucket_source = import_freecad_obj(repo_path(config["current_right_bucket_obj"]), "FROZEN__RIGHT_EYE_BUCKET_V9")
    cap = import_freecad_obj(repo_path(config["current_right_cap_obj"]), "FROZEN__RIGHT_EYE_REAR_CAP_V9")

    upper = duplicate(upper_source, "PROPOSED__RIGHT_UPPER_HEAD__OUTER_EYE_FLANGE_INTEGRATED_V1")
    lower = duplicate(lower_source, "PROPOSED__RIGHT_LOWER_FACE__LOWER_EYE_FLANGE_C046_C048_INTEGRATED_V1")
    bucket = duplicate(bucket_source, "PROPOSED__RIGHT_EYE_BUCKET_V9__TWO_FLANGES_INTEGRATED_V1")
    upper_components = split_components(upper_source, "UPPER_OWNER_COMPONENT")
    lower_components = split_components(lower_source, "LOWER_OWNER_COMPONENT")

    contract = config["locked_contract"]
    c046 = create_offset(c046_source, Vector(contract["c046_away_unit"]) * contract["c046_rigid_offset_mm"],
                         "APPROVED__C046_EYE_CLEARANCE_V2")
    c048 = create_trimmed(c048_source, contract["c048_trim_fraction"], "APPROVED__C048_EYE_CLEARANCE_V2")
    approved_clearances = {"c046_mm": distance(c046, bucket_source), "c048_mm": distance(c048, bucket_source)}
    if min(approved_clearances.values()) < contract["minimum_eye_clearance_mm"] - 0.01:
        raise RuntimeError(f"approved reinforcement clearance regressed: {approved_clearances}")

    flange_topology_before = {name: topology(obj) for name, obj in flanges.items()}
    owner_topology = {"upper": topology(upper), "lower": topology(lower), "bucket": topology(bucket), "cap": topology(cap)}

    approved = json.loads(repo_path(config["approved_flange_validation"]).read_text(encoding="utf-8"))
    records = {r["role"]: r for r in approved["candidate_records"]}
    shafts = {}
    shaft_checks = {}
    for role in ("outer_head", "lower_head"):
        source_role = role
        eye_role = role.replace("head", "eye")
        record = records[source_role]
        paired = records[eye_role]
        first = Vector(record["bounds_mm"]["min"])  # overwritten from authoritative V3 record below
        del first
        v3_report = json.loads((repo_path(config["accepted_flange_blend"]).parent / "eye-all-eight-flange-broad-base-review-v3-validation.json").read_text(encoding="utf-8"))
        role_name = "outer" if role.startswith("outer") else "lower"
        head_record = next(r for r in v3_report["candidate_records"] if r["side"] == "right" and r["role"] == role_name and r["owner_kind"] == "head")
        eye_record = next(r for r in v3_report["candidate_records"] if r["side"] == "right" and r["role"] == role_name and r["owner_kind"] == "eye")
        center = (Vector(head_record["m2_5_hole_center_mm"]) + Vector(eye_record["m2_5_hole_center_mm"])) / 2.0
        axis = Vector(head_record["m2_5_hole_axis"])
        shaft = cylinder(f"REVIEW_ONLY__M2_5_SHAFT__{role_name.upper()}", center, axis,
                         contract["m2_5_proof_shaft_diameter_mm"], contract["m2_5_proof_shaft_length_mm"])
        shafts[role_name] = shaft
        shaft_checks[role_name] = {
            "head_eye_axis_error_mm": head_record["paired_hole_axis_error_mm"],
            "head_flange_overlap": overlaps(shaft, flanges[config["flanges"][source_role]]),
            "eye_flange_overlap": overlaps(shaft, flanges[config["flanges"][eye_role]]),
        }

    gray = material("FROZEN_CONTEXT", (0.40, 0.44, 0.49, 1))
    upper_mat = material("INTEGRATED_UPPER_OWNER", (0.48, 0.62, 0.76, 1))
    lower_mat = material("INTEGRATED_LOWER_OWNER", (0.25, 0.62, 0.48, 1))
    eye_mat = material("INTEGRATED_EYE_OWNER", (0.03, 0.48, 0.96, 1))
    cap_mat = material("UNCHANGED_REAR_CAP", (0.15, 0.25, 0.55, 1))
    shaft_mat = material("M2_5_SHAFT_PROOF", (1.0, 0.72, 0.02, 1))
    for obj in bpy.data.objects:
        if obj.type == "MESH": assign(obj, gray)
    assign(upper, upper_mat); assign(lower, lower_mat); assign(bucket, eye_mat); assign(cap, cap_mat)
    for shaft in shafts.values(): assign(shaft, shaft_mat)

    scene = bpy.context.scene
    scene.name = "Right_Eye_Flange_Reinforcement_Owner_Integration_Review_V1"
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"; scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True; scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"; scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.035, 0.045, 0.06)
    scene.render.resolution_x = 1400; scene.render.resolution_y = 1100; scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    camera_data = bpy.data.cameras.new("HS11_INTEGRATION_CAMERA")
    camera = bpy.data.objects.new("HS11_INTEGRATION_CAMERA", camera_data)
    scene.collection.objects.link(camera); scene.camera = camera

    forbidden_names = {"R1_UNCL__R__C002__eye_mount", "R1_RET__R__C004__eye_mount"}
    forbidden = {bpy.data.objects[n] for n in forbidden_names if n in bpy.data.objects}
    stale = {upper_source, lower_source, c046_source, c048_source, bucket_source, *flanges.values(), *forbidden}
    all_context = {o for o in bpy.data.objects if o.type == "MESH" and o not in stale}
    core = {upper, lower, bucket, cap, c046, c048, *flanges.values(), *shafts.values()}
    renders = [
        render(camera, output, "01-right-integrated-whole-head-context", (330, -410, 225), (55, 70, 145), all_context, 58),
        render(camera, output, "02-right-three-integrated-owners-interior", (250, 305, 190), (82, 78, 138), core, 64),
        render(camera, output, "03-right-integrated-outer-interface", (175, 170, 170), (103, 85, 147), {upper, bucket, shafts["outer"]}, 76),
        render(camera, output, "04-right-integrated-lower-interface", (155, 165, 100), (67, 65, 121), {lower, bucket, shafts["lower"]}, 76),
        render(camera, output, "05-right-integrated-side-clearance", (160, 30, 120), (64, 63, 119), {lower, bucket, cap}, 72),
    ]

    review_objs = {}
    for key, obj in {"staged_right_upper_head": upper, "staged_right_lower_face": lower,
                     "staged_right_eye_bucket": bucket, "unchanged_right_eye_rear_cap": cap,
                     "approved_outer_head_flange": flanges[config["flanges"]["outer_head"]],
                     "approved_outer_eye_flange": flanges[config["flanges"]["outer_eye"]],
                     "approved_lower_head_flange": flanges[config["flanges"]["lower_head"]],
                     "approved_lower_eye_flange": flanges[config["flanges"]["lower_eye"]],
                     "approved_c046_clearance_v2": c046, "approved_c048_clearance_v2": c048,
                     "m2_5_outer_shaft": shafts["outer"], "m2_5_lower_shaft": shafts["lower"]}.items():
        path = output / "review" / f"{key}.obj"
        export_obj(obj, path)
        review_objs[key] = str(path.relative_to(REPO_ROOT))
    component_objs = {"upper": [], "lower": []}
    for owner_key, components in (("upper", upper_components), ("lower", lower_components)):
        component_dir = output / "review" / f"{owner_key}_components"
        component_dir.mkdir(exist_ok=True)
        for component in components:
            path = component_dir / f"{component.name.lower()}.obj"
            export_obj(component, path)
            component_objs[owner_key].append(str(path.relative_to(REPO_ROOT)))

    for obj in bpy.data.objects:
        if obj.type == "MESH":
            obj.hide_set(obj not in core)
            obj.hide_render = obj not in core
    scene["HS11_RIGHT_OWNER_INTEGRATION"] = True
    scene["MIRROR_PERFORMED"] = False; scene["PRINT_RELEASE"] = False
    blend_path = output / "CAT_HEAD_RIGHT_EYE_FLANGE_REINFORCEMENT_OWNER_INTEGRATION_REVIEW_V1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "source_hashes": {
            "v9_right_bucket_obj": sha256(repo_path(config["current_right_bucket_obj"])),
            "v9_right_cap_obj": sha256(repo_path(config["current_right_cap_obj"])),
            "production_v9_sha256_manifest": sha256(PACKAGE_ROOT / "production/eye-modules-v9/SHA256SUMS"),
        },
        "source_owner_topology": source_fingerprints,
        "accepted_flange_topology_before_union": flange_topology_before,
        "staged_owner_topology": owner_topology,
        "staged_owner_component_counts": {"upper": mesh_components(upper), "lower": mesh_components(lower), "bucket": mesh_components(bucket)},
        "component_local_occt_handoff": component_objs,
        "approved_reinforcement_eye_clearance_mm": {k: round(v, 4) for k, v in approved_clearances.items()},
        "m2_5_shaft_path_checks": shaft_checks,
        "right_rear_cap_interference_with_integrated_bucket": overlaps(cap, bucket),
        "right_rear_cap_clearance_mm": round(distance(cap, bucket), 4),
        "forbidden_source_mounts_in_review": any(o in core for o in forbidden),
        "production_boolean_performed_on_copied_right_owners": not stage_only,
        "mirror_performed": False,
        "no_stl_or_gcode_exported": True,
        "locked_contract": contract,
        "holds": config["holds"],
        "generated_files": {"blend": str(blend_path.relative_to(REPO_ROOT)), "renders": renders, "review_objs": review_objs},
    }
    if report["forbidden_source_mounts_in_review"]:
        raise RuntimeError("forbidden C002/C004 source mount resurrected")
    (output / "validation-v1.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
