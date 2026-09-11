#!/usr/bin/env python3
"""Generate the single V2 C002 rounded-terminal socket prototype.

The generator opens the hash-pinned canonical V34 FCStd, saves a disposable
candidate copy, and replaces only RETAINED_RIGHT_UPPER_C002_V34.Shape.  It
restores material only in the final Route 2 terminal interval of the existing
20.50 mm cavity, then subtracts the approved 23/21 mm lead-in/straight profile
with a linearly increasing terminal corner radius.

No helper object is added to the saved document.  The protected-root common,
profile references, sections, and rail gauges exist only in memory for the
requested review PNGs.  This script writes no validation report or release
artifact.
"""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import math
import struct
import sys
import zlib
from pathlib import Path
from typing import Any, Sequence

import FreeCAD as App
import Mesh
import Part


ITERATION_ID = "c002-rounded-terminal-profile-prototype-v1"
TARGET_OBJECT = "RETAINED_RIGHT_UPPER_C002_V34"
PROTECTED_ROOT_OBJECT = "RETAINED_RIGHT_UPPER_C042_V34"
IMAGE_WIDTH = 1000
IMAGE_HEIGHT = 750


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    return parser.parse_args(argv)


def repository_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("cannot locate repository root")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path}: root must be an object")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def vector(values: Sequence[float]) -> App.Vector:
    return App.Vector(float(values[0]), float(values[1]), float(values[2]))


def normalized(value: App.Vector, label: str) -> App.Vector:
    result = App.Vector(value)
    if result.Length <= 1.0e-12:
        raise RuntimeError(f"{label} has zero length")
    result.normalize()
    return result


def close_enough(first: float, second: float, tolerance: float = 1.0e-9) -> bool:
    return abs(float(first) - float(second)) <= tolerance


def points_match(
    first: App.Vector,
    second: App.Vector,
    tolerance: float = 1.0e-5,
) -> bool:
    return (first - second).Length <= tolerance


def point_from_local(
    local_u: float,
    local_v: float,
    local_t: float,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
) -> App.Vector:
    return origin + axis_u * local_u + axis_v * local_v + axis_t * local_t


def closed_wire(points: Sequence[App.Vector]) -> Part.Wire:
    if len(points) < 3:
        raise RuntimeError("closed wire requires at least three points")
    return Part.makePolygon([*points, points[0]])


def square_wire(
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    station_t: float,
    half_width: float,
) -> Part.Wire:
    points = [
        point_from_local(-half_width, -half_width, station_t, origin, axis_u, axis_v, axis_t),
        point_from_local(half_width, -half_width, station_t, origin, axis_u, axis_v, axis_t),
        point_from_local(half_width, half_width, station_t, origin, axis_u, axis_v, axis_t),
        point_from_local(-half_width, half_width, station_t, origin, axis_u, axis_v, axis_t),
    ]
    return closed_wire(points)


def rounded_square_wire(
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    station_t: float,
    half_width: float,
    radius: float,
) -> Part.Wire:
    if radius < -1.0e-12 or radius > half_width + 1.0e-12:
        raise RuntimeError("rounded-square radius is outside the profile")
    if radius <= 1.0e-12:
        return square_wire(origin, axis_u, axis_v, axis_t, station_t, half_width)

    tangent = half_width - radius
    root_two = math.sqrt(2.0)

    def local(local_u: float, local_v: float) -> App.Vector:
        return point_from_local(
            local_u,
            local_v,
            station_t,
            origin,
            axis_u,
            axis_v,
            axis_t,
        )

    bottom_right = local(tangent, -half_width)
    bottom_left = local(-tangent, -half_width)
    left_bottom = local(-half_width, -tangent)
    left_top = local(-half_width, tangent)
    top_left = local(-tangent, half_width)
    top_right = local(tangent, half_width)
    right_top = local(half_width, tangent)
    right_bottom = local(half_width, -tangent)

    edges = [
        Part.makeLine(bottom_right, bottom_left),
        Part.Arc(
            bottom_left,
            local(-tangent - radius / root_two, -tangent - radius / root_two),
            left_bottom,
        ).toShape(),
        Part.makeLine(left_bottom, left_top),
        Part.Arc(
            left_top,
            local(-tangent - radius / root_two, tangent + radius / root_two),
            top_left,
        ).toShape(),
        Part.makeLine(top_left, top_right),
        Part.Arc(
            top_right,
            local(tangent + radius / root_two, tangent + radius / root_two),
            right_top,
        ).toShape(),
        Part.makeLine(right_top, right_bottom),
        Part.Arc(
            right_bottom,
            local(tangent + radius / root_two, -tangent - radius / root_two),
            bottom_right,
        ).toShape(),
    ]
    return Part.Wire(edges)


def corner_removal_wire(
    sign_u: float,
    sign_v: float,
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    station_t: float,
    half_width: float,
    radius: float,
) -> Part.Wire:
    corner = point_from_local(
        sign_u * half_width,
        sign_v * half_width,
        station_t,
        origin,
        axis_u,
        axis_v,
        axis_t,
    )
    tangent_v = point_from_local(
        sign_u * half_width,
        sign_v * (half_width - radius),
        station_t,
        origin,
        axis_u,
        axis_v,
        axis_t,
    )
    tangent_u = point_from_local(
        sign_u * (half_width - radius),
        sign_v * half_width,
        station_t,
        origin,
        axis_u,
        axis_v,
        axis_t,
    )
    diagonal = half_width - radius + radius / math.sqrt(2.0)
    arc_midpoint = point_from_local(
        sign_u * diagonal,
        sign_v * diagonal,
        station_t,
        origin,
        axis_u,
        axis_v,
        axis_t,
    )
    return Part.Wire(
        [
            Part.makeLine(corner, tangent_v),
            Part.Arc(tangent_v, arc_midpoint, tangent_u).toShape(),
            Part.makeLine(tangent_u, corner),
        ]
    )


def local_box(
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    u_min: float,
    u_max: float,
    v_min: float,
    v_max: float,
    t_min: float,
    t_max: float,
) -> Part.Shape:
    face = Part.Face(
        closed_wire(
            [
                point_from_local(u_min, v_min, t_min, origin, axis_u, axis_v, axis_t),
                point_from_local(u_min, v_max, t_min, origin, axis_u, axis_v, axis_t),
                point_from_local(u_min, v_max, t_max, origin, axis_u, axis_v, axis_t),
                point_from_local(u_min, v_min, t_max, origin, axis_u, axis_v, axis_t),
            ]
        )
    )
    return face.extrude(axis_u * (u_max - u_min))


def require_single_solid(shape: Part.Shape, label: str) -> None:
    if shape.isNull():
        raise RuntimeError(f"{label}: null shape")
    if not shape.isValid():
        raise RuntimeError(f"{label}: invalid shape")
    if not shape.isClosed():
        raise RuntimeError(f"{label}: open shape")
    if len(shape.Solids) != 1:
        raise RuntimeError(f"{label}: expected one solid, found {len(shape.Solids)}")


def exact_route_2_solution(evidence: dict[str, Any]) -> dict[str, Any]:
    route = evidence.get("route_2_terminal_radius", {})
    for solution in route.get("solutions", []):
        if close_enough(solution.get("required_gap_mm", -1.0), 2.4):
            return solution
    raise RuntimeError("pinned evidence lacks the Route 2 2.4 mm solution")


def verify_route_2_parameters(
    parameters: dict[str, Any],
    evidence: dict[str, Any],
) -> None:
    solution = exact_route_2_solution(evidence)
    profile = parameters["profile"]
    root = parameters["protected_root"]
    rail = parameters["physical_prototype_rail"]
    checks = [
        (profile["terminal_stop_radius_mm"], solution["stop_radius_mm"], "terminal stop radius"),
        (profile["rounded_transition_length_mm"], solution["transition_length_mm"], "transition length"),
        (profile["transition_start_t_mm"], solution["transition_start_t_mm"], "transition start"),
        (profile["worst_insertion_path_radius_mm"], solution["maximum_radius_encountered_by_seated_rail_mm"], "seated-path radius"),
        (profile["additive_infill_start_t_mm"], solution["additive_infill_start_t_mm"], "infill start"),
        (profile["additive_infill_axial_length_mm"], solution["additive_infill_axial_length_mm"], "infill length"),
        (root["exact_common_volume_mm3"], evidence["protected_root"]["exact_volume_mm3"], "protected common volume"),
        (rail["minimum_outside_corner_radius_mm"], solution["tube_radius_for_0_5mm_clearance_mm_for_19_00_to_19_05"][1], "tube corner radius"),
    ]
    for actual, expected, label in checks:
        if not close_enough(actual, expected, 1.0e-11):
            raise RuntimeError(f"contract {label} does not match pinned Route 2 evidence")


def build_target_void(
    parameters: dict[str, Any],
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
) -> tuple[Part.Shape, Part.Shape, list[Part.Shape]]:
    profile = parameters["profile"]
    mouth_t = float(profile["mouth_t_mm"])
    lead_in = float(profile["lead_in_depth_mm"])
    stop_t = float(profile["stop_t_mm"])
    straight_half = float(profile["straight_across_flats_mm"]) / 2.0
    mouth_half = float(profile["mouth_across_flats_mm"]) / 2.0
    transition_start = float(profile["transition_start_t_mm"])
    stop_radius = float(profile["terminal_stop_radius_mm"])
    lead_transition_t = mouth_t + lead_in
    extension = 0.20

    full_square_void = Part.makeLoft(
        [
            square_wire(
                origin,
                axis_u,
                axis_v,
                axis_t,
                mouth_t - extension,
                mouth_half + extension,
            ),
            square_wire(
                origin,
                axis_u,
                axis_v,
                axis_t,
                lead_transition_t,
                straight_half,
            ),
            square_wire(
                origin,
                axis_u,
                axis_v,
                axis_t,
                stop_t,
                straight_half,
            ),
        ],
        True,
        True,
    )
    require_single_solid(full_square_void, "extended lead-in and straight void")

    corner_cutters: list[Part.Shape] = []
    rounded_void = full_square_void
    for sign_u, sign_v in ((1.0, 1.0), (1.0, -1.0), (-1.0, -1.0), (-1.0, 1.0)):
        apex = Part.Vertex(
            point_from_local(
                sign_u * straight_half,
                sign_v * straight_half,
                transition_start,
                origin,
                axis_u,
                axis_v,
                axis_t,
            )
        )
        stop_wire = corner_removal_wire(
            sign_u,
            sign_v,
            origin,
            axis_u,
            axis_v,
            axis_t,
            stop_t,
            straight_half,
            stop_radius,
        )
        cutter = Part.makeLoft([apex, stop_wire], True, True)
        require_single_solid(cutter, "terminal rounded-corner removal")
        corner_cutters.append(cutter)
        rounded_void = rounded_void.cut(cutter)

    rounded_void = rounded_void.removeSplitter()
    require_single_solid(rounded_void, "Route 2 target void")

    review_clip = local_box(
        origin,
        axis_u,
        axis_v,
        axis_t,
        -20.0,
        20.0,
        -20.0,
        20.0,
        mouth_t,
        stop_t,
    )
    review_void = rounded_void.common(review_clip).removeSplitter()
    require_single_solid(review_void, "exact-depth Route 2 review void")
    return rounded_void, review_void, corner_cutters


def build_candidate_shape(
    original_shape: Part.Shape,
    stop_face: Part.Face,
    parameters: dict[str, Any],
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
) -> tuple[Part.Shape, dict[str, Any]]:
    profile = parameters["profile"]
    cut_void, review_void, corner_cutters = build_target_void(
        parameters,
        origin,
        axis_u,
        axis_v,
        axis_t,
    )

    infill_length = float(profile["additive_infill_axial_length_mm"])
    boolean_overlap = 0.02
    plug_face = stop_face.copy()
    plug_face.translate(axis_t * boolean_overlap)
    restoration_plug = plug_face.extrude(
        -axis_t * (infill_length + boolean_overlap)
    )
    require_single_solid(restoration_plug, "terminal restoration plug")

    restored_owner = original_shape.fuse(restoration_plug).removeSplitter()
    require_single_solid(restored_owner, "C002 with terminal restoration")
    candidate_shape = restored_owner.cut(cut_void).removeSplitter()
    require_single_solid(candidate_shape, "C002 Route 2 replacement")

    old_void = stop_face.extrude(
        -axis_t * float(profile["exact_clear_depth_mm"])
    ).removeSplitter()
    require_single_solid(old_void, "baseline 20.50 mm void reference")
    old_terminal = stop_face.extrude(-axis_t * infill_length).removeSplitter()
    infill_visual = old_terminal.cut(review_void).removeSplitter()
    if infill_visual.isNull():
        raise RuntimeError("terminal infill review shape is null")

    return candidate_shape, {
        "target_void": review_void,
        "old_void": old_void,
        "old_terminal": old_terminal,
        "infill_visual": infill_visual,
        "corner_cutters": corner_cutters,
    }


def tuple3(value: Any) -> tuple[float, float, float]:
    if isinstance(value, App.Vector):
        return float(value.x), float(value.y), float(value.z)
    return float(value[0]), float(value[1]), float(value[2])


def transform_point(placement: App.Placement, value: Any) -> tuple[float, float, float]:
    transformed = placement.multVec(vector(tuple3(value)))
    return transformed.x, transformed.y, transformed.z


def shape_record(
    shape: Part.Shape,
    color: tuple[int, int, int],
    alpha: int = 255,
    edge: bool = False,
    deflection: float = 1.0,
    placement: App.Placement | None = None,
) -> dict[str, Any]:
    points, facets = shape.tessellate(deflection)
    active_placement = placement or App.Placement()
    return {
        "vertices": [transform_point(active_placement, point) for point in points],
        "triangles": [tuple(int(index) for index in facet[:3]) for facet in facets],
        "color": color,
        "alpha": int(alpha),
        "edge": bool(edge),
    }


def mesh_record(
    mesh: Mesh.Mesh,
    color: tuple[int, int, int],
    alpha: int = 255,
    edge: bool = False,
    placement: App.Placement | None = None,
) -> dict[str, Any]:
    points, facets = mesh.Topology
    active_placement = placement or App.Placement()
    return {
        "vertices": [transform_point(active_placement, point) for point in points],
        "triangles": [tuple(int(index) for index in facet[:3]) for facet in facets],
        "color": color,
        "alpha": int(alpha),
        "edge": bool(edge),
    }


def object_color(name: str) -> tuple[int, int, int]:
    if name == TARGET_OBJECT:
        return 32, 187, 225
    if name == PROTECTED_ROOT_OBJECT:
        return 77, 166, 92
    if "EAR" in name:
        return 180, 150, 108
    if "PANEL" in name:
        return 242, 154, 55
    if "LOWER" in name:
        return 105, 112, 121
    if "C001" in name:
        return 82, 151, 102
    return 165, 171, 180


def document_records(document: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for obj in document.Objects:
        placement = obj.Placement if hasattr(obj, "Placement") else App.Placement()
        if hasattr(obj, "Shape") and not obj.Shape.isNull():
            records.append(
                shape_record(
                    obj.Shape,
                    object_color(obj.Name),
                    255,
                    obj.Name == TARGET_OBJECT,
                    0.9 if obj.Name == TARGET_OBJECT else 1.7,
                    placement,
                )
            )
        elif hasattr(obj, "Mesh") and obj.Mesh.CountFacets > 0:
            records.append(mesh_record(obj.Mesh, object_color(obj.Name), 255, False, placement))
    return records


def dot_tuple(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> float:
    return sum(first[index] * second[index] for index in range(3))


def subtract_tuple(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> tuple[float, float, float]:
    return tuple(first[index] - second[index] for index in range(3))  # type: ignore[return-value]


def cross_tuple(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def normalize_tuple(
    value: tuple[float, float, float],
) -> tuple[float, float, float]:
    length = math.sqrt(dot_tuple(value, value))
    if length <= 1.0e-12:
        raise RuntimeError("render camera vector has zero length")
    return tuple(component / length for component in value)  # type: ignore[return-value]


def blend_pixel(
    pixels: bytearray,
    width: int,
    x_value: int,
    y_value: int,
    color: tuple[int, int, int],
    alpha: int,
) -> None:
    if not (0 <= x_value < width and 0 <= y_value < len(pixels) // (width * 3)):
        return
    offset = (y_value * width + x_value) * 3
    if alpha >= 255:
        pixels[offset : offset + 3] = bytes(color)
        return
    inverse = 255 - alpha
    for channel in range(3):
        pixels[offset + channel] = (
            color[channel] * alpha + pixels[offset + channel] * inverse
        ) // 255


def draw_line(
    pixels: bytearray,
    width: int,
    height: int,
    start: tuple[float, float],
    end: tuple[float, float],
    color: tuple[int, int, int],
    alpha: int,
) -> None:
    x0, y0 = int(round(start[0])), int(round(start[1]))
    x1, y1 = int(round(end[0])), int(round(end[1]))
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    error = dx + dy
    while True:
        if 0 <= x0 < width and 0 <= y0 < height:
            blend_pixel(pixels, width, x0, y0, color, alpha)
        if x0 == x1 and y0 == y1:
            break
        twice = 2 * error
        if twice >= dy:
            error += dy
            x0 += sx
        if twice <= dx:
            error += dx
            y0 += sy


def fill_triangle(
    pixels: bytearray,
    width: int,
    height: int,
    points: Sequence[tuple[float, float]],
    color: tuple[int, int, int],
    alpha: int,
) -> None:
    minimum_y = max(0, int(math.floor(min(point[1] for point in points))))
    maximum_y = min(height - 1, int(math.ceil(max(point[1] for point in points))))
    for y_value in range(minimum_y, maximum_y + 1):
        scan_y = y_value + 0.5
        intersections = []
        for index, first in enumerate(points):
            second = points[(index + 1) % 3]
            low = min(first[1], second[1])
            high = max(first[1], second[1])
            if high - low <= 1.0e-9 or not (low <= scan_y < high):
                continue
            ratio = (scan_y - first[1]) / (second[1] - first[1])
            intersections.append(first[0] + ratio * (second[0] - first[0]))
        if len(intersections) < 2:
            continue
        start_x = max(0, int(math.ceil(min(intersections))))
        end_x = min(width - 1, int(math.floor(max(intersections))))
        if end_x < start_x:
            continue
        if alpha >= 255:
            offset = (y_value * width + start_x) * 3
            pixels[offset : offset + (end_x - start_x + 1) * 3] = bytes(color) * (
                end_x - start_x + 1
            )
        else:
            for x_value in range(start_x, end_x + 1):
                blend_pixel(pixels, width, x_value, y_value, color, alpha)


def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + chunk_type
        + data
        + struct.pack(">I", binascii.crc32(chunk_type + data) & 0xFFFFFFFF)
    )


def write_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    rows = []
    stride = width * 3
    for y_value in range(height):
        start = y_value * stride
        rows.append(b"\x00" + bytes(pixels[start : start + stride]))
    payload = zlib.compress(b"".join(rows), 7)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", payload)
        + png_chunk(b"IEND", b"")
    )


def render_scene(
    path: Path,
    records: Sequence[dict[str, Any]],
    view_direction: tuple[float, float, float],
    up_hint: tuple[float, float, float],
    margin: int = 46,
) -> None:
    view = normalize_tuple(view_direction)
    up_seed = normalize_tuple(up_hint)
    right = normalize_tuple(cross_tuple(view, up_seed))
    up = normalize_tuple(cross_tuple(right, view))
    projected_records = []
    all_x: list[float] = []
    all_y: list[float] = []
    for record in records:
        projected = []
        for point in record["vertices"]:
            projected_point = (
                dot_tuple(point, right),
                dot_tuple(point, up),
                dot_tuple(point, view),
            )
            projected.append(projected_point)
            all_x.append(projected_point[0])
            all_y.append(projected_point[1])
        projected_records.append((record, projected))
    if not all_x or not all_y:
        raise RuntimeError(f"{path}: no renderable geometry")
    span_x = max(max(all_x) - min(all_x), 1.0)
    span_y = max(max(all_y) - min(all_y), 1.0)
    scale = min(
        (IMAGE_WIDTH - 2 * margin) / span_x,
        (IMAGE_HEIGHT - 2 * margin) / span_y,
    )
    center_x = (min(all_x) + max(all_x)) / 2.0
    center_y = (min(all_y) + max(all_y)) / 2.0

    triangles = []
    for record, projected in projected_records:
        for indices in record["triangles"]:
            p3d = [record["vertices"][index] for index in indices]
            p2d = [
                (
                    IMAGE_WIDTH / 2.0 + (projected[index][0] - center_x) * scale,
                    IMAGE_HEIGHT / 2.0 - (projected[index][1] - center_y) * scale,
                )
                for index in indices
            ]
            first_edge = subtract_tuple(p3d[1], p3d[0])
            second_edge = subtract_tuple(p3d[2], p3d[0])
            normal = cross_tuple(first_edge, second_edge)
            if math.sqrt(dot_tuple(normal, normal)) <= 1.0e-12:
                continue
            light = normalize_tuple(
                (
                    -view[0] + up[0] * 0.35 - right[0] * 0.20,
                    -view[1] + up[1] * 0.35 - right[1] * 0.20,
                    -view[2] + up[2] * 0.35 - right[2] * 0.20,
                )
            )
            lighting = 0.58 + 0.42 * abs(dot_tuple(normalize_tuple(normal), light))
            base = record["color"]
            shaded = tuple(max(0, min(255, int(channel * lighting))) for channel in base)
            depth = sum(projected[index][2] for index in indices) / 3.0
            triangles.append((depth, p2d, shaded, int(record["alpha"]), bool(record["edge"])))
    triangles.sort(key=lambda item: item[0], reverse=True)
    pixels = bytearray((246, 247, 249) * (IMAGE_WIDTH * IMAGE_HEIGHT))
    edge_queue = []
    for _, points, color, alpha, edge in triangles:
        fill_triangle(pixels, IMAGE_WIDTH, IMAGE_HEIGHT, points, color, alpha)
        if edge:
            edge_queue.append(points)
    for points in edge_queue:
        for index in range(3):
            draw_line(
                pixels,
                IMAGE_WIDTH,
                IMAGE_HEIGHT,
                points[index],
                points[(index + 1) % 3],
                (20, 55, 68),
                105,
            )
    write_png(path, IMAGE_WIDTH, IMAGE_HEIGHT, pixels)


def rail_gauge(
    parameters: dict[str, Any],
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    station_t: float,
) -> Part.Shape:
    rail = parameters["physical_prototype_rail"]
    profile_face = Part.Face(
        rounded_square_wire(
            origin,
            axis_u,
            axis_v,
            axis_t,
            station_t - 0.02,
            float(rail["outside_across_flats_mm"]) / 2.0,
            float(rail["minimum_outside_corner_radius_mm"]),
        )
    )
    return profile_face.extrude(axis_t * 0.02)


def render_rail_position(
    path: Path,
    target_shape: Part.Shape,
    target_void: Part.Shape,
    parameters: dict[str, Any],
    origin: App.Vector,
    axis_u: App.Vector,
    axis_v: App.Vector,
    axis_t: App.Vector,
    station_t: float,
) -> None:
    slice_box = local_box(
        origin,
        axis_u,
        axis_v,
        axis_t,
        -20.0,
        20.0,
        -20.0,
        20.0,
        station_t,
        station_t + 0.02,
    )
    material_slice = target_shape.common(slice_box).removeSplitter()
    cavity_slice = target_void.common(slice_box).removeSplitter()
    rail = rail_gauge(parameters, origin, axis_u, axis_v, axis_t, station_t)
    records = [
        shape_record(material_slice, (125, 132, 142), 225, True, 0.15),
        shape_record(cavity_slice, (50, 185, 226), 95, True, 0.12),
        shape_record(rail, (247, 151, 40), 245, True, 0.10),
    ]
    render_scene(path, records, tuple3(axis_t), tuple3(axis_v), margin=72)


def render_review_pack(
    document: Any,
    target: Any,
    protected_root: Any,
    protected_common: Part.Shape,
    parameters: dict[str, Any],
    construction: dict[str, Any],
    root: Path,
    contract: dict[str, Any],
) -> None:
    fixed_views = {
        "front": ((0.0, 1.0, 0.0), (0.0, 0.0, 1.0)),
        "rear": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
        "left": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        "right": ((-1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
        "top": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
        "bottom": ((0.0, 0.0, 1.0), (0.0, -1.0, 0.0)),
    }
    whole_records = document_records(document)
    for name in ("front", "rear", "left", "right", "top", "bottom"):
        direction, up = fixed_views[name]
        render_scene(root / contract["output"]["review_files"][name], whole_records, direction, up)

    origin = construction["origin"]
    axis_u = construction["axis_u"]
    axis_v = construction["axis_v"]
    axis_t = construction["axis_t"]
    target_void = construction["target_void"]
    old_void = construction["old_void"]
    infill = construction["infill_visual"]
    extra = parameters["review_artifacts"]

    section_box = local_box(
        origin,
        axis_u,
        axis_v,
        axis_t,
        -60.0,
        0.0,
        -60.0,
        60.0,
        -40.0,
        12.0,
    )
    longitudinal_section = target.Shape.common(section_box).removeSplitter()
    render_scene(
        root / extra["longitudinal_socket_section"],
        [
            shape_record(longitudinal_section, (224, 132, 44), 255, True, 0.45),
            shape_record(target_void, (39, 183, 224), 90, True, 0.30),
            shape_record(infill, (236, 76, 54), 245, True, 0.20),
        ],
        tuple3(axis_u),
        tuple3(axis_v),
    )

    blind_corner_box = local_box(
        origin,
        axis_u,
        axis_v,
        axis_t,
        7.0,
        17.0,
        7.0,
        17.0,
        -2.2,
        6.5,
    )
    render_scene(
        root / extra["blind_end_rounded_corner_close_up"],
        [
            shape_record(old_void.common(blind_corner_box), (224, 69, 65), 90, True, 0.12),
            shape_record(target_void.common(blind_corner_box), (38, 184, 224), 175, True, 0.10),
            shape_record(infill.common(blind_corner_box), (245, 151, 45), 250, True, 0.08),
            shape_record(protected_common.common(blind_corner_box), (184, 64, 205), 220, True, 0.10),
        ],
        tuple3(axis_t),
        tuple3(axis_v),
        margin=70,
    )

    overlay_direction = normalized(axis_u * 0.68 + axis_v * 0.58 + axis_t * 0.45, "root overlay camera")
    render_scene(
        root / extra["c002_c042_protected_root_overlay"],
        [
            shape_record(target.Shape, (39, 183, 224), 95, True, 0.65),
            shape_record(protected_root.Shape, (73, 170, 91), 105, True, 0.65),
            shape_record(protected_common, (188, 61, 205), 245, True, 0.30),
            shape_record(target_void, (246, 158, 47), 70, True, 0.35),
        ],
        tuple3(overlay_direction),
        tuple3(axis_v),
    )

    render_scene(
        root / extra["baseline_candidate_profile_overlay"],
        [
            shape_record(old_void, (224, 69, 65), 95, True, 0.32),
            shape_record(target_void, (38, 184, 224), 125, True, 0.28),
            shape_record(infill, (245, 151, 45), 245, True, 0.16),
        ],
        tuple3(axis_u),
        tuple3(axis_v),
        margin=70,
    )

    stations = parameters["rail_review_stations_t_mm"]
    render_rail_position(
        root / extra["rail_position_mouth"],
        target.Shape,
        target_void,
        parameters,
        origin,
        axis_u,
        axis_v,
        axis_t,
        float(stations["mouth"]),
    )
    render_rail_position(
        root / extra["rail_position_transition"],
        target.Shape,
        target_void,
        parameters,
        origin,
        axis_u,
        axis_v,
        axis_t,
        float(stations["terminal_transition_start"]),
    )
    render_rail_position(
        root / extra["rail_position_seated_stop"],
        target.Shape,
        target_void,
        parameters,
        origin,
        axis_u,
        axis_v,
        axis_t,
        float(stations["seated_rail_end"]),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = repository_root(args.contract)
    baseline = load_json(args.baseline)
    contract = load_json(args.contract)
    if contract.get("iteration_id") != ITERATION_ID:
        raise RuntimeError("iteration ID mismatch")
    if contract.get("target_object") != TARGET_OBJECT:
        raise RuntimeError("target object mismatch")
    mutations = contract.get("allowed_mutations", [])
    if len(mutations) != 1 or mutations[0].get("kind") != "replace_geometry":
        raise RuntimeError("generator requires exactly one replace_geometry mutation")
    if mutations[0].get("object") != TARGET_OBJECT:
        raise RuntimeError("mutation object mismatch")
    parameters = mutations[0]["parameters"]

    evidence_spec = parameters["route_2_evidence"]
    evidence_path = root / evidence_spec["path"]
    if sha256_file(evidence_path) != evidence_spec["sha256"]:
        raise RuntimeError("Route 2 evidence hash mismatch")
    evidence = load_json(evidence_path)
    verify_route_2_parameters(parameters, evidence)

    baseline_path = root / baseline["assembly"]["path"]
    if sha256_file(baseline_path) != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 hash mismatch")
    output_dir = root / contract["output"]["directory"]
    candidate_path = root / contract["output"]["candidate_fcstd"]
    output_dir.mkdir(parents=True, exist_ok=False)
    candidate_path.parent.mkdir(parents=True, exist_ok=True)

    frame = parameters["rail_frame"]
    origin = vector(frame["origin_head_mm"])
    axis_t = normalized(vector(frame["t_axis"]), "t axis")
    axis_u = normalized(vector(frame["u_axis"]), "u axis")
    axis_v = normalized(vector(frame["v_axis"]), "v axis")
    if abs(axis_u.dot(axis_v)) > 1.0e-9 or abs(axis_u.dot(axis_t)) > 1.0e-9 or abs(axis_v.dot(axis_t)) > 1.0e-9:
        raise RuntimeError("rail frame is not orthogonal")
    if (axis_u.cross(axis_v) - axis_t).Length > 1.0e-9:
        raise RuntimeError("rail frame handedness differs from u cross v = t")

    print("STAGE 1/6 pinned baseline, evidence, and Route 2 parameters verified", flush=True)
    document = App.openDocument(str(baseline_path))
    try:
        document.saveAs(str(candidate_path))
        target = document.getObject(TARGET_OBJECT)
        protected_root = document.getObject(PROTECTED_ROOT_OBJECT)
        if target is None or protected_root is None:
            raise RuntimeError("canonical V34 lacks C002 or protected C042")
        if target.TypeId != "Part::Feature":
            raise RuntimeError(f"unexpected target type {target.TypeId}")
        original_name = target.Name
        original_label = target.Label
        original_placement = App.Placement(target.Placement)
        if original_placement != App.Placement():
            raise RuntimeError("target placement is not the approved identity placement")

        original_shape = target.Shape.copy()
        if len(original_shape.Faces) < 164:
            raise RuntimeError("target lacks approved Face164 stop anchor")
        stop_face = original_shape.Faces[163]
        back_face = original_shape.Faces[9]
        profile = parameters["profile"]
        if not close_enough(stop_face.Area, float(parameters["anchors"]["stop_face_area_mm2"]), 1.0e-6):
            raise RuntimeError("Face164 area differs from approved stop anchor")
        if not points_match(stop_face.CenterOfMass, origin):
            raise RuntimeError("Face164 centroid differs from approved rail-frame origin")
        termination_anchor = back_face.CenterOfMass - axis_t * float(profile["back_face_offset_along_minus_t_mm"])
        if not points_match(termination_anchor, origin):
            raise RuntimeError("Face10 minus-t offset does not coincide with Face164")

        protected_common = original_shape.common(protected_root.Shape).removeSplitter()
        if protected_common.isNull():
            raise RuntimeError("baseline C002/C042 protected-root overlay is null")

        candidate_shape, construction = build_candidate_shape(
            original_shape,
            stop_face,
            parameters,
            origin,
            axis_u,
            axis_v,
            axis_t,
        )
        print("STAGE 2/6 single Route 2 internal-profile replacement constructed", flush=True)
        target.Shape = candidate_shape
        document.recompute()
        if target.Name != original_name or target.Label != original_label:
            raise RuntimeError("target identity changed during replacement")
        if target.Placement != original_placement:
            raise RuntimeError("target placement changed during replacement")
        document.save()
        print("STAGE 3/6 candidate saved with only C002.Shape replaced", flush=True)

        construction.update(
            {
                "origin": origin,
                "axis_u": axis_u,
                "axis_v": axis_v,
                "axis_t": axis_t,
            }
        )
        render_review_pack(
            document,
            target,
            protected_root,
            protected_common,
            parameters,
            construction,
            root,
            contract,
        )
        print("STAGE 4/6 six fixed whole-head views rendered", flush=True)
        print("STAGE 5/6 seven requested focused review views rendered", flush=True)
    finally:
        App.closeDocument(document.Name)

    if sha256_file(baseline_path) != baseline["assembly"]["sha256"]:
        raise RuntimeError("canonical V34 changed during generation")
    print("STAGE 6/6 canonical V34 remains hash-identical", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
