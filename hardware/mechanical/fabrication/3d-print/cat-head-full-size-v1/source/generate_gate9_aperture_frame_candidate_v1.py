#!/usr/bin/env python3
"""Generate review-only recessed Gate 9 aperture-frame shell repairs.

The candidate uses edge-parallel cylindrical ribs placed inside the dihedral
half-spaces of neighboring source facets.  Unlike the rejected nearest-vertex
bridges, each rib has a continuous, broad overlap with both adjoining shell
walls and an analytically bounded exterior recess.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import analyze_gate9_selected_bridge_sites as audit  # noqa: E402
import generate_gate1_master as gate1  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/gate9-aperture-frame-candidate-v1.json"
)
HEAD_CENTER = Vector((0.0, 135.0, 150.0))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def duplicate_object(
    source: bpy.types.Object, name: str
) -> bpy.types.Object:
    duplicate = source.copy()
    duplicate.data = source.data.copy()
    duplicate.name = name
    bpy.context.collection.objects.link(duplicate)
    duplicate.hide_render = False
    duplicate.hide_viewport = False
    return duplicate


def selected_object(prefix: str, suffix: str) -> bpy.types.Object:
    name = f"{prefix}__{suffix}"
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise KeyError(
            f"{name} not found; load the selected Gate 9 comparison BLEND"
        )
    return obj


def build_source_context(config: dict[str, Any]) -> dict[str, Any]:
    gate2_config = json.loads(
        (REPO_ROOT / config["source_gate2_config"]).read_text(
            encoding="utf-8"
        )
    )
    gate1_config = json.loads(
        gate1.DEFAULT_CONFIG.read_text(encoding="utf-8")
    )
    source = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    units = gate1.panel_units(
        source, gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV)
    )
    scale, origin, _ = gate1.make_transform(
        gate1.bounds(source.vertices),
        float(gate1_config["target_height_mm"]),
    )
    roles, _ = gate1.build_roles(units, gate1_config, scale)
    model = gate2.subdivide_center_panels(source, gate2_config)
    assignments = gate2.assign_faces(
        model.faces,
        model.vertices,
        roles,
        gate2_config,
        scale,
        origin,
    )
    transformed = [
        Vector(gate1.transform_point(vertex, scale, origin))
        for vertex in model.vertices
    ]
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(model.faces):
        indices = tuple(face.indices)
        for offset, first in enumerate(indices):
            second = indices[(offset + 1) % len(indices)]
            edge_faces[tuple(sorted((first, second)))].append(face_index)
    return {
        "model": model,
        "assignments": assignments,
        "transformed": transformed,
        "edge_faces": edge_faces,
    }


def oriented_indices(
    indices: tuple[int, ...], transformed: list[Vector]
) -> tuple[tuple[int, ...], Vector, Vector]:
    oriented = indices
    points = [transformed[index] for index in oriented]
    normal = (
        (points[1] - points[0]).cross(points[2] - points[0]).normalized()
    )
    center = sum(points, Vector()) / len(points)
    if normal.dot(center - HEAD_CENTER) < 0.0:
        oriented = tuple(reversed(oriented))
        normal = -normal
    return oriented, normal, center


def face_geometry(
    context: dict[str, Any], face_index: int
) -> tuple[tuple[int, ...], Vector, Vector]:
    return oriented_indices(
        tuple(context["model"].faces[face_index].indices),
        context["transformed"],
    )


def shared_edge(
    first_indices: tuple[int, ...], second_indices: tuple[int, ...]
) -> tuple[int, int]:
    common = set(first_indices) & set(second_indices)
    if len(common) != 2:
        raise ValueError(
            f"Expected one shared edge, found vertices {sorted(common)}"
        )
    first, second = sorted(common)
    return first, second


def equal_plane_offset(
    first_normal: Vector, second_normal: Vector, distance: float
) -> Vector:
    cosine = first_normal.dot(second_normal)
    denominator = 1.0 + cosine
    if denominator < 0.08:
        raise ValueError(
            "Cannot place an inboard edge rib between near-opposite normals"
        )
    return (
        -distance
        * (first_normal + second_normal)
        / denominator
    )


def make_edge_rib(
    name: str,
    first_index: int,
    second_index: int,
    first_normal: Vector,
    second_normal: Vector,
    transformed: list[Vector],
    radius: float,
    recess: float,
    assigned_material: bpy.types.Material,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    first = transformed[first_index]
    second = transformed[second_index]
    offset = equal_plane_offset(
        first_normal, second_normal, radius + recess
    )
    rib = gate5.cylinder(
        name,
        first + offset,
        second + offset,
        2.0 * radius,
        assigned_material,
        vertices=24,
    )
    first_max = first_normal.dot(offset) + radius
    second_max = second_normal.dot(offset) + radius
    return rib, {
        "name": name,
        "edge_vertex_indices": [first_index, second_index],
        "edge_length_mm": round((second - first).length, 3),
        "radius_mm": radius,
        "axis_offset_head_mm": [round(value, 4) for value in offset],
        "maximum_signed_distance_to_first_exterior_plane_mm": round(
            first_max, 4
        ),
        "maximum_signed_distance_to_second_exterior_plane_mm": round(
            second_max, 4
        ),
        "minimum_analytic_exterior_recess_mm": round(
            min(-first_max, -second_max), 4
        ),
    }


def make_vertex_hub(
    name: str,
    vertex_index: int,
    normals: list[Vector],
    transformed: list[Vector],
    radius: float,
    recess: float,
    assigned_material: bpy.types.Material,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    vertex = transformed[vertex_index]
    direction = HEAD_CENTER - vertex
    direction.normalize()
    if any(normal.dot(direction) >= -0.02 for normal in normals):
        direction = -sum(normals, Vector())
        if direction.length < 0.01:
            raise ValueError(f"{name}: cannot derive an inboard hub direction")
        direction.normalize()
    target = radius + recess
    required = []
    for normal in normals:
        projection = -normal.dot(direction)
        if projection <= 0.02:
            raise ValueError(
                f"{name}: hub direction does not enter all exterior planes"
            )
        required.append(target / projection)
    center = vertex + direction * max(required)
    bpy.ops.mesh.primitive_ico_sphere_add(
        subdivisions=2,
        radius=radius,
        location=center,
    )
    hub = bpy.context.object
    hub.name = name
    hub.data.materials.append(assigned_material)
    clearances = [
        -(normal.dot(center - vertex) + radius)
        for normal in normals
    ]
    return hub, {
        "name": name,
        "vertex_index": vertex_index,
        "radius_mm": radius,
        "center_head_mm": [round(value, 4) for value in center],
        "minimum_analytic_exterior_recess_mm": round(
            min(clearances), 4
        ),
        "plane_recesses_mm": [
            round(clearance, 4) for clearance in clearances
        ],
    }


def review_duplicate(
    source: bpy.types.Object, name: str
) -> bpy.types.Object:
    duplicate = duplicate_object(source, name)
    duplicate.color = (0.9, 0.18, 0.05, 1.0)
    return duplicate


def aperture_tools(
    part: str,
    values: dict[str, Any],
    context: dict[str, Any],
    frame_config: dict[str, Any],
    material: bpy.types.Material,
) -> tuple[list[bpy.types.Object], list[dict[str, Any]]]:
    glow_index = int(values["glow_face_index"])
    glow_indices, glow_normal, _ = face_geometry(context, glow_index)
    radius = float(frame_config["edge_rib_radius_mm"])
    hub_radius = float(frame_config["vertex_hub_radius_mm"])
    recess = float(frame_config["minimum_exterior_recess_mm"])
    tools: list[bpy.types.Object] = []
    records: list[dict[str, Any]] = []
    opaque_normals: list[Vector] = []
    edges: list[tuple[int, int]] = []
    for sequence, opaque_index in enumerate(
        values["opaque_face_indices"], start=1
    ):
        opaque_indices, opaque_normal, _ = face_geometry(
            context, int(opaque_index)
        )
        edge = shared_edge(glow_indices, opaque_indices)
        rib, record = make_edge_rib(
            f"{part}__aperture_edge_rib_{sequence}",
            *edge,
            glow_normal,
            opaque_normal,
            context["transformed"],
            radius,
            recess,
            material,
        )
        record.update(
            {
                "role": "aperture_edge_rib",
                "glow_face_index": glow_index,
                "opaque_face_index": int(opaque_index),
            }
        )
        tools.append(rib)
        records.append(record)
        opaque_normals.append(opaque_normal)
        edges.append(edge)
    common_vertices = set(edges[0]) & set(edges[1])
    if len(common_vertices) != 1:
        raise ValueError(
            f"{part}: aperture ribs do not meet at one source vertex"
        )
    hub_vertex = next(iter(common_vertices))
    hub, hub_record = make_vertex_hub(
        f"{part}__aperture_vertex_hub",
        hub_vertex,
        [glow_normal, *opaque_normals],
        context["transformed"],
        hub_radius,
        recess,
        material,
    )
    hub_record["role"] = "aperture_vertex_hub"
    tools.append(hub)
    records.append(hub_record)
    return tools, records


def closure_tools(
    part: str,
    closure_indices: list[int],
    context: dict[str, Any],
    frame_config: dict[str, Any],
    material: bpy.types.Material,
) -> tuple[list[bpy.types.Object], list[dict[str, Any]]]:
    oriented, closure_normal, _ = oriented_indices(
        tuple(closure_indices), context["transformed"]
    )
    radius = float(frame_config["edge_rib_radius_mm"])
    hub_radius = float(frame_config["vertex_hub_radius_mm"])
    recess = float(frame_config["minimum_exterior_recess_mm"])
    tools: list[bpy.types.Object] = []
    records: list[dict[str, Any]] = []
    normals_at_vertex: dict[int, list[Vector]] = defaultdict(
        lambda: [closure_normal]
    )
    for offset, first in enumerate(oriented):
        second = oriented[(offset + 1) % len(oriented)]
        edge = tuple(sorted((first, second)))
        adjacent = [
            index
            for index in context["edge_faces"].get(edge, [])
            if context["assignments"][index] == part
        ]
        if len(adjacent) != 1:
            raise ValueError(
                f"{part}: closure edge {edge} expected one adjacent "
                f"source face, found {adjacent}"
            )
        adjacent_index = adjacent[0]
        _, adjacent_normal, _ = face_geometry(
            context, adjacent_index
        )
        rib, record = make_edge_rib(
            f"{part}__closure_edge_rib_{offset + 1}",
            edge[0],
            edge[1],
            closure_normal,
            adjacent_normal,
            context["transformed"],
            radius,
            recess,
            material,
        )
        record.update(
            {
                "role": "bottom_closure_edge_rib",
                "closure_vertex_indices": list(closure_indices),
                "adjacent_face_index": adjacent_index,
            }
        )
        tools.append(rib)
        records.append(record)
        normals_at_vertex[first].append(adjacent_normal)
        normals_at_vertex[second].append(adjacent_normal)
    for sequence, vertex_index in enumerate(oriented, start=1):
        unique_normals = []
        for normal in normals_at_vertex[vertex_index]:
            if not any(
                normal.dot(existing) > 0.9999
                for existing in unique_normals
            ):
                unique_normals.append(normal)
        hub, hub_record = make_vertex_hub(
            f"{part}__closure_vertex_hub_{sequence}",
            vertex_index,
            unique_normals,
            context["transformed"],
            hub_radius,
            recess,
            material,
        )
        hub_record["role"] = "bottom_closure_vertex_hub"
        tools.append(hub)
        records.append(hub_record)
    return tools, records


def collision_summary(
    frame_objects: list[bpy.types.Object],
    cassette: bpy.types.Object,
    metal: dict[str, bpy.types.Object],
) -> dict[str, Any]:
    records = []
    for obj in frame_objects:
        records.append(
            {
                "frame_object": obj.name,
                "cassette": comparison.collision_record(obj, cassette),
                "metal_envelopes": {
                    name: comparison.collision_record(obj, envelope)
                    for name, envelope in metal.items()
                },
            }
        )
    return {
        "records": records,
        "cassette_intersection_count": sum(
            1 for record in records if record["cassette"]["intersects"]
        ),
        "metal_intersection_count": sum(
            1
            for record in records
            for collision in record["metal_envelopes"].values()
            if collision["intersects"]
        ),
    }


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    interface = json.loads(
        (REPO_ROOT / config["shared_interface_path"]).read_text(
            encoding="utf-8"
        )
    )
    if (
        interface["interface_revision"]
        != config["required_interface_revision"]
    ):
        raise ValueError("Shared shell/aluminum interface revision mismatch")
    output_dir = (REPO_ROOT / config["output_namespace"]).resolve()
    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    (output_dir / "shells").mkdir(parents=True, exist_ok=True)
    prefix = config["selected_variant_prefix"]
    context = build_source_context(config)

    for obj in bpy.data.objects:
        obj.hide_render = True
        obj.hide_viewport = True

    frame_material = comparison.create_material(
        "gate9_recessed_aperture_frame", "#E74A2F"
    )
    repaired_material = comparison.create_material(
        "gate9_repaired_shell", "#3985C6"
    )
    repaired: dict[str, bpy.types.Object] = {}
    review_frames: dict[str, list[bpy.types.Object]] = {}
    part_reports: dict[str, Any] = {}
    for part in audit.BODY_PARTS:
        shell = duplicate_object(
            selected_object(prefix, part),
            f"gate9_frame_candidate__{part}",
        )
        shell.data.materials.clear()
        shell.data.materials.append(repaired_material)
        shell.color = (0.18, 0.46, 0.72, 1.0)
        before_components = len(gate5.components(shell))
        tools, records = aperture_tools(
            part,
            config["aperture_connections"][part],
            context,
            config["frame"],
            frame_material,
        )
        if part in config["bottom_closure_connections"]:
            closure, closure_records = closure_tools(
                part,
                config["bottom_closure_connections"][part],
                context,
                config["frame"],
                frame_material,
            )
            tools.extend(closure)
            records.extend(closure_records)
        references = [
            review_duplicate(
                tool, f"review_frame__{part}__{index:02d}"
            )
            for index, tool in enumerate(tools, start=1)
        ]
        for tool in tools:
            gate5.apply_boolean(
                shell,
                tool,
                "UNION",
                solver=config["frame"]["boolean_solver"],
            )
            gate5.require_manifold(
                shell, f"{part} recessed-frame union"
            )
        after_components = len(gate5.components(shell))
        gate5.require_manifold(shell, f"{part} final repaired shell")
        stats = comparison.object_stats(
            shell, (250.0, 210.0, 220.0), 10
        )
        part_reports[part] = {
            "connected_components_before": before_components,
            "connected_components_after": after_components,
            "boundary_edges_after": stats["boundary_edges"],
            "nonmanifold_edges_after": stats["nonmanifold_edges"],
            "frame_features": records,
            "minimum_analytic_exterior_recess_mm": min(
                record["minimum_analytic_exterior_recess_mm"]
                for record in records
            ),
            "dimensions_mm": stats["dimensions_mm"],
            "volume_mm3": stats["volume_mm3"],
        }
        repaired[part] = shell
        review_frames[part] = references
        comparison.export_stl(
            shell, output_dir / "shells" / f"{part}.stl"
        )

    cassette = duplicate_object(
        selected_object(prefix, "rear_cassette"),
        "gate9_frame_candidate__rear_cassette",
    )
    cassette.color = (0.82, 0.52, 0.14, 1.0)
    metal_suffixes = (
        "backplate",
        "rail_left",
        "rail_right",
        "shoe_envelope_left",
        "shoe_envelope_right",
        "shoe_tool_envelope_left",
        "shoe_tool_envelope_right",
        "adapter_hardware_n22_n20",
        "adapter_hardware_n22_p20",
        "adapter_hardware_p22_n20",
        "adapter_hardware_p22_p20",
    )
    metal = {
        suffix: duplicate_object(
            selected_object(prefix, suffix),
            f"gate9_frame_candidate__{suffix}",
        )
        for suffix in metal_suffixes
    }
    for obj in metal.values():
        obj.color = (0.72, 0.74, 0.78, 1.0)
    for part in audit.BODY_PARTS:
        part_reports[part]["frame_keepout_collisions"] = (
            collision_summary(
                review_frames[part], cassette, metal
            )
        )

    camera = audit.configure_workbench_render()
    all_review_objects = [
        *repaired.values(),
        *[
            obj
            for objects in review_frames.values()
            for obj in objects
        ],
        cassette,
        *metal.values(),
    ]
    for part in audit.BODY_PARTS:
        audit.render_part(
            f"{part}__repaired_exterior",
            [repaired[part]],
            all_review_objects,
            output_dir,
            camera,
        )
        audit.render_part(
            f"{part}__internal_frame",
            [repaired[part], *review_frames[part]],
            all_review_objects,
            output_dir,
            camera,
        )
    for obj in all_review_objects:
        obj.hide_render = False
        obj.hide_viewport = False

    blend_path = (
        output_dir / "gate9-aperture-frame-candidate-v1.blend"
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    all_single = all(
        record["connected_components_after"] == 1
        and record["boundary_edges_after"] == 0
        and record["nonmanifold_edges_after"] == 0
        for record in part_reports.values()
    )
    all_recessed = all(
        record["minimum_analytic_exterior_recess_mm"]
        >= float(config["frame"]["minimum_exterior_recess_mm"])
        - 1.0e-4
        for record in part_reports.values()
    )
    keepouts_clear = all(
        record["frame_keepout_collisions"][
            "cassette_intersection_count"
        ]
        == 0
        and record["frame_keepout_collisions"][
            "metal_intersection_count"
        ]
        == 0
        for record in part_reports.values()
    )
    report = {
        "status": config["status"],
        "interface_revision": interface["interface_revision"],
        "config": str(config_path.relative_to(REPO_ROOT)),
        "parts": part_reports,
        "validation": {
            "all_body_shells_one_closed_manifold_component": all_single,
            "all_frame_features_meet_analytic_exterior_recess": (
                all_recessed
            ),
            "all_frame_keepout_envelopes_clear": keepouts_clear,
            "digital_candidate_pass": (
                all_single and all_recessed and keepouts_clear
            ),
        },
        "acceptance_holds": config["acceptance_holds"],
        "generated_review_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "shell_stls": str(
                (output_dir / "shells").relative_to(REPO_ROOT)
            ),
            "renders": str(
                (output_dir / "renders").relative_to(REPO_ROOT)
            ),
        },
    }
    report_path = (
        output_dir / "gate9-aperture-frame-candidate-v1.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "validation": report["validation"],
                "parts": {
                    part: {
                        "components_before": value[
                            "connected_components_before"
                        ],
                        "components_after": value[
                            "connected_components_after"
                        ],
                        "minimum_recess_mm": value[
                            "minimum_analytic_exterior_recess_mm"
                        ],
                        "cassette_intersections": value[
                            "frame_keepout_collisions"
                        ]["cassette_intersection_count"],
                        "metal_intersections": value[
                            "frame_keepout_collisions"
                        ]["metal_intersection_count"],
                    }
                    for part, value in part_reports.items()
                },
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )
    if not report["validation"]["digital_candidate_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
