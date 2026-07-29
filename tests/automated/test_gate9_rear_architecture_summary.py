"""Regression checks for the selected Gate 9 rear architecture."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/"
    "cat-head-full-size-v1/review/"
    "gate9-rear-architecture-summary-v1.json"
)
INTERFACE_PATH = (
    REPO_ROOT
    / "hardware/mechanical/interfaces/"
    "cat-head-shell-aluminum-interface-v03.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_gate9_selection_remains_full_size_and_on_frozen_interface() -> None:
    summary = load_json(SUMMARY_PATH)
    interface = load_json(INTERFACE_PATH)
    selected = summary["selected_architecture"]

    assert selected["name"] == "rear_cassette_full_scale"
    assert selected["head_height_mm"] == 330.0
    assert selected["uniform_scale"] == 1.0
    assert selected["upper_and_lower_rear_plane_threshold_mm"] == -70.0
    assert selected["interface_revision"] == interface["interface_revision"]
    assert selected["lower_rail_target_x_mm"] == [-40.0, 40.0]


def test_selected_cassette_beats_retained_support_and_time() -> None:
    summary = load_json(SUMMARY_PATH)
    architectures = summary["slicer_comparison"]["architectures"]
    retained = architectures["retained_full_scale"]
    selected = architectures["rear_cassette_full_scale"]

    assert (
        selected["estimated_print_time_seconds"]
        < retained["estimated_print_time_seconds"]
    )
    assert (
        selected["estimated_filament_g"]
        < retained["estimated_filament_g"]
    )
    assert (
        selected["estimated_support_filament_g"]
        < retained["estimated_support_filament_g"]
    )
    assert (
        selected["estimated_support_volume_cm3"]
        < retained["estimated_support_volume_cm3"]
    )


def test_selected_cassette_keeps_required_post_brim_margin() -> None:
    summary = load_json(SUMMARY_PATH)
    slicer = summary["slicer_comparison"]
    selected = slicer["architectures"]["rear_cassette_full_scale"]

    assert (
        selected["minimum_xy_margin_mm"]
        >= slicer["required_xy_margin_after_brim_mm"]
    )
    assert "V3" in slicer["canonical_margin_parser"]


def test_production_topology_hold_is_explicit() -> None:
    summary = load_json(SUMMARY_PATH)
    topology = summary["selected_raw_topology"]

    assert topology["rear_cassette_connected_components"] == 1
    assert topology["each_ear_connected_components"] == 1
    assert topology["each_upper_shell_connected_components"] > 1
    assert topology["each_lower_shell_connected_components"] > 1
    assert "exactly one connected" in topology["production_requirement"]


def test_coarse_metal_envelope_review_has_no_unintended_intersections() -> None:
    summary = load_json(SUMMARY_PATH)
    collision = summary["coarse_collision_review"]

    assert collision["unintended_intersection_count"] == 0
    assert collision["raw_lower_shoe_envelope_mm"] == [30.0, 30.0, 40.0]
