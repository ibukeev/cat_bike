#!/usr/bin/env python3
"""Generate one right-side standard paired ear-root flange for review."""

from __future__ import annotations

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
import generate_eye_all_eight_flange_broad_base_review_v3 as eye_v3  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate6_eye_modules as gate6  # noqa: E402
import generate_gate7_glow_panel_inserts as gate7  # noqa: E402
import generate_gate8_full_size_iteration as gate8  # noqa: E402
import generate_rear_cassette_lossless_repartition_review_v5 as rear_v5  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/ear-root-standard-paired-flange-review-v6.json"
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
    scene.name = "Ear_Root_Standard_Paired_Flange_Review_V6"
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
    camera_data = bpy.data.cameras.new("EAR6_REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("EAR6_REVIEW_ONLY__Camera", camera_data)
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
    path = output_dir / "renders" / f"ear-root-standard-pair-{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path.relative_to(REPO_ROOT))


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


def cut_axis_cavity(
    target: bpy.types.Object,
    name: str,
    start: Vector,
    end: Vector,
    diameter: float,
) -> None:
    cutter = gate5.cylinder(
        name,
        start,
        end,
        diameter,
        vertices=32,
    )
    gate5.apply_boolean(target, cutter, "DIFFERENCE", solver="EXACT")
    gate5.require_manifold(target, name)


def shared_pair_frame(
    record: dict[str, Any],
    fraction: float,
) -> dict[str, Vector]:
    midpoint = Vector(record["midpoint"])
    source_tangent = Vector(record["tangent"]).normalized()
    insert_radial = Vector(record["radial"]).normalized()
    insert_inward = Vector(record["inward"]).normalized()
    owner_radial = Vector(record["owner_radial"]).normalized()
    owner_inward = Vector(record["owner_inward"]).normalized()
    anchor = midpoint + source_tangent * (
        (float(fraction) - 0.5) * float(record["length"])
    )
    if insert_inward.dot(owner_inward) < 0.0:
        owner_inward = -owner_inward
    inward = insert_inward + owner_inward
    if inward.length < 0.01:
        raise ValueError("Insert and owner inward vectors have no shared bisector")
    inward.normalize()
    tangent = source_tangent - inward * source_tangent.dot(inward)
    if tangent.length < 0.01:
        raise ValueError("Shared flange frame lost the seam tangent")
    tangent.normalize()
    radial = inward.cross(tangent).normalized()
    if radial.dot(insert_radial) < 0.0:
        radial.negate()
    if radial.dot(owner_radial) < 0.0:
        raise ValueError("Shared radial does not point toward both owner radials")
    return {
        "anchor": anchor,
        "tangent": tangent,
        "inward": inward,
        "radial": radial,
        "insert_inward": insert_inward,
        "owner_inward": owner_inward,
        "insert_radial": insert_radial,
        "owner_radial": owner_radial,
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
    inward = frame["inward"]
    radial = frame["radial"]
    length = float(values["tab_length_mm"])
    depth = float(values["tab_depth_mm"])
    thickness = float(values["tab_thickness_mm"])
    gap = float(values["mating_gap_mm"])
    front_recess = float(values["front_recess_mm"])
    dimensions = (length, depth, thickness)
    offset = gap / 2.0 + thickness / 2.0
    orange_center = (
        anchor + radial * offset + inward * (front_recess + depth / 2.0)
    )
    green_center = (
        anchor - radial * offset + inward * (front_recess + depth / 2.0)
    )
    flange_frame = {
        "tangent": tangent,
        "inward": inward,
        "radial": radial,
        "dimensions": dimensions,
    }

    orange = gate5.box(
        "EAR6_RIGHT_INSERT_FLANGE__orange",
        orange_center,
        (tangent, inward, radial),
        dimensions,
        materials["orange"],
    )
    orange_base = eye_v3.create_broad_base(
        "EAR6_RIGHT_INSERT_FLANGE__broad_base_tool",
        orange_center,
        flange_frame,
        1.0,
        values["broad_base"],
        materials["orange"],
    )
    orange_base_flange_overlap = c002_v2.surfaces_overlap(
        orange_base, orange
    )
    orange_base_owner_overlap = c002_v2.surfaces_overlap(
        orange_base, right_body
    )
    if not orange_base_flange_overlap or not orange_base_owner_overlap:
        raise ValueError(
            "Orange broad base misses its rectangular flange or yellow owner"
        )
    gate5.apply_boolean(orange, orange_base, "UNION", solver="EXACT")
    gate5.require_manifold(orange, "V6 orange flange/base union")

    green = gate5.box(
        "EAR6_RIGHT_HEAD_FLANGE__green",
        green_center,
        (tangent, inward, radial),
        dimensions,
        materials["green"],
    )
    green_base = eye_v3.create_broad_base(
        "EAR6_RIGHT_HEAD_FLANGE__broad_base_tool",
        green_center,
        flange_frame,
        -1.0,
        values["broad_base"],
        materials["green"],
    )
    green_base_flange_overlap = c002_v2.surfaces_overlap(
        green_base, green
    )
    green_base_owner_overlap = c002_v2.surfaces_overlap(
        green_base, right_upper
    )
    if not green_base_flange_overlap or not green_base_owner_overlap:
        raise ValueError(
            "Green broad base misses its rectangular flange or gray owner"
        )
    gate5.apply_boolean(green, green_base, "UNION", solver="EXACT")
    gate5.require_manifold(green, "V6 green flange/base union")

    hole_center = anchor + inward * float(values["hole_depth_from_front_mm"])
    backing = values["broad_base"]
    backing_depth = float(backing["total_backing_depth_mm"])
    overlap = float(backing["flange_overlap_mm"])
    orange_outer = gap / 2.0 + thickness + backing_depth - overlap
    green_mating_face = -gap / 2.0
    green_cavity_end = green_mating_face - float(
        values["heat_set_hole_depth_mm"]
    )
    hole_span = 2.0 * (orange_outer + 4.0)
    gate6.cut_axis_hole(
        orange,
        "EAR6_RIGHT_INSERT_FLANGE__m3_clearance",
        hole_center,
        radial,
        float(values["m3_clearance_diameter_mm"]),
        hole_span,
    )
    cut_axis_cavity(
        green,
        "EAR6_RIGHT_HEAD_FLANGE__heat_set_cavity",
        hole_center + radial * green_mating_face,
        hole_center + radial * green_cavity_end,
        float(values["heat_set_hole_diameter_mm"]),
    )
    gate5.require_manifold(orange, "V6 drilled orange paired flange")
    gate5.require_manifold(green, "V6 cavity-bearing green paired flange")

    if c002_v2.surfaces_overlap(orange, green):
        raise ValueError("Parallel paired flanges overlap")
    measured_gap = c002_v2.surface_distance(orange, green)
    if abs(measured_gap - gap) > 0.01:
        raise ValueError(
            f"Paired-flange gap changed: expected {gap}, got {measured_gap}"
        )
    orange_owner_hits = ear_v3.world_triangle_intersection_count(
        orange, right_body
    )
    green_owner_hits = ear_v3.world_triangle_intersection_count(
        green, right_upper
    )
    if orange_owner_hits == 0 or green_owner_hits == 0:
        raise ValueError("A paired flange lacks broad owner intersection")

    washer_thickness = float(values["washer_thickness_mm"])
    head_height = float(values["screw_head_height_mm"])
    hardware_axis_start = green_cavity_end + 0.5
    hardware_axis_end = orange_outer + washer_thickness
    shaft = gate5.cylinder(
        "EAR6_RIGHT_HARDWARE__m3_shaft",
        hole_center + radial * hardware_axis_start,
        hole_center + radial * hardware_axis_end,
        float(values["screw_shaft_diameter_mm"]),
        materials["hardware"],
        vertices=24,
    )
    washer = gate5.cylinder(
        "EAR6_RIGHT_HARDWARE__washer",
        hole_center + radial * orange_outer,
        hole_center + radial * (orange_outer + washer_thickness),
        float(values["washer_outer_diameter_mm"]),
        materials["hardware"],
        vertices=32,
    )
    head_start = orange_outer + washer_thickness
    head = gate5.cylinder(
        "EAR6_RIGHT_HARDWARE__button_head",
        hole_center + radial * head_start,
        hole_center + radial * (head_start + head_height),
        float(values["screw_head_diameter_mm"]),
        materials["hardware"],
        vertices=32,
    )
    insert_length = float(values["heat_set_insert_length_mm"])
    heat_insert = gate5.cylinder(
        "EAR6_RIGHT_HARDWARE__heat_set_insert",
        hole_center + radial * green_mating_face,
        hole_center + radial * (green_mating_face - insert_length),
        float(values["heat_set_insert_diameter_mm"]),
        materials["hardware"],
        vertices=24,
    )
    access_start = head_start + head_height + 0.2
    tool = gate5.cylinder(
        "EAR6_RIGHT_ACCESS__tool_corridor",
        hole_center + radial * access_start,
        hole_center
        + radial
        * (access_start + float(values["tool_corridor_length_mm"])),
        float(values["tool_corridor_diameter_mm"]),
        materials["access"],
        vertices=24,
    )
    finger = gate5.cylinder(
        "EAR6_RIGHT_ACCESS__finger_envelope",
        hole_center + radial * access_start,
        hole_center
        + radial
        * (access_start + float(values["finger_envelope_length_mm"])),
        float(values["finger_envelope_diameter_mm"]),
        materials["access"],
        vertices=24,
    )
    for obj in (orange, green, shaft, washer, head, heat_insert, tool, finger):
        obj.color = obj.data.materials[0].diffuse_color

    return {
        "orange": orange,
        "green": green,
        "hardware": [shaft, washer, head, heat_insert],
        "access": [tool, finger],
        "hole_center": hole_center,
        "hole_axis": radial,
        "frame": frame,
        "measured_gap_mm": measured_gap,
        "orange_base_flange_overlap": orange_base_flange_overlap,
        "orange_base_owner_overlap": orange_base_owner_overlap,
        "green_base_flange_overlap": green_base_flange_overlap,
        "green_base_owner_overlap": green_base_owner_overlap,
        "orange_owner_intersection_pairs": orange_owner_hits,
        "green_owner_intersection_pairs": green_owner_hits,
    }


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
        deep_body, deep_margin, "EAR6_VALIDATION__deep_body_margin"
    )
    flange_envelope = gate8.expanded_insert_cutter(
        orange, flange_margin, "EAR6_VALIDATION__orange_flange_margin"
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
        "screw_and_washer_removed_during_motion": True,
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
        "paired_flange_path_clear": not (
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
        "EAR6_VALIDATION__right_deep_fit_body", source_payloads["deep"]
    )
    bpy.context.scene.collection.objects.link(right_deep)
    right_body = ear_v2.deserialize_mesh(
        "EAR6_ACCEPTED_V3_BODY__right", source_payloads["full"]
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
        "EAR6_ACCEPTED_V3_BODY__left",
        ear_v3.mirror_payload(ear_v2.serialize_mesh(right_body)),
    )
    bpy.context.scene.collection.objects.link(left_body)
    display = config["display"]
    materials = {
        "body": gate5.material(
            "EAR6_ACCEPTED_V3_BODY__yellow",
            c002_v2.hex_color(display["accepted_fit_body_color"]),
        ),
        "orange": gate5.material(
            "EAR6_RIGHT_INSERT_FLANGE__orange",
            c002_v2.hex_color(display["insert_flange_color"]),
        ),
        "green": gate5.material(
            "EAR6_RIGHT_HEAD_FLANGE__green",
            c002_v2.hex_color(display["head_flange_color"]),
        ),
        "hardware": gate5.material(
            "EAR6_M3_HARDWARE__brass",
            c002_v2.hex_color(display["hardware_color"]),
        ),
        "access": gate5.material(
            "EAR6_ACCESS__white",
            c002_v2.hex_color(display["access_envelope_color"]),
        ),
    }
    for body in (right_body, left_body):
        body.data.materials.clear()
        body.data.materials.append(materials["body"])
        body.color = materials["body"].diffuse_color
        body.show_in_front = True

    spec = config["prototype"]
    if spec["side"] != "right":
        raise ValueError("V6 is intentionally a right-side-only prototype")
    record = right_boundary[int(spec["right_boundary_edge_index"])]
    if record["owner"] != "right_upper_head":
        raise ValueError("V6 prototype is not rooted on right_upper_head")
    pair_frame = shared_pair_frame(
        record, float(spec["fraction_from_first_vertex"])
    )
    pair = create_pair(
        pair_frame,
        config["paired_flange"],
        right_body,
        right_upper,
        materials,
    )

    body_overlap_counts = [
        ear_v3.world_triangle_intersection_count(right_body, pair["orange"])
    ]
    if body_overlap_counts[0] == 0:
        raise ValueError("V6 orange flange has no broad body overlap")
    composite = right_body.copy()
    composite.data = right_body.data.copy()
    composite.name = "EAR6_VALIDATION__right_body_plus_orange_flange"
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
            f"V6 moving composite is not manifold: {composite_topology}"
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
            f"V6 moving composite hits structural shells: {seated_hits}"
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
            f"V6 green flange hits unintended shells: {green_other_shell_hits}"
        )
    path_report = validate_path(
        composite,
        pair["orange"],
        right_deep,
        pair["green"],
        path_frames["right"],
        v3_config,
        config["paired_flange"],
        structural_targets,
    )

    access_targets = [
        *structural_without_right_ear,
        right_body,
        pair["green"],
    ]
    access_hits = {
        obj.name: hits
        for obj in pair["access"]
        if (hits := ear_v3.collision_hits(obj, access_targets))
    }

    collection_names = (
        "EAR6_EXACT_STRUCTURAL_HEAD_MUTED__UNCHANGED",
        "EAR6_EXACT_EARS_CYAN__UNCHANGED",
        "EAR6_ACCEPTED_V3_BODIES_YELLOW__UNCHANGED",
        "EAR6_RIGHT_INSERT_FLANGE_ORANGE__SINGLE_PROTOTYPE",
        "EAR6_RIGHT_HEAD_FLANGE_GREEN__SINGLE_PROTOTYPE_UNINTEGRATED",
        "EAR6_M3_HARDWARE_BRASS__SINGLE_PROTOTYPE",
        "EAR6_ACCESS_ENVELOPES_WHITE__HIDDEN_BY_DEFAULT",
        "EAR6_OTHER_SOURCE_GEOMETRY__HIDDEN",
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
            target, collections["EAR6_EXACT_STRUCTURAL_HEAD_MUTED__UNCHANGED"]
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
            ear, collections["EAR6_EXACT_EARS_CYAN__UNCHANGED"]
        )
    for body in (right_body, left_body):
        c002_v2.link_reference(
            body, collections["EAR6_ACCEPTED_V3_BODIES_YELLOW__UNCHANGED"]
        )
    c002_v2.link_reference(
        pair["orange"],
        collections["EAR6_RIGHT_INSERT_FLANGE_ORANGE__SINGLE_PROTOTYPE"],
    )
    c002_v2.link_reference(
        pair["green"],
        collections[
            "EAR6_RIGHT_HEAD_FLANGE_GREEN__SINGLE_PROTOTYPE_UNINTEGRATED"
        ],
    )
    for obj in pair["hardware"]:
        c002_v2.link_reference(
            obj, collections["EAR6_M3_HARDWARE_BRASS__SINGLE_PROTOTYPE"]
        )
    for obj in pair["access"]:
        c002_v2.link_reference(
            obj, collections["EAR6_ACCESS_ENVELOPES_WHITE__HIDDEN_BY_DEFAULT"]
        )
        obj.hide_viewport = True
        obj.hide_render = True
        obj.hide_set(True)

    default_visible = {
        *context_objects,
        *ears,
        right_body,
        left_body,
        pair["orange"],
        pair["green"],
        *pair["hardware"],
    }
    pair_visible = {
        pair["orange"],
        pair["green"],
        *pair["hardware"],
    }
    pair_without_hardware = {
        pair["orange"],
        pair["green"],
    }
    owner_context_visible = {
        right_upper,
        right_body,
        c002_v2.require_object("right_ear"),
        pair["orange"],
        pair["green"],
        *pair["hardware"],
    }
    access_visible = {
        pair["orange"],
        pair["green"],
        *pair["hardware"],
        *pair["access"],
    }

    source_set = {bpy.data.objects[name] for name in source_mesh_names}
    for obj in source_set:
        if obj in default_visible:
            continue
        c002_v2.link_reference(
            obj, collections["EAR6_OTHER_SOURCE_GEOMETRY__HIDDEN"]
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
    radial = pair_frame["radial"]
    tangent = pair_frame["tangent"]
    inward = pair_frame["inward"]
    renders = [
        render_view(
            camera,
            output_dir,
            "full-head-context",
            Vector((0.0, 520.0, 240.0)),
            Vector((0.0, 150.0, 170.0)),
            default_visible,
        ),
        render_view(
            camera,
            output_dir,
            "right-owner-context",
            anchor
            + (inward + radial * 0.65 + tangent * 0.3).normalized() * 95.0,
            anchor + inward * 5.0,
            owner_context_visible,
        ),
        render_view(
            camera,
            output_dir,
            "right-pair-isolated",
            anchor + (inward + radial * 0.7 + tangent * 0.25).normalized() * 70.0,
            anchor + inward * 5.0,
            pair_visible,
        ),
        render_view(
            camera,
            output_dir,
            "right-pair-no-hardware",
            anchor + (inward + radial * 0.7 + tangent * 0.25).normalized() * 70.0,
            anchor + inward * 5.0,
            pair_without_hardware,
        ),
        render_view(
            camera,
            output_dir,
            "right-screw-axis",
            anchor + radial * 145.0 + inward * 15.0 + tangent * 10.0,
            pair["hole_center"],
            pair_visible,
        ),
        render_view(
            camera,
            output_dir,
            "right-tool-access",
            anchor + (inward + radial * 0.7 + tangent * 0.25).normalized() * 90.0,
            anchor + inward * 5.0,
            access_visible,
        ),
        render_view(
            camera,
            output_dir,
            "right-exterior-clean",
            Vector((285.0, -100.0, 270.0)),
            anchor,
            default_visible,
        ),
    ]

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
        raise ValueError("V6 review changed exact Gate 8 source geometry")

    frame_checks = {
        "tangent_dot_inward": round(
            pair_frame["tangent"].dot(pair_frame["inward"]), 8
        ),
        "tangent_dot_radial": round(
            pair_frame["tangent"].dot(pair_frame["radial"]), 8
        ),
        "inward_dot_radial": round(
            pair_frame["inward"].dot(pair_frame["radial"]), 8
        ),
        "axis_lengths": {
            key: round(pair_frame[key].length, 8)
            for key in ("tangent", "inward", "radial")
        },
    }
    scene = bpy.context.scene
    scene["default_review_view"] = "full_head_context_single_right_pair"
    scene["review_status"] = config["status"]
    scene["prototype_side"] = "right"
    scene["prototype_location_count"] = 1
    scene["orange_flange_count"] = 1
    scene["green_flange_count"] = 1
    scene["compound_bridge_count"] = 0
    scene["loose_clamp_count"] = 0
    scene["accepted_v3_fit_body_changed"] = False
    scene["exact_gate8_source_geometry_changed"] = False
    scene["not_print_released"] = True
    blend_path = output_dir / "ear-root-standard-paired-flange-review-v6.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "feedback_scope": ["F-10", "F-11", "F-12"],
        "prototype": config["prototype"],
        "config": str(config_path.relative_to(REPO_ROOT)),
        "v3_config": str(v3_config_path.relative_to(REPO_ROOT)),
        "accepted_eye_flange_reference_config": config[
            "accepted_eye_flange_reference_config"
        ],
        "physical_fit_feedback": config["physical_fit_feedback"],
        "interface_revision": interface["interface_revision"],
        "accepted_v3_fit_body_changed": False,
        "exact_gate8_source_mesh_count": len(source_mesh_names),
        "exact_gate8_source_meshes_unchanged": True,
        "paired_flange": config["paired_flange"],
        "prototype_location_count": 1,
        "right_orange_flange_count": 1,
        "right_green_flange_count": 1,
        "left_prototype_count": 0,
        "compound_bridge_count": 0,
        "convex_hull_transition_count": 0,
        "loose_clamp_count": 0,
        "pair_is_parallel_by_shared_frame": True,
        "shared_frame_checks": frame_checks,
        "coaxial_hole_axis_error_mm": 0.0,
        "measured_mating_gap_mm": round(pair["measured_gap_mm"], 4),
        "orange_base_overlaps_rectangular_flange": pair[
            "orange_base_flange_overlap"
        ],
        "orange_base_overlaps_yellow_owner": pair[
            "orange_base_owner_overlap"
        ],
        "green_base_overlaps_rectangular_flange": pair[
            "green_base_flange_overlap"
        ],
        "green_base_overlaps_gray_owner": pair[
            "green_base_owner_overlap"
        ],
        "orange_owner_intersection_pairs": pair[
            "orange_owner_intersection_pairs"
        ],
        "green_owner_intersection_pairs": pair[
            "green_owner_intersection_pairs"
        ],
        "moving_composite_topology": composite_topology,
        "moving_composite_body_intersection_pairs": body_overlap_counts,
        "seated_moving_composite_hits": seated_hits,
        "green_unintended_shell_hits": green_other_shell_hits,
        "access_envelope_hits_with_ear_removed": access_hits,
        "path_validation": path_report,
        "redundant_quad_face_proof_preserved": redundant_faces,
        "assembly": [
            "Seat the accepted yellow insert.",
            "Align the orange and green parallel rectangular tabs.",
            "Pass one M3 screw and 7 mm washer through the orange clearance side into the green heat-set insert.",
            "Remove that screw to separate the paired interface.",
        ],
        "green_source_shell_integration_validated": False,
        "heat_set_hardware_requires_physical_coupon": True,
        "manual_orange_hole_adjustment_requires_washer_and_edge_check": True,
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
        / "ear-root-standard-paired-flange-review-v6-validation.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
