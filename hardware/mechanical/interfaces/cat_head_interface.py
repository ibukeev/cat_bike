#!/usr/bin/env python3
"""Load and validate the shared cat-head shell/aluminum interface contract."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


DEFAULT_REVISION = "CAT-HEAD-SHELL-ALUMINUM-V0.3"
DEFAULT_FILENAME = "cat-head-shell-aluminum-interface-v03.json"
SUPPORTED_REVISIONS = {
    "CAT-HEAD-SHELL-ALUMINUM-V0.3",
    "CAT-HEAD-SHELL-ALUMINUM-V0.4",
}


class InterfaceContractError(ValueError):
    """Raised when a consumer cannot safely use the shared interface."""


def _norm(vector: list[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def _dot(first: list[float], second: list[float]) -> float:
    return sum(a * b for a, b in zip(first, second))


def _subtract(first: list[float], second: list[float]) -> list[float]:
    return [a - b for a, b in zip(first, second)]


def _axis_error_deg(actual: list[float], expected: list[float]) -> float:
    denominator = _norm(actual) * _norm(expected)
    if denominator == 0.0:
        return math.inf
    cosine = max(-1.0, min(1.0, _dot(actual, expected) / denominator))
    return math.degrees(math.acos(cosine))


def validate_interface(interface: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic validation report without mutating the contract."""
    tolerances = interface["validation_tolerances"]
    plane = interface["rear_interface_plane"]
    rails = interface["rail_system"]
    profile = rails["profile"]
    socket = rails["socket"]
    backplate = interface["aluminum_backplate"]

    expected_inside_width = (
        float(profile["outside_width_mm"])
        - 2.0 * float(profile["wall_thickness_mm"])
    )
    expected_inside_height = (
        float(profile["outside_height_mm"])
        - 2.0 * float(profile["wall_thickness_mm"])
    )
    width_clearance = (
        float(socket["printed_opening_width_mm"])
        - float(profile["outside_width_mm"])
    )
    height_clearance = (
        float(socket["printed_opening_height_mm"])
        - float(profile["outside_height_mm"])
    )
    clearance_each_side = min(width_clearance, height_clearance) / 2.0

    normal = [float(value) for value in plane["outward_normal_head"]]
    center = [float(value) for value in plane["center_head_mm"]]
    plane_errors = {
        side: abs(
            _dot(
                _subtract([float(value) for value in target], center),
                normal,
            )
        )
        for side, target in rails["lower_targets_head_mm"].items()
    }
    axis_lengths = {
        side: _norm([float(value) for value in axis])
        for side, axis in rails["accepted_axes_head"].items()
    }
    left_axis = [float(value) for value in rails["accepted_axes_head"]["left"]]
    right_axis = [float(value) for value in rails["accepted_axes_head"]["right"]]
    mirrored_left = [-right_axis[0], right_axis[1], right_axis[2]]
    axis_symmetry_error = _axis_error_deg(left_axis, mirrored_left)

    local_vertical = [0.0, -normal[2], normal[1]]
    local_vertical_length = _norm(local_vertical)
    local_vertical = [value / local_vertical_length for value in local_vertical]
    target_local_v = {
        side: _dot(
            _subtract([float(value) for value in target], center),
            local_vertical,
        )
        for side, target in rails["lower_targets_head_mm"].items()
    }
    half_height = float(backplate["height_mm"]) / 2.0

    def half_width_at(local_v: float) -> float:
        fraction = (local_v + half_height) / (2.0 * half_height)
        bottom = float(backplate["outer_bottom_width_mm"]) / 2.0
        top = float(backplate["outer_top_width_mm"]) / 2.0
        return bottom + fraction * (top - bottom)

    target_edge_clearance = {
        side: half_width_at(target_local_v[side])
        - abs(float(target[0]))
        - float(profile["outside_width_mm"]) / 2.0
        for side, target in rails["lower_targets_head_mm"].items()
    }
    required_stock = 2.0 * float(rails["modeled_installed_reference_length_mm"])

    checks = {
        "revision_matches_schema": {
            "value": interface["interface_revision"],
            "supported": sorted(SUPPORTED_REVISIONS),
            "pass": interface["interface_revision"] in SUPPORTED_REVISIONS,
        },
        "rear_plane_normal_is_unit": {
            "value": _norm(normal),
            "maximum_error": tolerances["vector_unit_length_error_max"],
            "pass": abs(_norm(normal) - 1.0)
            <= float(tolerances["vector_unit_length_error_max"]),
        },
        "lower_targets_lie_on_rear_plane": {
            "value_mm": max(plane_errors.values()),
            "required_max_mm": tolerances["target_to_rear_plane_error_mm_max"],
            "pass": max(plane_errors.values())
            <= float(tolerances["target_to_rear_plane_error_mm_max"]),
        },
        "rail_axes_are_unit": {
            "value": max(abs(value - 1.0) for value in axis_lengths.values()),
            "maximum_error": tolerances["vector_unit_length_error_max"],
            "pass": max(abs(value - 1.0) for value in axis_lengths.values())
            <= float(tolerances["vector_unit_length_error_max"]),
        },
        "rail_axes_are_mirrored": {
            "value_deg": axis_symmetry_error,
            "required_max_deg": tolerances["rail_axis_angular_error_deg_max"],
            "pass": axis_symmetry_error
            <= float(tolerances["rail_axis_angular_error_deg_max"]),
        },
        "inside_dimensions_match_measured_wall": {
            "value_mm": [expected_inside_width, expected_inside_height],
            "recorded_mm": [
                profile["derived_inside_width_mm"],
                profile["derived_inside_height_mm"],
            ],
            "pass": max(
                abs(expected_inside_width - float(profile["derived_inside_width_mm"])),
                abs(expected_inside_height - float(profile["derived_inside_height_mm"])),
            )
            <= float(tolerances["derived_dimension_error_mm_max"]),
        },
        "socket_clearance_matches_measured_stock": {
            "value_total_mm": [width_clearance, height_clearance],
            "value_each_side_mm": clearance_each_side,
            "required_each_side_mm": [
                tolerances["minimum_nominal_socket_clearance_each_side_mm"],
                tolerances["maximum_nominal_socket_clearance_each_side_mm"],
            ],
            "pass": (
                abs(width_clearance - float(socket["total_width_clearance_from_measured_stock_mm"]))
                <= float(tolerances["socket_opening_error_mm_max"])
                and abs(height_clearance - float(socket["total_height_clearance_from_measured_stock_mm"]))
                <= float(tolerances["socket_opening_error_mm_max"])
                and float(tolerances["minimum_nominal_socket_clearance_each_side_mm"])
                <= clearance_each_side
                <= float(tolerances["maximum_nominal_socket_clearance_each_side_mm"])
            ),
        },
        "available_stock_covers_two_modeled_routes": {
            "value_mm": profile["available_stock_length_mm"],
            "required_min_mm_before_kerf_and_fit_allowance": required_stock,
            "pass": float(profile["available_stock_length_mm"]) > required_stock,
        },
        "lower_targets_retain_positive_raw_plate_edge_clearance": {
            "value_mm": min(target_edge_clearance.values()),
            "pass": min(target_edge_clearance.values()) > 0.0,
        },
    }
    passed = all(check["pass"] for check in checks.values())
    return {
        "status": "PASS - COORDINATED REVIEW INTERFACE ONLY" if passed else "FAIL",
        "interface_revision": interface["interface_revision"],
        "release_status": "NOT A PRINT, CUT, OR DRILLING RELEASE",
        "checks": checks,
        "derived": {
            "inside_profile_mm": [expected_inside_width, expected_inside_height],
            "socket_clearance_each_side_mm": clearance_each_side,
            "lower_target_plane_errors_mm": plane_errors,
            "lower_target_local_v_mm": target_local_v,
            "raw_tube_to_backplate_edge_clearance_mm": target_edge_clearance,
            "stock_remaining_after_two_modeled_routes_mm": (
                float(profile["available_stock_length_mm"]) - required_stock
            ),
        },
        "open_items": interface["open_items"],
    }


def load_interface(
    path: Path,
    expected_revision: str = DEFAULT_REVISION,
) -> tuple[dict[str, Any], dict[str, Any]]:
    interface = json.loads(path.read_text(encoding="utf-8"))
    report = validate_interface(interface)
    if interface["interface_revision"] != expected_revision:
        raise InterfaceContractError(
            f"Interface revision {interface['interface_revision']} does not match "
            f"required {expected_revision}"
        )
    if not report["status"].startswith("PASS"):
        failed = [name for name, value in report["checks"].items() if not value["pass"]]
        raise InterfaceContractError(f"Shared interface validation failed: {failed}")
    return interface, report


def gate8_portal_contract(interface: dict[str, Any]) -> dict[str, Any]:
    rails = interface["rail_system"]
    profile = rails["profile"]
    socket = rails["socket"]
    return {
        "tube_profile": profile["description"],
        "tube_outer_width_mm": profile["outside_width_mm"],
        "tube_outer_height_mm": profile["outside_height_mm"],
        "tube_wall_thickness_mm": profile["wall_thickness_mm"],
        "tube_available_stock_length_mm": profile["available_stock_length_mm"],
        "tube_design_clearance_mm": socket["total_width_clearance_from_measured_stock_mm"],
        "tube_reference_length_mm": rails["review_display_length_mm"],
        "upper_target_right_mm": rails["upper_shell_search_targets_head_mm"]["right"],
        "upper_target_left_mm": rails["upper_shell_search_targets_head_mm"]["left"],
        "lower_route_right_mm": rails["lower_targets_head_mm"]["right"],
        "lower_route_left_mm": rails["lower_targets_head_mm"]["left"],
        "lower_route_basis": (
            f"Shared {interface['interface_revision']} lower targets on the "
            "aluminum rear-backplate plane"
        ),
        "socket_roll_reference": socket["roll_reference"],
        "clamp_length_mm": socket["insertion_depth_mm"],
        "m4_clearance_diameter_mm": socket["cross_bolt_clearance_diameter_mm"],
        "bolt_offset_from_open_end_mm": socket["cross_bolt_offset_from_open_end_mm"],
    }


def metal_head_interface_contract(interface: dict[str, Any]) -> dict[str, Any]:
    plane = interface["rear_interface_plane"]
    backplate = interface["aluminum_backplate"]
    rails = interface["rail_system"]
    profile = rails["profile"]
    socket = rails["socket"]
    holes = backplate["adapter_hole_pattern"]
    return {
        "actual_gate8_shell_bounds_head_mm": interface["head_envelope"],
        "rear_frame": {
            "outer_top_width_mm": backplate["outer_top_width_mm"],
            "outer_bottom_width_mm": backplate["outer_bottom_width_mm"],
            "plane_height_mm": backplate["height_mm"],
            "plane_center_head_mm": plane["center_head_mm"],
            "outward_normal_head": plane["outward_normal_head"],
        },
        "aluminum_backplate": {
            "material": backplate["material"],
            "thickness_mm": backplate["thickness_mm"],
            "outer_top_width_mm": backplate["outer_top_width_mm"],
            "outer_bottom_width_mm": backplate["outer_bottom_width_mm"],
            "height_mm": backplate["height_mm"],
            "bike_adapter_hole_diameter_mm": holes["diameter_mm"],
            "bike_adapter_hole_x_mm": max(abs(float(value)) for value in holes["x_mm"]),
            "bike_adapter_hole_v_mm": max(abs(float(value)) for value in holes["local_v_mm"]),
            "rail_lower_targets_head_mm": [
                rails["lower_targets_head_mm"]["left"],
                rails["lower_targets_head_mm"]["right"],
            ],
        },
        "internal_rails": {
            "profile": profile["description"],
            "outer_width_mm": profile["outside_width_mm"],
            "outer_height_mm": profile["outside_height_mm"],
            "wall_thickness_mm": profile["wall_thickness_mm"],
            "inside_width_mm": profile["derived_inside_width_mm"],
            "inside_height_mm": profile["derived_inside_height_mm"],
            "available_stock_length_mm": profile["available_stock_length_mm"],
            "socket_opening_mm": socket["printed_opening_width_mm"],
            "right_lower_target_head_mm": rails["lower_targets_head_mm"]["right"],
            "left_lower_target_head_mm": rails["lower_targets_head_mm"]["left"],
            "right_axis_head": rails["accepted_axes_head"]["right"],
            "left_axis_head": rails["accepted_axes_head"]["left"],
            "reference_length_mm": rails["modeled_installed_reference_length_mm"],
            "pitch_above_head_forward_deg": rails["pitch_above_head_forward_deg"],
            "yaw_from_head_centerline_deg": rails["yaw_from_head_centerline_deg"],
            "socket_roll_reference": socket["roll_reference"],
            "cross_bolt_angle_from_head_x_deg": socket["expected_cross_bolt_angle_from_head_x_deg"],
        },
    }


def default_interface_path() -> Path:
    return Path(__file__).resolve().parent / DEFAULT_FILENAME


def main() -> None:
    path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else default_interface_path()
    interface = json.loads(path.read_text(encoding="utf-8"))
    report = validate_interface(interface)
    print(json.dumps(report, indent=2))
    if not report["status"].startswith("PASS"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
