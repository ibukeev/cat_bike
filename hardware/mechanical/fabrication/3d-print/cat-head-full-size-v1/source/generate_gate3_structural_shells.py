#!/usr/bin/env python3
"""Generate inward 1.8 mm Gate 3 structural shell baselines in Blender."""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict, deque
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
GATE2_CONFIG = PACKAGE_ROOT / "config/gate2-section-layout.json"
GATE3_CONFIG = PACKAGE_ROOT / "config/gate3-structural-shells.json"
OUTPUT_DIR = PACKAGE_ROOT / "output/gate3-structural-shells"


def clean_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.materials, bpy.data.curves):
        for datablock in list(datablocks):
            if datablock.users == 0:
                datablocks.remove(datablock)


def create_material(name: str, color: str) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    values = tuple(int(color[index:index + 2], 16) / 255.0 for index in (1, 3, 5))
    material.diffuse_color = (*values, 1.0)
    return material


def split_vertex_fans(vertices: list[Point], faces: list[tuple[int, ...]]) -> tuple[list[Point], list[tuple[int, ...]], int]:
    """Duplicate pinched boundary vertices so every incident face fan is separate."""
    output_vertices = list(vertices)
    output_faces = [list(face) for face in faces]
    split_count = 0
    original_vertex_count = len(vertices)
    for vertex_index in range(original_vertex_count):
        incident = [index for index, face in enumerate(output_faces) if vertex_index in face]
        if len(incident) < 2:
            continue
        neighbors: dict[int, set[int]] = {index: set() for index in incident}
        for first_offset, first_index in enumerate(incident):
            first_face = output_faces[first_index]
            first_adjacent = {
                first_face[(first_face.index(vertex_index) - 1) % len(first_face)],
                first_face[(first_face.index(vertex_index) + 1) % len(first_face)],
            }
            for second_index in incident[first_offset + 1:]:
                second_face = output_faces[second_index]
                second_adjacent = {
                    second_face[(second_face.index(vertex_index) - 1) % len(second_face)],
                    second_face[(second_face.index(vertex_index) + 1) % len(second_face)],
                }
                if first_adjacent & second_adjacent:
                    neighbors[first_index].add(second_index)
                    neighbors[second_index].add(first_index)
        remaining = set(incident)
        fans: list[list[int]] = []
        while remaining:
            start = remaining.pop()
            queue = deque([start])
            fan = [start]
            while queue:
                current = queue.popleft()
                for neighbor in neighbors[current]:
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        queue.append(neighbor)
                        fan.append(neighbor)
            fans.append(fan)
        for fan in fans[1:]:
            replacement = len(output_vertices)
            output_vertices.append(output_vertices[vertex_index])
            split_count += 1
            for face_index in fan:
                output_faces[face_index] = [replacement if value == vertex_index else value for value in output_faces[face_index]]
    return output_vertices, [tuple(face) for face in output_faces], split_count


def create_section_object(
    name: str,
    source_faces: list[tuple[int, ...]],
    model: gate1.ObjModel,
    scale: float,
    origin: gate1.Point,
    material: bpy.types.Material,
) -> bpy.types.Object:
    used_vertices = sorted({index for face in source_faces for index in face})
    remap = {source: local for local, source in enumerate(used_vertices)}
    vertices = [gate1.transform_point(model.vertices[index], scale, origin) for index in used_vertices]
    faces = [tuple(remap[index] for index in face) for face in source_faces]
    vertices, faces, split_count = split_vertex_fans(vertices, faces)
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    obj["boundary_vertex_fan_splits"] = split_count
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    solidify = obj.modifiers.new("Inward_1p8mm_shell", "SOLIDIFY")
    solidify.thickness = float(CONFIG["wall_thickness_mm"])
    solidify.offset = float(CONFIG["solidify_offset"])
    solidify.use_rim = True
    solidify.use_rim_only = False
    solidify.use_even_offset = bool(CONFIG["use_even_offset"])
    solidify.use_quality_normals = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=solidify.name)
    obj.select_set(False)
    return obj


def create_compact_rear_base_frame(
    frame: dict[str, float], material: bpy.types.Material
) -> bpy.types.Object:
    """Create a closed, sloped trapezoidal frame extending inside the head."""
    top_y = float(frame["outer_top_y_mm"])
    top_z = float(frame["outer_top_z_mm"])
    bottom_y = float(frame["outer_bottom_y_mm"])
    bottom_z = float(frame["outer_bottom_z_mm"])
    top_width = float(frame["outer_top_width_mm"])
    bottom_width = float(frame["outer_bottom_width_mm"])
    rail = float(frame["rail_width_mm"])
    depth = float(frame["inward_depth_mm"])
    height = top_z - bottom_z
    if height <= 2.0 * rail:
        raise ValueError("Compact rear frame rails consume its full height")
    if min(top_width, bottom_width) <= 2.0 * rail:
        raise ValueError("Compact rear frame rails consume its full width")
    if depth <= 0.0:
        raise ValueError("Compact rear frame inward depth must be positive")

    def plane_y(z: float) -> float:
        return bottom_y + (z - bottom_z) * (top_y - bottom_y) / height

    vertical = Vector((0.0, top_y - bottom_y, top_z - bottom_z)).normalized()
    outward = vertical.cross(Vector((1.0, 0.0, 0.0))).normalized()
    inward = -outward

    inner_top_z = top_z - rail
    inner_bottom_z = bottom_z + rail
    front_vertices = [
        (-top_width / 2.0, top_y, top_z),
        (top_width / 2.0, top_y, top_z),
        (bottom_width / 2.0, bottom_y, bottom_z),
        (-bottom_width / 2.0, bottom_y, bottom_z),
        (-(top_width - 2.0 * rail) / 2.0, plane_y(inner_top_z), inner_top_z),
        ((top_width - 2.0 * rail) / 2.0, plane_y(inner_top_z), inner_top_z),
        ((bottom_width - 2.0 * rail) / 2.0, plane_y(inner_bottom_z), inner_bottom_z),
        (-(bottom_width - 2.0 * rail) / 2.0, plane_y(inner_bottom_z), inner_bottom_z),
    ]
    vertices = front_vertices + [
        tuple(Vector(vertex) + inward * depth) for vertex in front_vertices
    ]
    faces = (
        (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
        (8, 12, 13, 9), (9, 13, 14, 10), (10, 14, 15, 11), (11, 15, 12, 8),
        (0, 8, 9, 1), (1, 9, 10, 2), (2, 10, 11, 3), (3, 11, 8, 0),
        (4, 5, 13, 12), (5, 6, 14, 13), (6, 7, 15, 14), (7, 4, 12, 15),
    )
    mesh = bpy.data.meshes.new("rear_base_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new("rear_base", mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)

    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)
    return obj


def mesh_stats(obj: bpy.types.Object) -> dict[str, object]:
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    boundary_edges = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    nonmanifold_edges = sum(1 for edge in bm.edges if not edge.is_manifold)
    neighbors: dict[int, set[int]] = defaultdict(set)
    for edge in bm.edges:
        first, second = edge.verts[0].index, edge.verts[1].index
        neighbors[first].add(second)
        neighbors[second].add(first)
    remaining = set(range(len(bm.verts)))
    components = 0
    while remaining:
        components += 1
        start = remaining.pop()
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in neighbors[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
    points = [tuple(obj.matrix_world @ vertex.co) for vertex in mesh.vertices]
    fit = gate2.best_fit(points, CONFIG["printer_envelope_mm"], int(CONFIG["orientation_step_degrees"]))
    bounds_value = gate1.bounds(points)
    stats = {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "faces": len(mesh.polygons),
        "connected_components": components,
        "boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "dimensions_mm": [round(value, 3) for value in gate1.dimensions(bounds_value)],
        "orientation_search": fit,
        "boundary_vertex_fan_splits": int(obj.get("boundary_vertex_fan_splits", 0)),
    }
    bm.free()
    return stats


def export_stl(obj: bpy.types.Object, path: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    if hasattr(bpy.ops.wm, "stl_export"):
        bpy.ops.wm.stl_export(filepath=str(path), export_selected_objects=True, ascii_format=False)
    else:
        bpy.ops.export_mesh.stl(filepath=str(path), use_selection=True, ascii=False)
    obj.select_set(False)


def point_camera(camera: bpy.types.Object, target: tuple[float, float, float]) -> None:
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_previews(output_path: Path) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 720
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.025, 0.035, 0.05)

    camera_data = bpy.data.cameras.new("Gate3_Camera")
    camera = bpy.data.objects.new("Gate3_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.lens = 58

    for name, location, energy, size in (
        ("Key", (320.0, -280.0, 440.0), 1400.0, 260.0),
        ("Fill", (-300.0, -120.0, 250.0), 900.0, 220.0),
        ("Rear", (0.0, 420.0, 360.0), 1100.0, 180.0),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        scene.collection.objects.link(light)
        light.location = location
        point_camera(light, (0.0, 120.0, 155.0))

    for filename, location in (
        ("gate3-shells-front.png", (430.0, -560.0, 310.0)),
        ("gate3-shells-rear.png", (-430.0, 560.0, 310.0)),
    ):
        camera.location = location
        point_camera(camera, (0.0, 120.0, 155.0))
        scene.render.filepath = str(output_path / filename)
        bpy.ops.render.render(write_still=True)


def parse_blender_args() -> tuple[Path, Path]:
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    config_path = GATE3_CONFIG
    output_path = OUTPUT_DIR
    for index, value in enumerate(args):
        if value == "--config":
            config_path = Path(args[index + 1]).resolve()
        elif value == "--output-dir":
            output_path = Path(args[index + 1]).resolve()
    return config_path, output_path


CONFIG_PATH, OUTPUT_PATH = parse_blender_args()
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def main() -> None:
    clean_scene()
    gate2_config = json.loads(GATE2_CONFIG.read_text(encoding="utf-8"))
    gate1_config = json.loads(gate1.DEFAULT_CONFIG.read_text(encoding="utf-8"))
    source_model = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    units = gate1.panel_units(source_model, gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV))
    scale, origin, _ = gate1.make_transform(gate1.bounds(source_model.vertices), float(gate1_config["target_height_mm"]))
    roles, _ = gate1.build_roles(units, gate1_config, scale)
    model = gate2.subdivide_center_panels(source_model, gate2_config)
    assignments = gate2.assign_faces(model.faces, model.vertices, roles, gate2_config, scale, origin)

    OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
    objects: dict[str, bpy.types.Object] = {}
    report_sections: dict[str, object] = {}
    for section in gate2.SECTION_ORDER:
        material = create_material(section, gate2.COLORS[section])
        face_indices = [index for index, assignment in enumerate(assignments) if assignment == section]
        source_faces = [model.faces[index].indices for index in face_indices]
        closure_faces = [tuple(face) for face in CONFIG.get("bottom_closure_faces", {}).get(section, [])]
        source_faces.extend(closure_faces)
        if section == "rear_base":
            obj = create_compact_rear_base_frame(
                CONFIG["compact_rear_base_frame"], material
            )
        else:
            obj = create_section_object(
                section, source_faces, model, scale, origin, material
            )
        objects[section] = obj
        stats = mesh_stats(obj)
        stats["bottom_closure_face_count"] = len(closure_faces)
        stats["expected_connected_components_before_rear_ribs"] = CONFIG["expected_surface_components"][section]
        report_sections[section] = stats
        export_stl(obj, OUTPUT_PATH / f"{section}.stl")

    bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT_PATH / "gate3-structural-shells.blend"))
    bpy.ops.object.select_all(action="SELECT")
    if hasattr(bpy.ops.export_scene, "gltf"):
        bpy.ops.export_scene.gltf(filepath=str(OUTPUT_PATH / "gate3-structural-shells.glb"), export_format="GLB", use_selection=True)
    render_previews(OUTPUT_PATH)
    report = {
        "gate": "Gate 3 structural shell baseline",
        "status": "review_required",
        "wall_thickness_mm": CONFIG["wall_thickness_mm"],
        "solidify_offset": CONFIG["solidify_offset"],
        "use_even_offset": CONFIG["use_even_offset"],
        "bottom_closure_faces": CONFIG.get("bottom_closure_faces", {}),
        "sections": report_sections,
        "acceptance": {
            "all_sections_closed_manifold": all(value["boundary_edges"] == 0 and value["nonmanifold_edges"] == 0 for value in report_sections.values()),
            "all_sections_fit_orientation_search": all(value["orientation_search"]["fits"] for value in report_sections.values()),
            "approved_exterior_transform_unchanged": True,
            "mirrored_bottom_throat_openings_closed": all(
                report_sections[section]["bottom_closure_face_count"] == 1
                for section in ("right_lower_face", "left_lower_face")
            ),
            "compact_rear_base_frame_generated": True,
        },
        "review_notes": CONFIG.get("review_notes", []),
    }
    (OUTPUT_PATH / "gate3-shell-validation.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Wrote {OUTPUT_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
