#!/usr/bin/env python3
"""Slice every distinct part of the mirrored Gate 9 hybrid cassette."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import slice_gate9_architecture_comparison_v3 as patched  # noqa: E402


comparison = patched.comparison
COMPARISON_DIR = comparison.DEFAULT_COMPARISON_DIR
OUTPUT_DIR = COMPARISON_DIR / "slicer-review"
CONFIG_PATH = OUTPUT_DIR / "gate9-mk4s-asa-review.ini"
BASE_REPORT = OUTPUT_DIR / "gate9-slicer-comparison.json"
TRADEOFF_REPORT = OUTPUT_DIR / "gate9-cassette-tradeoff-slices.json"
ARCHITECTURE = (
    "rear_cassette_hybrid_mirrored_upper_n70_lower_panel_pair"
)


def metrics(part: dict[str, Any]) -> dict[str, Any]:
    return part["selected"]["metrics"]


def exact_full_set(parts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    ordered = (
        "left_upper_head",
        "right_upper_head",
        "left_lower_face",
        "right_lower_face",
        "left_ear",
        "right_ear",
        "rear_cassette",
    )
    part_metrics = {part: metrics(parts[part]) for part in ordered}

    def total(key: str) -> float:
        return sum(
            float(part_metrics[part][key] or 0.0) for part in ordered
        )

    return {
        "available": True,
        "estimation_method": (
            "sum of all seven distinct part slices; right ear reuses the "
            "geometrically identical left-ear slice"
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
            bool(
                part_metrics[part][
                    "passes_xy_margin_and_z_height"
                ]
            )
            for part in ordered
        ),
        "minimum_xy_margin_mm": min(
            float(part_metrics[part]["minimum_xy_margin_mm"])
            for part in ordered
        ),
    }


def main() -> None:
    base = json.loads(BASE_REPORT.read_text(encoding="utf-8"))
    tradeoff = json.loads(
        TRADEOFF_REPORT.read_text(encoding="utf-8")
    )
    base_parts = base["architectures"]["rear_cassette_full_scale"][
        "parts"
    ]
    n45_parts = tradeoff["architectures"][
        "rear_cassette_threshold_n45"
    ]["parts"]
    parts: dict[str, Any] = {
        "left_upper_head": base_parts["left_upper_head"],
        "left_lower_face": n45_parts["left_lower_face"],
        "left_ear": base_parts["left_ear"],
        "right_ear": base_parts["left_ear"],
    }
    for part, orientation_count in (
        ("right_upper_head", 2),
        ("right_lower_face", 3),
        ("rear_cassette", 3),
    ):
        parts[part] = comparison.slice_part(
            ARCHITECTURE,
            part,
            COMPARISON_DIR
            / "variants"
            / ARCHITECTURE
            / f"{part}.stl",
            orientation_count,
            OUTPUT_DIR,
            CONFIG_PATH,
            8,
        )
    result = {
        "status": "review_only_not_a_production_slice",
        "architecture": ARCHITECTURE,
        "parts": parts,
        "estimated_full_set": exact_full_set(parts),
        "known_topology_holds": [
            "each upper shell currently has two closed components and requires one broad inboard bridge",
            "the right lower shell currently has three closed components and requires broad inboard bridges",
            "final bridges must respect the rear cassette, rail, shoe, hardware, tool, wiring, sealing, and assembly keep-outs",
        ],
        "limitations": base["limitations"],
    }
    output_path = OUTPUT_DIR / "gate9-hybrid-cassette-slices.json"
    output_path.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "estimated_full_set": result["estimated_full_set"],
                "newly_sliced_parts": {
                    part: metrics(parts[part])
                    for part in (
                        "right_upper_head",
                        "right_lower_face",
                        "rear_cassette",
                    )
                },
                "report": str(
                    output_path.relative_to(comparison.REPO_ROOT)
                ),
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
