#!/usr/bin/env python3
"""Generate the mirrored-panel Gate 9 hybrid cassette candidate."""

from __future__ import annotations

import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate9_hybrid_cassette_variant as hybrid  # noqa: E402


original_selected_cassette_faces = (
    hybrid.comparison.selected_cassette_faces
)


def selected_cassette_faces_with_mirrored_lower_pair(
    model,
    assignments,
    transformed_points,
    interface,
    threshold_mm,
):
    selected = original_selected_cassette_faces(
        model,
        assignments,
        transformed_points,
        interface,
        threshold_mm,
    )
    if abs(float(threshold_mm) - hybrid.LOWER_THRESHOLD_MM) < 1e-9:
        for index, face in enumerate(model.faces):
            panel_id = gate1.canonical_source_panel_id(face.group)
            if (
                assignments[index] == "right_lower_face"
                and panel_id in {"TRI030", "TRI040"}
            ):
                selected.add(index)
    return selected


hybrid.VARIANT_NAME = (
    "rear_cassette_hybrid_mirrored_upper_n70_lower_panel_pair"
)
hybrid.comparison.selected_cassette_faces = (
    selected_cassette_faces_with_mirrored_lower_pair
)


if __name__ == "__main__":
    hybrid.main()
