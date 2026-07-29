#!/usr/bin/env python3
"""Generate Gate 9 V5 complementary keel and rear-bezel geometry."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate9_aperture_frame_and_keel_candidate_v3 as v3  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402
import generate_gate9_service_seams_candidate_v4 as v4  # noqa: E402
import gate9_service_seams_v4_continuous_spines as spines  # noqa: E402
import gate9_service_seams_v4_wire_ribs as wire_ribs  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT
    / "config/gate9-complementary-service-parts-candidate-v5.json"
)
BODY_PARTS = (
    "left_upper_head",
    "right_upper_head",
    "left_lower_face",
    "right_lower_face",
)
LOWER_PARTS = ("left_lower_face", "right_lower_face")
METAL_NAMES = v4.METAL_NAMES
WIRE_RIB_OUTWARD_ADJUSTMENT_MM = 0.0
WIRE_RIB_INWARD = Vector((0.0, -0.3069151497, 0.9517368811)).normalized()


def requested_config_path() -> Path:
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if "--config" in args:
        return Path(args[args.index("--config") + 1]).resolve()
    return DEFAULT_CONFIG.resolve()


def load_repo_json(relative_path: str) -> dict[str, Any]:
    return json.loads(
        (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    )


def delete_object(obj: bpy.types.Object) -> None:
    mesh = obj.data if obj.type == "MESH" else None
    bpy.data.objects.remove(obj, do_unlink=True)
    if mesh is not None and mesh.users == 0:
        bpy.data.meshes.remove(mesh)


def require_single_manifold(
    obj: bpy.types.Object, operation: str
) -> None:
    gate5.require_manifold(obj, operation)
    if len(gate5.components(obj)) != 1:
        raise ValueError(f"{operation}: {obj.name} is not one component")


def union(
    owner: bpy.types.Object,
    feature: bpy.types.Object,
    operation: str,
) -> None:
    if operation.startswith("keel cylindrical"):
        feature.location -= (
            WIRE_RIB_INWARD * WIRE_RIB_OUTWARD_ADJUSTMENT_MM
        )
        bpy.context.view_layer.update()
    selected_solver = (
        "MANIFOLD"
        if operation.startswith(("cassette continuous", "keel cylindrical"))
        else "EXACT"
    )
    gate5.apply_boolean(owner, feature, "UNION", solver=selected_solver)
    require_single_manifold(owner, operation)


def difference(
    owner: bpy.types.Object,
    cutter: bpy.types.Object,
    operation: str,
    solver: str,
) -> None:
    selected_solver = "MANIFOLD" if "fastener hole" in operation else "EXACT"
    gate5.apply_boolean(
        owner, cutter, "DIFFERENCE", solver=selected_solver
    )
    require_single_manifold(owner, operation)


def create_solidified_surface(
    name: str,
    vertices: list[Vector],
    faces: list[tuple[int, ...]],
    inward: Vector,
    thickness: float,
    material: bpy.types.Material,
) -> bpy.types.Object:
    adjusted_faces: list[tuple[int, ...]] = []
    for face in faces:
        first = vertices[face[0]]
        normal = Vector()
        for offset in range(1, len(face) - 1):
            candidate = (
                vertices[face[offset]] - first
            ).cross(vertices[face[offset + 1]] - first)
            if candidate.length > 0.001:
                normal = candidate.normalized()
                break
        if normal.length < 0.5:
            raise ValueError(f"{name}: degenerate source face {face}")
        adjusted_faces.append(
            tuple(reversed(face)) if normal.dot(inward) > 0.0 else face
        )

    mesh = bpy.data.meshes.new(f"{name}__mesh")
    mesh.from_pydata(vertices, [], adjusted_faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    solidify = obj.modifiers.new("V5_direct_inward_wall", "SOLIDIFY")
    solidify.thickness = thickness
    solidify.offset = -1.0
    solidify.use_rim = True
    solidify.use_rim_only = False
    solidify.use_even_offset = False
    solidify.use_quality_normals = True
    bpy.ops.object.modifier_apply(modifier=solidify.name)
    obj.select_set(False)
    require_single_manifold(obj, f"{name} direct solidification")
    return obj


def bilinear_point(
    center_front: Vector,
    side_front: Vector,
    center_rear: Vector,
    side_rear: Vector,
    u: float,
    v: float,
) -> Vector:
    front = center_front.lerp(side_front, u)
    rear = center_rear.lerp(side_rear, u)
    return front.lerp(rear, v)


def build_complementary_keel(
    v5_config: dict[str, Any],
    seam_config: dict[str, Any],
    material: bpy.types.Material,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    keel_config = v5_config["keel"]
    seam = seam_config["seam_geometry"]
    inward = Vector(seam["bottom_inward_normal_head"]).normalized()
    exterior_outset = float(
        keel_config["exterior_outset_mm"]
    )
    side_clearance = float(
        keel_config["lower_shell_side_clearance_mm"]
    )
    rear_clearance = float(keel_config["rear_bezel_clearance_mm"])
    rear_toward_keel = Vector(
        seam["rear_edge_toward_keel_head"]
    ).normalized()
    center_front = Vector((0.0, 40.065, 0.0))
    center_rear = Vector(seam["rear_edge_center_head_mm"])
    center_rear += rear_toward_keel * rear_clearance
    scupper_width = float(keel_config["front_scupper_width_mm"])
    scupper_depth = float(keel_config["front_scupper_depth_mm"])
    half_scupper = scupper_width / 2.0
    span_length = (center_rear - center_front).length
    notch_v = scupper_depth / span_length

    vertices: list[Vector] = []
    faces: list[tuple[int, ...]] = []
    coordinate_map: dict[tuple[float, float, float], int] = {}

    def index(point: Vector) -> int:
        key = tuple(round(float(value), 6) for value in point)
        if key not in coordinate_map:
            coordinate_map[key] = len(vertices)
            vertices.append(point)
        return coordinate_map[key]

    scupper_records = []
    for part, sign in (
        ("right_lower_face", 1.0),
        ("left_lower_face", -1.0),
    ):
        lower = seam["lower_seams"][part]
        toward_owner = Vector(lower["toward_owner_head"]).normalized()
        side_front = (
            Vector(lower["start_head_mm"])
            - toward_owner * side_clearance
        )
        side_rear = (
            Vector(lower["end_head_mm"])
            - toward_owner * side_clearance
            + rear_toward_keel * rear_clearance
        )
        front_half_width = abs(float(side_front.x))
        center_x = abs(
            float(keel_config["front_scupper_centers_x_mm"][
                1 if sign > 0 else 0
            ])
        )
        low_u = (center_x - half_scupper) / front_half_width
        high_u = (center_x + half_scupper) / front_half_width
        uv_outline = (
            (0.0, 0.0),
            (low_u, 0.0),
            (low_u, notch_v),
            (high_u, notch_v),
            (high_u, 0.0),
            (1.0, 0.0),
            (1.0, 1.0),
            (0.0, 1.0),
        )
        points = [
            bilinear_point(
                center_front,
                side_front,
                center_rear,
                side_rear,
                u,
                v,
            )
            for u, v in uv_outline
        ]
        points = [
            point - inward * exterior_outset for point in points
        ]
        faces.append(tuple(index(point) for point in points))
        scupper_records.append(
            {
                "side": "right" if sign > 0 else "left",
                "nominal_center_x_mm": sign * center_x,
                "width_mm": scupper_width,
                "depth_mm": scupper_depth,
                "analytic_open_area_mm2": round(
                    scupper_width * scupper_depth, 3
                ),
            }
        )

    keel = create_solidified_surface(
        "gate9_v5__bottom_keel",
        vertices,
        faces,
        inward,
        float(keel_config["wall_thickness_mm"]),
        material,
    )
    return keel, {
        "construction": keel_config["construction"],
        "exterior_outset_mm": exterior_outset,
        "lower_shell_side_clearance_mm": side_clearance,
        "rear_bezel_clearance_mm": rear_clearance,
        "scuppers": scupper_records,
        "minimum_open_scupper_area_mm2_each": float(
            keel_config["minimum_open_scupper_area_mm2_each"]
        ),
    }


def build_open_rear_bezel(
    source: bpy.types.Object,
    v5_config: dict[str, Any],
    interface: dict[str, Any],
    material: bpy.types.Material,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    bezel_config = v5_config["rear_bezel"]
    source_vertex_count = int(
        bezel_config["source_outer_vertex_count"]
    )
    source_face_count = int(bezel_config["source_outer_face_count"])
    if len(source.data.vertices) < source_vertex_count * 2:
        raise ValueError("V5 rear-bezel source lacks solidified vertex pairs")
    vertices = [
        source.matrix_world @ source.data.vertices[index].co.copy()
        for index in range(source_vertex_count)
    ]
    faces = [
        tuple(int(index) for index in polygon.vertices)
        for polygon in source.data.polygons[:source_face_count]
    ]
    if any(
        index >= source_vertex_count for face in faces for index in face
    ):
        raise ValueError("V5 rear-bezel outer-face extraction crossed the inner wall")

    inset = float(bezel_config["body_seam_inset_mm"])
    shell_target = Vector((0.0, 225.0, 160.0))
    body_indices = [
        int(value) for value in bezel_config["body_seam_vertex_indices"]
    ]
    for index in body_indices:
        direction = shell_target - vertices[index]
        if direction.length < 1.0:
            raise ValueError("V5 rear-bezel body seam inset direction collapsed")
        vertices[index] += direction.normalized() * inset

    plane = interface["rear_interface_plane"]
    center = Vector(plane["center_head_mm"])
    normal = Vector(plane["outward_normal_head"]).normalized()
    across = Vector((1.0, 0.0, 0.0))
    vertical = normal.cross(across).normalized()
    aperture_horizontal_clearance = float(
        bezel_config["metal_aperture_horizontal_clearance_mm"]
    )
    aperture_vertical_clearance = float(
        bezel_config["metal_aperture_vertical_clearance_mm"]
    )
    aperture_outward_offset = float(
        bezel_config["metal_aperture_outward_offset_mm"]
    )
    aperture_indices = [
        int(value)
        for value in bezel_config["metal_aperture_vertex_indices"]
    ]
    aperture_before = {}
    aperture_after = {}
    for index in aperture_indices:
        delta = vertices[index] - center
        local_x = delta.dot(across)
        local_v = delta.dot(vertical)
        local_n = delta.dot(normal)
        aperture_before[str(index)] = [
            round(local_x, 3),
            round(local_v, 3),
            round(local_n, 3),
        ]
        local_n += aperture_outward_offset
        if abs(local_x) > 0.01:
            local_x += (
                aperture_horizontal_clearance
                if local_x > 0.0
                else -aperture_horizontal_clearance
            )
        local_v += (
            aperture_vertical_clearance
            if local_v > 0.0
            else -aperture_vertical_clearance
        )
        vertices[index] = (
            center
            + across * local_x
            + vertical * local_v
            + normal * local_n
        )
        aperture_after[str(index)] = [
            round(local_x, 3),
            round(local_v, 3),
            round(local_n, 3),
        ]

    bezel = create_solidified_surface(
        "gate9_v5__rear_bezel",
        vertices,
        faces,
        -normal,
        float(bezel_config["wall_thickness_mm"]),
        material,
    )
    return bezel, {
        "construction": bezel_config["construction"],
        "body_seam_inset_mm": inset,
        "metal_aperture_horizontal_clearance_mm": (
            aperture_horizontal_clearance
        ),
        "metal_aperture_vertical_clearance_mm": (
            aperture_vertical_clearance
        ),
        "metal_aperture_outward_offset_mm": aperture_outward_offset,
        "source_outer_vertex_count": source_vertex_count,
        "source_outer_face_count": source_face_count,
        "metal_aperture_local_coordinates_before_mm": aperture_before,
        "metal_aperture_local_coordinates_after_mm": aperture_after,
    }


def collision_matrix(
    moving: bpy.types.Object,
    fixed: dict[str, bpy.types.Object],
) -> dict[str, Any]:
    return {
        name: comparison.collision_record(moving, obj)
        for name, obj in fixed.items()
    }


def all_clear(matrix: dict[str, Any]) -> bool:
    return all(not record["intersects"] for record in matrix.values())


def object_stats(
    obj: bpy.types.Object, architecture_config: dict[str, Any]
) -> dict[str, Any]:
    return v3.object_stats(obj, architecture_config)


def main() -> None:
    config_path = requested_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    global WIRE_RIB_OUTWARD_ADJUSTMENT_MM
    WIRE_RIB_OUTWARD_ADJUSTMENT_MM = float(
        config["keel"]["wire_rib_outward_adjustment_mm"]
    )
    v4_config = load_repo_json(config["source_v4_config"])
    v3_config_path = (
        REPO_ROOT / config["source_v3_config"]
    ).resolve()
    original_v3_requested_config_path = v3.requested_config_path
    original_base_parse_args = v3.base.parse_args
    v3.requested_config_path = lambda: v3_config_path
    v3.base.parse_args = lambda: type("V5Args", (), {"config": v3_config_path})()
    try:
        v3.main()
    finally:
        v3.requested_config_path = original_v3_requested_config_path
        v3.base.parse_args = original_base_parse_args

    output_dir = (REPO_ROOT / config["output_namespace"]).resolve()
    architecture_config = load_repo_json(
        config["source_architecture_config"]
    )
    interface = load_repo_json(config["shared_interface_path"])
    objects = {
        part: bpy.data.objects[f"gate9_frame_candidate__{part}"]
        for part in BODY_PARTS
    }
    source_keel = bpy.data.objects[
        "gate9_v3_partition_source__bottom_keel"
    ]
    source_cassette = bpy.data.objects[
        "gate9_frame_candidate__rear_cassette"
    ]
    metal = {
        name: bpy.data.objects[f"gate9_frame_candidate__{name}"]
        for name in METAL_NAMES
    }
    material = comparison.create_material(
        "gate9_v5_complementary_parts", "#31A67C"
    )
    seam_material = comparison.create_material(
        "gate9_v5_service_spines", "#8E5AC8"
    )
    cutter_material = comparison.create_material(
        "gate9_v5_cutters", "#D74949", alpha=0.25
    )

    keel, keel_report = build_complementary_keel(
        config, v4_config, material
    )
    bezel, bezel_report = build_open_rear_bezel(
        source_cassette, config, interface, material
    )
    source_keel.hide_render = True
    source_keel.hide_viewport = True
    source_cassette.hide_render = True
    source_cassette.hide_viewport = True

    v4.union = union
    v4.difference = difference
    spines.install(v4)
    wire_ribs.install(v4)
    fastener_records: list[dict[str, Any]] = []
    for part in LOWER_PARTS:
        fastener_records.extend(
            v4.add_lower_seal_and_pads(
                part,
                objects[part],
                keel,
                v4_config,
                seam_material,
                cutter_material,
            )
        )
    fastener_records.extend(
        v4.add_rear_seal_and_pads(
            bezel,
            keel,
            v4_config,
            seam_material,
            cutter_material,
        )
    )
    wire_report = v4.add_wire_channel(
        keel, v4_config, seam_material
    )
    wire_report["v5_outward_adjustment_mm"] = (
        WIRE_RIB_OUTWARD_ADJUSTMENT_MM
    )
    wire_report["rib_center_inward_mm"] = round(
        float(wire_report["rib_center_inward_mm"])
        - WIRE_RIB_OUTWARD_ADJUSTMENT_MM,
        3,
    )

    modified = {
        **objects,
        "rear_bezel": bezel,
        "bottom_keel": keel,
    }
    stats = {
        name: object_stats(obj, architecture_config)
        for name, obj in modified.items()
    }
    topology_pass = all(
        value["connected_components"] == 1
        and value["boundary_edges"] == 0
        and value["nonmanifold_edges"] == 0
        for value in stats.values()
    )
    seated = {
        "keel_to_lower_shells": collision_matrix(
            keel, {part: objects[part] for part in LOWER_PARTS}
        ),
        "keel_to_rear_bezel": comparison.collision_record(keel, bezel),
        "rear_bezel_to_body_shells": collision_matrix(bezel, objects),
    }
    seated_clear = (
        all_clear(seated["keel_to_lower_shells"])
        and not seated["keel_to_rear_bezel"]["intersects"]
        and all_clear(seated["rear_bezel_to_body_shells"])
    )
    seated_collision_records = [
        *seated["keel_to_lower_shells"].values(),
        seated["keel_to_rear_bezel"],
        *seated["rear_bezel_to_body_shells"].values(),
    ]
    minimum_sampled_seated_clearance = min(
        float(record["minimum_sampled_vertex_to_surface_distance_mm"])
        for record in seated_collision_records
    )
    required_sampled_seated_clearance = float(
        config["minimum_sampled_seated_clearance_mm"]
    )
    sampled_seated_clearance_pass = (
        minimum_sampled_seated_clearance
        >= required_sampled_seated_clearance
    )
    printed_to_metal = {
        name: collision_matrix(obj, metal)
        for name, obj in (
            ("bottom_keel", keel),
            ("rear_bezel", bezel),
            *[(part, objects[part]) for part in LOWER_PARTS],
        )
    }
    metal_clear = all(
        all_clear(matrix) for matrix in printed_to_metal.values()
    )
    inward = Vector(
        v4_config["seam_geometry"]["bottom_inward_normal_head"]
    ).normalized()
    keel_sweep = v4.sweep_records(
        keel,
        -inward,
        config["service_sweeps"]["keel_outward_test_offsets_mm"],
        {part: objects[part] for part in LOWER_PARTS},
    )
    rear_outward = Vector(
        interface["rear_interface_plane"]["outward_normal_head"]
    ).normalized()
    bezel_sweep = v4.sweep_records(
        bezel,
        rear_outward,
        config["service_sweeps"][
            "rear_bezel_outward_test_offsets_mm"
        ],
        {**objects, "bottom_keel": keel},
    )
    sweeps_clear = all(record["clear"] for record in keel_sweep) and all(
        record["clear"] for record in bezel_sweep
    )
    scuppers_pass = all(
        record["analytic_open_area_mm2"]
        >= keel_report["minimum_open_scupper_area_mm2_each"]
        for record in keel_report["scuppers"]
    )
    wire_pass = (
        wire_report["actual_clear_width_mm"]
        >= wire_report["minimum_clear_width_mm"]
        and wire_report["rear_exit_gap_width_mm"]
        >= wire_report["provisional_bundle_envelope_mm"][0]
    )

    shells_dir = output_dir / "shells"
    for name, obj in modified.items():
        comparison.export_stl(obj, shells_dir / f"{name}.stl")
    source_ear_dir = (
        REPO_ROOT
        / "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-rear-architecture-comparison-v1/variants/rear_cassette_full_scale"
    )
    for ear in ("left_ear", "right_ear"):
        source = source_ear_dir / f"{ear}.stl"
        if not source.exists():
            raise FileNotFoundError(source)

    all_review_objects = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and obj.name.startswith(
            (
                "gate9_frame_candidate__",
                "gate9_v3_partition_source__",
                "gate9_v5__",
                "review_frame__",
                "v4__",
            )
        )
    ]
    camera = bpy.data.objects.get("Bridge_Audit_Camera")
    if camera is None:
        camera = v3.base.audit.configure_workbench_render()
    for render_name, selected in (
        (
            "v5_complementary_parts__assembled",
            [*objects.values(), bezel, keel],
        ),
        (
            "v5_lower_shells_and_keel__inside",
            [objects["left_lower_face"], objects["right_lower_face"], keel],
        ),
        ("v5_open_rear_bezel_and_metal", [bezel, *metal.values()]),
        ("v5_keel_scuppers_wire_and_spines", [keel]),
    ):
        v3.base.audit.render_part(
            render_name,
            selected,
            all_review_objects,
            output_dir,
            camera,
        )
    for obj in all_review_objects:
        obj.hide_render = False
        obj.hide_viewport = False
    source_keel.hide_render = True
    source_keel.hide_viewport = True
    source_cassette.hide_render = True
    source_cassette.hide_viewport = True

    validation = {
        "all_six_modified_printed_parts_one_closed_manifold_component": topology_pass,
        "new_keel_and_rear_bezel_are_direct_boundary_constructions": True,
        "seated_complementary_printed_parts_clear": seated_clear,
        "minimum_sampled_seated_clearance_meets_requirement": (
            sampled_seated_clearance_pass
        ),
        "modified_service_parts_clear_frozen_v03_metal_envelopes": metal_clear,
        "ordered_keel_then_rear_bezel_service_sweeps_clear": sweeps_clear,
        "two_boundary_scuppers_meet_minimum_analytic_open_area": scuppers_pass,
        "protected_cylindrical_wire_ribs_and_rear_exit_meet_envelope": wire_pass,
    }
    validation["digital_v5_complementary_candidate_pass"] = all(
        validation.values()
    )
    report = {
        "status": config["status"],
        "interface_revision": interface["interface_revision"],
        "config": str(config_path.relative_to(REPO_ROOT)),
        "source_v3_config": config["source_v3_config"],
        "source_v4_config": config["source_v4_config"],
        "construction": {
            "bottom_keel": keel_report,
            "rear_bezel": bezel_report,
        },
        "fastener_manifest": fastener_records,
        "fastener_count": len(fastener_records),
        "wire_channel": wire_report,
        "seated_collision_after_v5": seated,
        "minimum_sampled_seated_clearance_mm": round(
            minimum_sampled_seated_clearance, 4
        ),
        "required_sampled_seated_clearance_mm": (
            required_sampled_seated_clearance
        ),
        "printed_to_frozen_metal_collisions": printed_to_metal,
        "service_sweeps": {
            "keel_from_bottom_first": keel_sweep,
            "rear_bezel_from_rear_after_keel": bezel_sweep,
        },
        "parts": stats,
        "validation": validation,
        "acceptance_holds": config["acceptance_holds"],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    blend_path = (
        output_dir
        / "gate9-complementary-service-parts-candidate-v5.blend"
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report["generated_review_files"] = {
        "blend": str(blend_path.relative_to(REPO_ROOT)),
        "shell_stls": str(shells_dir.relative_to(REPO_ROOT)),
        "renders": str((output_dir / "renders").relative_to(REPO_ROOT)),
    }
    report_path = (
        output_dir
        / "gate9-complementary-service-parts-candidate-v5.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "validation": validation,
                "fastener_count": len(fastener_records),
                "seated_collision_after_v5": seated,
                "rear_bezel_to_metal": printed_to_metal["rear_bezel"],
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        ),
        flush=True,
    )
    if not validation["digital_v5_complementary_candidate_pass"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
