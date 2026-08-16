#!/usr/bin/env python3
"""Audit rigid-translation routes for the existing V26 rail and C009.

The script opens hash-pinned inputs read-only, copies exact existing shapes in
memory, searches translations without rotation or deformation, and writes
deterministic JSON. It never saves CAD or exports geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import FreeCAD as App
import Part

from audit_right_upper_c001_c009_existing_body_routes import (
    bbox,
    choose_v26_rail,
    common_volume,
    enumerate_v26_solids,
    find_components,
    repository_root,
    sha256_file,
    shape_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    return parser.parse_args()


def vector(values) -> list[float]:
    return [float(values.x), float(values.y), float(values.z)]


def make_unit(values) -> App.Vector | None:
    candidate = App.Vector(float(values[0]), float(values[1]), float(values[2]))
    if candidate.Length <= 1.0e-12:
        return None
    candidate.normalize()
    return candidate


def vector_key(candidate: App.Vector) -> tuple[float, float, float]:
    return (
        round(float(candidate.x), 9),
        round(float(candidate.y), 9),
        round(float(candidate.z), 9),
    )


def translation_key(candidate: App.Vector) -> tuple[float, float, float]:
    return (
        round(float(candidate.x), 6),
        round(float(candidate.y), 6),
        round(float(candidate.z), 6),
    )


def scaled(candidate: App.Vector, factor: float) -> App.Vector:
    return App.Vector(
        float(candidate.x) * factor,
        float(candidate.y) * factor,
        float(candidate.z) * factor,
    )


def plus(first: App.Vector, second: App.Vector) -> App.Vector:
    return App.Vector(
        float(first.x) + float(second.x),
        float(first.y) + float(second.y),
        float(first.z) + float(second.z),
    )

def shape_center(shape) -> App.Vector:
    solids = list(shape.Solids)
    total_volume = sum(float(solid.Volume) for solid in solids)
    if total_volume > 1.0e-12:
        return App.Vector(
            sum(float(solid.CenterOfMass.x) * float(solid.Volume) for solid in solids)
            / total_volume,
            sum(float(solid.CenterOfMass.y) * float(solid.Volume) for solid in solids)
            / total_volume,
            sum(float(solid.CenterOfMass.z) * float(solid.Volume) for solid in solids)
            / total_volume,
        )
    bounds = shape.BoundBox
    return App.Vector(
        (float(bounds.XMin) + float(bounds.XMax)) * 0.5,
        (float(bounds.YMin) + float(bounds.YMax)) * 0.5,
        (float(bounds.ZMin) + float(bounds.ZMax)) * 0.5,
    )



def swept_face_proxy(target, moving, travel: float, padding: float):
    bounds = moving.BoundBox
    minimum = (
        float(bounds.XMin) - travel - padding,
        float(bounds.YMin) - travel - padding,
        float(bounds.ZMin) - travel - padding,
    )
    maximum = (
        float(bounds.XMax) + travel + padding,
        float(bounds.YMax) + travel + padding,
        float(bounds.ZMax) + travel + padding,
    )
    faces = []
    for face in target.Faces:
        candidate = face.BoundBox
        overlaps = (
            float(candidate.XMax) >= minimum[0]
            and float(candidate.XMin) <= maximum[0]
            and float(candidate.YMax) >= minimum[1]
            and float(candidate.YMin) <= maximum[1]
            and float(candidate.ZMax) >= minimum[2]
            and float(candidate.ZMin) <= maximum[2]
        )
        if overlaps:
            faces.append(face)
    if not faces:
        raise RuntimeError("no target faces overlap the bounded translation envelope")
    return Part.makeCompound(faces), {
        "source_face_count": len(target.Faces),
        "proxy_face_count": len(faces),
        "travel_envelope_mm": travel,
        "padding_mm": padding,
    }

def add_direction(
    directions: dict[tuple[float, float, float], App.Vector],
    values,
) -> None:
    candidate = make_unit(values)
    if candidate is not None:
        directions[vector_key(candidate)] = candidate


def closest_vector(first, second) -> App.Vector | None:
    distance, pairs, _ = first.distToShape(second)
    if distance <= 1.0e-9 or not pairs:
        return None
    first_point, second_point = pairs[0]
    candidate = App.Vector(
        float(second_point.x) - float(first_point.x),
        float(second_point.y) - float(first_point.y),
        float(second_point.z) - float(first_point.z),
    )
    return candidate if candidate.Length > 1.0e-12 else None


def candidate_directions(member, owner, eye) -> list[App.Vector]:
    directions: dict[tuple[float, float, float], App.Vector] = {}

    toward_owner = closest_vector(member, owner)
    if toward_owner is None:
        owner_center = shape_center(owner)
        member_center = shape_center(member)
        toward_owner = App.Vector(
            float(owner_center.x) - float(member_center.x),
            float(owner_center.y) - float(member_center.y),
            float(owner_center.z) - float(member_center.z),
        )
    away_eye = closest_vector(eye, member)
    if away_eye is None:
        member_center = shape_center(member)
        eye_center = shape_center(eye)
        away_eye = App.Vector(
            float(member_center.x) - float(eye_center.x),
            float(member_center.y) - float(eye_center.y),
            float(member_center.z) - float(eye_center.z),
        )

    anchor_vectors = [toward_owner, away_eye]
    for anchor in anchor_vectors:
        add_direction(directions, vector(anchor))
        add_direction(directions, [-value for value in vector(anchor)])

    owner_unit = make_unit(vector(toward_owner))
    eye_unit = make_unit(vector(away_eye))
    if owner_unit is not None and eye_unit is not None:
        for owner_weight in (0.5, 1.0, 2.0):
            for eye_weight in (0.5, 1.0, 2.0):
                combination = plus(
                    scaled(owner_unit, owner_weight),
                    scaled(eye_unit, eye_weight),
                )
                add_direction(directions, vector(combination))
                add_direction(directions, [-value for value in vector(combination)])

        cross = owner_unit.cross(eye_unit)
        if cross.Length > 1.0e-12:
            add_direction(directions, vector(cross))
            add_direction(directions, [-value for value in vector(cross)])
            for sign in (-1.0, 1.0):
                lateral = scaled(cross, sign)
                add_direction(
                    directions,
                    vector(plus(owner_unit, scaled(lateral, 0.5))),
                )
                add_direction(
                    directions,
                    vector(plus(eye_unit, scaled(lateral, 0.5))),
                )

    return [directions[key] for key in sorted(directions)]


def translated_shape(source, translation: App.Vector):
    candidate = source.copy()
    candidate.translate(translation)
    return candidate


def compact_probe(probe: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in probe.items()
        if key not in {"shape", "score"}
    }


def audit_member(
    name: str,
    source,
    owner,
    eye,
    obstacles: dict[str, object],
    numeric: dict[str, object],
) -> dict[str, object]:
    minimum_eye = float(numeric["minimum_eye_clearance_mm"])
    minimum_overlap = float(numeric["minimum_owner_overlap_mm3"])
    positive_threshold = float(numeric["positive_intersection_threshold_mm3"])
    contact_distance = float(numeric["owner_contact_distance_tolerance_mm"])
    maximum_translation = float(numeric["maximum_translation_mm"])
    sample_lengths = [float(value) for value in numeric["direction_sample_lengths_mm"]]
    refinement_steps = [float(value) for value in numeric["refinement_steps_mm"]]
    seed_count = int(numeric["refinement_seed_count"])
    refinement_cycles = int(numeric["refinement_cycles_per_step"])
    report_count = int(numeric["report_candidate_count"])

    eye_proxy, eye_proxy_summary = swept_face_proxy(
        eye,
        source,
        maximum_translation,
        minimum_eye,
    )
    owner_proxy, owner_proxy_summary = swept_face_proxy(
        owner,
        source,
        maximum_translation,
        contact_distance,
    )
    cache: dict[tuple[float, float, float], dict[str, object]] = {}

    def probe(translation: App.Vector) -> dict[str, object] | None:
        if translation.Length > maximum_translation + 1.0e-9:
            return None
        key = translation_key(translation)
        if key in cache:
            return cache[key]
        exact_translation = App.Vector(*key)
        shape = translated_shape(source, exact_translation)
        eye_distance = float(shape.distToShape(eye_proxy)[0])
        owner_distance = float(shape.distToShape(owner_proxy)[0])
        eye_deficit = max(0.0, minimum_eye - eye_distance)
        score = (
            eye_deficit * 1000.0
            + owner_distance * 20.0
            + exact_translation.Length * 0.01
        )
        result = {
            "translation_mm": vector(exact_translation),
            "translation_length_mm": float(exact_translation.Length),
            "eye_distance_mm": eye_distance,
            "owner_distance_mm": owner_distance,
            "meets_distance_prefilter": (
                eye_distance + 1.0e-9 >= minimum_eye
                and owner_distance <= contact_distance
            ),
            "score": score,
            "shape": shape,
        }
        cache[key] = result
        return result

    zero = probe(App.Vector(0.0, 0.0, 0.0))
    directions = candidate_directions(source, owner, eye)
    sample_lengths = [value for value in sample_lengths if value <= maximum_translation]
    for direction in directions:
        for distance in sample_lengths:
            probe(scaled(direction, distance))

    initial = sorted(
        cache.values(),
        key=lambda item: (
            item["score"],
            item["translation_length_mm"],
            item["translation_mm"],
        ),
    )[:seed_count]

    neighbor_directions = []
    for axis in range(3):
        for sign in (-1.0, 1.0):
            values = [0.0, 0.0, 0.0]
            values[axis] = sign
            neighbor_directions.append(App.Vector(*values))

    for seed in initial:
        current = App.Vector(*seed["translation_mm"])
        current_probe = seed
        for step in refinement_steps:
            for _ in range(refinement_cycles):
                neighbors = [current_probe]
                for direction in neighbor_directions:
                    neighbor = probe(plus(current, scaled(direction, step)))
                    if neighbor is not None:
                        neighbors.append(neighbor)
                winner = min(
                    neighbors,
                    key=lambda item: (
                        item["score"],
                        item["translation_length_mm"],
                        item["translation_mm"],
                    ),
                )
                if winner["translation_mm"] == current_probe["translation_mm"]:
                    break
                current_probe = winner
                current = App.Vector(*winner["translation_mm"])

    prefiltered = [
        item for item in cache.values() if item["meets_distance_prefilter"]
    ]
    accepted = []
    for item in sorted(
        prefiltered,
        key=lambda entry: (
            entry["translation_length_mm"],
            entry["translation_mm"],
        ),
    ):
        shape = item["shape"]
        exact_eye_distance = float(shape.distToShape(eye)[0])
        exact_owner_distance = float(shape.distToShape(owner)[0])
        if exact_eye_distance + 1.0e-9 < minimum_eye:
            continue
        if exact_owner_distance > contact_distance:
            continue
        owner_overlap = common_volume(shape, owner)
        if owner_overlap + 1.0e-12 < minimum_overlap:
            continue
        collisions = {}
        for identifier, obstacle in sorted(obstacles.items()):
            distance = float(shape.distToShape(obstacle)[0])
            overlap = (
                common_volume(shape, obstacle)
                if distance <= contact_distance
                else 0.0
            )
            if overlap > positive_threshold:
                collisions[identifier] = {
                    "intersection_volume_mm3": overlap,
                    "distance_mm": distance,
                }
        candidate = {
            **compact_probe(item),
            "owner_overlap_mm3": owner_overlap,
            "eye_distance_mm": exact_eye_distance,
            "owner_distance_mm": exact_owner_distance,
            "other_component_collisions": collisions,
            "clear_of_other_components": not collisions,
            "translated_shape": shape_summary(shape),
        }
        accepted.append(candidate)

    clean = [item for item in accepted if item["clear_of_other_components"]]
    clean.sort(
        key=lambda item: (
            item["translation_length_mm"],
            -item["owner_overlap_mm3"],
            item["translation_mm"],
        )
    )
    ranked = sorted(
        cache.values(),
        key=lambda item: (
            item["score"],
            item["translation_length_mm"],
            item["translation_mm"],
        ),
    )
    return {
        "member": name,
        "source": shape_summary(source),
        "initial_position": compact_probe(zero),
        "candidate_direction_count": len(directions),
        "distance_probe_count": len(cache),
        "bounded_distance_search": {
            "uses_exact_local_face_proxies": True,
            "eye": eye_proxy_summary,
            "owner": owner_proxy_summary,
        },
        "distance_prefilter_count": len(prefiltered),
        "owner_overlap_candidate_count": len(accepted),
        "clean_route_count": len(clean),
        "preferred_clean_route": clean[0] if clean else None,
        "best_distance_candidates": [
            compact_probe(item) for item in ranked[:report_count]
        ],
        "best_owner_overlap_candidates": accepted[:report_count],
    }


def main() -> int:
    args = parse_args()
    root = repository_root(args.contract)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))

    input_specs = contract["inputs"]
    actual_hashes = {}
    for identifier, spec in input_specs.items():
        path = root / spec["path"]
        actual_hashes[identifier] = sha256_file(path)
        if actual_hashes[identifier] != spec["sha256"]:
            raise RuntimeError(
                f"hash-pinned input mismatch for {identifier}: "
                f"{actual_hashes[identifier]}"
            )

    dependency = contract["implementation_dependency"]
    dependency_path = root / dependency["path"]
    dependency_hash = sha256_file(dependency_path)
    if dependency_hash != dependency["sha256"]:
        raise RuntimeError("V29 helper dependency hash mismatch")

    output_dir = root / contract["output"]["directory"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    output_dir.mkdir(parents=True)
    print("STAGE 1/7 contract and hashes verified", flush=True)

    eye = Part.Shape()
    eye.read(str(root / input_specs["replacement_eye_step"]["path"]))
    if eye.isNull():
        raise RuntimeError("replacement eye STEP imported as a null shape")
    print("STAGE 2/7 repaired eye imported", flush=True)

    accepted_document = App.openDocument(
        str(root / input_specs["accepted_context_fcstd"]["path"])
    )
    diagnostic_document = App.openDocument(
        str(root / input_specs["v26_diagnostic_fcstd"]["path"])
    )
    try:
        components = find_components(accepted_document)
        expected_ids = {f"C{index:03d}" for index in range(1, 43)}
        if set(components) != expected_ids:
            raise RuntimeError("accepted V25 component manifest mismatch")
        c001 = components["C001"].Shape
        c009 = components["C009"].Shape
        print("STAGE 3/7 accepted C001/C009 owners identified", flush=True)

        diagnostic = contract["v26_rail_identification"]
        rail_match, _ = choose_v26_rail(
            enumerate_v26_solids(diagnostic_document),
            eye,
            c001,
            diagnostic,
        )
        rail = rail_match["shape"]
        print("STAGE 4/7 exact V26 offset rail identified", flush=True)

        rail_obstacles = {
            identifier: obj.Shape
            for identifier, obj in components.items()
            if identifier != "C001"
        }
        c009_obstacles = {
            identifier: obj.Shape
            for identifier, obj in components.items()
            if identifier not in {"C001", "C009"}
        }
        numeric = contract["numeric_contract"]
        rail_result = audit_member(
            "V26_TAPERED_RAIL",
            rail,
            c001,
            eye,
            rail_obstacles,
            numeric,
        )
        print("STAGE 5/7 V26 rail translations audited", flush=True)
        c009_result = audit_member(
            "C009",
            c009,
            c001,
            eye,
            c009_obstacles,
            numeric,
        )
        print("STAGE 6/7 C009 translations audited", flush=True)

        both_clean = (
            rail_result["clean_route_count"] > 0
            and c009_result["clean_route_count"] > 0
        )
        one_clean = (
            rail_result["clean_route_count"] > 0
            or c009_result["clean_route_count"] > 0
        )
        status = (
            "PASS__BOTH_EXISTING_MEMBERS_HAVE_INDEPENDENT_TRANSLATION_ROUTES"
            if both_clean
            else (
                "PARTIAL__ONE_EXISTING_MEMBER_HAS_A_TRANSLATION_ROUTE"
                if one_clean
                else "FAIL__NO_CLEAN_EXISTING_MEMBER_TRANSLATION_ROUTE"
            )
        )
        result = {
            "schema_version": "1.0",
            "generator": "freecad-right-upper-existing-member-reposition-route-audit-v31",
            "freecad_version": App.Version(),
            "contract_id": contract["contract_id"],
            "status": status,
            "input_hashes": actual_hashes,
            "implementation_dependency_hash": dependency_hash,
            "v26_rail_match": {
                key: value
                for key, value in rail_match.items()
                if key != "shape"
            },
            "v26_tapered_rail": rail_result,
            "c009": c009_result,
            "interpretation": {
                "routes_are_independent": True,
                "simultaneous_route_compatibility_audited": False,
                "rotation_or_deformation_used": False,
                "v27_geometry_used": False,
                "geometry_artifact_created": False,
                "geometry_change_authorized": False,
            },
            "release_holds": contract["release_holds"],
            "outputs": {
                "validation": str(validation_path.relative_to(root)),
                "geometry_artifact_created": False,
                "upper_geometry_modified": False,
                "mirrored": False,
                "production_union_created": False,
                "step_or_stl_exported": False,
                "sliced": False,
            },
        }
        validation_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("STAGE 7/7 deterministic validation JSON saved", flush=True)
        print(
            json.dumps(
                {
                    "status": status,
                    "rail_clean_route_count": rail_result["clean_route_count"],
                    "rail_preferred": rail_result["preferred_clean_route"],
                    "c009_clean_route_count": c009_result["clean_route_count"],
                    "c009_preferred": c009_result["preferred_clean_route"],
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if both_clean else 1
    finally:
        App.closeDocument(diagnostic_document.Name)
        App.closeDocument(accepted_document.Name)


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
