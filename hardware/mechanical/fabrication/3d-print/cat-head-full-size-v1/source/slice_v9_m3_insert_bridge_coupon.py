#!/usr/bin/env python3
"""Real Prusa MK4 Generic ASA slice audit for the two-part V9 coupon."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import slice_gate9_aperture_frame_and_keel_candidate_v3 as v3  # noqa: E402


comparison = v3.comparison
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_COUPON_DIR = (
    PACKAGE_ROOT / "output/v9-m3-insert-bridge-coupon"
)
DEFAULT_SLICER_CONFIG = (
    PACKAGE_ROOT
    / "output/gate9-rear-architecture-comparison-v1"
    / "slicer-review/gate9-mk4s-asa-review.ini"
)
DEFAULT_REVIEW = (
    PACKAGE_ROOT / "review/v9-m3-insert-bridge-coupon-summary.json"
)
PART_ORDER = (
    "v9_m3_insert_coupon_base",
    "v9_m3_insert_coupon_bridge",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--coupon-dir",
        type=Path,
        default=DEFAULT_COUPON_DIR,
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_SLICER_CONFIG,
    )
    parser.add_argument("--review", type=Path, default=DEFAULT_REVIEW)
    parser.add_argument("--threads", type=int, default=8)
    return parser.parse_args()


def flat_slice(
    part: str,
    stl_path: Path,
    output_dir: Path,
    config_path: Path,
    threads: int,
) -> dict:
    points = comparison.read_binary_stl_points(stl_path)
    rotation = (0.0, 0.0, 0.0)
    dimensions = comparison.rotated_dimensions(points, rotation)
    orientation = comparison.Orientation(
        rotation,
        dimensions,
        comparison.orientation_score(dimensions),
    )
    candidate = comparison.slice_orientation(
        stl_path,
        orientation,
        output_dir / part,
        config_path,
        threads,
        1,
    )
    selected = comparison.choose_best_slice([candidate])
    return {
        "source_stl": str(stl_path.relative_to(REPO_ROOT)),
        "orientation_method": (
            "prescribed flat coupon orientation; real support/brim-"
            "inclusive Prusa MK4 Generic ASA slice"
        ),
        "orientation_candidates": [candidate],
        "selected_candidate_index": (
            selected["candidate_index"] if selected else None
        ),
        "selected": selected,
        "has_margin_passing_candidate": bool(
            selected
            and selected.get("metrics")
            and selected["metrics"]["passes_xy_margin_and_z_height"]
        ),
    }


def main() -> None:
    args = parse_args()
    coupon_dir = args.coupon_dir.resolve()
    config_path = args.config.resolve()
    review_path = args.review.resolve()
    output_dir = coupon_dir / "slicer-review"
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        part: coupon_dir / "parts" / f"{part}.stl"
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
        part: flat_slice(
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
        "exact sum of the prescribed flat real Prusa slices for the "
        "three-station insert base and matching two-hole bridge"
    )
    validation = {
        "both_coupon_parts_have_real_prusa_slices": (
            totals.get("available", False)
            and totals.get("part_count") == 2
        ),
        "both_coupon_parts_pass_xy_margin_and_z_height": (
            totals.get("available", False)
            and totals.get("all_parts_pass_margin", False)
        ),
        "coupon_prints_flat_without_generated_support": (
            totals.get("available", False)
            and float(totals.get("estimated_support_filament_g", -1.0))
            == 0.0
            and float(totals.get("estimated_support_volume_cm3", -1.0))
            == 0.0
        ),
    }
    report = {
        "status": (
            "physical coupon G-code feasibility only; the actual insert "
            "test still selects the production pilot"
        ),
        "printer": "Original Prusa MK4/MK4S 0.4 mm nozzle",
        "material_profile": "Generic ASA architecture review",
        "required_xy_margin_after_brim_mm": (
            comparison.REQUIRED_XY_MARGIN_MM
        ),
        "brim_width_mm": comparison.BRIM_WIDTH_MM,
        "parts": parts,
        "exact_two_part_set": totals,
        "validation": validation,
    }
    report_path = output_dir / "v9-m3-insert-bridge-coupon-slices.json"
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
        "exact_two_part_set": totals,
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
        "digital_coupon_geometry_and_slice_candidate_pass"
    ] = all(summary["digital_validation"].values())
    review_path.write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "validation": validation,
                "exact_two_part_set": totals,
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
