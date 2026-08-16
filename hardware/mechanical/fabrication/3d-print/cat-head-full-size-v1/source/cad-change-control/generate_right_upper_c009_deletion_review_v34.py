#!/usr/bin/env python3
"""Build the one-sided V34 review that omits separate right-upper C009.

The generator starts from the accepted V25 right-upper component manifest,
copies every component except C009 without transformation, and adds only frozen
reference copies of the repaired eye, complete right lower face, current right
primary ear, and accepted translucent A/B panel.  It performs no subtractive
cut, replacement construction, mirror, production union, or print export.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import FreeCAD as App
import Mesh
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
    parser.add_argument(
        "--overwrite-review-output",
        action="store_true",
        help="replace only this contract's named FCStd and validation outputs",
    )
    return parser.parse_args()


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


def find_exact_object(document, identity: str):
    matches = [
        obj
        for obj in document.Objects
        if obj.Name == identity or obj.Label == identity
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected exactly one object {identity!r} in {document.Name}, found {len(matches)}"
        )
    return matches[0]


def shape_delta(first: dict[str, object], second: dict[str, object]) -> dict[str, float]:
    bounds_first = first["bounds"]
    bounds_second = second["bounds"]
    bound_values = []
    for key in ("minimum_mm", "maximum_mm"):
        bound_values.extend(
            abs(float(a) - float(b))
            for a, b in zip(bounds_first[key], bounds_second[key])
        )
    return {
        "volume_mm3": abs(float(first["volume_mm3"]) - float(second["volume_mm3"])),
        "bounds_mm": max(bound_values, default=0.0),
    }


def mesh_summary(mesh) -> dict[str, object]:
    box = mesh.BoundBox
    return {
        "point_count": int(mesh.CountPoints),
        "facet_count": int(mesh.CountFacets),
        "bounds": {
            "minimum_mm": [float(box.XMin), float(box.YMin), float(box.ZMin)],
            "maximum_mm": [float(box.XMax), float(box.YMax), float(box.ZMax)],
        },
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
    if output_dir.exists() and not args.overwrite_review_output:
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=args.overwrite_review_output)
    print("STAGE 1/8 contract and hashes verified", flush=True)

    accepted_validation = json.loads(
        (root / contract["inputs"]["accepted_context_validation_json"]["path"]).read_text(
            encoding="utf-8"
        )
    )
    if accepted_validation.get("status") != contract["required_accepted_context_status"]:
        raise RuntimeError("accepted V25 validation status mismatch")

    eye = Part.Shape()
    eye.read(str(root / contract["inputs"]["replacement_eye_step"]["path"]))
    if eye.isNull():
        raise RuntimeError("replacement eye STEP imported as a null shape")

    accepted_document = App.openDocument(
        str(root / contract["inputs"]["accepted_context_fcstd"]["path"])
    )
    full_context_document = App.openDocument(
        str(root / contract["inputs"]["right_eye_full_context_fcstd"]["path"])
    )
    ear_document = App.openDocument(
        str(root / contract["inputs"]["right_primary_ear_fcstd"]["path"])
    )
    ab_document = App.openDocument(
        str(root / contract["inputs"]["right_ab_panel_fcstd"]["path"])
    )
    review_document = None
    try:
        components = find_components(accepted_document)
        expected_ids = {f"C{index:03d}" for index in range(1, 43)}
        retained_ids = expected_ids - {contract["target"]["component_id"]}
        if set(components) != expected_ids:
            raise RuntimeError("accepted V25 component manifest mismatch")
        if len(retained_ids) != int(contract["numeric_contract"]["retained_component_count"]):
            raise RuntimeError("retained component count contract mismatch")

        context = contract["context_objects"]
        lower_main_source = find_exact_object(full_context_document, context["lower_main"])
        lower_mesh_source = find_exact_object(
            full_context_document, context["lower_components_mesh"]
        )
        ear_source = find_exact_object(ear_document, context["right_primary_ear"])
        ab_source = find_exact_object(ab_document, context["right_translucent_ab_panel"])
        print("STAGE 2/8 exact source manifest and context identities verified", flush=True)

        source_c009 = components["C009"].Shape.copy()
        source_summaries = {
            identifier: shape_summary(obj.Shape)
            for identifier, obj in sorted(components.items())
        }
        retained_shapes = [components[identifier].Shape.copy() for identifier in sorted(retained_ids)]
        retained_compound = Part.makeCompound(retained_shapes)
        source_compound = Part.makeCompound(
            [components[identifier].Shape.copy() for identifier in sorted(expected_ids)]
        )
        source_c009_eye_intersection = common_volume(source_c009, eye)
        retained_eye_intersections = {}
        for identifier in sorted(retained_ids):
            shape = components[identifier].Shape
            distance = float(shape.distToShape(eye)[0])
            volume = common_volume(shape, eye) if distance <= 1.0e-6 else 0.0
            if volume > float(contract["numeric_contract"]["positive_intersection_threshold_mm3"]):
                retained_eye_intersections[identifier] = {
                    "distance_mm": distance,
                    "intersection_volume_mm3": volume,
                }
        print("STAGE 3/8 deletion-only in-memory manifest measured", flush=True)

        review_document = App.newDocument(
            "CAT_HEAD_RIGHT_UPPER_C009_DELETION_REVIEW_V34"
        )
        upper_group = review_document.addObject(
            "App::DocumentObjectGroup", "RETAINED_RIGHT_UPPER_V34"
        )
        upper_group.Label = "RETAINED__RIGHT_UPPER__V25_MINUS_C009__V34"
        context_group = review_document.addObject(
            "App::DocumentObjectGroup", "FROZEN_FULL_CONTEXT_V34"
        )
        context_group.Label = "FROZEN__FULL_RIGHT_CONTEXT__V34"

        copied_summaries = {}
        output_component_names = {}
        numeric = contract["numeric_contract"]
        copy_failures = {}
        for identifier in sorted(retained_ids):
            source = components[identifier]
            target = review_document.addObject(
                "Part::Feature", f"RETAINED_RIGHT_UPPER_{identifier}_V34"
            )
            target.Label = f"RETAINED__RIGHT_UPPER_{identifier}__V25__V34"
            target.Shape = source.Shape.copy()
            add_traceability(
                target,
                contract["contract_id"],
                "C001_OWNER" if identifier == "C001" else "RETAINED_UPPER_COMPONENT",
                f"V25:{source.Name}",
            )
            color = (0.25, 0.82, 0.36) if identifier == "C001" else (0.68, 0.71, 0.75)
            transparency = 38 if identifier == "C001" else 62
            set_view(target, color, transparency)
            upper_group.addObject(target)
            copied_summaries[identifier] = shape_summary(target.Shape)
            delta = shape_delta(source_summaries[identifier], copied_summaries[identifier])
            if (
                delta["volume_mm3"] > float(numeric["maximum_copy_volume_delta_mm3"])
                or delta["bounds_mm"] > float(numeric["maximum_copy_bound_delta_mm"])
                or copied_summaries[identifier]["face_count"]
                != source_summaries[identifier]["face_count"]
                or not copied_summaries[identifier]["valid"]
                or not copied_summaries[identifier]["closed"]
            ):
                copy_failures[identifier] = delta
            output_component_names[identifier] = target.Name

        eye_object = review_document.addObject(
            "Part::Feature", "FROZEN_REPAIRED_RIGHT_EYE_V4_V34"
        )
        eye_object.Label = "FROZEN__RIGHT_EYE_FULL_TOPOLOGY_REPAIRED_V4__V34"
        eye_object.Shape = eye.copy()
        add_traceability(
            eye_object, contract["contract_id"], "FROZEN_REPAIRED_EYE", "V4_STEP"
        )
        set_view(eye_object, (0.25, 0.78, 0.95), 68)
        context_group.addObject(eye_object)

        lower_main = review_document.addObject(
            "Part::Feature", "FROZEN_RIGHT_LOWER_MAIN_V34"
        )
        lower_main.Label = "FROZEN__RIGHT_LOWER_MAIN__V18__V34"
        lower_main.Shape = lower_main_source.Shape.copy()
        add_traceability(
            lower_main,
            contract["contract_id"],
            "FROZEN_RIGHT_LOWER_MAIN",
            f"V18:{lower_main_source.Name}",
        )
        set_view(lower_main, (0.34, 0.36, 0.40), 74)
        context_group.addObject(lower_main)

        lower_mesh = review_document.addObject(
            "Mesh::Feature", "FROZEN_RIGHT_LOWER_COMPONENTS_002_060_V34"
        )
        lower_mesh.Label = "FROZEN__RIGHT_LOWER_COMPONENTS_002_060__V18__V34"
        lower_mesh.Mesh = lower_mesh_source.Mesh.copy()
        add_traceability(
            lower_mesh,
            contract["contract_id"],
            "FROZEN_RIGHT_LOWER_COMPONENTS",
            f"V18:{lower_mesh_source.Name}",
        )
        if lower_mesh.ViewObject is not None:
            lower_mesh.ViewObject.ShapeColor = (0.34, 0.36, 0.40)
            lower_mesh.ViewObject.LineColor = (0.14, 0.15, 0.17)
            lower_mesh.ViewObject.Transparency = 74
            lower_mesh.ViewObject.Visibility = True
        context_group.addObject(lower_mesh)

        ear = review_document.addObject("Part::Feature", "FROZEN_RIGHT_PRIMARY_EAR_V34")
        ear.Label = "FROZEN__RIGHT_PRIMARY_EAR__V2__V34"
        ear.Shape = ear_source.Shape.copy()
        add_traceability(
            ear,
            contract["contract_id"],
            "FROZEN_RIGHT_PRIMARY_EAR",
            f"EAR_V2:{ear_source.Name}",
        )
        set_view(ear, (0.74, 0.67, 0.55), 55)
        context_group.addObject(ear)

        panel = review_document.addObject(
            "Part::Feature", "FROZEN_RIGHT_TRANSLUCENT_AB_PANEL_V34"
        )
        panel.Label = "FROZEN__RIGHT_TRANSLUCENT_AB_PANEL__V1__V34"
        panel.Shape = ab_source.Shape.copy()
        add_traceability(
            panel,
            contract["contract_id"],
            "FROZEN_RIGHT_TRANSLUCENT_AB_PANEL",
            f"AB_V1:{ab_source.Name}",
        )
        set_view(panel, (1.0, 0.62, 0.16), 66)
        context_group.addObject(panel)
        # DocumentObjectGroup defaults can reopen hidden in FreeCAD even when each
        # child has its own visibility enabled. Persist both review groups visible
        # so the FCStd opens directly into the intended full-context inspection.
        if upper_group.ViewObject is not None:
            upper_group.ViewObject.Visibility = True
        if context_group.ViewObject is not None:
            context_group.ViewObject.Visibility = True
        review_document.recompute()
        print("STAGE 4/8 review-only full context assembled", flush=True)

        context_checks = {
            "eye": shape_delta(shape_summary(eye), shape_summary(eye_object.Shape)),
            "lower_main": shape_delta(
                shape_summary(lower_main_source.Shape), shape_summary(lower_main.Shape)
            ),
            "right_primary_ear": shape_delta(
                shape_summary(ear_source.Shape), shape_summary(ear.Shape)
            ),
            "translucent_ab_panel": shape_delta(
                shape_summary(ab_source.Shape), shape_summary(panel.Shape)
            ),
        }
        source_mesh_summary = mesh_summary(lower_mesh_source.Mesh)
        copied_mesh_summary = mesh_summary(lower_mesh.Mesh)
        context_copy_passes = all(
            record["volume_mm3"] <= float(numeric["maximum_copy_volume_delta_mm3"])
            and record["bounds_mm"] <= float(numeric["maximum_copy_bound_delta_mm"])
            for record in context_checks.values()
        ) and source_mesh_summary == copied_mesh_summary

        expected_volume = sum(
            float(source_summaries[identifier]["volume_mm3"])
            for identifier in retained_ids
        )
        copied_volume = sum(
            float(copied_summaries[identifier]["volume_mm3"])
            for identifier in retained_ids
        )
        retained_summary = shape_summary(retained_compound)
        expected_faces = sum(
            int(source_summaries[identifier]["face_count"])
            for identifier in retained_ids
        )
        checks = {
            "input_hashes_match": True,
            "accepted_v25_validation_passes": True,
            "source_manifest_is_c001_through_c042": set(components) == expected_ids,
            "target_is_exact_separate_c009": bool(source_c009.isValid())
            and bool(source_c009.isClosed())
            and len(source_c009.Solids) == 1,
            "retained_manifest_is_exactly_v25_minus_c009": set(output_component_names)
            == retained_ids,
            "retained_component_count_is_41": len(output_component_names)
            == int(numeric["retained_component_count"]),
            "c009_absent_from_review_component_map": "C009"
            not in output_component_names,
            "all_retained_component_copies_exact": not copy_failures,
            "retained_compound_valid": bool(retained_compound.isValid()),
            "retained_compound_closed": bool(retained_compound.isClosed()),
            "retained_compound_has_41_solids": len(retained_compound.Solids)
            == int(numeric["retained_component_count"]),
            "retained_compound_face_count_is_source_minus_c009": len(
                retained_compound.Faces
            )
            == expected_faces,
            "retained_component_volume_sum_matches_source_minus_c009": abs(
                copied_volume - expected_volume
            )
            <= float(numeric["maximum_copy_volume_delta_mm3"]),
            "repaired_eye_valid_closed_one_solid": bool(eye.isValid())
            and bool(eye.isClosed())
            and len(eye.Solids) == 1,
            "full_context_copies_exact": context_copy_passes,
            "no_subtractive_cut_performed": True,
            "no_replacement_or_support_geometry_added": True,
            "no_mirror_union_or_export_performed": True,
        }
        passed = all(checks.values())
        print("STAGE 5/8 deletion and preservation gates evaluated", flush=True)

        result = {
            "schema_version": "1.0",
            "generator": "freecad-right-upper-c009-deletion-review-v34",
            "freecad_version": App.Version(),
            "contract_id": contract["contract_id"],
            "status": "PASS__REVIEW_ONLY_ONE_SIDED_C009_DELETION"
            if passed
            else "FAIL__NO_REVIEW_FILE_SAVED",
            "input_hashes": actual_hashes,
            "implementation_dependency_hash": dependency_hash,
            "operation": {
                "target_component": "C009",
                "method": "manifest_omission_of_separate_component",
                "subtractive_cut": False,
                "replacement_geometry_count": 0,
                "added_support_geometry_count": 0,
                "source_c009": {
                    "object_name": components["C009"].Name,
                    "object_label": components["C009"].Label,
                    "shape": source_summaries["C009"],
                    "repaired_eye_intersection_volume_mm3": source_c009_eye_intersection,
                },
            },
            "source_manifest": sorted(expected_ids),
            "retained_manifest": sorted(retained_ids),
            "retained_compound": retained_summary,
            "volume_ledger_mm3": {
                "source_v25_compound": float(source_compound.Volume),
                "removed_c009": float(source_c009.Volume),
                "retained_source_component_sum": expected_volume,
                "retained_copied_component_sum": copied_volume,
                "retained_review_compound": float(retained_compound.Volume),
                "note": "Preservation gate compares exact per-component sums; OCCT compound volume can vary slightly with compound ordering.",
            },
            "retained_eye_intersections": retained_eye_intersections,
            "known_hold": "Residual eye intersections from retained members are not modified or approved by V34.",
            "copy_failures": copy_failures,
            "context_copy_deltas": context_checks,
            "lower_context_mesh": {
                "source": source_mesh_summary,
                "copy": copied_mesh_summary,
            },
            "checks": checks,
            "review_display": contract["review_display"],
            "release_holds": contract["release_holds"],
            "review_objects": {
                "component_objects": output_component_names,
                "eye_object": eye_object.Name,
                "lower_main_object": lower_main.Name,
                "lower_components_mesh_object": lower_mesh.Name,
                "right_primary_ear_object": ear.Name,
                "translucent_ab_panel_object": panel.Name,
                "retained_upper_shape_object_count": 41,
                "full_context_shape_object_count": 5,
                "total_shape_object_count": 46,
                "c009_shape_object_count": 0,
                "added_geometry_count": 0,
            },
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
            raise RuntimeError(f"V34 gates failed: {checks}")

        print("STAGE 6/8 review object manifest finalized", flush=True)
        review_document.saveAs(str(review_path))
        result["outputs"]["fcstd_sha256"] = sha256_file(review_path)
        validation_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("STAGE 7/8 review file and validation saved", flush=True)
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "fcstd": str(review_path),
                    "validation": str(validation_path),
                },
                indent=2,
            ),
            flush=True,
        )
        print("STAGE 8/8 complete", flush=True)
    finally:
        if review_document is not None:
            App.closeDocument(review_document.Name)
        for document in (
            accepted_document,
            full_context_document,
            ear_document,
            ab_document,
        ):
            App.closeDocument(document.Name)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
