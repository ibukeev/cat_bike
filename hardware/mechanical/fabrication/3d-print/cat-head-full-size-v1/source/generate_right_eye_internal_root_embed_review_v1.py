#!/usr/bin/env python3
"""Propose minimal hidden root embeds for the right eye flanges and C048."""

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

import generate_c002_outer_flange_dual_root_upper_head_review_v2 as v2  # noqa: E402
import generate_eye_all_eight_flange_broad_base_review_v3 as flange_v3  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate6_eye_modules as gate6  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
CONFIG_PATH = PACKAGE_ROOT / "config/right-eye-internal-root-embed-review-v1.json"


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def world_geometry(obj):
    return ([obj.matrix_world @ v.co for v in obj.data.vertices], [tuple(p.vertices) for p in obj.data.polygons])


def bvh(obj):
    return BVHTree.FromPolygons(*world_geometry(obj), all_triangles=False)


def overlaps(a, b) -> bool:
    return bool(bvh(a).overlap(bvh(b)))


def distance(a, b) -> float:
    av, _ = world_geometry(a); bv, _ = world_geometry(b)
    ab, bb = bvh(a), bvh(b)
    values = [bb.find_nearest(p)[3] for p in av if bb.find_nearest(p)]
    values += [ab.find_nearest(p)[3] for p in bv if ab.find_nearest(p)]
    return float(min(values))


def topology(obj):
    bm = bmesh.new(); bm.from_mesh(obj.data)
    try:
        return {
            "vertices": len(bm.verts), "edges": len(bm.edges), "faces": len(bm.faces),
            "boundary_edges": sum(1 for e in bm.edges if len(e.link_faces) == 1),
            "nonmanifold_edges": sum(1 for e in bm.edges if len(e.link_faces) > 2),
            "volume_mm3": round(abs(bm.calc_volume(signed=True)), 4),
        }
    finally:
        bm.free()


def fingerprint(obj):
    vertices, faces = world_geometry(obj)
    payload = json.dumps({"vertices": [[round(x, 6) for x in v] for v in vertices], "faces": faces}, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def append_objects(blend: Path, names: list[str]):
    with bpy.data.libraries.load(str(blend), link=False) as (source, target):
        missing = sorted(set(names) - set(source.objects))
        if missing: raise RuntimeError(f"accepted flange objects missing: {missing}")
        target.objects = names
    result = {}
    for obj in target.objects:
        bpy.context.scene.collection.objects.link(obj); result[obj.name] = obj
    return result


def import_freecad_obj(path: Path, name: str):
    before = set(bpy.data.objects); bpy.ops.wm.obj_import(filepath=str(path))
    imported = [o for o in bpy.data.objects if o not in before and o.type == "MESH"]
    if len(imported) != 1: raise RuntimeError(f"expected one mesh from {path}, got {len(imported)}")
    obj = imported[0]; obj.name = name
    for vertex in obj.data.vertices:
        x, y, z = vertex.co; vertex.co = (x, z, -y)
    return obj


def create_trimmed_c048(source, fraction: float, name: str):
    world = [source.matrix_world @ v.co for v in source.data.vertices]
    vertices = [world[i].lerp(world[i + 3], fraction) for i in range(3)] + world[3:]
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(vertices, [], [tuple(p.vertices) for p in source.data.polygons]); mesh.update()
    obj = bpy.data.objects.new(name, mesh); bpy.context.scene.collection.objects.link(obj)
    return obj


def duplicate(source, name):
    obj = source.copy(); obj.data = source.data.copy(); obj.name = name
    bpy.context.scene.collection.objects.link(obj); obj.hide_set(False); obj.hide_render = False
    return obj


def apply_union(target, tool, name):
    bpy.ops.object.select_all(action="DESELECT"); target.select_set(True); bpy.context.view_layer.objects.active = target
    modifier = target.modifiers.new(name, "BOOLEAN"); modifier.operation = "UNION"; modifier.solver = "EXACT"; modifier.object = tool
    if hasattr(modifier, "use_self"): modifier.use_self = True
    bpy.ops.object.modifier_apply(modifier=modifier.name); bpy.data.objects.remove(tool, do_unlink=True); target.select_set(False)


def prism_from_face(name, source, face_index, direction, embed, overlap):
    face = source.data.polygons[face_index]
    points = [source.matrix_world @ source.data.vertices[i].co for i in face.vertices]
    start = [p - direction * overlap for p in points]
    end = [p + direction * embed for p in points]
    n = len(points); faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    mesh = bpy.data.meshes.new(f"{name}_MESH"); mesh.from_pydata(start + end, [], faces); mesh.update()
    obj = bpy.data.objects.new(name, mesh); bpy.context.scene.collection.objects.link(obj)
    return obj


def localized_prism_from_side_face(name, source, face_index, direction, embed, overlap, safe_end_fraction):
    face = source.data.polygons[face_index]
    indices = list(face.vertices)
    if len(indices) != 4:
        raise RuntimeError(f"expected quadrilateral C048 side face, got {len(indices)} vertices on face {face_index}")
    world = [source.matrix_world @ source.data.vertices[index].co for index in indices]
    safe_end = (world[0], world[1])
    unsafe_end = (world[3], world[2])
    points = [
        safe_end[0],
        safe_end[1],
        safe_end[1].lerp(unsafe_end[1], safe_end_fraction),
        safe_end[0].lerp(unsafe_end[0], safe_end_fraction),
    ]
    start = [point - direction * overlap for point in points]
    end = [point + direction * embed for point in points]
    n = len(points)
    faces = [tuple(range(n - 1, -1, -1)), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    mesh = bpy.data.meshes.new(f"{name}_MESH")
    mesh.from_pydata(start + end, [], faces); mesh.update()
    obj = bpy.data.objects.new(name, mesh); bpy.context.scene.collection.objects.link(obj)
    return obj


def intersection_volume(first, second) -> float:
    target = duplicate(first, f"TMP_INTERSECTION_{first.name}")
    tool = duplicate(second, f"TMP_INTERSECTION_{second.name}")
    try:
        bpy.ops.object.select_all(action="DESELECT"); target.select_set(True); bpy.context.view_layer.objects.active = target
        modifier = target.modifiers.new("TMP_EXACT_COMMON", "BOOLEAN"); modifier.operation = "INTERSECT"; modifier.solver = "EXACT"; modifier.object = tool
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        return topology(target)["volume_mm3"] if target.data.polygons else 0.0
    finally:
        bpy.data.objects.remove(target, do_unlink=True); bpy.data.objects.remove(tool, do_unlink=True)


def build_eye_root(name, flange, owner, frame, embed, overlap, hole_diameter, root_width, root_depth, flange_width):
    backing = frame["radial"]
    center = frame["eye_center"]
    owner_face = center + backing * frame["dimensions"][2] / 2.0
    old_owner_end = owner_face + backing * (4.0 - 0.8)
    root_material = material("PROPOSED_INTERNAL_ROOT_BUILD", (1.0, 0.03, 0.62, 1.0))
    shift = max(0.0, (root_width - flange_width) / 2.0)
    candidates = []
    for sign in (-1.0, 1.0):
        shifted_start = old_owner_end - backing * overlap + frame["tangent"] * shift * sign
        shifted_end = old_owner_end + backing * embed + frame["tangent"] * shift * sign
        candidate = v2.tapered_prism(
            f"{name}__DIRECTION_{int(sign):+d}", shifted_start, shifted_end,
            frame["tangent"], frame["inward"], root_width, root_width,
            root_depth, root_depth, root_material,
        )
        gate6.cut_axis_hole(candidate, f"{candidate.name}__M2_5_CLEARANCE", frame["eye_hole_center"], frame["radial"], hole_diameter, 12.0)
        candidates.append((intersection_volume(candidate, owner), candidate))
    candidates.sort(key=lambda item: item[0], reverse=True)
    root = candidates[0][1]
    bpy.data.objects.remove(candidates[1][1], do_unlink=True)
    root.name = name
    proposal = duplicate(flange, name.replace("ROOT_ADDITION", "FLANGE_WITH_ROOT_EMBED"))
    if not root_width == 22.0:
        apply_union(proposal, duplicate(root, f"TOOL__{name}"), "UNION__INTERNAL_ROOT_EMBED")
    return root, proposal


def material(name, color):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name); mat.diffuse_color = color; return mat


def assign(obj, mat):
    obj.data.materials.clear(); obj.data.materials.append(mat); obj.color = mat.diffuse_color


def look_at(obj, target):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def render(camera, output, name, location, target, visible, lens=72):
    for obj in bpy.data.objects:
        if obj.type == "MESH": obj.hide_render = obj not in visible; obj.hide_set(obj not in visible)
    camera.location = Vector(location); camera.data.lens = lens; look_at(camera, target)
    path = output / "review" / f"{name}.png"; bpy.context.scene.render.filepath = str(path); bpy.ops.render.render(write_still=True)
    return str(path.relative_to(REPO_ROOT))


def export_obj(obj, path):
    bpy.ops.object.select_all(action="DESELECT"); obj.hide_set(False); obj.hide_viewport = False; obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.obj_export(filepath=str(path), export_selected_objects=True, export_materials=False,
                          export_triangulated_mesh=True, forward_axis="Y", up_axis="Z")


def main():
    config_path = Path(sys.argv[sys.argv.index("--") + 1]).resolve() if "--" in sys.argv else CONFIG_PATH
    config = json.loads(config_path.read_text(encoding="utf-8")); source = repo_path(config["source_reinforcement_blend"])
    if Path(bpy.data.filepath).resolve() != source: raise RuntimeError(f"open controlled reinforcement source: {source}")
    output = repo_path(config["output_dir"]); (output / "review").mkdir(parents=True, exist_ok=True)
    contract = config["locked_contract"]; names = config["objects"]

    lower_owner = bpy.data.objects[names["lower_face_owner"]]
    c048_source = bpy.data.objects[names["c048"]]
    clearance = json.loads(repo_path(config["approved_clearance_validation"]).read_text(encoding="utf-8"))
    c048 = create_trimmed_c048(c048_source, clearance["c048_trim_fraction"], "APPROVED__C048_EYE_CLEARANCE_V2")
    bucket = import_freecad_obj(repo_path(config["current_right_bucket_obj"]), "FROZEN__RIGHT_EYE_BUCKET_V9")
    cap = import_freecad_obj(repo_path(config["current_right_cap_obj"]), "FROZEN__RIGHT_EYE_REAR_CAP_V9")
    flanges = append_objects(repo_path(config["accepted_flange_blend"]), [names[k] for k in ("outer_eye_flange", "lower_eye_flange", "outer_head_flange", "lower_head_flange")])

    frame = flange_v3.mount_frames(next(g for g in gate6.eye_geometry() if g["side"] == "right"))
    eye_proposals = {}
    root_additions = {}
    for role in ("outer", "lower"):
        key = f"{role}_eye_flange"
        root, proposal = build_eye_root(f"PROPOSED__RIGHT_{role.upper()}_EYE_FLANGE__ROOT_ADDITION_V1",
                                        flanges[names[key]], bucket, frame[role], contract["internal_embed_mm"],
                                        contract["root_overlap_with_approved_feature_mm"], contract["m2_5_clearance_diameter_mm"],
                                        contract.get("root_width_mm", 16.0), contract.get("root_depth_mm", 12.0),
                                        contract.get("approved_flange_width_mm", contract.get("root_width_mm", 16.0)))
        root_additions[role] = root; eye_proposals[role] = proposal

    contact_faces = [int(contract["c048_root_side_face_index_zero_based"])]
    alternatives = []
    for contact_face in contact_faces:
        base_normal = (c048.matrix_world.to_3x3() @ c048.data.polygons[contact_face].normal).normalized()
        for sign in (float(contract["c048_owner_inward_normal_sign"]),):
            direction = base_normal * sign
            root = localized_prism_from_side_face(
                f"TMP__C048_ROOT_FACE_{contact_face}_SIGN_{int(sign):+d}", c048, contact_face, direction,
                contract.get("c048_internal_embed_mm", contract["internal_embed_mm"]), contract["root_overlap_with_approved_feature_mm"],
                contract["c048_root_safe_end_fraction"],
            )
            proposal = duplicate(c048, f"TMP__C048_PROPOSAL_FACE_{contact_face}_SIGN_{int(sign):+d}")
            apply_union(proposal, duplicate(root, f"TMP__C048_UNION_TOOL_{contact_face}_{int(sign):+d}"), "TMP__UNION_C048_ROOT")
            alternatives.append({
                "contact_face": contact_face,
                "direction": direction,
                "root": root,
                "root_owner_volume": intersection_volume(root, lower_owner),
                "proposal_owner_volume": intersection_volume(proposal, lower_owner),
                "eye_clearance": distance(proposal, bucket),
            })
            bpy.data.objects.remove(proposal, do_unlink=True)
    valid_alternatives = [
        item for item in alternatives
        if item["eye_clearance"] >= contract["minimum_eye_clearance_mm"]
    ]
    if not valid_alternatives:
        diagnostic = [{
            "face": item["contact_face"],
            "direction": [round(v, 6) for v in item["direction"]],
            "root_owner_volume_mm3": item["root_owner_volume"],
            "proposal_owner_volume_mm3": item["proposal_owner_volume"],
            "eye_clearance_mm": round(item["eye_clearance"], 4),
        } for item in alternatives]
        raise RuntimeError(f"no clearance-safe C048 localized root embed: {diagnostic}")
    valid_alternatives.sort(key=lambda item: (item["eye_clearance"], item["root_owner_volume"]), reverse=True)
    selected = valid_alternatives[0]
    contact_face = selected["contact_face"]
    root_volume = selected["root_owner_volume"]
    c048_direction = selected["direction"]
    c048_root = selected["root"]
    for item in alternatives:
        if item is not selected:
            bpy.data.objects.remove(item["root"], do_unlink=True)
    c048_root.name = "PROPOSED__C048__LOWER_FACE_ROOT_ADDITION_V1"
    c048_proposal = duplicate(c048, "PROPOSED__C048__WITH_INTERNAL_ROOT_EMBED_V1")
    apply_union(c048_proposal, duplicate(c048_root, "TOOL__C048_INTERNAL_ROOT"), "UNION__C048_INTERNAL_ROOT")

    records = {}
    for role in ("outer", "lower"):
        root = root_additions[role]; proposal = eye_proposals[role]; original = flanges[names[f"{role}_eye_flange"]]
        records[role] = {
            "approved_flange_fingerprint": fingerprint(original),
            "root_addition_topology": topology(root), "proposal_topology": topology(proposal),
            "root_overlap_with_v9_bucket_mm3": intersection_volume(root, bucket),
            "proposal_overlap_with_v9_bucket_mm3": intersection_volume(proposal, bucket),
            "proposal_to_matching_head_flange_clearance_mm": round(distance(proposal, flanges[names[f"{role}_head_flange"]]), 4),
            "freecad_exact_fuse_required": contract.get("root_width_mm") == 22.0,
        }
    c048_record = {
        "approved_contact_face_zero_based": contact_face,
        "owner_embed_direction": [round(v, 6) for v in c048_direction],
        "root_addition_topology": topology(c048_root), "proposal_topology": topology(c048_proposal),
        "root_overlap_with_lower_face_mm3": root_volume,
        "proposal_overlap_with_lower_face_mm3": intersection_volume(c048_proposal, lower_owner),
        "proposal_eye_clearance_mm": round(distance(c048_proposal, bucket), 4),
    }
    for role, record in records.items():
        if record["root_overlap_with_v9_bucket_mm3"] < contract["minimum_positive_owner_root_volume_mm3"]:
            raise RuntimeError(f"{role} eye root embed does not establish positive V9 owner volume: {record}")
    if c048_record["proposal_eye_clearance_mm"] < contract["minimum_eye_clearance_mm"]:
        raise RuntimeError(f"C048 root embed violates eye clearance: {c048_record}")
    for obj in (*eye_proposals.values(), c048_proposal, *root_additions.values(), c048_root):
        t = topology(obj)
        if t["boundary_edges"] or t["nonmanifold_edges"]: raise RuntimeError(f"proposal is not manifold: {obj.name}: {t}")

    gray = material("FROZEN_OWNER_CONTEXT", (0.42, 0.46, 0.50, 1)); blue = material("FROZEN_V9_EYE", (0.03, 0.48, 0.96, 1))
    orange = material("APPROVED_FLANGE_BODY", (1.0, 0.36, 0.04, 1)); magenta = material("PROPOSED_INTERNAL_ROOT", (1.0, 0.03, 0.62, 1))
    cyan = material("APPROVED_C048", (0.02, 0.84, 1.0, 1)); dark = material("UNCHANGED_CAP", (0.12, 0.23, 0.52, 1))
    assign(lower_owner, gray); assign(bucket, blue); assign(cap, dark); assign(c048_proposal, cyan)
    for obj in eye_proposals.values(): assign(obj, orange)
    for obj in (*root_additions.values(), c048_root): assign(obj, magenta); obj.show_in_front = True
    for obj in flanges.values(): assign(obj, gray)

    scene = bpy.context.scene; scene.name = "Right_Eye_Internal_Root_Embed_Review_V1"; scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"; scene.display.shading.color_type = "MATERIAL"; scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True; scene.display.shading.cavity_type = "WORLD"; scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.035, 0.045, 0.06); scene.render.resolution_x = 1400; scene.render.resolution_y = 1100
    scene.render.resolution_percentage = 100; scene.render.image_settings.file_format = "PNG"
    camera_data = bpy.data.cameras.new("ROOT_EMBED_CAMERA"); camera = bpy.data.objects.new("ROOT_EMBED_CAMERA", camera_data)
    scene.collection.objects.link(camera); scene.camera = camera
    context = {lower_owner, bucket, cap, *eye_proposals.values(), c048_proposal}
    renders = [
        render(camera, output, "01-right-root-embed-owner-context", (155, 148, 112), (68, 68, 126), context),
        render(camera, output, "02-right-eye-root-additions-highlighted", (175, 170, 160), (88, 77, 140), {bucket, *eye_proposals.values(), *root_additions.values()}),
        render(camera, output, "03-c048-root-addition-highlighted", (145, 125, 105), (57, 56, 108), {lower_owner, bucket, c048_proposal, c048_root}),
        render(camera, output, "04-root-additions-isolated", (155, 135, 115), (67, 65, 122), {*root_additions.values(), c048_root}),
    ]
    review_objs = {}
    for key, obj in {"right_lower_face_context": lower_owner, "right_eye_bucket_v9": bucket, "right_eye_rear_cap_v9": cap,
                     "proposed_outer_eye_flange_with_root_embed": eye_proposals["outer"],
                     "proposed_lower_eye_flange_with_root_embed": eye_proposals["lower"],
                     "proposed_c048_with_root_embed": c048_proposal, "outer_root_addition": root_additions["outer"],
                     "lower_root_addition": root_additions["lower"], "c048_root_addition": c048_root,
                     "approved_outer_head_flange": flanges[names["outer_head_flange"]],
                     "approved_lower_head_flange": flanges[names["lower_head_flange"]]}.items():
        path = output / "review" / f"{key}.obj"; export_obj(obj, path); review_objs[key] = str(path.relative_to(REPO_ROOT))
    for obj in bpy.data.objects:
        if obj.type == "MESH": obj.hide_set(obj not in context); obj.hide_render = obj not in context
    scene["REVIEW_ONLY"] = True; scene["OWNER_BOOLEAN_PERFORMED"] = False; scene["MIRROR_PERFORMED"] = False; scene["PRINT_RELEASE"] = False
    review_version = "V2" if contract.get("root_width_mm") == 22.0 else "V1"
    blend_path = output / f"CAT_HEAD_RIGHT_EYE_RECTANGULAR_ROOT_REVIEW_{review_version}.blend"; bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report = {
        "status": config["status"], "locked_contract": contract,
        "eye_flange_root_records": records, "c048_root_record": c048_record,
        "right_cap_interference": overlaps(cap, bucket), "right_cap_clearance_mm": round(distance(cap, bucket), 4),
        "eye_root_additions_positive_owner_overlap": all(r["root_overlap_with_v9_bucket_mm3"] >= contract["minimum_positive_owner_root_volume_mm3"] for r in records.values()),
        "c048_root_owner_overlap_requires_freecad_exact_validation": True,
        "approved_mating_geometry_moved": False, "owner_boolean_performed": False, "mirror_performed": False,
        "no_stl_or_gcode_exported": True, "holds": config["holds"],
        "generated_files": {"blend": str(blend_path.relative_to(REPO_ROOT)), "renders": renders, "review_objs": review_objs},
    }
    (output / f"validation-{review_version.lower()}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
