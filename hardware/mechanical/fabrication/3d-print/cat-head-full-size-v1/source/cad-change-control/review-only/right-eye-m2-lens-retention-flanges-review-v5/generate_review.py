#!/usr/bin/env python3
"""Add four inward-facing M2 lens-retention tabs to approved review V4.

The V4 aperture, fitted face, perpendicular cassette walls, LED references,
rear plate, and read-only head context remain unchanged.  This is review-only
tooling and has no production/export path.
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
    for key, spec in contract["inputs"].items():
        path = root / str(spec["path"])
        actual = sha256_file(path)
        if actual != str(spec["sha256"]):
            raise RuntimeError(f"{key}: pin mismatch {actual} != {spec['sha256']}")
    path = root / str(contract["inputs"]["v4_review_generator"]["path"])
    spec = importlib.util.spec_from_file_location("_pinned_eye_review_v4", path)
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


def construct(context: dict[str, Any], App: Any, Part: Any) -> None:
    v4 = context["v4_module"]
    v3 = context["v3_module"]
    v4.construct(context, App, Part)
    toolkit = context["toolkit"]
    values = context["contract"]["dimensions_mm"]
    axis_n = context["axis_n"]
    box_inner = context["box_inner"]
    aperture = context["aperture"]
    v4_carrier = context["carrier"].copy()
    v4_lens = context["lens"].copy()
    v4_aperture = [copy_vector(App, point) for point in aperture]
    lens_front = float(values["lens_surround_front_depth"])
    lens_thickness = float(values["lens_thickness"])
    lens_back = lens_front + lens_thickness
    tab_width = float(values["lens_retention_tab_width"])
    tab_projection = float(values["lens_retention_tab_inward_projection"])
    wall_overlap = float(values["lens_retention_tab_wall_overlap"])
    tab_axial = float(values["lens_retention_tab_axial_thickness"])
    hole_projection = float(
        values["lens_retention_hole_center_inward_projection"]
    )
    pilot_radius = float(values["lens_retention_pilot_diameter"]) / 2.0
    clearance_radius = float(values["lens_clearance_hole_diameter"]) / 2.0
    screw_radius = float(values["lens_screw_nominal_diameter"]) / 2.0
    screw_length = float(values["lens_screw_length"])
    head_radius = float(values["lens_screw_head_diameter"]) / 2.0
    head_height = float(values["lens_screw_head_height"])
    center = toolkit.average(App, box_inner)
    tab_solids = []
    tab_footprints = []
    pilot_cutters = []
    lens_cutters = []
    screw_references = []
    hole_centers = []
    attachment_common = []
    for index in range(len(box_inner)):
        start = box_inner[index]
        end = box_inner[(index + 1) % len(box_inner)]
        tangent = end - start
        if float(tangent.Length) <= tab_width + 1.0:
            raise RuntimeError(f"box wall {index} is too short for an M2 tab")
        tangent.normalize()
        midpoint = (start + end) * 0.5
        inward = center - midpoint
        inward = inward - axis_n * float(inward.dot(axis_n))
        if float(inward.Length) <= 1.0e-9:
            raise RuntimeError(f"cannot derive inward direction for tab {index}")
        inward.normalize()
        half_width = tab_width / 2.0
        tab_loop = [
            midpoint - tangent * half_width - inward * wall_overlap,
            midpoint + tangent * half_width - inward * wall_overlap,
            midpoint + tangent * half_width + inward * tab_projection,
            midpoint - tangent * half_width + inward * tab_projection,
        ]
        footprint = toolkit.polygon_face(Part, tab_loop)
        tab = toolkit.polygon_face(
            Part, toolkit.at_depth(tab_loop, lens_back, axis_n)
        ).extrude(axis_n * tab_axial).removeSplitter()
        hole_planar = midpoint + inward * hole_projection
        hole_center = hole_planar + axis_n * lens_back
        pilot = Part.makeCylinder(
            pilot_radius,
            tab_axial + 0.10,
            hole_center - axis_n * 0.05,
            axis_n,
        )
        lens_cutter = Part.makeCylinder(
            clearance_radius,
            lens_thickness + 0.10,
            hole_planar + axis_n * (lens_front - 0.05),
            axis_n,
        )
        shaft = Part.makeCylinder(
            screw_radius,
            screw_length,
            hole_planar + axis_n * lens_front,
            axis_n,
        )
        head = Part.makeCylinder(
            head_radius,
            head_height,
            hole_planar + axis_n * (lens_front - head_height),
            axis_n,
        )
        screw = head.fuse(shaft).removeSplitter()
        tab_solids.append(tab)
        tab_footprints.append(footprint)
        pilot_cutters.append(pilot)
        lens_cutters.append(lens_cutter)
        screw_references.append(screw)
        hole_centers.append(hole_planar)
        attachment_common.append(v3.common_volume(v4_carrier, tab))
    predrill_carrier = toolkit.fuse_shapes(
        [v4_carrier, *tab_solids],
        "V5 carrier with four inward lens-retention tabs",
    ).removeSplitter()
    pilot_removed = []
    carrier = predrill_carrier
    for cutter in pilot_cutters:
        pilot_removed.append(v3.common_volume(carrier, cutter))
        carrier = carrier.cut(cutter).removeSplitter()
    toolkit.require_single_solid(carrier, "V5 M2 lens-retention carrier")
    lens = v4_lens
    lens_removed = []
    for cutter in lens_cutters:
        lens_removed.append(v3.common_volume(lens, cutter))
        lens = lens.cut(cutter).removeSplitter()
    toolkit.require_single_solid(lens, "V5 four-hole translucent lens")
    aperture_face = toolkit.polygon_face(Part, aperture)
    projected_area = sum(
        float(footprint.common(aperture_face).Area)
        for footprint in tab_footprints
    )
    pilot_residual = [
        v3.common_volume(carrier, cutter) for cutter in pilot_cutters
    ]
    lens_hole_residual = [
        v3.common_volume(lens, cutter) for cutter in lens_cutters
    ]
    expected_lens_removed = (
        len(lens_cutters)
        * math.pi
        * clearance_radius
        * clearance_radius
        * lens_thickness
    )
    actual_lens_removed = float(v4_lens.Volume - lens.Volume)
    screw_shell_common = 0.0
    for screw in screw_references:
        for _, owner in context["shell_records"]:
            if v3.aabb_near(screw, owner, 0.5):
                screw_shell_common += v3.common_volume(screw, owner)
    screw_led_common = sum(
        v3.common_volume(screw, led)
        for screw in screw_references
        for led in context["led_shapes"]
    )
    screw_rear_common = sum(
        v3.common_volume(screw, context["rear_cap"])
        for screw in screw_references
    )
    screw_axis_markers = [
        Part.makeCylinder(
            0.12,
            screw_length + head_height,
            center_point + axis_n * (lens_front - head_height),
            axis_n,
        )
        for center_point in hole_centers
    ]
    context.update({
        "v4_carrier_reference": v4_carrier,
        "v4_lens_reference": v4_lens,
        "v4_aperture_reference": v4_aperture,
        "carrier": carrier,
        "lens": lens,
        "lens_retention_tabs": Part.makeCompound(tab_solids),
        "lens_retention_tab_solids": tab_solids,
        "lens_retention_tab_footprints": tab_footprints,
        "lens_retention_pilot_cutters": pilot_cutters,
        "lens_clearance_cutters": lens_cutters,
        "lens_screw_references": Part.makeCompound(screw_references),
        "lens_screw_reference_solids": screw_references,
        "lens_screw_axis_markers": Part.makeCompound(screw_axis_markers),
        "lens_retention_hole_centers": hole_centers,
        "lens_retention_attachment_common_mm3": attachment_common,
        "lens_retention_pilot_removed_mm3": pilot_removed,
        "lens_retention_pilot_residual_mm3": pilot_residual,
        "lens_clearance_removed_mm3": lens_removed,
        "lens_clearance_residual_mm3": lens_hole_residual,
        "lens_expected_clearance_removed_mm3": expected_lens_removed,
        "lens_actual_clearance_removed_mm3": actual_lens_removed,
        "lens_retention_projected_area_mm2": projected_area,
        "lens_screw_shell_collision_mm3": screw_shell_common,
        "lens_screw_led_collision_mm3": screw_led_common,
        "lens_screw_rear_plate_collision_mm3": screw_rear_common,
    })


def evaluate(context: dict[str, Any]) -> dict[str, Any]:
    v4 = context["v4_module"]
    base = v4.evaluate(context)
    checks = base["checks"]
    measurements = base["measurements"]
    values = context["contract"]["dimensions_mm"]
    gates = context["contract"]["gates"]
    count = len(context["lens_retention_tab_solids"])
    pilot_radius = float(values["lens_retention_pilot_diameter"]) / 2.0
    half_width = float(values["lens_retention_tab_width"]) / 2.0
    projection = float(values["lens_retention_tab_inward_projection"])
    overlap = float(values["lens_retention_tab_wall_overlap"])
    center_projection = float(
        values["lens_retention_hole_center_inward_projection"]
    )
    material_margins = [
        half_width - pilot_radius,
        center_projection + overlap - pilot_radius,
        projection - center_projection - pilot_radius,
    ]
    minimum_material = min(material_margins)
    aperture_area = float(
        context["toolkit"].polygon_face(
            context["Part"], context["aperture"]
        ).Area
    )
    obstruction_fraction = (
        float(context["lens_retention_projected_area_mm2"]) / aperture_area
    )
    alignment_errors = []
    for pilot, clearance in zip(
        context["lens_retention_pilot_cutters"],
        context["lens_clearance_cutters"],
    ):
        delta = pilot.CenterOfMass - clearance.CenterOfMass
        lateral = delta - context["axis_n"] * float(
            delta.dot(context["axis_n"])
        )
        alignment_errors.append(float(lateral.Length))
    lens_volume_balance = abs(
        float(context["lens_actual_clearance_removed_mm3"])
        - float(context["lens_expected_clearance_removed_mm3"])
    )
    aperture_shift = max(
        float((current - reference).Length)
        for current, reference in zip(
            context["aperture"], context["v4_aperture_reference"]
        )
    )
    checks.update({
        "four_inward_lens_retention_tabs_present": (
            count == int(gates["required_lens_retention_tab_count"])
        ),
        "lens_retention_tabs_connected_to_box_walls": (
            len(context["lens_retention_attachment_common_mm3"]) == count
            and min(context["lens_retention_attachment_common_mm3"])
            > EPSILON_MM3
        ),
        "lens_retention_material_around_pilots": (
            minimum_material
            >= float(gates["minimum_lens_retention_material_around_pilot_mm"])
        ),
        "lens_retention_tabs_are_small_perimeter_features": (
            obstruction_fraction
            <= float(gates["maximum_lens_retention_projected_obstruction_fraction"])
        ),
        "four_carrier_pilot_holes_are_open": (
            len(context["lens_retention_pilot_residual_mm3"]) == count
            and max(context["lens_retention_pilot_residual_mm3"])
            <= float(gates["maximum_hole_residual_volume_mm3"])
        ),
        "four_lens_clearance_holes_are_open": (
            len(context["lens_clearance_residual_mm3"]) == count
            and max(context["lens_clearance_residual_mm3"])
            <= float(gates["maximum_hole_residual_volume_mm3"])
            and lens_volume_balance
            <= float(gates["maximum_lens_hole_volume_balance_mm3"])
        ),
        "lens_and_carrier_hole_axes_align": (
            max(alignment_errors)
            <= float(gates["maximum_hole_axis_alignment_error_mm"])
        ),
        "m2_reference_screws_clear_shell": (
            float(context["lens_screw_shell_collision_mm3"])
            <= float(gates["maximum_reference_screw_shell_collision_mm3"])
        ),
        "m2_reference_screws_clear_leds": (
            float(context["lens_screw_led_collision_mm3"])
            <= float(gates["maximum_reference_screw_led_collision_mm3"])
        ),
        "m2_reference_screws_clear_rear_plate": (
            float(context["lens_screw_rear_plate_collision_mm3"])
            <= float(gates["maximum_reference_screw_rear_plate_collision_mm3"])
        ),
        "v4_aperture_coordinates_unchanged": aperture_shift <= 1.0e-9,
    })
    measurements.update({
        "lens_retention_tab_count": count,
        "lens_retention_tab_width_mm": float(
            values["lens_retention_tab_width"]
        ),
        "lens_retention_tab_inward_projection_mm": projection,
        "lens_retention_tab_axial_thickness_mm": float(
            values["lens_retention_tab_axial_thickness"]
        ),
        "lens_retention_attachment_common_mm3": list(
            context["lens_retention_attachment_common_mm3"]
        ),
        "lens_retention_material_margins_mm": material_margins,
        "minimum_lens_retention_material_around_pilot_mm": minimum_material,
        "lens_retention_projected_area_mm2": float(
            context["lens_retention_projected_area_mm2"]
        ),
        "lens_retention_projected_obstruction_fraction": obstruction_fraction,
        "lens_retention_pilot_removed_mm3": list(
            context["lens_retention_pilot_removed_mm3"]
        ),
        "lens_retention_pilot_residual_mm3": list(
            context["lens_retention_pilot_residual_mm3"]
        ),
        "lens_clearance_removed_mm3": list(
            context["lens_clearance_removed_mm3"]
        ),
        "lens_clearance_residual_mm3": list(
            context["lens_clearance_residual_mm3"]
        ),
        "lens_expected_clearance_removed_mm3": float(
            context["lens_expected_clearance_removed_mm3"]
        ),
        "lens_actual_clearance_removed_mm3": float(
            context["lens_actual_clearance_removed_mm3"]
        ),
        "lens_clearance_volume_balance_mm3": lens_volume_balance,
        "lens_carrier_hole_axis_alignment_errors_mm": alignment_errors,
        "lens_retention_hole_centers_world_mm": [
            vector_values(point)
            for point in context["lens_retention_hole_centers"]
        ],
        "lens_screw_shell_collision_mm3": float(
            context["lens_screw_shell_collision_mm3"]
        ),
        "lens_screw_led_collision_mm3": float(
            context["lens_screw_led_collision_mm3"]
        ),
        "lens_screw_rear_plate_collision_mm3": float(
            context["lens_screw_rear_plate_collision_mm3"]
        ),
        "v4_aperture_maximum_coordinate_shift_mm": aperture_shift,
        "lens_fastener_specification": {
            "quantity": int(values["lens_retention_tab_count"]),
            "screw": "M2x4 pan-head",
            "carrier_pilot_diameter_mm": float(
                values["lens_retention_pilot_diameter"]
            ),
            "lens_clearance_diameter_mm": float(
                values["lens_clearance_hole_diameter"]
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
    doc = App.newDocument("RightEyeM2LensRetentionFlangesReviewV5")
    try:
        add_feature(
            context, doc, "REFERENCE__RELIEVED_RIGHT_HEAD_SHELL",
            "REFERENCE — RELIEVED RIGHT HEAD SHELL",
            context["shell"], (0.70, 0.70, 0.73), 78,
        )
        carrier = add_feature(
            context, doc, "PROPOSED__V5_EYE_CARRIER_WITH_M2_LENS_TABS",
            "PROPOSED — V4 EYE + FOUR INWARD M2 LENS TABS",
            context["carrier"], (0.12, 0.72, 0.28), 0,
        )
        carrier.addProperty("App::PropertyString", "Installation", "ReviewControl")
        carrier.Installation = (
            "Straight through eye opening; head-mounting flanges are next"
        )
        lens = add_feature(
            context, doc, "PROPOSED__FOUR_HOLE_TRANSLUCENT_LENS",
            "PROPOSED — 0.90 MM TRANSLUCENT LENS WITH FOUR M2 HOLES",
            context["lens"], (0.35, 0.86, 0.96), 55,
        )
        lens.addProperty("App::PropertyString", "Retention", "ReviewControl")
        lens.Retention = (
            "Four M2x4 pan-head screws; hand-tighten into 1.60 mm PETG pilots"
        )
        cap = add_feature(
            context, doc, "PROPOSED__REMOVABLE_LED_REAR_PLATE",
            "PROPOSED — REMOVABLE LED REAR PLATE",
            context["rear_cap"], (0.08, 0.34, 0.14), 0,
        )
        cap.addProperty("App::PropertyString", "WirePort", "ReviewControl")
        cap.WirePort = "4.0 mm through-hole; seal and strain-relieve cable"
        add_feature(
            context, doc, "REFERENCE__LENS_RETENTION_TABS",
            "REFERENCE — FOUR INWARD LENS-RETENTION TABS",
            context["lens_retention_tabs"], (1.00, 0.78, 0.05), 35,
        )
        screws = add_feature(
            context, doc, "REFERENCE__M2X4_LENS_SCREWS",
            "REFERENCE — FOUR M2×4 PAN-HEAD LENS SCREWS",
            context["lens_screw_references"], (0.82, 0.20, 0.08), 15,
        )
        screws.addProperty("App::PropertyString", "Hardware", "ReviewControl")
        screws.Hardware = "4x M2x4 pan-head; optional M2 nylon washers"
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
        add_feature(
            context, doc, "REFERENCE__LENS_SCREW_AXES",
            "REFERENCE — FOUR NORMAL-TO-LENS SCREW AXES",
            context["lens_screw_axis_markers"], (0.82, 0.12, 0.88), 0,
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
    carrier = toolkit.shape_record(
        context["carrier"], (36, 182, 72), deflection=0.35
    )
    lens = toolkit.shape_record(
        context["lens"], (80, 218, 242), deflection=0.20
    )
    tabs = toolkit.shape_record(
        context["lens_retention_tabs"], (255, 198, 15), deflection=0.16
    )
    screws = toolkit.shape_record(
        context["lens_screw_references"], (210, 52, 20), deflection=0.12
    )
    exploded_lens = context["lens"].copy()
    exploded_lens.translate(context["axis_n"] * -5.0)
    exploded_screws = context["lens_screw_references"].copy()
    exploded_screws.translate(context["axis_n"] * -2.5)
    toolkit.render_side_by_side(
        output / "lens-fasteners.png",
        [carrier, lens, screws],
        [
            carrier,
            tabs,
            toolkit.shape_record(
                exploded_lens, (80, 218, 242), deflection=0.20
            ),
            toolkit.shape_record(
                exploded_screws, (210, 52, 20), deflection=0.12
            ),
        ],
        v3.tuple3(context["axis_n"]),
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
    parser.add_argument("--mode", choices=("feasibility", "review"), required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--feasibility-report", type=Path)
    parser.add_argument("--feasibility-sha256")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    started = time.monotonic()
    context = prepare()
    report = public_report(
        context, "bounded_no_save_feasibility", time.monotonic() - started
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
            raise RuntimeError(f"feasibility report already exists: {args.report}")
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
    review_report["review_fcstd"] = str(fcstd.relative_to(context["root"]))
    review_report["review_fcstd_sha256"] = sha256_file(fcstd)
    review_report["feasibility_report_sha256"] = args.feasibility_sha256
    validation = output / context["contract"]["output"]["validation"]
    validation.write_text(
        json.dumps(review_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(review_report["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
