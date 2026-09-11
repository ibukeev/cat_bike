#!/usr/bin/env python3
"""No-save feasibility and gated REVIEW_ONLY lower-rim hook retention."""

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


HERE = Path(__file__).resolve().parent
REVIEW_ID = "right-eye-lower-rim-hook-retention-review-r1"
EPSILON = 1.0e-6


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def load_module(path: Path, digest: str, name: str) -> Any:
    actual = sha256_file(path)
    if actual != digest:
        raise RuntimeError(f"pinned module changed: {path}: {actual}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def resolve(root: Path, spec: dict[str, Any]) -> Path:
    path = Path(str(spec["path"]))
    return path if path.is_absolute() else root / path


def tuple3(vector: Any) -> list[float]:
    return [float(vector.x), float(vector.y), float(vector.z)]


def aabb_near(first: Any, second: Any, margin: float = 0.0) -> bool:
    a, b = first.BoundBox, second.BoundBox
    return not (
        a.XMax + margin < b.XMin or b.XMax + margin < a.XMin
        or a.YMax + margin < b.YMin or b.YMax + margin < a.YMin
        or a.ZMax + margin < b.ZMin or b.ZMax + margin < a.ZMin
    )


def common_volume(first: Any, second: Any) -> float:
    if not aabb_near(first, second):
        return 0.0
    common = first.common(second)
    return 0.0 if common.isNull() else float(common.Volume)


def axis_intervals(shape: Any, anchor: Any, axis: Any, half: float, Part: Any) -> list[tuple[float, float]]:
    line = Part.makeLine(anchor - axis * half, anchor + axis * half)
    common = line.common(shape)
    intervals = []
    for edge in common.Edges:
        offsets = sorted(float((vertex.Point - anchor).dot(axis)) for vertex in edge.Vertexes)
        if len(offsets) >= 2 and offsets[-1] - offsets[0] > 1.0e-7:
            intervals.append((offsets[0], offsets[-1]))
    return sorted(intervals)


def input_modules(contract: dict[str, Any]) -> tuple[Path, Any, Any, Any, dict[str, Path]]:
    v1_spec = contract["inputs"]["v1_generator"]
    guessed = HERE.parents[8]
    v1_path = resolve(guessed, v1_spec)
    v1 = load_module(v1_path, v1_spec["sha256"], "_hook_review_v1")
    root = v1.repo_root()
    validator_spec = contract["inputs"]["v1_validator"]
    validator_path = resolve(root, validator_spec)
    validator = load_module(
        validator_path, validator_spec["sha256"], "_hook_review_validator"
    )
    shell_spec = contract["inputs"]["expanded_cover_shell_generator"]
    shell_path = resolve(root, shell_spec)
    actual_shell = sha256_file(shell_path)
    allowed = {shell_spec["provisional_sha256"]}
    final = shell_spec["final_sha256_required_before_review_save"]
    if not str(final).startswith("PENDING_"):
        allowed.add(final)
    if actual_shell not in allowed:
        raise RuntimeError(f"expanded-cover shell generator changed: {actual_shell}")
    shell = load_module(shell_path, actual_shell, "_hook_review_shell")
    paths = {
        key: resolve(root, value)
        for key, value in contract["inputs"].items()
        if isinstance(value, dict) and "path" in value
    }
    return root, v1, validator, shell, paths


def verify_inputs(contract: dict[str, Any], paths: dict[str, Path], *, review: bool) -> None:
    for key in ("held_candidate", "v1_contract", "v1_generator", "v1_validator", "stage_a"):
        actual = sha256_file(paths[key])
        if actual != contract["inputs"][key]["sha256"]:
            raise RuntimeError(f"{key} hash mismatch: {actual}")
    for key in ("expanded_cover_shell_contract", "expanded_cover_shell_generator"):
        spec = contract["inputs"][key]
        actual = sha256_file(paths[key])
        expected = spec["final_sha256_required_before_review_save"] if review else spec["provisional_sha256"]
        if review and str(expected).startswith("PENDING_"):
            raise RuntimeError("review save is blocked pending final expanded-cover pins")
        if actual != expected:
            raise RuntimeError(f"{key} hash mismatch: {actual} != {expected}")


def verify_motion(contract: dict[str, Any], stage: dict[str, Any]) -> None:
    datum = stage["derived_datums"]
    expected = contract["motion"]
    if datum["pivot_role"] != "lower_eye_bore_center":
        raise RuntimeError("Stage-A pivot role changed")
    for key, stage_key in (
        ("pivot_mm", "pivot_mm"),
        ("rotation_axis", "rotation_axis"),
        ("translation_axis_inward_n", "translation_axis_inward_n"),
    ):
        if list(map(float, expected[key])) != list(map(float, datum[stage_key])):
            raise RuntimeError(f"Stage-A {key} changed")
    samples = stage["paths"][2]["samples"]
    pinned = [
        [int(item["sample_index"]), float(item["tilt_deg"]), float(item["translation_mm"])]
        for item in samples
    ]
    if pinned != [[int(item[0]), float(item[1]), float(item[2])] for item in expected["samples"]]:
        raise RuntimeError("exact Stage-A 21-pose path changed")


def expanded_cover_geometry(parameters: dict[str, Any], contract: dict[str, Any], v1: Any, App: Any, Part: Any) -> dict[str, Any]:
    toolkit = v1.toolkit
    lcs = parameters["aperture_lcs"]
    origin = toolkit.vector(App, lcs["origin_mm"])
    axis_u = toolkit.normalized(App, toolkit.vector(App, lcs["u"]), "hook u")
    axis_v = toolkit.normalized(App, toolkit.vector(App, lcs["v"]), "hook v")
    axis_n = toolkit.normalized(App, toolkit.vector(App, lcs["inward_n"]), "hook n")
    aperture = toolkit.planar_loop(
        [toolkit.vector(App, point) for point in lcs["visible_aperture_mm"]],
        origin, axis_u, axis_v, axis_n,
    )
    opening = toolkit.planar_loop(
        [toolkit.vector(App, point) for point in parameters["geometry"]["shell_opening_boundary_mm"]],
        origin, axis_u, axis_v, axis_n,
    )
    insets = parameters["geometry"]["front_optical_cassette"]["front_outer_vertex_insets_mm"]
    outer_front = v1._locally_inset_loop(App, opening, insets, axis_n)
    extension = float(contract["expanded_cover"]["radial_extension_from_v1_outer_front_mm"])
    expanded_outer = v1._locally_inset_loop(
        App, outer_front, [-extension] * len(outer_front), axis_n
    )
    front = float(contract["expanded_cover"]["front_depth_mm"])
    rear = float(contract["expanded_cover"]["rear_depth_mm"])
    cover = toolkit.loft_ring(
        Part, expanded_outer, aperture, expanded_outer, aperture,
        front, rear, axis_n, "provisional conservative expanded cover",
    )
    depth = float(contract["expanded_cover"]["coverage_projection_each_direction_mm"])
    coverage = toolkit.loft_ring(
        Part, expanded_outer, aperture, expanded_outer, aperture,
        -depth, depth, axis_n, "expanded cover hidden projection",
    )
    toolkit.require_single_solid(cover, "expanded cover")
    toolkit.require_single_solid(coverage, "expanded cover coverage")
    return {
        "origin": origin, "axis_u": axis_u, "axis_v": axis_v, "axis_n": axis_n,
        "aperture": aperture, "opening": opening, "outer_front": outer_front,
        "expanded_outer": expanded_outer, "cover": cover, "coverage": coverage,
    }


def build_hooks(contract: dict[str, Any], cover: dict[str, Any], owners: dict[str, Any], v1: Any, App: Any, Part: Any) -> tuple[list[Any], list[dict[str, Any]]]:
    values = contract["hooks"]
    edge = values["lower_opening_edge_indices"]
    if edge != [0, 3]:
        raise RuntimeError("lower opening edge changed")
    start, end = cover["opening"][edge[0]], cover["opening"][edge[1]]
    tangent = end - start
    tangent.normalize()
    outward = cover["axis_n"].cross(tangent)
    outward.normalize()
    center = v1.toolkit.average(App, cover["opening"])
    midpoint = (start + end) * 0.5
    if outward.dot(midpoint - center) < 0.0:
        outward = outward * -1.0
    axis_n = cover["axis_n"]
    hooks, records = [], []
    for station_index, fraction_raw in enumerate(values["station_fractions"], start=1):
        fraction = float(fraction_raw)
        boundary = start + (end - start) * fraction
        probe = boundary + outward * float(values["rim_probe_outward_mm"])
        candidates = []
        for owner_key, shape in owners.items():
            if shape is None or shape.isNull():
                continue
            for interval in axis_intervals(shape, probe, axis_n, 20.0, Part):
                candidates.append((abs((interval[0] + interval[1]) * 0.5), owner_key, interval))
        if not candidates:
            raise RuntimeError(f"hook station {station_index} has no exact shell rim interval")
        _, owner_key, interval = min(candidates)
        shell_rear = float(interval[1])
        clearance = float(values["stem_inside_edge_clearance_mm"])
        root_wall = float(values["root_wall_mm"])
        barb_wall = float(values["barb_axial_wall_mm"])
        rear_gap = float(values["rear_clearance_mm"])
        stem_front = float(values["root_front_depth_mm"])
        barb_front = shell_rear + rear_gap
        barb_back = barb_front + barb_wall
        if barb_back <= stem_front:
            raise RuntimeError(f"hook station {station_index} has invalid axial span")
        stem_center = (
            boundary - outward * (clearance + root_wall * 0.5)
            + axis_n * ((stem_front + barb_back) * 0.5)
        )
        stem = v1.toolkit.oriented_box(
            Part, stem_center, (tangent, outward, axis_n),
            (float(values["tangent_width_mm"]), root_wall, barb_back - stem_front),
        )
        barb_inner = -clearance - 0.10
        barb_outer = float(values["barb_outward_overhang_mm"])
        barb_center = (
            boundary + outward * ((barb_inner + barb_outer) * 0.5)
            + axis_n * ((barb_front + barb_back) * 0.5)
        )
        barb = v1.toolkit.oriented_box(
            Part, barb_center, (tangent, outward, axis_n),
            (float(values["tangent_width_mm"]), barb_outer - barb_inner, barb_wall),
        )
        hook = stem.fuse(barb).removeSplitter()
        v1.toolkit.require_single_solid(hook, f"lower hook {station_index}")
        hooks.append(hook)
        records.append({
            "station_index": station_index, "station_fraction": fraction,
            "owner": owner_key, "boundary_mm": tuple3(boundary),
            "probe_mm": tuple3(probe), "shell_interval_from_aperture_plane_mm": list(interval),
            "shell_contact_span_mm": float(interval[1] - interval[0]),
            "shell_rear_depth_mm": shell_rear, "seated_rear_clearance_mm": rear_gap,
            "root_wall_mm": root_wall, "barb_axial_wall_mm": barb_wall,
            "tangent_width_mm": float(values["tangent_width_mm"]),
        })
    return hooks, records


def shell_compound(components: Sequence[Any], replacements: dict[str, Any], Part: Any) -> Any:
    return Part.makeCompound([
        replacements.get(str(component.key), component.shape)
        for component in components
        if replacements.get(str(component.key), component.shape) is not None
    ])


def maximum_shell_common(shape: Any, components: Sequence[Any], replacements: dict[str, Any]) -> tuple[float, str | None]:
    maximum, owner = 0.0, None
    for component in components:
        candidate = replacements.get(str(component.key), component.shape)
        if candidate is None or candidate.isNull() or not aabb_near(shape, candidate):
            continue
        volume = common_volume(shape, candidate)
        if volume > maximum:
            maximum, owner = volume, str(component.key)
    return maximum, owner


def minimum_shell_distance(shape: Any, components: Sequence[Any], replacements: dict[str, Any]) -> float:
    minimum = math.inf
    for component in components:
        candidate = replacements.get(str(component.key), component.shape)
        if candidate is None or candidate.isNull():
            continue
        if not aabb_near(shape, candidate, 3.0):
            continue
        minimum = min(minimum, float(shape.distToShape(candidate)[0]))
    return minimum


def evaluate(contract: dict[str, Any], final_target: Any, target_base: Any, hooks: list[Any], hook_records: list[dict[str, Any]], cover: dict[str, Any], refs: dict[str, Any], components: Sequence[Any], replacements: dict[str, Any], shell: Any, App: Any, Part: Any) -> dict[str, Any]:
    motion = contract["motion"]
    pivot = App.Vector(*map(float, motion["pivot_mm"]))
    rotation_axis = App.Vector(*map(float, motion["rotation_axis"]))
    translation_axis = App.Vector(*map(float, motion["translation_axis_inward_n"]))
    rotation_axis.normalize(); translation_axis.normalize()
    poses = motion["samples"]
    hook_compound = Part.makeCompound(hooks)
    motion_records, max_collision, min_clearance = [], 0.0, math.inf
    for pose in poses:
        moved = shell.posed(hook_compound, pose, pivot, rotation_axis, translation_axis)
        collision, owner = maximum_shell_common(moved, components, replacements)
        clearance = minimum_shell_distance(moved, components, replacements)
        max_collision = max(max_collision, collision)
        min_clearance = min(min_clearance, clearance)
        motion_records.append({"sample_index": int(pose[0]), "collision_mm3": collision, "nearest_owner": owner, "clearance_mm": clearance})

    retention = []
    each_hook_retained = []
    for hook_index, hook in enumerate(hooks, start=1):
        maximum = 0.0
        first_positive = None
        for distance_raw in contract["hooks"]["retention_test_outward_translations_mm"]:
            distance = float(distance_raw)
            moved = hook.copy(); moved.translate(cover["axis_n"] * -distance)
            collision, owner = maximum_shell_common(moved, components, replacements)
            maximum = max(maximum, collision)
            if first_positive is None and collision > float(contract["limits"]["minimum_outward_retention_collision_mm3"]):
                first_positive = distance
            retention.append({"hook": hook_index, "outward_translation_mm": distance, "collision_mm3": collision, "owner": owner})
        each_hook_retained.append(maximum >= float(contract["limits"]["minimum_outward_retention_collision_mm3"]))

    hooks_outside_coverage = float(hook_compound.cut(cover["coverage"]).Volume)
    frustum_common = common_volume(hook_compound, refs["frustum"])
    exposed_hook = hook_compound.cut(target_base).removeSplitter()
    exterior_common = common_volume(exposed_hook, refs["exterior"])
    cartridge_max = 0.0
    cartridge_min = math.inf
    samples = int(contract["limits"]["cartridge_service_samples"])
    distance = float(contract["limits"]["cartridge_service_distance_mm"])
    for index in range(samples):
        moved = refs["cartridge"].copy()
        moved.translate(cover["axis_n"] * distance * index / (samples - 1))
        cartridge_max = max(cartridge_max, common_volume(hook_compound, moved))
        cartridge_min = min(cartridge_min, float(hook_compound.distToShape(moved)[0]))

    upper = refs["mounts"]["upper"]
    upper_tool = Part.makeCylinder(
        4.0, 40.0, upper["eye_bore"] - upper["bore_axis_vector"] * 20.0,
        upper["bore_axis_vector"],
    )
    upper_tool_common = common_volume(hook_compound, upper_tool)
    bore_common = max(
        common_volume(hook_compound.fuse(cover["cover"]), mount["bore_cutter_solid"])
        for mount in refs["mounts"].values()
    )
    full_matrix = shell.full_owner_collision_matrix(
        final_target, components, replacements, poses, pivot, rotation_axis, translation_axis
    )
    min_wall = min(
        float(contract["hooks"]["root_wall_mm"]),
        float(contract["hooks"]["barb_axial_wall_mm"]),
        float(contract["hooks"]["tangent_width_mm"]),
    )
    snap_deflection = float(contract["hooks"]["barb_outward_overhang_mm"]) + float(contract["hooks"]["stem_inside_edge_clearance_mm"])
    checks = {
        "one_valid_closed_target_solid": bool(final_target.isValid() and final_target.isClosed() and len(final_target.Solids) == 1),
        "minimum_hook_wall": min_wall >= float(contract["hooks"]["minimum_wall_mm"]),
        "fixed_21_pose_hook_zero_collision": max_collision <= EPSILON,
        "fixed_21_pose_full_target_zero_collision": full_matrix["positive_intersection_count"] == 0,
        "assembly_clearance": min_clearance >= float(motion["required_hook_clearance_mm"]) - 0.01,
        "two_positive_outward_retention_hooks": all(each_hook_retained),
        "inside_expanded_cover_projection": hooks_outside_coverage <= EPSILON,
        "zero_frustum_hook_occupancy": frustum_common <= EPSILON,
        "zero_exposed_exterior_hook_occupancy": exterior_common <= EPSILON,
        "upper_tool_clear": upper_tool_common <= EPSILON,
        "cartridge_service_clear": cartridge_max <= EPSILON,
        "signed_mount_bores_untouched": bore_common <= EPSILON,
    }
    return {
        "status": "FEASIBILITY_PASS__FINAL_SHELL_PIN_REQUIRED_FOR_REVIEW" if all(checks.values()) else "FEASIBILITY_FAIL__NO_REVIEW_ARTIFACT",
        "checks": checks,
        "measurements": {
            "target_volume_mm3": float(final_target.Volume), "hook_count": len(hooks),
            "hook_records": hook_records, "minimum_hook_wall_mm": min_wall,
            "maximum_hook_motion_collision_mm3": max_collision,
            "minimum_hook_motion_clearance_mm": min_clearance,
            "full_target_motion_positive_collision_count": full_matrix["positive_intersection_count"],
            "full_target_motion_collisions": full_matrix["positive_intersections"],
            "hook_motion": motion_records, "retention_sweep": retention,
            "hooks_outside_cover_projection_mm3": hooks_outside_coverage,
            "frustum_hook_intersection_mm3": frustum_common,
            "exposed_exterior_hook_intersection_mm3": exterior_common,
            "upper_tool_intersection_mm3": upper_tool_common,
            "cartridge_maximum_intersection_mm3": cartridge_max,
            "cartridge_minimum_clearance_mm": cartridge_min,
            "mount_bore_additive_intersection_mm3": bore_common,
            "estimated_snap_deflection_mm": snap_deflection,
            "material_recommendation": "PETG_OR_NYLON" if snap_deflection > 0.6 else "PLA_ACCEPTABLE",
        },
    }


def prepare(*, review: bool) -> dict[str, Any]:
    contract = load_json(HERE / "contract.json")
    root, v1, validator, shell, paths = input_modules(contract)
    verify_inputs(contract, paths, review=review)
    stage = load_json(paths["stage_a"]); verify_motion(contract, stage)
    parameters = load_json(paths["v1_contract"])["allowed_mutations"][0]["parameters"]
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    candidate_before = sha256_file(paths["held_candidate"])
    document = App.openDocument(str(paths["held_candidate"]))
    try:
        target = document.getObject(contract["inputs"]["held_candidate"]["object"])
        if target is None or target.Shape.isNull():
            raise RuntimeError("held eye target missing")
        held = target.Shape.copy()
    finally:
        App.closeDocument(document.Name)
    if sha256_file(paths["held_candidate"]) != candidate_before:
        raise RuntimeError("held candidate changed while closing read-only input")

    refs = validator._reference_geometry(parameters, App, Part)
    cover = expanded_cover_geometry(parameters, contract, v1, App, Part)
    target_base = held.fuse(cover["cover"]).removeSplitter()
    v1.toolkit.require_single_solid(target_base, "held eye plus expanded cover")
    components = v1._load_shell_components(parameters, App, Part)
    inventory = {str(item.key): item for item in components}
    motion = load_json(paths["expanded_cover_shell_contract"])["motion"]
    relief_contract = {
        "motion": {**motion, "samples": contract["motion"]["samples"]},
        "serial_owner_stages": [
            {"owner": "lower_C001", "collision_poses": [11, 12, 13, 14, 15, 16, 17]},
            {"owner": "lower_C013", "collision_poses": [17, 18]},
        ],
    }
    pivot = App.Vector(*map(float, contract["motion"]["pivot_mm"]))
    rotation_axis = App.Vector(*map(float, contract["motion"]["rotation_axis"])); rotation_axis.normalize()
    translation_axis = App.Vector(*map(float, contract["motion"]["translation_axis_inward_n"])); translation_axis.normalize()
    replacements, relief_records = {}, []
    for owner_key in ("lower_C001", "lower_C013"):
        relieved, record = shell.relieve_owner_serially(
            owner_key, inventory[owner_key].shape, target_base, [cover["coverage"]],
            relief_contract, pivot, rotation_axis, translation_axis, App, Part,
        )
        replacements[owner_key] = relieved; relief_records.append(record)
    owner_shapes = {
        key: replacements.get(key, component.shape) for key, component in inventory.items()
    }
    hooks, hook_records = build_hooks(contract, cover, owner_shapes, v1, App, Part)
    final_target = v1.toolkit.fuse_shapes(
        [target_base, *hooks], "expanded-cover eye with two lower rim hooks"
    ).removeSplitter()
    v1.toolkit.require_single_solid(final_target, "final hook-retained review eye")
    evaluation = evaluate(
        contract, final_target, target_base, hooks, hook_records, cover, refs,
        components, replacements, shell, App, Part,
    )
    return {
        "root": root, "contract": contract, "paths": paths, "v1": v1,
        "App": App, "Part": Part, "held": held, "target_base": target_base,
        "final_target": final_target, "hooks": hooks, "cover": cover, "refs": refs,
        "components": components, "replacements": replacements,
        "shell_compound": shell_compound(components, replacements, Part),
        "evaluation": evaluation, "relief_records": relief_records,
        "candidate_before": candidate_before,
    }


def public_report(context: dict[str, Any], mode: str, elapsed: float) -> dict[str, Any]:
    contract = context["contract"]
    return {
        "schema_version": 1, "review_id": REVIEW_ID, "mode": mode,
        "status": context["evaluation"]["status"], "authority": contract["authority"],
        "pins": {
            "tool": sha256_file(Path(__file__)), "contract": sha256_file(HERE / "contract.json"),
            **{key: sha256_file(path) for key, path in context["paths"].items()},
        },
        "expanded_cover": contract["expanded_cover"],
        "serial_shell_relief": context["relief_records"],
        **context["evaluation"],
        "elapsed_seconds": elapsed,
        "io_trace": {
            "held_candidate_opened_read_only": True, "held_candidate_saved": False,
            "canonical_saved": False, "review_fcstd_saved": mode == "single_review_artifact",
            "geometry_export_created": False, "manufacturing_output_created": False,
        },
    }


def create_review(context: dict[str, Any], output: Path) -> Path:
    App = context["App"]
    doc = App.newDocument("RightEyeLowerRimHookRetentionReviewR1")
    try:
        entries = [
            ("REFERENCE__RELIEVED_SHELL_101", context["shell_compound"], (0.72, 0.72, 0.74), 70),
            ("REFERENCE__HELD_EYE", context["held"], (0.22, 0.56, 0.82), 55),
            ("PROPOSED__EXPANDED_COVER_EYE_WITH_HOOKS", context["final_target"], (0.16, 0.72, 0.36), 0),
            ("REFERENCE__REAR_CARTRIDGE", context["refs"]["cartridge"], (0.90, 0.62, 0.18), 35),
        ]
        for name, shape, color, transparency in entries:
            obj = doc.addObject("Part::Feature", name); obj.Label = name.replace("__", " — ")
            obj.Shape = shape.copy(); obj.addProperty("App::PropertyString", "Authority", "ReviewControl")
            obj.Authority = context["contract"]["authority"]
            obj.ViewObject.ShapeColor = color; obj.ViewObject.Transparency = transparency
        for index, hook in enumerate(context["hooks"], start=1):
            obj = doc.addObject("Part::Feature", f"PROPOSED__HOOK_{index}")
            obj.Shape = hook.copy(); obj.addProperty("App::PropertyString", "Authority", "ReviewControl")
            obj.Authority = "REFERENCE_DECOMPOSITION__PART_OF_PROPOSED_TARGET"
            obj.ViewObject.ShapeColor = (0.94, 0.42, 0.12); obj.ViewObject.Transparency = 0
        doc.recompute()
        path = output / context["contract"]["output"]["fcstd"]
        doc.saveAs(str(path)); return path
    finally:
        App.closeDocument(doc.Name)


def render_views(context: dict[str, Any], output: Path) -> None:
    toolkit = context["v1"].toolkit
    base = [
        toolkit.shape_record(context["shell_compound"], (150, 154, 160), deflection=1.0),
        toolkit.shape_record(context["held"], (42, 142, 190), deflection=0.65),
    ]
    proposed = [
        toolkit.shape_record(context["shell_compound"], (150, 154, 160), deflection=1.0),
        toolkit.shape_record(context["final_target"], (44, 180, 92), deflection=0.45),
    ]
    fixed = {
        "front.png": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "rear.png": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
        "lower-hooks.png": (tuple3(context["cover"]["axis_n"]), tuple3(context["cover"]["axis_u"])),
        "side.png": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    }
    for name, (direction, up) in fixed.items():
        toolkit.render_side_by_side(output / name, base, proposed, direction, up)
    pose = context["contract"]["motion"]["samples"][0]
    motion = context["contract"]["motion"]
    pivot = context["App"].Vector(*motion["pivot_mm"])
    rotation = context["App"].Vector(*motion["rotation_axis"])
    translation = context["App"].Vector(*motion["translation_axis_inward_n"])
    moved = context["final_target"].copy(); moved.rotate(pivot, rotation, pose[1]); moved.translate(translation * pose[2])
    insertion = [toolkit.shape_record(context["shell_compound"], (150,154,160), deflection=1.0), toolkit.shape_record(moved, (44,180,92), deflection=0.45)]
    toolkit.render_side_by_side(output / "insertion-15deg.png", base, insertion, (1.0, -1.0, 0.25), (0.0, 0.0, 1.0))


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("feasibility", "review"), required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--feasibility-report", type=Path)
    parser.add_argument("--feasibility-sha256")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    started = time.monotonic()
    review = args.mode == "review"
    context = prepare(review=review)
    if not context["evaluation"]["status"].startswith("FEASIBILITY_PASS"):
        raise RuntimeError(json.dumps(context["evaluation"], sort_keys=True))
    if not review:
        if args.report is None or args.report.exists():
            raise RuntimeError("feasibility requires one fresh --report path")
        report = public_report(context, "bounded_no_save_feasibility", time.monotonic() - started)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(context["evaluation"]["status"]); return 0
    if args.feasibility_report is None or not args.feasibility_sha256:
        raise RuntimeError("review requires exact pinned feasibility report")
    if sha256_file(args.feasibility_report) != args.feasibility_sha256:
        raise RuntimeError("feasibility report hash mismatch")
    if not load_json(args.feasibility_report)["status"].startswith("FEASIBILITY_PASS"):
        raise RuntimeError("pinned feasibility report is not a pass")
    output = context["root"] / context["contract"]["output"]["directory"]
    if output.exists():
        raise RuntimeError(f"review output already exists: {output}")
    output.mkdir(parents=True)
    fcstd = create_review(context, output); render_views(context, output)
    report = public_report(context, "single_review_artifact", time.monotonic() - started)
    report["review_fcstd"] = str(fcstd.relative_to(context["root"]))
    report["review_fcstd_sha256"] = sha256_file(fcstd)
    report["feasibility_report_sha256"] = args.feasibility_sha256
    validation = output / context["contract"]["output"]["validation"]
    validation.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if sha256_file(context["paths"]["held_candidate"]) != context["candidate_before"]:
        raise RuntimeError("held candidate changed")
    print("REVIEW_ONLY_ARTIFACT_CREATED__AWAIT_HUMAN_REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
