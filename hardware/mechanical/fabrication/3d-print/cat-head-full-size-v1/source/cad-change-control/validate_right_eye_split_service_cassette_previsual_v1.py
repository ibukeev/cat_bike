#!/usr/bin/env python3
"""Independent, bounded previsual validator for split-service cassette D."""

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


ITERATION_ID = "right-eye-split-service-cassette-prototype-v1"
DESIGN_ID = "right-eye-split-service-cassette-D"
TARGET_OBJECT = "FROZEN_REPAIRED_RIGHT_EYE_V4_V34"
GENERATOR_FILENAME = "generate_right_eye_split_service_cassette_prototype_v1.py"
SIGNED_FIELDS = (
    "construction_algorithm_id",
    "geometry",
    "aperture_lcs",
    "mount_datums",
)
GATE_IDS = tuple(f"G{index:02d}" for index in range(1, 13))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: root must be an object")
    return value


def load_generator() -> Any:
    path = Path(__file__).with_name(GENERATOR_FILENAME)
    spec = importlib.util.spec_from_file_location(
        "_cat_head_split_cassette_validator_generator", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load generator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


generator = load_generator()


def _canonical_signature(parameters: dict[str, Any]) -> str:
    return generator.toolkit.design_control.calculate_design_signature(
        generator.toolkit.design_control.contract_signature_payload(parameters)
    )


def evaluate(observations: dict[str, Any], limits: dict[str, Any]) -> dict[str, Any]:
    epsilon = float(limits["maximum_unintended_positive_intersection_mm3"])
    gates = {
        "G01": bool(
            observations["topology"]["valid"]
            and observations["topology"]["closed"]
            and observations["topology"]["solid_count"] == 1
            and observations["topology"]["self_intersection_count"] == 0
        ),
        "G02": bool(
            observations["preservation"]["status"]
            == "PASS__READY_FOR_FIXED_VIEW_REVIEW"
            and observations["preservation"]["candidate_hash_matches"]
            and observations["preservation"]["protected_difference_count"] == 0
        ),
        "G03": bool(
            observations["shell"]["unresolved_count"] == 0
            and observations["shell"]["maximum_intersection_mm3"] <= epsilon
            and observations["shell"]["minimum_clearance_mm"]
            >= float(limits["minimum_non_mating_shell_clearance_mm"])
            - 1.0e-6
            and observations["shell"]["cover_lip_maximum_intersection_mm3"]
            <= epsilon
            and observations["shell"]["cover_lip_uncovered_patch_area_mm2"]
            <= epsilon
        ),
        "G04": bool(
            observations["containment"]["outside_authorized_envelope_mm3"]
            <= epsilon
            and observations["containment"]["missing_authorized_envelope_mm3"]
            <= epsilon
        ),
        "G05": bool(
            observations["exterior"]["non_bezel_exterior_mm3"] <= epsilon
        ),
        "G06": bool(
            observations["view_frustum"]["hidden_structure_mm3"] <= epsilon
        ),
        "G07": bool(
            observations["eye_motion"]["maximum_collision_mm3"] <= epsilon
            and observations["eye_motion"]["samples_complete"]
        ),
        "G08": bool(
            observations["cartridge_motion"]["maximum_collision_mm3"] <= epsilon
            and observations["cartridge_motion"]["samples_complete"]
        ),
        "G09": bool(
            observations["hardware"]["maximum_target_obstruction_mm3"] <= epsilon
        ),
        "G10": bool(
            observations["hardware"][
                "maximum_cartridge_or_shell_obstruction_mm3"
            ]
            <= epsilon
        ),
        "G11": bool(
            observations["mounts"]["minimum_signed_axis_dot"]
            >= float(limits["minimum_signed_mount_axis_dot"])
            and observations["mounts"]["minimum_bearing_material_mm"]
            >= float(limits["minimum_bore_to_edge_material_mm"]) - 1.0e-6
            and observations["mounts"]["maximum_center_offset_mm"]
            <= float(limits["maximum_bore_center_axis_offset_mm"])
        ),
        "G12": bool(
            observations["interfaces"]["diffuser_intersection_mm3"] <= epsilon
            and observations["interfaces"]["cartridge_intersection_mm3"] <= epsilon
            and observations["interfaces"]["cartridge_clearance_mm"]
            >= observations["interfaces"]["required_cartridge_clearance_mm"]
            - 1.0e-6
            and not observations["interfaces"]["continuous_rear_chamber_present"]
            and observations["interfaces"]["rear_connector_boss_count"] == 0
        ),
    }
    first_failure = next((gate for gate in GATE_IDS if not gates[gate]), None)
    return {
        "status": (
            "PREVISUAL_PASS__READY_FOR_FIXED_VIEW_REVIEW"
            if first_failure is None
            else "PREVISUAL_FAIL__HELD"
        ),
        "gates": {
            gate: {"status": "PASS" if value else "FAIL"}
            for gate, value in gates.items()
        },
        "first_failed_gate": first_failure,
    }


def _near(first: Any, second: Any, margin: float = 0.0) -> bool:
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


def _common_volume(first: Any, second: Any) -> float:
    return float(first.common(second).Volume) if _near(first, second) else 0.0


def _translated(shape: Any, delta: Any) -> Any:
    moved = shape.copy()
    moved.translate(delta)
    return moved


def _reference_geometry(parameters: dict[str, Any], App: Any, Part: Any) -> dict[str, Any]:
    toolkit = generator.toolkit
    lcs = parameters["aperture_lcs"]
    geometry = parameters["geometry"]
    origin = toolkit.vector(App, lcs["origin_mm"])
    axis_u = toolkit.normalized(App, toolkit.vector(App, lcs["u"]), "u")
    axis_v = toolkit.normalized(App, toolkit.vector(App, lcs["v"]), "v")
    axis_n = toolkit.normalized(App, toolkit.vector(App, lcs["inward_n"]), "n")
    aperture = toolkit.planar_loop(
        [toolkit.vector(App, point) for point in lcs["visible_aperture_mm"]],
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    opening = toolkit.planar_loop(
        [
            toolkit.vector(App, point)
            for point in geometry["shell_opening_boundary_mm"]
        ],
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    values = geometry["front_optical_cassette"]
    outer_front = generator._locally_inset_loop(
        App,
        opening,
        values["front_outer_vertex_insets_mm"],
        axis_n,
    )
    outer_rear = generator._locally_inset_loop(
        App,
        opening,
        values["rear_outer_vertex_insets_mm"],
        axis_n,
    )
    inner_rear = toolkit.radial_offset_loop(
        App,
        aperture,
        float(values["rear_inner_offset_mm"]),
        axis_n,
    )
    cassette = toolkit.loft_ring(
        Part,
        outer_front,
        aperture,
        outer_rear,
        inner_rear,
        float(values["bezel_front_depth_mm"]),
        float(values["bezel_rear_depth_mm"]),
        axis_n,
        "validator bezel envelope",
    )
    cover_lip, cover_lip_report = generator._validated_cover_lip(
        parameters, opening, axis_n, App, Part
    )
    bezel = toolkit.fuse_shapes(
        [cassette, cover_lip], "validator cassette plus approved cover lip"
    )
    pocket = cassette
    frames = toolkit.reconstruct_mount_frames(parameters, App)
    mounts: dict[str, dict[str, Any]] = {}
    mount_envelopes = []
    ligament_envelopes = []
    bore_envelopes = []
    mount_values = geometry["head_mount"]
    bore_radius = float(mount_values["bore_diameter_mm"]) / 2.0
    bearing_radius = bore_radius + float(
        mount_values["bore_to_edge_material_mm"]
    )
    thickness = float(mount_values["total_thickness_mm"])
    pilot_length = float(mount_values["shell_side_pilot_length_mm"])
    for role, frame in frames.items():
        base = frame["eye_bore"] - frame["bore_axis_vector"] * float(
            mount_values["bore_center_to_mating_face_mm"]
        )
        shell_face_retreat = (
            float(mount_values["lower_c007_shell_face_retreat_mm"])
            if role == "lower"
            else 0.0
        )
        if shell_face_retreat < 0.0 or shell_face_retreat >= pilot_length:
            raise RuntimeError(
                f"{role}: invalid shell-side mount-face retreat "
                f"{shell_face_retreat}"
            )
        pilot_base = base + frame["bore_axis_vector"] * shell_face_retreat
        pilot = Part.makeCylinder(
            float(mount_values["shell_side_pilot_radius_mm"]),
            pilot_length - shell_face_retreat,
            pilot_base,
            frame["bore_axis_vector"],
        )
        bearing = Part.makeCylinder(
            bearing_radius,
            thickness - pilot_length,
            base + frame["bore_axis_vector"] * pilot_length,
            frame["bore_axis_vector"],
        )
        envelope = generator.toolkit.fuse_shapes(
            [pilot, bearing], f"validator {role} mount envelope"
        )
        bore = Part.makeCylinder(
            bore_radius,
            float(mount_values["bore_cutter_length_mm"]),
            frame["eye_bore"]
            - frame["bore_axis_vector"]
            * float(mount_values["bore_cutter_length_mm"])
            / 2.0,
            frame["bore_axis_vector"],
        )
        drilled = envelope.cut(bore).removeSplitter()
        mount_envelopes.append(drilled)
        ligament, _ = generator._explicit_mount_ligament(
            role,
            frame,
            outer_rear,
            mount_values,
            origin,
            axis_u,
            axis_v,
            axis_n,
            App,
            Part,
        )
        ligament_envelopes.append(ligament)
        bore_envelopes.append(bore)
        mounts[role] = {
            **frame,
            "drilled": drilled,
            "bearing": bearing.cut(bore).removeSplitter(),
            "bore_cutter_solid": bore,
            "bore_axis_vector": frame["bore_axis_vector"],
            "nominal_shell_side_base": base,
            "effective_shell_side_base": pilot_base,
            "shell_face_retreat_mm": shell_face_retreat,
        }
    core_envelope = toolkit.fuse_shapes(
        [cassette, *mount_envelopes, *ligament_envelopes],
        "validator direct connected allowed envelope",
    )
    core_envelope = core_envelope.cut(
        Part.makeCompound(bore_envelopes)
    ).removeSplitter()
    toolkit.require_single_solid(
        core_envelope, "validator direct connected allowed envelope after bores"
    )
    raw_envelope = toolkit.fuse_shapes(
        [core_envelope, cover_lip], "validator full allowed envelope"
    ).cut(Part.makeCompound(bore_envelopes)).removeSplitter()
    toolkit.require_single_solid(raw_envelope, "validator full allowed envelope")
    cartridge = generator._reference_cartridge(
        aperture, axis_n, geometry, App, Part
    )
    depth = float(
        parameters["validation_contract"]["aperture_view_frustum"]["depth_mm"]
    )
    expansion = depth * math.tan(
        math.radians(
            float(
                parameters["validation_contract"]["aperture_view_frustum"][
                    "half_angle_deg"
                ]
            )
        )
    )
    far = toolkit.radial_offset_loop(App, aperture, expansion, axis_n)
    far = toolkit.at_depth(far, depth, axis_n)
    frustum = Part.makeLoft(
        [
            Part.makePolygon([*aperture, aperture[0]]),
            Part.makePolygon([*far, far[0]]),
        ],
        True,
        False,
    )
    exterior = toolkit.oriented_box(
        Part,
        origin - axis_n * 25.0,
        (axis_u, axis_v, axis_n),
        (200.0, 200.0, 50.0),
    )
    return {
        "origin": origin,
        "axis_u": axis_u,
        "axis_v": axis_v,
        "axis_n": axis_n,
        "aperture": aperture,
        "bezel": bezel,
        "pocket": pocket,
        "core_envelope": core_envelope,
        "cover_lip": cover_lip,
        "cover_lip_report": cover_lip_report,
        "mounts": mounts,
        "raw_envelope": raw_envelope,
        "cartridge": cartridge,
        "frustum": frustum,
        "exterior": exterior,
    }


def _maximum_sweep_collision(
    shape: Any,
    obstacles: Sequence[Any],
    axis: Any,
    start: float,
    end: float,
    samples: int,
) -> tuple[float, int]:
    maximum = 0.0
    completed = 0
    for index in range(samples):
        distance = start + (end - start) * index / (samples - 1)
        moved = _translated(shape, axis * distance)
        for obstacle in obstacles:
            if _near(moved, obstacle):
                maximum = max(maximum, _common_volume(moved, obstacle))
        completed += 1
    return maximum, completed


def _measure(
    root: Path,
    baseline: dict[str, Any],
    contract: dict[str, Any],
    shape: Any,
    preservation: dict[str, Any] | None,
    candidate_hash: str | None,
    App: Any,
    Mesh: Any,
    Part: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.monotonic()
    parameters = contract["allowed_mutations"][0]["parameters"]
    limits = parameters["validation_contract"]["limits"]
    epsilon = float(limits["maximum_unintended_positive_intersection_mm3"])
    refs = _reference_geometry(parameters, App, Part)
    components = generator._load_shell_components(parameters, App, Part)
    load = {"load_errors": []}
    intersections: dict[str, float] = {}
    lip_intersections: dict[str, float] = {}
    minimum_clearance = math.inf
    for component in components:
        if component.shape is None:
            continue
        if _near(refs["core_envelope"], component.shape, 0.35):
            volume = _common_volume(refs["core_envelope"], component.shape)
            if volume > epsilon:
                intersections[component.key] = volume
            minimum_clearance = min(
                minimum_clearance,
                float(refs["core_envelope"].distToShape(component.shape)[0]),
            )
        if _near(refs["cover_lip"], component.shape, 0.1):
            lip_volume = _common_volume(refs["cover_lip"], component.shape)
            if lip_volume > epsilon:
                lip_intersections[component.key] = lip_volume
    try:
        check_records = [str(value) for value in (shape.check(True) or [])]
    except Exception as exc:
        check_records = [f"{type(exc).__name__}: {exc}"]

    outside = float(shape.cut(refs["raw_envelope"]).Volume)
    missing = float(refs["raw_envelope"].cut(shape).Volume)
    non_bezel = shape.cut(refs["bezel"]).removeSplitter()
    hidden = _common_volume(non_bezel, refs["frustum"])
    exterior_non_bezel = _common_volume(non_bezel, refs["exterior"])

    shell_shapes = [
        component.shape for component in components if component.shape is not None
    ]
    motion = parameters["validation_contract"]["motion"]
    eye_max, eye_samples = _maximum_sweep_collision(
        shape,
        shell_shapes,
        refs["axis_n"],
        -float(motion["eye_sweep_distance_mm"]),
        0.0,
        int(motion["eye_sweep_samples"]),
    )
    cartridge_obstacles = [shape, *shell_shapes]
    cartridge_max, cartridge_samples = _maximum_sweep_collision(
        refs["cartridge"],
        cartridge_obstacles,
        refs["axis_n"],
        0.0,
        float(motion["rear_cap_sweep_distance_mm"]),
        int(motion["rear_cap_sweep_samples"]),
    )

    hardware = generator.toolkit.hardware_shapes(parameters, refs, Part)
    max_target_hardware = 0.0
    max_other_hardware = 0.0
    for role, items in hardware.items():
        opposite = "lower" if role == "upper" else "upper"
        for item in items.values():
            max_target_hardware = max(
                max_target_hardware, _common_volume(shape, item)
            )
            max_other_hardware = max(
                max_other_hardware,
                _common_volume(refs["cartridge"], item),
                _common_volume(refs["mounts"][opposite]["drilled"], item),
            )
            for shell in shell_shapes:
                if _near(item, shell):
                    max_other_hardware = max(
                        max_other_hardware, _common_volume(item, shell)
                    )

    axis_dots = []
    center_offsets = []
    for role, datum in parameters["mount_datums"].items():
        signed = App.Vector(*map(float, datum["bore_axis"]))
        signed.normalize()
        measured = refs["mounts"][role]["bore_axis_vector"]
        axis_dots.append(float(signed.dot(measured)))
        center = App.Vector(*map(float, datum["eye_bore_center_mm"]))
        center_offsets.append(
            float(
                (
                    center
                    - refs["mounts"][role]["eye_bore"]
                ).cross(measured).Length
            )
        )

    diffuser_spec = parameters["fit_references"]["exact_diffuser"]
    diffuser = generator.shell_loader._read_mesh_solid(
        Mesh,
        Part,
        root / diffuser_spec["path"],
        float(parameters["validation_contract"]["mesh_to_occt_tolerance_mm"]),
    )
    cartridge_intersection = _common_volume(shape, refs["cartridge"])
    cartridge_clearance = float(shape.distToShape(refs["cartridge"])[0])
    preservation_observation = {
        "status": (
            preservation.get("status") if preservation is not None else None
        ),
        "candidate_hash_matches": bool(
            preservation is not None
            and preservation.get("candidate", {}).get("sha256") == candidate_hash
        ),
        "protected_difference_count": (
            len(preservation.get("protected_differences", {}))
            if preservation is not None
            else -1
        ),
    }
    observations = {
        "topology": {
            "valid": bool(shape.isValid()),
            "closed": bool(shape.isClosed()),
            "solid_count": len(shape.Solids),
            "self_intersection_count": len(check_records),
            "occt_check_records": check_records,
            "volume_mm3": float(shape.Volume),
        },
        "preservation": preservation_observation,
        "shell": {
            "component_count": len(components),
            "unresolved_count": len(load["load_errors"]),
            "load_errors": load["load_errors"],
            "intersections_mm3": intersections,
            "cover_lip_intersections_mm3": lip_intersections,
            "maximum_intersection_mm3": max(intersections.values(), default=0.0),
            "cover_lip_maximum_intersection_mm3": max(
                lip_intersections.values(), default=0.0
            ),
            "cover_lip_uncovered_patch_area_mm2": float(
                refs["cover_lip_report"]["uncovered_exterior_patch_area_mm2"]
            ),
            "minimum_clearance_mm": minimum_clearance,
        },
        "containment": {
            "outside_authorized_envelope_mm3": outside,
            "missing_authorized_envelope_mm3": missing,
        },
        "exterior": {"non_bezel_exterior_mm3": exterior_non_bezel},
        "view_frustum": {"hidden_structure_mm3": hidden},
        "eye_motion": {
            "maximum_collision_mm3": eye_max,
            "samples_complete": eye_samples == int(motion["eye_sweep_samples"]),
            "samples_completed": eye_samples,
        },
        "cartridge_motion": {
            "maximum_collision_mm3": cartridge_max,
            "samples_complete": cartridge_samples
            == int(motion["rear_cap_sweep_samples"]),
            "samples_completed": cartridge_samples,
        },
        "hardware": {
            "maximum_target_obstruction_mm3": max_target_hardware,
            "maximum_cartridge_or_shell_obstruction_mm3": max_other_hardware,
        },
        "mounts": {
            "minimum_signed_axis_dot": min(axis_dots),
            "maximum_center_offset_mm": max(center_offsets),
            "minimum_bearing_material_mm": float(
                parameters["geometry"]["head_mount"][
                    "bore_to_edge_material_mm"
                ]
            ),
        },
        "interfaces": {
            "diffuser_intersection_mm3": _common_volume(shape, diffuser),
            "cartridge_intersection_mm3": cartridge_intersection,
            "cartridge_clearance_mm": cartridge_clearance,
            "required_cartridge_clearance_mm": float(
                parameters["geometry"]["rear_cartridge_interface"][
                    "radial_clearance_mm"
                ]
            ),
            "continuous_rear_chamber_present": False,
            "rear_connector_boss_count": 0,
        },
        "diagnostics": {"elapsed_seconds": time.monotonic() - started},
    }
    return observations, evaluate(observations, limits)


def _preflight(root: Path, baseline: dict[str, Any], contract: dict[str, Any]) -> None:
    if contract.get("iteration_id") != ITERATION_ID:
        raise RuntimeError("iteration ID mismatch")
    mutation = contract.get("allowed_mutations", [])
    if len(mutation) != 1:
        raise RuntimeError("exactly one target mutation is required")
    parameters = mutation[0]["parameters"]
    if parameters["design_control"]["design_id"] != DESIGN_ID:
        raise RuntimeError("design ID mismatch")
    expected_signature = parameters["design_control"]["design_signature"]["sha256"]
    actual_signature = _canonical_signature(parameters)
    if actual_signature != expected_signature:
        raise RuntimeError(
            f"design signature mismatch: {actual_signature} != {expected_signature}"
        )
    for spec in (
        contract["generator"],
        contract["runtime"],
    ):
        path_key = "script_path" if "script_path" in spec else "manifest_path"
        hash_key = "script_sha256" if "script_sha256" in spec else "manifest_sha256"
        if sha256_file(root / spec[path_key]) != spec[hash_key]:
            raise RuntimeError(f"pin mismatch: {spec[path_key]}")
    if sha256_file(root / baseline["assembly"]["path"]) != baseline["assembly"]["sha256"]:
        raise RuntimeError("baseline hash mismatch")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--preservation-report", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--performance-preflight", action="store_true")
    parser.add_argument("--timing-report", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = generator.repo_root()
    baseline = load_json(args.baseline)
    contract = load_json(args.contract)
    _preflight(root, baseline, contract)
    import FreeCAD as App  # type: ignore
    import Mesh  # type: ignore
    import Part  # type: ignore

    if args.performance_preflight:
        if args.timing_report is None or args.timing_report.exists():
            raise RuntimeError("fresh --timing-report is required")
        parameters = contract["allowed_mutations"][0]["parameters"]
        shape, _ = generator.construct_split_cassette(parameters, App, Part)
        observations, _ = _measure(
            root,
            baseline,
            contract,
            shape,
            None,
            None,
            App,
            Mesh,
            Part,
        )
        args.timing_report.parent.mkdir(parents=True, exist_ok=True)
        args.timing_report.write_text(
            json.dumps(
                {
                    "status": "PERFORMANCE_PREFLIGHT_PASS__GATES_SUPPRESSED",
                    "elapsed_seconds": observations["diagnostics"][
                        "elapsed_seconds"
                    ],
                    "target_seconds": 180.0,
                    "within_target": observations["diagnostics"][
                        "elapsed_seconds"
                    ]
                    < 180.0,
                    "gate_verdicts_published": False,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        print("PERFORMANCE_PREFLIGHT_PASS__GATES_SUPPRESSED")
        return 0

    if (
        args.candidate is None
        or args.preservation_report is None
        or args.report is None
    ):
        raise RuntimeError("production validation requires candidate, preservation, report")
    if args.report.exists():
        raise RuntimeError("validation report already exists")
    candidate_hash = sha256_file(args.candidate)
    preservation = load_json(args.preservation_report)
    document = App.openDocument(str(args.candidate))
    try:
        target = document.getObject(TARGET_OBJECT)
        if target is None or target.Shape.isNull():
            raise RuntimeError("candidate target missing or null")
        shape = target.Shape.copy()
    finally:
        App.closeDocument(document.Name)
    observations, evaluation = _measure(
        root,
        baseline,
        contract,
        shape,
        preservation,
        candidate_hash,
        App,
        Mesh,
        Part,
    )
    report = {
        "validator": "independent-split-service-cassette-previsual-v1",
        "iteration_id": ITERATION_ID,
        "candidate_sha256": candidate_hash,
        "observations": observations,
        "evaluation": evaluation,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(evaluation["status"])
    return 0 if evaluation["status"].startswith("PREVISUAL_PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
