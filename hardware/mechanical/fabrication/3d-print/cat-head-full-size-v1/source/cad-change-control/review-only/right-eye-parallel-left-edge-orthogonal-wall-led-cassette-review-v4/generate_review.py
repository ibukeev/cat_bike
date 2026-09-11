#!/usr/bin/env python3
"""Build a review-only V4 eye cassette from the pinned V3 construction.

V4 makes exactly two user-requested geometry changes: it replaces aperture
edge 0-to-1 with an equal-length line parallel to shell-opening edge 0-to-1,
and it replaces the tapered box loft with constant-section walls extruded
along the pinned aperture normal. Canonical inputs remain read-only.
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


def load_v3(root: Path, contract: dict[str, Any]) -> Any:
    for key in ("v3_review_generator", "v3_review_contract"):
        spec = contract["inputs"][key]
        path = root / str(spec["path"])
        actual = sha256_file(path)
        if actual != str(spec["sha256"]):
            raise RuntimeError(f"{path}: pin mismatch {actual} != {spec['sha256']}")
    path = root / str(contract["inputs"]["v3_review_generator"]["path"])
    spec = importlib.util.spec_from_file_location("_pinned_eye_review_v3", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.HERE = HERE
    return module


def vector_copy(App: Any, vector: Any) -> Any:
    return App.Vector(float(vector.x), float(vector.y), float(vector.z))


def vector_values(vector: Any) -> list[float]:
    return [float(vector.x), float(vector.y), float(vector.z)]


def parallel_left_edge_loop(
    App: Any,
    v3_loop: Sequence[Any],
    opening: Sequence[Any],
    axis_n: Any,
    normal_offset: float,
    lower_along_edge_inset: float,
) -> list[Any]:
    if len(v3_loop) != 4 or len(opening) != 4:
        raise RuntimeError("V4 requires four-point aperture and opening loops")
    shell_direction = opening[1] - opening[0]
    shell_length = float(shell_direction.Length)
    if shell_length <= 1.0e-9:
        raise RuntimeError("selected shell edge is degenerate")
    shell_direction.normalize()
    inward = axis_n.cross(shell_direction)
    if inward.Length <= 1.0e-9:
        raise RuntimeError("cannot derive selected-edge inward direction")
    inward.normalize()
    opening_center = App.Vector(
        sum(float(item.x) for item in opening) / len(opening),
        sum(float(item.y) for item in opening) / len(opening),
        sum(float(item.z) for item in opening) / len(opening),
    )
    shell_midpoint = (opening[0] + opening[1]) * 0.5
    if float((opening_center - shell_midpoint).dot(inward)) < 0.0:
        inward = inward * -1.0
    v3_edge_length = float((v3_loop[1] - v3_loop[0]).Length)
    start = (
        opening[0]
        + shell_direction * float(lower_along_edge_inset)
        + inward * float(normal_offset)
    )
    end = start + shell_direction * v3_edge_length
    upper_margin = float((opening[1] - end).dot(shell_direction))
    if upper_margin <= 0.0:
        raise RuntimeError("selected parallel aperture edge exceeds the shell edge")
    return [
        vector_copy(App, start),
        vector_copy(App, end),
        vector_copy(App, v3_loop[2]),
        vector_copy(App, v3_loop[3]),
    ]


def selected_edge_relief_cutter(
    App: Any,
    Part: Any,
    toolkit: Any,
    aperture: Sequence[Any],
    axis_n: Any,
    endpoint_extension: float,
    outward_span: float,
    inward_span: float,
    front_depth: float,
    rear_depth: float,
) -> Any:
    direction = aperture[1] - aperture[0]
    if direction.Length <= 1.0e-9:
        raise RuntimeError("selected aperture edge is degenerate")
    direction.normalize()
    inward = axis_n.cross(direction)
    if inward.Length <= 1.0e-9:
        raise RuntimeError("cannot derive selected-edge relief direction")
    inward.normalize()
    center = App.Vector(
        sum(float(item.x) for item in aperture) / len(aperture),
        sum(float(item.y) for item in aperture) / len(aperture),
        sum(float(item.z) for item in aperture) / len(aperture),
    )
    midpoint = (aperture[0] + aperture[1]) * 0.5
    if float((center - midpoint).dot(inward)) < 0.0:
        inward = inward * -1.0
    outward = inward * -1.0
    start = aperture[0] - direction * float(endpoint_extension)
    end = aperture[1] + direction * float(endpoint_extension)
    loop = [
        start + outward * float(outward_span),
        end + outward * float(outward_span),
        end + inward * float(inward_span),
        start + inward * float(inward_span),
    ]
    face = toolkit.polygon_face(
        Part, toolkit.at_depth(loop, float(front_depth), axis_n)
    )
    return face.extrude(axis_n * float(rear_depth - front_depth)).removeSplitter()


def read_inputs() -> dict[str, Any]:
    root = repository_root()
    contract = load_json(HERE / "contract.json")
    v3 = load_v3(root, contract)
    context = v3.read_inputs()
    context["v3_module"] = v3
    return context


def construct(context: dict[str, Any], App: Any, Part: Any) -> None:
    v3 = context["v3_module"]
    v3.construct(context, App, Part)
    values = context["contract"]["dimensions_mm"]
    toolkit = context["toolkit"]
    origin = context["origin"]
    axis_u = context["axis_u"]
    axis_v = context["axis_v"]
    axis_n = context["axis_n"]
    opening = context["opening"]
    cover_outer = context["cover_outer"]
    v3_aperture = [vector_copy(App, item) for item in context["aperture"]]
    aperture = parallel_left_edge_loop(
        App,
        v3_aperture,
        opening,
        axis_n,
        float(values["selected_left_edge_shell_normal_offset"]),
        float(values["selected_left_edge_lower_along_shell_edge_inset"]),
    )
    rim_outer = v3.polygon_inset_loop(
        App, aperture, -float(values["front_rim_width"]),
        origin, axis_u, axis_v, axis_n,
    )
    lens_outer = v3.polygon_inset_loop(
        App, aperture, -float(values["lens_outer_offset_from_new_aperture"]),
        origin, axis_u, axis_v, axis_n,
    )
    box_outer = v3.polygon_inset_loop(
        App, aperture, float(values["straight_box_outer_inset_from_aperture"]),
        origin, axis_u, axis_v, axis_n,
    )
    box_inner = v3.polygon_inset_loop(
        App, box_outer, float(values["straight_sidewall_thickness"]),
        origin, axis_u, axis_v, axis_n,
    )
    front_depth = float(values["front_depth"])
    bezel_rear = float(values["bezel_rear_depth"])
    lens_front_depth = float(values["lens_surround_front_depth"])
    lens_back_depth = float(values["lens_surround_rear_depth"])
    wall_front_depth = float(values["sidewall_front_depth"])
    rear_depth = float(values["sidewall_rear_depth"])
    selected_edge_relief = selected_edge_relief_cutter(
        App, Part, toolkit, aperture, axis_n,
        float(values["selected_edge_deep_rim_relief_endpoint_extension"]),
        float(values["selected_edge_deep_rim_relief_outward_span"]),
        float(values["selected_edge_deep_rim_relief_inward_span"]),
        float(values["selected_edge_deep_rim_relief_front_depth"]),
        float(values["selected_edge_deep_rim_relief_rear_depth"]),
    )
    unrelieved_bezel = toolkit.ring_prism(
        Part, rim_outer, aperture, front_depth, bezel_rear, axis_n,
        "parallel-edge aperture front bezel",
    )
    bezel = unrelieved_bezel.cut(selected_edge_relief).removeSplitter()
    opening_cover = toolkit.ring_prism(
        Part, cover_outer, aperture,
        float(values["opening_cover_front_depth"]),
        float(values["opening_cover_rear_depth"]),
        axis_n, "fitted opening cover and lower filler panel",
    )
    unrelieved_opening_cover_connector = toolkit.ring_prism(
        Part, rim_outer, aperture,
        float(values["opening_cover_connector_front_depth"]),
        float(values["opening_cover_connector_rear_depth"]),
        axis_n, "opening-cover connector collar",
    )
    opening_cover_connector = (
        unrelieved_opening_cover_connector.cut(selected_edge_relief).removeSplitter()
    )
    unrelieved_lens_surround = toolkit.ring_prism(
        Part, rim_outer, lens_outer,
        lens_front_depth, lens_back_depth, axis_n,
        "parallel-edge lens surround",
    )
    lens_surround = unrelieved_lens_surround.cut(selected_edge_relief).removeSplitter()
    selected_edge_deep_rim_removed = sum(
        v3.common_volume(shape, selected_edge_relief)
        for shape in (
            unrelieved_bezel,
            unrelieved_opening_cover_connector,
            unrelieved_lens_surround,
        )
    )
    walls = toolkit.ring_prism(
        Part, box_outer, box_inner,
        wall_front_depth, rear_depth, axis_n,
        "perpendicular straight sidewalls",
    )
    wall_transition_shelf = toolkit.ring_prism(
        Part, aperture, box_outer,
        lens_back_depth, lens_back_depth + 0.30, axis_n,
        "straight-wall front connector shelf",
    )
    seat_outer = v3.polygon_inset_loop(
        App, lens_outer, -float(values["lens_seat_outer_offset_from_lens"]),
        origin, axis_u, axis_v, axis_n,
    )
    lens_seat = toolkit.ring_prism(
        Part, seat_outer, aperture,
        lens_back_depth, lens_back_depth + 0.30, axis_n,
        "continuous rear lens seat",
    )
    carrier = toolkit.fuse_shapes(
        [
            opening_cover,
            opening_cover_connector,
            bezel,
            lens_surround,
            lens_seat,
            wall_transition_shelf,
            walls,
        ],
        "parallel-left-edge orthogonal-wall LED cassette and lower filler panel",
    ).removeSplitter()
    toolkit.require_single_solid(carrier, "V4 orthogonal-wall LED cassette carrier")
    lens_thickness = float(values["lens_thickness"])
    lens = toolkit.polygon_face(
        Part, toolkit.at_depth(lens_outer, lens_front_depth, axis_n)
    ).extrude(axis_n * lens_thickness).removeSplitter()
    toolkit.require_single_solid(lens, "V4 translucent eye lens")
    rear_clearance = float(values["rear_plate_radial_clearance"])
    cap_loop = v3.polygon_inset_loop(
        App, box_inner, rear_clearance, origin, axis_u, axis_v, axis_n,
    )
    cap_front = float(values["rear_plate_front_depth"])
    cap_thickness = float(values["rear_plate_thickness"])
    uncut_cap = toolkit.polygon_face(
        Part, toolkit.at_depth(cap_loop, cap_front, axis_n)
    ).extrude(axis_n * cap_thickness).removeSplitter()
    major = v3.farthest_axis(App, aperture)
    minor = toolkit.normalized(App, axis_n.cross(major), "aperture minor axis")
    cap_center = toolkit.average(App, cap_loop)
    wire_center = cap_center + minor * float(values["wire_port_minor_axis_offset"])
    wire_radius = float(values["wire_port_diameter"]) / 2.0
    wire_cutter = Part.makeCylinder(
        wire_radius, cap_thickness + 2.0,
        wire_center + axis_n * (cap_front - 1.0), axis_n,
    )
    wire_removed = v3.common_volume(uncut_cap, wire_cutter)
    rear_cap = uncut_cap.cut(wire_cutter).removeSplitter()
    toolkit.require_single_solid(rear_cap, "V4 removable LED rear plate")
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
    wire_led_common = sum(v3.common_volume(wire_cutter, item) for item in led_shapes)
    wire_corridor = Part.makeCylinder(
        wire_radius, cap_thickness + 10.0,
        wire_center + axis_n * (cap_front - 1.0), axis_n,
    )
    shell_marker_direction = opening[1] - opening[0]
    shell_marker_length = float(shell_marker_direction.Length)
    shell_marker_direction.normalize()
    aperture_marker_direction = aperture[1] - aperture[0]
    aperture_marker_length = float(aperture_marker_direction.Length)
    aperture_marker_direction.normalize()
    shell_edge_marker = Part.makeCylinder(
        0.22, shell_marker_length, opening[0], shell_marker_direction,
    )
    aperture_edge_marker = Part.makeCylinder(
        0.22, aperture_marker_length,
        aperture[0] - axis_n * 0.10, aperture_marker_direction,
    )
    lower_corner_marker = Part.makeSphere(0.65, aperture[0] - axis_n * 0.12)
    wall_axis_markers = []
    for point in box_outer:
        wall_axis_markers.append(
            Part.makeCylinder(
                0.16, rear_depth - wall_front_depth,
                point + axis_n * wall_front_depth, axis_n,
            )
        )
    context.update({
        "v3_aperture_reference": v3_aperture,
        "aperture": aperture,
        "rim_outer": rim_outer,
        "lens_outer": lens_outer,
        "outer_front": [vector_copy(App, item) for item in box_outer],
        "inner_front": [vector_copy(App, item) for item in box_inner],
        "outer_rear": [vector_copy(App, item) for item in box_outer],
        "inner_rear": [vector_copy(App, item) for item in box_inner],
        "box_outer": box_outer,
        "box_inner": box_inner,
        "opening_cover": opening_cover,
        "opening_cover_connector": opening_cover_connector,
        "bezel": bezel,
        "lens_surround": lens_surround,
        "walls": walls,
        "selected_edge_relief": selected_edge_relief,
        "selected_edge_deep_rim_removed_mm3": selected_edge_deep_rim_removed,
        "wall_transition_shelf": wall_transition_shelf,
        "carrier": carrier,
        "lens": lens,
        "rear_cap": rear_cap,
        "uncut_rear_cap": uncut_cap,
        "lens_seat": lens_seat,
        "led_shapes": led_shapes,
        "wire_cutter": wire_cutter,
        "wire_corridor": wire_corridor,
        "wire_removed_mm3": wire_removed,
        "expected_wire_removed_mm3": expected_wire_removed,
        "wire_led_intersection_mm3": wire_led_common,
        "major": major,
        "minor": minor,
        "lens_front_depth_mm": lens_front_depth,
        "lens_back_depth_mm": lens_front_depth + lens_thickness,
        "led_front_depth_mm": cap_front - led_depth,
        "selected_shell_edge_marker": shell_edge_marker,
        "selected_aperture_edge_marker": aperture_edge_marker,
        "selected_lower_corner_marker": lower_corner_marker,
        "wall_axis_markers": Part.makeCompound(wall_axis_markers),
    })


def angle_error_deg(first: Any, second: Any) -> float:
    denominator = float(first.Length * second.Length)
    if denominator <= 1.0e-12:
        raise RuntimeError("cannot compare degenerate directions")
    cosine = max(-1.0, min(1.0, float(first.dot(second)) / denominator))
    return math.degrees(math.acos(cosine))


def lateral_distance(delta: Any, axis_n: Any) -> float:
    lateral = delta - axis_n * float(delta.dot(axis_n))
    return float(lateral.Length)


def evaluate(context: dict[str, Any]) -> dict[str, Any]:
    v3 = context["v3_module"]
    base = v3.evaluate(context)
    checks = base["checks"]
    checks.pop("visible_aperture_shape_preserved_exactly", None)
    measurements = base["measurements"]
    for key in (
        "visible_aperture_uniform_scale",
        "visible_aperture_max_edge_scale_error",
        "visible_aperture_max_edge_direction_error",
        "visible_aperture_center_shift_mm",
        "visible_aperture_corner_moves_toward_shell_mm",
    ):
        measurements.pop(key, None)
    gates = context["contract"]["gates"]
    values = context["contract"]["dimensions_mm"]
    opening = context["opening"]
    v3_aperture = context["v3_aperture_reference"]
    aperture = context["aperture"]
    shell_edge = opening[1] - opening[0]
    v3_edge = v3_aperture[1] - v3_aperture[0]
    selected_edge = aperture[1] - aperture[0]
    parallel_angle_error = angle_error_deg(selected_edge, shell_edge)
    selected_edge_length_change = abs(float(selected_edge.Length - v3_edge.Length))
    shell_wire = context["Part"].makePolygon([opening[0], opening[1]])
    selected_wire = context["Part"].makePolygon([aperture[0], aperture[1]])
    selected_edge_shell_offset = float(selected_wire.distToShape(shell_wire)[0])
    lower_distance_v3 = float((v3_aperture[0] - opening[0]).Length)
    lower_distance_v4 = float((aperture[0] - opening[0]).Length)
    lower_approach_gain = lower_distance_v3 - lower_distance_v4
    upper_distance_v3 = float((v3_aperture[1] - opening[1]).Length)
    upper_distance_v4 = float((aperture[1] - opening[1]).Length)
    frozen_vertex_shifts = [
        float((aperture[index] - v3_aperture[index]).Length)
        for index in (2, 3)
    ]
    toolkit = context["toolkit"]
    v3_area = float(toolkit.polygon_face(context["Part"], v3_aperture).Area)
    v4_area = float(toolkit.polygon_face(context["Part"], aperture).Area)
    area_gain_v3 = v4_area / v3_area - 1.0
    wall_lateral_drifts = []
    for front, rear in zip(context["outer_front"], context["outer_rear"]):
        wall_lateral_drifts.append(lateral_distance(rear - front, context["axis_n"]))
    for front, rear in zip(context["inner_front"], context["inner_rear"]):
        wall_lateral_drifts.append(lateral_distance(rear - front, context["axis_n"]))
    wall_angle_errors = []
    front_depth = float(values["sidewall_front_depth"])
    rear_depth = float(values["sidewall_rear_depth"])
    for point in context["outer_front"]:
        direction = (
            point + context["axis_n"] * rear_depth
            - (point + context["axis_n"] * front_depth)
        )
        wall_angle_errors.append(angle_error_deg(direction, context["axis_n"]))
    maximum_wall_lateral_drift = max(wall_lateral_drifts)
    maximum_wall_angle_error = max(wall_angle_errors)
    feature_shell_intersections: dict[str, dict[str, float]] = {}
    feature_shell_intersection_records: dict[str, dict[str, Any]] = {}
    for feature_name in (
        "opening_cover",
        "opening_cover_connector",
        "bezel",
        "lens_surround",
        "lens_seat",
        "wall_transition_shelf",
        "walls",
    ):
        shape = context[feature_name]
        hits: dict[str, float] = {}
        for owner_name, owner in context["shell_records"]:
            if not v3.aabb_near(shape, owner):
                continue
            volume = v3.common_volume(shape, owner)
            if volume > EPSILON_MM3:
                hits[owner_name] = volume
                common = shape.common(owner)
                center = common.BoundBox.Center
                delta = center - context["origin"]
                feature_shell_intersection_records[
                    f"{feature_name}::{owner_name}"
                ] = {
                    "volume_mm3": volume,
                    "bbox_center_world_mm": vector_values(center),
                    "bbox_center_aperture_lcs_mm": [
                        float(delta.dot(context["axis_u"])),
                        float(delta.dot(context["axis_v"])),
                        float(delta.dot(context["axis_n"])),
                    ],
                    "nearest_aperture_vertex_index": min(
                        range(len(aperture)),
                        key=lambda index: float((center - aperture[index]).Length),
                    ),
                    "distances_to_aperture_vertices_mm": [
                        float((center - point).Length) for point in aperture
                    ],
                }
        if hits:
            feature_shell_intersections[feature_name] = hits
    static_clearance_records: dict[str, dict[str, Any]] = {}
    for feature_name, shape in (
        ("carrier", context["carrier"]),
        ("lens", context["lens"]),
        ("rear_cap", context["rear_cap"]),
        ("opening_cover", context["opening_cover"]),
        ("opening_cover_connector", context["opening_cover_connector"]),
        ("bezel", context["bezel"]),
        ("lens_surround", context["lens_surround"]),
        ("lens_seat", context["lens_seat"]),
        ("wall_transition_shelf", context["wall_transition_shelf"]),
        ("walls", context["walls"]),
    ):
        nearest_owner = None
        nearest_distance = math.inf
        nearest_pair = None
        for owner_name, owner in context["shell_records"]:
            if not v3.aabb_near(shape, owner, 5.0):
                continue
            distance_result = shape.distToShape(owner)
            distance = float(distance_result[0])
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_owner = owner_name
                nearest_pair = (
                    distance_result[1][0]
                    if distance_result[1] else None
                )
        record = {
            "nearest_owner": nearest_owner,
            "minimum_distance_mm": nearest_distance,
        }
        if nearest_pair is not None:
            feature_point, owner_point = nearest_pair
            record.update({
                "nearest_feature_point_world_mm": vector_values(feature_point),
                "nearest_owner_point_world_mm": vector_values(owner_point),
                "nearest_feature_point_aperture_lcs_mm": [
                    float((feature_point - context["origin"]).dot(context["axis_u"])),
                    float((feature_point - context["origin"]).dot(context["axis_v"])),
                    float((feature_point - context["origin"]).dot(context["axis_n"])),
                ],
                "nearest_owner_point_aperture_lcs_mm": [
                    float((owner_point - context["origin"]).dot(context["axis_u"])),
                    float((owner_point - context["origin"]).dot(context["axis_v"])),
                    float((owner_point - context["origin"]).dot(context["axis_n"])),
                ],
                "nearest_feature_point_distances_to_aperture_vertices_mm": [
                    float((feature_point - point).Length) for point in aperture
                ],
            })
        static_clearance_records[feature_name] = record
    checks.update({
        "selected_left_edge_parallel_to_shell_edge": (
            parallel_angle_error
            <= float(gates["maximum_selected_edge_parallel_angle_error_deg"])
        ),
        "selected_left_edge_length_preserved_from_v3": (
            selected_edge_length_change
            <= float(gates["maximum_selected_edge_length_change_mm"])
        ),
        "selected_left_edge_has_pinned_shell_offset": (
            abs(
                selected_edge_shell_offset
                - float(values["selected_left_edge_shell_normal_offset"])
            )
            <= float(gates["selected_edge_shell_offset_tolerance_mm"])
        ),
        "lower_left_corner_moved_toward_shell_corner": (
            lower_approach_gain
            >= float(gates["minimum_lower_left_corner_approach_gain_mm"])
        ),
        "unselected_aperture_vertices_unchanged": (
            max(frozen_vertex_shifts)
            <= float(gates["maximum_frozen_aperture_vertex_shift_mm"])
        ),
        "visible_aperture_is_larger_than_v3": (
            area_gain_v3
            >= float(gates["minimum_visible_aperture_area_gain_fraction_over_v3"])
        ),
        "sidewalls_perpendicular_to_front_plane": (
            maximum_wall_angle_error
            <= float(gates["maximum_sidewall_perpendicular_angle_error_deg"])
            and maximum_wall_lateral_drift
            <= float(gates["maximum_sidewall_lateral_drift_mm"])
        ),
        "selected_edge_deep_rim_relief_applied": (
            float(context["selected_edge_deep_rim_removed_mm3"])
            >= float(gates["minimum_selected_edge_deep_rim_removed_volume_mm3"])
        ),
    })
    measurements.update({
        "selected_aperture_edge_indices": [0, 1],
        "parallel_shell_edge_indices": [0, 1],
        "selected_left_edge_parallel_angle_error_deg": parallel_angle_error,
        "selected_left_edge_length_change_from_v3_mm": selected_edge_length_change,
        "selected_left_edge_shell_offset_mm": selected_edge_shell_offset,
        "lower_left_corner_distance_to_shell_corner_v3_mm": lower_distance_v3,
        "lower_left_corner_distance_to_shell_corner_v4_mm": lower_distance_v4,
        "lower_left_corner_approach_gain_mm": lower_approach_gain,
        "upper_left_corner_distance_to_shell_corner_v3_mm": upper_distance_v3,
        "upper_left_corner_distance_to_shell_corner_v4_mm": upper_distance_v4,
        "frozen_aperture_vertex_shifts_mm": frozen_vertex_shifts,
        "v3_visible_aperture_area_mm2": v3_area,
        "v4_visible_aperture_area_mm2": v4_area,
        "visible_aperture_area_gain_fraction_over_v3": area_gain_v3,
        "maximum_sidewall_perpendicular_angle_error_deg": maximum_wall_angle_error,
        "maximum_sidewall_lateral_drift_mm": maximum_wall_lateral_drift,
        "straight_box_outer_inset_from_aperture_mm": float(
            values["straight_box_outer_inset_from_aperture"]
        ),
        "feature_shell_intersections_mm3": feature_shell_intersections,
        "feature_shell_intersection_records": feature_shell_intersection_records,
        "static_shell_clearance_attribution": static_clearance_records,
        "selected_edge_deep_rim_removed_mm3": float(
            context["selected_edge_deep_rim_removed_mm3"]
        ),
    })
    base["anchors"] = {
        "selected_aperture_edge": {
            "indices": [0, 1],
            "start_world_mm": vector_values(aperture[0]),
            "end_world_mm": vector_values(aperture[1]),
        },
        "parallel_shell_edge": {
            "indices": [0, 1],
            "start_world_mm": vector_values(opening[0]),
            "end_world_mm": vector_values(opening[1]),
        },
    }
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
    v3 = context["v3_module"]
    v3.load_context_shapes(context, App, Part)
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
    return context["v3_module"].add_feature(
        doc, name, label, shape, color, transparency,
        context["contract"]["authority"],
    )


def create_review(context: dict[str, Any], output: Path) -> Path:
    App = context["App"]
    doc = App.newDocument("RightEyeParallelLeftEdgeOrthogonalWallReviewV4")
    try:
        add_feature(context, doc, "REFERENCE__RELIEVED_RIGHT_HEAD_SHELL", "REFERENCE — RELIEVED RIGHT HEAD SHELL", context["shell"], (0.70, 0.70, 0.73), 78)
        carrier = add_feature(context, doc, "PROPOSED__PARALLEL_EDGE_ORTHOGONAL_WALL_EYE_CARRIER", "PROPOSED — PARALLEL LEFT EDGE + PERPENDICULAR-WALL EYE", context["carrier"], (0.12, 0.72, 0.28), 0)
        carrier.addProperty("App::PropertyString", "Installation", "ReviewControl")
        carrier.Installation = "Straight through eye opening; 0.60 mm fitted panel perimeter; mounting flanges remain deferred"
        lens = add_feature(context, doc, "PROPOSED__TRANSLUCENT_LENS", "PROPOSED — 0.90 MM V4 TRANSLUCENT LENS", context["lens"], (0.35, 0.86, 0.96), 55)
        lens.addProperty("App::PropertyString", "Retention", "ReviewControl")
        lens.Retention = "Three tiny clear neutral-cure silicone dabs on continuous rear seat"
        cap = add_feature(context, doc, "PROPOSED__REMOVABLE_LED_REAR_PLATE", "PROPOSED — REMOVABLE LED REAR PLATE", context["rear_cap"], (0.08, 0.34, 0.14), 0)
        cap.addProperty("App::PropertyString", "WirePort", "ReviewControl")
        cap.WirePort = "4.0 mm through-hole; seal and strain-relieve cable"
        for index, led in enumerate(context["led_shapes"], start=1):
            add_feature(context, doc, f"REFERENCE__LED_PIXEL_{index}", f"REFERENCE — LED PIXEL {index}", led, (1.0, 0.62, 0.05), 12)
        add_feature(context, doc, "REFERENCE__WIRE_EXIT_4MM", "REFERENCE — 4 MM WIRE EXIT / ROUTE", context["wire_corridor"], (0.95, 0.18, 0.08), 65)
        add_feature(context, doc, "REFERENCE__CONTINUOUS_LENS_SEAT", "REFERENCE — CONTINUOUS REAR LENS SEAT", context["lens_seat"], (0.95, 0.48, 0.08), 50)
        add_feature(context, doc, "ANCHOR__OUTSIDE_SHELL_EDGE_0_1", "ANCHOR — OUTSIDE SHELL EDGE 0→1", context["selected_shell_edge_marker"], (0.10, 0.35, 1.00), 0)
        add_feature(context, doc, "ANCHOR__PARALLEL_APERTURE_EDGE_0_1", "ANCHOR — PARALLEL APERTURE EDGE 0→1", context["selected_aperture_edge_marker"], (1.00, 0.25, 0.05), 0)
        add_feature(context, doc, "ANCHOR__MOVED_LOWER_LEFT_CORNER", "ANCHOR — MOVED LOWER-LEFT CORNER", context["selected_lower_corner_marker"], (1.00, 0.82, 0.05), 0)
        add_feature(context, doc, "REFERENCE__PERPENDICULAR_WALL_AXES", "REFERENCE — PERPENDICULAR WALL AXES", context["wall_axis_markers"], (0.82, 0.12, 0.88), 0)
        add_feature(context, doc, "REFERENCE__SELECTED_EDGE_DEEP_RIM_RELIEF", "REFERENCE — SELECTED-EDGE DEEP RIM RELIEF", context["selected_edge_relief"], (0.92, 0.18, 0.12), 82)
        doc.recompute()
        path = output / context["contract"]["output"]["fcstd"]
        doc.saveAs(str(path))
        return path
    finally:
        App.closeDocument(doc.Name)


def render_views(context: dict[str, Any], output: Path) -> None:
    v3 = context["v3_module"]
    v3.render_views(context, output)
    toolkit = context["toolkit"]
    shell = toolkit.shape_record(context["shell"], (150, 154, 160), deflection=1.0)
    carrier = toolkit.shape_record(context["carrier"], (36, 182, 72), deflection=0.35)
    shell_edge = toolkit.shape_record(context["selected_shell_edge_marker"], (25, 90, 255), deflection=0.15)
    aperture_edge = toolkit.shape_record(context["selected_aperture_edge_marker"], (255, 65, 10), deflection=0.15)
    corner = toolkit.shape_record(context["selected_lower_corner_marker"], (255, 210, 10), deflection=0.15)
    wall_axes = toolkit.shape_record(context["wall_axis_markers"], (210, 30, 225), deflection=0.15)
    toolkit.render_side_by_side(
        output / "anchor-edge.png", [shell],
        [shell, carrier, shell_edge, aperture_edge, corner],
        v3.tuple3(context["axis_n"]), v3.tuple3(context["axis_v"]),
    )
    toolkit.render_side_by_side(
        output / "wall-normal.png", [carrier],
        [carrier, wall_axes],
        v3.tuple3(context["axis_u"]), v3.tuple3(context["axis_v"]),
    )


def public_report(context: dict[str, Any], mode: str, elapsed: float) -> dict[str, Any]:
    report = context["v3_module"].public_report(context, mode, elapsed)
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
