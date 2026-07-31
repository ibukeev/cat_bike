#!/usr/bin/env python3
"""Real Prusa MK4 Generic ASA slice audit for four updated V10 ear parts."""

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
DEFAULT_V10_DIR = (
    PACKAGE_ROOT / "output/gate9-ear-primary-interface-candidate-v10"
)
DEFAULT_CONFIG = (
    PACKAGE_ROOT
    / "output/gate9-rear-architecture-comparison-v1"
    / "slicer-review/gate9-mk4s-asa-review.ini"
)
DEFAULT_REVIEW = (
    PACKAGE_ROOT / "review/gate9-ear-primary-interface-v10-summary.json"
)
PART_ORDER = (
    "left_upper_head",
    "right_upper_head",
    "left_ear",
    "right_ear",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v10-dir", type=Path, default=DEFAULT_V10_DIR)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--threads", type=int, default=8)
    return parser.parse_args()


def slice_part(
    part: str,
    stl_path: Path,
    output_dir: Path,
    config_path: Path,
    threads: int,
) -> dict:
    points = comparison.read_binary_stl_points(stl_path)
    orientations = v7.vectorized_orientation_search(points, 3)
    candidates = []
    print(
        f"[slice] gate9_v10_primary_ear/{part}: "
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
        "source_stl": str(stl_path.relative_to(REPO_ROOT)),
        "orientation_method": (
            "exact NumPy coarse/refined bounding search followed by real "
            "support/brim-inclusive Prusa MK4 Generic ASA slices"
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
    v10_dir = args.v10_dir.resolve()
    config_path = args.config.resolve()
    review_path = args.review.resolve()
    output_dir = v10_dir / "slicer-review"
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        part: v10_dir / "parts" / f"{part}.stl"
        for part in PART_ORDER
    }
    missing = [
        str(path.relative_to(REPO_ROOT))
        for path in paths.values()
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(", ".join(missing))
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    if not review_path.exists():
        raise FileNotFoundError(review_path)
    parts = {
        part: slice_part(
            part,
            paths[part],
            output_dir,
            config_path,
            args.threads,
        )
        for part in PART_ORDER
    }
    totals = v3.exact_set_totals(parts)
    totals["summation_method"] = (
        "exact sum of independently orientation-searched and real-sliced "
        "left/right V10 upper shells and left/right V10 ears"
    )
    validation = {
        "all_four_v10_ear_interface_parts_have_margin_passing_slice": (
            totals.get("available", False)
            and totals.get("part_count") == 4
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
            "digital V10 support/brim-inclusive Generic ASA feasibility "
            "on Original Prusa MK4/MK4S; not production G-code authorization"
        ),
        "printer": "Original Prusa MK4/MK4S 0.4 mm nozzle",
        "material_profile": "Generic ASA architecture review",
        "required_xy_margin_after_brim_mm": (
            comparison.REQUIRED_XY_MARGIN_MM
        ),
        "brim_width_mm": comparison.BRIM_WIDTH_MM,
        "parts": parts,
        "exact_four_part_set": totals,
        "validation": validation,
    }
    report_path = output_dir / "gate9-v10-primary-ear-slices.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    summary = json.loads(review_path.read_text(encoding="utf-8"))
    summary["prusa_mk4_generic_asa_validation"] = {
        "report": str(report_path.relative_to(REPO_ROOT)),
        "all_parts_pass_xy_margin_and_z_height": all(
            validation.values()
        ),
        "required_minimum_xy_margin_mm": (
            comparison.REQUIRED_XY_MARGIN_MM
        ),
        "observed_minimum_xy_margin_mm": totals.get(
            "minimum_xy_margin_mm"
        ),
        "exact_four_part_set": totals,
        "selected_parts": {
            part: {
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
                "estimated_print_time_seconds": value["selected"][
                    "metrics"
                ]["estimated_print_time_seconds"],
            }
            for part, value in parts.items()
        },
    }
    summary["digital_validation"].update(validation)
    summary["digital_validation"][
        "digital_v10_primary_ear_geometry_and_slice_candidate_pass"
    ] = all(summary["digital_validation"].values())
    review_path.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "validation": validation,
                "exact_four_part_set": totals,
                "selected_parts": summary[
                    "prusa_mk4_generic_asa_validation"
                ]["selected_parts"],
                "report": str(report_path.relative_to(REPO_ROOT)),
                "review": str(review_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        ),
        flush=True,
    )
    if not all(validation.values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
