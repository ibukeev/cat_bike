#!/usr/bin/env python3
"""Real Prusa MK4 ASA/PETG slice audit for seven updated V11 parts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import slice_gate9_aperture_frame_and_keel_candidate_v3 as v3  # noqa: E402
import slice_gate9_m2_rear_interface_candidate_v7 as v7  # noqa: E402


comparison = v7.comparison
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_V11_DIR = (
    PACKAGE_ROOT / "output/gate9-under-ear-insert-antiflap-candidate-v11"
)
DEFAULT_ASA_CONFIG = (
    PACKAGE_ROOT
    / "output/gate9-rear-architecture-comparison-v1"
    / "slicer-review/gate9-mk4s-asa-review.ini"
)
DEFAULT_REVIEW = (
    PACKAGE_ROOT / "review/gate9-under-ear-insert-antiflap-v11-summary.json"
)
PART_MATERIAL = {
    "left_upper_head": "ASA",
    "right_upper_head": "ASA",
    "left_ear": "ASA",
    "right_ear": "ASA",
    "rear_bezel": "ASA",
    "left_under_ear_insert": "PETG",
    "right_under_ear_insert": "PETG",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v11-dir", type=Path, default=DEFAULT_V11_DIR)
    parser.add_argument("--asa-config", type=Path, default=DEFAULT_ASA_CONFIG)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--threads", type=int, default=8)
    return parser.parse_args()


def make_petg_config(asa_path: Path, output_path: Path) -> Path:
    text = asa_path.read_text(encoding="utf-8")
    replacements = {
        "bed_temperature = 105": "bed_temperature = 85",
        "filament_density = 1.07": "filament_density = 1.27",
        "filament_max_volumetric_speed = 11": (
            "filament_max_volumetric_speed = 8"
        ),
        'filament_settings_id = "Generic ASA architecture review"': (
            'filament_settings_id = "Generic PETG architecture review"'
        ),
        "filament_type = ASA": "filament_type = PETG",
        "first_layer_bed_temperature = 105": (
            "first_layer_bed_temperature = 85"
        ),
        "first_layer_temperature = 260": "first_layer_temperature = 240",
        "max_fan_speed = 20": "max_fan_speed = 50",
        "min_fan_speed = 0": "min_fan_speed = 30",
        "temperature = 260": "temperature = 240",
    }
    lines = text.splitlines()
    for source, target in replacements.items():
        matches = [index for index, line in enumerate(lines) if line == source]
        if len(matches) != 1:
            raise ValueError(f"PETG profile source setting is not unique: {source}")
        lines[matches[0]] = target
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output_path


def slice_part(
    part: str,
    stl_path: Path,
    output_dir: Path,
    config_path: Path,
    threads: int,
) -> dict:
    orientations = v7.vectorized_orientation_search(
        comparison.read_binary_stl_points(stl_path),
        3,
    )
    candidates = []
    print(
        f"[slice] gate9_v11/{part} ({PART_MATERIAL[part]}): "
        f"{len(orientations)} real Prusa candidates",
        flush=True,
    )
    for index, orientation in enumerate(orientations, start=1):
        candidates.append(
            comparison.slice_orientation(
                stl_path,
                orientation,
                output_dir / part,
                config_path,
                threads,
                index,
            )
        )
    selected = comparison.choose_best_slice(candidates)
    return {
        "material": PART_MATERIAL[part],
        "source_stl": str(stl_path.relative_to(REPO_ROOT)),
        "orientation_method": (
            "exact NumPy coarse/refined bounding search followed by real "
            "support/brim-inclusive Prusa MK4 slices"
        ),
        "orientation_candidates": candidates,
        "selected_candidate_index": (
            selected["candidate_index"] if selected else None
        ),
        "selected": selected,
        "has_margin_passing_candidate": any(
            candidate.get("metrics", {}).get(
                "passes_xy_margin_and_z_height", False
            )
            if candidate.get("metrics")
            else False
            for candidate in candidates
        ),
    }


def main() -> None:
    args = parse_args()
    v11_dir = args.v11_dir.resolve()
    asa_config = args.asa_config.resolve()
    review_path = args.review.resolve()
    output_dir = v11_dir / "slicer-review"
    output_dir.mkdir(parents=True, exist_ok=True)
    petg_config = make_petg_config(
        asa_config,
        output_dir / "gate9-mk4s-petg-review.ini",
    )
    paths = {
        part: v11_dir / "parts" / f"{part}.stl"
        for part in PART_MATERIAL
    }
    missing = [str(path) for path in paths.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(", ".join(missing))
    parts = {
        part: slice_part(
            part,
            paths[part],
            output_dir,
            asa_config if material == "ASA" else petg_config,
            args.threads,
        )
        for part, material in PART_MATERIAL.items()
    }
    totals = v3.exact_set_totals(parts)
    totals["summation_method"] = (
        "exact sum of independently orientation-searched and real-sliced "
        "five ASA shell parts and two PETG inserts"
    )
    validation = {
        "all_seven_v11_parts_have_margin_passing_real_slice": (
            totals.get("available", False)
            and totals.get("part_count") == 7
            and totals.get("all_parts_pass_margin", False)
        ),
        "minimum_post_brim_xy_margin_is_at_least_10mm": (
            totals.get("available", False)
            and float(totals.get("minimum_xy_margin_mm", -1.0))
            >= comparison.REQUIRED_XY_MARGIN_MM
        ),
    }
    report = {
        "status": (
            "digital V11 support/brim-inclusive Generic ASA/PETG feasibility "
            "on Original Prusa MK4/MK4S; not production G-code authorization"
        ),
        "printer": "Original Prusa MK4/MK4S 0.4 mm nozzle",
        "material_profiles": {
            "ASA": "Generic ASA architecture review",
            "PETG": "Generic PETG architecture review",
        },
        "required_xy_margin_after_brim_mm": comparison.REQUIRED_XY_MARGIN_MM,
        "brim_width_mm": comparison.BRIM_WIDTH_MM,
        "parts": parts,
        "exact_seven_part_set": totals,
        "validation": validation,
    }
    report_path = output_dir / "gate9-v11-under-ear-antiflap-slices.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = json.loads(review_path.read_text(encoding="utf-8"))
    summary["prusa_mk4_asa_petg_validation"] = {
        "report": str(report_path.relative_to(REPO_ROOT)),
        "all_parts_pass_xy_margin_and_z_height": all(validation.values()),
        "required_minimum_xy_margin_mm": comparison.REQUIRED_XY_MARGIN_MM,
        "observed_minimum_xy_margin_mm": totals.get("minimum_xy_margin_mm"),
        "exact_seven_part_set": totals,
        "selected_parts": {
            part: {
                "material": value["material"],
                "rotation_xyz_degrees": value["selected"][
                    "rotation_xyz_degrees"
                ],
                "minimum_xy_margin_mm": value["selected"]["metrics"][
                    "minimum_xy_margin_mm"
                ],
                "filament_g": value["selected"]["metrics"]["filament_g"],
                "support_filament_g": value["selected"]["metrics"][
                    "support_filament_g"
                ],
                "support_volume_cm3": value["selected"]["metrics"][
                    "support_volume_cm3"
                ],
                "estimated_print_time_seconds": value["selected"]["metrics"][
                    "estimated_print_time_seconds"
                ],
            }
            for part, value in parts.items()
            if value["selected"] is not None
        },
    }
    summary["digital_validation"].update(validation)
    summary["digital_validation"][
        "digital_v11_geometry_and_real_slice_candidate_pass"
    ] = all(summary["digital_validation"].values())
    slice_hold = (
        "Real support/brim-inclusive Prusa MK4 PETG/ASA slicing must pass "
        "for all seven updated V11 parts."
    )
    if all(validation.values()):
        summary["remaining_release_holds"] = [
            hold
            for hold in summary["remaining_release_holds"]
            if not hold.startswith("Real support/brim-inclusive Prusa MK4")
        ]
        summary["completed_release_checks"] = [
            "All seven updated V11 meshes pass closed-manifold topology and "
            "seated/service clearance validation.",
            "All seven updated V11 parts pass real support/brim-inclusive "
            "Prusa MK4 ASA/PETG slicing with the required post-brim XY margin.",
        ]
    else:
        if slice_hold not in summary["remaining_release_holds"]:
            summary["remaining_release_holds"].append(slice_hold)
        summary.pop("completed_release_checks", None)
    review_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "validation": validation,
                "exact_seven_part_set": totals,
                "selected_parts": summary["prusa_mk4_asa_petg_validation"][
                    "selected_parts"
                ],
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        ),
        flush=True,
    )
    if not all(validation.values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
