#!/usr/bin/env python3
"""Final bilateral-facet release validator for the approved C002 V2 candidate.

Validation-003 paired co-directional M4 bearing-face fragments from opposite U
sides as though they were circumferential neighbors.  This tooling-only
revision partitions the selected radial faces by their axial bearing interval,
reconstructs one circumferential polygon per side, and compares each candidate
side only with the corresponding V34 side.  All physical tolerances and all
other release gates remain unchanged.

The candidate and snapshot are opened read-only.  This module never saves an
FCStd document, invokes a generator, repairs geometry, exports, or promotes.
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

import validate_c002_rounded_terminal_release_v2_003 as previous  # noqa: E402


core = previous.core
VALIDATION_ID = "c002-rounded-terminal-profile-prototype-v2-release-validation-004"
VALIDATION_MODE = "read_only_independent_release_validation"
PREVIOUS_DEFECT = "VALIDATOR_DEFECT__BASELINE_AXIAL_FACE_FRAGMENT_PAIRING"
CANDIDATE_DISPOSITION = "CANDIDATE_UNCHANGED"
PASS_CLASSIFICATION = "RELEASE_VALIDATION_PASS__C002_ONLY"
EXPECTED_REMOVAL_SET = previous.EXPECTED_REMOVAL_SET
INVALID_REMOVAL_SET = previous.INVALID_REMOVAL_SET

GateFailure = core.GateFailure
axis_cylinder = core.axis_cylinder
difference_volume = core.difference_volume
shape_volume = core.shape_volume


class SignatureUnavailable(RuntimeError):
    """A failed signature prerequisite prevents dependent reconstruction."""


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--freecad-appdir", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--execute-authorized", action="store_true")
    return parser.parse_args(argv)


def _angle_gap(first: float, second: float) -> float:
    delta = abs(first - second) % (2.0 * math.pi)
    return min(delta, 2.0 * math.pi - delta)


def _public_face(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if not key.startswith("_")}


def partition_faceted_m4_bearing_faces(
    shape: Part.Shape,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    station_t: float,
    nominal_radius: float,
    cavity_half_width: float,
    inspection: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Select radial M4 faces and partition them by their inner U boundary."""

    support_band = float(inspection["facet_support_search_band_mm"])
    axial_dot_min = float(inspection["facet_edge_axis_dot_search_min"])
    minimum_u_span = float(inspection["facet_face_u_span_search_min_mm"])
    inner_edge_tolerance = float(
        inspection["bearing_inner_edge_match_error_mm_max"]
    )
    groups: dict[str, list[dict[str, Any]]] = {"left": [], "right": []}
    unpartitioned: list[dict[str, Any]] = []

    for index, face in enumerate(shape.Faces, start=1):
        if "plane" not in type(face.Surface).__name__.lower():
            continue
        coordinates = [
            core.local_coordinates(vertex.Point, origin, axis_u, axis_v, axis_t)
            for vertex in face.Vertexes
        ]
        if not coordinates:
            continue
        u_values = [item[0] for item in coordinates]
        if max(u_values) - min(u_values) < minimum_u_span:
            continue

        normal = core.face_normal(face)
        n_u = float(normal.dot(axis_u))
        n_v = float(normal.dot(axis_v))
        n_t = float(normal.dot(axis_t))
        radial_norm = math.hypot(n_v, n_t)
        if radial_norm <= 1.0e-12:
            continue
        centroid_u, centroid_v, centroid_t = core.local_coordinates(
            face.CenterOfMass, origin, axis_u, axis_v, axis_t
        )
        support = (
            n_u * centroid_u
            + n_v * centroid_v
            + n_t * (centroid_t - station_t)
        ) / radial_norm
        n_u /= radial_norm
        n_v /= radial_norm
        n_t /= radial_norm
        if support < 0.0:
            support = -support
            n_u = -n_u
            n_v = -n_v
            n_t = -n_t
        if abs(support - nominal_radius) > support_band:
            continue
        if (
            math.hypot(centroid_v, centroid_t - station_t)
            > nominal_radius + support_band
        ):
            continue

        u_min = min(u_values)
        u_max = max(u_values)
        axial_directions: list[App.Vector] = []
        for edge in face.Edges:
            if len(edge.Vertexes) != 2:
                continue
            delta = edge.Vertexes[1].Point - edge.Vertexes[0].Point
            if float(delta.Length) <= minimum_u_span:
                continue
            direction = core.normalized(delta, "M4 facet axial edge")
            if abs(float(direction.dot(axis_u))) < axial_dot_min:
                continue
            axial_directions.append(core.aligned(direction, axis_u))

        record = {
            "face_identifier": f"Face{index}",
            "normal_local": [n_u, n_v, n_t],
            "support_at_u0_from_expected_center_mm": support,
            "u_min_mm": u_min,
            "u_max_mm": u_max,
            "u_span_mm": u_max - u_min,
            "face_area_mm2": float(face.Area),
            "left_inner_edge_error_mm": abs(u_max + cavity_half_width),
            "right_inner_edge_error_mm": abs(u_min - cavity_half_width),
            "_axial_directions": axial_directions,
        }
        is_left = record["left_inner_edge_error_mm"] <= inner_edge_tolerance
        is_right = record["right_inner_edge_error_mm"] <= inner_edge_tolerance
        if is_left == is_right:
            unpartitioned.append(_public_face(record))
        else:
            groups["left" if is_left else "right"].append(record)

    core.require_gate(
        not unpartitioned,
        "M4_BEARING_FACE_PARTITION",
        unpartitioned,
        "every selected radial face belongs to exactly one axial bearing side",
    )
    return groups


def _bearing_summary(
    side: str, records: list[dict[str, Any]]
) -> dict[str, Any]:
    lengths = sorted(float(item["u_span_mm"]) for item in records)
    core.require_gate(
        bool(lengths) and min(lengths) > 0.0,
        f"M4_{side.upper()}_BEARING_REMAINS_PRINTED",
        [_public_face(item) for item in records],
        "one positive printed bearing interval for every side facet",
    )
    if not lengths:
        raise SignatureUnavailable(f"no {side} M4 bearing faces")
    return {
        "facet_face_count": len(records),
        "minimum_printed_bearing_length_wall_thickness_mm": min(lengths),
        "maximum_printed_bearing_length_wall_thickness_mm": max(lengths),
        "mean_printed_bearing_length_wall_thickness_mm": statistics.fmean(lengths),
        "per_face_lengths_mm": lengths,
        "face_identifiers": sorted(item["face_identifier"] for item in records),
    }


def _cluster_circumferential_fragments(
    side: str,
    records: list[dict[str, Any]],
    inspection: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Collapse adjacent topology fragments without merging physical duplicates."""

    fragments: list[dict[str, Any]] = []
    for record in records:
        angle = math.atan2(record["normal_local"][2], record["normal_local"][1])
        if angle < 0.0:
            angle += 2.0 * math.pi
        fragments.append(
            {
                "angle_rad": angle,
                "normal_u": record["normal_local"][0],
                "normal_v": record["normal_local"][1],
                "normal_t": record["normal_local"][2],
                "support_mm": record[
                    "support_at_u0_from_expected_center_mm"
                ],
                "face_identifier": record["face_identifier"],
                "u_min_mm": record["u_min_mm"],
                "u_max_mm": record["u_max_mm"],
                "area_mm2": max(float(record["face_area_mm2"]), 1.0e-15),
            }
        )
    fragments.sort(key=lambda item: item["angle_rad"])

    angular_limit = math.radians(
        float(inspection["facet_plane_merge_angular_error_deg_max"])
    )
    duplicate_or_parallel: list[dict[str, Any]] = []
    for position, first in enumerate(fragments):
        second = fragments[(position + 1) % len(fragments)]
        angle_delta = _angle_gap(first["angle_rad"], second["angle_rad"])
        if angle_delta <= angular_limit:
            duplicate_or_parallel.append(
                {
                    "first": first,
                    "second": second,
                    "angle_delta_deg": math.degrees(angle_delta),
                }
            )
    core.require_gate(
        not duplicate_or_parallel,
        f"M4_{side.upper()}_NO_DUPLICATE_OR_PARALLEL_FACETS",
        duplicate_or_parallel,
        {
            "maximum_parallel_angle_delta_deg": float(
                inspection["facet_plane_merge_angular_error_deg_max"]
            ),
            "rule": "a parallel duplicate within one axial side is invalid",
        },
    )
    if duplicate_or_parallel:
        raise SignatureUnavailable(f"duplicate or parallel {side} M4 facets")

    circular_gaps = [
        (
            fragments[(index + 1) % len(fragments)]["angle_rad"]
            - fragments[index]["angle_rad"]
        )
        % (2.0 * math.pi)
        for index in range(len(fragments))
    ]
    median_gap = statistics.median(circular_gaps)
    fragmented = min(circular_gaps) < median_gap / 2.0
    boundary_threshold = median_gap / 2.0 if fragmented else 0.0
    boundary_indices = {
        index
        for index, gap in enumerate(circular_gaps)
        if not fragmented or gap >= boundary_threshold
    }
    start = (min(boundary_indices) + 1) % len(fragments)
    clusters: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    for step in range(len(fragments)):
        index = (start + step) % len(fragments)
        current.append(fragments[index])
        if index in boundary_indices:
            clusters.append(current)
            current = []
    if current:
        clusters.append(current)

    facets: list[dict[str, Any]] = []
    for cluster in clusters:
        weight = float(len(cluster))
        normal_v = sum(item["normal_v"] for item in cluster) / weight
        normal_t = sum(item["normal_t"] for item in cluster) / weight
        radial_length = math.hypot(normal_v, normal_t)
        normal_v /= radial_length
        normal_t /= radial_length
        angle = math.atan2(normal_t, normal_v)
        if angle < 0.0:
            angle += 2.0 * math.pi
        source_faces = sorted(item["face_identifier"] for item in cluster)
        facets.append(
            {
                "angle_rad": angle,
                "normal_v": normal_v,
                "normal_t": normal_t,
                "support_mm": sum(item["support_mm"] for item in cluster) / weight,
                "face_identifier": "+".join(source_faces),
                "source_face_identifiers": source_faces,
                "source_fragment_count": len(cluster),
                "u_min_mm": min(item["u_min_mm"] for item in cluster),
                "u_max_mm": max(item["u_max_mm"] for item in cluster),
            }
        )
    facets.sort(key=lambda item: item["angle_rad"])
    return facets, {
        "method": "cyclic angular-gap partition plus equal-weight plane coefficients",
        "selected_face_fragment_count": len(fragments),
        "reconstructed_facet_count": len(facets),
        "median_circular_gap_rad": median_gap,
        "fragment_boundary_threshold_rad": boundary_threshold,
        "fragmented_faces_detected": fragmented,
        "physical_acceptance_tolerance_used_for_clustering": False,
    }


def _fit_side_axis_from_facet_normals(
    side: str,
    records: list[dict[str, Any]],
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
) -> App.Vector:
    """Fit the common plane-normal null direction independently per side."""

    aa = sum(item["normal_local"][1] ** 2 for item in records)
    ab = sum(
        item["normal_local"][1] * item["normal_local"][2] for item in records
    )
    cc = sum(item["normal_local"][2] ** 2 for item in records)
    rhs_v = -sum(
        item["normal_local"][0] * item["normal_local"][1] for item in records
    )
    rhs_t = -sum(
        item["normal_local"][0] * item["normal_local"][2] for item in records
    )
    determinant = aa * cc - ab * ab
    core.require_gate(
        abs(determinant) > 1.0e-9,
        f"M4_{side.upper()}_FACET_NORMAL_AXIS_FIT",
        determinant,
        "non-degenerate circumferential plane-normal system",
    )
    if abs(determinant) <= 1.0e-9:
        raise SignatureUnavailable(f"degenerate {side} M4 axis fit")
    local_v = (rhs_v * cc - ab * rhs_t) / determinant
    local_t = (aa * rhs_t - ab * rhs_v) / determinant
    measured_axis = axis_u + axis_v * local_v + axis_t * local_t
    return core.aligned(
        core.normalized(measured_axis, f"fitted {side} M4 axis"), axis_u
    )


def reconstruct_circumferential_side_signature(
    side: str,
    records: list[dict[str, Any]],
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    station_t: float,
    cavity_half_width: float,
    inspection: dict[str, Any],
) -> dict[str, Any]:
    """Reconstruct one circumferential polygon from one axial bearing side."""

    minimum_facets = int(inspection["minimum_faceted_tunnel_planes"])
    core.require_gate(
        len(records) >= minimum_facets,
        f"M4_{side.upper()}_FACETED_TUNNEL_SIGNATURE",
        {
            "selected_face_fragment_count": len(records),
            "selected_faces": [_public_face(item) for item in records],
        },
        {"minimum_selected_face_fragment_count": minimum_facets},
    )
    if len(records) < minimum_facets:
        raise SignatureUnavailable(f"insufficient {side} M4 facet faces")

    facets, clustering = _cluster_circumferential_fragments(
        side, records, inspection
    )
    core.require_gate(
        len(facets) >= minimum_facets,
        f"M4_{side.upper()}_RECONSTRUCTED_FACET_COUNT",
        clustering,
        {"minimum_reconstructed_facet_count": minimum_facets},
    )
    if len(facets) < minimum_facets:
        raise SignatureUnavailable(f"insufficient reconstructed {side} M4 facets")

    axial_directions = [
        direction
        for record in records
        for direction in record["_axial_directions"]
    ]
    core.require_gate(
        bool(axial_directions),
        f"M4_{side.upper()}_FACET_AXIS_SIGNATURE",
        {"axial_edge_signature_count": len(axial_directions)},
        "one or more tunnel-facet axial edges",
    )
    if not axial_directions:
        raise SignatureUnavailable(f"no {side} M4 axial edge signatures")
    measured_axis = _fit_side_axis_from_facet_normals(
        side, records, axis_u, axis_v, axis_t
    )
    clustering["axial_edge_signature_count"] = len(axial_directions)
    clustering["axis_measurement_method"] = "least-squares facet-plane null direction"

    vertices: list[tuple[float, float]] = []
    for position, first in enumerate(facets):
        second = facets[(position + 1) % len(facets)]
        a, b, c = first["normal_v"], first["normal_t"], first["support_mm"]
        d, e, f = second["normal_v"], second["normal_t"], second["support_mm"]
        determinant = a * e - b * d
        core.require_gate(
            abs(determinant) > 1.0e-9,
            f"M4_{side.upper()}_FACET_PLANE_INTERSECTION",
            {"first": first, "second": second, "determinant": determinant},
            "adjacent non-parallel facet planes within the same axial side",
        )
        if abs(determinant) <= 1.0e-9:
            raise SignatureUnavailable(f"invalid {side} facet-plane intersection")
        vertices.append(
            ((c * e - b * f) / determinant, (a * f - c * d) / determinant)
        )

    center_v = statistics.fmean(item[0] for item in vertices)
    center_tau = statistics.fmean(item[1] for item in vertices)
    diameter = 0.0
    for first in vertices:
        for second in vertices:
            diameter = max(
                diameter,
                math.hypot(first[0] - second[0], first[1] - second[1]),
            )

    return {
        "side": side,
        "geometry_kind": "faceted M4 tunnel axial bearing side",
        "cavity_half_width_mm": cavity_half_width,
        "facet_plane_count": len(facets),
        "selected_face_count": len(records),
        "selected_face_identifiers": sorted(
            item["face_identifier"] for item in records
        ),
        "fragment_reconstruction": clustering,
        "facet_order": facets,
        "center_local_v_mm": center_v,
        "station_local_t_mm": station_t + center_tau,
        "axis": core.vector_values(measured_axis),
        "clearance_circumdiameter_mm": diameter,
        "support_minimum_mm": min(item["support_mm"] for item in facets),
        "support_maximum_mm": max(item["support_mm"] for item in facets),
        "remaining_printed_bearing": _bearing_summary(side, records),
    }


def extract_bilateral_faceted_m4_signature(
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
    groups = partition_faceted_m4_bearing_faces(
        shape,
        origin,
        axis_u,
        axis_v,
        axis_t,
        station_t,
        nominal_radius,
        cavity_half_width,
        inspection,
    )
    return {
        "geometry_kind": "bilateral faceted M4 tunnel",
        "partition_rule": (
            "left: u_max ~= -cavity_half_width; "
            "right: u_min ~= +cavity_half_width"
        ),
        "left": reconstruct_circumferential_side_signature(
            "left",
            groups["left"],
            axis_u,
            axis_v,
            axis_t,
            station_t,
            cavity_half_width,
            inspection,
        ),
        "right": reconstruct_circumferential_side_signature(
            "right",
            groups["right"],
            axis_u,
            axis_v,
            axis_t,
            station_t,
            cavity_half_width,
            inspection,
        ),
    }


def _cyclic_facet_alignment(
    baseline: list[dict[str, Any]], candidate: list[dict[str, Any]]
) -> dict[str, Any]:
    if len(baseline) != len(candidate) or not baseline:
        return {
            "cyclic_shift": None,
            "maximum_angle_delta_deg": math.inf,
            "maximum_support_delta_mm": math.inf,
            "pairs": [],
        }
    best: dict[str, Any] | None = None
    for shift in range(len(baseline)):
        pairs = []
        for index, baseline_facet in enumerate(baseline):
            candidate_facet = candidate[(index + shift) % len(candidate)]
            pairs.append(
                {
                    "baseline_face_identifier": baseline_facet[
                        "face_identifier"
                    ],
                    "candidate_face_identifier": candidate_facet[
                        "face_identifier"
                    ],
                    "angle_delta_deg": math.degrees(
                        _angle_gap(
                            baseline_facet["angle_rad"],
                            candidate_facet["angle_rad"],
                        )
                    ),
                    "support_delta_mm": abs(
                        baseline_facet["support_mm"]
                        - candidate_facet["support_mm"]
                    ),
                }
            )
        record = {
            "cyclic_shift": shift,
            "maximum_angle_delta_deg": max(
                item["angle_delta_deg"] for item in pairs
            ),
            "maximum_support_delta_mm": max(
                item["support_delta_mm"] for item in pairs
            ),
            "pairs": pairs,
        }
        score = (
            record["maximum_angle_delta_deg"],
            record["maximum_support_delta_mm"],
        )
        if best is None or score < (
            best["maximum_angle_delta_deg"],
            best["maximum_support_delta_mm"],
        ):
            best = record
    assert best is not None
    return best


def compare_bilateral_signatures(
    baseline_signature: dict[str, Any],
    candidate_signature: dict[str, Any],
    axis_u: App.Vector,
    station: float,
    diameter: float,
    contract: dict[str, Any],
    interface: dict[str, Any],
) -> dict[str, Any]:
    tolerances = contract["tolerances"]
    inspection = contract["m4_inspection"]
    position_limit = float(tolerances["m4_candidate_baseline_position_mm_max"])
    diameter_limit = float(tolerances["m4_candidate_baseline_diameter_mm_max"])
    axis_limit = float(
        tolerances["m4_candidate_baseline_axis_angular_error_deg_max"]
    )
    order_angle_limit = float(
        inspection["facet_plane_merge_angular_error_deg_max"]
    )
    support_limit = float(inspection["facet_plane_merge_offset_error_mm_max"])
    interface_dimension_limit = float(
        interface["validation_tolerances"]["derived_dimension_error_mm_max"]
    )
    interface_axis_limit = float(
        interface["validation_tolerances"]["rail_axis_angular_error_deg_max"]
    )
    expected_angle = float(
        interface["rail_system"]["socket"][
            "expected_cross_bolt_angle_from_head_x_deg"
        ]
    )
    head_x = App.Vector(1.0, 0.0, 0.0)
    comparisons: dict[str, Any] = {}

    for side in ("left", "right"):
        baseline = baseline_signature[side]
        candidate = candidate_signature[side]
        facet_count_match = (
            candidate["facet_plane_count"] == baseline["facet_plane_count"]
        )
        core.require_gate(
            facet_count_match,
            f"M4_{side.upper()}_FACET_COUNT_MATCHES_BASELINE",
            {
                "baseline": baseline["facet_plane_count"],
                "candidate": candidate["facet_plane_count"],
            },
            "exact match",
        )
        alignment = _cyclic_facet_alignment(
            baseline["facet_order"], candidate["facet_order"]
        )
        core.require_gate(
            facet_count_match
            and alignment["maximum_angle_delta_deg"] <= order_angle_limit
            and alignment["maximum_support_delta_mm"] <= support_limit,
            f"M4_{side.upper()}_FACET_ORDER_AND_SUPPORT_MATCH_BASELINE",
            alignment,
            {
                "cyclic_order": "same orientation and exact facet count",
                "maximum_angle_delta_deg": order_angle_limit,
                "maximum_support_delta_mm": support_limit,
            },
        )

        baseline_axis = core.vector(baseline["axis"])
        candidate_axis = core.vector(candidate["axis"])
        center_delta = math.hypot(
            float(candidate["center_local_v_mm"])
            - float(baseline["center_local_v_mm"]),
            float(candidate["station_local_t_mm"])
            - float(baseline["station_local_t_mm"]),
        )
        measured_diameter_delta = abs(
            float(candidate["clearance_circumdiameter_mm"])
            - float(baseline["clearance_circumdiameter_mm"])
        )
        measured_axis_delta = core.angle_deg(
            candidate_axis, baseline_axis, unoriented=True
        )
        core.require_gate(
            center_delta <= position_limit
            and measured_diameter_delta <= diameter_limit
            and measured_axis_delta <= axis_limit,
            f"M4_{side.upper()}_CANDIDATE_MATCHES_BASELINE_SIGNATURE",
            {
                "center_and_station_delta_mm": center_delta,
                "diameter_delta_mm": measured_diameter_delta,
                "axis_delta_deg": measured_axis_delta,
            },
            {
                "center_and_station_delta_mm_max": position_limit,
                "diameter_delta_mm_max": diameter_limit,
                "axis_delta_deg_max": axis_limit,
            },
        )

        center_error = abs(float(candidate["center_local_v_mm"]))
        station_error = abs(float(candidate["station_local_t_mm"]) - station)
        absolute_diameter_error = abs(
            float(candidate["clearance_circumdiameter_mm"]) - diameter
        )
        absolute_axis_error = core.angle_deg(
            candidate_axis, axis_u, unoriented=True
        )
        measured_angle = core.angle_deg(
            candidate_axis, head_x, unoriented=True
        )
        core.require_gate(
            center_error <= interface_dimension_limit
            and station_error <= interface_dimension_limit
            and absolute_diameter_error <= interface_dimension_limit
            and absolute_axis_error <= interface_axis_limit
            and abs(measured_angle - expected_angle) <= interface_axis_limit,
            f"M4_{side.upper()}_CANDIDATE_MATCHES_FROZEN_INTERFACE",
            {
                "center_v_error_mm": center_error,
                "station_t_error_mm": station_error,
                "clearance_diameter_error_mm": absolute_diameter_error,
                "axis_to_contract_u_deg": absolute_axis_error,
                "cross_bolt_angle_from_head_x_deg": measured_angle,
                "cross_bolt_angle_error_deg": abs(measured_angle - expected_angle),
            },
            {
                "center_v_mm": 0.0,
                "station_t_mm": station,
                "clearance_diameter_mm": diameter,
                "dimension_error_mm_max": interface_dimension_limit,
                "axis_angular_error_deg_max": interface_axis_limit,
                "cross_bolt_angle_from_head_x_deg": expected_angle,
            },
        )
        comparisons[side] = {
            "facet_count_match": facet_count_match,
            "facet_order_and_support": alignment,
            "candidate_baseline_deltas": {
                "center_and_station_mm": center_delta,
                "diameter_mm": measured_diameter_delta,
                "axis_deg": measured_axis_delta,
            },
            "frozen_interface_match": {
                "center_v_mm": candidate["center_local_v_mm"],
                "station_t_mm": candidate["station_local_t_mm"],
                "axis": candidate["axis"],
                "clearance_circumdiameter_mm": candidate[
                    "clearance_circumdiameter_mm"
                ],
                "cross_bolt_angle_from_head_x_deg": measured_angle,
                "status": "PASS",
            },
            "remaining_printed_bearing": candidate[
                "remaining_printed_bearing"
            ],
        }
    return comparisons


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
    """Retain validation-003 M4 gates and replace only signature extraction."""

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

    baseline_signature = extract_bilateral_faceted_m4_signature(
        snapshot_shape,
        origin,
        axis_u,
        axis_v,
        axis_t,
        station,
        radius,
        float(profile["current_straight_across_flats_mm"]) / 2.0,
        inspection,
    )
    candidate_signature = extract_bilateral_faceted_m4_signature(
        candidate_shape,
        origin,
        axis_u,
        axis_v,
        axis_t,
        station,
        radius,
        float(profile["straight_across_flats_mm"]) / 2.0,
        inspection,
    )
    comparisons = compare_bilateral_signatures(
        baseline_signature,
        candidate_signature,
        axis_u,
        station,
        diameter,
        contract,
        interface,
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
        "bilateral_candidate_baseline_comparison": comparisons,
        "remaining_printed_bearing_length_wall_thickness": {
            side: candidate_signature[side]["remaining_printed_bearing"]
            for side in ("left", "right")
        },
        "frozen_interface_revision": interface["metal_handoff_record"][
            "revision"
        ],
    }


def verify_validation_003_defect(context: dict[str, Any]) -> dict[str, Any]:
    disposition = context["contract"]["validation_003_disposition"]
    core.require_gate(
        disposition.get("classification") == PREVIOUS_DEFECT
        and disposition.get("candidate_disposition") == CANDIDATE_DISPOSITION,
        "VALIDATION_003_RECLASSIFICATION",
        disposition,
        {
            "classification": PREVIOUS_DEFECT,
            "candidate_disposition": CANDIDATE_DISPOSITION,
        },
    )
    report = core.load_json(context["input_paths"]["validation_003_report"])
    failed = report.get("failed_gate") or {}
    actual = failed.get("actual") or {}
    first = actual.get("first") or {}
    second = actual.get("second") or {}
    first_face = ((first.get("faces") or [{}])[0]).get("face_identifier")
    second_face = ((second.get("faces") or [{}])[0]).get("face_identifier")
    first_u_max = float(
        ((first.get("faces") or [{}])[0]).get("u_max_mm", math.nan)
    )
    second_u_min = float(
        ((second.get("faces") or [{}])[0]).get("u_min_mm", math.nan)
    )
    core.require_gate(
        report.get("status") == "FAIL"
        and report.get("candidate_modified") is False
        and report.get("generator_invoked") is False
        and failed.get("gate") == "M4_FACET_PLANE_INTERSECTION"
        and first_face == "Face150"
        and second_face == "Face151"
        and first_u_max < 0.0
        and second_u_min > 0.0,
        "VALIDATION_003_DEFECT_EVIDENCE",
        {
            "status": report.get("status"),
            "candidate_modified": report.get("candidate_modified"),
            "generator_invoked": report.get("generator_invoked"),
            "gate": failed.get("gate"),
            "first_face": first_face,
            "first_u_max_mm": first_u_max,
            "second_face": second_face,
            "second_u_min_mm": second_u_min,
            "determinant": actual.get("determinant"),
        },
        "Face150 on negative U and Face151 on positive U were incorrectly paired",
    )
    validation_003_contract = core.load_json(
        context["input_paths"]["validation_003_contract"]
    )
    core.require_gate(
        validation_003_contract.get("validation_id")
        == "c002-rounded-terminal-profile-prototype-v2-release-validation-003"
        and validation_003_contract["visual_approval"]["candidate_sha256"]
        == context["input_records"]["candidate"]["sha256"],
        "VALIDATION_003_CONTRACT_IDENTITY",
        {
            "validation_id": validation_003_contract.get("validation_id"),
            "candidate_sha256": validation_003_contract.get(
                "visual_approval", {}
            ).get("candidate_sha256"),
        },
        {
            "validation_id": (
                "c002-rounded-terminal-profile-prototype-v2-release-validation-003"
            ),
            "candidate_sha256": context["input_records"]["candidate"]["sha256"],
        },
    )
    core.require_gate(
        context["contract"]["tolerances"]
        == validation_003_contract["tolerances"]
        and context["contract"]["m4_inspection"]
        == validation_003_contract["m4_inspection"],
        "PHYSICAL_TOLERANCES_UNCHANGED_FROM_VALIDATION_003",
        {
            "tolerances": context["contract"]["tolerances"],
            "m4_inspection": context["contract"]["m4_inspection"],
        },
        {
            "tolerances": validation_003_contract["tolerances"],
            "m4_inspection": validation_003_contract["m4_inspection"],
        },
    )
    return {
        "classification": PREVIOUS_DEFECT,
        "candidate_disposition": CANDIDATE_DISPOSITION,
        "candidate_modified": False,
        "evidence": {
            "failed_gate": failed.get("gate"),
            "negative_u_fragment": first_face,
            "positive_u_fragment": second_face,
            "determinant": actual.get("determinant"),
        },
        "physical_failure": False,
    }


def preflight_context(args: argparse.Namespace) -> dict[str, Any]:
    original_id = previous.VALIDATION_ID
    original_file = previous.__file__
    previous.VALIDATION_ID = VALIDATION_ID
    previous.__file__ = __file__
    try:
        context = previous.preflight_context(args)
    finally:
        previous.VALIDATION_ID = original_id
        previous.__file__ = original_file

    dependency_path, dependency_record = core.verify_file_input(
        context["root"],
        "validation_003_validator_dependency",
        context["contract"]["tooling_dependencies"][
            "validation_003_validator_dependency"
        ],
    )
    core.require_gate(
        dependency_path == Path(previous.__file__).resolve(),
        "VALIDATION_003_DEPENDENCY_PATH",
        str(dependency_path),
        str(Path(previous.__file__).resolve()),
    )
    policy = context["contract"]["faceted_m4_signature_policy"]
    core.require_gate(
        policy.get("partition_before_polygon_reconstruction") is True
        and policy.get("cross_side_plane_intersection_permitted") is False
        and policy.get("duplicate_parallel_within_side_must_fail") is True
        and policy.get("compare_sides") == ["left", "right"],
        "BILATERAL_M4_SIGNATURE_POLICY",
        policy,
        {
            "partition_before_polygon_reconstruction": True,
            "cross_side_plane_intersection_permitted": False,
            "duplicate_parallel_within_side_must_fail": True,
            "compare_sides": ["left", "right"],
        },
    )
    context["validation_003_dependency_record"] = dependency_record
    context["validation_003_reclassification"] = verify_validation_003_defect(
        context
    )
    return context


def _json_safe(value: Any) -> Any:
    if isinstance(value, App.Vector):
        return core.vector_values(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return repr(value)


class GateCollector:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def require(
        self, condition: bool, gate_id: str, actual: Any, expected: Any
    ) -> None:
        self.records.append(
            {
                "sequence": len(self.records) + 1,
                "gate": gate_id,
                "status": "PASS" if condition else "FAIL",
                "actual": _json_safe(actual),
                "expected": _json_safe(expected),
            }
        )

    def record_exception(self, exc: Exception) -> None:
        self.records.append(
            {
                "sequence": len(self.records) + 1,
                "gate": "VALIDATION_EVALUATION_EXCEPTION",
                "status": "FAIL",
                "actual": f"{type(exc).__name__}: {exc}",
                "expected": "all gates with satisfied prerequisites are evaluated",
            }
        )


def execute_validation_with_gate_report(
    context: dict[str, Any],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    """Run once while collecting every gate whose prerequisites are available."""

    collector = GateCollector()
    utility_module = sys.modules[core.require_candidate_health.__module__]
    original_core_require = core.require_gate
    original_utility_require = utility_module.require_gate
    original_evaluator = core.evaluate_m4_preservation
    metrics: dict[str, Any] | None = None
    try:
        core.require_gate = collector.require
        utility_module.require_gate = collector.require
        core.evaluate_m4_preservation = evaluate_m4_preservation
        metrics = core.execute_validation(context)
    except Exception as exc:
        collector.record_exception(exc)
    finally:
        core.evaluate_m4_preservation = original_evaluator
        utility_module.require_gate = original_utility_require
        core.require_gate = original_core_require

    observed_candidate_hash = core.sha256_file(context["input_paths"]["candidate"])
    collector.require(
        observed_candidate_hash
        == context["contract"]["inputs"]["candidate"]["sha256"],
        "CANDIDATE_IMMUTABLE_AFTER_VALIDATION",
        observed_candidate_hash,
        context["contract"]["inputs"]["candidate"]["sha256"],
    )
    return metrics, collector.records


def preflight_result(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "validation_id": VALIDATION_ID,
        "status": "PREFLIGHT_PASS__VALIDATION_NOT_EXECUTED",
        "candidate_disposition": CANDIDATE_DISPOSITION,
        "candidate_sha256": context["input_records"]["candidate"]["sha256"],
        "candidate_opened": False,
        "candidate_modified": False,
        "generator_invoked": False,
        "geometry_validation_executed": False,
        "output_created": False,
        "output_directory_exists": context["output_dir"].exists(),
        "runtime": context["runtime"],
        "validation_003_reclassification": context[
            "validation_003_reclassification"
        ],
        "validation_003_validator_dependency": context[
            "validation_003_dependency_record"
        ],
        "m4_expected_removal_set": EXPECTED_REMOVAL_SET,
        "m4_signature_method": "independent left/right axial bearing polygons",
        "all_determinable_gate_reporting": True,
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
            "candidate_disposition": CANDIDATE_DISPOSITION,
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

    metrics, gate_results = execute_validation_with_gate_report(context)
    failed_gates = [item for item in gate_results if item["status"] == "FAIL"]
    passed_count = sum(item["status"] == "PASS" for item in gate_results)
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
        "validation_003_reclassification": context[
            "validation_003_reclassification"
        ],
        "m4_expected_removal_set": EXPECTED_REMOVAL_SET,
        "gate_reporting": {
            "policy": "all determinable gates in this single execution",
            "total_reported": len(gate_results),
            "passed": passed_count,
            "failed": len(failed_gates),
            "complete_for_satisfied_prerequisites": True,
            "results": gate_results,
        },
    }
    if not failed_gates and metrics is not None:
        result.update(
            {
                "status": "PASS",
                "release_validation_result": PASS_CLASSIFICATION,
                "candidate_disposition": CANDIDATE_DISPOSITION,
                "c002_state": "FROZEN__ISOLATED_C002_CANDIDATE_ONLY",
                "failed_gate": None,
                "failed_gates": [],
                "metrics": metrics,
            }
        )
        exit_code = 0
    else:
        result.update(
            {
                "status": "FAIL",
                "release_validation_result": "RELEASE_VALIDATION_FAIL__C002_ONLY",
                "candidate_disposition": CANDIDATE_DISPOSITION,
                "failed_gate": failed_gates[0] if failed_gates else None,
                "failed_gates": failed_gates,
                "metrics": metrics,
            }
        )
        exit_code = 1

    context["output_dir"].mkdir(parents=True, exist_ok=False)
    context["report_path"].write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
