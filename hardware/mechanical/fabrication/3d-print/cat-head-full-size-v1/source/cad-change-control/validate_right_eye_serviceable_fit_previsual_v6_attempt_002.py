#!/usr/bin/env python3
"""Independent fail-closed pre-visual validation for V6 attempt-002.

The module intentionally imports FreeCAD only inside the real measurement
entrypoint.  Its design-signature and gate evaluator stay standard-library
only so the anti-loop and synthetic-failure regressions can run without
opening any CAD document.

The real validator is read-only.  It opens the canonical baseline, candidate,
and hash-pinned fit references; writes one deterministic JSON report inside an
already-existing iteration directory; and never saves, heals, exports, or
changes geometry.  A PASS authorizes only an opaque human review pack.  Deep
release validation remains a later, separately approved phase.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Sequence


ITERATION_ID = "right-eye-serviceable-fit-prototype-v6-attempt-002"
DESIGN_ID = "right-eye-serviceable-fit-C"
TOOLING_REVISION = 5
TARGET_OBJECT = "FROZEN_REPAIRED_RIGHT_EYE_V4_V34"
EDGE_PROJECTION_ALGORITHM = "nearest-point-on-closed-polygon-edge-v1"
FAILED_V4_SIGNATURE = "c52deaccc27b8a8ef681a184175a50bfeba0296fb8afda4e41d1a42292d24b2d"
FAILED_V4_STATUS = "GENERATOR_IMPLEMENTATION_FAILURE__NEAREST_VERTEX_DISTANCE"
FAILED_V5_SIGNATURE = "709e96116e4269ac3bb87cbce4bcf055fb0b82a18c692d5a23973797d4a97fb1"
FAILED_V5_STATUS = "TOOLING_FAILURE__SHELL_EDGE_DERIVED_MOUNT_AXIS"
SIGNATURE_ALGORITHM = "sha256-canonical-json-decimal-v1"
SIGNED_FIELDS = (
    "construction_algorithm_id",
    "geometry",
    "aperture_lcs",
    "mount_datums",
)
REQUIRED_DEFECT_IDS = {
    "V3-01-FASTENER-ACCESS",
    "V3-02-REAR-CAP-SERVICE",
    "V3-03-APERTURE-VISIBILITY",
    "V3-04-FLANGE-EXTERIOR-PROTRUSION",
    "V3-05-EYE-CORNER-EXTERIOR-ESCAPE",
    "V3-06-KNOWN-F19-SHELL-CONTACTS",
}


class DesignControlError(RuntimeError):
    """The machine-readable design-control contract is invalid."""


class RejectedDesignSignatureError(DesignControlError):
    """The proposed construction is equivalent to a rejected design."""


class ContractNotApprovedError(DesignControlError):
    """The draft contract has not been approved for candidate generation."""


def repository_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise DesignControlError("cannot locate repository root")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise DesignControlError(f"{path}: root must be an object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _independent_dot(first: Sequence[float], second: Sequence[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(first, second))


def _independent_add(
    first: Sequence[float], second: Sequence[float]
) -> tuple[float, float, float]:
    return tuple(float(a) + float(b) for a, b in zip(first, second))  # type: ignore[return-value]


def _independent_subtract(
    first: Sequence[float], second: Sequence[float]
) -> tuple[float, float, float]:
    return tuple(float(a) - float(b) for a, b in zip(first, second))  # type: ignore[return-value]


def _independent_scale(
    value: Sequence[float], scale: float
) -> tuple[float, float, float]:
    return tuple(float(component) * float(scale) for component in value)  # type: ignore[return-value]


def _independent_cross(
    first: Sequence[float], second: Sequence[float]
) -> tuple[float, float, float]:
    return (
        float(first[1]) * float(second[2])
        - float(first[2]) * float(second[1]),
        float(first[2]) * float(second[0])
        - float(first[0]) * float(second[2]),
        float(first[0]) * float(second[1])
        - float(first[1]) * float(second[0]),
    )


def _independent_length(value: Sequence[float]) -> float:
    return math.sqrt(_independent_dot(value, value))


def _independent_unit(
    value: Sequence[float], label: str
) -> tuple[float, float, float]:
    length = math.sqrt(_independent_dot(value, value))
    if length <= 1.0e-12:
        raise DesignControlError(f"{label} has zero length")
    return _independent_scale(value, 1.0 / length)


def preflight_independent_signed_mount_frames(
    parameters: dict[str, Any],
) -> dict[str, Any]:
    """Reconstruct V6 frames independently from only signed axes and LCS."""
    aperture_normal = _independent_unit(
        parameters["aperture_lcs"]["inward_n"], "aperture normal"
    )
    settings = parameters["geometry"]["head_mount"]
    limits = parameters["validation_contract"]["limits"]
    minimum_axis_dot = float(limits["minimum_signed_mount_axis_dot"])
    orthogonality_limit = float(limits["maximum_frame_orthogonality_error"])
    alignment_limit = float(limits["maximum_bore_center_axis_offset_mm"])
    dimensional_limit = float(limits["maximum_dimensional_deviation_mm"])
    expected_gap = float(settings["mating_gap_mm"])
    face_offset = float(settings["bore_center_to_mating_face_mm"])
    frames: dict[str, Any] = {}
    for role, datum in parameters["mount_datums"].items():
        signed = tuple(float(value) for value in datum["bore_axis"])
        bore_axis_vector = _independent_unit(signed, f"{role} signed bore")
        normal_component = _independent_scale(
            bore_axis_vector,
            _independent_dot(aperture_normal, bore_axis_vector),
        )
        depth = _independent_unit(
            _independent_subtract(aperture_normal, normal_component),
            f"{role} depth",
        )
        tangent = _independent_unit(
            _independent_cross(depth, bore_axis_vector), f"{role} tangent"
        )
        recovered_bore = _independent_unit(
            _independent_cross(tangent, depth), f"{role} recovered bore"
        )
        signed_unit = _independent_unit(signed, f"{role} signed unit")
        signed_axis_dot = _independent_dot(bore_axis_vector, signed_unit)
        signed_axis_error = _independent_length(
            _independent_subtract(bore_axis_vector, signed_unit)
        )
        orthogonality_error = max(
            abs(_independent_dot(bore_axis_vector, depth)),
            abs(_independent_dot(bore_axis_vector, tangent)),
            abs(_independent_dot(depth, tangent)),
        )
        unit_length_error = max(
            abs(_independent_length(bore_axis_vector) - 1.0),
            abs(_independent_length(depth) - 1.0),
            abs(_independent_length(tangent) - 1.0),
        )
        right_handed_dot = _independent_dot(recovered_bore, bore_axis_vector)
        eye = tuple(float(value) for value in datum["eye_bore_center_mm"])
        head = tuple(float(value) for value in datum["head_bore_center_mm"])
        delta = _independent_subtract(eye, head)
        axial = _independent_dot(delta, bore_axis_vector)
        center_axis_offset = _independent_length(
            _independent_subtract(
                delta, _independent_scale(bore_axis_vector, axial)
            )
        )
        mating_gap = axial - 2.0 * face_offset
        mating_gap_error = abs(mating_gap - expected_gap)
        passed = (
            signed_axis_dot >= minimum_axis_dot
            and signed_axis_error <= orthogonality_limit
            and orthogonality_error <= orthogonality_limit
            and unit_length_error <= orthogonality_limit
            and right_handed_dot >= minimum_axis_dot
            and center_axis_offset <= alignment_limit
            and mating_gap_error <= dimensional_limit
        )
        frames[role] = {
            "bore_axis_vector": bore_axis_vector,
            "depth": depth,
            "tangent": tangent,
            "signed_axis_dot": signed_axis_dot,
            "signed_axis_error": signed_axis_error,
            "orthogonality_error": orthogonality_error,
            "unit_length_error": unit_length_error,
            "right_handed_dot": right_handed_dot,
            "axial_center_separation_mm": axial,
            "center_axis_offset_mm": center_axis_offset,
            "mating_gap_mm": mating_gap,
            "mating_gap_error_mm": mating_gap_error,
            "passed": passed,
        }
        if not passed:
            raise DesignControlError(
                _diagnostic(
                    "independent V6 signed-axis frame preflight failed",
                    role=role,
                    measurements=frames[role],
                )
            )
    return {
        "status": "PASS__INDEPENDENT_SIGNED_AXIS_FRAMES",
        "algorithm": "independent-signed-axis-gram-schmidt-v1",
        "frames": frames,
        "shell_edge_used_to_define_axis": False,
    }


def _independent_rear_inner_uv(
    parameters: dict[str, Any],
) -> list[tuple[float, float]]:
    lcs = parameters["aperture_lcs"]
    origin = tuple(float(value) for value in lcs["origin_mm"])
    axis_u = _independent_unit(lcs["u"], "LCS u")
    axis_v = _independent_unit(lcs["v"], "LCS v")
    axis_n = _independent_unit(lcs["inward_n"], "LCS inward n")
    if max(
        abs(_independent_dot(axis_u, axis_v)),
        abs(_independent_dot(axis_u, axis_n)),
        abs(_independent_dot(axis_v, axis_n)),
    ) > 1.0e-6:
        raise DesignControlError("protected module LCS is not orthogonal")
    aperture: list[tuple[float, float, float]] = []
    for source in lcs["visible_aperture_mm"]:
        delta = _independent_subtract(source, origin)
        aperture.append(
            _independent_add(
                origin,
                _independent_add(
                    _independent_scale(axis_u, _independent_dot(delta, axis_u)),
                    _independent_scale(axis_v, _independent_dot(delta, axis_v)),
                ),
            )
        )
    centroid = tuple(
        sum(point[index] for point in aperture) / float(len(aperture))
        for index in range(3)
    )
    radial_offset = float(
        parameters["geometry"]["chamber"]["rear_inner_offset_mm"]
    )
    perimeter: list[tuple[float, float]] = []
    for point in aperture:
        direction = _independent_subtract(point, centroid)
        direction = _independent_subtract(
            direction,
            _independent_scale(axis_n, _independent_dot(direction, axis_n)),
        )
        direction = _independent_unit(direction, "rear perimeter radial")
        shifted = _independent_add(point, _independent_scale(direction, radial_offset))
        delta = _independent_subtract(shifted, origin)
        perimeter.append(
            (_independent_dot(delta, axis_u), _independent_dot(delta, axis_v))
        )
    return perimeter


def project_point_to_polygon_edges_independent(
    query_uv: Sequence[float],
    polygon_uv: Sequence[Sequence[float]],
) -> dict[str, Any]:
    """Independent segment projection; no generator helper is imported."""
    if len(polygon_uv) < 3:
        raise DesignControlError("rear perimeter has fewer than three vertices")
    query = (float(query_uv[0]), float(query_uv[1]))
    candidates: list[dict[str, Any]] = []
    for index in range(len(polygon_uv)):
        first = (float(polygon_uv[index][0]), float(polygon_uv[index][1]))
        second_raw = polygon_uv[(index + 1) % len(polygon_uv)]
        second = (float(second_raw[0]), float(second_raw[1]))
        vector = (second[0] - first[0], second[1] - first[1])
        denominator = vector[0] ** 2 + vector[1] ** 2
        if denominator <= 1.0e-18:
            raise DesignControlError(f"rear perimeter edge {index} is degenerate")
        unbounded = (
            (query[0] - first[0]) * vector[0]
            + (query[1] - first[1]) * vector[1]
        ) / denominator
        bounded = min(1.0, max(0.0, unbounded))
        point = (
            first[0] + bounded * vector[0],
            first[1] + bounded * vector[1],
        )
        squared = (query[0] - point[0]) ** 2 + (query[1] - point[1]) ** 2
        candidates.append(
            {
                "edge_index": index,
                "unbounded_parameter": unbounded,
                "segment_parameter": bounded,
                "point_uv_mm": point,
                "distance_squared_mm2": squared,
                "distance_mm": math.sqrt(squared),
            }
        )
    return min(
        candidates,
        key=lambda record: (
            float(record["distance_squared_mm2"]),
            int(record["edge_index"]),
        ),
    )


def independent_projection_lands_inside_segment(
    projection: dict[str, Any], interior_epsilon: float
) -> bool:
    unbounded = float(projection["unbounded_parameter"])
    bounded = float(projection["segment_parameter"])
    return (
        float(interior_epsilon) < unbounded < 1.0 - float(interior_epsilon)
        and abs(unbounded - bounded) <= 1.0e-15
    )


def independent_unsupported_span_is_within_limit(
    center_to_edge_mm: float,
    boss_radius_mm: float,
    maximum_unsupported_span_mm: float,
    tolerance_mm: float = 0.0,
) -> bool:
    unsupported_span = max(
        0.0, float(center_to_edge_mm) - float(boss_radius_mm)
    )
    return unsupported_span <= float(maximum_unsupported_span_mm) + float(
        tolerance_mm
    )


def preflight_independent_root_projection(
    parameters: dict[str, Any],
) -> dict[str, Any]:
    rear = parameters["geometry"]["rear_cap_connector"]
    if rear.get("projection_algorithm") != EDGE_PROJECTION_ALGORITHM:
        raise DesignControlError("V6 edge-projection algorithm mismatch")
    perimeter = _independent_rear_inner_uv(parameters)
    lcs = parameters["aperture_lcs"]
    origin = tuple(float(value) for value in lcs["origin_mm"])
    axis_u = _independent_unit(lcs["u"], "LCS u")
    axis_v = _independent_unit(lcs["v"], "LCS v")
    expected = rear["edge_projection_preflight"]
    tolerance = float(expected["numeric_tolerance_mm"])
    interior_epsilon = float(expected["segment_interior_epsilon"])
    radius = float(rear["outer_diameter_mm"]) / 2.0
    roots: dict[str, Any] = {}
    for role, center in rear["boss_centers_mm"].items():
        delta = _independent_subtract(center, origin)
        center_uv = (
            _independent_dot(delta, axis_u),
            _independent_dot(delta, axis_v),
        )
        projection = project_point_to_polygon_edges_independent(center_uv, perimeter)
        distance = float(projection["distance_mm"])
        unsupported = max(0.0, distance - radius)
        raw_parameter = float(projection["unbounded_parameter"])
        bounded_parameter = float(projection["segment_parameter"])
        inside = independent_projection_lands_inside_segment(
            projection, interior_epsilon
        )
        expected_role = expected[role]
        passes = (
            abs(distance - float(expected_role["center_to_edge_mm"])) <= tolerance
            and abs(unsupported - float(expected_role["unsupported_span_mm"]))
            <= tolerance
            and int(projection["edge_index"]) == int(expected_role["edge_index"])
            and inside
            and independent_unsupported_span_is_within_limit(
                distance,
                radius,
                float(rear["maximum_local_root_span_mm"]),
                tolerance,
            )
        )
        roots[role] = {
            **projection,
            "center_uv_mm": center_uv,
            "center_to_edge_mm": distance,
            "boss_radius_mm": radius,
            "unsupported_span_mm": unsupported,
            "projection_inside_segment": inside,
            "passed": passes,
        }
        if not passes:
            raise DesignControlError(
                _diagnostic(
                    "independent V6 rear-cap root projection failed",
                    role=role,
                    measurements=roots[role],
                )
            )
    return {
        "status": "PASS__INDEPENDENT_EDGE_PROJECTIONS",
        "algorithm": EDGE_PROJECTION_ALGORITHM,
        "roots": roots,
    }


def _decimal_text(value: int | float | Decimal) -> str:
    if isinstance(value, float) and not math.isfinite(value):
        raise DesignControlError("design signatures cannot contain NaN or infinity")
    decimal = Decimal(str(value))
    if decimal == 0:
        return "0"
    text = format(decimal.normalize(), "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def normalize_signature_value(value: Any) -> Any:
    """Normalize numbers and object ordering before canonical JSON hashing."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float, Decimal)):
        return {"$decimal": _decimal_text(value)}
    if isinstance(value, list):
        return [normalize_signature_value(item) for item in value]
    if isinstance(value, tuple):
        return [normalize_signature_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): normalize_signature_value(value[key])
            for key in sorted(value)
        }
    raise DesignControlError(
        f"unsupported design-signature value type: {type(value).__name__}"
    )


def canonical_signature_bytes(payload: dict[str, Any]) -> bytes:
    normalized = normalize_signature_value(payload)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def calculate_design_signature(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_signature_bytes(payload)).hexdigest()


def contract_signature_payload(parameters: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in SIGNED_FIELDS if field not in parameters]
    if missing:
        raise DesignControlError(f"design signature is missing signed fields: {missing}")
    return {field: parameters[field] for field in SIGNED_FIELDS}


def _diagnostic(error: str, **values: Any) -> str:
    return json.dumps({"error": error, **values}, sort_keys=True)


def preflight_design_control(
    contract: dict[str, Any],
    registry: dict[str, Any],
    *,
    require_approval: bool,
) -> dict[str, Any]:
    """Verify lineage, canonical signature, rejection registry, and approval.

    Rejected-signature detection intentionally precedes the approval check, so
    an unapproved copy of a rejected design is still diagnosed as an anti-loop
    violation rather than merely as a draft.
    """
    if contract.get("iteration_id") != ITERATION_ID:
        raise DesignControlError(
            _diagnostic(
                "iteration ID mismatch",
                expected=ITERATION_ID,
                observed=contract.get("iteration_id"),
                output_created=False,
                geometry_construction_started=False,
            )
        )
    if contract.get("target_object") != TARGET_OBJECT:
        raise DesignControlError("target object mismatch")
    mutations = contract.get("allowed_mutations")
    if not isinstance(mutations, list) or len(mutations) != 1:
        raise DesignControlError("exactly one target mutation is required")
    mutation = mutations[0]
    if mutation.get("kind") != "replace_geometry" or mutation.get("object") != TARGET_OBJECT:
        raise DesignControlError("V6 requires one replace_geometry target mutation")
    parameters = mutation.get("parameters")
    if not isinstance(parameters, dict):
        raise DesignControlError("mutation parameters must be an object")

    control = parameters.get("design_control")
    if not isinstance(control, dict):
        raise DesignControlError("design_control is required")
    if control.get("design_id") != DESIGN_ID:
        raise DesignControlError("design_id mismatch")
    if control.get("tooling_revision") != TOOLING_REVISION:
        raise DesignControlError(
            f"tooling_revision must be {TOOLING_REVISION} for this tooling revision"
        )
    if "design_version" in control or "design_version" in parameters:
        raise DesignControlError(
            "tooling revisions must not create design-version numbers"
        )
    signature_record = control.get("design_signature")
    if not isinstance(signature_record, dict):
        raise DesignControlError("design_control.design_signature is required")
    if signature_record.get("algorithm") != SIGNATURE_ALGORITHM:
        raise DesignControlError("unsupported design-signature algorithm")
    if tuple(signature_record.get("signed_fields", [])) != SIGNED_FIELDS:
        raise DesignControlError("design-signature signed_fields changed")

    payload = contract_signature_payload(parameters)
    calculated = calculate_design_signature(payload)
    declared = signature_record.get("sha256")
    if not isinstance(declared, str) or not re.fullmatch(r"[0-9a-f]{64}", declared):
        raise DesignControlError("declared design signature is not a SHA-256 digest")
    if calculated != declared:
        raise DesignControlError(
            _diagnostic(
                "declared design signature mismatch",
                declared=declared,
                calculated=calculated,
                output_created=False,
                geometry_construction_started=False,
            )
        )

    if registry.get("schema_version") != "1.0":
        raise DesignControlError("rejected-design registry schema mismatch")
    if registry.get("signature_algorithm") != SIGNATURE_ALGORITHM:
        raise DesignControlError("rejected-design registry algorithm mismatch")
    rejected_entries = registry.get("rejected_designs")
    if not isinstance(rejected_entries, list) or not rejected_entries:
        raise DesignControlError("rejected-design registry is empty")
    failed_v4_entries: list[dict[str, Any]] = []
    failed_v5_entries: list[dict[str, Any]] = []
    for entry in rejected_entries:
        if not isinstance(entry, dict):
            raise DesignControlError("rejected-design registry entry must be an object")
        entry_payload = entry.get("signature_payload")
        if not isinstance(entry_payload, dict):
            raise DesignControlError("rejected registry entry lacks signature_payload")
        registry_calculated = calculate_design_signature(entry_payload)
        if registry_calculated != entry.get("design_signature_sha256"):
            raise DesignControlError(
                f"rejected registry signature mismatch for {entry.get('registry_id')}"
            )
        if registry_calculated == FAILED_V4_SIGNATURE:
            failed_v4_entries.append(entry)
        if registry_calculated == FAILED_V5_SIGNATURE:
            failed_v5_entries.append(entry)
        if calculated == registry_calculated:
            raise RejectedDesignSignatureError(
                _diagnostic(
                    "REJECTED_DESIGN_SIGNATURE",
                    design_signature_sha256=calculated,
                    registry_id=entry.get("registry_id"),
                    status=entry.get("status"),
                    source_iterations=entry.get("source_iterations"),
                    output_created=False,
                    geometry_construction_started=False,
                )
            )

    if len(failed_v4_entries) != 1:
        raise DesignControlError(
            "rejected-design registry must contain exactly one failed V4 signature"
        )
    failed_v4_entry = failed_v4_entries[0]
    if failed_v4_entry.get("status") != FAILED_V4_STATUS:
        raise DesignControlError("failed V4 registry status mismatch")
    if "right-eye-serviceable-fit-prototype-v4" not in failed_v4_entry.get(
        "source_iterations", []
    ):
        raise DesignControlError("failed V4 registry lineage is missing")
    if len(failed_v5_entries) != 1:
        raise DesignControlError(
            "rejected-design registry must contain exactly one failed V5 signature"
        )
    failed_v5_entry = failed_v5_entries[0]
    if failed_v5_entry.get("status") != FAILED_V5_STATUS:
        raise DesignControlError("failed V5 registry status mismatch")
    if "right-eye-serviceable-fit-prototype-v5" not in failed_v5_entry.get(
        "source_iterations", []
    ):
        raise DesignControlError("failed V5 registry lineage is missing")

    defect_map = parameters.get("defect_resolution_map")
    if not isinstance(defect_map, list):
        raise DesignControlError("defect_resolution_map must be an array")
    mapped_ids = {
        item.get("defect_id") for item in defect_map if isinstance(item, dict)
    }
    if mapped_ids != REQUIRED_DEFECT_IDS:
        raise DesignControlError(
            f"defect_resolution_map must cover exactly {sorted(REQUIRED_DEFECT_IDS)}"
        )
    for item in defect_map:
        if not item.get("v6_construction") or not item.get("validation_gate"):
            raise DesignControlError(
                f"defect map entry {item.get('defect_id')} lacks construction or gate"
            )

    approval = control.get("approval")
    if not isinstance(approval, bool):
        raise DesignControlError("design_control.approval must be boolean")
    if require_approval and approval is not True:
        raise ContractNotApprovedError(
            _diagnostic(
                "DRAFT_NOT_APPROVED",
                design_id=DESIGN_ID,
                tooling_revision=TOOLING_REVISION,
                approval=False,
                output_created=False,
                geometry_construction_started=False,
            )
        )
    return {
        "status": "PASS__DESIGN_SIGNATURE_NOT_REJECTED",
        "design_id": DESIGN_ID,
        "tooling_revision": TOOLING_REVISION,
        "design_signature_sha256": calculated,
        "approval": approval,
        "rejected_signature_count": len(rejected_entries),
        "failed_v4_signature_registered": True,
        "failed_v4_status": FAILED_V4_STATUS,
        "failed_v5_signature_registered": True,
        "failed_v5_status": FAILED_V5_STATUS,
        "defect_ids": sorted(mapped_ids),
    }


def evaluate_previsual_observations(
    observations: dict[str, Any],
    limits: dict[str, Any],
) -> dict[str, Any]:
    """Pure fail-closed evaluator used by real measurements and regressions."""
    epsilon = float(limits["maximum_unintended_positive_intersection_mm3"])
    topology = observations.get("topology", {})
    preservation = observations.get("preservation", {})
    shell = observations.get("shell_matrix", {})
    containment = observations.get("containment", {})
    exterior = observations.get("exterior_aperture", {})
    frustum = observations.get("view_frustum", {})
    insertion = observations.get("eye_insertion_removal", {})
    cap_sweep = observations.get("rear_cap_sweep", {})
    hardware = observations.get("hardware_access", {})
    integrity = observations.get("mount_integrity", {})
    datums = observations.get("datum_and_interface_preservation", {})

    known_required = {
        "upper_C001",
        "lower_C001",
        "lower_C012",
        "lower_C013",
    }
    known = shell.get("known_f19_intersections_mm3", {})
    known_resolved = (
        isinstance(known, dict)
        and set(known) == known_required
        and all(float(value) <= epsilon for value in known.values())
    )

    hardware_roles_ok = True
    for role in ("upper", "lower"):
        record = hardware.get(role, {})
        hardware_roles_ok = hardware_roles_ok and all(
            (
                record.get("bolt_length_range_mm") == [8.0, 10.0],
                record.get("washer_count") == 2,
                float(record.get("washer_od_mm", -1.0)) == 7.0,
                float(record.get("washer_thickness_mm", -1.0)) == 0.8,
                float(record.get("nyloc_od_mm", -1.0)) == 7.0,
                float(record.get("nyloc_length_mm", -1.0)) == 5.0,
                float(record.get("tool_diameter_mm", -1.0)) == 8.0,
                float(record.get("tool_length_mm", -1.0)) == 20.0,
                float(record.get("max_path_collision_mm3", math.inf)) <= epsilon,
            )
        )

    prohibited_hardware = max(
        (
            float(record.get("max_prohibited_intersection_mm3", math.inf))
            for record in hardware.values()
            if isinstance(record, dict)
        ),
        default=math.inf,
    )
    behind_flange_blocking = max(
        (
            float(record.get("behind_flange_blocking_volume_mm3", math.inf))
            for record in hardware.values()
            if isinstance(record, dict)
        ),
        default=math.inf,
    )
    mount_roles_ok = all(
        float(integrity.get(role, {}).get("direct_owner_root_engagement_mm3", -1.0))
        >= float(limits["minimum_direct_owner_root_engagement_mm3"])
        and float(integrity.get(role, {}).get("bore_to_edge_material_mm", -1.0))
        >= float(limits["minimum_bore_to_edge_material_mm"])
        and abs(
            float(integrity.get(role, {}).get("head_mount_mating_gap_mm", math.inf))
            - float(limits["required_head_mount_mating_gap_mm"])
        )
        <= float(limits["maximum_dimensional_deviation_mm"])
        for role in ("upper", "lower")
    )

    gates = {
        "G01_ONE_VALID_CLOSED_CONNECTED_TARGET": bool(
            topology.get("valid")
            and topology.get("closed")
            and topology.get("solid_count") == 1
            and topology.get("connected_component_count") == 1
            and topology.get("self_intersection_count") == 0
        ),
        "G02_EXACT_NON_TARGET_PRESERVATION": bool(
            preservation.get("status") == "PASS__READY_FOR_FIXED_VIEW_REVIEW"
            and preservation.get("candidate_hash_matches") is True
            and preservation.get("protected_difference_count") == 0
        ),
        "G03_FULL_101_SHELL_MATRIX": bool(
            shell.get("component_count") == 101
            and shell.get("unresolved_error_count") == 0
            and float(shell.get("maximum_positive_intersection_mm3", math.inf))
            <= epsilon
            and known_resolved
            and shell.get("clearance_unresolved_error_count") == 0
            and float(shell.get("minimum_non_mating_clearance_mm", -math.inf))
            >= float(limits["minimum_non_mating_shell_clearance_mm"])
            and float(
                shell.get("upper_c001_clearance_outside_authorized_interfaces_mm", -math.inf)
            )
            >= float(limits["minimum_upper_c001_clearance_outside_authorized_mount_mm"])
        ),
        "G04_PERMITTED_EYE_ENVELOPE": bool(
            float(containment.get("outside_permitted_envelope_mm3", math.inf))
            <= epsilon
        ),
        "G05_ONLY_BEZEL_EXTERIOR": bool(
            float(exterior.get("non_bezel_exterior_volume_mm3", math.inf))
            <= epsilon
        ),
        "G06_ZERO_APERTURE_VIEW_FRUSTUM_OCCUPANCY": bool(
            float(frustum.get("mount_chamber_cap_volume_mm3", math.inf)) <= epsilon
        ),
        "G07_EYE_INSERTION_AND_REMOVAL": bool(
            insertion.get("complete_sample_set") is True
            and float(insertion.get("maximum_unintended_collision_mm3", math.inf))
            <= epsilon
        ),
        "G08_REAR_CAP_SEATING_AND_REMOVAL": bool(
            cap_sweep.get("complete_sample_set") is True
            and float(cap_sweep.get("maximum_unintended_collision_mm3", math.inf))
            <= epsilon
        ),
        "G09_BOTH_FASTENER_AND_TOOL_PATHS": bool(hardware_roles_ok),
        "G10_HARDWARE_AVOIDS_PROHIBITED_GEOMETRY": bool(
            prohibited_hardware <= epsilon
            and behind_flange_blocking <= epsilon
        ),
        "G11_MOUNT_ROOT_AND_EDGE_MATERIAL": bool(mount_roles_ok),
        "G12_DATUM_INTERFACE_AND_WALL_PRESERVATION": bool(
            datums.get("aperture_exact") is True
            and datums.get("module_lcs_exact") is True
            and datums.get("mount_datums_exact") is True
            and datums.get("signed_mount_frame_pass") is True
            and datums.get("signed_mount_frames_exact") is True
            and datums.get("connector_dimensions_exact") is True
            and datums.get("rear_cap_root_projection_pass") is True
            and datums.get("rear_cap_interface_pass") is True
            and datums.get("diffuser_interface_pass") is True
            and datums.get("minimum_wall_pass") is True
        ),
    }
    failed = [gate for gate, passed in gates.items() if not passed]
    mount_datum_conflict = bool(
        containment.get("mount_related_outside_volume_mm3", 0.0) > epsilon
        or any(
            gate in failed
            for gate in (
                "G09_BOTH_FASTENER_AND_TOOL_PATHS",
                "G10_HARDWARE_AVOIDS_PROHIBITED_GEOMETRY",
                "G11_MOUNT_ROOT_AND_EDGE_MATERIAL",
            )
        )
    )
    if not failed:
        status = "PASS__PREVISUAL_GATES__READY_FOR_OPAQUE_REVIEW"
    elif mount_datum_conflict:
        status = "BLOCKED__MOUNT_DATUM_CONFLICT"
    else:
        status = "FAIL__PREVISUAL_GATE__DO_NOT_PRESENT"
    return {
        "status": status,
        "passed": not failed,
        "approval_presentation_allowed": not failed,
        "failed_gates": failed,
        "gates": gates,
        "mount_datum_conflict": mount_datum_conflict,
    }


# The remaining helpers are imported only by the real FreeCAD measurement run.


def _vector(App: Any, values: Sequence[float]) -> Any:
    return App.Vector(float(values[0]), float(values[1]), float(values[2]))


def _normalized(App: Any, values: Any, label: str) -> Any:
    result = App.Vector(values)
    if result.Length <= 1.0e-9:
        raise RuntimeError(f"{label} has zero length")
    result.normalize()
    return result


def _local(point: Any, origin: Any, axis_u: Any, axis_v: Any, axis_n: Any) -> tuple[float, float, float]:
    delta = point - origin
    return delta.dot(axis_u), delta.dot(axis_v), delta.dot(axis_n)


def _from_local(u_value: float, v_value: float, depth: float, origin: Any, axis_u: Any, axis_v: Any, axis_n: Any) -> Any:
    return origin + axis_u * u_value + axis_v * v_value + axis_n * depth


def _planar_loop(points: Sequence[Any], origin: Any, axis_u: Any, axis_v: Any, axis_n: Any) -> list[Any]:
    return [
        _from_local(*_local(point, origin, axis_u, axis_v, axis_n)[:2], 0.0, origin, axis_u, axis_v, axis_n)
        for point in points
    ]


def _average(App: Any, points: Sequence[Any]) -> Any:
    result = App.Vector()
    for point in points:
        result += point
    return result / float(len(points))


def _radial_offset(App: Any, loop: Sequence[Any], offset: float, axis_n: Any) -> list[Any]:
    center = _average(App, loop)
    output = []
    for point in loop:
        radial = point - center
        radial -= axis_n * radial.dot(axis_n)
        radial = _normalized(App, radial, "loop radial")
        output.append(point + radial * float(offset))
    return output


def _at_depth(loop: Sequence[Any], depth: float, axis_n: Any) -> list[Any]:
    return [point + axis_n * float(depth) for point in loop]


def _face(Part: Any, loop: Sequence[Any]) -> Any:
    return Part.Face(Part.makePolygon([*loop, loop[0]]))


def _ring_prism(Part: Any, outer: Sequence[Any], inner: Sequence[Any], start: float, end: float, axis_n: Any) -> Any:
    ring = _face(Part, _at_depth(outer, start, axis_n)).cut(
        _face(Part, _at_depth(inner, start, axis_n))
    )
    return ring.extrude(axis_n * (end - start)).removeSplitter()


def _loft_ring(Part: Any, outer_a: Sequence[Any], inner_a: Sequence[Any], outer_b: Sequence[Any], inner_b: Sequence[Any], start: float, end: float, axis_n: Any) -> Any:
    outer = Part.makeLoft(
        [
            Part.makePolygon([*_at_depth(outer_a, start, axis_n), _at_depth(outer_a, start, axis_n)[0]]),
            Part.makePolygon([*_at_depth(outer_b, end, axis_n), _at_depth(outer_b, end, axis_n)[0]]),
        ],
        True,
        False,
    )
    inner = Part.makeLoft(
        [
            Part.makePolygon([*_at_depth(inner_a, start - 0.01, axis_n), _at_depth(inner_a, start - 0.01, axis_n)[0]]),
            Part.makePolygon([*_at_depth(inner_b, end + 0.01, axis_n), _at_depth(inner_b, end + 0.01, axis_n)[0]]),
        ],
        True,
        False,
    )
    return outer.cut(inner).removeSplitter()


def _oriented_box(Part: Any, center: Any, axes: Sequence[Any], dimensions: Sequence[float]) -> Any:
    half = [float(value) / 2.0 for value in dimensions]
    base = center - axes[0] * half[0] - axes[1] * half[1] - axes[2] * half[2]
    loop = [
        base,
        base + axes[0] * dimensions[0],
        base + axes[0] * dimensions[0] + axes[1] * dimensions[1],
        base + axes[1] * dimensions[1],
    ]
    return _face(Part, loop).extrude(axes[2] * dimensions[2]).removeSplitter()


def _translated(shape: Any, delta: Any) -> Any:
    result = shape.copy()
    result.translate(delta)
    return result


def _fuse(shapes: Sequence[Any]) -> Any:
    if not shapes:
        raise RuntimeError("cannot fuse an empty shape list")
    return shapes[0].multiFuse(list(shapes[1:])).removeSplitter()


def _mount_frames(parameters: dict[str, Any], App: Any) -> dict[str, dict[str, Any]]:
    lcs = parameters["aperture_lcs"]
    origin = _vector(App, lcs["origin_mm"])
    axis_u = _normalized(App, _vector(App, lcs["u"]), "LCS u")
    axis_v = _normalized(App, _vector(App, lcs["v"]), "LCS v")
    axis_n = _normalized(App, _vector(App, lcs["inward_n"]), "LCS n")
    independent_frames = preflight_independent_signed_mount_frames(parameters)
    minimum_axis_dot = float(
        parameters["validation_contract"]["limits"]["minimum_signed_mount_axis_dot"]
    )
    frames: dict[str, dict[str, Any]] = {}
    for role, datum in parameters["mount_datums"].items():
        record = independent_frames["frames"][role]
        bore_axis_vector = _normalized(
            App, _vector(App, datum["bore_axis"]), f"{role} authoritative signed bore"
        )
        depth = _normalized(
            App, _vector(App, record["depth"]), f"{role} independent depth"
        )
        tangent = _normalized(
            App, _vector(App, record["tangent"]), f"{role} independent tangent"
        )
        if bore_axis_vector.dot(
            _normalized(App, _vector(App, datum["bore_axis"]), f"{role} signed axis")
        ) < minimum_axis_dot:
            raise RuntimeError(f"{role} V6 bore differs from the authoritative signed axis")
        if tangent.cross(depth).dot(bore_axis_vector) < minimum_axis_dot:
            raise RuntimeError(f"{role} V6 independent frame is not right-handed")
        eye_bore = _vector(App, datum["eye_bore_center_mm"])
        head_bore = _vector(App, datum["head_bore_center_mm"])
        frames[role] = {
            "origin": origin,
            "axis_u": axis_u,
            "axis_v": axis_v,
            "axis_n": axis_n,
            "tangent": tangent,
            "depth": depth,
            "bore_axis_vector": bore_axis_vector,
            "eye_bore": eye_bore,
            "head_bore": head_bore,
            "root_extension": _vector(App, datum["owner_root_extension_vector_mm"]),
        }
    return frames


def _reference_geometry(parameters: dict[str, Any], App: Any, Part: Any) -> dict[str, Any]:
    lcs = parameters["aperture_lcs"]
    geometry = parameters["geometry"]
    origin = _vector(App, lcs["origin_mm"])
    axis_u = _normalized(App, _vector(App, lcs["u"]), "LCS u")
    axis_v = _normalized(App, _vector(App, lcs["v"]), "LCS v")
    axis_n = _normalized(App, _vector(App, lcs["inward_n"]), "LCS n")
    aperture = _planar_loop(
        [_vector(App, point) for point in lcs["visible_aperture_mm"]],
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    opening = _planar_loop(
        [_vector(App, point) for point in geometry["shell_opening_boundary_mm"]],
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    bezel_values = geometry["bezel"]
    diffuser_values = geometry["diffuser_interface"]
    chamber_values = geometry["chamber"]
    outer_fit = _radial_offset(
        App, opening, -float(bezel_values["shell_opening_clearance_mm"]), axis_n
    )
    diffuser_loop = _radial_offset(
        App, aperture, float(diffuser_values["overlap_mm"]), axis_n
    )
    pocket_loop = _radial_offset(
        App, diffuser_loop, float(diffuser_values["pocket_clearance_mm"]), axis_n
    )
    front_outer = _radial_offset(
        App, pocket_loop, float(chamber_values["wall_thickness_mm"]), axis_n
    )
    rear_inner = _radial_offset(
        App, aperture, float(chamber_values["rear_inner_offset_mm"]), axis_n
    )
    rear_outer = _radial_offset(
        App, rear_inner, float(chamber_values["wall_thickness_mm"]), axis_n
    )
    collar_outer = _radial_offset(
        App, aperture, float(bezel_values["collar_outer_offset_mm"]), axis_n
    )
    collar_inner = _radial_offset(
        App, aperture, float(bezel_values["collar_inner_offset_mm"]), axis_n
    )
    front_bezel = _ring_prism(
        Part,
        outer_fit,
        aperture,
        float(bezel_values["front_depth_mm"]),
        float(bezel_values["front_depth_mm"]) + float(bezel_values["thickness_mm"]),
        axis_n,
    )
    collar = _ring_prism(
        Part,
        collar_outer,
        collar_inner,
        float(bezel_values["collar_start_depth_mm"]),
        float(bezel_values["collar_end_depth_mm"]),
        axis_n,
    )
    bezel = _fuse([front_bezel, collar])
    front_wall = _ring_prism(
        Part,
        front_outer,
        pocket_loop,
        float(chamber_values["front_start_depth_mm"]),
        float(chamber_values["taper_start_depth_mm"]) + 0.3,
        axis_n,
    )
    taper = _loft_ring(
        Part,
        front_outer,
        pocket_loop,
        rear_outer,
        rear_inner,
        float(chamber_values["taper_start_depth_mm"]),
        float(chamber_values["taper_end_depth_mm"]),
        axis_n,
    )
    rear_wall = _ring_prism(
        Part,
        rear_outer,
        rear_inner,
        float(chamber_values["taper_end_depth_mm"]) - 0.3,
        float(chamber_values["depth_mm"]),
        axis_n,
    )
    diffuser_seat = _ring_prism(
        Part,
        front_outer,
        rear_inner,
        float(diffuser_values["seat_start_depth_mm"]),
        float(diffuser_values["seat_end_depth_mm"]),
        axis_n,
    )
    chamber = _fuse([front_wall, taper, rear_wall, diffuser_seat])

    rear = geometry["rear_cap_connector"]
    rear_seat = _ring_prism(
        Part,
        rear_outer,
        rear_inner,
        float(rear["seat_front_depth_mm"]),
        float(chamber_values["depth_mm"]),
        axis_n,
    )
    cap_shapes = [rear_seat]
    cap_bores = []
    cap_root_records: dict[str, dict[str, Any]] = {}
    rear_inner_uv = [
        _local(point, origin, axis_u, axis_v, axis_n)[:2] for point in rear_inner
    ]
    for role, center_values in rear["boss_centers_mm"].items():
        center = _vector(App, center_values)
        center_u, center_v, _ = _local(center, origin, axis_u, axis_v, axis_n)
        start = float(chamber_values["depth_mm"]) - float(rear["engagement_depth_mm"])
        boss_base = _from_local(center_u, center_v, start, origin, axis_u, axis_v, axis_n)
        boss = Part.makeCylinder(
            float(rear["outer_diameter_mm"]) / 2.0,
            float(rear["engagement_depth_mm"]),
            boss_base,
            axis_n,
        )
        projection = project_point_to_polygon_edges_independent(
            (center_u, center_v), rear_inner_uv
        )
        center_to_edge = float(projection["distance_mm"])
        boss_radius = float(rear["outer_diameter_mm"]) / 2.0
        unsupported_span = max(0.0, center_to_edge - boss_radius)
        segment_parameter = float(projection["segment_parameter"])
        interior_epsilon = float(
            rear["edge_projection_preflight"]["segment_interior_epsilon"]
        )
        if not independent_projection_lands_inside_segment(
            projection, interior_epsilon
        ):
            raise RuntimeError(
                f"{role} rear-cap connector projection landed at a vertex"
            )
        if not independent_unsupported_span_is_within_limit(
            center_to_edge,
            boss_radius,
            float(rear["maximum_local_root_span_mm"]),
        ):
            raise RuntimeError(
                f"{role} rear-cap connector unsupported span exceeds local limit: "
                f"{unsupported_span:.10f} mm"
            )
        projected_u, projected_v = projection["point_uv_mm"]
        dx, dy = projected_u - center_u, projected_v - center_v
        if center_to_edge > 1.0e-9:
            along_u, along_v = dx / center_to_edge, dy / center_to_edge
            across_u, across_v = -along_v, along_u
            half_width = float(rear["local_root_width_mm"]) / 2.0
            landing_u = projected_u + along_u * float(rear["wall_overlap_mm"])
            landing_v = projected_v + along_v * float(rear["wall_overlap_mm"])
            loop_uv = [
                (center_u - across_u * half_width, center_v - across_v * half_width),
                (landing_u - across_u * half_width, landing_v - across_v * half_width),
                (landing_u + across_u * half_width, landing_v + across_v * half_width),
                (center_u + across_u * half_width, center_v + across_v * half_width),
            ]
            loop = [
                _from_local(u, v, start, origin, axis_u, axis_v, axis_n)
                for u, v in loop_uv
            ]
            cap_shapes.append(
                _face(Part, loop).extrude(axis_n * float(rear["root_axial_depth_mm"]))
            )
        cap_root_records[role] = {
            **projection,
            "center_uv_mm": [center_u, center_v],
            "center_to_edge_mm": center_to_edge,
            "boss_radius_mm": boss_radius,
            "unsupported_span_mm": unsupported_span,
            "wall_overlap_mm": float(rear["wall_overlap_mm"]),
            "root_width_mm": float(rear["local_root_width_mm"]),
            "root_axial_depth_mm": float(rear["root_axial_depth_mm"]),
            "projection_inside_segment": True,
        }
        cap_shapes.append(boss)
        cap_bores.append(
            Part.makeCylinder(
                float(rear["bore_diameter_mm"]) / 2.0,
                float(rear["engagement_depth_mm"]) + 2.0,
                boss_base - axis_n,
                axis_n,
            )
        )
    cap_feature_uncut = _fuse(cap_shapes)
    cap_feature = cap_feature_uncut.cut(Part.makeCompound(cap_bores)).removeSplitter()

    frames = _mount_frames(parameters, App)
    mounts: dict[str, dict[str, Any]] = {}
    mount_shapes = []
    mount_bores = []
    head_mount = geometry["head_mount"]
    length = float(head_mount["leaf_length_mm"])
    depth = float(head_mount["leaf_depth_mm"])
    thickness = float(head_mount["leaf_thickness_mm"])
    bore_radius = float(head_mount["bore_diameter_mm"]) / 2.0
    collar_radius = float(head_mount["edge_ligament_collar_outer_diameter_mm"]) / 2.0
    for role, frame in frames.items():
        eye_center = frame["eye_bore"] - frame["depth"] * (
            float(head_mount["bore_depth_from_aperture_plane_mm"]) - depth / 2.0
        )
        thick_center = eye_center + frame["bore_axis_vector"] * (
            (thickness - float(head_mount["legacy_leaf_thickness_mm"])) / 2.0
        )
        leaf = _oriented_box(
            Part,
            thick_center,
            (
                frame["tangent"],
                frame["depth"],
                frame["bore_axis_vector"],
            ),
            (length, depth, thickness),
        )
        collar_base = frame["eye_bore"] - frame["bore_axis_vector"] * float(
            head_mount["bore_center_to_mating_face_mm"]
        )
        collar = Part.makeCylinder(
            collar_radius,
            thickness,
            collar_base,
            frame["bore_axis_vector"],
        )
        local_leaf = _fuse([leaf, collar])
        extended = _fuse(
            [local_leaf, _translated(local_leaf, frame["root_extension"])]
        )
        bore_cutter_solid = Part.makeCylinder(
            bore_radius,
            float(head_mount["bore_cutter_length_mm"]),
            frame["eye_bore"]
            - frame["bore_axis_vector"]
            * (float(head_mount["bore_cutter_length_mm"]) / 2.0),
            frame["bore_axis_vector"],
        )
        drilled = extended.cut(bore_cutter_solid).removeSplitter()
        annulus_outer = Part.makeCylinder(
            bore_radius + float(head_mount["bore_to_edge_material_mm"]),
            thickness,
            collar_base,
            frame["bore_axis_vector"],
        )
        annulus = annulus_outer.cut(
            Part.makeCylinder(
                bore_radius,
                thickness,
                collar_base,
                frame["bore_axis_vector"],
            )
        )
        mounts[role] = {
            **frame,
            "uncut": extended,
            "drilled": drilled,
            "bore_cutter_solid": bore_cutter_solid,
            "required_ligament_annulus": annulus,
        }
        mount_shapes.append(drilled)
        mount_bores.append(bore_cutter_solid)

    uncut_union = _fuse([bezel, chamber, cap_feature, *mount_shapes])
    expected_target = uncut_union.cut(Part.makeCompound(mount_bores)).removeSplitter()
    permitted = _fuse([bezel, chamber, cap_feature_uncut, *[record["uncut"] for record in mounts.values()]])
    return {
        "origin": origin,
        "axis_u": axis_u,
        "axis_v": axis_v,
        "axis_n": axis_n,
        "aperture": aperture,
        "outer_fit": outer_fit,
        "bezel": bezel,
        "chamber": chamber,
        "cap_feature": cap_feature,
        "cap_roots": cap_root_records,
        "mounts": mounts,
        "expected_target": expected_target,
        "permitted_envelope": permitted,
    }


def _bounds(shape: Any) -> dict[str, list[float]] | None:
    if shape.isNull():
        return None
    box = shape.BoundBox
    return {
        "minimum_mm": [float(box.XMin), float(box.YMin), float(box.ZMin)],
        "maximum_mm": [float(box.XMax), float(box.YMax), float(box.ZMax)],
    }


def _aabb_separation(shape: Any, minimum: Sequence[float], maximum: Sequence[float]) -> float:
    box = shape.BoundBox
    low = (box.XMin, box.YMin, box.ZMin)
    high = (box.XMax, box.YMax, box.ZMax)
    gaps = [
        max(float(minimum[i]) - float(high[i]), float(low[i]) - float(maximum[i]), 0.0)
        for i in range(3)
    ]
    return math.sqrt(sum(value * value for value in gaps))


def _boxes_overlap(first: Any, second: Any, tolerance: float = 1.0e-9) -> bool:
    a, b = first.BoundBox, second.BoundBox
    return not (
        a.XMax < b.XMin - tolerance
        or a.XMin > b.XMax + tolerance
        or a.YMax < b.YMin - tolerance
        or a.YMin > b.YMax + tolerance
        or a.ZMax < b.ZMin - tolerance
        or a.ZMin > b.ZMax + tolerance
    )


@dataclass
class ShellComponent:
    key: str
    shape: Any | None
    minimum_mm: list[float]
    maximum_mm: list[float]
    source: str


def _reconstruct_mesh_solid(path: Path, tolerance: float, Mesh: Any, Part: Any) -> Any:
    mesh = Mesh.Mesh(str(path))
    shell = Part.Shape()
    shell.makeShapeFromMesh(mesh.Topology, tolerance)
    if shell.isNull() or not shell.isClosed():
        raise RuntimeError("mesh did not reconstruct as a closed OCCT shell")
    solid = Part.makeSolid(shell)
    if not solid.isValid() or len(solid.Solids) != 1:
        raise RuntimeError("mesh did not reconstruct as one valid OCCT solid")
    return solid


def _load_shell_components(
    root: Path,
    baseline_path: Path,
    validation: dict[str, Any],
    App: Any,
    Mesh: Any,
    Part: Any,
) -> tuple[list[ShellComponent], dict[str, Any]]:
    source = validation["shell_matrix_sources"]
    errors: list[str] = []
    components: list[ShellComponent] = []
    upper_manifest_path = root / source["upper_component_manifest"]["path"]
    lower_manifest_path = root / source["lower_component_manifest"]["path"]
    lower_c001_path = root / source["lower_c001"]["path"]
    for label, spec, path in (
        ("upper component manifest", source["upper_component_manifest"], upper_manifest_path),
        ("lower component manifest", source["lower_component_manifest"], lower_manifest_path),
        ("lower C001", source["lower_c001"], lower_c001_path),
    ):
        actual = sha256_file(path) if path.is_file() else None
        if actual != spec["sha256"]:
            raise RuntimeError(f"{label} hash mismatch")
    upper_manifest = load_json(upper_manifest_path)
    lower_manifest = load_json(lower_manifest_path)
    upper_map = upper_manifest["review_objects"]["component_objects"]
    required_upper = {f"C{index:03d}" for index in range(1, 43) if index != 9}
    if set(upper_map) != required_upper:
        raise RuntimeError("upper shell manifest is not C001-C042 excluding C009")
    upper_doc = App.openDocument(str(baseline_path))
    try:
        for identifier in sorted(required_upper):
            obj = upper_doc.getObject(upper_map[identifier])
            if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
                errors.append(f"upper_{identifier}: missing or null")
                continue
            shape = obj.Shape.copy()
            box = shape.BoundBox
            components.append(
                ShellComponent(
                    f"upper_{identifier}",
                    shape,
                    [box.XMin, box.YMin, box.ZMin],
                    [box.XMax, box.YMax, box.ZMax],
                    obj.Name,
                )
            )
    finally:
        App.closeDocument(upper_doc.Name)

    lower_doc = App.openDocument(str(lower_c001_path))
    try:
        obj = lower_doc.getObject(source["lower_c001"]["object_name"])
        if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
            errors.append("lower_C001: missing or null")
        else:
            shape = obj.Shape.copy()
            box = shape.BoundBox
            components.append(
                ShellComponent(
                    "lower_C001",
                    shape,
                    [box.XMin, box.YMin, box.ZMin],
                    [box.XMax, box.YMax, box.ZMax],
                    obj.Name,
                )
            )
    finally:
        App.closeDocument(lower_doc.Name)

    lower_entries = {
        entry["name"]: entry
        for entry in lower_manifest["unchanged_components_002_through_060"]
    }
    required_lower = {f"V11_LOWER_COMPONENT_{index:03d}" for index in range(2, 61)}
    if set(lower_entries) != required_lower:
        raise RuntimeError("lower shell manifest is not C002-C060")
    tolerance = float(validation["mesh_to_occt_tolerance_mm"])
    for number in range(2, 61):
        identifier = f"C{number:03d}"
        entry = lower_entries[f"V11_LOWER_COMPONENT_{number:03d}"]
        path = root / entry["source_obj"]
        actual = sha256_file(path) if path.is_file() else None
        if actual != entry["source_obj_sha256"]:
            errors.append(f"lower_{identifier}: source hash mismatch")
            continue
        try:
            shape = _reconstruct_mesh_solid(path, tolerance, Mesh, Part)
        except Exception:
            shape = None
        components.append(
            ShellComponent(
                f"lower_{identifier}",
                shape,
                [float(value) for value in entry["bbox_min_mm"]],
                [float(value) for value in entry["bbox_max_mm"]],
                entry["source_obj"],
            )
        )
    return components, {"load_errors": errors}

def _load_protected_obstacles(
    baseline_path: Path, App: Any
) -> list[ShellComponent]:
    obstacles: list[ShellComponent] = []
    document = App.openDocument(str(baseline_path))
    try:
        for obj in document.Objects:
            if obj.Name == TARGET_OBJECT:
                continue
            if not hasattr(obj, "Shape") or obj.Shape.isNull():
                continue
            shape = obj.Shape.copy()
            box = shape.BoundBox
            obstacles.append(
                ShellComponent(
                    f"protected_{obj.Name}",
                    shape,
                    [box.XMin, box.YMin, box.ZMin],
                    [box.XMax, box.YMax, box.ZMax],
                    obj.Name,
                )
            )
    finally:
        App.closeDocument(document.Name)
    if not obstacles:
        raise RuntimeError("canonical baseline has no protected solid obstacles")
    return obstacles


def _intersection_record(shape: Any, component: ShellComponent, epsilon: float) -> dict[str, Any]:
    if component.shape is None:
        separation = _aabb_separation(shape, component.minimum_mm, component.maximum_mm)
        return {
            "intersection_volume_mm3": 0.0 if separation > 0.0 else None,
            "distance_lower_bound_mm": separation,
            "unresolved": separation <= 0.0,
            "method": "strict_aabb_separation_for_nonsewn_frozen_obj",
        }
    if not _boxes_overlap(shape, component.shape):
        return {
            "intersection_volume_mm3": 0.0,
            "distance_mm": float(shape.distToShape(component.shape)[0]),
            "unresolved": False,
            "method": "aabb_prefilter_then_occt_distance",
        }
    common = shape.common(component.shape)
    volume = float(common.Volume)
    return {
        "intersection_volume_mm3": volume,
        "distance_mm": float(shape.distToShape(component.shape)[0]),
        "intersection_bounds": _bounds(common) if volume > epsilon else None,
        "unresolved": False,
        "method": "exact_occt_common_and_distance",
    }


def _clearance_record(shape: Any, component: ShellComponent) -> dict[str, Any]:
    """Return an exact distance or a conservative AABB lower bound.

    A non-sewn frozen OBJ is acceptable only when its bounding box alone proves
    the required gap. Any overlapping AABB without an OCCT solid is unresolved
    and therefore fails closed in the evaluator.
    """
    if shape.isNull():
        return {
            "distance_mm": None,
            "unresolved": True,
            "method": "null_trimmed_target",
        }
    if component.shape is None:
        separation = _aabb_separation(
            shape, component.minimum_mm, component.maximum_mm
        )
        return {
            "distance_mm": separation if separation > 0.0 else None,
            "distance_lower_bound_mm": separation,
            "unresolved": separation <= 0.0,
            "method": "strict_aabb_lower_bound_for_nonsewn_frozen_obj",
        }
    if component.shape.isNull():
        return {
            "distance_mm": 1.0e300,
            "unresolved": False,
            "method": "no_component_material_outside_authorized_interface",
        }
    return {
        "distance_mm": float(shape.distToShape(component.shape)[0]),
        "unresolved": False,
        "method": "exact_occt_distance",
    }


def _authorized_interface_masks(
    parameters: dict[str, Any], references: dict[str, Any], Part: Any
) -> dict[str, Any]:
    settings = parameters["validation_contract"]["authorized_mating_interfaces"]
    mount_settings = settings["head_mounts"]
    radius = float(mount_settings["radial_mask_mm"])
    half_length = float(mount_settings["axial_half_length_mm"])
    masks = {"aperture_bezel": references["bezel"].copy()}
    for role, mount in references["mounts"].items():
        axis = mount["bore_axis_vector"]
        center = (mount["eye_bore"] + mount["head_bore"]) / 2.0
        masks[role] = Part.makeCylinder(
            radius,
            2.0 * half_length,
            center - axis * half_length,
            axis,
        )
    return masks


def _measure_sweep(
    moving: Any,
    translations: Sequence[Any],
    components: Sequence[ShellComponent],
    epsilon: float,
) -> dict[str, Any]:
    maximum = 0.0
    unresolved: list[str] = []
    samples = []
    for index, translation in enumerate(translations):
        placed = _translated(moving, translation)
        sample_max = 0.0
        for component in components:
            record = _intersection_record(placed, component, epsilon)
            if record["unresolved"]:
                unresolved.append(f"sample_{index}:{component.key}")
                continue
            sample_max = max(sample_max, float(record["intersection_volume_mm3"]))
        maximum = max(maximum, sample_max)
        samples.append({"index": index, "maximum_collision_mm3": sample_max})
    return {
        "sample_count": len(samples),
        "complete_sample_set": not unresolved,
        "maximum_unintended_collision_mm3": maximum if not unresolved else math.inf,
        "unresolved": unresolved,
        "samples": samples,
    }


def _hardware_envelopes(parameters: dict[str, Any], references: dict[str, Any], App: Any, Part: Any) -> dict[str, dict[str, Any]]:
    hardware = parameters["validation_contract"]["hardware_envelopes"]
    thickness = float(parameters["geometry"]["head_mount"]["leaf_thickness_mm"])
    mating_offset = float(parameters["geometry"]["head_mount"]["bore_center_to_mating_face_mm"])
    result: dict[str, dict[str, Any]] = {}
    for role, mount in references["mounts"].items():
        bore_axis_vector = mount["bore_axis_vector"]
        eye_bore = mount["eye_bore"]
        head_bore = mount["head_bore"]
        eye_owner_face = eye_bore + bore_axis_vector * (thickness - mating_offset)
        head_owner_face = head_bore - bore_axis_vector * (thickness - mating_offset)
        washer_thickness = float(hardware["washer_thickness_mm"])
        washer_radius = float(hardware["washer_outer_diameter_mm"]) / 2.0
        bolt = Part.makeCylinder(
            float(hardware["bolt_diameter_mm"]) / 2.0,
            float(hardware["bolt_max_length_mm"]),
            head_owner_face,
            bore_axis_vector,
        )
        head_washer = Part.makeCylinder(
            washer_radius,
            washer_thickness,
            head_owner_face - bore_axis_vector * washer_thickness,
            bore_axis_vector,
        )
        eye_washer = Part.makeCylinder(
            washer_radius,
            washer_thickness,
            eye_owner_face,
            bore_axis_vector,
        )
        nyloc = Part.makeCylinder(
            float(hardware["nyloc_outer_diameter_mm"]) / 2.0,
            float(hardware["nyloc_length_mm"]),
            head_owner_face
            - bore_axis_vector
            * (washer_thickness + float(hardware["nyloc_length_mm"])),
            bore_axis_vector,
        )
        tool = Part.makeCylinder(
            float(hardware["tool_approach_diameter_mm"]) / 2.0,
            float(hardware["tool_approach_length_mm"]),
            head_owner_face
            - bore_axis_vector
            * (
                washer_thickness
                + float(hardware["nyloc_length_mm"])
                + float(hardware["tool_approach_length_mm"])
            ),
            bore_axis_vector,
        )
        result[role] = {
            "bolt": bolt,
            "head_washer": head_washer,
            "eye_washer": eye_washer,
            "nyloc": nyloc,
            "tool": tool,
        }
    return result


def _safe_common_volume(first: Any, second: Any) -> float:
    if not _boxes_overlap(first, second):
        return 0.0
    return float(first.common(second).Volume)


def _read_step(Part: Any, path: Path) -> Any:
    shape = Part.Shape()
    shape.read(str(path))
    if shape.isNull():
        raise RuntimeError(f"STEP imported null: {path}")
    return shape


def _read_mesh_solid(Mesh: Any, Part: Any, path: Path, tolerance: float) -> Any:
    return _reconstruct_mesh_solid(path, tolerance, Mesh, Part)


def _metadata_exact(target: Any, parameters: dict[str, Any], App: Any) -> dict[str, bool]:
    required = {
        "ServiceableFitDesignId": DESIGN_ID,
        "ServiceableFitToolingRevision": str(TOOLING_REVISION),
        "ServiceableFitDesignSignature": parameters["design_control"]["design_signature"]["sha256"],
    }
    strings_ok = all(
        name in target.PropertiesList and str(getattr(target, name)) == value
        for name, value in required.items()
    )
    geometry = parameters["geometry"]
    dimension_pairs = (
        ("ServiceableFitHeadMountBoreDiameter", geometry["head_mount"]["bore_diameter_mm"]),
        ("ServiceableFitHeadMountMatingGap", geometry["head_mount"]["mating_gap_mm"]),
        ("ServiceableFitHeadMountLeafLength", geometry["head_mount"]["leaf_length_mm"]),
        ("ServiceableFitHeadMountLeafDepth", geometry["head_mount"]["leaf_depth_mm"]),
        ("ServiceableFitHeadMountLeafThickness", geometry["head_mount"]["leaf_thickness_mm"]),
        ("ServiceableFitCapOuterDiameter", geometry["rear_cap_connector"]["outer_diameter_mm"]),
        ("ServiceableFitCapBoreDiameter", geometry["rear_cap_connector"]["bore_diameter_mm"]),
        ("ServiceableFitCapEngagementDepth", geometry["rear_cap_connector"]["engagement_depth_mm"]),
        ("ServiceableFitCapMatingGap", geometry["rear_cap_connector"]["mating_gap_mm"]),
        ("ServiceableFitCapRootWidth", geometry["rear_cap_connector"]["local_root_width_mm"]),
        ("ServiceableFitCapRootAxialDepth", geometry["rear_cap_connector"]["root_axial_depth_mm"]),
        ("ServiceableFitCapRootWallOverlap", geometry["rear_cap_connector"]["wall_overlap_mm"]),
        ("ServiceableFitCapMaximumUnsupportedSpan", geometry["rear_cap_connector"]["maximum_local_root_span_mm"]),
        ("ServiceableFitDiffuserPocketClearance", geometry["diffuser_interface"]["pocket_clearance_mm"]),
        ("ServiceableFitMinimumChamberWall", geometry["chamber"]["wall_thickness_mm"]),
    )
    dimensions_ok = all(
        name in target.PropertiesList
        and abs(
            float(getattr(getattr(target, name), "Value", getattr(target, name)))
            - float(expected)
        )
        <= 1.0e-9
        for name, expected in dimension_pairs
    )
    root_dimensions_ok = True
    for role, expected in geometry["rear_cap_connector"][
        "edge_projection_preflight"
    ].items():
        if role not in ("upper", "lower"):
            continue
        title = role.capitalize()
        for suffix, value in (
            ("CenterToEdge", expected["center_to_edge_mm"]),
            ("UnsupportedSpan", expected["unsupported_span_mm"]),
            ("ProjectionSegmentParameter", expected["segment_parameter"]),
        ):
            name = f"ServiceableFitCap{title}{suffix}"
            root_dimensions_ok = root_dimensions_ok and name in target.PropertiesList
            if name in target.PropertiesList:
                actual = getattr(target, name)
                actual_value = float(getattr(actual, "Value", actual))
                root_dimensions_ok = root_dimensions_ok and abs(
                    actual_value - float(value)
                ) <= 1.0e-9
    lcs = parameters["aperture_lcs"]
    vector_pairs = (
        ("ServiceableFitLCSOrigin", lcs["origin_mm"]),
        ("ServiceableFitLCSU", lcs["u"]),
        ("ServiceableFitLCSV", lcs["v"]),
        ("ServiceableFitLCSInwardN", lcs["inward_n"]),
    )
    lcs_ok = strings_ok and all(
        name in target.PropertiesList
        and (getattr(target, name) - _vector(App, values)).Length <= 1.0e-9
        for name, values in vector_pairs
    )
    mount_ok = True
    frame_ok = True
    independent_frames = preflight_independent_signed_mount_frames(parameters)
    for role, datum in parameters["mount_datums"].items():
        title = role.capitalize()
        for suffix, values in (
            ("EyeBoreCenter", datum["eye_bore_center_mm"]),
            ("HeadBoreCenter", datum["head_bore_center_mm"]),
            ("BoreAxis", datum["bore_axis"]),
        ):
            name = f"ServiceableFit{title}{suffix}"
            mount_ok = mount_ok and name in target.PropertiesList and (
                getattr(target, name) - _vector(App, values)
            ).Length <= 1.0e-9
        frame = independent_frames["frames"][role]
        for suffix, values in (
            ("FrameBore", frame["bore_axis_vector"]),
            ("FrameDepth", frame["depth"]),
            ("FrameTangent", frame["tangent"]),
        ):
            name = f"ServiceableFit{title}{suffix}"
            frame_ok = frame_ok and name in target.PropertiesList and (
                getattr(target, name) - _vector(App, values)
            ).Length <= 1.0e-9
    return {
        "aperture_exact": strings_ok
        and "ServiceableFitVisibleAperture" in target.PropertiesList
        and len(target.ServiceableFitVisibleAperture) == len(lcs["visible_aperture_mm"])
        and max(
            (actual - _vector(App, expected)).Length
            for actual, expected in zip(
                target.ServiceableFitVisibleAperture,
                lcs["visible_aperture_mm"],
            )
        )
        <= 1.0e-9,
        "module_lcs_exact": lcs_ok,
        "connector_dimensions_exact": dimensions_ok and root_dimensions_ok,
        "mount_datums_exact": mount_ok,
        "signed_mount_frames_exact": frame_ok,
    }


def measure_previsual(
    root: Path,
    baseline: dict[str, Any],
    contract: dict[str, Any],
    preservation_report: dict[str, Any],
    root_projection_preflight: dict[str, Any],
    signed_frame_preflight: dict[str, Any],
    candidate_path: Path,
    App: Any,
    Mesh: Any,
    Part: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    parameters = contract["allowed_mutations"][0]["parameters"]
    validation = parameters["validation_contract"]
    limits = validation["limits"]
    epsilon = float(limits["maximum_unintended_positive_intersection_mm3"])
    references = _reference_geometry(parameters, App, Part)
    baseline_path = root / baseline["assembly"]["path"]
    components, component_load = _load_shell_components(
        root, baseline_path, validation, App, Mesh, Part
    )
    protected_obstacles = _load_protected_obstacles(baseline_path, App)
    collision_obstacles = [*components, *protected_obstacles]

    candidate_document = App.openDocument(str(candidate_path))
    try:
        target = candidate_document.getObject(TARGET_OBJECT)
        if target is None or not hasattr(target, "Shape") or target.Shape.isNull():
            raise RuntimeError("candidate target is missing or null")
        target_shape = target.Shape.copy()
        metadata = _metadata_exact(target, parameters, App)
    finally:
        App.closeDocument(candidate_document.Name)

    try:
        raw_check = target_shape.check(True)
        check_records = [str(item) for item in (raw_check or [])]
    except Exception as exc:
        check_records = [f"{type(exc).__name__}: {exc}"]
    topology = {
        "valid": bool(target_shape.isValid()),
        "closed": bool(target_shape.isClosed()),
        "solid_count": len(target_shape.Solids),
        "connected_component_count": len(target_shape.Solids),
        "self_intersection_count": len(check_records),
        "occt_check_records": check_records,
        "volume_mm3": float(target_shape.Volume),
        "bounds": _bounds(target_shape),
    }

    candidate_sha = sha256_file(candidate_path)
    preservation = {
        "status": preservation_report.get("status"),
        "candidate_hash_matches": preservation_report.get("candidate", {}).get("sha256")
        == candidate_sha,
        "protected_difference_count": len(
            preservation_report.get("protected_differences", {})
        ),
        "candidate_sha256": candidate_sha,
    }

    shell_results: dict[str, Any] = {}
    maximum_intersection = 0.0
    unresolved = list(component_load["load_errors"])
    for component in components:
        record = _intersection_record(target_shape, component, epsilon)
        shell_results[component.key] = record
        if record["unresolved"]:
            unresolved.append(component.key)
        else:
            maximum_intersection = max(
                maximum_intersection, float(record["intersection_volume_mm3"])
            )
    known = {
        "upper_C001": shell_results.get("upper_C001", {}).get("intersection_volume_mm3", math.inf),
        "lower_C001": shell_results.get("lower_C001", {}).get("intersection_volume_mm3", math.inf),
        "lower_C012": shell_results.get("lower_C012", {}).get("intersection_volume_mm3", math.inf),
        "lower_C013": shell_results.get("lower_C013", {}).get("intersection_volume_mm3", math.inf),
    }
    shell_matrix = {
        "component_count": len(shell_results),
        "unresolved_error_count": len(unresolved),
        "unresolved_errors": unresolved,
        "maximum_positive_intersection_mm3": maximum_intersection,
        "known_f19_intersections_mm3": known,
        "results": shell_results,
    }

    authorized_masks = _authorized_interface_masks(parameters, references, Part)
    all_authorized = _fuse(list(authorized_masks.values()))
    non_mating_target = target_shape.cut(all_authorized).removeSplitter()
    clearance_results: dict[str, Any] = {}
    clearance_unresolved: list[str] = []
    minimum_non_mating_clearance = math.inf
    for component in components:
        trimmed_component = component
        if component.shape is not None:
            trimmed_shape = component.shape.cut(all_authorized).removeSplitter()
            trimmed_component = ShellComponent(
                component.key,
                trimmed_shape,
                component.minimum_mm,
                component.maximum_mm,
                component.source,
            )
        record = _clearance_record(non_mating_target, trimmed_component)
        clearance_results[component.key] = record
        if record["unresolved"]:
            clearance_unresolved.append(component.key)
        else:
            minimum_non_mating_clearance = min(
                minimum_non_mating_clearance, float(record["distance_mm"])
            )

    upper_component = next(
        (component for component in components if component.key == "upper_C001"),
        None,
    )
    upper_authorized = _fuse(
        [authorized_masks["aperture_bezel"], authorized_masks["upper"]]
    )
    upper_target = target_shape.cut(upper_authorized).removeSplitter()
    if upper_component is None or upper_component.shape is None:
        upper_c001_record = {
            "distance_mm": None,
            "unresolved": True,
            "method": "missing_exact_upper_C001",
        }
    else:
        upper_shape = upper_component.shape.cut(upper_authorized).removeSplitter()
        upper_c001_record = _clearance_record(
            upper_target,
            ShellComponent("upper_C001", upper_shape, [], [], upper_component.source),
        )
    shell_matrix.update(
        {
            "authorized_interface_masks": sorted(authorized_masks),
            "clearance_unresolved_error_count": len(clearance_unresolved)
            + int(upper_c001_record["unresolved"]),
            "clearance_unresolved_errors": clearance_unresolved,
            "minimum_non_mating_clearance_mm": minimum_non_mating_clearance,
            "upper_c001_clearance_outside_authorized_interfaces_mm": upper_c001_record.get("distance_mm"),
            "upper_c001_clearance_record": upper_c001_record,
            "clearance_results": clearance_results,
        }
    )

    outside = target_shape.cut(references["permitted_envelope"]).removeSplitter()
    mount_shell_max = 0.0
    for mount in references["mounts"].values():
        for component in components:
            record = _intersection_record(mount["drilled"], component, epsilon)
            if not record["unresolved"]:
                mount_shell_max = max(
                    mount_shell_max, float(record["intersection_volume_mm3"])
                )
    containment = {
        "outside_permitted_envelope_mm3": float(outside.Volume),
        "outside_bounds": _bounds(outside),
        "mount_related_outside_volume_mm3": mount_shell_max,
    }

    # Exterior is the negative-LCS-normal half-space.  It is deliberately
    # oversized, then clipped to the target, so only positive volume matters.
    exterior_loop = [(-160.0, -160.0), (160.0, -160.0), (160.0, 160.0), (-160.0, 160.0)]
    exterior_points = [
        _from_local(u, v, -50.0, references["origin"], references["axis_u"], references["axis_v"], references["axis_n"])
        for u, v in exterior_loop
    ]
    exterior_halfspace = _face(Part, exterior_points).extrude(references["axis_n"] * 50.0)
    exterior_target = target_shape.common(exterior_halfspace)
    non_bezel_exterior = exterior_target.cut(references["bezel"]).removeSplitter()
    exterior_aperture = {
        "target_exterior_volume_mm3": float(exterior_target.Volume),
        "non_bezel_exterior_volume_mm3": float(non_bezel_exterior.Volume),
    }

    frustum_values = validation["aperture_view_frustum"]
    depth = float(frustum_values["depth_mm"])
    expansion = depth * math.tan(math.radians(float(frustum_values["half_angle_deg"])))
    far_loop = _radial_offset(App, references["aperture"], expansion, references["axis_n"])
    frustum = Part.makeLoft(
        [
            Part.makePolygon([*references["aperture"], references["aperture"][0]]),
            Part.makePolygon([*_at_depth(far_loop, depth, references["axis_n"]), _at_depth(far_loop, depth, references["axis_n"])[0]]),
        ],
        True,
        False,
    )
    hidden_features = _fuse(
        [
            references["chamber"],
            references["cap_feature"],
            *[record["drilled"] for record in references["mounts"].values()],
        ]
    )
    frustum_overlap = hidden_features.common(frustum)
    view_frustum = {
        "half_angle_deg": float(frustum_values["half_angle_deg"]),
        "mount_chamber_cap_volume_mm3": float(frustum_overlap.Volume),
        "overlap_bounds": _bounds(frustum_overlap),
    }

    fit_refs = parameters["fit_references"]
    for name, spec in fit_refs.items():
        path = root / spec["path"]
        if sha256_file(path) != spec["sha256"]:
            raise RuntimeError(f"fit reference hash mismatch: {name}")
    cap = _read_step(Part, root / fit_refs["exact_v9_cap"]["path"])
    diffuser = _read_mesh_solid(
        Mesh,
        Part,
        root / fit_refs["exact_diffuser"]["path"],
        float(validation["mesh_to_occt_tolerance_mm"]),
    )
    motion = validation["motion"]
    eye_steps = int(motion["eye_sweep_samples"])
    eye_distance = float(motion["eye_sweep_distance_mm"])
    eye_translations = [
        -references["axis_n"] * eye_distance * (1.0 - index / (eye_steps - 1))
        for index in range(eye_steps)
    ]
    moving_eye = _fuse([target_shape, diffuser])
    eye_sweep = _measure_sweep(
        moving_eye, eye_translations, collision_obstacles, epsilon
    )
    eye_sweep["insertion_sample_count"] = eye_steps
    eye_sweep["removal_is_exact_reverse"] = True
    eye_sweep["shell_component_count"] = len(components)
    eye_sweep["protected_obstacle_count"] = len(protected_obstacles)

    cap_steps = int(motion["rear_cap_sweep_samples"])
    cap_distance = float(motion["rear_cap_sweep_distance_mm"])
    seated_offset = float(parameters["geometry"]["rear_cap_connector"]["reference_seating_translation_mm"])
    cap_translations = [
        references["axis_n"]
        * (seated_offset + cap_distance * index / (cap_steps - 1))
        for index in range(cap_steps)
    ]
    cap_sweep = _measure_sweep(cap, cap_translations, collision_obstacles, epsilon)
    target_cap_max = 0.0
    for translation in cap_translations:
        target_cap_max = max(
            target_cap_max,
            _safe_common_volume(target_shape, _translated(cap, translation)),
        )
    cap_sweep["maximum_unintended_collision_mm3"] = max(
        float(cap_sweep["maximum_unintended_collision_mm3"]), target_cap_max
    )
    cap_sweep["removal_is_exact_reverse"] = True

    cap_sweep["shell_component_count"] = len(components)
    cap_sweep["protected_obstacle_count"] = len(protected_obstacles)
    hardware_shapes = _hardware_envelopes(parameters, references, App, Part)
    hardware_contract = validation["hardware_envelopes"]
    hardware_records: dict[str, Any] = {}
    all_cap_positions = [_translated(cap, translation) for translation in cap_translations]
    for role, shapes in hardware_shapes.items():
        current_mount = references["mounts"][role]["drilled"]
        opposite_role = "lower" if role == "upper" else "upper"
        opposite_mount = references["mounts"][opposite_role]["drilled"]
        max_collision = 0.0
        collision_details: dict[str, float] = {}
        for name, envelope in shapes.items():
            # The drilled current mount is included: the shaft must remain in
            # the bore and bearing envelopes may only touch, never overlap.
            subjects = {
                "target": target_shape,
                "opposite_mount": opposite_mount,
                "chamber": references["chamber"],
                "rear_cap_seated": all_cap_positions[0],
            }
            for subject_name, subject in subjects.items():
                volume = _safe_common_volume(envelope, subject)
                collision_details[f"{name}_vs_{subject_name}"] = volume
                max_collision = max(max_collision, volume)
            for component in collision_obstacles:
                record = _intersection_record(envelope, component, epsilon)
                if record["unresolved"]:
                    max_collision = math.inf
                else:
                    max_collision = max(
                        max_collision, float(record["intersection_volume_mm3"])
                    )
        hardware_records[role] = {
            "bolt_length_range_mm": [
                float(hardware_contract["bolt_min_length_mm"]),
                float(hardware_contract["bolt_max_length_mm"]),
            ],
            "washer_count": 2,
            "washer_od_mm": float(hardware_contract["washer_outer_diameter_mm"]),
            "washer_thickness_mm": float(hardware_contract["washer_thickness_mm"]),
            "nyloc_od_mm": float(hardware_contract["nyloc_outer_diameter_mm"]),
            "nyloc_length_mm": float(hardware_contract["nyloc_length_mm"]),
            "tool_diameter_mm": float(hardware_contract["tool_approach_diameter_mm"]),
            "tool_length_mm": float(hardware_contract["tool_approach_length_mm"]),
            "max_path_collision_mm3": max_collision,
            "max_prohibited_intersection_mm3": max_collision,
            "behind_flange_blocking_volume_mm3": max(
                collision_details.get("head_washer_vs_target", math.inf),
                collision_details.get("nyloc_vs_target", math.inf),
                collision_details.get("tool_vs_target", math.inf),
            ),
            "collision_details": collision_details,
            "current_mount_reference_volume_mm3": float(current_mount.Volume),
        }

    integrity: dict[str, Any] = {}
    mount_face_offset = float(
        parameters["geometry"]["head_mount"]["bore_center_to_mating_face_mm"]
    )
    for role, mount in references["mounts"].items():
        engagement = _safe_common_volume(mount["uncut"], references["chamber"])
        missing_ligament = mount["required_ligament_annulus"].cut(target_shape)
        measured_mating_gap = (
            (mount["eye_bore"] - mount["head_bore"]).dot(
                mount["bore_axis_vector"]
            )
            - 2.0 * mount_face_offset
        )
        integrity[role] = {
            "direct_owner_root_engagement_mm3": engagement,
            "required_ligament_missing_volume_mm3": float(missing_ligament.Volume),
            "head_mount_mating_gap_mm": float(measured_mating_gap),
            "bore_to_edge_material_mm": float(
                limits["minimum_bore_to_edge_material_mm"]
            )
            if float(missing_ligament.Volume) <= epsilon
            else 0.0,
        }

    expected_difference = target_shape.cut(references["expected_target"])
    expected_missing = references["expected_target"].cut(target_shape)
    cap_seated = _translated(cap, references["axis_n"] * seated_offset)
    cap_intersection = _safe_common_volume(target_shape, cap_seated)
    cap_clearance = float(target_shape.distToShape(cap_seated)[0])
    diffuser_intersection = _safe_common_volume(target_shape, diffuser)
    datum_interface = {
        **metadata,
        "signed_mount_frame_pass": signed_frame_preflight.get("status")
        == "PASS__INDEPENDENT_SIGNED_AXIS_FRAMES"
        and all(
            record.get("passed") is True
            for record in signed_frame_preflight.get("frames", {}).values()
        ),
        "signed_mount_frame_preflight": signed_frame_preflight,
        "rear_cap_root_projection_pass": root_projection_preflight.get("status")
        == "PASS__INDEPENDENT_EDGE_PROJECTIONS"
        and all(
            record.get("passed") is True
            for record in root_projection_preflight.get("roots", {}).values()
        ),
        "rear_cap_root_projection": root_projection_preflight,
        "reconstructed_cap_roots": references["cap_roots"],
        "rear_cap_interface_pass": cap_intersection <= epsilon
        and abs(
            cap_clearance - float(parameters["geometry"]["rear_cap_connector"]["mating_gap_mm"])
        )
        <= float(limits["maximum_dimensional_deviation_mm"]),
        "diffuser_interface_pass": diffuser_intersection <= epsilon,
        "minimum_wall_pass": float(expected_difference.Volume) <= epsilon
        and float(expected_missing.Volume) <= epsilon,
        "target_outside_expected_reference_mm3": float(expected_difference.Volume),
        "expected_reference_missing_from_target_mm3": float(expected_missing.Volume),
        "rear_cap_intersection_mm3": cap_intersection,
        "rear_cap_minimum_clearance_mm": cap_clearance,
        "diffuser_intersection_mm3": diffuser_intersection,
    }

    observations = {
        "topology": topology,
        "preservation": preservation,
        "shell_matrix": shell_matrix,
        "containment": containment,
        "exterior_aperture": exterior_aperture,
        "view_frustum": view_frustum,
        "eye_insertion_removal": eye_sweep,
        "rear_cap_sweep": cap_sweep,
        "hardware_access": hardware_records,
        "mount_integrity": integrity,
        "datum_and_interface_preservation": datum_interface,
    }
    evaluation = evaluate_previsual_observations(observations, limits)
    return observations, evaluation


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--preservation-report", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = repository_root(args.contract)
    baseline = load_json(args.baseline)
    contract = load_json(args.contract)
    parameters = contract["allowed_mutations"][0]["parameters"]
    registry_spec = parameters["design_control"]["rejected_signature_registry"]
    registry_path = root / registry_spec["path"]
    if sha256_file(registry_path) != registry_spec["sha256"]:
        raise DesignControlError("rejected-design registry hash mismatch")
    registry = load_json(registry_path)
    design_preflight = preflight_design_control(
        contract, registry, require_approval=True
    )
    root_projection_preflight = preflight_independent_root_projection(parameters)
    signed_frame_preflight = preflight_independent_signed_mount_frames(parameters)

    expected_baseline_hash = baseline["assembly"]["sha256"]
    baseline_path = root / baseline["assembly"]["path"]
    if sha256_file(baseline_path) != expected_baseline_hash:
        raise RuntimeError("canonical V34 hash mismatch")
    output_dir = root / contract["output"]["directory"]
    if not output_dir.is_dir():
        raise RuntimeError("iteration output directory is missing; validator never creates it")
    candidate_path = root / contract["output"]["candidate_fcstd"]
    preservation_path = args.preservation_report
    if not preservation_path.is_absolute():
        preservation_path = root / preservation_path
    expected_preservation = output_dir / "preservation-report.json"
    if preservation_path.resolve() != expected_preservation.resolve():
        raise RuntimeError("preservation report path is not the controlled iteration report")
    report_path = args.report
    if not report_path.is_absolute():
        report_path = root / report_path
    expected_report = output_dir / "previsual-validation.json"
    if report_path.resolve() != expected_report.resolve():
        raise RuntimeError("previsual report path is not the controlled iteration report")
    if report_path.exists():
        raise FileExistsError("refusing to overwrite previsual evidence")
    preservation_report = load_json(preservation_path)
    if preservation_report.get("status") != "PASS__READY_FOR_FIXED_VIEW_REVIEW":
        raise RuntimeError("exact preservation did not pass before previsual validation")
    if not candidate_path.is_file():
        raise RuntimeError("candidate is missing")

    import FreeCAD as App  # type: ignore
    import Mesh  # type: ignore
    import Part  # type: ignore

    observations, evaluation = measure_previsual(
        root,
        baseline,
        contract,
        preservation_report,
        root_projection_preflight,
        signed_frame_preflight,
        candidate_path,
        App,
        Mesh,
        Part,
    )
    result = {
        "schema_version": "1.0",
        "iteration_id": ITERATION_ID,
        "design_id": DESIGN_ID,
        "tooling_revision": TOOLING_REVISION,
        "validator": "independent-right-eye-serviceable-fit-previsual-v6",
        "design_preflight": design_preflight,
        "root_projection_preflight": root_projection_preflight,
        "signed_frame_preflight": signed_frame_preflight,
        "status": evaluation["status"],
        "evaluation": evaluation,
        "observations": observations,
        "deep_release_validation_run": False,
        "visual_approval_status": "PENDING" if evaluation["passed"] else "NOT_ELIGIBLE",
        "geometry_modified": False,
        "geometry_artifact_created": False,
        "approval_presentation_allowed": evaluation["approval_presentation_allowed"],
    }
    report_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if evaluation["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
