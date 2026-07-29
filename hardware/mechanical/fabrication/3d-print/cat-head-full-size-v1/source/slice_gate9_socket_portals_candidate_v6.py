#!/usr/bin/env python3
"""Slice the revised V6.1 upper shells and optional socket coupon."""

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
DEFAULT_V6_DIR = PACKAGE_ROOT / "output/gate9-socket-portals-candidate-v6"
DEFAULT_CONFIG = (
    PACKAGE_ROOT
    / "output/gate9-rear-architecture-comparison-v1"
    / "slicer-review/gate9-mk4s-asa-review.ini"
)
DEFAULT_V5_REPORT = (
    PACKAGE_ROOT
    / "output/gate9-complementary-service-parts-candidate-v5"
    / "slicer-review/gate9-complementary-service-parts-v5-slices.json"
)
PART_ORDER = (
    "left_upper_head",
    "right_upper_head",
    "socket_fit_coupon",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v6-dir", type=Path, default=DEFAULT_V6_DIR)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--v5-report",
        type=Path,
        default=DEFAULT_V5_REPORT,
    )
    parser.add_argument("--threads", type=int, default=8)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def selected_totals(
    reports: dict[str, dict],
) -> dict[str, float | int | bool | str]:
    metrics = [
        value["selected"]["metrics"] for value in reports.values()
    ]
    return {
        "available": all(
            value.get("selected") is not None
            for value in reports.values()
        ),
        "part_count": len(reports),
        "summation_method": (
            "exact sum of independently orientation-searched and sliced "
            "left/right V6 upper shells and the socket-fit coupon"
        ),
        "estimated_filament_g": round(
            sum(float(value["filament_g"]) for value in metrics), 3
        ),
        "estimated_support_filament_g": round(
            sum(
                float(value["support_filament_g"])
                for value in metrics
            ),
            3,
        ),
        "estimated_support_volume_cm3": round(
            sum(
                float(value["support_volume_cm3"])
                for value in metrics
            ),
            3,
        ),
        "estimated_print_time_seconds": sum(
            int(value["estimated_print_time_seconds"])
            for value in metrics
        ),
        "all_parts_pass_margin": all(
            bool(value["passes_xy_margin_and_z_height"])
            for value in metrics
        ),
        "minimum_xy_margin_mm": min(
            float(value["minimum_xy_margin_mm"]) for value in metrics
        ),
    }


def main() -> None:
    args = parse_args()
    v6_dir = args.v6_dir.resolve()
    config_path = args.config.resolve()
    v5_report_path = args.v5_report.resolve()
    output_dir = v6_dir / "slicer-review"
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "left_upper_head": v6_dir / "shells/left_upper_head.stl",
        "right_upper_head": v6_dir / "shells/right_upper_head.stl",
        "socket_fit_coupon": (
            v6_dir / "test-coupons/gate9_v6_socket_fit_coupon.stl"
        ),
    }
    missing = [
        str(path.relative_to(REPO_ROOT))
        for path in paths.values()
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(", ".join(missing))
    orientation_counts = {
        "left_upper_head": 3,
        "right_upper_head": 3,
        "socket_fit_coupon": 2,
    }
    part_reports = {
        part: comparison.slice_part(
            "gate9_v6_socket_portals",
            part,
            paths[part],
            orientation_counts[part],
            output_dir,
            config_path,
            args.threads,
        )
        for part in PART_ORDER
    }
    coupon_points = comparison.read_binary_stl_points(
        paths["socket_fit_coupon"]
    )
    flat_rotation = (0.0, 0.0, 0.0)
    flat_dimensions = comparison.rotated_dimensions(
        coupon_points,
        flat_rotation,
    )
    flat_orientation = comparison.Orientation(
        flat_rotation,
        flat_dimensions,
        comparison.orientation_score(flat_dimensions),
    )
    flat_coupon = comparison.slice_orientation(
        paths["socket_fit_coupon"],
        flat_orientation,
        output_dir
        / "gate9_v6_socket_portals"
        / "socket_fit_coupon",
        config_path,
        args.threads,
        0,
    )
    part_reports["socket_fit_coupon"][
        "prescribed_flat_wall_candidate"
    ] = flat_coupon
    if (
        flat_coupon.get("metrics") is not None
        and flat_coupon["metrics"]["passes_xy_margin_and_z_height"]
    ):
        part_reports["socket_fit_coupon"]["selected"] = flat_coupon
        part_reports["socket_fit_coupon"]["selected_candidate_index"] = 0
    totals = selected_totals(part_reports)
    if v5_report_path.exists():
        v5_report = json.loads(
            v5_report_path.read_text(encoding="utf-8")
        )
        current_eight_parts = dict(v5_report["parts"])
        current_eight_parts["left_upper_head"] = part_reports[
            "left_upper_head"
        ]
        current_eight_parts["right_upper_head"] = part_reports[
            "right_upper_head"
        ]
        full_totals = v3.exact_set_totals(current_eight_parts)
        full_totals["summation_method"] = (
            "exact V5 eight-part set with the left and right upper "
            "shell slices replaced by their V6 socket-integrated slices"
        )
    else:
        full_totals = {
            "available": False,
            "reason": f"missing V5 slicer report: {v5_report_path}",
        }
    report = {
        "status": (
            "review-only V6.1 ASA slice feasibility for the two modified "
            "upper shells and optional diagnostic socket coupon; not a production-print release"
        ),
        "printer": "Original Prusa MK4/MK4S 0.4 mm nozzle",
        "material_profile": "Generic ASA architecture review",
        "required_xy_margin_after_brim_mm": (
            comparison.REQUIRED_XY_MARGIN_MM
        ),
        "brim_width_mm": comparison.BRIM_WIDTH_MM,
        "parts": part_reports,
        "exact_three_part_set": totals,
        "exact_current_eight_part_set": full_totals,
        "validation": {
            "both_modified_upper_shells_and_optional_coupon_have_margin_passing_slice": (
                totals["available"]
                and totals["all_parts_pass_margin"]
            ),
            "minimum_margin_meets_requirement": (
                totals["available"]
                and float(totals["minimum_xy_margin_mm"])
                >= comparison.REQUIRED_XY_MARGIN_MM
            ),
            "current_eight_part_set_retains_required_margin": (
                full_totals.get("available", False)
                and full_totals.get("all_parts_pass_margin", False)
                and float(full_totals.get("minimum_xy_margin_mm", -1.0))
                >= comparison.REQUIRED_XY_MARGIN_MM
            ),
        },
        "coupon_decision": [
            "The user accepted bypassing the physical coupon and using the conservative 21.0 mm straight bore.",
            "The 1.0 mm 45-degree lead-in expands the mouth to 23.0 mm while preserving the 32.5 mm outer envelope.",
            "The retained coupon STL is optional diagnostic evidence only if later fit or rattle is rejected.",
            "A thin hidden-face shim is permitted if bolted physical rattle is unacceptable.",
            "Do not drill or cut the final rails from the 158.172 mm reference length."
        ],
        "remaining_production_blockers": [
            "Final rail cut lengths, lower shoes, and anti-crush plugs are unresolved.",
            "Backplate perimeter holes and the complete lamp/steering envelope are unresolved.",
            "Ear, eye, wrapped-panel, and remaining shell-seam gates are unresolved."
        ],
    }
    report_path = output_dir / "gate9-socket-portals-v6-slices.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "validation": report["validation"],
                "exact_three_part_set": totals,
                "exact_current_eight_part_set": full_totals,
                "selected_parts": {
                    part: {
                        "rotation_xyz_degrees": value["selected"][
                            "rotation_xyz_degrees"
                        ],
                        "minimum_xy_margin_mm": value["selected"][
                            "metrics"
                        ]["minimum_xy_margin_mm"],
                        "filament_g": value["selected"]["metrics"][
                            "filament_g"
                        ],
                        "support_filament_g": value["selected"][
                            "metrics"
                        ]["support_filament_g"],
                    }
                    for part, value in part_reports.items()
                },
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        ),
        flush=True,
    )
    if not all(report["validation"].values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
