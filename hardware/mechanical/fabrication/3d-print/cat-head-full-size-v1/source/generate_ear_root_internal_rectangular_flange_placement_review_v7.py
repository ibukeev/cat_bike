#!/usr/bin/env python3
"""Generate one right-side internal rectangular flange placement review."""

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
import generate_gate7_glow_panel_inserts as gate7  # noqa: E402
import generate_gate8_full_size_iteration as gate8  # noqa: E402
import generate_rear_cassette_lossless_repartition_review_v5 as rear_v5  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/ear-root-internal-rectangular-flange-placement-review-v7.json"
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
    scene.name = "Ear_Root_Internal_Rectangular_Flange_Placement_Review_V7"
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
    camera_data = bpy.data.cameras.new("EAR7_REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("EAR7_REVIEW_ONLY__Camera", camera_data)
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
        / f"ear-root-internal-rectangular-placement-{name}.png"
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


def extract_right_boundary(v3_config: dict[str, Any]) -> list[dict[str, Any]]:
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
        group = groups[v3_config["sides"]["right"]["candidate_group"]]
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
    right_body: bpy.types.Object,
    right_upper: bpy.types.Object,
    materials: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    anchor = frame["anchor"]
    tangent = frame["tangent"]
    interior = frame["interior"]
    across = frame["across"]
    length = float(values["tab_length_mm"])
    depth = float(values["tab_interior_depth_mm"])
    thickness = float(values["tab_thickness_mm"])
    gap = float(values["mating_gap_mm"])
    root_inset = float(values["owner_root_inset_mm"])
    if root_inset < 0.0 or root_inset >= depth:
        raise ValueError("Rectangular root inset must be nonnegative and inside tab depth")
    dimensions = (length, depth, thickness)
    offset = gap / 2.0 + thickness / 2.0
    interior_center = interior * (depth / 2.0 + root_inset)
    orange_center = anchor + across * offset + interior_center
    green_center = anchor - across * offset + interior_center
    axes = (tangent, interior, across)

    orange = gate5.box(
        "EAR7_RIGHT_INSERT_FLANGE__orange",
        orange_center,
        axes,
        dimensions,
        materials["orange"],
    )
    green = gate5.box(
        "EAR7_RIGHT_HEAD_FLANGE__green",
        green_center,
        axes,
        dimensions,
        materials["green"],
    )
    gate5.require_manifold(orange, "V7 orange rectangular placement tab")
    gate5.require_manifold(green, "V7 green rectangular placement tab")
    orange.color = orange.data.materials[0].diffuse_color
    green.color = green.data.materials[0].diffuse_color

    if c002_v2.surfaces_overlap(orange, green):
        raise ValueError("V7 rectangular placement tabs overlap")
    measured_gap = c002_v2.surface_distance(orange, green)
    if abs(measured_gap - gap) > 0.01:
        raise ValueError(
            f"V7 placement gap changed: expected {gap}, got {measured_gap}"
        )
    orange_owner_hits = ear_v3.world_triangle_intersection_count(
        orange, right_body
    )
    green_owner_hits = ear_v3.world_triangle_intersection_count(
        green, right_upper
    )
    if orange_owner_hits == 0:
        raise ValueError("Orange rectangular tab does not root into yellow owner")
    if green_owner_hits == 0:
        raise ValueError("Green rectangular tab does not root into gray owner")

    return {
        "orange": orange,
        "green": green,
        "hardware": [],
        "access": [],
        "pair_center": anchor + interior * (depth / 2.0 + root_inset),
        "frame": frame,
        "dimensions_mm": [length, depth, thickness],
        "root_inset_mm": root_inset,
        "measured_gap_mm": measured_gap,
        "orange_owner_overlap": True,
        "green_owner_overlap": True,
        "orange_owner_intersection_pairs": orange_owner_hits,
        "green_owner_intersection_pairs": green_owner_hits,
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
    gate5.apply_boolean(result, tool, operation, solver="EXACT")
    if not result.data.polygons or gate5.mesh_volume(result) <= 0.001:
        raise ValueError(f"V7 review proof is empty: {name}")
    gate5.require_manifold(result, f"V7 review-only owner cutaway {name}")
    result.data.materials.clear()
    result.data.materials.append(material)
    result.color = material.diffuse_color
    result["review_only"] = True
    result["derived_from_tab"] = tab.name
    result["derived_from_owner"] = owner.name
    result["boolean_operation"] = operation
    return result


def validate_path(
    composite: bpy.types.Object,
    orange: bpy.types.Object,
    deep_body: bpy.types.Object,
    green: bpy.types.Object,
    frame: dict[str, Any],
    v3_config: dict[str, Any],
    values: dict[str, Any],
    structural_targets: list[bpy.types.Object],
) -> dict[str, Any]:
    targets = [
        target
        for target in structural_targets
        if target.name != "right_ear"
    ]
    samples = ear_v3.path_samples(frame, v3_config["insertion_path"])
    deep_margin = float(
        v3_config["fit_clearance"]["deep_body_path_margin_mm"]
    )
    flange_margin = float(values["moving_flange_path_margin_mm"])
    deep_envelope = gate8.expanded_insert_cutter(
        deep_body, deep_margin, "EAR7_VALIDATION__deep_body_margin"
    )
    flange_envelope = gate8.expanded_insert_cutter(
        orange, flange_margin, "EAR7_VALIDATION__orange_flange_margin"
    )
    actual_conflicts = []
    baseline_deep_conflicts = []
    flange_margin_conflicts = []
    maximum_actual = 0
    maximum_deep = 0
    maximum_flange_margin = 0
    for sample in samples:
        for obj in (composite, deep_envelope, flange_envelope):
            obj.matrix_world = sample["matrix"]
        actual_hits = ear_v3.collision_hits(
            composite, [*targets, green]
        )
        deep_hits = ear_v3.collision_hits(deep_envelope, targets)
        flange_hits = ear_v3.collision_hits(
            flange_envelope, [*targets, green]
        )
        maximum_actual = max(maximum_actual, sum(actual_hits.values()))
        maximum_deep = max(maximum_deep, sum(deep_hits.values()))
        maximum_flange_margin = max(
            maximum_flange_margin, sum(flange_hits.values())
        )
        metadata = {
            key: value for key, value in sample.items() if key != "matrix"
        }
        if actual_hits:
            actual_conflicts.append({**metadata, "hits": actual_hits})
        if deep_hits:
            baseline_deep_conflicts.append({**metadata, "hits": deep_hits})
        if flange_hits:
            flange_margin_conflicts.append(
                {**metadata, "hits": flange_hits}
            )
    for obj in (composite, deep_envelope, flange_envelope):
        obj.matrix_world = Matrix.Identity(4)
    bpy.data.objects.remove(deep_envelope, do_unlink=True)
    bpy.data.objects.remove(flange_envelope, do_unlink=True)
    if baseline_deep_conflicts:
        raise ValueError(
            f"Accepted V3 deep-body path regressed: {baseline_deep_conflicts}"
        )
    return {
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
        "placement_pair_path_clear": not (
            actual_conflicts or flange_margin_conflicts
        ),
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
    right_boundary = extract_right_boundary(v3_config)
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
    right_upper = c002_v2.require_object("right_upper_head")

    right_deep = ear_v2.deserialize_mesh(
        "EAR7_VALIDATION__right_deep_fit_body", source_payloads["deep"]
    )
    bpy.context.scene.collection.objects.link(right_deep)
    right_body = ear_v2.deserialize_mesh(
        "EAR7_ACCEPTED_V3_BODY__right", source_payloads["full"]
    )
    bpy.context.scene.collection.objects.link(right_body)
    ear_clearance = float(
        v3_config["fit_clearance"]["exact_ear_local_clearance_mm"]
    )
    ear_v3.apply_exact_ear_clearance(
        right_deep, bpy.data.objects["right_ear"], ear_clearance
    )
    ear_v3.apply_exact_ear_clearance(
        right_body, bpy.data.objects["right_ear"], ear_clearance
    )
    left_body = ear_v2.deserialize_mesh(
        "EAR7_ACCEPTED_V3_BODY__left",
        ear_v3.mirror_payload(ear_v2.serialize_mesh(right_body)),
    )
    bpy.context.scene.collection.objects.link(left_body)
    display = config["display"]
    materials = {
        "body": gate5.material(
            "EAR7_ACCEPTED_V3_BODY__yellow",
            c002_v2.hex_color(display["accepted_fit_body_color"]),
        ),
        "orange": gate5.material(
            "EAR7_RIGHT_INSERT_FLANGE__orange",
            c002_v2.hex_color(display["insert_flange_color"]),
        ),
        "green": gate5.material(
            "EAR7_RIGHT_HEAD_FLANGE__green",
            c002_v2.hex_color(display["head_flange_color"]),
        ),
        "head_owner_proof": gate5.material(
            "EAR7_REVIEW_ONLY__head_owner_gray",
            c002_v2.hex_color(display["upper_head_color"]),
        ),
    }
    for body in (right_body, left_body):
        body.data.materials.clear()
        body.data.materials.append(materials["body"])
        body.color = materials["body"].diffuse_color
        body.show_in_front = True

    spec = config["prototype"]
    if spec["side"] != "right":
        raise ValueError("V7 is intentionally a right-side-only prototype")
    record = right_boundary[int(spec["right_boundary_edge_index"])]
    if record["owner"] != "right_upper_head":
        raise ValueError("V7 prototype is not rooted on right_upper_head")
    pair_frame = shared_pair_frame(
        record, float(spec["fraction_from_first_vertex"])
    )
    pair = create_pair(
        pair_frame,
        config["placement_pair"],
        right_body,
        right_upper,
        materials,
    )
    proofs = {
        "orange_exposed": create_boolean_proof_part(
            pair["orange"],
            right_body,
            "EAR7_REVIEW_ONLY__orange_exposed_outside_yellow_owner",
            "DIFFERENCE",
            materials["orange"],
        ),
        "orange_owner_overlap": create_boolean_proof_part(
            pair["orange"],
            right_body,
            "EAR7_REVIEW_ONLY__orange_inside_yellow_owner",
            "INTERSECT",
            materials["body"],
        ),
        "green_exposed": create_boolean_proof_part(
            pair["green"],
            right_upper,
            "EAR7_REVIEW_ONLY__green_exposed_outside_gray_owner",
            "DIFFERENCE",
            materials["green"],
        ),
        "green_owner_overlap": create_boolean_proof_part(
            pair["green"],
            right_upper,
            "EAR7_REVIEW_ONLY__green_inside_gray_owner",
            "INTERSECT",
            materials["head_owner_proof"],
        ),
    }
    proof_volumes = {
        name: round(gate5.mesh_volume(obj), 4)
        for name, obj in proofs.items()
    }

    body_overlap_counts = [
        ear_v3.world_triangle_intersection_count(right_body, pair["orange"])
    ]
    if body_overlap_counts[0] == 0:
        raise ValueError("V7 orange flange has no broad body overlap")
    composite = right_body.copy()
    composite.data = right_body.data.copy()
    composite.name = "EAR7_VALIDATION__right_body_plus_orange_flange"
    bpy.context.scene.collection.objects.link(composite)
    union_tool = pair["orange"].copy()
    union_tool.data = pair["orange"].data.copy()
    union_tool.name = f"{composite.name}__union_tool"
    bpy.context.scene.collection.objects.link(union_tool)
    gate5.apply_boolean(
        composite, union_tool, "UNION", solver="MANIFOLD"
    )
    boundary, nonmanifold = gate5.topology_counts(composite)
    composite_topology = {
        "connected_components": len(gate5.components(composite)),
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "faces": len(composite.data.polygons),
        "volume_mm3": round(gate5.mesh_volume(composite), 4),
    }
    if (
        composite_topology["connected_components"] != 1
        or boundary
        or nonmanifold
    ):
        raise ValueError(
            f"V7 moving composite is not manifold: {composite_topology}"
        )
    structural_without_right_ear = [
        target
        for target in structural_targets
        if target.name != "right_ear"
    ]
    seated_hits = ear_v3.collision_hits(
        composite, structural_without_right_ear
    )
    if seated_hits:
        raise ValueError(
            f"V7 moving composite hits structural shells: {seated_hits}"
        )
    green_other_shell_hits = ear_v3.collision_hits(
        pair["green"],
        [
            target
            for target in structural_targets
            if target.name != "right_upper_head"
        ],
    )
    if green_other_shell_hits:
        raise ValueError(
            f"V7 green flange hits unintended shells: {green_other_shell_hits}"
        )
    path_report = validate_path(
        composite,
        pair["orange"],
        right_deep,
        pair["green"],
        path_frames["right"],
        v3_config,
        config["placement_pair"],
        structural_targets,
    )

    collection_names = (
        "EAR7_EXACT_STRUCTURAL_HEAD_MUTED__UNCHANGED",
        "EAR7_EXACT_EARS_CYAN__UNCHANGED",
        "EAR7_ACCEPTED_V3_BODIES_YELLOW__UNCHANGED",
        "EAR7_RIGHT_INSERT_FLANGE_ORANGE__SINGLE_PROTOTYPE",
        "EAR7_RIGHT_HEAD_FLANGE_GREEN__SINGLE_PROTOTYPE_UNINTEGRATED",
        "EAR7_REVIEW_ONLY__OWNER_ROOT_BOOLEAN_CUTAWAY_PROOFS__HIDDEN",
        "EAR7_OTHER_SOURCE_GEOMETRY__HIDDEN",
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
            target, collections["EAR7_EXACT_STRUCTURAL_HEAD_MUTED__UNCHANGED"]
        )
        context_objects.add(target)
    ears = {
        c002_v2.require_object("left_ear"),
        c002_v2.require_object("right_ear"),
    }
    for ear in ears:
        ear.color = c002_v2.hex_color(display["ear_color"])
        ear.display_type = "WIRE"
        ear.show_wire = True
        ear.hide_viewport = False
        ear.hide_render = False
        ear.hide_set(False)
        c002_v2.link_reference(
            ear, collections["EAR7_EXACT_EARS_CYAN__UNCHANGED"]
        )
    for body in (right_body, left_body):
        c002_v2.link_reference(
            body, collections["EAR7_ACCEPTED_V3_BODIES_YELLOW__UNCHANGED"]
        )
    c002_v2.link_reference(
        pair["orange"],
        collections["EAR7_RIGHT_INSERT_FLANGE_ORANGE__SINGLE_PROTOTYPE"],
    )
    c002_v2.link_reference(
        pair["green"],
        collections[
            "EAR7_RIGHT_HEAD_FLANGE_GREEN__SINGLE_PROTOTYPE_UNINTEGRATED"
        ],
    )
    for proof in proofs.values():
        c002_v2.link_reference(
            proof,
            collections[
                "EAR7_REVIEW_ONLY__OWNER_ROOT_BOOLEAN_CUTAWAY_PROOFS__HIDDEN"
            ],
        )
    default_visible = {
        *context_objects,
        *ears,
        right_body,
        left_body,
        pair["orange"],
        pair["green"],
    }
    pair_visible = {
        pair["orange"],
        pair["green"],
    }
    orange_owner_visible = {
        proofs["orange_exposed"],
        proofs["orange_owner_overlap"],
    }
    green_owner_visible = {
        proofs["green_exposed"],
        proofs["green_owner_overlap"],
    }
    exterior_baseline_visible = default_visible - {
        pair["orange"], pair["green"]
    }

    source_set = {bpy.data.objects[name] for name in source_mesh_names}
    for obj in source_set:
        if obj in default_visible:
            continue
        c002_v2.link_reference(
            obj, collections["EAR7_OTHER_SOURCE_GEOMETRY__HIDDEN"]
        )
        obj.hide_viewport = True
        obj.hide_render = True
        obj.hide_set(True)

    bpy.data.objects.remove(composite, do_unlink=True)
    bpy.data.objects.remove(right_deep, do_unlink=True)

    camera = configure_scene(
        output_dir, int(display["render_resolution_px"])
    )
    anchor = pair_frame["anchor"]
    tangent = pair_frame["tangent"]
    interior = pair_frame["interior"]
    across = pair_frame["across"]
    pair_target = pair["pair_center"]
    front_camera = Vector((0.0, 520.0, 240.0))
    front_target = Vector((0.0, 150.0, 170.0))
    right_camera = Vector((285.0, -100.0, 270.0))
    top_camera = Vector((0.0, 150.0, 600.0))
    renders = [
        render_view(
            camera,
            output_dir,
            "full-head-context",
            front_camera,
            front_target,
            default_visible,
        ),
        render_view(
            camera,
            output_dir,
            "right-orange-owner-root",
            pair_target
            + (across + tangent * 0.12 + interior * 0.12).normalized() * 60.0,
            pair_target,
            orange_owner_visible,
        ),
        render_view(
            camera,
            output_dir,
            "right-green-owner-root",
            pair_target
            + (across + tangent * 0.12 + interior * 0.12).normalized() * 60.0,
            pair_target,
            green_owner_visible,
        ),
        render_view(
            camera,
            output_dir,
            "right-pair-isolated",
            pair_target
            + (interior * 0.8 + tangent * 0.55).normalized()
            * 55.0,
            pair_target,
            pair_visible,
        ),
        render_view(
            camera,
            output_dir,
            "exterior-front-baseline",
            front_camera,
            front_target,
            exterior_baseline_visible,
        ),
        render_view(
            camera,
            output_dir,
            "exterior-front-candidate",
            front_camera,
            front_target,
            default_visible,
        ),
        render_view(
            camera,
            output_dir,
            "exterior-right-baseline",
            right_camera,
            anchor,
            exterior_baseline_visible,
        ),
        render_view(
            camera,
            output_dir,
            "exterior-right-candidate",
            right_camera,
            anchor,
            default_visible,
        ),
        render_view(
            camera,
            output_dir,
            "exterior-top-baseline",
            top_camera,
            front_target,
            exterior_baseline_visible,
        ),
        render_view(
            camera,
            output_dir,
            "exterior-top-candidate",
            top_camera,
            front_target,
            default_visible,
        ),
    ]

    silhouette_pairs = {
        "front": (renders[4], renders[5]),
        "right": (renders[6], renders[7]),
        "top": (renders[8], renders[9]),
    }
    silhouette_comparison = {}
    for view_name, (baseline_render, candidate_render) in silhouette_pairs.items():
        comparison = compare_render_pixels(
            repo_path(baseline_render), repo_path(candidate_render)
        )
        comparison["baseline_render"] = baseline_render
        comparison["candidate_render"] = candidate_render
        silhouette_comparison[view_name] = comparison
        if not comparison["identical"]:
            raise ValueError(
                f"V7 changes the {view_name} exterior silhouette: {comparison}"
            )

    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in default_visible
            obj.hide_render = obj not in default_visible
            obj.hide_set(obj not in default_visible)
    camera.location = Vector((0.0, 520.0, 240.0))
    point_at(camera, Vector((0.0, 150.0, 170.0)))

    protected_after = {
        name: rear_v5.mesh_fingerprint(bpy.data.objects[name])
        for name in source_mesh_names
    }
    if protected_before != protected_after:
        raise ValueError("V7 review changed exact Gate 8 source geometry")

    frame_checks = {
        "tangent_dot_interior": round(
            pair_frame["tangent"].dot(pair_frame["interior"]), 8
        ),
        "tangent_dot_across": round(
            pair_frame["tangent"].dot(pair_frame["across"]), 8
        ),
        "interior_dot_across": round(
            pair_frame["interior"].dot(pair_frame["across"]), 8
        ),
        "interior_dot_exterior": round(
            pair_frame["interior"].dot(pair_frame["exterior"]), 8
        ),
        "insert_interior_alignment": round(
            pair_frame["interior"].dot(pair_frame["insert_interior"]), 8
        ),
        "owner_interior_alignment": round(
            pair_frame["interior"].dot(pair_frame["owner_interior"]), 8
        ),
        "insert_across_alignment": round(
            pair_frame["across"].dot(pair_frame["insert_across"]), 8
        ),
        "owner_across_alignment": round(
            pair_frame["across"].dot(pair_frame["owner_across"]), 8
        ),
        "axis_lengths": {
            key: round(pair_frame[key].length, 8)
            for key in ("tangent", "interior", "across", "exterior")
        },
    }
    scene = bpy.context.scene
    scene["default_review_view"] = "full_head_context_single_right_pair"
    scene["review_status"] = config["status"]
    scene["prototype_side"] = "right"
    scene["prototype_location_count"] = 1
    scene["orange_flange_count"] = 1
    scene["green_flange_count"] = 1
    scene["placement_only"] = True
    scene["hardware_count"] = 0
    scene["hole_count"] = 0
    scene["separate_root_geometry_count"] = 0
    scene["review_only_boolean_cutaway_proof_count"] = len(proofs)
    scene["trapezoid_or_broad_base_count"] = 0
    scene["exterior_silhouette_views_identical"] = True
    scene["compound_bridge_count"] = 0
    scene["loose_clamp_count"] = 0
    scene["accepted_v3_fit_body_changed"] = False
    scene["exact_gate8_source_geometry_changed"] = False
    scene["not_print_released"] = True
    blend_path = output_dir / "ear-root-internal-rectangular-flange-placement-review-v7.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "feedback_scope": ["F-10", "F-11", "F-12"],
        "prototype": config["prototype"],
        "config": str(config_path.relative_to(REPO_ROOT)),
        "v3_config": str(v3_config_path.relative_to(REPO_ROOT)),
        "physical_fit_feedback": config["physical_fit_feedback"],
        "interface_revision": interface["interface_revision"],
        "accepted_v3_fit_body_changed": False,
        "exact_gate8_source_mesh_count": len(source_mesh_names),
        "exact_gate8_source_meshes_unchanged": True,
        "placement_pair": config["placement_pair"],
        "prototype_location_count": 1,
        "right_orange_flange_count": 1,
        "right_green_flange_count": 1,
        "left_prototype_count": 0,
        "rectangular_tab_count": 2,
        "separate_root_geometry_count": 0,
        "review_only_boolean_cutaway_proof_count": len(proofs),
        "review_only_boolean_cutaway_proof_objects": sorted(
            obj.name for obj in proofs.values()
        ),
        "review_only_boolean_cutaway_proof_volumes_mm3": proof_volumes,
        "review_only_proofs_change_connector_geometry": False,
        "hardware_count": 0,
        "hole_count": 0,
        "compound_bridge_count": 0,
        "convex_hull_transition_count": 0,
        "loose_clamp_count": 0,
        "trapezoid_or_broad_base_count": 0,
        "pair_is_parallel_by_shared_frame": True,
        "shared_frame_checks": frame_checks,
        "rectangle_dimensions_mm": pair["dimensions_mm"],
        "rectangular_owner_root_inset_mm": pair["root_inset_mm"],
        "measured_mating_gap_mm": round(pair["measured_gap_mm"], 4),
        "orange_rectangle_overlaps_yellow_owner": pair[
            "orange_owner_overlap"
        ],
        "green_rectangle_overlaps_gray_owner": pair[
            "green_owner_overlap"
        ],
        "orange_owner_intersection_pairs": pair[
            "orange_owner_intersection_pairs"
        ],
        "green_owner_intersection_pairs": pair[
            "green_owner_intersection_pairs"
        ],
        "exterior_silhouette_comparison": silhouette_comparison,
        "moving_composite_topology": composite_topology,
        "moving_composite_body_intersection_pairs": body_overlap_counts,
        "seated_moving_composite_hits": seated_hits,
        "green_unintended_shell_hits": green_other_shell_hits,
        "path_validation": path_report,
        "redundant_quad_face_proof_preserved": redundant_faces,
        "review_sequence": [
            "Review the two rectangular tabs and owner roots only.",
            "Do not add holes or hardware until placement is accepted.",
            "Do not mirror or replicate until the single joint is accepted.",
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
        / "ear-root-internal-rectangular-flange-placement-review-v7-validation.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
