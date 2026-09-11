#!/usr/bin/env python3
"""Generate one V6 serviceable-fit right-eye candidate from canonical V34.

This is a new construction lineage.  It does not import, call, inspect, or
reuse the V1/V3 generator, any V1/V3 candidate, or either quarantined V4/V5
FCStd.  The eye is reconstructed from the protected aperture/LCS, the numeric
V5/V17 mount datums, and the V6 serviceability contract.

The generator writes only the one iteration directory: a same-document
candidate plus opaque review PNGs.  It does not write a validation report.
Independent preservation and pre-visual validation must pass before any image
may be presented for approval.
"""

from __future__ import annotations

import argparse
import binascii
import hashlib
import importlib.util
import json
import math
import struct
import sys
import zlib
from pathlib import Path
from typing import Any, Sequence

import validate_right_eye_serviceable_fit_previsual_v6 as design_control


ITERATION_ID = "right-eye-serviceable-fit-prototype-v6"
DESIGN_ID = "right-eye-serviceable-fit-C"
TOOLING_REVISION = 3
TARGET_OBJECT = "FROZEN_REPAIRED_RIGHT_EYE_V4_V34"
IMAGE_WIDTH = 1000
IMAGE_HEIGHT = 750
EDGE_PROJECTION_ALGORITHM = "nearest-point-on-closed-polygon-edge-v1"
V9_BOSS_CENTERS_MM = {
    "upper": (72.2476, 78.1286, 175.5293),
    "lower": (66.305, 63.709, 134.355),
}


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--pure-frame-preflight-only", action="store_true")
    mode.add_argument(
        "--in-memory-finalization-preflight",
        "--in-memory-construction-preflight",
        dest="in_memory_finalization_preflight",
        action="store_true",
    )
    return parser.parse_args(argv)


def repository_root(start: Path) -> Path:
    return design_control.repository_root(start)


def load_json(path: Path) -> dict[str, Any]:
    return design_control.load_json(path)


def sha256_file(path: Path) -> str:
    return design_control.sha256_file(path)


def _dot3(first: Sequence[float], second: Sequence[float]) -> float:
    return sum(float(a) * float(b) for a, b in zip(first, second))


def _add3(first: Sequence[float], second: Sequence[float]) -> tuple[float, float, float]:
    return tuple(float(a) + float(b) for a, b in zip(first, second))  # type: ignore[return-value]


def _subtract3(first: Sequence[float], second: Sequence[float]) -> tuple[float, float, float]:
    return tuple(float(a) - float(b) for a, b in zip(first, second))  # type: ignore[return-value]


def _scale3(value: Sequence[float], scale: float) -> tuple[float, float, float]:
    return tuple(float(component) * float(scale) for component in value)  # type: ignore[return-value]


def _cross3(
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


def _length3(value: Sequence[float]) -> float:
    return math.sqrt(_dot3(value, value))


def _normalize3(value: Sequence[float], label: str) -> tuple[float, float, float]:
    length = math.sqrt(_dot3(value, value))
    if length <= 1.0e-12:
        raise RuntimeError(f"{label} has zero length")
    return _scale3(value, 1.0 / length)


def _rear_inner_polygon_uv(parameters: dict[str, Any]) -> list[tuple[float, float]]:
    """Reconstruct the signed rear inner perimeter without importing FreeCAD."""
    lcs = parameters["aperture_lcs"]
    origin = tuple(float(value) for value in lcs["origin_mm"])
    axis_u = _normalize3(lcs["u"], "LCS u")
    axis_v = _normalize3(lcs["v"], "LCS v")
    axis_n = _normalize3(lcs["inward_n"], "LCS inward n")
    if max(
        abs(_dot3(axis_u, axis_v)),
        abs(_dot3(axis_u, axis_n)),
        abs(_dot3(axis_v, axis_n)),
    ) > 1.0e-6:
        raise RuntimeError("protected module LCS is not orthogonal")

    projected: list[tuple[float, float, float]] = []
    for raw_point in lcs["visible_aperture_mm"]:
        delta = _subtract3(raw_point, origin)
        projected.append(
            _add3(
                origin,
                _add3(
                    _scale3(axis_u, _dot3(delta, axis_u)),
                    _scale3(axis_v, _dot3(delta, axis_v)),
                ),
            )
        )
    center = tuple(
        sum(point[index] for point in projected) / float(len(projected))
        for index in range(3)
    )
    offset = float(parameters["geometry"]["chamber"]["rear_inner_offset_mm"])
    output: list[tuple[float, float]] = []
    for point in projected:
        radial = _subtract3(point, center)
        radial = _subtract3(radial, _scale3(axis_n, _dot3(radial, axis_n)))
        radial = _normalize3(radial, "rear inner loop radial")
        shifted = _add3(point, _scale3(radial, offset))
        delta = _subtract3(shifted, origin)
        output.append((_dot3(delta, axis_u), _dot3(delta, axis_v)))
    return output


def nearest_point_on_polygon_edge_uv(
    point_uv: Sequence[float],
    polygon_uv: Sequence[Sequence[float]],
) -> dict[str, Any]:
    """Return the deterministic nearest point on a closed polygon's edges."""
    if len(polygon_uv) < 3:
        raise RuntimeError("rear inner perimeter requires at least three vertices")
    point = (float(point_uv[0]), float(point_uv[1]))
    best: dict[str, Any] | None = None
    for edge_index, start_raw in enumerate(polygon_uv):
        end_raw = polygon_uv[(edge_index + 1) % len(polygon_uv)]
        start = (float(start_raw[0]), float(start_raw[1]))
        end = (float(end_raw[0]), float(end_raw[1]))
        edge = (end[0] - start[0], end[1] - start[1])
        length_squared = edge[0] * edge[0] + edge[1] * edge[1]
        if length_squared <= 1.0e-18:
            raise RuntimeError(f"rear inner perimeter edge {edge_index} is degenerate")
        raw_t = (
            (point[0] - start[0]) * edge[0]
            + (point[1] - start[1]) * edge[1]
        ) / length_squared
        segment_t = max(0.0, min(1.0, raw_t))
        projected = (
            start[0] + segment_t * edge[0],
            start[1] + segment_t * edge[1],
        )
        distance_squared = (
            (point[0] - projected[0]) ** 2
            + (point[1] - projected[1]) ** 2
        )
        record = {
            "edge_index": edge_index,
            "raw_segment_parameter": raw_t,
            "segment_parameter": segment_t,
            "point_uv_mm": projected,
            "distance_mm": math.sqrt(distance_squared),
            "distance_squared_mm2": distance_squared,
        }
        if best is None or (distance_squared, edge_index) < (
            float(best["distance_squared_mm2"]),
            int(best["edge_index"]),
        ):
            best = record
    if best is None:
        raise RuntimeError("rear inner perimeter projection produced no edge")
    return best


def projection_lands_strictly_inside_segment(
    projection: dict[str, Any], interior_epsilon: float
) -> bool:
    raw_t = float(projection["raw_segment_parameter"])
    segment_t = float(projection["segment_parameter"])
    return (
        float(interior_epsilon) < raw_t < 1.0 - float(interior_epsilon)
        and abs(raw_t - segment_t) <= 1.0e-15
    )


def unsupported_span_is_within_limit(
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


def preflight_rear_cap_edge_projection(parameters: dict[str, Any]) -> dict[str, Any]:
    """Fail before FreeCAD import if the signed V5 root decision is inconsistent."""
    rear = parameters["geometry"]["rear_cap_connector"]
    exact_values = {
        "projection_algorithm": EDGE_PROJECTION_ALGORITHM,
        "outer_diameter_mm": 6.0,
        "local_root_width_mm": 6.0,
        "root_axial_depth_mm": 4.0,
        "engagement_depth_mm": 4.0,
        "wall_overlap_mm": 1.0,
        "maximum_local_root_span_mm": 2.3,
        "boss_axis": "aperture_lcs.inward_n",
    }
    for name, expected in exact_values.items():
        if rear.get(name) != expected:
            raise RuntimeError(
                json.dumps(
                    {
                        "error": "V5 rear-cap root contract mismatch",
                        "field": name,
                        "expected": expected,
                        "actual": rear.get(name),
                        "output_created": False,
                        "geometry_construction_started": False,
                    },
                    sort_keys=True,
                )
            )
    if rear.get("boss_centers_mm") != {
        role: list(values) for role, values in V9_BOSS_CENTERS_MM.items()
    }:
        raise RuntimeError("exact V9 rear-cap boss centers changed")

    polygon_uv = _rear_inner_polygon_uv(parameters)
    lcs = parameters["aperture_lcs"]
    origin = tuple(float(value) for value in lcs["origin_mm"])
    axis_u = _normalize3(lcs["u"], "LCS u")
    axis_v = _normalize3(lcs["v"], "LCS v")
    expected_records = rear["edge_projection_preflight"]
    tolerance = float(expected_records["numeric_tolerance_mm"])
    interior_epsilon = float(expected_records["segment_interior_epsilon"])
    boss_radius = float(rear["outer_diameter_mm"]) / 2.0
    roots: dict[str, Any] = {}
    for role, center_values in rear["boss_centers_mm"].items():
        delta = _subtract3(center_values, origin)
        center_uv = (_dot3(delta, axis_u), _dot3(delta, axis_v))
        projection = nearest_point_on_polygon_edge_uv(center_uv, polygon_uv)
        center_to_edge = float(projection["distance_mm"])
        unsupported = max(0.0, center_to_edge - boss_radius)
        raw_t = float(projection["raw_segment_parameter"])
        segment_t = float(projection["segment_parameter"])
        inside_segment = projection_lands_strictly_inside_segment(
            projection, interior_epsilon
        )
        expected = expected_records[role]
        failures = []
        if abs(center_to_edge - float(expected["center_to_edge_mm"])) > tolerance:
            failures.append("center_to_edge_mm")
        if abs(unsupported - float(expected["unsupported_span_mm"])) > tolerance:
            failures.append("unsupported_span_mm")
        if int(projection["edge_index"]) != int(expected["edge_index"]):
            failures.append("edge_index")
        if not inside_segment:
            failures.append("projection_not_inside_segment")
        if not unsupported_span_is_within_limit(
            center_to_edge,
            boss_radius,
            float(rear["maximum_local_root_span_mm"]),
            tolerance,
        ):
            failures.append("unsupported_span_exceeds_limit")
        record = {
            **projection,
            "center_uv_mm": center_uv,
            "center_to_edge_mm": center_to_edge,
            "boss_radius_mm": boss_radius,
            "unsupported_span_mm": unsupported,
            "maximum_unsupported_span_mm": float(
                rear["maximum_local_root_span_mm"]
            ),
            "projection_inside_segment": inside_segment,
            "failures": failures,
        }
        roots[role] = record
        if failures:
            raise RuntimeError(
                json.dumps(
                    {
                        "error": "V6 rear-cap edge-projection preflight failed",
                        "role": role,
                        "measurements": record,
                        "output_created": False,
                        "geometry_construction_started": False,
                    },
                    sort_keys=True,
                )
            )
    return {
        "status": "PASS__EDGE_PROJECTIONS_INTERIOR_AND_WITHIN_2_30_MM",
        "algorithm": EDGE_PROJECTION_ALGORITHM,
        "roots": roots,
    }


def preflight_signed_mount_frames(parameters: dict[str, Any]) -> dict[str, Any]:
    """Construct the authoritative frames without FreeCAD or shell-edge axes."""
    lcs = parameters["aperture_lcs"]
    aperture_normal = _normalize3(lcs["inward_n"], "aperture normal")
    settings = parameters["geometry"]["head_mount"]
    limits = parameters["validation_contract"]["limits"]
    minimum_axis_dot = float(limits["minimum_signed_mount_axis_dot"])
    orthogonality_limit = float(limits["maximum_frame_orthogonality_error"])
    alignment_limit = float(limits["maximum_bore_center_axis_offset_mm"])
    dimensional_limit = float(limits["maximum_dimensional_deviation_mm"])
    face_offset = float(settings["bore_center_to_mating_face_mm"])
    expected_gap = float(settings["mating_gap_mm"])
    frames: dict[str, Any] = {}

    for role, datum in parameters["mount_datums"].items():
        signed = tuple(float(value) for value in datum["bore_axis"])
        bore_axis_vector = _normalize3(signed, f"{role} signed bore axis")
        depth_raw = _subtract3(
            aperture_normal,
            _scale3(
                bore_axis_vector,
                _dot3(aperture_normal, bore_axis_vector),
            ),
        )
        depth = _normalize3(depth_raw, f"{role} projected aperture depth")
        tangent = _normalize3(
            _cross3(depth, bore_axis_vector), f"{role} tangent"
        )
        reconstructed_bore = _normalize3(
            _cross3(tangent, depth), f"{role} reconstructed bore"
        )

        signed_axis_dot = _dot3(
            bore_axis_vector,
            _normalize3(signed, f"{role} signed axis"),
        )
        signed_axis_error = _length3(
            _subtract3(
                bore_axis_vector,
                _normalize3(signed, f"{role} signed axis"),
            )
        )
        orthogonality_error = max(
            abs(_dot3(bore_axis_vector, depth)),
            abs(_dot3(bore_axis_vector, tangent)),
            abs(_dot3(depth, tangent)),
        )
        unit_length_error = max(
            abs(_length3(bore_axis_vector) - 1.0),
            abs(_length3(depth) - 1.0),
            abs(_length3(tangent) - 1.0),
        )
        right_handed_dot = _dot3(reconstructed_bore, bore_axis_vector)

        eye = tuple(float(value) for value in datum["eye_bore_center_mm"])
        head = tuple(float(value) for value in datum["head_bore_center_mm"])
        center_delta = _subtract3(eye, head)
        axial_separation = _dot3(center_delta, bore_axis_vector)
        center_axis_offset = _length3(
            _subtract3(
                center_delta,
                _scale3(bore_axis_vector, axial_separation),
            )
        )
        mating_gap = axial_separation - 2.0 * face_offset
        mating_gap_error = abs(mating_gap - expected_gap)
        passes = (
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
            "axial_center_separation_mm": axial_separation,
            "center_axis_offset_mm": center_axis_offset,
            "mating_gap_mm": mating_gap,
            "mating_gap_error_mm": mating_gap_error,
            "passed": passes,
        }
        if not passes:
            raise RuntimeError(
                json.dumps(
                    {
                        "error": "V6 signed-axis mount-frame preflight failed",
                        "role": role,
                        "measurements": frames[role],
                        "output_created": False,
                        "geometry_construction_started": False,
                    },
                    sort_keys=True,
                )
            )
    return {
        "status": "PASS__SIGNED_AXES_EXACT__ORTHONORMAL_RIGHT_HANDED",
        "algorithm": "signed-bore-axis-aperture-normal-gram-schmidt-v1",
        "minimum_signed_axis_dot": minimum_axis_dot,
        "frames": frames,
        "shell_edge_used_to_define_axis": False,
    }


def import_pinned_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load pinned module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_pinned_file(root: Path, spec: dict[str, Any], label: str) -> Path:
    path = root / str(spec["path"])
    actual = sha256_file(path) if path.is_file() else None
    if actual != spec["sha256"]:
        raise RuntimeError(
            json.dumps(
                {
                    "error": "pinned dependency mismatch",
                    "dependency": label,
                    "path": str(spec["path"]),
                    "actual_sha256": actual,
                    "expected_sha256": spec["sha256"],
                    "output_created": False,
                    "geometry_construction_started": False,
                },
                sort_keys=True,
            )
        )
    return path


def pure_frame_preflight(
    baseline_argument: Path, contract_argument: Path
) -> dict[str, Any]:
    """Run every standard-library control before importing FreeCAD."""
    root = repository_root(contract_argument)
    baseline = load_json(baseline_argument)
    contract = load_json(contract_argument)
    parameters = contract["allowed_mutations"][0]["parameters"]
    root_projection = preflight_rear_cap_edge_projection(parameters)
    frames = preflight_signed_mount_frames(parameters)
    registry_spec = parameters["design_control"]["rejected_signature_registry"]
    registry_path = verify_pinned_file(
        root, registry_spec, "rejected-design-signature registry"
    )
    registry = load_json(registry_path)
    design = design_control.preflight_design_control(
        contract, registry, require_approval=True
    )
    baseline_path = root / baseline["assembly"]["path"]
    if baseline["assembly"]["sha256"] != (
        "9cf0b72f711c8f0eb15d8825e430e9bf6ec0dc9611ac7c297b90fafa9b554584"
    ):
        raise RuntimeError("pure V6 preflight is not pinned to canonical V34")
    if sha256_file(baseline_path) != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 hash mismatch")
    output_dir = root / contract["output"]["directory"]
    candidate_path = root / contract["output"]["candidate_fcstd"]
    if output_dir.exists() or candidate_path.exists():
        raise RuntimeError("V6 pure preflight requires a new output target")
    return {
        "status": "PASS__PURE_FRAME_PREFLIGHT__NO_FREECAD_NO_OUTPUT",
        "iteration_id": ITERATION_ID,
        "design_signature_sha256": design["design_signature_sha256"],
        "rear_cap_edge_projection": root_projection,
        "mount_frames": frames,
        "baseline_sha256": baseline["assembly"]["sha256"],
        "output_exists": False,
        "candidate_exists": False,
        "freecad_imported": False,
        "geometry_construction_started": False,
        "quarantined_v4_or_v5_geometry_source_used": False,
    }


def immutable_preflight(
    baseline_argument: Path,
    contract_argument: Path,
    *,
    require_new_output: bool = True,
) -> dict[str, Any]:
    root = repository_root(contract_argument)
    baseline = load_json(baseline_argument)
    contract = load_json(contract_argument)
    mutations = contract.get("allowed_mutations", [])
    if len(mutations) != 1 or not isinstance(mutations[0].get("parameters"), dict):
        raise RuntimeError("V6 requires one machine-readable mutation")
    parameters = mutations[0]["parameters"]
    root_projection_report = preflight_rear_cap_edge_projection(parameters)
    frame_preflight_report = preflight_signed_mount_frames(parameters)
    control = parameters["design_control"]
    registry_path = verify_pinned_file(
        root,
        control["rejected_signature_registry"],
        "rejected-design-signature registry",
    )
    registry = load_json(registry_path)
    design_report = design_control.preflight_design_control(
        contract,
        registry,
        require_approval=True,
    )

    tooling = parameters["tooling_dependencies"]
    shared_validator_path = verify_pinned_file(
        root, tooling["shared_validator"], "shared V2 validator"
    )
    shared_validator = import_pinned_module(
        shared_validator_path, "cat_head_shared_v2_validator_for_eye_v6"
    )
    shared_report = shared_validator.validate_files(
        baseline_argument,
        contract_argument,
        verify_files=True,
        require_new_output=require_new_output,
    )
    if shared_report.get("status") != "PASS":
        raise RuntimeError(
            json.dumps(
                {
                    "error": "shared V2 preflight failed",
                    "shared_report": shared_report,
                    "output_created": False,
                    "geometry_construction_started": False,
                },
                sort_keys=True,
            )
        )
    for key in (
        "shared_runner",
        "shared_preservation_module",
        "shared_preservation_comparator",
        "independent_previsual_validator",
    ):
        verify_pinned_file(root, tooling[key], key)

    for group_name in ("fit_references", "lineage_references"):
        for name, spec in parameters[group_name].items():
            verify_pinned_file(root, spec, f"{group_name}/{name}")
    validation = parameters["validation_contract"]
    for name in ("upper_component_manifest", "lower_component_manifest", "lower_c001"):
        verify_pinned_file(
            root,
            validation["shell_matrix_sources"][name],
            f"shell matrix/{name}",
        )

    baseline_path = root / baseline["assembly"]["path"]
    if baseline.get("assembly", {}).get("sha256") != (
        "9cf0b72f711c8f0eb15d8825e430e9bf6ec0dc9611ac7c297b90fafa9b554584"
    ):
        raise RuntimeError("contract is not pinned to canonical V34")
    if sha256_file(baseline_path) != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 hash mismatch")
    if contract.get("baseline_id") != baseline.get("baseline_id"):
        raise RuntimeError("baseline ID mismatch")
    output_dir = root / contract["output"]["directory"]
    candidate_path = root / contract["output"]["candidate_fcstd"]
    if require_new_output and (output_dir.exists() or candidate_path.exists()):
        raise RuntimeError(f"iteration output already exists: {output_dir}")

    # FreeCAD imports happen only after every standard-library signature,
    # lineage, approval, and file-pin check has passed.
    import FreeCAD as App  # type: ignore
    import Mesh  # type: ignore
    import Part  # type: ignore

    runtime_manifest_path = root / contract["runtime"]["manifest_path"]
    runtime_manifest = load_json(runtime_manifest_path)
    probe_path = verify_pinned_file(
        root,
        {
            "path": runtime_manifest["probe"]["script_path"],
            "sha256": runtime_manifest["probe"]["script_sha256"],
        },
        "approved runtime probe",
    )
    probe = import_pinned_module(probe_path, "cat_head_runtime_probe_for_eye_v6")
    observed_runtime = probe.runtime_record()
    expected_runtime = {
        "freecad_version": runtime_manifest["freecad"]["version_record"],
        "freecad_program_version": runtime_manifest["freecad"]["program_version"],
        "occt_version": runtime_manifest["occt"]["version"],
        "python_version": runtime_manifest["python"]["version"],
        "platform_machine": runtime_manifest["platform"]["machine"],
    }
    if observed_runtime != expected_runtime:
        raise RuntimeError(
            json.dumps(
                {
                    "error": "approved runtime mismatch",
                    "expected_runtime": expected_runtime,
                    "observed_runtime": observed_runtime,
                    "output_created": False,
                    "geometry_construction_started": False,
                },
                sort_keys=True,
            )
        )

    document = App.openDocument(str(baseline_path))
    try:
        target = document.getObject(TARGET_OBJECT)
        if target is None or target.TypeId != "Part::Feature" or target.Shape.isNull():
            raise RuntimeError("canonical V34 target is missing, null, or wrong type")
        original = {
            "name": target.Name,
            "label": target.Label,
            "type_id": target.TypeId,
            "placement": App.Placement(target.Placement),
        }
    except Exception:
        App.closeDocument(document.Name)
        raise
    return {
        "root": root,
        "baseline": baseline,
        "contract": contract,
        "parameters": parameters,
        "root_projection_report": root_projection_report,
        "frame_preflight_report": frame_preflight_report,
        "design_report": design_report,
        "shared_report": shared_report,
        "runtime": observed_runtime,
        "baseline_path": baseline_path,
        "output_dir": output_dir,
        "candidate_path": candidate_path,
        "document": document,
        "target": target,
        "original": original,
        "App": App,
        "Mesh": Mesh,
        "Part": Part,
        "geometry_construction_started": False,
        "requires_new_output": require_new_output,
        "io_trace": {
            "save_as_called": False,
            "document_save_called": False,
            "geometry_export_created": False,
            "candidate_created": False,
        },
        "finalization_trace": {
            "target_assignment_performed": False,
            "metadata_assignment_performed": False,
            "recompute_performed": False,
            "final_assertions_performed": False,
        },
    }


def vector(App: Any, values: Sequence[float]) -> Any:
    return App.Vector(float(values[0]), float(values[1]), float(values[2]))


def normalized(App: Any, value: Any, label: str) -> Any:
    result = App.Vector(value)
    if result.Length <= 1.0e-9:
        raise RuntimeError(f"{label} has zero length")
    result.normalize()
    return result


def average(App: Any, points: Sequence[Any]) -> Any:
    result = App.Vector()
    for point in points:
        result += point
    return result / float(len(points))


def local_coordinates(point: Any, origin: Any, axis_u: Any, axis_v: Any, axis_n: Any) -> tuple[float, float, float]:
    delta = point - origin
    return delta.dot(axis_u), delta.dot(axis_v), delta.dot(axis_n)


def point_from_local(u_value: float, v_value: float, depth: float, origin: Any, axis_u: Any, axis_v: Any, axis_n: Any) -> Any:
    return origin + axis_u * u_value + axis_v * v_value + axis_n * depth


def planar_loop(points: Sequence[Any], origin: Any, axis_u: Any, axis_v: Any, axis_n: Any) -> list[Any]:
    output = []
    for point in points:
        local_u, local_v, _ = local_coordinates(
            point, origin, axis_u, axis_v, axis_n
        )
        output.append(
            point_from_local(local_u, local_v, 0.0, origin, axis_u, axis_v, axis_n)
        )
    return output


def radial_offset_loop(App: Any, loop: Sequence[Any], offset: float, axis_n: Any) -> list[Any]:
    center = average(App, loop)
    output = []
    for point in loop:
        radial = point - center
        radial -= axis_n * radial.dot(axis_n)
        radial = normalized(App, radial, "loop radial")
        output.append(point + radial * float(offset))
    return output


def at_depth(loop: Sequence[Any], depth: float, axis_n: Any) -> list[Any]:
    return [point + axis_n * float(depth) for point in loop]


def polygon_face(Part: Any, loop: Sequence[Any]) -> Any:
    return Part.Face(Part.makePolygon([*loop, loop[0]]))


def ring_prism(Part: Any, outer: Sequence[Any], inner: Sequence[Any], start: float, end: float, axis_n: Any, label: str) -> Any:
    if end <= start:
        raise RuntimeError(f"{label}: non-positive depth")
    ring = polygon_face(Part, at_depth(outer, start, axis_n)).cut(
        polygon_face(Part, at_depth(inner, start, axis_n))
    )
    shape = ring.extrude(axis_n * (end - start)).removeSplitter()
    require_single_solid(shape, label)
    return shape


def loft_ring(Part: Any, outer_start: Sequence[Any], inner_start: Sequence[Any], outer_end: Sequence[Any], inner_end: Sequence[Any], start: float, end: float, axis_n: Any, label: str) -> Any:
    outer_start_depth = at_depth(outer_start, start, axis_n)
    outer_end_depth = at_depth(outer_end, end, axis_n)
    inner_start_depth = at_depth(inner_start, start - 0.01, axis_n)
    inner_end_depth = at_depth(inner_end, end + 0.01, axis_n)
    outer = Part.makeLoft(
        [
            Part.makePolygon([*outer_start_depth, outer_start_depth[0]]),
            Part.makePolygon([*outer_end_depth, outer_end_depth[0]]),
        ],
        True,
        False,
    )
    inner = Part.makeLoft(
        [
            Part.makePolygon([*inner_start_depth, inner_start_depth[0]]),
            Part.makePolygon([*inner_end_depth, inner_end_depth[0]]),
        ],
        True,
        False,
    )
    shape = outer.cut(inner).removeSplitter()
    require_single_solid(shape, label)
    return shape


def fuse_shapes(shapes: Sequence[Any], label: str, require_one: bool = True) -> Any:
    if not shapes:
        raise RuntimeError(f"{label}: no shapes")
    result = shapes[0].multiFuse(list(shapes[1:])).removeSplitter()
    if result.isNull():
        raise RuntimeError(f"{label}: null Boolean union")
    if require_one:
        require_single_solid(result, label)
    return result


def oriented_box(Part: Any, center: Any, axes: Sequence[Any], dimensions: Sequence[float]) -> Any:
    half = [float(value) / 2.0 for value in dimensions]
    base = center - axes[0] * half[0] - axes[1] * half[1] - axes[2] * half[2]
    loop = [
        base,
        base + axes[0] * dimensions[0],
        base + axes[0] * dimensions[0] + axes[1] * dimensions[1],
        base + axes[1] * dimensions[1],
    ]
    return polygon_face(Part, loop).extrude(axes[2] * dimensions[2]).removeSplitter()


def translated(shape: Any, delta: Any) -> Any:
    result = shape.copy()
    result.translate(delta)
    return result


def require_single_solid(shape: Any, label: str) -> None:
    if shape.isNull() or not shape.isValid() or not shape.isClosed():
        raise RuntimeError(f"{label}: shape is null, invalid, or open")
    if len(shape.Solids) != 1:
        raise RuntimeError(f"{label}: expected one solid, found {len(shape.Solids)}")


def reconstruct_mount_frames(parameters: dict[str, Any], App: Any) -> dict[str, dict[str, Any]]:
    lcs = parameters["aperture_lcs"]
    origin = vector(App, lcs["origin_mm"])
    axis_u = normalized(App, vector(App, lcs["u"]), "LCS u")
    axis_v = normalized(App, vector(App, lcs["v"]), "LCS v")
    axis_n = normalized(App, vector(App, lcs["inward_n"]), "LCS inward n")
    pure_frames = preflight_signed_mount_frames(parameters)
    minimum_axis_dot = float(
        parameters["validation_contract"]["limits"]["minimum_signed_mount_axis_dot"]
    )
    frames: dict[str, dict[str, Any]] = {}
    for role, datum in parameters["mount_datums"].items():
        record = pure_frames["frames"][role]
        bore_axis_vector = normalized(
            App, vector(App, datum["bore_axis"]), f"{role} approved axis"
        )
        depth = normalized(
            App, vector(App, record["depth"]), f"{role} V6 depth"
        )
        tangent = normalized(
            App, vector(App, record["tangent"]), f"{role} V6 tangent"
        )
        if bore_axis_vector.dot(
            normalized(App, vector(App, datum["bore_axis"]), f"{role} signed axis")
        ) < minimum_axis_dot:
            raise RuntimeError(
                f"BLOCKED__MOUNT_DATUM_CONFLICT: {role} signed bore axis changed"
            )
        if tangent.cross(depth).dot(bore_axis_vector) < minimum_axis_dot:
            raise RuntimeError(f"{role} V6 mount frame is not right-handed")
        frames[role] = {
            "origin": origin,
            "axis_u": axis_u,
            "axis_v": axis_v,
            "axis_n": axis_n,
            "tangent": tangent,
            "depth": depth,
            "bore_axis_vector": bore_axis_vector,
            "eye_bore": vector(App, datum["eye_bore_center_mm"]),
            "head_bore": vector(App, datum["head_bore_center_mm"]),
            "root_extension": vector(
                App, datum["owner_root_extension_vector_mm"]
            ),
        }
    return frames


def construct_serviceable_eye(parameters: dict[str, Any], App: Any, Part: Any) -> tuple[Any, dict[str, Any]]:
    lcs = parameters["aperture_lcs"]
    geometry = parameters["geometry"]
    origin = vector(App, lcs["origin_mm"])
    axis_u = normalized(App, vector(App, lcs["u"]), "LCS u")
    axis_v = normalized(App, vector(App, lcs["v"]), "LCS v")
    axis_n = normalized(App, vector(App, lcs["inward_n"]), "LCS inward n")
    if max(abs(axis_u.dot(axis_v)), abs(axis_u.dot(axis_n)), abs(axis_v.dot(axis_n))) > 1.0e-6:
        raise RuntimeError("protected module LCS is not orthogonal")
    aperture_exact = [vector(App, point) for point in lcs["visible_aperture_mm"]]
    aperture = planar_loop(aperture_exact, origin, axis_u, axis_v, axis_n)
    max_plane_error = max(
        abs(local_coordinates(point, origin, axis_u, axis_v, axis_n)[2])
        for point in aperture_exact
    )
    if max_plane_error > float(lcs["aperture_rounding_tolerance_mm"]):
        raise RuntimeError("protected visible aperture exceeds rounding tolerance")
    opening = planar_loop(
        [vector(App, point) for point in geometry["shell_opening_boundary_mm"]],
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    bezel_values = geometry["bezel"]
    diffuser = geometry["diffuser_interface"]
    chamber_values = geometry["chamber"]
    outer_fit = radial_offset_loop(
        App, opening, -float(bezel_values["shell_opening_clearance_mm"]), axis_n
    )
    diffuser_loop = radial_offset_loop(
        App, aperture, float(diffuser["overlap_mm"]), axis_n
    )
    pocket_loop = radial_offset_loop(
        App, diffuser_loop, float(diffuser["pocket_clearance_mm"]), axis_n
    )
    front_outer = radial_offset_loop(
        App, pocket_loop, float(chamber_values["wall_thickness_mm"]), axis_n
    )
    rear_inner = radial_offset_loop(
        App, aperture, float(chamber_values["rear_inner_offset_mm"]), axis_n
    )
    rear_outer = radial_offset_loop(
        App, rear_inner, float(chamber_values["wall_thickness_mm"]), axis_n
    )
    collar_outer = radial_offset_loop(
        App, aperture, float(bezel_values["collar_outer_offset_mm"]), axis_n
    )
    collar_inner = radial_offset_loop(
        App, aperture, float(bezel_values["collar_inner_offset_mm"]), axis_n
    )
    front_bezel = ring_prism(
        Part,
        outer_fit,
        aperture,
        float(bezel_values["front_depth_mm"]),
        float(bezel_values["front_depth_mm"]) + float(bezel_values["thickness_mm"]),
        axis_n,
        "approved visible bezel",
    )
    collar = ring_prism(
        Part,
        collar_outer,
        collar_inner,
        float(bezel_values["collar_start_depth_mm"]),
        float(bezel_values["collar_end_depth_mm"]),
        axis_n,
        "continuous bezel collar",
    )
    bezel = fuse_shapes([front_bezel, collar], "continuous bezel")
    front_wall = ring_prism(
        Part,
        front_outer,
        pocket_loop,
        float(chamber_values["front_start_depth_mm"]),
        float(chamber_values["taper_start_depth_mm"]) + 0.3,
        axis_n,
        "front chamber perimeter",
    )
    taper = loft_ring(
        Part,
        front_outer,
        pocket_loop,
        rear_outer,
        rear_inner,
        float(chamber_values["taper_start_depth_mm"]),
        float(chamber_values["taper_end_depth_mm"]),
        axis_n,
        "local chamber taper",
    )
    rear_wall = ring_prism(
        Part,
        rear_outer,
        rear_inner,
        float(chamber_values["taper_end_depth_mm"]) - 0.3,
        float(chamber_values["depth_mm"]),
        axis_n,
        "rear chamber perimeter",
    )
    diffuser_seat = ring_prism(
        Part,
        front_outer,
        rear_inner,
        float(diffuser["seat_start_depth_mm"]),
        float(diffuser["seat_end_depth_mm"]),
        axis_n,
        "continuous diffuser shoulder",
    )
    chamber = fuse_shapes(
        [front_wall, taper, rear_wall, diffuser_seat],
        "continuous chamber and diffuser shoulder",
    )

    rear = geometry["rear_cap_connector"]
    rear_seat = ring_prism(
        Part,
        rear_outer,
        rear_inner,
        float(rear["seat_front_depth_mm"]),
        float(chamber_values["depth_mm"]),
        axis_n,
        "rear-cap perimeter seat",
    )
    cap_shapes = [rear_seat]
    cap_bores = []
    cap_root_records: dict[str, Any] = {}
    rear_inner_uv = [
        local_coordinates(point, origin, axis_u, axis_v, axis_n)[:2]
        for point in rear_inner
    ]
    for role, center_values in rear["boss_centers_mm"].items():
        center = vector(App, center_values)
        center_u, center_v, _ = local_coordinates(
            center, origin, axis_u, axis_v, axis_n
        )
        boss_start = float(chamber_values["depth_mm"]) - float(
            rear["engagement_depth_mm"]
        )
        root_start = float(chamber_values["depth_mm"]) - float(
            rear["root_axial_depth_mm"]
        )
        base = point_from_local(
            center_u, center_v, boss_start, origin, axis_u, axis_v, axis_n
        )
        boss = Part.makeCylinder(
            float(rear["outer_diameter_mm"]) / 2.0,
            float(rear["engagement_depth_mm"]),
            base,
            axis_n,
        )
        projection = nearest_point_on_polygon_edge_uv(
            (center_u, center_v), rear_inner_uv
        )
        nearest = projection["point_uv_mm"]
        dx, dy = nearest[0] - center_u, nearest[1] - center_v
        center_to_edge = math.hypot(dx, dy)
        boss_radius = float(rear["outer_diameter_mm"]) / 2.0
        unsupported_span = max(0.0, center_to_edge - boss_radius)
        interior_epsilon = float(
            rear["edge_projection_preflight"]["segment_interior_epsilon"]
        )
        if not projection_lands_strictly_inside_segment(
            projection, interior_epsilon
        ):
            raise RuntimeError(
                f"{role} rear-cap projection landed at a prohibited vertex"
            )
        if not unsupported_span_is_within_limit(
            center_to_edge,
            boss_radius,
            float(rear["maximum_local_root_span_mm"]),
        ):
            raise RuntimeError(
                json.dumps(
                    {
                        "error": "rear-cap unsupported root span exceeds limit",
                        "role": role,
                        "center_to_edge_mm": center_to_edge,
                        "boss_radius_mm": boss_radius,
                        "unsupported_span_mm": unsupported_span,
                        "maximum_unsupported_span_mm": float(
                            rear["maximum_local_root_span_mm"]
                        ),
                    },
                    sort_keys=True,
                )
            )
        if center_to_edge > 1.0e-9:
            along_u, along_v = dx / center_to_edge, dy / center_to_edge
            across_u, across_v = -along_v, along_u
            half_width = float(rear["local_root_width_mm"]) / 2.0
            wall_overlap = float(rear["wall_overlap_mm"])
            root_end = (
                nearest[0] + along_u * wall_overlap,
                nearest[1] + along_v * wall_overlap,
            )
            root_uv = [
                (center_u - across_u * half_width, center_v - across_v * half_width),
                (root_end[0] - across_u * half_width, root_end[1] - across_v * half_width),
                (root_end[0] + across_u * half_width, root_end[1] + across_v * half_width),
                (center_u + across_u * half_width, center_v + across_v * half_width),
            ]
            root_loop = [
                point_from_local(u, v, root_start, origin, axis_u, axis_v, axis_n)
                for u, v in root_uv
            ]
            cap_shapes.append(
                polygon_face(Part, root_loop).extrude(
                    axis_n * float(rear["root_axial_depth_mm"])
                )
            )
        cap_root_records[role] = {
            "edge_index": int(projection["edge_index"]),
            "segment_parameter": float(projection["segment_parameter"]),
            "projection_uv_mm": nearest,
            "center_to_edge_mm": center_to_edge,
            "boss_radius_mm": boss_radius,
            "unsupported_span_mm": unsupported_span,
            "root_width_mm": float(rear["local_root_width_mm"]),
            "root_axial_depth_mm": float(rear["root_axial_depth_mm"]),
            "wall_overlap_mm": float(rear["wall_overlap_mm"]),
        }
        cap_shapes.append(boss)
        cap_bores.append(
            Part.makeCylinder(
                float(rear["bore_diameter_mm"]) / 2.0,
                float(rear["engagement_depth_mm"]) + 2.0,
                base - axis_n,
                axis_n,
            )
        )
    cap_feature = fuse_shapes(
        cap_shapes, "separate upper and lower rear-cap retention"
    ).cut(Part.makeCompound(cap_bores)).removeSplitter()
    require_single_solid(cap_feature, "drilled rear-cap retention")

    mount_values = geometry["head_mount"]
    frames = reconstruct_mount_frames(parameters, App)
    mount_records: dict[str, Any] = {}
    mount_shapes = []
    mount_bores = []
    length = float(mount_values["leaf_length_mm"])
    depth = float(mount_values["leaf_depth_mm"])
    thickness = float(mount_values["leaf_thickness_mm"])
    legacy_thickness = float(mount_values["legacy_leaf_thickness_mm"])
    bore_radius = float(mount_values["bore_diameter_mm"]) / 2.0
    collar_radius = float(
        mount_values["edge_ligament_collar_outer_diameter_mm"]
    ) / 2.0
    for role, frame in frames.items():
        eye_center = frame["eye_bore"] - frame["depth"] * (
            float(mount_values["bore_depth_from_aperture_plane_mm"]) - depth / 2.0
        )
        thick_center = eye_center + frame["bore_axis_vector"] * (
            (thickness - legacy_thickness) / 2.0
        )
        leaf = oriented_box(
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
            mount_values["bore_center_to_mating_face_mm"]
        )
        collar = Part.makeCylinder(
            collar_radius,
            thickness,
            collar_base,
            frame["bore_axis_vector"],
        )
        compact_leaf = fuse_shapes(
            [leaf, collar], f"{role} compact leaf and local edge collar"
        )
        local_root = fuse_shapes(
            [compact_leaf, translated(compact_leaf, frame["root_extension"])],
            f"{role} 1.50 mm local owner-root extension",
        )
        cutter_length = float(mount_values["bore_cutter_length_mm"])
        bore_cutter_solid = Part.makeCylinder(
            bore_radius,
            cutter_length,
            frame["eye_bore"]
            - frame["bore_axis_vector"] * (cutter_length / 2.0),
            frame["bore_axis_vector"],
        )
        drilled = local_root.cut(bore_cutter_solid).removeSplitter()
        require_single_solid(drilled, f"{role} drilled compact mount")
        mount_shapes.append(drilled)
        mount_bores.append(bore_cutter_solid)
        mount_records[role] = {
            **frame,
            "uncut": local_root,
            "drilled": drilled,
            "bore_cutter_solid": bore_cutter_solid,
        }

    # No centroid-directed web, landing inset, 14 mm root plate, bridge, wedge,
    # trapezoid, or aperture-crossing support exists in this construction.
    final = fuse_shapes(
        [bezel, chamber, cap_feature, *mount_shapes],
        "one connected serviceable eye bucket",
    )
    final = final.cut(Part.makeCompound(mount_bores)).removeSplitter()
    require_single_solid(final, "final V6 serviceable eye")
    construction = {
        "origin": origin,
        "axis_u": axis_u,
        "axis_v": axis_v,
        "axis_n": axis_n,
        "aperture_exact": aperture_exact,
        "aperture_planar": aperture,
        "bezel": bezel,
        "chamber": chamber,
        "cap_feature": cap_feature,
        "cap_roots": cap_root_records,
        "mounts": mount_records,
        "aperture_plane_error_mm": max_plane_error,
    }
    return final, construction


def is_vector_metadata_value(value: Any) -> bool:
    return (
        all(hasattr(value, component) for component in ("x", "y", "z", "Length"))
        and callable(getattr(value, "dot", None))
        and callable(getattr(value, "cross", None))
        and not hasattr(value, "ShapeType")
    )


def assert_metadata_value_type(
    property_type: str,
    name: str,
    value: Any,
) -> None:
    if property_type == "App::PropertyString":
        valid = isinstance(value, str)
    elif property_type == "App::PropertyVector":
        valid = is_vector_metadata_value(value)
    elif property_type == "App::PropertyVectorList":
        valid = (
            isinstance(value, (list, tuple))
            and all(is_vector_metadata_value(item) for item in value)
        )
    elif property_type in {"App::PropertyLength", "App::PropertyFloat"}:
        valid = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(float(value))
        )
    else:
        raise TypeError(f"unsupported metadata property type: {property_type}")
    if not valid:
        raise TypeError(
            f"{name} requires {property_type}, received {type(value).__name__}"
        )


def assert_property_schema(
    target: Any,
    property_type: str,
    name: str,
    group: str,
) -> None:
    if name not in target.PropertiesList:
        raise RuntimeError(f"metadata property was not created: {name}")
    get_type = getattr(target, "getTypeIdOfProperty", None)
    if not callable(get_type):
        raise RuntimeError("target cannot report metadata property types")
    actual_type = get_type(name)
    if actual_type != property_type:
        raise TypeError(
            f"{name} schema mismatch: expected {property_type}, found {actual_type}"
        )
    get_group = getattr(target, "getGroupOfProperty", None)
    if callable(get_group):
        actual_group = get_group(name)
        if actual_group != group:
            raise TypeError(
                f"{name} group mismatch: expected {group}, found {actual_group}"
            )


def add_property(target: Any, property_type: str, name: str, group: str) -> None:
    if name not in target.PropertiesList:
        target.addProperty(property_type, name, group)
    assert_property_schema(target, property_type, name, group)


def assign_typed_metadata_property(
    target: Any,
    property_type: str,
    name: str,
    group: str,
    value: Any,
) -> dict[str, str]:
    add_property(target, property_type, name, group)
    assert_property_schema(target, property_type, name, group)
    assert_metadata_value_type(property_type, name, value)
    setattr(target, name, value)
    return {"name": name, "property_type": property_type, "group": group}


def attach_history(
    target: Any,
    parameters: dict[str, Any],
    construction: dict[str, Any],
) -> list[dict[str, str]]:
    assigned: list[dict[str, str]] = []
    for name, value in (
        ("ServiceableFitDesignId", DESIGN_ID),
        ("ServiceableFitToolingRevision", str(TOOLING_REVISION)),
        (
            "ServiceableFitDesignSignature",
            parameters["design_control"]["design_signature"]["sha256"],
        ),
        ("ServiceableFitIterationId", ITERATION_ID),
        (
            "ServiceableFitState",
            "DISPOSABLE__REQUIRES_PRESERVATION_AND_PREVISUAL_PASS",
        ),
    ):
        assigned.append(
            assign_typed_metadata_property(
                target,
                "App::PropertyString",
                name,
                "ServiceableFitC",
                value,
            )
        )
    for name, value in (
        ("ServiceableFitLCSOrigin", construction["origin"]),
        ("ServiceableFitLCSU", construction["axis_u"]),
        ("ServiceableFitLCSV", construction["axis_v"]),
        ("ServiceableFitLCSInwardN", construction["axis_n"]),
    ):
        assigned.append(
            assign_typed_metadata_property(
                target,
                "App::PropertyVector",
                name,
                "ServiceableFitDatums",
                value,
            )
        )
    assigned.append(
        assign_typed_metadata_property(
            target,
            "App::PropertyVectorList",
            "ServiceableFitVisibleAperture",
            "ServiceableFitDatums",
            construction["aperture_exact"],
        )
    )
    geometry = parameters["geometry"]
    dimension_values = (
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
    for name, value in dimension_values:
        assigned.append(
            assign_typed_metadata_property(
                target,
                "App::PropertyLength",
                name,
                "ServiceableFitDimensions",
                float(value),
            )
        )
    for role, record in construction["cap_roots"].items():
        title = role.capitalize()
        for suffix, value in (
            ("CenterToEdge", record["center_to_edge_mm"]),
            ("UnsupportedSpan", record["unsupported_span_mm"]),
            ("ProjectionSegmentParameter", record["segment_parameter"]),
        ):
            name = f"ServiceableFitCap{title}{suffix}"
            assigned.append(
                assign_typed_metadata_property(
                    target,
                    (
                        "App::PropertyLength"
                        if suffix != "ProjectionSegmentParameter"
                        else "App::PropertyFloat"
                    ),
                    name,
                    "ServiceableFitDimensions",
                    float(value),
                )
            )
    for role, datum in parameters["mount_datums"].items():
        title = role.capitalize()
        for suffix, values in (
            ("EyeBoreCenter", datum["eye_bore_center_mm"]),
            ("HeadBoreCenter", datum["head_bore_center_mm"]),
            ("BoreAxis", datum["bore_axis"]),
        ):
            name = f"ServiceableFit{title}{suffix}"
            assigned.append(
                assign_typed_metadata_property(
                    target,
                    "App::PropertyVector",
                    name,
                    "ServiceableFitDatums",
                    construction["origin"].__class__(
                        float(values[0]), float(values[1]), float(values[2])
                    ),
                )
            )
        frame = construction["mounts"][role]
        for suffix, value in (
            ("FrameBore", frame["bore_axis_vector"]),
            ("FrameDepth", frame["depth"]),
            ("FrameTangent", frame["tangent"]),
        ):
            name = f"ServiceableFit{title}{suffix}"
            assigned.append(
                assign_typed_metadata_property(
                    target,
                    "App::PropertyVector",
                    name,
                    "ServiceableFitDatums",
                    value,
                )
            )
    return assigned


def shape_check_records(shape: Any, label: str) -> list[str]:
    try:
        raw_check = shape.check(True)
    except Exception as exc:
        raise RuntimeError(
            f"{label}: OCCT shape check raised {type(exc).__name__}: {exc}"
        ) from exc
    records = [str(item) for item in (raw_check or [])]
    if records:
        raise RuntimeError(
            json.dumps(
                {
                    "error": f"{label}: OCCT shape check failed",
                    "records": records,
                },
                sort_keys=True,
            )
        )
    return records


def assert_product_defect_regressions(
    parameters: dict[str, Any],
    construction: dict[str, Any],
) -> dict[str, Any]:
    frame_preflight = preflight_signed_mount_frames(parameters)
    root_preflight = preflight_rear_cap_edge_projection(parameters)
    minimum_axis_dot = float(
        parameters["validation_contract"]["limits"][
            "minimum_signed_mount_axis_dot"
        ]
    )
    root_tolerance = float(
        parameters["geometry"]["rear_cap_connector"][
            "edge_projection_preflight"
        ]["numeric_tolerance_mm"]
    )
    mount_results: dict[str, Any] = {}
    for role, datum in parameters["mount_datums"].items():
        mount = construction["mounts"][role]
        if "bore" in mount:
            raise TypeError(f"{role} mount retains ambiguous semantic key 'bore'")
        bore_axis_vector = mount.get("bore_axis_vector")
        bore_cutter_solid = mount.get("bore_cutter_solid")
        if not is_vector_metadata_value(bore_axis_vector):
            raise TypeError(f"{role} bore_axis_vector is not a FreeCAD vector")
        if is_vector_metadata_value(bore_cutter_solid):
            raise TypeError(f"{role} bore_cutter_solid is incorrectly a vector")
        if (
            getattr(bore_cutter_solid, "ShapeType", None) != "Solid"
            or bore_cutter_solid.isNull()
            or not bore_cutter_solid.isValid()
            or not bore_cutter_solid.isClosed()
            or len(bore_cutter_solid.Solids) != 1
        ):
            raise TypeError(f"{role} bore_cutter_solid is not one valid closed solid")
        if bore_axis_vector is bore_cutter_solid:
            raise TypeError(f"{role} bore vector and cutter solid alias each other")
        signed_axis = bore_axis_vector.__class__(
            *[float(value) for value in datum["bore_axis"]]
        )
        signed_axis.normalize()
        signed_axis_dot = bore_axis_vector.dot(signed_axis)
        right_handed_dot = mount["tangent"].cross(mount["depth"]).dot(
            bore_axis_vector
        )
        if signed_axis_dot < minimum_axis_dot:
            raise RuntimeError(f"{role} finalized signed bore axis changed")
        if right_handed_dot < minimum_axis_dot:
            raise RuntimeError(f"{role} finalized frame is not right-handed")
        expected_frame = frame_preflight["frames"][role]
        expected_axis = bore_axis_vector.__class__(
            *[float(value) for value in expected_frame["bore_axis_vector"]]
        )
        if (bore_axis_vector - expected_axis).Length > 1.0e-12:
            raise RuntimeError(f"{role} finalized frame differs from pure preflight")
        mount_results[role] = {
            "signed_axis_dot": float(signed_axis_dot),
            "right_handed_dot": float(right_handed_dot),
            "bore_axis_vector_type": type(bore_axis_vector).__name__,
            "bore_cutter_solid_shape_type": bore_cutter_solid.ShapeType,
        }

    root_results: dict[str, Any] = {}
    for role, actual in construction["cap_roots"].items():
        expected = root_preflight["roots"][role]
        if int(actual["edge_index"]) != int(expected["edge_index"]):
            raise RuntimeError(f"{role} finalized cap-root edge changed")
        for key in (
            "center_to_edge_mm",
            "unsupported_span_mm",
            "segment_parameter",
        ):
            if abs(float(actual[key]) - float(expected[key])) > root_tolerance:
                raise RuntimeError(f"{role} finalized cap-root {key} changed")
        if float(actual["unsupported_span_mm"]) > float(
            parameters["geometry"]["rear_cap_connector"][
                "maximum_local_root_span_mm"
            ]
        ) + root_tolerance:
            raise RuntimeError(f"{role} finalized cap-root span exceeds contract")
        root_results[role] = {
            "edge_index": int(actual["edge_index"]),
            "segment_parameter": float(actual["segment_parameter"]),
            "unsupported_span_mm": float(actual["unsupported_span_mm"]),
        }

    return {
        "semantic_bore_key_collision_absent": True,
        "shell_edge_used_to_define_mount_axis": False,
        "signed_mount_frames": mount_results,
        "rear_cap_root_projections": root_results,
    }


def assert_assigned_shape_equivalent(
    assigned_shape: Any,
    constructed_shape: Any,
    maximum_residual_volume_mm3: float,
) -> dict[str, Any]:
    require_single_solid(assigned_shape, "assigned V6 target shape")
    require_single_solid(constructed_shape, "constructed V6 replacement shape")
    topology_names = ("Solids", "Shells", "Faces", "Edges", "Vertexes")
    assigned_topology = {
        name: len(getattr(assigned_shape, name)) for name in topology_names
    }
    constructed_topology = {
        name: len(getattr(constructed_shape, name)) for name in topology_names
    }
    if assigned_topology != constructed_topology:
        raise RuntimeError("assigned target Shape topology differs from construction")
    bound_names = ("XMin", "YMin", "ZMin", "XMax", "YMax", "ZMax")
    maximum_bound_error = max(
        abs(
            float(getattr(assigned_shape.BoundBox, name))
            - float(getattr(constructed_shape.BoundBox, name))
        )
        for name in bound_names
    )
    if maximum_bound_error > 1.0e-9:
        raise RuntimeError("assigned target Shape bounds differ from construction")
    volume_error = abs(float(assigned_shape.Volume) - float(constructed_shape.Volume))
    if volume_error > float(maximum_residual_volume_mm3):
        raise RuntimeError("assigned target Shape volume differs from construction")
    is_same = getattr(assigned_shape, "isSame", None)
    if callable(is_same) and is_same(constructed_shape):
        assigned_minus_constructed = 0.0
        constructed_minus_assigned = 0.0
        method = "occt_isSame"
    else:
        assigned_minus_constructed = float(
            assigned_shape.cut(constructed_shape).Volume
        )
        constructed_minus_assigned = float(
            constructed_shape.cut(assigned_shape).Volume
        )
        method = "occt_symmetric_difference"
    maximum_residual = max(
        assigned_minus_constructed,
        constructed_minus_assigned,
    )
    if maximum_residual > float(maximum_residual_volume_mm3):
        raise RuntimeError(
            "assigned target Shape has nonzero symmetric-difference volume"
        )
    return {
        "method": method,
        "assigned_minus_constructed_mm3": assigned_minus_constructed,
        "constructed_minus_assigned_mm3": constructed_minus_assigned,
        "maximum_bound_error_mm": maximum_bound_error,
        "volume_error_mm3": volume_error,
        "topology": assigned_topology,
    }


def assert_finalized_target(
    context: dict[str, Any],
    candidate_shape: Any,
    construction: dict[str, Any],
    metadata_manifest: Sequence[dict[str, str]],
) -> dict[str, Any]:
    target = context["target"]
    original = context["original"]
    if (
        target.Name != original["name"]
        or target.Label != original["label"]
        or target.TypeId != original["type_id"]
    ):
        raise RuntimeError("target identity changed")
    if target.Placement != original["placement"]:
        raise RuntimeError("target placement changed")
    require_single_solid(target.Shape, "finalized V6 target")
    shape_assignment = assert_assigned_shape_equivalent(
        target.Shape,
        candidate_shape,
        float(
            context["parameters"]["validation_contract"]["limits"][
                "maximum_unintended_positive_intersection_mm3"
            ]
        ),
    )
    shape_records = shape_check_records(target.Shape, "finalized V6 target")
    for record in metadata_manifest:
        assert_property_schema(
            target,
            record["property_type"],
            record["name"],
            record["group"],
        )
    product_defects = assert_product_defect_regressions(
        context["parameters"], construction
    )
    return {
        "identity_assertions_performed": True,
        "placement_assertions_performed": True,
        "shape_assertions_performed": True,
        "product_defect_assertions_performed": True,
        "shape_check_record_count": len(shape_records),
        "shape_assignment": shape_assignment,
        "metadata_property_count": len(metadata_manifest),
        "product_defect_results": product_defects,
    }


def finalize_target(
    context: dict[str, Any],
    candidate_shape: Any,
    construction: dict[str, Any],
) -> dict[str, Any]:
    trace = context["finalization_trace"]
    target = context["target"]
    target.Shape = candidate_shape
    trace["target_assignment_performed"] = True
    metadata_manifest = attach_history(
        target,
        context["parameters"],
        construction,
    )
    trace["metadata_assignment_performed"] = True
    context["document"].recompute()
    trace["recompute_performed"] = True
    assertions = assert_finalized_target(
        context,
        candidate_shape,
        construction,
        metadata_manifest,
    )
    trace["final_assertions_performed"] = True
    return {
        "trace": dict(trace),
        "metadata_manifest": list(metadata_manifest),
        "assertions": assertions,
    }


def construct_and_finalize_target(context: dict[str, Any]) -> dict[str, Any]:
    context["geometry_construction_started"] = True
    candidate_shape, construction = construct_serviceable_eye(
        context["parameters"], context["App"], context["Part"]
    )
    finalization = finalize_target(context, candidate_shape, construction)
    return {
        "candidate_shape": candidate_shape,
        "construction": construction,
        "finalization": finalization,
    }


def tuple3(value: Any) -> tuple[float, float, float]:
    return float(value[0]), float(value[1]), float(value[2])


def shape_record(shape: Any, color: tuple[int, int, int], placement: Any | None = None, deflection: float = 1.2) -> dict[str, Any]:
    points, facets = shape.tessellate(deflection)
    vertices = []
    for point in points:
        transformed = placement.multVec(point) if placement is not None else point
        vertices.append((float(transformed.x), float(transformed.y), float(transformed.z)))
    return {
        "vertices": vertices,
        "triangles": [tuple(int(index) for index in facet[:3]) for facet in facets],
        "color": color,
    }


def mesh_record(mesh: Any, color: tuple[int, int, int]) -> dict[str, Any]:
    points, facets = mesh.Topology
    return {
        "vertices": [tuple3(point) for point in points],
        "triangles": [tuple(int(index) for index in facet[:3]) for facet in facets],
        "color": color,
    }


def object_color(name: str, target_name: str) -> tuple[int, int, int]:
    if name == target_name:
        return (28, 151, 190)
    if "EAR" in name:
        return (176, 145, 99)
    if "PANEL" in name:
        return (224, 145, 54)
    if "LOWER" in name:
        return (102, 109, 117)
    if "C001" in name:
        return (78, 137, 94)
    return (165, 170, 177)


def document_records(document: Any) -> list[dict[str, Any]]:
    records = []
    for obj in document.Objects:
        if hasattr(obj, "Shape") and not obj.Shape.isNull():
            records.append(
                shape_record(
                    obj.Shape,
                    object_color(obj.Name, TARGET_OBJECT),
                    obj.Placement if hasattr(obj, "Placement") else None,
                    0.8 if obj.Name == TARGET_OBJECT else 1.8,
                )
            )
    return records


def dot(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return sum(first[index] * second[index] for index in range(3))


def cross(first: tuple[float, float, float], second: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def normalize(value: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(dot(value, value))
    if length <= 1.0e-12:
        raise RuntimeError("render vector has zero length")
    return tuple(component / length for component in value)  # type: ignore[return-value]


def blend_pixel(pixels: bytearray, width: int, height: int, x_value: int, y_value: int, color: tuple[int, int, int]) -> None:
    if 0 <= x_value < width and 0 <= y_value < height:
        offset = (y_value * width + x_value) * 3
        pixels[offset : offset + 3] = bytes(color)


def fill_triangle(pixels: bytearray, width: int, height: int, points: Sequence[tuple[float, float]], color: tuple[int, int, int]) -> None:
    minimum_y = max(0, int(math.floor(min(point[1] for point in points))))
    maximum_y = min(height - 1, int(math.ceil(max(point[1] for point in points))))
    for y_value in range(minimum_y, maximum_y + 1):
        scan_y = y_value + 0.5
        intersections = []
        for index, first in enumerate(points):
            second = points[(index + 1) % 3]
            low, high = min(first[1], second[1]), max(first[1], second[1])
            if high - low <= 1.0e-9 or not (low <= scan_y < high):
                continue
            ratio = (scan_y - first[1]) / (second[1] - first[1])
            intersections.append(first[0] + ratio * (second[0] - first[0]))
        if len(intersections) < 2:
            continue
        start = max(0, int(math.ceil(min(intersections))))
        end = min(width - 1, int(math.floor(max(intersections))))
        if end >= start:
            offset = (y_value * width + start) * 3
            pixels[offset : offset + (end - start + 1) * 3] = bytes(color) * (
                end - start + 1
            )


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    )


def write_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    rows = []
    stride = width * 3
    for row in range(height):
        rows.append(b"\x00" + bytes(pixels[row * stride : (row + 1) * stride]))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(b"".join(rows), 7))
        + png_chunk(b"IEND", b"")
    )


def render_panel(records: Sequence[dict[str, Any]], direction: tuple[float, float, float], up_hint: tuple[float, float, float], focus: tuple[float, float, float] | None = None, focus_span: float | None = None) -> bytearray:
    view = normalize(direction)
    right = normalize(cross(view, normalize(up_hint)))
    up = normalize(cross(right, view))
    projected_records = []
    all_x: list[float] = []
    all_y: list[float] = []
    for record in records:
        projected = [(dot(point, right), dot(point, up), dot(point, view)) for point in record["vertices"]]
        projected_records.append((record, projected))
        all_x.extend(point[0] for point in projected)
        all_y.extend(point[1] for point in projected)
    if not all_x:
        raise RuntimeError("review scene has no geometry")
    if focus is None:
        center_x = (min(all_x) + max(all_x)) / 2.0
        center_y = (min(all_y) + max(all_y)) / 2.0
        span_x = max(max(all_x) - min(all_x), 1.0)
        span_y = max(max(all_y) - min(all_y), 1.0)
    else:
        center_x, center_y = dot(focus, right), dot(focus, up)
        span_x = span_y = float(focus_span or 40.0)
    scale = min((IMAGE_WIDTH - 70) / span_x, (IMAGE_HEIGHT - 70) / span_y)
    triangles = []
    light = normalize((-view[0] + up[0] * 0.35, -view[1] + up[1] * 0.35, -view[2] + up[2] * 0.35))
    for record, projected in projected_records:
        for indices in record["triangles"]:
            points3 = [record["vertices"][index] for index in indices]
            first = tuple(points3[1][i] - points3[0][i] for i in range(3))
            second = tuple(points3[2][i] - points3[0][i] for i in range(3))
            normal = cross(first, second)
            if dot(normal, normal) <= 1.0e-16:
                continue
            shade = 0.58 + 0.42 * abs(dot(normalize(normal), light))
            color = tuple(max(0, min(255, int(channel * shade))) for channel in record["color"])
            points2 = [
                (
                    IMAGE_WIDTH / 2.0 + (projected[index][0] - center_x) * scale,
                    IMAGE_HEIGHT / 2.0 - (projected[index][1] - center_y) * scale,
                )
                for index in indices
            ]
            depth = sum(projected[index][2] for index in indices) / 3.0
            triangles.append((depth, points2, color))
    triangles.sort(key=lambda item: item[0], reverse=True)
    pixels = bytearray((246, 247, 249) * (IMAGE_WIDTH * IMAGE_HEIGHT))
    for _, points, color in triangles:
        fill_triangle(pixels, IMAGE_WIDTH, IMAGE_HEIGHT, points, color)
    return pixels


def render_side_by_side(path: Path, baseline_records: Sequence[dict[str, Any]], candidate_records: Sequence[dict[str, Any]], direction: tuple[float, float, float], up: tuple[float, float, float], focus: tuple[float, float, float] | None = None, focus_span: float | None = None) -> None:
    left = render_panel(baseline_records, direction, up, focus, focus_span)
    right = render_panel(candidate_records, direction, up, focus, focus_span)
    width = IMAGE_WIDTH * 2 + 12
    pixels = bytearray((35, 39, 45) * (width * IMAGE_HEIGHT))
    for row in range(IMAGE_HEIGHT):
        source = row * IMAGE_WIDTH * 3
        target = row * width * 3
        pixels[target : target + IMAGE_WIDTH * 3] = left[source : source + IMAGE_WIDTH * 3]
        right_target = target + (IMAGE_WIDTH + 12) * 3
        pixels[right_target : right_target + IMAGE_WIDTH * 3] = right[source : source + IMAGE_WIDTH * 3]
    write_png(path, width, IMAGE_HEIGHT, pixels)


def hardware_shapes(parameters: dict[str, Any], construction: dict[str, Any], Part: Any) -> dict[str, dict[str, Any]]:
    hardware = parameters["validation_contract"]["hardware_envelopes"]
    mount_values = parameters["geometry"]["head_mount"]
    thickness = float(mount_values["leaf_thickness_mm"])
    mating = float(mount_values["bore_center_to_mating_face_mm"])
    result = {}
    for role, mount in construction["mounts"].items():
        bore_axis_vector = mount["bore_axis_vector"]
        eye_face = mount["eye_bore"] + bore_axis_vector * (thickness - mating)
        head_face = mount["head_bore"] - bore_axis_vector * (thickness - mating)
        washer_t = float(hardware["washer_thickness_mm"])
        result[role] = {
            "bolt": Part.makeCylinder(float(hardware["bolt_diameter_mm"]) / 2.0, float(hardware["bolt_max_length_mm"]), head_face, bore_axis_vector),
            "head_washer": Part.makeCylinder(float(hardware["washer_outer_diameter_mm"]) / 2.0, washer_t, head_face - bore_axis_vector * washer_t, bore_axis_vector),
            "eye_washer": Part.makeCylinder(float(hardware["washer_outer_diameter_mm"]) / 2.0, washer_t, eye_face, bore_axis_vector),
            "nyloc": Part.makeCylinder(float(hardware["nyloc_outer_diameter_mm"]) / 2.0, float(hardware["nyloc_length_mm"]), head_face - bore_axis_vector * (washer_t + float(hardware["nyloc_length_mm"])), bore_axis_vector),
            "tool": Part.makeCylinder(float(hardware["tool_approach_diameter_mm"]) / 2.0, float(hardware["tool_approach_length_mm"]), head_face - bore_axis_vector * (washer_t + float(hardware["nyloc_length_mm"]) + float(hardware["tool_approach_length_mm"])), bore_axis_vector),
        }
    return result


def read_step(Part: Any, path: Path) -> Any:
    shape = Part.Shape()
    shape.read(str(path))
    if shape.isNull():
        raise RuntimeError(f"STEP imported null: {path}")
    return shape


def render_review_pack(
    context: dict[str, Any],
    baseline_records: Sequence[dict[str, Any]],
    baseline_target_shape: Any,
    construction: dict[str, Any],
) -> None:
    root = context["root"]
    contract = context["contract"]
    parameters = context["parameters"]
    document = context["document"]
    Part = context["Part"]
    candidate_records = document_records(document)
    fixed_views = {
        "front": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "rear": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
        "left": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        "right": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        "top": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
        "bottom": ((0.0, 0.0, 1.0), (0.0, -1.0, 0.0)),
    }
    for name, (direction, up) in fixed_views.items():
        render_side_by_side(
            root / contract["output"]["review_files"][name],
            baseline_records,
            candidate_records,
            direction,
            up,
        )

    extras = parameters["review_artifacts"]
    axis_n = tuple3(construction["axis_n"])
    axis_u = tuple3(construction["axis_u"])
    for index, corner in enumerate(construction["aperture_exact"]):
        render_side_by_side(
            root / extras["exterior_aperture_corners"][index],
            baseline_records,
            candidate_records,
            axis_n,
            axis_u,
            tuple3(corner),
            34.0,
        )

    target = context["target"].Shape
    hardware = hardware_shapes(parameters, construction, Part)
    colors = {
        "bolt": (34, 126, 210),
        "head_washer": (242, 178, 42),
        "eye_washer": (242, 178, 42),
        "nyloc": (140, 76, 190),
        "tool": (45, 175, 104),
    }
    baseline_hardware_records = [
        shape_record(baseline_target_shape, (162, 169, 177), deflection=0.8)
    ]
    candidate_hardware_records = [
        shape_record(target, (35, 151, 190), deflection=0.7)
    ]
    for role_shapes in hardware.values():
        for name, shape in role_shapes.items():
            record = shape_record(shape, colors[name], deflection=0.35)
            baseline_hardware_records.append(record)
            candidate_hardware_records.append(record)
    render_side_by_side(
        root / extras["interior_flange_backs_and_hardware"],
        baseline_hardware_records,
        candidate_hardware_records,
        tuple(-value for value in axis_n),
        axis_u,
    )

    cap_ref = parameters["fit_references"]["exact_v9_cap"]
    cap = read_step(Part, root / cap_ref["path"])
    seated = translated(
        cap,
        construction["axis_n"]
        * float(parameters["geometry"]["rear_cap_connector"]["reference_seating_translation_mm"]),
    )
    removed = translated(
        seated,
        construction["axis_n"]
        * float(parameters["validation_contract"]["motion"]["rear_cap_sweep_distance_mm"]),
    )
    baseline_cap_records = [
        shape_record(baseline_target_shape, (162, 169, 177), deflection=0.8),
        shape_record(seated, (237, 170, 55), deflection=0.6),
        shape_record(removed, (68, 167, 112), deflection=0.6),
    ]
    candidate_cap_records = [
        shape_record(target, (34, 151, 190), deflection=0.75),
        shape_record(seated, (237, 170, 55), deflection=0.6),
        shape_record(removed, (68, 167, 112), deflection=0.6),
    ]
    render_side_by_side(
        root / extras["rear_cap_installation_removal"],
        baseline_cap_records,
        candidate_cap_records,
        tuple3(construction["axis_v"]),
        axis_u,
    )

    mount_centers = [record["eye_bore"] for record in construction["mounts"].values()]
    section_center = (mount_centers[0] + mount_centers[1]) / 2.0
    slab = oriented_box(
        Part,
        section_center,
        (construction["axis_u"], construction["axis_n"], construction["axis_v"]),
        (150.0, 60.0, 1.0),
    )
    section = target.common(slab).removeSplitter()
    baseline_section = baseline_target_shape.common(slab).removeSplitter()
    baseline_section_records = [
        shape_record(baseline_section, (162, 169, 177), deflection=0.4)
    ]
    section_records = [shape_record(section, (223, 130, 38), deflection=0.35)]
    for role, record in construction["mounts"].items():
        section_records.append(
            shape_record(
                record["drilled"],
                (44, 154, 190) if role == "upper" else (93, 88, 184),
                deflection=0.35,
            )
        )
    render_side_by_side(
        root / extras["section_through_chamber_and_mounts"],
        baseline_section_records,
        section_records,
        tuple3(construction["axis_v"]),
        axis_u,
    )


def save_as_candidate_document(context: dict[str, Any]) -> None:
    context["io_trace"]["save_as_called"] = True
    context["document"].saveAs(str(context["candidate_path"]))
    context["io_trace"]["candidate_created"] = True


def save_candidate_document(context: dict[str, Any]) -> None:
    context["io_trace"]["document_save_called"] = True
    context["document"].save()


def close_context_document(context: dict[str, Any]) -> None:
    document = context.get("document")
    if document is None:
        return
    if document.Name in context["App"].listDocuments():
        context["App"].closeDocument(document.Name)


def prepare_disposable_finalization_document(context: dict[str, Any]) -> None:
    canonical_document = context["document"]
    context["App"].closeDocument(canonical_document.Name)
    context["document"] = None
    context["target"] = None
    disposable_document = context["App"].newDocument(
        "RightEyeV6InMemoryFinalizationPreflight"
    )
    disposable_target = disposable_document.addObject(
        context["original"]["type_id"],
        context["original"]["name"],
    )
    disposable_target.Label = context["original"]["label"]
    disposable_target.Placement = context["App"].Placement(
        context["original"]["placement"]
    )
    if getattr(disposable_document, "FileName", ""):
        raise RuntimeError("disposable preflight document unexpectedly has a file")
    context["document"] = disposable_document
    context["target"] = disposable_target
    context["disposable_document"] = True
    context["canonical_document_closed_without_save"] = True


def construct_candidate(context: dict[str, Any]) -> None:
    document, target = context["document"], context["target"]
    baseline_records = document_records(document)
    baseline_target_shape = target.Shape.copy()
    context["output_dir"].mkdir(parents=True, exist_ok=False)
    context["candidate_path"].parent.mkdir(parents=True, exist_ok=True)
    save_as_candidate_document(context)
    print("STAGE 1/5 immutable V6 preflight passed and saveAs completed", flush=True)
    finalized = construct_and_finalize_target(context)
    construction = finalized["construction"]
    print(
        "STAGE 2/5 new compact-leaf serviceable eye constructed and finalized",
        flush=True,
    )
    save_candidate_document(context)
    print("STAGE 3/5 candidate saved with only target geometry replaced", flush=True)
    render_review_pack(
        context, baseline_records, baseline_target_shape, construction
    )
    print("STAGE 4/5 opaque comparison and service review pack rendered", flush=True)
    if sha256_file(context["baseline_path"]) != context["baseline"]["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 changed during generation")
    print("STAGE 5/5 canonical V34 remains hash-identical", flush=True)


def in_memory_finalization_preflight(context: dict[str, Any]) -> dict[str, Any]:
    """Run the exact target finalizer in one disposable unsaved document."""
    if context["requires_new_output"]:
        raise RuntimeError("in-memory finalization requires no-output preflight mode")
    prepare_disposable_finalization_document(context)
    finalized = construct_and_finalize_target(context)
    candidate_shape = finalized["candidate_shape"]
    construction = finalized["construction"]
    finalization = finalized["finalization"]
    if sha256_file(context["baseline_path"]) != context["baseline"]["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 changed during in-memory preflight")
    io_trace = context["io_trace"]
    trace = finalization["trace"]
    if any(
        (
            io_trace["save_as_called"],
            io_trace["document_save_called"],
            io_trace["geometry_export_created"],
            io_trace["candidate_created"],
        )
    ):
        raise RuntimeError("in-memory finalization attempted a prohibited write")
    return {
        "status": "IN_MEMORY_FINALIZATION_PASS",
        "iteration_id": ITERATION_ID,
        "design_id": DESIGN_ID,
        "tooling_revision": TOOLING_REVISION,
        "design_signature_sha256": context["design_report"]["design_signature_sha256"],
        "rejected_signature_match": False,
        "shared_contract_preflight": context["shared_report"]["status"],
        "runtime": context["runtime"],
        "geometry_construction_started": True,
        "target_assignment_performed": trace["target_assignment_performed"],
        "metadata_assignment_performed": trace[
            "metadata_assignment_performed"
        ],
        "recompute_performed": trace["recompute_performed"],
        "final_assertions_performed": trace["final_assertions_performed"],
        "save_as_called": io_trace["save_as_called"],
        "document_save_called": io_trace["document_save_called"],
        "candidate_exists": io_trace["candidate_created"],
        "geometry_export_created": io_trace["geometry_export_created"],
        "disposable_document_unsaved": not bool(
            getattr(context["document"], "FileName", "")
        ),
        "canonical_document_closed_without_save": context[
            "canonical_document_closed_without_save"
        ],
        "candidate_output_inspected": False,
        "quarantined_v6_candidate_used": False,
        "valid": bool(candidate_shape.isValid()),
        "closed": bool(candidate_shape.isClosed()),
        "solid_count": len(candidate_shape.Solids),
        "connected_component_count": len(candidate_shape.Solids),
        "self_intersection_count": finalization["assertions"][
            "shape_check_record_count"
        ],
        "volume_mm3": float(candidate_shape.Volume),
        "metadata_property_count": finalization["assertions"][
            "metadata_property_count"
        ],
        "final_assertions": finalization["assertions"],
        "v1_or_v3_geometry_source_used": False,
        "quarantined_v4_geometry_source_used": False,
        "quarantined_v5_geometry_source_used": False,
        "rear_cap_edge_projection": context["root_projection_report"],
        "mount_frame_preflight": context["frame_preflight_report"],
        "constructed_mount_roles": sorted(construction["mounts"]),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.pure_frame_preflight_only:
        print(
            json.dumps(
                pure_frame_preflight(args.baseline, args.contract),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    context = immutable_preflight(
        args.baseline,
        args.contract,
        require_new_output=not args.in_memory_finalization_preflight,
    )
    try:
        if args.in_memory_finalization_preflight:
            print(
                json.dumps(
                    in_memory_finalization_preflight(context),
                    indent=2,
                    sort_keys=True,
                )
            )
            return 0
        construct_candidate(context)
        return 0
    finally:
        close_context_document(context)


if __name__ == "__main__":
    raise SystemExit(main())
