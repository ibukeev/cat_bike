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
import print_topology_policy as topology_policy  # noqa: E402

PACKAGE_ROOT = SCRIPT_DIR.parent
GATE2_CONFIG = PACKAGE_ROOT / "config/gate2-section-layout.json"
GATE3_CONFIG = PACKAGE_ROOT / "config/gate3-structural-shells.json"
GATE3_BLEND = PACKAGE_ROOT / "output/10-design-gates/gate3-structural-shells/gate3-structural-shells.blend"
CONFIG_PATH = PACKAGE_ROOT / "config/gate5-ribs-and-joints.json"
OUTPUT_DIR = PACKAGE_ROOT / "output/10-design-gates/gate5-ribs-and-joints"


def transformed_source() -> tuple[gate1.ObjModel, list[str], float, gate1.Point]:
    gate1_config = json.loads(gate1.DEFAULT_CONFIG.read_text(encoding="utf-8"))
    gate2_config = json.loads(GATE2_CONFIG.read_text(encoding="utf-8"))
    source = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    units = gate1.panel_units(source, gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV))
    scale, origin, _ = gate1.make_transform(
        gate1.bounds(source.vertices), float(gate1_config["target_height_mm"])
    )
    roles, _ = gate1.build_roles(units, gate1_config, scale)
    model = gate2.subdivide_center_panels(source, gate2_config)
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
    """Return one gusset side for each panel bordering an internal source edge."""
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
        face_indices = [first_index, second_index]
        face_groups = [first_face.group, second_face.group]
        source_panels = [first_panel, second_panel]
        normals = [
            list(outward_normal(first_face, points)),
            list(outward_normal(second_face, points)),
        ]
        for attachment_offset in (0, 1):
            output.append(
                {
                    "section": section,
                    "face_indices": face_indices,
                    "face_groups": face_groups,
                    "source_panels": source_panels,
                    "attachment_face_index": face_indices[attachment_offset],
                    "attachment_face_group": face_groups[attachment_offset],
                    "attachment_source_panel": source_panels[attachment_offset],
                    "attachment_normal": normals[attachment_offset],
                    "attachment_offset": attachment_offset,
                    "vertex_indices": list(edge),
                    "p0": list(p0),
                    "p1": list(p1),
                    "length_mm": (p1 - p0).length,
                }
            )
    output.sort(
        key=lambda value: (
            value["section"],
            value["attachment_offset"] == 0,
            -value["length_mm"],
            value["attachment_face_group"],
        )
    )
    return output


def panel_rib_profile(
    segment: dict[str, Any], ribs: dict[str, Any]
) -> tuple[float, float, float, str]:
    """Return the main or compact opposite-panel gusset profile."""
    if segment["attachment_offset"] == 0:
        supplementary = ribs["supplementary_panel_side"]
        return (
            float(supplementary["foot_width_mm"]),
            float(supplementary["rib_height_mm"]),
            float(supplementary["edge_inset_mm"]),
            "supplementary",
        )
    return (
        float(ribs["foot_width_mm"]),
        float(ribs["rib_height_mm"]),
        float(ribs["edge_inset_mm"]),
        "main",
    )


def internal_gusset_junctions(
    model: gate1.ObjModel,
    segments: list[dict[str, Any]],
    points: list[Vector],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Find every internal source vertex shared by two or more main gussets."""
    at_vertex: dict[tuple[str, int], list[int]] = defaultdict(list)
    for segment_index, segment in enumerate(segments):
        if segment["attachment_offset"] != 1:
            continue
        first, second = segment["vertex_indices"]
        at_vertex[(segment["section"], first)].append(segment_index)
        at_vertex[(segment["section"], second)].append(segment_index)

    output = []
    for (section, vertex_index), segment_indices in sorted(at_vertex.items()):
        if len(segment_indices) < 2:
            continue
        output.append(
            {
                "section": section,
                "vertex_index": vertex_index,
                "rib_segment_indices": segment_indices,
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


def convex_hull_points(
    name: str,
    point_values: list[Vector],
    assigned_material: bpy.types.Material | None = None,
) -> bpy.types.Object:
    """Create one closed triangulated convex hub from an internal point cloud."""
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata([tuple(value) for value in point_values], [], [])
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.convex_hull(
        delete_unused=True,
        use_existing_faces=False,
        make_holes=False,
        join_triangles=True,
    )
    bpy.ops.object.mode_set(mode="OBJECT")
    if assigned_material:
        obj.data.materials.append(assigned_material)
    obj.select_set(False)
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


def apply_boolean(
    target: bpy.types.Object,
    tool: bpy.types.Object,
    operation: str,
    solver: str = "EXACT",
) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    bpy.context.view_layer.objects.active = target
    target.select_set(True)
    modifier = target.modifiers.new(f"{operation}_{tool.name}", "BOOLEAN")
    modifier.operation = operation
    modifier.solver = solver
    modifier.object = tool
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(tool, do_unlink=True)
    target.select_set(False)


def join_closed_overlapping_mesh(
    target: bpy.types.Object, tool: bpy.types.Object
) -> None:
    """Keep two watertight meshes in one STL without a fragile CAD boolean."""
    bpy.ops.object.select_all(action="DESELECT")
    target.select_set(True)
    tool.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()
    target.name = target.name
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
    segments: list[dict[str, Any]],
    max_spacing: float,
    ear_minimum_count: int = 1,
) -> list[tuple[dict[str, Any], float, int]]:
    output = []
    for segment in segments:
        count = max(1, math.ceil(segment["length_mm"] / (2.0 * max_spacing)))
        if any(section.endswith("_ear") for section in segment["sections"]):
            count = max(count, ear_minimum_count)
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


def trapezoid_prism_cutter(
    name: str, frame: dict[str, Any], side: str
) -> bpy.types.Object:
    """Create a through-cut prism for the compact rear service aperture."""
    center_x = float(frame["center_x_mm"])
    center_y = float(frame["center_y_mm"])
    center_z = float(frame["center_z_mm"])
    depth = float(frame["cut_depth_mm"])
    top_width = float(frame["opening_top_width_mm"])
    bottom_width = float(frame["opening_bottom_width_mm"])
    height = float(frame["opening_height_mm"])
    top_z = center_z + height / 2.0
    bottom_z = center_z - height / 2.0
    front_y = center_y - depth / 2.0
    rear_y = center_y + depth / 2.0
    center_spine = float(frame["center_spine_width_mm"])
    if side == "left":
        profile = (
            (center_x - top_width / 2.0, top_z),
            (center_x - center_spine / 2.0, top_z),
            (center_x - center_spine / 2.0, bottom_z),
            (center_x - bottom_width / 2.0, bottom_z),
        )
    elif side == "right":
        profile = (
            (center_x + center_spine / 2.0, top_z),
            (center_x + top_width / 2.0, top_z),
            (center_x + bottom_width / 2.0, bottom_z),
            (center_x + center_spine / 2.0, bottom_z),
        )
    else:
        raise ValueError(f"Unsupported compact rear aperture side: {side}")
    vertices = [
        (x, front_y, z) for x, z in profile
    ] + [
        (x, rear_y, z) for x, z in profile
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
    cutter = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(cutter)
    return cutter


def cut_compact_rear_service_aperture(
    shells: dict[str, bpy.types.Object], config: dict[str, Any]
) -> dict[str, Any]:
    """Open the trapezoidal rear service aperture through both lower shells."""
    frame = config["compact_rear_service_frame"]
    hosts = list(frame["host_sections"])
    for section in hosts:
        component_count_before = len(components(shells[section]))
        side = "left" if section.startswith("left_") else "right"
        cutter = trapezoid_prism_cutter(
            f"compact_rear_service_aperture_{section}", frame, side
        )
        apply_boolean(shells[section], cutter, "DIFFERENCE", solver="MANIFOLD")
        require_manifold(shells[section], f"{section} compact rear service cut")
        if len(components(shells[section])) != component_count_before:
            raise ValueError(
                f"{section}: compact rear service cut changed component count"
            )
    return {
        "shape": "trapezoid",
        "opening_top_width_mm": float(frame["opening_top_width_mm"]),
        "opening_bottom_width_mm": float(frame["opening_bottom_width_mm"]),
        "opening_height_mm": float(frame["opening_height_mm"]),
        "center_spine_width_mm": float(frame["center_spine_width_mm"]),
        "host_sections": hosts,
        "old_rectangular_rim_and_tie_rails_removed": True,
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
            float(joint.get("ear_module_length_mm", joint["module_length_mm"])),
            float(segment["length_mm"]) * 0.90 / allocation_count,
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



def rear_base_inward_direction(frame: dict[str, Any]) -> Vector:
    """Return the inward normal of the sloped procedural rear-base plane."""
    vertical = Vector((
        0.0,
        float(frame["outer_top_y_mm"]) - float(frame["outer_bottom_y_mm"]),
        float(frame["outer_top_z_mm"]) - float(frame["outer_bottom_z_mm"]),
    )).normalized()
    outward = vertical.cross(Vector((1.0, 0.0, 0.0))).normalized()
    return -outward


def rear_base_inner_profile(frame: dict[str, Any]) -> list[Vector]:
    """Return the four inner-opening corners on the rear-frame plane."""
    top_y = float(frame["outer_top_y_mm"])
    top_z = float(frame["outer_top_z_mm"])
    bottom_y = float(frame["outer_bottom_y_mm"])
    bottom_z = float(frame["outer_bottom_z_mm"])
    top_width = float(frame["outer_top_width_mm"])
    bottom_width = float(frame["outer_bottom_width_mm"])
    rail = float(frame["rail_width_mm"])
    height = top_z - bottom_z

    def plane_y(z: float) -> float:
        return bottom_y + (z - bottom_z) * (top_y - bottom_y) / height

    inner_top_z = top_z - rail
    inner_bottom_z = bottom_z + rail
    return [
        Vector((-(top_width - 2.0 * rail) / 2.0, plane_y(inner_top_z), inner_top_z)),
        Vector(((top_width - 2.0 * rail) / 2.0, plane_y(inner_top_z), inner_top_z)),
        Vector(((bottom_width - 2.0 * rail) / 2.0, plane_y(inner_bottom_z), inner_bottom_z)),
        Vector((-(bottom_width - 2.0 * rail) / 2.0, plane_y(inner_bottom_z), inner_bottom_z)),
    ]


def rear_base_bore_length(
    seam_point: Vector, bolt_axis: Vector, frame: dict[str, Any]
) -> float:
    """Measure from an outer rear-frame seam to its actual inner opening edge."""
    bottom_origin = Vector((
        0.0,
        float(frame["outer_bottom_y_mm"]),
        float(frame["outer_bottom_z_mm"]),
    ))
    vertical = Vector((
        0.0,
        float(frame["outer_top_y_mm"]) - float(frame["outer_bottom_y_mm"]),
        float(frame["outer_top_z_mm"]) - float(frame["outer_bottom_z_mm"]),
    )).normalized()
    horizontal = Vector((1.0, 0.0, 0.0))

    def projected(point: Vector) -> Vector:
        delta = point - bottom_origin
        return Vector((delta.dot(horizontal), delta.dot(vertical)))

    def cross_2d(first: Vector, second: Vector) -> float:
        return first.x * second.y - first.y * second.x

    origin_2d = projected(seam_point)
    direction_2d = Vector((bolt_axis.dot(horizontal), bolt_axis.dot(vertical)))
    inner = [projected(point) for point in rear_base_inner_profile(frame)]
    hits = []
    for index, first in enumerate(inner):
        second = inner[(index + 1) % len(inner)]
        edge = second - first
        denominator = cross_2d(direction_2d, edge)
        if abs(denominator) < 1e-8:
            continue
        offset = first - origin_2d
        distance = cross_2d(offset, edge) / denominator
        edge_fraction = cross_2d(offset, direction_2d) / denominator
        if distance > 0.0 and -1e-6 <= edge_fraction <= 1.0 + 1e-6:
            hits.append(distance)
    if not hits:
        raise ValueError("Rear-base M3 path did not reach the inner opening")
    return min(hits)


def create_rear_base_connection_rail(
    name: str,
    connection: dict[str, Any],
    config: dict[str, Any],
    rear_frame: dict[str, Any],
    rear_base: bpy.types.Object,
    flange_material: bpy.types.Material,
) -> tuple[str, bpy.types.Object, list[dict[str, Any]]]:
    """Create one continuous shell rail and its M3 paths through the rear frame."""
    joint = config["joint_system"]
    rear_values = config["rear_base_flange_connections"]
    validation = config["validation"]
    section = str(connection["section"])
    p0 = Vector(connection["p0_mm"])
    p1 = Vector(connection["p1_mm"])
    tangent = (p1 - p0).normalized()
    segment_length = (p1 - p0).length
    end_setback = float(connection["rail_end_setback_mm"])
    rail_length = segment_length - 2.0 * end_setback
    if rail_length <= 4.0:
        raise ValueError(f"{name}: rear connector rail is too short")

    inward = rear_base_inward_direction(rear_frame)
    bolt_axis = inward.cross(tangent).normalized()
    frame_center = Vector(config["rear_base_flange_connections"]["frame_center_mm"])
    seam_center = p0.lerp(p1, 0.5)
    toward_frame = frame_center - seam_center
    toward_frame -= tangent * toward_frame.dot(tangent)
    toward_frame -= inward * toward_frame.dot(inward)
    if toward_frame.length < 0.01:
        raise ValueError(f"{name}: cannot determine frame-side rail direction")
    if bolt_axis.dot(toward_frame) < 0.0:
        bolt_axis.negate()

    tab_thickness = float(
        rear_values.get(
            "flange_tab_thickness_mm",
            joint["flange_tab_thickness_mm"],
        )
    )
    tab_depth = float(
        rear_values.get("flange_tab_depth_mm", joint["flange_tab_depth_mm"])
    )
    clearance = float(
        rear_values.get(
            "flange_face_clearance_mm",
            joint["flange_face_clearance_mm"],
        )
    )
    wall = float(config["shell_wall_thickness_mm"])
    root_overlap = float(
        rear_values.get(
            "flange_shell_overlap_mm",
            joint["flange_shell_overlap_mm"],
        )
    )
    cut_extension = float(joint["boolean_cut_extension_mm"])
    tab_depth_center = wall + tab_depth / 2.0 - root_overlap
    face_offset = tab_thickness / 2.0 + clearance / 2.0
    rail_center = (
        seam_center + inward * tab_depth_center - bolt_axis * face_offset
    )
    rail = box(
        name,
        rail_center,
        (tangent, bolt_axis, inward),
        (rail_length, tab_thickness, tab_depth),
        flange_material,
    )
    initial_volume = mesh_volume(rail)
    module_data = []
    fractions = list(connection["fractions"])
    if not fractions:
        raise ValueError(f"{name}: no rear-base M3 positions configured")
    for module_index, fraction in enumerate(fractions, start=1):
        seam_point = p0.lerp(p1, float(fraction))
        fastener_center = (
            seam_point
            + inward * (tab_depth_center + tab_depth * 0.20)
        )
        axis_distances = [
            ((rail.matrix_world @ vertex.co) - fastener_center).dot(bolt_axis)
            for vertex in rail.data.vertices
        ]
        rail_hole = cylinder(
            f"{name}_m3_{module_index}",
            fastener_center + bolt_axis * (min(axis_distances) - cut_extension),
            fastener_center + bolt_axis * (max(axis_distances) + cut_extension),
            float(joint["m3_clearance_diameter_mm"]),
        )
        apply_boolean(rail, rail_hole, "DIFFERENCE")
        require_manifold(rail, f"{name} rail M3 cut {module_index}")

        bore_length = rear_base_bore_length(seam_point, bolt_axis, rear_frame)
        rear_bore = cylinder(
            f"{name}_rear_base_internal_m3_bore_{module_index}",
            fastener_center + bolt_axis * (min(axis_distances) - cut_extension),
            fastener_center + bolt_axis * (bore_length + cut_extension),
            float(joint["m3_clearance_diameter_mm"]),
        )
        apply_boolean(rear_base, rear_bore, "DIFFERENCE", solver="MANIFOLD")
        require_manifold(rear_base, f"{name} rear-base M3 bore {module_index}")
        module_data.append((module_index, bore_length))

    final_volume = mesh_volume(rail)
    retained_ratio = final_volume / initial_volume
    minimum_ratio = float(validation["minimum_flange_retained_volume_ratio"])
    maximum_ratio = float(validation["maximum_flange_retained_volume_ratio"])
    if not minimum_ratio <= retained_ratio <= maximum_ratio:
        raise ValueError(
            f"{name}: connector rail retained ratio {retained_ratio:.3f} is "
            f"outside {minimum_ratio:.3f}..{maximum_ratio:.3f}"
        )
    if len(components(rail)) != 1:
        raise ValueError(f"{name}: connector rail split after M3 cuts")
    projected_ratio = projected_extent(rail, tangent) / rail_length
    if projected_ratio < float(validation["minimum_flange_projected_length_ratio"]):
        raise ValueError(f"{name}: connector rail projected length is below the limit")

    minimum_recess = wall - root_overlap
    requested_recess = float(
        config["rear_base_flange_connections"]
        ["minimum_tab_exterior_recess_mm"]
    )
    if minimum_recess < requested_recess:
        raise ValueError(f"{name}: connector rail does not clear the exterior")
    records = []
    for module_index, bore_length in module_data:
        records.append({
            "name": f"{name}_path_{module_index:02d}",
            "sections": ["rear_base", section],
            "owner": "rear_base",
            "receiver": section,
            "source_faces": ["procedural_rear_base_perimeter"],
            "connector_rail_length_mm": round(rail_length, 3),
            "connector_rail_end_setback_mm": end_setback,
            "flange_tab_depth_mm": tab_depth,
            "flange_tab_thickness_mm": tab_thickness,
            "flange_face_clearance_mm": clearance,
            "internal_m3_screws": 1,
            "captive_square_nuts": 0,
            "loose_m3_nyloc_nuts": 1,
            "alignment_dowels": 0,
            "exterior_fastener_holes": 0,
            "minimum_exterior_skin_mm": round(wall, 3),
            "minimum_tab_exterior_recess_mm": round(minimum_recess, 3),
            "fastener_axis": [round(value, 4) for value in bolt_axis],
            "fastener_axis_uses_shared_interior_bisector": False,
            "tabs_are_matching_plain_rectangles": False,
            "receiver_tab_retained_volume_ratio": round(retained_ratio, 4),
            "integrated_flange_tabs_valid": True,
            "internal_tool_access_required": True,
            "procedural_rear_base_attachment": True,
            "continuous_rear_base_connector_rail": True,
            "isolated_opening_tab": False,
            "rear_base_internal_bore": True,
            "rear_base_bore_length_mm": round(bore_length, 3),
        })
    return section, rail, records


def create_rear_loaded_base_pads(
    name: str,
    connection: dict[str, Any],
    config: dict[str, Any],
    rear_frame: dict[str, Any],
    rear_base: bpy.types.Object,
    flange_material: bpy.types.Material,
) -> tuple[str, list[bpy.types.Object], list[dict[str, Any]]]:
    """Create large rear-normal M5 pads that never undercut base insertion."""
    values = config["rear_base_flange_connections"]
    validation = config["validation"]
    section = str(connection["section"])
    p0 = Vector(connection["p0_mm"])
    p1 = Vector(connection["p1_mm"])
    tangent = (p1 - p0).normalized()
    inward = rear_base_inward_direction(rear_frame)
    outward = -inward
    frame_center = Vector(values["frame_center_mm"])
    seam_center = p0.lerp(p1, 0.5)
    toward_frame = frame_center - seam_center
    toward_frame -= tangent * toward_frame.dot(tangent)
    toward_frame -= inward * toward_frame.dot(inward)
    if toward_frame.length < 0.01:
        raise ValueError(f"{name}: cannot determine rear-frame radial direction")
    toward_frame.normalize()

    pad_length = float(values["pad_tangent_length_mm"])
    pad_width = float(values["pad_radial_width_mm"])
    pad_depth = float(values["pad_depth_mm"])
    pad_recess = float(values["pad_minimum_exterior_recess_mm"])
    fastener_inset = float(values["pad_fastener_inset_from_outer_edge_mm"])
    pad_center_inset = float(values["pad_center_inset_from_outer_edge_mm"])
    hole_diameter = float(values["m5_clearance_diameter_mm"])
    tool_envelope = float(values["minimum_nut_tool_envelope_diameter_mm"])
    frame_depth = float(
        rear_frame.get("frame_depth_mm", rear_frame.get("inward_depth_mm", 0.0))
    )
    if rear_frame.get("depth_direction", "inward") != "outward":
        raise ValueError("Rear-loaded base pads require an outward rear frame")
    tangent_tool_clearance = pad_length / 2.0 - tool_envelope / 2.0
    radial_tool_clearance = (
        pad_width / 2.0
        - abs(fastener_inset - pad_center_inset)
        - tool_envelope / 2.0
    )
    tool_edge_clearance = min(tangent_tool_clearance, radial_tool_clearance)
    if tool_edge_clearance < 6.0:
        raise ValueError(f"{name}: nut/tool envelope lacks 6 mm pad edge clearance")

    pads = []
    records = []
    for index, fraction in enumerate(connection["fractions"], start=1):
        seam_point = p0.lerp(p1, float(fraction))
        fastener_center = seam_point + toward_frame * fastener_inset
        pad_center = (
            seam_point
            + toward_frame * pad_center_inset
            + inward * (pad_recess + pad_depth / 2.0)
        )
        pad = box(
            f"{name}_pad_{index:02d}",
            pad_center,
            (tangent, toward_frame, inward),
            (pad_length, pad_width, pad_depth),
            flange_material,
        )
        initial_volume = mesh_volume(pad)
        pad_hole = cylinder(
            f"{name}_pad_m5_{index:02d}",
            fastener_center + outward * 2.0,
            fastener_center + inward * (pad_recess + pad_depth + 2.0),
            hole_diameter,
        )
        apply_boolean(pad, pad_hole, "DIFFERENCE", solver="MANIFOLD")
        require_manifold(pad, f"{name} large pad M5 cut {index}")
        retained_ratio = mesh_volume(pad) / initial_volume
        if retained_ratio < float(validation["minimum_flange_retained_volume_ratio"]):
            raise ValueError(f"{name}: rear pad retained ratio is too low")

        base_hole = cylinder(
            f"{name}_rear_base_m5_{index:02d}",
            fastener_center + outward * (frame_depth + 2.0),
            fastener_center + inward * 2.0,
            hole_diameter,
        )
        apply_boolean(rear_base, base_hole, "DIFFERENCE", solver="MANIFOLD")
        require_manifold(rear_base, f"{name} rear-loaded base M5 cut {index}")
        pads.append(pad)
        records.append({
            "name": f"{name}_path_{index:02d}",
            "sections": ["rear_base", section],
            "owner": "rear_base",
            "receiver": section,
            "source_faces": ["procedural_rear_base_perimeter"],
            "fastener_center_mm": [round(value, 4) for value in fastener_center],
            "pad_dimensions_mm": [pad_length, pad_width, pad_depth],
            "nut_tool_envelope_diameter_mm": tool_envelope,
            "nut_tool_envelope_edge_clearance_mm": round(tool_edge_clearance, 3),
            "rear_m5_screws": 1,
            "internal_m3_screws": 0,
            "captive_square_nuts": 0,
            "loose_m3_nyloc_nuts": 0,
            "alignment_dowels": 0,
            "exterior_fastener_holes": 1,
            "minimum_exterior_skin_mm": round(pad_recess, 3),
            "minimum_tab_exterior_recess_mm": round(pad_recess, 3),
            "fastener_axis": [round(value, 4) for value in inward],
            "tabs_are_matching_plain_rectangles": False,
            "receiver_tab_retained_volume_ratio": round(retained_ratio, 4),
            "integrated_flange_tabs_valid": True,
            "internal_tool_access_required": True,
            "rear_loaded_screw_head": True,
            "procedural_rear_base_attachment": True,
            "continuous_rear_base_connector_rail": False,
            "large_structural_mounting_pad": True,
            "isolated_opening_tab": False,
            "rear_base_internal_bore": True,
            "rear_base_bore_length_mm": round(frame_depth + pad_depth, 3),
        })
    return section, pads, records


def create_internal_flange_tab(
    name: str,
    module_length: float,
    tangent: Vector,
    flange_center: Vector,
    bolt_axis: Vector,
    inward: Vector,
    tab_thickness: float,
    tab_depth: float,
    flange_material: bpy.types.Material,
) -> bpy.types.Object:
    """Make one plain rectangular tab: the same shape on either shell."""
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
    ear_joint = any(section.endswith("_ear") for section in segment["sections"])
    owner_local = side_geometry(
        name, segment, owner, seam_point, tangent, model, points
    )
    receiver_local = side_geometry(
        name, segment, receiver, seam_point, tangent, model, points
    )
    tab_thickness = float(
        joint.get("ear_flange_tab_thickness_mm", joint["flange_tab_thickness_mm"])
        if ear_joint
        else joint["flange_tab_thickness_mm"]
    )
    tab_depth = float(
        joint.get("ear_flange_tab_depth_mm", joint["flange_tab_depth_mm"])
        if ear_joint
        else joint["flange_tab_depth_mm"]
    )
    clearance = float(joint["flange_face_clearance_mm"])
    wall = float(config["shell_wall_thickness_mm"])
    root_overlap = float(
        joint.get("ear_flange_shell_overlap_mm", joint["flange_shell_overlap_mm"])
        if ear_joint
        else joint["flange_shell_overlap_mm"]
    )
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
    owner_root_center = owner_center.copy()
    receiver_root_center = receiver_center.copy()

    # Recess the whole matching pair far enough that every tab vertex remains
    # inside both source-face exterior planes.  This explicitly prevents the
    # receiver-tab exposure visible in the prior owner-plane construction.
    requested_recess = float(
        joint["ear_minimum_tab_exterior_recess_mm"]
        if ear_joint
        else joint["minimum_tab_exterior_recess_mm"]
    )
    half_dimensions = (module_length / 2.0, tab_thickness / 2.0, tab_depth / 2.0)

    def maximum_outward_projection(
        center: Vector,
        normal: Vector,
        half_extents: tuple[float, float, float],
    ) -> float:
        return (
            (center - seam_point).dot(normal)
            + half_extents[0] * abs(tangent.dot(normal))
            + half_extents[1] * abs(bolt_axis.dot(normal))
            + half_extents[2] * abs(inward.dot(normal))
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
                (maximum_outward_projection(center, normal, half_dimensions) + requested_recess)
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
        tab_thickness,
        tab_depth,
        flange_material,
    )
    receiver_tab = create_internal_flange_tab(
        f"{name}_{receiver}",
        module_length,
        tangent,
        receiver_center,
        bolt_axis,
        inward,
        tab_thickness,
        tab_depth,
        flange_material,
    )
    root_web_length = float(
        joint.get("ear_flange_root_web_length_mm", joint["flange_root_web_length_mm"])
        if ear_joint
        else joint["flange_root_web_length_mm"]
    )
    root_web_thickness = float(
        joint.get("ear_flange_root_web_thickness_mm", joint["flange_root_web_thickness_mm"])
        if ear_joint
        else joint["flange_root_web_thickness_mm"]
    )
    root_web_margin = float(
        joint.get("ear_flange_root_web_end_margin_mm", joint["flange_root_web_end_margin_mm"])
        if ear_joint
        else joint["flange_root_web_end_margin_mm"]
    )
    root_web_overlap = float(
        joint.get("ear_flange_root_web_boolean_overlap_mm", joint["flange_root_web_boolean_overlap_mm"])
        if ear_joint
        else joint["flange_root_web_boolean_overlap_mm"]
    )
    solid_root_base = bool(
        joint.get(
            "solid_ear_flange_root_base"
            if ear_joint
            else "solid_flange_root_base",
            False,
        )
    )
    root_requested_recess = float(joint["minimum_root_web_exterior_recess_mm"])
    root_half_dimensions = (
        root_web_length / 2.0,
        root_web_thickness / 2.0,
        tab_depth / 2.0,
    )
    root_required_shift = 0.0
    for center in (owner_root_center, receiver_root_center):
        for normal in normals:
            inward_projection = -inward.dot(normal)
            root_required_shift = max(
                root_required_shift,
                (
                    maximum_outward_projection(center, normal, root_half_dimensions)
                    + root_requested_recess
                )
                / inward_projection,
            )
    if root_required_shift > 0.0:
        root_required_shift += 0.02
        owner_root_center += inward * root_required_shift
        receiver_root_center += inward * root_required_shift
    if root_required_shift >= required_shift:
        raise ValueError(f"{name}: hidden root anchors do not precede recessed tabs")
    root_web_offset = module_length / 2.0 - root_web_length / 2.0 - root_web_margin
    if root_web_offset <= root_web_length / 2.0:
        raise ValueError(f"{name}: flange root webs do not fit the module")
    # Extend only toward the recessed tab. This prevents a coplanar boolean
    # seam without moving the narrow shell-side roots toward the exterior.
    root_web_depth = (
        tab_depth + required_shift - root_required_shift + root_web_overlap
    )
    for label, tab, root_center, tab_center in (
        (owner, owner_tab, owner_root_center, owner_center),
        (receiver, receiver_tab, receiver_root_center, receiver_center),
    ):
        web_center = (root_center + tab_center) / 2.0 + inward * (root_web_overlap / 2.0)
        for web_number, direction in enumerate((-1.0, 1.0), start=1):
            web = box(
                f"{name}_{label}_root_web_{web_number}",
                web_center + tangent * (direction * root_web_offset),
                (tangent, bolt_axis, inward),
                (root_web_length, root_web_thickness, root_web_depth),
                flange_material,
            )
            apply_boolean(tab, web, "UNION", solver="EXACT")
        require_manifold(tab, f"{name} {label} recessed root webs")
        if len(components(tab)) != 1:
            raise ValueError(f"{name}: {label} root webs did not join the tab")
        if solid_root_base:
            bpy.ops.object.select_all(action="DESELECT")
            tab.select_set(True)
            bpy.context.view_layer.objects.active = tab
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.convex_hull(
                delete_unused=True,
                use_existing_faces=False,
                make_holes=False,
                join_triangles=True,
            )
            bpy.ops.object.mode_set(mode="OBJECT")
            tab.select_set(False)
            require_manifold(
                tab, f"{name} {label} continuous solid root base"
            )
    initial_volumes = {
        owner: mesh_volume(owner_tab),
        receiver: mesh_volume(receiver_tab),
    }
    fastener_center = (owner_center + receiver_center) / 2.0 + inward * (tab_depth * 0.20)
    screw_count = int(
        joint.get(
            "ear_fastener_count_per_module" if ear_joint
            else "body_fastener_count_per_module",
            2 if ear_joint else 1,
        )
    )
    if screw_count < 1:
        raise ValueError(f"{name}: flange module needs at least one fastener")
    if screw_count == 1:
        screw_points = [fastener_center]
    else:
        half_span = module_length * 0.28
        screw_points = [
            fastener_center
            + tangent * (-half_span + 2.0 * half_span * index / (screw_count - 1))
            for index in range(screw_count)
        ]
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
        maximum_outward_projection(center, normal, half_dimensions)
        for center in (owner_center, receiver_center)
        for normal in normals
    )
    minimum_root_web_exterior_recess = -max(
        maximum_outward_projection(center, normal, root_half_dimensions)
        for center in (owner_root_center, receiver_root_center)
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
    if solid_root_base:
        maximum_ratio = float(
            validation["maximum_solid_base_flange_retained_volume_ratio"]
        )
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
        "minimum_root_web_exterior_recess_mm": round(
            minimum_root_web_exterior_recess, 3
        ),
        "flange_root_web_count_per_tab": 2,
        "flange_root_web_length_mm": root_web_length,
        "flange_root_web_thickness_mm": root_web_thickness,
        "flange_root_is_continuous_solid_base": solid_root_base,
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
    foot_width, rib_height, edge_inset, panel_side_role = panel_rib_profile(
        segment, ribs
    )
    supplementary = ribs.get("supplementary_panel_side", {})
    end_setback = float(
        supplementary.get("end_setback_mm", ribs["end_setback_mm"])
        if panel_side_role == "supplementary"
        else ribs["end_setback_mm"]
    )
    length = (p1 - p0).length - 2.0 * end_setback
    if length <= 4.0:
        raise ValueError(f"{name}: internal panel rib is too short")
    start, end = p0 + tangent * end_setback, p1 - tangent * end_setback
    attachment_face = model.faces[segment["attachment_face_index"]]
    attachment_normal = Vector(segment["attachment_normal"]).normalized()

    def toward_panel(face: gate1.ObjFace, normal: Vector) -> Vector:
        direction = face_centroid(face, points) - p0.lerp(p1, 0.5)
        direction -= tangent * direction.dot(tangent)
        direction -= normal * direction.dot(normal)
        if direction.length < 0.01:
            raise ValueError(f"{name}: cannot orient internal panel rib")
        return direction.normalized()

    toward_attachment = toward_panel(attachment_face, attachment_normal)
    wall = float(config["shell_wall_thickness_mm"])
    shell_overlap = float(
        supplementary.get("shell_overlap_mm", ribs["shell_overlap_mm"])
        if panel_side_role == "supplementary"
        else ribs["shell_overlap_mm"]
    )
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

    wedge = create_panel_wedge(
        "reinforcement", attachment_normal, toward_attachment
    )
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
        "attachment_source_face": attachment_face.group,
        "attachment_source_panel": segment["attachment_source_panel"],
        "panel_side_role": panel_side_role,
        "foot_width_mm": foot_width,
        "rib_height_mm": rib_height,
        "minimum_exterior_recess_mm": round(minimum_exterior_recess, 3),
        "interior_shift_mm": 0.0,
        "integral_to_section_shell": True,
    }


def create_internal_gusset_junction_node(
    name: str,
    junction: dict[str, Any],
    segments: list[dict[str, Any]],
    model: gate1.ObjModel,
    points: list[Vector],
    config: dict[str, Any],
    rib_material: bpy.types.Material,
) -> tuple[str, bpy.types.Object, dict[str, Any]]:
    """Create a triangulated hub that overlaps the full end section of each rib."""
    ribs = config["internal_panel_ribs"]
    section = junction["section"]
    vertex = points[junction["vertex_index"]]
    wall = float(config["shell_wall_thickness_mm"])
    wall_depth = wall - float(ribs["shell_overlap_mm"])
    join_distance = float(ribs["end_setback_mm"]) + float(
        ribs["junction_overlap_mm"]
    )
    requested_recess = float(ribs["minimum_exterior_recess_mm"])
    if wall_depth < requested_recess:
        raise ValueError(f"{name}: junction node is too near the exterior")
    point_cloud = []
    attachment_faces = []
    outward_normals = []
    incident_rib_heights = []
    for segment_index in junction["rib_segment_indices"]:
        segment = segments[segment_index]
        foot_width, rib_height, edge_inset, _ = panel_rib_profile(segment, ribs)
        incident_rib_heights.append(rib_height)
        p0, p1 = Vector(segment["p0"]), Vector(segment["p1"])
        first_index, second_index = segment["vertex_indices"]
        if junction["vertex_index"] == first_index:
            edge_point = vertex + (p1 - p0).normalized() * join_distance
        elif junction["vertex_index"] == second_index:
            edge_point = vertex + (p0 - p1).normalized() * join_distance
        else:
            raise ValueError(f"{name}: junction does not lie on rib segment")
        tangent = (p1 - p0).normalized()
        face = model.faces[segment["attachment_face_index"]]
        normal = Vector(segment["attachment_normal"]).normalized()
        toward_face = face_centroid(face, points) - p0.lerp(p1, 0.5)
        toward_face -= tangent * toward_face.dot(tangent)
        toward_face -= normal * toward_face.dot(normal)
        if toward_face.length < 0.01:
            raise ValueError(f"{name}: cannot align truss hub to {face.group}")
        toward_face.normalize()
        point_cloud.extend(
            (
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
        )
        attachment_faces.append(face.group)
        outward_normals.append(normal)
    interior = -sum(outward_normals, Vector((0.0, 0.0, 0.0)))
    if interior.length < 0.01:
        raise ValueError(f"{name}: cannot determine truss-hub interior direction")
    interior.normalize()
    point_cloud.append(
        vertex + interior * (wall + max(incident_rib_heights) + 1.0)
    )
    node = convex_hull_points(name, point_cloud, rib_material)
    require_manifold(node, f"{name} triangulated truss hub")
    return section, node, {
        "name": name,
        "section": section,
        "source_vertex_index": junction["vertex_index"],
        "connected_rib_segment_indices": junction["rib_segment_indices"],
        "attachment_source_faces": sorted(set(attachment_faces)),
        "connected_rib_count": len(junction["rib_segment_indices"]),
        "geometry": "triangulated convex hub overlapping full gusset end sections",
        "junction_overlap_mm": float(ribs["junction_overlap_mm"]),
        "minimum_exterior_recess_mm": round(wall_depth, 3),
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
    gate3_config = json.loads(GATE3_CONFIG.read_text(encoding="utf-8"))
    rear_frame_config = gate3_config["compact_rear_base_frame"]
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
    baseline_component_counts = {
        name: len(components(obj)) for name, obj in shells.items()
    }
    flange_material = material(
        "Gate5_internal_flange_tabs", (0.95, 0.58, 0.08, 1.0)
    )
    rib_material = material(
        "Gate5_internal_panel_ribs", (0.72, 0.12, 0.08, 1.0)
    )
    rear_frame_result = dict(config["upper_planar_rear_frame"])
    allocations = distribute_modules(
        usable,
        float(config["joint_system"]["module_max_spacing_mm"]),
        int(config["joint_system"].get("ear_minimum_module_count", 1)),
    )
    pair_counts: dict[str, int] = defaultdict(int)
    joint_tasks = []
    for segment, fraction, allocation_count in allocations:
        pair = "__".join(segment["sections"])
        pair_counts[pair] += 1
        name = f"internal_flange_tab_{pair}_{pair_counts[pair]:02d}"
        joint_tasks.append((name, segment, fraction, allocation_count))

    joint_records = []
    rear_attachment_records = []
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

    rear_connection_config = config["rear_base_flange_connections"]
    for connection in rear_connection_config["connections"]:
        section = str(connection["section"])
        pair = f"rear_base__{section}"
        if rear_connection_config.get("connection_mode") == "rear_loaded_large_pads":
            name = f"rear_base_structural_pad_{section}"
            pad_section, pads, records = create_rear_loaded_base_pads(
                name, connection, config, rear_frame_config,
                shells["rear_base"], flange_material,
            )
            tabs_by_section[pad_section].extend(pads)
        else:
            name = f"rear_base_connector_rail_{section}"
            rail_section, rail, records = create_rear_base_connection_rail(
                name, connection, config, rear_frame_config,
                shells["rear_base"], flange_material,
            )
            tabs_by_section[rail_section].append(rail)
        pair_counts[pair] += len(records)
        joint_records.extend(records)
        rear_attachment_records.extend(records)
    rear_frame_result["attached_sections"] = list(
        rear_connection_config["attached_sections"]
    )
    rear_frame_result["continuous_connector_rail_count"] = sum(
        value.get("continuous_rear_base_connector_rail", False)
        for value in rear_attachment_records
    )
    rear_frame_result["large_structural_pad_count"] = sum(
        value.get("large_structural_mounting_pad", False)
        for value in rear_attachment_records
    )
    rear_frame_result["isolated_opening_tab_count"] = 0
    rear_frame_result["internal_m3_attachment_count"] = sum(
        value["internal_m3_screws"] for value in rear_attachment_records
    )
    rear_frame_result["rear_m5_attachment_count"] = sum(
        value.get("rear_m5_screws", 0) for value in rear_attachment_records
    )

    expected_component_counts = {
        section: len(components(shell)) for section, shell in shells.items()
    }
    for section, tab_parts in sorted(tabs_by_section.items()):
        for tab_index, tab in enumerate(tab_parts, start=1):
            apply_boolean(shells[section], tab, "UNION", solver="MANIFOLD")
            require_manifold(
                shells[section], f"{section} flange-tab union {tab_index}"
            )
        expected_components = expected_component_counts.get(section, 1)
        if len(components(shells[section])) > expected_components:
            bpy.ops.wm.save_as_mainfile(filepath="/tmp/gate5-rear-pad-union-debug.blend")
            raise ValueError(
                f"Flange-tab union increased {section} to "
                f"{len(components(shells[section]))} components; expected at "
                f"most {expected_components}"
            )

    rib_settings = config["internal_panel_ribs"]
    target_rib_sections = set(rib_settings["target_sections"])
    internal_rib_segments = internal_panel_segments(
        model, assignments, points, target_rib_sections
    )
    internal_rib_connection_keys = {
        (segment["section"], tuple(segment["vertex_indices"]))
        for segment in internal_rib_segments
    }
    ribs_by_section: dict[str, list[bpy.types.Object]] = defaultdict(list)
    main_ribs_by_section: dict[str, list[bpy.types.Object]] = defaultdict(list)
    supplementary_ribs_by_section: dict[str, list[bpy.types.Object]] = defaultdict(list)
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
        if record["panel_side_role"] == "main":
            main_ribs_by_section[section].extend(rib_parts)
        else:
            supplementary_ribs_by_section[section].extend(rib_parts)
        rib_records.append(record)
    gusset_junctions = internal_gusset_junctions(
        model, internal_rib_segments, points, config
    )
    junction_counts: dict[str, int] = defaultdict(int)
    junctions_by_section: dict[str, list[bpy.types.Object]] = defaultdict(list)
    junction_records = []
    for junction in gusset_junctions:
        section = junction["section"]
        junction_counts[section] += 1
        name = f"internal_gusset_junction_{section}_{junction_counts[section]:02d}"
        section, node, record = create_internal_gusset_junction_node(
            name, junction, internal_rib_segments, model, points, config, rib_material
        )
        junctions_by_section[section].append(node)
        junction_records.append(record)
    missing_rib_sections = target_rib_sections - set(ribs_by_section)
    if missing_rib_sections:
        raise ValueError(
            "No internal panel ribs were generated for requested sections: "
            f"{sorted(missing_rib_sections)}"
        )

    for section, rib_parts in sorted(main_ribs_by_section.items()):
        for rib_index, rib in enumerate(rib_parts, start=1):
            join_closed_overlapping_mesh(shells[section], rib)
            require_manifold(
                shells[section],
                f"{section} main triangular-gusset closed-mesh join {rib_index}",
            )
    support_sections = set(junctions_by_section) | set(supplementary_ribs_by_section)
    for section in sorted(support_sections):
        support_parts = (
            junctions_by_section.get(section, [])
            + supplementary_ribs_by_section.get(section, [])
        )
        for support_index, support_tool in enumerate(support_parts, start=1):
            join_closed_overlapping_mesh(shells[section], support_tool)
            require_manifold(
                shells[section],
                f"{section} truss-or-compact-gusset closed-mesh join {support_index}",
            )
    for section in sorted(target_rib_sections):
        if len(components(shells[section])) < baseline_component_counts[section]:
            raise ValueError(
                f"Internal reinforcement unexpectedly removed a closed component from "
                f"{section}"
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
    main_rib_count = sum(
        value["panel_side_role"] == "main" for value in rib_records
    )
    supplementary_rib_count = len(rib_records) - main_rib_count
    minimum_recorded_skin = min(
        value["minimum_exterior_skin_mm"]
        for value in joint_records
        if not value.get("procedural_rear_base_attachment", False)
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
            "main_gusset_count": main_rib_count,
            "compact_opposite_side_gusset_count": supplementary_rib_count,
            "integral_triangular_junction_node_count": len(junction_records),
            "junction_nodes_by_section": dict(sorted(junction_counts.items())),
            "eligible_internal_panel_connection_count": len(
                internal_rib_connection_keys
            ),
            "eligible_internal_panel_side_count": len(internal_rib_segments),
            "target_sections": sorted(target_rib_sections),
            "ribs_by_section": dict(sorted(rib_counts.items())),
            "cross_section": rib_settings["cross_section"],
            "foot_width_mm": float(rib_settings["foot_width_mm"]),
            "rib_height_mm": float(rib_settings["rib_height_mm"]),
            "compact_opposite_side_profile_mm": rib_settings[
                "supplementary_panel_side"
            ],
            "total_length_mm": round(
                sum(value["length_mm"] for value in rib_records), 3
            ),
            "slicer_union_strategy": "Each recessed gusset and hub remains a closed, overlapping internal solid in its shell STL; the 0.5 mm designed shell overlap is unioned by the slicer without risking a non-manifold CAD boolean at multi-panel vertex fans.",
            "status": f"Both panel sides of all {len(internal_rib_connection_keys)} source-panel connections internal to the four requested body shells are reinforced; {len(junction_records)} triangulated hubs overlap every shared main-gusset endpoint, while the compact opposite-side gussets clear the hub zone. Inter-shell flange seams, outer edges, rear base, and ears are excluded."
        },
        "upper_planar_rear_frame": rear_frame_result,
        "connection_fastener_module_count": len(joint_records),
        "flange_tab_module_count": sum(
            not value.get("procedural_rear_base_attachment", False)
            for value in joint_records
        ),
        "rear_base_attachment_path_count": len(rear_attachment_records),
        "flange_tab_modules_by_pair": dict(sorted(pair_counts.items())),
        "internal_m3_screw_count": sum(
            value["internal_m3_screws"] for value in joint_records
        ),
        "rear_m5_screw_count": sum(
            value.get("rear_m5_screws", 0) for value in joint_records
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
        "integral_internal_gusset_junction_manifest": junction_records,
        "acceptance": {
            "all_shells_closed_manifold": all(
                value["boundary_edges"] == 0 and value["nonmanifold_edges"] == 0
                for value in shell_metrics.values()
            ),
            "one_slicer_union_stl_exported_per_shell": topology_policy.all_single_closed_bodies(
                shell_metrics.values()
            ),
            "all_shells_single_connected_body": topology_policy.all_single_closed_bodies(
                shell_metrics.values()
            ),
            "closed_reinforcement_bodies_retained_in_target_shells": all(
                value["connected_components"] >= baseline_component_counts[name]
                for name, value in shell_metrics.items()
                if name in target_rib_sections
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
            "all_non_rear_joints_use_internal_fasteners": all(
                value["internal_tool_access_required"]
                and value["exterior_fastener_holes"] == 0
                for value in joint_records
                if not value.get("procedural_rear_base_attachment", False)
            ),
            "rear_base_has_six_intentional_rear_m5_paths": (
                len(rear_attachment_records) == 6
                and sum(value.get("rear_m5_screws", 0) for value in rear_attachment_records) == 6
                and all(value["exterior_fastener_holes"] == 1 for value in rear_attachment_records)
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
                and len(rib_records) == 2 * len(internal_rib_connection_keys)
            ),
            "all_main_truss_junctions_connected": (
                len(junction_records) == len(gusset_junctions)
            ),
            "all_junction_nodes_recessed_from_exterior": bool(junction_records) and all(
                value["minimum_exterior_recess_mm"]
                >= float(rib_settings["minimum_exterior_recess_mm"])
                for value in junction_records
            ),
            "ribs_confined_to_requested_body_shells": (
                set(value["section"] for value in rib_records)
                == target_rib_sections
            ),
            "no_inter_shell_or_outer_edge_ribs": True,
            "all_flange_tabs_recessed_from_exterior": all(
                value["minimum_tab_exterior_recess_mm"]
                >= float(
                    rear_connection_config["minimum_tab_exterior_recess_mm"]
                    if value.get("procedural_rear_base_attachment", False)
                    else config["joint_system"]
                    ["minimum_tab_exterior_recess_mm"]
                )
                for value in joint_records
            ),
            "all_source_seam_flange_tabs_have_two_hidden_root_webs": all(
                value["flange_root_web_count_per_tab"] == 2
                and value["minimum_root_web_exterior_recess_mm"]
                >= float(
                    config["joint_system"]
                    ["minimum_root_web_exterior_recess_mm"]
                )
                for value in joint_records
                if not value.get("procedural_rear_base_attachment", False)
            ),
            "all_source_seam_flange_pairs_are_matching_plain_rectangles": all(
                value["tabs_are_matching_plain_rectangles"]
                for value in joint_records
                if not value.get("procedural_rear_base_attachment", False)
            ),
            "rear_base_uses_large_structural_mounting_pads": (
                len(rear_attachment_records) == 6
                and all(
                    value.get("large_structural_mounting_pad", False)
                    and value["nut_tool_envelope_edge_clearance_mm"] >= 6.0
                    for value in rear_attachment_records
                )
            ),
            "eye_island_reinforcement_deferred": True,
            "upper_planar_rear_frame_integrated": (
                rear_frame_result["lower_face_rear_panels_remain_continuous"]
                and rear_frame_result["old_lower_service_cut_removed"]
                and rear_frame_result["old_rectangular_rim_and_tie_rails_removed"]
            ),
            "rear_base_attached_to_all_four_adjacent_shells": (
                len(rear_attachment_records) == 6
                and set(value["receiver"] for value in rear_attachment_records)
                == set(rear_connection_config["attached_sections"])
            ),
            "rear_base_m5_paths_have_usable_through_bores": all(
                value["rear_base_internal_bore"]
                and value["rear_base_bore_length_mm"] > 0.0
                for value in rear_attachment_records
            ),
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
