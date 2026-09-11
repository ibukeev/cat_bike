#!/usr/bin/env python3
"""Single corrected REVIEW_ONLY compliant-hook carrier feasibility/artifact."""

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
        raise RuntimeError(f"pinned analytic dependency changed: {actual} != {digest}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def construct_flexible_hooks(contract: dict[str, Any], geometry: dict[str, Any], components: Sequence[Any], r1: Any, v1: Any, App: Any, Part: Any) -> tuple[list[Any], list[dict[str, Any]]]:
    values = contract["hooks"]
    start, end = geometry["opening"][0], geometry["opening"][3]
    tangent = end - start; tangent.normalize()
    axis_n = geometry["refs"]["axis_n"]
    outward = axis_n.cross(tangent); outward.normalize()
    center = v1.toolkit.average(App, geometry["opening"])
    if outward.dot((start + end) * 0.5 - center) < 0.0:
        outward = outward * -1.0
    hooks, records = [], []
    for index, (fraction_raw, direction_raw) in enumerate(zip(values["station_fractions"], values["opposed_root_directions"]), start=1):
        fraction, direction = float(fraction_raw), float(direction_raw)
        tip_boundary = start + (end - start) * fraction
        root_boundary = tip_boundary + tangent * direction * float(values["compliant_arm_length_mm"])
        probe = tip_boundary + outward * float(values["rim_probe_outward_mm"])
        candidates = []
        for component in components:
            shape = component.shape
            if shape is None or shape.isNull():
                continue
            for interval in r1.axis_intervals(shape, probe, axis_n, 20.0, Part):
                candidates.append((abs((interval[0] + interval[1]) * 0.5), str(component.key), interval))
        if not candidates:
            raise RuntimeError(f"flex hook {index}: no exact lower rim interval")
        _, owner, interval = min(candidates)
        rear = float(interval[1])
        gap = float(values["rear_seated_gap_mm"])
        axial_wall = float(values["arm_axial_wall_mm"])
        front, back = rear + gap, rear + gap + axial_wall
        clearance = float(values["arm_inside_edge_clearance_mm"])
        root_wall = float(values["arm_root_wall_mm"])
        radial_center = -clearance - root_wall * 0.5
        arm_center = (root_boundary + tip_boundary) * 0.5 + outward * radial_center + axis_n * ((front + back) * 0.5)
        arm = v1.toolkit.oriented_box(
            Part, arm_center, (tangent, outward, axis_n),
            (float(values["compliant_arm_length_mm"]) + 0.20, root_wall, axial_wall),
        )
        root_front = float(values["root_front_depth_mm"])
        root_center = root_boundary + outward * radial_center + axis_n * ((root_front + back) * 0.5)
        root = v1.toolkit.oriented_box(
            Part, root_center, (tangent, outward, axis_n),
            (root_wall, root_wall, back - root_front),
        )
        tip_width = float(values["tip_tangent_width_mm"])
        inner = -clearance - 0.10
        outer = float(values["barb_tip_outward_offset_mm"])
        base = tip_boundary - tangent * (tip_width * 0.5)
        points = [
            base + outward * inner + axis_n * front,
            base + outward * outer + axis_n * front,
            base + outward * inner + axis_n * back,
        ]
        wire = Part.makePolygon([*points, points[0]])
        barb = Part.Face(wire).extrude(tangent * tip_width).removeSplitter()
        hook = root.fuse(arm).fuse(barb).removeSplitter()
        v1.toolkit.require_single_solid(hook, f"compliant lower hook {index}")
        hooks.append(hook)
        records.append({
            "station_index": index, "station_fraction": fraction, "owner": owner,
            "tip_boundary_mm": r1.vector_values(tip_boundary),
            "root_boundary_mm": r1.vector_values(root_boundary),
            "shell_interval_mm": list(interval), "shell_contact_span_mm": float(interval[1] - interval[0]),
            "rear_seated_gap_mm": gap, "arm_length_mm": float(values["compliant_arm_length_mm"]),
            "required_radial_deflection_mm": outer - (-clearance),
        })
    return hooks, records


def evaluate(contract: dict[str, Any], carrier: Any, base: Any, hooks: list[Any], records: list[dict[str, Any]], geometry: dict[str, Any], components: Sequence[Any], r1: Any, App: Any, Part: Any) -> dict[str, Any]:
    motion = contract["motion"]
    pivot = App.Vector(*map(float, motion["pivot_mm"]))
    rotation = App.Vector(*map(float, motion["rotation_axis"])); rotation.normalize()
    translation = App.Vector(*map(float, motion["translation_axis_inward_n"])); translation.normalize()
    hook_compound = Part.makeCompound(hooks)
    allowed = set(map(int, contract["hooks"]["allowed_compliant_contact_poses"]))
    motion_records = []
    base_maximum = 0.0
    disallowed_maximum = 0.0
    allowed_maximum = 0.0
    pose_clearance = {}
    pose_collision = {}
    for pose in motion["samples"]:
        sample = int(pose[0])
        moved_base = r1.posed(base, pose, pivot, rotation, translation)
        moved_hooks = r1.posed(hook_compound, pose, pivot, rotation, translation)
        base_collision, base_owner = r1.maximum_shell_common(moved_base, components)
        hook_collision, hook_owner = r1.maximum_shell_common(moved_hooks, components)
        hook_clearance, nearest = r1.minimum_shell_distance(moved_hooks, components)
        base_maximum = max(base_maximum, base_collision)
        if sample in allowed:
            allowed_maximum = max(allowed_maximum, hook_collision)
        else:
            disallowed_maximum = max(disallowed_maximum, hook_collision)
        pose_clearance[sample] = hook_clearance; pose_collision[sample] = hook_collision
        motion_records.append({
            "sample_index": sample, "base_collision_mm3": base_collision,
            "base_collision_owner": base_owner, "rigid_hook_collision_mm3": hook_collision,
            "hook_collision_owner": hook_owner, "rigid_hook_clearance_mm": hook_clearance,
            "nearest_owner": nearest, "compliant_contact_authorized": sample in allowed,
        })

    retention, retained = [], []
    threshold = float(contract["limits"]["minimum_outward_retention_collision_mm3"])
    for index, hook in enumerate(hooks, start=1):
        maximum = 0.0
        for distance_raw in contract["hooks"]["retention_test_outward_translations_mm"]:
            distance = float(distance_raw)
            moved = hook.copy(); moved.translate(geometry["refs"]["axis_n"] * -distance)
            collision, owner = r1.maximum_shell_common(moved, components)
            maximum = max(maximum, collision)
            retention.append({"hook": index, "outward_translation_mm": distance, "collision_mm3": collision, "owner": owner})
        retained.append(maximum >= threshold)

    deflection = max(float(item["required_radial_deflection_mm"]) for item in records)
    wall = float(contract["hooks"]["arm_root_wall_mm"])
    length = float(contract["hooks"]["compliant_arm_length_mm"])
    strain = 1.5 * wall * deflection / (length * length)
    pla_margin = float(contract["material"]["conservative_pla_allowable_strain"]) / strain
    petg_margin = float(contract["material"]["petg_allowable_strain"]) / strain
    nylon_margin = float(contract["material"]["nylon_allowable_strain"]) / strain
    hidden = carrier.cut(geometry["refs"]["bezel"]).removeSplitter()
    frustum = r1.common_volume(hidden, geometry["refs"]["frustum"])
    exterior = r1.common_volume(hook_compound, geometry["refs"]["exterior"])
    upper_bore = r1.common_volume(hook_compound, geometry["refs"]["mounts"]["upper"]["bore_cutter_solid"])
    cartridge_common = r1.common_volume(carrier, geometry["refs"]["cartridge"])
    cartridge_clearance = float(carrier.distToShape(geometry["refs"]["cartridge"])[0])
    seated_clearance = float(pose_clearance[20])
    preengagement_clearance = float(pose_clearance[15])
    min_wall = min(wall, float(contract["hooks"]["arm_axial_wall_mm"]))
    checks = {
        "one_valid_closed_carrier_solid": bool(carrier.isValid() and carrier.isClosed() and len(carrier.Solids) == 1),
        "minimum_1p2_mm_hook_wall": min_wall >= float(contract["hooks"]["minimum_wall_mm"]),
        "base_carrier_21_pose_zero_collision": base_maximum <= EPSILON,
        "rigid_contact_only_at_authorized_snap_poses": disallowed_maximum <= EPSILON and all(pose_collision[index] > EPSILON for index in allowed),
        "preengagement_clearance": preengagement_clearance >= float(contract["limits"]["minimum_preengagement_clearance_mm"]),
        "seated_zero_collision_and_clearance": pose_collision[20] <= EPSILON and seated_clearance >= float(contract["limits"]["minimum_seated_shell_clearance_mm"]),
        "elastic_deflection_at_or_below_0p60": deflection <= float(contract["limits"]["maximum_elastic_deflection_mm"]),
        "petg_strain_margin_at_least_one": petg_margin >= 1.0,
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
            "hook_records": records, "minimum_hook_wall_mm": min_wall,
            "maximum_base_motion_collision_mm3": base_maximum,
            "maximum_authorized_rigid_hook_contact_mm3": allowed_maximum,
            "maximum_disallowed_hook_collision_mm3": disallowed_maximum,
            "preengagement_pose15_clearance_mm": preengagement_clearance,
            "seated_pose20_clearance_mm": seated_clearance,
            "required_elastic_deflection_mm": deflection,
            "calculated_surface_strain": strain, "pla_strain_margin": pla_margin,
            "petg_strain_margin": petg_margin, "nylon_strain_margin": nylon_margin,
            "material_recommendation": "PETG_PREFERRED__PLA_MARGIN_FAIL" if pla_margin < 1.0 else "PLA_STATIC_PASS__PETG_PREFERRED_FOR_CYCLE_LIFE",
            "motion": motion_records, "retention_sweep": retention,
            "hidden_frustum_intersection_mm3": frustum,
            "hook_exterior_intersection_mm3": exterior,
            "upper_bore_intersection_mm3": upper_bore,
            "rear_cartridge_intersection_mm3": cartridge_common,
            "rear_cartridge_clearance_mm": cartridge_clearance,
        },
    }


def prepare() -> dict[str, Any]:
    contract = load_json(HERE / "contract.json")
    root = HERE.parents[8]
    r1_spec = contract["lineage_source"]["r1_generator"]
    r1_path = root / r1_spec["path"]
    r1 = load_module(r1_path, r1_spec["sha256"], "_front_flex_hook_r1")
    r1_contract_spec = contract["lineage_source"]["r1_contract"]
    if sha256_file(root / r1_contract_spec["path"]) != r1_contract_spec["sha256"]:
        raise RuntimeError("pinned R1 analytic contract changed")
    root2, v1, validator, paths = r1.load_dependencies(contract)
    if root2 != root:
        raise RuntimeError("repository root mismatch")
    stage = r1.load_json(paths["stage_a"]); r1.verify_motion(contract, stage)
    parameters = r1.load_json(paths["v1_contract"])["allowed_mutations"][0]["parameters"]
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore
    candidate_before = sha256_file(paths["held_candidate"])
    document = App.openDocument(str(paths["held_candidate"]))
    try:
        target = document.getObject(contract["inputs"]["held_candidate"]["object"])
        if target is None or target.Shape.isNull():
            raise RuntimeError("held source target missing")
        held = target.Shape.copy()
    finally:
        App.closeDocument(document.Name)
    if sha256_file(paths["held_candidate"]) != candidate_before:
        raise RuntimeError("held candidate changed")
    geometry = r1.construct_carrier(parameters, v1, validator, App, Part)
    components = v1._load_shell_components(parameters, App, Part)
    hooks, records = construct_flexible_hooks(contract, geometry, components, r1, v1, App, Part)
    carrier = v1.toolkit.fuse_shapes([geometry["base"], *hooks], "front carrier with compliant lower hooks").removeSplitter()
    v1.toolkit.require_single_solid(carrier, "front carrier with compliant lower hooks")
    evaluation = evaluate(contract, carrier, geometry["base"], hooks, records, geometry, components, r1, App, Part)
    shell = Part.makeCompound([item.shape for item in components if item.shape is not None])
    return {"root": root, "contract": contract, "paths": paths, "r1": r1, "v1": v1, "App": App, "Part": Part, "held": held, "geometry": geometry, "components": components, "shell": shell, "hooks": hooks, "carrier": carrier, "evaluation": evaluation, "candidate_before": candidate_before}


def public_report(context: dict[str, Any], mode: str, elapsed: float) -> dict[str, Any]:
    return {
        "schema_version": 1, "review_id": context["contract"]["review_id"],
        "authority": context["contract"]["authority"], "mode": mode,
        "pins": {"tool": sha256_file(Path(__file__)), "contract": sha256_file(HERE / "contract.json"), **{key: sha256_file(path) for key, path in context["paths"].items()}},
        **context["evaluation"], "elapsed_seconds": elapsed,
        "io_trace": {"held_candidate_opened_read_only": True, "held_candidate_saved": False, "canonical_saved": False, "geometry_export_created": False, "production_output_created": False, "review_fcstd_saved": mode == "single_review_artifact"},
    }


def create_review(context: dict[str, Any], output: Path) -> Path:
    App = context["App"]
    doc = App.newDocument("RightEyeFrontCarrierFlexHooksReviewR2")
    try:
        entries = [
            ("REFERENCE__SHELL_101", context["shell"], (0.72,0.72,0.74), 72),
            ("REFERENCE__HELD_SPLIT_EYE", context["held"], (0.20,0.58,0.82), 70),
            ("PROPOSED__FRONT_CARRIER_FLEX_HOOKS_R2", context["carrier"], (0.14,0.74,0.34), 0),
            ("REFERENCE__INSIDE_INSTALLED_REAR_CARTRIDGE", context["geometry"]["refs"]["cartridge"], (0.90,0.62,0.18), 30),
        ]
        for name, shape, color, transparency in entries:
            obj = doc.addObject("Part::Feature", name); obj.Label = name.replace("__", " — ")
            obj.Shape = shape.copy(); obj.addProperty("App::PropertyString", "Authority", "ReviewControl")
            obj.Authority = context["contract"]["authority"]
            obj.ViewObject.ShapeColor = color; obj.ViewObject.Transparency = transparency
        for index, hook in enumerate(context["hooks"], start=1):
            obj = doc.addObject("Part::Feature", f"REFERENCE__COMPLIANT_HOOK_{index}")
            obj.Shape = hook.copy(); obj.addProperty("App::PropertyString", "Authority", "ReviewControl")
            obj.Authority = "REFERENCE_DECOMPOSITION__PART_OF_PROPOSED_CARRIER"
            obj.ViewObject.ShapeColor = (0.95,0.40,0.10)
        proposed = doc.getObject("PROPOSED__FRONT_CARRIER_FLEX_HOOKS_R2")
        proposed.addProperty("App::PropertyVector", "UpperEyeBoreCenter", "ProtectedDatums")
        proposed.addProperty("App::PropertyVector", "UpperSignedBoreAxis", "ProtectedDatums")
        proposed.addProperty("App::PropertyVector", "UnusedLowerBoreReference", "ProtectedDatums")
        proposed.UpperEyeBoreCenter = context["geometry"]["refs"]["mounts"]["upper"]["eye_bore"]
        proposed.UpperSignedBoreAxis = context["geometry"]["refs"]["mounts"]["upper"]["bore_axis_vector"]
        proposed.UnusedLowerBoreReference = context["geometry"]["refs"]["mounts"]["lower"]["eye_bore"]
        doc.recompute(); path = output / context["contract"]["output"]["fcstd"]
        doc.saveAs(str(path)); return path
    finally:
        App.closeDocument(doc.Name)


def render_views(context: dict[str, Any], output: Path) -> None:
    toolkit = context["v1"].toolkit
    base = [toolkit.shape_record(context["shell"], (150,154,160), deflection=1.0), toolkit.shape_record(context["held"], (42,142,190), deflection=0.7)]
    proposed = [toolkit.shape_record(context["shell"], (150,154,160), deflection=1.0), toolkit.shape_record(context["carrier"], (44,180,92), deflection=0.4), toolkit.shape_record(context["geometry"]["refs"]["cartridge"], (223,164,54), deflection=0.55)]
    fixed = {
        "front.png": ((0.0,1.0,0.0),(0.0,0.0,1.0)),
        "rear.png": ((0.0,-1.0,0.0),(0.0,0.0,1.0)),
        "lower-hooks.png": (tuple(-value for value in r1_tuple(context["geometry"]["refs"]["axis_n"])), r1_tuple(context["geometry"]["refs"]["axis_u"])),
        "side.png": ((1.0,0.0,0.0),(0.0,0.0,1.0)),
    }
    for name, (direction, up) in fixed.items():
        toolkit.render_side_by_side(output / name, base, proposed, direction, up)
    pose = context["contract"]["motion"]["samples"][8]
    motion = context["contract"]["motion"]
    moved = r1_posed(context["carrier"], pose, motion, context["App"])
    insertion = [toolkit.shape_record(context["shell"], (150,154,160), deflection=1.0), toolkit.shape_record(moved, (44,180,92), deflection=0.4)]
    toolkit.render_side_by_side(output / "insertion-15deg.png", base, insertion, (1.0,-1.0,0.25),(0.0,0.0,1.0))


def r1_tuple(vector: Any) -> tuple[float, float, float]:
    return (float(vector.x), float(vector.y), float(vector.z))


def r1_posed(shape: Any, pose: Sequence[float], motion: dict[str, Any], App: Any) -> Any:
    moved = shape.copy(); moved.rotate(App.Vector(*motion["pivot_mm"]), App.Vector(*motion["rotation_axis"]), float(pose[1])); moved.translate(App.Vector(*motion["translation_axis_inward_n"]) * float(pose[2])); return moved


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--mode", choices=("feasibility","review"), required=True)
    parser.add_argument("--report", type=Path); parser.add_argument("--feasibility-report", type=Path); parser.add_argument("--feasibility-sha256")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    started = time.monotonic(); context = prepare()
    if context["evaluation"]["status"] != "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED":
        print(json.dumps(public_report(context, "bounded_no_save_feasibility", time.monotonic()-started), indent=2, sort_keys=True))
        raise RuntimeError("corrected flexible-hook feasibility failed")
    if args.mode == "feasibility":
        if args.report is None or args.report.exists(): raise RuntimeError("fresh --report required")
        report = public_report(context, "bounded_no_save_feasibility", time.monotonic()-started)
        args.report.parent.mkdir(parents=True, exist_ok=True); args.report.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(report["status"]); return 0
    if args.feasibility_report is None or not args.feasibility_sha256 or sha256_file(args.feasibility_report) != args.feasibility_sha256:
        raise RuntimeError("review requires exact pinned feasibility report")
    output = context["root"] / context["contract"]["output"]["directory"]
    if output.exists(): raise RuntimeError(f"review output exists: {output}")
    output.mkdir(parents=True); fcstd = create_review(context, output); render_views(context, output)
    report = public_report(context, "single_review_artifact", time.monotonic()-started)
    report["review_fcstd"] = str(fcstd.relative_to(context["root"])); report["review_fcstd_sha256"] = sha256_file(fcstd); report["feasibility_report_sha256"] = args.feasibility_sha256
    (output / context["contract"]["output"]["validation"]).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("REVIEW_ONLY_ARTIFACT_CREATED__AWAIT_HUMAN_REVIEW"); return 0


if __name__ == "__main__":
    raise SystemExit(main())
