#!/usr/bin/env python3
"""Slice every actual Gate 9 aperture-frame and keel V3 candidate part."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import slice_gate9_architecture_comparison_v3 as canonical  # noqa: E402


comparison = canonical.comparison
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_V3_DIR = (
    PACKAGE_ROOT
    / "output/gate9-aperture-frame-and-keel-candidate-v3"
)
DEFAULT_COMPARISON_DIR = (
    PACKAGE_ROOT
    / "output/gate9-rear-architecture-comparison-v1"
)
DEFAULT_CONFIG = (
    DEFAULT_COMPARISON_DIR
    / "slicer-review/gate9-mk4s-asa-review.ini"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v3-dir", type=Path, default=DEFAULT_V3_DIR)
    parser.add_argument(
        "--comparison-dir",
        type=Path,
        default=DEFAULT_COMPARISON_DIR,
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--threads", type=int, default=8)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def selected_metrics(
    report: dict[str, Any],
) -> dict[str, Any] | None:
    selected = report.get("selected")
    return selected.get("metrics") if selected else None


def exact_set_totals(
    parts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    metrics = {
        part: selected_metrics(report)
        for part, report in parts.items()
    }
    missing = [
        part for part, value in metrics.items() if value is None
    ]
    if missing:
        return {
            "available": False,
            "missing_selected_slices": missing,
        }

    def total(key: str) -> float:
        return sum(
            float(value[key] or 0.0)
            for value in metrics.values()
            if value is not None
        )

    return {
        "available": True,
        "part_count": len(parts),
        "summation_method": (
            "exact sum of independently searched and sliced left/right "
            "upper shells, left/right lower shells, left/right ears, "
            "rear cassette, and bottom keel"
        ),
        "estimated_filament_g": round(total("filament_g"), 3),
        "estimated_support_filament_g": round(
            total("support_filament_g"), 3
        ),
        "estimated_support_volume_cm3": round(
            total("support_volume_cm3"), 3
        ),
        "estimated_print_time_seconds": round(
            total("estimated_print_time_seconds")
        ),
        "all_parts_pass_margin": all(
            bool(value["passes_xy_margin_and_z_height"])
            for value in metrics.values()
            if value is not None
        ),
        "minimum_xy_margin_mm": min(
            float(value["minimum_xy_margin_mm"])
            for value in metrics.values()
            if value is not None
        ),
    }


def main() -> None:
    args = parse_args()
    v3_dir = args.v3_dir.resolve()
    comparison_dir = args.comparison_dir.resolve()
    config_path = args.config.resolve()
    output_dir = v3_dir / "slicer-review"
    output_dir.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Canonical Gate 9 ASA slicer config missing: {config_path}"
        )
    paths = {
        part: v3_dir / "shells" / f"{part}.stl"
        for part in (
            "left_upper_head",
            "right_upper_head",
            "left_lower_face",
            "right_lower_face",
            "bottom_keel",
            "rear_cassette",
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
        raise FileNotFoundError(
            "Missing V3 candidate STL files: " + ", ".join(missing)
        )
    orientation_counts = {
        "left_upper_head": 2,
        "right_upper_head": 2,
        "left_lower_face": 3,
        "right_lower_face": 3,
        "left_ear": 2,
        "right_ear": 2,
        "bottom_keel": 3,
        "rear_cassette": 3,
    }
    part_reports = {}
    for part in (
        "left_upper_head",
        "right_upper_head",
        "left_lower_face",
        "right_lower_face",
        "left_ear",
        "right_ear",
        "rear_cassette",
        "bottom_keel",
    ):
        part_reports[part] = comparison.slice_part(
            "gate9_v3_actual_parts",
            part,
            paths[part],
            orientation_counts[part],
            output_dir,
            config_path,
            args.threads,
        )
    totals = exact_set_totals(part_reports)
    report = {
        "status": (
            "review-only V3 actual-part slices; not a production G-code "
            "release"
        ),
        "margin_parser_revision": (
            "V3 preserves Custom XY travel while stripping startup purge E"
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
        "limitations": [
            "These slices contain the clean V3 topology frame and keel partition, not final seam flanges, sockets, eye mounts, glow-panel retainers, or fastener pads.",
            "Selected orientations must be repeated after final production geometry is added.",
            "No generated G-code in this namespace is approved for an ASA production print."
        ],
    }
    report_path = (
        output_dir
        / "gate9-aperture-frame-and-keel-v3-slices.json"
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
                        "estimated_print_time_seconds": value[
                            "selected"
                        ]["metrics"]["estimated_print_time_seconds"],
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
