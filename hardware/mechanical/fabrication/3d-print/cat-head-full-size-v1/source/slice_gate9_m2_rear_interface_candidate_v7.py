#!/usr/bin/env python3
"""Slice all eight printed V7 rear-interface parts on the Prusa MK4."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import slice_gate9_aperture_frame_and_keel_candidate_v3 as v3  # noqa: E402


comparison = v3.comparison
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_V7_DIR = PACKAGE_ROOT / "output/gate9-m2-rear-interface-candidate-v7"
DEFAULT_CONFIG = (
    PACKAGE_ROOT
    / "output/gate9-rear-architecture-comparison-v1"
    / "slicer-review/gate9-mk4s-asa-review.ini"
)
PART_ORDER = (
    "left_upper_head",
    "right_upper_head",
    "left_lower_face",
    "right_lower_face",
    "rear_bezel",
    "bottom_keel",
    "left_socket_outer_cap",
    "right_socket_outer_cap",
)

CRITICAL_EXTRA_ORIENTATIONS = {
    "left_lower_face": ((111.0, 30.5, 30.5),),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v7-dir", type=Path, default=DEFAULT_V7_DIR)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--threads", type=int, default=8)
    args = (
        sys.argv[sys.argv.index("--") + 1 :]
        if "--" in sys.argv
        else sys.argv[1:]
    )
    return parser.parse_args(args)


def vectorized_dimensions(
    points: np.ndarray,
    rotation: tuple[float, float, float],
) -> tuple[float, float, float]:
    ax, ay, az = np.radians(rotation)
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)
    x, y, z = points[:, 0], points[:, 1], points[:, 2]
    y1, z1 = y * cx - z * sx, y * sx + z * cx
    x2, z2 = x * cy + z1 * sy, -x * sy + z1 * cy
    x3, y3 = x2 * cz - y1 * sz, x2 * sz + y1 * cz
    return (
        float(np.ptp(x3)),
        float(np.ptp(y3)),
        float(np.ptp(z2)),
    )


def vectorized_orientation_search(
    points: list[tuple[float, float, float]],
    requested_count: int,
) -> list:
    array = np.asarray(points, dtype=np.float64)
    coarse = []
    for ax in range(0, 180, 15):
        for ay in range(0, 180, 15):
            for az in range(0, 180, 15):
                rotation = (float(ax), float(ay), float(az))
                dimensions = vectorized_dimensions(array, rotation)
                coarse.append(
                    comparison.Orientation(
                        rotation,
                        dimensions,
                        comparison.orientation_score(dimensions),
                    )
                )
    seeds = comparison.best_distinct(coarse, 8, 18.0)
    refined_by_rotation = {}
    for seed in seeds:
        for dx in range(-15, 16, 3):
            for dy in range(-15, 16, 3):
                for dz in range(-15, 16, 3):
                    rotation = tuple(
                        (
                            seed.rotation_xyz_degrees[index] + delta
                        )
                        % 180.0
                        for index, delta in enumerate((dx, dy, dz))
                    )
                    if rotation in refined_by_rotation:
                        continue
                    dimensions = vectorized_dimensions(array, rotation)
                    refined_by_rotation[rotation] = comparison.Orientation(
                        rotation,
                        dimensions,
                        comparison.orientation_score(dimensions),
                    )
    fine_seeds = comparison.best_distinct(
        refined_by_rotation.values(),
        12,
        minimum_angle_distance=6.0,
    )
    fine_by_rotation = {}
    for seed in fine_seeds:
        for dx in range(-4, 5):
            for dy in range(-4, 5):
                for dz in range(-4, 5):
                    rotation = tuple(
                        (
                            seed.rotation_xyz_degrees[index] + delta
                        )
                        % 180.0
                        for index, delta in enumerate((dx, dy, dz))
                    )
                    if rotation in fine_by_rotation:
                        continue
                    dimensions = vectorized_dimensions(array, rotation)
                    fine_by_rotation[rotation] = comparison.Orientation(
                        rotation,
                        dimensions,
                        comparison.orientation_score(dimensions),
                    )
    return comparison.best_distinct(
        fine_by_rotation.values(),
        requested_count,
        minimum_angle_distance=12.0,
    )


def slice_vectorized(
    part: str,
    stl_path: Path,
    output_dir: Path,
    config_path: Path,
    threads: int,
) -> dict:
    points = comparison.read_binary_stl_points(stl_path)
    orientations = vectorized_orientation_search(points, 3)
    for rotation in CRITICAL_EXTRA_ORIENTATIONS.get(part, ()):
        dimensions = comparison.rotated_dimensions(points, rotation)
        orientations.append(
            comparison.Orientation(
                rotation,
                dimensions,
                comparison.orientation_score(dimensions),
            )
        )
    candidates = []
    print(
        f"[slice] gate9_v7_m2_rear_interface/{part}: "
        f"{len(orientations)} exact vectorized candidates",
        flush=True,
    )
    for index, orientation in enumerate(orientations, start=1):
        print(
            f"[slice] gate9_v7_m2_rear_interface/{part}: "
            f"candidate {index}/{len(orientations)} "
            f"{orientation.rotation_xyz_degrees} "
            f"score={orientation.envelope_score:.4f}",
            flush=True,
        )
        candidates.append(
            comparison.slice_orientation(
                stl_path,
                orientation,
                output_dir / "gate9_v7_m2_rear_interface" / part,
                config_path,
                threads,
                index,
            )
        )
    selected = comparison.choose_best_slice(candidates)
    return {
        "source_stl": str(stl_path.relative_to(REPO_ROOT)),
        "orientation_method": (
            "exact NumPy coarse/refined bounding search over all unique "
            "STL vertices followed by real Prusa support/brim slices"
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
    v7_dir = args.v7_dir.resolve()
    config_path = args.config.resolve()
    output_dir = v7_dir / "slicer-review"
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        part: v7_dir / "shells" / f"{part}.stl"
        for part in (
            "left_upper_head",
            "right_upper_head",
            "left_lower_face",
            "right_lower_face",
            "rear_bezel",
            "bottom_keel",
        )
    }
    paths["left_socket_outer_cap"] = (
        v7_dir / "socket-caps/left_socket_outer_cap.stl"
    )
    paths["right_socket_outer_cap"] = (
        v7_dir / "socket-caps/right_socket_outer_cap.stl"
    )
    missing = [
        str(path.relative_to(REPO_ROOT))
        for path in paths.values()
        if not path.exists()
    ]
    if missing:
        raise FileNotFoundError(", ".join(missing))
    if not config_path.exists():
        raise FileNotFoundError(config_path)

    part_reports = {
        part: slice_vectorized(
            part,
            paths[part],
            output_dir,
            config_path,
            args.threads,
        )
        for part in PART_ORDER
    }
    totals = v3.exact_set_totals(part_reports)
    totals["summation_method"] = (
        "exact sum of independently orientation-searched and sliced "
        "six V7 shell/service parts plus two removable socket caps"
    )
    validation = {
        "all_eight_v7_parts_have_margin_passing_slice": (
            totals.get("available", False)
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
            "digital V7 Generic ASA slice feasibility on Original Prusa "
            "MK4/MK4S; physical rear-interface coupon and complete head "
            "release remain required before production ASA printing"
        ),
        "printer": "Original Prusa MK4/MK4S 0.4 mm nozzle",
        "material_profile": "Generic ASA architecture review",
        "orientation_method": (
            "exact vectorized coarse/refined geometry search; all recorded "
            "candidates are actual support/brim-inclusive Prusa slices"
        ),
        "required_xy_margin_after_brim_mm": (
            comparison.REQUIRED_XY_MARGIN_MM
        ),
        "brim_width_mm": comparison.BRIM_WIDTH_MM,
        "parts": part_reports,
        "exact_eight_part_set": totals,
        "validation": validation,
    }
    report_path = output_dir / "gate9-v7-m2-rear-interface-slices.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "validation": validation,
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
    if not all(validation.values()):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
