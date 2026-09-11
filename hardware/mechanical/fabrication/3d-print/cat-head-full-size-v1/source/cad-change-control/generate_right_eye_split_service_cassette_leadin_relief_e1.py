#!/usr/bin/env python3
"""Build and preflight the additive E1 lower lead-in relief in memory only.

The immutable split-cassette V1 generator remains the nominal-geometry
authority.  E1 subtracts only conservative, inverse-mapped world-frame
BoundBoxes of exact collision commons along the approved fixed-15-degree path.
This module has no candidate/open/save/export/promotion code path.
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


GENERATOR_ID = "right-eye-split-service-cassette-leadin-relief-e1"
V1_GENERATOR = "generate_right_eye_split_service_cassette_prototype_v1.py"
V1_GENERATOR_SHA256 = "611aa4b63a0cd81420a01507168095c9a0a4d967d306688d78fe69b5383815fc"
V1_VALIDATOR = "validate_right_eye_split_service_cassette_previsual_v1.py"
V1_VALIDATOR_SHA256 = "d7ad39bea689e8df54484eaf97c9077df73d3c8c8eb03c18696859ea15133ccf"
V1_CONTRACT_RELATIVE = (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/v2/right-eye-split-service-cassette-prototype-v1.json"
)
V1_CONTRACT_SHA256 = "08fa1c89ad307598e8b0edaa3dc55085cd2ddc977904209972ca698d21790b9f"
E1_CONTRACT_RELATIVE = (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/v2/right-eye-split-service-cassette-leadin-relief-e1.json"
)
COLLISION_POSES = {
    "lower_C001": (11, 12, 13, 14, 15, 16, 17),
    "lower_C013": (17, 18),
}
POSES = (
    (0, 15.0, -45.0), (1, 15.0, -40.5), (2, 15.0, -36.0),
    (3, 15.0, -31.5), (4, 15.0, -27.0), (5, 15.0, -22.5),
    (6, 15.0, -18.0), (7, 15.0, -13.5), (8, 15.0, -9.0),
    (9, 13.75, -8.25), (10, 12.5, -7.5), (11, 11.25, -6.75),
    (12, 10.000000000000002, -6.000000000000001),
    (13, 8.749999999999998, -5.249999999999999),
    (14, 7.5, -4.5), (15, 6.249999999999999, -3.7499999999999996),
    (16, 5.000000000000001, -3.0000000000000004),
    (17, 3.75, -2.25),
    (18, 2.4999999999999996, -1.4999999999999996),
    (19, 1.2500000000000004, -0.7500000000000003), (20, 0.0, -0.0),
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_pinned(filename: str, digest: str, module_name: str) -> Any:
    path = Path(__file__).with_name(filename)
    actual = sha256_file(path)
    if actual != digest:
        raise RuntimeError(f"immutable dependency changed: {filename}: {actual}")
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


v1 = _load_pinned(V1_GENERATOR, V1_GENERATOR_SHA256, "_e1_nominal_generator_v1")
validator_v1 = _load_pinned(V1_VALIDATOR, V1_VALIDATOR_SHA256, "_e1_validator_v1")


def _load_inputs() -> tuple[Path, dict[str, Any], dict[str, Any]]:
    root = v1.repo_root()
    v1_path = root / V1_CONTRACT_RELATIVE
    if sha256_file(v1_path) != V1_CONTRACT_SHA256:
        raise RuntimeError("immutable V1 contract hash mismatch")
    v1_contract = json.loads(v1_path.read_text(encoding="utf-8"))
    e1_path = root / E1_CONTRACT_RELATIVE
    e1_contract = json.loads(e1_path.read_text(encoding="utf-8"))
    if e1_contract.get("schema_version") != "cat-head-right-eye-split-service-cassette-leadin-relief-e1-v1":
        raise RuntimeError("unexpected E1 contract schema")
    embedded = tuple(
        (int(item["sample_index"]), float(item["tilt_deg"]),
         float(item["translation_mm"]))
        for item in e1_contract["motion_path"]["samples"]
    )
    if embedded != POSES:
        raise RuntimeError("E1 contract embedded pose table changed")
    declared_collisions = {
        key: tuple(map(int, values))
        for key, values in e1_contract["relief"]["collision_poses"].items()
    }
    if declared_collisions != COLLISION_POSES:
        raise RuntimeError("E1 contract collision-pose scope changed")
    return root, v1_contract["allowed_mutations"][0]["parameters"], e1_contract


def _pose_record(index: int) -> tuple[float, float]:
    record = POSES[index]
    if record[0] != index:
        raise RuntimeError("non-contiguous embedded E1 pose table")
    return float(record[1]), float(record[2])


def _posed(shape: Any, index: int, pivot: Any, rotation_axis: Any,
            translation_axis: Any) -> Any:
    tilt, translation = _pose_record(index)
    moved = shape.copy()
    moved.rotate(pivot, rotation_axis, tilt)
    moved.translate(translation_axis * translation)
    return moved


def _inverse_mapped_expanded_box(common: Any, clearance: float, index: int,
                                 pivot: Any, rotation_axis: Any,
                                 translation_axis: Any, App: Any,
                                 Part: Any) -> tuple[Any, dict[str, Any]]:
    box = common.BoundBox
    minimum = [float(box.XMin) - clearance, float(box.YMin) - clearance,
               float(box.ZMin) - clearance]
    maximum = [float(box.XMax) + clearance, float(box.YMax) + clearance,
               float(box.ZMax) + clearance]
    cutter = Part.makeBox(
        maximum[0] - minimum[0], maximum[1] - minimum[1],
        maximum[2] - minimum[2], App.Vector(*minimum),
    )
    tilt, translation = _pose_record(index)
    cutter.translate(translation_axis * (-translation))
    cutter.rotate(pivot, rotation_axis, -tilt)
    return cutter, {
        "source_sample_index": index,
        "tilt_deg": tilt,
        "translation_mm": translation,
        "exact_common_mm3": float(common.Volume),
        "world_common_bbox_minimum_mm": [float(box.XMin), float(box.YMin), float(box.ZMin)],
        "world_common_bbox_maximum_mm": [float(box.XMax), float(box.YMax), float(box.ZMax)],
        "world_expanded_bbox_minimum_mm": minimum,
        "world_expanded_bbox_maximum_mm": maximum,
    }


def _datum_guard_parts(parameters: dict[str, Any], construction: dict[str, Any],
                       App: Any, Part: Any) -> dict[str, Any]:
    values = parameters["geometry"]["head_mount"]
    bore_radius = float(values["bore_diameter_mm"]) / 2.0
    minimum_wall = 0.7
    total = float(values["total_thickness_mm"])
    face_offset = float(values["bore_center_to_mating_face_mm"])
    pilot_radius = float(values["shell_side_pilot_radius_mm"])
    bearing_radius = bore_radius + float(values["bore_to_edge_material_mm"])
    seat_guard_depth = 0.05
    guards = {}
    for role, mount in construction["mounts"].items():
        axis = mount["bore_axis_vector"]
        center = mount["eye_bore"]
        base = center - axis * face_offset
        retreat = float(mount["shell_face_retreat_mm"])
        core = Part.makeCylinder(
            bore_radius + minimum_wall,
            total - retreat,
            base + axis * retreat,
            axis,
        )
        shell_seat = Part.makeCylinder(
            pilot_radius, seat_guard_depth,
            base + axis * retreat, axis,
        )
        eye_seat = Part.makeCylinder(
            bearing_radius, seat_guard_depth,
            base + axis * (total - seat_guard_depth), axis,
        )
        bore = mount["bore_cutter_solid"]
        guards[f"{role}_bore_wall_core"] = core.cut(bore)
        guards[f"{role}_shell_mating_seat"] = shell_seat.cut(bore)
        guards[f"{role}_eye_mating_seat"] = eye_seat.cut(bore)
    return guards


def _datum_guards(parameters: dict[str, Any], construction: dict[str, Any],
                  App: Any, Part: Any) -> Any:
    guards = _datum_guard_parts(parameters, construction, App, Part)
    return v1.toolkit.fuse_shapes(
        list(guards.values()), "E1 fused bore-core and mating-seat guards",
        require_one=False,
    )


def _ligament_guards(parameters: dict[str, Any], construction: dict[str, Any],
                     App: Any, Part: Any) -> dict[str, Any]:
    values = parameters["geometry"]["head_mount"]
    output = {}
    for role, frame in construction["mounts"].items():
        ligament, _ = v1._explicit_mount_ligament(
            role, frame, construction["outer_rear"], values,
            construction["origin"], construction["axis_u"],
            construction["axis_v"], construction["axis_n"], App, Part,
        )
        output[role] = ligament
    return output


def _optical_guards(construction: dict[str, Any], App: Any, Part: Any) -> dict[str, Any]:
    """Protect the exact visible skin/wire and lip, not the hidden cassette."""
    toolkit = v1.toolkit
    axis_n = construction["axis_n"]
    aperture = construction["aperture_planar"]
    aperture_outer = toolkit.radial_offset_loop(App, aperture, 0.7, axis_n)
    aperture_inner = toolkit.radial_offset_loop(App, aperture, -0.05, axis_n)
    aperture_band = toolkit.ring_prism(
        Part, aperture_outer, aperture_inner, -0.05, 1.25, axis_n,
        "E1 protected 0.7 mm aperture band",
    ).common(construction["cassette"]).removeSplitter()
    front_skin_depth = 0.7
    front_slab = toolkit.oriented_box(
        Part,
        construction["origin"] + axis_n * (front_skin_depth / 2.0),
        (construction["axis_u"], construction["axis_v"], axis_n),
        (200.0, 200.0, front_skin_depth),
    )
    front_skin = front_slab.common(construction["cassette"]).removeSplitter()
    return {
        "aperture_band": aperture_band,
        "front_skin": front_skin,
        "cover_lip": construction["cover_lip"],
    }


def construct_e1(parameters: dict[str, Any], contract: dict[str, Any],
                 App: Any, Part: Any) -> tuple[Any, dict[str, Any]]:
    nominal, construction = v1.construct_split_cassette(parameters, App, Part)
    components = v1._load_shell_components(parameters, App, Part)
    owners = {str(item.key): item for item in components}
    clearance = float(contract["relief"]["motion_clearance_mm"])
    path = contract["motion_path"]
    pivot = App.Vector(*map(float, path["pivot_mm"]))
    rotation_axis = App.Vector(*map(float, path["rotation_axis"]))
    translation_axis = App.Vector(*map(float, path["translation_axis_inward_n"]))
    rotation_axis.normalize()
    translation_axis.normalize()
    datum_guard_parts = _datum_guard_parts(parameters, construction, App, Part)
    datum_guards = v1.toolkit.fuse_shapes(
        list(datum_guard_parts.values()),
        "E1 fused bore-core and mating-seat guards", require_one=False,
    )
    ligament_guards = _ligament_guards(parameters, construction, App, Part)
    optical_guards = _optical_guards(construction, App, Part)
    attribution_features = {
        "bezel": construction["bezel"],
        "cassette": construction["cassette"],
        "cover_lip": construction["cover_lip"],
        "upper_mount": construction["mounts"]["upper"]["drilled"],
        "lower_mount": construction["mounts"]["lower"]["drilled"],
        "upper_ligament": ligament_guards["upper"],
        "lower_ligament": ligament_guards["lower"],
        "datum_guards": datum_guards,
        **{f"datum_{name}": shape for name, shape in datum_guard_parts.items()},
        **{f"optical_{name}": shape for name, shape in optical_guards.items()},
    }
    cutters = []
    records = []
    for owner_key, pose_indices in COLLISION_POSES.items():
        owner = owners.get(owner_key)
        if owner is None or owner.shape is None or owner.shape.isNull():
            raise RuntimeError(f"required exact collision owner unavailable: {owner_key}")
        for index in pose_indices:
            moved = _posed(nominal, index, pivot, rotation_axis, translation_axis)
            common = moved.common(owner.shape)
            if common.isNull() or float(common.Volume) <= 1.0e-6:
                raise RuntimeError(f"declared collision disappeared: {owner_key} pose {index}")
            cutter, record = _inverse_mapped_expanded_box(
                common, clearance, index, pivot, rotation_axis,
                translation_axis, App, Part,
            )
            record["owner"] = owner_key
            seated_common = common.copy()
            tilt, translation = _pose_record(index)
            seated_common.translate(translation_axis * (-translation))
            seated_common.rotate(pivot, rotation_axis, -tilt)
            record["seated_exact_common_feature_mm3"] = {
                name: float(seated_common.common(feature).Volume)
                for name, feature in attribution_features.items()
            }
            cutters.append(cutter)
            records.append(record)
    relief_envelope = v1.toolkit.fuse_shapes(
        cutters, "E1 fused inverse-mapped clearance boxes", require_one=False
    )
    raw_target_cutter = relief_envelope.common(nominal).removeSplitter()
    applied_cutter = raw_target_cutter.cut(datum_guards).removeSplitter()
    cut_stage_volumes = {"raw_target_cutter_mm3": float(raw_target_cutter.Volume),
                         "after_datum_guards_mm3": float(applied_cutter.Volume)}
    for name, guard in ligament_guards.items():
        applied_cutter = applied_cutter.cut(guard).removeSplitter()
        cut_stage_volumes[f"after_{name}_ligament_guard_mm3"] = float(applied_cutter.Volume)
    for name, guard in optical_guards.items():
        applied_cutter = applied_cutter.cut(guard).removeSplitter()
        cut_stage_volumes[f"after_{name}_guard_mm3"] = float(applied_cutter.Volume)
    relieved = nominal.cut(applied_cutter).removeSplitter()

    refs = validator_v1._reference_geometry(parameters, App, Part)
    before_sliver = relieved.cut(refs["bezel"]).removeSplitter().common(refs["exterior"])
    sliver_before_mm3 = float(before_sliver.Volume) if not before_sliver.isNull() else 0.0
    if sliver_before_mm3 > 1.0e-6:
        relieved = relieved.cut(before_sliver).removeSplitter()
    v1.toolkit.require_single_solid(relieved, "E1 relieved split cassette")
    sliver_after = relieved.cut(refs["bezel"]).removeSplitter().common(refs["exterior"])
    sliver_after_mm3 = float(sliver_after.Volume) if not sliver_after.isNull() else 0.0
    return relieved, {
        "nominal": nominal,
        "construction": construction,
        "components": components,
        "owners": owners,
        "pivot": pivot,
        "rotation_axis": rotation_axis,
        "translation_axis": translation_axis,
        "relief_envelope": relief_envelope,
        "cut_stage_volumes": cut_stage_volumes,
        "applied_cutter": applied_cutter,
        "datum_guards": datum_guards,
        "datum_guard_parts": datum_guard_parts,
        "ligament_guards": ligament_guards,
        "optical_guards": optical_guards,
        "collision_box_records": records,
        "g05_sliver_before_trim_mm3": sliver_before_mm3,
        "g05_sliver_after_trim_mm3": sliver_after_mm3,
    }


def preflight() -> dict[str, Any]:
    started = time.monotonic()
    root, parameters, contract = _load_inputs()
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore
    relieved, evidence = construct_e1(parameters, contract, App, Part)
    maximum_collision = 0.0
    minimum_distance = math.inf
    post = []
    for owner_key, pose_indices in COLLISION_POSES.items():
        owner = evidence["owners"][owner_key].shape
        for index in pose_indices:
            moved = _posed(relieved, index, evidence["pivot"],
                           evidence["rotation_axis"], evidence["translation_axis"])
            common = moved.common(owner)
            volume = float(common.Volume) if not common.isNull() else 0.0
            distance = float(moved.distToShape(owner)[0])
            maximum_collision = max(maximum_collision, volume)
            minimum_distance = min(minimum_distance, distance)
            post.append({"owner": owner_key, "source_sample_index": index,
                         "collision_mm3": volume, "distance_mm": distance})
    nominal = evidence["nominal"]
    removed = float(nominal.cut(relieved).Volume)
    added = float(relieved.cut(nominal).Volume)
    epsilon = 1.0e-6
    clearance = float(contract["relief"]["motion_clearance_mm"])
    dimensional_tolerance = float(
        parameters["validation_contract"]["limits"]["maximum_dimensional_deviation_mm"]
    )
    protected_core_missing = float(evidence["datum_guards"].cut(relieved).Volume)
    applied_ligament_intersection = max(
        float(evidence["applied_cutter"].common(shape).Volume)
        for shape in evidence["ligament_guards"].values()
    )
    applied_optical_intersection = max(
        float(evidence["applied_cutter"].common(shape).Volume)
        for shape in evidence["optical_guards"].values()
    )
    source_minimum_wall = min(
        float(parameters["geometry"]["front_optical_cassette"]["minimum_printed_wall_mm"]),
        float(parameters["geometry"]["lower_c001_cover_lip"]["minimum_printed_wall_mm"]),
        float(parameters["geometry"]["head_mount"]["ligament_thickness_mm"]),
    )
    wall_gate = bool(
        source_minimum_wall >= 0.7
        and protected_core_missing <= epsilon
        and applied_ligament_intersection <= epsilon
        and applied_optical_intersection <= epsilon
    )
    clearance_gate = bool(
        minimum_distance >= clearance - dimensional_tolerance
    )
    passes = (
        relieved.isValid() and len(relieved.Solids) == 1
        and maximum_collision <= epsilon
        and clearance_gate
        and wall_gate
        and evidence["g05_sliver_after_trim_mm3"] <= epsilon
        and added <= epsilon
    )
    return {
        "schema_version": "cat-head-e1-leadin-relief-preflight-v1",
        "status": "PASS__E1_IN_MEMORY_NO_SAVE_PREFLIGHT" if passes else "FAIL__E1_IN_MEMORY_PREFLIGHT",
        "generator_id": GENERATOR_ID,
        "pins": {
            "generator_e1": sha256_file(Path(__file__)),
            "generator_v1": V1_GENERATOR_SHA256,
            "validator_v1": V1_VALIDATOR_SHA256,
            "contract_v1": V1_CONTRACT_SHA256,
            "contract_e1": sha256_file(root / E1_CONTRACT_RELATIVE),
        },
        "relief": {
            "clearance_mm": float(contract["relief"]["motion_clearance_mm"]),
            "box_count": len(evidence["collision_box_records"]),
            "box_records": evidence["collision_box_records"],
            "cut_stage_volumes_mm3": evidence["cut_stage_volumes"],
            "removed_volume_mm3": removed,
            "added_volume_mm3": added,
        },
        "post_relief_motion": {
            "maximum_collision_mm3": maximum_collision,
            "minimum_distance_mm": minimum_distance,
            "required_minimum_distance_mm": clearance - dimensional_tolerance,
            "clearance_gate": clearance_gate,
            "poses": post,
        },
        "preservation": {
            "valid": bool(relieved.isValid()),
            "solid_count": len(relieved.Solids),
            "aperture_and_lip_clipped_from_cutter": True,
            "bore_centers_axes_and_mating_seats_guarded": True,
            "minimum_guarded_bore_wall_mm": 0.7,
            "minimum_declared_wall_mm": source_minimum_wall,
            "protected_mount_core_missing_mm3": protected_core_missing,
            "applied_cutter_ligament_intersection_mm3": applied_ligament_intersection,
            "applied_cutter_protected_optical_intersection_mm3": applied_optical_intersection,
            "post_cut_minimum_wall_gate": wall_gate,
            "g05_lower_ligament_exterior_sliver_before_trim_mm3": evidence["g05_sliver_before_trim_mm3"],
            "g05_lower_ligament_exterior_sliver_after_trim_mm3": evidence["g05_sliver_after_trim_mm3"],
            "shell_mutated": False,
        },
        "integration_holds": contract["integration_holds"],
        "constraint_conflict": None if clearance_gate else {
            "status": "BLOCKED__RELIEF_REQUIRES_PROTECTED_GEOMETRY_REMOVAL",
            "blocking_features": [
                "lower_bore_wall_core_at_0.70_mm",
                "lower_shell_mating_seat",
                "visible_front_cassette_skin_at_0.70_mm",
                "visible_aperture_band_at_0.70_mm",
            ],
            "required_resolution": (
                "Change the fixed motion path or authorize a redesign of a "
                "protected feature; target-only E1 subtraction cannot pass."
            ),
        },
        "io_trace": {
            "candidate_opened": False, "candidate_saved": False,
            "document_save_called": False, "geometry_export_created": False,
            "render_created": False, "promotion_performed": False,
        },
        "finalization_trace": {
            "in_memory_shape_constructed": True,
            "final_assertions_performed": True,
            "save_capability_present": False,
            "candidate_assignment_performed": False,
        },
        "elapsed_seconds": time.monotonic() - started,
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in-memory-preflight", action="store_true")
    parser.add_argument("--report", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if not args.in_memory_preflight:
        raise RuntimeError("E1 authorizes only --in-memory-preflight")
    report = preflight()
    if args.report is not None:
        root = v1.repo_root()
        path = args.report if args.report.is_absolute() else root / args.report
        tooling = root / "reports/generated/cat-head-cad-tooling"
        path.resolve().relative_to(tooling.resolve())
        if path.exists():
            raise FileExistsError(f"refusing to overwrite tooling evidence: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
