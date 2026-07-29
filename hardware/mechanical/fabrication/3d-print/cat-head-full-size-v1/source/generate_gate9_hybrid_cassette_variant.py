#!/usr/bin/env python3
"""Generate the Gate 9 hybrid upper-deep/lower-shallow rear cassette."""

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

import generate_gate1_master as gate1  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate3_structural_shells as gate3  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/gate9-rear-architecture-comparison-v1.json"
)
DEFAULT_OUTPUT = (
    PACKAGE_ROOT / "output/gate9-rear-architecture-comparison-v1"
)
VARIANT_NAME = "rear_cassette_hybrid_upper_n70_lower_n45"
UPPER_THRESHOLD_MM = -70.0
LOWER_THRESHOLD_MM = -45.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return parser.parse_args(args)


def load_repo_json(relative_path: str) -> dict[str, Any]:
    return json.loads(
        (REPO_ROOT / relative_path).read_text(encoding="utf-8")
    )


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    interface = load_repo_json(config["shared_interface_path"])
    gate2_config = load_repo_json(config["source_gate2_config"])
    gate1_config = json.loads(
        gate1.DEFAULT_CONFIG.read_text(encoding="utf-8")
    )
    source_model = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    units = gate1.panel_units(
        source_model,
        gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV),
    )
    source_scale, source_origin, _ = gate1.make_transform(
        gate1.bounds(source_model.vertices),
        float(gate1_config["target_height_mm"]),
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
    transformed_points = [
        gate1.transform_point(vertex, source_scale, source_origin)
        for vertex in model.vertices
    ]
    upper_candidates = comparison.selected_cassette_faces(
        model,
        assignments,
        transformed_points,
        interface,
        UPPER_THRESHOLD_MM,
    )
    lower_candidates = comparison.selected_cassette_faces(
        model,
        assignments,
        transformed_points,
        interface,
        LOWER_THRESHOLD_MM,
    )
    cassette_faces = {
        index
        for index in upper_candidates
        if assignments[index]
        in {"right_upper_head", "left_upper_head"}
    } | {
        index
        for index in lower_candidates
        if assignments[index]
        in {"right_lower_face", "left_lower_face"}
    }

    gate3.clean_scene()
    materials = {
        key: comparison.create_material(
            f"hybrid_{key}",
            color,
            0.36 if key in {"shoe", "tool", "hardware"} else 1.0,
        )
        for key, color in comparison.SECTION_COLORS.items()
    }
    shell_config = config["shell"]
    scale_center = Vector(
        interface["rear_interface_plane"]["center_head_mm"]
    )
    output_dir = args.output_dir.resolve()
    variant_dir = output_dir / "variants" / VARIANT_NAME
    objects: dict[str, bpy.types.Object] = {}
    parts: dict[str, Any] = {}
    for section in (*comparison.BODY_SECTIONS, *comparison.EAR_SECTIONS):
        face_indices = [
            index
            for index, assignment in enumerate(assignments)
            if assignment == section and index not in cassette_faces
        ]
        source_faces = [
            model.faces[index].indices for index in face_indices
        ]
        if section in comparison.BODY_SECTIONS:
            source_faces.extend(
                tuple(face)
                for face in shell_config.get(
                    "bottom_closure_faces", {}
                ).get(section, [])
            )
        obj = comparison.create_shell_object(
            f"{VARIANT_NAME}__{section}",
            source_faces,
            model,
            source_scale,
            source_origin,
            1.0,
            scale_center,
            materials[section],
            shell_config,
        )
        objects[section] = obj
        parts[section] = comparison.object_stats(
            obj,
            shell_config["printer_envelope_mm"],
            int(shell_config["orientation_step_degrees"]),
        )
        comparison.export_stl(obj, variant_dir / f"{section}.stl")

    cassette = comparison.create_shell_object(
        f"{VARIANT_NAME}__rear_cassette",
        [model.faces[index].indices for index in cassette_faces],
        model,
        source_scale,
        source_origin,
        1.0,
        scale_center,
        materials["rear_cassette"],
        shell_config,
    )
    objects["rear_cassette"] = cassette
    parts["rear_cassette"] = comparison.object_stats(
        cassette,
        shell_config["printer_envelope_mm"],
        int(shell_config["orientation_step_degrees"]),
    )
    comparison.export_stl(
        cassette, variant_dir / "rear_cassette.stl"
    )

    metal = comparison.create_interface_envelopes(
        VARIANT_NAME,
        interface,
        config["provisional_collision_envelopes"],
        materials,
    )
    collisions = []
    for metal_key, metal_obj in metal.items():
        for shell_key, shell_obj in objects.items():
            record = comparison.collision_record(metal_obj, shell_obj)
            record["metal_envelope"] = metal_key
            record["shell_part"] = shell_key
            record["classification"] = (
                "interface_contact_or_pass_through_to_design"
                if shell_key == "rear_cassette"
                else "unintended_if_intersecting"
            )
            collisions.append(record)

    blend_path = output_dir / "gate9-hybrid-cassette-variant.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report = {
        "status": "review_only",
        "interface_revision": interface["interface_revision"],
        "variant": VARIANT_NAME,
        "selection_rule": {
            "upper_sections_rear_plane_threshold_mm": UPPER_THRESHOLD_MM,
            "lower_sections_rear_plane_threshold_mm": LOWER_THRESHOLD_MM,
        },
        "cassette_source_face_count": len(cassette_faces),
        "cassette_panel_ids": sorted(
            {
                gate1.canonical_source_panel_id(
                    model.faces[index].group
                )
                for index in cassette_faces
            }
        ),
        "parts": parts,
        "collision_matrix": collisions,
        "unintended_intersection_count": sum(
            1
            for record in collisions
            if record["classification"] == "unintended_if_intersecting"
            and record["intersects"]
        ),
        "blend": str(blend_path.relative_to(REPO_ROOT)),
        "variant_stls": str(variant_dir.relative_to(REPO_ROOT)),
    }
    report_path = output_dir / "gate9-hybrid-cassette-variant.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "variant": VARIANT_NAME,
                "cassette_source_face_count": len(cassette_faces),
                "unintended_intersection_count": report[
                    "unintended_intersection_count"
                ],
                "parts": {
                    part: {
                        "dimensions_mm": stats["dimensions_mm"],
                        "connected_components": stats[
                            "connected_components"
                        ],
                        "boundary_edges": stats["boundary_edges"],
                        "nonmanifold_edges": stats["nonmanifold_edges"],
                    }
                    for part, stats in parts.items()
                },
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
