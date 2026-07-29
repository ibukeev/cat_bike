#!/usr/bin/env python3
"""Run the Gate 9 V1 comparison with the Gate 1 height owner restored.

The V1 review generator inherited Gate 3's stale assumption that
``target_height_mm`` lived in Gate 2.  Keep that failed review script as an
audit artifact and inject the canonical Gate 1 value without modifying any
historical source or output.
"""

from __future__ import annotations

import json

import generate_gate1_master as gate1
import generate_gate9_rear_architecture_comparison as comparison


original_load_repo_json = comparison.load_repo_json


def load_repo_json_with_gate1_height(relative_path: str) -> dict:
    data = original_load_repo_json(relative_path)
    if relative_path == (
        "hardware/mechanical/fabrication/3d-print/"
        "cat-head-full-size-v1/config/gate2-section-layout.json"
    ):
        gate1_config = json.loads(
            gate1.DEFAULT_CONFIG.read_text(encoding="utf-8")
        )
        data["target_height_mm"] = float(
            gate1_config["target_height_mm"]
        )
    return data


comparison.load_repo_json = load_repo_json_with_gate1_height


if __name__ == "__main__":
    comparison.main()
