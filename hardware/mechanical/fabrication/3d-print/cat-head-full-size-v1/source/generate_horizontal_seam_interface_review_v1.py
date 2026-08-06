#!/usr/bin/env python3
"""Generate one scoped horizontal cassette-boundary rail review.

Only a mirrored rail pair along the longest MANQ007 horizontal V5 boundary is
new. Rejected C006 rails and C002 eye mounts are hidden reference geometry.
Nothing is Boolean-unioned or released for production.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_lower_reinforcement_ownership_review_v1 as reinforcement_v1  # noqa: E402
import generate_rear_cassette_lossless_repartition_review_v5 as v5  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/horizontal-seam-interface-review-v1.json"
DEFAULT_OUTPUT = PACKAGE_ROOT / "output/30-reinforcement-baselines/horizontal-seam-interface-review-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def hex_color(value: str) -> tuple[float, float, float, float]:
    clean = value.lstrip("#")
    return tuple(int(clean[offset : offset + 2], 16) / 255.0 for offset in (0, 2, 4)) + (1.0,)


def curve_fingerprint(obj: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    for spline in obj.data.splines:
        digest.update(f"spline:{spline.type}\n".encode())
        for point in spline.points:
            world = obj.matrix_world @ Vector(point.co[:3])
            digest.update(f"{world.x:.9f},{world.y:.9f},{world.z:.9f}\n".encode())
    return digest.hexdigest()


def edge_faces(model: Any) -> dict[tuple[int, int], list[int]]:
    output: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(model.faces):
        for offset, first in enumerate(face.indices):
            second = face.indices[(offset + 1) % len(face.indices)]
            output[tuple(sorted((first, second)))].append(face_index)
    return output


def canonical_endpoints(points: list[Vector]) -> list[list[float]]:
    return sorted([[round(axis, 6) for axis in point] for point in points])


def find_target_edge(
    model: Any,
    points: list[Vector],
    cassette_indices: set[int],
    panel_id: str,
    target_config: dict[str, Any],
) -> tuple[tuple[int, int], int]:
    adjacency = edge_faces(model)
    tolerance = float(target_config["horizontal_axis_tolerance_mm"])
    candidates = []
    for face_index in sorted(cassette_indices):
        face = model.faces[face_index]
        if gate1.canonical_source_panel_id(face.group) != panel_id:
            continue
        for offset, first in enumerate(face.indices):
            second = face.indices[(offset + 1) % len(face.indices)]
            edge = tuple(sorted((first, second)))
            p0, p1 = points[edge[0]], points[edge[1]]
            delta = p1 - p0
            if (
                abs(delta.y) <= tolerance
                and abs(delta.z) <= tolerance
                and delta.length > 80.0
                and len(adjacency[edge]) == 1
            ):
                candidates.append((edge, face_index))
    if len(candidates) != 1:
        raise ValueError(
            f"Expected one long exposed horizontal edge on {panel_id}: {candidates}"
        )
    return candidates[0]


def validate_expected_edge(
    edge: tuple[int, int],
    points: list[Vector],
    section_config: dict[str, Any],
    target_config: dict[str, Any],
) -> None:
    actual = canonical_endpoints([points[index] for index in edge])
    expected = canonical_endpoints(
        [Vector(value) for value in section_config["expected_endpoints_mm"]]
    )
    tolerance = float(target_config["endpoint_tolerance_mm"])
    for actual_point, expected_point in zip(actual, expected):
        if (Vector(actual_point) - Vector(expected_point)).length > tolerance:
            raise ValueError(f"Target boundary endpoint changed: {actual} != {expected}")
    length = (points[edge[1]] - points[edge[0]]).length
    if abs(length - float(target_config["expected_edge_length_mm"])) > tolerance:
        raise ValueError(f"Target boundary length changed: {length}")


def create_rail(
    section: str,
    edge: tuple[int, int],
    face_index: int,
    model: Any,
    points: list[Vector],
    values: dict[str, Any],
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    p0, p1 = points[edge[0]], points[edge[1]]
    tangent = (p1 - p0).normalized()
    midpoint = p0.lerp(p1, 0.5)
    face = model.faces[face_index]
    normal = gate5.outward_normal(face, points).normalized()
    face_center = sum((points[index] for index in face.indices), Vector()) / len(
        face.indices
    )
    toward_face = face_center - midpoint
    toward_face -= normal * toward_face.dot(normal)
    toward_face -= tangent * toward_face.dot(tangent)
    if toward_face.length <= 1e-6:
        raise ValueError(f"Cannot derive panel-inward direction for {section}")
    toward_face.normalize()

    foot_width = float(values["foot_width_mm"])
    depth = float(values["inward_depth_mm"])
    seam_inset = float(values["seam_inset_mm"])
    overlap = float(values["shell_overlap_mm"])
    wall = float(values["shell_wall_thickness_mm"])
    end_setback = float(values["end_setback_mm"])
    length = (p1 - p0).length - 2.0 * end_setback
    center = (
        midpoint
        + toward_face * (seam_inset + foot_width / 2.0)
        - normal * (wall + depth / 2.0 - overlap)
    )
    name = f"H1_PROPOSED__{section}__MANQ007_horizontal_boundary_rail"
    rail = gate5.box(
        name,
        center,
        (tangent, toward_face, normal),
        (length, foot_width, depth),
        material,
    )
    for source_collection in list(rail.users_collection):
        source_collection.objects.unlink(rail)
    collection.objects.link(rail)
    rail["review_only"] = True
    rail["source_section"] = section
    rail["source_panel_id"] = gate1.canonical_source_panel_id(face.group)
    rail["target_boundary_edge"] = json.dumps(list(edge))
    rail["candidate_status"] = "proposed horizontal boundary reinforcement only"
    rail["fastener_hole_count"] = 0
    boundary, nonmanifold = gate5.topology_counts(rail)
    return rail, {
        "section": section,
        "source_panel_id": gate1.canonical_source_panel_id(face.group),
        "boundary_edge_vertex_indices": list(edge),
        "boundary_endpoints_mm": [list(p0), list(p1)],
        "boundary_length_mm": (p1 - p0).length,
        "rail_center_mm": list(center),
        "rail_axes": {
            "tangent": list(tangent),
            "toward_panel": list(toward_face),
            "outward_normal": list(normal),
        },
        "rail_dimensions_mm": [length, foot_width, depth],
        "boundary_coverage_ratio": length / (p1 - p0).length,
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "volume_mm3": gate5.mesh_volume(rail),
        "review_object": rail.name,
    }


def mirrored_vertex_tokens(
    obj: bpy.types.Object,
    mirror_x: bool,
) -> list[tuple[float, float, float]]:
    output = []
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        if mirror_x:
            point.x = -point.x
        output.append(tuple(round(axis, 5) for axis in point))
    return sorted(output)


def minimum_vertex_distance(
    first: bpy.types.Object,
    second: bpy.types.Object,
) -> float:
    first_points = [first.matrix_world @ vertex.co for vertex in first.data.vertices]
    second_points = [second.matrix_world @ vertex.co for vertex in second.data.vertices]
    return min((a - b).length for a in first_points for b in second_points)


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def configure_scene(output_dir: Path, resolution_px: int) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.name = "Horizontal_Seam_Interface_Review_V1"
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "OBJECT"
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    shading.curvature_ridge_factor = 2.0
    shading.curvature_valley_factor = 1.5
    shading.background_type = "VIEWPORT"
    shading.background_color = (0.035, 0.045, 0.06)
    scene.render.resolution_x = resolution_px
    scene.render.resolution_y = resolution_px
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    camera_data = bpy.data.cameras.new("H1_REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("H1_REVIEW_ONLY__Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 54.0
    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    return camera


def render_views(
    camera: bpy.types.Object,
    output_dir: Path,
    prefix: str,
    visible: set[bpy.types.Object],
) -> list[str]:
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_render = obj not in visible
    target = Vector((0.0, 185.0, 62.0))
    views = (
        ("rear", Vector((0.0, 525.0, 165.0))),
        ("rear-left", Vector((-350.0, 460.0, 190.0))),
        ("rear-right", Vector((350.0, 460.0, 190.0))),
        ("front", Vector((0.0, -450.0, 160.0))),
    )
    paths = []
    for label, location in views:
        camera.location = location
        point_at(camera, target)
        path = output_dir / "renders" / f"{prefix}-{label}.png"
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        paths.append(str(path.relative_to(REPO_ROOT)))
    return paths


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_blend = repo_path(config["source_reinforcement_review_blend"])
    if Path(bpy.data.filepath).resolve() != source_blend:
        raise ValueError(f"Open the configured R1 blend before running: {source_blend}")
    interface_path = repo_path(config["shared_interface_path"])
    interface = json.loads(interface_path.read_text(encoding="utf-8"))
    if interface["interface_revision"] != config["required_interface_revision"]:
        raise ValueError("Shared shell/aluminum interface revision changed")
    output_dir.mkdir(parents=True, exist_ok=True)

    protected_meshes_before = {
        obj.name: v5.mesh_fingerprint(obj)
        for obj in bpy.data.objects
        if obj.type == "MESH"
    }
    protected_curves_before = {
        obj.name: curve_fingerprint(obj)
        for obj in bpy.data.objects
        if obj.name.startswith("V5_BOUNDARY__")
    }

    reinforcement_config = json.loads(
        repo_path(config["source_reinforcement_review_config"]).read_text(
            encoding="utf-8"
        )
    )
    model, _assignments, points, _retained, cassette = (
        reinforcement_v1.build_ownership_sets(reinforcement_config, interface)
    )
    proposed_collection = bpy.data.collections.new(
        "H1_PROPOSED_HORIZONTAL_MANQ007_RAILS"
    )
    reference_collection = bpy.data.collections.new(
        "H1_UNCHANGED_REINFORCEMENT_REFERENCE"
    )
    rejected_collection = bpy.data.collections.new("H1_REJECTED_SOURCE_REFERENCE")
    boundary_collection = bpy.data.collections.new("H1_APPROVED_V5_BOUNDARY_REFERENCE")
    for collection in (
        proposed_collection,
        reference_collection,
        rejected_collection,
        boundary_collection,
    ):
        bpy.context.scene.collection.children.link(collection)

    proposed_material = gate5.material(
        "H1__Proposed_Horizontal_Rail_Green",
        hex_color(config["review_display"]["proposed_rail_color"]),
    )
    rail_objects = []
    rail_records = []
    for section in ("left_lower_face", "right_lower_face"):
        section_config = config["target_boundary"][section]
        edge, face_index = find_target_edge(
            model,
            points,
            cassette[section],
            section_config["panel_id"],
            config["target_boundary"],
        )
        validate_expected_edge(
            edge, points, section_config, config["target_boundary"]
        )
        rail, record = create_rail(
            section,
            edge,
            face_index,
            model,
            points,
            config["proposed_rail"],
            proposed_collection,
            proposed_material,
        )
        rail.color = hex_color(config["review_display"]["proposed_rail_color"])
        rail_objects.append(rail)
        rail_records.append(record)

    left_rail, right_rail = rail_objects
    mirrored_geometry_matches = mirrored_vertex_tokens(
        left_rail, mirror_x=True
    ) == mirrored_vertex_tokens(right_rail, mirror_x=False)
    if not mirrored_geometry_matches:
        raise ValueError("Proposed left/right horizontal rails are not exact X mirrors")
    if any(record["boundary_edges"] or record["nonmanifold_edges"] for record in rail_records):
        raise ValueError("A proposed review rail is not closed and manifold")

    excluded_objects = []
    for name in config["excluded_source_objects"]:
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise ValueError(f"Missing rejected review object {name}")
        rejected_collection.objects.link(obj)
        obj.hide_viewport = True
        obj.hide_render = True
        obj["candidate_status"] = "rejected by user; hidden reference only"
        excluded_objects.append(obj)

    integrated_collection_name = "R1_INTEGRATED_SHELL_PLUS_REINFORCEMENT"
    unchanged_objects = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.name.startswith("R1_"):
            continue
        if obj in excluded_objects:
            continue
        if any(collection.name == integrated_collection_name for collection in obj.users_collection):
            continue
        reference_collection.objects.link(obj)
        obj.color = hex_color(
            config["review_display"]["unchanged_reinforcement_color"]
        )
        unchanged_objects.append(obj)

    seam_objects = []
    for name in ("V5_BOUNDARY__left_lower_face", "V5_BOUNDARY__right_lower_face"):
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise ValueError(f"Missing approved boundary reference {name}")
        boundary_collection.objects.link(obj)
        obj.color = hex_color(config["review_display"]["boundary_color"])
        obj.show_in_front = True
        seam_objects.append(obj)

    context_shells = {
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and (
            obj.name.startswith("V5_RETAINED__")
            or obj.name.startswith("V5_CASSETTE__moved_from_")
        )
    }
    for obj in context_shells:
        obj.display_type = "WIRE"
        obj.show_in_front = True

    proposed_set = set(rail_objects)
    reference_set = set(unchanged_objects)
    seam_set = set(seam_objects)
    default_visible = proposed_set | reference_set | seam_set | context_shells
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in default_visible
            obj.hide_render = True

    camera = configure_scene(
        output_dir, int(config["review_display"]["render_resolution_px"])
    )
    render_paths = render_views(
        camera,
        output_dir,
        "horizontal-seam-rails-with-existing-frame",
        proposed_set | reference_set | seam_set,
    )
    render_paths.extend(
        render_views(
            camera,
            output_dir,
            "horizontal-seam-rails-isolated",
            proposed_set | seam_set,
        )
    )
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in default_visible
            obj.hide_render = obj not in (proposed_set | reference_set | seam_set)
    camera.location = Vector((0.0, 525.0, 165.0))
    point_at(camera, Vector((0.0, 185.0, 62.0)))

    protected_meshes_after = {
        name: v5.mesh_fingerprint(bpy.data.objects[name])
        for name in protected_meshes_before
    }
    protected_curves_after = {
        name: curve_fingerprint(bpy.data.objects[name])
        for name in protected_curves_before
    }
    if protected_meshes_before != protected_meshes_after:
        raise ValueError("A pre-existing review/source mesh changed")
    if protected_curves_before != protected_curves_after:
        raise ValueError("An approved V5 boundary curve changed")

    excluded_clearances = {
        rail.name: {
            excluded.name: round(minimum_vertex_distance(rail, excluded), 3)
            for excluded in excluded_objects
        }
        for rail in rail_objects
    }
    scene = bpy.context.scene
    scene["review_status"] = config["status"]
    scene["proposed_change"] = "one mirrored MANQ007 horizontal rail pair"
    scene["excluded_source_objects"] = json.dumps(config["excluded_source_objects"])
    scene["source_geometry_unchanged"] = True
    blend_path = output_dir / "horizontal-seam-interface-review-v1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "source_reinforcement_review_blend": str(source_blend.relative_to(REPO_ROOT)),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "interface_revision": interface["interface_revision"],
        "target_boundary_rule": config["target_boundary"],
        "proposed_rail_dimensions": config["proposed_rail"],
        "rail_records": rail_records,
        "mirrored_geometry_matches": mirrored_geometry_matches,
        "all_proposed_rails_closed_and_manifold": all(
            record["boundary_edges"] == 0 and record["nonmanifold_edges"] == 0
            for record in rail_records
        ),
        "excluded_source_objects": config["excluded_source_objects"],
        "excluded_objects_preserved_but_hidden": all(
            obj.hide_viewport and obj.hide_render for obj in excluded_objects
        ),
        "proposed_to_excluded_vertex_clearance_mm": excluded_clearances,
        "protected_preexisting_mesh_count": len(protected_meshes_before),
        "protected_preexisting_mesh_geometry_unchanged": protected_meshes_before
        == protected_meshes_after,
        "approved_v5_boundary_geometry_unchanged": protected_curves_before
        == protected_curves_after,
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": render_paths,
        },
        "no_stl_or_gcode_exported": True,
        "review_holds": config["review_holds"],
    }
    report_path = output_dir / "horizontal-seam-interface-review-v1-validation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "proposed_rail_count": len(rail_records),
                "rail_dimensions_mm": [
                    [round(value, 3) for value in record["rail_dimensions_mm"]]
                    for record in rail_records
                ],
                "boundary_coverage_ratio": [
                    round(record["boundary_coverage_ratio"], 6)
                    for record in rail_records
                ],
                "mirrored_geometry_matches": report["mirrored_geometry_matches"],
                "all_proposed_rails_closed_and_manifold": report[
                    "all_proposed_rails_closed_and_manifold"
                ],
                "protected_preexisting_mesh_geometry_unchanged": report[
                    "protected_preexisting_mesh_geometry_unchanged"
                ],
                "approved_v5_boundary_geometry_unchanged": report[
                    "approved_v5_boundary_geometry_unchanged"
                ],
                "blend": report["generated_files"]["blend"],
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
