#!/usr/bin/env python3
"""Generate full-size shells with hidden flange tabs and internal panel gussets."""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import bpy
import bmesh
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402

PACKAGE_ROOT = SCRIPT_DIR.parent
GATE2_CONFIG = PACKAGE_ROOT / "config/gate2-section-layout.json"
GATE3_BLEND = PACKAGE_ROOT / "output/gate3-structural-shells/gate3-structural-shells.blend"
CONFIG_PATH = PACKAGE_ROOT / "config/gate5-ribs-and-joints.json"
OUTPUT_DIR = PACKAGE_ROOT / "output/gate5-ribs-and-joints"


def transformed_source() -> tuple[gate1.ObjModel, list[str], float, gate1.Point]:
    gate1_config = json.loads(gate1.DEFAULT_CONFIG.read_text(encoding="utf-8"))
    gate2_config = json.loads(GATE2_CONFIG.read_text(encoding="utf-8"))
    source = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    units = gate1.panel_units(source, gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV))
    scale, origin, _ = gate1.make_transform(
        gate1.bounds(source.vertices), float(gate1_config["target_height_mm"])
    )
    roles, _ = gate1.build_roles(units, gate1_config, scale)
    model = gate2.subdivide_lower_center_panel(source, gate2_config["lower_center_split_panel"])
    assignments = gate2.assign_faces(
        model.faces, model.vertices, roles, gate2_config, scale, origin
    )
    return model, assignments, scale, origin


def face_centroid(face: gate1.ObjFace, points: list[Vector]) -> Vector:
    return sum((points[index] for index in face.indices), Vector()) / len(face.indices)


def outward_normal(face: gate1.ObjFace, points: list[Vector]) -> Vector:
    normal = (points[face.indices[1]] - points[face.indices[0]]).cross(
        points[face.indices[2]] - points[face.indices[0]]
    )
    if normal.length == 0.0:
        raise ValueError(f"Degenerate face {face.group}")
    normal.normalize()
    head_center = Vector((0.0, 135.0, 150.0))
    return normal if normal.dot(face_centroid(face, points) - head_center) >= 0.0 else -normal


def seam_segments(
    model: gate1.ObjModel,
    assignments: list[str],
    scale: float,
    origin: gate1.Point,
) -> tuple[list[Vector], list[dict[str, Any]]]:
    structural = set(gate2.SECTION_ORDER)
    points = [Vector(gate1.transform_point(value, scale, origin)) for value in model.vertices]
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(model.faces):
        for offset, first in enumerate(face.indices):
            second = face.indices[(offset + 1) % len(face.indices)]
            edge_faces[tuple(sorted((first, second)))].append(face_index)
    output = []
    for edge, adjacent in edge_faces.items():
        if len(adjacent) != 2:
            continue
        first_index, second_index = adjacent
        first_section, second_section = assignments[first_index], assignments[second_index]
        if (
            first_section not in structural
            or second_section not in structural
            or first_section == second_section
        ):
            continue
        if first_section > second_section:
            first_index, second_index = second_index, first_index
            first_section, second_section = second_section, first_section
        p0, p1 = points[edge[0]], points[edge[1]]
        output.append(
            {
                "sections": [first_section, second_section],
                "face_indices": [first_index, second_index],
                "face_groups": [model.faces[first_index].group, model.faces[second_index].group],
                "p0": list(p0),
                "p1": list(p1),
                "length_mm": (p1 - p0).length,
                "normals": [
                    list(outward_normal(model.faces[first_index], points)),
                    list(outward_normal(model.faces[second_index], points)),
                ],
            }
        )
    output.sort(key=lambda value: (value["sections"], -value["length_mm"]))
    return points, output


def internal_panel_segments(
    model: gate1.ObjModel,
    assignments: list[str],
    points: list[Vector],
    target_sections: set[str],
) -> list[dict[str, Any]]:
    """Return source-panel edges shared wholly inside one requested shell."""
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(model.faces):
        for offset, first in enumerate(face.indices):
            second = face.indices[(offset + 1) % len(face.indices)]
            edge_faces[tuple(sorted((first, second)))].append(face_index)

    output = []
    for edge, adjacent in edge_faces.items():
        if len(adjacent) != 2:
            continue
        first_index, second_index = adjacent
        section = assignments[first_index]
        if section not in target_sections or assignments[second_index] != section:
            continue
        first_face, second_face = model.faces[first_index], model.faces[second_index]
        first_panel = gate2.canonical_source_panel_id(first_face.group)
        second_panel = gate2.canonical_source_panel_id(second_face.group)
        if first_panel == second_panel:
            continue
        p0, p1 = points[edge[0]], points[edge[1]]
        output.append(
            {
                "section": section,
                "face_indices": [first_index, second_index],
                "face_groups": [first_face.group, second_face.group],
                "source_panels": [first_panel, second_panel],
                "vertex_indices": list(edge),
                "p0": list(p0),
                "p1": list(p1),
                "length_mm": (p1 - p0).length,
                "normals": [
                    list(outward_normal(first_face, points)),
                    list(outward_normal(second_face, points)),
                ],
            }
        )
    output.sort(key=lambda value: (value["section"], -value["length_mm"]))
    return output


def internal_gusset_junctions(
    model: gate1.ObjModel,
    segments: list[dict[str, Any]],
    points: list[Vector],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Find same-face, non-collinear gusset pairs that can share a corner node."""
    ribs = config["internal_panel_ribs"]
    at_vertex: dict[tuple[str, int, int], list[tuple[int, int]]] = defaultdict(list)
    for segment_index, segment in enumerate(segments):
        first, second = segment["vertex_indices"]
        face_index = segment["face_indices"][1]
        key_prefix = (segment["section"], face_index)
        at_vertex[(*key_prefix, first)].append((segment_index, second))
        at_vertex[(*key_prefix, second)].append((segment_index, first))

    output = []
    minimum_angle = float(ribs["junction_minimum_angle_deg"])
    maximum_angle = float(ribs["junction_maximum_angle_deg"])
    for (section, face_index, vertex_index), values in sorted(at_vertex.items()):
        if len(values) != 2:
            continue
        (first_segment, first_other), (second_segment, second_other) = values
        first_direction = (points[first_other] - points[vertex_index]).normalized()
        second_direction = (points[second_other] - points[vertex_index]).normalized()
        angle = math.degrees(first_direction.angle(second_direction))
        if not minimum_angle <= angle <= maximum_angle:
            continue
        output.append(
            {
                "section": section,
                "attachment_face_index": face_index,
                "attachment_source_face": model.faces[face_index].group,
                "vertex_index": vertex_index,
                "other_vertex_indices": [first_other, second_other],
                "rib_segment_indices": [first_segment, second_segment],
                "included_angle_deg": angle,
            }
        )
    return output


def seam_report(segments: list[dict[str, Any]], minimum: float) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for segment in segments:
        grouped[tuple(segment["sections"])].append(segment)
    pairs = {}
    for pair, values in sorted(grouped.items()):
        usable = [value for value in values if value["length_mm"] >= minimum]
        pairs["__".join(pair)] = {
            "edge_count": len(values),
            "usable_edge_count": len(usable),
            "total_length_mm": round(sum(value["length_mm"] for value in values), 3),
            "usable_lengths_mm": [round(value["length_mm"], 3) for value in usable],
            "face_groups": [value["face_groups"] for value in usable],
        }
    return {"pair_count": len(pairs), "pairs": pairs}


def material(name: str, color: tuple[float, float, float, float]) -> bpy.types.Material:
    value = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    value.diffuse_color = color
    value.roughness = 0.45
    return value


def box(
    name: str,
    center: Vector,
    axes: tuple[Vector, Vector, Vector],
    dimensions: tuple[float, float, float],
    assigned_material: bpy.types.Material | None = None,
) -> bpy.types.Object:
    unit = tuple(axis.normalized() for axis in axes)
    half = tuple(value / 2.0 for value in dimensions)
    signs = (
        (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
        (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1),
    )
    vertices = [
        center + unit[0] * half[0] * sx + unit[1] * half[1] * sy + unit[2] * half[2] * sz
        for sx, sy, sz in signs
    ]
    faces = (
        (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4),
        (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7),
    )
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata([tuple(value) for value in vertices], [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if assigned_material:
        obj.data.materials.append(assigned_material)
    return obj


def triangular_prism(
    name: str,
    first: tuple[Vector, Vector, Vector],
    second: tuple[Vector, Vector, Vector],
    assigned_material: bpy.types.Material | None = None,
) -> bpy.types.Object:
    """Create a closed triangular prism between matching three-point ends."""
    vertices = [*first, *second]
    faces = (
        (0, 1, 2), (3, 5, 4),
        (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0),
    )
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata([tuple(value) for value in vertices], [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    if assigned_material:
        obj.data.materials.append(assigned_material)
    return obj


def cylinder(
    name: str,
    first: Vector,
    second: Vector,
    diameter: float,
    assigned_material: bpy.types.Material | None = None,
    vertices: int = 16,
) -> bpy.types.Object:
    direction = second - first
    if direction.length < 0.01:
        raise ValueError(f"Cylinder {name} is too short")
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices,
        radius=diameter / 2.0,
        depth=direction.length,
        location=(first + second) / 2.0,
    )
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler = direction.to_track_quat("Z", "Y").to_euler()
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    if assigned_material:
        obj.data.materials.append(assigned_material)
    return obj


def apply_boolean(target: bpy.types.Object, tool: bpy.types.Object, operation: str) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    modifier = target.modifiers.new(f"{operation}_{tool.name}", "BOOLEAN")
    modifier.operation = operation
    modifier.solver = "EXACT"
    modifier.object = tool
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(tool, do_unlink=True)
    target.select_set(False)


def convex_hull_objects(
    name: str,
    objects: list[bpy.types.Object],
    assigned_material: bpy.types.Material,
) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.join()
    hull = bpy.context.object
    hull.name = name
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.convex_hull(
        delete_unused=True,
        use_existing_faces=False,
        make_holes=False,
        join_triangles=True,
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    hull.data.materials.clear()
    hull.data.materials.append(assigned_material)
    hull.select_set(False)
    return hull


def union_mesh_objects(
    name: str, objects: list[bpy.types.Object]
) -> bpy.types.Object:
    combined = objects[0]
    combined.name = name
    for tool in objects[1:]:
        apply_boolean(combined, tool, "UNION")
        require_manifold(combined, f"{name} internal frame-part union")
    return combined


def components(obj: bpy.types.Object) -> list[list[int]]:
    neighbors: dict[int, set[int]] = defaultdict(set)
    for edge in obj.data.edges:
        first, second = edge.vertices
        neighbors[first].add(second)
        neighbors[second].add(first)
    remaining = set(range(len(obj.data.vertices)))
    output = []
    while remaining:
        start = remaining.pop()
        stack = [start]
        component = [start]
        while stack:
            current = stack.pop()
            for neighbor in neighbors[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
                    component.append(neighbor)
        output.append(component)
    return sorted(output, key=len, reverse=True)


def topology_counts(obj: bpy.types.Object) -> tuple[int, int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    nonmanifold = sum(1 for edge in bm.edges if not edge.is_manifold)
    bm.free()
    return boundary, nonmanifold


def require_manifold(obj: bpy.types.Object, operation_name: str) -> None:
    boundary, nonmanifold = topology_counts(obj)
    if boundary or nonmanifold:
        raise ValueError(
            f"{operation_name} damaged {obj.name}: "
            f"boundary={boundary}, nonmanifold={nonmanifold}"
        )


def remove_loose_geometry(obj: bpy.types.Object) -> None:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    loose_vertices = [vertex for vertex in bm.verts if not vertex.link_faces]
    if loose_vertices:
        bmesh.ops.delete(bm, geom=loose_vertices, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def mesh_volume(obj: bpy.types.Object) -> float:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    volume = abs(bm.calc_volume(signed=True))
    bm.free()
    return volume


def component_volume(obj: bpy.types.Object, vertex_indices: list[int]) -> float:
    """Return enclosed volume for one closed connected mesh component."""
    selected = set(vertex_indices)
    vertices = obj.data.vertices
    transform = obj.matrix_world
    signed_volume = 0.0
    for polygon in obj.data.polygons:
        if polygon.vertices[0] not in selected:
            continue
        first = transform @ vertices[polygon.vertices[0]].co
        for offset in range(1, len(polygon.vertices) - 1):
            second = transform @ vertices[polygon.vertices[offset]].co
            third = transform @ vertices[polygon.vertices[offset + 1]].co
            signed_volume += first.dot(second.cross(third)) / 6.0
    return abs(signed_volume)


def keep_largest_component(obj: bpy.types.Object) -> dict[str, float | int]:
    """Remove boolean slivers while retaining the component with most volume."""
    found = components(obj)
    volumes = [component_volume(obj, component) for component in found]
    if len(found) <= 1:
        return {
            "component_count_before_cleanup": len(found),
            "removed_component_count": 0,
            "kept_component_volume_mm3": round(volumes[0] if volumes else 0.0, 3),
            "removed_component_volume_mm3": 0.0,
        }
    keep_index = max(range(len(found)), key=lambda index: volumes[index])
    keep = set(found[keep_index])
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    remove = [vertex for vertex in bm.verts if vertex.index not in keep]
    bmesh.ops.delete(bm, geom=remove, context="VERTS")
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    removed_volume = sum(
        volume for index, volume in enumerate(volumes) if index != keep_index
    )
    obj["removed_boolean_sliver_components"] = len(found) - 1
    obj["removed_boolean_sliver_volume_mm3"] = removed_volume
    return {
        "component_count_before_cleanup": len(found),
        "removed_component_count": len(found) - 1,
        "kept_component_volume_mm3": round(volumes[keep_index], 3),
        "removed_component_volume_mm3": round(removed_volume, 3),
    }


def projected_extent(obj: bpy.types.Object, axis: Vector) -> float:
    direction = axis.normalized()
    values = [
        (obj.matrix_world @ vertex.co).dot(direction) for vertex in obj.data.vertices
    ]
    return max(values) - min(values)


def add_eye_ribs(
    obj: bpy.types.Object,
    config: dict[str, Any],
    rib_material: bpy.types.Material,
) -> list[dict[str, Any]]:
    values = config["internal_ribs"]
    found = components(obj)
    if len(found) != 2:
        raise ValueError(f"{obj.name}: expected 2 components before eye ribs, found {len(found)}")
    main, island = found
    center = Vector((0.0, 135.0, 150.0))
    world = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]

    def inner_half(indices: list[int]) -> list[int]:
        ordered = sorted(indices, key=lambda index: (world[index] - center).length)
        return ordered[: max(2, len(ordered) // 2)]

    main_inner, island_inner = inner_half(main), inner_half(island)
    candidates = []
    for island_index in island_inner:
        main_index = min(
            main_inner, key=lambda index: (world[index] - world[island_index]).length
        )
        candidates.append(
            ((world[main_index] - world[island_index]).length, island_index, main_index)
        )
    selected = []
    for candidate in sorted(candidates):
        if all(
            (world[candidate[1]] - world[existing[1]]).length
            >= float(values["minimum_anchor_separation_mm"])
            for existing in selected
        ):
            selected.append(candidate)
        if len(selected) == int(values["eye_bridge_count_per_side"]):
            break
    if len(selected) != int(values["eye_bridge_count_per_side"]):
        raise ValueError(f"{obj.name}: could not place separated eye ribs")

    records = []
    for rib_index, (_, island_index, main_index) in enumerate(selected, start=1):
        first, second = world[island_index], world[main_index]
        offset = float(values["eye_bridge_interior_offset_mm"])
        first_inner = first + (center - first).normalized() * offset
        second_inner = second + (center - second).normalized() * offset
        direction = (second_inner - first_inner).normalized()
        tool = cylinder(
            f"{obj.name}_eye_rib_{rib_index}",
            first_inner - direction * (offset + 2.0),
            second_inner + direction * (offset + 2.0),
            float(values["eye_bridge_diameter_mm"]),
            rib_material,
            vertices=12,
        )
        apply_boolean(obj, tool, "UNION")
        records.append({"rib": rib_index, "span_mm": round((second - first).length, 3)})
    return records


def distribute_modules(
    segments: list[dict[str, Any]], max_spacing: float
) -> list[tuple[dict[str, Any], float, int]]:
    output = []
    for segment in segments:
        count = max(1, math.ceil(segment["length_mm"] / (2.0 * max_spacing)))
        for module_index in range(count):
            output.append((segment, (module_index + 1) / (count + 1), count))
    return output


def joint_roles(
    segment: dict[str, Any], config: dict[str, Any]
) -> tuple[str, str]:
    pair = "__".join(segment["sections"])
    if pair not in config["integrated_joint_ownership"]:
        raise ValueError(f"No integrated-joint ownership rule for {pair}")
    rule = config["integrated_joint_ownership"][pair]
    owner, receiver = rule["owner"], rule["receiver"]
    if {owner, receiver} != set(segment["sections"]):
        raise ValueError(f"Invalid owner/receiver rule for {pair}: {rule}")
    return owner, receiver


def side_geometry(
    name: str,
    segment: dict[str, Any],
    section: str,
    seam_point: Vector,
    tangent: Vector,
    model: gate1.ObjModel,
    points: list[Vector],
) -> dict[str, Any]:
    side_index = segment["sections"].index(section)
    face = model.faces[segment["face_indices"][side_index]]
    normal = Vector(segment["normals"][side_index]).normalized()
    toward_face = face_centroid(face, points) - seam_point
    toward_face -= tangent * toward_face.dot(tangent)
    toward_face -= normal * toward_face.dot(normal)
    face_depth = toward_face.length
    if face_depth < 0.01:
        raise ValueError(f"{name}: cannot orient geometry on {face.group}")
    toward_face.normalize()
    return {
        "section": section,
        "face": face,
        "normal": normal,
        "toward_face": toward_face,
        "face_depth_mm": face_depth,
    }


def add_owner_seam_rib(
    segment: dict[str, Any],
    model: gate1.ObjModel,
    points: list[Vector],
    config: dict[str, Any],
    rib_material: bpy.types.Material,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    owner, receiver = joint_roles(segment, config)
    frame = config["internal_frame"]
    wall = float(config["shell_wall_thickness_mm"])
    p0, p1 = Vector(segment["p0"]), Vector(segment["p1"])
    tangent = (p1 - p0).normalized()
    seam_point = p0.lerp(p1, 0.5)
    geometry = side_geometry(
        f"seam_rib_{owner}", segment, owner, seam_point, tangent, model, points
    )
    end_margin = float(frame["seam_rib_end_margin_mm"])
    length = float(segment["length_mm"]) - 2.0 * end_margin
    if length <= 4.0:
        raise ValueError(f"Seam rib for {segment['face_groups']} is too short")
    thickness = float(frame["seam_rib_thickness_mm"])
    depth = float(frame["seam_rib_depth_mm"])
    overlap = float(frame["seam_rib_shell_overlap_mm"])
    face_offset = min(
        float(frame["seam_rib_face_offset_mm"]), geometry["face_depth_mm"]
    )
    surface_center = seam_point + geometry["toward_face"] * face_offset
    rib = box(
        f"seam_rib_{owner}_{geometry['face'].group}",
        surface_center
        - geometry["normal"] * (wall + depth / 2.0 - overlap),
        (tangent, geometry["toward_face"], geometry["normal"]),
        (length, thickness, depth),
        rib_material,
    )
    return rib, {
        "owner": owner,
        "receiver": receiver,
        "source_faces": segment["face_groups"],
        "length_mm": round(length, 3),
        "depth_mm": depth,
        "thickness_mm": thickness,
        "face_offset_mm": round(face_offset, 3),
    }


def cut_rear_service_opening_and_add_rim(
    rear: bpy.types.Object,
    config: dict[str, Any],
    rim_material: bpy.types.Material,
) -> dict[str, Any]:
    opening = config["rear_service_opening"]
    before_faces = len(rear.data.polygons)
    bpy.ops.mesh.primitive_cube_add(
        location=(
            float(opening["center_x_mm"]),
            float(opening["center_y_mm"]),
            float(opening["center_z_mm"]),
        )
    )
    cutter = bpy.context.active_object
    cutter.name = "gate5_rear_service_opening_cutter"
    cutter.dimensions = (
        float(opening["width_mm"]),
        float(opening["cut_depth_mm"]),
        float(opening["height_mm"]),
    )
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    apply_boolean(rear, cutter, "DIFFERENCE")
    require_manifold(rear, "rear service-opening cut")

    width = float(opening["width_mm"])
    height = float(opening["height_mm"])
    rim_width = float(opening["rim_width_mm"])
    rim_depth = float(opening["rim_depth_mm"])
    center_x = float(opening["center_x_mm"])
    center_y = float(opening["rim_center_y_mm"])
    center_z = float(opening["center_z_mm"])
    tie_length = float(opening["rim_tie_length_mm"])
    tie_x_offset = float(opening["rim_tie_x_offset_mm"])
    bottom_z = center_z - height / 2.0 - rim_width / 2.0
    tie_y = center_y - tie_length / 2.0 + rim_depth / 2.0
    axes = (Vector((1.0, 0.0, 0.0)), Vector((0.0, 1.0, 0.0)), Vector((0.0, 0.0, 1.0)))
    bars = (
        (
            "left",
            Vector((center_x - width / 2.0 - rim_width / 2.0, center_y, center_z)),
            (rim_width, rim_depth, height + 2.0 * rim_width),
        ),
        (
            "right",
            Vector((center_x + width / 2.0 + rim_width / 2.0, center_y, center_z)),
            (rim_width, rim_depth, height + 2.0 * rim_width),
        ),
        (
            "bottom",
            Vector((center_x, center_y, bottom_z)),
            (width + 2.0 * rim_width, rim_depth, rim_width),
        ),
        (
            "top",
            Vector((center_x, center_y, center_z + height / 2.0 + rim_width / 2.0)),
            (width + 2.0 * rim_width, rim_depth, rim_width),
        ),
        (
            "tie_left",
            Vector((center_x - tie_x_offset, tie_y, bottom_z)),
            (rim_width, tie_length, rim_width),
        ),
        (
            "tie_right",
            Vector((center_x + tie_x_offset, tie_y, bottom_z)),
            (rim_width, tie_length, rim_width),
        ),
    )
    for label, center, dimensions in bars:
        bar = box(
            f"rear_service_rim_{label}", center, axes, dimensions, rim_material
        )
        apply_boolean(rear, bar, "UNION")
        require_manifold(rear, f"rear service-rim {label} union")
    if len(components(rear)) != 1:
        raise ValueError("Rear service rim did not form one connected rear-base solid")
    return {
        "width_mm": width,
        "height_mm": height,
        "rim_width_mm": rim_width,
        "rim_depth_mm": rim_depth,
        "rim_tie_length_mm": tie_length,
        "faces_before": before_faces,
        "faces_after": len(rear.data.polygons),
        "connected_after_rim": True,
    }


def joint_module_length(
    segment: dict[str, Any], allocation_count: int, config: dict[str, Any]
) -> float:
    joint = config["joint_system"]
    module_length = min(
        float(joint["module_length_mm"]),
        float(segment["length_mm"]) * 0.72 / allocation_count,
    )
    if any(section.endswith("_ear") for section in segment["sections"]):
        module_length = min(
            float(joint["module_length_mm"]),
            float(segment["length_mm"]) * 0.90,
        )
    return module_length


def add_joint_shell_pads(
    name: str,
    segment: dict[str, Any],
    fraction: float,
    allocation_count: int,
    model: gate1.ObjModel,
    points: list[Vector],
    shells: dict[str, bpy.types.Object],
    config: dict[str, Any],
    reinforcement_material: bpy.types.Material,
) -> None:
    joint = config["joint_system"]
    p0, p1 = Vector(segment["p0"]), Vector(segment["p1"])
    tangent = (p1 - p0).normalized()
    seam_point = p0.lerp(p1, fraction)
    module_length = joint_module_length(segment, allocation_count, config)
    width = float(joint["bridge_width_mm"])
    wall = float(config["shell_wall_thickness_mm"])
    reinforcement = float(joint["shell_reinforcement_thickness_mm"])
    shell_overlap = 0.5
    for section in segment["sections"]:
        geometry = side_geometry(
            name, segment, section, seam_point, tangent, model, points
        )
        surface_center = seam_point + geometry["toward_face"] * (width / 2.0)
        shell_pad = box(
            f"{name}_{section}_shell_pad",
            surface_center
            - geometry["normal"]
            * (wall + reinforcement / 2.0 - shell_overlap),
            (tangent, geometry["toward_face"], geometry["normal"]),
            (module_length, width, reinforcement),
            reinforcement_material,
        )
        apply_boolean(shells[section], shell_pad, "UNION")
        require_manifold(shells[section], f"{name} shell-pad union")


def create_integrated_joint(
    name: str,
    segment: dict[str, Any],
    fraction: float,
    allocation_count: int,
    model: gate1.ObjModel,
    points: list[Vector],
    shells: dict[str, bpy.types.Object],
    config: dict[str, Any],
    bridge_material: bpy.types.Material,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    joint = config["joint_system"]
    owner, receiver = joint_roles(segment, config)
    p0, p1 = Vector(segment["p0"]), Vector(segment["p1"])
    tangent = (p1 - p0).normalized()
    seam_point = p0.lerp(p1, fraction)
    module_length = joint_module_length(segment, allocation_count, config)
    ear_joint = any(section.endswith("_ear") for section in segment["sections"])
    width = float(joint["bridge_width_mm"])
    thickness = float(joint["bridge_thickness_mm"])
    wall = float(config["shell_wall_thickness_mm"])
    reinforcement = float(joint["shell_reinforcement_thickness_mm"])
    clearance = float(joint["receiver_contact_clearance_mm"])
    owner_overlap = float(joint["owner_bridge_overlap_mm"])
    cut_extension = float(joint["boolean_cut_extension_mm"])
    shell_overlap = 0.5
    shell_pad_inner_depth = wall + reinforcement - shell_overlap
    owner_seat_depth = shell_pad_inner_depth - owner_overlap
    receiver_seat_depth = shell_pad_inner_depth + clearance
    pads = []
    side_records: dict[str, dict[str, Any]] = {}

    for section in segment["sections"]:
        geometry = side_geometry(
            name, segment, section, seam_point, tangent, model, points
        )
        normal = geometry["normal"]
        toward_face = geometry["toward_face"]
        surface_center = seam_point + toward_face * (width / 2.0)

        seat_depth = owner_seat_depth if section == owner else receiver_seat_depth
        bridge_pad = box(
            f"{name}_{section}_bridge_pad",
            surface_center - normal * (seat_depth + thickness / 2.0),
            (tangent, toward_face, normal),
            (module_length, width, thickness),
            bridge_material,
        )
        pads.append(bridge_pad)
        side_records[section] = {
            **geometry,
            "surface_center": surface_center,
            "seat_depth": seat_depth,
        }

    bridge = convex_hull_objects(name, pads, bridge_material)
    initial_hull_volume = mesh_volume(bridge)
    receiver_record = side_records[receiver]
    normal = receiver_record["normal"]
    toward_face = receiver_record["toward_face"]
    fastening_line = seam_point + toward_face * (width * 0.58)
    screw_points = (
        [
            fastening_line - tangent * (module_length * 0.28),
            fastening_line + tangent * (module_length * 0.28),
        ]
        if ear_joint
        else [fastening_line - tangent * (module_length * 0.18)]
    )
    align_point = (
        seam_point + toward_face * (width * 0.45)
        if ear_joint
        else fastening_line + tangent * (module_length * 0.22)
    )

    for screw_index, screw_point in enumerate(screw_points, start=1):
        bridge_hole = cylinder(
            f"{name}_internal_m3_{screw_index}",
            screw_point - normal * (receiver_seat_depth - cut_extension),
            screw_point
            - normal * (receiver_seat_depth + thickness + cut_extension),
            float(joint["m3_clearance_diameter_mm"]),
        )
        apply_boolean(bridge, bridge_hole, "DIFFERENCE")

    bridge_contact = align_point - normal * receiver_seat_depth
    bridge_dowel_pocket = cylinder(
        f"{name}_bridge_dowel_pocket",
        bridge_contact + normal * cut_extension,
        bridge_contact
        - normal
        * (float(joint["alignment_bridge_engagement_mm"]) + cut_extension),
        float(joint["alignment_bridge_pocket_diameter_mm"]),
    )
    apply_boolean(bridge, bridge_dowel_pocket, "DIFFERENCE")
    remove_loose_geometry(bridge)
    cleanup = keep_largest_component(bridge)
    require_manifold(bridge, f"{name} bridge hardware cuts")

    final_volume = mesh_volume(bridge)
    retained_volume_ratio = final_volume / initial_hull_volume
    length_extent = projected_extent(bridge, tangent)
    projected_length_ratio = length_extent / module_length
    validation = config["validation"]
    minimum_volume_ratio = float(
        validation["minimum_bridge_retained_volume_ratio"]
    )
    maximum_volume_ratio = float(
        validation["maximum_bridge_retained_volume_ratio"]
    )
    minimum_length_ratio = float(
        validation["minimum_bridge_projected_length_ratio"]
    )
    maximum_cleanup_volume = float(
        validation["maximum_boolean_cleanup_volume_mm3"]
    )
    if retained_volume_ratio < minimum_volume_ratio:
        raise ValueError(
            f"{name}: retained volume ratio {retained_volume_ratio:.3f} is below "
            f"{minimum_volume_ratio:.3f}"
        )
    if retained_volume_ratio > maximum_volume_ratio:
        raise ValueError(
            f"{name}: retained bridge ratio {retained_volume_ratio:.3f} is above "
            f"{maximum_volume_ratio:.3f}; hidden hardware cuts may be missing"
        )
    if projected_length_ratio < minimum_length_ratio:
        raise ValueError(
            f"{name}: projected length ratio {projected_length_ratio:.3f} is below "
            f"{minimum_length_ratio:.3f}"
        )
    if cleanup["removed_component_volume_mm3"] > maximum_cleanup_volume:
        raise ValueError(
            f"{name}: boolean cleanup removed "
            f"{cleanup['removed_component_volume_mm3']:.3f} mm^3, above the "
            f"{maximum_cleanup_volume:.3f} mm^3 limit"
        )

    nut_depth = float(joint["square_nut_depth_mm"])
    nut_cut_depth = nut_depth + cut_extension
    for screw_index, screw_point in enumerate(screw_points, start=1):
        nut_pocket = box(
            f"{name}_{receiver}_captive_nut_{screw_index}",
            screw_point - normal * (wall + nut_cut_depth / 2.0),
            (tangent, toward_face, normal),
            (
                float(joint["square_nut_width_mm"]),
                float(joint["square_nut_width_mm"]),
                nut_cut_depth,
            ),
        )
        apply_boolean(shells[receiver], nut_pocket, "DIFFERENCE")
        require_manifold(
            shells[receiver], f"{name} receiver captive-nut pocket {screw_index}"
        )

    receiver_socket = cylinder(
        f"{name}_{receiver}_dowel_socket",
        align_point
        - normal * (shell_pad_inner_depth + cut_extension),
        align_point
        - normal
        * (
            shell_pad_inner_depth
            - float(joint["alignment_receiver_engagement_mm"])
        ),
        float(joint["alignment_receiver_socket_diameter_mm"]),
    )
    apply_boolean(shells[receiver], receiver_socket, "DIFFERENCE")
    require_manifold(shells[receiver], f"{name} receiver dowel socket")

    if len(components(shells[receiver])) != 1:
        raise ValueError(f"{name}: receiver hardware split {receiver}")

    exterior_skin = min(
        wall,
        shell_pad_inner_depth
        - float(joint["alignment_receiver_engagement_mm"]),
    )
    minimum_skin = float(
        validation["minimum_hidden_hardware_exterior_skin_mm"]
    )
    if exterior_skin < minimum_skin:
        raise ValueError(
            f"{name}: hidden hardware leaves {exterior_skin:.3f} mm exterior skin, "
            f"below {minimum_skin:.3f} mm"
        )

    screw_count = 2 if ear_joint else 1
    return bridge, {
        "name": name,
        "sections": segment["sections"],
        "owner": owner,
        "receiver": receiver,
        "source_faces": segment["face_groups"],
        "module_length_mm": round(module_length, 3),
        "internal_m3_screws": screw_count,
        "captive_square_nuts": screw_count,
        "alignment_dowels": 1,
        "exterior_fastener_holes": 0,
        "minimum_exterior_skin_mm": round(exterior_skin, 3),
        "initial_hull_volume_mm3": round(initial_hull_volume, 3),
        "final_volume_mm3": round(final_volume, 3),
        "retained_volume_ratio": round(retained_volume_ratio, 4),
        "projected_length_mm": round(length_extent, 3),
        "projected_length_ratio": round(projected_length_ratio, 4),
        "boolean_cleanup": cleanup,
        "integrated_load_spreading_body_valid": True,
        "internal_tool_access_required": True,
    }


def create_internal_flange_tab(
    name: str,
    module_length: float,
    tangent: Vector,
    flange_center: Vector,
    bolt_axis: Vector,
    inward: Vector,
    config: dict[str, Any],
    flange_material: bpy.types.Material,
) -> bpy.types.Object:
    """Make one plain rectangular tab: the same shape on either shell."""
    joint = config["joint_system"]
    tab_thickness = float(joint["flange_tab_thickness_mm"])
    tab_depth = float(joint["flange_tab_depth_mm"])
    return box(
        name,
        flange_center,
        (tangent, bolt_axis, inward),
        (module_length, tab_thickness, tab_depth),
        flange_material,
    )


def create_internal_flange_tabs(
    name: str,
    segment: dict[str, Any],
    fraction: float,
    allocation_count: int,
    model: gate1.ObjModel,
    points: list[Vector],
    config: dict[str, Any],
    flange_material: bpy.types.Material,
) -> tuple[dict[str, bpy.types.Object], dict[str, Any]]:
    """Create matching rectangular flange tabs and internal through-bolts."""
    joint = config["joint_system"]
    validation = config["validation"]
    owner, receiver = joint_roles(segment, config)
    p0, p1 = Vector(segment["p0"]), Vector(segment["p1"])
    tangent = (p1 - p0).normalized()
    seam_point = p0.lerp(p1, fraction)
    module_length = joint_module_length(segment, allocation_count, config)
    owner_local = side_geometry(
        name, segment, owner, seam_point, tangent, model, points
    )
    receiver_local = side_geometry(
        name, segment, receiver, seam_point, tangent, model, points
    )
    tab_thickness = float(joint["flange_tab_thickness_mm"])
    tab_depth = float(joint["flange_tab_depth_mm"])
    clearance = float(joint["flange_face_clearance_mm"])
    wall = float(config["shell_wall_thickness_mm"])
    root_overlap = float(joint["flange_shell_overlap_mm"])
    cut_extension = float(joint["boolean_cut_extension_mm"])

    average_inward = -owner_local["normal"] - receiver_local["normal"]
    if average_inward.length < 0.01:
        raise ValueError(f"{name}: cannot determine a shared interior direction")
    # On a dihedral seam a bolt cannot be exactly parallel to both panels.
    # Use their shared interior bisector instead: both matching tabs remain
    # fully inside the head and the through-bolt never approaches the exterior.
    inward = average_inward.normalized()
    bolt_axis = inward.cross(tangent).normalized()
    if bolt_axis.dot(owner_local["toward_face"]) < 0.0:
        bolt_axis.negate()
    tab_depth_center = wall + tab_depth / 2.0 - root_overlap
    face_offset = tab_thickness / 2.0 + clearance / 2.0
    owner_center = seam_point + inward * tab_depth_center + bolt_axis * face_offset
    receiver_center = seam_point + inward * tab_depth_center - bolt_axis * face_offset

    # Recess the whole matching pair far enough that every tab vertex remains
    # inside both source-face exterior planes.  This explicitly prevents the
    # receiver-tab exposure visible in the prior owner-plane construction.
    requested_recess = float(joint["minimum_tab_exterior_recess_mm"])
    half_dimensions = (module_length / 2.0, tab_thickness / 2.0, tab_depth / 2.0)

    def maximum_outward_projection(center: Vector, normal: Vector) -> float:
        return (
            (center - seam_point).dot(normal)
            + half_dimensions[0] * abs(tangent.dot(normal))
            + half_dimensions[1] * abs(bolt_axis.dot(normal))
            + half_dimensions[2] * abs(inward.dot(normal))
        )

    normals = (owner_local["normal"], receiver_local["normal"])
    centers = (owner_center, receiver_center)
    required_shift = 0.0
    for center in centers:
        for normal in normals:
            inward_projection = -inward.dot(normal)
            if inward_projection <= 0.01:
                raise ValueError(f"{name}: shared tab direction is not interior")
            required_shift = max(
                required_shift,
                (maximum_outward_projection(center, normal) + requested_recess)
                / inward_projection,
            )
    if required_shift > 0.0:
        # Keep a deliberate machining/boolean margin rather than landing a
        # box vertex exactly on an exterior plane.
        required_shift += 0.02
        owner_center += inward * required_shift
        receiver_center += inward * required_shift
    owner_tab = create_internal_flange_tab(
        f"{name}_{owner}",
        module_length,
        tangent,
        owner_center,
        bolt_axis,
        inward,
        config,
        flange_material,
    )
    receiver_tab = create_internal_flange_tab(
        f"{name}_{receiver}",
        module_length,
        tangent,
        receiver_center,
        bolt_axis,
        inward,
        config,
        flange_material,
    )
    initial_volumes = {
        owner: mesh_volume(owner_tab),
        receiver: mesh_volume(receiver_tab),
    }
    ear_joint = any(section.endswith("_ear") for section in segment["sections"])
    fastener_center = (owner_center + receiver_center) / 2.0 + inward * (tab_depth * 0.20)
    screw_points = (
        [
            fastener_center - tangent * (module_length * 0.25),
            fastener_center + tangent * (module_length * 0.25),
        ]
        if ear_joint
        else [fastener_center]
    )
    for screw_index, screw_point in enumerate(screw_points, start=1):
        for label, tab in ((owner, owner_tab), (receiver, receiver_tab)):
            axis_distances = [
                ((tab.matrix_world @ vertex.co) - screw_point).dot(bolt_axis)
                for vertex in tab.data.vertices
            ]
            first = screw_point + bolt_axis * (min(axis_distances) - cut_extension)
            second = screw_point + bolt_axis * (max(axis_distances) + cut_extension)
            hole = cylinder(
                f"{name}_{label}_m3_{screw_index}",
                first,
                second,
                float(joint["m3_clearance_diameter_mm"]),
            )
            apply_boolean(tab, hole, "DIFFERENCE")
            require_manifold(tab, f"{name} {label} M3 cut {screw_index}")

    tabs = {owner: owner_tab, receiver: receiver_tab}
    minimum_exterior_recess = -max(
        maximum_outward_projection(center, normal)
        for center in (owner_center, receiver_center)
        for normal in normals
    )
    if minimum_exterior_recess + 1e-6 < requested_recess:
        raise ValueError(
            f"{name}: tab pair recess {minimum_exterior_recess:.6f} mm is below "
            f"the required {requested_recess:.6f} mm after a {required_shift:.6f} mm shift"
        )
    final_volumes = {section: mesh_volume(tab) for section, tab in tabs.items()}
    retained = {
        section: final_volumes[section] / initial_volumes[section]
        for section in tabs
    }
    minimum_ratio = float(validation["minimum_flange_retained_volume_ratio"])
    maximum_ratio = float(validation["maximum_flange_retained_volume_ratio"])
    minimum_length_ratio = float(validation["minimum_flange_projected_length_ratio"])
    for section, tab in tabs.items():
        if len(components(tab)) != 1:
            raise ValueError(f"{name}: flange tab split on {section}")
        if not minimum_ratio <= retained[section] <= maximum_ratio:
            raise ValueError(
                f"{name}: {section} flange retained ratio "
                f"{retained[section]:.3f} is outside "
                f"{minimum_ratio:.3f}..{maximum_ratio:.3f}"
            )
        projected_length_ratio = projected_extent(tab, tangent) / module_length
        if projected_length_ratio < minimum_length_ratio:
            raise ValueError(
                f"{name}: {section} flange projected length ratio "
                f"{projected_length_ratio:.3f} is below {minimum_length_ratio:.3f}"
            )

    screw_count = len(screw_points)
    exterior_skin = wall
    if exterior_skin < float(validation["minimum_hidden_hardware_exterior_skin_mm"]):
        raise ValueError(f"{name}: exterior skin is below the configured limit")
    return tabs, {
        "name": name,
        "sections": segment["sections"],
        "owner": owner,
        "receiver": receiver,
        "source_faces": segment["face_groups"],
        "module_length_mm": round(module_length, 3),
        "flange_tab_depth_mm": tab_depth,
        "flange_tab_thickness_mm": tab_thickness,
        "flange_face_clearance_mm": clearance,
        "internal_m3_screws": screw_count,
        "captive_square_nuts": 0,
        "loose_m3_nyloc_nuts": screw_count,
        "alignment_dowels": 0,
        "exterior_fastener_holes": 0,
        "minimum_exterior_skin_mm": round(exterior_skin, 3),
        "minimum_tab_exterior_recess_mm": round(minimum_exterior_recess, 3),
        "fastener_axis": [round(value, 4) for value in bolt_axis],
        "fastener_axis_uses_shared_interior_bisector": True,
        "tabs_are_matching_plain_rectangles": True,
        "owner_tab_retained_volume_ratio": round(retained[owner], 4),
        "receiver_tab_retained_volume_ratio": round(retained[receiver], 4),
        "integrated_flange_tabs_valid": True,
        "internal_tool_access_required": True,
    }


def create_internal_panel_rib(
    name: str,
    segment: dict[str, Any],
    model: gate1.ObjModel,
    points: list[Vector],
    config: dict[str, Any],
    rib_material: bpy.types.Material,
) -> tuple[str, list[bpy.types.Object], dict[str, Any]]:
    """Create one light triangular gusset along an internal panel edge."""
    ribs = config["internal_panel_ribs"]
    section = segment["section"]
    p0, p1 = Vector(segment["p0"]), Vector(segment["p1"])
    tangent = (p1 - p0).normalized()
    end_setback = float(ribs["end_setback_mm"])
    length = (p1 - p0).length - 2.0 * end_setback
    if length <= 4.0:
        raise ValueError(f"{name}: internal panel rib is too short")
    start, end = p0 + tangent * end_setback, p1 - tangent * end_setback
    second_face = model.faces[segment["face_indices"][1]]
    second_normal = Vector(segment["normals"][1]).normalized()

    def toward_panel(face: gate1.ObjFace, normal: Vector) -> Vector:
        direction = face_centroid(face, points) - p0.lerp(p1, 0.5)
        direction -= tangent * direction.dot(tangent)
        direction -= normal * direction.dot(normal)
        if direction.length < 0.01:
            raise ValueError(f"{name}: cannot orient internal panel rib")
        return direction.normalized()

    toward_second = toward_panel(second_face, second_normal)
    wall = float(config["shell_wall_thickness_mm"])
    shell_overlap = float(ribs["shell_overlap_mm"])
    foot_width = float(ribs["foot_width_mm"])
    rib_height = float(ribs["rib_height_mm"])
    edge_inset = float(ribs["edge_inset_mm"])
    wall_depth = wall - shell_overlap
    requested_recess = float(ribs["minimum_exterior_recess_mm"])
    if wall_depth < requested_recess:
        raise ValueError(f"{name}: triangular rib foot is too near the exterior")

    def create_panel_wedge(
        suffix: str, normal: Vector, toward_face: Vector
    ) -> bpy.types.Object:
        def triangle_at(edge_point: Vector) -> tuple[Vector, Vector, Vector]:
            return (
                edge_point
                + toward_face * edge_inset
                - normal * wall_depth,
                edge_point
                + toward_face * (edge_inset + foot_width)
                - normal * wall_depth,
                edge_point
                + toward_face * (edge_inset + foot_width)
                - normal * (wall + rib_height),
            )

        wedge = triangular_prism(
            f"{name}_{suffix}", triangle_at(start), triangle_at(end), rib_material
        )
        require_manifold(wedge, f"{name} {suffix} triangular wedge")
        return wedge

    wedge = create_panel_wedge("reinforcement", second_normal, toward_second)
    minimum_exterior_recess = wall_depth
    if minimum_exterior_recess + 1e-6 < requested_recess:
        raise ValueError(f"{name}: triangular rib does not clear the exterior")
    return section, [wedge], {
        "name": name,
        "section": section,
        "source_faces": segment["face_groups"],
        "source_panels": segment["source_panels"],
        "length_mm": round(length, 3),
        "cross_section": "triangular",
        "wedge_count": 1,
        "attachment_source_face": second_face.group,
        "attachment_source_panel": segment["source_panels"][1],
        "foot_width_mm": foot_width,
        "rib_height_mm": rib_height,
        "minimum_exterior_recess_mm": round(minimum_exterior_recess, 3),
        "interior_shift_mm": 0.0,
        "integral_to_section_shell": True,
    }


def metrics(obj: bpy.types.Object, config: dict[str, Any]) -> dict[str, Any]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    nonmanifold = sum(1 for edge in bm.edges if not edge.is_manifold)
    volume = abs(bm.calc_volume(signed=True))
    bm.free()
    points = [tuple(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices]
    return {
        "vertices": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "connected_components": len(components(obj)),
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "volume_mm3": round(volume, 3),
        "estimated_asa_mass_g": round(volume / 1000.0 * 1.07, 2),
        "orientation_search": gate2.best_fit(
            points,
            config["printer_envelope_mm"],
            int(config["orientation_step_degrees"]),
        ),
    }


def export_stl(obj: bpy.types.Object, path: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(
        filepath=str(path), export_selected_objects=True, ascii_format=False
    )
    obj.select_set(False)


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    model, assignments, scale, origin = transformed_source()
    points, segments = seam_segments(model, assignments, scale, origin)
    minimum = float(config["joint_system"]["minimum_usable_seam_edge_mm"])
    usable = [segment for segment in segments if segment["length_mm"] >= minimum]
    excluded = {
        tuple(value) for value in config.get("excluded_joint_face_pairs", [])
    }
    usable = [
        segment for segment in usable
        if tuple(segment["face_groups"]) not in excluded
    ]
    audit = seam_report(segments, minimum)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "gate5-seam-audit.json").write_text(
        json.dumps({"gate": "Gate 5 seam audit", "seams": audit}, indent=2)
        + chr(10),
        encoding="utf-8",
    )

    bpy.ops.wm.open_mainfile(filepath=str(GATE3_BLEND))
    shells = {name: bpy.data.objects[name] for name in gate2.SECTION_ORDER}
    baseline_volumes = {name: mesh_volume(obj) for name, obj in shells.items()}
    rim_material = material("Gate5_rear_service_rim", (0.16, 0.32, 0.38, 1.0))
    flange_material = material(
        "Gate5_internal_flange_tabs", (0.95, 0.58, 0.08, 1.0)
    )
    rib_material = material(
        "Gate5_internal_panel_ribs", (0.72, 0.12, 0.08, 1.0)
    )
    rear_service_result = cut_rear_service_opening_and_add_rim(
        shells["rear_base"], config, rim_material
    )

    allocations = distribute_modules(
        usable, float(config["joint_system"]["module_max_spacing_mm"])
    )
    pair_counts: dict[str, int] = defaultdict(int)
    joint_tasks = []
    for segment, fraction, allocation_count in allocations:
        pair = "__".join(segment["sections"])
        pair_counts[pair] += 1
        name = f"internal_flange_tab_{pair}_{pair_counts[pair]:02d}"
        joint_tasks.append((name, segment, fraction, allocation_count))

    joint_records = []
    tabs_by_section: dict[str, list[bpy.types.Object]] = defaultdict(list)
    for name, segment, fraction, allocation_count in joint_tasks:
        tabs, record = create_internal_flange_tabs(
            name,
            segment,
            fraction,
            allocation_count,
            model,
            points,
            config,
            flange_material,
        )
        for section, tab in tabs.items():
            tabs_by_section[section].append(tab)
        joint_records.append(record)

    expected_component_counts: dict[str, int] = {}
    for section, tab_parts in sorted(tabs_by_section.items()):
        for tab_index, tab in enumerate(tab_parts, start=1):
            apply_boolean(shells[section], tab, "UNION")
            require_manifold(
                shells[section], f"{section} flange-tab union {tab_index}"
            )
        expected_components = expected_component_counts.get(section, 1)
        if len(components(shells[section])) != expected_components:
            raise ValueError(
                f"Flange-tab union changed {section} to "
                f"{len(components(shells[section]))} components; expected "
                f"{expected_components}"
            )

    rib_settings = config["internal_panel_ribs"]
    target_rib_sections = set(rib_settings["target_sections"])
    internal_rib_segments = internal_panel_segments(
        model, assignments, points, target_rib_sections
    )
    ribs_by_section: dict[str, list[bpy.types.Object]] = defaultdict(list)
    rib_counts: dict[str, int] = defaultdict(int)
    rib_records = []
    for segment in internal_rib_segments:
        section = segment["section"]
        rib_counts[section] += 1
        name = f"internal_panel_rib_{section}_{rib_counts[section]:02d}"
        section, rib_parts, record = create_internal_panel_rib(
            name, segment, model, points, config, rib_material
        )
        ribs_by_section[section].extend(rib_parts)
        rib_records.append(record)
    missing_rib_sections = target_rib_sections - set(ribs_by_section)
    if missing_rib_sections:
        raise ValueError(
            "No internal panel ribs were generated for requested sections: "
            f"{sorted(missing_rib_sections)}"
        )

    for section, rib_parts in sorted(ribs_by_section.items()):
        for rib_index, rib in enumerate(rib_parts, start=1):
            apply_boolean(shells[section], rib, "UNION")
            require_manifold(
                shells[section], f"{section} triangular-rib union {rib_index}"
            )
        if len(components(shells[section])) != 1:
            raise ValueError(
                f"Triangular-rib union changed {section} to "
                f"{len(components(shells[section]))} components"
            )

    shell_metrics = {name: metrics(obj, config) for name, obj in shells.items()}
    minimum_volume_ratio = float(
        config["validation"]["minimum_shell_volume_ratio_vs_gate3"]
    )
    for name, value in shell_metrics.items():
        volume_ratio = value["volume_mm3"] / baseline_volumes[name]
        if volume_ratio < minimum_volume_ratio:
            raise ValueError(
                f"{name}: final volume ratio {volume_ratio:.3f} is below the "
                f"{minimum_volume_ratio:.3f} Gate 3 baseline limit"
            )
        value["volume_ratio_to_gate3_baseline"] = round(volume_ratio, 4)
    shell_dir, joiner_dir = OUTPUT_DIR / "shells", OUTPUT_DIR / "joiners"
    shell_dir.mkdir(exist_ok=True)
    joiner_dir.mkdir(exist_ok=True)
    for directory in (shell_dir, joiner_dir):
        for stale in directory.glob("*.stl"):
            stale.unlink()
    for name, obj in shells.items():
        export_stl(obj, shell_dir / f"{name}.stl")

    all_objects = list(shells.values())
    bpy.ops.object.select_all(action="DESELECT")
    for obj in all_objects:
        obj.select_set(True)
    bpy.ops.wm.stl_export(
        filepath=str(OUTPUT_DIR / "gate5-internal-flange-tabs-review.stl"),
        export_selected_objects=True,
        ascii_format=False,
    )
    bpy.ops.export_scene.gltf(
        filepath=str(OUTPUT_DIR / "gate5-internal-flange-tabs-review.glb"),
        export_format="GLB",
        use_selection=True,
    )
    bpy.ops.wm.save_as_mainfile(
        filepath=str(OUTPUT_DIR / "gate5-internal-flange-tabs-review.blend")
    )
    backup = OUTPUT_DIR / "gate5-internal-flange-tabs-review.blend1"
    if backup.exists():
        backup.unlink()
    for stale_name in (
        "gate5-jointed-assembly-review.stl",
        "gate5-jointed-assembly-review.glb",
        "gate5-jointed-assembly-review.blend",
        "gate5-jointed-assembly-review.blend1",
        "gate5-integrated-frame-review.stl",
        "gate5-integrated-frame-review.glb",
        "gate5-integrated-frame-review.blend",
        "gate5-integrated-frame-review.blend1",
    ):
        stale = OUTPUT_DIR / stale_name
        if stale.exists():
            stale.unlink()

    all_metrics = list(shell_metrics.values())
    printed_mass = sum(value["estimated_asa_mass_g"] for value in all_metrics)
    minimum_recorded_skin = min(
        value["minimum_exterior_skin_mm"] for value in joint_records
    )
    report = {
        "gate": "Gate 5 internal flange tabs, hidden joints, and internal panel ribs",
        "status": "review_required",
        "seams": audit,
        "reinforcement_ribs": {
            "integral_triangular_rib_count": len(rib_records),
            "triangular_wedge_prism_count": sum(
                value["wedge_count"] for value in rib_records
            ),
            "eligible_internal_panel_connection_count": len(internal_rib_segments),
            "target_sections": sorted(target_rib_sections),
            "ribs_by_section": dict(sorted(rib_counts.items())),
            "cross_section": rib_settings["cross_section"],
            "foot_width_mm": float(rib_settings["foot_width_mm"]),
            "rib_height_mm": float(rib_settings["rib_height_mm"]),
            "total_length_mm": round(
                sum(value["length_mm"] for value in rib_records), 3
            ),
            "status": "Every source-panel connection internal to the four requested body shells is reinforced; inter-shell flange seams, outer edges, rear base, and ears are excluded."
        },
        "rear_service_opening_and_rim": rear_service_result,
        "flange_tab_module_count": len(joint_records),
        "flange_tab_modules_by_pair": dict(sorted(pair_counts.items())),
        "internal_m3_screw_count": sum(
            value["internal_m3_screws"] for value in joint_records
        ),
        "captive_m3_square_nut_count": sum(
            value["captive_square_nuts"] for value in joint_records
        ),
        "loose_m3_nyloc_nut_count": sum(
            value["loose_m3_nyloc_nuts"] for value in joint_records
        ),
        "alignment_dowel_count": sum(
            value["alignment_dowels"] for value in joint_records
        ),
        "separate_printed_joiner_count": 0,
        "exterior_fastener_hole_count": sum(
            value["exterior_fastener_holes"] for value in joint_records
        ),
        "minimum_hidden_hardware_exterior_skin_mm": round(
            minimum_recorded_skin, 3
        ),
        "estimated_printed_asa_mass_g": round(printed_mass, 2),
        "hardware": config["fasteners"],
        "shells": shell_metrics,
        "flange_tab_manifest": joint_records,
        "integral_internal_panel_rib_manifest": rib_records,
        "acceptance": {
            "all_seven_shells_single_connected_solids": all(
                value["connected_components"] == 1
                for value in shell_metrics.values()
            ),
            "all_shells_closed_manifold": all(
                value["boundary_edges"] == 0 and value["nonmanifold_edges"] == 0
                for value in shell_metrics.values()
            ),
            "all_shells_retain_gate3_baseline_volume": all(
                value["volume_ratio_to_gate3_baseline"]
                >= minimum_volume_ratio
                for value in shell_metrics.values()
            ),
            "all_flange_tabs_retain_load_spreading_body": all(
                value["integrated_flange_tabs_valid"]
                for value in joint_records
            ),
            "all_joints_use_internal_fasteners": all(
                value["internal_tool_access_required"]
                and value["exterior_fastener_holes"] == 0
                for value in joint_records
            ),
            "hidden_hardware_preserves_minimum_exterior_skin": (
                minimum_recorded_skin
                >= float(
                    config["validation"][
                        "minimum_hidden_hardware_exterior_skin_mm"
                    ]
                )
            ),
            "no_separate_printed_joiners": not any(joiner_dir.glob("*.stl")),
            "all_integral_triangular_ribs_recessed_from_exterior": bool(rib_records) and all(
                value["minimum_exterior_recess_mm"]
                >= float(rib_settings["minimum_exterior_recess_mm"])
                for value in rib_records
            ),
            "every_eligible_internal_panel_connection_reinforced": (
                len(rib_records) == len(internal_rib_segments)
            ),
            "ribs_confined_to_requested_body_shells": (
                set(value["section"] for value in rib_records)
                == target_rib_sections
            ),
            "no_inter_shell_or_outer_edge_ribs": True,
            "all_flange_tabs_recessed_from_exterior": all(
                value["minimum_tab_exterior_recess_mm"]
                >= float(config["joint_system"]["minimum_tab_exterior_recess_mm"])
                for value in joint_records
            ),
            "all_flange_pairs_are_matching_plain_rectangles": all(
                value["tabs_are_matching_plain_rectangles"]
                for value in joint_records
            ),
            "eye_island_reinforcement_deferred": True,
            "rear_service_opening_and_rim_integrated": rear_service_result[
                "connected_after_rim"
            ],
            "all_parts_fit_orientation_search": all(
                value["orientation_search"]["fits"] for value in all_metrics
            ),
            "rear_connector_flange_deferred": True,
        },
        "validation_thresholds": config["validation"],
        "deferred": config["deferred"],
        "review_notes": config["review_notes"],
    }
    (OUTPUT_DIR / "gate5-validation-report.json").write_text(
        json.dumps(report, indent=2) + chr(10), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
