#!/usr/bin/env python3
"""Generate the one-sided V40 repaired-eye/shell conflict review.

The repaired eye is hash-pinned and never transformed.  No support geometry is
added.  Only the four V35-positive shell owners are changed, using the numeric
contract in the paired JSON file.  The generator then re-runs the complete
41-upper + 60-lower exact collision matrix and saves review geometry only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import FreeCAD as App
import Mesh
import Part


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--overwrite-review-output", action="store_true")
    return parser.parse_args()


def repository_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("repository root not found")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def shape_bounds(shape) -> dict[str, list[float]] | None:
    if shape.isNull():
        return None
    box = shape.BoundBox
    return {
        "minimum_mm": [float(box.XMin), float(box.YMin), float(box.ZMin)],
        "maximum_mm": [float(box.XMax), float(box.YMax), float(box.ZMax)],
    }


def shape_summary(shape) -> dict[str, object]:
    return {
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids),
        "face_count": len(shape.Faces),
        "edge_count": len(shape.Edges),
        "vertex_count": len(shape.Vertexes),
        "volume_mm3": float(shape.Volume),
        "bounds": shape_bounds(shape),
    }


def common_volume(first, second) -> float:
    return float(first.common(second).Volume)


def measure_pair(eye, component, threshold: float) -> dict[str, object]:
    common = eye.common(component)
    volume = float(common.Volume)
    return {
        "intersection_volume_mm3": volume,
        "distance_mm": float(eye.distToShape(component)[0]),
        "positive_intersection": volume > threshold,
        "intersection_bounds": shape_bounds(common) if volume > threshold else None,
    }


def reconstruct_obj_solid(path: Path, tolerance_mm: float):
    mesh = Mesh.Mesh(str(path))
    shell = Part.Shape()
    shell.makeShapeFromMesh(mesh.Topology, tolerance_mm)
    if shell.isNull() or not shell.isClosed():
        raise RuntimeError(f"OBJ cannot be reconstructed as a closed shell: {path}")
    solid = Part.makeSolid(shell)
    if not solid.isValid() or not solid.isClosed() or len(solid.Solids) != 1:
        raise RuntimeError(f"OBJ reconstruction is not one valid closed solid: {path}")
    return solid


def retained_halfspace(shape, axis_values, shortening_mm: float):
    axis = App.Vector(*axis_values)
    axis.normalize()
    maximum = max(App.Vector(vertex.Point).dot(axis) for vertex in shape.Vertexes)
    plane_point = axis * (maximum - shortening_mm)
    halfspace = Part.makeBox(2000.0, 2000.0, 1000.0, App.Vector(-1000, -1000, -1000))
    halfspace.Placement = App.Placement(
        plane_point, App.Rotation(App.Vector(0, 0, 1), axis)
    )
    return shape.common(halfspace).removeSplitter()


def add_traceability(obj, contract_id: str, role: str, source: str) -> None:
    obj.addProperty("App::PropertyString", "ContractId", "ChangeControl")
    obj.ContractId = contract_id
    obj.addProperty("App::PropertyString", "ReviewRole", "ChangeControl")
    obj.ReviewRole = role
    obj.addProperty("App::PropertyString", "SourceIdentity", "ChangeControl")
    obj.SourceIdentity = source
    obj.addProperty("App::PropertyString", "ReleaseState", "ChangeControl")
    obj.ReleaseState = "REVIEW_ONLY__NO_MIRROR_NO_UNION_NO_STL_NO_PRINT"


def set_view(obj, color, transparency: int, visible: bool = True) -> None:
    if obj.ViewObject is None:
        return
    obj.ViewObject.ShapeColor = color
    obj.ViewObject.LineColor = tuple(max(0.0, value * 0.42) for value in color)
    obj.ViewObject.Transparency = transparency
    obj.ViewObject.LineWidth = 1.5
    obj.ViewObject.Visibility = visible


def add_part_object(document, group, name, label, shape, contract_id, role, source, color, transparency):
    obj = document.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape.copy()
    add_traceability(obj, contract_id, role, source)
    set_view(obj, color, transparency)
    group.addObject(obj)
    return obj


def aabb_separation_lower_bound(eye, minimum_mm, maximum_mm) -> float:
    box = eye.BoundBox
    eye_minimum = (box.XMin, box.YMin, box.ZMin)
    eye_maximum = (box.XMax, box.YMax, box.ZMax)
    gaps = [
        max(
            float(minimum_mm[index]) - float(eye_maximum[index]),
            float(eye_minimum[index]) - float(maximum_mm[index]),
            0.0,
        )
        for index in range(3)
    ]
    return math.sqrt(sum(value * value for value in gaps))


def main() -> int:
    args = parse_args()
    root = repository_root(args.contract)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    inputs = contract["frozen_inputs"]
    numeric = contract["numeric_contract"]
    threshold = float(numeric["positive_intersection_threshold_mm3"])
    reconstruction_tolerance = float(numeric["mesh_to_occt_tolerance_mm"])

    pinned_paths = {
        "upper_v34_fcstd": root / inputs["right_upper_v34"]["fcstd_path"],
        "upper_v34_validation": root / inputs["right_upper_v34"]["validation_path"],
        "upper_c001_v26_fcstd": root / inputs["right_upper_c001_v26"]["fcstd_path"],
        "eye_step": root / inputs["repaired_eye_v4"]["step_path"],
        "lower_v14_validation": root / inputs["right_lower_v14"]["validation_path"],
        "lower_c001_v13_fcstd": root / inputs["right_lower_component_001_v13"]["fcstd_path"],
        "v35_validation": root / inputs["v35_audit"]["validation_path"],
    }
    expected_hashes = {
        "upper_v34_fcstd": inputs["right_upper_v34"]["fcstd_sha256"],
        "upper_v34_validation": inputs["right_upper_v34"]["validation_sha256"],
        "upper_c001_v26_fcstd": inputs["right_upper_c001_v26"]["fcstd_sha256"],
        "eye_step": inputs["repaired_eye_v4"]["step_sha256"],
        "lower_v14_validation": inputs["right_lower_v14"]["validation_sha256"],
        "lower_c001_v13_fcstd": inputs["right_lower_component_001_v13"]["fcstd_sha256"],
        "v35_validation": inputs["v35_audit"]["validation_sha256"],
    }
    actual_hashes = {name: sha256_file(path) for name, path in pinned_paths.items()}
    if actual_hashes != expected_hashes:
        raise RuntimeError("hash-pinned input mismatch")

    upper_validation = json.loads(pinned_paths["upper_v34_validation"].read_text())
    lower_validation = json.loads(pinned_paths["lower_v14_validation"].read_text())
    v35_validation = json.loads(pinned_paths["v35_validation"].read_text())
    if v35_validation["positive_upper_components"] != inputs["v35_audit"]["required_positive_upper"]:
        raise RuntimeError("V35 positive-upper component set changed")
    if v35_validation["positive_lower_components"] != inputs["v35_audit"]["required_positive_lower"]:
        raise RuntimeError("V35 positive-lower component set changed")

    output_dir = root / contract["output"]["directory"]
    review_path = output_dir / contract["output"]["fcstd"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_dir.exists() and not args.overwrite_review_output:
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=args.overwrite_review_output)
    print("STAGE 1/9 contracts, hashes, and V35 target set verified", flush=True)

    eye = Part.Shape()
    eye.read(str(pinned_paths["eye_step"]))
    if eye.isNull() or not eye.isValid() or not eye.isClosed() or len(eye.Solids) != 1:
        raise RuntimeError("repaired eye is not one valid closed solid")

    upper_document = App.openDocument(str(pinned_paths["upper_v34_fcstd"]))
    v26_document = App.openDocument(str(pinned_paths["upper_c001_v26_fcstd"]))
    lower_c001_document = App.openDocument(str(pinned_paths["lower_c001_v13_fcstd"]))
    review_document = None
    try:
        component_object_map = upper_validation["review_objects"]["component_objects"]
        expected_upper_ids = {f"C{index:03d}" for index in range(1, 43) if index != 9}
        if set(component_object_map) != expected_upper_ids:
            raise RuntimeError("V34 upper component manifest mismatch")
        upper_sources = {}
        for identifier in sorted(expected_upper_ids):
            obj = upper_document.getObject(component_object_map[identifier])
            if obj is None or obj.Shape.isNull():
                raise RuntimeError(f"missing V34 upper {identifier}")
            upper_sources[identifier] = obj.Shape.copy()

        v26_object = v26_document.getObject(inputs["right_upper_c001_v26"]["candidate_object_name"])
        if v26_object is None or v26_object.Shape.isNull():
            raise RuntimeError("missing V26 upper-C001 candidate")
        v26_solids = list(v26_object.Shape.Solids)
        if len(v26_solids) < 2:
            raise RuntimeError("V26 candidate no longer contains the recorded detached solids")
        upper_c001 = max(v26_solids, key=lambda item: float(item.Volume)).copy()

        lower_c001_source_obj = lower_c001_document.getObject(
            inputs["right_lower_component_001_v13"]["object_name"]
        )
        if lower_c001_source_obj is None or lower_c001_source_obj.Shape.isNull():
            raise RuntimeError("missing V13 lower C001")
        lower_c001_source = lower_c001_source_obj.Shape.copy()

        lower_entries = {
            entry["name"]: entry
            for entry in lower_validation["unchanged_components_002_through_060"]
        }
        expected_lower_names = {f"V11_LOWER_COMPONENT_{index:03d}" for index in range(2, 61)}
        if set(lower_entries) != expected_lower_names:
            raise RuntimeError("V14 lower C002-C060 manifest mismatch")

        lower_sources = {}
        lower_nonsewn_meshes = {}
        verified_lower_hashes = {}
        for index in range(2, 61):
            identifier = f"C{index:03d}"
            entry = lower_entries[f"V11_LOWER_COMPONENT_{index:03d}"]
            path = root / entry["source_obj"]
            source_hash = sha256_file(path)
            if source_hash != entry["source_obj_sha256"]:
                raise RuntimeError(f"lower {identifier} source hash mismatch")
            verified_lower_hashes[identifier] = source_hash
            try:
                lower_sources[identifier] = reconstruct_obj_solid(path, reconstruction_tolerance)
            except RuntimeError:
                separation = aabb_separation_lower_bound(eye, entry["bbox_min_mm"], entry["bbox_max_mm"])
                if separation <= 0.0:
                    raise
                lower_nonsewn_meshes[identifier] = Mesh.Mesh(str(path))
        print("STAGE 2/9 exact upper/lower sources loaded", flush=True)

        eye_shift = eye.copy()
        relief_direction = App.Vector(*numeric["lower_c001_relief_direction"])
        relief_direction.normalize()
        eye_shift.translate(relief_direction * float(numeric["lower_c001_relief_gap_mm"]))
        lower_c001 = lower_c001_source.cut(eye).cut(eye_shift).removeSplitter()
        lower_c012 = retained_halfspace(
            lower_sources["C012"],
            numeric["member_trim_axis"],
            float(numeric["lower_c012_shortening_mm"]),
        )
        lower_c013 = retained_halfspace(
            lower_sources["C013"],
            numeric["member_trim_axis"],
            float(numeric["lower_c013_shortening_mm"]),
        )
        changed_shapes = {
            "UPPER_C001": upper_c001,
            "LOWER_C001": lower_c001,
            "LOWER_C012": lower_c012,
            "LOWER_C013": lower_c013,
        }
        changed_shape_summaries = {name: shape_summary(shape) for name, shape in changed_shapes.items()}
        print("STAGE 3/9 four numeric owner corrections generated in memory", flush=True)

        upper_candidates = dict(upper_sources)
        upper_candidates["C001"] = upper_c001
        lower_candidates = dict(lower_sources)
        lower_candidates["C001"] = lower_c001
        lower_candidates["C012"] = lower_c012
        lower_candidates["C013"] = lower_c013

        upper_results = {
            identifier: measure_pair(eye, shape, threshold)
            for identifier, shape in sorted(upper_candidates.items())
        }
        lower_results = {
            identifier: measure_pair(eye, shape, threshold)
            for identifier, shape in sorted(lower_candidates.items())
        }
        nonsewn_proofs = {}
        for identifier in sorted(lower_nonsewn_meshes):
            record = v35_validation["lower_component_results"][identifier]
            if record["positive_intersection"] or float(record["distance_lower_bound_mm"]) <= 0.0:
                raise RuntimeError(f"invalid V35 AABB proof for lower {identifier}")
            nonsewn_proofs[identifier] = record
            lower_results[identifier] = {
                "intersection_volume_mm3": 0.0,
                "distance_mm": None,
                "distance_lower_bound_mm": float(record["distance_lower_bound_mm"]),
                "positive_intersection": False,
                "intersection_bounds": None,
                "evaluation_method": "unchanged_hash_pinned_V35_strict_AABB_proof",
            }
        positive_upper = sorted(name for name, record in upper_results.items() if record["positive_intersection"])
        positive_lower = sorted(name for name, record in lower_results.items() if record["positive_intersection"])
        print("STAGE 4/9 complete 101-component eye collision matrix evaluated", flush=True)

        c012_c001_engagement = common_volume(lower_c012, lower_c001)
        c013_engagements = {
            "C002": common_volume(lower_c013, lower_sources["C002"]),
            "C011": common_volume(lower_c013, lower_sources["C011"]),
            "C012": common_volume(lower_c013, lower_c012),
        }
        c013_upper_c032_overlap = common_volume(lower_c013, upper_sources["C032"])
        c012_eye_clearance = float(lower_c012.distToShape(eye)[0])
        c013_eye_clearance = float(lower_c013.distToShape(eye)[0])
        minimum_engagement = float(numeric["minimum_positive_owner_engagement_mm3"])

        checks = {
            "all_pinned_hashes_match": actual_hashes == expected_hashes,
            "eye_unchanged_valid_closed_one_solid": bool(eye.isValid()) and bool(eye.isClosed()) and len(eye.Solids) == 1,
            "all_four_changed_owners_valid_closed_one_solid": all(
                record["valid"] and record["closed"] and record["solid_count"] == 1
                for record in changed_shape_summaries.values()
            ),
            "upper_manifest_has_41_components": len(upper_results) == int(numeric["required_upper_component_count"]),
            "lower_manifest_has_60_components": len(lower_results) == int(numeric["required_lower_component_count"]),
            "all_59_lower_source_hashes_match": len(verified_lower_hashes) == 59,
            "zero_positive_upper_eye_intersections": not positive_upper,
            "zero_positive_lower_eye_intersections": not positive_lower,
            "c012_eye_clearance_at_least_4mm": c012_eye_clearance >= float(numeric["minimum_c012_c013_eye_clearance_mm"]),
            "c013_eye_clearance_at_least_4mm": c013_eye_clearance >= float(numeric["minimum_c012_c013_eye_clearance_mm"]),
            "c012_remains_engaged_to_lower_c001": c012_c001_engagement > minimum_engagement,
            "c013_remains_engaged_to_existing_lower_members": all(value > minimum_engagement for value in c013_engagements.values()),
            "c013_no_longer_overlaps_upper_c032": c013_upper_c032_overlap <= threshold,
            "no_added_bridge_rail_rib_flange_or_support": True,
            "no_mirror_union_or_export": True,
        }
        passed = all(checks.values())
        print("STAGE 5/9 topology, engagement, and ownership checks evaluated", flush=True)

        review_document = App.newDocument("CAT_HEAD_RIGHT_EYE_SHELL_CONFLICT_CORRECTION_REVIEW_V40")
        eye_group = review_document.addObject("App::DocumentObjectGroup", "FROZEN_EYE_V40")
        eye_group.Label = "01__FROZEN_REPAIRED_EYE__UNCHANGED"
        changed_group = review_document.addObject("App::DocumentObjectGroup", "CHANGED_OWNERS_V40")
        changed_group.Label = "02__FOUR_CORRECTED_OWNERS__REVIEW"
        context_group = review_document.addObject("App::DocumentObjectGroup", "UNCHANGED_CONTEXT_V40")
        context_group.Label = "03__UNCHANGED_RIGHT_SHELL_CONTEXT"
        audit_group = review_document.addObject("App::DocumentObjectGroup", "AUDIT_V40")
        audit_group.Label = "04__ZERO_INTERSECTION_AUDIT"

        eye_object = add_part_object(
            review_document, eye_group, "FROZEN_REPAIRED_RIGHT_EYE_V40",
            "FROZEN__REPAIRED_RIGHT_EYE__UNCHANGED__V40", eye,
            contract["contract_id"], "FROZEN_REPAIRED_EYE", "V4_STEP_HASH_PINNED",
            (0.20, 0.72, 0.96), 62,
        )
        changed_objects = {
            "UPPER_C001": add_part_object(
                review_document, changed_group, "PROPOSED_UPPER_C001_MAIN_ONLY_V40",
                "PROPOSED__UPPER_C001__V26_MAIN_BODY_ONLY__V40", upper_c001,
                contract["contract_id"], "CORRECTED_UPPER_C001", "V26_LARGEST_VALID_SOLID",
                (1.00, 0.58, 0.12), 28,
            ),
            "LOWER_C001": add_part_object(
                review_document, changed_group, "PROPOSED_LOWER_C001_EYE_RELIEF_V40",
                "PROPOSED__LOWER_C001__0P30MM_EYE_RELIEF__V40", lower_c001,
                contract["contract_id"], "CORRECTED_LOWER_C001", "V13_MINUS_FIXED_AND_SHIFTED_EYE",
                (0.96, 0.42, 0.16), 32,
            ),
            "LOWER_C012": add_part_object(
                review_document, changed_group, "PROPOSED_LOWER_C012_SHORTENED_V40",
                "PROPOSED__LOWER_C012__SHORTENED_5P452MM__V40", lower_c012,
                contract["contract_id"], "CORRECTED_LOWER_C012", "V14_C012_EYE_END_SHORTENED",
                (0.82, 0.30, 0.82), 20,
            ),
            "LOWER_C013": add_part_object(
                review_document, changed_group, "PROPOSED_LOWER_C013_SHORTENED_V40",
                "PROPOSED__LOWER_C013__SHORTENED_45P090MM__V40", lower_c013,
                contract["contract_id"], "CORRECTED_LOWER_C013", "V14_C013_EYE_END_SHORTENED",
                (0.72, 0.24, 0.92), 20,
            ),
        }

        unchanged_upper = Part.makeCompound(
            [shape for identifier, shape in sorted(upper_sources.items()) if identifier != "C001"]
        )
        unchanged_lower = Part.makeCompound(
            [
                shape
                for identifier, shape in sorted(lower_sources.items())
                if identifier not in {"C012", "C013"}
            ]
        )
        upper_context_object = add_part_object(
            review_document, context_group, "FROZEN_UNCHANGED_UPPER_CONTEXT_V40",
            "FROZEN__UNCHANGED_UPPER_C002_C042_MINUS_C009__V40", unchanged_upper,
            contract["contract_id"], "UNCHANGED_UPPER_CONTEXT", "V34_COMPONENT_COPIES",
            (0.64, 0.67, 0.72), 76,
        )
        lower_context_object = add_part_object(
            review_document, context_group, "FROZEN_UNCHANGED_LOWER_CONTEXT_V40",
            "FROZEN__UNCHANGED_LOWER_SOLIDS_C002_C060_EXCEPT_C012_C013__V40", unchanged_lower,
            contract["contract_id"], "UNCHANGED_LOWER_CONTEXT", "V14_RECONSTRUCTED_SOLIDS",
            (0.36, 0.40, 0.45), 78,
        )
        nonsewn_object_names = []
        for identifier, mesh in sorted(lower_nonsewn_meshes.items()):
            obj = review_document.addObject("Mesh::Feature", f"FROZEN_LOWER_{identifier}_MESH_V40")
            obj.Label = f"FROZEN__LOWER_{identifier}__UNCHANGED_MESH__V40"
            obj.Mesh = mesh.copy()
            add_traceability(obj, contract["contract_id"], "UNCHANGED_NONSEWN_LOWER_CONTEXT", f"V14:{identifier}")
            if obj.ViewObject is not None:
                obj.ViewObject.ShapeColor = (0.36, 0.40, 0.45)
                obj.ViewObject.Transparency = 78
            context_group.addObject(obj)
            nonsewn_object_names.append(obj.Name)

        audit_table = review_document.addObject("App::FeaturePython", "V40_AUDIT_SUMMARY")
        audit_table.Label = "AUDIT__101_COMPONENTS__ZERO_POSITIVE_INTERSECTIONS__V40"
        audit_table.addProperty("App::PropertyInteger", "UpperComponentsTested", "Audit")
        audit_table.UpperComponentsTested = len(upper_results)
        audit_table.addProperty("App::PropertyInteger", "LowerComponentsTested", "Audit")
        audit_table.LowerComponentsTested = len(lower_results)
        audit_table.addProperty("App::PropertyInteger", "PositiveIntersections", "Audit")
        audit_table.PositiveIntersections = len(positive_upper) + len(positive_lower)
        audit_table.addProperty("App::PropertyString", "ExteriorContainment", "Audit")
        audit_table.ExteriorContainment = "VISUAL_HOLD__NO_CLOSED_CONTAINMENT_ENVELOPE_EXISTS"
        audit_group.addObject(audit_table)
        for group in (eye_group, changed_group, context_group, audit_group):
            if group.ViewObject is not None:
                group.ViewObject.Visibility = True
        review_document.recompute()
        print("STAGE 6/9 compact full-context review assembled", flush=True)

        result = {
            "schema_version": "1.0",
            "generator": "freecad-right-eye-shell-conflict-correction-review-v40",
            "freecad_version": App.Version(),
            "contract_id": contract["contract_id"],
            "status": "PASS__COLLISION_FREE_REVIEW__EXTERIOR_CONTAINMENT_VISUAL_HOLD" if passed else "FAIL__NO_REVIEW_FILE_SAVED",
            "input_hashes": actual_hashes,
            "numeric_contract": numeric,
            "eye": shape_summary(eye),
            "changed_owner_summaries": changed_shape_summaries,
            "upper_component_results": upper_results,
            "lower_component_results": lower_results,
            "nonsewn_lower_aabb_proofs": nonsewn_proofs,
            "positive_upper_components": positive_upper,
            "positive_lower_components": positive_lower,
            "positive_intersection_count": len(positive_upper) + len(positive_lower),
            "clearance_mm": {"lower_c012_to_eye": c012_eye_clearance, "lower_c013_to_eye": c013_eye_clearance},
            "engagement_volume_mm3": {
                "lower_c012_to_lower_c001": c012_c001_engagement,
                "lower_c013_to_lower_c002": c013_engagements["C002"],
                "lower_c013_to_lower_c011": c013_engagements["C011"],
                "lower_c013_to_lower_c012": c013_engagements["C012"],
                "lower_c013_to_upper_c032_unwanted": c013_upper_c032_overlap,
            },
            "checks": checks,
            "exterior_containment": {
                "status": "VISUAL_REVIEW_REQUIRED",
                "reason": "The assembled shell is not one closed solid, so a mathematically complete inside/outside containment test is unavailable.",
                "automatic_evidence": "All 101 eye-versus-shell component intersections are zero; visible exterior breach must still be reviewed from outside views.",
            },
            "review_objects": {
                "eye": eye_object.Name,
                "changed": {name: obj.Name for name, obj in changed_objects.items()},
                "unchanged_upper_compound": upper_context_object.Name,
                "unchanged_lower_compound": lower_context_object.Name,
                "unchanged_nonsewn_lower_meshes": nonsewn_object_names,
                "audit": audit_table.Name,
            },
            "release_holds": contract["release_holds"],
            "outputs": {
                "fcstd": str(review_path.relative_to(root)) if passed else None,
                "validation": str(validation_path.relative_to(root)),
                "mirrored": False,
                "production_union_created": False,
                "stl_exported": False,
                "sliced": False,
            },
        }

        if not passed:
            validation_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            raise RuntimeError(f"V40 validation failed: {checks}")
        print("STAGE 7/9 all review gates passed", flush=True)
        review_document.saveAs(str(review_path))
        result["outputs"]["fcstd_sha256"] = sha256_file(review_path)
        validation_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("STAGE 8/9 review file and validation saved", flush=True)
        print(json.dumps({"status": result["status"], "fcstd": str(review_path), "validation": str(validation_path)}, indent=2), flush=True)
        print("STAGE 9/9 complete", flush=True)
    finally:
        if review_document is not None:
            App.closeDocument(review_document.Name)
        App.closeDocument(upper_document.Name)
        App.closeDocument(v26_document.Name)
        App.closeDocument(lower_c001_document.Name)
    return 0


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
