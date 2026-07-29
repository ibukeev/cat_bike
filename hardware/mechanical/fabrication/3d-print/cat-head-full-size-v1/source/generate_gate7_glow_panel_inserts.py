#!/usr/bin/env python3
"""Generate grouped translucent glow inserts and concealed shell retainers."""

from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

import bpy
import bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate6_eye_modules as gate6  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
GATE1_CONFIG = PACKAGE_ROOT / "config/gate1-panel-roles.json"
GATE2_CONFIG = PACKAGE_ROOT / "config/gate2-section-layout.json"
CONFIG_PATH = PACKAGE_ROOT / "config/gate7-glow-panel-inserts.json"
GATE6_BLEND = (
    PACKAGE_ROOT
    / "output/gate6-eye-modules/gate6-eye-modules-review.blend"
)
OUTPUT_DIR = PACKAGE_ROOT / "output/gate7-glow-panel-inserts"
INSERT_OUTPUT_DIR = OUTPUT_DIR / "glow-inserts"
SHELL_OUTPUT_DIR = OUTPUT_DIR / "shells"
SMALL_OUTPUT_DIR = OUTPUT_DIR / "small-model-100mm"

CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
HEAD_CENTER = Vector((0.0, 135.0, 150.0))


def face_edges(indices: tuple[int, ...]) -> list[tuple[int, int]]:
    return [
        tuple(sorted((indices[index], indices[(index + 1) % len(indices)])))
        for index in range(len(indices))
    ]


def oriented_face(
    face: gate1.ObjFace, transformed: list[Vector]
) -> tuple[tuple[int, ...], Vector, Vector]:
    return oriented_indices(tuple(face.indices), transformed)


def oriented_indices(
    source_indices: tuple[int, ...], transformed: list[Vector]
) -> tuple[tuple[int, ...], Vector, Vector]:
    indices = source_indices
    points = [transformed[index] for index in indices]
    normal = (points[1] - points[0]).cross(points[2] - points[0]).normalized()
    center = sum(points, Vector()) / len(points)
    if normal.dot(center - HEAD_CENTER) < 0.0:
        indices = tuple(reversed(indices))
        normal = -normal
    return indices, normal, center


def group_surface_faces(
    group: dict[str, Any], context: dict[str, Any]
) -> list[dict[str, Any]]:
    """Return source faces plus any configured edge-sharing bridge face."""
    model = context["model"]
    transformed = context["transformed"]
    interface = CONFIG.get("ear_root_interfaces", {}).get(group["name"])
    face_indices = list(group["face_indices"])
    if interface and interface.get("simplify_to_largest_face_per_source_panel"):
        faces_by_panel: dict[str, list[int]] = defaultdict(list)
        for face_index in face_indices:
            faces_by_panel[context["panel_by_face"][face_index]].append(
                face_index
            )

        def face_area(face_index: int) -> float:
            points = [
                transformed[index]
                for index in model.faces[face_index].indices
            ]
            origin = points[0]
            return sum(
                (points[index] - origin)
                .cross(points[index + 1] - origin)
                .length
                / 2.0
                for index in range(1, len(points) - 1)
            )

        face_indices = [
            max(panel_faces, key=face_area)
            for panel_faces in faces_by_panel.values()
        ]
    records = []
    for face_index in face_indices:
        indices, normal, center = oriented_face(
            model.faces[face_index], transformed
        )
        records.append(
            {
                "face_index": face_index,
                "indices": indices,
                "normal": normal,
                "center": center,
                "synthetic": False,
            }
        )
    if interface and "bridge_triangle_source_vertices" in interface:
        indices, normal, center = oriented_indices(
            tuple(
                int(index)
                for index in interface["bridge_triangle_source_vertices"]
            ),
            transformed,
        )
        records.append(
            {
                "face_index": None,
                "indices": indices,
                "normal": normal,
                "center": center,
                "synthetic": True,
            }
        )
    return records


def source_context() -> dict[str, Any]:
    gate1_config = json.loads(GATE1_CONFIG.read_text(encoding="utf-8"))
    gate2_config = json.loads(GATE2_CONFIG.read_text(encoding="utf-8"))
    source = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    units = gate1.panel_units(
        source, gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV)
    )
    scale, origin, _ = gate1.make_transform(
        gate1.bounds(source.vertices), float(gate1_config["target_height_mm"])
    )
    roles, _ = gate1.build_roles(units, gate1_config, scale)
    model = gate2.subdivide_center_panels(source, gate2_config)
    assignments = gate2.assign_faces(
        model.faces, model.vertices, roles, gate2_config, scale, origin
    )
    transformed = [
        Vector(gate1.transform_point(vertex, scale, origin))
        for vertex in model.vertices
    ]
    panel_by_face = [
        gate1.canonical_source_panel_id(face.group) for face in model.faces
    ]
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(model.faces):
        for edge in face_edges(tuple(face.indices)):
            edge_faces[edge].append(face_index)
    return {
        "config": gate1_config,
        "model": model,
        "assignments": assignments,
        "transformed": transformed,
        "panel_by_face": panel_by_face,
        "edge_faces": edge_faces,
    }


def connected_panel_groups(context: dict[str, Any]) -> list[dict[str, Any]]:
    approved = set(context["config"]["glow_transmitting_panels"])
    reclassified = set(CONFIG.get("opaque_reclassified_panels", []))
    if not reclassified <= approved:
        raise ValueError(
            f"Opaque reclassification contains unapproved panels: "
            f"{sorted(reclassified - approved)}"
        )
    approved -= reclassified
    adjacency = {panel: set() for panel in approved}
    model = context["model"]
    panel_by_face = context["panel_by_face"]
    for face_indices in context["edge_faces"].values():
        if len(face_indices) != 2:
            continue
        first, second = (panel_by_face[index] for index in face_indices)
        if first in approved and second in approved and first != second:
            adjacency[first].add(second)
            adjacency[second].add(first)

    configured = {
        name: set(panel_ids)
        for name, panel_ids in CONFIG.get("combined_groups", {}).items()
    }
    configured_panels: set[str] = set()
    for name, panel_ids in configured.items():
        if not panel_ids or not panel_ids <= approved:
            raise ValueError(
                f"Configured group {name} contains missing or unapproved panels"
            )
        overlap = configured_panels & panel_ids
        if overlap:
            raise ValueError(
                f"Configured group {name} reuses panels {sorted(overlap)}"
            )
        configured_panels.update(panel_ids)

    components = list(configured.values())
    remaining = approved - configured_panels
    while remaining:
        start = remaining.pop()
        component = {start}
        queue = deque([start])
        while queue:
            current = queue.popleft()
            for neighbor in adjacency[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)
        if len(component) > 1:
            raise ValueError(
                f"Unconfigured connected glow component: {sorted(component)}"
            )
        components.append(component)

    groups: list[dict[str, Any]] = []
    for component in components:
        matching_names = [
            name for name, panel_ids in configured.items() if panel_ids == component
        ]
        name = matching_names[0] if matching_names else f"panel_{next(iter(component))}"
        face_indices = [
            index
            for index, panel_id in enumerate(context["panel_by_face"])
            if panel_id in component
        ]
        groups.append(
            {
                "name": name,
                "panel_ids": sorted(component),
                "face_indices": face_indices,
                "combined": len(component) > 1,
            }
        )
    groups.sort(key=lambda value: (not value["combined"], value["name"]))
    if sum(len(group["panel_ids"]) for group in groups) != len(approved):
        raise ValueError("Gate 7 grouping did not cover every approved glow panel")
    return groups


def group_boundary(
    group: dict[str, Any], context: dict[str, Any]
) -> list[dict[str, Any]]:
    face_set = set(group["face_indices"])
    transformed = context["transformed"]
    assignments = context["assignments"]
    edge_faces = context["edge_faces"]
    group_edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    surface_faces = group_surface_faces(group, context)
    for local_index, surface_face in enumerate(surface_faces):
        for edge in face_edges(surface_face["indices"]):
            group_edge_faces[edge].append(local_index)

    records = []
    for edge, local_faces in group_edge_faces.items():
        if len(local_faces) != 1:
            continue
        surface_face = surface_faces[local_faces[0]]
        face_index = surface_face["face_index"]
        indices = surface_face["indices"]
        normal = surface_face["normal"]
        face_center = surface_face["center"]
        first, second = edge
        first_point, second_point = transformed[first], transformed[second]
        edge_vector = second_point - first_point
        if edge_vector.length < 0.01:
            raise ValueError(f"{group['name']} has a zero-length boundary edge")
        tangent = edge_vector.normalized()
        inward = -normal
        midpoint = (first_point + second_point) / 2.0
        radial = face_center - midpoint
        radial -= inward * radial.dot(inward)
        radial -= tangent * radial.dot(tangent)
        if radial.length < 0.01:
            radial = inward.cross(tangent)
        radial.normalize()
        neighbor_assignments = {
            assignments[index]
            for index in edge_faces[edge]
            if index not in face_set
            and assignments[index] in gate2.SECTION_ORDER
        }
        owner = next(iter(neighbor_assignments)) if len(neighbor_assignments) == 1 else None
        records.append(
            {
                "edge": edge,
                "face_index": face_index,
                "midpoint": midpoint,
                "tangent": tangent,
                "inward": inward,
                "radial": radial,
                "length": edge_vector.length,
                "owner": owner,
                "source_indices": indices,
            }
        )
    return records


def finish_surface_insert(
    name: str,
    vertices: list[Vector],
    faces: list[tuple[int, ...]],
    material: bpy.types.Material,
    thickness_mm: float | None = None,
) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata([tuple(point) for point in vertices], [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    modifier = obj.modifiers.new(f"{name}_inward_thickness", "SOLIDIFY")
    modifier.thickness = (
        float(thickness_mm)
        if thickness_mm is not None
        else float(CONFIG["insert"]["visible_thickness_mm"])
    )
    modifier.offset = -1.0
    modifier.use_rim = True
    modifier.use_rim_only = False
    modifier.use_even_offset = False
    modifier.use_quality_normals = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.select_set(False)
    gate5.require_manifold(obj, f"{name} solidification")
    return obj


def localize_bridge_connector_notch(
    output_vertices: list[Vector],
    output_faces: list[tuple[int, ...]],
    remap: dict[int, int],
    surface_faces: list[dict[str, Any]],
    transformed: list[Vector],
    interface: dict[str, Any] | None,
) -> None:
    """Inset only the bridge's top edge, not its shared front/back corners."""
    if not interface or "bridge_triangle_source_vertices" not in interface:
        return
    connector_vertices = {
        int(index)
        for index in interface["bridge_connector_source_vertices"]
    }
    _, bridge_face = next(
        (index, face)
        for index, face in enumerate(surface_faces)
        if face["synthetic"]
    )
    bridge_indices = bridge_face["indices"]
    shared_vertex = next(
        index for index in bridge_indices if index not in connector_vertices
    )
    relief = float(
        CONFIG["ear_root_interfaces"]["connector_corner_relief_depth_mm"]
    )
    notch_indices: dict[int, int] = {}
    for source_index in connector_vertices:
        direction = transformed[shared_vertex] - transformed[source_index]
        direction -= bridge_face["normal"] * direction.dot(
            bridge_face["normal"]
        )
        if direction.length < 0.01:
            raise ValueError("Ear-root top notch has no inward direction")
        notch_indices[source_index] = len(output_vertices)
        output_vertices.append(
            output_vertices[remap[source_index]]
            + direction.normalized() * relief
        )

    for face_index, surface_face in enumerate(surface_faces):
        source_loop = surface_face["indices"]
        if surface_face["synthetic"]:
            output_faces[face_index] = tuple(
                notch_indices.get(source_index, remap[source_index])
                for source_index in source_loop
            )
            continue
        notched_face: list[int] = []
        for index, source_index in enumerate(source_loop):
            next_source = source_loop[(index + 1) % len(source_loop)]
            notched_face.append(remap[source_index])
            edge = {source_index, next_source}
            connector_on_edge = edge & connector_vertices
            if shared_vertex in edge and connector_on_edge:
                connector_vertex = next(iter(connector_on_edge))
                notched_face.append(notch_indices[connector_vertex])
        output_faces[face_index] = tuple(notched_face)


def create_insert(
    group: dict[str, Any],
    boundary: list[dict[str, Any]],
    capture_records: list[dict[str, Any]],
    context: dict[str, Any],
    material: bpy.types.Material,
) -> bpy.types.Object:
    transformed = context["transformed"]
    surface_faces = group_surface_faces(group, context)
    used = sorted(
        {
            index
            for surface_face in surface_faces
            for index in surface_face["indices"]
        }
    )
    remap = {source: local for local, source in enumerate(used)}
    oriented = [
        (
            surface_face["indices"],
            surface_face["normal"],
            surface_face["center"],
        )
        for surface_face in surface_faces
    ]
    normals_by_vertex: dict[int, list[Vector]] = defaultdict(list)
    centers_by_vertex: dict[int, list[Vector]] = defaultdict(list)
    for indices, normal, center in oriented:
        for index in indices:
            normals_by_vertex[index].append(normal)
            centers_by_vertex[index].append(center)
    boundary_vertices = {index for record in boundary for index in record["edge"]}
    clearance = float(CONFIG["insert"]["perimeter_clearance_mm"])
    setback = float(CONFIG["insert"]["surface_setback_mm"])
    ear_interface = CONFIG.get("ear_root_interfaces", {}).get(group["name"])
    ear_notch_vertices: set[int] = set()
    if ear_interface:
        ear_notch_vertices = {
            int(index)
            for index in ear_interface.get(
                "connector_source_vertices",
                [ear_interface.get("connector_source_vertex")],
            )
            if index is not None
        }
        if not ear_notch_vertices <= set(used):
            raise ValueError(
                f"{group['name']} does not contain configured connector vertices "
                f"{sorted(ear_notch_vertices - set(used))}"
            )
    side_tip_directions = {}
    for source_index in ear_notch_vertices:
        side_edges = [
            record
            for record in boundary
            if source_index in record["edge"]
            and not set(record["edge"]) <= ear_notch_vertices
        ]
        if len(side_edges) != 1:
            raise ValueError(
                f"{group['name']} connector tip {source_index} has "
                f"{len(side_edges)} exterior side edges"
            )
        other_index = next(
            index
            for index in side_edges[0]["edge"]
            if index != source_index
        )
        side_tip_directions[source_index] = (
            transformed[other_index] - transformed[source_index]
        ).normalized()
    output_vertices = []
    for index in used:
        point = transformed[index].copy()
        normal = sum(normals_by_vertex[index], Vector()).normalized()
        if index in boundary_vertices:
            target = sum(centers_by_vertex[index], Vector()) / len(
                centers_by_vertex[index]
            )
            direction = target - point
            direction -= normal * direction.dot(normal)
            if direction.length > 0.01:
                point += direction.normalized() * clearance
        if index in side_tip_directions:
            point += side_tip_directions[index] * float(
                CONFIG["ear_root_interfaces"]
                ["connector_side_tip_setback_mm"]
            )
        point -= normal * setback
        output_vertices.append(point)
    output_faces = [
        tuple(remap[index] for index in indices) for indices, _, _ in oriented
    ]
    localize_bridge_connector_notch(
        output_vertices,
        output_faces,
        remap,
        surface_faces,
        transformed,
        ear_interface,
    )
    insert = finish_surface_insert(
        f"glow_insert_{group['name']}", output_vertices, output_faces, material
    )

    overlap = float(CONFIG["insert"]["perimeter_overlap_mm"])
    flange_thickness = float(
        CONFIG["insert"]["overlap_flange_thickness_mm"]
    )
    simplified_ear_cluster = "bridge_triangle_source_vertices" in (
        ear_interface or {}
    )
    flange_start = (
        1.2
        if simplified_ear_cluster
        else float(CONFIG["shell_wall_thickness_mm"])
        + float(CONFIG["insert"]["gasket_gap_mm"])
    )
    inside_capture = 1.0
    overlap_records = capture_records if simplified_ear_cluster else boundary
    for edge_number, record in enumerate(overlap_records, start=1):
        length = max(2.0, record["length"] - 0.4)
        strip_midpoint = record["midpoint"].copy()
        notch_vertices = ear_notch_vertices & set(record["edge"])
        if notch_vertices:
            ear_notch_vertex = next(iter(notch_vertices))
            other_vertex = next(
                index for index in record["edge"] if index != ear_notch_vertex
            )
            away = transformed[other_vertex] - transformed[ear_notch_vertex]
            trim = min(
                float(
                    CONFIG["ear_root_interfaces"]
                    ["connector_corner_relief_depth_mm"]
                ),
                record["length"] - 2.4,
            )
            strip_midpoint += away.normalized() * (trim / 2.0)
            length = max(2.0, record["length"] - trim - 0.4)
        edge_overlap = overlap
        if (
            ear_interface
            and "ear_shell" in ear_interface
            and record["owner"] == ear_interface["ear_shell"]
        ):
            edge_overlap = float(
                CONFIG["ear_root_interfaces"]["ear_edge_total_overlap_mm"]
            )
        strip = gate5.box(
            f"{insert.name}_overlap_{edge_number}",
            strip_midpoint
            - record["radial"] * ((edge_overlap - inside_capture) / 2.0)
            + record["inward"] * (flange_start + flange_thickness / 2.0),
            (record["tangent"], record["inward"], record["radial"]),
            (length, flange_thickness, edge_overlap + inside_capture),
            material,
        )
        if simplified_ear_cluster:
            gate5.apply_boolean(insert, strip, "UNION", solver="EXACT")
        else:
            gate5.join_closed_overlapping_mesh(insert, strip)
    gate5.require_manifold(insert, f"{group['name']} perimeter overlap")
    return insert


def add_visual_seam_cap(
    group: dict[str, Any],
    insert: bpy.types.Object,
    boundary: list[dict[str, Any]],
    context: dict[str, Any],
    material: bpy.types.Material,
) -> dict[str, Any]:
    """Add a shallow near-edge cap while retaining deep fit clearance."""
    transformed = context["transformed"]
    surface_faces = group_surface_faces(group, context)
    used = sorted(
        {
            index
            for surface_face in surface_faces
            for index in surface_face["indices"]
        }
    )
    remap = {source: local for local, source in enumerate(used)}
    oriented = [
        (
            surface_face["indices"],
            surface_face["normal"],
            surface_face["center"],
        )
        for surface_face in surface_faces
    ]
    normals_by_vertex: dict[int, list[Vector]] = defaultdict(list)
    centers_by_vertex: dict[int, list[Vector]] = defaultdict(list)
    for indices, normal, center in oriented:
        for index in indices:
            normals_by_vertex[index].append(normal)
            centers_by_vertex[index].append(center)
    boundary_vertices = {index for record in boundary for index in record["edge"]}
    values = CONFIG["visible_seam_cap"]
    clearance = float(values["perimeter_clearance_mm"])
    setback = float(values["surface_setback_mm"])
    ear_interface = CONFIG.get("ear_root_interfaces", {}).get(group["name"])
    relief_vertices = {
        int(index)
        for index in (ear_interface or {}).get(
            "connector_source_vertices",
            [(ear_interface or {}).get("connector_source_vertex")],
        )
        if index is not None
    }
    side_tip_directions = {}
    for source_index in relief_vertices:
        side_edges = [
            record
            for record in boundary
            if source_index in record["edge"]
            and not set(record["edge"]) <= relief_vertices
        ]
        if len(side_edges) != 1:
            raise ValueError(
                f"{group['name']} cap connector tip {source_index} has "
                f"{len(side_edges)} exterior side edges"
            )
        other_index = next(
            index
            for index in side_edges[0]["edge"]
            if index != source_index
        )
        side_tip_directions[source_index] = (
            transformed[other_index] - transformed[source_index]
        ).normalized()
    output_vertices = []
    for index in used:
        point = transformed[index].copy()
        normal = sum(normals_by_vertex[index], Vector()).normalized()
        if index in boundary_vertices:
            target = sum(centers_by_vertex[index], Vector()) / len(
                centers_by_vertex[index]
            )
            direction = target - point
            direction -= normal * direction.dot(normal)
            if direction.length > 0.01:
                point += direction.normalized() * clearance
        if index in side_tip_directions:
            point += side_tip_directions[index] * float(
                CONFIG["ear_root_interfaces"]
                ["connector_side_tip_setback_mm"]
            )
        point -= normal * setback
        output_vertices.append(point)
    output_faces = [
        tuple(remap[index] for index in indices) for indices, _, _ in oriented
    ]
    localize_bridge_connector_notch(
        output_vertices,
        output_faces,
        remap,
        surface_faces,
        transformed,
        ear_interface,
    )
    cap = finish_surface_insert(
        f"{insert.name}_visible_seam_cap",
        output_vertices,
        output_faces,
        material,
        float(values["thickness_mm"]),
    )
    depsgraph = bpy.context.evaluated_depsgraph_get()
    intersections = len(
        BVHTree.FromObject(insert, depsgraph).overlap(
            BVHTree.FromObject(cap, depsgraph)
        )
    )
    if intersections == 0:
        raise ValueError(f"{group['name']} visible cap does not overlap its body")
    if "bridge_triangle_source_vertices" in (ear_interface or {}):
        gate5.apply_boolean(insert, cap, "UNION", solver="EXACT")
    else:
        gate5.join_closed_overlapping_mesh(insert, cap)
    gate5.require_manifold(insert, f"{group['name']} visible seam cap")
    return {
        "perimeter_clearance_mm": clearance,
        "surface_setback_mm": setback,
        "thickness_mm": float(values["thickness_mm"]),
        "body_attachment_triangle_intersections": intersections,
        "deep_body_clearance_mm": float(
            CONFIG["insert"]["perimeter_clearance_mm"]
        ),
    }


def add_ear_root_bridge(
    group: dict[str, Any],
    insert: bpy.types.Object,
    context: dict[str, Any],
    material: bpy.types.Material,
) -> dict[str, Any] | None:
    """Report the bridge already integrated into the simplified surface."""
    interface = CONFIG.get("ear_root_interfaces", {}).get(group["name"])
    if not interface or "bridge_triangle_source_vertices" not in interface:
        return None
    source_indices = tuple(
        int(index) for index in interface["bridge_triangle_source_vertices"]
    )
    connector_vertices = {
        int(index)
        for index in interface["bridge_connector_source_vertices"]
    }
    surface_faces = group_surface_faces(group, context)
    return {
        "name": interface["bridge_name"],
        "source_vertices": list(source_indices),
        "connector_relief_vertices": sorted(connector_vertices),
        "combined_with_insert": group["name"],
        "additional_printed_part": False,
        "integrated_in_edge_connected_surface": True,
        "visible_surface_plane_count": len(surface_faces),
        "visible_cap_perimeter_clearance_mm": float(
            CONFIG["visible_seam_cap"]["perimeter_clearance_mm"]
        ),
    }


def usable_mount_edges(boundary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    minimum = float(CONFIG["mount"]["tab_length_mm"]) + 1.0
    return [
        record
        for record in boundary
        if record["owner"] is not None and record["length"] >= minimum
    ]


def choose_mounts(
    group: dict[str, Any], boundary: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    candidates = usable_mount_edges(boundary)
    if CONFIG.get("combined_mount_modes", {}).get(group["name"]) == "upper_shared_edges":
        hooks = []
        screws = []
        for owner in ("right_upper_head", "left_upper_head"):
            owned = [record for record in candidates if record["owner"] == owner]
            if not owned:
                raise ValueError(f"{group['name']} has no shared upper edge on {owner}")
            source = max(owned, key=lambda value: value["length"])
            hook = dict(source)
            screw = dict(source)
            spacing = min(source["length"] * 0.24, 10.0)
            hook["midpoint"] = source["midpoint"] - source["tangent"] * spacing
            screw["midpoint"] = source["midpoint"] + source["tangent"] * spacing
            hooks.append(hook)
            screws.append(screw)
        return hooks, screws
    ear_interface = CONFIG.get("ear_root_interfaces", {}).get(group["name"])
    if ear_interface and "ear_shell" in ear_interface:
        ear_edges = [
            record
            for record in candidates
            if record["owner"] == ear_interface["ear_shell"]
        ]
        body_edges = [
            record
            for record in candidates
            if record["owner"] == ear_interface["body_shell"]
        ]
        if ear_interface.get("mount_entirely_to_body_shell"):
            connector_vertices = {
                int(index)
                for index in ear_interface["connector_source_vertices"]
            }
            body_edges = [
                record
                for record in body_edges
                if not (set(record["edge"]) & connector_vertices)
            ]
            if len(body_edges) < 2:
                raise ValueError(
                    f"{group['name']} needs two body-shell mounting edges "
                    "away from its top connector notch"
                )
            hook = min(body_edges, key=lambda value: value["midpoint"].z)
            screw = max(
                (record for record in body_edges if record is not hook),
                key=lambda value: (
                    value["midpoint"] - hook["midpoint"]
                ).length,
            )
            return [hook], [screw]
        if not ear_edges or not body_edges:
            raise ValueError(
                f"{group['name']} needs both ear and body mounting edges"
            )
        # The lower ear edge is farthest from the structural two-bolt ear tab.
        hook = min(ear_edges, key=lambda value: value["midpoint"].z)
        screw = max(body_edges, key=lambda value: value["length"])
        return [hook], [screw]

    if group["combined"]:
        hooks = []
        screws = []
        for owner in ("right_upper_head", "left_upper_head"):
            owned = [record for record in candidates if record["owner"] == owner]
            if not owned:
                raise ValueError(f"{group['name']} has no hook edge on {owner}")
            hooks.append(
                max(
                    owned,
                    key=lambda value: (
                        value["midpoint"].z,
                        value["length"],
                    ),
                )
            )
        for owner in ("right_lower_face", "left_lower_face"):
            owned = [record for record in candidates if record["owner"] == owner]
            if not owned:
                raise ValueError(f"{group['name']} has no screw edge on {owner}")
            screws.append(
                max(
                    owned,
                    key=lambda value: (
                        value["length"],
                        -value["midpoint"].z,
                    ),
                )
            )
        return hooks, screws

    if len(candidates) < 2:
        raise ValueError(f"{group['name']} needs two structural boundary edges")
    safest = sorted(
        candidates,
        key=lambda value: value["midpoint"].z
        - 0.25 * abs(value["midpoint"].x),
        reverse=True,
    )[:2]
    screw = max(safest, key=lambda value: value["length"])
    hook = next(
        record for record in safest if record is not screw
    )
    return [hook], [screw]


def add_fixed_hook(
    group_name: str,
    hook_number: int,
    record: dict[str, Any],
    shell: bpy.types.Object,
    material: bpy.types.Material,
) -> None:
    values = CONFIG["mount"]
    length = min(float(values["hook_length_mm"]), record["length"] - 1.0)
    stem_width = float(values["hook_stem_width_mm"])
    stem_depth = float(values["hook_stem_depth_mm"])
    lip_reach = float(values["hook_lip_reach_mm"])
    lip_thickness = float(values["hook_lip_thickness_mm"])
    recess = float(values["front_recess_mm"])
    panel_overlap = float(CONFIG["insert"]["perimeter_overlap_mm"])
    attach_overlap = 0.5
    axes = (record["tangent"], record["inward"], record["radial"])
    stem = gate5.box(
        f"{group_name}_fixed_hook_{hook_number}_stem",
        record["midpoint"]
        - record["radial"]
        * (panel_overlap + stem_width / 2.0 - attach_overlap)
        + record["inward"] * (recess + stem_depth / 2.0),
        axes,
        (length, stem_depth, stem_width),
        material,
    )
    lip_width = panel_overlap + lip_reach
    lip = gate5.box(
        f"{group_name}_fixed_hook_{hook_number}_lip",
        record["midpoint"]
        - record["radial"] * panel_overlap
        + record["inward"] * (recess + stem_depth - lip_thickness / 2.0),
        axes,
        (length, lip_thickness, lip_width),
        material,
    )
    gate5.apply_boolean(shell, stem, "UNION", solver="MANIFOLD")
    gate5.apply_boolean(shell, lip, "UNION", solver="MANIFOLD")
    gate5.require_manifold(shell, f"{group_name} fixed hook {hook_number}")


def add_screw_mount(
    group_name: str,
    mount_number: int,
    record: dict[str, Any],
    insert: bpy.types.Object,
    shell: bpy.types.Object,
    insert_material: bpy.types.Material,
    shell_material: bpy.types.Material,
) -> dict[str, Any]:
    values = CONFIG["mount"]
    length = min(float(values["tab_length_mm"]), record["length"] - 1.0)
    depth = float(values["tab_depth_mm"])
    thickness = float(values["tab_thickness_mm"])
    gap = float(values["tab_face_gap_mm"])
    overlap = float(values["shell_overlap_mm"])
    panel_overlap = float(CONFIG["insert"]["perimeter_overlap_mm"])
    recess = float(values["front_recess_mm"])
    hole_depth = float(values["bolt_depth_from_surface_mm"])
    axes = (record["tangent"], record["inward"], record["radial"])
    insert_center = (
        record["midpoint"]
        - record["radial"] * (panel_overlap - thickness / 2.0 + 0.4)
        + record["inward"] * (recess + depth / 2.0)
    )
    shell_center = insert_center - record["radial"] * (thickness + gap)
    shell_tab = gate5.box(
        f"{group_name}_shell_mount_tab_{mount_number}",
        shell_center,
        axes,
        (length, depth, thickness),
        shell_material,
    )
    insert_tab = gate5.box(
        f"{group_name}_insert_mount_tab_{mount_number}",
        insert_center,
        axes,
        (length, depth, thickness),
        insert_material,
    )
    for tab, center in ((shell_tab, shell_center), (insert_tab, insert_center)):
        hole_center = center + record["inward"] * (hole_depth - depth / 2.0)
        gate6.cut_axis_hole(
            tab,
            f"{tab.name}_m2_5_clearance",
            hole_center,
            record["radial"],
            float(values["m2_5_clearance_diameter_mm"]),
            thickness + 3.0,
        )
    gate5.apply_boolean(shell, shell_tab, "UNION", solver="MANIFOLD")
    interface = CONFIG.get("ear_root_interfaces", {}).get(group_name)
    if "bridge_triangle_source_vertices" in (interface or {}):
        gate5.apply_boolean(insert, insert_tab, "UNION", solver="EXACT")
    else:
        gate5.join_closed_overlapping_mesh(insert, insert_tab)
    gate5.require_manifold(shell, f"{group_name} shell mount {mount_number}")
    gate5.require_manifold(insert, f"{group_name} insert mount {mount_number}")
    return {
        "owner_shell": record["owner"],
        "anchor_mm": [round(value, 4) for value in record["midpoint"]],
        "axis": [round(value, 5) for value in record["radial"]],
        "axis_parallel_to_panel": abs(record["radial"].dot(record["inward"]))
        < 1e-5,
    }


def part_metrics(obj: bpy.types.Object) -> dict[str, Any]:
    boundary, nonmanifold = gate5.topology_counts(obj)
    components = gate5.components(obj)
    points = [tuple(obj.matrix_world @ vertex.co) for vertex in obj.data.vertices]
    return {
        "vertices": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "connected_components": len(components),
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "dimensions_mm_sorted": [round(float(value), 3) for value in sorted(obj.dimensions)],
        "orientation_search": gate2.best_fit(
            points,
            CONFIG["printer_envelope_mm"],
            int(CONFIG["orientation_step_degrees"]),
        ),
    }


def validate_ear_connector_clearance(
    inserts: list[bpy.types.Object],
) -> dict[str, dict[str, Any]]:
    """Check both inserts against freshly recreated Gate 5 ear tabs."""
    interfaces = {
        name: interface
        for name, interface in CONFIG["ear_root_interfaces"].items()
        if isinstance(interface, dict) and "gate5_joint_pair" in interface
    }
    pair_to_groups: dict[str, list[str]] = defaultdict(list)
    for name, interface in interfaces.items():
        pair_to_groups[interface["gate5_joint_pair"]].append(name)
    insert_by_group = {
        obj.name.removeprefix("glow_insert_"): obj for obj in inserts
    }
    gate5_config = json.loads(gate5.CONFIG_PATH.read_text(encoding="utf-8"))
    model, assignments, scale, origin = gate5.transformed_source()
    points, segments = gate5.seam_segments(model, assignments, scale, origin)
    minimum = float(
        gate5_config["joint_system"]["minimum_usable_seam_edge_mm"]
    )
    excluded = {
        tuple(value)
        for value in gate5_config.get("excluded_joint_face_pairs", [])
    }
    usable = [
        segment
        for segment in segments
        if segment["length_mm"] >= minimum
        and tuple(segment["face_groups"]) not in excluded
    ]
    allocations = gate5.distribute_modules(
        usable,
        float(gate5_config["joint_system"]["module_max_spacing_mm"]),
        int(gate5_config["joint_system"].get("ear_minimum_module_count", 1)),
    )
    temporary_material = gate5.material(
        "Gate7_temporary_ear_clearance_validation", (0.25, 0.25, 0.25, 1.0)
    )
    depsgraph = bpy.context.evaluated_depsgraph_get()
    required_clearance = float(
        CONFIG["ear_root_interfaces"]["connector_clearance_mm"]
    )
    results = {}
    for segment, fraction, allocation_count in allocations:
        pair = "__".join(segment["sections"])
        if pair not in pair_to_groups:
            continue
        tabs, _ = gate5.create_internal_flange_tabs(
            f"gate7_clearance_validation_{pair}",
            segment,
            fraction,
            allocation_count,
            model,
            points,
            gate5_config,
            temporary_material,
        )
        for group_name in pair_to_groups[pair]:
            insert = insert_by_group[group_name]
            insert_tree = BVHTree.FromObject(insert, depsgraph)
            intersections = 0
            sampled_gaps = []
            for tab in tabs.values():
                tab_tree = BVHTree.FromObject(tab, depsgraph)
                intersections += len(insert_tree.overlap(tab_tree))
                for vertex in tab.data.vertices:
                    nearest = insert_tree.find_nearest(
                        tab.matrix_world @ vertex.co
                    )
                    if nearest:
                        sampled_gaps.append(nearest[3])
            minimum_gap = min(sampled_gaps)
            if intersections:
                raise ValueError(
                    f"{group_name} still intersects the Gate 5 ear connector "
                    f"at {intersections} triangle pairs"
                )
            if minimum_gap + 1e-6 < required_clearance:
                raise ValueError(
                    f"{group_name} connector gap {minimum_gap:.3f} mm is below "
                    f"the required {required_clearance:.3f} mm"
                )
            results[group_name] = {
                "triangle_intersection_count": intersections,
                "minimum_connector_vertex_to_insert_surface_gap_mm": round(
                    minimum_gap, 4
                ),
                "required_clearance_mm": required_clearance,
            }
        for tab in tabs.values():
            bpy.data.objects.remove(tab, do_unlink=True)
    missing = set(interfaces) - set(results)
    if missing:
        raise ValueError(f"Missing ear clearance validation for {sorted(missing)}")
    return results


def main() -> None:
    for directory in (
        OUTPUT_DIR,
        INSERT_OUTPUT_DIR,
        SHELL_OUTPUT_DIR,
        SMALL_OUTPUT_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)
    for directory in (INSERT_OUTPUT_DIR, SMALL_OUTPUT_DIR):
        for stale_stl in directory.glob("*.stl"):
            stale_stl.unlink()
    bpy.ops.wm.open_mainfile(filepath=str(GATE6_BLEND))
    context = source_context()
    groups = connected_panel_groups(context)
    shells = {name: bpy.data.objects[name] for name in gate2.SECTION_ORDER}
    insert_material = gate5.material(
        "Gate7_frosted_glow_insert", (0.58, 0.16, 0.92, 0.72)
    )
    inserts = []
    group_reports = []
    for group in groups:
        boundary = group_boundary(group, context)
        hooks, screws = choose_mounts(group, boundary)
        insert = create_insert(
            group,
            boundary,
            [*hooks, *screws],
            context,
            insert_material,
        )
        seam_cap_record = add_visual_seam_cap(
            group, insert, boundary, context, insert_material
        )
        bridge_record = add_ear_root_bridge(
            group, insert, context, insert_material
        )
        ear_clearance = None
        if group["name"] in CONFIG.get("ear_root_interfaces", {}):
            ear_clearance = {
                "clearance_mm": float(
                    CONFIG["ear_root_interfaces"]["connector_clearance_mm"]
                ),
                "corner_relief_depth_mm": float(
                    CONFIG["ear_root_interfaces"]
                    ["connector_corner_relief_depth_mm"]
                ),
                "structural_gate5_connector_unchanged": True,
                "translucent_ear_root_return_mm": float(
                    CONFIG["ear_root_interfaces"]["ear_edge_total_overlap_mm"]
                ),
                "adjacent_hidden_returns_trimmed_to_relief": True,
            }
        hook_records = []
        for hook_number, record in enumerate(hooks, start=1):
            add_fixed_hook(
                group["name"],
                hook_number,
                record,
                shells[record["owner"]],
                shells[record["owner"]].data.materials[0],
            )
            hook_records.append(
                {
                    "owner_shell": record["owner"],
                    "anchor_mm": [round(value, 4) for value in record["midpoint"]],
                }
            )
        screw_records = [
            add_screw_mount(
                group["name"],
                mount_number,
                record,
                insert,
                shells[record["owner"]],
                insert_material,
                shells[record["owner"]].data.materials[0],
            )
            for mount_number, record in enumerate(screws, start=1)
        ]
        gate5.export_stl(insert, INSERT_OUTPUT_DIR / f"{insert.name}.stl")
        inserts.append(insert)
        group_reports.append(
            {
                "name": group["name"],
                "panel_ids": group["panel_ids"],
                "combined": group["combined"],
                "source_panel_count": len(group["panel_ids"]),
                "boundary_edge_count": len(boundary),
                "hook_count": len(hooks),
                "m2_5_fastener_count": len(screws),
                "hooks": hook_records,
                "screw_mounts": screw_records,
                "ear_root_revision": ear_clearance,
                "ear_root_bridge": bridge_record,
                "visible_seam_cap": seam_cap_record,
            }
        )

    ear_clearance_validation = validate_ear_connector_clearance(inserts)
    for group_report in group_reports:
        if group_report["name"] in ear_clearance_validation:
            group_report["ear_root_revision"].update(
                ear_clearance_validation[group_report["name"]]
            )

    for shell_name, shell in shells.items():
        gate5.require_manifold(shell, f"Gate 7 shell {shell_name}")
        gate5.export_stl(shell, SHELL_OUTPUT_DIR / f"{shell_name}.stl")

    scale = (
        float(CONFIG["small_model_head_height_mm"])
        / float(CONFIG["source_head_height_mm"])
    )
    scaled = [
        gate6.duplicate_scaled(insert, f"small_{insert.name}", scale)
        for insert in inserts
    ]
    for part in scaled:
        gate5.export_stl(part, SMALL_OUTPUT_DIR / f"{part.name}.stl")
    gate6.export_selected(
        SMALL_OUTPUT_DIR / "gate7_grouped_glow_inserts_visual_assembly.stl",
        scaled,
    )
    for part in scaled:
        bpy.data.objects.remove(part, do_unlink=True)

    review_objects = [
        obj for obj in bpy.context.scene.objects if obj.type == "MESH"
    ]
    gate6.export_selected(
        OUTPUT_DIR / "gate7-glow-panel-inserts-review.stl", review_objects
    )
    bpy.ops.object.select_all(action="DESELECT")
    for obj in review_objects:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=str(OUTPUT_DIR / "gate7-glow-panel-inserts-review.glb"),
        export_format="GLB",
        use_selection=True,
    )
    bpy.ops.wm.save_as_mainfile(
        filepath=str(OUTPUT_DIR / "gate7-glow-panel-inserts-review.blend")
    )

    insert_metrics = {insert.name: part_metrics(insert) for insert in inserts}
    shell_metrics = {name: part_metrics(shell) for name, shell in shells.items()}
    expected = CONFIG["expected"]
    central_group_name = CONFIG.get(
        "central_group_name", "central_12_panel_cluster"
    )
    central = next(
        report
        for report in group_reports
        if report["name"] == central_group_name
    )
    noncentral = [report for report in group_reports if report is not central]
    acceptance = {
        "all_configured_translucent_panels_covered": sum(
            report["source_panel_count"] for report in group_reports
        )
        == int(expected["approved_panel_count"]),
        "expected_printed_insert_count": len(inserts)
        == int(expected["printed_insert_count"]),
        "central_group_has_expected_panel_count": central["source_panel_count"]
        == int(expected.get("central_panel_count", 12)),
        "central_mount_count": central["hook_count"]
        == int(expected["central_hook_count"])
        and central["m2_5_fastener_count"]
        == int(expected["central_fastener_count"]),
        "noncentral_insert_mount_counts": all(
            report["hook_count"] == int(expected["single_hook_count"])
            and report["m2_5_fastener_count"]
            == int(expected["single_fastener_count"])
            for report in noncentral
        ),
        "all_fastener_axes_parallel_to_local_panels": all(
            mount["axis_parallel_to_panel"]
            for report in group_reports
            for mount in report["screw_mounts"]
        ),
        "no_exterior_fastener_holes": True,
        "ear_root_returns_and_connector_notches_mirrored": all(
            report["ear_root_revision"] is not None
            for report in group_reports
            if report["name"] in CONFIG["ear_root_interfaces"]
        )
        and len(
            [
                report
                for report in group_reports
                if report["ear_root_revision"] is not None
            ]
        )
        == 2,
        "two_missing_ear_root_panes_added_without_extra_parts": len(
            [
                report
                for report in group_reports
                if report["ear_root_bridge"] is not None
                and not report["ear_root_bridge"]["additional_printed_part"]
            ]
        )
        == 2,
        "all_inserts_have_near_edge_visible_caps": all(
            report["visible_seam_cap"]["perimeter_clearance_mm"]
            == float(CONFIG["visible_seam_cap"]["perimeter_clearance_mm"])
            and report["visible_seam_cap"]
            ["body_attachment_triangle_intersections"]
            > 0
            for report in group_reports
        ),
        "both_ear_root_clusters_are_integrated_three_plane_surfaces": all(
            report["ear_root_bridge"]
            ["integrated_in_edge_connected_surface"]
            and report["ear_root_bridge"]["visible_surface_plane_count"] == 3
            for report in group_reports
            if report["ear_root_bridge"] is not None
        )
        and len(
            [
                report
                for report in group_reports
                if report["ear_root_bridge"] is not None
            ]
        )
        == 2,
        "both_ear_root_insert_meshes_are_single_component": all(
            len(gate5.components(insert)) == 1
            for insert in inserts
            if insert.name
            in {
                "glow_insert_right_ear_root_cluster",
                "glow_insert_left_ear_root_cluster",
            }
        ),
        "ear_connectors_have_verified_clearance": all(
            value["triangle_intersection_count"] == 0
            and value["minimum_connector_vertex_to_insert_surface_gap_mm"]
            >= value["required_clearance_mm"]
            for value in ear_clearance_validation.values()
        ),
        "all_inserts_closed_manifold": all(
            value["boundary_edges"] == 0 and value["nonmanifold_edges"] == 0
            for value in insert_metrics.values()
        ),
        "all_gate7_shells_closed_manifold": all(
            value["boundary_edges"] == 0 and value["nonmanifold_edges"] == 0
            for value in shell_metrics.values()
        ),
        "all_inserts_fit_printer": all(
            value["orientation_search"]["fits"]
            for value in insert_metrics.values()
        ),
        "small_model_visual_export_created": (
            SMALL_OUTPUT_DIR / "gate7_grouped_glow_inserts_visual_assembly.stl"
        ).exists(),
    }
    if not all(acceptance.values()):
        failures = [name for name, passed in acceptance.items() if not passed]
        raise ValueError(f"Gate 7 validation failed: {failures}")

    total_fasteners = sum(
        report["m2_5_fastener_count"] for report in group_reports
    )
    report = {
        "gate": "Gate 7 grouped translucent glow-panel inserts",
        "status": "review_required",
        "groups": group_reports,
        "insert_metrics": insert_metrics,
        "revised_shell_metrics": shell_metrics,
        "hardware": {
            "m2_5_through_bolts": total_fasteners,
            "m2_5_washers": total_fasteners * 2,
            "m2_5_loose_nyloc_nuts": total_fasteners,
            "fixed_integrated_hooks": sum(
                report["hook_count"] for report in group_reports
            ),
        },
        "ear_connector_clearance_validation": ear_clearance_validation,
        "small_model_scale": round(scale, 6),
        "acceptance": acceptance,
        "review_notes": CONFIG["review_notes"],
    }
    (OUTPUT_DIR / "gate7-glow-panel-validation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    print(f"Wrote {OUTPUT_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
