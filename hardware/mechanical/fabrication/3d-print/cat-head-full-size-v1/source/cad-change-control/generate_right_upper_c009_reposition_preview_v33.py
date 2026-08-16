#!/usr/bin/env python3
"""Build the review-only V33 preview for the accepted C009 translation.

The generator opens hash-pinned accepted inputs read-only, copies the complete
42-component V25 right-upper context into a new document, substitutes the
topology-repaired V4 eye, and rigidly translates only the existing C009 solid
by the V32-approved review vector.  It adds no support geometry and performs
no production union, mirror, STL export, slicing, or print release.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import FreeCAD as App
import Part

from audit_right_upper_c001_c009_existing_body_routes import (
    common_volume,
    find_components,
    repository_root,
    sha256_file,
    shape_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    return parser.parse_args()


def add_traceability(obj, contract_id: str, component_id: str, role: str) -> None:
    obj.addProperty("App::PropertyString", "ContractId", "ChangeControl")
    obj.ContractId = contract_id
    obj.addProperty("App::PropertyString", "ComponentId", "ChangeControl")
    obj.ComponentId = component_id
    obj.addProperty("App::PropertyString", "ReviewRole", "ChangeControl")
    obj.ReviewRole = role
    obj.addProperty("App::PropertyString", "ReleaseState", "ChangeControl")
    obj.ReleaseState = "REVIEW_ONLY__NO_MIRROR_NO_UNION_NO_STL_NO_PRINT"


def set_view(obj, color, transparency: int, visible: bool = True) -> None:
    if obj.ViewObject is None:
        return
    obj.ViewObject.ShapeColor = color
    obj.ViewObject.LineColor = tuple(max(0.0, value * 0.45) for value in color)
    obj.ViewObject.Transparency = transparency
    obj.ViewObject.LineWidth = 1.5
    obj.ViewObject.Visibility = visible


def exact_collision(candidate, obstacle, threshold: float) -> dict[str, object]:
    distance = float(candidate.distToShape(obstacle)[0])
    overlap = common_volume(candidate, obstacle) if distance <= 1.0e-6 else 0.0
    return {
        "distance_mm": distance,
        "intersection_volume_mm3": overlap,
        "clear": overlap <= threshold,
    }


def main() -> int:
    args = parse_args()
    root = repository_root(args.contract)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))

    actual_hashes = {}
    for identifier, spec in contract["inputs"].items():
        path = root / spec["path"]
        actual_hashes[identifier] = sha256_file(path)
        if actual_hashes[identifier] != spec["sha256"]:
            raise RuntimeError(f"hash-pinned input mismatch for {identifier}")

    dependency = contract["implementation_dependency"]
    dependency_hash = sha256_file(root / dependency["path"])
    if dependency_hash != dependency["sha256"]:
        raise RuntimeError("component-identification helper hash mismatch")

    output_dir = root / contract["output"]["directory"]
    review_path = output_dir / contract["output"]["fcstd"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    output_dir.mkdir(parents=True)
    print("STAGE 1/7 contract and hashes verified", flush=True)

    v32 = json.loads(
        (root / contract["inputs"]["v32_validation_json"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    if v32["status"] != contract["required_v32_status"]:
        raise RuntimeError("V32 full-context validation is not the required pass")
    candidate_contract = contract["candidate"]
    if v32["candidate"]["source_member"] != candidate_contract["source_member"]:
        raise RuntimeError("V32 source member differs from V33 contract")
    if v32["candidate"]["translation_mm"] != candidate_contract["translation_mm"]:
        raise RuntimeError("V32 translation differs from V33 contract")
    print("STAGE 2/7 V32 route authorization verified", flush=True)

    eye = Part.Shape()
    eye.read(str(root / contract["inputs"]["replacement_eye_step"]["path"]))
    if eye.isNull():
        raise RuntimeError("replacement eye STEP imported as a null shape")

    source_document = App.openDocument(
        str(root / contract["inputs"]["accepted_context_fcstd"]["path"])
    )
    review_document = None
    try:
        components = find_components(source_document)
        expected_ids = {f"C{index:03d}" for index in range(1, 43)}
        if set(components) != expected_ids:
            raise RuntimeError("accepted V25 component manifest mismatch")

        source_c009 = components["C009"].Shape.copy()
        c001 = components["C001"].Shape.copy()
        moved_c009 = source_c009.copy()
        moved_c009.translate(App.Vector(*candidate_contract["translation_mm"]))
        print("STAGE 3/7 exact C009 translated in memory", flush=True)

        numeric = contract["numeric_contract"]
        threshold = float(numeric["positive_intersection_threshold_mm3"])
        owner_overlap = common_volume(moved_c009, c001)
        eye_clearance = float(moved_c009.distToShape(eye)[0])
        collisions = {
            identifier: exact_collision(moved_c009, obj.Shape, threshold)
            for identifier, obj in sorted(components.items())
            if identifier not in {"C001", "C009"}
        }
        collision_failures = {
            identifier: record
            for identifier, record in collisions.items()
            if not record["clear"]
        }
        source_summary = shape_summary(source_c009)
        moved_summary = shape_summary(moved_c009)
        eye_summary = shape_summary(eye)

        checks = {
            "input_hashes_match": True,
            "v32_full_context_status_passes": True,
            "upper_component_manifest_is_c001_through_c042": set(components)
            == expected_ids,
            "replacement_eye_valid": bool(eye.isValid()),
            "replacement_eye_closed": bool(eye.isClosed()),
            "replacement_eye_one_solid": len(eye.Solids) == 1,
            "moved_c009_valid": bool(moved_c009.isValid()),
            "moved_c009_closed": bool(moved_c009.isClosed()),
            "moved_c009_one_solid": len(moved_c009.Solids) == 1,
            "c009_face_count_preserved": moved_summary["face_count"]
            == source_summary["face_count"],
            "c009_volume_preserved": abs(
                moved_summary["volume_mm3"] - source_summary["volume_mm3"]
            )
            <= float(numeric["maximum_volume_delta_mm3"]),
            "eye_clearance_passes": eye_clearance + 1.0e-9
            >= float(numeric["minimum_eye_clearance_mm"]),
            "c001_engagement_passes": owner_overlap + 1.0e-12
            >= float(numeric["minimum_owner_overlap_mm3"]),
            "zero_other_upper_component_collisions": not collision_failures,
            "v32_eye_clearance_reproduced": abs(
                eye_clearance - float(v32["candidate"]["repaired_eye_clearance_mm"])
            )
            <= float(numeric["maximum_metric_reproduction_delta_mm"]),
            "v32_owner_overlap_reproduced": abs(
                owner_overlap - float(v32["candidate"]["c001_owner_overlap_mm3"])
            )
            <= float(numeric["maximum_metric_reproduction_delta_mm3"]),
        }
        passed = all(checks.values())
        print("STAGE 4/7 exact geometry gates measured", flush=True)

        result = {
            "schema_version": "1.0",
            "generator": "freecad-right-upper-c009-reposition-preview-v33",
            "freecad_version": App.Version(),
            "contract_id": contract["contract_id"],
            "status": "PASS__REVIEW_ONLY_ONE_SIDED_PREVIEW" if passed else "FAIL__NO_REVIEW_FILE_SAVED",
            "input_hashes": actual_hashes,
            "implementation_dependency_hash": dependency_hash,
            "candidate": {
                **candidate_contract,
                "source_object_name": components["C009"].Name,
                "source_object_label": components["C009"].Label,
                "source_shape": source_summary,
                "moved_shape": moved_summary,
                "repaired_eye_clearance_mm": eye_clearance,
                "c001_owner_overlap_mm3": owner_overlap,
            },
            "owner": {
                "component_id": "C001",
                "source_object_name": components["C001"].Name,
                "source_object_label": components["C001"].Label,
                "shape": shape_summary(c001),
            },
            "replacement_eye": eye_summary,
            "other_upper_component_checks": collisions,
            "collision_failures": collision_failures,
            "checks": checks,
            "review_display": contract["review_display"],
            "release_holds": contract["release_holds"],
            "outputs": {
                "fcstd": str(review_path.relative_to(root)) if passed else None,
                "validation": str(validation_path.relative_to(root)),
            },
        }

        if not passed:
            validation_path.write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            raise RuntimeError(f"V33 gates failed: {checks}")

        review_document = App.newDocument(
            "CAT_HEAD_RIGHT_UPPER_C009_REPOSITION_PREVIEW_V33"
        )
        frozen_group = review_document.addObject("App::DocumentObjectGroup", "FROZEN_CONTEXT_V33")
        frozen_group.Label = "FROZEN_CONTEXT__V25__V33"
        owner_group = review_document.addObject("App::DocumentObjectGroup", "OWNER_C001_V33")
        owner_group.Label = "OWNER__C001__V33"
        candidate_group = review_document.addObject("App::DocumentObjectGroup", "PROPOSED_MOVED_C009_V33")
        candidate_group.Label = "PROPOSED__MOVED_EXISTING_C009__V33"
        eye_group = review_document.addObject("App::DocumentObjectGroup", "REPAIRED_EYE_V33")
        eye_group.Label = "REPAIRED_EYE__V4__V33"

        output_component_names = {}
        for identifier, source in sorted(components.items()):
            if identifier == "C009":
                target = review_document.addObject(
                    "Part::Feature", "PROPOSED_RIGHT_UPPER_C009_MOVED_V33"
                )
                target.Label = "PROPOSED__EXISTING_C009_MOVED_BY_V32_VECTOR__V33"
                target.Shape = moved_c009.copy()
                add_traceability(target, contract["contract_id"], identifier, "MOVED_EXISTING_MEMBER")
                target.addProperty("App::PropertyVector", "TranslationVector", "ChangeControl")
                target.TranslationVector = App.Vector(*candidate_contract["translation_mm"])
                set_view(target, (1.0, 0.48, 0.05), 0)
                candidate_group.addObject(target)
            else:
                target = review_document.addObject(
                    "Part::Feature", f"FROZEN_RIGHT_UPPER_{identifier}_V33"
                )
                target.Label = f"FROZEN__RIGHT_UPPER_{identifier}__V25__V33"
                target.Shape = source.Shape.copy()
                role = "C001_OWNER" if identifier == "C001" else "FROZEN_CONTEXT"
                add_traceability(target, contract["contract_id"], identifier, role)
                if identifier == "C001":
                    set_view(target, (0.25, 0.82, 0.36), 35)
                    owner_group.addObject(target)
                else:
                    set_view(target, (0.68, 0.71, 0.75), 65)
                    frozen_group.addObject(target)
            output_component_names[identifier] = target.Name

        eye_object = review_document.addObject(
            "Part::Feature", "FROZEN_REPAIRED_RIGHT_EYE_V4_V33"
        )
        eye_object.Label = "FROZEN__RIGHT_EYE_FULL_TOPOLOGY_REPAIRED_V4__V33"
        eye_object.Shape = eye.copy()
        add_traceability(eye_object, contract["contract_id"], "RIGHT_EYE", "REPAIRED_FROZEN_CONTEXT")
        set_view(eye_object, (0.25, 0.78, 0.95), 72)
        eye_group.addObject(eye_object)

        review_document.recompute()
        result["review_objects"] = {
            "component_objects": output_component_names,
            "eye_object": eye_object.Name,
            "frozen_context_group": frozen_group.Name,
            "owner_group": owner_group.Name,
            "candidate_group": candidate_group.Name,
            "eye_group": eye_group.Name,
            "shape_object_count": 43,
            "added_support_geometry_count": 0,
        }
        print("STAGE 5/7 review-only context assembled", flush=True)

        review_document.saveAs(str(review_path))
        result["outputs"]["fcstd_sha256"] = sha256_file(review_path)
        validation_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("STAGE 6/7 review file saved", flush=True)
        print(json.dumps({"status": result["status"], "fcstd": str(review_path), "validation": str(validation_path)}, indent=2), flush=True)
        print("STAGE 7/7 complete", flush=True)
    finally:
        if review_document is not None:
            App.closeDocument(review_document.Name)
        App.closeDocument(source_document.Name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
