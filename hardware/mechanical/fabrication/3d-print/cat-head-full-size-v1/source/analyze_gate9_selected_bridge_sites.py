#!/usr/bin/env python3
"""Audit broad bridge sites for the selected Gate 9 shell components."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import bpy
import bmesh
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate3_structural_shells as gate3  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/gate9-rear-architecture-comparison-v1.json"
)
DEFAULT_VARIANT_DIR = (
    PACKAGE_ROOT
    / "output/gate9-rear-architecture-comparison-v1/variants"
    / "rear_cassette_full_scale"
)
DEFAULT_OUTPUT = (
    PACKAGE_ROOT
    / "output/gate9-selected-bridge-site-audit-v1"
)
BODY_PARTS = (
    "left_upper_head",
    "right_upper_head",
    "left_lower_face",
    "right_lower_face",
)
COMPONENT_COLORS = (
    (0.16, 0.55, 0.95, 1.0),
    (0.96, 0.62, 0.12, 1.0),
    (0.35, 0.82, 0.42, 1.0),
    (0.78, 0.34, 0.88, 1.0),
)
BRIDGE_COLOR = (0.95, 0.12, 0.12, 1.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--variant-dir", type=Path, default=DEFAULT_VARIANT_DIR
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--candidate-bridge-diameter-mm", type=float, default=14.0
    )
    parser.add_argument(
        "--candidate-end-overlap-mm", type=float, default=6.0
    )
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(args)


def import_stl(path: Path, name: str) -> bpy.types.Object:
    bpy.ops.object.select_all(action="DESELECT")
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=str(path))
    else:
        bpy.ops.import_mesh.stl(filepath=str(path))
    obj = bpy.context.selected_objects[0]
    obj.name = name
    return obj


def split_loose_parts(
    obj: bpy.types.Object, part_name: str
) -> list[bpy.types.Object]:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    separated = list(bpy.context.selected_objects)
    separated.sort(
        key=lambda item: len(item.data.polygons), reverse=True
    )
    for index, component in enumerate(separated):
        component.name = f"{part_name}__component_{index + 1}"
        component.color = COMPONENT_COLORS[
            index % len(COMPONENT_COLORS)
        ]
    return separated


def object_component_stats(obj: bpy.types.Object) -> dict[str, Any]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    minimum = Vector(
        tuple(min(point[axis] for point in points) for axis in range(3))
    )
    maximum = Vector(
        tuple(max(point[axis] for point in points) for axis in range(3))
    )
    centroid = sum(points, Vector()) / len(points)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary_edges = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    nonmanifold_edges = sum(1 for edge in bm.edges if not edge.is_manifold)
    volume = (
        abs(float(bm.calc_volume(signed=True)))
        if boundary_edges == 0
        else None
    )
    bm.free()
    return {
        "vertices": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "volume_mm3": round(volume, 3) if volume is not None else None,
        "bounds_min_head_mm": [
            round(value, 3) for value in minimum
        ],
        "bounds_max_head_mm": [
            round(value, 3) for value in maximum
        ],
        "dimensions_mm": [
            round(maximum[index] - minimum[index], 3)
            for index in range(3)
        ],
        "centroid_head_mm": [
            round(value, 3) for value in centroid
        ],
    }


def closest_vertex_pair(
    first: bpy.types.Object,
    second: bpy.types.Object,
) -> tuple[Vector, Vector, float]:
    first_points = [
        first.matrix_world @ vertex.co for vertex in first.data.vertices
    ]
    second_points = [
        second.matrix_world @ vertex.co
        for vertex in second.data.vertices
    ]
    best_first = first_points[0]
    best_second = second_points[0]
    best_distance = math.inf
    for first_point in first_points:
        for second_point in second_points:
            distance = (second_point - first_point).length
            if distance < best_distance:
                best_distance = distance
                best_first = first_point
                best_second = second_point
    return best_first, best_second, best_distance


def create_bridge_candidate(
    name: str,
    first: Vector,
    second: Vector,
    diameter_mm: float,
    overlap_mm: float,
) -> bpy.types.Object:
    direction = (second - first).normalized()
    center = (first + second) / 2.0
    length = (second - first).length + 2.0 * overlap_mm
    bridge = comparison.create_oriented_cylinder(
        name,
        center,
        direction,
        diameter_mm,
        length,
        comparison.create_material(
            f"{name}_material", "#F12626"
        ),
        vertices=32,
    )
    bridge.color = BRIDGE_COLOR
    bridge["review_only_candidate"] = True
    bridge["candidate_diameter_mm"] = diameter_mm
    bridge["candidate_end_overlap_mm"] = overlap_mm
    return bridge


def all_pair_candidates(
    part_name: str,
    components: list[bpy.types.Object],
    diameter_mm: float,
    overlap_mm: float,
) -> tuple[list[bpy.types.Object], list[dict[str, Any]]]:
    bridges = []
    records = []
    primary = components[0]
    for index, component in enumerate(components[1:], start=2):
        first, second, distance = closest_vertex_pair(primary, component)
        bridge = create_bridge_candidate(
            f"{part_name}__bridge_to_component_{index}",
            first,
            second,
            diameter_mm,
            overlap_mm,
        )
        bridges.append(bridge)
        records.append(
            {
                "primary_component": primary.name,
                "target_component": component.name,
                "closest_point_primary_head_mm": [
                    round(value, 3) for value in first
                ],
                "closest_point_target_head_mm": [
                    round(value, 3) for value in second
                ],
                "surface_sample_distance_mm": round(distance, 3),
                "candidate_bridge_diameter_mm": diameter_mm,
                "candidate_end_overlap_mm": overlap_mm,
                "candidate_bridge_length_mm": round(
                    distance + 2.0 * overlap_mm, 3
                ),
            }
        )
    return bridges, records


def object_bounds_center(
    objects: list[bpy.types.Object],
) -> tuple[Vector, Vector]:
    points = [
        obj.matrix_world @ vertex.co
        for obj in objects
        for vertex in obj.data.vertices
    ]
    minimum = Vector(
        tuple(min(point[axis] for point in points) for axis in range(3))
    )
    maximum = Vector(
        tuple(max(point[axis] for point in points) for axis in range(3))
    )
    return (minimum + maximum) / 2.0, maximum - minimum


def point_camera(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (
        target - camera.location
    ).to_track_quat("-Z", "Y").to_euler()


def configure_workbench_render() -> bpy.types.Object:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 820
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.studio_light = "paint.sl"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "WORLD"
    scene.display.shading.curvature_ridge_factor = 1.8
    scene.display.shading.curvature_valley_factor = 1.4
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.055, 0.065, 0.08)

    camera_data = bpy.data.cameras.new("Bridge_Audit_Camera")
    camera = bpy.data.objects.new("Bridge_Audit_Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = "ORTHO"
    return camera


def render_part(
    part_name: str,
    visible: list[bpy.types.Object],
    all_review_objects: list[bpy.types.Object],
    output_dir: Path,
    camera: bpy.types.Object,
) -> None:
    for obj in all_review_objects:
        obj.hide_render = obj not in visible
    target, dimensions = object_bounds_center(visible)
    camera.data.ortho_scale = max(dimensions) * 1.28
    views = (
        ("front", Vector((0.0, -650.0, 0.0))),
        ("rear", Vector((0.0, 650.0, 0.0))),
        ("side", Vector((-650.0, 0.0, 0.0))),
        ("bottom-oblique", Vector((-430.0, -420.0, -330.0))),
    )
    for suffix, direction in views:
        camera.location = target + direction
        point_camera(camera, target)
        bpy.context.scene.render.filepath = str(
            output_dir / "renders" / f"{part_name}__{suffix}.png"
        )
        bpy.ops.render.render(write_still=True)


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    interface = json.loads(
        (
            REPO_ROOT / config["shared_interface_path"]
        ).read_text(encoding="utf-8")
    )
    variant_dir = args.variant_dir.resolve()
    output_dir = args.output_dir.resolve()
    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    gate3.clean_scene()

    component_objects: dict[str, list[bpy.types.Object]] = {}
    bridge_objects: dict[str, list[bpy.types.Object]] = {}
    report_parts: dict[str, Any] = {}
    for part in BODY_PARTS:
        imported = import_stl(variant_dir / f"{part}.stl", part)
        components = split_loose_parts(imported, part)
        bridges, bridge_records = all_pair_candidates(
            part,
            components,
            args.candidate_bridge_diameter_mm,
            args.candidate_end_overlap_mm,
        )
        component_objects[part] = components
        bridge_objects[part] = bridges
        report_parts[part] = {
            "component_count": len(components),
            "components": [
                object_component_stats(component)
                for component in components
            ],
            "closest_pair_bridge_candidates": bridge_records,
        }

    cassette = import_stl(
        variant_dir / "rear_cassette.stl", "rear_cassette"
    )
    cassette.color = (0.54, 0.58, 0.64, 1.0)
    envelope_materials = {
        key: comparison.create_material(
            f"bridge_audit_{key}",
            color,
            0.35,
        )
        for key, color in comparison.SECTION_COLORS.items()
        if key in {"backplate", "rail", "shoe", "tool", "hardware"}
    }
    metal = comparison.create_interface_envelopes(
        "bridge_audit",
        interface,
        config["provisional_collision_envelopes"],
        envelope_materials,
    )
    for obj in metal.values():
        obj.color = (0.72, 0.74, 0.78, 1.0)

    for part, bridges in bridge_objects.items():
        collision_records = []
        for bridge in bridges:
            collision_records.append(
                {
                    "bridge": bridge.name,
                    "cassette": comparison.collision_record(
                        bridge, cassette
                    ),
                    "metal_envelopes": {
                        name: comparison.collision_record(
                            bridge, envelope
                        )
                        for name, envelope in metal.items()
                    },
                }
            )
        report_parts[part]["candidate_keepout_collisions"] = (
            collision_records
        )

    camera = configure_workbench_render()
    all_review_objects = [
        *[
            obj
            for objects in component_objects.values()
            for obj in objects
        ],
        *[
            obj for objects in bridge_objects.values() for obj in objects
        ],
        cassette,
        *metal.values(),
    ]
    for part in BODY_PARTS:
        render_part(
            part,
            [*component_objects[part], *bridge_objects[part]],
            all_review_objects,
            output_dir,
            camera,
        )
    for obj in all_review_objects:
        obj.hide_render = False
    bpy.ops.wm.save_as_mainfile(
        filepath=str(output_dir / "gate9-selected-bridge-site-audit-v1.blend")
    )

    report = {
        "status": "review_only_bridge_site_audit",
        "interface_revision": interface["interface_revision"],
        "selected_variant": "rear_cassette_full_scale",
        "candidate_bridge_policy": {
            "diameter_mm": args.candidate_bridge_diameter_mm,
            "end_overlap_mm": args.candidate_end_overlap_mm,
            "meaning": "visual/collision envelope only; not approved production geometry",
        },
        "parts": report_parts,
        "acceptance_holds": [
            "closest-point candidates must be visually confirmed to remain fully inboard and away from eye/glow openings",
            "every accepted bridge must boolean-union into one closed body and pass exact topology validation",
            "bridges must not intersect cassette, metal, shoe, hardware, tool, wiring, sealing, drainage, or assembly keep-outs",
            "bridge cross sections must be broad and gusseted; thin flying tabs are prohibited",
        ],
    }
    report_path = output_dir / "gate9-selected-bridge-site-audit-v1.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "parts": {
                    part: {
                        "component_count": value["component_count"],
                        "bridge_candidates": value[
                            "closest_pair_bridge_candidates"
                        ],
                        "cassette_collision_count": sum(
                            1
                            for record in value[
                                "candidate_keepout_collisions"
                            ]
                            if record["cassette"]["intersects"]
                        ),
                        "metal_envelope_collision_count": sum(
                            1
                            for record in value[
                                "candidate_keepout_collisions"
                            ]
                            for collision in record[
                                "metal_envelopes"
                            ].values()
                            if collision["intersects"]
                        ),
                    }
                    for part, value in report_parts.items()
                },
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
