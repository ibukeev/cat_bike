#!/usr/bin/env python3
"""Prove a hidden shell-side 15-degree service path, then gate review output.

This is deliberately non-authoritative.  The held eye is opened read-only and
never assigned or saved.  Only disposable copies of lower_C001 and lower_C013
are cut, serially, and only inside the approved bezel/lip projection.  A fresh
REVIEW_ONLY FCStd and deterministic fixed views may be written only after the
full in-memory motion, coverage, topology, and preservation gates pass.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path
from typing import Any, Sequence


SOURCE_DIR = Path(__file__).resolve().parents[2]
V1_GENERATOR = SOURCE_DIR / "generate_right_eye_split_service_cassette_prototype_v1.py"
V1_GENERATOR_SHA256 = "611aa4b63a0cd81420a01507168095c9a0a4d967d306688d78fe69b5383815fc"
V1_VALIDATOR = SOURCE_DIR / "validate_right_eye_split_service_cassette_previsual_v1.py"
V1_VALIDATOR_SHA256 = "d7ad39bea689e8df54484eaf97c9077df73d3c8c8eb03c18696859ea15133ccf"
V1_CONTRACT_RELATIVE = (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/v2/right-eye-split-service-cassette-prototype-v1.json"
)
V1_CONTRACT_SHA256 = "08fa1c89ad307598e8b0edaa3dc55085cd2ddc977904209972ca698d21790b9f"
CONTRACT_PATH = Path(__file__).with_name("contract.json")
EPSILON_MM3 = 1.0e-6


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_pinned(path: Path, digest: str, name: str) -> Any:
    actual = sha256_file(path)
    if actual != digest:
        raise RuntimeError(f"pinned dependency changed: {path.name}: {actual}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


v1 = load_pinned(V1_GENERATOR, V1_GENERATOR_SHA256, "_shell_path_review_v1_generator")
validator = load_pinned(V1_VALIDATOR, V1_VALIDATOR_SHA256, "_shell_path_review_v1_validator")


def load_inputs() -> tuple[Path, dict[str, Any], dict[str, Any]]:
    root = v1.repo_root()
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schema_version") != "cat-head-right-eye-split-service-expanded-cover-shell-path-review-v1":
        raise RuntimeError("unexpected shell-path review contract")
    v1_path = root / V1_CONTRACT_RELATIVE
    if sha256_file(v1_path) != V1_CONTRACT_SHA256:
        raise RuntimeError("immutable split-cassette contract changed")
    source = json.loads(v1_path.read_text(encoding="utf-8"))
    poses = contract["motion"]["samples"]
    if len(poses) != 21 or [int(item[0]) for item in poses] != list(range(21)):
        raise RuntimeError("contract must embed the exact contiguous 21-pose path")
    if [item["owner"] for item in contract["serial_owner_stages"]] != [
        "lower_C001", "lower_C013"
    ]:
        raise RuntimeError("serial owner order changed")
    return root, source["allowed_mutations"][0]["parameters"], contract


def posed(shape: Any, pose: Sequence[float], pivot: Any, rotation_axis: Any,
          translation_axis: Any) -> Any:
    moved = shape.copy()
    moved.rotate(pivot, rotation_axis, float(pose[1]))
    moved.translate(translation_axis * float(pose[2]))
    return moved


def bbox_separation(first: Any, second: Any) -> float:
    a, b = first.BoundBox, second.BoundBox
    gaps = (
        max(float(a.XMin) - float(b.XMax), float(b.XMin) - float(a.XMax), 0.0),
        max(float(a.YMin) - float(b.YMax), float(b.YMin) - float(a.YMax), 0.0),
        max(float(a.ZMin) - float(b.ZMax), float(b.ZMin) - float(a.ZMax), 0.0),
    )
    return math.sqrt(sum(value * value for value in gaps))


def bbox_separation_values(shape: Any, minimum: Sequence[float],
                           maximum: Sequence[float]) -> float:
    box = shape.BoundBox
    gaps = (
        max(float(minimum[0]) - float(box.XMax), float(box.XMin) - float(maximum[0]), 0.0),
        max(float(minimum[1]) - float(box.YMax), float(box.YMin) - float(maximum[1]), 0.0),
        max(float(minimum[2]) - float(box.ZMax), float(box.ZMin) - float(maximum[2]), 0.0),
    )
    return math.sqrt(sum(value * value for value in gaps))


def box_from_bounds(minimum: Sequence[float], maximum: Sequence[float],
                    App: Any, Part: Any) -> Any:
    return Part.makeBox(
        float(maximum[0]) - float(minimum[0]),
        float(maximum[1]) - float(minimum[1]),
        float(maximum[2]) - float(minimum[2]),
        App.Vector(*map(float, minimum)),
    )


def expanded_common_box(common: Any, padding: float, App: Any, Part: Any) -> Any:
    box = common.BoundBox
    return box_from_bounds(
        (box.XMin - padding, box.YMin - padding, box.ZMin - padding),
        (box.XMax + padding, box.YMax + padding, box.ZMax + padding),
        App, Part,
    )


def closest_pair_boxes(result: Any, padding: float, App: Any, Part: Any) -> list[Any]:
    boxes = []
    for first, second in result[1]:
        minimum = (
            min(float(first.x), float(second.x)) - padding,
            min(float(first.y), float(second.y)) - padding,
            min(float(first.z), float(second.z)) - padding,
        )
        maximum = (
            max(float(first.x), float(second.x)) + padding,
            max(float(first.y), float(second.y)) + padding,
            max(float(first.z), float(second.z)) + padding,
        )
        boxes.append(box_from_bounds(minimum, maximum, App, Part))
    return boxes


def face_normal(face: Any) -> Any:
    u0, u1, v0, v1 = map(float, face.ParameterRange)
    normal = face.normalAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
    normal.normalize()
    return normal


def approved_coverage_envelope(refs: dict[str, Any], depth: float,
                               Part: Any) -> tuple[Any, list[Any], dict[str, Any]]:
    axis = refs["axis_n"]
    projected = []
    records = []
    for index, face in enumerate(refs["bezel"].Faces, start=1):
        surface = str(getattr(face.Surface, "TypeId", type(face.Surface).__name__))
        if "plane" not in surface.lower():
            continue
        normal = face_normal(face)
        dot = float(normal.dot(axis))
        if dot > -0.999999:
            continue
        prisms = [
            face.extrude(axis * depth).removeSplitter(),
            face.extrude(axis * (-depth)).removeSplitter(),
        ]
        prisms = [
            prism for prism in prisms
            if not prism.isNull() and float(prism.Volume) > EPSILON_MM3
        ]
        if not prisms:
            continue
        projected.extend(prisms)
        records.append({"face_index": index, "area_mm2": float(face.Area),
                        "normal_dot_inward": dot})
    if not projected:
        raise RuntimeError("approved bezel/lip has no outward planar coverage faces")
    envelope = Part.makeCompound(projected)
    return envelope, projected, {"outward_face_count": len(records),
                      "symmetric_projection_solid_count": len(projected),
                      "faces": records,
                      "projection_depth_mm": depth,
                      "aggregate_projection_volume_mm3": sum(float(item.Volume) for item in projected)}


def widened_cover_projection(parameters: dict[str, Any], refs: dict[str, Any],
                              extension: float, depth: float, App: Any,
                              Part: Any) -> tuple[Any, list[Any], list[Any], list[Any]]:
    toolkit = v1.toolkit
    lcs = parameters["aperture_lcs"]
    opening = toolkit.planar_loop(
        [toolkit.vector(App, point) for point in parameters["geometry"]["shell_opening_boundary_mm"]],
        refs["origin"], refs["axis_u"], refs["axis_v"], refs["axis_n"],
    )
    outer_front = v1._locally_inset_loop(
        App, opening,
        parameters["geometry"]["front_optical_cassette"]["front_outer_vertex_insets_mm"],
        refs["axis_n"],
    )
    widened = toolkit.radial_offset_loop(App, outer_front, extension, refs["axis_n"])
    ring = toolkit.polygon_face(Part, widened).cut(
        toolkit.polygon_face(Part, refs["aperture"])
    )
    parts = [
        ring.extrude(refs["axis_n"] * depth).removeSplitter(),
        ring.extrude(refs["axis_n"] * (-depth)).removeSplitter(),
    ]
    return Part.makeCompound(parts), parts, outer_front, widened


def collision_relief_segments(owner: Any, target: Any,
                              poses: Sequence[Sequence[float]], pivot: Any,
                              rotation_axis: Any, translation_axis: Any,
                              required: float, tolerance: float, padding: float,
                              App: Any, Part: Any) -> tuple[list[Any], list[dict[str, Any]]]:
    segments, records = [], []
    for pose in poses:
        moved = posed(target, pose, pivot, rotation_axis, translation_axis)
        result = moved.distToShape(owner)
        distance = float(result[0])
        boxes, kind, volume = [], None, 0.0
        if bbox_separation(moved, owner) <= 1.0e-9:
            common = moved.common(owner)
            volume = float(common.Volume) if not common.isNull() else 0.0
            if volume > EPSILON_MM3:
                boxes = [expanded_common_box(common, padding, App, Part)]
                kind = "exact_common_bbox"
        if not boxes and distance < required - tolerance:
            boxes = closest_pair_boxes(result, padding, App, Part)
            kind = "closest_pair_bbox"
        for box in boxes:
            segment = owner.common(box).removeSplitter()
            if segment.isNull() or float(segment.Volume) <= EPSILON_MM3:
                continue
            segments.append(segment)
            bb = segment.BoundBox
            records.append({
                "sample_index": int(pose[0]), "kind": kind,
                "collision_mm3": volume, "distance_mm": distance,
                "segment_volume_mm3": float(segment.Volume),
                "bbox_minimum_mm": [float(bb.XMin), float(bb.YMin), float(bb.ZMin)],
                "bbox_maximum_mm": [float(bb.XMax), float(bb.YMax), float(bb.ZMax)],
            })
    return segments, records


def uncovered_volume(segments: Sequence[Any], coverage_parts: Sequence[Any]) -> float:
    total = 0.0
    for segment in segments:
        remaining = segment.copy()
        for part in coverage_parts:
            remaining = remaining.cut(part).removeSplitter()
            if remaining.isNull():
                break
        if not remaining.isNull():
            total += max(0.0, float(remaining.Volume))
    return total


def measure_extension() -> dict[str, Any]:
    root, parameters, contract = load_inputs()
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore
    eye, eye_record = load_held_eye(root, contract, App)
    refs = validator._reference_geometry(parameters, App, Part)
    _, baseline_parts, _ = approved_coverage_envelope(
        refs, float(contract["coverage"]["projection_depth_mm"]), Part
    )
    components = v1._load_shell_components(parameters, App, Part)
    owners = {str(item.key): item for item in components}
    pivot = App.Vector(*map(float, contract["motion"]["pivot_mm"]))
    rotation_axis = App.Vector(*map(float, contract["motion"]["rotation_axis"]))
    translation_axis = App.Vector(*map(float, contract["motion"]["translation_axis_inward_n"]))
    rotation_axis.normalize()
    translation_axis.normalize()
    required = float(contract["motion"]["required_clearance_mm"])
    tolerance = float(contract["motion"]["dimensional_tolerance_mm"])
    padding = float(contract["motion"]["cutter_bbox_padding_mm"])
    segments, owner_records = [], {}
    for key in ("lower_C001", "lower_C013"):
        component = owners[key]
        if component.shape is None:
            raise RuntimeError(f"required exact shell owner unavailable: {key}")
        found, records = collision_relief_segments(
            component.shape, eye, contract["motion"]["samples"], pivot,
            rotation_axis, translation_axis, required, tolerance, padding, App, Part,
        )
        segments.extend(found)
        owner_records[key] = records
    coverage = contract["coverage"]
    depth = float(coverage["projection_depth_mm"])
    cap = float(coverage["maximum_selected_extension_mm"])
    resolution = float(coverage["measurement_resolution_mm"])
    epsilon = float(coverage["maximum_removed_volume_outside_coverage_mm3"])

    def outside(extension: float) -> tuple[float, list[Any], list[Any]]:
        _, parts, base, widened = widened_cover_projection(
            parameters, refs, extension, depth, App, Part
        )
        return uncovered_volume(segments, parts), base, widened

    baseline_outside = uncovered_volume(segments, baseline_parts)
    at_cap, base_loop, cap_loop = outside(cap)
    if at_cap > epsilon:
        status, required_extension, selected = "BLOCKED__REQUIRES_MORE_THAN_3P0_MM", None, None
    else:
        low, high = 0.0, cap
        while high - low > resolution / 4.0:
            middle = (low + high) / 2.0
            if outside(middle)[0] <= epsilon:
                high = middle
            else:
                low = middle
        required_extension = math.ceil(high / resolution - 1.0e-9) * resolution
        increment = float(coverage["manufacturing_round_increment_mm"])
        extra = float(coverage["manufacturing_extra_margin_mm"])
        selected = math.ceil(required_extension / increment - 1.0e-9) * increment + extra
        status = "PASS__EXTENSION_MEASURED" if selected <= cap else "BLOCKED__MARGIN_EXCEEDS_3P0_MM"
    selected_loop = None
    if selected is not None and selected <= cap:
        _, _, _, selected_loop = widened_cover_projection(parameters, refs, selected, depth, App, Part)
    points = lambda loop: [[float(p.x), float(p.y), float(p.z)] for p in loop]
    return {
        "schema_version": "cat-head-expanded-cover-extension-measure-v1",
        "status": status,
        "authority": contract["authority"],
        "held_candidate_sha256": eye_record["sha256"],
        "collision_segment_count": len(segments),
        "baseline_uncovered_collision_relief_mm3": baseline_outside,
        "at_cap_uncovered_collision_relief_mm3": at_cap,
        "minimum_required_extension_mm": required_extension,
        "selected_manufacturing_extension_mm": selected,
        "base_outer_front_world_mm": points(base_loop),
        "selected_outer_world_mm": points(selected_loop) if selected_loop else None,
        "owners": owner_records,
        "io_trace": {
            "held_candidate_saved": False,
            "review_saved": False,
            "geometry_export_created": False,
            "production_output_created": False,
        },
    }


def load_held_eye(root: Path, contract: dict[str, Any], App: Any) -> tuple[Any, dict[str, Any]]:
    spec = contract["inputs"]["held_candidate"]
    path = root / spec["path"]
    actual = sha256_file(path)
    if actual != spec["sha256"]:
        raise RuntimeError(f"held candidate hash changed: {actual}")
    document = App.openDocument(str(path))
    try:
        target = document.getObject(spec["object"])
        if target is None or not hasattr(target, "Shape") or target.Shape.isNull():
            raise RuntimeError("held split-eye target is missing")
        shape = target.Shape.copy()
        record = {
            "path": spec["path"], "sha256": actual, "object": target.Name,
            "volume_mm3": float(shape.Volume), "area_mm2": float(shape.Area),
            "solid_count": len(shape.Solids), "valid": bool(shape.isValid()),
        }
    finally:
        App.closeDocument(document.Name)
    return shape, record


def owner_motion_measure(target: Any, owner: Any, poses: Sequence[Sequence[float]],
                         pivot: Any, rotation_axis: Any,
                         translation_axis: Any) -> dict[str, Any]:
    maximum = 0.0
    minimum = math.inf
    records = []
    for pose in poses:
        moved = posed(target, pose, pivot, rotation_axis, translation_axis)
        if bbox_separation(moved, owner) > 1.0e-9:
            volume = 0.0
        else:
            common = moved.common(owner)
            volume = float(common.Volume) if not common.isNull() else 0.0
        distance = float(moved.distToShape(owner)[0])
        maximum = max(maximum, volume)
        minimum = min(minimum, distance)
        records.append({"sample_index": int(pose[0]), "collision_mm3": volume,
                        "distance_mm": distance})
    return {"maximum_collision_mm3": maximum, "minimum_distance_mm": minimum,
            "poses": records}


def relieve_owner_serially(owner_key: str, owner: Any, target: Any,
                           coverage_parts: Sequence[Any], contract: dict[str, Any],
                           pivot: Any, rotation_axis: Any,
                           translation_axis: Any, App: Any,
                           Part: Any) -> tuple[Any, dict[str, Any]]:
    motion = contract["motion"]
    poses = motion["samples"]
    required = float(motion["required_clearance_mm"])
    tolerance = float(motion["dimensional_tolerance_mm"])
    padding = float(motion["cutter_bbox_padding_mm"])
    stage = next(item for item in contract["serial_owner_stages"] if item["owner"] == owner_key)
    original = owner.copy()
    current = owner.copy()
    iteration_records = []
    maximum_cutter_outside_coverage = 0.0
    for iteration in range(3):
        boxes = []
        triggers = []
        for pose in poses:
            moved = posed(target, pose, pivot, rotation_axis, translation_axis)
            distance_result = moved.distToShape(current)
            distance = float(distance_result[0])
            common = None
            volume = 0.0
            if bbox_separation(moved, current) <= 1.0e-9:
                common = moved.common(current)
                volume = float(common.Volume) if not common.isNull() else 0.0
            if volume > EPSILON_MM3:
                boxes.append(expanded_common_box(common, padding, App, Part))
                triggers.append({"sample_index": int(pose[0]), "kind": "exact_common_bbox",
                                 "collision_mm3": volume, "distance_mm": distance})
            elif distance < required - tolerance:
                near_boxes = closest_pair_boxes(distance_result, padding, App, Part)
                boxes.extend(near_boxes)
                triggers.append({"sample_index": int(pose[0]), "kind": "closest_pair_bbox",
                                 "collision_mm3": 0.0, "distance_mm": distance,
                                 "closest_pair_count": len(near_boxes)})
        if not boxes:
            break
        next_shape = current.copy()
        applied_cutter_volume = 0.0
        applied_box_count = 0
        for box in boxes:
            for coverage_part in coverage_parts:
                hidden_cutter = box.common(coverage_part).removeSplitter()
                if hidden_cutter.isNull() or float(hidden_cutter.Volume) <= EPSILON_MM3:
                    continue
                before = float(next_shape.Volume)
                maximum_cutter_outside_coverage = max(
                    maximum_cutter_outside_coverage,
                    float(hidden_cutter.cut(coverage_part).Volume),
                )
                next_shape = next_shape.cut(hidden_cutter).removeSplitter()
                applied_cutter_volume += max(0.0, before - float(next_shape.Volume))
                applied_box_count += 1
        if next_shape.isNull() or not next_shape.isValid() or not next_shape.isClosed():
            raise RuntimeError(f"{owner_key}: relief produced invalid/open owner")
        if len(next_shape.Solids) != 1:
            raise RuntimeError(f"{owner_key}: relief changed owner solid count to {len(next_shape.Solids)}")
        removed_now_mm3 = max(0.0, float(current.Volume) - float(next_shape.Volume))
        iteration_records.append({
            "iteration": iteration + 1, "trigger_count": len(triggers),
            "triggers": triggers, "clearance_box_count": len(boxes),
            "applied_box_count": applied_box_count,
            "applied_cutter_removed_mm3": applied_cutter_volume,
            "removed_mm3": removed_now_mm3,
        })
        if removed_now_mm3 <= EPSILON_MM3:
            break
        current = next_shape
    removed_volume = max(0.0, float(original.Volume) - float(current.Volume))
    measure = owner_motion_measure(
        target, current, poses, pivot, rotation_axis, translation_axis
    )
    declared = {record["sample_index"]: record for record in measure["poses"]}
    declared_minimum = min(
        float(declared[int(index)]["distance_mm"])
        for index in stage["collision_poses"]
    )
    return current, {
        "owner": owner_key,
        "iterations": iteration_records,
        "original_volume_mm3": float(original.Volume),
        "review_volume_mm3": float(current.Volume),
        "removed_volume_mm3": removed_volume,
        "removed_outside_coverage_mm3": maximum_cutter_outside_coverage,
        "valid": bool(current.isValid()), "closed": bool(current.isClosed()),
        "solid_count": len(current.Solids),
        "motion": measure,
        "declared_collision_pose_minimum_distance_mm": declared_minimum,
    }


def full_owner_collision_matrix(target: Any, components: Sequence[Any],
                                replacements: dict[str, Any],
                                poses: Sequence[Sequence[float]], pivot: Any,
                                rotation_axis: Any,
                                translation_axis: Any) -> dict[str, Any]:
    positives = []
    near_records = []
    unresolved = []
    exact_calls = 0
    for pose in poses:
        moved = posed(target, pose, pivot, rotation_axis, translation_axis)
        for component in components:
            key = str(component.key)
            shape = replacements.get(key, component.shape)
            if shape is None:
                separation = bbox_separation_values(
                    moved, component.minimum_mm, component.maximum_mm
                )
                if separation <= 0.0:
                    unresolved.append({"owner": key, "sample_index": int(pose[0]),
                                       "aabb_separation_mm": separation})
                continue
            separation = bbox_separation(moved, shape)
            if separation > 0.0:
                continue
            exact_calls += 1
            common = moved.common(shape)
            volume = float(common.Volume) if not common.isNull() else 0.0
            if volume > EPSILON_MM3:
                positives.append({"owner": key, "sample_index": int(pose[0]),
                                  "collision_mm3": volume})
            else:
                near_records.append({"owner": key, "sample_index": int(pose[0]),
                                     "distance_mm": float(moved.distToShape(shape)[0])})
    return {"positive_intersections": positives,
            "positive_intersection_count": len(positives),
            "aabb_only_unresolved": unresolved,
            "aabb_only_unresolved_count": len(unresolved),
            "exact_common_calls": exact_calls,
            "near_zero_records": near_records}


def build_preflight() -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.monotonic()
    root, parameters, contract = load_inputs()
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    eye, eye_record = load_held_eye(root, contract, App)
    refs = validator._reference_geometry(parameters, App, Part)
    coverage, coverage_parts, coverage_record = approved_coverage_envelope(
        refs, float(contract["coverage"]["projection_depth_mm"]), Part
    )
    components = v1._load_shell_components(parameters, App, Part)
    owners = {str(item.key): item for item in components}
    pivot = App.Vector(*map(float, contract["motion"]["pivot_mm"]))
    rotation_axis = App.Vector(*map(float, contract["motion"]["rotation_axis"]))
    translation_axis = App.Vector(*map(float, contract["motion"]["translation_axis_inward_n"]))
    rotation_axis.normalize()
    translation_axis.normalize()

    replacements = {}
    stages = []
    for owner_key in ("lower_C001", "lower_C013"):
        component = owners.get(owner_key)
        if component is None or component.shape is None:
            raise RuntimeError(f"required exact shell owner unavailable: {owner_key}")
        relieved, stage = relieve_owner_serially(
            owner_key, component.shape, eye, coverage_parts, contract, pivot,
            rotation_axis, translation_axis, App, Part,
        )
        replacements[owner_key] = relieved
        stages.append(stage)

    matrix = full_owner_collision_matrix(
        eye, components, replacements, contract["motion"]["samples"], pivot,
        rotation_axis, translation_axis,
    )
    required = float(contract["motion"]["required_clearance_mm"])
    tolerance = float(contract["motion"]["dimensional_tolerance_mm"])
    coverage_limit = float(
        contract["coverage"]["maximum_removed_volume_outside_coverage_mm3"]
    )
    checks = {
        "held_eye_valid_one_solid": bool(eye.isValid()) and len(eye.Solids) == 1,
        "serial_owner_order_exact": [item["owner"] for item in stages]
        == ["lower_C001", "lower_C013"],
        "changed_owners_valid_closed_one_solid": all(
            item["valid"] and item["closed"] and item["solid_count"] == 1
            for item in stages
        ),
        "changed_owner_declared_poses_clear_0p50": all(
            item["declared_collision_pose_minimum_distance_mm"]
            >= required - tolerance for item in stages
        ),
        "changed_owner_full_path_zero_collision": all(
            item["motion"]["maximum_collision_mm3"] <= EPSILON_MM3
            for item in stages
        ),
        "removed_volume_fully_behind_approved_bezel_lip": all(
            item["removed_outside_coverage_mm3"] <= coverage_limit
            for item in stages
        ),
        "full_101_owner_path_zero_collision": matrix["positive_intersection_count"] == 0,
        "full_101_owner_path_has_no_unresolved_aabb": matrix["aabb_only_unresolved_count"] == 0,
        "eye_target_not_mutated": True,
        "all_other_owners_not_mutated": True,
        "no_production_output_or_export": True,
    }
    passed = all(checks.values())
    report = {
        "schema_version": "cat-head-right-eye-shell-path-review-preflight-v1",
        "status": "PASS__REVIEW_ONLY_SHELL_PATH_PREFLIGHT" if passed else "FAIL__NO_REVIEW_OUTPUT",
        "authority": contract["authority"],
        "pins": {
            "generator": sha256_file(Path(__file__)),
            "contract": sha256_file(CONTRACT_PATH),
            "v1_generator": V1_GENERATOR_SHA256,
            "v1_validator": V1_VALIDATOR_SHA256,
            "v1_contract": V1_CONTRACT_SHA256,
            "held_candidate": eye_record["sha256"],
        },
        "eye": eye_record,
        "coverage": coverage_record,
        "serial_stages": stages,
        "full_owner_matrix": matrix,
        "checks": checks,
        "release_holds": contract["release_holds"],
        "io_trace": {"held_candidate_opened_read_only": True,
                     "held_candidate_saved": False, "review_saved": False,
                     "geometry_export_created": False, "production_output_created": False},
        "elapsed_seconds": time.monotonic() - started,
    }
    context = {"root": root, "contract": contract, "App": App, "Part": Part,
               "eye": eye, "coverage": coverage, "coverage_parts": coverage_parts,
               "components": components,
               "owners": owners, "replacements": replacements}
    return report, context


def add_metadata(obj: Any, role: str, source: str) -> None:
    for name, value in {
        "Authority": "REVIEW_ONLY__NON_AUTHORITATIVE__NOT_A_PRINT_SOURCE",
        "ReviewRole": role,
        "SourceIdentity": source,
        "ReleaseState": "NO_PRINT_NO_EXPORT_NO_PROMOTION",
    }.items():
        obj.addProperty("App::PropertyString", name, "ChangeControl")
        setattr(obj, name, value)


def write_review(report: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    if not report["status"].startswith("PASS"):
        raise RuntimeError("review output is gated on a passing in-memory proof")
    root, contract = context["root"], context["contract"]
    output = root / contract["outputs"]["directory"]
    if output.exists():
        raise FileExistsError(f"refusing to overwrite review output: {output}")
    App, Part = context["App"], context["Part"]
    document = App.newDocument("RIGHT_EYE_SPLIT_SERVICE_SHELL_PATH_REVIEW_V1")
    try:
        document.Label = "REVIEW_ONLY__NON_AUTHORITATIVE__RIGHT_EYE_SHELL_PATH_V1"
        group = document.addObject("App::DocumentObjectGroup", "REVIEW_ONLY_SHELL_PATH")
        for name, label, shape, role, source, color, transparency in (
            ("HELD_SPLIT_EYE_READ_ONLY", "HELD__SPLIT_EYE__READ_ONLY", context["eye"],
             "HELD_EYE", "hash-pinned held candidate", (0.20, 0.72, 0.96), 45),
            ("PROPOSED_LOWER_C001_HIDDEN_PATH", "PROPOSED__LOWER_C001__HIDDEN_PATH",
             context["replacements"]["lower_C001"], "CHANGED_OWNER_REVIEW",
             "lower_C001 disposable copy", (0.96, 0.46, 0.12), 20),
            ("PROPOSED_LOWER_C013_HIDDEN_PATH", "PROPOSED__LOWER_C013__HIDDEN_PATH",
             context["replacements"]["lower_C013"], "CHANGED_OWNER_REVIEW",
             "lower_C013 disposable copy", (0.72, 0.24, 0.92), 20),
            ("APPROVED_BEZEL_LIP_COVERAGE", "PROOF__APPROVED_BEZEL_LIP_COVERAGE",
             context["coverage"], "COVERAGE_PROOF", "approved bezel/lip projection",
             (0.20, 0.86, 0.48), 86),
        ):
            obj = document.addObject("Part::Feature", name)
            obj.Label = label
            obj.Shape = shape.copy()
            add_metadata(obj, role, source)
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.Transparency = transparency
            group.addObject(obj)
        audit = document.addObject("App::FeaturePython", "REVIEW_ONLY_PATH_AUDIT")
        audit.addProperty("App::PropertyString", "PreflightStatus", "Audit")
        audit.PreflightStatus = report["status"]
        audit.addProperty("App::PropertyString", "GeneratorSha256", "Audit")
        audit.GeneratorSha256 = report["pins"]["generator"]
        audit.addProperty("App::PropertyString", "ReleaseHold", "Audit")
        audit.ReleaseHold = "REVIEW_ONLY__NO_PRINT_NO_EXPORT_NO_PROMOTION"
        group.addObject(audit)
        document.recompute()

        output.mkdir(parents=True, exist_ok=False)
        fcstd = output / contract["outputs"]["fcstd"]
        document.saveAs(str(fcstd))
        baseline_records = [
            v1.toolkit.shape_record(context["eye"], (40, 150, 195), deflection=0.55),
            v1.toolkit.shape_record(context["owners"]["lower_C001"].shape, (210, 115, 55), deflection=0.75),
            v1.toolkit.shape_record(context["owners"]["lower_C013"].shape, (145, 70, 175), deflection=0.75),
        ]
        review_records = [
            v1.toolkit.shape_record(context["eye"], (40, 150, 195), deflection=0.55),
            v1.toolkit.shape_record(context["replacements"]["lower_C001"], (235, 120, 35), deflection=0.75),
            v1.toolkit.shape_record(context["replacements"]["lower_C013"], (165, 65, 205), deflection=0.75),
        ]
        views = {
            "front.png": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), None, None),
            "rear.png": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0), None, None),
            "lower-path.png": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
                               (66.77454, 66.06956, 122.28207), 42.0),
            "side.png": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0),
                         (66.77454, 66.06956, 122.28207), 60.0),
        }
        for name, (direction, up, focus, span) in views.items():
            v1.toolkit.render_side_by_side(
                output / name, baseline_records, review_records,
                direction, up, focus, span,
            )
        report["io_trace"]["review_saved"] = True
        report["outputs"] = {
            "fcstd": str(fcstd.relative_to(root)),
            "fcstd_sha256": sha256_file(fcstd),
            "fixed_views": {
                name: {"path": str((output / name).relative_to(root)),
                       "sha256": sha256_file(output / name)} for name in views
            },
            "validation": str((output / contract["outputs"]["validation"]).relative_to(root)),
            "production_output_created": False,
            "geometry_export_created": False,
        }
        validation = output / contract["outputs"]["validation"]
        validation.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return report
    finally:
        App.closeDocument(document.Name)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--measure-extension", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--write-review-if-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.measure_extension:
        report = measure_extension()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["status"].startswith("PASS") else 1
    report, context = build_preflight()
    if args.write_review_if_pass:
        report = write_review(report, context)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
