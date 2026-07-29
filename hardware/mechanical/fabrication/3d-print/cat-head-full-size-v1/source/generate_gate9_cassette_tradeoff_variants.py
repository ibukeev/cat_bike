#!/usr/bin/env python3
"""Export shallower Gate 9 cassette variants for slicer tradeoff review."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


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
THRESHOLDS_MM = (-35.0, -45.0)


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

    gate3.clean_scene()
    materials = {
        key: comparison.create_material(
            f"tradeoff_{key}",
            color,
            0.36 if key in {"shoe", "tool", "hardware"} else 1.0,
        )
        for key, color in comparison.SECTION_COLORS.items()
    }
    reports: dict[str, Any] = {}
    all_objects = []
    output_dir = args.output_dir.resolve()
    for threshold in THRESHOLDS_MM:
        name = f"rear_cassette_threshold_n{abs(int(threshold))}"
        objects, report = comparison.create_variant(
            name,
            1.0,
            threshold,
            model,
            assignments,
            source_scale,
            source_origin,
            transformed_points,
            interface,
            config,
            materials,
            output_dir,
        )
        reports[name] = report
        all_objects.extend(objects.values())

    blend_path = output_dir / "gate9-cassette-tradeoff-variants.blend"
    bpy = __import__("bpy")
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report = {
        "status": "review_only",
        "interface_revision": interface["interface_revision"],
        "thresholds_mm": list(THRESHOLDS_MM),
        "variants": reports,
        "blend": str(blend_path.relative_to(REPO_ROOT)),
    }
    report_path = output_dir / "gate9-cassette-tradeoffs.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "variants": {
                    name: {
                        "cassette_source_face_count": value[
                            "cassette_source_face_count"
                        ],
                        "unintended_intersection_count": value[
                            "unintended_intersection_count"
                        ],
                        "part_dimensions_mm": {
                            part: stats["dimensions_mm"]
                            for part, stats in value["parts"].items()
                            if part
                            in {
                                "left_upper_head",
                                "left_lower_face",
                                "rear_cassette",
                            }
                        },
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
