#!/usr/bin/env python3
"""Build a lower-face-only Gate 8 rear-cassette ownership review.

This script opens the unchanged Gate 8 review blend, removes review-only
reference objects, keeps both upper-head pieces unchanged, and shows only rear
facets from the lower faces plus an unchanged orange copy of rear_base. It does
not alter any Gate 8 production mesh and exports no STL or G-code.
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
import generate_gate2_section_layout as gate2  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/rear-cassette-seam-review-v2.json"
DEFAULT_OUTPUT = PACKAGE_ROOT / "output/rear-cassette-seam-review-v2"
ALLOWED_CASSETTE_SOURCE_SECTIONS = {
    "right_lower_face",
    "left_lower_face",
}
PRODUCTION_PARTS = {
    "left_ear",
    "left_eye_bucket",
    "left_eye_diffuser",
    "left_eye_led_rear_cap",
    "left_lower_face",
    "left_upper_head",
    "rear_base",
    "right_ear",
    "right_eye_bucket",
    "right_eye_diffuser",
    "right_eye_led_rear_cap",
    "right_lower_face",
    "right_upper_head",
    "glow_insert_central_6_panel_cluster",
    "glow_insert_left_ear_root_cluster",
    "glow_insert_panel_QUAD003",
    "glow_insert_panel_QUAD005",
    "glow_insert_panel_QUAD017",
    "glow_insert_panel_QUAD031",
    "glow_insert_right_ear_root_cluster",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_material(
    name: str,
    color_hex: str,
    alpha: float = 1.0,
    metallic: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    rgb = tuple(
        int(color_hex[index : index + 2], 16) / 255.0
        for index in (1, 3, 5)
    )
    material.diffuse_color = (*rgb, alpha)
    material.use_nodes = True
    shader = material.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = (*rgb, 1.0)
        shader.inputs["Roughness"].default_value = 0.34
        shader.inputs["Metallic"].default_value = metallic
        shader.inputs["Alpha"].default_value = alpha
    if alpha < 1.0 and hasattr(material, "surface_render_method"):
        material.surface_render_method = "DITHERED"
    return material


def clean_gate8_scene() -> tuple[list[str], dict[str, tuple[int, int]]]:
    missing = sorted(PRODUCTION_PARTS - set(bpy.data.objects.keys()))
    if missing:
        raise ValueError(f"Gate 8 review blend is missing production parts: {missing}")

    removed: list[str] = []
    for obj in list(bpy.data.objects):
        if obj.name not in PRODUCTION_PARTS:
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)

    production_collection = bpy.data.collections.new("UNCHANGED_GATE8_PRODUCTION")
    bpy.context.scene.collection.children.link(production_collection)
    mesh_stats: dict[str, tuple[int, int]] = {}
    for name in sorted(PRODUCTION_PARTS):
        obj = bpy.data.objects[name]
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        production_collection.objects.link(obj)
        if obj.type == "MESH":
            mesh_stats[name] = (len(obj.data.vertices), len(obj.data.polygons))
        obj["geometry_role"] = "unchanged Gate 8 production object"

    rear_base = bpy.data.objects["rear_base"]
    rear_base.hide_viewport = True
    rear_base.hide_render = True
    rear_base["candidate_view_status"] = (
        "hidden only because the proposed rear cassette replaces it"
    )
    return sorted(removed), mesh_stats


def create_rear_base_overlay(
    material: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    source = bpy.data.objects["rear_base"]
    overlay = source.copy()
    overlay.data = source.data.copy()
    overlay.name = "REVIEW_ONLY__existing_rear_base_cassette_overlay"
    overlay.data.name = f"{overlay.name}_mesh"
    overlay.hide_viewport = False
    overlay.hide_render = False
    collection.objects.link(overlay)
    overlay.data.materials.clear()
    overlay.data.materials.append(material)
    if "geometry_role" in overlay:
        del overlay["geometry_role"]
    if "candidate_view_status" in overlay:
        del overlay["candidate_view_status"]
    overlay["review_only"] = True
    overlay["not_printable"] = True
    overlay["meaning"] = (
        "unchanged Gate 8 rear_base included in proposed cassette ownership"
    )
    return overlay


def source_selection(
    config: dict[str, Any],
    interface: dict[str, Any],
) -> tuple[
    gate1.ObjModel,
    list[str],
    list[tuple[float, float, float]],
    set[int],
    set[tuple[int, int]],
]:
    gate2_config = json.loads(
        repo_path(config["source_gate2_config"]).read_text(encoding="utf-8")
    )
    gate1_config = json.loads(gate1.DEFAULT_CONFIG.read_text(encoding="utf-8"))
    source_model = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    units = gate1.panel_units(
        source_model,
        gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV),
    )
    source_scale, source_origin, _ = gate1.make_transform(
        gate1.bounds(source_model.vertices),
        float(config["head_height_mm"]),
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
    points = [
        gate1.transform_point(vertex, source_scale, source_origin)
        for vertex in model.vertices
    ]

    plane = interface["rear_interface_plane"]
    plane_center = Vector(plane["center_head_mm"])
    plane_normal = Vector(plane["outward_normal_head"]).normalized()
    threshold = float(
        config["rear_cassette_cut"]["rear_plane_threshold_mm"]
    )
    source_sections = set(
        config["rear_cassette_cut"]["source_sections"]
    )
    if source_sections != ALLOWED_CASSETTE_SOURCE_SECTIONS:
        raise ValueError(
            "V2 permits cassette facet ownership only from both lower-face sections"
        )
    selected: set[int] = set()
    for index, (face, assignment) in enumerate(zip(model.faces, assignments)):
        if assignment not in source_sections:
            continue
        centroid = sum(
            (Vector(points[vertex]) for vertex in face.indices),
            Vector(),
        ) / len(face.indices)
        signed_distance = float((centroid - plane_center).dot(plane_normal))
        if signed_distance >= threshold:
            selected.add(index)
    if not selected:
        raise ValueError("Rear-cassette cut selected no body facets")

    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for face_index, face in enumerate(model.faces):
        indices = face.indices
        for offset, first in enumerate(indices):
            second = indices[(offset + 1) % len(indices)]
            edge_faces[tuple(sorted((first, second)))].append(face_index)

    seam_edges: set[tuple[int, int]] = set()
    for edge, adjacent in edge_faces.items():
        has_selected = any(index in selected for index in adjacent)
        has_retained_body = any(
            index not in selected and assignments[index] in source_sections
            for index in adjacent
        )
        if has_selected and has_retained_body:
            seam_edges.add(edge)
    if not seam_edges:
        raise ValueError("Rear-cassette cut produced no body seam")
    return model, assignments, points, selected, seam_edges


def outward_offset_points(
    model: gate1.ObjModel,
    points: list[tuple[float, float, float]],
    selected: set[int],
    offset_mm: float,
) -> dict[int, tuple[float, float, float]]:
    used = sorted(
        {
            vertex
            for face_index in selected
            for vertex in model.faces[face_index].indices
        }
    )
    center = sum((Vector(point) for point in points), Vector()) / len(points)
    normal_sums: dict[int, Vector] = defaultdict(Vector)
    for face_index in selected:
        face = model.faces[face_index]
        coordinates = [Vector(points[index]) for index in face.indices]
        normal = (coordinates[1] - coordinates[0]).cross(
            coordinates[2] - coordinates[0]
        )
        if normal.length <= 1e-9:
            continue
        normal.normalize()
        centroid = sum(coordinates, Vector()) / len(coordinates)
        if normal.dot(centroid - center) < 0.0:
            normal.negate()
        for vertex in face.indices:
            normal_sums[vertex] = normal_sums[vertex] + normal

    offset_points: dict[int, tuple[float, float, float]] = {}
    for vertex in used:
        normal = normal_sums[vertex]
        if normal.length > 1e-9:
            normal.normalize()
        offset_points[vertex] = tuple(Vector(points[vertex]) + normal * offset_mm)
    return offset_points


def create_surface(
    name: str,
    model: gate1.ObjModel,
    points_by_source_index: dict[int, tuple[float, float, float]],
    selected: set[int],
    material: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    used = sorted(points_by_source_index)
    remap = {source: local for local, source in enumerate(used)}
    vertices = [points_by_source_index[source] for source in used]
    faces = [
        tuple(remap[index] for index in model.faces[face_index].indices)
        for face_index in sorted(selected)
    ]
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["review_only"] = True
    obj["not_printable"] = True
    return obj


def create_seam(
    name: str,
    seam_edges: set[tuple[int, int]],
    display_points: dict[int, tuple[float, float, float]],
    radius_mm: float,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    curve = bpy.data.curves.new(f"{name}_curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 1
    curve.bevel_depth = radius_mm
    curve.bevel_resolution = 2
    curve.use_fill_caps = True
    for first, second in sorted(seam_edges):
        spline = curve.splines.new("POLY")
        spline.points.add(1)
        spline.points[0].co = (*display_points[first], 1.0)
        spline.points[1].co = (*display_points[second], 1.0)
    obj = bpy.data.objects.new(name, curve)
    collection.objects.link(obj)
    obj.data.materials.append(material)
    obj["review_only"] = True
    obj["meaning"] = "proposed rear-cassette ownership boundary"
    return obj


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def configure_review_scene(
    output_dir: Path,
    resolution_px: int,
) -> tuple[bpy.types.Object, list[bpy.types.Object]]:
    scene = bpy.context.scene
    scene.name = "Rear_Cassette_Seam_Review_V2"
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    shading.curvature_ridge_factor = 1.8
    shading.curvature_valley_factor = 1.4
    shading.background_type = "VIEWPORT"
    shading.background_color = (0.055, 0.065, 0.085)
    scene.render.resolution_x = resolution_px
    scene.render.resolution_y = resolution_px
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.014, 0.018, 0.028)

    camera_data = bpy.data.cameras.new("REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("REVIEW_ONLY__Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 58.0

    lights: list[bpy.types.Object] = []
    for name, location, energy, size in (
        ("REVIEW_ONLY__Key", (380.0, -320.0, 500.0), 1350.0, 260.0),
        ("REVIEW_ONLY__Fill", (-400.0, 20.0, 320.0), 1050.0, 260.0),
        ("REVIEW_ONLY__Rear", (20.0, 600.0, 420.0), 1450.0, 240.0),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        light = bpy.data.objects.new(name, data)
        scene.collection.objects.link(light)
        light.location = location
        point_at(light, Vector((0.0, 175.0, 165.0)))
        lights.append(light)

    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    return camera, lights


def render_views(camera: bpy.types.Object, output_dir: Path) -> list[str]:
    scene = bpy.context.scene
    target = Vector((0.0, 175.0, 165.0))
    views = (
        ("front", Vector((0.0, -610.0, 260.0))),
        ("rear", Vector((0.0, 650.0, 280.0))),
        ("rear-left", Vector((-430.0, 560.0, 330.0))),
        ("rear-right", Vector((430.0, 560.0, 330.0))),
        ("left", Vector((-620.0, 145.0, 270.0))),
        ("right", Vector((620.0, 145.0, 270.0))),
    )
    paths: list[str] = []
    for label, location in views:
        camera.location = location
        point_at(camera, target)
        path = output_dir / "renders" / f"rear-cassette-seam-{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        paths.append(str(path.relative_to(REPO_ROOT)))
    camera.location = Vector((0.0, 650.0, 280.0))
    point_at(camera, target)
    return paths


def render_isolated_views(
    camera: bpy.types.Object,
    output_dir: Path,
    cassette_review_objects: list[bpy.types.Object],
) -> list[str]:
    scene = bpy.context.scene
    saved_visibility = {
        name: bpy.data.objects[name].hide_render
        for name in PRODUCTION_PARTS
    }
    for name in PRODUCTION_PARTS:
        bpy.data.objects[name].hide_render = True
    for obj in cassette_review_objects:
        obj.hide_render = False

    target = Vector((0.0, 245.0, 145.0))
    views = (
        ("isolated-rear", Vector((0.0, 650.0, 260.0))),
        ("isolated-rear-left", Vector((-430.0, 560.0, 300.0))),
        ("isolated-rear-right", Vector((430.0, 560.0, 300.0))),
    )
    paths: list[str] = []
    for label, location in views:
        camera.location = location
        point_at(camera, target)
        path = output_dir / "renders" / f"rear-cassette-seam-{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        paths.append(str(path.relative_to(REPO_ROOT)))

    for name, hidden in saved_visibility.items():
        bpy.data.objects[name].hide_render = hidden
    return paths


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_blend = repo_path(config["source_gate8_blend"])
    if Path(bpy.data.filepath).resolve() != source_blend:
        raise ValueError(
            f"Open the configured Gate 8 blend before running this script: {source_blend}"
        )
    interface_path = repo_path(config["shared_interface_path"])
    interface = json.loads(interface_path.read_text(encoding="utf-8"))
    actual_revision = interface["interface_revision"]
    required_revision = config["required_interface_revision"]
    if actual_revision != required_revision:
        raise ValueError(
            f"Interface mismatch: {actual_revision} != {required_revision}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    removed_references, mesh_stats_before = clean_gate8_scene()
    model, assignments, points, selected, seam_edges = source_selection(
        config, interface
    )
    exact_points = {
        vertex: points[vertex]
        for face_index in selected
        for vertex in model.faces[face_index].indices
    }
    display_points = outward_offset_points(
        model,
        points,
        selected,
        float(config["review_display"]["overlay_offset_mm"]),
    )

    review_collection = bpy.data.collections.new(
        "REVIEW_ONLY_PROPOSED_REAR_CASSETTE"
    )
    bpy.context.scene.collection.children.link(review_collection)
    overlay_material = make_material(
        "REVIEW_ONLY__Rear_Cassette_Orange",
        config["review_display"]["overlay_color"],
        alpha=0.82,
    )
    seam_material = make_material(
        "REVIEW_ONLY__Proposed_Seam_Yellow",
        config["review_display"]["seam_color"],
        alpha=1.0,
    )
    exact_surface = create_surface(
        "REVIEW_ONLY__rear_cassette_exact_surface",
        model,
        exact_points,
        selected,
        overlay_material,
        review_collection,
    )
    exact_surface.hide_viewport = True
    exact_surface.hide_render = True
    exact_surface["meaning"] = "exact unshifted selected source facets"

    overlay = create_surface(
        "REVIEW_ONLY__rear_cassette_visible_overlay",
        model,
        display_points,
        selected,
        overlay_material,
        review_collection,
    )
    overlay["display_offset_mm"] = float(
        config["review_display"]["overlay_offset_mm"]
    )
    seam = create_seam(
        "REVIEW_ONLY__proposed_rear_cassette_seam",
        seam_edges,
        display_points,
        float(config["review_display"]["seam_radius_mm"]),
        seam_material,
        review_collection,
    )
    rear_base_overlay = create_rear_base_overlay(
        overlay_material, review_collection
    )

    camera, _lights = configure_review_scene(
        output_dir,
        int(config["review_display"]["render_resolution_px"]),
    )
    render_paths = render_views(camera, output_dir)
    render_paths.extend(
        render_isolated_views(
            camera, output_dir, [overlay, seam, rear_base_overlay]
        )
    )

    scene = bpy.context.scene
    scene["review_status"] = config["status"]
    scene["production_geometry_modified"] = False
    scene["rear_cassette_threshold_mm"] = float(
        config["rear_cassette_cut"]["rear_plane_threshold_mm"]
    )
    scene["instructions"] = (
        "Orange is proposed cassette ownership from lower-face facets plus "
        "the existing rear_base; yellow is the lower-face cut seam; "
        "both upper-head pieces remain unchanged."
    )

    blend_path = output_dir / "rear-cassette-seam-review-v2.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    bpy.ops.object.select_all(action="DESELECT")
    export_names = (PRODUCTION_PARTS - {"rear_base"}) | {
        overlay.name, seam.name, rear_base_overlay.name
    }
    for name in export_names:
        obj = bpy.data.objects.get(name)
        if obj is not None:
            obj.select_set(True)
    glb_path = output_dir / "rear-cassette-seam-review-v2.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path),
        export_format="GLB",
        use_selection=True,
    )

    mesh_stats_after = {
        name: (len(bpy.data.objects[name].data.vertices), len(bpy.data.objects[name].data.polygons))
        for name in sorted(PRODUCTION_PARTS)
        if bpy.data.objects[name].type == "MESH"
    }
    selected_panels = sorted(
        {
            gate1.canonical_source_panel_id(model.faces[index].group)
            for index in selected
        }
    )
    selected_sections = sorted({assignments[index] for index in selected})
    exact_bounds = gate1.bounds(list(exact_points.values()))
    report = {
        "schema_version": 2,
        "status": config["status"],
        "source_gate8_blend": str(source_blend.relative_to(REPO_ROOT)),
        "source_gate8_blend_sha256": sha256(source_blend),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "config_sha256": sha256(config_path),
        "shared_interface": str(interface_path.relative_to(REPO_ROOT)),
        "interface_revision": interface["interface_revision"],
        "rear_plane": interface["rear_interface_plane"],
        "selection_rule": config["rear_cassette_cut"]["selection_rule"],
        "rear_plane_threshold_mm": float(
            config["rear_cassette_cut"]["rear_plane_threshold_mm"]
        ),
        "configured_cassette_source_sections": sorted(
            config["rear_cassette_cut"]["source_sections"]
        ),
        "actual_selected_source_sections": selected_sections,
        "upper_head_facet_ownership_unchanged": not any(
            section in {"left_upper_head", "right_upper_head"}
            for section in selected_sections
        ),
        "existing_rear_base_included_in_cassette_ownership": True,
        "ownership_group_is_single_connected_body": False,
        "connection_status": (
            "rear_base and selected lower-face surfaces remain separate review "
            "objects; connection and aluminum reconciliation are deferred"
        ),
        "selected_source_face_count": len(selected),
        "selected_source_panel_ids": selected_panels,
        "proposed_seam_edge_count": len(seam_edges),
        "exact_selected_surface_dimensions_mm": [
            round(value, 3) for value in gate1.dimensions(exact_bounds)
        ],
        "production_parts_present": sorted(PRODUCTION_PARTS),
        "production_mesh_stats_unchanged": mesh_stats_before == mesh_stats_after,
        "production_geometry_modified": False,
        "rear_base_candidate_view": (
            "original present but hidden; unchanged orange duplicate included "
            "in cassette ownership review"
        ),
        "removed_gate8_review_references": removed_references,
        "review_objects": [
            exact_surface.name, overlay.name, seam.name, rear_base_overlay.name
        ],
        "no_stl_or_gcode_exported": True,
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "glb": str(glb_path.relative_to(REPO_ROOT)),
            "renders": render_paths,
        },
        "review_holds": config["review_holds"],
    }
    report_path = output_dir / "rear-cassette-seam-review-v2-validation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(
        {
            "status": report["status"],
            "selected_source_face_count": len(selected),
            "proposed_seam_edge_count": len(seam_edges),
            "production_mesh_stats_unchanged": report[
                "production_mesh_stats_unchanged"
            ],
            "blend": report["generated_files"]["blend"],
            "report": str(report_path.relative_to(REPO_ROOT)),
        },
        indent=2,
    ))


if __name__ == "__main__":
    main()
