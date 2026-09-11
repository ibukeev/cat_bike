#!/usr/bin/env python3
"""Corrected, read-only release validator for the approved C002 V2 candidate.

Validation-001 incorrectly required zero material removal everywhere inside a
smooth 4.50 mm cylinder.  The frozen M4 clearance is a faceted void, so the
authorized 20.50 -> 21.00 mm socket widening legitimately removes the small
pieces of baseline wall that lie between that faceted void and the smooth
gauge.  This validator distinguishes that overlap from an M4 tunnel change.

The module imports only immutable, hash-pinned utility functions from the
validation-001 verifier.  It never calls that verifier's validate() or main(),
never imports either C002 generator, and never saves an FCStd document.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any, Sequence

import FreeCAD as App
import Part


CONTROL_DIR = Path(__file__).resolve().parent
if str(CONTROL_DIR) not in sys.path:
    sys.path.insert(0, str(CONTROL_DIR))

from validate_c002_rounded_terminal_release_v2 import (  # noqa: E402
    GateFailure,
    PROTECTED_ROOT_OBJECT,
    TARGET_OBJECT,
    aligned,
    angle_deg,
    build_independent_expected_shape,
    checked_repo_path,
    common_volume,
    difference_volume,
    face_normal,
    load_json,
    local_coordinates,
    measure_straight_cavity_frame,
    normalized,
    placement_record,
    placements_match,
    raw_shape_digests,
    repository_root,
    require_candidate_health,
    require_gate,
    sha256_file,
    shape_metrics,
    vector,
    vector_values,
    verify_file_input,
    verify_numeric_contract,
    verify_runtime,
)


VALIDATION_ID = "c002-rounded-terminal-profile-prototype-v2-release-validation-002"
VALIDATION_MODE = "read_only_independent_release_validation"
HOLD_CLASSIFICATION = "VALIDATOR_HOLD__CANDIDATE_UNCHANGED"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--freecad-appdir", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--execute-authorized", action="store_true")
    return parser.parse_args(argv)


def shape_volume(shape: Part.Shape) -> float:
    return 0.0 if shape.isNull() else float(shape.Volume)


def orthonormal_frame(parameters: dict[str, Any]) -> tuple[App.Vector, ...]:
    frame = parameters["rail_frame"]
    origin = vector(frame["origin_head_mm"])
    axis_t = normalized(vector(frame["t_axis"]), "contract t axis")
    axis_u = normalized(vector(frame["u_axis"]), "contract u axis")
    axis_v = normalized(vector(frame["v_axis"]), "contract v axis")
    errors = {
        "u_dot_v": float(axis_u.dot(axis_v)),
        "u_dot_t": float(axis_u.dot(axis_t)),
        "v_dot_t": float(axis_v.dot(axis_t)),
        "u_cross_v_minus_t_length": float((axis_u.cross(axis_v) - axis_t).Length),
    }
    require_gate(
        max(abs(errors[key]) for key in ("u_dot_v", "u_dot_t", "v_dot_t"))
        <= 1.0e-9
        and errors["u_cross_v_minus_t_length"] <= 1.0e-9,
        "CONTRACT_FRAME_ORTHONORMAL",
        errors,
        "orthogonal right-handed frame within 1e-9",
    )
    return origin, axis_u, axis_v, axis_t


def verify_hold_evidence(
    contract: dict[str, Any],
    input_paths: dict[str, Path],
    dependency_path: Path,
) -> dict[str, Any]:
    disposition = contract["validation_001_disposition"]
    require_gate(
        disposition.get("classification") == HOLD_CLASSIFICATION,
        "VALIDATION_001_DISPOSITION",
        disposition.get("classification"),
        HOLD_CLASSIFICATION,
    )
    report = load_json(input_paths["validation_001_report"])
    failed = report.get("failed_gate") or {}
    actual = failed.get("actual") or {}
    expected_removed = float(disposition["reported_removed_inside_smooth_gauge_mm3"])
    require_gate(
        report.get("status") == "FAIL"
        and report.get("candidate_modified") is False
        and report.get("generator_invoked") is False
        and failed.get("gate") == "M4_TUNNEL_UNCHANGED_VOLUME"
        and float(actual.get("added_change_inside_m4_mm3", math.nan)) == 0.0
        and abs(
            float(actual.get("removed_change_inside_m4_mm3", math.nan))
            - expected_removed
        )
        <= 1.0e-15,
        "VALIDATION_001_HOLD_EVIDENCE",
        report,
        {
            "status": "FAIL",
            "candidate_modified": False,
            "generator_invoked": False,
            "failed_gate": "M4_TUNNEL_UNCHANGED_VOLUME",
            "added_mm3": 0.0,
            "removed_mm3": expected_removed,
        },
    )

    source = dependency_path.read_text(encoding="utf-8")
    exact_index = source.find('"EXACT_ROUTE2_EXPECTED_GEOMETRY"')
    envelope_index = source.find('"ZERO_EXTERIOR_DEVIATION"')
    faulty_index = source.find('"M4_TUNNEL_UNCHANGED_VOLUME"')
    require_gate(
        0 <= exact_index < envelope_index < faulty_index,
        "VALIDATION_001_GATE_ORDER",
        {
            "EXACT_ROUTE2_EXPECTED_GEOMETRY": exact_index,
            "ZERO_EXTERIOR_DEVIATION": envelope_index,
            "M4_TUNNEL_UNCHANGED_VOLUME": faulty_index,
        },
        "exact geometry and envelope gates precede the reported M4 hold",
    )
    return {
        "classification": HOLD_CLASSIFICATION,
        "candidate_modified": False,
        "reported_added_inside_smooth_gauge_mm3": 0.0,
        "reported_removed_inside_smooth_gauge_mm3": expected_removed,
        "prior_passed_gates": [
            "EXACT_ROUTE2_EXPECTED_GEOMETRY",
            "ZERO_EXTERIOR_DEVIATION",
        ],
        "set_containment_proof": (
            "(removed intersect smooth_M4_gauge) minus authorized_target_void "
            "is a subset of removed minus authorized_target_void; validation-001 "
            "reached its later M4 gate only after the latter was <= 0.000001 mm3"
        ),
        "result": (
            "reported removal is inside the authorized target cavity envelope "
            "within the unchanged 0.000001 mm3 Boolean tolerance"
        ),
    }


def preflight_context(args: argparse.Namespace) -> dict[str, Any]:
    root = repository_root(args.contract)
    contract_path = args.contract.resolve()
    contract = load_json(contract_path)
    require_gate(
        contract.get("validation_id") == VALIDATION_ID,
        "VALIDATION_ID",
        contract.get("validation_id"),
        VALIDATION_ID,
    )
    require_gate(
        contract.get("mode") == VALIDATION_MODE,
        "VALIDATION_MODE",
        contract.get("mode"),
        VALIDATION_MODE,
    )
    require_gate(
        contract.get("state") == "prepared_awaiting_explicit_execution_authorization",
        "VALIDATION_STATE",
        contract.get("state"),
        "prepared_awaiting_explicit_execution_authorization",
    )

    output_dir = checked_repo_path(root, contract["output"]["directory"])
    report_path = checked_repo_path(root, contract["output"]["report"])
    try:
        report_path.relative_to(output_dir)
    except ValueError as exc:
        raise GateFailure("REPORT_PATH_SCOPE", str(report_path), f"inside {output_dir}") from exc
    require_gate(
        not output_dir.exists(),
        "RELEASE_VALIDATION_OUTPUT_MUST_BE_NEW",
        str(output_dir),
        "absent before the single authorized validation pass",
    )

    input_records: dict[str, Any] = {}
    input_paths: dict[str, Path] = {}
    for label, spec in contract["inputs"].items():
        path, record = verify_file_input(root, label, spec)
        input_paths[label] = path
        input_records[label] = record

    dependency_path, dependency_record = verify_file_input(
        root,
        "validation_001_utility_dependency",
        contract["tooling_dependencies"]["validation_001_utility_dependency"],
    )
    validator_path, validator_record = verify_file_input(
        root,
        "validator",
        contract["validator"],
    )
    require_gate(
        validator_path == Path(__file__).resolve(),
        "VALIDATOR_PATH",
        str(Path(__file__).resolve()),
        str(validator_path),
    )

    candidate_hash = input_records["candidate"]["sha256"]
    require_gate(
        contract["visual_approval"]["candidate_sha256"] == candidate_hash,
        "VISUAL_APPROVAL_CANDIDATE_HASH",
        contract["visual_approval"]["candidate_sha256"],
        candidate_hash,
    )
    iteration = load_json(input_paths["iteration_contract"])
    evidence = load_json(input_paths["route2_evidence"])
    interface = load_json(input_paths["interface"])
    preservation = load_json(input_paths["preservation_report"])
    runner_result = load_json(input_paths["runner_result"])
    runtime_manifest = load_json(input_paths["runtime_manifest"])

    require_gate(
        iteration["generator"]["script_path"]
        == contract["inputs"]["c002_generator"]["path"]
        and iteration["generator"]["script_sha256"]
        == contract["inputs"]["c002_generator"]["sha256"],
        "C002_GENERATOR_REMAINS_ITERATION_PIN",
        iteration["generator"],
        contract["inputs"]["c002_generator"],
    )
    require_gate(
        runner_result.get("status")
        == "CANDIDATE_READY__RUN_PRESERVATION_GATE_AND_FIXED_VIEWS"
        and runner_result["candidate"]["sha256"] == candidate_hash,
        "RUNNER_RESULT_STATUS",
        runner_result,
        "CANDIDATE_READY with the visually approved candidate hash",
    )
    require_gate(
        preservation.get("status") == "PASS__READY_FOR_FIXED_VIEW_REVIEW"
        and preservation["candidate"]["sha256"] == candidate_hash
        and not preservation.get("errors")
        and not preservation.get("protected_differences")
        and not preservation.get("target_errors"),
        "PRESERVATION_STATUS",
        preservation,
        "PASS with no errors, protected differences, or target errors",
    )

    parameters, numeric_record = verify_numeric_contract(iteration, evidence, interface)
    origin, axis_u, axis_v, axis_t = orthonormal_frame(parameters)
    runtime = verify_runtime(args.freecad_appdir, runtime_manifest)
    hold_evidence = verify_hold_evidence(contract, input_paths, dependency_path)

    profile = parameters["profile"]
    m4 = parameters["m4_tunnel"]
    radius = float(m4["nominal_clearance_diameter_mm"]) / 2.0
    station = float(m4["station_t_mm"])
    gauge_t_range = [station - radius, station + radius]
    straight_t_range = [
        float(profile["lead_in_transition_t_mm"]),
        float(profile["transition_start_t_mm"]),
    ]
    require_gate(
        gauge_t_range[0] >= straight_t_range[0]
        and gauge_t_range[1] <= straight_t_range[1],
        "M4_GAUGE_WITHIN_STRAIGHT_PROFILE_RANGE",
        gauge_t_range,
        straight_t_range,
    )

    return {
        "root": root,
        "contract": contract,
        "contract_path": contract_path,
        "output_dir": output_dir,
        "report_path": report_path,
        "input_records": input_records,
        "input_paths": input_paths,
        "dependency_record": dependency_record,
        "validator_record": validator_record,
        "iteration": iteration,
        "interface": interface,
        "parameters": parameters,
        "numeric_record": numeric_record,
        "runtime": runtime,
        "hold_evidence": hold_evidence,
        "origin": origin,
        "axis_u": axis_u,
        "axis_v": axis_v,
        "axis_t": axis_t,
        "m4_gauge_t_range_mm": gauge_t_range,
        "straight_profile_t_range_mm": straight_t_range,
    }


def axis_cylinder(
    radius: float,
    half_length: float,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_t: App.Vector,
    station_t: float,
) -> Part.Shape:
    return Part.makeCylinder(
        radius,
        2.0 * half_length,
        origin + axis_t * station_t - axis_u * half_length,
        axis_u,
    )


def _angle_gap(first: float, second: float) -> float:
    delta = abs(first - second) % (2.0 * math.pi)
    return min(delta, 2.0 * math.pi - delta)


def _bearing_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    lengths = sorted(float(item["length_mm"]) for item in records)
    require_gate(
        bool(lengths) and min(lengths) > 0.0,
        "M4_BEARING_REMAINS_PRINTED_BOTH_SIDES",
        records,
        "at least one positive printed bearing length per side",
    )
    return {
        "facet_face_count": len(records),
        "minimum_printed_bearing_length_wall_thickness_mm": min(lengths),
        "maximum_printed_bearing_length_wall_thickness_mm": max(lengths),
        "mean_printed_bearing_length_wall_thickness_mm": statistics.fmean(lengths),
        "per_face_lengths_mm": lengths,
        "face_identifiers": sorted(item["face_identifier"] for item in records),
    }


def extract_faceted_m4_signature(
    shape: Part.Shape,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    station_t: float,
    nominal_radius: float,
    cavity_half_width: float,
    inspection: dict[str, Any],
) -> dict[str, Any]:
    support_band = float(inspection["facet_support_search_band_mm"])
    axial_dot_min = float(inspection["facet_edge_axis_dot_search_min"])
    minimum_u_span = float(inspection["facet_face_u_span_search_min_mm"])
    plane_angle_merge = math.radians(
        float(inspection["facet_plane_merge_angular_error_deg_max"])
    )
    plane_offset_merge = float(inspection["facet_plane_merge_offset_error_mm_max"])
    inner_edge_tolerance = float(inspection["bearing_inner_edge_match_error_mm_max"])

    selected_faces: list[dict[str, Any]] = []
    axial_directions: list[App.Vector] = []
    for index, face in enumerate(shape.Faces, start=1):
        if "plane" not in type(face.Surface).__name__.lower():
            continue
        coordinates = [
            local_coordinates(vertex.Point, origin, axis_u, axis_v, axis_t)
            for vertex in face.Vertexes
        ]
        if not coordinates:
            continue
        u_values = [item[0] for item in coordinates]
        if max(u_values) - min(u_values) < minimum_u_span:
            continue
        normal = face_normal(face)
        n_u = float(normal.dot(axis_u))
        n_v = float(normal.dot(axis_v))
        n_t = float(normal.dot(axis_t))
        radial_norm = math.hypot(n_v, n_t)
        if radial_norm <= 1.0e-12:
            continue
        centroid_u, centroid_v, centroid_t = local_coordinates(
            face.CenterOfMass,
            origin,
            axis_u,
            axis_v,
            axis_t,
        )
        support = (
            n_u * centroid_u
            + n_v * centroid_v
            + n_t * (centroid_t - station_t)
        ) / radial_norm
        n_v /= radial_norm
        n_t /= radial_norm
        n_u /= radial_norm
        if support < 0.0:
            support = -support
            n_u = -n_u
            n_v = -n_v
            n_t = -n_t
        if abs(support - nominal_radius) > support_band:
            continue
        if math.hypot(centroid_v, centroid_t - station_t) > nominal_radius + support_band:
            continue

        face_record = {
            "face_identifier": f"Face{index}",
            "normal_local": [n_u, n_v, n_t],
            "support_at_u0_from_expected_center_mm": support,
            "u_min_mm": min(u_values),
            "u_max_mm": max(u_values),
            "u_span_mm": max(u_values) - min(u_values),
        }
        selected_faces.append(face_record)
        for edge in face.Edges:
            if len(edge.Vertexes) != 2:
                continue
            delta = edge.Vertexes[1].Point - edge.Vertexes[0].Point
            if float(delta.Length) <= minimum_u_span:
                continue
            direction = normalized(delta, "M4 facet axial edge")
            if abs(float(direction.dot(axis_u))) < axial_dot_min:
                continue
            axial_directions.append(aligned(direction, axis_u))

    require_gate(
        bool(selected_faces),
        "M4_FACETED_TUNNEL_SIGNATURE",
        {"selected_face_count": 0},
        "complete planar faceted tunnel signature",
    )

    facets: list[dict[str, Any]] = []
    for record in selected_faces:
        angle = math.atan2(record["normal_local"][2], record["normal_local"][1])
        if angle < 0.0:
            angle += 2.0 * math.pi
        match = None
        for existing in facets:
            if (
                _angle_gap(angle, existing["angle_rad"]) <= plane_angle_merge
                and abs(
                    record["support_at_u0_from_expected_center_mm"]
                    - existing["support_mm"]
                )
                <= plane_offset_merge
            ):
                match = existing
                break
        if match is None:
            facets.append(
                {
                    "angle_rad": angle,
                    "normal_v": record["normal_local"][1],
                    "normal_t": record["normal_local"][2],
                    "support_mm": record["support_at_u0_from_expected_center_mm"],
                    "faces": [record],
                }
            )
        else:
            match["faces"].append(record)

    facets.sort(key=lambda item: item["angle_rad"])
    minimum_facets = int(inspection["minimum_faceted_tunnel_planes"])
    require_gate(
        len(facets) >= minimum_facets,
        "M4_FACETED_TUNNEL_SIGNATURE",
        {
            "facet_plane_count": len(facets),
            "selected_faces": selected_faces,
        },
        {"minimum_facet_plane_count": minimum_facets},
    )
    require_gate(
        bool(axial_directions),
        "M4_FACET_AXIS_SIGNATURE",
        [],
        "one or more tunnel-facet axial edges",
    )
    axis_total = App.Vector(0.0, 0.0, 0.0)
    for direction in axial_directions:
        axis_total = axis_total + direction
    measured_axis = aligned(normalized(axis_total, "measured M4 axis"), axis_u)

    vertices: list[tuple[float, float]] = []
    for position, first in enumerate(facets):
        second = facets[(position + 1) % len(facets)]
        a, b, c = first["normal_v"], first["normal_t"], first["support_mm"]
        d, e, f = second["normal_v"], second["normal_t"], second["support_mm"]
        determinant = a * e - b * d
        require_gate(
            abs(determinant) > 1.0e-9,
            "M4_FACET_PLANE_INTERSECTION",
            {"first": first, "second": second, "determinant": determinant},
            "adjacent non-parallel facet planes",
        )
        vertices.append(((c * e - b * f) / determinant, (a * f - c * d) / determinant))

    center_v = statistics.fmean(item[0] for item in vertices)
    center_tau = statistics.fmean(item[1] for item in vertices)
    diameter = 0.0
    for first in vertices:
        for second in vertices:
            diameter = max(diameter, math.hypot(first[0] - second[0], first[1] - second[1]))

    left_records: list[dict[str, Any]] = []
    right_records: list[dict[str, Any]] = []
    for record in selected_faces:
        u_min = float(record["u_min_mm"])
        u_max = float(record["u_max_mm"])
        if abs(u_max + cavity_half_width) <= inner_edge_tolerance:
            left_records.append(
                {
                    "face_identifier": record["face_identifier"],
                    "inner_u_mm": u_max,
                    "outer_u_mm": u_min,
                    "length_mm": u_max - u_min,
                }
            )
        if abs(u_min - cavity_half_width) <= inner_edge_tolerance:
            right_records.append(
                {
                    "face_identifier": record["face_identifier"],
                    "inner_u_mm": u_min,
                    "outer_u_mm": u_max,
                    "length_mm": u_max - u_min,
                }
            )

    return {
        "geometry_kind": "faceted M4 tunnel",
        "facet_plane_count": len(facets),
        "selected_face_count": len(selected_faces),
        "selected_face_identifiers": sorted(
            item["face_identifier"] for item in selected_faces
        ),
        "center_local_v_mm": center_v,
        "station_local_t_mm": station_t + center_tau,
        "axis": vector_values(measured_axis),
        "clearance_circumdiameter_mm": diameter,
        "bearing_left": _bearing_summary(left_records),
        "bearing_right": _bearing_summary(right_records),
    }


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
    tolerances = contract["tolerances"]
    inspection = contract["m4_inspection"]
    m4 = parameters["m4_tunnel"]
    profile = parameters["profile"]
    diameter = float(m4["nominal_clearance_diameter_mm"])
    radius = diameter / 2.0
    station = float(m4["station_t_mm"])
    half_length = float(inspection["axial_half_length_mm"])
    smooth_gauge = axis_cylinder(radius, half_length, origin, axis_u, axis_t, station)
    bearing_gauge = axis_cylinder(
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
    no_refill_tolerance = float(tolerances["m4_original_void_refill_volume_mm3_max"])
    require_gate(
        shape_volume(refilled_original_void) <= no_refill_tolerance,
        "M4_ORIGINAL_VOID_NOT_REFILLED",
        shape_volume(refilled_original_void),
        {"maximum_mm3": no_refill_tolerance},
    )

    removed_in_smooth_gauge = removed.common(smooth_gauge)
    removed_outside_target = removed_in_smooth_gauge.cut(target_void)
    envelope_tolerance = float(
        tolerances["m4_removed_outside_authorized_cavity_volume_mm3_max"]
    )
    require_gate(
        shape_volume(removed_outside_target) <= envelope_tolerance,
        "M4_REMOVAL_CONTAINED_IN_AUTHORIZED_CAVITY_ENVELOPE",
        {
            "removed_inside_smooth_gauge_mm3": shape_volume(removed_in_smooth_gauge),
            "removed_outside_authorized_target_void_mm3": shape_volume(
                removed_outside_target
            ),
        },
        {"outside_volume_mm3_max": envelope_tolerance},
    )

    straight_enlargement = target_void.cut(old_void)
    expected_overlap = snapshot_shape.common(straight_enlargement).common(smooth_gauge)
    actual_minus_expected = difference_volume(removed_in_smooth_gauge, expected_overlap)
    expected_minus_actual = difference_volume(expected_overlap, removed_in_smooth_gauge)
    overlap_tolerance = float(
        tolerances["m4_intentional_overlap_symmetric_difference_volume_mm3_max"]
    )
    require_gate(
        actual_minus_expected <= overlap_tolerance
        and expected_minus_actual <= overlap_tolerance,
        "M4_SMOOTH_GAUGE_REMOVAL_EQUALS_AUTHORIZED_PROFILE_ENLARGEMENT",
        {
            "actual_removed_inside_smooth_gauge_mm3": shape_volume(
                removed_in_smooth_gauge
            ),
            "baseline_material_in_authorized_enlargement_and_gauge_mm3": shape_volume(
                expected_overlap
            ),
            "actual_minus_expected_mm3": actual_minus_expected,
            "expected_minus_actual_mm3": expected_minus_actual,
        },
        {"each_symmetric_difference_mm3_max": overlap_tolerance},
    )
    historical = float(
        contract["validation_001_disposition"][
            "reported_removed_inside_smooth_gauge_mm3"
        ]
    )
    historical_tolerance = float(
        tolerances["m4_historical_observation_volume_mm3_max"]
    )
    require_gate(
        abs(shape_volume(removed_in_smooth_gauge) - historical)
        <= historical_tolerance,
        "M4_HOLD_OBSERVATION_REPRODUCED",
        shape_volume(removed_in_smooth_gauge),
        {"value_mm3": historical, "absolute_error_mm3_max": historical_tolerance},
    )

    bearing_region = bearing_gauge.cut(target_void)
    snapshot_bearing = snapshot_shape.common(bearing_region)
    candidate_bearing = candidate_shape.common(bearing_region)
    snapshot_minus_candidate = difference_volume(snapshot_bearing, candidate_bearing)
    candidate_minus_snapshot = difference_volume(candidate_bearing, snapshot_bearing)
    bearing_tolerance = float(
        tolerances["m4_bearing_symmetric_difference_volume_mm3_max"]
    )
    require_gate(
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
    baseline_signature = extract_faceted_m4_signature(
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
    candidate_signature = extract_faceted_m4_signature(
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

    preservation_position = float(tolerances["m4_candidate_baseline_position_mm_max"])
    preservation_diameter = float(tolerances["m4_candidate_baseline_diameter_mm_max"])
    preservation_axis = float(
        tolerances["m4_candidate_baseline_axis_angular_error_deg_max"]
    )
    baseline_axis = vector(baseline_signature["axis"])
    candidate_axis = vector(candidate_signature["axis"])
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
    axis_delta = angle_deg(candidate_axis, baseline_axis, unoriented=True)
    require_gate(
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
    axis_error = angle_deg(candidate_axis, axis_u, unoriented=True)
    expected_angle = float(
        interface["rail_system"]["socket"][
            "expected_cross_bolt_angle_from_head_x_deg"
        ]
    )
    measured_angle = angle_deg(candidate_axis, App.Vector(1.0, 0.0, 0.0), unoriented=True)
    require_gate(
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
            "refilled_or_obstructed_volume_mm3": shape_volume(refilled_original_void),
            "maximum_mm3": no_refill_tolerance,
        },
        "authorized_profile_overlap": {
            "reported_validation_001_removed_inside_smooth_gauge_mm3": historical,
            "measured_removed_inside_smooth_gauge_mm3": shape_volume(
                removed_in_smooth_gauge
            ),
            "baseline_material_in_authorized_20_50_to_21_00_enlargement_and_gauge_mm3": shape_volume(
                expected_overlap
            ),
            "removed_outside_authorized_target_void_mm3": shape_volume(
                removed_outside_target
            ),
            "classification": "INTENTIONAL_20_50_TO_21_00_PROFILE_ENLARGEMENT_INTERSECTION",
        },
        "bearing_region_preservation": {
            "inspection_radius_mm": float(inspection["bearing_inspection_radius_mm"]),
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


def execute_validation(context: dict[str, Any]) -> dict[str, Any]:
    contract = context["contract"]
    parameters = context["parameters"]
    interface = context["interface"]
    input_paths = context["input_paths"]
    origin = context["origin"]
    axis_u = context["axis_u"]
    axis_v = context["axis_v"]
    axis_t = context["axis_t"]

    snapshot_shapes = raw_shape_digests(input_paths["no_op_snapshot"])
    candidate_shapes = raw_shape_digests(input_paths["candidate"])
    require_gate(
        set(snapshot_shapes) == set(candidate_shapes),
        "RAW_SHAPE_OBJECT_SET",
        {
            "missing": sorted(set(snapshot_shapes) - set(candidate_shapes)),
            "added": sorted(set(candidate_shapes) - set(snapshot_shapes)),
        },
        {"missing": [], "added": []},
    )
    protected_names = sorted(set(snapshot_shapes) - {TARGET_OBJECT})
    protected_mismatches = {
        name: {"snapshot": snapshot_shapes[name], "candidate": candidate_shapes[name]}
        for name in protected_names
        if snapshot_shapes[name] != candidate_shapes[name]
    }
    require_gate(
        not protected_mismatches,
        "PROTECTED_RAW_BREP_IDENTITY",
        protected_mismatches,
        {},
    )
    require_gate(
        snapshot_shapes[TARGET_OBJECT] != candidate_shapes[TARGET_OBJECT],
        "TARGET_RAW_BREP_CHANGED",
        {
            "snapshot": snapshot_shapes[TARGET_OBJECT],
            "candidate": candidate_shapes[TARGET_OBJECT],
        },
        "different target BREP digests",
    )

    snapshot_document = App.openDocument(str(input_paths["no_op_snapshot"]))
    candidate_document = App.openDocument(str(input_paths["candidate"]))
    try:
        snapshot_objects = {obj.Name: obj for obj in snapshot_document.Objects}
        candidate_objects = {obj.Name: obj for obj in candidate_document.Objects}
        require_gate(
            set(snapshot_objects) == set(candidate_objects),
            "FREECAD_OBJECT_SET",
            {
                "missing": sorted(set(snapshot_objects) - set(candidate_objects)),
                "added": sorted(set(candidate_objects) - set(snapshot_objects)),
            },
            {"missing": [], "added": []},
        )
        snapshot_target = snapshot_objects.get(TARGET_OBJECT)
        candidate_target = candidate_objects.get(TARGET_OBJECT)
        snapshot_c042 = snapshot_objects.get(PROTECTED_ROOT_OBJECT)
        candidate_c042 = candidate_objects.get(PROTECTED_ROOT_OBJECT)
        require_gate(
            all(
                item is not None
                for item in (
                    snapshot_target,
                    candidate_target,
                    snapshot_c042,
                    candidate_c042,
                )
            ),
            "REQUIRED_OBJECTS_PRESENT",
            {
                "snapshot_target": snapshot_target is not None,
                "candidate_target": candidate_target is not None,
                "snapshot_c042": snapshot_c042 is not None,
                "candidate_c042": candidate_c042 is not None,
            },
            "all true",
        )
        require_gate(
            candidate_target.TypeId == snapshot_target.TypeId == "Part::Feature",
            "TARGET_TYPE",
            {"snapshot": snapshot_target.TypeId, "candidate": candidate_target.TypeId},
            "Part::Feature",
        )
        require_gate(
            candidate_target.Label == snapshot_target.Label,
            "TARGET_LABEL",
            candidate_target.Label,
            snapshot_target.Label,
        )
        require_gate(
            placements_match(candidate_target.Placement, snapshot_target.Placement),
            "TARGET_PLACEMENT",
            placement_record(candidate_target.Placement),
            placement_record(snapshot_target.Placement),
        )

        snapshot_shape = snapshot_target.Shape.copy()
        target_shape = candidate_target.Shape.copy()
        c042_shape = candidate_c042.Shape.copy()
        candidate_metrics = shape_metrics(target_shape)
        require_candidate_health(candidate_metrics)
        construction = build_independent_expected_shape(
            snapshot_shape,
            parameters,
            origin,
            axis_u,
            axis_v,
            axis_t,
        )
        tolerances = contract["tolerances"]
        missing_volume = difference_volume(construction["expected"], target_shape)
        extra_volume = difference_volume(target_shape, construction["expected"])
        shape_tolerance = float(tolerances["shape_symmetric_difference_volume_mm3_max"])
        require_gate(
            missing_volume <= shape_tolerance and extra_volume <= shape_tolerance,
            "EXACT_ROUTE2_EXPECTED_GEOMETRY",
            {
                "expected_minus_candidate_mm3": missing_volume,
                "candidate_minus_expected_mm3": extra_volume,
            },
            {"each_mm3_max": shape_tolerance},
        )

        added = target_shape.cut(snapshot_shape)
        removed = snapshot_shape.cut(target_shape)
        added_outside_old_void = difference_volume(added, construction["old_void"])
        removed_outside_target_void = difference_volume(
            removed, construction["target_void"]
        )
        exterior_tolerance = float(
            tolerances["change_outside_authorized_socket_envelope_mm3_max"]
        )
        require_gate(
            added_outside_old_void <= exterior_tolerance
            and removed_outside_target_void <= exterior_tolerance,
            "ZERO_EXTERIOR_DEVIATION",
            {
                "added_outside_old_void_mm3": added_outside_old_void,
                "removed_outside_target_void_mm3": removed_outside_target_void,
            },
            {"each_mm3_max": exterior_tolerance},
        )

        candidate_common = target_shape.common(c042_shape)
        snapshot_common = snapshot_shape.common(snapshot_c042.Shape)
        expected_common = float(parameters["protected_root"]["exact_common_volume_mm3"])
        common_tolerance = float(tolerances["protected_common_volume_mm3"])
        candidate_common_volume = shape_volume(candidate_common)
        snapshot_common_volume = shape_volume(snapshot_common)
        require_gate(
            abs(candidate_common_volume - expected_common) <= common_tolerance
            and abs(candidate_common_volume - snapshot_common_volume)
            <= common_tolerance,
            "C002_C042_COMMON_PRESERVATION",
            {
                "candidate_mm3": candidate_common_volume,
                "snapshot_mm3": snapshot_common_volume,
            },
            {"expected_mm3": expected_common, "tolerance_mm3": common_tolerance},
        )
        ligament = float(construction["review_void"].distToShape(candidate_common)[0])
        ligament_minimum = float(
            parameters["profile"]["finished_minimum_cavity_to_root_ligament_mm"]
        )
        ligament_epsilon = float(tolerances["distance_numeric_epsilon_mm"])
        require_gate(
            ligament + ligament_epsilon >= ligament_minimum,
            "CAVITY_TO_ROOT_LIGAMENT",
            ligament,
            {"minimum_mm": ligament_minimum, "numeric_epsilon_mm": ligament_epsilon},
        )

        m4_metrics = evaluate_m4_preservation(
            snapshot_shape,
            target_shape,
            construction["target_void"],
            construction["old_void"],
            origin,
            axis_u,
            axis_v,
            axis_t,
            parameters,
            contract,
            interface,
        )

        candidate_frame = measure_straight_cavity_frame(
            target_shape,
            origin,
            axis_u,
            axis_v,
            axis_t,
            float(parameters["profile"]["straight_across_flats_mm"]) / 2.0,
        )
        snapshot_frame = measure_straight_cavity_frame(
            snapshot_shape,
            origin,
            axis_u,
            axis_v,
            axis_t,
            float(parameters["profile"]["current_straight_across_flats_mm"]) / 2.0,
        )
        measured_t = vector(candidate_frame["measured_t_axis"])
        measured_u = vector(candidate_frame["measured_u_axis"])
        snapshot_t = vector(snapshot_frame["measured_t_axis"])
        snapshot_u = vector(snapshot_frame["measured_u_axis"])
        frame_axis_delta = angle_deg(measured_t, snapshot_t)
        frame_roll_delta = angle_deg(measured_u, snapshot_u)
        frame_limit = float(
            tolerances["socket_frame_preservation_angular_error_deg_max"]
        )
        require_gate(
            frame_axis_delta <= frame_limit and frame_roll_delta <= frame_limit,
            "SOCKET_AXIS_AND_ROLL_PRESERVATION",
            {"axis_delta_deg": frame_axis_delta, "roll_delta_deg": frame_roll_delta},
            {"each_maximum_deg": frame_limit},
        )

        m2_t = normalized(
            vector(interface["rail_system"]["accepted_axes_head"]["right"]),
            "M2 right rail axis",
        )
        head_x = App.Vector(1.0, 0.0, 0.0)
        m2_roll_u = normalized(
            head_x - m2_t * float(head_x.dot(m2_t)),
            "M2 head-x-projected roll",
        )
        axis_limit = float(
            interface["validation_tolerances"]["rail_axis_angular_error_deg_max"]
        )
        roll_limit = float(tolerances["socket_roll_angular_error_deg_max"])
        measured_to_m2 = angle_deg(measured_t, m2_t)
        measured_roll_to_m2 = angle_deg(measured_u, m2_roll_u)
        require_gate(
            measured_to_m2 <= axis_limit and measured_roll_to_m2 <= roll_limit,
            "CANDIDATE_SOCKET_FRAME_MATCHES_FROZEN_M2",
            {
                "axis_error_deg": measured_to_m2,
                "roll_error_deg": measured_roll_to_m2,
            },
            {"axis_max_deg": axis_limit, "roll_max_deg": roll_limit},
        )

        immutable_after: dict[str, str] = {}
        for label, path in input_paths.items():
            observed = sha256_file(path)
            expected = contract["inputs"][label]["sha256"]
            require_gate(
                observed == expected,
                f"{label.upper()}_CHANGED_DURING_VALIDATION",
                observed,
                expected,
            )
            immutable_after[label] = observed

        return {
            "input_integrity": context["input_records"],
            "validator": context["validator_record"],
            "tooling_dependency": context["dependency_record"],
            "contract_sha256": sha256_file(context["contract_path"]),
            "runtime": context["runtime"],
            "numeric_contract": context["numeric_record"],
            "validation_001_disposition": context["hold_evidence"],
            "target": {
                "object": TARGET_OBJECT,
                "health": candidate_metrics,
                "placement": placement_record(candidate_target.Placement),
            },
            "route2_geometry": {
                "expected_minus_candidate_mm3": missing_volume,
                "candidate_minus_expected_mm3": extra_volume,
                "status": "PASS",
            },
            "localized_change": {
                "added_material_mm3": shape_volume(added),
                "removed_material_mm3": shape_volume(removed),
                "added_outside_old_void_mm3": added_outside_old_void,
                "removed_outside_target_void_mm3": removed_outside_target_void,
                "status": "PASS",
            },
            "protected_root": {
                "candidate_common_volume_mm3": candidate_common_volume,
                "snapshot_common_volume_mm3": snapshot_common_volume,
                "cavity_to_root_ligament_mm": ligament,
                "status": "PASS",
            },
            "m4_tunnel": m4_metrics,
            "m2_axis_and_roll": {
                "interface_revision": interface["metal_handoff_record"]["revision"],
                "frozen_axis": vector_values(m2_t),
                "candidate_axis": vector_values(measured_t),
                "frozen_roll": vector_values(m2_roll_u),
                "candidate_roll": vector_values(measured_u),
                "candidate_snapshot_axis_delta_deg": frame_axis_delta,
                "candidate_snapshot_roll_delta_deg": frame_roll_delta,
                "candidate_to_m2_axis_error_deg": measured_to_m2,
                "candidate_to_m2_roll_error_deg": measured_roll_to_m2,
                "axis_changed": False,
                "roll_changed": False,
                "status": "PASS",
            },
            "raw_shape_preservation": {
                "protected_checked_count": len(protected_names),
                "protected_mismatches": protected_mismatches,
                "status": "PASS",
            },
            "immutable_hashes_after": immutable_after,
        }
    finally:
        App.closeDocument(candidate_document.Name)
        App.closeDocument(snapshot_document.Name)


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
        "m4_gauge_t_range_mm": context["m4_gauge_t_range_mm"],
        "straight_profile_t_range_mm": context["straight_profile_t_range_mm"],
        "next_action": "await explicit authorization for --execute-authorized",
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        context = preflight_context(args)
    except GateFailure as exc:
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
        "candidate_modified": False,
        "generator_invoked": False,
        "automatic_retry": False,
        "automatic_healing_used": False,
        "full_system_release": False,
        "release_holds": context["contract"]["release_holds"],
    }
    exit_code = 1
    try:
        metrics = execute_validation(context)
        result.update(
            {
                "status": "PASS",
                "candidate_disposition": "TECHNICAL_VALIDATION_PASS__NO_PROMOTION",
                "failed_gate": None,
                "metrics": metrics,
            }
        )
        exit_code = 0
    except GateFailure as exc:
        result.update(
            {
                "status": "FAIL",
                "candidate_disposition": HOLD_CLASSIFICATION,
                "failed_gate": exc.record(),
            }
        )
    except Exception as exc:
        result.update(
            {
                "status": "FAIL",
                "candidate_disposition": HOLD_CLASSIFICATION,
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
