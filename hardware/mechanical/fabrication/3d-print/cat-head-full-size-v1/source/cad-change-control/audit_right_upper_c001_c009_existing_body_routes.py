#!/usr/bin/env python3
"""Audit existing-body correction routes for right-upper C001 and C009.

The script opens hash-pinned inputs read-only and writes deterministic JSON.
It may create transient in-memory measurement sweeps, but it never changes a
document, saves CAD, exports geometry, mirrors, unions production owners, or
reuses the rejected V27 construction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
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


def planar_face_normal(face):
    if not isinstance(face.Surface, Part.Plane):
        return None
    u_min, u_max, v_min, v_max = face.ParameterRange
    normal = face.normalAt((u_min + u_max) / 2.0, (v_min + v_max) / 2.0)
    if normal.Length <= 0.0:
        return None
    normal.normalize()
    return normal


def face_summary(index: int, face) -> dict[str, object]:
    normal = planar_face_normal(face)
    return {
        "face": f"Face{index}",
        "area_mm2": float(face.Area),
        "centroid_mm": vector(face.CenterOfMass),
        "planar": normal is not None,
        "normal": vector(normal) if normal is not None else None,
    }


def common_volume(first, second) -> float:
    return float(first.common(second).Volume)


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


def enumerate_v26_solids(document) -> list[dict[str, object]]:
    solids = []
    for obj in document.Objects:
        if not hasattr(obj, "Shape") or obj.Shape.isNull():
            continue
        for index, solid in enumerate(obj.Shape.Solids, start=1):
            solids.append(
                {
                    "object_name": obj.Name,
                    "object_label": obj.Label,
                    "solid_index": index,
                    "shape": solid,
                    "volume_mm3": float(solid.Volume),
                    "bounds": bbox(solid),
                }
            )
    return solids


def choose_v26_rail(solids, eye, main, settings):
    candidates = []
    target_volume = float(settings["rail_volume_target_mm3"])
    volume_tolerance = float(settings["rail_volume_tolerance_mm3"])
    eye_target = float(settings["rail_eye_clearance_target_mm"])
    main_target = float(settings["rail_main_gap_target_mm"])
    distance_tolerance = float(settings["distance_match_tolerance_mm"])
    offset = App.Vector(*[float(value) for value in settings["diagnostic_offset_mm"]])
    for item in solids:
        if abs(item["volume_mm3"] - target_volume) > volume_tolerance:
            continue
        shape = item["shape"].copy()
        source_bounds = bbox(shape)
        shape.translate(offset)
        eye_distance = float(shape.distToShape(eye)[0])
        main_distance = float(shape.distToShape(main)[0])
        score = abs(eye_distance - eye_target) + abs(main_distance - main_target)
        candidates.append(
            {
                **item,
                "source_bounds": source_bounds,
                "transient_diagnostic_offset_mm": vector(offset),
                "bounds": bbox(shape),
                "shape": shape,
                "eye_distance_mm": eye_distance,
                "main_distance_mm": main_distance,
                "match_score_mm": score,
            }
        )
    candidates.sort(key=lambda item: item["match_score_mm"])
    if not candidates:
        raise RuntimeError("no V26 rail-volume candidate found")
    winner = candidates[0]
    if winner["match_score_mm"] > 2.0 * distance_tolerance:
        raise RuntimeError(
            f"best V26 rail candidate does not match checkpoint distances: {winner}"
        )
    return winner, candidates


def transient_extension(face, direction, length_mm: float):
    displacement = App.Vector(
        direction.x * length_mm,
        direction.y * length_mm,
        direction.z * length_mm,
    )
    return face.extrude(displacement)


def route_measurement(
    face,
    direction,
    length_mm,
    rail,
    main,
    eye,
    *,
    check_rail=False,
    measure_main=True,
    measure_eye=True,
):
    sweep = transient_extension(face, direction, length_mm)
    rail_overlap = common_volume(sweep, rail) if check_rail else 0.0
    main_distance = float(sweep.distToShape(main)[0]) if measure_main else None
    main_overlap = (
        common_volume(sweep, main)
        if measure_main and main_distance <= 1.0e-7
        else 0.0
    )
    eye_distance = float(sweep.distToShape(eye)[0]) if measure_eye else None
    return {
        "sweep": sweep,
        "length_mm": float(length_mm),
        "volume_mm3": float(sweep.Volume),
        "main_distance_mm": main_distance,
        "rail_overlap_mm3": rail_overlap,
        "main_overlap_mm3": main_overlap,
        "eye_overlap_mm3": 0.0,
        "eye_distance_mm": eye_distance,
    }


def audit_direct_routes(rail, main, eye, components, numeric):
    minimum_eye_clearance = float(numeric["minimum_eye_clearance_mm"])
    minimum_root_overlap = float(numeric["minimum_root_overlap_mm3"])
    positive_threshold = float(numeric["positive_intersection_threshold_mm3"])
    maximum_length = float(numeric["maximum_search_length_mm"])
    refinements = int(numeric["binary_refinement_iterations"])
    routes = []

    for face_index, face in enumerate(rail.Faces, start=1):
        normal = planar_face_normal(face)
        if normal is None:
            continue
        for sign in (1.0, -1.0):
            direction = App.Vector(normal.x * sign, normal.y * sign, normal.z * sign)
            probe = route_measurement(
                face,
                direction,
                min(0.25, maximum_length),
                rail,
                main,
                eye,
                check_rail=True,
                measure_main=False,
                measure_eye=False,
            )
            if probe["rail_overlap_mm3"] > positive_threshold:
                continue

            maximum = route_measurement(
                face,
                direction,
                maximum_length,
                rail,
                main,
                eye,
                measure_eye=False,
            )
            if maximum["main_overlap_mm3"] < minimum_root_overlap:
                continue

            low = 0.0
            high = maximum_length
            best = maximum
            for _ in range(refinements):
                midpoint = (low + high) / 2.0
                measurement = route_measurement(
                    face,
                    direction,
                    midpoint,
                    rail,
                    main,
                    eye,
                    measure_eye=False,
                )
                if measurement["main_overlap_mm3"] >= minimum_root_overlap:
                    high = midpoint
                    best = measurement
                else:
                    low = midpoint

            best = route_measurement(
                face,
                direction,
                best["length_mm"],
                rail,
                main,
                eye,
            )
            if (
                best["main_overlap_mm3"] < minimum_root_overlap
                or best["eye_distance_mm"] < minimum_eye_clearance
            ):
                continue

            other_contacts = {}
            for identifier, obj in sorted(components.items()):
                if identifier == "C001":
                    continue
                volume = common_volume(best["sweep"], obj.Shape)
                if volume > positive_threshold:
                    other_contacts[identifier] = volume
            routes.append(
                {
                    "source_face": f"Face{face_index}",
                    "source_face_area_mm2": float(face.Area),
                    "source_face_centroid_mm": vector(face.CenterOfMass),
                    "direction": vector(direction),
                    "minimum_length_mm": best["length_mm"],
                    "sweep_volume_mm3": best["volume_mm3"],
                    "rail_overlap_mm3": best["rail_overlap_mm3"],
                    "main_overlap_mm3": best["main_overlap_mm3"],
                    "eye_distance_mm": best["eye_distance_mm"],
                    "eye_overlap_mm3": best["eye_overlap_mm3"],
                    "other_upper_component_contacts": other_contacts,
                    "clear_of_other_upper_components": not other_contacts,
                }
            )
    routes.sort(
        key=lambda item: (
            not item["clear_of_other_upper_components"],
            item["minimum_length_mm"],
            item["sweep_volume_mm3"],
        )
    )
    return routes


def main() -> int:
    args = parse_args()
    root = repository_root(args.contract)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    accepted = contract["accepted_context"]
    diagnostic = contract["v26_diagnostic"]
    eye_contract = contract["replacement_eye"]

    accepted_path = root / accepted["path"]
    diagnostic_path = root / diagnostic["path"]
    eye_path = root / eye_contract["path"]
    expected_hashes = {
        "accepted_context_fcstd": accepted["sha256"],
        "v26_diagnostic_fcstd": diagnostic["sha256"],
        "replacement_eye_step": eye_contract["sha256"],
    }
    actual_hashes = {
        "accepted_context_fcstd": sha256_file(accepted_path),
        "v26_diagnostic_fcstd": sha256_file(diagnostic_path),
        "replacement_eye_step": sha256_file(eye_path),
    }
    if actual_hashes != expected_hashes:
        raise RuntimeError(f"hash-pinned input mismatch: {actual_hashes}")

    output_dir = root / contract["output"]["directory"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    output_dir.mkdir(parents=True)
    print("STAGE 1/7 contract and hashes verified", flush=True)

    eye = Part.Shape()
    eye.read(str(eye_path))
    if eye.isNull():
        raise RuntimeError("replacement eye STEP imported as a null shape")
    print("STAGE 2/7 repaired eye imported", flush=True)

    accepted_document = App.openDocument(str(accepted_path))
    diagnostic_document = App.openDocument(str(diagnostic_path))
    try:
        components = find_components(accepted_document)
        expected_ids = {f"C{index:03d}" for index in range(1, 43)}
        if set(components) != expected_ids:
            raise RuntimeError("accepted V25 component manifest mismatch")
        c001 = components["C001"].Shape
        c009 = components["C009"].Shape
        print("STAGE 3/7 accepted C001/C009 owners identified", flush=True)

        v26_solids = enumerate_v26_solids(diagnostic_document)
        rail_match, rail_candidates = choose_v26_rail(
            v26_solids, eye, c001, diagnostic
        )
        rail = rail_match["shape"]
        print("STAGE 4/7 V26 offset rail identified", flush=True)

        routes = audit_direct_routes(
            rail, c001, eye, components, contract["numeric_contract"]
        )
        print("STAGE 5/7 direct existing-face routes audited", flush=True)

        threshold = float(
            contract["numeric_contract"]["positive_intersection_threshold_mm3"]
        )
        c009_neighbors = {}
        for identifier, obj in sorted(components.items()):
            if identifier == "C009":
                continue
            volume = common_volume(c009, obj.Shape)
            distance = float(c009.distToShape(obj.Shape)[0])
            if volume > threshold or distance < 1.0:
                c009_neighbors[identifier] = {
                    "intersection_volume_mm3": volume,
                    "distance_mm": distance,
                }
        c009_eye = {
            "intersection_volume_mm3": common_volume(c009, eye),
            "distance_mm": float(c009.distToShape(eye)[0]),
        }
        c009_faces = [
            face_summary(index, face)
            for index, face in enumerate(c009.Faces, start=1)
        ]
        print("STAGE 6/7 C009 ownership neighborhood audited", flush=True)

        serializable_candidates = []
        for item in rail_candidates:
            serializable_candidates.append(
                {
                    key: value
                    for key, value in item.items()
                    if key != "shape"
                }
            )
        serializable_match = {
            key: value for key, value in rail_match.items() if key != "shape"
        }
        clean_routes = [
            route for route in routes if route["clear_of_other_upper_components"]
        ]
        c009_positive_neighbors = sorted(
            identifier
            for identifier, values in c009_neighbors.items()
            if values["intersection_volume_mm3"] > threshold
        )
        result = {
            "schema_version": "1.0",
            "generator": "freecad-right-upper-c001-c009-existing-body-route-audit-v29",
            "freecad_version": App.Version(),
            "contract_id": contract["contract_id"],
            "status": "PASS__READ_ONLY_ROUTE_EVIDENCE"
            if clean_routes
            else "FAIL__NO_CLEAN_DIRECT_ROUTE_FOUND",
            "input_hashes": actual_hashes,
            "c001": {
                "accepted_owner": shape_summary(c001),
                "v26_offset_rail": shape_summary(rail),
                "v26_offset_rail_match": serializable_match,
                "all_v26_rail_volume_candidates": serializable_candidates,
                "rail_faces": [
                    face_summary(index, face)
                    for index, face in enumerate(rail.Faces, start=1)
                ],
                "direct_existing_face_extension_routes": routes,
                "clean_direct_route_count": len(clean_routes),
                "preferred_clean_route": clean_routes[0] if clean_routes else None,
            },
            "c009": {
                "shape": shape_summary(c009),
                "eye_contact": c009_eye,
                "near_or_positive_upper_neighbors": c009_neighbors,
                "positive_upper_neighbors": c009_positive_neighbors,
                "faces": c009_faces,
                "single_owner_attachment_only": c009_positive_neighbors == ["C001"],
                "disposition": "HOLD__NO_DELETE_OR_TRIM_AUTHORIZED",
            },
            "interpretation": {
                "v27_geometry_used": False,
                "geometry_artifact_created": False,
                "direct_route_is_measurement_only": True,
                "c009_removal_authorized": False,
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
        validation_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print("STAGE 7/7 deterministic validation JSON saved", flush=True)
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "clean_direct_route_count": len(clean_routes),
                    "preferred_clean_route": result["c001"]["preferred_clean_route"],
                    "c009_positive_upper_neighbors": c009_positive_neighbors,
                    "c009_eye_contact": c009_eye,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if clean_routes else 1
    finally:
        App.closeDocument(diagnostic_document.Name)
        App.closeDocument(accepted_document.Name)


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
