#!/usr/bin/env python3
"""Build the corrected review-only V6 lens-retention arrangement.

The approved V4 carrier geometry is retained.  Four flanges are fused to the
translucent lens and extend rearward inside the cassette.  Four M2 screws enter
radially through the opaque cassette walls, so no fastener is visible from the
front.  V5 is deliberately not imported or reused.
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


def load_v4(root: Path, contract: dict[str, Any]) -> Any:
    for key, pin in contract["inputs"].items():
        path = root / str(pin["path"])
        actual = sha256_file(path)
        if actual != str(pin["sha256"]):
            raise RuntimeError(
                f"{key}: pin mismatch {actual} != {pin['sha256']}"
            )
    path = root / str(contract["inputs"]["v4_generator"]["path"])
    spec = importlib.util.spec_from_file_location(
        "_pinned_approved_eye_review_v4", path
    )
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
    v4 = load_v4(root, contract)
    context = v4.read_inputs()
    context["v4_contract"] = context["contract"]
    context["contract"] = contract
    context["v4_module"] = v4
    return context


def run_v4_construct(
    context: dict[str, Any], App: Any, Part: Any
) -> None:
    active = context["contract"]
    context["contract"] = context["v4_contract"]
    try:
        context["v4_module"].construct(context, App, Part)
    finally:
        context["contract"] = active


def run_v4_evaluate(context: dict[str, Any]) -> dict[str, Any]:
    active = context["contract"]
    context["contract"] = context["v4_contract"]
    try:
        return context["v4_module"].evaluate(context)
    finally:
        context["contract"] = active


def construct(context: dict[str, Any], App: Any, Part: Any) -> None:
    run_v4_construct(context, App, Part)
    v3 = context["v3_module"]
    toolkit = context["toolkit"]
    values = context["contract"]["dimensions_mm"]
    axis_n = context["axis_n"]
    box_outer = context["box_outer"]
    box_inner = context["box_inner"]
    v4_carrier = context["carrier"].copy()
    v4_lens = context["lens"].copy()
    v4_aperture = [copy_vector(App, item) for item in context["aperture"]]
    lens_back = float(context["lens_back_depth_mm"])

    flange_width = float(values["lens_integral_flange_width"])
    flange_depth = float(values["lens_integral_flange_radial_depth"])
    wall_clearance = float(
        values["lens_integral_flange_wall_clearance"]
    )
    rear_length = float(values["lens_integral_flange_rear_length"])
    front_overlap = float(
        values["lens_integral_flange_front_overlap"]
    )
    pilot_offset = float(
        values["lens_integral_flange_pilot_rear_offset"]
    )
    pilot_radius = (
        float(values["lens_integral_flange_pilot_diameter"]) / 2.0
    )
    clearance_radius = (
        float(values["carrier_side_clearance_hole_diameter"]) / 2.0
    )
    head_recess_radius = (
        float(values["carrier_side_head_recess_diameter"]) / 2.0
    )
    head_recess_depth = float(
        values["carrier_side_head_recess_depth"]
    )
    screw_radius = float(values["screw_nominal_diameter"]) / 2.0
    screw_length = float(values["screw_length"])
    head_radius = float(values["screw_head_diameter"]) / 2.0
    head_height = float(values["screw_head_height"])
    pilot_depth = lens_back + pilot_offset

    flange_raw_solids = []
    flange_display_solids = []
    carrier_cutters = []
    carrier_head_recess_cutters = []
    lens_pilot_cutters = []
    screw_solids = []
    screw_shaft_solids = []
    screw_head_solids = []
    screw_axis_markers = []
    screw_axes = []
    screw_centers = []
    flange_attachment_common = []
    wall_spans = []
    box_center = toolkit.average(App, box_inner)

    for index in range(len(box_inner)):
        inner_start = box_inner[index]
        inner_end = box_inner[(index + 1) % len(box_inner)]
        outer_start = box_outer[index]
        outer_end = box_outer[(index + 1) % len(box_outer)]
        tangent = inner_end - inner_start
        if float(tangent.Length) <= flange_width + 1.0:
            raise RuntimeError(
                f"box wall {index} is too short for a lens flange"
            )
        tangent.normalize()
        inner_mid = (inner_start + inner_end) * 0.5
        outer_mid = (outer_start + outer_end) * 0.5
        inward = axis_n.cross(tangent)
        if float(inward.Length) <= 1.0e-9:
            raise RuntimeError(
                f"cannot derive radial screw axis for wall {index}"
            )
        inward.normalize()
        if float((box_center - inner_mid).dot(inward)) < 0.0:
            inward = inward * -1.0
        wall_span = float((inner_mid - outer_mid).dot(inward))
        if wall_span <= 0.0:
            raise RuntimeError(
                f"wall {index} has a non-positive normal thickness"
            )
        outer_axis_point = inner_mid - inward * wall_span
        half_width = flange_width / 2.0
        flange_outer = inner_mid + inward * wall_clearance
        flange_loop = [
            flange_outer - tangent * half_width,
            flange_outer + tangent * half_width,
            flange_outer + tangent * half_width + inward * flange_depth,
            flange_outer - tangent * half_width + inward * flange_depth,
        ]
        flange = toolkit.polygon_face(
            Part,
            toolkit.at_depth(
                flange_loop, lens_back - front_overlap, axis_n
            ),
        ).extrude(
            axis_n * (rear_length + front_overlap)
        ).removeSplitter()
        flange_raw_solids.append(flange)
        flange_attachment_common.append(
            v3.common_volume(v4_lens, flange)
        )

        carrier_cutter = Part.makeCylinder(
            clearance_radius,
            wall_span + wall_clearance + 0.20,
            outer_axis_point
            - inward * 0.10
            + axis_n * pilot_depth,
            inward,
        )
        pilot_cutter = Part.makeCylinder(
            pilot_radius,
            flange_depth + 0.10,
            flange_outer
            - inward * 0.05
            + axis_n * pilot_depth,
            inward,
        )
        head_recess_cutter = Part.makeCylinder(
            head_recess_radius,
            head_recess_depth + 0.10,
            outer_axis_point
            - inward * 0.05
            + axis_n * pilot_depth,
            inward,
        )
        shaft_start = (
            outer_axis_point
            + inward * head_recess_depth
            + axis_n * pilot_depth
        )
        shaft = Part.makeCylinder(
            screw_radius, screw_length, shaft_start, inward
        )
        head = Part.makeCylinder(
            head_radius,
            head_height,
            outer_axis_point
            + inward * (head_recess_depth - head_height)
            + axis_n * pilot_depth,
            inward,
        )
        screw = head.fuse(shaft).removeSplitter()
        marker = Part.makeCylinder(
            0.12,
            screw_length + head_height,
            outer_axis_point
            + inward * (head_recess_depth - head_height)
            + axis_n * pilot_depth,
            inward,
        )

        carrier_cutters.append(carrier_cutter)
        carrier_head_recess_cutters.append(head_recess_cutter)
        lens_pilot_cutters.append(pilot_cutter)
        screw_solids.append(screw)
        screw_shaft_solids.append(shaft)
        screw_head_solids.append(head)
        screw_axis_markers.append(marker)
        screw_axes.append(copy_vector(App, inward))
        screw_centers.append(
            flange_outer + axis_n * pilot_depth
        )
        wall_spans.append(wall_span)

    predrill_lens = toolkit.fuse_shapes(
        [v4_lens, *flange_raw_solids],
        "V6 translucent lens with four integral rearward flanges",
    ).removeSplitter()
    lens = predrill_lens
    lens_pilot_removed = []
    for flange, cutter in zip(flange_raw_solids, lens_pilot_cutters):
        lens_pilot_removed.append(v3.common_volume(lens, cutter))
        flange_display_solids.append(
            flange.cut(cutter).removeSplitter()
        )
        lens = lens.cut(cutter).removeSplitter()
    toolkit.require_single_solid(
        lens, "V6 lens with integral side-screw flanges"
    )

    carrier = v4_carrier
    carrier_hole_removed = []
    carrier_head_recess_removed = []
    carrier_stepped_cutters = []
    for hole, recess in zip(
        carrier_cutters, carrier_head_recess_cutters
    ):
        carrier_hole_removed.append(
            v3.common_volume(v4_carrier, hole)
        )
        carrier_head_recess_removed.append(
            v3.common_volume(v4_carrier, recess)
        )
        stepped = hole.fuse(recess).removeSplitter()
        carrier_stepped_cutters.append(stepped)
        carrier = carrier.cut(stepped).removeSplitter()
    toolkit.require_single_solid(
        carrier, "V6 carrier with four radial side holes"
    )

    carrier_hole_residual = [
        v3.common_volume(carrier, cutter)
        for cutter in carrier_cutters
    ]
    carrier_head_recess_residual = [
        v3.common_volume(carrier, cutter)
        for cutter in carrier_head_recess_cutters
    ]
    lens_pilot_residual = [
        v3.common_volume(lens, cutter)
        for cutter in lens_pilot_cutters
    ]
    carrier_alignment_errors = []
    for axis, carrier_cutter, lens_cutter in zip(
        screw_axes, carrier_cutters, lens_pilot_cutters
    ):
        delta = carrier_cutter.CenterOfMass - lens_cutter.CenterOfMass
        lateral = delta - axis * float(delta.dot(axis))
        carrier_alignment_errors.append(float(lateral.Length))

    screw_carrier_common = sum(
        v3.common_volume(screw, carrier)
        for screw in screw_solids
    )
    screw_head_carrier_common = [
        v3.common_volume(head, carrier)
        for head in screw_head_solids
    ]
    screw_shaft_carrier_common = [
        v3.common_volume(shaft, carrier)
        for shaft in screw_shaft_solids
    ]
    screw_shell_common = 0.0
    for screw in screw_solids:
        for _, owner in context["shell_records"]:
            if v3.aabb_near(screw, owner, 0.5):
                screw_shell_common += v3.common_volume(screw, owner)
    screw_led_common = sum(
        v3.common_volume(screw, led)
        for screw in screw_solids
        for led in context["led_shapes"]
    )
    screw_rear_common = sum(
        v3.common_volume(screw, context["rear_cap"])
        for screw in screw_solids
    )
    visible_cavity = toolkit.polygon_face(
        Part,
        toolkit.at_depth(
            box_inner,
            float(values["carrier_front_depth"]),
            axis_n,
        ),
    ).extrude(
        axis_n
        * (
            float(values["box_wall_rear_depth"])
            - float(values["carrier_front_depth"])
        )
    ).removeSplitter()
    visible_head_common = sum(
        v3.common_volume(head, visible_cavity)
        for head in screw_head_solids
    )

    flange_insertion_records = []
    flange_insertion_maximum_common = 0.0
    flange_features = Part.makeCompound(flange_display_solids)
    for offset in (-6.0, -5.0, -4.0, -3.0, -2.0, -1.0, -0.5, -0.25, 0.0):
        moved = flange_features.copy()
        moved.translate(axis_n * offset)
        common = v3.common_volume(moved, carrier)
        flange_insertion_records.append({
            "front_normal_offset_mm": offset,
            "carrier_common_mm3": common,
        })
        flange_insertion_maximum_common = max(
            flange_insertion_maximum_common, common
        )

    context.update({
        "v4_carrier_reference": v4_carrier,
        "v4_lens_reference": v4_lens,
        "v4_aperture_reference": v4_aperture,
        "carrier": carrier,
        "lens": lens,
        "lens_integral_flange_raw_solids": flange_raw_solids,
        "lens_integral_flange_display_solids": flange_display_solids,
        "lens_integral_flange_features": flange_features,
        "carrier_side_hole_cutters": carrier_cutters,
        "carrier_side_head_recess_cutters": carrier_head_recess_cutters,
        "carrier_side_stepped_cutters": carrier_stepped_cutters,
        "lens_flange_pilot_cutters": lens_pilot_cutters,
        "side_screw_reference_solids": screw_solids,
        "side_screw_shaft_solids": screw_shaft_solids,
        "side_screw_references": Part.makeCompound(screw_solids),
        "side_screw_head_solids": screw_head_solids,
        "side_screw_axes": screw_axes,
        "side_screw_axis_markers": Part.makeCompound(
            screw_axis_markers
        ),
        "side_screw_centers": screw_centers,
        "lens_flange_attachment_common_mm3": flange_attachment_common,
        "carrier_side_hole_removed_mm3": carrier_hole_removed,
        "carrier_side_hole_residual_mm3": carrier_hole_residual,
        "carrier_side_head_recess_removed_mm3": (
            carrier_head_recess_removed
        ),
        "carrier_side_head_recess_residual_mm3": (
            carrier_head_recess_residual
        ),
        "lens_flange_pilot_removed_mm3": lens_pilot_removed,
        "lens_flange_pilot_residual_mm3": lens_pilot_residual,
        "side_hole_alignment_errors_mm": carrier_alignment_errors,
        "side_screw_carrier_collision_mm3": screw_carrier_common,
        "side_screw_head_carrier_collision_mm3": (
            screw_head_carrier_common
        ),
        "side_screw_shaft_carrier_collision_mm3": (
            screw_shaft_carrier_common
        ),
        "side_screw_shell_collision_mm3": screw_shell_common,
        "side_screw_led_collision_mm3": screw_led_common,
        "side_screw_rear_plate_collision_mm3": screw_rear_common,
        "side_screw_visible_cavity_collision_mm3": visible_head_common,
        "visible_cavity_reference": visible_cavity,
        "lens_flange_insertion_records": flange_insertion_records,
        "lens_flange_insertion_maximum_collision_mm3": (
            flange_insertion_maximum_common
        ),
        "carrier_wall_spans_mm": wall_spans,
    })


def evaluate(context: dict[str, Any]) -> dict[str, Any]:
    base = run_v4_evaluate(context)
    checks = base["checks"]
    measurements = base["measurements"]
    values = context["contract"]["dimensions_mm"]
    gates = context["contract"]["gates"]
    count = len(context["lens_integral_flange_raw_solids"])
    pilot_radius = (
        float(values["lens_integral_flange_pilot_diameter"]) / 2.0
    )
    tangential_margin = (
        float(values["lens_integral_flange_width"]) / 2.0
        - pilot_radius
    )
    axial_front_margin = (
        float(values["lens_integral_flange_pilot_rear_offset"])
        + float(values["lens_integral_flange_front_overlap"])
        - pilot_radius
    )
    axial_rear_margin = (
        float(values["lens_integral_flange_rear_length"])
        - float(values["lens_integral_flange_pilot_rear_offset"])
        - pilot_radius
    )
    material_margins = [
        tangential_margin, axial_front_margin, axial_rear_margin
    ]
    minimum_material = min(material_margins)
    normal_dots = [
        abs(float(axis.dot(context["axis_n"])))
        for axis in context["side_screw_axes"]
    ]
    aperture_shift = max(
        float((current - reference).Length)
        for current, reference in zip(
            context["aperture"], context["v4_aperture_reference"]
        )
    )
    carrier = context["carrier"]
    lens = context["lens"]
    checks.update({
        "four_integral_lens_flange_features_present": (
            count
            == int(gates["required_lens_integral_flange_count"])
        ),
        "four_radial_carrier_side_holes_present": (
            len(context["carrier_side_hole_cutters"])
            == int(gates["required_carrier_side_hole_count"])
        ),
        "lens_flange_features_are_integrally_attached": (
            len(context["lens_flange_attachment_common_mm3"]) == count
            and min(context["lens_flange_attachment_common_mm3"])
            >= float(gates["minimum_flange_attachment_common_mm3"])
        ),
        "lens_flange_material_around_pilots_is_printable": (
            minimum_material
            >= float(gates["minimum_flange_material_around_pilot_mm"])
        ),
        "carrier_side_clearance_holes_are_open": (
            len(context["carrier_side_hole_residual_mm3"]) == count
            and max(context["carrier_side_hole_residual_mm3"])
            <= float(gates["maximum_carrier_hole_residual_mm3"])
        ),
        "carrier_side_head_recesses_are_open": (
            len(context["carrier_side_head_recess_residual_mm3"]) == count
            and max(context["carrier_side_head_recess_residual_mm3"])
            <= float(
                gates["maximum_carrier_head_recess_residual_mm3"]
            )
        ),
        "carrier_wall_behind_head_recess_is_structural": (
            min(context["carrier_wall_spans_mm"])
            - float(values["carrier_side_head_recess_depth"])
            >= float(gates["minimum_wall_behind_head_recess_mm"])
        ),
        "lens_flange_pilot_holes_are_open": (
            len(context["lens_flange_pilot_residual_mm3"]) == count
            and max(context["lens_flange_pilot_residual_mm3"])
            <= float(gates["maximum_lens_pilot_residual_mm3"])
        ),
        "carrier_and_lens_side_hole_axes_align": (
            max(context["side_hole_alignment_errors_mm"])
            <= float(gates["maximum_side_axis_alignment_error_mm"])
        ),
        "screw_axes_are_parallel_to_eye_front_plane": (
            max(normal_dots)
            <= float(gates["maximum_screw_axis_front_normal_dot"])
        ),
        "reference_side_screws_clear_carrier_after_drilling": (
            float(context["side_screw_carrier_collision_mm3"])
            <= float(
                gates["maximum_reference_screw_carrier_collision_mm3"]
            )
        ),
        "reference_side_screws_clear_head_shell": (
            float(context["side_screw_shell_collision_mm3"])
            <= float(gates["maximum_reference_screw_shell_collision_mm3"])
        ),
        "reference_side_screws_clear_led_pixels": (
            float(context["side_screw_led_collision_mm3"])
            <= float(gates["maximum_reference_screw_led_collision_mm3"])
        ),
        "reference_side_screws_clear_rear_plate": (
            float(context["side_screw_rear_plate_collision_mm3"])
            <= float(
                gates["maximum_reference_screw_rear_plate_collision_mm3"]
            )
        ),
        "screw_heads_are_outside_visible_aperture_cavity": (
            float(context["side_screw_visible_cavity_collision_mm3"])
            <= float(gates["maximum_visible_aperture_head_collision_mm3"])
        ),
        "lens_integral_flanges_enter_box_without_wall_collision": (
            float(
                context["lens_flange_insertion_maximum_collision_mm3"]
            )
            <= float(
                gates["maximum_lens_flange_insertion_collision_mm3"]
            )
        ),
        "approved_v4_aperture_coordinates_unchanged": (
            aperture_shift
            <= float(gates["maximum_aperture_coordinate_shift_mm"])
        ),
        "carrier_remains_one_valid_closed_solid": (
            bool(carrier.isValid())
            and bool(carrier.isClosed())
            and len(carrier.Solids) == 1
        ),
        "lens_and_integral_flanges_are_one_valid_closed_solid": (
            bool(lens.isValid())
            and bool(lens.isClosed())
            and len(lens.Solids) == 1
        ),
    })
    measurements.update({
        "lens_integral_flange_count": count,
        "lens_integral_flange_attachment_common_mm3": list(
            context["lens_flange_attachment_common_mm3"]
        ),
        "lens_integral_flange_material_margins_mm": material_margins,
        "minimum_lens_integral_flange_material_mm": minimum_material,
        "carrier_wall_spans_mm": list(context["carrier_wall_spans_mm"]),
        "carrier_side_hole_removed_mm3": list(
            context["carrier_side_hole_removed_mm3"]
        ),
        "carrier_side_hole_residual_mm3": list(
            context["carrier_side_hole_residual_mm3"]
        ),
        "carrier_side_head_recess_removed_mm3": list(
            context["carrier_side_head_recess_removed_mm3"]
        ),
        "carrier_side_head_recess_residual_mm3": list(
            context["carrier_side_head_recess_residual_mm3"]
        ),
        "minimum_wall_behind_head_recess_mm": (
            min(context["carrier_wall_spans_mm"])
            - float(values["carrier_side_head_recess_depth"])
        ),
        "lens_flange_pilot_removed_mm3": list(
            context["lens_flange_pilot_removed_mm3"]
        ),
        "lens_flange_pilot_residual_mm3": list(
            context["lens_flange_pilot_residual_mm3"]
        ),
        "side_hole_alignment_errors_mm": list(
            context["side_hole_alignment_errors_mm"]
        ),
        "side_screw_axis_front_normal_dots": normal_dots,
        "side_screw_centers_world_mm": [
            vector_values(point)
            for point in context["side_screw_centers"]
        ],
        "side_screw_carrier_collision_mm3": float(
            context["side_screw_carrier_collision_mm3"]
        ),
        "side_screw_head_carrier_collision_mm3": list(
            context["side_screw_head_carrier_collision_mm3"]
        ),
        "side_screw_shaft_carrier_collision_mm3": list(
            context["side_screw_shaft_carrier_collision_mm3"]
        ),
        "side_screw_shell_collision_mm3": float(
            context["side_screw_shell_collision_mm3"]
        ),
        "side_screw_led_collision_mm3": float(
            context["side_screw_led_collision_mm3"]
        ),
        "side_screw_rear_plate_collision_mm3": float(
            context["side_screw_rear_plate_collision_mm3"]
        ),
        "side_screw_visible_cavity_collision_mm3": float(
            context["side_screw_visible_cavity_collision_mm3"]
        ),
        "lens_flange_insertion_samples": list(
            context["lens_flange_insertion_records"]
        ),
        "lens_flange_insertion_maximum_collision_mm3": float(
            context["lens_flange_insertion_maximum_collision_mm3"]
        ),
        "v4_aperture_maximum_coordinate_shift_mm": aperture_shift,
        "lens_side_fastener_specification": {
            "quantity": count,
            "screw": "M2x4 pan-head",
            "carrier_clearance_diameter_mm": float(
                values["carrier_side_clearance_hole_diameter"]
            ),
            "lens_flange_pilot_diameter_mm": float(
                values["lens_integral_flange_pilot_diameter"]
            ),
            "installation": (
                "sideways from inside head through opaque carrier walls"
            ),
        },
    })
    failed = [key for key, value in checks.items() if not value]
    base["failed_checks"] = failed
    base["status"] = (
        "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED"
        if not failed else "FEASIBILITY_FAIL__NO_REVIEW_ARTIFACT"
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
    return context["v4_module"].add_feature(
        context, doc, name, label, shape, color, transparency
    )


def create_review(context: dict[str, Any], output: Path) -> Path:
    App = context["App"]
    doc = App.newDocument("RightEyeLensIntegralSideScrewFlangesReviewV6")
    try:
        add_feature(
            context, doc, "REFERENCE__RELIEVED_RIGHT_HEAD_SHELL",
            "REFERENCE — RELIEVED RIGHT HEAD SHELL",
            context["shell"], (0.70, 0.70, 0.73), 78,
        )
        carrier = add_feature(
            context, doc, "PROPOSED__V6_OPAQUE_EYE_CARRIER",
            "PROPOSED — V4 OPAQUE CARRIER WITH FOUR SIDE HOLES",
            context["carrier"], (0.12, 0.72, 0.28), 0,
        )
        carrier.addProperty(
            "App::PropertyString", "Installation", "ReviewControl"
        )
        carrier.Installation = (
            "Carrier through eye opening; lens seats from front; "
            "M2 screws enter sideways from inside head"
        )
        lens = add_feature(
            context, doc, "PROPOSED__V6_LENS_WITH_INTEGRAL_FLANGES",
            "PROPOSED — 0.90 MM LENS + FOUR INTEGRAL REAR FLANGES",
            context["lens"], (0.35, 0.86, 0.96), 55,
        )
        lens.addProperty(
            "App::PropertyString", "Retention", "ReviewControl"
        )
        lens.Retention = (
            "4x M2x4 screws through opaque side walls into lens-owned "
            "1.60 mm radial pilots; no front-visible fasteners"
        )
        add_feature(
            context, doc, "REFERENCE__LENS_INTEGRAL_FLANGES",
            "REFERENCE — FOUR LENS-OWNED REARWARD FLANGES",
            context["lens_integral_flange_features"],
            (1.00, 0.78, 0.05), 38,
        )
        screws = add_feature(
            context, doc, "REFERENCE__HIDDEN_M2X4_SIDE_SCREWS",
            "REFERENCE — FOUR HIDDEN SIDEWAYS M2×4 SCREWS",
            context["side_screw_references"],
            (0.82, 0.20, 0.08), 12,
        )
        screws.addProperty(
            "App::PropertyString", "Hardware", "ReviewControl"
        )
        screws.Hardware = (
            "4x M2x4 pan-head; heads behind front plane and outside "
            "visible cavity; hand-tighten"
        )
        add_feature(
            context, doc, "REFERENCE__SIDE_SCREW_AXES",
            "REFERENCE — FOUR RADIAL SIDE-SCREW AXES",
            context["side_screw_axis_markers"],
            (0.82, 0.12, 0.88), 0,
        )
        cap = add_feature(
            context, doc, "PROPOSED__REMOVABLE_LED_REAR_PLATE",
            "PROPOSED — REMOVABLE LED REAR PLATE",
            context["rear_cap"], (0.08, 0.34, 0.14), 0,
        )
        cap.addProperty(
            "App::PropertyString", "WirePort", "ReviewControl"
        )
        cap.WirePort = (
            "4.0 mm through-hole; seal and strain-relieve cable"
        )
        for index, led in enumerate(context["led_shapes"], start=1):
            add_feature(
                context, doc, f"REFERENCE__LED_PIXEL_{index}",
                f"REFERENCE — LED PIXEL {index}",
                led, (1.0, 0.62, 0.05), 12,
            )
        add_feature(
            context, doc, "REFERENCE__WIRE_EXIT_4MM",
            "REFERENCE — 4 MM WIRE EXIT / ROUTE",
            context["wire_corridor"], (0.95, 0.18, 0.08), 65,
        )
        add_feature(
            context, doc, "REFERENCE__CONTINUOUS_LENS_SEAT",
            "REFERENCE — CONTINUOUS REAR LENS SEAT",
            context["lens_seat"], (0.95, 0.48, 0.08), 50,
        )
        doc.recompute()
        path = output / context["contract"]["output"]["fcstd"]
        doc.saveAs(str(path))
        return path
    finally:
        App.closeDocument(doc.Name)


def render_views(context: dict[str, Any], output: Path) -> None:
    context["v4_module"].render_views(context, output)
    toolkit = context["toolkit"]
    v3 = context["v3_module"]
    shell = toolkit.shape_record(
        context["shell"], (150, 154, 160), deflection=1.0
    )
    carrier = toolkit.shape_record(
        context["carrier"], (36, 182, 72), deflection=0.30
    )
    lens = toolkit.shape_record(
        context["lens"], (80, 218, 242), deflection=0.18
    )
    flanges = toolkit.shape_record(
        context["lens_integral_flange_features"],
        (255, 198, 15), deflection=0.14,
    )
    screws = toolkit.shape_record(
        context["side_screw_references"],
        (210, 52, 20), deflection=0.10,
    )
    exploded_lens_shape = context["lens"].copy()
    exploded_lens_shape.translate(context["axis_n"] * -7.0)
    exploded_screw_shape = context["side_screw_references"].copy()
    exploded_screw_shape.translate(context["axis_n"] * -7.0)
    exploded_lens = toolkit.shape_record(
        exploded_lens_shape, (80, 218, 242), deflection=0.18
    )
    exploded_screws = toolkit.shape_record(
        exploded_screw_shape, (210, 52, 20), deflection=0.10
    )
    toolkit.render_side_by_side(
        output / "lens-side-fasteners.png",
        [shell, carrier, lens, screws],
        [carrier, flanges, exploded_lens, exploded_screws],
        v3.tuple3(context["axis_u"]),
        v3.tuple3(context["axis_v"]),
    )


def public_report(
    context: dict[str, Any], mode: str, elapsed: float
) -> dict[str, Any]:
    report = context["v4_module"].public_report(context, mode, elapsed)
    report["pins"]["contract_sha256"] = sha256_file(HERE / "contract.json")
    report["pins"]["generator_sha256"] = sha256_file(Path(__file__))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode", choices=("feasibility", "review"), required=True
    )
    parser.add_argument("--report", type=Path)
    parser.add_argument("--feasibility-report", type=Path)
    parser.add_argument("--feasibility-sha256")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    started = time.monotonic()
    context = prepare()
    report = public_report(
        context,
        "bounded_no_save_feasibility",
        time.monotonic() - started,
    )
    if context["evaluation"]["status"] != (
        "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED"
    ):
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1
    if args.mode == "feasibility":
        if args.report is None:
            raise RuntimeError("--report is required for feasibility")
        if args.report.exists():
            raise RuntimeError(
                f"feasibility report already exists: {args.report}"
            )
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(report["status"])
        return 0
    if args.feasibility_report is None or not args.feasibility_sha256:
        raise RuntimeError(
            "review requires --feasibility-report and --feasibility-sha256"
        )
    if sha256_file(args.feasibility_report) != args.feasibility_sha256:
        raise RuntimeError("feasibility report hash mismatch")
    output = context["root"] / context["contract"]["output"]["directory"]
    if output.exists():
        raise RuntimeError(f"review output already exists: {output}")
    output.mkdir(parents=True)
    fcstd = create_review(context, output)
    render_views(context, output)
    review_report = public_report(
        context, "single_review_artifact", time.monotonic() - started
    )
    review_report["review_fcstd"] = str(
        fcstd.relative_to(context["root"])
    )
    review_report["review_fcstd_sha256"] = sha256_file(fcstd)
    review_report["feasibility_report_sha256"] = (
        args.feasibility_sha256
    )
    validation = output / context["contract"]["output"]["validation"]
    validation.write_text(
        json.dumps(review_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(review_report["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
