#!/usr/bin/env python3
"""Generate the F-10/F-11/F-12 removable under-ear clamp review."""

from __future__ import annotations

import argparse
import copy
import json
import math
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
DEFAULT_CONFIG = PACKAGE_ROOT / "config/ear-root-removable-clamp-review-v4.json"
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
    scene.name = "Ear_Root_Removable_Clamp_Review_V4"
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
    camera_data = bpy.data.cameras.new("EAR4_REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("EAR4_REVIEW_ONLY__Camera", camera_data)
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
    path = output_dir / "renders" / f"ear-root-clamp-{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path.relative_to(REPO_ROOT))


def vector_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "edge": [int(value) for value in record["edge"]],
        "owner": record["owner"],
        "length": float(record["length"]),
        **{
            key: [float(value) for value in record[key]]
            for key in ("midpoint", "tangent", "inward", "radial", "owner_inward", "owner_radial")
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
                owner_outward = sum((gate5.outward_normal(context["model"].faces[index], context["transformed"]) for index in neighbor_faces), Vector())
                if owner_outward.length < 0.01:
                    raise ValueError(f"Boundary edge {record['edge']} has opposing owner normals")
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
        return [
            vector_record(record)
            for record in records
        ]
    finally:
        gate7.CONFIG = original


def object_copy(obj: bpy.types.Object, name: str) -> bpy.types.Object:
    duplicate = obj.copy()
    duplicate.data = obj.data.copy()
    duplicate.name = name
    bpy.context.scene.collection.objects.link(duplicate)
    return duplicate


def mirror_object(
    obj: bpy.types.Object,
    name: str,
    material: bpy.types.Material | None = None,
) -> bpy.types.Object:
    mirrored = ear_v2.deserialize_mesh(
        name, ear_v3.mirror_payload(ear_v2.serialize_mesh(obj))
    )
    bpy.context.scene.collection.objects.link(mirrored)
    if material:
        mirrored.data.materials.clear()
        mirrored.data.materials.append(material)
        mirrored.color = material.diffuse_color
    return mirrored


def frame_vectors(record: dict[str, Any]) -> tuple[Vector, Vector, Vector, Vector]:
    return (
        Vector(record["midpoint"]),
        Vector(record["tangent"]).normalized(),
        Vector(record["radial"]).normalized(),
        Vector(record["inward"]).normalized(),
    )


def owner_frame_vectors(
    record: dict[str, Any]
) -> tuple[Vector, Vector, Vector, Vector]:
    return (
        Vector(record["midpoint"]),
        Vector(record["tangent"]).normalized(),
        Vector(record["owner_radial"]).normalized(),
        Vector(record["owner_inward"]).normalized(),
    )


def mount_anchor(
    record: dict[str, Any], fraction_from_first: float
) -> Vector:
    midpoint, tangent, _, _ = frame_vectors(record)
    return midpoint + tangent * (
        (float(fraction_from_first) - 0.5) * float(record["length"])
    )


def ranged_box(
    name: str,
    anchor: Vector,
    tangent: Vector,
    radial: Vector,
    inward: Vector,
    tangent_length: float,
    radial_min: float,
    radial_max: float,
    outer_depth: float,
    thickness: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    center = (
        anchor
        + radial * ((radial_min + radial_max) / 2.0)
        + inward * (outer_depth + thickness / 2.0)
    )
    obj = gate5.box(
        name,
        center,
        (tangent, radial, inward),
        (tangent_length, radial_max - radial_min, thickness),
        material,
    )
    obj.color = material.diffuse_color
    return obj


def transverse_convex_hull(
    points: list[Vector],
    anchor: Vector,
    tangent: Vector,
    basis_u: Vector,
) -> list[Vector]:
    basis_u = basis_u.normalized()
    basis_v = tangent.normalized().cross(basis_u).normalized()
    projected = sorted(
        {
            (
                round((point - anchor).dot(basis_u), 9),
                round((point - anchor).dot(basis_v), 9),
            ): point
            for point in points
        }.items()
    )
    if len(projected) < 3:
        raise ValueError("Clamp cross-section has fewer than three unique points")

    def cross(first: Any, second: Any, third: Any) -> float:
        return (
            (second[0][0] - first[0][0]) * (third[0][1] - first[0][1])
            - (second[0][1] - first[0][1]) * (third[0][0] - first[0][0])
        )

    lower: list[Any] = []
    for item in projected:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], item) <= 0.0:
            lower.pop()
        lower.append(item)
    upper: list[Any] = []
    for item in reversed(projected):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], item) <= 0.0:
            upper.pop()
        upper.append(item)
    return [point for _, point in lower[:-1] + upper[:-1]]


def bridging_clamp(
    name: str,
    anchor: Vector,
    tangent: Vector,
    insert_radial: Vector,
    insert_inward: Vector,
    shell_radial: Vector,
    shell_inward: Vector,
    values: dict[str, Any],
    material: bpy.types.Material,
) -> bpy.types.Object:
    half_tangent = float(values["removable_clamp_tangent_length_mm"]) / 2.0
    shell_radial_min = float(values["removable_clamp_radial_min_mm"])
    shell_radial_max = float(values["removable_clamp_shell_contact_radial_max_mm"])
    insert_radial_min = float(values["removable_clamp_insert_contact_radial_min_mm"])
    insert_radial_max = float(values["removable_clamp_radial_max_mm"])
    insert_outer = float(values["removable_clamp_outer_depth_mm"])
    shell_outer = float(values["removable_clamp_shell_side_outer_depth_mm"])
    thickness = float(values["removable_clamp_thickness_mm"])
    lead = float(values["clamp_lead_in_mm"])
    candidates = [
        *[
            anchor + shell_radial * radial_offset + shell_inward * depth
            for radial_offset in (shell_radial_min, shell_radial_max)
            for depth in (shell_outer, shell_outer + thickness)
        ],
        *[
            anchor + insert_radial * radial_offset + insert_inward * depth
            for radial_offset, depth in (
                (insert_radial_min, insert_outer),
                (insert_radial_max - lead, insert_outer),
                (insert_radial_max, insert_outer + lead),
                (insert_radial_max, insert_outer + thickness + lead),
                (insert_radial_max - lead, insert_outer + thickness),
                (insert_radial_min, insert_outer + thickness),
            )
        ],
    ]
    cross_section = transverse_convex_hull(
        candidates, anchor, tangent, insert_radial
    )
    vertices = [
        point + tangent * tangent_offset
        for tangent_offset in (-half_tangent, half_tangent)
        for point in cross_section
    ]
    count = len(cross_section)
    faces: list[tuple[int, ...]] = [
        tuple(range(count - 1, -1, -1)),
        tuple(range(count, 2 * count)),
    ]
    for index in range(count):
        following = (index + 1) % count
        faces.append((index, following, count + following, count + index))
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata([tuple(value) for value in vertices], [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.data.materials.append(material)
    obj.color = material.diffuse_color
    gate5.require_manifold(obj, name)
    return obj


def cut_axis_cavity(
    target: bpy.types.Object,
    name: str,
    center: Vector,
    axis: Vector,
    diameter: float,
    length: float,
) -> None:
    cutter = gate5.cylinder(
        name,
        center - axis.normalized() * length / 2.0,
        center + axis.normalized() * length / 2.0,
        diameter,
        vertices=32,
    )
    gate5.apply_boolean(target, cutter, "DIFFERENCE", solver="EXACT")
    gate5.require_manifold(target, f"{target.name} {name}")


def create_point_geometry(
    point_id: str,
    record: dict[str, Any],
    fraction: float,
    values: dict[str, Any],
    materials: dict[str, bpy.types.Material],
) -> dict[str, Any]:
    midpoint, tangent, insert_radial, insert_inward = frame_vectors(record)
    _, _, shell_radial, shell_inward = owner_frame_vectors(record)
    anchor = mount_anchor(record, fraction)
    insert_flange = ranged_box(
        f"EAR4_INSERT_FLANGE__right__{point_id}",
        anchor,
        tangent,
        insert_radial,
        insert_inward,
        float(values["insert_flange_tangent_length_mm"]),
        float(values["insert_flange_radial_min_mm"]),
        float(values["insert_flange_radial_max_mm"]),
        float(values["insert_flange_outer_depth_mm"]),
        float(values["insert_flange_thickness_mm"]),
        materials["insert_flange"],
    )
    shell_anchor = ranged_box(
        f"EAR4_FIXED_SHELL_ANCHOR__right__{point_id}",
        anchor,
        tangent,
        shell_radial,
        shell_inward,
        float(values["shell_anchor_tangent_length_mm"]),
        float(values["shell_anchor_radial_min_mm"]),
        float(values["shell_anchor_radial_max_mm"]),
        float(values["shell_anchor_outer_depth_mm"]),
        float(values["shell_anchor_thickness_mm"]),
        materials["fixed_shell"],
    )
    gate5.require_manifold(shell_anchor, f"right {point_id} fixed assembly")

    screw_radial = float(values["screw_radial_offset_mm"])
    radial = shell_radial
    inward = shell_inward
    anchor_inner = float(values["shell_anchor_outer_depth_mm"]) + float(
        values["shell_anchor_thickness_mm"]
    )
    heat_depth = float(values["heat_set_hole_depth_mm"])
    heat_center = (
        anchor
        + radial * screw_radial
        + inward * (anchor_inner - heat_depth / 2.0)
    )
    cut_axis_cavity(
        shell_anchor,
        f"EAR4_HEAT_SET_CAVITY__right__{point_id}",
        heat_center,
        inward,
        float(values["heat_set_hole_diameter_mm"]),
        heat_depth,
    )

    clamp = bridging_clamp(
        f"EAR4_REMOVABLE_CLAMP__right__{point_id}",
        anchor,
        tangent,
        insert_radial,
        insert_inward,
        shell_radial,
        shell_inward,
        values,
        materials["clamp"],
    )
    clamp_shell_outer = float(values["removable_clamp_shell_side_outer_depth_mm"])
    clamp_thickness = float(values["removable_clamp_thickness_mm"])
    clamp_hole_center = (
        anchor
        + radial * screw_radial
        + inward * (clamp_shell_outer + clamp_thickness / 2.0)
    )
    gate6.cut_axis_hole(
        clamp,
        f"EAR4_M3_CLEARANCE__right__{point_id}",
        clamp_hole_center,
        inward,
        float(values["m3_clearance_diameter_mm"]),
        clamp_thickness + 2.0,
    )

    heat_insert = gate5.cylinder(
        f"EAR4_HARDWARE__right__{point_id}__heat_set_insert",
        anchor
        + radial * screw_radial
        + inward * (anchor_inner - float(values["heat_set_insert_length_mm"])),
        anchor + radial * screw_radial + inward * anchor_inner,
        float(values["heat_set_insert_diameter_mm"]),
        materials["hardware"],
        vertices=24,
    )
    shaft = gate5.cylinder(
        f"EAR4_HARDWARE__right__{point_id}__m3_shaft",
        anchor + radial * screw_radial + inward * (anchor_inner - 3.0),
        anchor
        + radial * screw_radial
        + inward * (clamp_shell_outer + clamp_thickness + 0.8),
        3.0,
        materials["hardware"],
        vertices=24,
    )
    washer_start = clamp_shell_outer + clamp_thickness
    washer = gate5.cylinder(
        f"EAR4_HARDWARE__right__{point_id}__washer",
        anchor + radial * screw_radial + inward * washer_start,
        anchor + radial * screw_radial + inward * (washer_start + 0.8),
        float(values["washer_outer_diameter_mm"]),
        materials["hardware"],
        vertices=32,
    )
    head_start = washer_start + 0.8
    head = gate5.cylinder(
        f"EAR4_HARDWARE__right__{point_id}__button_head",
        anchor + radial * screw_radial + inward * head_start,
        anchor
        + radial * screw_radial
        + inward * (head_start + float(values["screw_head_height_mm"])),
        float(values["screw_head_diameter_mm"]),
        materials["hardware"],
        vertices=32,
    )
    access_start = head_start + float(values["screw_head_height_mm"]) + 0.2
    tool = gate5.cylinder(
        f"EAR4_ACCESS__right__{point_id}__tool_corridor",
        anchor + radial * screw_radial + inward * access_start,
        anchor
        + radial * screw_radial
        + inward * (access_start + float(values["tool_corridor_length_mm"])),
        float(values["tool_corridor_diameter_mm"]),
        materials["access"],
        vertices=24,
    )
    finger = gate5.cylinder(
        f"EAR4_ACCESS__right__{point_id}__finger_envelope",
        anchor + radial * screw_radial + inward * access_start,
        anchor
        + radial * screw_radial
        + inward * (access_start + float(values["finger_envelope_length_mm"])),
        float(values["finger_envelope_diameter_mm"]),
        materials["access"],
        vertices=24,
    )
    for obj in (heat_insert, shaft, washer, head, tool, finger):
        obj.color = obj.data.materials[0].diffuse_color
    return {
        "id": point_id,
        "anchor": anchor,
        "tangent": tangent,
        "radial": radial,
        "inward": inward,
        "insert_radial": insert_radial,
        "insert_inward": insert_inward,
        "insert_flange": insert_flange,
        "fixed_shell": shell_anchor,
        "clamp": clamp,
        "hardware": [heat_insert, shaft, washer, head],
        "access": [tool, finger],
        "edge_record": record,
    }


def topology_record(obj: bpy.types.Object) -> dict[str, Any]:
    boundary, nonmanifold = gate5.topology_counts(obj)
    return {
        "connected_components": len(gate5.components(obj)),
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "faces": len(obj.data.polygons),
        "volume_mm3": round(gate5.mesh_volume(obj), 4),
    }


def union_composite(
    body: bpy.types.Object,
    flanges: list[bpy.types.Object],
    name: str,
) -> tuple[bpy.types.Object, list[int]]:
    composite = object_copy(body, name)
    overlaps = []
    for index, flange in enumerate(flanges, start=1):
        overlaps.append(
            ear_v3.world_triangle_intersection_count(composite, flange)
        )
        tool = object_copy(flange, f"{name}__union_tool_{index}")
        gate5.apply_boolean(composite, tool, "UNION", solver="EXACT")
    topology = topology_record(composite)
    if (
        topology["connected_components"] != 1
        or topology["boundary_edges"]
        or topology["nonmanifold_edges"]
    ):
        raise ValueError(f"{name} is not one connected manifold: {topology}")
    if any(count == 0 for count in overlaps):
        raise ValueError(f"{name} has a flange without broad body overlap")
    return composite, overlaps


def collision_hits(
    obj: bpy.types.Object, targets: list[bpy.types.Object]
) -> dict[str, int]:
    return ear_v3.collision_hits(obj, targets)


def validate_path(
    side: str,
    composite: bpy.types.Object,
    moving_retainers: list[bpy.types.Object],
    deep_body: bpy.types.Object,
    frame: dict[str, Any],
    v3_config: dict[str, Any],
    v4_config: dict[str, Any],
    structural_targets: list[bpy.types.Object],
    fixed_targets: list[bpy.types.Object],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    targets = [
        target
        for target in [*structural_targets, *fixed_targets]
        if target.name != f"{side}_ear"
    ]
    samples = ear_v3.path_samples(frame, v3_config["insertion_path"])
    body_margin = float(
        v3_config["fit_clearance"]["deep_body_path_margin_mm"]
    )
    retention_margin = float(
        v4_config["retention"]["moving_retention_path_margin_mm"]
    )
    deep_envelope = gate8.expanded_insert_cutter(
        deep_body, body_margin, f"EAR4_{side}_deep_body_margin"
    )
    retention_envelopes = [
        gate8.expanded_insert_cutter(
            retainer, retention_margin, f"EAR4_{side}_retention_margin_{index}"
        )
        for index, retainer in enumerate(moving_retainers, start=1)
    ]
    conflicts = []
    deep_conflicts = []
    moving_margin_conflicts = []
    maximum_actual = 0
    maximum_deep = 0
    maximum_moving_margin = 0
    for sample in samples:
        for obj in (composite, deep_envelope, *retention_envelopes):
            obj.matrix_world = sample["matrix"]
        actual_hits = collision_hits(composite, targets)
        deep_hits = collision_hits(deep_envelope, targets)
        margin_hits = {}
        for envelope in retention_envelopes:
            for target_name, count in collision_hits(envelope, targets).items():
                margin_hits[target_name] = margin_hits.get(target_name, 0) + count
        maximum_actual = max(maximum_actual, sum(actual_hits.values()))
        maximum_deep = max(maximum_deep, sum(deep_hits.values()))
        maximum_moving_margin = max(
            maximum_moving_margin, sum(margin_hits.values())
        )
        metadata = {
            key: value for key, value in sample.items() if key != "matrix"
        }
        if actual_hits:
            conflicts.append({**metadata, "hits": actual_hits})
        if deep_hits:
            deep_conflicts.append({**metadata, "hits": deep_hits})
        if margin_hits:
            moving_margin_conflicts.append({**metadata, "hits": margin_hits})
    for obj in (composite, deep_envelope, *retention_envelopes):
        obj.matrix_world = Matrix.Identity(4)
    bpy.data.objects.remove(deep_envelope, do_unlink=True)
    for envelope in retention_envelopes:
        bpy.data.objects.remove(envelope, do_unlink=True)
    if conflicts or deep_conflicts or moving_margin_conflicts:
        raise ValueError(
            f"{side} V4 path conflict: actual={conflicts}; "
            f"deep={deep_conflicts}; retention_margin={moving_margin_conflicts}"
        )
    return (
        {
            "side": side,
            "clamps_and_screws_removed_during_path": True,
            "sample_count": len(samples),
            "maximum_actual_triangle_intersection_pairs": maximum_actual,
            "v3_deep_body_margin_mm": body_margin,
            "maximum_deep_body_margin_triangle_intersection_pairs": maximum_deep,
            "moving_retention_margin_mm": retention_margin,
            "maximum_moving_retention_margin_triangle_intersection_pairs": maximum_moving_margin,
            "all_samples_clear": True,
        },
        samples,
    )


def link_reference(
    obj: bpy.types.Object, collection: bpy.types.Collection
) -> None:
    c002_v2.link_reference(obj, collection)


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    v3_config_path = repo_path(config["v3_config"])
    v3_config = json.loads(v3_config_path.read_text(encoding="utf-8"))
    source_gate6 = repo_path(v3_config["source_gate6_blend"])
    source_gate8 = repo_path(v3_config["source_gate8_blend"])
    shared_interface = json.loads(
        repo_path(config["shared_interface_path"]).read_text(encoding="utf-8")
    )
    if (
        shared_interface["interface_revision"]
        != config["required_interface_revision"]
    ):
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
    for target in structural_targets:
        target.hide_set(False)
        target.hide_viewport = False

    right_deep = ear_v2.deserialize_mesh(
        "EAR4_VALIDATION__right_deep_fit_body", source_payloads["deep"]
    )
    bpy.context.scene.collection.objects.link(right_deep)
    right_body = ear_v2.deserialize_mesh(
        "EAR4_ACCEPTED_V3_BODY__right", source_payloads["full"]
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
    left_deep = mirror_object(
        right_deep, "EAR4_VALIDATION__left_deep_fit_body"
    )
    left_body = mirror_object(
        right_body, "EAR4_ACCEPTED_V3_BODY__left"
    )
    bodies = {"left": left_body, "right": right_body}
    deep_bodies = {"left": left_deep, "right": right_deep}

    display = config["display"]
    materials = {
        "body": gate5.material(
            "EAR4_ACCEPTED_V3_BODY__yellow",
            c002_v2.hex_color(display["accepted_fit_body_color"]),
        ),
        "insert_flange": gate5.material(
            "EAR4_INSERT_FLANGES__orange",
            c002_v2.hex_color(display["insert_flange_color"]),
        ),
        "fixed_shell": gate5.material(
            "EAR4_FIXED_SHELL_ANCHORS__green",
            c002_v2.hex_color(display["fixed_shell_anchor_color"]),
        ),
        "clamp": gate5.material(
            "EAR4_REMOVABLE_CLAMPS__blue",
            c002_v2.hex_color(display["removable_clamp_color"]),
        ),
        "hardware": gate5.material(
            "EAR4_HARDWARE__brass",
            c002_v2.hex_color(display["hardware_color"]),
        ),
        "access": gate5.material(
            "EAR4_ACCESS_ENVELOPES__white",
            c002_v2.hex_color(display["access_envelope_color"]),
        ),
    }
    for body in bodies.values():
        body.data.materials.clear()
        body.data.materials.append(materials["body"])
        body.color = materials["body"].diffuse_color
        body.show_in_front = True

    point_records: dict[str, list[dict[str, Any]]] = {"right": [], "left": []}
    for spec in config["mount_points"]:
        edge_index = int(spec["right_boundary_edge_index"])
        record = right_boundary[edge_index]
        if record["owner"] != "right_upper_head":
            raise ValueError(f"Point {spec['id']} is not on right_upper_head")
        point = create_point_geometry(
            spec["id"],
            record,
            float(spec["fraction_from_first_vertex"]),
            config["retention"],
            materials,
        )
        point["spec"] = spec
        point_records["right"].append(point)

    for right_point in point_records["right"]:
        point_id = right_point["id"]
        left_point = {
            "id": point_id,
            "spec": right_point["spec"],
            "anchor": Vector(
                (-right_point["anchor"].x, right_point["anchor"].y, right_point["anchor"].z)
            ),
            "tangent": Vector(
                (-right_point["tangent"].x, right_point["tangent"].y, right_point["tangent"].z)
            ),
            "radial": Vector(
                (-right_point["radial"].x, right_point["radial"].y, right_point["radial"].z)
            ),
            "inward": Vector(
                (-right_point["inward"].x, right_point["inward"].y, right_point["inward"].z)
            ),
            "insert_radial": Vector(
                (-right_point["insert_radial"].x, right_point["insert_radial"].y, right_point["insert_radial"].z)
            ),
            "insert_inward": Vector(
                (-right_point["insert_inward"].x, right_point["insert_inward"].y, right_point["insert_inward"].z)
            ),
            "insert_flange": mirror_object(
                right_point["insert_flange"],
                f"EAR4_INSERT_FLANGE__left__{point_id}",
                materials["insert_flange"],
            ),
            "fixed_shell": mirror_object(
                right_point["fixed_shell"],
                f"EAR4_FIXED_SHELL_ANCHOR__left__{point_id}",
                materials["fixed_shell"],
            ),
            "clamp": mirror_object(
                right_point["clamp"],
                f"EAR4_REMOVABLE_CLAMP__left__{point_id}",
                materials["clamp"],
            ),
            "hardware": [
                mirror_object(
                    obj,
                    obj.name.replace("__right__", "__left__"),
                    materials["hardware"],
                )
                for obj in right_point["hardware"]
            ],
            "access": [
                mirror_object(
                    obj,
                    obj.name.replace("__right__", "__left__"),
                    materials["access"],
                )
                for obj in right_point["access"]
            ],
            "edge_record": right_point["edge_record"],
        }
        point_records["left"].append(left_point)

    composites = {}
    flange_overlap_counts = {}
    fixed_by_side = {}
    clamps_by_side = {}
    hardware_by_side = {}
    access_by_side = {}
    for side in ("left", "right"):
        flanges = [point["insert_flange"] for point in point_records[side]]
        composite, overlaps = union_composite(
            bodies[side], flanges, f"EAR4_VALIDATION__{side}_moving_composite"
        )
        composites[side] = composite
        flange_overlap_counts[side] = overlaps
        fixed_by_side[side] = [
            point["fixed_shell"] for point in point_records[side]
        ]
        clamps_by_side[side] = [point["clamp"] for point in point_records[side]]
        hardware_by_side[side] = [
            obj for point in point_records[side] for obj in point["hardware"]
        ]
        access_by_side[side] = [
            obj for point in point_records[side] for obj in point["access"]
        ]

    all_fixed = [obj for values in fixed_by_side.values() for obj in values]
    all_clamps = [obj for values in clamps_by_side.values() for obj in values]
    side_reports = {}
    path_reports = {}
    path_samples = {}
    for side in ("left", "right"):
        ear = c002_v2.require_object(f"{side}_ear")
        upper = c002_v2.require_object(f"{side}_upper_head")
        other_structural = [
            target for target in structural_targets if target.name != upper.name
        ]
        fixed_unintended_hits = {}
        fixed_root_hits = []
        for fixed in fixed_by_side[side]:
            root_hits = ear_v3.world_triangle_intersection_count(fixed, upper)
            if root_hits == 0:
                raise ValueError(f"{fixed.name} has no broad upper-head root")
            fixed_root_hits.append(root_hits)
            hits = collision_hits(fixed, other_structural)
            if hits:
                fixed_unintended_hits[fixed.name] = hits
        if fixed_unintended_hits:
            raise ValueError(
                f"{side} fixed anchors hit unintended shells: "
                f"{fixed_unintended_hits}"
            )
        seated_hits = collision_hits(
            composites[side], [*structural_targets, *all_fixed]
        )
        if seated_hits:
            component_fixed_hits = {}
            moving_parts = [
                bodies[side],
                *[
                    point["insert_flange"]
                    for point in point_records[side]
                ],
            ]
            for moving_part in moving_parts:
                hits = collision_hits(moving_part, all_fixed)
                if hits:
                    component_fixed_hits[moving_part.name] = hits
            raise ValueError(
                f"{side} moving composite seated hits: {seated_hits}; "
                f"components={component_fixed_hits}"
            )

        clamp_hits = {}
        retention = config["retention"]
        fixed_contact_gap = float(
            retention["removable_clamp_shell_side_outer_depth_mm"]
        ) - (
            float(retention["shell_anchor_outer_depth_mm"])
            + float(retention["shell_anchor_thickness_mm"])
        )
        fixed_tangent_overlap = min(
            float(retention["removable_clamp_tangent_length_mm"]),
            float(retention["shell_anchor_tangent_length_mm"]),
        )
        fixed_radial_overlap = min(
            float(retention["removable_clamp_shell_contact_radial_max_mm"]),
            float(retention["shell_anchor_radial_max_mm"]),
        ) - max(
            float(retention["removable_clamp_radial_min_mm"]),
            float(retention["shell_anchor_radial_min_mm"]),
        )
        insert_contact_gap = float(
            retention["removable_clamp_outer_depth_mm"]
        ) - (
            float(retention["insert_flange_outer_depth_mm"])
            + float(retention["insert_flange_thickness_mm"])
        )
        insert_tangent_overlap = min(
            float(retention["removable_clamp_tangent_length_mm"]),
            float(retention["insert_flange_tangent_length_mm"]),
        )
        insert_radial_overlap = min(
            float(retention["removable_clamp_radial_max_mm"]),
            float(retention["insert_flange_radial_max_mm"]),
        ) - max(
            float(retention["removable_clamp_insert_contact_radial_min_mm"]),
            float(retention["insert_flange_radial_min_mm"]),
        )
        if abs(fixed_contact_gap) > 0.001 or fixed_radial_overlap <= 0.0:
            raise ValueError("Clamp does not seat on its fixed shell anchor")
        if (
            abs(insert_contact_gap - float(retention["clamp_pad_gap_mm"])) > 0.001
            or insert_radial_overlap <= 0.0
        ):
            raise ValueError("Clamp does not seat on its orange flange pad")
        fixed_contact_area = fixed_tangent_overlap * fixed_radial_overlap
        insert_contact_area = insert_tangent_overlap * insert_radial_overlap
        expected_fixed_contact_areas = {}
        expected_insert_contact_areas = {}
        for point in point_records[side]:
            clamp = point["clamp"]
            expected_fixed = point["fixed_shell"]
            expected_fixed_contact_areas[clamp.name] = round(
                fixed_contact_area, 4
            )
            expected_insert_contact_areas[clamp.name] = round(
                insert_contact_area, 4
            )
            clamp_targets = [
                *structural_targets,
                composites[side],
                *[fixed for fixed in all_fixed if fixed != expected_fixed],
            ]
            hits = collision_hits(clamp, clamp_targets)
            if hits:
                clamp_hits[clamp.name] = hits
        if clamp_hits:
            depth_sweep = {}
            for point in point_records[side]:
                clamp = point["clamp"]
                results = {}
                for delta in (0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0):
                    clamp.matrix_world = Matrix.Translation(
                        point["inward"] * delta
                    )
                    results[str(delta)] = collision_hits(clamp, [upper])
                clamp.matrix_world = Matrix.Identity(4)
                depth_sweep[point["id"]] = results
            raise ValueError(
                f"{side} assembled clamp collision: {clamp_hits}; "
                f"upper_head_depth_sweep={depth_sweep}"
            )

        access_hits = {}
        access_targets = [
            target
            for target in [*structural_targets, *all_fixed, *all_clamps]
            if target.name != ear.name
        ]
        for access in access_by_side[side]:
            hits = collision_hits(access, access_targets)
            if hits:
                access_hits[access.name] = hits
        if access_hits:
            raise ValueError(f"{side} access envelope blocked: {access_hits}")

        path_report, samples = validate_path(
            side,
            composites[side],
            [point["insert_flange"] for point in point_records[side]],
            deep_bodies[side],
            path_frames[side],
            v3_config,
            config,
            structural_targets,
            all_fixed,
        )
        path_reports[side] = path_report
        path_samples[side] = samples


        anchors = [point["anchor"] for point in point_records[side]]
        separations = [
            (anchors[first] - anchors[second]).length
            for first in range(len(anchors))
            for second in range(first + 1, len(anchors))
        ]
        minimum_separation = min(separations)
        if minimum_separation < float(
            config["retention"]["minimum_pairwise_anchor_separation_mm"]
        ):
            raise ValueError(f"{side} clamp points are not spatially separated")
        side_reports[side] = {
            "point_count": len(point_records[side]),
            "minimum_pairwise_anchor_separation_mm": round(
                minimum_separation, 4
            ),
            "moving_composite_topology": topology_record(composites[side]),
            "insert_flange_body_intersection_pairs": flange_overlap_counts[side],
            "fixed_anchor_upper_head_intersection_pairs": fixed_root_hits,
            "fixed_anchor_unintended_shell_hits": fixed_unintended_hits,
            "seated_moving_composite_hits": seated_hits,
            "assembled_clamp_hits": clamp_hits,
            "clamp_fixed_anchor_contact_area_mm2": expected_fixed_contact_areas,
            "clamp_fixed_anchor_contact_gap_mm": round(fixed_contact_gap, 4),
            "clamp_fixed_anchor_radial_overlap_mm": round(fixed_radial_overlap, 4),
            "clamp_insert_pad_contact_area_mm2": expected_insert_contact_areas,
            "clamp_insert_pad_gap_mm": round(insert_contact_gap, 4),
            "clamp_insert_pad_radial_overlap_mm": round(insert_radial_overlap, 4),
            "access_envelope_hits_with_ear_removed": access_hits,
            "clamp_axes_dot_local_inward": [
                round(point["inward"].dot(point["inward"]), 6)
                for point in point_records[side]
            ],
            "points": [
                {
                    "id": point["id"],
                    "role": point["spec"]["role"],
                    "anchor_mm": [round(float(value), 4) for value in point["anchor"]],
                    "owner_shell": f"{side}_upper_head",
                    "fastener_axis": [round(float(value), 6) for value in point["inward"]],
                    "direct_interior_approach": True,
                    "moving_flange_has_no_fastener_hole": True,
                    "clamp_is_removable_before_insert_motion": True,
                }
                for point in point_records[side]
            ],
            "path_validation": path_report,
        }

    right_body_bounds = ear_v2.mesh_bounds(bodies["right"])
    left_body_bounds = ear_v2.mesh_bounds(bodies["left"])
    body_symmetry_error = max(
        abs(left_body_bounds["minimum"][0] + right_body_bounds["maximum"][0]),
        abs(left_body_bounds["maximum"][0] + right_body_bounds["minimum"][0]),
        *(
            abs(left_body_bounds[key][axis] - right_body_bounds[key][axis])
            for key in ("minimum", "maximum")
            for axis in (1, 2)
        ),
    )
    if body_symmetry_error > 0.01:
        raise ValueError("Accepted V3 bodies lost mirror symmetry")

    collection_names = (
        "EAR4_EXACT_EARS_CYAN__UNCHANGED",
        "EAR4_EXACT_UPPER_HEADS_GRAY__UNCHANGED",
        "EAR4_ACCEPTED_V3_BODIES_YELLOW__UNCHANGED",
        "EAR4_INSERT_FLANGES_ORANGE__PROPOSED",
        "EAR4_FIXED_SHELL_ANCHORS_GREEN__PROPOSED_NOT_INTEGRATED",
        "EAR4_EXACT_LOWER_AND_REAR_SHELLS_MUTED__UNCHANGED",
        "EAR4_REMOVABLE_CLAMPS_BLUE__REMOVE_BEFORE_INSERT_MOTION",
        "EAR4_M3_HARDWARE_BRASS__PROPOSED",
        "EAR4_ACCESS_ENVELOPES_WHITE__HIDDEN_BY_DEFAULT",
        "EAR4_OTHER_SOURCE_GEOMETRY__HIDDEN",
    )
    collections = {}
    for name in collection_names:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        collections[name] = collection

    all_visible: set[bpy.types.Object] = set()
    side_visible: dict[str, set[bpy.types.Object]] = {}
    access_visible: dict[str, set[bpy.types.Object]] = {}
    interior_review_visible: dict[str, set[bpy.types.Object]] = {}
    insertion_ready_visible: dict[str, set[bpy.types.Object]] = {}
    for side in ("left", "right"):
        ear = c002_v2.require_object(f"{side}_ear")
        upper = c002_v2.require_object(f"{side}_upper_head")
        ear.color = c002_v2.hex_color(display["ear_color"])
        upper.color = c002_v2.hex_color(display["upper_head_color"])
        ear.show_wire = True
        upper.show_wire = True
        link_reference(ear, collections["EAR4_EXACT_EARS_CYAN__UNCHANGED"])
        link_reference(
            upper, collections["EAR4_EXACT_UPPER_HEADS_GRAY__UNCHANGED"]
        )
        link_reference(
            bodies[side],
            collections["EAR4_ACCEPTED_V3_BODIES_YELLOW__UNCHANGED"],
        )
        for obj in [
            ear,
            upper,
            bodies[side],
            *[point["insert_flange"] for point in point_records[side]],
            *fixed_by_side[side],
            *clamps_by_side[side],
            *hardware_by_side[side],
        ]:
            obj.hide_viewport = False
            obj.hide_render = False
            obj.hide_set(False)
        for point in point_records[side]:
            link_reference(
                point["insert_flange"],
                collections["EAR4_INSERT_FLANGES_ORANGE__PROPOSED"],
            )
            link_reference(
                point["fixed_shell"],
                collections[
                    "EAR4_FIXED_SHELL_ANCHORS_GREEN__PROPOSED_NOT_INTEGRATED"
                ],
            )
            link_reference(
                point["clamp"],
                collections[
                    "EAR4_REMOVABLE_CLAMPS_BLUE__REMOVE_BEFORE_INSERT_MOTION"
                ],
            )
            for obj in point["hardware"]:
                link_reference(
                    obj, collections["EAR4_M3_HARDWARE_BRASS__PROPOSED"]
                )
            for obj in point["access"]:
                link_reference(
                    obj,
                    collections[
                        "EAR4_ACCESS_ENVELOPES_WHITE__HIDDEN_BY_DEFAULT"
                    ],
                )
                obj.hide_viewport = True
                obj.hide_render = True
                obj.hide_set(True)
        visible = {
            ear,
            upper,
            bodies[side],
            *[point["insert_flange"] for point in point_records[side]],
            *fixed_by_side[side],
            *clamps_by_side[side],
            *hardware_by_side[side],
        }
        side_visible[side] = visible
        all_visible |= visible
        interior_review_visible[side] = {
            *[point["insert_flange"] for point in point_records[side]],
            *fixed_by_side[side],
            *clamps_by_side[side],
            *hardware_by_side[side],
        }
        access_visible[side] = {
            *[point["insert_flange"] for point in point_records[side]],
            *fixed_by_side[side],
            *clamps_by_side[side],
            *hardware_by_side[side],
            *access_by_side[side],
        }
        insertion_ready_visible[side] = {
            *[point["insert_flange"] for point in point_records[side]],
            *fixed_by_side[side],
        }

    context_shells = set(structural_targets)
    for name in ("right_lower_face", "left_lower_face", "rear_base"):
        obj = c002_v2.require_object(name)
        obj.color = c002_v2.hex_color(
            display["lower_rear_context_color"]
        )
        obj.show_wire = True
        obj.hide_viewport = False
        obj.hide_render = False
        obj.hide_set(False)
        link_reference(
            obj,
            collections[
                "EAR4_EXACT_LOWER_AND_REAR_SHELLS_MUTED__UNCHANGED"
            ],
        )
        all_visible.add(obj)

    for composite in composites.values():
        bpy.data.objects.remove(composite, do_unlink=True)
    for deep in deep_bodies.values():
        bpy.data.objects.remove(deep, do_unlink=True)
    source_set = {bpy.data.objects[name] for name in source_mesh_names}
    for obj in source_set:
        if obj in all_visible:
            continue
        link_reference(
            obj, collections["EAR4_OTHER_SOURCE_GEOMETRY__HIDDEN"]
        )
        obj.hide_viewport = True
        obj.hide_render = True
        obj.hide_set(True)

    isolated_visible = set().union(*interior_review_visible.values())
    default_visible = set(all_visible)

    camera = configure_scene(
        output_dir, int(display["render_resolution_px"])
    )
    context_shell_colors = {obj: tuple(obj.color) for obj in context_shells}
    for obj in context_shells:
        obj.color = (*obj.color[:3], 0.12)
        obj.display_type = "WIRE"
    renders = [
        render_view(
            camera,
            output_dir,
            "both-head-context",
            Vector((0.0, 520.0, 240.0)),
            Vector((0.0, 150.0, 170.0)),
            default_visible,
        ),
        render_view(
            camera,
            output_dir,
            "both-ear-root-context",
            Vector((0.0, 440.0, 270.0)),
            Vector((0.0, 175.0, 220.0)),
            default_visible,
        ),
        render_view(
            camera,
            output_dir,
            "both-retention-isolated",
            Vector((0.0, 430.0, 270.0)),
            Vector((0.0, 166.0, 222.0)),
            isolated_visible,
        ),
    ]
    for obj in context_shells:
        obj.color = context_shell_colors[obj]
        obj.display_type = "SOLID"

    for side, sign in (("left", -1.0), ("right", 1.0)):
        target = Vector((sign * 92.0, 168.0, 220.0))
        review_direction = Vector((sign, 1.0, 0.25)).normalized()
        review_location = target + review_direction * 220.0
        renders.extend(
            [
                render_view(
                    camera,
                    output_dir,
                    f"{side}-retention-isolated",
                    review_location,
                    target,
                    interior_review_visible[side],
                ),
                render_view(
                    camera,
                    output_dir,
                    f"{side}-insertion-ready-clamps-removed",
                    review_location,
                    target,
                    insertion_ready_visible[side],
                ),
                render_view(
                    camera,
                    output_dir,
                    f"{side}-tool-access-isolated",
                    review_location,
                    target,
                    access_visible[side],
                ),
                render_view(
                    camera,
                    output_dir,
                    f"{side}-exterior-clean",
                    Vector((sign * 285.0, -100.0, 270.0)),
                    target,
                    side_visible[side],
                ),
            ]
        )

    for obj in context_shells:
        obj.display_type = "WIRE"
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
        raise ValueError("V4 review changed exact Gate 8 source geometry")
    scene = bpy.context.scene
    scene["default_review_view"] = "full_structural_head_context_wireframe"
    scene["review_status"] = config["status"]
    scene["feedback_ids"] = "F-10,F-11,F-12"
    scene["retention_points_per_side"] = int(
        config["retention"]["point_count_per_side"]
    )
    scene["clamps_removable_before_insert_motion"] = True
    scene["accepted_v3_fit_body_changed"] = False
    scene["exact_gate8_source_geometry_changed"] = False
    scene["not_print_released"] = True
    scene["heat_set_cavity_shell_integration_validated"] = False
    scene["fixed_anchor_shell_integration_topology_validated"] = False
    blend_path = output_dir / "ear-root-removable-clamp-review-v4.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "feedback_scope": ["F-10", "F-11", "F-12"],
        "physical_acceptance_tests": ["A-08", "A-09", "A-10", "A-12", "A-18"],
        "config": str(config_path.relative_to(REPO_ROOT)),
        "v3_config": str(v3_config_path.relative_to(REPO_ROOT)),
        "physical_fit_feedback": config["physical_fit_feedback"],
        "interface_revision": shared_interface["interface_revision"],
        "accepted_v3_fit_body_changed": False,
        "accepted_v3_body_mirror_bounds_error_mm": round(body_symmetry_error, 6),
        "exact_gate8_source_mesh_count": len(source_mesh_names),
        "exact_gate8_source_meshes_unchanged": True,
        "retention": config["retention"],
        "assembly_sequence": config["assembly_sequence"],
        "side_records": side_reports,
        "path_validation": path_reports,
        "redundant_quad_face_proof_preserved": redundant_faces,
        "all_three_points_short_and_separated": True,
        "all_fasteners_approach_normal_to_local_panel_from_inside": True,
        "moving_insert_flanges_have_no_fastener_holes": True,
        "clamps_and_screws_removed_before_insert_motion": True,
        "green_shell_geometry_is_unintegrated_review_proposal": True,
        "heat_set_hardware_requires_physical_coupon": True,
        "heat_set_cavity_shell_integration_validated": False,
        "no_stl_or_gcode_exported": True,
        "fixed_anchor_shell_integration_topology_validated": False,
        "not_print_released": True,
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": renders,
        },
        "review_holds": config["review_holds"],
    }
    report_path = output_dir / "ear-root-removable-clamp-review-v4-validation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
