#!/usr/bin/env python3
"""Final read-only release validator for the approved C002 V2 candidate.

Validation-002 used a theoretical 20.50 mm old void to decide which baseline
material could be removed where the authorized socket profile intersects the
smooth M4 gauge.  V34 itself is the authority for material existence.  This
validator therefore defines the expected removal as exactly::

    V34 no-op snapshot intersect target_void intersect smooth_M4_gauge

All other validation-002 physical, interface, Route 2, preservation, and
immutability gates are retained.  The candidate is opened read-only and this
module never calls save(), saveAs(), a C002 generator, or a release exporter.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Sequence

import FreeCAD as App
import Part


CONTROL_DIR = Path(__file__).resolve().parent
if str(CONTROL_DIR) not in sys.path:
    sys.path.insert(0, str(CONTROL_DIR))

import validate_c002_rounded_terminal_release_v2_002 as core  # noqa: E402


VALIDATION_ID = "c002-rounded-terminal-profile-prototype-v2-release-validation-003"
VALIDATION_MODE = "read_only_independent_release_validation"
HOLD_CLASSIFICATION = "VALIDATOR_HOLD__CANDIDATE_UNCHANGED"
PASS_CLASSIFICATION = "RELEASE_VALIDATION_PASS"
EXPECTED_REMOVAL_SET = "snapshot ∩ target_void ∩ smooth_gauge"
INVALID_REMOVAL_SET = (
    "snapshot ∩ (target_void - ideal_old_20_50_void) ∩ smooth_gauge"
)


# Re-export the stable types and helpers used by the focused regression suite.
GateFailure = core.GateFailure
axis_cylinder = core.axis_cylinder
difference_volume = core.difference_volume
shape_volume = core.shape_volume


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--freecad-appdir", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--execute-authorized", action="store_true")
    return parser.parse_args(argv)


def evaluate_m4_preservation(
    snapshot_shape: Part.Shape,
    candidate_shape: Part.Shape,
    target_void: Part.Shape,
    old_void: Part.Shape,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    parameters: dict[str, Any],
    contract: dict[str, Any],
    interface: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate every M4 gate with V34 material as the removal authority.

    ``old_void`` remains in the signature only so the unchanged validation-002
    execution core can call this function.  It is intentionally excluded from
    the expected-removal set.
    """

    _ = old_void
    tolerances = contract["tolerances"]
    inspection = contract["m4_inspection"]
    m4 = parameters["m4_tunnel"]
    profile = parameters["profile"]
    diameter = float(m4["nominal_clearance_diameter_mm"])
    radius = diameter / 2.0
    station = float(m4["station_t_mm"])
    half_length = float(inspection["axial_half_length_mm"])
    smooth_gauge = core.axis_cylinder(
        radius, half_length, origin, axis_u, axis_t, station
    )
    bearing_gauge = core.axis_cylinder(
        float(inspection["bearing_inspection_radius_mm"]),
        half_length,
        origin,
        axis_u,
        axis_t,
        station,
    )

    added = candidate_shape.cut(snapshot_shape)
    removed = snapshot_shape.cut(candidate_shape)
    original_m4_void = bearing_gauge.cut(snapshot_shape)
    refilled_original_void = added.common(original_m4_void)
    no_refill_tolerance = float(
        tolerances["m4_original_void_refill_volume_mm3_max"]
    )
    core.require_gate(
        core.shape_volume(refilled_original_void) <= no_refill_tolerance,
        "M4_ORIGINAL_VOID_NOT_REFILLED",
        core.shape_volume(refilled_original_void),
        {"maximum_mm3": no_refill_tolerance},
    )

    removed_in_smooth_gauge = removed.common(smooth_gauge)
    removed_outside_target = removed_in_smooth_gauge.cut(target_void)
    envelope_tolerance = float(
        tolerances["m4_removed_outside_authorized_cavity_volume_mm3_max"]
    )
    core.require_gate(
        core.shape_volume(removed_outside_target) <= envelope_tolerance,
        "M4_REMOVAL_CONTAINED_IN_AUTHORIZED_CAVITY_ENVELOPE",
        {
            "removed_inside_smooth_gauge_mm3": core.shape_volume(
                removed_in_smooth_gauge
            ),
            "removed_outside_authorized_target_void_mm3": core.shape_volume(
                removed_outside_target
            ),
        },
        {"outside_volume_mm3_max": envelope_tolerance},
    )

    # Authorized correction: actual V34 material, not a theoretical old void,
    # defines what material exists and is expected to be removed.
    expected_overlap = snapshot_shape.common(target_void).common(smooth_gauge)
    actual_minus_expected = core.difference_volume(
        removed_in_smooth_gauge, expected_overlap
    )
    expected_minus_actual = core.difference_volume(
        expected_overlap, removed_in_smooth_gauge
    )
    overlap_tolerance = float(
        tolerances["m4_intentional_overlap_symmetric_difference_volume_mm3_max"]
    )
    core.require_gate(
        actual_minus_expected <= overlap_tolerance
        and expected_minus_actual <= overlap_tolerance,
        "M4_SMOOTH_GAUGE_REMOVAL_EQUALS_SNAPSHOT_TARGET_VOID_INTERSECTION",
        {
            "actual_removed_inside_smooth_gauge_mm3": core.shape_volume(
                removed_in_smooth_gauge
            ),
            "baseline_snapshot_material_in_target_void_and_smooth_gauge_mm3": (
                core.shape_volume(expected_overlap)
            ),
            "actual_minus_expected_mm3": actual_minus_expected,
            "expected_minus_actual_mm3": expected_minus_actual,
        },
        {
            "set_definition": EXPECTED_REMOVAL_SET,
            "each_symmetric_difference_mm3_max": overlap_tolerance,
        },
    )
    historical = float(
        contract["validation_001_disposition"][
            "reported_removed_inside_smooth_gauge_mm3"
        ]
    )
    historical_tolerance = float(
        tolerances["m4_historical_observation_volume_mm3_max"]
    )
    core.require_gate(
        abs(core.shape_volume(removed_in_smooth_gauge) - historical)
        <= historical_tolerance,
        "M4_HOLD_OBSERVATION_REPRODUCED",
        core.shape_volume(removed_in_smooth_gauge),
        {"value_mm3": historical, "absolute_error_mm3_max": historical_tolerance},
    )

    bearing_region = bearing_gauge.cut(target_void)
    snapshot_bearing = snapshot_shape.common(bearing_region)
    candidate_bearing = candidate_shape.common(bearing_region)
    snapshot_minus_candidate = core.difference_volume(
        snapshot_bearing, candidate_bearing
    )
    candidate_minus_snapshot = core.difference_volume(
        candidate_bearing, snapshot_bearing
    )
    bearing_tolerance = float(
        tolerances["m4_bearing_symmetric_difference_volume_mm3_max"]
    )
    core.require_gate(
        snapshot_minus_candidate <= bearing_tolerance
        and candidate_minus_snapshot <= bearing_tolerance,
        "M4_BEARING_REGIONS_OUTSIDE_AUTHORIZED_CAVITY_UNCHANGED",
        {
            "snapshot_minus_candidate_mm3": snapshot_minus_candidate,
            "candidate_minus_snapshot_mm3": candidate_minus_snapshot,
        },
        {"each_mm3_max": bearing_tolerance},
    )

    current_half = float(profile["current_straight_across_flats_mm"]) / 2.0
    target_half = float(profile["straight_across_flats_mm"]) / 2.0
    baseline_signature = core.extract_faceted_m4_signature(
        snapshot_shape,
        origin,
        axis_u,
        axis_v,
        axis_t,
        station,
        radius,
        current_half,
        inspection,
    )
    candidate_signature = core.extract_faceted_m4_signature(
        candidate_shape,
        origin,
        axis_u,
        axis_v,
        axis_t,
        station,
        radius,
        target_half,
        inspection,
    )

    preservation_position = float(
        tolerances["m4_candidate_baseline_position_mm_max"]
    )
    preservation_diameter = float(
        tolerances["m4_candidate_baseline_diameter_mm_max"]
    )
    preservation_axis = float(
        tolerances["m4_candidate_baseline_axis_angular_error_deg_max"]
    )
    baseline_axis = core.vector(baseline_signature["axis"])
    candidate_axis = core.vector(candidate_signature["axis"])
    center_delta = math.hypot(
        float(candidate_signature["center_local_v_mm"])
        - float(baseline_signature["center_local_v_mm"]),
        float(candidate_signature["station_local_t_mm"])
        - float(baseline_signature["station_local_t_mm"]),
    )
    diameter_delta = abs(
        float(candidate_signature["clearance_circumdiameter_mm"])
        - float(baseline_signature["clearance_circumdiameter_mm"])
    )
    axis_delta = core.angle_deg(candidate_axis, baseline_axis, unoriented=True)
    core.require_gate(
        center_delta <= preservation_position
        and diameter_delta <= preservation_diameter
        and axis_delta <= preservation_axis
        and candidate_signature["facet_plane_count"]
        == baseline_signature["facet_plane_count"],
        "M4_CANDIDATE_MATCHES_BASELINE_SIGNATURE",
        {
            "center_delta_mm": center_delta,
            "diameter_delta_mm": diameter_delta,
            "axis_delta_deg": axis_delta,
            "baseline_facet_plane_count": baseline_signature["facet_plane_count"],
            "candidate_facet_plane_count": candidate_signature["facet_plane_count"],
        },
        {
            "center_delta_mm_max": preservation_position,
            "diameter_delta_mm_max": preservation_diameter,
            "axis_delta_deg_max": preservation_axis,
            "facet_plane_count": "exact baseline match",
        },
    )

    interface_tolerance = interface["validation_tolerances"]
    dimension_limit = float(interface_tolerance["derived_dimension_error_mm_max"])
    axis_limit = float(interface_tolerance["rail_axis_angular_error_deg_max"])
    center_error = abs(float(candidate_signature["center_local_v_mm"]))
    station_error = abs(float(candidate_signature["station_local_t_mm"]) - station)
    diameter_error = abs(
        float(candidate_signature["clearance_circumdiameter_mm"]) - diameter
    )
    axis_error = core.angle_deg(candidate_axis, axis_u, unoriented=True)
    expected_angle = float(
        interface["rail_system"]["socket"][
            "expected_cross_bolt_angle_from_head_x_deg"
        ]
    )
    measured_angle = core.angle_deg(
        candidate_axis, App.Vector(1.0, 0.0, 0.0), unoriented=True
    )
    core.require_gate(
        center_error <= dimension_limit
        and station_error <= dimension_limit
        and diameter_error <= dimension_limit
        and axis_error <= axis_limit
        and abs(measured_angle - expected_angle) <= axis_limit,
        "M4_CANDIDATE_MATCHES_FROZEN_INTERFACE",
        {
            "center_v_error_mm": center_error,
            "station_t_error_mm": station_error,
            "clearance_diameter_error_mm": diameter_error,
            "axis_to_contract_u_deg": axis_error,
            "cross_bolt_angle_from_head_x_deg": measured_angle,
            "cross_bolt_angle_error_deg": abs(measured_angle - expected_angle),
        },
        {
            "center_v_mm": 0.0,
            "station_t_mm": station,
            "clearance_diameter_mm": diameter,
            "dimension_error_mm_max": dimension_limit,
            "axis_angular_error_deg_max": axis_limit,
            "cross_bolt_angle_from_head_x_deg": expected_angle,
        },
    )

    return {
        "status": "PASS",
        "original_void": {
            "refilled_or_obstructed_volume_mm3": core.shape_volume(
                refilled_original_void
            ),
            "maximum_mm3": no_refill_tolerance,
        },
        "authorized_profile_overlap": {
            "expected_removal_set": EXPECTED_REMOVAL_SET,
            "reported_validation_001_removed_inside_smooth_gauge_mm3": historical,
            "measured_removed_inside_smooth_gauge_mm3": core.shape_volume(
                removed_in_smooth_gauge
            ),
            "baseline_snapshot_material_in_target_void_and_smooth_gauge_mm3": (
                core.shape_volume(expected_overlap)
            ),
            "removed_outside_authorized_target_void_mm3": core.shape_volume(
                removed_outside_target
            ),
            "classification": (
                "V34_SNAPSHOT_MATERIAL_REMOVED_ONLY_WITHIN_TARGET_VOID_AND_M4_GAUGE"
            ),
        },
        "bearing_region_preservation": {
            "inspection_radius_mm": float(
                inspection["bearing_inspection_radius_mm"]
            ),
            "snapshot_minus_candidate_mm3": snapshot_minus_candidate,
            "candidate_minus_snapshot_mm3": candidate_minus_snapshot,
            "status": "PASS",
        },
        "baseline_signature": baseline_signature,
        "candidate_signature": candidate_signature,
        "candidate_baseline_deltas": {
            "center_mm": center_delta,
            "diameter_mm": diameter_delta,
            "axis_deg": axis_delta,
        },
        "frozen_interface_match": {
            "center_v_mm": candidate_signature["center_local_v_mm"],
            "station_t_mm": candidate_signature["station_local_t_mm"],
            "axis": candidate_signature["axis"],
            "clearance_circumdiameter_mm": candidate_signature[
                "clearance_circumdiameter_mm"
            ],
            "cross_bolt_angle_from_head_x_deg": measured_angle,
            "interface_revision": interface["metal_handoff_record"]["revision"],
            "status": "PASS",
        },
        "remaining_printed_bearing_length_wall_thickness": {
            "left": candidate_signature["bearing_left"],
            "right": candidate_signature["bearing_right"],
        },
    }


def verify_validation_002_hold(context: dict[str, Any]) -> dict[str, Any]:
    contract = context["contract"]
    disposition = contract["validation_002_disposition"]
    core.require_gate(
        disposition.get("classification") == HOLD_CLASSIFICATION,
        "VALIDATION_002_DISPOSITION",
        disposition.get("classification"),
        HOLD_CLASSIFICATION,
    )
    report = core.load_json(context["input_paths"]["validation_002_report"])
    failed = report.get("failed_gate") or {}
    actual = failed.get("actual") or {}
    expected = disposition["reported_values_mm3"]
    observed = {
        "actual_removed_inside_smooth_gauge_mm3": float(
            actual.get("actual_removed_inside_smooth_gauge_mm3", math.nan)
        ),
        "baseline_material_in_authorized_enlargement_and_gauge_mm3": float(
            actual.get(
                "baseline_material_in_authorized_enlargement_and_gauge_mm3",
                math.nan,
            )
        ),
        "actual_minus_expected_mm3": float(
            actual.get("actual_minus_expected_mm3", math.nan)
        ),
        "expected_minus_actual_mm3": float(
            actual.get("expected_minus_actual_mm3", math.nan)
        ),
    }
    values_match = all(
        abs(observed[key] - float(expected[key])) <= 1.0e-15 for key in expected
    )
    core.require_gate(
        report.get("status") == "FAIL"
        and report.get("candidate_modified") is False
        and report.get("generator_invoked") is False
        and failed.get("gate")
        == "M4_SMOOTH_GAUGE_REMOVAL_EQUALS_AUTHORIZED_PROFILE_ENLARGEMENT"
        and values_match,
        "VALIDATION_002_HOLD_EVIDENCE",
        {
            "status": report.get("status"),
            "candidate_modified": report.get("candidate_modified"),
            "generator_invoked": report.get("generator_invoked"),
            "failed_gate": failed.get("gate"),
            "reported_values_mm3": observed,
        },
        {
            "status": "FAIL",
            "candidate_modified": False,
            "generator_invoked": False,
            "failed_gate": (
                "M4_SMOOTH_GAUGE_REMOVAL_EQUALS_AUTHORIZED_PROFILE_ENLARGEMENT"
            ),
            "reported_values_mm3": expected,
        },
    )
    validation_002_contract = core.load_json(
        context["input_paths"]["validation_002_contract"]
    )
    core.require_gate(
        validation_002_contract.get("validation_id")
        == "c002-rounded-terminal-profile-prototype-v2-release-validation-002"
        and validation_002_contract["visual_approval"]["candidate_sha256"]
        == context["input_records"]["candidate"]["sha256"],
        "VALIDATION_002_CONTRACT_IDENTITY",
        {
            "validation_id": validation_002_contract.get("validation_id"),
            "candidate_sha256": validation_002_contract.get("visual_approval", {}).get(
                "candidate_sha256"
            ),
        },
        {
            "validation_id": (
                "c002-rounded-terminal-profile-prototype-v2-release-validation-002"
            ),
            "candidate_sha256": context["input_records"]["candidate"]["sha256"],
        },
    )
    return {
        "classification": HOLD_CLASSIFICATION,
        "candidate_modified": False,
        "failed_gate": failed.get("gate"),
        "reported_values_mm3": observed,
        "correction_scope": "expected-removal set definition only",
    }


def preflight_context(args: argparse.Namespace) -> dict[str, Any]:
    # The immutable validation-002 preflight supplies all established input,
    # runtime, numeric-contract, visual-approval, and V1-hold checks.  These two
    # globals are temporarily rebound only so that preflight evaluates the new
    # validation ID and the new hash-pinned validator path.
    original_id = core.VALIDATION_ID
    original_file = core.__file__
    core.VALIDATION_ID = VALIDATION_ID
    core.__file__ = __file__
    try:
        context = core.preflight_context(args)
    finally:
        core.VALIDATION_ID = original_id
        core.__file__ = original_file

    dependency_path, dependency_record = core.verify_file_input(
        context["root"],
        "validation_002_validator_core",
        context["contract"]["tooling_dependencies"][
            "validation_002_validator_core"
        ],
    )
    core.require_gate(
        dependency_path == Path(core.__file__).resolve(),
        "VALIDATION_002_CORE_PATH",
        str(dependency_path),
        str(Path(core.__file__).resolve()),
    )
    set_contract = context["contract"]["m4_expected_removal_set"]
    core.require_gate(
        set_contract.get("definition") == EXPECTED_REMOVAL_SET
        and set_contract.get("rejected_definition") == INVALID_REMOVAL_SET,
        "M4_EXPECTED_REMOVAL_SET_CONTRACT",
        set_contract,
        {
            "definition": EXPECTED_REMOVAL_SET,
            "rejected_definition": INVALID_REMOVAL_SET,
        },
    )
    core.require_gate(
        context["contract"]["execution_policy"].get(
            "immediate_single_execution_authorized"
        )
        is True,
        "EXECUTION_AUTHORIZATION_RECORDED",
        context["contract"]["execution_policy"].get(
            "immediate_single_execution_authorized"
        ),
        True,
    )
    context["validation_002_core_record"] = dependency_record
    context["validation_002_hold_evidence"] = verify_validation_002_hold(context)
    return context


def execute_validation(context: dict[str, Any]) -> dict[str, Any]:
    # Preserve the complete validation-002 gate order while replacing only its
    # M4 evaluator with the function above for the duration of this call.
    original_evaluator = core.evaluate_m4_preservation
    core.evaluate_m4_preservation = evaluate_m4_preservation
    try:
        return core.execute_validation(context)
    finally:
        core.evaluate_m4_preservation = original_evaluator


def preflight_result(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "validation_id": VALIDATION_ID,
        "status": "PREFLIGHT_PASS__VALIDATION_NOT_EXECUTED",
        "candidate_disposition": HOLD_CLASSIFICATION,
        "candidate_sha256": context["input_records"]["candidate"]["sha256"],
        "candidate_opened": False,
        "candidate_modified": False,
        "generator_invoked": False,
        "geometry_validation_executed": False,
        "output_created": False,
        "output_directory_exists": context["output_dir"].exists(),
        "runtime": context["runtime"],
        "validation_001_disposition": context["hold_evidence"],
        "validation_002_disposition": context["validation_002_hold_evidence"],
        "validation_002_validator_core": context["validation_002_core_record"],
        "m4_expected_removal_set": EXPECTED_REMOVAL_SET,
        "m4_gauge_t_range_mm": context["m4_gauge_t_range_mm"],
        "straight_profile_t_range_mm": context["straight_profile_t_range_mm"],
        "next_action": (
            "single immediate --execute-authorized pass under recorded user approval"
        ),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        context = preflight_context(args)
    except core.GateFailure as exc:
        result = {
            "schema_version": "1.0",
            "validation_id": VALIDATION_ID,
            "status": "PREFLIGHT_FAIL",
            "candidate_disposition": HOLD_CLASSIFICATION,
            "candidate_modified": False,
            "generator_invoked": False,
            "geometry_validation_executed": False,
            "output_created": False,
            "failed_gate": exc.record(),
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    if args.preflight_only:
        print(json.dumps(preflight_result(context), indent=2, sort_keys=True))
        return 0

    result: dict[str, Any] = {
        "schema_version": "1.0",
        "validation_id": VALIDATION_ID,
        "mode": VALIDATION_MODE,
        "candidate_sha256": context["input_records"]["candidate"]["sha256"],
        "candidate_modified": False,
        "generator_invoked": False,
        "automatic_retry": False,
        "automatic_healing_used": False,
        "full_system_release": False,
        "release_holds": context["contract"]["release_holds"],
        "m4_expected_removal_set": EXPECTED_REMOVAL_SET,
        "validation_002_disposition": context["validation_002_hold_evidence"],
        "validation_002_validator_core": context["validation_002_core_record"],
    }
    exit_code = 1
    try:
        metrics = execute_validation(context)
        result.update(
            {
                "status": "PASS",
                "release_validation_result": PASS_CLASSIFICATION,
                "candidate_disposition": "C002_FROZEN__NO_PROMOTION",
                "failed_gate": None,
                "metrics": metrics,
            }
        )
        exit_code = 0
    except core.GateFailure as exc:
        result.update(
            {
                "status": "FAIL",
                "release_validation_result": "PHYSICAL_VALIDATION_FAILURE",
                "candidate_disposition": (
                    "CANDIDATE_UNCHANGED__STOP_PERMANENTLY"
                ),
                "failed_gate": exc.record(),
            }
        )
    except Exception as exc:
        result.update(
            {
                "status": "FAIL",
                "release_validation_result": "VALIDATOR_EXCEPTION",
                "candidate_disposition": (
                    "CANDIDATE_UNCHANGED__STOP_PERMANENTLY"
                ),
                "failed_gate": {
                    "gate": "VALIDATOR_EXCEPTION",
                    "actual": f"{type(exc).__name__}: {exc}",
                    "expected": "validator completes without exception",
                },
            }
        )

    context["output_dir"].mkdir(parents=True, exist_ok=False)
    context["report_path"].write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
