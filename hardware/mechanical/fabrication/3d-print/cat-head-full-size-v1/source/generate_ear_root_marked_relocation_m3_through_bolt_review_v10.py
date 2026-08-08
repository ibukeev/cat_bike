#!/usr/bin/env python3
"""Relocate the user-marked connector and retain aligned M3 flange bores."""

from __future__ import annotations

from array import array
import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Matrix, Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_c002_outer_flange_dual_root_upper_head_review_v2 as c002_v2  # noqa: E402
import generate_ear_root_insertion_fit_review_v3 as ear_v3  # noqa: E402
import generate_ear_root_restored_coverage_review_v2 as ear_v2  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate6_eye_modules as gate6  # noqa: E402
import generate_gate7_glow_panel_inserts as gate7  # noqa: E402
import generate_gate8_full_size_iteration as gate8  # noqa: E402
import generate_rear_cassette_lossless_repartition_review_v5 as rear_v5  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/ear-root-marked-relocation-m3-through-bolt-review-v10.json"
)
DEFAULT_OUTPUT = PACKAGE_ROOT / "output/00-current-review"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def point_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (
        target - camera.location
    ).to_track_quat("-Z", "Y").to_euler()


def configure_scene(output_dir: Path, resolution_px: int) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.name = "Ear_Root_Internal_Rectangular_Flange_Placement_Review_V10"
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
    camera_data = bpy.data.cameras.new("EAR10_REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("EAR10_REVIEW_ONLY__Camera", camera_data)
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
    xray: bool = False,
) -> str:
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_render = obj not in visible
    camera.location = location
    point_at(camera, target)
    shading = bpy.context.scene.display.shading
    shading.show_xray = xray
    shading.xray_alpha = 0.28
    path = (
        output_dir
        / "renders"
        / f"ear-root-marked-relocation-m3-through-bolt-{name}.png"
    )
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path.relative_to(REPO_ROOT))


def compare_render_pixels(
    baseline_path: Path,
    candidate_path: Path,
) -> dict[str, Any]:
    baseline = bpy.data.images.load(str(baseline_path), check_existing=False)
    candidate = bpy.data.images.load(str(candidate_path), check_existing=False)
    try:
        if tuple(baseline.size) != tuple(candidate.size):
            raise ValueError("Exterior comparison images have different sizes")
        channel_count = len(baseline.pixels)
        baseline_pixels = array("f", [0.0]) * channel_count
        candidate_pixels = array("f", [0.0]) * channel_count
        baseline.pixels.foreach_get(baseline_pixels)
        candidate.pixels.foreach_get(candidate_pixels)
        different_channels = 0
        maximum_delta = 0.0
        for baseline_value, candidate_value in zip(
            baseline_pixels, candidate_pixels
        ):
            delta = abs(baseline_value - candidate_value)
            if delta > 1.0e-6:
                different_channels += 1
                maximum_delta = max(maximum_delta, delta)
        return {
            "resolution_px": [int(value) for value in baseline.size],
            "different_channel_count": different_channels,
            "maximum_channel_delta": round(maximum_delta, 8),
            "identical": different_channels == 0,
        }
    finally:
        bpy.data.images.remove(baseline)
        bpy.data.images.remove(candidate)



def boundary_record(record: dict[str, Any]) -> dict[str, Any]:
    vectors = (
        "midpoint", "tangent", "inward", "radial", "owner_inward", "owner_radial"
    )
    return {
        "edge": [int(value) for value in record["edge"]],
        "owner": record["owner"],
        "length": float(record["length"]),
        **{
            key: [float(value) for value in record[key]]
            for key in vectors
        },
    }


def extract_boundary(
    v3_config: dict[str, Any], side: str
) -> list[dict[str, Any]]:
    if side not in {"left", "right"}:
        raise ValueError(f"Unsupported side: {side}")
    original = gate7.CONFIG
    gate7.CONFIG = copy.deepcopy(original)
    relief = v3_config["accepted_v2_relief"]
    fit = v3_config["fit_clearance"]
    values = gate7.CONFIG["ear_root_interfaces"]
    values["connector_clearance_mm"] = float(
        relief["connector_clearance_mm"]
    )
    values["connector_corner_relief_depth_mm"] = float(
        relief["connector_corner_relief_depth_mm"]
    )
    values["connector_side_tip_setback_mm"] = float(
        relief["connector_side_tip_setback_mm"]
    )
    gate7.CONFIG["insert"]["perimeter_clearance_mm"] = float(
        fit["candidate_deep_body_perimeter_clearance_mm"]
    )
    gate7.CONFIG["visible_seam_cap"]["perimeter_clearance_mm"] = float(
        fit["candidate_visible_cap_perimeter_clearance_mm"]
    )
    try:
        context = gate7.source_context()
        groups = {
            group["name"]: group
            for group in gate7.connected_panel_groups(context)
        }
        group = groups[v3_config["sides"][side]["candidate_group"]]
        records = gate7.group_boundary(group, context)
        for record in records:
            neighbor_faces = [
                face_index
                for face_index in context["edge_faces"][tuple(record["edge"])]
                if context["assignments"][face_index] == record["owner"]
            ]
            if not neighbor_faces:
                owner_inward = Vector(record["inward"]).normalized()
            else:
                owner_outward = sum(
                    (
                        gate5.outward_normal(
                            context["model"].faces[index], context["transformed"]
                        )
                        for index in neighbor_faces
                    ),
                    Vector(),
                )
                if owner_outward.length < 0.01:
                    raise ValueError(
                        f"Boundary edge {record['edge']} has opposing owner normals"
                    )
                owner_inward = -owner_outward.normalized()
            tangent = Vector(record["tangent"]).normalized()
            insert_radial = Vector(record["radial"]).normalized()
            owner_radial = insert_radial - owner_inward * insert_radial.dot(owner_inward)
            owner_radial -= tangent * owner_radial.dot(tangent)
            if owner_radial.length < 0.01:
                raise ValueError(f"Boundary edge {record['edge']} has no owner radial")
            owner_radial.normalize()
            if owner_radial.dot(insert_radial) < 0.0:
                owner_radial.negate()
            record["owner_inward"] = owner_inward
            record["owner_radial"] = owner_radial
        return [boundary_record(record) for record in records]
    finally:
        gate7.CONFIG = original


def shared_pair_frame(
    record: dict[str, Any],
    fraction: float,
) -> dict[str, Vector]:
    midpoint = Vector(record["midpoint"])
    source_tangent = Vector(record["tangent"]).normalized()
    insert_interior = Vector(record["inward"]).normalized()
    owner_interior = Vector(record["owner_inward"]).normalized()
    insert_across = Vector(record["radial"]).normalized()
    owner_across = Vector(record["owner_radial"]).normalized()
    anchor = midpoint + source_tangent * (
        (float(fraction) - 0.5) * float(record["length"])
    )
    if insert_interior.dot(owner_interior) < 0.0:
        owner_interior.negate()
    interior = insert_interior + owner_interior
    if interior.length < 0.01:
        raise ValueError("Adjacent owners have no shared interior normal")
    interior.normalize()
    tangent = source_tangent - interior * source_tangent.dot(interior)
    if tangent.length < 0.01:
        raise ValueError("Internal flange frame lost the seam tangent")
    tangent.normalize()
    across = interior.cross(tangent).normalized()
    if across.dot(insert_across) < 0.0:
        across.negate()
    if across.dot(owner_across) < 0.0:
        raise ValueError("Shared seam direction disagrees across owner frames")
    exterior = -interior
    return {
        "anchor": anchor,
        "tangent": tangent,
        "interior": interior,
        "across": across,
        "exterior": exterior,
        "insert_interior": insert_interior,
        "owner_interior": owner_interior,
        "insert_across": insert_across,
        "owner_across": owner_across,
    }


def create_pair(
    frame: dict[str, Vector],
    values: dict[str, Any],
    moving_body: bpy.types.Object,
    fixed_owner: bpy.types.Object,
    materials: dict[str, bpy.types.Material],
    side: str,
    location_id: str,
) -> dict[str, Any]:
    anchor = frame["anchor"]
    tangent = frame["tangent"]
    interior = frame["interior"]
    across = frame["across"]
    length = float(values["tab_length_mm"])
    depth = float(values["tab_interior_depth_mm"])
    thickness = float(values["tab_thickness_mm"])
    gap = float(values["mating_gap_mm"])
    shared_offset = float(values["shared_tab_interior_offset_mm"])
    moving_relief = float(values.get("moving_tab_interior_relief_mm", 0.0))
    hole_diameter = float(values["m3_clearance_diameter_mm"])
    hole_cut_extension = float(values["hole_cut_extension_mm"])
    minimum_hole_edge = float(values["minimum_hole_edge_material_mm"])
    if shared_offset < 0.0 or shared_offset >= depth:
        raise ValueError("Shared tab interior offset must be nonnegative and inside tab depth")
    dimensions = (length, depth, thickness)
    offset = gap / 2.0 + thickness / 2.0
    interior_center = interior * (depth / 2.0 + shared_offset)
    orange_center = (
        anchor + across * offset + interior_center + interior * moving_relief
    )
    green_center = anchor - across * offset + interior_center
    axes = (tangent, interior, across)
    label = f"{side.upper()}_{location_id}"

    orange = gate5.box(
        f"EAR10_{label}_INSERT_FLANGE__orange",
        orange_center,
        axes,
        dimensions,
        materials["orange"],
    )
    green = gate5.box(
        f"EAR10_{label}_HEAD_FLANGE__green",
        green_center,
        axes,
        dimensions,
        materials["green"],
    )
    hole_center = anchor + interior * (
        shared_offset + depth / 2.0 + moving_relief / 2.0
    )
    hole_span = 2.0 * (
        gap / 2.0 + thickness + hole_cut_extension
    )
    hole_radius = hole_diameter / 2.0
    tangent_edge_material = length / 2.0 - hole_radius
    interior_edge_material = (
        depth / 2.0 - abs(moving_relief) / 2.0 - hole_radius
    )
    actual_minimum_hole_edge = min(
        tangent_edge_material, interior_edge_material
    )
    if actual_minimum_hole_edge < minimum_hole_edge:
        raise ValueError(
            f"V10 {label} M3 bore edge material is "
            f"{actual_minimum_hole_edge:.3f} mm, below {minimum_hole_edge:.3f} mm"
        )
    for role, tab in (("orange", orange), ("green", green)):
        gate6.cut_axis_hole(
            tab,
            f"EAR10_{label}_{role.upper()}__m3_clearance",
            hole_center,
            across,
            hole_diameter,
            hole_span,
        )
        gate5.require_manifold(tab, f"V10 {label} drilled {role} tab")
    orange.color = orange.data.materials[0].diffuse_color
    green.color = green.data.materials[0].diffuse_color

    if c002_v2.surfaces_overlap(orange, green):
        raise ValueError(f"V10 {label} rectangular tabs overlap")
    measured_gap = c002_v2.surface_distance(orange, green)
    if abs(measured_gap - gap) > 0.01:
        raise ValueError(
            f"V10 {label} placement gap changed: expected {gap}, got {measured_gap}"
        )
    orange_owner_hits = ear_v3.world_triangle_intersection_count(
        orange, moving_body
    )
    green_owner_hits = ear_v3.world_triangle_intersection_count(
        green, fixed_owner
    )
    if orange_owner_hits == 0:
        raise ValueError(f"V10 {label} orange tab does not root into moving owner")
    if green_owner_hits == 0:
        raise ValueError(f"V10 {label} green tab does not root into fixed owner")

    return {
        "side": side,
        "location_id": location_id,
        "orange": orange,
        "green": green,
        "pair_center": (
            anchor
            + interior * (depth / 2.0 + shared_offset + moving_relief / 2.0)
        ),
        "frame": frame,
        "dimensions_mm": [length, depth, thickness],
        "shared_offset_mm": shared_offset,
        "moving_tab_interior_relief_mm": moving_relief,
        "fastener_center": hole_center,
        "fastener_axis": across,
        "m3_clearance_diameter_mm": hole_diameter,
        "hole_span_mm": hole_span,
        "minimum_hole_edge_material_mm": actual_minimum_hole_edge,
        "measured_gap_mm": measured_gap,
        "orange_owner_intersection_pairs": orange_owner_hits,
        "green_owner_intersection_pairs": green_owner_hits,
    }


def mirror_vector(value: Vector) -> Vector:
    return Vector((-value.x, value.y, value.z))


def mirror_pair_from_right(
    right_pair: dict[str, Any],
    left_body: bpy.types.Object,
    left_fixed_owner: bpy.types.Object,
    materials: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    location_id = right_pair["location_id"]
    objects = {}
    for role, material_name in (("orange", "orange"), ("green", "green")):
        source = right_pair[role]
        mirrored = ear_v2.deserialize_mesh(
            f"EAR10_LEFT_{location_id}_{role.upper()}_FLANGE__{role}",
            ear_v3.mirror_payload(ear_v2.serialize_mesh(source)),
        )
        bpy.context.scene.collection.objects.link(mirrored)
        mirrored.data.materials.clear()
        mirrored.data.materials.append(materials[material_name])
        mirrored.color = materials[material_name].diffuse_color
        gate5.require_manifold(
            mirrored, f"V10 LEFT_{location_id} mirrored {role} tab"
        )
        objects[role] = mirrored
    gap = c002_v2.surface_distance(objects["orange"], objects["green"])
    if abs(gap - right_pair["measured_gap_mm"]) > 0.01:
        raise ValueError(f"V10 LEFT_{location_id} mirrored gap changed")
    orange_hits = ear_v3.world_triangle_intersection_count(
        objects["orange"], left_body
    )
    green_hits = ear_v3.world_triangle_intersection_count(
        objects["green"], left_fixed_owner
    )
    if orange_hits == 0 or green_hits == 0:
        raise ValueError(
            f"V10 LEFT_{location_id} mirrored owner root missing: "
            f"orange={orange_hits}, green={green_hits}"
        )
    frame = {
        key: mirror_vector(value)
        for key, value in right_pair["frame"].items()
    }
    return {
        "side": "left",
        "location_id": location_id,
        "orange": objects["orange"],
        "green": objects["green"],
        "pair_center": mirror_vector(right_pair["pair_center"]),
        "frame": frame,
        "dimensions_mm": list(right_pair["dimensions_mm"]),
        "shared_offset_mm": right_pair["shared_offset_mm"],
        "moving_tab_interior_relief_mm": right_pair[
            "moving_tab_interior_relief_mm"
        ],
        "fastener_center": mirror_vector(right_pair["fastener_center"]),
        "fastener_axis": mirror_vector(right_pair["fastener_axis"]),
        "m3_clearance_diameter_mm": right_pair[
            "m3_clearance_diameter_mm"
        ],
        "hole_span_mm": right_pair["hole_span_mm"],
        "minimum_hole_edge_material_mm": right_pair[
            "minimum_hole_edge_material_mm"
        ],
        "measured_gap_mm": gap,
        "orange_owner_intersection_pairs": orange_hits,
        "green_owner_intersection_pairs": green_hits,
    }


def validate_open_aligned_bore(pair: dict[str, Any]) -> dict[str, Any]:
    """Prove a slightly undersized gauge passes through both drilled tabs."""
    axis = pair["fastener_axis"].normalized()
    center = pair["fastener_center"]
    span = float(pair["hole_span_mm"])
    gauge_diameter = float(pair["m3_clearance_diameter_mm"]) - 0.2
    gauge = gate5.cylinder(
        f"EAR10_VALIDATION__{pair['side']}_{pair['location_id']}_m3_bore_gauge",
        center - axis * span / 2.0,
        center + axis * span / 2.0,
        gauge_diameter,
        vertices=24,
    )
    hits = {
        role: ear_v3.world_triangle_intersection_count(gauge, pair[role])
        for role in ("orange", "green")
    }
    bpy.data.objects.remove(gauge, do_unlink=True)
    if any(hits.values()):
        raise ValueError(
            f"V10 {pair['side']} {pair['location_id']} M3 bore is obstructed: {hits}"
        )
    return {
        "side": pair["side"],
        "location_id": pair["location_id"],
        "nominal": "M3",
        "clearance_diameter_mm": pair["m3_clearance_diameter_mm"],
        "undersized_gauge_diameter_mm": gauge_diameter,
        "orange_gauge_intersection_pairs": hits["orange"],
        "green_gauge_intersection_pairs": hits["green"],
        "common_center_mm": [round(value, 5) for value in center],
        "common_axis": [round(value, 6) for value in axis],
        "minimum_hole_edge_material_mm": round(
            pair["minimum_hole_edge_material_mm"], 4
        ),
        "open_and_aligned": True,
    }

def create_boolean_proof_part(
    tab: bpy.types.Object,
    owner: bpy.types.Object,
    name: str,
    operation: str,
    material: bpy.types.Material,
) -> bpy.types.Object:
    """Create a hidden review-only cutaway; never use it as connector geometry."""
    result = tab.copy()
    result.data = tab.data.copy()
    result.name = name
    bpy.context.scene.collection.objects.link(result)
    tool = owner.copy()
    tool.data = owner.data.copy()
    tool.name = f"{name}__owner_boolean_tool"
    bpy.context.scene.collection.objects.link(tool)
    gate5.apply_boolean(result, tool, operation, solver="MANIFOLD")
    if not result.data.polygons or gate5.mesh_volume(result) <= 0.001:
        raise ValueError(f"V10 review proof is empty: {name}")
    result.data.materials.clear()
    result.data.materials.append(material)
    result.color = material.diffuse_color
    result["review_only"] = True
    result["derived_from_tab"] = tab.name
    result["derived_from_owner"] = owner.name
    result["boolean_operation"] = operation
    return result


def fuse_owner_with_tabs(
    owner: bpy.types.Object,
    tabs: list[bpy.types.Object],
    name: str,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    composite = owner.copy()
    composite.data = owner.data.copy()
    composite.name = name
    bpy.context.scene.collection.objects.link(composite)
    for index, tab in enumerate(tabs):
        tool = tab.copy()
        tool.data = tab.data.copy()
        tool.name = f"{name}__union_tool_{index}"
        bpy.context.scene.collection.objects.link(tool)
        gate5.apply_boolean(composite, tool, "UNION", solver="EXACT")
    boundary, nonmanifold = gate5.topology_counts(composite)
    topology = {
        "connected_components": len(gate5.components(composite)),
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "faces": len(composite.data.polygons),
        "volume_mm3": round(gate5.mesh_volume(composite), 4),
    }
    if (
        topology["connected_components"] != 1
        or boundary
        or nonmanifold
    ):
        raise ValueError(f"V10 owner/tab composite is not manifold: {topology}")
    return composite, topology


def validate_side_path(
    side: str,
    composite: bpy.types.Object,
    orange_tabs: list[bpy.types.Object],
    deep_body: bpy.types.Object,
    green_tabs: list[bpy.types.Object],
    frame: dict[str, Any],
    v3_config: dict[str, Any],
    values: dict[str, Any],
    structural_targets: list[bpy.types.Object],
) -> dict[str, Any]:
    targets = [
        target
        for target in structural_targets
        if target.name != f"{side}_ear"
    ]
    samples = ear_v3.path_samples(frame, v3_config["insertion_path"])
    deep_margin = float(v3_config["fit_clearance"]["deep_body_path_margin_mm"])
    flange_margin = float(values["moving_flange_path_margin_mm"])
    deep_envelope = gate8.expanded_insert_cutter(
        deep_body, deep_margin, f"EAR10_VALIDATION__{side}_deep_body_margin"
    )
    flange_envelopes = []
    for orange in orange_tabs:
        envelope = gate8.expanded_insert_cutter(
            orange,
            flange_margin,
            f"EAR10_VALIDATION__{orange.name}_margin",
        )
        flange_envelopes.append((orange.name, envelope))
    actual_conflicts = []
    baseline_deep_conflicts = []
    flange_margin_conflicts = []
    maximum_actual = 0
    maximum_deep = 0
    maximum_flange_margin = 0
    for sample in samples:
        for obj in (composite, deep_envelope):
            obj.matrix_world = sample["matrix"]
        for _, envelope in flange_envelopes:
            envelope.matrix_world = sample["matrix"]
        actual_hits = ear_v3.collision_hits(
            composite, [*targets, *green_tabs]
        )
        deep_hits = ear_v3.collision_hits(deep_envelope, targets)
        margin_hits = {}
        for tab_name, envelope in flange_envelopes:
            hits = ear_v3.collision_hits(
                envelope, [*targets, *green_tabs]
            )
            if hits:
                margin_hits[tab_name] = hits
        maximum_actual = max(maximum_actual, sum(actual_hits.values()))
        maximum_deep = max(maximum_deep, sum(deep_hits.values()))
        maximum_flange_margin = max(
            maximum_flange_margin,
            sum(sum(hits.values()) for hits in margin_hits.values()),
        )
        metadata = {
            key: value for key, value in sample.items() if key != "matrix"
        }
        if actual_hits:
            actual_conflicts.append({**metadata, "hits": actual_hits})
        if deep_hits:
            baseline_deep_conflicts.append({**metadata, "hits": deep_hits})
        if margin_hits:
            flange_margin_conflicts.append(
                {**metadata, "per_tab_hits": margin_hits}
            )
    for obj in (composite, deep_envelope):
        obj.matrix_world = Matrix.Identity(4)
    for _, envelope in flange_envelopes:
        envelope.matrix_world = Matrix.Identity(4)
        bpy.data.objects.remove(envelope, do_unlink=True)
    bpy.data.objects.remove(deep_envelope, do_unlink=True)
    if baseline_deep_conflicts:
        raise ValueError(
            f"Accepted V3 {side} deep-body path regressed: {baseline_deep_conflicts}"
        )
    if actual_conflicts:
        raise ValueError(f"V10 {side} actual path collides: {actual_conflicts}")
    return {
        "side": side,
        "sample_count": len(samples),
        "hardware_present_during_motion": False,
        "accepted_v3_deep_body_margin_mm": deep_margin,
        "accepted_v3_deep_body_path_clear": True,
        "maximum_deep_body_margin_triangle_intersection_pairs": maximum_deep,
        "moving_flange_margin_mm": flange_margin,
        "actual_conflicts": actual_conflicts,
        "moving_flange_margin_conflicts": flange_margin_conflicts,
        "maximum_actual_triangle_intersection_pairs": maximum_actual,
        "maximum_moving_flange_margin_triangle_intersection_pairs": (
            maximum_flange_margin
        ),
        "all_actual_geometry_path_clear": True,
        "conservative_flange_margin_path_clear": not flange_margin_conflicts,
    }

def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    v3_config_path = repo_path(config["v3_config"])
    v3_config = json.loads(v3_config_path.read_text(encoding="utf-8"))
    source_gate6 = repo_path(v3_config["source_gate6_blend"])
    source_gate8 = repo_path(v3_config["source_gate8_blend"])
    interface = json.loads(
        repo_path(config["shared_interface_path"]).read_text(encoding="utf-8")
    )
    if interface["interface_revision"] != config["required_interface_revision"]:
        raise ValueError("Shared shell/aluminum interface revision changed")
    output_dir.mkdir(parents=True, exist_ok=True)

    source_payloads, path_frames, redundant_faces = (
        ear_v3.generate_source_payloads(v3_config, source_gate6)
    )
    boundaries = {
        side: extract_boundary(v3_config, side)
        for side in ("right", "left")
    }
    bpy.ops.wm.open_mainfile(filepath=str(source_gate8))
    source_mesh_names = sorted(
        obj.name for obj in bpy.data.objects if obj.type == "MESH"
    )
    protected_before = {
        name: rear_v5.mesh_fingerprint(bpy.data.objects[name])
        for name in source_mesh_names
    }
    structural_targets = [
        c002_v2.require_object(name) for name in gate2.SECTION_ORDER
    ]
    upper_heads = {
        side: c002_v2.require_object(f"{side}_upper_head")
        for side in ("right", "left")
    }
    ears = {
        side: c002_v2.require_object(f"{side}_ear")
        for side in ("right", "left")
    }

    right_deep = ear_v2.deserialize_mesh(
        "EAR10_VALIDATION__right_deep_fit_body", source_payloads["deep"]
    )
    bpy.context.scene.collection.objects.link(right_deep)
    right_body = ear_v2.deserialize_mesh(
        "EAR10_ACCEPTED_V3_BODY__right", source_payloads["full"]
    )
    bpy.context.scene.collection.objects.link(right_body)
    ear_clearance = float(
        v3_config["fit_clearance"]["exact_ear_local_clearance_mm"]
    )
    ear_v3.apply_exact_ear_clearance(right_deep, ears["right"], ear_clearance)
    ear_v3.apply_exact_ear_clearance(right_body, ears["right"], ear_clearance)
    left_deep = ear_v2.deserialize_mesh(
        "EAR10_VALIDATION__left_deep_fit_body",
        ear_v3.mirror_payload(ear_v2.serialize_mesh(right_deep)),
    )
    bpy.context.scene.collection.objects.link(left_deep)
    left_body = ear_v2.deserialize_mesh(
        "EAR10_ACCEPTED_V3_BODY__left",
        ear_v3.mirror_payload(ear_v2.serialize_mesh(right_body)),
    )
    bpy.context.scene.collection.objects.link(left_body)
    bodies = {"right": right_body, "left": left_body}
    deep_bodies = {"right": right_deep, "left": left_deep}

    display = config["display"]
    materials = {
        "body": gate5.material(
            "EAR10_ACCEPTED_V3_BODY__yellow",
            c002_v2.hex_color(display["accepted_fit_body_color"]),
        ),
        "orange": gate5.material(
            "EAR10_INSERT_FLANGE__orange",
            c002_v2.hex_color(display["insert_flange_color"]),
        ),
        "green": gate5.material(
            "EAR10_HEAD_FLANGE__green",
            c002_v2.hex_color(display["head_flange_color"]),
        ),
        "head_owner_proof": gate5.material(
            "EAR10_REVIEW_ONLY__head_owner_gray",
            c002_v2.hex_color(display["upper_head_color"]),
        ),
    }
    for body in bodies.values():
        body.data.materials.clear()
        body.data.materials.append(materials["body"])
        body.color = materials["body"].diffuse_color
        body.show_in_front = True

    values = config["placement_pair"]
    location_specs = config["locations"]
    if len(location_specs) != 2:
        raise ValueError("V10 requires exactly two connector locations per side")
    pairs: list[dict[str, Any]] = []
    pairs_by_side: dict[str, list[dict[str, Any]]] = {
        "right": [],
        "left": [],
    }
    for spec in location_specs:
        right_record = boundaries["right"][
            int(spec["right_boundary_edge_index"])
        ]
        if right_record["owner"] != "right_upper_head":
            raise ValueError(
                f"V10 right {spec['id']} owner changed: {right_record['owner']}"
            )
        right_frame = shared_pair_frame(
            right_record, float(spec["fraction_from_first_vertex"])
        )
        right_pair = create_pair(
            right_frame,
            values,
            bodies["right"],
            upper_heads["right"],
            materials,
            "right",
            spec["id"],
        )
        right_pair["role"] = spec["role"]
        pairs.append(right_pair)
        pairs_by_side["right"].append(right_pair)

        left_record = boundaries["left"][
            int(spec["left_boundary_edge_index"])
        ]
        if left_record["owner"] != "left_upper_head":
            raise ValueError(
                f"V10 left {spec['id']} owner changed: {left_record['owner']}"
            )
        expected_left_frame = shared_pair_frame(
            left_record, float(spec["fraction_from_first_vertex"])
        )
        mirrored_anchor_error = (
            mirror_vector(right_frame["anchor"])
            - expected_left_frame["anchor"]
        ).length
        if mirrored_anchor_error > 0.01:
            raise ValueError(
                f"V10 left {spec['id']} seam anchor is not mirrored: "
                f"{mirrored_anchor_error:.4f} mm"
            )
        left_pair = mirror_pair_from_right(
            right_pair,
            bodies["left"],
            upper_heads["left"],
            materials,
        )
        left_pair["role"] = spec["role"]
        pairs.append(left_pair)
        pairs_by_side["left"].append(left_pair)

    if len(pairs) != 4:
        raise ValueError("V10 must contain four connector sets total")
    separations = {}
    minimum_separation = float(values["minimum_same_side_location_separation_mm"])
    for side, side_pairs in pairs_by_side.items():
        separation = (
            side_pairs[0]["pair_center"] - side_pairs[1]["pair_center"]
        ).length
        separations[side] = round(separation, 4)
        if separation < minimum_separation:
            raise ValueError(
                f"V10 {side} connector sets are clustered: {separation:.3f} mm"
            )
    mirror_errors = {}
    for spec in location_specs:
        right_pair = next(
            pair
            for pair in pairs_by_side["right"]
            if pair["location_id"] == spec["id"]
        )
        left_pair = next(
            pair
            for pair in pairs_by_side["left"]
            if pair["location_id"] == spec["id"]
        )
        right_center = right_pair["pair_center"]
        mirrored = Vector((-right_center.x, right_center.y, right_center.z))
        error = (mirrored - left_pair["pair_center"]).length
        mirror_errors[spec["id"]] = round(error, 6)
        if error > 0.01:
            raise ValueError(
                f"V10 location {spec['id']} is not mirrored: {error:.4f} mm"
            )

    bore_reports = [validate_open_aligned_bore(pair) for pair in pairs]
    if len(bore_reports) != 4 or not all(
        report["open_and_aligned"] for report in bore_reports
    ):
        raise ValueError("V10 requires four open, aligned M3 fastener paths")

    proofs: dict[str, bpy.types.Object] = {}
    proof_parts_by_pair: dict[str, dict[str, bpy.types.Object]] = {}
    proof_volumes: dict[str, float] = {}
    proof_partition_checks: dict[str, dict[str, float | bool]] = {}
    minimum_overlap = float(values["minimum_owner_overlap_volume_mm3"])
    owner_overlap_volumes: dict[str, float] = {}
    for pair in pairs:
        side = pair["side"]
        location_id = pair["location_id"]
        key = f"{side}_{location_id}"
        prefix = f"EAR10_REVIEW_ONLY__{key}"
        parts = {
            "orange_exposed": create_boolean_proof_part(
                pair["orange"],
                bodies[side],
                f"{prefix}_orange_exposed_outside_yellow_owner",
                "DIFFERENCE",
                materials["orange"],
            ),
            "orange_owner_overlap": create_boolean_proof_part(
                pair["orange"],
                bodies[side],
                f"{prefix}_orange_inside_yellow_owner",
                "INTERSECT",
                materials["body"],
            ),
            "green_exposed": create_boolean_proof_part(
                pair["green"],
                upper_heads[side],
                f"{prefix}_green_exposed_outside_gray_owner",
                "DIFFERENCE",
                materials["green"],
            ),
            "green_owner_overlap": create_boolean_proof_part(
                pair["green"],
                upper_heads[side],
                f"{prefix}_green_inside_gray_owner",
                "INTERSECT",
                materials["head_owner_proof"],
            ),
        }
        proof_parts_by_pair[key] = parts
        for part_name, obj in parts.items():
            proof_key = f"{key}_{part_name}"
            proofs[proof_key] = obj
            proof_volumes[proof_key] = round(gate5.mesh_volume(obj), 4)
        for role in ("orange", "green"):
            tab_volume = gate5.mesh_volume(pair[role])
            exposed_volume = gate5.mesh_volume(parts[f"{role}_exposed"])
            overlap_volume = gate5.mesh_volume(
                parts[f"{role}_owner_overlap"]
            )
            partition_error = abs(
                tab_volume - exposed_volume - overlap_volume
            )
            partition_tolerance = max(0.5, tab_volume * 0.025)
            if overlap_volume > tab_volume + 0.01:
                raise ValueError(
                    f"V10 impossible {key} {role} owner overlap: "
                    f"tab={tab_volume:.3f}, overlap={overlap_volume:.3f}"
                )
            proof_partition_checks[f"{key}_{role}"] = {
                "tab_volume_mm3": round(tab_volume, 4),
                "exposed_volume_mm3": round(exposed_volume, 4),
                "owner_overlap_volume_mm3": round(overlap_volume, 4),
                "partition_error_mm3": round(partition_error, 4),
                "partition_tolerance_mm3": round(partition_tolerance, 4),
                "partition_within_tolerance": (
                    partition_error <= partition_tolerance
                ),
                "owner_overlap_not_greater_than_tab": True,
            }
        for owner_key in ("orange_owner_overlap", "green_owner_overlap"):
            volume = gate5.mesh_volume(parts[owner_key])
            volume_key = f"{key}_{owner_key}"
            owner_overlap_volumes[volume_key] = round(volume, 4)
            if volume < minimum_overlap:
                raise ValueError(
                    f"V10 weak owner root {volume_key}: {volume:.3f} mm3"
                )

    owner_overlap_mirror_checks: dict[str, dict[str, float | bool]] = {}
    for location_id in ("A", "B"):
        for role in ("orange", "green"):
            suffix = f"{role}_owner_overlap"
            right_volume = owner_overlap_volumes[
                f"right_{location_id}_{suffix}"
            ]
            left_volume = owner_overlap_volumes[
                f"left_{location_id}_{suffix}"
            ]
            error = abs(right_volume - left_volume)
            tolerance = max(2.0, 0.15 * max(right_volume, left_volume))
            if error > tolerance:
                raise ValueError(
                    f"V10 asymmetric {location_id} {role} owner overlap: "
                    f"right={right_volume:.3f}, left={left_volume:.3f}, "
                    f"error={error:.3f}, tolerance={tolerance:.3f}"
                )
            owner_overlap_mirror_checks[f"{location_id}_{role}"] = {
                "right_volume_mm3": right_volume,
                "left_volume_mm3": left_volume,
                "absolute_error_mm3": round(error, 4),
                "tolerance_mm3": round(tolerance, 4),
                "within_tolerance": True,
            }

    moving_composites = {}
    moving_topology = {}
    seated_hits = {}
    green_unintended_hits = {}
    path_reports = {}
    for side in ("right", "left"):
        orange_tabs = [pair["orange"] for pair in pairs_by_side[side]]
        green_tabs = [pair["green"] for pair in pairs_by_side[side]]
        composite, topology = fuse_owner_with_tabs(
            bodies[side],
            orange_tabs,
            f"EAR10_VALIDATION__{side}_body_plus_two_orange_tabs",
        )
        moving_composites[side] = composite
        moving_topology[side] = topology
        targets_without_own_ear = [
            target
            for target in structural_targets
            if target.name != f"{side}_ear"
        ]
        per_orange_hits = {}
        for pair in pairs_by_side[side]:
            hits = ear_v3.collision_hits(
                pair["orange"], targets_without_own_ear
            )
            if hits:
                per_orange_hits[pair["location_id"]] = hits
        side_seated_hits = ear_v3.collision_hits(
            composite, targets_without_own_ear
        )
        if side_seated_hits:
            raise ValueError(
                f"V10 {side} moving composite hits shells: {side_seated_hits}; "
                f"per-orange={per_orange_hits}"
            )
        seated_hits[side] = side_seated_hits
        per_green_hits = {}
        for pair in pairs_by_side[side]:
            hits = ear_v3.collision_hits(
                pair["green"],
                [
                    target
                    for target in structural_targets
                    if target.name != f"{side}_upper_head"
                ],
            )
            if hits:
                per_green_hits[pair["location_id"]] = hits
        if per_green_hits:
            raise ValueError(
                f"V10 {side} green tabs hit unintended shells: {per_green_hits}"
            )
        green_unintended_hits[side] = per_green_hits
        path_reports[side] = validate_side_path(
            side,
            composite,
            orange_tabs,
            deep_bodies[side],
            green_tabs,
            path_frames[side],
            v3_config,
            values,
            structural_targets,
        )

    collection_names = (
        "EAR10_EXACT_STRUCTURAL_HEAD_MUTED__UNCHANGED",
        "EAR10_EXACT_EARS_CYAN__UNCHANGED",
        "EAR10_ACCEPTED_V3_TRANSLUCENT_BODIES_YELLOW__UNCHANGED",
        "EAR10_RIGHT_INSERT_FLANGES_ORANGE__TWO_SETS",
        "EAR10_LEFT_INSERT_FLANGES_ORANGE__TWO_SETS",
        "EAR10_RIGHT_HEAD_FLANGES_GREEN__TWO_SETS_UNINTEGRATED",
        "EAR10_LEFT_HEAD_FLANGES_GREEN__TWO_SETS_UNINTEGRATED",
        "EAR10_REVIEW_ONLY__OWNER_ROOT_BOOLEAN_CUTAWAY_PROOFS__HIDDEN",
        "EAR10_OTHER_SOURCE_GEOMETRY__HIDDEN",
    )
    collections: dict[str, bpy.types.Collection] = {}
    for name in collection_names:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        collections[name] = collection

    context_objects: set[bpy.types.Object] = set()
    for target in structural_targets:
        target.color = c002_v2.hex_color(display["lower_rear_context_color"])
        target.display_type = "WIRE"
        target.show_wire = True
        target.hide_viewport = False
        target.hide_render = False
        target.hide_set(False)
        c002_v2.link_reference(
            target, collections["EAR10_EXACT_STRUCTURAL_HEAD_MUTED__UNCHANGED"]
        )
        context_objects.add(target)
    for ear in ears.values():
        ear.color = c002_v2.hex_color(display["ear_color"])
        ear.display_type = "WIRE"
        ear.show_wire = True
        ear.hide_viewport = False
        ear.hide_render = False
        ear.hide_set(False)
        c002_v2.link_reference(
            ear, collections["EAR10_EXACT_EARS_CYAN__UNCHANGED"]
        )
    for body in bodies.values():
        c002_v2.link_reference(
            body,
            collections[
                "EAR10_ACCEPTED_V3_TRANSLUCENT_BODIES_YELLOW__UNCHANGED"
            ],
        )
    for pair in pairs:
        side_label = pair["side"].upper()
        c002_v2.link_reference(
            pair["orange"],
            collections[f"EAR10_{side_label}_INSERT_FLANGES_ORANGE__TWO_SETS"],
        )
        c002_v2.link_reference(
            pair["green"],
            collections[
                f"EAR10_{side_label}_HEAD_FLANGES_GREEN__TWO_SETS_UNINTEGRATED"
            ],
        )
    for proof in proofs.values():
        c002_v2.link_reference(
            proof,
            collections[
                "EAR10_REVIEW_ONLY__OWNER_ROOT_BOOLEAN_CUTAWAY_PROOFS__HIDDEN"
            ],
        )

    all_tabs = {
        obj
        for pair in pairs
        for obj in (pair["orange"], pair["green"])
    }
    default_visible = {
        *context_objects,
        *ears.values(),
        *bodies.values(),
        *all_tabs,
    }
    exterior_baseline_visible = default_visible - all_tabs
    side_pair_visible = {
        side: {
            obj
            for pair in pairs_by_side[side]
            for obj in (pair["orange"], pair["green"])
        }
        for side in ("right", "left")
    }
    side_body_visible = {
        side: {
            bodies[side],
            *(pair["orange"] for pair in pairs_by_side[side]),
        }
        for side in ("right", "left")
    }
    marked_relocation_visible = {
        side: {
            bodies[side],
            ears[side],
            *(
                obj
                for pair in pairs_by_side[side]
                for obj in (pair["orange"], pair["green"])
            ),
        }
        for side in ("right", "left")
    }

    source_set = {bpy.data.objects[name] for name in source_mesh_names}
    for obj in source_set:
        if obj in default_visible:
            continue
        c002_v2.link_reference(
            obj, collections["EAR10_OTHER_SOURCE_GEOMETRY__HIDDEN"]
        )
        obj.hide_viewport = True
        obj.hide_render = True
        obj.hide_set(True)

    for composite in moving_composites.values():
        bpy.data.objects.remove(composite, do_unlink=True)
    for deep_body in deep_bodies.values():
        bpy.data.objects.remove(deep_body, do_unlink=True)

    camera = configure_scene(output_dir, int(display["render_resolution_px"]))
    pair_targets = {
        side: sum(
            (pair["pair_center"] for pair in pairs_by_side[side]), Vector()
        )
        / len(pairs_by_side[side])
        for side in ("right", "left")
    }
    average_interiors = {
        side: sum(
            (pair["frame"]["interior"] for pair in pairs_by_side[side]),
            Vector(),
        ).normalized()
        for side in ("right", "left")
    }
    side_cameras = {
        side: pair_targets[side]
        + (average_interiors[side] + Vector((0.0, 0.0, 0.18))).normalized()
        * 175.0
        for side in ("right", "left")
    }
    front_camera = Vector((0.0, 520.0, 240.0))
    front_target = Vector((0.0, 150.0, 170.0))
    right_camera = Vector((330.0, 130.0, 250.0))
    left_camera = Vector((-330.0, 130.0, 250.0))
    top_camera = Vector((0.0, 150.0, 600.0))
    renders = []
    renders.append(
        render_view(
            camera,
            output_dir,
            "full-head-context",
            front_camera,
            front_target,
            default_visible,
        )
    )
    marked_targets = {
        "right": Vector((90.0, 170.0, 215.0)),
        "left": Vector((-90.0, 170.0, 215.0)),
    }
    marked_cameras = {
        "right": Vector((310.0, 390.0, 285.0)),
        "left": Vector((-310.0, 390.0, 285.0)),
    }
    for side in ("right", "left"):
        renders.append(
            render_view(
                camera,
                output_dir,
                f"{side}-user-marked-relocation-context",
                marked_cameras[side],
                marked_targets[side],
                marked_relocation_visible[side],
            )
        )
    for side in ("right", "left"):
        renders.append(
            render_view(
                camera,
                output_dir,
                f"{side}-translucent-piece-two-orange-roots",
                side_cameras[side],
                pair_targets[side],
                side_body_visible[side],
            )
        )
        renders.append(
            render_view(
                camera,
                output_dir,
                f"{side}-two-connector-sets-isolated",
                side_cameras[side],
                pair_targets[side],
                side_pair_visible[side],
            )
        )
    for pair in pairs:
        key = f"{pair['side']}_{pair['location_id']}"
        frame = pair["frame"]
        target = pair["pair_center"]
        hole_camera_location = pair["fastener_center"] + (
            frame["across"]
            + frame["tangent"] * 0.45
            + frame["interior"] * 0.10
        ).normalized() * 48.0
        renders.append(
            render_view(
                camera,
                output_dir,
                f"{pair['side']}-{pair['location_id'].lower()}-m3-hole-alignment",
                hole_camera_location,
                pair["fastener_center"],
                {pair["orange"], pair["green"]},
            )
        )
        camera_location = target + (
            frame["across"]
            + frame["tangent"] * 0.12
            + frame["interior"] * 0.12
        ).normalized() * 65.0
        proof_parts = proof_parts_by_pair[key]
        for role in ("orange", "green"):
            visible = {
                proof_parts[f"{role}_exposed"],
                proof_parts[f"{role}_owner_overlap"],
            }
            renders.append(
                render_view(
                    camera,
                    output_dir,
                    f"{pair['side']}-{pair['location_id'].lower()}-{role}-owner-root",
                    camera_location,
                    target,
                    visible,
                )
            )

    silhouette_shading = bpy.context.scene.display.shading
    silhouette_shading.light = "FLAT"
    silhouette_shading.color_type = "SINGLE"
    silhouette_shading.single_color = (0.82, 0.82, 0.82)
    silhouette_shading.show_shadows = False
    silhouette_shading.show_cavity = False
    silhouette_views = {
        "front": (front_camera, front_target),
        "right": (right_camera, pair_targets["right"]),
        "left": (left_camera, pair_targets["left"]),
        "top": (top_camera, front_target),
    }
    silhouette_render_pairs = {}
    for view_name, (location, target) in silhouette_views.items():
        baseline = render_view(
            camera,
            output_dir,
            f"exterior-{view_name}-baseline",
            location,
            target,
            exterior_baseline_visible,
        )
        candidate = render_view(
            camera,
            output_dir,
            f"exterior-{view_name}-candidate",
            location,
            target,
            default_visible,
        )
        renders.extend((baseline, candidate))
        silhouette_render_pairs[view_name] = (baseline, candidate)

    silhouette_comparison = {}
    for view_name, (baseline_render, candidate_render) in (
        silhouette_render_pairs.items()
    ):
        comparison = compare_render_pixels(
            repo_path(baseline_render), repo_path(candidate_render)
        )
        comparison["baseline_render"] = baseline_render
        comparison["candidate_render"] = candidate_render
        silhouette_comparison[view_name] = comparison
        if not comparison["identical"]:
            raise ValueError(
                f"V10 changes the {view_name} exterior silhouette: {comparison}"
            )

    silhouette_shading.light = "STUDIO"
    silhouette_shading.color_type = "OBJECT"
    silhouette_shading.show_shadows = True
    silhouette_shading.show_cavity = True
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in default_visible
            obj.hide_render = obj not in default_visible
            obj.hide_set(obj not in default_visible)
    camera.location = front_camera
    point_at(camera, front_target)

    protected_after = {
        name: rear_v5.mesh_fingerprint(bpy.data.objects[name])
        for name in source_mesh_names
    }
    if protected_before != protected_after:
        raise ValueError("V10 review changed exact Gate 8 source geometry")

    frame_checks = {}
    for pair in pairs:
        frame = pair["frame"]
        key = f"{pair['side']}_{pair['location_id']}"
        frame_checks[key] = {
            "tangent_dot_interior": round(
                frame["tangent"].dot(frame["interior"]), 8
            ),
            "tangent_dot_across": round(
                frame["tangent"].dot(frame["across"]), 8
            ),
            "interior_dot_across": round(
                frame["interior"].dot(frame["across"]), 8
            ),
            "axis_lengths": {
                name: round(frame[name].length, 8)
                for name in ("tangent", "interior", "across")
            },
        }

    scene = bpy.context.scene
    scene["default_review_view"] = "full_head_context_four_connector_sets"
    scene["review_status"] = config["status"]
    scene["connector_sets_per_translucent_piece"] = 2
    scene["connector_set_count"] = 4
    scene["orange_flange_count"] = 4
    scene["green_flange_count"] = 4
    scene["rectangular_tab_count"] = 8
    scene["placement_only"] = False
    scene["placement_and_hole_review"] = True
    scene["aligned_m3_fastener_path_count"] = 4
    scene["drilled_tab_hole_count"] = 8
    scene["specified_m3_fastener_count"] = 4
    scene["modeled_hardware_count"] = 0
    scene["separate_root_geometry_count"] = 0
    scene["review_only_boolean_cutaway_proof_count"] = len(proofs)
    scene["trapezoid_or_broad_base_count"] = 0
    scene["exterior_silhouette_views_identical"] = True
    scene["compound_bridge_count"] = 0
    scene["loose_clamp_count"] = 0
    scene["accepted_v3_fit_body_changed"] = False
    scene["exact_gate8_source_geometry_changed"] = False
    scene["not_print_released"] = True
    blend_path = (
        output_dir
        / "ear-root-marked-relocation-m3-through-bolt-review-v10.blend"
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    pair_reports = []
    for pair in pairs:
        pair_reports.append(
            {
                "side": pair["side"],
                "location_id": pair["location_id"],
                "role": pair["role"],
                "center": [round(value, 5) for value in pair["pair_center"]],
                "dimensions_mm": pair["dimensions_mm"],
                "shared_offset_mm": pair["shared_offset_mm"],
                "moving_tab_interior_relief_mm": pair[
                    "moving_tab_interior_relief_mm"
                ],
                "m3_clearance_diameter_mm": pair[
                    "m3_clearance_diameter_mm"
                ],
                "fastener_center_mm": [
                    round(value, 5) for value in pair["fastener_center"]
                ],
                "fastener_axis": [
                    round(value, 6)
                    for value in pair["fastener_axis"].normalized()
                ],
                "minimum_hole_edge_material_mm": round(
                    pair["minimum_hole_edge_material_mm"], 4
                ),
                "measured_gap_mm": round(pair["measured_gap_mm"], 4),
                "orange_owner_intersection_pairs": pair[
                    "orange_owner_intersection_pairs"
                ],
                "green_owner_intersection_pairs": pair[
                    "green_owner_intersection_pairs"
                ],
            }
        )
    report = {
        "status": config["status"],
        "feedback_scope": ["F-10", "F-11", "F-12"],
        "config": str(config_path.relative_to(REPO_ROOT)),
        "v3_config": str(v3_config_path.relative_to(REPO_ROOT)),
        "physical_fit_feedback": config["physical_fit_feedback"],
        "interface_revision": interface["interface_revision"],
        "accepted_v3_fit_body_changed": False,
        "exact_gate8_source_mesh_count": len(source_mesh_names),
        "exact_gate8_source_meshes_unchanged": True,
        "placement_pair": values,
        "connector_sets_per_translucent_piece": 2,
        "translucent_piece_count": 2,
        "connector_set_count": 4,
        "right_connector_set_count": 2,
        "left_connector_set_count": 2,
        "orange_flange_count": 4,
        "green_flange_count": 4,
        "rectangular_tab_count": 8,
        "separate_root_geometry_count": 0,
        "fastener": config["fastener"],
        "aligned_m3_fastener_path_count": 4,
        "drilled_tab_hole_count": 8,
        "specified_m3_fastener_count": 4,
        "modeled_hardware_count": 0,
        "bore_reports": bore_reports,
        "all_m3_bores_open_and_aligned": all(
            value["open_and_aligned"] for value in bore_reports
        ),
        "minimum_actual_hole_edge_material_mm": min(
            value["minimum_hole_edge_material_mm"]
            for value in bore_reports
        ),
        "compound_bridge_count": 0,
        "convex_hull_transition_count": 0,
        "loose_clamp_count": 0,
        "trapezoid_or_broad_base_count": 0,
        "pair_reports": pair_reports,
        "same_side_location_separation_mm": separations,
        "minimum_required_same_side_separation_mm": minimum_separation,
        "mirror_center_errors_mm": mirror_errors,
        "shared_frame_checks": frame_checks,
        "minimum_required_owner_overlap_volume_mm3": minimum_overlap,
        "owner_overlap_volumes_mm3": owner_overlap_volumes,
        "minimum_actual_owner_overlap_volume_mm3": min(
            owner_overlap_volumes.values()
        ),
        "review_only_boolean_cutaway_proof_count": len(proofs),
        "review_only_boolean_cutaway_proof_volumes_mm3": proof_volumes,
        "owner_proof_partition_diagnostics": proof_partition_checks,
        "all_owner_overlap_bounds_valid": True,
        "owner_overlap_mirror_checks": owner_overlap_mirror_checks,
        "all_owner_overlap_mirror_checks_valid": True,
        "review_only_proofs_change_connector_geometry": False,
        "exterior_silhouette_comparison": silhouette_comparison,
        "moving_composite_topology": moving_topology,
        "seated_moving_composite_hits": seated_hits,
        "green_unintended_shell_hits": green_unintended_hits,
        "path_validation": path_reports,
        "all_actual_geometry_paths_clear": all(
            value["all_actual_geometry_path_clear"]
            for value in path_reports.values()
        ),
        "all_conservative_flange_margin_paths_clear": all(
            value["conservative_flange_margin_path_clear"]
            for value in path_reports.values()
        ),
        "redundant_quad_face_proof_preserved": redundant_faces,
        "review_sequence": [
            "Review the retained set and the crossed-to-checked relocated set on each yellow translucent piece.",
            "Review all eight drilled rectangular tabs and the owner-root cutaways.",
            "Confirm every orange/green pair has one common 3.4 mm M3 through-bolt path.",
        ],
        "green_source_shell_integration_validated": False,
        "no_stl_or_gcode_exported": True,
        "not_print_released": True,
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": renders,
        },
        "review_holds": config["review_holds"],
    }
    report_path = (
        output_dir
        / "ear-root-marked-relocation-m3-through-bolt-review-v10-validation.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
