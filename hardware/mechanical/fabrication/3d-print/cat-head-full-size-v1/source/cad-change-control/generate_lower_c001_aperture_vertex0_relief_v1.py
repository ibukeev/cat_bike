#!/usr/bin/env python3
"""Generate the isolated lower-C001 aperture-vertex relief candidate.

The only persisted mutation is ``FROZEN_RIGHT_LOWER_MAIN_V34.Shape``.  The
relief is the single connected intersection between that owner and the exact
1.000 mm tubular envelope of the immutable eye-aperture wire.  The canonical
V34 document is opened read-only and is never saved.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Sequence


ITERATION_ID = "lower-c001-aperture-vertex0-relief-v1"
DESIGN_ID = "lower-c001-aperture-vertex0-relief-A"
TOOLING_REVISION = 3
TARGET_OBJECT = "FROZEN_RIGHT_LOWER_MAIN_V34"
SIGNATURE_ALGORITHM = "sha256-canonical-json-decimal-v1"
SIGNED_FIELDS = (
    "construction_algorithm_id",
    "relief",
    "cover_lip_interface",
    "aperture_lcs",
    "shell_opening_boundary_mm",
)
RENDER_TOOLKIT_FILENAME = "generate_right_eye_serviceable_fit_prototype_v6_attempt_002.py"
RENDER_TOOLKIT_SHA256 = "bba7f44c07c20526ccda2d1cbefdfe38fe86ddc1bd5a48c354928e8fcb3a50e9"
SIGNATURE_HELPER_FILENAME = "validate_right_eye_serviceable_fit_previsual_v4.py"
SIGNATURE_HELPER_SHA256 = "2e2b60894fcdc21279fa9f297620000bdc524cd7499c68317eb896ac2f8053c8"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--in-memory-finalization-preflight", action="store_true")
    return parser.parse_args(argv)


def repository_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("cannot locate repository root")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: root must be an object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def import_pinned(path: Path, expected_sha256: str, name: str) -> Any:
    actual = sha256_file(path) if path.is_file() else None
    if actual != expected_sha256:
        raise RuntimeError(f"{path.name}: hash mismatch: {actual} != {expected_sha256}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_pinned(root: Path, spec: dict[str, Any], label: str) -> Path:
    path = root / str(spec["path"])
    actual = sha256_file(path) if path.is_file() else None
    if actual != spec["sha256"]:
        raise RuntimeError(f"{label}: hash mismatch: {actual} != {spec['sha256']}")
    return path


def validate_design_control(
    root: Path, contract: dict[str, Any], parameters: dict[str, Any]
) -> dict[str, Any]:
    control = parameters.get("design_control")
    if not isinstance(control, dict):
        raise RuntimeError("design_control is required")
    if control.get("design_id") != DESIGN_ID:
        raise RuntimeError("design_id mismatch")
    if control.get("tooling_revision") != TOOLING_REVISION:
        raise RuntimeError("tooling_revision mismatch")
    if control.get("approval") is not True:
        raise RuntimeError("relief design is not approved")
    signature = control.get("design_signature", {})
    if signature.get("algorithm") != SIGNATURE_ALGORITHM:
        raise RuntimeError("signature algorithm mismatch")
    if tuple(signature.get("signed_fields", [])) != SIGNED_FIELDS:
        raise RuntimeError("signed field set mismatch")
    helper_path = Path(__file__).with_name(SIGNATURE_HELPER_FILENAME)
    helper = import_pinned(
        helper_path, SIGNATURE_HELPER_SHA256, "lower_c001_signature_helper"
    )
    payload = {field: parameters[field] for field in SIGNED_FIELDS}
    calculated = helper.calculate_design_signature(payload)
    declared = signature.get("sha256")
    if not isinstance(declared, str) or not re.fullmatch(r"[0-9a-f]{64}", declared):
        raise RuntimeError("declared design signature is invalid")
    if declared != calculated:
        raise RuntimeError(f"design signature mismatch: {declared} != {calculated}")
    registry_path = verify_pinned(
        root, control["rejected_signature_registry"], "rejected signature registry"
    )
    registry = load_json(registry_path)
    for entry in registry.get("rejected_designs", []):
        rejected_payload = entry.get("signature_payload")
        if not isinstance(rejected_payload, dict):
            raise RuntimeError("rejected registry entry lacks signature payload")
        rejected = helper.calculate_design_signature(rejected_payload)
        if rejected != entry.get("design_signature_sha256"):
            raise RuntimeError("rejected registry contains an invalid signature")
        if rejected == calculated:
            raise RuntimeError(f"REJECTED_DESIGN_SIGNATURE: {entry.get('registry_id')}")
    return {"signature_sha256": calculated, "payload": payload}


def validate_contract_scope(contract: dict[str, Any]) -> dict[str, Any]:
    if contract.get("iteration_id") != ITERATION_ID:
        raise RuntimeError("iteration ID mismatch")
    if contract.get("target_object") != TARGET_OBJECT:
        raise RuntimeError("target object mismatch")
    mutations = contract.get("allowed_mutations", [])
    if len(mutations) != 1:
        raise RuntimeError("exactly one mutation is required")
    mutation = mutations[0]
    if mutation.get("kind") != "replace_geometry" or mutation.get("object") != TARGET_OBJECT:
        raise RuntimeError("relief requires one replace_geometry target mutation")
    parameters = mutation.get("parameters")
    if not isinstance(parameters, dict):
        raise RuntimeError("mutation parameters are missing")
    return parameters


def vector(App: Any, values: Sequence[float]) -> Any:
    return App.Vector(*[float(value) for value in values])


def normalized(App: Any, value: Any, label: str) -> Any:
    result = App.Vector(value)
    if result.Length <= 1.0e-12:
        raise RuntimeError(f"{label} has zero length")
    result.normalize()
    return result


def local_coordinates(point: Any, origin: Any, axes: Sequence[Any]) -> list[float]:
    delta = point - origin
    return [float(delta.dot(axis)) for axis in axes]


def planar_loop(
    App: Any, points: Sequence[Sequence[float]], origin: Any, axes: Sequence[Any]
) -> list[Any]:
    output = []
    axis_u, axis_v, _axis_n = axes
    for values in points:
        point = vector(App, values)
        local = local_coordinates(point, origin, axes)
        output.append(origin + axis_u * local[0] + axis_v * local[1])
    return output


def require_single_solid(shape: Any, label: str) -> None:
    if (
        shape.isNull()
        or not shape.isValid()
        or not shape.isClosed()
        or len(shape.Solids) != 1
    ):
        raise RuntimeError(
            f"{label}: expected one valid closed solid; "
            f"valid={shape.isValid()} closed={shape.isClosed()} solids={len(shape.Solids)}"
        )


def capsule_envelope(Part: Any, aperture: Sequence[Any], radius: float) -> Any:
    pieces = [Part.makeSphere(radius, point) for point in aperture]
    for index, first in enumerate(aperture):
        delta = aperture[(index + 1) % len(aperture)] - first
        pieces.append(Part.makeCylinder(radius, float(delta.Length), first, delta))
    envelope = pieces[0].multiFuse(pieces[1:]).removeSplitter()
    require_single_solid(envelope, "immutable aperture exclusion envelope")
    return envelope


def opening_prism(
    Part: Any, opening: Sequence[Any], axis_n: Any, depth: float = 200.0
) -> Any:
    start = [point - axis_n * (depth / 2.0) for point in opening]
    face = Part.Face(Part.makePolygon([*start, start[0]]))
    prism = face.extrude(axis_n * depth)
    require_single_solid(prism, "existing eye-opening projection prism")
    return prism


def proposed_cover_lip_envelope(
    parameters: dict[str, Any],
    opening: Sequence[Any],
    axes: Sequence[Any],
    App: Any,
    Part: Any,
) -> dict[str, Any]:
    """Build only the pinned adverse-tolerance coverage envelope, never eye geometry."""
    spec = parameters["cover_lip_interface"]
    if spec["source_eye_design_id"] != "right-eye-split-service-cassette-D":
        raise RuntimeError("cover-lip source eye design changed")
    if spec["source_eye_design_signature_sha256"] != (
        "362d5bf06ab5dbf94a087dc0a40977d8277e9281a358d98a25a8043a1865ce73"
    ):
        raise RuntimeError("cover-lip source eye signature changed")
    if spec["baseline_exterior_face_index"] != 321:
        raise RuntimeError("cover-lip exterior face anchor changed")
    insets = [float(value) for value in spec["source_front_outer_vertex_insets_mm"]]
    if len(opening) != 4 or insets != [0.3, 0.3, 0.3, 0.3]:
        raise RuntimeError("cover-lip source bezel footprint changed")
    center = App.Vector(0.0, 0.0, 0.0)
    for point in opening:
        center += point
    center /= float(len(opening))
    outer_front = []
    for point, inset in zip(opening, insets):
        radial = point - center
        radial -= axes[2] * radial.dot(axes[2])
        radial = normalized(App, radial, "cover-lip source outer radial")
        outer_front.append(point - radial * inset)
    edge_indices = list(spec["source_outer_edge_vertex_indices"])
    if edge_indices != [0, 3]:
        raise RuntimeError("cover-lip source edge changed")
    tangent = normalized(
        App,
        outer_front[edge_indices[1]] - outer_front[edge_indices[0]],
        "cover-lip tangent",
    )
    outward = normalized(App, axes[2].cross(tangent), "cover-lip outward")
    tolerance = float(spec["adverse_dimensional_tolerance_mm"])
    nominal_reach = float(spec["nominal_in_plane_reach_mm"])
    effective_reach = nominal_reach - tolerance
    nominal_outward = float(spec["nominal_outward_axial_cover_mm"])
    effective_outward = nominal_outward - tolerance
    if nominal_reach + 1.0e-12 < float(
        spec["measured_tolerance_inclusive_required_reach_mm"]
    ):
        raise RuntimeError("cover-lip nominal reach is insufficient")
    required_effective_reach = (
        float(spec["measured_tolerance_inclusive_required_reach_mm"]) - tolerance
    )
    if effective_reach + 1.0e-12 < required_effective_reach:
        raise RuntimeError("cover-lip adverse in-plane reach is insufficient")
    if effective_outward + 1.0e-12 < float(
        spec["required_measured_outward_cover_mm"]
    ):
        raise RuntimeError("cover-lip adverse axial cover is insufficient")
    coverage_depth = float(spec["coverage_envelope_inward_depth_mm"])
    if abs(coverage_depth - effective_outward) > 1.0e-12:
        raise RuntimeError("cover-lip adverse axial envelope must terminate at n=0")
    tangent_start = float(spec["tangent_start_mm"]) + tolerance
    tangent_end = (
        float(spec["tangent_start_mm"])
        + float(spec["tangent_length_mm"])
        - tolerance
    )
    if tangent_end <= tangent_start:
        raise RuntimeError("cover-lip tangent interval collapsed")
    start = outer_front[edge_indices[0]] + tangent * tangent_start
    end = outer_front[edge_indices[0]] + tangent * tangent_end
    loop = [start, end, end + outward * effective_reach, start + outward * effective_reach]
    face = Part.Face(Part.makePolygon([*loop, loop[0]]))
    front = face.copy()
    front.translate(axes[2] * -effective_outward)
    volume = front.extrude(axes[2] * coverage_depth)
    require_single_solid(volume, "proposed lower-V0 cover-lip envelope")
    return {
        "volume": volume,
        "footprint": face,
        "effective_reach_mm": effective_reach,
        "effective_outward_cover_mm": effective_outward,
        "effective_tangent_start_mm": tangent_start,
        "effective_tangent_end_mm": tangent_end,
    }


def deep_bop_defect_counts(shape: Any) -> dict[str, int]:
    """Return normalized deep-BOP defects, including ValueError diagnostics."""
    try:
        records = [str(item) for item in (shape.check(True) or [])]
    except ValueError as exc:
        records = str(exc).splitlines()
    defects: dict[str, int] = {}
    for record in records:
        match = re.search(r"Error in ([^:]+):\s*(.+)$", record.strip())
        key = (
            f"{match.group(1)}:{match.group(2)}"
            if match
            else f"UNPARSED:{record.strip()}"
        )
        defects[key] = defects.get(key, 0) + 1
    return dict(sorted(defects.items()))


def added_deep_bop_defects(
    baseline: dict[str, int], candidate: dict[str, int]
) -> dict[str, int]:
    return {
        key: count - baseline.get(key, 0)
        for key, count in candidate.items()
        if count > baseline.get(key, 0)
    }


def construct_relief(context: dict[str, Any]) -> tuple[Any, dict[str, Any]]:
    App, Part = context["App"], context["Part"]
    parameters = context["parameters"]
    target_shape = context["original_shape"]
    relief = parameters["relief"]
    lcs = parameters["aperture_lcs"]
    origin = vector(App, lcs["origin_mm"])
    axes = (
        normalized(App, vector(App, lcs["u"]), "aperture u"),
        normalized(App, vector(App, lcs["v"]), "aperture v"),
        normalized(App, vector(App, lcs["inward_n"]), "aperture inward n"),
    )
    aperture = planar_loop(App, lcs["visible_aperture_mm"], origin, axes)
    opening = planar_loop(
        App, parameters["shell_opening_boundary_mm"], origin, axes
    )
    aperture_digest = canonical_json_sha256(lcs["visible_aperture_mm"])
    if aperture_digest != relief["immutable_aperture_coordinates_sha256"]:
        raise RuntimeError("immutable aperture coordinate digest mismatch")
    vertex0 = aperture[0]
    expected_vertex0 = vector(App, relief["vertex0_head_mm"])
    if (vertex0 - expected_vertex0).Length > float(relief["coordinate_tolerance_mm"]):
        raise RuntimeError("approved aperture vertex V0 changed")
    wire = Part.makePolygon([*aperture, aperture[0]])
    pre_distance = float(wire.distToShape(target_shape)[0])
    if abs(pre_distance - float(relief["approved_pre_relief_span_mm"])) > float(
        relief["measurement_tolerance_mm"]
    ):
        raise RuntimeError("baseline aperture-to-lower_C001 span changed")
    radius = float(relief["exclusion_envelope_radius_mm"])
    envelope = capsule_envelope(Part, aperture, radius)
    expected_removed = target_shape.common(envelope).removeSplitter()
    require_single_solid(expected_removed, "single connected V0 relief intersection")
    removed_defects = deep_bop_defect_counts(expected_removed)
    if removed_defects:
        raise RuntimeError(f"approved V0 relief cutter has deep defects: {removed_defects}")
    if float(expected_removed.distToShape(Part.Vertex(vertex0))[0]) > radius + 1.0e-6:
        raise RuntimeError("relief intersection is not the V0-connected component")
    # Subtract only the already-intersected, deep-checked material.  This is
    # physically identical to the approved envelope intersection while
    # avoiding a second global envelope/target Boolean.
    candidate = target_shape.cut(expected_removed).removeSplitter()
    require_single_solid(candidate, "relieved lower_C001")
    baseline_deep_defects = deep_bop_defect_counts(target_shape)
    candidate_deep_defects = deep_bop_defect_counts(candidate)
    new_deep_defects = added_deep_bop_defects(
        baseline_deep_defects, candidate_deep_defects
    )
    if new_deep_defects:
        raise RuntimeError(f"relief introduced deep BOP defects: {new_deep_defects}")
    actual_removed = target_shape.cut(candidate).removeSplitter()
    require_single_solid(actual_removed, "actual lower_C001 removed material")
    added = candidate.cut(target_shape).removeSplitter()
    post_distance = float(wire.distToShape(candidate)[0])
    opening_region = opening_prism(Part, opening, axes[2])
    outside_opening = float(actual_removed.cut(opening_region).Volume)
    lip = proposed_cover_lip_envelope(parameters, opening, axes, App, Part)
    face_index = int(parameters["cover_lip_interface"]["baseline_exterior_face_index"])
    if face_index < 1 or face_index > len(target_shape.Faces):
        raise RuntimeError("pinned exterior face index is unavailable")
    exterior_patch = target_shape.Faces[face_index - 1].common(actual_removed).removeSplitter()
    if exterior_patch.isNull():
        raise RuntimeError("pinned Face321 exterior relief patch is null")
    covered_patch = exterior_patch.common(lip["volume"])
    uncovered_patch = exterior_patch.cut(lip["volume"])
    expected_minus_actual = float(expected_removed.cut(actual_removed).Volume)
    actual_minus_expected = float(actual_removed.cut(expected_removed).Volume)
    retreat = radius - pre_distance
    measurements = {
        "aperture_coordinates_sha256": aperture_digest,
        "pre_relief_span_mm": pre_distance,
        "post_relief_span_mm": post_distance,
        "maximum_retreat_mm": retreat,
        "removed_volume_mm3": float(actual_removed.Volume),
        "added_volume_mm3": float(added.Volume),
        "expected_minus_actual_mm3": expected_minus_actual,
        "actual_minus_expected_mm3": actual_minus_expected,
        "removed_outside_eye_opening_mm3": outside_opening,
        "exterior_patch_area_mm2": float(exterior_patch.Area),
        "covered_exterior_patch_area_mm2": float(covered_patch.Area),
        "uncovered_exterior_patch_area_mm2": float(uncovered_patch.Area),
        "cover_area_balance_residual_mm2": float(
            exterior_patch.Area - covered_patch.Area - uncovered_patch.Area
        ),
        "cover_lip_effective_reach_mm": float(lip["effective_reach_mm"]),
        "cover_lip_effective_outward_cover_mm": float(
            lip["effective_outward_cover_mm"]
        ),
        "cover_lip_minimum_printed_wall_mm": float(
            parameters["cover_lip_interface"]["minimum_printed_wall_mm"]
        ),
        "removed_solid_count": len(actual_removed.Solids),
        "candidate_solid_count": len(candidate.Solids),
        "candidate_valid": bool(candidate.isValid()),
        "candidate_closed": bool(candidate.isClosed()),
        "baseline_deep_bop_defects": baseline_deep_defects,
        "candidate_deep_bop_defects": candidate_deep_defects,
        "new_deep_bop_defects": new_deep_defects,
    }
    return candidate, {
        "origin": origin,
        "axis_u": axes[0],
        "axis_v": axes[1],
        "axis_n": axes[2],
        "aperture": aperture,
        "aperture_wire": wire,
        "opening": opening,
        "opening_prism": opening_region,
        "envelope": envelope,
        "expected_removed": expected_removed,
        "actual_removed": actual_removed,
        "exterior_patch": exterior_patch,
        "cover_lip_envelope": lip["volume"],
        "measurements": measurements,
    }


def evaluate_measurements(parameters: dict[str, Any], values: dict[str, Any]) -> dict[str, Any]:
    relief = parameters["relief"]
    lip = parameters["cover_lip_interface"]
    boolean_epsilon = float(relief["boolean_volume_epsilon_mm3"])
    distance_tolerance = float(relief["measurement_tolerance_mm"])
    gates = {
        "R01_APERTURE_COORDINATES_EXACT": values["aperture_coordinates_sha256"]
        == relief["immutable_aperture_coordinates_sha256"],
        "R02_BASELINE_SPAN_PINNED": abs(
            float(values["pre_relief_span_mm"])
            - float(relief["approved_pre_relief_span_mm"])
        )
        <= distance_tolerance,
        "R03_SINGLE_CONNECTED_REMOVAL": int(values["removed_solid_count"]) == 1,
        "R04_SUBTRACTION_ONLY": float(values["added_volume_mm3"]) <= boolean_epsilon,
        "R05_EXACT_ENVELOPE_INTERSECTION": max(
            float(values["expected_minus_actual_mm3"]),
            float(values["actual_minus_expected_mm3"]),
        )
        <= boolean_epsilon,
        "R06_POST_SPAN_AT_LEAST_1MM": float(values["post_relief_span_mm"])
        >= float(relief["required_post_relief_span_mm"]) - distance_tolerance,
        "R07_RETREAT_WITHIN_HARD_CAP": float(values["maximum_retreat_mm"])
        <= float(relief["hard_cap_retreat_mm"]) + 1.0e-9,
        "R08_EXTERIOR_RELIEF_FULLY_COVERED_BY_PINNED_LIP": (
            abs(
                float(values["exterior_patch_area_mm2"])
                - float(lip["expected_exterior_relief_patch_area_mm2"])
            )
            <= float(lip["patch_area_tolerance_mm2"])
            and float(values["uncovered_exterior_patch_area_mm2"])
            <= float(lip["maximum_uncovered_patch_area_mm2"])
            and abs(float(values["cover_area_balance_residual_mm2"]))
            <= float(lip["patch_area_tolerance_mm2"])
            and float(values["cover_lip_effective_outward_cover_mm"])
            + 1.0e-12
            >= float(lip["required_measured_outward_cover_mm"])
            and float(values["cover_lip_effective_reach_mm"]) + 1.0e-12
            >= (
                float(lip["measured_tolerance_inclusive_required_reach_mm"])
                - float(lip["adverse_dimensional_tolerance_mm"])
            )
            and abs(
                float(values["cover_lip_minimum_printed_wall_mm"])
                - float(lip["minimum_printed_wall_mm"])
            )
            <= 1.0e-12
        ),
        "R09_VALID_CLOSED_SINGLE_TARGET": bool(values["candidate_valid"])
        and bool(values["candidate_closed"])
        and int(values["candidate_solid_count"]) == 1
        and not values["new_deep_bop_defects"],
        "R10_NONZERO_BOUNDED_RELIEF": boolean_epsilon
        < float(values["removed_volume_mm3"]),
    }
    failed = [name for name, passed in gates.items() if not passed]
    return {
        "status": "PASS" if not failed else "FAIL",
        "gates": gates,
        "failed_gates": failed,
    }


def attach_metadata(
    context: dict[str, Any], construction: dict[str, Any]
) -> list[dict[str, str]]:
    toolkit = context["renderer"]
    target = context["target"]
    parameters = context["parameters"]
    measurements = construction["measurements"]
    assigned = []
    for name, value in (
        ("LowerC001ReliefDesignId", DESIGN_ID),
        ("LowerC001ReliefIterationId", ITERATION_ID),
        ("LowerC001ReliefToolingRevision", str(TOOLING_REVISION)),
        (
            "LowerC001ReliefDesignSignature",
            parameters["design_control"]["design_signature"]["sha256"],
        ),
        (
            "LowerC001ReliefState",
            "DISPOSABLE__REQUIRES_PRESERVATION_PHYSICAL_AND_VISUAL_PASS",
        ),
        (
            "LowerC001CoverLipEyeDesignSignature",
            parameters["cover_lip_interface"]["source_eye_design_signature_sha256"],
        ),
    ):
        assigned.append(
            toolkit.assign_typed_metadata_property(
                target, "App::PropertyString", name, "LowerC001Relief", value
            )
        )
    assigned.append(
        toolkit.assign_typed_metadata_property(
            target,
            "App::PropertyVector",
            "LowerC001ReliefApertureVertexV0",
            "LowerC001ReliefDatums",
            vector(context["App"], parameters["relief"]["vertex0_head_mm"]),
        )
    )
    for name, value in (
        ("LowerC001ReliefExclusionRadius", parameters["relief"]["exclusion_envelope_radius_mm"]),
        ("LowerC001ReliefNominalMaximumRetreat", parameters["relief"]["nominal_maximum_retreat_mm"]),
        ("LowerC001ReliefHardCapRetreat", parameters["relief"]["hard_cap_retreat_mm"]),
        ("LowerC001ReliefPreSpan", measurements["pre_relief_span_mm"]),
        ("LowerC001ReliefPostSpan", measurements["post_relief_span_mm"]),
        ("LowerC001CoverLipNominalReach", parameters["cover_lip_interface"]["nominal_in_plane_reach_mm"]),
        ("LowerC001CoverLipNominalOutwardCover", parameters["cover_lip_interface"]["nominal_outward_axial_cover_mm"]),
    ):
        assigned.append(
            toolkit.assign_typed_metadata_property(
                target, "App::PropertyLength", name, "LowerC001ReliefDimensions", float(value)
            )
        )
    assigned.append(
        toolkit.assign_typed_metadata_property(
            target,
            "App::PropertyFloat",
            "LowerC001ReliefRemovedVolume",
            "LowerC001ReliefDimensions",
            float(measurements["removed_volume_mm3"]),
        )
    )
    return assigned


def finalize_target(
    context: dict[str, Any], candidate: Any, construction: dict[str, Any]
) -> dict[str, Any]:
    trace = context["finalization_trace"]
    target = context["target"]
    target.Shape = candidate
    trace["target_assignment_performed"] = True
    metadata = attach_metadata(context, construction)
    trace["metadata_assignment_performed"] = True
    context["document"].recompute()
    trace["recompute_performed"] = True
    original = context["original"]
    if (
        target.Name != original["name"]
        or target.Label != original["label"]
        or target.TypeId != original["type_id"]
        or target.Placement != original["placement"]
    ):
        raise RuntimeError("target identity or placement changed")
    require_single_solid(target.Shape, "finalized lower_C001 relief target")
    residual = max(
        float(target.Shape.cut(candidate).Volume),
        float(candidate.cut(target.Shape).Volume),
    )
    if residual > float(
        context["parameters"]["relief"]["boolean_volume_epsilon_mm3"]
    ):
        raise RuntimeError("assigned target differs from constructed relief")
    for record in metadata:
        context["renderer"].assert_property_schema(
            target, record["property_type"], record["name"], record["group"]
        )
    physical = evaluate_measurements(
        context["parameters"], construction["measurements"]
    )
    if physical["status"] != "PASS":
        raise RuntimeError(json.dumps(physical, sort_keys=True))
    trace["final_assertions_performed"] = True
    return {
        "trace": dict(trace),
        "metadata_property_count": len(metadata),
        "shape_symmetric_difference_mm3": residual,
        "physical_gates": physical,
    }


def document_records(
    document: Any, renderer: Any, target_color: tuple[int, int, int]
) -> list[dict[str, Any]]:
    records = []
    for obj in document.Objects:
        if not hasattr(obj, "Shape") or obj.Shape.isNull():
            continue
        if obj.Name == TARGET_OBJECT:
            color = target_color
            deflection = 0.55
        elif "EYE" in obj.Name:
            color = (42, 152, 193)
            deflection = 0.75
        elif "EAR" in obj.Name:
            color = (176, 145, 99)
            deflection = 1.8
        elif "PANEL" in obj.Name:
            color = (224, 145, 54)
            deflection = 1.8
        else:
            color = (164, 169, 176)
            deflection = 1.8
        records.append(
            renderer.shape_record(
                obj.Shape,
                color,
                obj.Placement if hasattr(obj, "Placement") else None,
                deflection,
            )
        )
    return records


def render_review_pack(
    context: dict[str, Any], baseline_records: list[dict[str, Any]], construction: dict[str, Any]
) -> None:
    root, contract, renderer = context["root"], context["contract"], context["renderer"]
    candidate_records = document_records(context["document"], renderer, (37, 151, 190))
    fixed_views = {
        "front": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "rear": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
        "left": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        "right": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        "top": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
        "bottom": ((0.0, 0.0, 1.0), (0.0, -1.0, 0.0)),
    }
    for name, (direction, up) in fixed_views.items():
        renderer.render_side_by_side(
            root / contract["output"]["review_files"][name],
            baseline_records,
            candidate_records,
            direction,
            up,
        )
    extras = context["parameters"]["review_artifacts"]
    v0 = tuple(float(value) for value in context["parameters"]["relief"]["vertex0_head_mm"])
    axis_n = renderer.tuple3(construction["axis_n"])
    axis_u = renderer.tuple3(construction["axis_u"])
    renderer.render_side_by_side(
        root / extras["focused_exterior"], baseline_records, candidate_records,
        axis_n, axis_u, v0, 18.0,
    )
    renderer.render_side_by_side(
        root / extras["focused_interior"], baseline_records, candidate_records,
        tuple(-value for value in axis_n), axis_u, v0, 18.0,
    )
    overlay_records = [
        renderer.shape_record(context["original_shape"], (164, 169, 176), deflection=0.55),
        renderer.shape_record(construction["actual_removed"], (239, 151, 45), deflection=0.08),
        renderer.shape_record(construction["aperture_wire"], (40, 170, 105), deflection=0.05),
    ]
    pixels = renderer.render_panel(overlay_records, axis_n, axis_u, v0, 18.0)
    renderer.write_png(
        root / extras["relief_overlay"], renderer.IMAGE_WIDTH, renderer.IMAGE_HEIGHT, pixels
    )
    section_records = [
        renderer.shape_record(context["target"].Shape, (37, 151, 190), deflection=0.45),
        renderer.shape_record(construction["envelope"], (82, 177, 109), deflection=0.10),
        renderer.shape_record(construction["actual_removed"], (239, 151, 45), deflection=0.08),
    ]
    pixels = renderer.render_panel(
        section_records, renderer.tuple3(construction["axis_v"]), axis_n, v0, 18.0
    )
    renderer.write_png(
        root / extras["clearance_section"], renderer.IMAGE_WIDTH, renderer.IMAGE_HEIGHT, pixels
    )


def immutable_preflight(
    baseline_argument: Path,
    contract_argument: Path,
    *,
    require_new_output: bool = True,
) -> dict[str, Any]:
    root = repository_root(contract_argument)
    baseline = load_json(baseline_argument)
    contract = load_json(contract_argument)
    parameters = validate_contract_scope(contract)
    design = validate_design_control(root, contract, parameters)
    tooling = parameters["tooling_dependencies"]
    shared_validator_path = verify_pinned(
        root, tooling["shared_validator"], "shared V2 validator"
    )
    shared_validator = import_pinned(
        shared_validator_path,
        tooling["shared_validator"]["sha256"],
        "lower_c001_shared_v2_validator",
    )
    report = shared_validator.validate_files(
        baseline_argument,
        contract_argument,
        verify_files=True,
        require_new_output=require_new_output,
    )
    if report.get("status") != "PASS":
        raise RuntimeError(json.dumps(report, sort_keys=True))
    for name in (
        "shared_runner",
        "shared_preservation_module",
        "shared_preservation_comparator",
        "independent_physical_validator",
        "deterministic_test",
    ):
        verify_pinned(root, tooling[name], name)
    renderer = import_pinned(
        Path(__file__).with_name(RENDER_TOOLKIT_FILENAME),
        RENDER_TOOLKIT_SHA256,
        "lower_c001_review_renderer",
    )
    baseline_path = root / baseline["assembly"]["path"]
    if sha256_file(baseline_path) != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 hash mismatch")
    if contract.get("baseline_id") != baseline.get("baseline_id"):
        raise RuntimeError("baseline ID mismatch")
    output_dir = root / contract["output"]["directory"]
    candidate_path = root / contract["output"]["candidate_fcstd"]
    if require_new_output and (output_dir.exists() or candidate_path.exists()):
        raise RuntimeError(f"iteration output already exists: {output_dir}")
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    runtime_path = root / contract["runtime"]["manifest_path"]
    runtime = load_json(runtime_path)
    probe_path = verify_pinned(
        root,
        {"path": runtime["probe"]["script_path"], "sha256": runtime["probe"]["script_sha256"]},
        "runtime probe",
    )
    probe = import_pinned(probe_path, runtime["probe"]["script_sha256"], "lower_c001_runtime_probe")
    observed = probe.runtime_record()
    expected = {
        "freecad_version": runtime["freecad"]["version_record"],
        "freecad_program_version": runtime["freecad"]["program_version"],
        "occt_version": runtime["occt"]["version"],
        "python_version": runtime["python"]["version"],
        "platform_machine": runtime["platform"]["machine"],
    }
    if observed != expected:
        raise RuntimeError(f"approved runtime mismatch: {observed} != {expected}")
    document = App.openDocument(str(baseline_path))
    try:
        target = document.getObject(TARGET_OBJECT)
        if target is None or target.TypeId != "Part::Feature" or target.Shape.isNull():
            raise RuntimeError("canonical V34 lower_C001 target is missing/null/wrong type")
        if target.Placement != App.Placement():
            raise RuntimeError("lower_C001 target placement is not identity")
        original_shape = target.Shape.copy()
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
        "design": design,
        "shared_report": report,
        "runtime": observed,
        "baseline_path": baseline_path,
        "output_dir": output_dir,
        "candidate_path": candidate_path,
        "document": document,
        "target": target,
        "original_shape": original_shape,
        "original": original,
        "renderer": renderer,
        "App": App,
        "Part": Part,
        "io_trace": {"save_as_called": False, "document_save_called": False},
        "finalization_trace": {
            "target_assignment_performed": False,
            "metadata_assignment_performed": False,
            "recompute_performed": False,
            "final_assertions_performed": False,
        },
    }


def in_memory_finalization_report(context: dict[str, Any]) -> dict[str, Any]:
    candidate, construction = construct_relief(context)
    finalization = finalize_target(context, candidate, construction)
    return {
        "status": "IN_MEMORY_FINALIZATION_PASS",
        "iteration_id": ITERATION_ID,
        "design_id": DESIGN_ID,
        "design_signature_sha256": context["design"]["signature_sha256"],
        "runtime": context["runtime"],
        "measurements": construction["measurements"],
        **finalization["trace"],
        "save_as_called": context["io_trace"]["save_as_called"],
        "document_save_called": context["io_trace"]["document_save_called"],
        "candidate_exists": context["candidate_path"].exists(),
        "geometry_export_created": False,
        "output_exists": context["output_dir"].exists(),
    }


def generate_candidate(context: dict[str, Any]) -> None:
    baseline_records = document_records(
        context["document"], context["renderer"], (223, 137, 65)
    )
    context["output_dir"].mkdir(parents=True, exist_ok=False)
    context["candidate_path"].parent.mkdir(parents=True, exist_ok=True)
    context["document"].saveAs(str(context["candidate_path"]))
    context["io_trace"]["save_as_called"] = True
    print("STAGE 1/5 same-runtime no-op candidate saved", flush=True)
    candidate, construction = construct_relief(context)
    finalize_target(context, candidate, construction)
    print("STAGE 2/5 isolated lower_C001 relief finalized", flush=True)
    context["document"].save()
    context["io_trace"]["document_save_called"] = True
    print("STAGE 3/5 candidate saved", flush=True)
    render_review_pack(context, baseline_records, construction)
    print("STAGE 4/5 fixed whole-head and focused views rendered", flush=True)
    if sha256_file(context["baseline_path"]) != context["baseline"]["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 changed during generation")
    print("STAGE 5/5 canonical V34 remains hash-identical", flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    context = immutable_preflight(args.baseline, args.contract)
    try:
        if args.in_memory_finalization_preflight:
            print(json.dumps(in_memory_finalization_report(context), indent=2, sort_keys=True))
        else:
            generate_candidate(context)
        return 0
    finally:
        context["App"].closeDocument(context["document"].Name)


if __name__ == "__main__":
    raise SystemExit(main())
