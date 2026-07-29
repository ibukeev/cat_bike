#!/usr/bin/env python3
"""Slice all eight actual parts from the Gate 9 V5 review candidate."""

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
DEFAULT_V5_DIR = (
    PACKAGE_ROOT / "output/gate9-complementary-service-parts-candidate-v5"
)
DEFAULT_COMPARISON_DIR = (
    PACKAGE_ROOT / "output/gate9-rear-architecture-comparison-v1"
)
DEFAULT_CONFIG = (
    DEFAULT_COMPARISON_DIR
    / "slicer-review/gate9-mk4s-asa-review.ini"
)
PART_ORDER = (
    "left_upper_head",
    "right_upper_head",
    "left_lower_face",
    "right_lower_face",
    "left_ear",
    "right_ear",
    "rear_bezel",
    "bottom_keel",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v5-dir", type=Path, default=DEFAULT_V5_DIR)
    parser.add_argument(
        "--comparison-dir",
        type=Path,
        default=DEFAULT_COMPARISON_DIR,
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--threads", type=int, default=8)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def main() -> None:
    args = parse_args()
    v5_dir = args.v5_dir.resolve()
    comparison_dir = args.comparison_dir.resolve()
    config_path = args.config.resolve()
    output_dir = v5_dir / "slicer-review"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        raise FileNotFoundError(config_path)
    paths = {
        part: v5_dir / "shells" / f"{part}.stl"
        for part in (
            "left_upper_head",
            "right_upper_head",
            "left_lower_face",
            "right_lower_face",
            "bottom_keel",
            "rear_bezel",
        )
    }
    for ear in ("left_ear", "right_ear"):
        paths[ear] = (
            comparison_dir
            / "variants/rear_cassette_full_scale"
            / f"{ear}.stl"
        )
    missing = [
        str(path.relative_to(REPO_ROOT))
        for path in paths.values()
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(", ".join(missing))
    orientation_counts = {
        "left_upper_head": 2,
        "right_upper_head": 2,
        "left_lower_face": 3,
        "right_lower_face": 3,
        "left_ear": 2,
        "right_ear": 2,
        "bottom_keel": 3,
        "rear_bezel": 3,
    }
    part_reports = {
        part: comparison.slice_part(
            "gate9_v5_complementary_service_parts",
            part,
            paths[part],
            orientation_counts[part],
            output_dir,
            config_path,
            args.threads,
        )
        for part in PART_ORDER
    }
    totals = v3.exact_set_totals(part_reports)
    totals["summation_method"] = totals["summation_method"].replace(
        "rear cassette",
        "rear bezel",
    )
    report = {
        "status": (
            "review-only V5 ASA slice feasibility; the complementary "
            "service-parts digital gate passed, but unresolved production "
            "blocks still prohibit a full-head print"
        ),
        "printer": "Original Prusa MK4/MK4S 0.4 mm nozzle",
        "material_profile": "Generic ASA architecture review",
        "required_xy_margin_after_brim_mm": (
            comparison.REQUIRED_XY_MARGIN_MM
        ),
        "brim_width_mm": comparison.BRIM_WIDTH_MM,
        "parts": part_reports,
        "exact_eight_part_set": totals,
        "validation": {
            "all_eight_parts_have_margin_passing_slice": (
                totals.get("available", False)
                and totals.get("all_parts_pass_margin", False)
            ),
            "minimum_margin_meets_requirement": (
                totals.get("available", False)
                and float(totals.get("minimum_xy_margin_mm", -1.0))
                >= comparison.REQUIRED_XY_MARGIN_MM
            ),
        },
        "production_blockers": [
            "Real 20.5 mm rail sockets and revised front/top portals are not integrated.",
            "The two-bolt ear interface is not integrated into the V5 body shells.",
            "The connected eye module and wrapped glow-panel interfaces remain unresolved.",
            "Final inter-shell seams, tool access, and complete hardware sweeps remain unresolved.",
            "Physical seam, socket, eye, and panel coupons are required before a full ASA print.",
            "This report proves printer-envelope and slicer feasibility only."
        ],
    }
    report_path = (
        output_dir
        / "gate9-complementary-service-parts-v5-slices.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "validation": report["validation"],
                "exact_eight_part_set": totals,
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
