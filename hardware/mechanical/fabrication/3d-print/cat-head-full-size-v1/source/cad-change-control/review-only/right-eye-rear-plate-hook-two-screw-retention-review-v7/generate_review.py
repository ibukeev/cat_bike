#!/usr/bin/env python3
"""Build and validate the review-only V7 rear-plate retention proposal.

V7 preserves the complete accepted V6 carrier/lens construction.  It changes
only the removable LED rear plate and the immediately adjacent rear interior:
two plate-owned hooks on the wire-side edge, two carrier-owned ledges, a
continuous shallow locating/light-blocking rim, and two rear-driven M2 screws
into integral pilot bosses on the opposite edge.
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


HERE = Path(__file__).resolve().parent
EPSILON_MM3 = 1.0e-6


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_root() -> Path:
    for candidate in (HERE, *HERE.parents):
        if (candidate / ".git").exists() and (candidate / "hardware").exists():
            return candidate
    raise RuntimeError("repository root not found")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: JSON root must be an object")
    return value


def load_v6(root: Path, contract: dict[str, Any]) -> Any:
    for key, pin in contract["inputs"].items():
        path = root / str(pin["path"])
        actual = sha256_file(path)
        if actual != str(pin["sha256"]):
            raise RuntimeError(f"{key}: pin mismatch {actual} != {pin['sha256']}")
    path = root / str(contract["inputs"]["v6_generator"]["path"])
    spec = importlib.util.spec_from_file_location("_pinned_approved_eye_v6", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def copy_vector(App: Any, value: Any) -> Any:
    return App.Vector(float(value.x), float(value.y), float(value.z))


def vector_values(value: Any) -> list[float]:
    return [float(value.x), float(value.y), float(value.z)]


def read_inputs() -> dict[str, Any]:
    root = repository_root()
    contract = load_json(HERE / "contract.json")
    v6 = load_v6(root, contract)
    context = v6.read_inputs()
    context["v6_contract"] = context["contract"]
    context["contract"] = contract
    context["v6_module"] = v6
    return context


def run_v6_construct(context: dict[str, Any], App: Any, Part: Any) -> None:
    active = context["contract"]
    context["contract"] = context["v6_contract"]
    try:
        context["v6_module"].construct(context, App, Part)
    finally:
        context["contract"] = active


def run_v6_evaluate(context: dict[str, Any]) -> dict[str, Any]:
    active = context["contract"]
    context["contract"] = context["v6_contract"]
    try:
        return context["v6_module"].evaluate(context)
    finally:
        context["contract"] = active


def edge_frame(
    App: Any,
    loop: Sequence[Any],
    index: int,
    axis_n: Any,
    center: Any,
) -> tuple[Any, Any, Any, float]:
    start = loop[index]
    end = loop[(index + 1) % len(loop)]
    delta = end - start
    length = float(delta.Length)
    if length <= 1.0e-9:
        raise RuntimeError(f"edge {index} is degenerate")
    tangent = copy_vector(App, delta)
    tangent.normalize()
    midpoint = (start + end) * 0.5
    inward = axis_n.cross(tangent)
    if float(inward.Length) <= 1.0e-9:
        raise RuntimeError(f"edge {index} has no inward direction")
    inward.normalize()
    if float((center - midpoint).dot(inward)) < 0.0:
        inward = inward * -1.0
    return start, tangent, inward, length


def edge_point(start: Any, tangent: Any, length: float, fraction: float) -> Any:
    return start + tangent * (length * fraction)


def point_segment_distance(point: Any, start: Any, end: Any) -> float:
    delta = end - start
    squared = float(delta.dot(delta))
    if squared <= 1.0e-12:
        return float((point - start).Length)
    parameter = max(0.0, min(1.0, float((point - start).dot(delta)) / squared))
    return float((point - (start + delta * parameter)).Length)


def rectangle_prism(
    Part: Any,
    toolkit: Any,
    axis_n: Any,
    anchor: Any,
    tangent: Any,
    inward: Any,
    width: float,
    radial_start: float,
    radial_end: float,
    front_depth: float,
    rear_depth: float,
) -> Any:
    half = width / 2.0
    loop = [
        anchor - tangent * half + inward * radial_start,
        anchor + tangent * half + inward * radial_start,
        anchor + tangent * half + inward * radial_end,
        anchor - tangent * half + inward * radial_end,
    ]
    shape = toolkit.polygon_face(
        Part, toolkit.at_depth(loop, front_depth, axis_n)
    ).extrude(axis_n * (rear_depth - front_depth)).removeSplitter()
    if shape.isNull() or not shape.isValid() or not shape.isClosed():
        raise RuntimeError("rectangular retention prism is invalid")
    return shape


def common_volume(v3: Any, first: Any, second: Any) -> float:
    if not v3.aabb_near(first, second, 0.0):
        return 0.0
    return v3.common_volume(first, second)


def shell_common(context: dict[str, Any], shape: Any) -> float:
    v3 = context["v3_module"]
    total = 0.0
    for _, owner in context["shell_records"]:
        if v3.aabb_near(shape, owner, 0.25):
            total += v3.common_volume(shape, owner)
    return total


def construct(context: dict[str, Any], App: Any, Part: Any) -> None:
    run_v6_construct(context, App, Part)
    toolkit = context["toolkit"]
    v3 = context["v3_module"]
    values = context["contract"]["dimensions_mm"]
    axis_n = context["axis_n"]
    axis_u = context["axis_u"]
    axis_v = context["axis_v"]
    origin = context["origin"]
    box_inner = context["box_inner"]
    box_center = toolkit.average(App, box_inner)
    v6_carrier = context["carrier"].copy()
    v6_rear_plate = context["rear_cap"].copy()
    v6_lens = context["lens"].copy()
    v6_aperture = [copy_vector(App, item) for item in context["aperture"]]

    cap_front = float(values["rear_plate_front_depth"])
    cap_thickness = float(values["rear_plate_thickness"])
    cap_rear = cap_front + cap_thickness
    cap_loop = v3.polygon_inset_loop(
        App,
        box_inner,
        float(values["rear_plate_radial_clearance"]),
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    wire_center = context["wire_cutter"].CenterOfMass
    edge_wire_distances = [
        point_segment_distance(
            wire_center, box_inner[index], box_inner[(index + 1) % len(box_inner)]
        )
        for index in range(len(box_inner))
    ]
    hook_edge_index = min(range(len(box_inner)), key=edge_wire_distances.__getitem__)
    screw_edge_index = (hook_edge_index + len(box_inner) // 2) % len(box_inner)
    hook_start, hook_tangent, hook_inward, hook_length = edge_frame(
        App, box_inner, hook_edge_index, axis_n, box_center
    )
    screw_start, screw_tangent, screw_inward, screw_length_edge = edge_frame(
        App, box_inner, screw_edge_index, axis_n, box_center
    )

    rim_outer = v3.polygon_inset_loop(
        App,
        box_inner,
        -float(values["locating_rim_outer_overlap_into_wall"]),
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    rim_inner = v3.polygon_inset_loop(
        App,
        cap_loop,
        float(values["locating_rim_inner_inset_from_plate_edge"]),
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    locating_rim = toolkit.ring_prism(
        Part,
        rim_outer,
        rim_inner,
        float(values["locating_rim_front_depth"]),
        float(values["locating_rim_rear_depth"]),
        axis_n,
        "rear plate locating and light-blocking rim",
    )

    plate = v6_rear_plate
    hook_notches = []
    hook_solids = []
    hook_toes = []
    hook_necks = []
    carrier_ledges = []
    hook_centers = []
    ledge_root_common = []
    hook_ledge_seated_common = []
    hook_pullout_common = []
    for fraction in values["hook_tangent_fractions"]:
        anchor = edge_point(hook_start, hook_tangent, hook_length, float(fraction))
        hook_centers.append(anchor)
        notch = rectangle_prism(
            Part,
            toolkit,
            axis_n,
            anchor,
            hook_tangent,
            hook_inward,
            float(values["hook_notch_width"]),
            -0.30,
            float(values["hook_notch_radial_depth"]),
            cap_front - 0.10,
            cap_rear + 0.10,
        )
        plate = plate.cut(notch).removeSplitter()
        hook_notches.append(notch)
        toe = rectangle_prism(
            Part,
            toolkit,
            axis_n,
            anchor,
            hook_tangent,
            hook_inward,
            float(values["hook_toe_width"]),
            float(values["hook_toe_radial_start"]),
            float(values["hook_toe_radial_end"]),
            float(values["hook_toe_front_depth"]),
            float(values["hook_toe_rear_depth"]),
        )
        neck = rectangle_prism(
            Part,
            toolkit,
            axis_n,
            anchor,
            hook_tangent,
            hook_inward,
            float(values["hook_toe_width"]),
            float(values["hook_neck_radial_start"]),
            float(values["hook_neck_radial_end"]),
            float(values["hook_neck_front_depth"]),
            float(values["hook_neck_rear_depth"]),
        )
        hook = toe.fuse(neck).removeSplitter()
        ledge = rectangle_prism(
            Part,
            toolkit,
            axis_n,
            anchor,
            hook_tangent,
            hook_inward,
            float(values["carrier_hook_ledge_width"]),
            float(values["carrier_hook_ledge_radial_start"]),
            float(values["carrier_hook_ledge_radial_end"]),
            float(values["carrier_hook_ledge_front_depth"]),
            float(values["carrier_hook_ledge_rear_depth"]),
        )
        hook_solids.append(hook)
        hook_toes.append(toe)
        hook_necks.append(neck)
        carrier_ledges.append(ledge)
        ledge_root_common.append(v3.common_volume(ledge, v6_carrier))
        hook_ledge_seated_common.append(v3.common_volume(hook, ledge))
        pulled = hook.copy()
        pulled.translate(axis_n * 0.10)
        hook_pullout_common.append(v3.common_volume(pulled, ledge))

    plate = toolkit.fuse_shapes(
        [plate, *hook_solids], "V7 rear plate with two integral hooks"
    ).removeSplitter()

    boss_solids = []
    boss_pilot_cutters = []
    plate_hole_cutters = []
    rear_screw_solids = []
    rear_screw_shafts = []
    rear_screw_heads = []
    rear_screw_centers = []
    rear_screw_axis_markers = []
    driver_corridors = []
    boss_root_common = []
    for fraction in values["rear_screw_tangent_fractions"]:
        edge_anchor = edge_point(
            screw_start, screw_tangent, screw_length_edge, float(fraction)
        )
        boss = rectangle_prism(
            Part,
            toolkit,
            axis_n,
            edge_anchor,
            screw_tangent,
            screw_inward,
            float(values["carrier_boss_tangent_width"]),
            float(values["carrier_boss_radial_start"]),
            float(values["carrier_boss_radial_end"]),
            float(values["carrier_boss_front_depth"]),
            float(values["carrier_boss_rear_depth"]),
        )
        center = edge_anchor + screw_inward * float(
            values["carrier_boss_center_radial_offset"]
        )
        pilot = Part.makeCylinder(
            float(values["carrier_boss_pilot_diameter"]) / 2.0,
            float(values["carrier_boss_rear_depth"])
            - float(values["carrier_boss_front_depth"])
            + 0.30,
            center + axis_n * (float(values["carrier_boss_front_depth"]) - 0.10),
            axis_n,
        )
        plate_hole = Part.makeCylinder(
            float(values["rear_plate_clearance_hole_diameter"]) / 2.0,
            cap_thickness + 0.20,
            center + axis_n * (cap_front - 0.10),
            axis_n,
        )
        shaft = Part.makeCylinder(
            float(values["rear_screw_nominal_diameter"]) / 2.0,
            float(values["rear_screw_length"]),
            center + axis_n * cap_rear,
            axis_n * -1.0,
        )
        head = Part.makeCylinder(
            float(values["rear_screw_head_diameter"]) / 2.0,
            float(values["rear_screw_head_height"]),
            center + axis_n * cap_rear,
            axis_n,
        )
        screw = head.fuse(shaft).removeSplitter()
        driver = Part.makeCylinder(
            float(values["rear_driver_corridor_diameter"]) / 2.0,
            float(values["rear_driver_corridor_length"]),
            center
            + axis_n
            * (cap_rear + float(values["rear_screw_head_height"])),
            axis_n,
        )
        marker = Part.makeCylinder(
            0.12,
            float(values["rear_screw_length"])
            + float(values["rear_screw_head_height"]),
            center + axis_n * cap_rear,
            axis_n * -1.0,
        )
        boss_solids.append(boss)
        boss_pilot_cutters.append(pilot)
        plate_hole_cutters.append(plate_hole)
        rear_screw_solids.append(screw)
        rear_screw_shafts.append(shaft)
        rear_screw_heads.append(head)
        rear_screw_centers.append(center)
        rear_screw_axis_markers.append(marker)
        driver_corridors.append(driver)
        boss_root_common.append(v3.common_volume(boss, v6_carrier))

    for cutter in plate_hole_cutters:
        plate = plate.cut(cutter).removeSplitter()
    toolkit.require_single_solid(plate, "V7 hooked and drilled rear plate")

    predrill_carrier = toolkit.fuse_shapes(
        [v6_carrier, locating_rim, *carrier_ledges, *boss_solids],
        "V7 carrier with rear retention rim, ledges, and bosses",
    ).removeSplitter()
    carrier_without_ledges = toolkit.fuse_shapes(
        [v6_carrier, locating_rim, *boss_solids],
        "V7 pivot-obstacle carrier without intentional hook ledges",
    ).removeSplitter()
    carrier = predrill_carrier
    for cutter in boss_pilot_cutters:
        carrier = carrier.cut(cutter).removeSplitter()
        carrier_without_ledges = carrier_without_ledges.cut(cutter).removeSplitter()
    toolkit.require_single_solid(carrier, "V7 carrier with rear retention")

    plate_hole_residual = [v3.common_volume(plate, item) for item in plate_hole_cutters]
    boss_pilot_residual = [v3.common_volume(carrier, item) for item in boss_pilot_cutters]
    rear_screw_plate_common = [
        v3.common_volume(screw, plate) for screw in rear_screw_solids
    ]
    rear_screw_thread_common = [
        v3.common_volume(shaft, carrier) for shaft in rear_screw_shafts
    ]
    rear_screw_unintended_carrier_common = []
    for shaft, boss in zip(rear_screw_shafts, boss_solids):
        outside_boss = shaft.cut(boss).removeSplitter()
        rear_screw_unintended_carrier_common.append(
            v3.common_volume(outside_boss, carrier)
        )
    rear_screw_alignment_errors = []
    for center, plate_hole, boss_pilot in zip(
        rear_screw_centers, plate_hole_cutters, boss_pilot_cutters
    ):
        for cutter in (plate_hole, boss_pilot):
            delta = cutter.CenterOfMass - center
            lateral = delta - axis_n * float(delta.dot(axis_n))
            rear_screw_alignment_errors.append(float(lateral.Length))

    rear_screw_compound = Part.makeCompound(rear_screw_solids)
    driver_compound = Part.makeCompound(driver_corridors)
    carrier_feature_compound = Part.makeCompound(
        [locating_rim, *carrier_ledges, *boss_solids]
    )
    plate_hook_compound = Part.makeCompound(hook_solids)
    all_new_retention = Part.makeCompound(
        [locating_rim, *carrier_ledges, *boss_solids, *hook_solids]
    )

    rear_screw_shell_common = shell_common(context, rear_screw_compound)
    rear_screw_led_common = sum(
        common_volume(v3, rear_screw_compound, led) for led in context["led_shapes"]
    )
    rear_screw_wire_common = common_volume(
        v3, rear_screw_compound, context["wire_corridor"]
    )
    rear_screw_lens_common = common_volume(v3, rear_screw_compound, context["lens"])
    rear_screw_side_hardware_common = common_volume(
        v3, rear_screw_compound, context["side_screw_references"]
    )
    driver_shell_common = shell_common(context, driver_compound)
    driver_eye_common = sum(
        common_volume(v3, driver_compound, shape)
        for shape in (carrier, plate, context["lens"], context["side_screw_references"])
    )
    new_retention_shell_common = shell_common(context, all_new_retention)
    new_retention_led_common = sum(
        common_volume(v3, all_new_retention, led) for led in context["led_shapes"]
    )
    new_retention_wire_common = common_volume(
        v3, all_new_retention, context["wire_corridor"]
    )
    new_retention_lens_common = common_volume(
        v3, all_new_retention, context["lens"]
    )
    seated_plate_carrier_common = v3.common_volume(plate, carrier)
    locating_rim_distance = float(plate.distToShape(locating_rim)[0])
    locating_rim_root_common = v3.common_volume(locating_rim, v6_carrier)
    lens_symmetric_difference = (
        v3.common_volume(context["lens"].cut(v6_lens), context["lens"])
        + v3.common_volume(v6_lens.cut(context["lens"]), v6_lens)
    )
    aperture_shift = max(
        float((current - frozen).Length)
        for current, frozen in zip(context["aperture"], v6_aperture)
    )

    pivot_anchor = (
        edge_point(hook_start, hook_tangent, hook_length, 0.50)
        + hook_inward * 0.90
        + axis_n
        * (
            float(values["hook_toe_rear_depth"])
            + float(values["carrier_hook_ledge_front_depth"])
        )
        * 0.5
    )
    screw_edge_anchor = edge_point(screw_start, screw_tangent, screw_length_edge, 0.50)
    test_rotation = App.Rotation(hook_tangent, 1.0)
    test_point = pivot_anchor + test_rotation.multVec(screw_edge_anchor - pivot_anchor)
    pivot_sign = 1.0 if float((test_point - screw_edge_anchor).dot(axis_n)) > 0.0 else -1.0
    pivot_records = []
    pivot_maximum_unintended_common = 0.0
    pivot_maximum_full_carrier_common = 0.0
    pivot_final_rearward_motion = 0.0
    for angle in values["pivot_review_angles_deg"]:
        signed_angle = pivot_sign * float(angle)
        moved = plate.copy()
        moved.rotate(pivot_anchor, hook_tangent, signed_angle)
        common = v3.common_volume(moved, carrier_without_ledges)
        full_common = v3.common_volume(moved, carrier)
        rotated_point = pivot_anchor + App.Rotation(
            hook_tangent, signed_angle
        ).multVec(screw_edge_anchor - pivot_anchor)
        rearward = float((rotated_point - screw_edge_anchor).dot(axis_n))
        pivot_records.append({
            "angle_deg": float(angle),
            "signed_angle_deg": signed_angle,
            "unintended_carrier_common_mm3": common,
            "full_carrier_common_mm3": full_common,
            "screw_edge_rearward_motion_mm": rearward,
        })
        pivot_maximum_unintended_common = max(pivot_maximum_unintended_common, common)
        pivot_maximum_full_carrier_common = max(pivot_maximum_full_carrier_common, full_common)
        pivot_final_rearward_motion = rearward

    final_angle = pivot_sign * float(values["pivot_review_angles_deg"][-1])
    disengagement_records = []
    disengagement_maximum_common = 0.0
    disengagement_final_hook_clearance = 0.0
    ledge_compound = Part.makeCompound(carrier_ledges)
    for slide in values["hook_disengagement_slide_samples_mm"]:
        moved = plate.copy()
        moved.rotate(pivot_anchor, hook_tangent, final_angle)
        moved.translate(hook_inward * float(slide))
        common = v3.common_volume(moved, carrier)
        hook_clearance = float(moved.distToShape(ledge_compound)[0])
        disengagement_records.append({
            "inward_slide_mm": float(slide),
            "full_carrier_common_mm3": common,
            "hook_ledge_clearance_mm": hook_clearance,
        })
        disengagement_maximum_common = max(disengagement_maximum_common, common)
        disengagement_final_hook_clearance = hook_clearance

    context.update({
        "v6_carrier_reference": v6_carrier,
        "v6_rear_plate_reference": v6_rear_plate,
        "v6_lens_reference_v7": v6_lens,
        "v6_aperture_reference_v7": v6_aperture,
        "carrier": carrier,
        "rear_cap": plate,
        "rear_locating_rim": locating_rim,
        "rear_hook_ledges": carrier_ledges,
        "rear_hook_ledge_features": Part.makeCompound(carrier_ledges),
        "rear_plate_hooks": hook_solids,
        "rear_plate_hook_features": plate_hook_compound,
        "rear_hook_toes": hook_toes,
        "rear_hook_necks": hook_necks,
        "rear_hook_notches": hook_notches,
        "rear_bosses": boss_solids,
        "rear_boss_features": Part.makeCompound(boss_solids),
        "rear_boss_pilot_cutters": boss_pilot_cutters,
        "rear_plate_hole_cutters": plate_hole_cutters,
        "rear_retention_carrier_features": carrier_feature_compound,
        "rear_retention_all_new_features": all_new_retention,
        "rear_screw_solids": rear_screw_solids,
        "rear_screw_references": rear_screw_compound,
        "rear_screw_shafts": rear_screw_shafts,
        "rear_screw_heads": rear_screw_heads,
        "rear_screw_centers": rear_screw_centers,
        "rear_screw_axis_markers": Part.makeCompound(rear_screw_axis_markers),
        "rear_driver_corridors": driver_compound,
        "rear_hook_edge_index": hook_edge_index,
        "rear_screw_edge_index": screw_edge_index,
        "rear_edge_wire_distances_mm": edge_wire_distances,
        "rear_hook_centers": hook_centers,
        "rear_hook_radial_engagement_mm": float(values["hook_radial_engagement"]),
        "rear_hook_axial_clearance_mm": (
            float(values["carrier_hook_ledge_front_depth"])
            - float(values["hook_toe_rear_depth"])
        ),
        "rear_hook_ledge_seated_common_mm3": hook_ledge_seated_common,
        "rear_hook_pullout_capture_mm3": hook_pullout_common,
        "rear_boss_root_common_mm3": boss_root_common,
        "rear_ledge_root_common_mm3": ledge_root_common,
        "rear_locating_rim_root_common_mm3": locating_rim_root_common,
        "rear_locating_rim_distance_mm": locating_rim_distance,
        "rear_plate_carrier_common_mm3": seated_plate_carrier_common,
        "rear_plate_hole_residual_mm3": plate_hole_residual,
        "rear_boss_pilot_residual_mm3": boss_pilot_residual,
        "rear_screw_plate_common_mm3": rear_screw_plate_common,
        "rear_screw_thread_engagement_mm3": rear_screw_thread_common,
        "rear_screw_unintended_carrier_common_mm3": rear_screw_unintended_carrier_common,
        "rear_screw_alignment_errors_mm": rear_screw_alignment_errors,
        "rear_screw_shell_common_mm3": rear_screw_shell_common,
        "rear_screw_led_common_mm3": rear_screw_led_common,
        "rear_screw_wire_common_mm3": rear_screw_wire_common,
        "rear_screw_lens_common_mm3": rear_screw_lens_common,
        "rear_screw_side_hardware_common_mm3": rear_screw_side_hardware_common,
        "rear_driver_shell_common_mm3": driver_shell_common,
        "rear_driver_eye_common_mm3": driver_eye_common,
        "new_retention_shell_common_mm3": new_retention_shell_common,
        "new_retention_led_common_mm3": new_retention_led_common,
        "new_retention_wire_common_mm3": new_retention_wire_common,
        "new_retention_lens_common_mm3": new_retention_lens_common,
        "v6_lens_symmetric_difference_mm3": lens_symmetric_difference,
        "v6_aperture_maximum_shift_mm": aperture_shift,
        "rear_plate_pivot_records": pivot_records,
        "rear_plate_pivot_maximum_unintended_common_mm3": pivot_maximum_unintended_common,
        "rear_plate_pivot_maximum_full_carrier_common_mm3": pivot_maximum_full_carrier_common,
        "rear_plate_pivot_final_rearward_motion_mm": pivot_final_rearward_motion,
        "rear_plate_disengagement_records": disengagement_records,
        "rear_plate_disengagement_maximum_common_mm3": disengagement_maximum_common,
        "rear_plate_disengagement_final_hook_clearance_mm": disengagement_final_hook_clearance,
        "rear_plate_pivot_anchor": pivot_anchor,
        "rear_plate_pivot_axis": hook_tangent,
    })


def evaluate(context: dict[str, Any]) -> dict[str, Any]:
    base = run_v6_evaluate(context)
    checks = base["checks"]
    measurements = base["measurements"]
    values = context["contract"]["dimensions_mm"]
    gates = context["contract"]["gates"]
    carrier = context["carrier"]
    plate = context["rear_cap"]
    boss_radius = float(values["carrier_boss_pilot_diameter"]) / 2.0
    boss_tangent_margin = float(values["carrier_boss_tangent_width"]) / 2.0 - boss_radius
    boss_radial_margin = min(
        float(values["carrier_boss_center_radial_offset"])
        - float(values["carrier_boss_radial_start"])
        - boss_radius,
        float(values["carrier_boss_radial_end"])
        - float(values["carrier_boss_center_radial_offset"])
        - boss_radius,
    )
    boss_material = min(boss_tangent_margin, boss_radial_margin)
    hook_count = len(context["rear_plate_hooks"])
    screw_count = len(context["rear_screw_solids"])
    hook_edge_is_nearest = (
        context["rear_hook_edge_index"]
        == min(
            range(len(context["rear_edge_wire_distances_mm"])),
            key=context["rear_edge_wire_distances_mm"].__getitem__,
        )
    )
    screw_edge_is_opposite = (
        context["rear_screw_edge_index"]
        == (context["rear_hook_edge_index"] + 2) % 4
    )
    expected_rim_gap = float(values["rear_plate_to_locating_rim_gap"])
    rim_gap_error = abs(context["rear_locating_rim_distance_mm"] - expected_rim_gap)
    expected_hook_gap = float(values["hook_axial_clearance"])
    hook_gap_error = abs(context["rear_hook_axial_clearance_mm"] - expected_hook_gap)
    checks.update({
        "two_wire_side_rear_plate_hooks_present": (
            hook_count == int(gates["required_hook_count"])
        ),
        "hook_edge_is_structured_edge_nearest_wire_exit": hook_edge_is_nearest,
        "two_opposite_rear_m2_screws_present": (
            screw_count == int(gates["required_rear_screw_count"])
        ),
        "screw_edge_is_opposite_hook_edge": screw_edge_is_opposite,
        "hook_radial_engagement_is_structural": (
            context["rear_hook_radial_engagement_mm"]
            >= float(gates["minimum_hook_radial_engagement_mm"])
        ),
        "hook_axial_clearance_matches_contract": (
            hook_gap_error <= float(gates["hook_axial_clearance_tolerance_mm"])
        ),
        "hook_and_ledge_are_collision_free_when_seated": (
            max(context["rear_hook_ledge_seated_common_mm3"])
            <= float(gates["maximum_seated_hook_ledge_collision_mm3"])
        ),
        "hooks_capture_rearward_pullout": (
            min(context["rear_hook_pullout_capture_mm3"])
            >= float(gates["minimum_hook_pullout_capture_mm3"])
        ),
        "rear_plate_is_collision_free_when_seated": (
            context["rear_plate_carrier_common_mm3"]
            <= float(gates["maximum_seated_rear_plate_carrier_collision_mm3"])
        ),
        "continuous_locating_rim_has_pinned_gap": (
            rim_gap_error <= float(gates["maximum_locating_rim_gap_error_mm"])
        ),
        "rear_bosses_have_structural_pilot_material": (
            boss_material >= float(gates["minimum_boss_material_around_pilot_mm"])
        ),
        "rear_bosses_are_integrally_rooted": (
            min(context["rear_boss_root_common_mm3"])
            >= float(gates["minimum_boss_root_common_mm3"])
        ),
        "hook_ledges_are_integrally_rooted": (
            min(context["rear_ledge_root_common_mm3"])
            >= float(gates["minimum_ledge_root_common_mm3"])
        ),
        "locating_rim_is_integrally_rooted": (
            context["rear_locating_rim_root_common_mm3"]
            >= float(gates["minimum_locating_rim_root_common_mm3"])
        ),
        "rear_plate_clearance_holes_are_open": (
            max(context["rear_plate_hole_residual_mm3"])
            <= float(gates["maximum_plate_clearance_hole_residual_mm3"])
        ),
        "rear_boss_pilot_holes_are_open": (
            max(context["rear_boss_pilot_residual_mm3"])
            <= float(gates["maximum_boss_pilot_residual_mm3"])
        ),
        "rear_screw_axes_align_with_plate_and_boss_holes": (
            max(context["rear_screw_alignment_errors_mm"])
            <= float(gates["maximum_rear_screw_axis_alignment_error_mm"])
        ),
        "rear_screws_clear_plate_after_drilling": (
            max(context["rear_screw_plate_common_mm3"])
            <= float(gates["maximum_rear_screw_plate_collision_mm3"])
        ),
        "rear_screws_touch_carrier_only_in_threading_bosses": (
            max(context["rear_screw_unintended_carrier_common_mm3"])
            <= float(gates["maximum_unintended_rear_screw_carrier_collision_mm3"])
            and min(context["rear_screw_thread_engagement_mm3"]) > EPSILON_MM3
        ),
        "rear_screws_clear_head_shell": (
            context["rear_screw_shell_common_mm3"]
            <= float(gates["maximum_rear_screw_shell_collision_mm3"])
        ),
        "rear_screws_clear_led_pixels": (
            context["rear_screw_led_common_mm3"]
            <= float(gates["maximum_rear_screw_led_collision_mm3"])
        ),
        "rear_screws_clear_wire_route": (
            context["rear_screw_wire_common_mm3"]
            <= float(gates["maximum_rear_screw_wire_collision_mm3"])
        ),
        "rear_screws_clear_lens": (
            context["rear_screw_lens_common_mm3"]
            <= float(gates["maximum_rear_screw_lens_collision_mm3"])
        ),
        "rear_screws_clear_v6_side_hardware": (
            context["rear_screw_side_hardware_common_mm3"]
            <= float(gates["maximum_rear_screw_side_hardware_collision_mm3"])
        ),
        "rear_driver_corridors_clear_head_shell": (
            context["rear_driver_shell_common_mm3"]
            <= float(gates["maximum_driver_corridor_shell_collision_mm3"])
        ),
        "rear_driver_corridors_clear_eye_geometry": (
            context["rear_driver_eye_common_mm3"]
            <= float(gates["maximum_driver_corridor_eye_collision_mm3"])
        ),
        "new_retention_features_clear_head_shell": (
            context["new_retention_shell_common_mm3"]
            <= float(gates["maximum_new_retention_shell_collision_mm3"])
        ),
        "new_retention_features_clear_led_pixels": (
            context["new_retention_led_common_mm3"]
            <= float(gates["maximum_new_retention_led_collision_mm3"])
        ),
        "new_retention_features_clear_wire_route": (
            context["new_retention_wire_common_mm3"]
            <= float(gates["maximum_new_retention_wire_collision_mm3"])
        ),
        "new_retention_features_clear_lens": (
            context["new_retention_lens_common_mm3"]
            <= float(gates["maximum_new_retention_lens_collision_mm3"])
        ),
        "approved_v6_lens_geometry_is_unchanged": (
            context["v6_lens_symmetric_difference_mm3"]
            <= float(gates["maximum_v6_lens_symmetric_difference_mm3"])
        ),
        "approved_v6_aperture_coordinates_are_unchanged": (
            context["v6_aperture_maximum_shift_mm"]
            <= float(gates["maximum_v6_aperture_coordinate_shift_mm"])
        ),
        "rear_plate_pivots_open_without_unintended_collision": (
            context["rear_plate_pivot_maximum_unintended_common_mm3"]
            <= float(gates["maximum_pivot_unintended_collision_mm3"])
            and context["rear_plate_pivot_maximum_full_carrier_common_mm3"]
            <= float(gates["maximum_pivot_full_carrier_collision_mm3"])
            and context["rear_plate_pivot_final_rearward_motion_mm"]
            >= float(gates["minimum_pivot_screw_edge_rearward_motion_mm"])
        ),
        "rear_plate_hooks_disengage_on_bounded_inward_slide": (
            context["rear_plate_disengagement_maximum_common_mm3"]
            <= float(gates["maximum_hook_disengagement_slide_collision_mm3"])
            and context["rear_plate_disengagement_final_hook_clearance_mm"]
            >= float(gates["minimum_final_hook_disengagement_clearance_mm"])
        ),
        "carrier_with_rear_retention_is_one_valid_closed_solid": (
            bool(carrier.isValid()) and bool(carrier.isClosed()) and len(carrier.Solids) == 1
        ),
        "rear_plate_with_hooks_is_one_valid_closed_solid": (
            bool(plate.isValid()) and bool(plate.isClosed()) and len(plate.Solids) == 1
        ),
    })
    measurements.update({
        "rear_hook_edge_index": context["rear_hook_edge_index"],
        "rear_screw_edge_index": context["rear_screw_edge_index"],
        "rear_edge_wire_distances_mm": list(context["rear_edge_wire_distances_mm"]),
        "rear_hook_centers_world_mm": [vector_values(item) for item in context["rear_hook_centers"]],
        "rear_screw_centers_world_mm": [vector_values(item) for item in context["rear_screw_centers"]],
        "rear_hook_radial_engagement_mm": context["rear_hook_radial_engagement_mm"],
        "rear_hook_axial_clearance_mm": context["rear_hook_axial_clearance_mm"],
        "rear_hook_axial_clearance_error_mm": hook_gap_error,
        "rear_hook_ledge_seated_common_mm3": list(context["rear_hook_ledge_seated_common_mm3"]),
        "rear_hook_pullout_capture_mm3": list(context["rear_hook_pullout_capture_mm3"]),
        "rear_boss_material_around_pilot_mm": boss_material,
        "rear_boss_root_common_mm3": list(context["rear_boss_root_common_mm3"]),
        "rear_ledge_root_common_mm3": list(context["rear_ledge_root_common_mm3"]),
        "rear_locating_rim_root_common_mm3": context["rear_locating_rim_root_common_mm3"],
        "rear_locating_rim_distance_mm": context["rear_locating_rim_distance_mm"],
        "rear_locating_rim_gap_error_mm": rim_gap_error,
        "rear_plate_carrier_common_mm3": context["rear_plate_carrier_common_mm3"],
        "rear_plate_hole_residual_mm3": list(context["rear_plate_hole_residual_mm3"]),
        "rear_boss_pilot_residual_mm3": list(context["rear_boss_pilot_residual_mm3"]),
        "rear_screw_plate_common_mm3": list(context["rear_screw_plate_common_mm3"]),
        "rear_screw_thread_engagement_mm3": list(context["rear_screw_thread_engagement_mm3"]),
        "rear_screw_unintended_carrier_common_mm3": list(context["rear_screw_unintended_carrier_common_mm3"]),
        "rear_screw_alignment_errors_mm": list(context["rear_screw_alignment_errors_mm"]),
        "rear_screw_shell_common_mm3": context["rear_screw_shell_common_mm3"],
        "rear_screw_led_common_mm3": context["rear_screw_led_common_mm3"],
        "rear_screw_wire_common_mm3": context["rear_screw_wire_common_mm3"],
        "rear_screw_lens_common_mm3": context["rear_screw_lens_common_mm3"],
        "rear_screw_side_hardware_common_mm3": context["rear_screw_side_hardware_common_mm3"],
        "rear_driver_shell_common_mm3": context["rear_driver_shell_common_mm3"],
        "rear_driver_eye_common_mm3": context["rear_driver_eye_common_mm3"],
        "new_retention_shell_common_mm3": context["new_retention_shell_common_mm3"],
        "new_retention_led_common_mm3": context["new_retention_led_common_mm3"],
        "new_retention_wire_common_mm3": context["new_retention_wire_common_mm3"],
        "new_retention_lens_common_mm3": context["new_retention_lens_common_mm3"],
        "v6_lens_symmetric_difference_mm3": context["v6_lens_symmetric_difference_mm3"],
        "v6_aperture_maximum_shift_mm": context["v6_aperture_maximum_shift_mm"],
        "rear_plate_pivot_samples": list(context["rear_plate_pivot_records"]),
        "rear_plate_disengagement_samples": list(context["rear_plate_disengagement_records"]),
        "rear_plate_disengagement_final_hook_clearance_mm": context["rear_plate_disengagement_final_hook_clearance_mm"],
        "rear_plate_pivot_anchor_world_mm": vector_values(context["rear_plate_pivot_anchor"]),
        "rear_plate_pivot_axis_world": vector_values(context["rear_plate_pivot_axis"]),
        "rear_plate_retention_hardware": {
            "quantity": 2,
            "screw": "M2x6 pan-head",
            "plate_clearance_hole_mm": float(values["rear_plate_clearance_hole_diameter"]),
            "carrier_pilot_hole_mm": float(values["carrier_boss_pilot_diameter"]),
            "driver_corridor_diameter_mm": float(values["rear_driver_corridor_diameter"]),
            "service": "rear-accessible from inside head; two screws only, no nuts",
        },
    })
    failed = [key for key, value in checks.items() if not value]
    base["failed_checks"] = failed
    base["status"] = (
        "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED"
        if not failed
        else "FEASIBILITY_FAIL__NO_REVIEW_ARTIFACT"
    )
    return base


def prepare() -> dict[str, Any]:
    context = read_inputs()
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore
    context["v3_module"].load_context_shapes(context, App, Part)
    construct(context, App, Part)
    context["evaluation"] = evaluate(context)
    return context


def add_feature(
    context: dict[str, Any],
    doc: Any,
    name: str,
    label: str,
    shape: Any,
    color: tuple[float, float, float],
    transparency: int,
) -> Any:
    return context["v6_module"].add_feature(
        context, doc, name, label, shape, color, transparency
    )


def create_review(context: dict[str, Any], output: Path) -> Path:
    App = context["App"]
    doc = App.newDocument("RightEyeRearPlateHookTwoScrewRetentionReviewV7")
    try:
        add_feature(
            context,
            doc,
            "REFERENCE__RELIEVED_RIGHT_HEAD_SHELL",
            "REFERENCE — RELIEVED RIGHT HEAD SHELL",
            context["shell"],
            (0.70, 0.70, 0.73),
            78,
        )
        carrier = add_feature(
            context,
            doc,
            "PROPOSED__V7_EYE_CARRIER_WITH_REAR_RECEIVERS",
            "PROPOSED — V6 EYE CARRIER + REAR RIM, HOOK LEDGES, AND BOSSES",
            context["carrier"],
            (0.12, 0.72, 0.28),
            0,
        )
        carrier.addProperty("App::PropertyString", "RearRetention", "ReviewControl")
        carrier.RearRetention = "2 wire-side ledges + continuous locating rim + 2 opposite M2 pilot bosses"
        lens = add_feature(
            context,
            doc,
            "PROPOSED__V6_LENS_WITH_INTEGRAL_SIDE_FLANGES_UNCHANGED",
            "PROPOSED — APPROVED V6 LENS + FOUR INTEGRAL SIDE FLANGES (UNCHANGED)",
            context["lens"],
            (0.35, 0.86, 0.96),
            55,
        )
        lens.addProperty("App::PropertyString", "Retention", "ReviewControl")
        lens.Retention = "Unchanged 4x hidden sideways M2x4 screws through carrier walls"
        add_feature(
            context,
            doc,
            "REFERENCE__V6_HIDDEN_LENS_SIDE_SCREWS",
            "REFERENCE — FOUR APPROVED HIDDEN V6 LENS SCREWS",
            context["side_screw_references"],
            (0.82, 0.20, 0.08),
            15,
        )
        plate = add_feature(
            context,
            doc,
            "PROPOSED__V7_REMOVABLE_LED_REAR_PLATE",
            "PROPOSED — REMOVABLE LED PLATE WITH TWO INTEGRAL HOOKS",
            context["rear_cap"],
            (0.08, 0.34, 0.14),
            0,
        )
        plate.addProperty("App::PropertyString", "ServiceSequence", "ReviewControl")
        plate.ServiceSequence = "Remove 2 rear M2 screws; pivot screw edge rearward; disengage wire-side hooks"
        add_feature(
            context,
            doc,
            "REFERENCE__V7_REAR_PLATE_HOOKS",
            "REFERENCE — TWO PLATE-OWNED WIRE-SIDE HOOKS",
            context["rear_plate_hook_features"],
            (1.00, 0.72, 0.04),
            28,
        )
        add_feature(
            context,
            doc,
            "REFERENCE__V7_CARRIER_HOOK_LEDGES",
            "REFERENCE — TWO CARRIER-OWNED HOOK LEDGES",
            context["rear_hook_ledge_features"],
            (0.94, 0.18, 0.66),
            25,
        )
        add_feature(
            context,
            doc,
            "REFERENCE__V7_REAR_M2_BOSSES",
            "REFERENCE — TWO OPPOSITE CARRIER M2 PILOT BOSSES",
            context["rear_boss_features"],
            (0.65, 0.22, 0.92),
            25,
        )
        screws = add_feature(
            context,
            doc,
            "REFERENCE__V7_REAR_M2X6_SCREWS",
            "REFERENCE — TWO REAR-ACCESSIBLE M2×6 SCREWS",
            context["rear_screw_references"],
            (0.82, 0.20, 0.08),
            8,
        )
        screws.addProperty("App::PropertyString", "Hardware", "ReviewControl")
        screws.Hardware = "2x M2x6 pan-head; 2.2 mm plate clearance; 1.6 mm carrier pilot; no nuts"
        add_feature(
            context,
            doc,
            "REFERENCE__V7_REAR_DRIVER_CORRIDORS",
            "REFERENCE — TWO 5 MM REAR PH0 DRIVER CORRIDORS",
            context["rear_driver_corridors"],
            (0.88, 0.12, 0.12),
            78,
        )
        add_feature(
            context,
            doc,
            "REFERENCE__V7_CONTINUOUS_REAR_LIGHT_BLOCKING_SEAT",
            "REFERENCE — CONTINUOUS 0.05 MM REAR PLATE STOP / LIGHT BLOCK",
            context["rear_locating_rim"],
            (0.94, 0.48, 0.06),
            38,
        )
        for index, led in enumerate(context["led_shapes"], start=1):
            add_feature(
                context,
                doc,
                f"REFERENCE__LED_PIXEL_{index}",
                f"REFERENCE — LED PIXEL {index}",
                led,
                (1.0, 0.62, 0.05),
                12,
            )
        add_feature(
            context,
            doc,
            "REFERENCE__WIRE_EXIT_4MM",
            "REFERENCE — UNCHANGED 4 MM WIRE EXIT / ROUTE",
            context["wire_corridor"],
            (0.95, 0.18, 0.08),
            65,
        )
        exploded_plate = context["rear_cap"].copy()
        exploded_plate.translate(context["axis_n"] * 9.0)
        exploded_screws = context["rear_screw_references"].copy()
        exploded_screws.translate(context["axis_n"] * 9.0)
        exploded = add_feature(
            context,
            doc,
            "REVIEW__EXPLODED_REAR_PLATE_AND_SCREWS",
            "REVIEW — EXPLODED REAR PLATE + TWO SCREWS",
            context["Part"].makeCompound([exploded_plate, exploded_screws]),
            (0.20, 0.82, 0.48),
            25,
        )
        exploded.Authority = "EXPLODED_PRESENTATION_ONLY__NOT_ASSEMBLY_GEOMETRY"
        doc.recompute()
        path = output / context["contract"]["output"]["fcstd"]
        doc.saveAs(str(path))
        return path
    finally:
        App.closeDocument(doc.Name)


def render_views(context: dict[str, Any], output: Path) -> None:
    context["v6_module"].render_views(context, output)
    toolkit = context["toolkit"]
    v3 = context["v3_module"]
    shell = toolkit.shape_record(context["shell"], (150, 154, 160), deflection=1.0)
    carrier = toolkit.shape_record(context["carrier"], (36, 182, 72), deflection=0.26)
    plate = toolkit.shape_record(context["rear_cap"], (22, 94, 48), deflection=0.18)
    hooks = toolkit.shape_record(context["rear_plate_hook_features"], (255, 184, 12), deflection=0.10)
    ledges = toolkit.shape_record(context["rear_hook_ledge_features"], (238, 42, 168), deflection=0.10)
    bosses = toolkit.shape_record(context["rear_boss_features"], (164, 56, 232), deflection=0.10)
    screws = toolkit.shape_record(context["rear_screw_references"], (212, 50, 22), deflection=0.08)
    wire = toolkit.shape_record(context["wire_corridor"], (240, 40, 20), deflection=0.12)
    toolkit.render_side_by_side(
        output / "rear-plate-seated.png",
        [shell, carrier, plate, screws],
        [carrier, plate, hooks, ledges, bosses, screws, wire],
        v3.tuple3(context["axis_u"]),
        v3.tuple3(context["axis_v"]),
    )
    exploded_plate_shape = context["rear_cap"].copy()
    exploded_plate_shape.translate(context["axis_n"] * 9.0)
    exploded_screw_shape = context["rear_screw_references"].copy()
    exploded_screw_shape.translate(context["axis_n"] * 9.0)
    exploded_plate = toolkit.shape_record(exploded_plate_shape, (22, 160, 86), deflection=0.18)
    exploded_screws = toolkit.shape_record(exploded_screw_shape, (212, 50, 22), deflection=0.08)
    toolkit.render_side_by_side(
        output / "rear-plate-retention-exploded.png",
        [carrier, ledges, bosses, exploded_plate, exploded_screws],
        [plate, hooks, ledges, bosses, screws, wire],
        v3.tuple3(context["axis_u"]),
        v3.tuple3(context["axis_v"]),
    )


def public_report(context: dict[str, Any], mode: str, elapsed: float) -> dict[str, Any]:
    report = context["v6_module"].public_report(context, mode, elapsed)
    report["pins"]["approved_v6_contract_sha256"] = context["contract"]["inputs"]["v6_contract"]["sha256"]
    report["pins"]["approved_v6_generator_sha256"] = context["contract"]["inputs"]["v6_generator"]["sha256"]
    report["pins"]["contract_sha256"] = sha256_file(HERE / "contract.json")
    report["pins"]["generator_sha256"] = sha256_file(Path(__file__))
    report["authority"] = context["contract"]["authority"]
    report["review_id"] = context["contract"]["review_id"]
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("feasibility", "review"), required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--feasibility-report", type=Path)
    parser.add_argument("--feasibility-sha256")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    started = time.monotonic()
    context = prepare()
    report = public_report(context, "bounded_no_save_feasibility", time.monotonic() - started)
    if context["evaluation"]["status"] != "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED":
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1
    if args.mode == "feasibility":
        if args.report is None:
            raise RuntimeError("--report is required for feasibility")
        if args.report.exists():
            raise RuntimeError(f"feasibility report already exists: {args.report}")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(report["status"])
        return 0
    if args.feasibility_report is None or not args.feasibility_sha256:
        raise RuntimeError("review requires --feasibility-report and --feasibility-sha256")
    if sha256_file(args.feasibility_report) != args.feasibility_sha256:
        raise RuntimeError("feasibility report hash mismatch")
    output = context["root"] / context["contract"]["output"]["directory"]
    if output.exists():
        raise RuntimeError(f"review output already exists: {output}")
    output.mkdir(parents=True)
    fcstd = create_review(context, output)
    render_views(context, output)
    review_report = public_report(context, "single_review_artifact", time.monotonic() - started)
    review_report["review_fcstd"] = str(fcstd.relative_to(context["root"]))
    review_report["review_fcstd_sha256"] = sha256_file(fcstd)
    review_report["feasibility_report_sha256"] = args.feasibility_sha256
    validation = output / context["contract"]["output"]["validation"]
    validation.write_text(json.dumps(review_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(review_report["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
