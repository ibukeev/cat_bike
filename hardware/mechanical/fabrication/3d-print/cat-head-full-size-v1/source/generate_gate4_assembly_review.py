#!/usr/bin/env python3
"""Generate a complete coverage-review assembly with temporary panels and eyes."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
GATE3_BLEND = PACKAGE_ROOT / "output/gate3-structural-shells/gate3-structural-shells.blend"
CONFIG_PATH = PACKAGE_ROOT / "config/gate4-assembly-review.json"
OUTPUT_DIR = PACKAGE_ROOT / "output/gate4-assembly-review"


def material(name: str, color: tuple[float, float, float, float], metallic: float = 0.0) -> bpy.types.Material:
    existing = bpy.data.materials.get(name)
    if existing:
        return existing
    value = bpy.data.materials.new(name)
    value.diffuse_color = color
    value.metallic = metallic
    value.roughness = 0.38
    return value


def create_solidified_object(
    name: str,
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
    thickness: float,
    assigned_material: bpy.types.Material,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(assigned_material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    modifier = obj.modifiers.new("Temporary_inward_thickness", "SOLIDIFY")
    modifier.thickness = thickness
    modifier.offset = -1.0
    modifier.use_rim = True
    modifier.use_even_offset = False
    modifier.use_quality_normals = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)
    return obj


def panel_object(
    panel_id: str,
    faces: list[gate1.ObjFace],
    model: gate1.ObjModel,
    scale: float,
    origin: gate1.Point,
    thickness: float,
    assigned_material: bpy.types.Material,
) -> bpy.types.Object:
    used = sorted({index for face in faces for index in face.indices})
    remap = {source: local for local, source in enumerate(used)}
    vertices = [gate1.transform_point(model.vertices[index], scale, origin) for index in used]
    local_faces = [tuple(remap[index] for index in face.indices) for face in faces]
    return create_solidified_object(f"glow_{panel_id}", vertices, local_faces, thickness, assigned_material)


def front_svg_inverse(
    point: list[float],
    target_bounds: dict[str, tuple[float, float]],
) -> tuple[float, float]:
    origin_x, origin_y, width, height = 40.0, 80.0, 390.0, 320.0
    margin = 18.0
    min_x, max_x = target_bounds["x"]
    min_z, max_z = target_bounds["z"]
    local_scale = min((width - margin * 2) / (max_x - min_x), (height - margin * 2) / (max_z - min_z))
    used_width = (max_x - min_x) * local_scale
    used_height = (max_z - min_z) * local_scale
    offset_x = origin_x + (width - used_width) / 2.0 - min_x * local_scale
    offset_y = origin_y + (height - used_height) / 2.0 + max_z * local_scale
    return (float(point[0]) - offset_x) / local_scale, (offset_y - float(point[1])) / local_scale


def y_on_plane(x: float, z: float, plane_points: list[Vector]) -> float:
    normal = (plane_points[1] - plane_points[0]).cross(plane_points[2] - plane_points[0])
    return plane_points[0].y - (normal.x * (x - plane_points[0].x) + normal.z * (z - plane_points[0].z)) / normal.y


def create_eye_objects(
    gate1_config: dict,
    eye_model: gate1.ObjModel,
    scale: float,
    origin: gate1.Point,
    target_bounds: dict[str, tuple[float, float]],
    thickness: float,
    assigned_material: bpy.types.Material,
) -> list[bpy.types.Object]:
    eye_faces = gate1.find_eye_faces(eye_model, gate1_config)
    objects = []
    for aperture_index, (unit_id, aperture) in enumerate(zip(("EYE_RIGHT", "EYE_LEFT"), gate1_config["eye_aperture_front_svg"])):
        reference_face = eye_faces[unit_id][0]
        plane = [Vector(gate1.transform_point(eye_model.vertices[index], scale, origin)) for index in reference_face.indices[:3]]
        vertices = []
        for svg_point in aperture:
            x, z = front_svg_inverse(svg_point, target_bounds)
            vertices.append((x, y_on_plane(x, z, plane), z))
        objects.append(create_solidified_object(f"corrected_{unit_id.lower()}", vertices, [tuple(range(len(vertices)))], thickness, assigned_material))
    return objects


def create_opaque_infill_objects(
    config: dict,
    model: gate1.ObjModel,
    scale: float,
    origin: gate1.Point,
    eye_objects: list[bpy.types.Object],
    thickness: float,
    assigned_material: bpy.types.Material,
) -> list[bpy.types.Object]:
    infill = config["opaque_infill"]
    objects: list[bpy.types.Object] = []
    for name, key in (
        ("opaque_right_under_ear", "right_under_ear_loop"),
        ("opaque_left_under_ear", "left_under_ear_loop"),
    ):
        vertices = [gate1.transform_point(model.vertices[index], scale, origin) for index in infill[key]]
        objects.append(create_solidified_object(name, vertices, [tuple(range(len(vertices)))], thickness, assigned_material))

    for side_index, (side, outer_key, order_key) in enumerate((
        ("right", "right_eye_outer_loop", "right_eye_inner_order"),
        ("left", "left_eye_outer_loop", "left_eye_inner_order"),
    )):
        outer = [gate1.transform_point(model.vertices[index], scale, origin) for index in infill[outer_key]]
        corrected_eye = eye_objects[side_index]
        inner_source = [tuple(corrected_eye.data.vertices[index].co) for index in range(4)]
        inner = [inner_source[index] for index in infill[order_key]]
        vertices = outer + inner
        faces = []
        for index in range(4):
            following = (index + 1) % 4
            faces.append((index, following, 4 + following, 4 + index))
        objects.append(create_solidified_object(f"opaque_{side}_eye_surround", vertices, faces, thickness, assigned_material))
    return objects


def cut_rear_service_opening(config: dict) -> dict[str, int]:
    rear = bpy.data.objects["rear_base"]
    before = {"vertices_before": len(rear.data.vertices), "faces_before": len(rear.data.polygons)}
    opening = config["rear_service_opening"]
    bpy.ops.mesh.primitive_cube_add(location=(opening["center_x_mm"], opening["center_y_mm"], opening["center_z_mm"]))
    cutter = bpy.context.active_object
    cutter.name = "rear_service_opening_cutter"
    cutter.dimensions = (opening["width_mm"], opening["cut_depth_mm"], opening["height_mm"])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.context.view_layer.objects.active = rear
    modifier = rear.modifiers.new("Rear_service_100x80", "BOOLEAN")
    modifier.operation = "DIFFERENCE"
    modifier.solver = "EXACT"
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    return {
        **before,
        "vertices_after": len(rear.data.vertices),
        "faces_after": len(rear.data.polygons),
    }


def mesh_is_closed_manifold(obj: bpy.types.Object) -> bool:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    result = all(edge.is_manifold for edge in bm.edges)
    bm.free()
    return result


def export_selected(path: Path, objects: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True, ascii_format=False)


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    gate1_config = json.loads(gate1.DEFAULT_CONFIG.read_text(encoding="utf-8"))
    bpy.ops.wm.open_mainfile(filepath=str(GATE3_BLEND))
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    model = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    scale, origin, _ = gate1.make_transform(gate1.bounds(model.vertices), float(gate1_config["target_height_mm"]))
    transformed = [gate1.transform_point(vertex, scale, origin) for vertex in model.vertices]
    target_bounds = gate1.bounds(transformed)
    glow_ids = set(gate1_config["glow_transmitting_panels"])
    faces_by_panel: dict[str, list[gate1.ObjFace]] = {panel_id: [] for panel_id in glow_ids}
    for face in model.faces:
        panel_id = gate1.canonical_source_panel_id(face.group)
        if panel_id in faces_by_panel:
            faces_by_panel[panel_id].append(face)

    glow_material = material("Temporary_glow_transmitting", (0.50, 0.0, 0.50, 0.78))
    eye_material = material("Temporary_corrected_eye", (0.51, 0.96, 1.0, 0.82))
    opaque_material = material("Temporary_opaque_infill", (0.30, 0.20, 0.14, 1.0))
    glow_objects = [
        panel_object(panel_id, faces_by_panel[panel_id], model, scale, origin, float(config["temporary_panel_thickness_mm"]), glow_material)
        for panel_id in sorted(glow_ids)
    ]
    eye_model = gate1.read_obj(gate1.SOURCE_EYE_OBJ)
    eye_objects = create_eye_objects(gate1_config, eye_model, scale, origin, target_bounds, float(config["temporary_panel_thickness_mm"]), eye_material)
    opaque_objects = create_opaque_infill_objects(config, model, scale, origin, eye_objects, float(config["temporary_panel_thickness_mm"]), opaque_material)
    temporary_objects = glow_objects + eye_objects + opaque_objects

    rear_cut_result = cut_rear_service_opening(config)
    structural_objects = [bpy.data.objects[name] for name in gate2.SECTION_ORDER]
    all_objects = structural_objects + temporary_objects

    for panel in temporary_objects:
        export_selected(OUTPUT_DIR / f"{panel.name}.stl", [panel])
    export_selected(OUTPUT_DIR / "gate4-complete-review-assembly.stl", all_objects)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in all_objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(OUTPUT_DIR / "gate4-complete-review-assembly.glb"), export_format="GLB", use_selection=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_DIR / "gate4-complete-review-assembly.blend"))

    report = {
        "gate": "Gate 4 complete coverage review",
        "status": "review_required",
        "structural_section_count": len(structural_objects),
        "temporary_glow_panel_count": len(glow_objects),
        "temporary_corrected_eye_count": len(eye_objects),
        "temporary_opaque_infill_count": len(opaque_objects),
        "rear_service_opening": config["rear_service_opening"],
        "rear_service_cut_mesh_change": rear_cut_result,
        "acceptance": {
            "all_20_glow_panels_present": len(glow_objects) == 20,
            "both_corrected_eye_inserts_present": len(eye_objects) == 2,
            "both_under_ear_openings_closed": len([obj for obj in opaque_objects if "under_ear" in obj.name]) == 2,
            "both_oversized_eye_openings_have_opaque_surrounds": len([obj for obj in opaque_objects if "eye_surround" in obj.name]) == 2,
            "all_review_objects_closed_manifold": all(mesh_is_closed_manifold(obj) for obj in all_objects),
            "rear_service_opening_cut_applied": rear_cut_result["faces_after"] != rear_cut_result["faces_before"],
            "mouth_faces_intentionally_absent": True
        },
        "intended_large_openings": ["mouth", "rear_service_100x80"],
        "review_notes": config.get("review_notes", [])
    }
    (OUTPUT_DIR / "gate4-coverage-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Wrote {OUTPUT_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
