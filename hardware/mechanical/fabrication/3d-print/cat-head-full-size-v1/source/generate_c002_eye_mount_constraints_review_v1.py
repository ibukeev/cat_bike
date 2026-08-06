#!/usr/bin/env python3
"""Generate an isolated constraints review for the rejected outer C002 mounts.

This generator creates no replacement mount mesh. It exposes the rejected C002
pieces, preserved eye buckets and lower C004 mounts, and the nearest accepted
outer seam rails so the mounting concept can be reviewed before geometry work.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_rear_cassette_lossless_repartition_review_v5 as v5  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/c002-eye-mount-constraints-review-v1.json"
DEFAULT_OUTPUT = PACKAGE_ROOT / "output/00-current-review"


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


def world_geometry(obj: bpy.types.Object) -> tuple[list[Vector], list[tuple[int, ...]]]:
    vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    faces = [tuple(polygon.vertices) for polygon in obj.data.polygons]
    return vertices, faces


def world_bvh(obj: bpy.types.Object) -> BVHTree:
    vertices, faces = world_geometry(obj)
    return BVHTree.FromPolygons(vertices, faces, all_triangles=False)


def surface_distance(first: bpy.types.Object, second: bpy.types.Object) -> float:
    first_vertices, _ = world_geometry(first)
    second_vertices, _ = world_geometry(second)
    first_bvh = world_bvh(first)
    second_bvh = world_bvh(second)
    distances = []
    for point in first_vertices:
        nearest = second_bvh.find_nearest(point)
        if nearest is not None:
            distances.append(nearest[3])
    for point in second_vertices:
        nearest = first_bvh.find_nearest(point)
        if nearest is not None:
            distances.append(nearest[3])
    return float(min(distances))


def surfaces_overlap(first: bpy.types.Object, second: bpy.types.Object) -> bool:
    return bool(world_bvh(first).overlap(world_bvh(second)))


def require_object(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        raise ValueError(f"Missing required mesh object {name}")
    return obj


def link_reference(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    if obj.name not in collection.objects:
        collection.objects.link(obj)


def point_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def configure_scene(output_dir: Path, resolution_px: int) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.name = "C002_Eye_Mount_Constraints_Review_V1"
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
    camera_data = bpy.data.cameras.new("E1_REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("E1_REVIEW_ONLY__Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 58.0
    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    return camera


def render_view(
    camera: bpy.types.Object,
    output_dir: Path,
    name: str,
    location: Vector,
    target: Vector,
    visible: set[bpy.types.Object],
) -> str:
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_render = obj not in visible
    camera.location = location
    point_at(camera, target)
    path = output_dir / "renders" / f"c002-constraints-{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path.relative_to(REPO_ROOT))


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_blend = repo_path(config["source_reinforcement_blend"])
    if Path(bpy.data.filepath).resolve() != source_blend:
        raise ValueError(f"Open the configured accepted reinforcement blend: {source_blend}")
    interface = json.loads(repo_path(config["shared_interface_path"]).read_text(encoding="utf-8"))
    if interface["interface_revision"] != config["required_interface_revision"]:
        raise ValueError("Shared shell/aluminum interface revision changed")
    output_dir.mkdir(parents=True, exist_ok=True)

    protected_before = {
        obj.name: v5.mesh_fingerprint(obj)
        for obj in bpy.data.objects
        if obj.type == "MESH"
    }
    original_mesh_count = len(protected_before)

    collections = {}
    for name in (
        "E1_REJECTED_C002_RED",
        "E1_PRESERVED_EYE_BUCKETS_BLUE",
        "E1_PRESERVED_LOWER_C004_GREEN",
        "E1_CANDIDATE_OUTER_ANCHORS_YELLOW",
        "E1_NEARBY_REINFORCEMENT_CONTEXT",
        "E1_RETAINED_SHELL_WIREFRAME",
    ):
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        collections[name] = collection

    display = config["display"]
    side_records: dict[str, Any] = {}
    side_visible: dict[str, set[bpy.types.Object]] = {}
    key_objects: set[bpy.types.Object] = set()

    for side, names in config["sides"].items():
        rejected = require_object(names["rejected_outer_mount"])
        lower_mount = require_object(names["preserved_lower_mount"])
        bucket = require_object(names["eye_bucket"])
        anchor = require_object(names["outer_anchor"])
        shell = require_object(names["retained_shell"])

        rejected.color = hex_color(display["rejected_mount_color"])
        bucket.color = hex_color(display["eye_bucket_color"])
        lower_mount.color = hex_color(display["preserved_lower_mount_color"])
        anchor.color = hex_color(display["candidate_anchor_color"])
        shell.color = hex_color(display["shell_wire_color"])
        for obj in (rejected, bucket, lower_mount, anchor):
            obj.show_in_front = True
            obj.hide_viewport = False
        shell.display_type = "WIRE"
        shell.show_in_front = False
        shell.hide_viewport = False

        link_reference(rejected, collections["E1_REJECTED_C002_RED"])
        link_reference(bucket, collections["E1_PRESERVED_EYE_BUCKETS_BLUE"])
        link_reference(lower_mount, collections["E1_PRESERVED_LOWER_C004_GREEN"])
        link_reference(anchor, collections["E1_CANDIDATE_OUTER_ANCHORS_YELLOW"])
        link_reference(shell, collections["E1_RETAINED_SHELL_WIREFRAME"])

        side_code = "L" if side == "left" else "R"
        nearby = []
        for obj in bpy.data.objects:
            if (
                obj.type == "MESH"
                and obj.name.startswith(f"R1_RET__{side_code}__")
                and obj not in {lower_mount, anchor}
                and surface_distance(rejected, obj) <= 50.0
            ):
                obj.color = hex_color(display["nearby_reinforcement_color"])
                obj.hide_viewport = False
                link_reference(obj, collections["E1_NEARBY_REINFORCEMENT_CONTEXT"])
                nearby.append(obj)

        rejected_boundary, rejected_nonmanifold = gate5.topology_counts(rejected)
        side_records[side] = {
            "rejected_outer_mount": rejected.name,
            "rejected_dimensions_mm": [round(value, 4) for value in rejected.dimensions],
            "rejected_boundary_edges": rejected_boundary,
            "rejected_nonmanifold_edges": rejected_nonmanifold,
            "eye_bucket": bucket.name,
            "rejected_to_bucket_gap_mm": round(surface_distance(rejected, bucket), 4),
            "preserved_lower_mount": lower_mount.name,
            "lower_mount_to_bucket_gap_mm": round(surface_distance(lower_mount, bucket), 4),
            "candidate_outer_anchor": anchor.name,
            "rejected_to_anchor_gap_mm": round(surface_distance(rejected, anchor), 4),
            "rejected_overlaps_anchor": surfaces_overlap(rejected, anchor),
            "retained_shell": shell.name,
            "rejected_to_retained_shell_gap_mm": round(surface_distance(rejected, shell), 4),
            "nearby_retained_reinforcement": [obj.name for obj in nearby],
        }
        essentials = {rejected, bucket, lower_mount, anchor, shell}
        side_visible[side] = essentials | set(nearby)
        key_objects |= essentials

    default_visible = side_visible["left"] | side_visible["right"]
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in default_visible
            obj.hide_render = True

    camera = configure_scene(output_dir, int(display["render_resolution_px"]))
    renders = []
    renders.append(render_view(camera, output_dir, "both-interior", Vector((0.0, 390.0, 205.0)), Vector((0.0, 77.0, 140.0)), default_visible))
    renders.append(render_view(camera, output_dir, "left-interior", Vector((-285.0, 315.0, 205.0)), Vector((-86.0, 77.0, 140.0)), side_visible["left"]))
    renders.append(render_view(camera, output_dir, "right-interior", Vector((285.0, 315.0, 205.0)), Vector((86.0, 77.0, 140.0)), side_visible["right"]))
    renders.append(render_view(camera, output_dir, "left-exterior", Vector((-260.0, -250.0, 190.0)), Vector((-86.0, 77.0, 140.0)), side_visible["left"]))
    renders.append(render_view(camera, output_dir, "right-exterior", Vector((260.0, -250.0, 190.0)), Vector((86.0, 77.0, 140.0)), side_visible["right"]))
    isolated_left = {require_object(config["sides"]["left"][key]) for key in ("rejected_outer_mount", "preserved_lower_mount", "eye_bucket", "outer_anchor")}
    isolated_right = {require_object(config["sides"]["right"][key]) for key in ("rejected_outer_mount", "preserved_lower_mount", "eye_bucket", "outer_anchor")}
    renders.append(render_view(camera, output_dir, "left-isolated", Vector((-270.0, 300.0, 195.0)), Vector((-86.0, 77.0, 140.0)), isolated_left))
    renders.append(render_view(camera, output_dir, "right-isolated", Vector((270.0, 300.0, 195.0)), Vector((86.0, 77.0, 140.0)), isolated_right))

    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in default_visible
            obj.hide_render = obj not in default_visible
    camera.location = Vector((0.0, 390.0, 205.0))
    point_at(camera, Vector((0.0, 77.0, 140.0)))

    protected_after = {
        name: v5.mesh_fingerprint(bpy.data.objects[name])
        for name in protected_before
    }
    if protected_before != protected_after:
        raise ValueError("A pre-existing source/review mesh changed")
    final_mesh_count = sum(obj.type == "MESH" for obj in bpy.data.objects)
    if final_mesh_count != original_mesh_count:
        raise ValueError("This constraints review must not create mesh geometry")

    scene = bpy.context.scene
    scene["review_status"] = config["status"]
    scene["replacement_mount_geometry_created"] = False
    scene["source_mesh_geometry_unchanged"] = True
    blend_path = output_dir / "c002-eye-mount-constraints-review-v1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "source_reinforcement_blend": str(source_blend.relative_to(REPO_ROOT)),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "interface_revision": interface["interface_revision"],
        "side_records": side_records,
        "replacement_mount_geometry_created": False,
        "source_mesh_count": original_mesh_count,
        "source_mesh_geometry_unchanged": protected_before == protected_after,
        "preserved_assumptions": [
            "Existing Gate 6 eye buckets",
            "Existing retained lower C004 eye mounts",
            "Accepted reinforcement additions",
            "Shared aluminum interface V0.5",
        ],
        "next_design_decision": "Replace only the outer C002 function with a low-profile internal attachment to the named accepted seam rail after this interface is visually approved.",
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": renders,
        },
        "no_stl_or_gcode_exported": True,
        "review_holds": config["review_holds"],
    }
    report_path = output_dir / "c002-eye-mount-constraints-review-v1-validation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
