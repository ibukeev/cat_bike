#!/usr/bin/env python3
"""Evaluate a separate bottom-keel partition for the Gate 9 body.

The review candidate moves the two manually split MANQ008 bottom-center facets
and the two synthetic front closure triangles out of the lower face shells and
into one narrow underside service part.  It does not approve that architecture;
it measures whether the partition removes the lower-shell point contacts
without compromising the selected rear cassette or metal interface.
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

import analyze_gate9_selected_bridge_sites as audit  # noqa: E402
import generate_gate1_master as gate1  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate3_structural_shells as gate3  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/gate9-rear-architecture-comparison-v1.json"
)
DEFAULT_OUTPUT = (
    PACKAGE_ROOT / "output/gate9-bottom-keel-partition-candidate"
)
KEEL_SOURCE_FACE_INDICES = (109, 110)
LOWER_PARTS = ("left_lower_face", "right_lower_face")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def build_context(
    config: dict[str, Any], interface: dict[str, Any]
) -> dict[str, Any]:
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
        config["variants"]["rear_cassette_full_scale"][
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
    return {
        "model": model,
        "assignments": assignments,
        "scale": scale,
        "origin": origin,
        "transformed": transformed,
        "cassette_faces": cassette_faces,
        "scale_center": Vector(
            interface["rear_interface_plane"]["center_head_mm"]
        ),
    }


def create_shell(
    name: str,
    source_faces: list[tuple[int, ...]],
    context: dict[str, Any],
    config: dict[str, Any],
    material: bpy.types.Material,
) -> bpy.types.Object:
    return comparison.create_shell_object(
        name,
        source_faces,
        context["model"],
        context["scale"],
        context["origin"],
        1.0,
        context["scale_center"],
        material,
        config["shell"],
    )


def part_stats(
    obj: bpy.types.Object, config: dict[str, Any]
) -> dict[str, Any]:
    stats = comparison.object_stats(
        obj,
        config["shell"]["printer_envelope_mm"],
        int(config["shell"]["orientation_step_degrees"]),
    )
    stats["component_vertex_counts"] = [
        len(component) for component in gate5.components(obj)
    ]
    return stats


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    interface = json.loads(
        (REPO_ROOT / config["shared_interface_path"]).read_text(
            encoding="utf-8"
        )
    )
    output_dir = args.output_dir.resolve()
    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    (output_dir / "parts").mkdir(parents=True, exist_ok=True)
    context = build_context(config, interface)
    gate3.clean_scene()
    materials = {
        "left_lower_face": comparison.create_material(
            "keel_left_lower", "#2F70BB"
        ),
        "right_lower_face": comparison.create_material(
            "keel_right_lower", "#235FA7"
        ),
        "bottom_keel": comparison.create_material(
            "bottom_keel", "#31A67C"
        ),
        "rear_cassette": comparison.create_material(
            "keel_cassette", "#E59735"
        ),
    }
    parts: dict[str, bpy.types.Object] = {}
    reports: dict[str, Any] = {}
    for part in LOWER_PARTS:
        face_indices = [
            index
            for index, assignment in enumerate(context["assignments"])
            if assignment == part
            and index not in context["cassette_faces"]
            and index not in KEEL_SOURCE_FACE_INDICES
        ]
        obj = create_shell(
            f"keel_candidate__{part}",
            [
                tuple(context["model"].faces[index].indices)
                for index in face_indices
            ],
            context,
            config,
            materials[part],
        )
        parts[part] = obj
        reports[part] = part_stats(obj, config)
        comparison.export_stl(
            obj, output_dir / "parts" / f"{part}.stl"
        )

    closure_faces = [
        tuple(face)
        for face in config["shell"]["bottom_closure_faces"].values()
    ]
    keel = create_shell(
        "keel_candidate__bottom_keel",
        [
            *[
                tuple(context["model"].faces[index].indices)
                for index in KEEL_SOURCE_FACE_INDICES
            ],
            *closure_faces,
        ],
        context,
        config,
        materials["bottom_keel"],
    )
    parts["bottom_keel"] = keel
    reports["bottom_keel"] = part_stats(keel, config)
    comparison.export_stl(
        keel, output_dir / "parts" / "bottom_keel.stl"
    )

    cassette = create_shell(
        "keel_candidate__rear_cassette",
        [
            tuple(context["model"].faces[index].indices)
            for index in context["cassette_faces"]
        ],
        context,
        config,
        materials["rear_cassette"],
    )
    parts["rear_cassette"] = cassette
    reports["rear_cassette"] = part_stats(cassette, config)

    envelope_materials = {
        key: comparison.create_material(
            f"keel_candidate_{key}", color, 0.35
        )
        for key, color in comparison.SECTION_COLORS.items()
        if key in {"backplate", "rail", "shoe", "tool", "hardware"}
    }
    metal = comparison.create_interface_envelopes(
        "keel_candidate",
        interface,
        config["provisional_collision_envelopes"],
        envelope_materials,
    )
    keel_collisions = {
        "rear_cassette": comparison.collision_record(keel, cassette),
        "metal_envelopes": {
            name: comparison.collision_record(keel, envelope)
            for name, envelope in metal.items()
        },
    }

    camera = audit.configure_workbench_render()
    all_objects = [*parts.values(), *metal.values()]
    audit.render_part(
        "bottom_keel__assembled_lower_and_cassette",
        [
            parts["left_lower_face"],
            parts["right_lower_face"],
            keel,
            cassette,
        ],
        all_objects,
        output_dir,
        camera,
    )
    audit.render_part(
        "bottom_keel__isolated",
        [keel],
        all_objects,
        output_dir,
        camera,
    )
    for obj in all_objects:
        obj.hide_render = False
        obj.hide_viewport = False
    blend_path = output_dir / "gate9-bottom-keel-partition-candidate.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": "review_only_bottom_keel_partition_candidate",
        "interface_revision": interface["interface_revision"],
        "rear_cassette_threshold_mm": float(
            config["variants"]["rear_cassette_full_scale"][
                "rear_cassette_threshold_mm"
            ]
        ),
        "ownership_change": {
            "bottom_keel_source_face_indices": list(
                KEEL_SOURCE_FACE_INDICES
            ),
            "bottom_keel_source_panel_ids": [
                gate1.canonical_source_panel_id(
                    context["model"].faces[index].group
                )
                for index in KEEL_SOURCE_FACE_INDICES
            ],
            "bottom_closure_faces": closure_faces,
            "meaning": (
                "Move the point-connected bottom-center facets and synthetic "
                "closure triangles out of both lower face shells and into one "
                "separately serviceable underside part."
            ),
        },
        "parts": reports,
        "bottom_keel_collisions": keel_collisions,
        "validation": {
            "both_lower_shells_drop_to_two_pre_frame_components": all(
                reports[part]["connected_components"] == 2
                for part in LOWER_PARTS
            ),
            "bottom_keel_is_one_closed_manifold_component": (
                reports["bottom_keel"]["connected_components"] == 1
                and reports["bottom_keel"]["boundary_edges"] == 0
                and reports["bottom_keel"]["nonmanifold_edges"] == 0
            ),
            "bottom_keel_clears_metal_envelopes": all(
                not collision["intersects"]
                for collision in keel_collisions[
                    "metal_envelopes"
                ].values()
            ),
            "cassette_contact_requires_seam_design": (
                keel_collisions["rear_cassette"]["intersects"]
            ),
        },
        "holds": [
            "The two lower shells still require the recessed glow-aperture frame to connect their remaining two components.",
            "The bottom keel needs explicit complementary seams, alignment, fasteners, drainage, wiring access, and an assembly/removal path.",
            "The keel/cassette boundary must be designed rather than accepted as overlapping review geometry.",
            "All actual candidate parts must be sliced before the partition can be selected."
        ],
        "generated_review_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "parts": str((output_dir / "parts").relative_to(REPO_ROOT)),
            "renders": str(
                (output_dir / "renders").relative_to(REPO_ROOT)
            ),
        },
    }
    report_path = (
        output_dir / "gate9-bottom-keel-partition-candidate.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "validation": report["validation"],
                "parts": {
                    name: {
                        "components": value["connected_components"],
                        "dimensions_mm": value["dimensions_mm"],
                        "volume_mm3": value["volume_mm3"],
                    }
                    for name, value in reports.items()
                },
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
