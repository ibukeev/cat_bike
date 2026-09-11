#!/usr/bin/env python3
"""Independent read-only physical validation for the isolated lower-C001 relief."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sys
from pathlib import Path
from typing import Any, Sequence

import FreeCAD as App
import Part


ITERATION_ID = "lower-c001-aperture-vertex0-relief-v1"
TARGET_OBJECT = "FROZEN_RIGHT_LOWER_MAIN_V34"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--preservation-report", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
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


def vector(values: Sequence[float]) -> App.Vector:
    return App.Vector(*[float(value) for value in values])


def normalized(value: App.Vector, label: str) -> App.Vector:
    result = App.Vector(value)
    if result.Length <= 1.0e-12:
        raise RuntimeError(f"{label} has zero length")
    result.normalize()
    return result


def local_coordinates(
    point: App.Vector, origin: App.Vector, axes: Sequence[App.Vector]
) -> list[float]:
    delta = point - origin
    return [float(delta.dot(axis)) for axis in axes]


def planar_loop(
    points: Sequence[Sequence[float]],
    origin: App.Vector,
    axes: Sequence[App.Vector],
) -> list[App.Vector]:
    axis_u, axis_v, _axis_n = axes
    result = []
    for values in points:
        local = local_coordinates(vector(values), origin, axes)
        result.append(origin + axis_u * local[0] + axis_v * local[1])
    return result


def require_single_solid(shape: Any, label: str) -> None:
    if shape.isNull() or not shape.isValid() or not shape.isClosed() or len(shape.Solids) != 1:
        raise RuntimeError(
            f"{label}: valid={shape.isValid()} closed={shape.isClosed()} solids={len(shape.Solids)}"
        )


def deep_bop_defect_counts(shape: Any) -> dict[str, int]:
    """Normalize deep-BOP records, including FreeCAD's ValueError form."""
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


def capsule_envelope(aperture: Sequence[App.Vector], radius: float) -> Any:
    pieces = [Part.makeSphere(radius, point) for point in aperture]
    for index, first in enumerate(aperture):
        delta = aperture[(index + 1) % len(aperture)] - first
        pieces.append(Part.makeCylinder(radius, float(delta.Length), first, delta))
    shape = pieces[0].multiFuse(pieces[1:]).removeSplitter()
    require_single_solid(shape, "aperture exclusion envelope")
    return shape


def opening_prism(
    opening: Sequence[App.Vector], axis_n: App.Vector, depth: float = 200.0
) -> Any:
    start = [point - axis_n * (depth / 2.0) for point in opening]
    face = Part.Face(Part.makePolygon([*start, start[0]]))
    shape = face.extrude(axis_n * depth)
    require_single_solid(shape, "eye-opening projection prism")
    return shape


def proposed_cover_lip_envelope(
    parameters: dict[str, Any],
    opening: Sequence[App.Vector],
    axes: Sequence[App.Vector],
) -> dict[str, Any]:
    """Independently reconstruct the pinned adverse-tolerance lip envelope."""
    spec = parameters["cover_lip_interface"]
    if spec["source_eye_design_id"] != "right-eye-split-service-cassette-D":
        raise RuntimeError("cover-lip source eye design changed")
    if spec["source_eye_design_signature_sha256"] != (
        "362d5bf06ab5dbf94a087dc0a40977d8277e9281a358d98a25a8043a1865ce73"
    ):
        raise RuntimeError("cover-lip source eye signature changed")
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
        radial = normalized(radial, "cover-lip source outer radial")
        outer_front.append(point - radial * inset)
    if list(spec["source_outer_edge_vertex_indices"]) != [0, 3]:
        raise RuntimeError("cover-lip source edge changed")
    tangent = normalized(outer_front[3] - outer_front[0], "cover-lip tangent")
    outward = normalized(axes[2].cross(tangent), "cover-lip outward")
    tolerance = float(spec["adverse_dimensional_tolerance_mm"])
    effective_reach = float(spec["nominal_in_plane_reach_mm"]) - tolerance
    effective_outward = float(spec["nominal_outward_axial_cover_mm"]) - tolerance
    if float(spec["nominal_in_plane_reach_mm"]) + 1.0e-12 < float(
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
    tangent_end = float(spec["tangent_start_mm"]) + float(spec["tangent_length_mm"]) - tolerance
    if tangent_end <= tangent_start:
        raise RuntimeError("cover-lip tangent interval collapsed")
    start = outer_front[0] + tangent * tangent_start
    end = outer_front[0] + tangent * tangent_end
    loop = [start, end, end + outward * effective_reach, start + outward * effective_reach]
    face = Part.Face(Part.makePolygon([*loop, loop[0]]))
    front = face.copy()
    front.translate(axes[2] * -effective_outward)
    volume = front.extrude(axes[2] * coverage_depth)
    require_single_solid(volume, "proposed lower-V0 cover-lip envelope")
    return {
        "volume": volume,
        "effective_reach_mm": effective_reach,
        "effective_outward_cover_mm": effective_outward,
    }


def placement_record(value: App.Placement) -> dict[str, Any]:
    return {
        "base": [float(value.Base.x), float(value.Base.y), float(value.Base.z)],
        "rotation_q": [float(item) for item in value.Rotation.Q],
    }


def runtime_record() -> dict[str, Any]:
    version = list(App.Version())
    return {
        "freecad_version": version,
        "freecad_program_version": f"{version[0]}.{version[1]}R{version[3]}",
        "occt_version": str(Part.OCC_VERSION),
        "python_version": platform.python_version(),
        "platform_machine": platform.machine(),
    }


def exact_authorized_removal_from_candidate(
    base_shape: Any,
    candidate_shape: Any,
    expected_removed: Any,
    boolean_epsilon: float,
) -> tuple[Any, dict[str, float]]:
    """Validate the persisted result, avoiding unstable base-minus-candidate BOP."""
    expected_candidate = base_shape.cut(expected_removed).removeSplitter()
    require_single_solid(expected_candidate, "expected relieved lower-C001")
    candidate_minus_expected = candidate_shape.cut(expected_candidate).removeSplitter()
    expected_minus_candidate = expected_candidate.cut(candidate_shape).removeSplitter()
    measurements = {
        "candidate_minus_expected_candidate_mm3": float(
            candidate_minus_expected.Volume
        ),
        "expected_candidate_minus_candidate_mm3": float(
            expected_minus_candidate.Volume
        ),
    }
    if max(measurements.values()) > boolean_epsilon:
        raise RuntimeError(
            "persisted lower-C001 differs from the exact authorized relieved result: "
            + json.dumps(measurements, sort_keys=True)
        )
    return expected_removed, measurements


def evaluate_gates(
    values: dict[str, Any], parameters: dict[str, Any], preservation_ok: bool
) -> dict[str, Any]:
    relief = parameters["relief"]
    lip = parameters["cover_lip_interface"]
    eps = float(relief["boolean_volume_epsilon_mm3"])
    tol = float(relief["measurement_tolerance_mm"])
    gates = {
        "R01_PRESERVATION_PASS": bool(preservation_ok),
        "R02_APERTURE_COORDINATES_EXACT": values["aperture_coordinates_sha256"]
        == relief["immutable_aperture_coordinates_sha256"],
        "R03_BASELINE_SPAN_PINNED": abs(
            float(values["pre_relief_span_mm"])
            - float(relief["approved_pre_relief_span_mm"])
        ) <= tol,
        "R04_SINGLE_CONNECTED_REMOVAL": int(values["removed_solid_count"]) == 1,
        "R05_SUBTRACTION_ONLY": float(values["added_volume_mm3"]) <= eps,
        "R06_EXACT_ENVELOPE_INTERSECTION": max(
            float(values["expected_minus_actual_mm3"]),
            float(values["actual_minus_expected_mm3"]),
        ) <= eps,
        "R07_POST_SPAN_AT_LEAST_1MM": float(values["post_relief_span_mm"])
        >= float(relief["required_post_relief_span_mm"]) - tol,
        "R08_RETREAT_WITHIN_HARD_CAP": float(values["maximum_retreat_mm"])
        <= float(relief["hard_cap_retreat_mm"]) + 1.0e-9,
        "R09_EXTERIOR_RELIEF_FULLY_COVERED_BY_PINNED_LIP": (
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
        "R10_VALID_CLOSED_SINGLE_TARGET": bool(values["candidate_valid"])
        and bool(values["candidate_closed"])
        and int(values["candidate_solid_count"]) == 1
        and not values["new_deep_bop_defects"]
        and not values["removed_deep_bop_defects"],
        "R11_NONZERO_BOUNDED_RELIEF": float(values["removed_volume_mm3"]) > eps,
        "R12_TARGET_IDENTITY_AND_PLACEMENT": bool(values["target_identity_preserved"]),
        "R13_METADATA_EXACT": bool(values["metadata_exact"]),
        "R14_REVIEW_PACK_COMPLETE": bool(values["review_pack_complete"]),
    }
    failed = [name for name, passed in gates.items() if not passed]
    return {
        "status": "PASS" if not failed else "FAIL",
        "gates": gates,
        "failed_gates": failed,
    }


def preservation_gate(
    report: dict[str, Any], contract: dict[str, Any], candidate_sha256: str
) -> tuple[bool, dict[str, Any]]:
    protected = report.get("shape_identity", {}).get("protected", {})
    ok = (
        report.get("status") == "PASS__READY_FOR_FIXED_VIEW_REVIEW"
        and report.get("iteration_id") == ITERATION_ID
        and report.get("target_object") == TARGET_OBJECT
        and report.get("candidate", {}).get("sha256") == candidate_sha256
        and report.get("protected_differences") == {}
        and report.get("added_objects") == []
        and report.get("missing_objects") == []
        and report.get("target_errors") == []
        and protected.get("status") == "PASS"
        and contract.get("target_object") == TARGET_OBJECT
    )
    return ok, {
        "status": report.get("status"),
        "protected_status": protected.get("status"),
        "protected_checked_count": protected.get("checked_count"),
        "candidate_sha256": report.get("candidate", {}).get("sha256"),
    }


def measure(
    root: Path,
    baseline: dict[str, Any],
    contract: dict[str, Any],
    baseline_document: Any,
    candidate_document: Any,
) -> dict[str, Any]:
    parameters = contract["allowed_mutations"][0]["parameters"]
    relief = parameters["relief"]
    base_target = baseline_document.getObject(TARGET_OBJECT)
    candidate_target = candidate_document.getObject(TARGET_OBJECT)
    if base_target is None or candidate_target is None:
        raise RuntimeError("lower-C001 target missing")
    if base_target.TypeId != "Part::Feature" or candidate_target.TypeId != "Part::Feature":
        raise RuntimeError("lower-C001 target type changed")
    base_shape = base_target.Shape.copy()
    candidate_shape = candidate_target.Shape.copy()
    lcs = parameters["aperture_lcs"]
    origin = vector(lcs["origin_mm"])
    axes = (
        normalized(vector(lcs["u"]), "u"),
        normalized(vector(lcs["v"]), "v"),
        normalized(vector(lcs["inward_n"]), "n"),
    )
    aperture = planar_loop(lcs["visible_aperture_mm"], origin, axes)
    opening = planar_loop(parameters["shell_opening_boundary_mm"], origin, axes)
    wire = Part.makePolygon([*aperture, aperture[0]])
    envelope = capsule_envelope(aperture, float(relief["exclusion_envelope_radius_mm"]))
    expected = base_shape.common(envelope).removeSplitter()
    added = candidate_shape.cut(base_shape).removeSplitter()
    require_single_solid(expected, "expected V0 removal")
    removed, equivalence = exact_authorized_removal_from_candidate(
        base_shape,
        candidate_shape,
        expected,
        float(relief["boolean_volume_epsilon_mm3"]),
    )
    lip = proposed_cover_lip_envelope(parameters, opening, axes)
    face_index = int(parameters["cover_lip_interface"]["baseline_exterior_face_index"])
    if face_index < 1 or face_index > len(base_shape.Faces):
        raise RuntimeError("pinned exterior face index is unavailable")
    exterior_patch = base_shape.Faces[face_index - 1].common(removed).removeSplitter()
    if exterior_patch.isNull():
        raise RuntimeError("pinned Face321 exterior relief patch is null")
    covered_patch = exterior_patch.common(lip["volume"])
    uncovered_patch = exterior_patch.cut(lip["volume"])
    baseline_deep_defects = deep_bop_defect_counts(base_shape)
    candidate_deep_defects = deep_bop_defect_counts(candidate_shape)
    removed_deep_defects = deep_bop_defect_counts(removed)
    new_deep_defects = added_deep_bop_defects(
        baseline_deep_defects, candidate_deep_defects
    )
    review_paths = [root / path for path in contract["output"]["review_files"].values()]
    review_paths.extend(
        root / path for path in parameters["review_artifacts"].values()
    )
    metadata_expected = {
        "LowerC001ReliefDesignId": parameters["design_control"]["design_id"],
        "LowerC001ReliefIterationId": ITERATION_ID,
        "LowerC001ReliefToolingRevision": str(parameters["design_control"]["tooling_revision"]),
        "LowerC001ReliefDesignSignature": parameters["design_control"]["design_signature"]["sha256"],
        "LowerC001CoverLipEyeDesignSignature": parameters["cover_lip_interface"]["source_eye_design_signature_sha256"],
    }
    metadata_exact = all(
        name in candidate_target.PropertiesList and str(getattr(candidate_target, name)) == value
        for name, value in metadata_expected.items()
    )
    pre_span = float(wire.distToShape(base_shape)[0])
    return {
        "aperture_coordinates_sha256": canonical_json_sha256(lcs["visible_aperture_mm"]),
        "pre_relief_span_mm": pre_span,
        "post_relief_span_mm": float(wire.distToShape(candidate_shape)[0]),
        "maximum_retreat_mm": float(relief["exclusion_envelope_radius_mm"]) - pre_span,
        "removed_volume_mm3": float(removed.Volume),
        "added_volume_mm3": float(added.Volume),
        "expected_minus_actual_mm3": float(
            equivalence["expected_candidate_minus_candidate_mm3"]
        ),
        "actual_minus_expected_mm3": float(
            equivalence["candidate_minus_expected_candidate_mm3"]
        ),
        **equivalence,
        "removed_outside_eye_opening_mm3": float(
            removed.cut(opening_prism(opening, axes[2])).Volume
        ),
        "exterior_patch_area_mm2": float(exterior_patch.Area),
        "covered_exterior_patch_area_mm2": float(covered_patch.Area),
        "uncovered_exterior_patch_area_mm2": float(uncovered_patch.Area),
        "cover_area_balance_residual_mm2": float(
            exterior_patch.Area - covered_patch.Area - uncovered_patch.Area
        ),
        "cover_lip_effective_reach_mm": float(lip["effective_reach_mm"]),
        "cover_lip_effective_outward_cover_mm": float(lip["effective_outward_cover_mm"]),
        "cover_lip_minimum_printed_wall_mm": float(
            parameters["cover_lip_interface"]["minimum_printed_wall_mm"]
        ),
        "removed_solid_count": len(removed.Solids),
        "candidate_solid_count": len(candidate_shape.Solids),
        "candidate_valid": bool(candidate_shape.isValid()),
        "candidate_closed": bool(candidate_shape.isClosed()),
        "baseline_deep_bop_defects": baseline_deep_defects,
        "candidate_deep_bop_defects": candidate_deep_defects,
        "new_deep_bop_defects": new_deep_defects,
        "removed_deep_bop_defects": removed_deep_defects,
        "target_identity_preserved": (
            base_target.Name == candidate_target.Name
            and base_target.Label == candidate_target.Label
            and base_target.TypeId == candidate_target.TypeId
            and placement_record(base_target.Placement) == placement_record(candidate_target.Placement)
        ),
        "metadata_exact": metadata_exact,
        "review_pack_complete": all(path.is_file() for path in review_paths),
        "review_files": [str(path.relative_to(root)) for path in review_paths],
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = repository_root(args.contract)
    baseline = load_json(args.baseline)
    contract = load_json(args.contract)
    if contract.get("iteration_id") != ITERATION_ID:
        raise RuntimeError("iteration ID mismatch")
    output_dir = root / contract["output"]["directory"]
    expected_report = output_dir / "relief-validation.json"
    report_path = args.report if args.report.is_absolute() else root / args.report
    if report_path.resolve() != expected_report.resolve():
        raise RuntimeError(f"report must be exactly {expected_report}")
    if report_path.exists():
        raise RuntimeError("validation report already exists; retry is forbidden")
    baseline_path = root / baseline["assembly"]["path"]
    candidate_path = root / contract["output"]["candidate_fcstd"]
    preservation_path = (
        args.preservation_report
        if args.preservation_report.is_absolute()
        else root / args.preservation_report
    )
    for label, path in (
        ("baseline", baseline_path),
        ("candidate", candidate_path),
        ("preservation report", preservation_path),
    ):
        if not path.is_file():
            raise RuntimeError(f"{label} missing: {path}")
    baseline_sha256 = sha256_file(baseline_path)
    if baseline_sha256 != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 hash mismatch")
    candidate_sha256 = sha256_file(candidate_path)
    preservation = load_json(preservation_path)
    preservation_ok, preservation_summary = preservation_gate(
        preservation, contract, candidate_sha256
    )
    runtime_manifest = load_json(root / contract["runtime"]["manifest_path"])
    expected_runtime = {
        "freecad_version": runtime_manifest["freecad"]["version_record"],
        "freecad_program_version": runtime_manifest["freecad"]["program_version"],
        "occt_version": runtime_manifest["occt"]["version"],
        "python_version": runtime_manifest["python"]["version"],
        "platform_machine": runtime_manifest["platform"]["machine"],
    }
    observed_runtime = runtime_record()
    if observed_runtime != expected_runtime:
        raise RuntimeError(f"runtime mismatch: {observed_runtime} != {expected_runtime}")
    baseline_document = App.openDocument(str(baseline_path))
    candidate_document = App.openDocument(str(candidate_path))
    try:
        values = measure(
            root, baseline, contract, baseline_document, candidate_document
        )
    finally:
        App.closeDocument(candidate_document.Name)
        App.closeDocument(baseline_document.Name)
    result = evaluate_gates(
        values, contract["allowed_mutations"][0]["parameters"], preservation_ok
    )
    report = {
        "schema_version": "2.0",
        "iteration_id": ITERATION_ID,
        "status": (
            "RELIEF_VALIDATION_PASS__READY_FOR_HUMAN_VISUAL_REVIEW"
            if result["status"] == "PASS"
            else "RELIEF_VALIDATION_FAIL__CANDIDATE_UNCHANGED"
        ),
        "baseline": {"path": baseline["assembly"]["path"], "sha256": baseline_sha256},
        "candidate": {"path": contract["output"]["candidate_fcstd"], "sha256": candidate_sha256},
        "preservation": preservation_summary,
        "runtime": observed_runtime,
        "measurements": values,
        **result,
        "candidate_modified": False,
        "retry_allowed": False,
        "downstream_holds_active": True,
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
