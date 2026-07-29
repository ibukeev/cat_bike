#!/usr/bin/env python3
"""Generate review-only Gate 9 rear-architecture comparison geometry."""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Callable

import bpy
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate3_structural_shells as gate3  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/gate9-rear-architecture-comparison-v1.json"
)
DEFAULT_OUTPUT = (
    PACKAGE_ROOT / "output/gate9-rear-architecture-comparison-v1"
)
BODY_SECTIONS = (
    "right_upper_head",
    "left_upper_head",
    "right_lower_face",
    "left_lower_face",
)
EAR_SECTIONS = ("right_ear", "left_ear")
SECTION_COLORS = {
    "right_upper_head": "#3978C6",
    "left_upper_head": "#4A91DB",
    "right_lower_face": "#235FA7",
    "left_lower_face": "#2F70BB",
    "right_ear": "#5FA9E6",
    "left_ear": "#78B9EC",
    "rear_base": "#7555C8",
    "rear_cassette": "#E59735",
    "backplate": "#AEB7C3",
    "rail": "#D9DEE5",
    "shoe": "#C94040",
    "tool": "#EF7A62",
    "hardware": "#D061A7",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(args)


def load_repo_json(relative_path: str) -> dict[str, Any]:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


def create_material(name: str, color: str, alpha: float = 1.0) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    values = tuple(
        int(color[index : index + 2], 16) / 255.0 for index in (1, 3, 5)
    )
    material.diffuse_color = (*values, alpha)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = (*values, 1.0)
        shader.inputs["Roughness"].default_value = 0.42
        shader.inputs["Metallic"].default_value = (
            0.72 if name.startswith(("backplate", "rail")) else 0.0
        )
        shader.inputs["Alpha"].default_value = alpha
    if alpha < 1.0:
        material.surface_render_method = "DITHERED"
    return material


def transformed_source_point(
    point: tuple[float, float, float],
    source_scale: float,
    source_origin: tuple[float, float, float],
    uniform_scale: float,
    scale_center: Vector,
) -> tuple[float, float, float]:
    baseline = Vector(gate1.transform_point(point, source_scale, source_origin))
    transformed = scale_center + (baseline - scale_center) * uniform_scale
    return tuple(transformed)


def create_shell_object(
    name: str,
    source_faces: list[tuple[int, ...]],
    model: gate1.ObjModel,
    source_scale: float,
    source_origin: tuple[float, float, float],
    uniform_scale: float,
    scale_center: Vector,
    material: bpy.types.Material,
    shell_config: dict[str, Any],
) -> bpy.types.Object:
    used_vertices = sorted({index for face in source_faces for index in face})
    remap = {source: local for local, source in enumerate(used_vertices)}
    vertices = [
        transformed_source_point(
            model.vertices[index],
            source_scale,
            source_origin,
            uniform_scale,
            scale_center,
        )
        for index in used_vertices
    ]
    faces = [tuple(remap[index] for index in face) for face in source_faces]
    vertices, faces, split_count = gate3.split_vertex_fans(vertices, faces)
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
    solidify.thickness = float(shell_config["wall_thickness_mm"])
    solidify.offset = float(shell_config["solidify_offset"])
    solidify.use_rim = True
    solidify.use_rim_only = False
    solidify.use_even_offset = bool(shell_config["use_even_offset"])
    solidify.use_quality_normals = True
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=solidify.name)
    obj.select_set(False)
    return obj


def create_oriented_box(
    name: str,
    center: Vector,
    axes: tuple[Vector, Vector, Vector],
    dimensions: tuple[float, float, float],
    material: bpy.types.Material,
) -> bpy.types.Object:
    vertices: list[tuple[float, float, float]] = []
    for signs in (
        (-1, -1, -1),
        (1, -1, -1),
        (1, 1, -1),
        (-1, 1, -1),
        (-1, -1, 1),
        (1, -1, 1),
        (1, 1, 1),
        (-1, 1, 1),
    ):
        point = center.copy()
        for axis, sign, dimension in zip(axes, signs, dimensions):
            point += axis * sign * dimension / 2.0
        vertices.append(tuple(point))
    faces = (
        (0, 1, 2, 3),
        (4, 7, 6, 5),
        (0, 4, 5, 1),
        (1, 5, 6, 2),
        (2, 6, 7, 3),
        (4, 0, 3, 7),
    )
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def create_oriented_cylinder(
    name: str,
    center: Vector,
    axis: Vector,
    diameter: float,
    length: float,
    material: bpy.types.Material,
    vertices: int = 24,
) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=diameter / 2.0,
        depth=length,
        location=center,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference(axis)
    obj.data.materials.append(material)
    return obj


def create_backplate(
    name: str,
    interface: dict[str, Any],
    material: bpy.types.Material,
) -> bpy.types.Object:
    plane = interface["rear_interface_plane"]
    plate = interface["aluminum_backplate"]
    center = Vector(plane["center_head_mm"])
    normal = Vector(plane["outward_normal_head"]).normalized()
    across = Vector((1.0, 0.0, 0.0))
    vertical = normal.cross(across).normalized()
    thickness = float(plate["thickness_mm"])
    top_width = float(plate["outer_top_width_mm"])
    bottom_width = float(plate["outer_bottom_width_mm"])
    height = float(plate["height_mm"])

    local = (
        (-top_width / 2.0, height / 2.0, -thickness / 2.0),
        (top_width / 2.0, height / 2.0, -thickness / 2.0),
        (bottom_width / 2.0, -height / 2.0, -thickness / 2.0),
        (-bottom_width / 2.0, -height / 2.0, -thickness / 2.0),
        (-top_width / 2.0, height / 2.0, thickness / 2.0),
        (top_width / 2.0, height / 2.0, thickness / 2.0),
        (bottom_width / 2.0, -height / 2.0, thickness / 2.0),
        (-bottom_width / 2.0, -height / 2.0, thickness / 2.0),
    )
    vertices = [
        tuple(center + across * x + vertical * y + normal * z)
        for x, y, z in local
    ]
    faces = (
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    )
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def rail_roll_axes(axis: Vector) -> tuple[Vector, Vector, Vector]:
    along = axis.normalized()
    across = Vector((1.0, 0.0, 0.0))
    across = (across - along * across.dot(along)).normalized()
    other = along.cross(across).normalized()
    return across, other, along


def create_interface_envelopes(
    prefix: str,
    interface: dict[str, Any],
    envelope_config: dict[str, Any],
    materials: dict[str, bpy.types.Material],
) -> dict[str, bpy.types.Object]:
    objects: dict[str, bpy.types.Object] = {}
    plate = create_backplate(
        f"{prefix}__backplate", interface, materials["backplate"]
    )
    objects["backplate"] = plate
    rail = interface["rail_system"]
    rail_size = float(rail["profile"]["outside_width_mm"])
    rail_length = float(rail["modeled_installed_reference_length_mm"])
    shoe_width = float(envelope_config["raw_lower_shoe_width_mm"])
    shoe_height = float(envelope_config["raw_lower_shoe_height_mm"])
    shoe_length = float(envelope_config["raw_lower_shoe_length_mm"])
    tool_diameter = float(
        envelope_config["lower_shoe_tool_envelope_diameter_mm"]
    )
    tool_length = float(
        envelope_config["lower_shoe_tool_envelope_length_mm"]
    )

    for side in ("left", "right"):
        target = Vector(rail["lower_targets_head_mm"][side])
        axis = Vector(rail["accepted_axes_head"][side]).normalized()
        axes = rail_roll_axes(axis)
        objects[f"rail_{side}"] = create_oriented_box(
            f"{prefix}__rail_{side}",
            target + axis * rail_length / 2.0,
            axes,
            (rail_size, rail_size, rail_length),
            materials["rail"],
        )
        objects[f"shoe_{side}"] = create_oriented_box(
            f"{prefix}__shoe_envelope_{side}",
            target + axis * shoe_length / 2.0,
            axes,
            (shoe_width, shoe_height, shoe_length),
            materials["shoe"],
        )
        objects[f"tool_{side}"] = create_oriented_cylinder(
            f"{prefix}__shoe_tool_envelope_{side}",
            target + axis * tool_length / 2.0,
            axis,
            tool_diameter,
            tool_length,
            materials["tool"],
        )

    plane = interface["rear_interface_plane"]
    center = Vector(plane["center_head_mm"])
    normal = Vector(plane["outward_normal_head"]).normalized()
    across = Vector((1.0, 0.0, 0.0))
    vertical = normal.cross(across).normalized()
    pattern = interface["aluminum_backplate"]["adapter_hole_pattern"]
    hardware_diameter = float(
        envelope_config["adapter_hardware_envelope_diameter_mm"]
    )
    hardware_depth = float(
        envelope_config["adapter_hardware_envelope_total_depth_mm"]
    )
    for x in pattern["x_mm"]:
        for local_v in pattern["local_v_mm"]:
            label = f"{'p' if x >= 0 else 'n'}{abs(int(x))}_{'p' if local_v >= 0 else 'n'}{abs(int(local_v))}"
            hardware_center = center + across * float(x) + vertical * float(local_v)
            objects[f"adapter_hardware_{label}"] = create_oriented_cylinder(
                f"{prefix}__adapter_hardware_{label}",
                hardware_center,
                normal,
                hardware_diameter,
                hardware_depth,
                materials["hardware"],
            )
    return objects


def object_stats(
    obj: bpy.types.Object,
    printer_envelope: list[float],
    orientation_step: int,
) -> dict[str, Any]:
    mesh = obj.data
    points = [tuple(obj.matrix_world @ vertex.co) for vertex in mesh.vertices]
    bounds_value = gate1.bounds(points)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    boundary_edges = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    nonmanifold_edges = sum(1 for edge in bm.edges if not edge.is_manifold)
    volume = abs(float(bm.calc_volume(signed=True))) if not boundary_edges else None
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
    bm.free()
    return {
        "vertices": len(mesh.vertices),
        "faces": len(mesh.polygons),
        "connected_components": components,
        "boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "dimensions_mm": [
            round(value, 3) for value in gate1.dimensions(bounds_value)
        ],
        "volume_mm3": round(volume, 3) if volume is not None else None,
        "orientation_search": gate2.best_fit(
            points, printer_envelope, orientation_step
        ),
        "boundary_vertex_fan_splits": int(
            obj.get("boundary_vertex_fan_splits", 0)
        ),
    }


def object_bvh(obj: bpy.types.Object) -> BVHTree:
    vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    polygons = [tuple(poly.vertices) for poly in obj.data.polygons]
    return BVHTree.FromPolygons(vertices, polygons, all_triangles=False)


def collision_record(
    first: bpy.types.Object, second: bpy.types.Object
) -> dict[str, Any]:
    first_bvh = object_bvh(first)
    second_bvh = object_bvh(second)
    overlaps = first_bvh.overlap(second_bvh)
    minimum_distance = math.inf
    for vertex in first.data.vertices:
        nearest = second_bvh.find_nearest(first.matrix_world @ vertex.co)
        if nearest:
            minimum_distance = min(minimum_distance, float(nearest[3]))
    for vertex in second.data.vertices:
        nearest = first_bvh.find_nearest(second.matrix_world @ vertex.co)
        if nearest:
            minimum_distance = min(minimum_distance, float(nearest[3]))
    return {
        "first": first.name,
        "second": second.name,
        "triangle_overlap_pair_count": len(overlaps),
        "minimum_sampled_vertex_to_surface_distance_mm": (
            round(minimum_distance, 4)
            if math.isfinite(minimum_distance)
            else None
        ),
        "intersects": bool(overlaps),
    }


def export_stl(obj: bpy.types.Object, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gate3.export_stl(obj, path)


def face_signed_distance(
    face: gate1.ObjFace,
    model: gate1.ObjModel,
    transformed_points: list[tuple[float, float, float]],
    plane_center: Vector,
    plane_normal: Vector,
) -> float:
    centroid = sum(
        (Vector(transformed_points[index]) for index in face.indices),
        Vector(),
    ) / len(face.indices)
    return float((centroid - plane_center).dot(plane_normal))


def selected_cassette_faces(
    model: gate1.ObjModel,
    assignments: list[str],
    transformed_points: list[tuple[float, float, float]],
    interface: dict[str, Any],
    threshold_mm: float,
) -> set[int]:
    plane = interface["rear_interface_plane"]
    center = Vector(plane["center_head_mm"])
    normal = Vector(plane["outward_normal_head"]).normalized()
    return {
        index
        for index, (face, assignment) in enumerate(
            zip(model.faces, assignments)
        )
        if assignment in BODY_SECTIONS
        and face_signed_distance(
            face, model, transformed_points, center, normal
        )
        >= threshold_mm
    }


def create_variant(
    name: str,
    uniform_scale: float,
    cassette_threshold_mm: float | None,
    model: gate1.ObjModel,
    assignments: list[str],
    source_scale: float,
    source_origin: tuple[float, float, float],
    transformed_points: list[tuple[float, float, float]],
    interface: dict[str, Any],
    config: dict[str, Any],
    materials: dict[str, bpy.types.Material],
    output_dir: Path,
) -> tuple[dict[str, bpy.types.Object], dict[str, Any]]:
    shell_config = config["shell"]
    printer_envelope = shell_config["printer_envelope_mm"]
    orientation_step = int(shell_config["orientation_step_degrees"])
    scale_center = Vector(interface["rear_interface_plane"]["center_head_mm"])
    cassette_faces: set[int] = set()
    if cassette_threshold_mm is not None:
        cassette_faces = selected_cassette_faces(
            model,
            assignments,
            transformed_points,
            interface,
            cassette_threshold_mm,
        )
        if not cassette_faces:
            raise ValueError(f"{name}: cassette threshold selected no faces")

    objects: dict[str, bpy.types.Object] = {}
    report: dict[str, Any] = {
        "uniform_scale": uniform_scale,
        "rear_cassette_threshold_mm": cassette_threshold_mm,
        "cassette_source_face_count": len(cassette_faces),
        "cassette_source_panel_ids": sorted(
            {
                gate1.canonical_source_panel_id(model.faces[index].group)
                for index in cassette_faces
            }
        ),
        "parts": {},
    }
    for section in (*BODY_SECTIONS, *EAR_SECTIONS):
        face_indices = [
            index
            for index, assignment in enumerate(assignments)
            if assignment == section and index not in cassette_faces
        ]
        source_faces = [model.faces[index].indices for index in face_indices]
        if section in BODY_SECTIONS:
            source_faces.extend(
                tuple(face)
                for face in shell_config.get(
                    "bottom_closure_faces", {}
                ).get(section, [])
            )
        obj = create_shell_object(
            f"{name}__{section}",
            source_faces,
            model,
            source_scale,
            source_origin,
            uniform_scale,
            scale_center,
            materials[section],
            shell_config,
        )
        objects[section] = obj
        report["parts"][section] = object_stats(
            obj, printer_envelope, orientation_step
        )
        export_stl(
            obj,
            output_dir / "variants" / name / f"{section}.stl",
        )

    if cassette_faces:
        source_faces = [model.faces[index].indices for index in cassette_faces]
        rear = create_shell_object(
            f"{name}__rear_cassette",
            source_faces,
            model,
            source_scale,
            source_origin,
            uniform_scale,
            scale_center,
            materials["rear_cassette"],
            shell_config,
        )
        objects["rear_cassette"] = rear
        report["parts"]["rear_cassette"] = object_stats(
            rear, printer_envelope, orientation_step
        )
        export_stl(
            rear,
            output_dir / "variants" / name / "rear_cassette.stl",
        )
    else:
        gate3.CONFIG = {
            **shell_config,
            "compact_rear_base_frame": shell_config[
                "retained_rear_frame"
            ],
        }
        rear = gate3.create_compact_rear_base_frame(
            shell_config["retained_rear_frame"],
            materials["rear_base"],
        )
        rear.name = f"{name}__rear_base"
        if uniform_scale != 1.0:
            for vertex in rear.data.vertices:
                baseline = Vector(vertex.co)
                vertex.co = scale_center + (
                    baseline - scale_center
                ) * uniform_scale
        objects["rear_base"] = rear
        report["parts"]["rear_base"] = object_stats(
            rear, printer_envelope, orientation_step
        )
        export_stl(
            rear,
            output_dir / "variants" / name / "rear_base.stl",
        )

    metal = create_interface_envelopes(
        name,
        interface,
        config["provisional_collision_envelopes"],
        materials,
    )
    objects.update({f"metal::{key}": value for key, value in metal.items()})

    collisions: list[dict[str, Any]] = []
    for metal_key, metal_obj in metal.items():
        for shell_key, shell_obj in objects.items():
            if shell_key.startswith("metal::"):
                continue
            record = collision_record(metal_obj, shell_obj)
            record["metal_envelope"] = metal_key
            record["shell_part"] = shell_key
            record["classification"] = (
                "interface_contact_or_pass_through_to_design"
                if shell_key in {"rear_base", "rear_cassette"}
                else "unintended_if_intersecting"
            )
            collisions.append(record)
    report["collision_matrix"] = collisions
    report["unintended_intersection_count"] = sum(
        1
        for record in collisions
        if record["classification"] == "unintended_if_intersecting"
        and record["intersects"]
    )
    report["part_count"] = len(report["parts"])
    report["total_closed_mesh_volume_mm3"] = round(
        sum(
            float(part["volume_mm3"])
            for part in report["parts"].values()
            if part["volume_mm3"] is not None
        ),
        3,
    )
    return objects, report


def hide_objects(objects: list[bpy.types.Object], hidden: bool) -> None:
    for obj in objects:
        obj.hide_render = hidden


def point_camera(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (
        target - camera.location
    ).to_track_quat("-Z", "Y").to_euler()


def render_variant(
    name: str,
    objects: list[bpy.types.Object],
    all_variant_objects: list[bpy.types.Object],
    output_dir: Path,
) -> None:
    hide_objects(all_variant_objects, True)
    hide_objects(objects, False)
    scene = bpy.context.scene
    camera = bpy.data.objects["Gate9_Camera"]
    target = Vector((0.0, 177.0, 165.0))
    views = (
        ("rear-oblique", Vector((390.0, 580.0, 340.0))),
        ("front-oblique", Vector((390.0, -540.0, 320.0))),
        ("left-side", Vector((-580.0, 145.0, 260.0))),
    )
    for suffix, location in views:
        camera.location = location
        point_camera(camera, target)
        scene.render.filepath = str(
            output_dir / "renders" / f"{name}__{suffix}.png"
        )
        bpy.ops.render.render(write_still=True)


def configure_render(output_dir: Path) -> None:
    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = 1120
    scene.render.resolution_y = 840
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.018, 0.024, 0.036)

    camera_data = bpy.data.cameras.new("Gate9_Camera")
    camera = bpy.data.objects.new("Gate9_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.lens = 58

    for name, location, energy, size in (
        ("Gate9_Key", (350.0, -300.0, 480.0), 1500.0, 260.0),
        ("Gate9_Fill", (-360.0, 20.0, 300.0), 1100.0, 240.0),
        ("Gate9_Rear", (40.0, 560.0, 420.0), 1300.0, 220.0),
    ):
        light_data = bpy.data.lights.new(name, "AREA")
        light_data.energy = energy
        light_data.shape = "DISK"
        light_data.size = size
        light = bpy.data.objects.new(name, light_data)
        scene.collection.objects.link(light)
        light.location = location
        point_camera(light, Vector((0.0, 175.0, 165.0)))


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    interface = load_repo_json(config["shared_interface_path"])
    if interface["interface_revision"] != config["required_interface_revision"]:
        raise ValueError(
            "Interface mismatch: "
            f"{interface['interface_revision']} != "
            f"{config['required_interface_revision']}"
        )
    gate2_config = load_repo_json(config["source_gate2_config"])
    gate1_config = json.loads(
        gate1.DEFAULT_CONFIG.read_text(encoding="utf-8")
    )
    source_model = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    units = gate1.panel_units(
        source_model,
        gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV),
    )
    source_scale, source_origin, _ = gate1.make_transform(
        gate1.bounds(source_model.vertices),
        float(gate2_config["target_height_mm"]),
    )
    roles, _ = gate1.build_roles(units, gate1_config, source_scale)
    model = gate2.subdivide_center_panels(source_model, gate2_config)
    assignments = gate2.assign_faces(
        model.faces,
        model.vertices,
        roles,
        gate2_config,
        source_scale,
        source_origin,
    )
    transformed_points = [
        gate1.transform_point(vertex, source_scale, source_origin)
        for vertex in model.vertices
    ]

    gate3.clean_scene()
    output_dir.mkdir(parents=True, exist_ok=True)
    materials = {
        key: create_material(key, color, 0.36 if key in {"shoe", "tool", "hardware"} else 1.0)
        for key, color in SECTION_COLORS.items()
    }
    variant_specs: list[tuple[str, float, float | None]] = [
        ("retained_full_scale", 1.0, None),
        (
            "rear_cassette_full_scale",
            1.0,
            float(
                config["variants"]["rear_cassette_full_scale"][
                    "rear_cassette_threshold_mm"
                ]
            ),
        ),
    ]
    for scale in config["variants"]["uniform_scale_candidates"]["scales"]:
        label = f"uniform_scale_{float(scale):.2f}".replace(".", "p")
        variant_specs.append((label, float(scale), None))

    reports: dict[str, Any] = {}
    variant_objects: dict[str, list[bpy.types.Object]] = {}
    for name, uniform_scale, cassette_threshold in variant_specs:
        objects, report = create_variant(
            name,
            uniform_scale,
            cassette_threshold,
            model,
            assignments,
            source_scale,
            source_origin,
            transformed_points,
            interface,
            config,
            materials,
            output_dir,
        )
        reports[name] = report
        variant_objects[name] = list(objects.values())

    configure_render(output_dir)
    display_scale = float(
        config["variants"]["uniform_scale_candidates"]["display_scale"]
    )
    display_scale_name = (
        f"uniform_scale_{display_scale:.2f}".replace(".", "p")
    )
    all_objects = [
        obj for objects in variant_objects.values() for obj in objects
    ]
    for name in (
        "retained_full_scale",
        display_scale_name,
        "rear_cassette_full_scale",
    ):
        render_variant(name, variant_objects[name], all_objects, output_dir)
    hide_objects(all_objects, False)

    blend_path = output_dir / "gate9-rear-architecture-comparison-v1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.object.select_all(action="SELECT")
    if hasattr(bpy.ops.export_scene, "gltf"):
        bpy.ops.export_scene.gltf(
            filepath=str(
                output_dir
                / "gate9-rear-architecture-comparison-v1.glb"
            ),
            export_format="GLB",
            use_selection=True,
        )

    report = {
        "gate": "Gate 9 rear architecture comparison V1",
        "status": config["status"],
        "interface_revision": interface["interface_revision"],
        "config": str(config_path.relative_to(REPO_ROOT)),
        "rear_cassette_selection_rule": (
            "whole source facets assigned to the four body sections whose "
            "centroid signed distance from the frozen rear plane is at least "
            "the configured threshold"
        ),
        "provisional_collision_envelopes": config[
            "provisional_collision_envelopes"
        ],
        "variants": reports,
        "slicer_review": config["slicer_review"],
        "review_holds": config["review_holds"],
        "generated_review_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "glb": str(
                (
                    output_dir
                    / "gate9-rear-architecture-comparison-v1.glb"
                ).relative_to(REPO_ROOT)
            ),
            "renders": str((output_dir / "renders").relative_to(REPO_ROOT)),
            "stl_variants": str(
                (output_dir / "variants").relative_to(REPO_ROOT)
            ),
        },
    }
    report_path = output_dir / "gate9-rear-architecture-comparison-v1.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(
        {
            "status": report["status"],
            "interface_revision": report["interface_revision"],
            "variants": {
                name: {
                    "part_count": value["part_count"],
                    "unintended_intersection_count": value[
                        "unintended_intersection_count"
                    ],
                    "cassette_source_face_count": value[
                        "cassette_source_face_count"
                    ],
                }
                for name, value in reports.items()
            },
            "report": str(report_path.relative_to(REPO_ROOT)),
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
