#!/usr/bin/env python3
"""Read-only full-context audit of the accepted V31 C009 translation.

The script hash-pins every input, copies and translates only the existing C009
solid in memory, and writes deterministic JSON.  It never saves a CAD document
or exports geometry.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
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


def bounds(shape) -> tuple[list[float], list[float]]:
    box = shape.BoundBox
    return (
        [float(box.XMin), float(box.YMin), float(box.ZMin)],
        [float(box.XMax), float(box.YMax), float(box.ZMax)],
    )


def aabb_distance(
    first: tuple[list[float], list[float]],
    second: tuple[list[float], list[float]],
) -> float:
    squared = 0.0
    for axis in range(3):
        if first[1][axis] < second[0][axis]:
            gap = second[0][axis] - first[1][axis]
        elif second[1][axis] < first[0][axis]:
            gap = first[0][axis] - second[1][axis]
        else:
            gap = 0.0
        squared += gap * gap
    return math.sqrt(squared)


def exact_clearance_record(candidate, obstacle, threshold: float) -> dict[str, object]:
    distance = float(candidate.distToShape(obstacle)[0])
    overlap = common_volume(candidate, obstacle) if distance <= 1.0e-6 else 0.0
    return {
        "distance_mm": distance,
        "intersection_volume_mm3": overlap,
        "clear": overlap <= threshold,
        "obstacle": shape_summary(obstacle),
    }


def shape_object(document, label: str):
    matches = [
        obj
        for obj in document.Objects
        if getattr(obj, "Label", "") == label
        and hasattr(obj, "Shape")
        and not obj.Shape.isNull()
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected one shape labelled {label!r}, found {len(matches)}")
    return matches[0]


def identity_matrix() -> list[list[float]]:
    return [
        [1.0, 0.0, 0.0, 0.0],
        [0.0, 1.0, 0.0, 0.0],
        [0.0, 0.0, 1.0, 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def matrix_multiply(a, b):
    return [
        [sum(a[row][k] * b[k][column] for k in range(4)) for column in range(4)]
        for row in range(4)
    ]


def quaternion_matrix(values) -> list[list[float]]:
    x, y, z, w = [float(value) for value in values]
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w), 0.0],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w), 0.0],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y), 0.0],
        [0.0, 0.0, 0.0, 1.0],
    ]


def node_matrix(node) -> list[list[float]]:
    if "matrix" in node:
        values = [float(value) for value in node["matrix"]]
        return [[values[column * 4 + row] for column in range(4)] for row in range(4)]
    translation = [float(value) for value in node.get("translation", [0.0, 0.0, 0.0])]
    scale = [float(value) for value in node.get("scale", [1.0, 1.0, 1.0])]
    result = quaternion_matrix(node.get("rotation", [0.0, 0.0, 0.0, 1.0]))
    for row in range(3):
        for column in range(3):
            result[row][column] *= scale[column]
        result[row][3] = translation[row]
    return result


def transform_point(matrix, point) -> list[float]:
    values = [float(point[0]), float(point[1]), float(point[2]), 1.0]
    return [sum(matrix[row][column] * values[column] for column in range(4)) for row in range(3)]


def combine_bounds(records) -> tuple[list[float], list[float]]:
    return (
        [min(record[0][axis] for record in records) for axis in range(3)],
        [max(record[1][axis] for record in records) for axis in range(3)],
    )


def glb_named_bounds(path: Path, target_names: set[str]) -> dict[str, tuple[list[float], list[float]]]:
    raw = path.read_bytes()
    magic, version, total_length = struct.unpack_from("<4sII", raw, 0)
    if magic != b"glTF" or version != 2 or total_length != len(raw):
        raise RuntimeError("invalid GLB header")
    offset = 12
    json_data = None
    while offset < len(raw):
        chunk_length, chunk_type = struct.unpack_from("<II", raw, offset)
        offset += 8
        chunk = raw[offset : offset + chunk_length]
        offset += chunk_length
        if chunk_type == 0x4E4F534A:
            json_data = json.loads(chunk.decode("utf-8").rstrip(" \t\r\n\x00"))
            break
    if json_data is None:
        raise RuntimeError("GLB JSON chunk not found")

    accessors = json_data["accessors"]
    meshes = json_data["meshes"]
    nodes = json_data["nodes"]
    scene_index = int(json_data.get("scene", 0))
    scene_roots = json_data["scenes"][scene_index]["nodes"]
    found: dict[str, list[tuple[list[float], list[float]]]] = {}

    def walk(index: int, parent_matrix) -> None:
        node = nodes[index]
        world = matrix_multiply(parent_matrix, node_matrix(node))
        name = node.get("name", "")
        if name in target_names and "mesh" in node:
            records = []
            for primitive in meshes[int(node["mesh"])]["primitives"]:
                accessor = accessors[int(primitive["attributes"]["POSITION"])]
                low = accessor.get("min")
                high = accessor.get("max")
                if low is None or high is None:
                    raise RuntimeError(f"GLB POSITION bounds absent for {name}")
                corners = [
                    transform_point(world, [x, y, z])
                    for x in (low[0], high[0])
                    for y in (low[1], high[1])
                    for z in (low[2], high[2])
                ]
                records.append((
                    [min(point[axis] for point in corners) for axis in range(3)],
                    [max(point[axis] for point in corners) for axis in range(3)],
                ))
            found.setdefault(name, []).extend(records)
        for child in node.get("children", []):
            walk(int(child), world)

    for root in scene_roots:
        walk(int(root), identity_matrix())
    missing = target_names - set(found)
    if missing:
        raise RuntimeError(f"missing cassette GLB nodes: {sorted(missing)}")
    return {name: combine_bounds(records) for name, records in sorted(found.items())}


def point_aabb_squared(point, box) -> float:
    total = 0.0
    for axis in range(3):
        value = point[axis]
        if value < box[0][axis]:
            delta = box[0][axis] - value
        elif value > box[1][axis]:
            delta = value - box[1][axis]
        else:
            delta = 0.0
        total += delta * delta
    return total


def segment_aabb_distance(start, end, box) -> float:
    # Squared distance from a line segment to an AABB is convex in segment t.
    low = 0.0
    high = 1.0
    for _ in range(100):
        first = low + (high - low) / 3.0
        second = high - (high - low) / 3.0
        first_point = [start[i] + (end[i] - start[i]) * first for i in range(3)]
        second_point = [start[i] + (end[i] - start[i]) * second for i in range(3)]
        if point_aabb_squared(first_point, box) <= point_aabb_squared(second_point, box):
            high = second
        else:
            low = first
    parameter = (low + high) * 0.5
    point = [start[i] + (end[i] - start[i]) * parameter for i in range(3)]
    return math.sqrt(point_aabb_squared(point, box))


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
        raise RuntimeError("helper dependency hash mismatch")

    output_dir = root / contract["output"]["directory"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    output_dir.mkdir(parents=True)
    print("STAGE 1/8 contract and hashes verified", flush=True)

    input_specs = contract["inputs"]
    v31 = json.loads((root / input_specs["v31_validation_json"]["path"]).read_text())
    preferred = v31["c009"]["preferred_clean_route"]
    expected = contract["candidate"]
    if preferred["translation_mm"] != expected["translation_mm"]:
        raise RuntimeError("V31 translation differs from V32 candidate contract")

    accepted_document = App.openDocument(str(root / input_specs["accepted_context_fcstd"]["path"]))
    context_document = App.openDocument(str(root / input_specs["v18_context_fcstd"]["path"]))
    ear_document = App.openDocument(str(root / input_specs["ear_context_fcstd"]["path"]))
    try:
        components = find_components(accepted_document)
        c001 = components["C001"].Shape
        candidate = components["C009"].Shape.copy()
        candidate.translate(App.Vector(*preferred["translation_mm"]))
        print("STAGE 2/8 exact translated C009 reconstructed", flush=True)

        eye = Part.Shape()
        eye.read(str(root / input_specs["replacement_eye_step"]["path"]))
        rear_cap = Part.Shape()
        rear_cap.read(str(root / input_specs["rear_cap_step"]["path"]))
        if eye.isNull() or rear_cap.isNull():
            raise RuntimeError("STEP context imported as a null shape")

        numeric = contract["numeric_contract"]
        threshold = float(numeric["positive_intersection_threshold_mm3"])
        owner_overlap = common_volume(candidate, c001)
        eye_distance = float(candidate.distToShape(eye)[0])
        if owner_overlap + 1.0e-12 < float(numeric["minimum_owner_overlap_mm3"]):
            raise RuntimeError("candidate lost required C001 engagement")
        if eye_distance + 1.0e-9 < float(numeric["minimum_eye_clearance_mm"]):
            raise RuntimeError("candidate lost required repaired-eye clearance")
        print("STAGE 3/8 eye clearance and owner engagement revalidated", flush=True)

        exact_context_labels = contract["v18_exact_context_labels"]
        exact_context = {
            identifier: shape_object(context_document, label).Shape
            for identifier, label in exact_context_labels.items()
        }
        exact_context["right_primary_ear"] = shape_object(
            ear_document, contract["ear_label"]
        ).Shape
        exact_context["right_eye_rear_cap"] = rear_cap
        exact_records = {
            identifier: exact_clearance_record(candidate, obstacle, threshold)
            for identifier, obstacle in sorted(exact_context.items())
        }
        exact_clear = all(record["clear"] for record in exact_records.values())
        print("STAGE 4/8 exact frozen neighbors audited", flush=True)

        candidate_bounds = bounds(candidate)
        inventory = json.loads((root / input_specs["lower_inventory_json"]["path"]).read_text())
        lower_records = []
        for record in inventory["components"][1:]:
            other = (record["bbox_min_mm"], record["bbox_max_mm"])
            lower_records.append({
                "component": record["name"],
                "aabb_distance_mm": aabb_distance(candidate_bounds, other),
                "aabb_overlap": aabb_distance(candidate_bounds, other) <= 1.0e-12,
            })
        lower_broadphase_clear = not any(record["aabb_overlap"] for record in lower_records)
        print("STAGE 5/8 lower-face broad phase audited", flush=True)

        cassette_names = set(contract["rear_cassette_node_names"])
        cassette_bounds = glb_named_bounds(
            root / input_specs["rear_cassette_glb"]["path"], cassette_names
        )
        cassette_records = {
            name: {
                "bounds": {"minimum_mm": value[0], "maximum_mm": value[1]},
                "aabb_distance_mm": aabb_distance(candidate_bounds, value),
                "aabb_overlap": aabb_distance(candidate_bounds, value) <= 1.0e-12,
            }
            for name, value in cassette_bounds.items()
        }
        cassette_broadphase_clear = not any(
            record["aabb_overlap"] for record in cassette_records.values()
        )
        print("STAGE 6/8 rear-cassette broad phase audited", flush=True)

        aluminum = json.loads((root / input_specs["aluminum_interface_json"]["path"]).read_text())
        rail = aluminum["rail_system"]
        start = [float(value) for value in rail["lower_targets_head_mm"]["right"]]
        axis = [float(value) for value in rail["accepted_axes_head"]["right"]]
        length = float(rail["modeled_installed_reference_length_mm"])
        end = [start[index] + axis[index] * length for index in range(3)]
        profile = rail["profile"]
        radius = 0.5 * math.hypot(
            float(profile["outside_width_mm"]),
            float(profile["outside_height_mm"]),
        )
        centerline_distance = segment_aabb_distance(start, end, candidate_bounds)
        conservative_clearance = centerline_distance - radius
        aluminum_clear = conservative_clearance > 0.0
        aluminum_record = {
            "right_rail_start_mm": start,
            "right_rail_end_mm": end,
            "conservative_profile_radius_mm": radius,
            "centerline_to_candidate_aabb_distance_mm": centerline_distance,
            "conservative_clearance_mm": conservative_clearance,
            "clear": aluminum_clear,
        }
        print("STAGE 7/8 aluminum rail envelope audited", flush=True)

        passed = exact_clear and lower_broadphase_clear and cassette_broadphase_clear and aluminum_clear
        status = (
            "PASS__DECLARED_FROZEN_FULL_CONTEXT_CLEAR"
            if passed
            else "FAIL__DECLARED_FROZEN_CONTEXT_COLLISION"
        )
        result = {
            "schema_version": "1.0",
            "generator": "freecad-right-upper-c009-full-context-route-audit-v32",
            "freecad_version": App.Version(),
            "contract_id": contract["contract_id"],
            "status": status,
            "input_hashes": actual_hashes,
            "implementation_dependency_hash": dependency_hash,
            "candidate": {
                "source_member": "C009",
                "translation_mm": preferred["translation_mm"],
                "shape": shape_summary(candidate),
                "c001_owner_overlap_mm3": owner_overlap,
                "repaired_eye_clearance_mm": eye_distance,
            },
            "exact_context": exact_records,
            "lower_face_components_002_060_broadphase": {
                "method": "hash-pinned source-ledger AABB separation",
                "clear": lower_broadphase_clear,
                "minimum_aabb_distance_mm": min(record["aabb_distance_mm"] for record in lower_records),
                "records": lower_records,
            },
            "rear_cassette_broadphase": {
                "method": "hash-pinned GLB accessor bounds with node transforms",
                "clear": cassette_broadphase_clear,
                "records": cassette_records,
            },
            "aluminum_interface": aluminum_record,
            "interpretation": {
                "existing_member_only": True,
                "rigid_translation_only": True,
                "full_service_sweeps_audited": False,
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
        validation_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print("STAGE 8/8 deterministic validation JSON saved", flush=True)
        print(json.dumps({
            "status": status,
            "candidate": result["candidate"],
            "exact_context": exact_records,
            "lower_broadphase_clear": lower_broadphase_clear,
            "cassette_broadphase_clear": cassette_broadphase_clear,
            "aluminum": aluminum_record,
        }, indent=2, sort_keys=True))
        return 0 if passed else 1
    finally:
        App.closeDocument(ear_document.Name)
        App.closeDocument(context_document.Name)
        App.closeDocument(accepted_document.Name)


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
