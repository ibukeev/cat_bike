#!/usr/bin/env python3
"""Generate the combined Gate 9 aperture-frame and bottom-keel V3 candidate."""

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

import generate_gate1_master as gate1  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate9_aperture_frame_candidate_v1 as base  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT
    / "config/gate9-aperture-frame-and-keel-candidate-v3.json"
)
LOWER_PARTS = ("left_lower_face", "right_lower_face")


def requested_config_path() -> Path:
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    if "--config" in args:
        return Path(args[args.index("--config") + 1]).resolve()
    return DEFAULT_CONFIG.resolve()


def build_partition_objects(
    config: dict[str, Any],
) -> tuple[
    dict[str, bpy.types.Object],
    bpy.types.Object,
    dict[str, Any],
]:
    architecture_config = json.loads(
        (
            REPO_ROOT / config["source_architecture_config"]
        ).read_text(encoding="utf-8")
    )
    interface = json.loads(
        (REPO_ROOT / config["shared_interface_path"]).read_text(
            encoding="utf-8"
        )
    )
    gate2_config = json.loads(
        (REPO_ROOT / config["source_gate2_config"]).read_text(
            encoding="utf-8"
        )
    )
    gate1_config = json.loads(
        gate1.DEFAULT_CONFIG.read_text(encoding="utf-8")
    )
    source = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    units = gate1.panel_units(
        source, gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV)
    )
    scale, origin, _ = gate1.make_transform(
        gate1.bounds(source.vertices),
        float(gate1_config["target_height_mm"]),
    )
    roles, _ = gate1.build_roles(units, gate1_config, scale)
    model = gate2.subdivide_center_panels(source, gate2_config)
    assignments = gate2.assign_faces(
        model.faces,
        model.vertices,
        roles,
        gate2_config,
        scale,
        origin,
    )
    transformed = [
        gate1.transform_point(vertex, scale, origin)
        for vertex in model.vertices
    ]
    threshold = float(
        architecture_config["variants"]["rear_cassette_full_scale"][
            "rear_cassette_threshold_mm"
        ]
    )
    cassette_faces = comparison.selected_cassette_faces(
        model,
        assignments,
        transformed,
        interface,
        threshold,
    )
    scale_center = Vector(
        interface["rear_interface_plane"]["center_head_mm"]
    )
    shell_config = architecture_config["shell"]
    keel_faces = set(
        int(index)
        for index in config["bottom_keel_partition"][
            "source_face_indices"
        ]
    )
    material = comparison.create_material(
        "gate9_v3_partition_source", "#387AB8"
    )
    lower_objects = {}
    source_face_indices = {}
    for part in LOWER_PARTS:
        selected = [
            index
            for index, assignment in enumerate(assignments)
            if assignment == part
            and index not in cassette_faces
            and index not in keel_faces
        ]
        source_faces = [
            tuple(model.faces[index].indices) for index in selected
        ]
        obj = comparison.create_shell_object(
            f"gate9_v3_partition_source__{part}",
            source_faces,
            model,
            scale,
            origin,
            1.0,
            scale_center,
            material,
            shell_config,
        )
        lower_objects[part] = obj
        source_face_indices[part] = selected

    closure_faces = [
        tuple(int(index) for index in face)
        for face in config["bottom_keel_partition"]["closure_faces"]
    ]
    keel_source_faces = [
        *[
            tuple(model.faces[index].indices)
            for index in sorted(keel_faces)
        ],
        *closure_faces,
    ]
    keel = comparison.create_shell_object(
        "gate9_v3_partition_source__bottom_keel",
        keel_source_faces,
        model,
        scale,
        origin,
        1.0,
        scale_center,
        comparison.create_material(
            "gate9_v3_bottom_keel", "#31A67C"
        ),
        shell_config,
    )
    partition_report = {
        "rear_cassette_threshold_mm": threshold,
        "lower_source_face_indices": source_face_indices,
        "bottom_keel_source_face_indices": sorted(keel_faces),
        "bottom_keel_closure_faces": [
            list(face) for face in closure_faces
        ],
        "bottom_keel_components_before_clearance": len(
            gate5.components(keel)
        ),
    }
    return lower_objects, keel, {
        "architecture_config": architecture_config,
        "partition": partition_report,
    }


def expanded_cutter(
    source: bpy.types.Object,
    name: str,
    expansion_mm: float,
) -> bpy.types.Object:
    cutter = base.duplicate_object(source, name)
    cutter.data.update(calc_edges=True)
    for vertex in cutter.data.vertices:
        normal = vertex.normal.copy()
        if normal.length > 0.01:
            vertex.co += normal.normalized() * expansion_mm
    cutter.data.update(calc_edges=True)
    return cutter


def object_stats(
    obj: bpy.types.Object, architecture_config: dict[str, Any]
) -> dict[str, Any]:
    shell = architecture_config["shell"]
    stats = comparison.object_stats(
        obj,
        shell["printer_envelope_mm"],
        int(shell["orientation_step_degrees"]),
    )
    stats["component_vertex_counts"] = [
        len(component) for component in gate5.components(obj)
    ]
    return stats


def main() -> None:
    config_path = requested_config_path()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    lower_objects, keel, partition_context = build_partition_objects(
        config
    )
    original_selected_object = base.selected_object
    original_make_edge_rib = base.make_edge_rib

    def selected_object(
        prefix: str, suffix: str
    ) -> bpy.types.Object:
        if suffix in lower_objects:
            return lower_objects[suffix]
        return original_selected_object(prefix, suffix)

    def trimmed_make_edge_rib(
        name: str,
        first_index: int,
        second_index: int,
        first_normal: Vector,
        second_normal: Vector,
        transformed: list[Vector],
        radius: float,
        recess: float,
        assigned_material: bpy.types.Material,
    ) -> tuple[bpy.types.Object, dict[str, Any]]:
        part = next(
            (
                candidate
                for candidate in base.audit.BODY_PARTS
                if name.startswith(f"{candidate}__")
            ),
            "",
        )
        configured = config["frame"].get(
            "edge_endpoint_trim_mm", {}
        ).get(part, {})
        first_trim = float(configured.get(str(first_index), 0.0))
        second_trim = float(configured.get(str(second_index), 0.0))
        adjusted = list(transformed)
        first = transformed[first_index]
        second = transformed[second_index]
        axis = second - first
        length = axis.length
        if first_trim + second_trim >= length - 4.0:
            raise ValueError(
                f"{name}: endpoint trims consume the rib span"
            )
        axis.normalize()
        adjusted[first_index] = first + axis * first_trim
        adjusted[second_index] = second - axis * second_trim
        rib, record = original_make_edge_rib(
            name,
            first_index,
            second_index,
            first_normal,
            second_normal,
            adjusted,
            radius,
            recess,
            assigned_material,
        )
        record["endpoint_trim_mm"] = {
            str(first_index): first_trim,
            str(second_index): second_trim,
        }
        record["untrimmed_edge_length_mm"] = round(length, 3)
        return rib, record

    base.selected_object = selected_object
    base.make_edge_rib = trimmed_make_edge_rib
    base.main()

    output_dir = (REPO_ROOT / config["output_namespace"]).resolve()
    base_report_path = (
        output_dir / "gate9-aperture-frame-candidate-v1.json"
    )
    report = json.loads(
        base_report_path.read_text(encoding="utf-8")
    )
    architecture_config = partition_context["architecture_config"]
    cassette = bpy.data.objects.get(
        "gate9_frame_candidate__rear_cassette"
    )
    if cassette is None:
        raise KeyError("V3 cassette collision reference is missing")
    metal_names = (
        "backplate",
        "rail_left",
        "rail_right",
        "shoe_envelope_left",
        "shoe_envelope_right",
        "shoe_tool_envelope_left",
        "shoe_tool_envelope_right",
        "adapter_hardware_n22_n20",
        "adapter_hardware_n22_p20",
        "adapter_hardware_p22_n20",
        "adapter_hardware_p22_p20",
    )
    metal = {
        name: bpy.data.objects[
            f"gate9_frame_candidate__{name}"
        ]
        for name in metal_names
    }
    keel.hide_render = False
    keel.hide_viewport = False
    keel.color = (0.13, 0.58, 0.39, 1.0)
    contact_before = comparison.collision_record(keel, cassette)
    clearance = float(
        config["bottom_keel_partition"][
            "keel_cassette_clearance_mm"
        ]
    )
    cutter = expanded_cutter(
        cassette,
        "gate9_v3_expanded_cassette_clearance_cutter",
        clearance,
    )
    gate5.apply_boolean(
        keel,
        cutter,
        "DIFFERENCE",
        solver=config["frame"]["boolean_solver"],
    )
    gate5.require_manifold(
        keel, "V3 bottom-keel cassette-clearance cut"
    )
    if len(gate5.components(keel)) != 1:
        raise ValueError(
            "V3 cassette-clearance cut split the bottom keel"
        )
    contact_after = comparison.collision_record(keel, cassette)
    metal_collisions = {
        name: comparison.collision_record(keel, envelope)
        for name, envelope in metal.items()
    }
    keel_stats = object_stats(keel, architecture_config)
    comparison.export_stl(
        keel, output_dir / "shells" / "bottom_keel.stl"
    )
    comparison.export_stl(
        cassette, output_dir / "shells" / "rear_cassette.stl"
    )

    all_review_objects = [
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and obj.name.startswith(
            (
                "gate9_frame_candidate__",
                "review_frame__",
                "gate9_v3_partition_source__",
            )
        )
    ]
    camera = bpy.data.objects.get("Bridge_Audit_Camera")
    if camera is None:
        camera = base.audit.configure_workbench_render()
    base.audit.render_part(
        "bottom_keel__relieved",
        [keel],
        all_review_objects,
        output_dir,
        camera,
    )
    lower_repaired = [
        bpy.data.objects[f"gate9_frame_candidate__{part}"]
        for part in LOWER_PARTS
    ]
    base.audit.render_part(
        "v3_lower_shells_keel_and_cassette__assembled",
        [*lower_repaired, keel, cassette],
        all_review_objects,
        output_dir,
        camera,
    )
    for obj in all_review_objects:
        obj.hide_render = False
        obj.hide_viewport = False

    report["status"] = config["status"]
    report["config"] = str(config_path.relative_to(REPO_ROOT))
    report["parts"]["bottom_keel"] = {
        **keel_stats,
        "connected_components_before_clearance": (
            partition_context["partition"][
                "bottom_keel_components_before_clearance"
            ]
        ),
        "connected_components_after": len(
            gate5.components(keel)
        ),
        "cassette_contact_before_clearance": contact_before,
        "cassette_contact_after_clearance": contact_after,
        "metal_envelope_collisions": metal_collisions,
    }
    report["bottom_keel_partition"] = {
        **partition_context["partition"],
        **config["bottom_keel_partition"],
    }
    base_validation = report["validation"]
    keel_single = (
        keel_stats["connected_components"] == 1
        and keel_stats["boundary_edges"] == 0
        and keel_stats["nonmanifold_edges"] == 0
    )
    keel_clear = (
        not contact_after["intersects"]
        and all(
            not collision["intersects"]
            for collision in metal_collisions.values()
        )
    )
    report["validation"] = {
        "all_four_body_shells_one_closed_manifold_component": (
            base_validation[
                "all_body_shells_one_closed_manifold_component"
            ]
        ),
        "bottom_keel_one_closed_manifold_component": keel_single,
        "all_aperture_frames_meet_analytic_exterior_recess": (
            base_validation[
                "all_frame_features_meet_analytic_exterior_recess"
            ]
        ),
        "all_body_frames_clear_cassette_and_metal_envelopes": (
            base_validation["all_frame_keepout_envelopes_clear"]
        ),
        "relieved_bottom_keel_clears_cassette_and_metal_envelopes": (
            keel_clear
        ),
        "digital_v3_topology_and_coarse_keepout_pass": (
            base_validation["digital_candidate_pass"]
            and keel_single
            and keel_clear
        ),
    }
    report["acceptance_holds"] = config["acceptance_holds"]
    blend_path = (
        output_dir
        / "gate9-aperture-frame-and-keel-candidate-v3.blend"
    )
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report["generated_review_files"] = {
        "blend": str(blend_path.relative_to(REPO_ROOT)),
        "shell_stls": str(
            (output_dir / "shells").relative_to(REPO_ROOT)
        ),
        "renders": str(
            (output_dir / "renders").relative_to(REPO_ROOT)
        ),
    }
    report_path = (
        output_dir
        / "gate9-aperture-frame-and-keel-candidate-v3.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "validation": report["validation"],
                "parts": {
                    part: {
                        "components_after": value[
                            "connected_components_after"
                        ],
                        "cassette_intersections": value[
                            "frame_keepout_collisions"
                        ]["cassette_intersection_count"],
                        "metal_intersections": value[
                            "frame_keepout_collisions"
                        ]["metal_intersection_count"],
                    }
                    for part, value in report["parts"].items()
                    if part in base.audit.BODY_PARTS
                },
                "bottom_keel": {
                    "components_after": report["parts"][
                        "bottom_keel"
                    ]["connected_components_after"],
                    "cassette_contact_before": contact_before[
                        "intersects"
                    ],
                    "cassette_contact_after": contact_after[
                        "intersects"
                    ],
                    "metal_intersection_count": sum(
                        1
                        for collision in metal_collisions.values()
                        if collision["intersects"]
                    ),
                    "dimensions_mm": keel_stats["dimensions_mm"],
                },
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )
    if not report["validation"][
        "digital_v3_topology_and_coarse_keepout_pass"
    ]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
