#!/usr/bin/env python3
"""Bounded front-carrier/hook feasibility; never mutates held or shell inputs."""

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
        raise RuntimeError(f"pinned module changed: {actual} != {digest}")
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


def vector_values(vector: Any) -> list[float]:
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


def posed(shape: Any, pose: Sequence[float], pivot: Any, rotation_axis: Any, translation_axis: Any) -> Any:
    moved = shape.copy()
    moved.rotate(pivot, rotation_axis, float(pose[1]))
    moved.translate(translation_axis * float(pose[2]))
    return moved


def axis_intervals(shape: Any, anchor: Any, axis: Any, half: float, Part: Any) -> list[tuple[float, float]]:
    line = Part.makeLine(anchor - axis * half, anchor + axis * half)
    common = line.common(shape)
    output = []
    for edge in common.Edges:
        values = sorted(float((vertex.Point - anchor).dot(axis)) for vertex in edge.Vertexes)
        if len(values) >= 2 and values[-1] - values[0] > 1.0e-7:
            output.append((values[0], values[-1]))
    return sorted(output)


def maximum_shell_common(shape: Any, components: Sequence[Any]) -> tuple[float, str | None]:
    maximum, owner = 0.0, None
    for component in components:
        obstacle = component.shape
        if obstacle is None or obstacle.isNull() or not aabb_near(shape, obstacle):
            continue
        volume = common_volume(shape, obstacle)
        if volume > maximum:
            maximum, owner = volume, str(component.key)
    return maximum, owner


def minimum_shell_distance(shape: Any, components: Sequence[Any]) -> tuple[float, str | None]:
    minimum, owner = math.inf, None
    for component in components:
        obstacle = component.shape
        if obstacle is None or obstacle.isNull() or not aabb_near(shape, obstacle, 4.0):
            continue
        distance = float(shape.distToShape(obstacle)[0])
        if distance < minimum:
            minimum, owner = distance, str(component.key)
    return minimum, owner


def load_dependencies(contract: dict[str, Any]) -> tuple[Path, Any, Any, dict[str, Path]]:
    root = HERE.parents[8]
    paths = {
        key: resolve(root, value) for key, value in contract["inputs"].items()
    }
    for key, path in paths.items():
        actual = sha256_file(path)
        if actual != contract["inputs"][key]["sha256"]:
            raise RuntimeError(f"{key} hash mismatch: {actual}")
    v1 = load_module(
        paths["v1_generator"], contract["inputs"]["v1_generator"]["sha256"],
        "_front_hook_v1",
    )
    validator = load_module(
        paths["v1_validator"], contract["inputs"]["v1_validator"]["sha256"],
        "_front_hook_validator",
    )
    if v1.repo_root() != root:
        raise RuntimeError("repository root mismatch")
    return root, v1, validator, paths


def verify_motion(contract: dict[str, Any], stage: dict[str, Any]) -> None:
    datum = stage["derived_datums"]
    if datum["pivot_role"] != "lower_eye_bore_center":
        raise RuntimeError("Stage-A pivot role changed")
    for key in ("pivot_mm", "rotation_axis", "translation_axis_inward_n"):
        if list(map(float, datum[key])) != list(map(float, contract["motion"][key])):
            raise RuntimeError(f"Stage-A motion datum changed: {key}")
    samples = [
        [int(item["sample_index"]), float(item["tilt_deg"]), float(item["translation_mm"])]
        for item in stage["paths"][2]["samples"]
    ]
    expected = [[int(item[0]), float(item[1]), float(item[2])] for item in contract["motion"]["samples"]]
    if samples != expected:
        raise RuntimeError("Stage-A 21-pose path changed")


def construct_carrier(parameters: dict[str, Any], v1: Any, validator: Any, App: Any, Part: Any) -> dict[str, Any]:
    refs = validator._reference_geometry(parameters, App, Part)
    toolkit = v1.toolkit
    lcs = parameters["aperture_lcs"]
    geometry = parameters["geometry"]
    origin, axis_u, axis_v, axis_n = refs["origin"], refs["axis_u"], refs["axis_v"], refs["axis_n"]
    opening = toolkit.planar_loop(
        [toolkit.vector(App, point) for point in geometry["shell_opening_boundary_mm"]],
        origin, axis_u, axis_v, axis_n,
    )
    rear_insets = geometry["front_optical_cassette"]["rear_outer_vertex_insets_mm"]
    outer_rear = v1._locally_inset_loop(App, opening, rear_insets, axis_n)
    upper = refs["mounts"]["upper"]
    ligament, ligament_record = v1._explicit_mount_ligament(
        "upper", upper, outer_rear, geometry["head_mount"],
        origin, axis_u, axis_v, axis_n, App, Part,
    )
    base = toolkit.fuse_shapes(
        [refs["pocket"], refs["cover_lip"], upper["drilled"], ligament],
        "front carrier with exact upper mount",
    )
    base = base.cut(upper["bore_cutter_solid"]).removeSplitter()
    toolkit.require_single_solid(base, "front carrier base")
    return {
        "base": base, "refs": refs, "opening": opening, "outer_rear": outer_rear,
        "upper_ligament": ligament, "upper_ligament_record": ligament_record,
    }


def construct_hooks(contract: dict[str, Any], geometry: dict[str, Any], components: Sequence[Any], v1: Any, App: Any, Part: Any) -> tuple[list[Any], list[dict[str, Any]]]:
    values = contract["hooks"]
    if values["lower_opening_edge_indices"] != [0, 3]:
        raise RuntimeError("lower opening edge changed")
    start, end = geometry["opening"][0], geometry["opening"][3]
    tangent = end - start; tangent.normalize()
    axis_n = geometry["refs"]["axis_n"]
    outward = axis_n.cross(tangent); outward.normalize()
    center = v1.toolkit.average(App, geometry["opening"])
    if outward.dot((start + end) * 0.5 - center) < 0.0:
        outward = outward * -1.0
    hooks, records = [], []
    for index, fraction_raw in enumerate(values["station_fractions"], start=1):
        fraction = float(fraction_raw)
        boundary = start + (end - start) * fraction
        probe = boundary + outward * float(values["rim_probe_outward_mm"])
        candidates = []
        for component in components:
            shape = component.shape
            if shape is None or shape.isNull():
                continue
            for interval in axis_intervals(shape, probe, axis_n, 20.0, Part):
                candidates.append((abs((interval[0] + interval[1]) * 0.5), str(component.key), interval))
        if not candidates:
            raise RuntimeError(f"hook station {index}: no exact aperture-rim shell interval")
        _, owner, interval = min(candidates)
        shell_rear = float(interval[1])
        clearance = float(values["stem_inside_edge_clearance_mm"])
        root_wall = float(values["root_wall_mm"])
        rear_gap = float(values["rear_clearance_mm"])
        barb_wall = float(values["barb_axial_wall_mm"])
        stem_front = float(values["root_front_depth_mm"])
        barb_front = shell_rear + rear_gap
        barb_back = barb_front + barb_wall
        if barb_back <= stem_front:
            raise RuntimeError(f"hook station {index}: nonpositive stem length")
        stem_center = boundary - outward * (clearance + root_wall * 0.5) + axis_n * ((stem_front + barb_back) * 0.5)
        stem = v1.toolkit.oriented_box(
            Part, stem_center, (tangent, outward, axis_n),
            (float(values["tangent_width_mm"]), root_wall, barb_back - stem_front),
        )
        barb_inner = -clearance - 0.10
        barb_outer = float(values["barb_outward_overhang_mm"])
        barb_center = boundary + outward * ((barb_inner + barb_outer) * 0.5) + axis_n * ((barb_front + barb_back) * 0.5)
        barb = v1.toolkit.oriented_box(
            Part, barb_center, (tangent, outward, axis_n),
            (float(values["tangent_width_mm"]), barb_outer - barb_inner, barb_wall),
        )
        hook = stem.fuse(barb).removeSplitter()
        v1.toolkit.require_single_solid(hook, f"lower hook {index}")
        hooks.append(hook)
        records.append({
            "station_index": index, "station_fraction": fraction, "owner": owner,
            "boundary_mm": vector_values(boundary), "probe_mm": vector_values(probe),
            "shell_interval_mm": list(interval),
            "shell_contact_span_mm": float(interval[1] - interval[0]),
            "seated_rear_clearance_mm": rear_gap,
        })
    return hooks, records


def evaluate(contract: dict[str, Any], carrier: Any, base: Any, hooks: list[Any], hook_records: list[dict[str, Any]], geometry: dict[str, Any], components: Sequence[Any], App: Any, Part: Any) -> dict[str, Any]:
    motion = contract["motion"]
    pivot = App.Vector(*map(float, motion["pivot_mm"]))
    rotation_axis = App.Vector(*map(float, motion["rotation_axis"])); rotation_axis.normalize()
    translation_axis = App.Vector(*map(float, motion["translation_axis_inward_n"])); translation_axis.normalize()
    hook_compound = Part.makeCompound(hooks)
    motion_records, maximum, minimum = [], 0.0, math.inf
    full_maximum = 0.0
    for pose in motion["samples"]:
        moved_hooks = posed(hook_compound, pose, pivot, rotation_axis, translation_axis)
        collision, owner = maximum_shell_common(moved_hooks, components)
        clearance, nearest = minimum_shell_distance(moved_hooks, components)
        moved_carrier = posed(carrier, pose, pivot, rotation_axis, translation_axis)
        full_collision, full_owner = maximum_shell_common(moved_carrier, components)
        maximum = max(maximum, collision); minimum = min(minimum, clearance)
        full_maximum = max(full_maximum, full_collision)
        motion_records.append({
            "sample_index": int(pose[0]), "hook_collision_mm3": collision,
            "hook_collision_owner": owner, "hook_clearance_mm": clearance,
            "hook_nearest_owner": nearest, "carrier_collision_mm3": full_collision,
            "carrier_collision_owner": full_owner,
        })
    retention, retained = [], []
    threshold = float(contract["limits"]["minimum_outward_retention_collision_mm3"])
    for index, hook in enumerate(hooks, start=1):
        hook_max = 0.0
        for distance_raw in contract["hooks"]["retention_test_outward_translations_mm"]:
            distance = float(distance_raw)
            moved = hook.copy(); moved.translate(geometry["refs"]["axis_n"] * -distance)
            collision, owner = maximum_shell_common(moved, components)
            hook_max = max(hook_max, collision)
            retention.append({"hook": index, "outward_translation_mm": distance, "collision_mm3": collision, "owner": owner})
        retained.append(hook_max >= threshold)
    hidden = carrier.cut(geometry["refs"]["bezel"]).removeSplitter()
    frustum = common_volume(hidden, geometry["refs"]["frustum"])
    exterior = common_volume(hook_compound, geometry["refs"]["exterior"])
    upper_bore = common_volume(hook_compound, geometry["refs"]["mounts"]["upper"]["bore_cutter_solid"])
    cartridge_common = common_volume(carrier, geometry["refs"]["cartridge"])
    cartridge_clearance = float(carrier.distToShape(geometry["refs"]["cartridge"])[0])
    min_wall = min(
        float(contract["hooks"]["root_wall_mm"]),
        float(contract["hooks"]["barb_axial_wall_mm"]),
        float(contract["hooks"]["tangent_width_mm"]),
    )
    snap_deflection = float(contract["hooks"]["barb_outward_overhang_mm"]) + float(contract["hooks"]["stem_inside_edge_clearance_mm"])
    checks = {
        "one_valid_closed_carrier_solid": bool(carrier.isValid() and carrier.isClosed() and len(carrier.Solids) == 1),
        "minimum_hook_wall": min_wall >= float(contract["hooks"]["minimum_wall_mm"]),
        "front_carrier_21_pose_zero_collision": full_maximum <= EPSILON,
        "hook_21_pose_zero_collision": maximum <= EPSILON,
        "hook_assembly_clearance": minimum >= float(motion["required_clearance_mm"]) - 0.01,
        "two_positive_pullout_retention_hooks": all(retained),
        "zero_hidden_frustum_occupancy": frustum <= EPSILON,
        "zero_hook_exterior_occupancy": exterior <= EPSILON,
        "upper_signed_bore_clear": upper_bore <= EPSILON,
        "rear_cartridge_separate_and_clear": cartridge_common <= EPSILON and cartridge_clearance >= float(contract["limits"]["cartridge_static_clearance_mm"]),
    }
    return {
        "status": "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED" if all(checks.values()) else "FEASIBILITY_FAIL__NO_REVIEW_ARTIFACT",
        "checks": checks,
        "measurements": {
            "carrier_volume_mm3": float(carrier.Volume), "base_volume_mm3": float(base.Volume),
            "hook_count": len(hooks), "hook_records": hook_records,
            "minimum_hook_wall_mm": min_wall, "maximum_hook_motion_collision_mm3": maximum,
            "maximum_carrier_motion_collision_mm3": full_maximum,
            "minimum_hook_motion_clearance_mm": minimum, "motion": motion_records,
            "retention_sweep": retention, "hidden_frustum_intersection_mm3": frustum,
            "hook_exterior_intersection_mm3": exterior, "upper_bore_intersection_mm3": upper_bore,
            "rear_cartridge_intersection_mm3": cartridge_common,
            "rear_cartridge_clearance_mm": cartridge_clearance,
            "estimated_snap_deflection_mm": snap_deflection,
            "material_recommendation": "PETG_OR_NYLON" if snap_deflection > 0.6 else "PLA_ACCEPTABLE",
        },
    }


def prepare() -> dict[str, Any]:
    contract = load_json(HERE / "contract.json")
    root, v1, validator, paths = load_dependencies(contract)
    stage = load_json(paths["stage_a"]); verify_motion(contract, stage)
    parameters = load_json(paths["v1_contract"])["allowed_mutations"][0]["parameters"]
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore
    before = sha256_file(paths["held_candidate"])
    document = App.openDocument(str(paths["held_candidate"]))
    try:
        target = document.getObject(contract["inputs"]["held_candidate"]["object"])
        if target is None or target.Shape.isNull():
            raise RuntimeError("held source target missing")
        held_record = {"volume_mm3": float(target.Shape.Volume), "valid": bool(target.Shape.isValid())}
    finally:
        App.closeDocument(document.Name)
    if sha256_file(paths["held_candidate"]) != before:
        raise RuntimeError("held candidate changed")
    geometry = construct_carrier(parameters, v1, validator, App, Part)
    components = v1._load_shell_components(parameters, App, Part)
    hooks, hook_records = construct_hooks(contract, geometry, components, v1, App, Part)
    carrier = v1.toolkit.fuse_shapes([geometry["base"], *hooks], "front carrier with lower hooks").removeSplitter()
    v1.toolkit.require_single_solid(carrier, "front carrier with lower hooks")
    evaluation = evaluate(contract, carrier, geometry["base"], hooks, hook_records, geometry, components, App, Part)
    return {
        "root": root, "contract": contract, "paths": paths, "v1": v1,
        "App": App, "Part": Part, "geometry": geometry, "components": components,
        "hooks": hooks, "carrier": carrier, "evaluation": evaluation,
        "held_record": held_record, "held_sha256": before,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("feasibility",), required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.report.exists():
        raise RuntimeError("fresh feasibility --report is required")
    started = time.monotonic(); context = prepare()
    report = {
        "schema_version": 1, "review_id": context["contract"]["review_id"],
        "authority": context["contract"]["authority"], "mode": "bounded_no_save_feasibility",
        "pins": {"tool": sha256_file(Path(__file__)), "contract": sha256_file(HERE / "contract.json"), **{key: sha256_file(path) for key, path in context["paths"].items()}},
        "held_source": context["held_record"], **context["evaluation"],
        "elapsed_seconds": time.monotonic() - started,
        "io_trace": {"held_candidate_opened_read_only": True, "held_candidate_saved": False, "review_fcstd_saved": False, "geometry_export_created": False, "production_output_created": False},
    }
    if report["status"] != "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED":
        print(json.dumps(report, indent=2, sort_keys=True))
        raise RuntimeError("bounded front-carrier feasibility failed")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(report["status"]); return 0


if __name__ == "__main__":
    raise SystemExit(main())
