#!/usr/bin/env python3
"""Audit non-additive C001/C009 eye-clearance routes.

The script opens hash-pinned inputs read-only, creates only transient in-memory
measurement shapes, and writes deterministic JSON. It never saves CAD, exports
geometry, changes a source document, mirrors, performs a production union, or
authorizes deletion of C009.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import FreeCAD as App
import Part


COMPONENT_PATTERN = re.compile(r"__C(\d{3})_")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
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


def vector(values) -> list[float]:
    return [float(values.x), float(values.y), float(values.z)]


def bbox(shape) -> dict[str, list[float]]:
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
        "volume_mm3": float(shape.Volume),
        "bounds": bbox(shape),
    }


def component_id(obj) -> str | None:
    text = f"{obj.Name} {obj.Label}"
    if "UPPER_C012" in text:
        return "C012"
    if "UPPER_C027" in text:
        return "C027"
    match = COMPONENT_PATTERN.search(text)
    return f"C{match.group(1)}" if match else None


def find_components(document) -> dict[str, object]:
    components: dict[str, object] = {}
    for obj in document.Objects:
        if not hasattr(obj, "Shape") or obj.Shape.isNull():
            continue
        identifier = component_id(obj)
        if identifier is None:
            continue
        if identifier in components:
            raise RuntimeError(f"duplicate upper component {identifier}")
        components[identifier] = obj
    return components


def common_volume(first, second) -> float:
    return float(first.common(second).Volume)


def boxes_overlap(first, second, margin: float) -> bool:
    a = first.BoundBox
    b = second.BoundBox
    return not (
        a.XMax + margin < b.XMin
        or b.XMax + margin < a.XMin
        or a.YMax + margin < b.YMin
        or b.YMax + margin < a.YMin
        or a.ZMax + margin < b.ZMin
        or b.ZMax + margin < a.ZMin
    )


def make_clearance_offset(eye, numeric):
    distance = float(numeric["minimum_eye_clearance_mm"])
    tolerances = [
        float(numeric["offset_tolerance_mm"]),
        float(numeric["fallback_offset_tolerance_mm"]),
    ]
    attempts = []
    for tolerance in tolerances:
        try:
            offset = eye.makeOffsetShape(
                distance,
                tolerance,
                False,
                False,
                0,
                0,
                True,
            )
            summary = shape_summary(offset)
            contains_source_remainder = float(eye.cut(offset).Volume)
            attempts.append(
                {
                    "tolerance_mm": tolerance,
                    "succeeded": True,
                    "summary": summary,
                    "source_outside_offset_volume_mm3": contains_source_remainder,
                }
            )
            if (
                summary["valid"]
                and summary["closed"]
                and summary["solid_count"] == 1
                and contains_source_remainder <= 1.0e-6
            ):
                return offset, attempts
        except Exception as exc:
            attempts.append(
                {
                    "tolerance_mm": tolerance,
                    "succeeded": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return None, attempts


def owner_contact(shape, neighbor, threshold: float) -> dict[str, float | bool]:
    distance = float(shape.distToShape(neighbor)[0])
    overlap = common_volume(shape, neighbor) if distance <= 1.0e-7 else 0.0
    return {
        "distance_mm": distance,
        "intersection_volume_mm3": overlap,
        "positive": overlap > threshold,
    }


def main() -> int:
    args = parse_args()
    root = repository_root(args.contract)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    accepted = contract["accepted_context"]
    eye_contract = contract["replacement_eye"]
    prior = contract["prior_audit"]
    numeric = contract["numeric_contract"]

    accepted_path = root / accepted["path"]
    eye_path = root / eye_contract["path"]
    prior_path = root / prior["path"]
    expected_hashes = {
        "accepted_context_fcstd": accepted["sha256"],
        "replacement_eye_step": eye_contract["sha256"],
        "prior_v29_validation": prior["sha256"],
    }
    actual_hashes = {
        "accepted_context_fcstd": sha256_file(accepted_path),
        "replacement_eye_step": sha256_file(eye_path),
        "prior_v29_validation": sha256_file(prior_path),
    }
    if actual_hashes != expected_hashes:
        raise RuntimeError(f"hash-pinned input mismatch: {actual_hashes}")

    output_dir = root / contract["output"]["directory"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    print("STAGE 1/7 contract and hashes verified", flush=True)

    eye = Part.Shape()
    eye.read(str(eye_path))
    if eye.isNull():
        raise RuntimeError("replacement eye STEP imported as a null shape")
    print("STAGE 2/7 repaired eye imported", flush=True)

    document = App.openDocument(str(accepted_path))
    try:
        components = find_components(document)
        expected_ids = {f"C{index:03d}" for index in range(1, 43)}
        if set(components) != expected_ids:
            raise RuntimeError("accepted V25 component manifest mismatch")
        c001 = components["C001"].Shape
        c009 = components["C009"].Shape
        print("STAGE 3/7 accepted C001/C009 owners identified", flush=True)

        offset, offset_attempts = make_clearance_offset(eye, numeric)
        print("STAGE 4/7 transient eye-clearance offset attempted", flush=True)

        threshold = float(numeric["positive_intersection_threshold_mm3"])
        min_contact = float(numeric["minimum_preserved_owner_contact_mm3"])
        max_loss_fraction = float(numeric["maximum_contact_loss_fraction"])
        margin = float(numeric["bounding_box_filter_margin_mm"])

        c001_route = {
            "status": "FAIL__NO_VALID_CLEARANCE_OFFSET",
            "source": shape_summary(c001),
            "offset_attempts": offset_attempts,
            "geometry_artifact_created": False,
        }
        if offset is not None:
            removal = c001.common(offset)
            candidate = c001.cut(offset).removeSplitter()
            candidate_summary = shape_summary(candidate)
            eye_clearance = float(candidate.distToShape(eye)[0])
            removed_summary = shape_summary(removal) if not removal.isNull() else None
            changed_contacts = {}
            preserved_positive_contacts = []
            lost_positive_contacts = []
            excessive_contact_losses = []
            for identifier, obj in sorted(components.items()):
                if identifier == "C001":
                    continue
                neighbor = obj.Shape
                if not boxes_overlap(removal, neighbor, margin):
                    continue
                before = owner_contact(c001, neighbor, threshold)
                after = owner_contact(candidate, neighbor, threshold)
                before_volume = float(before["intersection_volume_mm3"])
                after_volume = float(after["intersection_volume_mm3"])
                loss_fraction = (
                    max(0.0, before_volume - after_volume) / before_volume
                    if before_volume > threshold
                    else 0.0
                )
                changed_contacts[identifier] = {
                    "before": before,
                    "after": after,
                    "loss_fraction": loss_fraction,
                }
                if before_volume > threshold:
                    if after_volume >= min_contact:
                        preserved_positive_contacts.append(identifier)
                    else:
                        lost_positive_contacts.append(identifier)
                    if loss_fraction > max_loss_fraction:
                        excessive_contact_losses.append(identifier)

            topology_pass = (
                candidate_summary["valid"]
                and candidate_summary["closed"]
                and candidate_summary["solid_count"] == 1
            )
            clearance_pass = (
                eye_clearance + 1.0e-6
                >= float(numeric["minimum_eye_clearance_mm"])
            )
            contacts_pass = not lost_positive_contacts and not excessive_contact_losses
            route_pass = topology_pass and clearance_pass and contacts_pass
            c001_route = {
                "status": (
                    "PASS__TRANSIENT_NON_ADDITIVE_ROUTE"
                    if route_pass
                    else "FAIL__TRANSIENT_NON_ADDITIVE_ROUTE"
                ),
                "source": shape_summary(c001),
                "clearance_offset": shape_summary(offset),
                "offset_attempts": offset_attempts,
                "removed_region": removed_summary,
                "removed_volume_fraction": float(removal.Volume / c001.Volume),
                "transient_candidate": candidate_summary,
                "resulting_eye_clearance_mm": eye_clearance,
                "topology_pass": topology_pass,
                "clearance_pass": clearance_pass,
                "contacts_pass": contacts_pass,
                "changed_or_near_owner_contacts": changed_contacts,
                "preserved_positive_contacts": preserved_positive_contacts,
                "lost_positive_contacts": lost_positive_contacts,
                "excessive_contact_losses": excessive_contact_losses,
                "geometry_artifact_created": False,
            }
        print("STAGE 5/7 transient C001 subtraction audited", flush=True)

        c009_neighbors = {}
        for identifier, obj in sorted(components.items()):
            if identifier == "C009":
                continue
            contact = owner_contact(c009, obj.Shape, threshold)
            if contact["positive"] or contact["distance_mm"] < 1.0:
                c009_neighbors[identifier] = contact
        c009_positive_neighbors = sorted(
            identifier
            for identifier, contact in c009_neighbors.items()
            if contact["positive"]
        )
        c009_route = {
            "source": shape_summary(c009),
            "eye_contact": owner_contact(c009, eye, threshold),
            "near_or_positive_upper_neighbors": c009_neighbors,
            "positive_upper_neighbors": c009_positive_neighbors,
            "single_owner_attachment_only": c009_positive_neighbors == ["C001"],
            "geometric_deletion_would_not_modify_other_shapes": True,
            "structural_function_proven_redundant": False,
            "status": "HOLD__STRUCTURAL_FUNCTION_UNRESOLVED",
            "deletion_authorized": False,
        }
        print("STAGE 6/7 C009 deletion consequences classified", flush=True)

        c001_pass = c001_route["status"] == "PASS__TRANSIENT_NON_ADDITIVE_ROUTE"
        result = {
            "schema_version": "1.0",
            "generator": "freecad-right-upper-c001-c009-non-additive-route-audit-v30",
            "freecad_version": App.Version(),
            "contract_id": contract["contract_id"],
            "status": (
                "PASS__C001_ROUTE_FOUND_C009_HELD"
                if c001_pass
                else "FAIL__NO_COMPLETE_NON_ADDITIVE_ROUTE"
            ),
            "input_hashes": actual_hashes,
            "c001_non_additive_route": c001_route,
            "c009_deletion_route": c009_route,
            "interpretation": {
                "v27_geometry_used": False,
                "visible_add_on_geometry_created": False,
                "c001_route_is_measurement_only": True,
                "c009_deletion_authorized": False,
                "production_geometry_modified": False,
            },
            "release_holds": contract["release_holds"],
            "outputs": {
                "validation": str(validation_path.relative_to(root)),
                "geometry_artifact_created": False,
                "upper_geometry_modified": False,
                "mirrored": False,
                "production_union_created": False,
                "stl_exported": False,
                "sliced": False,
            },
        }
        output_dir.mkdir(parents=True)
        validation_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print("STAGE 7/7 deterministic validation JSON saved", flush=True)
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "c001_status": c001_route["status"],
                    "c001_eye_clearance_mm": c001_route.get(
                        "resulting_eye_clearance_mm"
                    ),
                    "c001_lost_contacts": c001_route.get(
                        "lost_positive_contacts", []
                    ),
                    "c009_status": c009_route["status"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if c001_pass else 1
    finally:
        App.closeDocument(document.Name)


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
