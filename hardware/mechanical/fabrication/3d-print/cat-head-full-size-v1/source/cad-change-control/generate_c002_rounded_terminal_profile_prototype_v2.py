#!/usr/bin/env python3
"""Generate the one authorized C002 Route 2 V2 review candidate.

This wrapper keeps the V1 Route 2 construction implementation hash-pinned,
but replaces V1's raw face-list lookups with fail-closed mapped-subelement and
complete-geometric-signature resolution.  Runtime, baseline, evidence, shared
V2 tooling, rail-frame, and anchor checks all complete before the output
directory is created or ``saveAs`` is called.

``--preflight-only`` performs those immutable checks and exits without creating
an output directory, saving a document, or constructing candidate geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Sequence

import FreeCAD as App
import Part


ITERATION_ID = "c002-rounded-terminal-profile-prototype-v2"
TARGET_OBJECT = "RETAINED_RIGHT_UPPER_C002_V34"
PROTECTED_ROOT_OBJECT = "RETAINED_RIGHT_UPPER_C042_V34"
AREA_TOLERANCE_MM2 = 1.0e-6
APPROVED_AREA_DECIMALS = 2
POSITION_TOLERANCE_MM = 1.0e-3
NORMAL_VECTOR_TOLERANCE = 1.0e-5
ORTHOGONALITY_TOLERANCE = 1.0e-9


class RuntimePreconditionError(RuntimeError):
    """The loaded FreeCAD/OCCT runtime differs from the contract pin."""


class AnchorResolutionError(RuntimeError):
    """A required mapped or signature-resolved baseline anchor is invalid."""


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--preflight-only", action="store_true")
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


def vector(values: Sequence[float]) -> App.Vector:
    return App.Vector(float(values[0]), float(values[1]), float(values[2]))


def normalized(value: App.Vector, label: str) -> App.Vector:
    result = App.Vector(value)
    if result.Length <= 1.0e-12:
        raise RuntimeError(f"{label} has zero length")
    result.normalize()
    return result


def vector_values(value: App.Vector) -> list[float]:
    return [float(value.x), float(value.y), float(value.z)]


def import_pinned_module(path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load pinned module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_pinned_dependency(root: Path, item: dict[str, Any], label: str) -> Path:
    path = root / str(item["path"])
    expected = str(item["sha256"])
    actual = sha256_file(path) if path.is_file() else None
    if actual != expected:
        raise RuntimeError(
            json.dumps(
                {
                    "error": "pinned tooling dependency mismatch",
                    "dependency": label,
                    "path": str(item["path"]),
                    "actual_sha256": actual,
                    "expected_sha256": expected,
                },
                sort_keys=True,
            )
        )
    return path


def verify_runtime(
    root: Path,
    runtime_reference: dict[str, Any],
) -> tuple[dict[str, Any], Any]:
    manifest_path = root / str(runtime_reference["manifest_path"])
    expected_manifest_hash = str(runtime_reference["manifest_sha256"])
    actual_manifest_hash = sha256_file(manifest_path) if manifest_path.is_file() else None
    if actual_manifest_hash != expected_manifest_hash:
        raise RuntimePreconditionError(
            json.dumps(
                {
                    "error": "approved runtime manifest mismatch before generation",
                    "runtime_manifest": str(runtime_reference["manifest_path"]),
                    "actual_sha256": actual_manifest_hash,
                    "expected_sha256": expected_manifest_hash,
                    "output_created": False,
                    "geometry_construction_started": False,
                },
                sort_keys=True,
            )
        )
    manifest = load_json(manifest_path)
    probe_path = verify_pinned_dependency(
        root,
        {
            "path": manifest["probe"]["script_path"],
            "sha256": manifest["probe"]["script_sha256"],
        },
        "shared FreeCAD runtime probe",
    )
    probe = import_pinned_module(probe_path, "cat_head_shared_runtime_probe_v2")
    actual = probe.runtime_record()
    expected = {
        "freecad_version": manifest["freecad"]["version_record"],
        "freecad_program_version": manifest["freecad"]["program_version"],
        "occt_version": manifest["occt"]["version"],
        "python_version": manifest["python"]["version"],
        "platform_machine": manifest["platform"]["machine"],
    }
    if actual != expected:
        raise RuntimePreconditionError(
            json.dumps(
                {
                    "error": "FreeCAD runtime mismatch before generation",
                    "actual_runtime": actual,
                    "expected_runtime": expected,
                    "output_created": False,
                    "geometry_construction_started": False,
                },
                sort_keys=True,
            )
        )
    return actual, probe


def frame_from_parameters(
    parameters: dict[str, Any],
) -> tuple[App.Vector, App.Vector, App.Vector, App.Vector]:
    frame = parameters["rail_frame"]
    origin = vector(frame["origin_head_mm"])
    axis_t = normalized(vector(frame["t_axis"]), "t axis")
    axis_u = normalized(vector(frame["u_axis"]), "u axis")
    axis_v = normalized(vector(frame["v_axis"]), "v axis")
    if (
        abs(axis_u.dot(axis_v)) > ORTHOGONALITY_TOLERANCE
        or abs(axis_u.dot(axis_t)) > ORTHOGONALITY_TOLERANCE
        or abs(axis_v.dot(axis_t)) > ORTHOGONALITY_TOLERANCE
    ):
        raise RuntimeError("rail frame is not orthogonal")
    if (axis_u.cross(axis_v) - axis_t).Length > ORTHOGONALITY_TOLERANCE:
        raise RuntimeError("rail frame handedness differs from u cross v = t")
    return origin, axis_u, axis_v, axis_t


def face_normal(face: Part.Face) -> App.Vector:
    parameter_range = face.ParameterRange
    u_value = (float(parameter_range[0]) + float(parameter_range[1])) / 2.0
    v_value = (float(parameter_range[2]) + float(parameter_range[3])) / 2.0
    return normalized(face.normalAt(u_value, v_value), "face normal")


def face_record(
    face: Part.Face,
    identifier: str,
    resolution: str,
    origin: App.Vector,
    axis_t: App.Vector,
    offset_along_minus_t_mm: float,
) -> dict[str, Any]:
    normal = face_normal(face)
    centroid = face.CenterOfMass
    derived_plane_point = centroid - axis_t * offset_along_minus_t_mm
    surface_type = str(
        getattr(face.Surface, "TypeId", type(face.Surface).__name__)
    )
    return {
        "face_identifier": identifier,
        "resolution": resolution,
        "surface_type": surface_type,
        "is_planar": "Plane" in surface_type,
        "area_mm2": float(face.Area),
        "area_mm2_at_approved_precision": round(
            float(face.Area), APPROVED_AREA_DECIMALS
        ),
        "centroid_head_mm": vector_values(centroid),
        "normal": vector_values(normal),
        "normal_dot_plus_t": float(normal.dot(axis_t)),
        "normal_dot_minus_t": float(normal.dot(-axis_t)),
        "face10_offset_plane_point_head_mm": vector_values(derived_plane_point),
        "face10_offset_plane_residual_to_origin_mm": abs(
            float((origin - derived_plane_point).dot(axis_t))
        ),
        "centroid_residual_to_origin_mm": float((centroid - origin).Length),
    }


def expected_anchor_record(
    anchor_name: str,
    parameters: dict[str, Any],
    origin: App.Vector,
    axis_t: App.Vector,
) -> dict[str, Any]:
    anchors = parameters["anchors"]
    if anchor_name == "Face10":
        return {
            "face_identifier": f"{TARGET_OBJECT}.Face10",
            "surface_type": "planar",
            "area_mm2": float(anchors["face10_expected_area_mm2"]),
            "normal": vector_values(axis_t),
            "offset_along_minus_t_mm": float(
                anchors["face10_offset_along_minus_t_mm"]
            ),
            "offset_plane_coincident_point_head_mm": vector_values(origin),
            "tolerances": {
                "area_mm2": AREA_TOLERANCE_MM2,
                "approved_area_decimals": APPROVED_AREA_DECIMALS,
                "position_mm": POSITION_TOLERANCE_MM,
                "normal_vector": NORMAL_VECTOR_TOLERANCE,
            },
        }
    if anchor_name == "Face164":
        return {
            "face_identifier": f"{TARGET_OBJECT}.Face164",
            "role": "corroborating current-cavity witness only",
            "surface_type": "planar",
            "area_mm2": float(anchors["face164_expected_area_mm2"]),
            "centroid_head_mm": vector_values(origin),
            "normal": vector_values(-axis_t),
            "tolerances": {
                "area_mm2": AREA_TOLERANCE_MM2,
                "approved_area_decimals": APPROVED_AREA_DECIMALS,
                "position_mm": POSITION_TOLERANCE_MM,
                "normal_vector": NORMAL_VECTOR_TOLERANCE,
            },
        }
    raise ValueError(f"unsupported anchor {anchor_name}")


def face_matches(
    record: dict[str, Any],
    expected: dict[str, Any],
    anchor_name: str,
) -> bool:
    actual_normal = vector(record["normal"])
    expected_normal = vector(expected["normal"])
    if not record["is_planar"]:
        return False
    if (
        abs(
            float(record["area_mm2_at_approved_precision"])
            - float(expected["area_mm2"])
        )
        > AREA_TOLERANCE_MM2
    ):
        return False
    if (actual_normal - expected_normal).Length > NORMAL_VECTOR_TOLERANCE:
        return False
    if anchor_name == "Face10":
        return (
            float(record["face10_offset_plane_residual_to_origin_mm"])
            <= POSITION_TOLERANCE_MM
        )
    return float(record["centroid_residual_to_origin_mm"]) <= POSITION_TOLERANCE_MM


def mapped_face_candidates(target: Any, anchor_name: str) -> list[tuple[str, Part.Face]]:
    candidates: list[tuple[str, Part.Face]] = []
    attempts = (
        ("FreeCAD.DocumentObject.getSubObject", lambda: target.getSubObject(anchor_name)),
        ("FreeCAD.TopoShape.getElement", lambda: target.Shape.getElement(anchor_name)),
    )
    for method, resolver in attempts:
        try:
            candidate = resolver()
        except (AttributeError, IndexError, KeyError, RuntimeError, TypeError):
            continue
        if isinstance(candidate, (tuple, list)):
            candidate = next(
                (
                    item
                    for item in candidate
                    if getattr(item, "ShapeType", None) == "Face"
                ),
                None,
            )
        if candidate is None or getattr(candidate, "ShapeType", None) != "Face":
            continue
        if any(candidate.isSame(existing) for _, existing in candidates):
            continue
        candidates.append((method, candidate))
    return candidates


def mismatch_score(
    record: dict[str, Any],
    expected: dict[str, Any],
    anchor_name: str,
) -> float:
    normal_error = (vector(record["normal"]) - vector(expected["normal"])).Length
    area_error = abs(
        float(record["area_mm2_at_approved_precision"])
        - float(expected["area_mm2"])
    )
    position_error = float(
        record[
            "face10_offset_plane_residual_to_origin_mm"
            if anchor_name == "Face10"
            else "centroid_residual_to_origin_mm"
        ]
    )
    planar_penalty = 0.0 if record["is_planar"] else 1.0e6
    return planar_penalty + area_error + normal_error * 1000.0 + position_error


def resolve_anchor(
    target: Any,
    anchor_name: str,
    parameters: dict[str, Any],
    origin: App.Vector,
    axis_t: App.Vector,
    runtime_record: dict[str, Any],
) -> tuple[Part.Face, dict[str, Any]]:
    expected = expected_anchor_record(anchor_name, parameters, origin, axis_t)
    offset = float(parameters["anchors"]["face10_offset_along_minus_t_mm"])
    mapped_records: list[dict[str, Any]] = []
    for method, candidate in mapped_face_candidates(target, anchor_name):
        record = face_record(
            candidate,
            f"{TARGET_OBJECT}.{anchor_name}",
            method,
            origin,
            axis_t,
            offset,
        )
        mapped_records.append(record)
        if face_matches(record, expected, anchor_name):
            return candidate, {"expected": expected, "actual": record}

    scanned: list[tuple[Part.Face, dict[str, Any]]] = []
    signature_matches: list[tuple[Part.Face, dict[str, Any]]] = []
    for ordinal, candidate in enumerate(target.Shape.Faces, start=1):
        record = face_record(
            candidate,
            f"{TARGET_OBJECT}.signature-scan-face-{ordinal}",
            "complete approved geometric signature",
            origin,
            axis_t,
            offset,
        )
        scanned.append((candidate, record))
        if face_matches(record, expected, anchor_name):
            signature_matches.append((candidate, record))
    if len(signature_matches) == 1:
        candidate, record = signature_matches[0]
        return candidate, {"expected": expected, "actual": record}

    closest = sorted(
        (record for _, record in scanned),
        key=lambda record: mismatch_score(record, expected, anchor_name),
    )[:5]
    raise AnchorResolutionError(
        json.dumps(
            {
                "error": "approved FreeCAD anchor did not resolve uniquely",
                "anchor": f"{TARGET_OBJECT}.{anchor_name}",
                "runtime": runtime_record,
                "expected": expected,
                "mapped_actuals": mapped_records,
                "signature_match_count": len(signature_matches),
                "closest_actuals": closest,
                "output_created": False,
                "geometry_construction_started": False,
            },
            sort_keys=True,
        )
    )


def resolve_c002_anchors(
    target: Any,
    parameters: dict[str, Any],
    origin: App.Vector,
    axis_t: App.Vector,
    runtime_record: dict[str, Any],
) -> dict[str, Any]:
    face10, face10_record = resolve_anchor(
        target,
        "Face10",
        parameters,
        origin,
        axis_t,
        runtime_record,
    )
    face164, face164_record = resolve_anchor(
        target,
        "Face164",
        parameters,
        origin,
        axis_t,
        runtime_record,
    )
    face10_plane_point = face10.CenterOfMass - axis_t * float(
        parameters["anchors"]["face10_offset_along_minus_t_mm"]
    )
    witness_residual = abs(float((face164.CenterOfMass - face10_plane_point).dot(axis_t)))
    if witness_residual > POSITION_TOLERANCE_MM:
        raise AnchorResolutionError(
            json.dumps(
                {
                    "error": "Face164 witness is not coincident with the Face10 offset plane",
                    "runtime": runtime_record,
                    "expected": {
                        "plane_coincidence_residual_mm": 0.0,
                        "position_tolerance_mm": POSITION_TOLERANCE_MM,
                    },
                    "actual": {
                        "face10": face10_record["actual"],
                        "face164": face164_record["actual"],
                        "plane_coincidence_residual_mm": witness_residual,
                    },
                    "output_created": False,
                    "geometry_construction_started": False,
                },
                sort_keys=True,
            )
        )
    return {
        "face10": face10,
        "face164": face164,
        "records": {
            "primary_termination_datum": face10_record,
            "corroborating_current_cavity_witness": face164_record,
            "plane_coincidence_residual_mm": witness_residual,
        },
    }


def validate_contract_scope(contract: dict[str, Any]) -> dict[str, Any]:
    if contract.get("iteration_id") != ITERATION_ID:
        raise RuntimeError("iteration ID mismatch")
    if contract.get("target_object") != TARGET_OBJECT:
        raise RuntimeError("target object mismatch")
    mutations = contract.get("allowed_mutations", [])
    if len(mutations) != 1 or mutations[0].get("kind") != "replace_geometry":
        raise RuntimeError("generator requires exactly one replace_geometry mutation")
    if mutations[0].get("object") != TARGET_OBJECT:
        raise RuntimeError("mutation object mismatch")
    return mutations[0]["parameters"]


def immutable_preflight(
    baseline_argument: Path,
    contract_argument: Path,
) -> dict[str, Any]:
    root = repository_root(contract_argument)
    baseline = load_json(baseline_argument)
    contract = load_json(contract_argument)
    parameters = validate_contract_scope(contract)

    tooling = parameters["tooling_dependencies"]
    runtime_record, _ = verify_runtime(root, contract["runtime"])
    for key in (
        "shared_validator",
        "shared_runner",
        "shared_preservation_module",
        "shared_preservation_comparator",
    ):
        verify_pinned_dependency(root, tooling[key], key)
    geometry_path = verify_pinned_dependency(
        root,
        tooling["route_2_geometry_implementation"],
        "hash-pinned V1 Route 2 geometry implementation",
    )
    geometry = import_pinned_module(geometry_path, "c002_route_2_geometry_v1_pinned")

    evidence_spec = parameters["route_2_evidence"]
    evidence_path = root / evidence_spec["path"]
    actual_evidence_hash = sha256_file(evidence_path)
    if actual_evidence_hash != evidence_spec["sha256"]:
        raise RuntimeError("Route 2 evidence hash mismatch")
    evidence = load_json(evidence_path)
    geometry.verify_route_2_parameters(parameters, evidence)

    interface_spec = parameters["interface_reference"]
    interface_path = root / interface_spec["path"]
    if sha256_file(interface_path) != interface_spec["sha256"]:
        raise RuntimeError("frozen shell/aluminum interface hash mismatch")

    baseline_path = root / baseline["assembly"]["path"]
    actual_baseline_hash = sha256_file(baseline_path)
    if actual_baseline_hash != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 hash mismatch")
    if baseline.get("baseline_id") != contract.get("baseline_id"):
        raise RuntimeError("contract baseline ID differs from baseline manifest")

    output_dir = root / contract["output"]["directory"]
    candidate_path = root / contract["output"]["candidate_fcstd"]
    if output_dir.exists():
        raise RuntimeError(f"V2 output already exists and is quarantined: {output_dir}")

    origin, axis_u, axis_v, axis_t = frame_from_parameters(parameters)
    document = App.openDocument(str(baseline_path))
    try:
        target = document.getObject(TARGET_OBJECT)
        protected_root = document.getObject(PROTECTED_ROOT_OBJECT)
        if target is None or protected_root is None:
            raise RuntimeError("canonical V34 lacks C002 or protected C042")
        if target.TypeId != "Part::Feature":
            raise RuntimeError(f"unexpected target type {target.TypeId}")
        if target.Placement != App.Placement():
            raise RuntimeError("target placement is not the approved identity placement")
        anchors = resolve_c002_anchors(
            target,
            parameters,
            origin,
            axis_t,
            runtime_record,
        )
        original_shape = target.Shape.copy()
        original_name = target.Name
        original_label = target.Label
        original_placement = App.Placement(target.Placement)
        if sha256_file(baseline_path) != baseline["assembly"]["sha256"]:
            raise RuntimeError("canonical V34 changed during immutable preflight")
    except Exception:
        App.closeDocument(document.Name)
        raise

    return {
        "root": root,
        "baseline": baseline,
        "contract": contract,
        "parameters": parameters,
        "runtime": runtime_record,
        "geometry": geometry,
        "baseline_path": baseline_path,
        "output_dir": output_dir,
        "candidate_path": candidate_path,
        "document": document,
        "target": target,
        "protected_root": protected_root,
        "original_shape": original_shape,
        "original_name": original_name,
        "original_label": original_label,
        "original_placement": original_placement,
        "origin": origin,
        "axis_u": axis_u,
        "axis_v": axis_v,
        "axis_t": axis_t,
        "anchors": anchors,
    }


def preflight_report(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "PASS__NO_OUTPUT_CREATED__NO_GEOMETRY_CONSTRUCTED",
        "iteration_id": ITERATION_ID,
        "runtime": context["runtime"],
        "baseline": {
            "path": str(context["baseline"]["assembly"]["path"]),
            "sha256": str(context["baseline"]["assembly"]["sha256"]),
        },
        "target_object": TARGET_OBJECT,
        "anchors": context["anchors"]["records"],
        "output_directory": str(context["contract"]["output"]["directory"]),
        "output_exists": context["output_dir"].exists(),
        "geometry_construction_started": False,
    }


def construct_candidate(context: dict[str, Any]) -> None:
    root = context["root"]
    baseline = context["baseline"]
    contract = context["contract"]
    parameters = context["parameters"]
    geometry = context["geometry"]
    document = context["document"]
    target = context["target"]
    protected_root = context["protected_root"]
    original_shape = context["original_shape"]
    origin = context["origin"]
    axis_u = context["axis_u"]
    axis_v = context["axis_v"]
    axis_t = context["axis_t"]

    context["output_dir"].mkdir(parents=True, exist_ok=False)
    context["candidate_path"].parent.mkdir(parents=True, exist_ok=True)
    document.saveAs(str(context["candidate_path"]))
    print(
        "STAGE 1/6 runtime, pinned inputs, mapped anchors, and signatures verified",
        flush=True,
    )

    protected_common = original_shape.common(protected_root.Shape).removeSplitter()
    if protected_common.isNull():
        raise RuntimeError("baseline C002/C042 protected-root overlay is null")

    current_half_width = float(parameters["profile"]["current_straight_across_flats_mm"]) / 2.0
    termination_face = Part.Face(
        geometry.square_wire(
            origin,
            axis_u,
            axis_v,
            axis_t,
            float(parameters["anchors"]["stop_plane_t_mm"]),
            current_half_width,
        )
    )
    candidate_shape, construction = geometry.build_candidate_shape(
        original_shape,
        termination_face,
        parameters,
        origin,
        axis_u,
        axis_v,
        axis_t,
    )
    print("STAGE 2/6 single Route 2 internal-profile replacement constructed", flush=True)
    target.Shape = candidate_shape
    document.recompute()
    if target.Name != context["original_name"] or target.Label != context["original_label"]:
        raise RuntimeError("target identity changed during replacement")
    if target.Placement != context["original_placement"]:
        raise RuntimeError("target placement changed during replacement")
    document.save()
    print("STAGE 3/6 candidate saved with only C002.Shape replaced", flush=True)

    construction.update(
        {
            "origin": origin,
            "axis_u": axis_u,
            "axis_v": axis_v,
            "axis_t": axis_t,
        }
    )
    geometry.render_review_pack(
        document,
        target,
        protected_root,
        protected_common,
        parameters,
        construction,
        root,
        contract,
    )
    print("STAGE 4/6 six fixed whole-head views rendered", flush=True)
    print("STAGE 5/6 seven requested focused review views rendered", flush=True)

    if sha256_file(context["baseline_path"]) != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 changed during generation")
    print("STAGE 6/6 canonical V34 remains hash-identical", flush=True)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    context = immutable_preflight(args.baseline, args.contract)
    try:
        if args.preflight_only:
            print(json.dumps(preflight_report(context), indent=2, sort_keys=True))
            return 0
        construct_candidate(context)
        return 0
    finally:
        App.closeDocument(context["document"].Name)


if __name__ == "__main__":
    raise SystemExit(main())
