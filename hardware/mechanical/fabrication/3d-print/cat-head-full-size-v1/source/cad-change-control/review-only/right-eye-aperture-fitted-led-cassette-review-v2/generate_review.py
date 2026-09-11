#!/usr/bin/env python3
"""Build and validate a review-only eye cassette contained by the opening.

The relieved canonical head and released lens are opened read-only.  Feasibility
mode writes JSON only.  Review mode creates a new non-authoritative document;
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


def load_pinned_module(path: Path, digest: str, name: str) -> Any:
    actual = sha256_file(path)
    if actual != digest:
        raise RuntimeError(f"{path}: hash mismatch {actual} != {digest}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def require_pin(root: Path, spec: dict[str, Any]) -> Path:
    path = root / str(spec["path"])
    actual = sha256_file(path)
    if actual != str(spec["sha256"]):
        raise RuntimeError(f"{path}: pin mismatch {actual} != {spec['sha256']}")
    return path


def shape_evidence(shape: Any) -> dict[str, Any]:
    messages = [str(item) for item in (shape.check(True) or [])]
    return {
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids),
        "volume_mm3": float(shape.Volume),
        "occt_check_messages": messages,
    }


def strict_shape_pass(evidence: dict[str, Any]) -> bool:
    return bool(
        evidence["valid"]
        and evidence["closed"]
        and evidence["solid_count"] == 1
        and float(evidence["volume_mm3"]) > 0.0
        and not evidence["occt_check_messages"]
    )


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
    result = first.common(second)
    return 0.0 if result.isNull() else float(result.Volume)


def sample_values(start: float, end: float, count: int) -> list[float]:
    if count < 2:
        raise RuntimeError("sample count must be at least two")
    return [start + (end - start) * index / (count - 1) for index in range(count)]


def polygon_inset_loop(
    App: Any,
    loop: Sequence[Any],
    inset: float,
    origin: Any,
    axis_u: Any,
    axis_v: Any,
    axis_n: Any,
) -> list[Any]:
    """Offset every polygon edge by an exact in-plane normal distance.

    The inherited radial helper moves vertices toward the centroid, so its
    numeric parameter is not the actual wall thickness on a skew quadrilateral.
    This line-intersection construction makes the requested clearance and wall
    stock physical rather than nominal.
    """
    if len(loop) < 3:
        raise RuntimeError("polygon inset requires at least three vertices")
    points = []
    for point in loop:
        delta = point - origin
        points.append((float(delta.dot(axis_u)), float(delta.dot(axis_v))))
    twice_area = sum(
        points[index][0] * points[(index + 1) % len(points)][1]
        - points[(index + 1) % len(points)][0] * points[index][1]
        for index in range(len(points))
    )
    if abs(twice_area) <= 1.0e-9:
        raise RuntimeError("polygon inset source is degenerate")
    winding = 1.0 if twice_area > 0.0 else -1.0
    lines = []
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        if length <= 1.0e-9:
            raise RuntimeError("polygon inset source has a zero-length edge")
        nx, ny = winding * (-dy / length), winding * (dx / length)
        lines.append(((start[0] + nx * inset, start[1] + ny * inset), (dx, dy)))
    output = []
    for index in range(len(lines)):
        first_point, first_direction = lines[index - 1]
        second_point, second_direction = lines[index]
        cross = (
            first_direction[0] * second_direction[1]
            - first_direction[1] * second_direction[0]
        )
        if abs(cross) <= 1.0e-9:
            raise RuntimeError("polygon inset has parallel adjacent edges")
        delta_x = second_point[0] - first_point[0]
        delta_y = second_point[1] - first_point[1]
        parameter = (
            delta_x * second_direction[1] - delta_y * second_direction[0]
        ) / cross
        u_value = first_point[0] + parameter * first_direction[0]
        v_value = first_point[1] + parameter * first_direction[1]
        output.append(origin + axis_u * u_value + axis_v * v_value)
    return output


def shell_objects(document: Any) -> list[tuple[str, Any]]:
    records: list[tuple[str, Any]] = []
    for obj in document.Objects:
        name = str(obj.Name)
        if not (
            name.startswith("RETAINED_RIGHT_UPPER_C")
            or name == "FROZEN_RIGHT_LOWER_MAIN_V34"
        ):
            continue
        shape = getattr(obj, "Shape", None)
        if shape is None or shape.isNull():
            raise RuntimeError(f"shell object has no shape: {name}")
        records.append((name, shape.copy()))
    if len(records) != 42:
        raise RuntimeError(f"expected 42 relieved shell context objects, found {len(records)}")
    return records


def farthest_axis(App: Any, loop: Sequence[Any]) -> Any:
    best = None
    best_length = -1.0
    for first in range(len(loop)):
        for second in range(first + 1, len(loop)):
            candidate = loop[second] - loop[first]
            if candidate.Length > best_length:
                best = candidate
                best_length = candidate.Length
    if best is None or best.Length <= 1.0e-9:
        raise RuntimeError("cannot derive aperture major axis")
    best.normalize()
    return best


def read_inputs() -> dict[str, Any]:
    root = repository_root()
    contract = load_json(HERE / "contract.json")
    inputs = contract["inputs"]
    generator_path = require_pin(root, inputs["geometry_generator"])
    geometry_contract_path = require_pin(root, inputs["geometry_contract"])
    manifest_path = require_pin(root, inputs["relieved_head_manifest"])
    head_path = require_pin(root, inputs["relieved_head_fcstd"])
    require_pin(root, inputs["former_lens_print_source_fcstd"])
    manifest = load_json(manifest_path)
    if manifest.get("state") != "human_approved_canonical":
        raise RuntimeError("relieved head manifest is not human-approved canonical")
    if str(manifest["assembly"]["sha256"]) != inputs["relieved_head_fcstd"]["sha256"]:
        raise RuntimeError("relieved head manifest and direct FCStd pin disagree")
    v1 = load_pinned_module(
        generator_path,
        str(inputs["geometry_generator"]["sha256"]),
        "_aperture_contained_review_geometry",
    )
    parameters = load_json(geometry_contract_path)["allowed_mutations"][0]["parameters"]
    return {
        "root": root,
        "contract": contract,
        "parameters": parameters,
        "v1": v1,
        "head_path": head_path,
    }


def load_context_shapes(context: dict[str, Any], App: Any, Part: Any) -> None:
    head_doc = App.openDocument(str(context["head_path"]))
    try:
        shell_records = shell_objects(head_doc)
    finally:
        App.closeDocument(head_doc.Name)
    context["shell_records"] = shell_records
    context["shell"] = Part.makeCompound([shape for _, shape in shell_records])


def construct(context: dict[str, Any], App: Any, Part: Any) -> None:
    contract = context["contract"]
    values = contract["dimensions_mm"]
    parameters = context["parameters"]
    toolkit = context["v1"].toolkit
    lcs = parameters["aperture_lcs"]
    geometry = parameters["geometry"]
    origin = toolkit.vector(App, lcs["origin_mm"])
    axis_u = toolkit.normalized(App, toolkit.vector(App, lcs["u"]), "aperture u")
    axis_v = toolkit.normalized(App, toolkit.vector(App, lcs["v"]), "aperture v")
    axis_n = toolkit.normalized(App, toolkit.vector(App, lcs["inward_n"]), "aperture inward n")
    former_aperture = toolkit.planar_loop(
        [toolkit.vector(App, point) for point in lcs["visible_aperture_mm"]],
        origin, axis_u, axis_v, axis_n,
    )
    aperture = polygon_inset_loop(
        App,
        former_aperture,
        float(values["visible_aperture_radial_inset"]),
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    opening = toolkit.planar_loop(
        [toolkit.vector(App, point) for point in geometry["shell_opening_boundary_mm"]],
        origin, axis_u, axis_v, axis_n,
    )
    cover_outer = polygon_inset_loop(
        App,
        opening,
        float(values["opening_cover_perimeter_clearance"]),
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    lens_outer = polygon_inset_loop(
        App,
        aperture,
        -float(values["lens_outer_offset_from_new_aperture"]),
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    # Build the carrier from the eye aperture itself, not from the much larger
    # shell-opening quadrilateral. This makes it an insertable, inward-tapered
    # electronics box instead of another surface-spanning flange.
    inner_front = polygon_inset_loop(
        App,
        former_aperture,
        float(values["front_inner_radial_inset"]),
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    outer_front = polygon_inset_loop(
        App,
        former_aperture,
        float(values["front_perimeter_radial_inset"]),
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    outer_rear = polygon_inset_loop(
        App,
        former_aperture,
        float(values["rear_perimeter_radial_inset"]),
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    inner_rear = polygon_inset_loop(
        App,
        outer_rear,
        float(values["nominal_sidewall_thickness"]),
        origin,
        axis_u,
        axis_v,
        axis_n,
    )
    front_depth = float(values["front_depth"])
    bezel_rear = float(values["bezel_rear_depth"])
    rear_depth = float(values["sidewall_rear_depth"])
    bezel = toolkit.ring_prism(
        Part, outer_front, aperture, front_depth, bezel_rear, axis_n,
        "aperture-contained front bezel",
    )
    opening_cover = toolkit.ring_prism(
        Part,
        cover_outer,
        aperture,
        float(values["opening_cover_front_depth"]),
        float(values["opening_cover_rear_depth"]),
        axis_n,
        "fitted opening cover and lower filler panel",
    )
    opening_cover_connector = toolkit.ring_prism(
        Part,
        outer_front,
        aperture,
        float(values["opening_cover_connector_front_depth"]),
        float(values["opening_cover_connector_rear_depth"]),
        axis_n,
        "opening-cover connector collar",
    )
    walls = toolkit.loft_ring(
        Part, outer_front, inner_front, outer_rear, inner_rear,
        bezel_rear - 0.05, rear_depth, axis_n,
        "aperture-contained tapered sidewalls",
    )
    seat_outer = polygon_inset_loop(
        App, inner_front, -0.15, origin, axis_u, axis_v, axis_n
    )
    lens_back_depth = 2.1
    lens_seat = toolkit.ring_prism(
        Part, seat_outer, aperture, lens_back_depth, lens_back_depth + 0.30,
        axis_n, "continuous rear lens seat",
    )
    carrier = toolkit.fuse_shapes(
        [opening_cover, opening_cover_connector, bezel, walls, lens_seat],
        "aperture-fitted LED cassette carrier and lower filler panel",
    ).removeSplitter()
    toolkit.require_single_solid(carrier, "aperture-contained LED cassette carrier")
    lens_front_depth = float(values["bezel_rear_depth"])
    lens_thickness = float(values["lens_thickness"])
    lens = toolkit.polygon_face(
        Part, toolkit.at_depth(lens_outer, lens_front_depth, axis_n)
    ).extrude(axis_n * lens_thickness).removeSplitter()
    toolkit.require_single_solid(lens, "smaller translucent eye lens")

    rear_clearance = float(values["rear_plate_radial_clearance"])
    cap_loop = polygon_inset_loop(
        App, inner_rear, rear_clearance, origin, axis_u, axis_v, axis_n
    )
    cap_front = float(values["rear_plate_front_depth"])
    cap_thickness = float(values["rear_plate_thickness"])
    uncut_cap = toolkit.polygon_face(
        Part, toolkit.at_depth(cap_loop, cap_front, axis_n)
    ).extrude(axis_n * cap_thickness).removeSplitter()
    major = farthest_axis(App, aperture)
    minor = toolkit.normalized(App, axis_n.cross(major), "aperture minor axis")
    cap_center = toolkit.average(App, cap_loop)
    wire_center = cap_center + minor * float(values["wire_port_minor_axis_offset"])
    wire_radius = float(values["wire_port_diameter"]) / 2.0
    wire_cutter = Part.makeCylinder(
        wire_radius, cap_thickness + 2.0,
        wire_center + axis_n * (cap_front - 1.0), axis_n,
    )
    wire_removed = common_volume(uncut_cap, wire_cutter)
    rear_cap = uncut_cap.cut(wire_cutter).removeSplitter()
    toolkit.require_single_solid(rear_cap, "removable LED rear plate")
    expected_wire_removed = math.pi * wire_radius * wire_radius * cap_thickness

    pixel_count = int(values["pixel_count"])
    pitch = float(values["led_reference_pitch"])
    led_radius = float(values["led_reference_diameter"]) / 2.0
    led_depth = float(values["led_reference_depth"])
    offsets = [(index - (pixel_count - 1) / 2.0) * pitch for index in range(pixel_count)]
    led_shapes = [
        Part.makeCylinder(
            led_radius, led_depth,
            cap_center + major * offset + axis_n * (cap_front - led_depth), axis_n,
        )
        for offset in offsets
    ]
    wire_led_common = sum(common_volume(wire_cutter, item) for item in led_shapes)
    wire_corridor = Part.makeCylinder(
        wire_radius, cap_thickness + 10.0,
        wire_center + axis_n * (cap_front - 1.0), axis_n,
    )
    context.update({
        "App": App, "Part": Part, "toolkit": toolkit,
        "origin": origin, "axis_u": axis_u, "axis_v": axis_v, "axis_n": axis_n,
        "opening": opening, "cover_outer": cover_outer,
        "opening_cover": opening_cover,
        "opening_cover_connector": opening_cover_connector,
        "former_aperture": former_aperture,
        "aperture": aperture, "outer_front": outer_front,
        "outer_rear": outer_rear, "inner_front": inner_front, "inner_rear": inner_rear,
        "carrier": carrier, "lens": lens,
        "rear_cap": rear_cap, "uncut_rear_cap": uncut_cap,
        "lens_seat": lens_seat, "led_shapes": led_shapes,
        "wire_cutter": wire_cutter, "wire_corridor": wire_corridor,
        "wire_removed_mm3": wire_removed,
        "expected_wire_removed_mm3": expected_wire_removed,
        "wire_led_intersection_mm3": wire_led_common,
        "major": major, "minor": minor,
        "lens_front_depth_mm": lens_front_depth,
        "lens_back_depth_mm": lens_front_depth + lens_thickness,
        "led_front_depth_mm": cap_front - led_depth,
    })


def shell_collision_records(
    shapes: Sequence[tuple[str, Any]], shell_records: Sequence[tuple[str, Any]]
) -> tuple[dict[str, float], float]:
    intersections: dict[str, float] = {}
    minimum = math.inf
    for shape_name, shape in shapes:
        for owner_name, owner in shell_records:
            if not aabb_near(shape, owner, 5.0):
                continue
            volume = common_volume(shape, owner)
            if volume > EPSILON_MM3:
                intersections[f"{shape_name}::{owner_name}"] = volume
            distance = float(shape.distToShape(owner)[0])
            minimum = min(minimum, distance)
    return intersections, minimum


def motion_records(
    moving: Any,
    shell_records: Sequence[tuple[str, Any]],
    axis_n: Any,
    translations: Sequence[float],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for sample_index, translation in enumerate(translations):
        posed = moving.copy()
        posed.translate(axis_n * float(translation))
        hits: dict[str, float] = {}
        for owner_name, owner in shell_records:
            if not aabb_near(posed, owner):
                continue
            volume = common_volume(posed, owner)
            if volume > EPSILON_MM3:
                hits[owner_name] = volume
        records.append({
            "sample_index": sample_index,
            "translation_mm": float(translation),
            "positive_intersections_mm3": hits,
        })
    return records


def evaluate(context: dict[str, Any]) -> dict[str, Any]:
    Part = context["Part"]
    contract = context["contract"]
    gates = contract["gates"]
    toolkit = context["toolkit"]
    opening_face = toolkit.polygon_face(Part, context["opening"])
    cover_outer_face = toolkit.polygon_face(Part, context["cover_outer"])
    former_aperture_face = toolkit.polygon_face(Part, context["former_aperture"])
    aperture_face = toolkit.polygon_face(Part, context["aperture"])
    opening_wire = Part.makePolygon([*context["opening"], context["opening"][0]])
    cover_outer_wire = Part.makePolygon([*context["cover_outer"], context["cover_outer"][0]])
    outer_front_wire = Part.makePolygon([*context["outer_front"], context["outer_front"][0]])
    outer_rear_wire = Part.makePolygon([*context["outer_rear"], context["outer_rear"][0]])
    inner_front_wire = Part.makePolygon([*context["inner_front"], context["inner_front"][0]])
    inner_rear_wire = Part.makePolygon([*context["inner_rear"], context["inner_rear"][0]])
    outside_opening_area = float(cover_outer_face.cut(opening_face).Area)
    opening_gap = float(cover_outer_wire.distToShape(opening_wire)[0])
    front_wall = float(outer_front_wire.distToShape(inner_front_wire)[0])
    rear_wall = float(outer_rear_wire.distToShape(inner_rear_wire)[0])
    lens_face = context["lens"].section(aperture_face)
    uncovered_aperture = float(aperture_face.cut(toolkit.polygon_face(
        Part,
        toolkit.radial_offset_loop(
            context["App"],
            context["aperture"],
            float(contract["dimensions_mm"]["lens_outer_offset_from_new_aperture"]),
            context["axis_n"],
        )
    )).Area)
    lens_carrier_common = common_volume(context["lens"], context["carrier"])
    lens_carrier_distance = float(context["lens"].distToShape(context["carrier"])[0])
    static_intersections, static_minimum = shell_collision_records(
        [
            ("carrier", context["carrier"]),
            ("lens", context["lens"]),
            ("rear_cap", context["rear_cap"]),
        ],
        context["shell_records"],
    )
    inserted = Part.makeCompound([context["carrier"], context["lens"]])
    insertion = motion_records(
        inserted, context["shell_records"], context["axis_n"],
        sample_values(
            float(gates["insertion_translation_start_mm"]),
            float(gates["insertion_translation_end_mm"]),
            int(gates["insertion_sample_count"]),
        ),
    )
    cap_service = motion_records(
        context["rear_cap"], context["shell_records"], context["axis_n"],
        sample_values(
            float(gates["rear_plate_service_translation_mm"]), 0.0,
            int(gates["rear_plate_service_sample_count"]),
        ),
    )
    led_carrier_common = sum(common_volume(item, context["carrier"]) for item in context["led_shapes"])
    led_cap_common = sum(common_volume(item, context["rear_cap"]) for item in context["led_shapes"])
    carrier_evidence = shape_evidence(context["carrier"])
    cap_evidence = shape_evidence(context["rear_cap"])
    lens_evidence = shape_evidence(context["lens"])
    maximum_motion_collision = max(
        [0.0]
        + [max([0.0, *record["positive_intersections_mm3"].values()]) for record in insertion]
    )
    maximum_cap_service_collision = max(
        [0.0]
        + [max([0.0, *record["positive_intersections_mm3"].values()]) for record in cap_service]
    )
    led_to_lens_gap = context["led_front_depth_mm"] - context["lens_back_depth_mm"]
    wire_balance = abs(context["wire_removed_mm3"] - context["expected_wire_removed_mm3"])
    required_lower_filler = cover_outer_face.cut(former_aperture_face)
    actual_cover_projection = cover_outer_face.cut(aperture_face)
    uncovered_lower_filler = float(required_lower_filler.cut(actual_cover_projection).Area)
    opening_cover_common = common_volume(context["carrier"], context["opening_cover"])
    opening_cover_volume = float(context["opening_cover"].Volume)
    checks = {
        "carrier_valid_closed_one_solid_deep_clean": strict_shape_pass(carrier_evidence),
        "rear_plate_valid_closed_one_solid_deep_clean": strict_shape_pass(cap_evidence),
        "released_lens_valid_closed_one_solid_deep_clean": strict_shape_pass(lens_evidence),
        "carrier_front_wholly_inside_opening": outside_opening_area <= 1.0e-6,
        "integral_lower_opening_panel_present": (
            opening_cover_volume > 0.0
            and abs(opening_cover_common - opening_cover_volume) <= 1.0e-5
            and float(required_lower_filler.Area) > 0.0
            and uncovered_lower_filler <= 1.0e-6
        ),
        "actual_front_opening_gap": opening_gap >= float(gates["minimum_actual_front_opening_gap_mm"]),
        "actual_sidewall_thickness": min(front_wall, rear_wall) >= float(gates["minimum_actual_sidewall_thickness_mm"]),
        "zero_static_shell_intersection": not static_intersections,
        "minimum_static_shell_clearance": static_minimum >= float(gates["minimum_static_shell_clearance_mm"]),
        "straight_front_insertion_clear": maximum_motion_collision <= float(gates["maximum_positive_shell_intersection_mm3"]),
        "rear_plate_inside_service_clear": maximum_cap_service_collision <= float(gates["maximum_positive_shell_intersection_mm3"]),
        "released_lens_does_not_intersect_carrier": lens_carrier_common <= float(gates["maximum_lens_carrier_intersection_mm3"]),
        "released_lens_contacts_seat": lens_carrier_distance <= 1.0e-6,
        "visible_aperture_covered": uncovered_aperture <= 1.0e-6 and not lens_face.isNull(),
        "four_led_references_inside_cavity": len(context["led_shapes"]) == 4 and led_carrier_common <= EPSILON_MM3,
        "led_references_touch_rear_plate": led_cap_common <= EPSILON_MM3,
        "led_to_lens_gap": led_to_lens_gap >= float(gates["minimum_led_to_lens_gap_mm"]),
        "wire_port_is_exact_through_hole": context["wire_removed_mm3"] > 0.0 and wire_balance <= 0.05,
        "wire_port_clear_of_led_references": context["wire_led_intersection_mm3"] <= EPSILON_MM3,
    }
    failed = [key for key, value in checks.items() if not value]
    return {
        "status": "FEASIBILITY_PASS__REVIEW_ARTIFACT_ALLOWED" if not failed else "FEASIBILITY_FAIL__NO_REVIEW_ARTIFACT",
        "checks": checks,
        "failed_checks": failed,
        "measurements": {
            "outside_opening_area_mm2": outside_opening_area,
            "required_lower_filler_area_mm2": float(required_lower_filler.Area),
            "uncovered_lower_filler_area_mm2": uncovered_lower_filler,
            "opening_cover_panel_volume_mm3": opening_cover_volume,
            "actual_front_opening_gap_mm": opening_gap,
            "front_sidewall_thickness_mm": front_wall,
            "rear_sidewall_thickness_mm": rear_wall,
            "static_shell_intersections_mm3": static_intersections,
            "minimum_static_shell_clearance_mm": static_minimum,
            "maximum_insertion_collision_mm3": maximum_motion_collision,
            "maximum_rear_plate_service_collision_mm3": maximum_cap_service_collision,
            "lens_carrier_intersection_mm3": lens_carrier_common,
            "lens_carrier_distance_mm": lens_carrier_distance,
            "uncovered_aperture_area_mm2": uncovered_aperture,
            "led_carrier_intersection_mm3": led_carrier_common,
            "led_rear_plate_intersection_mm3": led_cap_common,
            "led_to_lens_gap_mm": led_to_lens_gap,
            "wire_port_removed_volume_mm3": context["wire_removed_mm3"],
            "wire_port_expected_volume_mm3": context["expected_wire_removed_mm3"],
            "wire_port_volume_balance_mm3": wire_balance,
            "wire_port_led_intersection_mm3": context["wire_led_intersection_mm3"],
            "carrier": carrier_evidence,
            "rear_plate": cap_evidence,
            "lens": lens_evidence,
        },
        "insertion_samples": insertion,
        "rear_plate_service_samples": cap_service,
    }


def prepare() -> dict[str, Any]:
    context = read_inputs()
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore
    load_context_shapes(context, App, Part)
    construct(context, App, Part)
    context["evaluation"] = evaluate(context)
    return context


def public_report(context: dict[str, Any], mode: str, elapsed: float) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "review_id": context["contract"]["review_id"],
        "authority": context["contract"]["authority"],
        "mode": mode,
        **context["evaluation"],
        "pins": {
            "contract_sha256": sha256_file(HERE / "contract.json"),
            "generator_sha256": sha256_file(Path(__file__)),
            **{key: value["sha256"] for key, value in context["contract"]["inputs"].items()},
        },
        "elapsed_seconds": elapsed,
        "io_trace": {
            "canonical_opened_read_only": True,
            "canonical_saved": False,
            "former_lens_source_opened": False,
            "new_lens_constructed_in_memory": True,
            "review_fcstd_saved": mode == "single_review_artifact",
            "geometry_export_created": False,
            "production_output_created": False,
        },
    }


def add_feature(doc: Any, name: str, label: str, shape: Any, color: tuple[float, float, float], transparency: int, authority: str) -> Any:
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape.copy()
    obj.addProperty("App::PropertyString", "Authority", "ReviewControl")
    obj.Authority = authority
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = transparency
    return obj


def create_review(context: dict[str, Any], output: Path) -> Path:
    App = context["App"]
    authority = context["contract"]["authority"]
    doc = App.newDocument("RightEyeApertureFittedLedCassetteReviewV2")
    try:
        add_feature(doc, "REFERENCE__RELIEVED_RIGHT_HEAD_SHELL", "REFERENCE — RELIEVED RIGHT HEAD SHELL", context["shell"], (0.70, 0.70, 0.73), 78, authority)
        carrier = add_feature(doc, "PROPOSED__APERTURE_FITTED_CARRIER_AND_LOWER_PANEL", "PROPOSED — FITTED CARRIER + LOWER OPENING PANEL", context["carrier"], (0.12, 0.72, 0.28), 0, authority)
        carrier.addProperty("App::PropertyString", "Installation", "ReviewControl")
        carrier.Installation = "Straight through eye opening; 0.60 mm fitted perimeter for a thin black seal; rear mounting flanges are next"
        lens = add_feature(doc, "PROPOSED__TRANSLUCENT_LENS", "PROPOSED — 0.90 MM TRANSLUCENT LENS", context["lens"], (0.35, 0.86, 0.96), 55, authority)
        lens.addProperty("App::PropertyString", "Retention", "ReviewControl")
        lens.Retention = "Three tiny clear neutral-cure silicone dabs on continuous rear seat"
        cap = add_feature(doc, "PROPOSED__REMOVABLE_LED_REAR_PLATE", "PROPOSED — REMOVABLE LED REAR PLATE", context["rear_cap"], (0.08, 0.34, 0.14), 0, authority)
        cap.addProperty("App::PropertyString", "WirePort", "ReviewControl")
        cap.WirePort = "4.0 mm through-hole; seal and strain-relieve cable"
        for index, led in enumerate(context["led_shapes"], start=1):
            add_feature(doc, f"REFERENCE__LED_PIXEL_{index}", f"REFERENCE — LED PIXEL {index}", led, (1.0, 0.62, 0.05), 12, authority)
        add_feature(doc, "REFERENCE__WIRE_EXIT_4MM", "REFERENCE — 4 MM WIRE EXIT / ROUTE", context["wire_corridor"], (0.95, 0.18, 0.08), 65, authority)
        add_feature(doc, "REFERENCE__CONTINUOUS_LENS_SEAT", "REFERENCE — CONTINUOUS REAR LENS SEAT", context["lens_seat"], (0.95, 0.48, 0.08), 50, authority)
        doc.recompute()
        path = output / context["contract"]["output"]["fcstd"]
        doc.saveAs(str(path))
        return path
    finally:
        App.closeDocument(doc.Name)


def tuple3(vector: Any) -> tuple[float, float, float]:
    return float(vector.x), float(vector.y), float(vector.z)


def render_views(context: dict[str, Any], output: Path) -> None:
    toolkit = context["toolkit"]
    shell = toolkit.shape_record(context["shell"], (150, 154, 160), deflection=1.0)
    carrier = toolkit.shape_record(context["carrier"], (36, 182, 72), deflection=0.35)
    lens = toolkit.shape_record(context["lens"], (95, 220, 242), deflection=0.3)
    cap = toolkit.shape_record(context["rear_cap"], (20, 86, 38), deflection=0.3)
    leds = [toolkit.shape_record(shape, (255, 160, 15), deflection=0.25) for shape in context["led_shapes"]]
    wire = toolkit.shape_record(context["wire_corridor"], (235, 50, 25), deflection=0.25)
    full = [shell, carrier, lens, cap, *leds, wire]
    axis_n = context["axis_n"]
    axis_u = context["axis_u"]
    views = {
        "front.png": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "rear.png": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
        "side.png": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        "inside-leds.png": (tuple(-value for value in tuple3(axis_n)), tuple3(axis_u)),
    }
    for name, (direction, up) in views.items():
        toolkit.render_side_by_side(output / name, [shell], full, direction, up)
    exploded_lens = context["lens"].copy()
    exploded_lens.translate(axis_n * -8.0)
    exploded_cap = context["rear_cap"].copy()
    exploded_cap.translate(axis_n * 10.0)
    toolkit.render_side_by_side(
        output / "exploded.png", [shell],
        [shell, carrier, toolkit.shape_record(exploded_lens, (95, 220, 242), deflection=0.3), toolkit.shape_record(exploded_cap, (20, 86, 38), deflection=0.3), *leds, wire],
        (0.0, -1.0, 0.0), (0.0, 0.0, 1.0),
    )
    insertion = context["carrier"].copy()
    insertion.translate(axis_n * -9.0)
    toolkit.render_side_by_side(
        output / "insertion.png", [shell, carrier],
        [shell, toolkit.shape_record(insertion, (36, 182, 72), deflection=0.35)],
        tuple3(axis_u), (0.0, 0.0, 1.0),
    )


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
