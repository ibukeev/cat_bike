#!/usr/bin/env python3
"""Bounded feasibility and REVIEW_ONLY lower-eye interior backer clamp.

The pinned relieved shell and held split-eye candidate are opened read-only.
Feasibility constructs one additive backer in memory.  Review mode may then
copy reference shapes and the proposal into one new NONAUTHORITATIVE FCStd;
it never saves either input document and never exports manufacturing geometry.
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


REVIEW_ID = "right-eye-lower-interior-backer-clamp-r1"
TARGET_OBJECT = "FROZEN_REPAIRED_RIGHT_EYE_V4_V34"
VALIDATOR_FILENAME = "validate_right_eye_split_service_cassette_previsual_v1.py"
VALIDATOR_SHA256 = "d7ad39bea689e8df54484eaf97c9077df73d3c8c8eb03c18696859ea15133ccf"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_shape(shape: Any) -> str:
    payload = shape.exportBrepToString()
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"JSON root is not an object: {path}")
    return value


def load_pinned_validator() -> Any:
    cad_dir = Path(__file__).resolve().parents[2]
    path = cad_dir / VALIDATOR_FILENAME
    actual = sha256_file(path)
    if actual != VALIDATOR_SHA256:
        raise RuntimeError(f"split-eye validator hash mismatch: {actual}")
    name = "_cat_head_backer_clamp_pinned_validator"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load pinned validator: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validator = load_pinned_validator()
generator = validator.generator
toolkit = generator.toolkit


def repository_root() -> Path:
    return generator.repo_root()


def verify_spec(root: Path, spec: dict[str, Any], label: str) -> Path:
    path = Path(str(spec["path"]))
    if not path.is_absolute():
        path = root / path
    actual = sha256_file(path)
    if actual != spec["sha256"]:
        raise RuntimeError(f"{label} hash mismatch: {actual} != {spec['sha256']}")
    return path


def aabb_near(first: Any, second: Any, margin: float = 0.0) -> bool:
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


def vector_values(vector: Any) -> list[float]:
    return [float(vector.x), float(vector.y), float(vector.z)]


def axis_intervals(
    owner_shape: Any,
    anchor: Any,
    axis: Any,
    half_length: float,
    Part: Any,
) -> list[tuple[float, float]]:
    probe = Part.makeLine(anchor - axis * half_length, anchor + axis * half_length)
    section = owner_shape.common(probe)
    intervals: list[tuple[float, float]] = []
    for edge in section.Edges:
        offsets = sorted(float((vertex.Point - anchor).dot(axis)) for vertex in edge.Vertexes)
        if len(offsets) >= 2 and offsets[-1] - offsets[0] > 1.0e-8:
            intervals.append((offsets[0], offsets[-1]))
    return sorted(intervals)


def select_edge_anchors(
    owner_shape: Any,
    head_bore: Any,
    tangent: Any,
    depth: Any,
    axis: Any,
    scan: dict[str, Any],
    Part: Any,
) -> list[dict[str, Any]]:
    """Resolve exactly one negative and one positive local edge support."""
    step = float(scan["tangent_step_mm"])
    low = float(scan["tangent_min_mm"])
    high = float(scan["tangent_max_mm"])
    minimum_abs = float(scan["minimum_opposite_tangent_magnitude_mm"])
    tolerance = float(scan["axis_interval_tolerance_mm"])
    count = int(round((high - low) / step)) + 1
    records: list[dict[str, Any]] = []
    for index in range(count):
        tangent_offset = low + index * step
        if abs(tangent_offset) < minimum_abs:
            continue
        for depth_offset_raw in scan["depth_offsets_mm"]:
            depth_offset = float(depth_offset_raw)
            anchor = head_bore + tangent * tangent_offset + depth * depth_offset
            negative = [
                item
                for item in axis_intervals(
                    owner_shape,
                    anchor,
                    axis,
                    float(scan["ray_half_length_mm"]),
                    Part,
                )
                if item[0] < -tolerance and item[1] <= tolerance
            ]
            if not negative:
                continue
            interval = min(negative, key=lambda item: item[0])
            records.append(
                {
                    "side": "negative_tangent" if tangent_offset < 0.0 else "positive_tangent",
                    "tangent_offset_mm": tangent_offset,
                    "depth_offset_mm": depth_offset,
                    "interval_mm": [float(interval[0]), float(interval[1])],
                    "anchor": anchor,
                }
            )
    selected: list[dict[str, Any]] = []
    for side in ("negative_tangent", "positive_tangent"):
        candidates = [record for record in records if record["side"] == side]
        if not candidates:
            raise RuntimeError(f"no exact lower_C001 rear-edge support on {side}")
        selected.append(
            min(
                candidates,
                key=lambda item: (
                    abs(float(item["tangent_offset_mm"])),
                    abs(float(item["depth_offset_mm"])),
                    float(item["interval_mm"][0]),
                ),
            )
        )
    return selected


def build_backer(
    parameters: dict[str, Any],
    refs: dict[str, Any],
    components: Sequence[Any],
    App: Any,
    Part: Any,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    geometry = parameters["geometry"]
    target = parameters["target"]
    frame = refs["mounts"]["lower"]
    eye_bore = frame["eye_bore"]
    head_bore = frame["head_bore"]
    axis = frame["bore_axis_vector"]
    tangent = frame["tangent"]
    depth = frame["depth"]

    expected_eye = App.Vector(*map(float, target["eye_bore_center_mm"]))
    expected_head = App.Vector(*map(float, target["head_bore_center_mm"]))
    expected_axis = App.Vector(*map(float, target["signed_bore_axis"]))
    expected_axis.normalize()
    datum_residuals = {
        "eye_center_mm": float((eye_bore - expected_eye).Length),
        "head_center_mm": float((head_bore - expected_head).Length),
        "axis_dot": float(axis.dot(expected_axis)),
    }
    if (
        datum_residuals["eye_center_mm"] > 1.0e-6
        or datum_residuals["head_center_mm"] > 1.0e-6
        or datum_residuals["axis_dot"] < 0.999999
    ):
        raise RuntimeError(f"protected lower bore datum changed: {datum_residuals}")

    inventory = {str(component.key): component for component in components}
    owner_key = str(target["receiving_owner"])
    owner = inventory.get(owner_key)
    if owner is None or owner.shape is None or owner.shape.isNull():
        raise RuntimeError(f"exact receiving owner is unavailable: {owner_key}")
    anchors = select_edge_anchors(
        owner.shape,
        head_bore,
        tangent,
        depth,
        axis,
        geometry["anchor_scan"],
        Part,
    )

    exits = [float(item["interval_mm"][0]) for item in anchors]
    bridge_front = min(exits) - float(
        geometry["bridge_front_setback_from_farthest_exit_mm"]
    )
    bridge_thickness = float(geometry["bridge_thickness_mm"])
    bridge_back = bridge_front - bridge_thickness
    foot_radius = float(geometry["foot_radius_mm"])
    tangent_min = min(float(item["tangent_offset_mm"]) for item in anchors)
    tangent_max = max(float(item["tangent_offset_mm"]) for item in anchors)
    depth_center = sum(float(item["depth_offset_mm"]) for item in anchors) / 2.0
    bridge_length = tangent_max - tangent_min + 2.0 * foot_radius
    bridge_center = (
        head_bore
        + tangent * ((tangent_min + tangent_max) / 2.0)
        + depth * depth_center
        + axis * (bridge_front - bridge_thickness / 2.0)
    )
    bridge = toolkit.oriented_box(
        Part,
        bridge_center,
        (tangent, depth, axis),
        (bridge_length, float(geometry["bridge_depth_mm"]), bridge_thickness),
    )
    overlap = 0.3
    feet = []
    for record, exit_offset in zip(anchors, exits):
        start_offset = bridge_front - overlap
        length = exit_offset - start_offset
        if length <= overlap:
            raise RuntimeError("backer contact foot has no positive length")
        base = record["anchor"] + axis * start_offset
        feet.append(Part.makeCylinder(foot_radius, length, base, axis))
    raw = bridge.multiFuse(feet).removeSplitter()
    toolkit.require_single_solid(raw, "raw lower interior backer")

    shell_shapes = [
        component.shape
        for component in components
        if component.shape is not None and not component.shape.isNull()
    ]
    shell_compound = Part.makeCompound(shell_shapes)
    conformal = raw.cut(shell_compound).removeSplitter()
    toolkit.require_single_solid(conformal, "shell-conformal lower interior backer")

    bore_radius = float(geometry["bore_diameter_mm"]) / 2.0
    bore = Part.makeCylinder(
        bore_radius,
        40.0,
        head_bore - axis * 20.0,
        axis,
    )
    backer = conformal.cut(bore).removeSplitter()
    toolkit.require_single_solid(backer, "drilled lower interior backer")
    if not backer.isValid() or not backer.isClosed() or len(backer.Solids) != 1:
        raise RuntimeError("backer is not one valid closed solid")
    try:
        check_records = [str(value) for value in (backer.check(True) or [])]
    except Exception as exc:
        check_records = [f"{type(exc).__name__}: {exc}"]
    if check_records:
        raise RuntimeError(f"backer OCCT check failed: {check_records}")

    minimum_wall = min(
        bridge_thickness,
        float(geometry["bridge_depth_mm"]) / 2.0 - bore_radius,
        bridge_length / 2.0 - bore_radius,
    )
    if minimum_wall < float(geometry["minimum_printed_wall_mm"]):
        raise RuntimeError(f"minimum printed wall failed: {minimum_wall}")

    anchor_public = []
    for item in anchors:
        anchor_public.append(
            {
                "side": item["side"],
                "tangent_offset_mm": float(item["tangent_offset_mm"]),
                "depth_offset_mm": float(item["depth_offset_mm"]),
                "interval_mm": [float(value) for value in item["interval_mm"]],
                "anchor_mm": vector_values(item["anchor"]),
                "outer_exit_mm": vector_values(
                    item["anchor"] + axis * float(item["interval_mm"][0])
                ),
            }
        )
    construction = {
        "axis": axis,
        "tangent": tangent,
        "depth": depth,
        "eye_bore": eye_bore,
        "head_bore": head_bore,
        "bridge_front_offset_from_head_bore_mm": bridge_front,
        "bridge_back_offset_from_head_bore_mm": bridge_back,
        "bridge_length_mm": bridge_length,
        "anchors": anchor_public,
        "shell_compound": shell_compound,
        "owner_shape": owner.shape,
        "minimum_wall_mm": minimum_wall,
        "datum_residuals": datum_residuals,
    }
    return backer, construction, inventory


def translated(shape: Any, vector: Any) -> Any:
    moved = shape.copy()
    moved.translate(vector)
    return moved


def evaluate_geometry(
    contract: dict[str, Any],
    held_eye: Any,
    held_eye_placement: Any,
    backer: Any,
    construction: dict[str, Any],
    components: Sequence[Any],
    refs: dict[str, Any],
    App: Any,
    Part: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    geometry = contract["geometry"]
    hardware = contract["hardware"]
    epsilon = float(geometry["maximum_positive_intersection_mm3"])
    intersections: dict[str, float] = {}
    minimum_noncontact_clearance = math.inf
    for component in components:
        shape = component.shape
        if shape is None or shape.isNull() or not aabb_near(backer, shape, 0.1):
            continue
        common = float(backer.common(shape).Volume)
        if common > epsilon:
            intersections[str(component.key)] = common
        if str(component.key) != contract["target"]["receiving_owner"]:
            minimum_noncontact_clearance = min(
                minimum_noncontact_clearance,
                float(backer.distToShape(shape)[0]),
            )
    if intersections:
        raise RuntimeError(f"backer intersects protected shell owners: {intersections}")

    owner = construction["owner_shape"]
    contact_distance = float(backer.distToShape(owner)[0])
    contact_section = backer.section(owner)
    contact_length = sum(float(edge.Length) for edge in contact_section.Edges)
    if contact_distance > 1.0e-6 or contact_length < float(
        geometry["minimum_contact_section_length_mm"]
    ):
        raise RuntimeError(
            f"backer does not clamp the exact opening edge: distance={contact_distance}, "
            f"section={contact_length}"
        )

    held_eye_shape = held_eye.Shape.copy()
    held_eye_shape.Placement = held_eye_placement
    eye_common = float(backer.common(held_eye_shape).Volume)
    if eye_common > epsilon:
        raise RuntimeError(f"backer intersects held eye: {eye_common}")

    frustum_common = float(backer.common(refs["frustum"]).Volume)
    exterior_common = float(backer.common(refs["exterior"]).Volume)
    if frustum_common > epsilon or exterior_common > epsilon:
        raise RuntimeError(
            f"backer enters protected visibility: frustum={frustum_common}, "
            f"exterior={exterior_common}"
        )

    cartridge_max = 0.0
    cartridge_min_clearance = math.inf
    samples = int(contract["service"]["cartridge_samples"])
    distance = float(contract["service"]["cartridge_distance_mm"])
    for index in range(samples):
        fraction = index / (samples - 1)
        moved = translated(refs["cartridge"], refs["axis_n"] * distance * fraction)
        if aabb_near(backer, moved, 0.1):
            cartridge_max = max(cartridge_max, float(backer.common(moved).Volume))
            cartridge_min_clearance = min(
                cartridge_min_clearance, float(backer.distToShape(moved)[0])
            )
    if cartridge_max > epsilon:
        raise RuntimeError(f"backer blocks cartridge service sweep: {cartridge_max}")

    axis = construction["axis"]
    eye_bore = construction["eye_bore"]
    head_bore = construction["head_bore"]
    bridge_back = float(construction["bridge_back_offset_from_head_bore_mm"])
    head_from_eye = float((head_bore - eye_bore).dot(axis))
    mount = contract["_split_parameters"]["geometry"]["head_mount"]
    eye_face_offset = (
        -float(mount["bore_center_to_mating_face_mm"])
        + float(mount["total_thickness_mm"])
    )
    rear_face_from_eye = head_from_eye + bridge_back
    grip_span = eye_face_offset - rear_face_from_eye
    bolt_length = float(hardware["bolt_length_mm"])
    if grip_span <= 0.0 or grip_span + 2.0 > bolt_length:
        raise RuntimeError(
            f"M2.5 bolt grip is invalid: span={grip_span}, length={bolt_length}"
        )

    washer_t = float(hardware["washer_thickness_mm"])
    washer_r = float(hardware["washer_outer_diameter_mm"]) / 2.0
    nyloc_l = float(hardware["nyloc_length_mm"])
    nyloc_r = float(hardware["nyloc_outer_diameter_mm"]) / 2.0
    tool_l = float(hardware["tool_approach_length_mm"])
    tool_r = float(hardware["tool_approach_diameter_mm"]) / 2.0
    rear_face = head_bore + axis * bridge_back
    eye_face = eye_bore + axis * eye_face_offset
    bolt = Part.makeCylinder(
        float(hardware["bolt_diameter_mm"]) / 2.0,
        bolt_length,
        rear_face,
        axis,
    )
    eye_washer = Part.makeCylinder(washer_r, washer_t, eye_face, axis)
    backer_washer = Part.makeCylinder(
        washer_r, washer_t, rear_face - axis * washer_t, axis
    )
    nyloc = Part.makeCylinder(
        nyloc_r,
        nyloc_l,
        rear_face - axis * (washer_t + nyloc_l),
        axis,
    )
    tool = Part.makeCylinder(
        tool_r,
        tool_l,
        rear_face - axis * (washer_t + nyloc_l + tool_l),
        axis,
    )
    hardware_shapes = {
        "bolt": bolt,
        "eye_washer": eye_washer,
        "backer_washer": backer_washer,
        "nyloc": nyloc,
        "tool": tool,
    }
    obstruction: dict[str, dict[str, float]] = {}
    shell_shapes = [
        component.shape
        for component in components
        if component.shape is not None and not component.shape.isNull()
    ]
    for name, shape in hardware_shapes.items():
        values = {
            "shell_mm3": max(
                (
                    float(shape.common(shell).Volume)
                    for shell in shell_shapes
                    if aabb_near(shape, shell, 0.0)
                ),
                default=0.0,
            ),
            "cartridge_mm3": float(shape.common(refs["cartridge"]).Volume),
        }
        if name in {"eye_washer", "backer_washer", "nyloc", "tool"}:
            values["held_eye_mm3"] = float(shape.common(held_eye_shape).Volume)
        if name in {"eye_washer", "nyloc", "tool"}:
            values["backer_mm3"] = float(shape.common(backer).Volume)
        obstruction[name] = values
    prohibited_hardware = max(
        (value for values in obstruction.values() for value in values.values()),
        default=0.0,
    )
    if prohibited_hardware > epsilon:
        raise RuntimeError(f"hardware/tool access is obstructed: {obstruction}")

    checks = {
        "topology": bool(backer.isValid() and backer.isClosed() and len(backer.Solids) == 1),
        "datum": bool(
            construction["datum_residuals"]["eye_center_mm"] <= 1.0e-6
            and construction["datum_residuals"]["head_center_mm"] <= 1.0e-6
            and construction["datum_residuals"]["axis_dot"] >= 0.999999
        ),
        "two_edge_anchors": len(construction["anchors"]) == 2,
        "shell_clear": not intersections,
        "edge_contact": contact_distance <= 1.0e-6
        and contact_length >= float(geometry["minimum_contact_section_length_mm"]),
        "eye_clear": eye_common <= epsilon,
        "visibility_clear": frustum_common <= epsilon and exterior_common <= epsilon,
        "cartridge_service_clear": cartridge_max <= epsilon,
        "hardware_tool_clear": prohibited_hardware <= epsilon,
        "minimum_wall": construction["minimum_wall_mm"]
        >= float(geometry["minimum_printed_wall_mm"]),
    }
    evaluation = {
        "status": (
            "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED"
            if all(checks.values())
            else "FEASIBILITY_FAIL__NO_REVIEW_ARTIFACT"
        ),
        "checks": checks,
        "measurements": {
            "volume_mm3": float(backer.Volume),
            "bounds_mm": {
                "min": [backer.BoundBox.XMin, backer.BoundBox.YMin, backer.BoundBox.ZMin],
                "max": [backer.BoundBox.XMax, backer.BoundBox.YMax, backer.BoundBox.ZMax],
            },
            "minimum_wall_mm": float(construction["minimum_wall_mm"]),
            "datum_residuals": construction["datum_residuals"],
            "anchors": construction["anchors"],
            "edge_contact_distance_mm": contact_distance,
            "edge_contact_section_length_mm": contact_length,
            "maximum_shell_intersection_mm3": max(intersections.values(), default=0.0),
            "minimum_noncontact_shell_clearance_mm": minimum_noncontact_clearance,
            "held_eye_intersection_mm3": eye_common,
            "frustum_intersection_mm3": frustum_common,
            "exterior_intersection_mm3": exterior_common,
            "cartridge_service_maximum_intersection_mm3": cartridge_max,
            "cartridge_service_minimum_clearance_mm": cartridge_min_clearance,
            "bolt_grip_span_mm": grip_span,
            "bolt_length_mm": bolt_length,
            "hardware_obstructions_mm3": obstruction,
        },
    }
    return evaluation, hardware_shapes


def prepare() -> dict[str, Any]:
    root = repository_root()
    contract_path = Path(__file__).with_name("contract.json")
    contract = load_json(contract_path)
    inputs = contract["inputs"]
    paths = {name: verify_spec(root, spec, name) for name, spec in inputs.items()}
    split_contract = load_json(paths["split_eye_contract"])
    split_parameters = split_contract["allowed_mutations"][0]["parameters"]
    contract["_split_parameters"] = split_parameters

    import FreeCAD as App  # type: ignore
    import Mesh  # type: ignore  # noqa: F401
    import Part  # type: ignore

    candidate_before = sha256_file(paths["held_eye_candidate"])
    baseline_before = sha256_file(paths["relieved_shell_fcstd"])
    document = App.openDocument(str(paths["held_eye_candidate"]))
    try:
        target = document.getObject(TARGET_OBJECT)
        if target is None or target.TypeId != "Part::Feature" or target.Shape.isNull():
            raise RuntimeError("held eye target is missing or invalid")
        original_target_hash = sha256_shape(target.Shape)
        original_target_placement = App.Placement(target.Placement)
        components = generator._load_shell_components(split_parameters, App, Part)
        if len(components) != 101:
            raise RuntimeError(f"expected 101 shell owners, got {len(components)}")
        refs = validator._reference_geometry(split_parameters, App, Part)
        backer, construction, inventory = build_backer(
            contract, refs, components, App, Part
        )
        evaluation, hardware_shapes = evaluate_geometry(
            contract,
            target,
            original_target_placement,
            backer,
            construction,
            components,
            refs,
            App,
            Part,
        )
        if sha256_shape(target.Shape) != original_target_hash:
            raise RuntimeError("held eye target changed in memory")
        if target.Placement != original_target_placement:
            raise RuntimeError("held eye placement changed in memory")
        return {
            "root": root,
            "contract_path": contract_path,
            "contract": contract,
            "paths": paths,
            "document": document,
            "target": target,
            "target_shape": target.Shape.copy(),
            "target_placement": original_target_placement,
            "target_shape_hash": original_target_hash,
            "components": components,
            "refs": refs,
            "backer": backer,
            "construction": construction,
            "hardware_shapes": hardware_shapes,
            "evaluation": evaluation,
            "candidate_before": candidate_before,
            "baseline_before": baseline_before,
            "App": App,
            "Part": Part,
            "inventory": inventory,
        }
    except Exception:
        App.closeDocument(document.Name)
        raise


def public_report(context: dict[str, Any], *, mode: str) -> dict[str, Any]:
    candidate_after = sha256_file(context["paths"]["held_eye_candidate"])
    baseline_after = sha256_file(context["paths"]["relieved_shell_fcstd"])
    if candidate_after != context["candidate_before"]:
        raise RuntimeError("held candidate changed on disk")
    if baseline_after != context["baseline_before"]:
        raise RuntimeError("relieved shell baseline changed on disk")
    return {
        "schema_version": 1,
        "review_id": REVIEW_ID,
        "mode": mode,
        "status": context["evaluation"]["status"],
        "evaluation": context["evaluation"],
        "pins": {
            "contract_sha256": sha256_file(context["contract_path"]),
            "tool_sha256": sha256_file(Path(__file__)),
            "held_candidate_sha256": candidate_after,
            "relieved_shell_sha256": baseline_after,
            "held_target_brep_sha256": context["target_shape_hash"],
        },
        "input_write_trace": {
            "held_candidate_opened_read_only": True,
            "held_candidate_saved": False,
            "relieved_shell_saved": False,
            "canonical_v34_saved": False,
            "geometry_export_created": False,
        },
        "authority": "REVIEW_ONLY__NONAUTHORITATIVE__NOT_PRINT_READY",
    }


def render_views(context: dict[str, Any], output_dir: Path) -> None:
    toolkit = generator.toolkit
    shell_compound = context["construction"]["shell_compound"]
    target_shape = context["target_shape"]
    cartridge = context["refs"]["cartridge"]
    backer = context["backer"]
    base_records = [
        toolkit.shape_record(shell_compound, (150, 154, 160), deflection=1.0),
        toolkit.shape_record(target_shape, (42, 142, 190), deflection=0.65),
        toolkit.shape_record(cartridge, (223, 164, 54), deflection=0.55),
    ]
    candidate_records = [*base_records, toolkit.shape_record(backer, (44, 180, 92), deflection=0.3)]
    colors = {
        "bolt": (44, 126, 210),
        "eye_washer": (241, 184, 52),
        "backer_washer": (241, 184, 52),
        "nyloc": (148, 80, 190),
        "tool": (39, 176, 155),
    }
    for name, shape in context["hardware_shapes"].items():
        candidate_records.append(toolkit.shape_record(shape, colors[name], deflection=0.3))
    fixed = {
        "front": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "rear": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
        "left": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        "right": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        "top": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
        "bottom": ((0.0, 0.0, 1.0), (0.0, -1.0, 0.0)),
    }
    review_dir = output_dir / "review"
    for name, (direction, up) in fixed.items():
        toolkit.render_side_by_side(
            review_dir / f"{name}.png",
            base_records,
            candidate_records,
            direction,
            up,
        )
    toolkit.render_side_by_side(
        review_dir / "interior-closeup.png",
        base_records,
        candidate_records,
        tuple(-value for value in toolkit.tuple3(context["construction"]["axis"])),
        toolkit.tuple3(context["construction"]["tangent"]),
        toolkit.tuple3(context["construction"]["head_bore"]),
        42.0,
    )


def create_review(context: dict[str, Any], output_dir: Path) -> Path:
    App = context["App"]
    contract = context["contract"]
    review = App.newDocument("RightEyeLowerInteriorBackerClampReviewR1")
    try:
        entries = [
            ("REFERENCE__SHELL_101", "REFERENCE — relieved shell 101-owner compound", context["construction"]["shell_compound"], (0.72, 0.72, 0.74), 70),
            ("REFERENCE__HELD_SPLIT_EYE", "REFERENCE — held split eye ec72a948", context["target_shape"], (0.20, 0.58, 0.82), 20),
            ("REFERENCE__REAR_CARTRIDGE", "REFERENCE — independent rear cartridge", context["refs"]["cartridge"], (0.90, 0.62, 0.18), 35),
            ("PROPOSED__LOWER_INTERIOR_BACKER_CLAMP_R1", "PROPOSED — lower interior backer clamp R1", context["backer"], (0.15, 0.72, 0.34), 0),
        ]
        for name, label, shape, color, transparency in entries:
            obj = review.addObject("Part::Feature", name)
            obj.Label = label
            obj.Shape = shape.copy()
            obj.addProperty("App::PropertyString", "Authority", "ReviewControl")
            obj.Authority = "REVIEW_ONLY__NONAUTHORITATIVE__NOT_PRINT_READY"
            if name.startswith("PROPOSED"):
                obj.addProperty("App::PropertyVector", "LowerEyeBoreCenter", "ProtectedDatums")
                obj.addProperty("App::PropertyVector", "LowerHeadBoreCenter", "ProtectedDatums")
                obj.addProperty("App::PropertyVector", "LowerSignedBoreAxis", "ProtectedDatums")
                obj.LowerEyeBoreCenter = context["construction"]["eye_bore"]
                obj.LowerHeadBoreCenter = context["construction"]["head_bore"]
                obj.LowerSignedBoreAxis = context["construction"]["axis"]
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.Transparency = transparency
        for name, shape in context["hardware_shapes"].items():
            obj = review.addObject("Part::Feature", f"REFERENCE__HARDWARE_{name.upper()}")
            obj.Label = f"REFERENCE — {name} access envelope"
            obj.Shape = shape.copy()
            obj.addProperty("App::PropertyString", "Authority", "ReviewControl")
            obj.Authority = "REFERENCE_ONLY__NOT_PART_OF_BACKER_SOLID"
            obj.ViewObject.ShapeColor = (0.80, 0.55, 0.12)
            obj.ViewObject.Transparency = 25 if name == "tool" else 0
        review.recompute()
        fcstd_path = output_dir / contract["output"]["fcstd"]
        review.saveAs(str(fcstd_path))
        return fcstd_path
    finally:
        App.closeDocument(review.Name)


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
    context = prepare()
    try:
        if context["evaluation"]["status"] != "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED":
            raise RuntimeError("bounded feasibility did not pass")
        if args.mode == "feasibility":
            if args.report is None or args.report.exists():
                raise RuntimeError("fresh --report is required for feasibility mode")
            report = public_report(context, mode="feasibility_no_save")
            report["elapsed_seconds"] = time.monotonic() - started
            report["review_artifact_created"] = False
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print("FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED")
            return 0

        if (
            args.feasibility_report is None
            or not args.feasibility_sha256
            or sha256_file(args.feasibility_report) != args.feasibility_sha256
        ):
            raise RuntimeError("review mode requires the exact pinned feasibility report")
        feasibility = load_json(args.feasibility_report)
        if feasibility.get("status") != "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED":
            raise RuntimeError("pinned feasibility report is not a pass")
        root = context["root"]
        output_dir = root / context["contract"]["output"]["directory"]
        if output_dir.exists():
            raise RuntimeError(f"review output already exists: {output_dir}")
        output_dir.mkdir(parents=True)
        fcstd_path = create_review(context, output_dir)
        render_views(context, output_dir)
        report = public_report(context, mode="single_review_artifact")
        report["elapsed_seconds"] = time.monotonic() - started
        report["review_artifact_created"] = True
        report["review_fcstd"] = str(fcstd_path.relative_to(root))
        report["review_fcstd_sha256"] = sha256_file(fcstd_path)
        report["feasibility_report_sha256"] = args.feasibility_sha256
        validation_path = output_dir / context["contract"]["output"]["validation"]
        validation_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("REVIEW_ONLY_ARTIFACT_CREATED__AWAIT_HUMAN_INSPECTION")
        return 0
    finally:
        candidate_path = context["paths"]["held_eye_candidate"]
        baseline_path = context["paths"]["relieved_shell_fcstd"]
        App = context["App"]
        if App.getDocument(context["document"].Name) is not None:
            App.closeDocument(context["document"].Name)
        if sha256_file(candidate_path) != context["candidate_before"]:
            raise RuntimeError("held candidate changed during close")
        if sha256_file(baseline_path) != context["baseline_before"]:
            raise RuntimeError("relieved shell changed during close")


if __name__ == "__main__":
    raise SystemExit(main())
