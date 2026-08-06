#!/usr/bin/env python3
"""Generate an eight-flange broad-base eye-mount structural review.

Each side receives four review candidates: the outer and lower head-shell
flanges and their matching eye-bucket flanges. Every candidate preserves the
Gate 6 mating tab and hole, then adds a continuous flared base on the owner
side. Source shell and bucket meshes remain unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_c002_outer_flange_dual_root_upper_head_review_v2 as v2  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate6_eye_modules as gate6  # noqa: E402
import generate_rear_cassette_lossless_repartition_review_v5 as v5  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/eye-all-eight-flange-broad-base-review-v3.json"
DEFAULT_OUTPUT = PACKAGE_ROOT / "output/50-eye-mount-reviews/eye-all-eight-flange-broad-base-review-v3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def mount_frames(geometry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    settings = gate6.CONFIG["head_mount"]
    outer = geometry["outer"]
    aperture = geometry["aperture"]
    inward = geometry["inward"]
    if len(outer) != 4 or len(aperture) != 4:
        raise ValueError("Eye mount expects matching four-sided loops")
    edges = [(index, (index + 1) % 4) for index in range(4)]
    midpoints = {
        edge: (outer[edge[0]] + outer[edge[1]]) / 2.0 for edge in edges
    }
    side_edge = max(edges, key=lambda edge: abs(midpoints[edge].x))
    lower_edge = min(
        (edge for edge in edges if edge != side_edge),
        key=lambda edge: midpoints[edge].z,
    )
    length = float(settings["tab_length_mm"])
    depth = float(settings["tab_depth_mm"])
    thickness = float(settings["tab_thickness_mm"])
    gap = float(settings["tab_face_gap_mm"])
    overlap = float(settings["shell_overlap_mm"])
    front_recess = float(settings["front_recess_mm"])
    hole_depth = float(settings["bolt_depth_from_eye_plane_mm"])
    result = {}
    for role, edge in (("outer", side_edge), ("lower", lower_edge)):
        first, second = edge
        anchor = midpoints[edge]
        aperture_midpoint = (aperture[first] + aperture[second]) / 2.0
        tangent = outer[second] - outer[first]
        tangent -= inward * tangent.dot(inward)
        if tangent.length < 0.01:
            raise ValueError(
                f"{geometry['side']} {role} mount edge has no tangent"
            )
        tangent.normalize()
        radial = inward.cross(tangent).normalized()
        if radial.dot(aperture_midpoint - anchor) < 0.0:
            radial = -radial
        head_center = (
            anchor
            + radial * (thickness / 2.0 - overlap)
            + inward * (front_recess + depth / 2.0)
        )
        eye_center = (
            anchor
            + radial * (thickness - overlap + gap + thickness / 2.0)
            + inward * (front_recess + depth / 2.0)
        )
        result[role] = {
            "role": role,
            "edge": list(edge),
            "anchor": anchor,
            "tangent": tangent,
            "inward": inward,
            "radial": radial,
            "dimensions": (length, depth, thickness),
            "head_center": head_center,
            "eye_center": eye_center,
            "head_hole_center": head_center
            + inward * (hole_depth - depth / 2.0),
            "eye_hole_center": eye_center
            + inward * (hole_depth - depth / 2.0),
            "hole_diameter": float(settings["m2_5_clearance_diameter_mm"]),
            "front_recess": front_recess,
            "mating_gap": gap,
        }
    return result


def create_broad_base(
    name: str,
    center: Vector,
    frame: dict[str, Any],
    backing_sign: float,
    values: dict[str, Any],
    material: bpy.types.Material,
) -> bpy.types.Object:
    backing = frame["radial"] * backing_sign
    owner_face = center + backing * frame["dimensions"][2] / 2.0
    overlap = float(values["flange_overlap_mm"])
    total_depth = float(values["total_backing_depth_mm"])
    if overlap <= 0.0 or overlap >= total_depth:
        raise ValueError(
            "Broad-base overlap must be positive and below total depth"
        )
    return v2.tapered_prism(
        name,
        owner_face - backing * overlap,
        owner_face + backing * (total_depth - overlap),
        frame["tangent"],
        frame["inward"],
        float(values["flange_end_length_mm"]),
        float(values["owner_end_length_mm"]),
        float(values["flange_end_depth_mm"]),
        float(values["owner_end_depth_mm"]),
        material,
    )


def create_candidate(
    side: str,
    role: str,
    owner_kind: str,
    frame: dict[str, Any],
    owner: bpy.types.Object,
    opposing_center: Vector,
    config: dict[str, Any],
    material: bpy.types.Material,
    collection: bpy.types.Collection,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    is_head = owner_kind == "head"
    center = frame["head_center"] if is_head else frame["eye_center"]
    hole_center = (
        frame["head_hole_center"] if is_head else frame["eye_hole_center"]
    )
    backing_sign = -1.0 if is_head else 1.0
    prefix = "HEAD" if is_head else "EYE"
    side_code = "L" if side == "left" else "R"
    name = (
        f"E4_PROPOSED__{side_code}__{role.upper()}__"
        f"{prefix}_flange_broad_base"
    )
    candidate = gate5.box(
        name,
        center,
        (frame["tangent"], frame["inward"], frame["radial"]),
        frame["dimensions"],
        material,
    )
    v2.move_to_collection(candidate, collection)
    opposing = gate5.box(
        f"{name}__opposing_clearance_tool",
        opposing_center,
        (frame["tangent"], frame["inward"], frame["radial"]),
        frame["dimensions"],
        material,
    )
    base = create_broad_base(
        f"{name}__broad_base_tool",
        center,
        frame,
        backing_sign,
        config["broad_base"],
        material,
    )
    base_volume = gate5.mesh_volume(base)
    checks = {
        "base_overlaps_flange": v2.surfaces_overlap(base, candidate),
        "base_overlaps_owner": v2.surfaces_overlap(base, owner),
        "base_overlaps_opposing_flange": v2.surfaces_overlap(base, opposing),
    }
    if not checks["base_overlaps_flange"] or not checks["base_overlaps_owner"]:
        raise ValueError(f"{name} broad base misses its flange or owner")
    if checks["base_overlaps_opposing_flange"]:
        raise ValueError(f"{name} broad base enters the mating flange envelope")
    gate5.apply_boolean(candidate, base, "UNION", solver="EXACT")
    gate6.cut_axis_hole(
        candidate,
        f"{name}__m2_5_clearance",
        hole_center,
        frame["radial"],
        frame["hole_diameter"],
        float(config["broad_base"]["total_backing_depth_mm"])
        + frame["dimensions"][2]
        + 4.0,
    )
    opposing_gap = v2.surface_distance(candidate, opposing)
    opposing_overlap = v2.surfaces_overlap(candidate, opposing)
    owner_overlap = v2.surfaces_overlap(candidate, owner)
    boundary, nonmanifold = gate5.topology_counts(candidate)
    opposing_mesh = opposing.data
    bpy.data.objects.remove(opposing, do_unlink=True)
    if opposing_mesh.users == 0:
        bpy.data.meshes.remove(opposing_mesh)
    candidate.color = tuple(material.diffuse_color)
    candidate.show_in_front = True
    candidate["review_only"] = True
    candidate["owner_kind"] = owner_kind
    candidate["owner_object"] = owner.name
    candidate["mount_role"] = role
    candidate["broad_base_count"] = 1
    if boundary or nonmanifold:
        raise ValueError(f"{name} is not closed and manifold")
    if not owner_overlap:
        raise ValueError(f"{name} does not overlap {owner.name}")
    if opposing_overlap or opposing_gap < float(
        config["broad_base"]["minimum_mating_gap_mm"]
    ):
        raise ValueError(
            f"{name} violates mating clearance: overlap={opposing_overlap}, "
            f"gap={opposing_gap:.4f} mm"
        )
    return candidate, {
        "side": side,
        "role": role,
        "owner_kind": owner_kind,
        "candidate": candidate.name,
        "owner_object": owner.name,
        "mount_edge_indices": frame["edge"],
        "flange_center_mm": [round(value, 4) for value in center],
        "m2_5_hole_center_mm": [round(value, 4) for value in hole_center],
        "m2_5_hole_axis": [round(value, 5) for value in frame["radial"]],
        "m2_5_clearance_diameter_mm": frame["hole_diameter"],
        "flange_dimensions_mm": list(frame["dimensions"]),
        "front_recess_mm": frame["front_recess"],
        "mating_gap_mm": round(opposing_gap, 4),
        "base_overlaps_flange_before_union": checks["base_overlaps_flange"],
        "base_overlaps_owner_before_union": checks["base_overlaps_owner"],
        "base_clears_opposing_flange_before_union": not checks[
            "base_overlaps_opposing_flange"
        ],
        "candidate_overlaps_owner": owner_overlap,
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "broad_base_volume_before_union_mm3": round(base_volume, 4),
        "candidate_volume_mm3": round(gate5.mesh_volume(candidate), 4),
    }


def point_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (
        target - camera.location
    ).to_track_quat("-Z", "Y").to_euler()


def configure_scene(
    output_dir: Path, resolution_px: int
) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.name = "Eye_All_Eight_Flange_Broad_Base_Review_V3"
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
    camera_data = bpy.data.cameras.new("E4_REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("E4_REVIEW_ONLY__Camera", camera_data)
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
    path = (
        output_dir
        / "renders"
        / f"eye-all-eight-flange-broad-base-{name}.png"
    )
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
        raise ValueError(
            f"Open the configured accepted reinforcement blend: {source_blend}"
        )
    if repo_path(config["gate6_eye_config"]) != gate6.CONFIG_PATH.resolve():
        raise ValueError("Configured Gate 6 eye settings path changed")
    interface = json.loads(
        repo_path(config["shared_interface_path"]).read_text(encoding="utf-8")
    )
    if interface["interface_revision"] != config["required_interface_revision"]:
        raise ValueError("Shared shell/aluminum interface revision changed")
    output_dir.mkdir(parents=True, exist_ok=True)

    source_reference_names = {
        values[key]
        for values in config["sides"].values()
        for key in (
            "outer_head_source_reference",
            "lower_head_source_reference",
        )
    }
    protected_before = {
        obj.name: v5.mesh_fingerprint(obj)
        for obj in bpy.data.objects
        if obj.type == "MESH"
    }
    source_visible_names = {
        obj.name
        for obj in bpy.data.objects
        if obj.type == "MESH" and not obj.hide_viewport and not obj.hide_get()
    }

    collection_names = (
        "E4_PROPOSED_HEAD_FLANGES_PURPLE",
        "E4_PROPOSED_EYE_FLANGES_ORANGE",
        "E4_PRESERVED_EYE_BUCKETS_BLUE",
        "E4_OWNER_SHELLS_GRAY",
        "E4_SOURCE_MOUNT_REFERENCES_HIDDEN",
    )
    collections = {}
    for name in collection_names:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        collections[name] = collection

    head_material = gate5.material(
        "E4__Proposed_Head_Flange_Broad_Base_Purple",
        v2.hex_color(config["display"]["head_candidate_color"]),
    )
    eye_material = gate5.material(
        "E4__Proposed_Eye_Flange_Broad_Base_Orange",
        v2.hex_color(config["display"]["eye_candidate_color"]),
    )
    geometry_by_side = {
        value["side"]: value for value in gate6.eye_geometry()
    }
    candidates: list[bpy.types.Object] = []
    records: list[dict[str, Any]] = []
    side_visible: dict[str, set[bpy.types.Object]] = {}
    pair_visible: dict[tuple[str, str], set[bpy.types.Object]] = {}

    for side, names in config["sides"].items():
        bucket = v2.require_object(names["eye_bucket"])
        bucket.color = v2.hex_color(config["display"]["eye_bucket_color"])
        bucket.show_wire = True
        v2.link_reference(
            bucket, collections["E4_PRESERVED_EYE_BUCKETS_BLUE"]
        )
        side_objects: set[bpy.types.Object] = {bucket}
        frames = mount_frames(geometry_by_side[side])
        for role, frame in frames.items():
            owner = v2.require_object(names[f"{role}_head_owner"])
            owner.color = v2.hex_color(
                config["display"]["owner_shell_color"]
            )
            owner.show_wire = True
            v2.link_reference(owner, collections["E4_OWNER_SHELLS_GRAY"])
            head_candidate, head_record = create_candidate(
                side,
                role,
                "head",
                frame,
                owner,
                frame["eye_center"],
                config,
                head_material,
                collections["E4_PROPOSED_HEAD_FLANGES_PURPLE"],
            )
            eye_candidate, eye_record = create_candidate(
                side,
                role,
                "eye",
                frame,
                bucket,
                frame["head_center"],
                config,
                eye_material,
                collections["E4_PROPOSED_EYE_FLANGES_ORANGE"],
            )
            hole_delta = Vector(
                eye_record["m2_5_hole_center_mm"]
            ) - Vector(head_record["m2_5_hole_center_mm"])
            projected_error = (
                hole_delta
                - frame["radial"] * hole_delta.dot(frame["radial"])
            ).length
            if projected_error > 0.001:
                raise ValueError(f"{side} {role} M2.5 pair is not coaxial")
            head_record["paired_hole_axis_error_mm"] = round(
                projected_error, 6
            )
            eye_record["paired_hole_axis_error_mm"] = round(
                projected_error, 6
            )
            candidates.extend((head_candidate, eye_candidate))
            records.extend((head_record, eye_record))
            pair = {head_candidate, eye_candidate, owner, bucket}
            pair_visible[(side, role)] = pair
            side_objects |= pair
        side_visible[side] = side_objects

    for name in source_reference_names:
        obj = v2.require_object(name)
        v2.link_reference(
            obj, collections["E4_SOURCE_MOUNT_REFERENCES_HIDDEN"]
        )
        obj.hide_viewport = True
        obj.hide_render = True
        obj.hide_set(True)

    all_eight_visible = side_visible["left"] | side_visible["right"]
    whole_head_visible = {
        bpy.data.objects[name]
        for name in source_visible_names
        if name in bpy.data.objects and name not in source_reference_names
    } | set(candidates)
    required_buckets = {
        v2.require_object(config["sides"][side]["eye_bucket"])
        for side in ("left", "right")
    }
    whole_head_visible |= required_buckets
    if not required_buckets.issubset(whole_head_visible):
        raise ValueError("Saved whole-head view must include both eye buckets")
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in all_eight_visible
            obj.hide_render = True

    camera = configure_scene(
        output_dir, int(config["display"]["render_resolution_px"])
    )
    renders = [
        render_view(
            camera,
            output_dir,
            "all-eight-interior",
            Vector((0.0, 390.0, 205.0)),
            Vector((0.0, 77.0, 140.0)),
            all_eight_visible,
        ),
        render_view(
            camera,
            output_dir,
            "left-all-four",
            Vector((-285.0, 315.0, 205.0)),
            Vector((-86.0, 77.0, 140.0)),
            side_visible["left"],
        ),
        render_view(
            camera,
            output_dir,
            "right-all-four",
            Vector((285.0, 315.0, 205.0)),
            Vector((86.0, 77.0, 140.0)),
            side_visible["right"],
        ),
        render_view(
            camera,
            output_dir,
            "left-outer-pair",
            Vector((-173.0, 168.0, 170.0)),
            Vector((-103.0, 85.0, 147.0)),
            pair_visible[("left", "outer")],
        ),
        render_view(
            camera,
            output_dir,
            "right-outer-pair",
            Vector((173.0, 168.0, 170.0)),
            Vector((103.0, 85.0, 147.0)),
            pair_visible[("right", "outer")],
        ),
        render_view(
            camera,
            output_dir,
            "left-lower-pair",
            Vector((-170.0, 175.0, 95.0)),
            Vector((-84.0, 78.0, 105.0)),
            pair_visible[("left", "lower")],
        ),
        render_view(
            camera,
            output_dir,
            "right-lower-pair",
            Vector((170.0, 175.0, 95.0)),
            Vector((84.0, 78.0, 105.0)),
            pair_visible[("right", "lower")],
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
    counts_by_side = {
        side: sum(record["side"] == side for record in records)
        for side in ("left", "right")
    }
    counts_by_owner_kind = {
        kind: sum(record["owner_kind"] == kind for record in records)
        for kind in ("head", "eye")
    }
    if counts_by_side != {"left": 4, "right": 4}:
        raise ValueError(
            f"Expected four flange candidates per side: {counts_by_side}"
        )
    if counts_by_owner_kind != {"head": 4, "eye": 4}:
        raise ValueError(
            f"Expected four head and four eye candidates: "
            f"{counts_by_owner_kind}"
        )

    scene = bpy.context.scene
    scene["review_status"] = config["status"]
    scene["flange_candidate_count"] = len(candidates)
    scene["flange_candidate_count_left"] = counts_by_side["left"]
    scene["flange_candidate_count_right"] = counts_by_side["right"]
    scene["broad_base_count"] = len(candidates)
    scene["v2_dual_end_roots_rejected"] = True
    scene["source_mesh_geometry_unchanged"] = True
    scene["production_owner_boolean_performed"] = False
    scene["saved_whole_head_view_includes_both_eye_buckets"] = True
    blend_path = output_dir / "eye-all-eight-flange-broad-base-review-v3.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "source_reinforcement_blend": str(
            source_blend.relative_to(REPO_ROOT)
        ),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "interface_revision": interface["interface_revision"],
        "v2_dual_end_roots_rejected": True,
        "candidate_records": records,
        "flange_candidate_count": len(candidates),
        "flange_candidate_count_by_side": counts_by_side,
        "flange_candidate_count_by_owner_kind": counts_by_owner_kind,
        "exactly_four_candidates_per_side": counts_by_side
        == {"left": 4, "right": 4},
        "exactly_eight_broad_bases": len(candidates) == 8,
        "all_bases_overlap_their_flange": all(
            record["base_overlaps_flange_before_union"]
            for record in records
        ),
        "all_bases_overlap_their_owner": all(
            record["base_overlaps_owner_before_union"]
            for record in records
        ),
        "all_bases_clear_opposing_flange": all(
            record["base_clears_opposing_flange_before_union"]
            for record in records
        ),
        "all_candidates_closed_and_manifold": all(
            gate5.topology_counts(obj) == (0, 0) for obj in candidates
        ),
        "all_candidates_preserve_mating_gap": all(
            record["mating_gap_mm"]
            >= float(config["broad_base"]["minimum_mating_gap_mm"])
            for record in records
        ),
        "all_paired_m2_5_holes_coaxial": all(
            record["paired_hole_axis_error_mm"] <= 0.001
            for record in records
        ),
        "saved_whole_head_view_includes_both_eye_buckets": True,
        "source_mount_references_hidden": sorted(source_reference_names),
        "preserved_source_mesh_count": len(protected_before),
        "preserved_source_mesh_geometry_unchanged": (
            protected_before == protected_after
        ),
        "production_owner_boolean_performed": False,
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": renders,
        },
        "no_stl_or_gcode_exported": True,
        "review_holds": config["review_holds"],
    }
    report_path = (
        output_dir
        / "eye-all-eight-flange-broad-base-review-v3-validation.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
