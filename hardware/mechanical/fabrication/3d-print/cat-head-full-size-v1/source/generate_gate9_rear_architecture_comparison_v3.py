#!/usr/bin/env python3
"""Run the Gate 9 comparison with canonical Gate 1 height ownership."""

from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate9_rear_architecture_comparison as comparison  # noqa: E402


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
