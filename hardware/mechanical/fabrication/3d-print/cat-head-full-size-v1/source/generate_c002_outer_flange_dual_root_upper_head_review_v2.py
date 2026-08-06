#!/usr/bin/env python3
"""Generate a review-only dual-root upper-head mount for each outer eye flange.

Each candidate preserves the exact accepted Gate 6 flange mating position and
M2.5 hole while using two compact tapered roots, one at each end of the flange,
to distribute vibration loads into the matching upper-head shell. Production
shell meshes remain unchanged.
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
import generate_gate6_eye_modules as gate6  # noqa: E402
import generate_rear_cassette_lossless_repartition_review_v5 as v5  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/c002-outer-flange-dual-root-upper-head-review-v2.json"
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
    return (
        [obj.matrix_world @ vertex.co for vertex in obj.data.vertices],
        [tuple(polygon.vertices) for polygon in obj.data.polygons],
    )


def world_bvh(obj: bpy.types.Object) -> BVHTree:
    vertices, faces = world_geometry(obj)
    return BVHTree.FromPolygons(vertices, faces, all_triangles=False)


def closest_surface_pair(
    first: bpy.types.Object, second: bpy.types.Object
) -> tuple[Vector, Vector, float]:
    first_vertices, _ = world_geometry(first)
    second_vertices, _ = world_geometry(second)
    first_bvh = world_bvh(first)
    second_bvh = world_bvh(second)
    best_first = first_vertices[0]
    best_second = second_vertices[0]
    best_distance = float("inf")
    for point in first_vertices:
        nearest = second_bvh.find_nearest(point)
        if nearest is not None and nearest[3] < best_distance:
            best_first, best_second, best_distance = point, nearest[0], nearest[3]
    for point in second_vertices:
        nearest = first_bvh.find_nearest(point)
        if nearest is not None and nearest[3] < best_distance:
            best_first, best_second, best_distance = nearest[0], point, nearest[3]
    return best_first.copy(), best_second.copy(), float(best_distance)


def surface_distance(first: bpy.types.Object, second: bpy.types.Object) -> float:
    return closest_surface_pair(first, second)[2]


def surfaces_overlap(first: bpy.types.Object, second: bpy.types.Object) -> bool:
    return bool(world_bvh(first).overlap(world_bvh(second)))


def require_object(name: str) -> bpy.types.Object:
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != "MESH":
        raise ValueError(f"Missing required mesh object {name}")
    return obj


def move_to_collection(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    for source in list(obj.users_collection):
        source.objects.unlink(obj)
    collection.objects.link(obj)


def link_reference(obj: bpy.types.Object, collection: bpy.types.Collection) -> None:
    if obj.name not in collection.objects:
        collection.objects.link(obj)


def recalculate_normals(obj: bpy.types.Object) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    obj.select_set(False)


def tapered_prism(
    name: str,
    start: Vector,
    end: Vector,
    width_axis: Vector,
    thickness_axis: Vector,
    start_width: float,
    end_width: float,
    start_thickness: float,
    end_thickness: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    width_axis = width_axis.normalized()
    thickness_axis = thickness_axis.normalized()
    start_points = [
        start - width_axis * start_width / 2.0 - thickness_axis * start_thickness / 2.0,
        start + width_axis * start_width / 2.0 - thickness_axis * start_thickness / 2.0,
        start + width_axis * start_width / 2.0 + thickness_axis * start_thickness / 2.0,
        start - width_axis * start_width / 2.0 + thickness_axis * start_thickness / 2.0,
    ]
    end_points = [
        end - width_axis * end_width / 2.0 - thickness_axis * end_thickness / 2.0,
        end + width_axis * end_width / 2.0 - thickness_axis * end_thickness / 2.0,
        end + width_axis * end_width / 2.0 + thickness_axis * end_thickness / 2.0,
        end - width_axis * end_width / 2.0 + thickness_axis * end_thickness / 2.0,
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
    mesh.from_pydata([tuple(point) for point in start_points + end_points], [], faces)
    mesh.update(calc_edges=True)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    recalculate_normals(obj)
    return obj


def outer_flange_frame(geometry: dict[str, Any]) -> dict[str, Any]:
    settings = gate6.CONFIG["head_mount"]
    outer = geometry["outer"]
    aperture = geometry["aperture"]
    inward = geometry["inward"]
    edges = [(index, (index + 1) % 4) for index in range(4)]
    midpoints = {edge: (outer[edge[0]] + outer[edge[1]]) / 2.0 for edge in edges}
    edge = max(edges, key=lambda value: abs(midpoints[value].x))
    first, second = edge
    anchor = midpoints[edge]
    aperture_midpoint = (aperture[first] + aperture[second]) / 2.0
    tangent = outer[second] - outer[first]
    tangent -= inward * tangent.dot(inward)
    tangent.normalize()
    radial = inward.cross(tangent).normalized()
    if radial.dot(aperture_midpoint - anchor) < 0.0:
        radial = -radial
    length = float(settings["tab_length_mm"])
    depth = float(settings["tab_depth_mm"])
    thickness = float(settings["tab_thickness_mm"])
    overlap = float(settings["shell_overlap_mm"])
    front_recess = float(settings["front_recess_mm"])
    center = (
        anchor
        + radial * (thickness / 2.0 - overlap)
        + inward * (front_recess + depth / 2.0)
    )
    hole_center = center + inward * (
        float(settings["bolt_depth_from_eye_plane_mm"]) - depth / 2.0
    )
    return {
        "edge": list(edge),
        "anchor": anchor,
        "tangent": tangent,
        "inward": inward,
        "radial": radial,
        "center": center,
        "hole_center": hole_center,
        "dimensions": (length, depth, thickness),
        "hole_diameter": float(settings["m2_5_clearance_diameter_mm"]),
        "front_recess": front_recess,
        "bucket_face_gap": float(settings["tab_face_gap_mm"]),
    }


def create_candidate(
    side: str,
    geometry: dict[str, Any],
    names: dict[str, str],
    config: dict[str, Any],
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    frame = outer_flange_frame(geometry)
    owner_shell = require_object(names["owner_shell"])
    bucket = require_object(names["eye_bucket"])
    old_mount = require_object(names["rejected_outer_mount"])
    candidate = gate5.box(
        names["proposed_object"],
        frame["center"],
        (frame["tangent"], frame["inward"], frame["radial"]),
        frame["dimensions"],
        material,
    )
    move_to_collection(candidate, collection)

    values = config["root"]
    shell_gap = surface_distance(candidate, owner_shell)
    maximum_shell_gap = float(values["maximum_flange_to_owner_shell_gap_mm"])
    if shell_gap > maximum_shell_gap:
        raise ValueError(
            f"{side} upper-head shell is {shell_gap:.4f} mm from the preserved "
            f"flange, above the {maximum_shell_gap:.4f} mm compact-root limit"
        )

    root_length = float(values["centerline_length_mm"])
    flange_overlap = float(values["flange_overlap_mm"])
    if flange_overlap <= 0.0 or flange_overlap >= root_length:
        raise ValueError("Root overlap must be positive and shorter than the root")
    shell_end_thickness = float(values["shell_end_thickness_mm"])
    if shell_end_thickness > float(frame["dimensions"][2]):
        raise ValueError("Roots must stay inside the preserved flange thickness")

    radial_shift = -frame["radial"] * (
        (float(frame["dimensions"][2]) - shell_end_thickness) / 2.0
    )
    flange_length = float(frame["dimensions"][0])
    root_records = []
    for root_index, direction_sign in enumerate((-1.0, 1.0), start=1):
        root_direction = frame["tangent"] * direction_sign
        flange_end = (
            frame["center"] + root_direction * flange_length / 2.0
        )
        root_start = (
            flange_end - root_direction * flange_overlap + radial_shift
        )
        root_end = (
            flange_end
            + root_direction * (root_length - flange_overlap)
            + radial_shift
        )
        root = tapered_prism(
            f"{names['proposed_object']}__hidden_root_{root_index}_tool",
            root_start,
            root_end,
            frame["inward"],
            frame["radial"],
            float(values["flange_end_depth_mm"]),
            float(values["shell_end_depth_mm"]),
            float(values["flange_end_thickness_mm"]),
            shell_end_thickness,
            material,
        )
        root_flange_overlap = surfaces_overlap(root, candidate)
        root_shell_overlap = surfaces_overlap(root, owner_shell)
        root_bucket_overlap = surfaces_overlap(root, bucket)
        root_bucket_gap = surface_distance(root, bucket)
        if not root_flange_overlap or not root_shell_overlap:
            raise ValueError(
                f"{side} hidden root {root_index} does not overlap both the "
                "preserved flange and its upper-head owner shell"
            )
        if root_bucket_overlap or root_bucket_gap < float(
            values["minimum_root_to_bucket_clearance_mm"]
        ):
            raise ValueError(
                f"{side} hidden root {root_index} violates eye-bucket clearance: "
                f"overlap={root_bucket_overlap}, gap={root_bucket_gap:.4f} mm"
            )
        root_records.append(
            {
                "root_index": root_index,
                "flange_end_center_mm": [
                    round(value, 4) for value in flange_end
                ],
                "root_axis": [
                    round(value, 5) for value in root_direction
                ],
                "root_overlaps_flange": root_flange_overlap,
                "root_overlaps_owner_shell": root_shell_overlap,
                "root_to_bucket_gap_before_union_mm": round(root_bucket_gap, 4),
            }
        )
        gate5.apply_boolean(candidate, root, "UNION", solver="EXACT")

    gate6.cut_axis_hole(
        candidate,
        f"{names['proposed_object']}__m2_5_clearance",
        frame["hole_center"],
        frame["radial"],
        frame["hole_diameter"],
        20.0,
    )
    candidate.color = hex_color(config["display"]["proposed_mount_color"])
    candidate.show_in_front = True
    candidate["review_only"] = True
    candidate["replaces_rejected_object"] = old_mount.name
    candidate["owner_shell"] = owner_shell.name
    candidate["preserves_gate6_outer_flange"] = True
    candidate["root_count"] = len(root_records)
    candidate["root_centerline_length_mm"] = root_length

    boundary, nonmanifold = gate5.topology_counts(candidate)
    bucket_overlap = surfaces_overlap(candidate, bucket)
    bucket_gap = surface_distance(candidate, bucket)
    shell_overlap = surfaces_overlap(candidate, owner_shell)
    old_overlap = surfaces_overlap(candidate, old_mount)
    if boundary or nonmanifold:
        raise ValueError(f"{side} proposed outer mount is not closed and manifold")
    if not shell_overlap:
        raise ValueError(f"{side} proposed outer mount does not overlap its owner shell")
    if bucket_overlap or bucket_gap < float(
        values["minimum_candidate_to_bucket_clearance_mm"]
    ):
        raise ValueError(
            f"{side} proposed mount violates the preserved eye-bucket gap: "
            f"overlap={bucket_overlap}, gap={bucket_gap:.5f} mm"
        )
    if not old_overlap:
        raise ValueError(f"{side} proposed flange does not preserve the old mating location")
    if len(root_records) != int(config["root_count_per_connector"]):
        raise ValueError(f"{side} candidate does not have two validated roots")

    return candidate, {
        "side": side,
        "proposed_object": candidate.name,
        "rejected_object_removed": old_mount.name,
        "preserved_lower_mount": names["preserved_lower_mount"],
        "eye_bucket": bucket.name,
        "owner_shell": owner_shell.name,
        "outer_edge_indices": frame["edge"],
        "gate6_anchor_mm": [round(value, 4) for value in frame["anchor"]],
        "m2_5_hole_center_mm": [round(value, 4) for value in frame["hole_center"]],
        "m2_5_hole_axis": [round(value, 5) for value in frame["radial"]],
        "m2_5_clearance_diameter_mm": frame["hole_diameter"],
        "flange_dimensions_mm": list(frame["dimensions"]),
        "front_recess_mm": frame["front_recess"],
        "bucket_face_gap_from_gate6_mm": frame["bucket_face_gap"],
        "flange_to_owner_shell_gap_before_roots_mm": round(shell_gap, 4),
        "root_count": len(root_records),
        "root_centerline_length_mm": root_length,
        "root_extension_beyond_flange_mm": round(root_length - flange_overlap, 4),
        "root_flange_end_depth_mm": float(values["flange_end_depth_mm"]),
        "root_shell_end_depth_mm": float(values["shell_end_depth_mm"]),
        "root_flange_end_thickness_mm": float(values["flange_end_thickness_mm"]),
        "root_shell_end_thickness_mm": shell_end_thickness,
        "root_records": root_records,
        "minimum_root_to_bucket_gap_before_union_mm": min(
            record["root_to_bucket_gap_before_union_mm"]
            for record in root_records
        ),
        "candidate_to_bucket_gap_mm": round(bucket_gap, 4),
        "candidate_overlaps_owner_shell": shell_overlap,
        "candidate_overlaps_old_flange_location": old_overlap,
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "candidate_dimensions_mm": [round(value, 4) for value in candidate.dimensions],
        "candidate_volume_mm3": round(gate5.mesh_volume(candidate), 4),
    }

def point_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def configure_scene(output_dir: Path, resolution_px: int) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.name = "C002_Outer_Flange_Dual_Root_Upper_Head_Review_V2"
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "OBJECT"
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    shading.background_type = "VIEWPORT"
    shading.background_color = (0.035, 0.045, 0.06)
    scene.render.resolution_x = resolution_px
    scene.render.resolution_y = resolution_px
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    camera_data = bpy.data.cameras.new("E3_REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("E3_REVIEW_ONLY__Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 58.0
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            space.shading.type = "SOLID"
            space.shading.color_type = "OBJECT"
            space.region_3d.view_perspective = "CAMERA"
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
    path = output_dir / "renders" / f"outer-flange-dual-root-upper-head-{name}.png"
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
    if repo_path(config["gate6_eye_config"]) != gate6.CONFIG_PATH.resolve():
        raise ValueError("Configured Gate 6 eye settings path changed")
    interface = json.loads(repo_path(config["shared_interface_path"]).read_text(encoding="utf-8"))
    if interface["interface_revision"] != config["required_interface_revision"]:
        raise ValueError("Shared shell/aluminum interface revision changed")
    output_dir.mkdir(parents=True, exist_ok=True)

    rejected_names = {
        values["rejected_outer_mount"] for values in config["sides"].values()
    }
    protected_before = {
        obj.name: v5.mesh_fingerprint(obj)
        for obj in bpy.data.objects
        if obj.type == "MESH" and obj.name not in rejected_names
    }
    source_visible_names = {
        obj.name
        for obj in bpy.data.objects
        if obj.type == "MESH" and not obj.hide_viewport and not obj.hide_get()
    }
    original_mesh_count = sum(obj.type == "MESH" for obj in bpy.data.objects)

    collection_names = (
        "E3_PROPOSED_OUTER_FLANGES_PURPLE",
        "E3_PRESERVED_EYE_BUCKETS_BLUE",
        "E3_PRESERVED_LOWER_C004_GREEN",
        "E3_OWNER_UPPER_HEAD_SHELLS_GRAY",
        "E3_NEARBY_REINFORCEMENT_CONTEXT",
    )
    collections = {}
    for name in collection_names:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        collections[name] = collection

    material = gate5.material(
        "E3__Proposed_Outer_Flange_Upper_Head_Root_Purple",
        hex_color(config["display"]["proposed_mount_color"]),
    )
    geometry_by_side = {value["side"]: value for value in gate6.eye_geometry()}
    candidate_objects = []
    side_records = []
    side_visible: dict[str, set[bpy.types.Object]] = {}
    rejected_objects = []

    for side, names in config["sides"].items():
        candidate, record = create_candidate(
            side,
            geometry_by_side[side],
            names,
            config,
            collections["E3_PROPOSED_OUTER_FLANGES_PURPLE"],
            material,
        )
        bucket = require_object(names["eye_bucket"])
        lower_mount = require_object(names["preserved_lower_mount"])
        owner_shell = require_object(names["owner_shell"])
        rejected = require_object(names["rejected_outer_mount"])
        bucket.color = hex_color(config["display"]["eye_bucket_color"])
        lower_mount.color = hex_color(config["display"]["preserved_lower_mount_color"])
        owner_shell.color = hex_color(config["display"]["shell_wire_color"])
        owner_shell.show_wire = True
        for obj in (candidate, bucket, lower_mount, owner_shell):
            obj.hide_viewport = False
            obj.hide_set(False)
        candidate.show_in_front = True
        bucket.show_in_front = True
        lower_mount.show_in_front = True
        link_reference(bucket, collections["E3_PRESERVED_EYE_BUCKETS_BLUE"])
        link_reference(lower_mount, collections["E3_PRESERVED_LOWER_C004_GREEN"])
        link_reference(owner_shell, collections["E3_OWNER_UPPER_HEAD_SHELLS_GRAY"])
        side_code = "L" if side == "left" else "R"
        nearby = []
        for obj in bpy.data.objects:
            if (
                obj.type == "MESH"
                and obj.name.startswith(f"R1_RET__{side_code}__")
                and obj not in {lower_mount}
                and surface_distance(candidate, obj) <= 35.0
            ):
                obj.color = hex_color(config["display"]["nearby_reinforcement_color"])
                link_reference(obj, collections["E3_NEARBY_REINFORCEMENT_CONTEXT"])
                nearby.append(obj)
        record["nearby_retained_reinforcement"] = [obj.name for obj in nearby]
        side_records.append(record)
        side_visible[side] = {
            candidate,
            bucket,
            lower_mount,
            owner_shell,
        } | set(nearby)
        candidate_objects.append(candidate)
        rejected_objects.append(rejected)

    for rejected in rejected_objects:
        mesh = rejected.data
        bpy.data.objects.remove(rejected, do_unlink=True)
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)

    left_record = next(value for value in side_records if value["side"] == "left")
    right_record = next(value for value in side_records if value["side"] == "right")
    left_hole = Vector(left_record["m2_5_hole_center_mm"])
    right_hole = Vector(right_record["m2_5_hole_center_mm"])
    mirrored_hole_error = (
        Vector((-left_hole.x, left_hole.y, left_hole.z)) - right_hole
    ).length

    closeup_visible = side_visible["left"] | side_visible["right"]
    whole_head_visible = {
        bpy.data.objects[name]
        for name in source_visible_names
        if name in bpy.data.objects and name not in rejected_names
    } | closeup_visible
    required_eye_buckets = {
        require_object(config["sides"]["left"]["eye_bucket"]),
        require_object(config["sides"]["right"]["eye_bucket"]),
    }
    if not required_eye_buckets.issubset(whole_head_visible):
        raise ValueError("Saved whole-head view must include both eye buckets")
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in closeup_visible
            obj.hide_render = True

    camera = configure_scene(output_dir, int(config["display"]["render_resolution_px"]))
    renders = [
        render_view(
            camera,
            output_dir,
            "both-interior",
            Vector((0.0, 390.0, 205.0)),
            Vector((0.0, 77.0, 140.0)),
            closeup_visible,
        ),
        render_view(
            camera,
            output_dir,
            "left-interior",
            Vector((-285.0, 315.0, 205.0)),
            Vector((-86.0, 77.0, 140.0)),
            side_visible["left"],
        ),
        render_view(
            camera,
            output_dir,
            "right-interior",
            Vector((285.0, 315.0, 205.0)),
            Vector((86.0, 77.0, 140.0)),
            side_visible["right"],
        ),
        render_view(
            camera,
            output_dir,
            "left-exterior",
            Vector((-260.0, -250.0, 190.0)),
            Vector((-86.0, 77.0, 140.0)),
            side_visible["left"],
        ),
        render_view(
            camera,
            output_dir,
            "right-exterior",
            Vector((260.0, -250.0, 190.0)),
            Vector((86.0, 77.0, 140.0)),
            side_visible["right"],
        ),
        render_view(
            camera,
            output_dir,
            "left-root-detail",
            Vector((-173.0, 168.0, 170.0)),
            Vector((-103.0, 85.0, 147.0)),
            {
                candidate_objects[0],
                require_object(config["sides"]["left"]["eye_bucket"]),
                require_object(config["sides"]["left"]["owner_shell"]),
            },
        ),
        render_view(
            camera,
            output_dir,
            "right-root-detail",
            Vector((173.0, 168.0, 170.0)),
            Vector((103.0, 85.0, 147.0)),
            {
                candidate_objects[1],
                require_object(config["sides"]["right"]["eye_bucket"]),
                require_object(config["sides"]["right"]["owner_shell"]),
            },
        ),
        render_view(
            camera,
            output_dir,
            "whole-head-front",
            Vector((0.0, -520.0, 210.0)),
            Vector((0.0, 35.0, 125.0)),
            whole_head_visible,
        ),
        render_view(
            camera,
            output_dir,
            "whole-head-three-quarter",
            Vector((-360.0, -420.0, 235.0)),
            Vector((0.0, 35.0, 125.0)),
            whole_head_visible,
        ),
    ]

    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in whole_head_visible
            obj.hide_render = obj not in whole_head_visible
    camera.location = Vector((-360.0, -420.0, 235.0))
    point_at(camera, Vector((0.0, 35.0, 125.0)))

    protected_after = {
        name: v5.mesh_fingerprint(bpy.data.objects[name])
        for name in protected_before
    }
    if protected_before != protected_after:
        raise ValueError("A preserved source/review mesh changed")
    final_mesh_count = sum(obj.type == "MESH" for obj in bpy.data.objects)
    if final_mesh_count != original_mesh_count:
        raise ValueError("Review must replace two rejected meshes with exactly two candidates")

    scene = bpy.context.scene
    scene["review_status"] = config["status"]
    scene["rejected_c002_objects_removed"] = True
    scene["replacement_mount_geometry_count"] = 2
    scene["root_count_per_connector"] = 2
    scene["candidate_owner_shells"] = "left_upper_head,right_upper_head"
    scene["source_mesh_geometry_unchanged"] = True
    scene["production_shell_boolean_performed"] = False
    blend_path = output_dir / "c002-outer-flange-dual-root-upper-head-review-v2.blend"
    scene["saved_whole_head_view_includes_both_eye_buckets"] = True
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "source_reinforcement_blend": str(source_blend.relative_to(REPO_ROOT)),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "interface_revision": interface["interface_revision"],
        "side_records": side_records,
        "inherited_gate6_hole_center_mirror_delta_mm": round(mirrored_hole_error, 6),
        "exact_source_side_hole_positions_preserved": True,
        "rejected_c002_objects_removed": sorted(rejected_names),
        "saved_whole_head_view_includes_both_eye_buckets": True,
        "unrelated_c010_c012_used_as_mount_anchors": False,
        "replacement_mount_geometry_count": len(candidate_objects),
        "root_count_per_connector": int(config["root_count_per_connector"]),
        "all_candidates_have_two_roots": all(
            record["root_count"] == int(config["root_count_per_connector"])
            for record in side_records
        ),
        "all_candidates_closed_and_manifold": all(
            gate5.topology_counts(obj) == (0, 0) for obj in candidate_objects
        ),
        "all_candidates_overlap_upper_head_owner_shell": all(
            record["candidate_overlaps_owner_shell"] for record in side_records
        ),
        "all_candidates_preserve_bucket_clearance": all(
            record["candidate_to_bucket_gap_mm"]
            >= float(config["root"]["minimum_candidate_to_bucket_clearance_mm"])
            for record in side_records
        ),
        "all_hidden_roots_clear_eye_buckets": all(
            root["root_to_bucket_gap_before_union_mm"]
            >= float(config["root"]["minimum_root_to_bucket_clearance_mm"])
            for record in side_records
            for root in record["root_records"]
        ),
        "preserved_source_mesh_count": len(protected_before),
        "preserved_source_mesh_geometry_unchanged": protected_before == protected_after,
        "production_shell_boolean_performed": False,
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": renders,
        },
        "no_stl_or_gcode_exported": True,
        "review_holds": config["review_holds"],
    }
    report_path = (
        output_dir / "c002-outer-flange-dual-root-upper-head-review-v2-validation.json"
    )
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
