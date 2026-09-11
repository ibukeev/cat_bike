#!/usr/bin/env python3
"""Additive G09/G10 hardware-seat correction for the held split cassette.

The immutable V1 validator remains the authority for G01-G12 and every fixed
datum/tolerance.  This revision changes only the construction of the five
hardware envelopes used by G09/G10.  Instead of applying the legacy
``leaf_thickness_mm`` arithmetic to the 2.8 mm stepped mount, it locates the
actual analytic planar bearing faces concentric with each unchanged signed
M2.5 bore.  The bolt-head washer starts outside the target-side face.  The
nut-side washer, nyloc, and straight tool corridor terminate at the actual
outer signed-axis exit through the declared protected receiving owner; the
intersected BREP face and its normal mismatch are reported without pretending
that a faceted receiver face is parallel to the bore.

Tooling preflight constructs only disposable in-memory geometry.  Production
mode is read-only, requires a fresh hash-pinned authorization, and writes only
one new JSON report beside the immutable held candidate.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Iterator, Sequence


ORIGINAL_VALIDATOR_FILENAME = "validate_right_eye_split_service_cassette_previsual_v1.py"
ORIGINAL_VALIDATOR_SHA256 = "d7ad39bea689e8df54484eaf97c9077df73d3c8c8eb03c18696859ea15133ccf"
CONTRACT_RELATIVE = (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/v2/right-eye-split-service-cassette-prototype-v1.json"
)
CONTRACT_SHA256 = "08fa1c89ad307598e8b0edaa3dc55085cd2ddc977904209972ca698d21790b9f"
BASELINE_RELATIVE = (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/v2/approved-baseline-v34-lower-c001-relief-v1.json"
)
BASELINE_SHA256 = "f7225c42be8714a979962859991a7799e275a7d35fe4c774c6d7292019687ce3"
HELD_CANDIDATE_RELATIVE = (
    "reports/generated/cat-head-cad-iterations/"
    "right-eye-split-service-cassette-prototype-v1/candidate.FCStd"
)
HELD_CANDIDATE_SHA256 = "ec72a9480d105fdfdee2d509424b35de2e0abb0efb1eded14e718bfceb302f61"
PRESERVATION_RELATIVE = (
    "reports/generated/cat-head-cad-iterations/"
    "right-eye-split-service-cassette-prototype-v1/preservation-report.json"
)
PRESERVATION_SHA256 = "ea8ba3085962b53519d1aebf08d9624c96424c9b41801b0effff55cc9fd7c9b5"
FAILED_REPORT_RELATIVE = (
    "reports/generated/cat-head-cad-iterations/"
    "right-eye-split-service-cassette-prototype-v1/previsual-validation.json"
)
FAILED_REPORT_SHA256 = "e49b6ac67b7241a7a2178fa4ce83403fce0db3b0c131918de0317a12387c8d01"
RUNTIME_MANIFEST_RELATIVE = (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/v2/freecad-runtime-1.1.3-r20260725-occt-7.8.1.json"
)
RUNTIME_MANIFEST_SHA256 = "0051cd65fc00f3270aadecd992ad7f571a327646054399e9ee17f39ae48c4bf1"
VALIDATOR_ID = "independent-split-service-cassette-previsual-v1-validator-revision-001"
VALIDATOR_REVISION = 1
PERFORMANCE_TARGET_SECONDS = 180.0
PRODUCTION_TIMEOUT_SECONDS = 300
RECEIVING_OWNER_KEYS = {
    "upper": ("upper_C001",),
    "lower": ("lower_C001",),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_original() -> Any:
    path = Path(__file__).with_name(ORIGINAL_VALIDATOR_FILENAME)
    actual = sha256_file(path)
    if actual != ORIGINAL_VALIDATOR_SHA256:
        raise RuntimeError(f"immutable V1 validator hash mismatch: {actual}")
    name = "_cat_head_immutable_split_service_validator_v1"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load immutable validator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


original = _load_original()
evaluate = original.evaluate


def _resolve(root: Path, path: Path) -> Path:
    return path if path.is_absolute() else root / path


def _vector_values(vector: Any) -> list[float]:
    return [float(vector.x), float(vector.y), float(vector.z)]


def _face_normal(face: Any) -> Any:
    u_min, u_max, v_min, v_max = map(float, face.ParameterRange)
    normal = face.normalAt((u_min + u_max) / 2.0, (v_min + v_max) / 2.0)
    if float(normal.Length) <= 1.0e-12:
        raise RuntimeError("planar mount face has a zero normal")
    normal.normalize()
    return normal


def axial_bore_face_records(
    shape: Any,
    bore_center: Any,
    signed_axis: Any,
    bore_radius_mm: float,
    limits: dict[str, Any],
    source: str,
    Part: Any,
    require_bore_material_match: bool = True,
) -> list[dict[str, Any]]:
    """Return actual analytic bearing planes concentric with a signed bore."""

    axis_dot_min = float(limits["minimum_signed_mount_axis_dot"])
    radial_tolerance = float(limits["maximum_bore_center_axis_offset_mm"])
    dimension_tolerance = float(limits["maximum_dimensional_deviation_mm"])
    records: list[dict[str, Any]] = []
    for face_index, face in enumerate(shape.Faces, start=1):
        surface_type = str(
            getattr(face.Surface, "TypeId", type(face.Surface).__name__)
        )
        if "plane" not in surface_type.lower():
            continue
        normal = _face_normal(face)
        normal_dot = float(normal.dot(signed_axis))
        if abs(normal_dot) < axis_dot_min:
            continue
        plane_offset = float((face.CenterOfMass - bore_center).dot(signed_axis))
        plane_axis_point = bore_center + signed_axis * plane_offset
        axis_to_material = float(
            Part.Vertex(plane_axis_point).distToShape(face)[0]
        )
        material_residual = abs(axis_to_material - bore_radius_mm)
        if require_bore_material_match and material_residual > dimension_tolerance:
            continue
        matched_edge: dict[str, Any] | None = None
        for edge_index, edge in enumerate(face.Edges, start=1):
            curve = edge.Curve
            curve_type = str(getattr(curve, "TypeId", type(curve).__name__))
            if "circle" not in curve_type.lower():
                continue
            radius = float(curve.Radius)
            if abs(radius - bore_radius_mm) > dimension_tolerance:
                continue
            center = curve.Center
            radial_residual = float(
                (center - bore_center).cross(signed_axis).Length
            )
            if radial_residual > radial_tolerance:
                continue
            curve_axis = curve.Axis
            curve_axis.normalize()
            curve_axis_dot = float(curve_axis.dot(signed_axis))
            if abs(curve_axis_dot) < axis_dot_min:
                continue
            edge_offset = float((center - bore_center).dot(signed_axis))
            if abs(edge_offset - plane_offset) > dimension_tolerance:
                continue
            matched_edge = {
                "edge_index": edge_index,
                "curve_type": curve_type,
                "radius_mm": radius,
                "radius_residual_mm": abs(radius - bore_radius_mm),
                "center_mm": _vector_values(center),
                "center_axis_residual_mm": radial_residual,
                "curve_axis_dot_signed_bore": curve_axis_dot,
            }
            break
        records.append(
            {
                "source": source,
                "face_index": face_index,
                "surface_type": surface_type,
                "area_mm2": float(face.Area),
                "centroid_mm": _vector_values(face.CenterOfMass),
                "normal": _vector_values(normal),
                "normal_dot_signed_bore": normal_dot,
                "signed_plane_offset_from_bore_center_mm": plane_offset,
                "axis_to_face_material_distance_mm": axis_to_material,
                "axis_to_face_material_residual_mm": material_residual,
                "bore_edge": matched_edge,
                "_face": face,
            }
        )
    return records


def select_external_face(
    records: Sequence[dict[str, Any]],
    *,
    side: str,
    maximum_axial_distance_mm: float,
) -> dict[str, Any]:
    if side not in {"positive", "negative"}:
        raise ValueError(f"unsupported mount side: {side}")
    candidates = [
        record
        for record in records
        if abs(float(record["signed_plane_offset_from_bore_center_mm"]))
        <= maximum_axial_distance_mm
    ]
    if not candidates:
        raise RuntimeError(f"no actual axial bore face found on {side} side")
    selected = (
        max(candidates, key=lambda item: float(item["signed_plane_offset_from_bore_center_mm"]))
        if side == "positive"
        else min(candidates, key=lambda item: float(item["signed_plane_offset_from_bore_center_mm"]))
    )
    offset = float(selected["signed_plane_offset_from_bore_center_mm"])
    if (side == "positive" and offset <= 0.0) or (
        side == "negative" and offset >= 0.0
    ):
        raise RuntimeError(f"actual {side} external face has wrong signed offset: {offset}")
    return selected


def _public_face(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if not key.startswith("_")}


def _assert_fixed_hardware(hardware: dict[str, Any]) -> None:
    exact = {
        "bolt_nominal": "M2.5",
        "bolt_diameter_mm": 2.5,
        "bolt_min_length_mm": 8.0,
        "bolt_max_length_mm": 10.0,
        "washer_count_per_mount": 2,
        "washer_outer_diameter_mm": 7.0,
        "washer_thickness_mm": 0.8,
        "nyloc_outer_diameter_mm": 7.0,
        "nyloc_length_mm": 5.0,
        "tool_approach_diameter_mm": 8.0,
        "tool_approach_length_mm": 20.0,
    }
    for key, expected in exact.items():
        actual = hardware.get(key)
        if actual != expected:
            raise RuntimeError(f"fixed hardware changed: {key}={actual!r} != {expected!r}")


def select_unique_negative_receiver_interval(
    intervals: Sequence[dict[str, Any]], tolerance_mm: float
) -> dict[str, Any]:
    negative = [
        item
        for item in intervals
        if float(item["minimum_offset_mm"]) < -tolerance_mm
        and float(item["maximum_offset_mm"]) <= tolerance_mm
    ]
    if len(negative) != 1:
        raise RuntimeError(
            "missing or ambiguous receiving-owner axis interval: "
            f"found {len(negative)}"
        )
    return negative[0]


def receiving_owner_outer_exit(
    role: str,
    mount: dict[str, Any],
    shell_components: Sequence[Any],
    limits: dict[str, Any],
    Part: Any,
) -> tuple[Any, dict[str, Any]]:
    """Find the negative-axis exit of the actual protected receiving solid."""

    if role not in RECEIVING_OWNER_KEYS:
        raise RuntimeError(f"undeclared receiving-owner role: {role}")
    inventory = {str(component.key): component for component in shell_components}
    expected_keys = RECEIVING_OWNER_KEYS[role]
    if any(key not in inventory for key in expected_keys):
        raise RuntimeError(f"{role}: declared receiving owner is missing")
    axis = mount["bore_axis_vector"]
    center = mount["head_bore"]
    half_length = 20.0
    probe = Part.makeLine(
        center - axis * half_length,
        center + axis * half_length,
    )
    intervals: list[dict[str, Any]] = []
    for key in expected_keys:
        owner = inventory[key]
        if owner.shape is None or owner.shape.isNull():
            raise RuntimeError(f"{role}: receiving owner {key} has no exact shape")
        section = owner.shape.common(probe)
        for edge_index, edge in enumerate(section.Edges, start=1):
            offsets = sorted(
                float((vertex.Point - center).dot(axis))
                for vertex in edge.Vertexes
            )
            if len(offsets) < 2 or offsets[-1] - offsets[0] <= 1.0e-9:
                continue
            intervals.append(
                {
                    "owner_key": key,
                    "owner_source": str(owner.source),
                    "section_edge_index": edge_index,
                    "minimum_offset_mm": offsets[0],
                    "maximum_offset_mm": offsets[-1],
                    "_owner_shape": owner.shape,
                }
            )
    tolerance = float(limits["maximum_dimensional_deviation_mm"])
    try:
        selected = select_unique_negative_receiver_interval(intervals, tolerance)
    except RuntimeError as exc:
        raise RuntimeError(f"{role}: {exc}") from exc
    exit_offset = float(selected["minimum_offset_mm"])
    exit_point = center + axis * exit_offset
    owner_shape = selected["_owner_shape"]
    face_candidates: list[dict[str, Any]] = []
    vertex = Part.Vertex(exit_point)
    for face_index, face in enumerate(owner_shape.Faces, start=1):
        distance = float(vertex.distToShape(face)[0])
        if distance > tolerance:
            continue
        normal = _face_normal(face)
        dot = float(normal.dot(axis))
        face_candidates.append(
            {
                "face_index": face_index,
                "surface_type": str(
                    getattr(face.Surface, "TypeId", type(face.Surface).__name__)
                ),
                "distance_to_exit_mm": distance,
                "normal": _vector_values(normal),
                "normal_dot_signed_bore": dot,
                "normal_parallel_mismatch": 1.0 - abs(dot),
            }
        )
    if not face_candidates:
        raise RuntimeError(f"{role}: receiving-owner exit face was not found")
    face_candidates.sort(
        key=lambda item: (
            float(item["distance_to_exit_mm"]),
            float(item["normal_parallel_mismatch"]),
            int(item["face_index"]),
        )
    )
    best = face_candidates[0]
    equally_near = [
        item
        for item in face_candidates
        if abs(float(item["distance_to_exit_mm"]) - float(best["distance_to_exit_mm"]))
        <= 1.0e-7
        and abs(float(item["normal_parallel_mismatch"]) - float(best["normal_parallel_mismatch"]))
        <= 1.0e-7
    ]
    if len(equally_near) != 1:
        raise RuntimeError(f"{role}: receiving-owner exit face is ambiguous")
    return exit_point, {
        "algorithm": "signed-bore-axis-protected-owner-solid-exit-v1",
        "declared_owner_keys": list(expected_keys),
        "owner_key": selected["owner_key"],
        "owner_source": selected["owner_source"],
        "axis_interval_mm": [
            float(selected["minimum_offset_mm"]),
            float(selected["maximum_offset_mm"]),
        ],
        "outer_exit_offset_from_head_bore_mm": exit_offset,
        "outer_exit_point_mm": _vector_values(exit_point),
        "intersected_face": best,
    }


def hardware_shapes_from_actual_faces(
    parameters: dict[str, Any],
    references: dict[str, Any],
    shell_components: Sequence[Any],
    Part: Any,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    hardware = parameters["validation_contract"]["hardware_envelopes"]
    limits = parameters["validation_contract"]["limits"]
    _assert_fixed_hardware(hardware)
    mount_values = parameters["geometry"]["head_mount"]
    bore_radius = float(mount_values["bore_diameter_mm"]) / 2.0
    search_distance = float(hardware["bolt_max_length_mm"])
    result: dict[str, dict[str, Any]] = {}
    evidence: dict[str, Any] = {}
    for role, mount in references["mounts"].items():
        axis = mount["bore_axis_vector"]
        eye_records = axial_bore_face_records(
            mount["drilled"], mount["eye_bore"], axis, bore_radius, limits,
            f"{role}:target_stepped_mount", Part,
        )
        eye_face = select_external_face(
            eye_records, side="positive", maximum_axial_distance_mm=search_distance
        )
        shell_seat, receiver_evidence = receiving_owner_outer_exit(
            role, mount, shell_components, limits, Part
        )
        eye_seat = mount["eye_bore"] + axis * float(
            eye_face["signed_plane_offset_from_bore_center_mm"]
        )
        seat_span = float((eye_seat - shell_seat).dot(axis))
        if seat_span <= 0.0 or seat_span > float(hardware["bolt_max_length_mm"]):
            raise RuntimeError(f"{role}: actual support-face span is invalid: {seat_span}")
        washer_t = float(hardware["washer_thickness_mm"])
        nyloc_l = float(hardware["nyloc_length_mm"])
        tool_l = float(hardware["tool_approach_length_mm"])
        result[role] = {
            "bolt": Part.makeCylinder(
                float(hardware["bolt_diameter_mm"]) / 2.0,
                float(hardware["bolt_max_length_mm"]), shell_seat, axis,
            ),
            "head_washer": Part.makeCylinder(
                float(hardware["washer_outer_diameter_mm"]) / 2.0,
                washer_t, shell_seat - axis * washer_t, axis,
            ),
            "eye_washer": Part.makeCylinder(
                float(hardware["washer_outer_diameter_mm"]) / 2.0,
                washer_t, eye_seat, axis,
            ),
            "nyloc": Part.makeCylinder(
                float(hardware["nyloc_outer_diameter_mm"]) / 2.0,
                nyloc_l, shell_seat - axis * (washer_t + nyloc_l), axis,
            ),
            "tool": Part.makeCylinder(
                float(hardware["tool_approach_diameter_mm"]) / 2.0,
                tool_l,
                shell_seat - axis * (washer_t + nyloc_l + tool_l), axis,
            ),
        }
        evidence[role] = {
            "algorithm": "actual-analytic-planar-mount-faces-on-signed-bore-v1",
            "signed_bore_axis": _vector_values(axis),
            "eye_bore_center_mm": _vector_values(mount["eye_bore"]),
            "head_bore_center_mm": _vector_values(mount["head_bore"]),
            "target_eye_external_face": _public_face(eye_face),
            "protected_receiver_outer_exit": receiver_evidence,
            "actual_outer_face_span_mm": seat_span,
            "bolt_head_washer_seat_mm": _vector_values(eye_seat),
            "nyloc_washer_seat_mm": _vector_values(shell_seat),
            "hardware": {
                "bolt_nominal": hardware["bolt_nominal"],
                "bolt_diameter_mm": float(hardware["bolt_diameter_mm"]),
                "bolt_length_range_mm": [
                    float(hardware["bolt_min_length_mm"]),
                    float(hardware["bolt_max_length_mm"]),
                ],
                "washer_outer_diameter_mm": float(hardware["washer_outer_diameter_mm"]),
                "washer_thickness_mm": washer_t,
                "nyloc_outer_diameter_mm": float(hardware["nyloc_outer_diameter_mm"]),
                "nyloc_length_mm": nyloc_l,
                "tool_approach_diameter_mm": float(hardware["tool_approach_diameter_mm"]),
                "tool_approach_length_mm": tool_l,
            },
        }
    return result, evidence


@contextlib.contextmanager
def corrected_hardware_context() -> Iterator[dict[str, Any]]:
    """Patch only V1's in-memory helper call and restore it unconditionally."""

    captured: dict[str, Any] = {}
    old_loader = original.generator._load_shell_components
    old_hardware = original.generator.toolkit.hardware_shapes

    def recording_loader(*args: Any, **kwargs: Any) -> Any:
        components = old_loader(*args, **kwargs)
        captured["shell_components"] = components
        return components

    def revised_hardware(parameters: dict[str, Any], refs: dict[str, Any], Part: Any) -> Any:
        if "shell_components" not in captured:
            raise RuntimeError("shell matrix was not loaded before hardware derivation")
        shapes, evidence = hardware_shapes_from_actual_faces(
            parameters, refs, captured["shell_components"], Part
        )
        captured["face_evidence"] = evidence
        return shapes

    original.generator._load_shell_components = recording_loader
    original.generator.toolkit.hardware_shapes = revised_hardware
    try:
        yield captured
    finally:
        original.generator._load_shell_components = old_loader
        original.generator.toolkit.hardware_shapes = old_hardware


def revised_measure(*args: Any, **kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    with corrected_hardware_context() as captured:
        observations, evaluation = original._measure(*args, **kwargs)
    observations["hardware"]["seat_derivation"] = captured["face_evidence"]
    return observations, evaluation


def _verify_base_inputs(root: Path, baseline_path: Path, contract_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    baseline_path = _resolve(root, baseline_path)
    contract_path = _resolve(root, contract_path)
    exact = {
        baseline_path: BASELINE_SHA256,
        contract_path: CONTRACT_SHA256,
        root / RUNTIME_MANIFEST_RELATIVE: RUNTIME_MANIFEST_SHA256,
        Path(__file__).with_name(ORIGINAL_VALIDATOR_FILENAME): ORIGINAL_VALIDATOR_SHA256,
    }
    if baseline_path.resolve() != (root / BASELINE_RELATIVE).resolve():
        raise RuntimeError("baseline path differs from immutable held lineage")
    if contract_path.resolve() != (root / CONTRACT_RELATIVE).resolve():
        raise RuntimeError("contract path differs from immutable held lineage")
    for path, expected in exact.items():
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(f"immutable pin mismatch: {path}: {actual}")
    baseline = original.load_json(baseline_path)
    contract = original.load_json(contract_path)
    original._preflight(root, baseline, contract)
    return baseline, contract


def _hardware_fixture_preflight(
    root: Path, baseline: dict[str, Any], contract: dict[str, Any], App: Any, Mesh: Any, Part: Any
) -> dict[str, Any]:
    del baseline, Mesh
    started = time.monotonic()
    parameters = contract["allowed_mutations"][0]["parameters"]
    target, _ = original.generator.construct_split_cassette(parameters, App, Part)
    refs = original._reference_geometry(parameters, App, Part)
    components = original.generator._load_shell_components(parameters, App, Part)
    hardware, evidence = hardware_shapes_from_actual_faces(
        parameters, refs, components, Part
    )
    cartridge = refs["cartridge"]
    shell_shapes = [item.shape for item in components if item.shape is not None]
    details: dict[str, Any] = {}
    maximum_target = 0.0
    maximum_other = 0.0
    for role, items in hardware.items():
        opposite = "lower" if role == "upper" else "upper"
        role_details: dict[str, Any] = {}
        for name, item in items.items():
            target_volume = original._common_volume(target, item)
            other_volume = max(
                original._common_volume(cartridge, item),
                original._common_volume(refs["mounts"][opposite]["drilled"], item),
                *(original._common_volume(shell, item) for shell in shell_shapes),
            )
            maximum_target = max(maximum_target, target_volume)
            maximum_other = max(maximum_other, other_volume)
            role_details[name] = {
                "target_obstruction_mm3": target_volume,
                "cartridge_shell_or_opposite_obstruction_mm3": other_volume,
            }
        details[role] = role_details
    epsilon = float(
        parameters["validation_contract"]["limits"]
        ["maximum_unintended_positive_intersection_mm3"]
    )
    elapsed = time.monotonic() - started
    passed = maximum_target <= epsilon and maximum_other <= epsilon
    return {
        "schema_version": "1.0",
        "status": (
            "PASS__IN_MEMORY_G09_G10_ACTUAL_FACE_PREFLIGHT"
            if passed and elapsed < PERFORMANCE_TARGET_SECONDS
            else "FAIL__IN_MEMORY_G09_G10_ACTUAL_FACE_PREFLIGHT"
        ),
        "validator_id": VALIDATOR_ID,
        "validator_revision": VALIDATOR_REVISION,
        "scope": "G09_G10_HARDWARE_ENVELOPE_PLACEMENT_ONLY",
        "gate_verdict_publication_suppressed": True,
        "candidate_opened": False,
        "candidate_output_reused": False,
        "save_as_called": False,
        "document_save_called": False,
        "geometry_export_created": False,
        "elapsed_seconds": elapsed,
        "target_seconds": PERFORMANCE_TARGET_SECONDS,
        "maximum_target_obstruction_mm3": maximum_target,
        "maximum_cartridge_or_shell_obstruction_mm3": maximum_other,
        "fixed_tolerance_mm3": epsilon,
        "face_derivation": evidence,
        "fixture_collision_details": details,
    }


def discover_receiving_owners(
    contract: dict[str, Any], App: Any, Part: Any
) -> dict[str, Any]:
    """Read-only signed-axis ownership scan over all authoritative owners."""

    parameters = contract["allowed_mutations"][0]["parameters"]
    frames = original.generator.toolkit.reconstruct_mount_frames(parameters, App)
    components = original.generator._load_shell_components(parameters, App, Part)
    if len(components) != 101:
        raise RuntimeError(f"authoritative owner count changed: {len(components)}")
    tolerance = float(
        parameters["validation_contract"]["limits"]
        ["maximum_dimensional_deviation_mm"]
    )
    roles: dict[str, Any] = {}
    for role, mount in frames.items():
        axis = mount["bore_axis_vector"]
        center = mount["head_bore"]
        probe = Part.makeLine(center - axis * 10.0, center + axis * 10.0)
        center_vertex = Part.Vertex(center)
        matches: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        for component in components:
            shape = component.shape
            if shape is None or shape.isNull():
                unresolved.append({
                    "owner_key": str(component.key),
                    "owner_source": str(component.source),
                    "reason": "exact solid unavailable",
                })
                continue
            nearest = float(center_vertex.distToShape(shape)[0])
            contains = bool(shape.isInside(center, tolerance, True))
            section = shape.common(probe)
            intervals: list[list[float]] = []
            for edge in section.Edges:
                offsets = sorted(
                    float((vertex.Point - center).dot(axis))
                    for vertex in edge.Vertexes
                )
                if len(offsets) >= 2 and offsets[-1] - offsets[0] > 1.0e-9:
                    intervals.append([offsets[0], offsets[-1]])
            point_offsets = sorted(
                {
                    round(float((vertex.Point - center).dot(axis)), 12)
                    for vertex in section.Vertexes
                }
            )
            if contains or intervals or point_offsets:
                matches.append({
                    "owner_key": str(component.key),
                    "owner_source": str(component.source),
                    "center_inside_solid": contains,
                    "nearest_distance_from_head_bore_center_mm": nearest,
                    "signed_axis_intervals_within_plus_minus_10_mm": intervals,
                    "signed_axis_intersection_points_mm": point_offsets,
                })
        roles[role] = {
            "head_bore_center_mm": _vector_values(center),
            "signed_bore_axis": _vector_values(axis),
            "matching_owners": matches,
            "matching_owner_count": len(matches),
            "unresolved_exact_owner_count": len(unresolved),
            "unresolved_exact_owners": unresolved,
        }
    return {
        "status": "READ_ONLY_101_OWNER_SIGNED_AXIS_DISCOVERY_COMPLETE",
        "candidate_opened": False,
        "candidate_output_reused": False,
        "document_save_called": False,
        "geometry_export_created": False,
        "authoritative_owner_count": len(components),
        "probe_half_length_mm": 10.0,
        "roles": roles,
    }


def validate_authorization(root: Path, path: Path, expected_hash: str) -> tuple[dict[str, Any], str]:
    path = _resolve(root, path)
    actual_hash = sha256_file(path)
    if actual_hash != expected_hash:
        raise RuntimeError("authorization hash mismatch")
    record = original.load_json(path)
    if record.get("state") != "AUTHORIZED__NOT_INVOKED":
        raise RuntimeError("authorization is not fresh")
    if record.get("classification") != "VALIDATOR_HOLD__CANDIDATE_IMMUTABLE":
        raise RuntimeError("authorization classification changed")
    pins = record.get("immutable_pins", {})
    expected_pins = {
        "candidate_sha256": HELD_CANDIDATE_SHA256,
        "preservation_report_sha256": PRESERVATION_SHA256,
        "failed_validator_report_sha256": FAILED_REPORT_SHA256,
        "original_contract_sha256": CONTRACT_SHA256,
        "original_validator_sha256": ORIGINAL_VALIDATOR_SHA256,
        "baseline_manifest_sha256": BASELINE_SHA256,
        "runtime_manifest_sha256": RUNTIME_MANIFEST_SHA256,
    }
    if any(pins.get(key) != value for key, value in expected_pins.items()):
        raise RuntimeError("authorization immutable pins changed")
    revision = record.get("validator_revision", {})
    if revision.get("id") != VALIDATOR_ID or int(revision.get("revision", -1)) != VALIDATOR_REVISION:
        raise RuntimeError("authorization validator identity changed")
    revision_path = root / revision.get("path", "")
    if revision_path.resolve() != Path(__file__).resolve():
        raise RuntimeError("authorization validator path changed")
    if sha256_file(revision_path) != revision.get("sha256"):
        raise RuntimeError("authorization validator hash changed")
    preflight = record.get("in_memory_preflight", {})
    preflight_path = root / preflight.get("path", "")
    if sha256_file(preflight_path) != preflight.get("sha256"):
        raise RuntimeError("authorization preflight hash changed")
    if original.load_json(preflight_path).get("status") != "PASS__IN_MEMORY_G09_G10_ACTUAL_FACE_PREFLIGHT":
        raise RuntimeError("authorization preflight did not pass")
    regression = record.get("regression", {})
    test_path = root / regression.get("test_path", "")
    if sha256_file(test_path) != regression.get("test_sha256") or regression.get("status") != "PASS":
        raise RuntimeError("authorization regression evidence changed")
    report_path = root / record.get("fresh_output", {}).get("report_path", "")
    expected_parent = root / Path(HELD_CANDIDATE_RELATIVE).parent
    if report_path.parent.resolve() != expected_parent.resolve() or report_path.exists():
        raise RuntimeError("authorized output is not fresh in held iteration")
    if record.get("max_invocations") != 1 or record.get("production_timeout_seconds") != PRODUCTION_TIMEOUT_SECONDS:
        raise RuntimeError("authorization invocation budget changed")
    return record, actual_hash


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--performance-preflight", action="store_true")
    parser.add_argument("--timing-report", type=Path)
    parser.add_argument("--verify-authorization-only", action="store_true")
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--authorization-sha256")
    parser.add_argument("--ownership-discovery", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = original.generator.repo_root()
    baseline, contract = _verify_base_inputs(root, args.baseline, args.contract)
    if args.ownership_discovery:
        if (
            args.performance_preflight
            or args.verify_authorization_only
            or args.timing_report is not None
            or args.authorization is not None
        ):
            raise RuntimeError("ownership discovery is a standalone read-only mode")
        import FreeCAD as App  # type: ignore
        import Part  # type: ignore

        print(json.dumps(discover_receiving_owners(contract, App, Part), indent=2, sort_keys=True))
        return 0
    if args.verify_authorization_only:
        if args.authorization is None or args.authorization_sha256 is None:
            raise RuntimeError("hash-pinned authorization is required")
        record, digest = validate_authorization(root, args.authorization, args.authorization_sha256)
        print(json.dumps({
            "status": "VALIDATOR_AUTHORIZATION_READY__NOT_INVOKED",
            "authorization_id": record["authorization_id"],
            "authorization_sha256": digest,
            "candidate_opened": False,
            "validator_invoked": False,
        }, indent=2, sort_keys=True))
        return 0
    if not args.performance_preflight:
        raise RuntimeError("this tooling session permits only --performance-preflight or --verify-authorization-only")
    if args.timing_report is None or args.authorization is not None:
        raise RuntimeError("preflight requires one fresh --timing-report and no authorization")
    report_path = _resolve(root, args.timing_report)
    tooling_root = root / "reports/generated/cat-head-cad-tooling"
    try:
        report_path.resolve().relative_to(tooling_root.resolve())
    except ValueError as exc:
        raise RuntimeError("timing report must stay under cat-head-cad-tooling") from exc
    if report_path.exists():
        raise FileExistsError("refusing to overwrite tooling preflight")
    import FreeCAD as App  # type: ignore
    import Mesh  # type: ignore
    import Part  # type: ignore

    report = _hardware_fixture_preflight(root, baseline, contract, App, Mesh, Part)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(report["status"])
    return 0 if report["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
