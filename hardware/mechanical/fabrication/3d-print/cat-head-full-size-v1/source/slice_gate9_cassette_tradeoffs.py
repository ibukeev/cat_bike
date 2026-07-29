#!/usr/bin/env python3
"""Slice shallower Gate 9 rear-cassette seam candidates."""

from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import slice_gate9_architecture_comparison_v3 as patched  # noqa: E402


comparison = patched.comparison
COMPARISON_DIR = comparison.DEFAULT_COMPARISON_DIR
OUTPUT_DIR = COMPARISON_DIR / "slicer-review"
CONFIG_PATH = OUTPUT_DIR / "gate9-mk4s-asa-review.ini"
BASE_REPORT = OUTPUT_DIR / "gate9-slicer-comparison.json"
ARCHITECTURES = (
    "rear_cassette_threshold_n35",
    "rear_cassette_threshold_n45",
)


def main() -> None:
    base = json.loads(BASE_REPORT.read_text(encoding="utf-8"))
    shared_ear = base["architectures"]["rear_cassette_full_scale"][
        "parts"
    ]["left_ear"]
    reports = {}
    for architecture in ARCHITECTURES:
        parts = {"left_ear": shared_ear}
        for part, orientation_count in (
            ("left_upper_head", 1),
            ("left_lower_face", 2),
            ("rear_cassette", 3),
        ):
            parts[part] = comparison.slice_part(
                architecture,
                part,
                COMPARISON_DIR
                / "variants"
                / architecture
                / f"{part}.stl",
                orientation_count,
                OUTPUT_DIR,
                CONFIG_PATH,
                8,
            )
        reports[architecture] = {
            "parts": parts,
            "estimated_full_set": comparison.estimated_full_set(
                parts, "rear_cassette"
            ),
        }
    output = {
        "status": "review_only_not_a_production_slice",
        "margin_parser_revision": (
            "V3 preserves Custom XY travel while stripping startup purge E"
        ),
        "architectures": reports,
        "comparison_target": "rear_cassette_full_scale uses -70 mm threshold",
        "limitations": base["limitations"],
    }
    output_path = OUTPUT_DIR / "gate9-cassette-tradeoff-slices.json"
    output_path.write_text(
        json.dumps(output, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "architecture_totals": {
                    name: value["estimated_full_set"]
                    for name, value in reports.items()
                },
                "selected_part_metrics": {
                    name: {
                        part: value["parts"][part]["selected"]["metrics"]
                        for part in (
                            "left_upper_head",
                            "left_lower_face",
                            "rear_cassette",
                        )
                    }
                    for name, value in reports.items()
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
