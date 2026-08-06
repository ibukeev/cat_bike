#!/usr/bin/env python3
"""Generate printable mirror-facet cap prototypes from four real Gate 8 facets.

The printed parts are thin, flat cosmetic backers. Their smooth build-plate
faces receive adhesive mirror film after printing. This generator exports
individual STLs, one ready-to-slice plate per thickness, a 1:1 SVG placement
guide, a smaller first-physical-trial plate, a part manifest, and an automatic
validation report.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402


Point2 = tuple[float, float]
Point3 = tuple[float, float, float]
Triangle = tuple[Point3, Point3, Point3]

PACKAGE_ROOT = SCRIPT_DIR.parent
DEFAULT_CONFIG = PACKAGE_ROOT / "config/mirror-facet-cap-prototypes.json"
GATE1_CONFIG = PACKAGE_ROOT / "config/gate1-panel-roles.json"
GATE8_CONFIG = PACKAGE_ROOT / "config/gate8-full-size-structural-iteration.json"
DEFAULT_OUTPUT = PACKAGE_ROOT / "output/40-prototypes/mirror-facet-cap-prototypes"


@dataclass(frozen=True)
class CapOutline:
    cap_id: str
    panel_id: str
    location: str
    purpose: str
    source_face_count: int
    source_triangle_ids: tuple[str, ...]
    gate8_role: str
    planarity_residual_mm: float
    original_points: tuple[Point2, ...]
    inset_points: tuple[Point2, ...]
    cap_points: tuple[Point2, ...]
    original_area_mm2: float
    cap_area_mm2: float
    dimensions_mm: Point2


@dataclass(frozen=True)
class PlacedCap:
    outline: CapOutline
    points: tuple[Point2, ...]
    rotation_degrees: int
    offset_mm: Point2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Prototype configuration JSON.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Ignored output directory for generated prototype assets.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print the report without writing generated assets.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def add3(a: Point3, b: Point3) -> Point3:
    return tuple(a[index] + b[index] for index in range(3))


def sub3(a: Point3, b: Point3) -> Point3:
    return tuple(a[index] - b[index] for index in range(3))


def scale3(vector: Point3, factor: float) -> Point3:
    return tuple(component * factor for component in vector)


def dot3(a: Point3, b: Point3) -> float:
    return sum(a[index] * b[index] for index in range(3))


def cross3(a: Point3, b: Point3) -> Point3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def length3(vector: Point3) -> float:
    return math.sqrt(dot3(vector, vector))


def normalize3(vector: Point3) -> Point3:
    magnitude = length3(vector)
    if magnitude <= 1e-12:
        raise ValueError("Cannot normalize a zero-length 3D vector")
    return scale3(vector, 1.0 / magnitude)


def add2(a: Point2, b: Point2) -> Point2:
    return a[0] + b[0], a[1] + b[1]


def sub2(a: Point2, b: Point2) -> Point2:
    return a[0] - b[0], a[1] - b[1]


def scale2(vector: Point2, factor: float) -> Point2:
    return vector[0] * factor, vector[1] * factor


def cross2(a: Point2, b: Point2) -> float:
    return a[0] * b[1] - a[1] * b[0]


def length2(vector: Point2) -> float:
    return math.hypot(*vector)


def normalize2(vector: Point2) -> Point2:
    magnitude = length2(vector)
    if magnitude <= 1e-12:
        raise ValueError("Cannot normalize a zero-length 2D vector")
    return scale2(vector, 1.0 / magnitude)


def signed_area(points: Sequence[Point2]) -> float:
    return 0.5 * sum(
        cross2(points[index], points[(index + 1) % len(points)])
        for index in range(len(points))
    )


def polygon_area(points: Sequence[Point2]) -> float:
    return abs(signed_area(points))


def bounds2(points: Sequence[Point2]) -> tuple[float, float, float, float]:
    return (
        min(point[0] for point in points),
        min(point[1] for point in points),
        max(point[0] for point in points),
        max(point[1] for point in points),
    )


def dimensions2(points: Sequence[Point2]) -> Point2:
    minimum_x, minimum_y, maximum_x, maximum_y = bounds2(points)
    return maximum_x - minimum_x, maximum_y - minimum_y


def normalize_origin(points: Sequence[Point2]) -> tuple[Point2, ...]:
    minimum_x, minimum_y, _, _ = bounds2(points)
    return tuple((point[0] - minimum_x, point[1] - minimum_y) for point in points)


def is_convex_ccw(points: Sequence[Point2], tolerance: float = 1e-8) -> bool:
    return all(
        cross2(
            sub2(points[(index + 1) % len(points)], points[index]),
            sub2(points[(index + 2) % len(points)], points[(index + 1) % len(points)]),
        )
        >= -tolerance
        for index in range(len(points))
    )


def boundary_cycle(faces: Sequence[gate1.ObjFace]) -> tuple[int, ...]:
    counts: Counter[tuple[int, int]] = Counter()
    for face in faces:
        for index, start in enumerate(face.indices):
            end = face.indices[(index + 1) % len(face.indices)]
            counts[tuple(sorted((start, end)))] += 1

    boundary_edges = [edge for edge, count in counts.items() if count == 1]
    adjacency: dict[int, list[int]] = defaultdict(list)
    for start, end in boundary_edges:
        adjacency[start].append(end)
        adjacency[end].append(start)
    bad_vertices = {
        vertex: neighbors
        for vertex, neighbors in adjacency.items()
        if len(neighbors) != 2
    }
    if bad_vertices:
        raise ValueError(f"Panel boundary is not one simple loop: {bad_vertices}")

    start = min(adjacency)
    cycle = [start]
    previous: int | None = None
    current = start
    while True:
        candidates = sorted(
            neighbor for neighbor in adjacency[current] if neighbor != previous
        )
        if not candidates:
            raise ValueError("Panel boundary walk reached a dead end")
        next_vertex = candidates[0]
        if next_vertex == start:
            break
        if next_vertex in cycle:
            raise ValueError("Panel boundary walk formed a premature loop")
        cycle.append(next_vertex)
        previous, current = current, next_vertex
    if len(cycle) != len(adjacency):
        raise ValueError(
            f"Panel boundary walk used {len(cycle)} of {len(adjacency)} vertices"
        )
    return tuple(cycle)


def panel_faces(model: gate1.ObjModel) -> dict[str, list[gate1.ObjFace]]:
    grouped: dict[str, list[gate1.ObjFace]] = defaultdict(list)
    for face in model.faces:
        grouped[gate1.canonical_source_panel_id(face.group)].append(face)
    return dict(grouped)


def raw_group_faces(model: gate1.ObjModel) -> dict[str, list[gate1.ObjFace]]:
    grouped: dict[str, list[gate1.ObjFace]] = defaultdict(list)
    for face in model.faces:
        grouped[face.group].append(face)
    return dict(grouped)


def panel_local_outline(
    model: gate1.ObjModel,
    faces: Sequence[gate1.ObjFace],
    scale: float,
    source_origin: Point3,
) -> tuple[tuple[Point2, ...], float]:
    boundary = boundary_cycle(faces)
    transformed_vertices = {
        index: gate1.transform_point(model.vertices[index], scale, source_origin)
        for index in {vertex for face in faces for vertex in face.indices}
    }

    normal_sum: Point3 = (0.0, 0.0, 0.0)
    for face in faces:
        anchor = transformed_vertices[face.indices[0]]
        for index in range(1, len(face.indices) - 1):
            first = transformed_vertices[face.indices[index]]
            second = transformed_vertices[face.indices[index + 1]]
            normal_sum = add3(
                normal_sum,
                cross3(sub3(first, anchor), sub3(second, anchor)),
            )
    normal = normalize3(normal_sum)

    boundary_points = [transformed_vertices[index] for index in boundary]
    longest_edge = max(
        (
            length3(
                sub3(
                    boundary_points[(index + 1) % len(boundary_points)],
                    boundary_points[index],
                )
            ),
            index,
        )
        for index in range(len(boundary_points))
    )[1]
    x_axis = normalize3(
        sub3(
            boundary_points[(longest_edge + 1) % len(boundary_points)],
            boundary_points[longest_edge],
        )
    )
    y_axis = normalize3(cross3(normal, x_axis))
    plane_origin = tuple(
        sum(point[axis] for point in boundary_points) / len(boundary_points)
        for axis in range(3)
    )

    residual = max(
        abs(dot3(sub3(point, plane_origin), normal))
        for point in transformed_vertices.values()
    )
    projected = [
        (
            dot3(sub3(point, plane_origin), x_axis),
            dot3(sub3(point, plane_origin), y_axis),
        )
        for point in boundary_points
    ]
    if signed_area(projected) < 0:
        projected.reverse()
    if not is_convex_ccw(projected):
        raise ValueError("Selected facet boundary is not a convex polygon")
    return normalize_origin(projected), residual


def line_intersection(
    first_point: Point2,
    first_direction: Point2,
    second_point: Point2,
    second_direction: Point2,
) -> Point2:
    denominator = cross2(first_direction, second_direction)
    if abs(denominator) <= 1e-10:
        raise ValueError("Cannot inset polygon with parallel adjacent edges")
    parameter = cross2(
        sub2(second_point, first_point),
        second_direction,
    ) / denominator
    return add2(first_point, scale2(first_direction, parameter))


def inset_convex_polygon(
    points: Sequence[Point2],
    inset_mm: float,
) -> tuple[Point2, ...]:
    if signed_area(points) <= 0 or not is_convex_ccw(points):
        raise ValueError("Inset requires a convex counter-clockwise polygon")
    shifted_edges: list[tuple[Point2, Point2]] = []
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        direction = normalize2(sub2(end, start))
        inward = (-direction[1], direction[0])
        shifted_edges.append((add2(start, scale2(inward, inset_mm)), direction))

    inset_points = []
    for index in range(len(points)):
        previous = shifted_edges[(index - 1) % len(points)]
        current = shifted_edges[index]
        inset_points.append(
            line_intersection(
                previous[0],
                previous[1],
                current[0],
                current[1],
            )
        )
    if signed_area(inset_points) <= 0 or not is_convex_ccw(inset_points):
        raise ValueError("Inset collapsed or inverted the selected facet")
    return normalize_origin(inset_points)


def chamfer_polygon(
    points: Sequence[Point2],
    requested_mm: float,
) -> tuple[Point2, ...]:
    if requested_mm <= 0:
        return tuple(points)
    result: list[Point2] = []
    for index, vertex in enumerate(points):
        previous = points[(index - 1) % len(points)]
        following = points[(index + 1) % len(points)]
        previous_length = length2(sub2(previous, vertex))
        following_length = length2(sub2(following, vertex))
        chamfer = min(
            requested_mm,
            previous_length * 0.2,
            following_length * 0.2,
        )
        toward_previous = normalize2(sub2(previous, vertex))
        toward_following = normalize2(sub2(following, vertex))
        result.append(add2(vertex, scale2(toward_previous, chamfer)))
        result.append(add2(vertex, scale2(toward_following, chamfer)))
    if signed_area(result) <= 0 or not is_convex_ccw(result):
        raise ValueError("Corner chamfer produced an invalid cap polygon")
    return normalize_origin(result)


def triangle_normal(triangle: Triangle) -> Point3:
    first = sub3(triangle[1], triangle[0])
    second = sub3(triangle[2], triangle[0])
    cross = cross3(first, second)
    magnitude = length3(cross)
    if magnitude <= 1e-10:
        raise ValueError(f"Degenerate STL triangle: {triangle}")
    return scale3(cross, 1.0 / magnitude)


def extruded_triangles(
    points: Sequence[Point2],
    thickness_mm: float,
) -> list[Triangle]:
    if signed_area(points) <= 0 or not is_convex_ccw(points):
        raise ValueError("Extrusion requires a convex counter-clockwise polygon")
    bottom = [(point[0], point[1], 0.0) for point in points]
    top = [(point[0], point[1], thickness_mm) for point in points]
    triangles: list[Triangle] = []
    for index in range(1, len(points) - 1):
        triangles.append((bottom[0], bottom[index + 1], bottom[index]))
        triangles.append((top[0], top[index], top[index + 1]))
    for index in range(len(points)):
        following = (index + 1) % len(points)
        triangles.append((bottom[index], bottom[following], top[following]))
        triangles.append((bottom[index], top[following], top[index]))
    for triangle in triangles:
        triangle_normal(triangle)
    return triangles


def quantized_point(point: Point3) -> tuple[int, int, int]:
    return tuple(round(component * 1_000_000) for component in point)


def mesh_topology(triangles: Sequence[Triangle]) -> dict[str, Any]:
    edge_counts: Counter[
        tuple[tuple[int, int, int], tuple[int, int, int]]
    ] = Counter()
    signed_volume_mm3 = 0.0
    for triangle in triangles:
        normal = triangle_normal(triangle)
        if not all(math.isfinite(value) for value in (*normal, *triangle[0])):
            raise ValueError("Mesh contains a non-finite value")
        for index in range(3):
            first = quantized_point(triangle[index])
            second = quantized_point(triangle[(index + 1) % 3])
            edge_counts[tuple(sorted((first, second)))] += 1
        signed_volume_mm3 += dot3(
            triangle[0],
            cross3(triangle[1], triangle[2]),
        ) / 6.0
    boundary_edges = sum(count == 1 for count in edge_counts.values())
    nonmanifold_edges = sum(count != 2 for count in edge_counts.values())
    return {
        "triangle_count": len(triangles),
        "boundary_edges": boundary_edges,
        "nonmanifold_edges": nonmanifold_edges,
        "signed_volume_mm3": signed_volume_mm3,
        "volume_mm3": abs(signed_volume_mm3),
    }


def write_ascii_stl(
    path: Path,
    name: str,
    triangles: Sequence[Triangle],
) -> None:
    lines = [f"solid {name}"]
    for triangle in triangles:
        normal = triangle_normal(triangle)
        lines.append(
            "  facet normal {:.9f} {:.9f} {:.9f}".format(*normal)
        )
        lines.append("    outer loop")
        lines.extend(
            "      vertex {:.9f} {:.9f} {:.9f}".format(*vertex)
            for vertex in triangle
        )
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append(f"endsolid {name}")
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def rotate_points(points: Sequence[Point2], degrees: int) -> tuple[Point2, ...]:
    if degrees == 0:
        return normalize_origin(points)
    if degrees == 90:
        return normalize_origin(tuple((-point[1], point[0]) for point in points))
    raise ValueError(f"Unsupported plate rotation: {degrees}")


def pack_caps(
    outlines: Sequence[CapOutline],
    bed_mm: Point2,
    margin_mm: float,
    spacing_mm: float,
) -> tuple[PlacedCap, ...]:
    usable_width = bed_mm[0] - 2.0 * margin_mm
    usable_height = bed_mm[1] - 2.0 * margin_mm
    best: tuple[float, float, tuple[PlacedCap, ...]] | None = None

    for ordering in itertools.permutations(outlines):
        for rotations in itertools.product((0, 90), repeat=len(outlines)):
            x_cursor = 0.0
            y_cursor = 0.0
            row_height = 0.0
            placed: list[PlacedCap] = []
            used_width = 0.0
            failed = False
            for outline, rotation in zip(ordering, rotations):
                rotated = rotate_points(outline.cap_points, rotation)
                width, height = dimensions2(rotated)
                if width > usable_width or height > usable_height:
                    failed = True
                    break
                if x_cursor > 0 and x_cursor + width > usable_width:
                    x_cursor = 0.0
                    y_cursor += row_height + spacing_mm
                    row_height = 0.0
                if y_cursor + height > usable_height:
                    failed = True
                    break
                offset = (margin_mm + x_cursor, margin_mm + y_cursor)
                translated = tuple(add2(point, offset) for point in rotated)
                placed.append(
                    PlacedCap(
                        outline=outline,
                        points=translated,
                        rotation_degrees=rotation,
                        offset_mm=offset,
                    )
                )
                x_cursor += width + spacing_mm
                row_height = max(row_height, height)
                used_width = max(used_width, x_cursor - spacing_mm)
            if failed:
                continue
            used_height = y_cursor + row_height
            candidate = (used_height, used_width, tuple(placed))
            if best is None or candidate[:2] < best[:2]:
                best = candidate
    if best is None:
        raise ValueError(
            f"Four cap prototypes do not fit {bed_mm[0]} x {bed_mm[1]} mm"
        )
    return best[2]


def translated_triangles(
    triangles: Sequence[Triangle],
    offset: Point2,
) -> list[Triangle]:
    return [
        tuple(
            (vertex[0] + offset[0], vertex[1] + offset[1], vertex[2])
            for vertex in triangle
        )
        for triangle in triangles
    ]


def combined_plate_triangles(
    placed: Sequence[PlacedCap],
    thickness_mm: float,
) -> list[Triangle]:
    triangles: list[Triangle] = []
    for item in placed:
        triangles.extend(extruded_triangles(item.points, thickness_mm))
    return triangles


def centroid2(points: Sequence[Point2]) -> Point2:
    area_factor = sum(
        cross2(points[index], points[(index + 1) % len(points)])
        for index in range(len(points))
    )
    if abs(area_factor) <= 1e-12:
        minimum_x, minimum_y, maximum_x, maximum_y = bounds2(points)
        return (minimum_x + maximum_x) / 2.0, (minimum_y + maximum_y) / 2.0
    x = sum(
        (points[index][0] + points[(index + 1) % len(points)][0])
        * cross2(points[index], points[(index + 1) % len(points)])
        for index in range(len(points))
    )
    y = sum(
        (points[index][1] + points[(index + 1) % len(points)][1])
        * cross2(points[index], points[(index + 1) % len(points)])
        for index in range(len(points))
    )
    return x / (3.0 * area_factor), y / (3.0 * area_factor)


def svg_polygon(points: Sequence[Point2], bed_height_mm: float) -> str:
    return " ".join(
        f"{point[0]:.3f},{bed_height_mm - point[1]:.3f}"
        for point in points
    )


def write_plate_svg(
    path: Path,
    placed: Sequence[PlacedCap],
    bed_mm: Point2,
    config: dict[str, Any],
) -> None:
    colors = ("#c98778", "#dda393", "#b56d5f", "#efc1aa")
    rows = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{bed_mm[0]:.3f}mm" height="{bed_mm[1]:.3f}mm" '
            f'viewBox="0 0 {bed_mm[0]:.3f} {bed_mm[1]:.3f}">'
        ),
        "<style>",
        "text { font-family: sans-serif; fill: #111827; }",
        ".label { font-size: 4px; font-weight: 700; text-anchor: middle; }",
        ".note { font-size: 3.4px; }",
        "</style>",
        (
            f'<rect x="0.25" y="0.25" width="{bed_mm[0] - 0.5:.3f}" '
            f'height="{bed_mm[1] - 0.5:.3f}" fill="#f6f7f8" '
            f'stroke="#6b7280" stroke-width="0.5"/>'
        ),
    ]
    for index, item in enumerate(placed):
        rows.append(
            f'<polygon points="{svg_polygon(item.points, bed_mm[1])}" '
            f'fill="{colors[index % len(colors)]}" fill-opacity="0.8" '
            f'stroke="#111827" stroke-width="0.45"/>'
        )
        center_x, center_y = centroid2(item.points)
        rows.append(
            f'<text class="label" x="{center_x:.3f}" '
            f'y="{bed_mm[1] - center_y:.3f}">{item.outline.cap_id}</text>'
        )
    rows.extend(
        (
            (
                '<text class="note" x="6" y="7">'
                f'1:1 outline; {config["perimeter_inset_mm"]:.1f} mm inset; '
                f'{config["corner_chamfer_mm"]:.1f} mm corner chamfer</text>'
            ),
            (
                '<text class="note" x="6" y="11.2">'
                "Print mirror face against smooth build plate; SVG is a dimensional check, not a cut file.</text>"
            ),
            "</svg>",
        )
    )
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def gate8_role(
    panel_id: str,
    gate1_roles: dict[str, dict[str, str]],
    gate8_config: dict[str, Any],
) -> str:
    opaque_overrides = set(
        gate8_config["opaque_muzzle_frame"]["opaque_reclassified_panel_ids"]
    )
    if panel_id in opaque_overrides:
        return "integrated_opaque"
    return gate1_roles[panel_id]["role"]


def build_outlines(
    config: dict[str, Any],
    model: gate1.ObjModel,
    metadata: dict[str, list[dict[str, str]]],
    gate1_config: dict[str, Any],
    gate8_config: dict[str, Any],
    selections: Sequence[dict[str, Any]] | None = None,
) -> tuple[list[CapOutline], float]:
    units = gate1.panel_units(model, metadata)
    source_bounds = gate1.bounds(model.vertices)
    scale, source_origin, _ = gate1.make_transform(
        source_bounds,
        float(config["source_head_height_mm"]),
    )
    gate1_roles, _ = gate1.build_roles(units, gate1_config, scale)
    faces_by_panel = panel_faces(model)
    faces_by_raw_group = raw_group_faces(model)

    outlines: list[CapOutline] = []
    selected_facets = config["selected_facets"] if selections is None else selections
    for selection in selected_facets:
        cap_id = selection["cap_id"]
        panel_id = selection["source_panel_id"]
        if panel_id not in units or panel_id not in faces_by_panel:
            raise ValueError(f"Selected mirror-cap facet {panel_id} is absent")
        selected_faces: list[gate1.ObjFace] = []
        for group_name in selection["source_face_groups"]:
            if group_name not in faces_by_raw_group:
                raise ValueError(
                    f"Selected mirror-cap face group {group_name} is absent"
                )
            selected_faces.extend(faces_by_raw_group[group_name])
        if not selected_faces:
            raise ValueError(f"Selected mirror cap {cap_id} has no source faces")
        role = gate8_role(panel_id, gate1_roles, gate8_config)
        if role != selection["expected_gate8_role"]:
            raise ValueError(
                f"{panel_id} expected {selection['expected_gate8_role']} "
                f"at Gate 8 but resolved to {role}"
            )
        original, residual = panel_local_outline(
            model,
            selected_faces,
            scale,
            source_origin,
        )
        inset = inset_convex_polygon(
            original,
            float(config["perimeter_inset_mm"]),
        )
        cap = chamfer_polygon(
            inset,
            float(config["corner_chamfer_mm"]),
        )
        outlines.append(
            CapOutline(
                cap_id=cap_id,
                panel_id=panel_id,
                location=selection["location"],
                purpose=selection["purpose"],
                source_face_count=len(selected_faces),
                source_triangle_ids=tuple(face.group for face in selected_faces),
                gate8_role=role,
                planarity_residual_mm=residual,
                original_points=tuple(original),
                inset_points=tuple(inset),
                cap_points=tuple(cap),
                original_area_mm2=polygon_area(original),
                cap_area_mm2=polygon_area(cap),
                dimensions_mm=dimensions2(cap),
            )
        )
    return outlines, scale


def thickness_slug(thickness_mm: float) -> str:
    return f"{thickness_mm:.1f}".replace(".", "p") + "mm"


def part_manifest_rows(
    outlines: Sequence[CapOutline],
    thicknesses_mm: Sequence[float],
    density_g_cm3: float,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for thickness in thicknesses_mm:
        slug = thickness_slug(thickness)
        for outline in outlines:
            triangles = extruded_triangles(outline.cap_points, thickness)
            topology = mesh_topology(triangles)
            expected_volume = outline.cap_area_mm2 * thickness
            mass_g = expected_volume / 1000.0 * density_g_cm3
            rows.append(
                {
                    "source_panel_id": outline.panel_id,
                    "cap_id": outline.cap_id,
                    "location": outline.location,
                    "gate8_role": outline.gate8_role,
                    "source_face_count": str(outline.source_face_count),
                    "source_triangle_ids": " ".join(outline.source_triangle_ids),
                    "thickness_mm": f"{thickness:.3f}",
                    "width_mm": f"{outline.dimensions_mm[0]:.3f}",
                    "height_mm": f"{outline.dimensions_mm[1]:.3f}",
                    "original_facet_area_mm2": f"{outline.original_area_mm2:.3f}",
                    "cap_area_mm2": f"{outline.cap_area_mm2:.3f}",
                    "volume_mm3": f"{topology['volume_mm3']:.3f}",
                    "estimated_black_asa_mass_g": f"{mass_g:.3f}",
                    "planarity_residual_mm": (
                        f"{outline.planarity_residual_mm:.6f}"
                    ),
                    "stl": f"{slug}/{outline.cap_id.lower()}_{slug}.stl",
                    "purpose": outline.purpose,
                }
            )
    return rows


def write_manifest_csv(path: Path, rows: Sequence[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    gate1_config = json.loads(GATE1_CONFIG.read_text(encoding="utf-8"))
    gate8_config = json.loads(GATE8_CONFIG.read_text(encoding="utf-8"))
    model = gate1.read_obj(gate1.SOURCE_SURFACE_OBJ)
    metadata = gate1.read_panel_metadata(gate1.SOURCE_PANEL_CSV)

    outlines, scale = build_outlines(
        config,
        model,
        metadata,
        gate1_config,
        gate8_config,
    )
    thicknesses = [float(value) for value in config["prototype_thicknesses_mm"]]
    bed_mm = tuple(float(value) for value in config["printer_bed_mm"])
    placed = pack_caps(
        outlines,
        bed_mm,
        float(config["plate_margin_mm"]),
        float(config["part_spacing_mm"]),
    )
    first_trial = config["first_physical_trial"]
    trial_thickness = float(first_trial["thickness_mm"])
    if trial_thickness not in thicknesses:
        raise ValueError(
            "First physical trial thickness must be one of the generated "
            f"prototype thicknesses: {trial_thickness}"
        )
    trial_outlines, trial_scale = build_outlines(
        config,
        model,
        metadata,
        gate1_config,
        gate8_config,
        selections=first_trial["selected_facets"],
    )
    if not math.isclose(trial_scale, scale, abs_tol=1e-12):
        raise ValueError("Starter and comparison caps resolved different scales")
    trial_cap_ids = [outline.cap_id for outline in trial_outlines]
    if len(trial_cap_ids) != len(set(trial_cap_ids)):
        raise ValueError("First physical trial cap IDs must be unique")
    trial_placed = pack_caps(
        trial_outlines,
        bed_mm,
        float(config["plate_margin_mm"]),
        float(config["part_spacing_mm"]),
    )
    trial_triangles = combined_plate_triangles(
        trial_placed,
        trial_thickness,
    )
    trial_topology = mesh_topology(trial_triangles)
    trial_minimum_x = min(
        point[0] for item in trial_placed for point in item.points
    )
    trial_minimum_y = min(
        point[1] for item in trial_placed for point in item.points
    )
    trial_maximum_x = max(
        point[0] for item in trial_placed for point in item.points
    )
    trial_maximum_y = max(
        point[1] for item in trial_placed for point in item.points
    )
    trial_plate_fits = (
        trial_minimum_x >= 0
        and trial_minimum_y >= 0
        and trial_maximum_x <= bed_mm[0]
        and trial_maximum_y <= bed_mm[1]
    )
    trial_density = float(first_trial["density_g_cm3"])
    trial_mass_g = (
        sum(outline.cap_area_mm2 for outline in trial_outlines)
        * trial_thickness
        / 1000.0
        * trial_density
    )
    density = float(config["cap_density_g_cm3"])
    rows = part_manifest_rows(outlines, thicknesses, density)

    individual_topologies: dict[str, dict[str, Any]] = {}
    plate_topologies: dict[str, dict[str, Any]] = {}
    total_mass_by_thickness: dict[str, float] = {}
    for thickness in thicknesses:
        slug = thickness_slug(thickness)
        total_mass = 0.0
        for outline in outlines:
            triangles = extruded_triangles(outline.cap_points, thickness)
            individual_topologies[f"{outline.cap_id}_{slug}"] = mesh_topology(
                triangles
            )
            total_mass += (
                outline.cap_area_mm2 * thickness / 1000.0 * density
            )
        plate_triangles = combined_plate_triangles(placed, thickness)
        plate_topologies[slug] = mesh_topology(plate_triangles)
        total_mass_by_thickness[slug] = total_mass

    planarity_limit = float(config["planarity_tolerance_mm"])
    maximum_x = max(point[0] for item in placed for point in item.points)
    maximum_y = max(point[1] for item in placed for point in item.points)
    minimum_x = min(point[0] for item in placed for point in item.points)
    minimum_y = min(point[1] for item in placed for point in item.points)
    plate_fits = (
        minimum_x >= 0
        and minimum_y >= 0
        and maximum_x <= bed_mm[0]
        and maximum_y <= bed_mm[1]
    )
    acceptance = {
        "four_source_facets_become_six_planar_caps": (
            len({outline.panel_id for outline in outlines}) == 4
            and len(outlines) == 6
        ),
        "all_selected_facets_are_gate8_opaque": all(
            outline.gate8_role == "integrated_opaque" for outline in outlines
        ),
        "all_selected_facets_are_planar": all(
            outline.planarity_residual_mm <= planarity_limit
            for outline in outlines
        ),
        "all_insets_preserve_positive_area": all(
            0 < outline.cap_area_mm2 < outline.original_area_mm2
            for outline in outlines
        ),
        "all_individual_stls_are_closed_manifold": all(
            topology["boundary_edges"] == 0
            and topology["nonmanifold_edges"] == 0
            for topology in individual_topologies.values()
        ),
        "both_plates_are_closed_manifold_components": all(
            topology["boundary_edges"] == 0
            and topology["nonmanifold_edges"] == 0
            for topology in plate_topologies.values()
        ),
        "plate_layout_fits_printer_bed": plate_fits,
        "both_requested_thicknesses_generated": set(thicknesses) == {0.6, 0.8},
        "left_starter_plate_has_three_representative_caps": (
            first_trial["side"] == "left"
            and set(trial_cap_ids) == {"TRI042", "TRI019", "QUAD025_B"}
            and len(trial_outlines) == 3
        ),
        "starter_plate_is_closed_manifold": (
            trial_topology["boundary_edges"] == 0
            and trial_topology["nonmanifold_edges"] == 0
        ),
        "starter_plate_fits_printer_bed": trial_plate_fits,
    }
    report = {
        "schema_version": 1,
        "config": str(args.config.relative_to(PACKAGE_ROOT)),
        "source_files": {
            "accepted_surface_obj": {
                "path": str(gate1.SOURCE_SURFACE_OBJ.relative_to(gate1.REPO_ROOT)),
                "sha256": sha256(gate1.SOURCE_SURFACE_OBJ),
            },
            "panel_metadata_csv": {
                "path": str(gate1.SOURCE_PANEL_CSV.relative_to(gate1.REPO_ROOT)),
                "sha256": sha256(gate1.SOURCE_PANEL_CSV),
            },
            "gate1_roles": {
                "path": str(GATE1_CONFIG.relative_to(PACKAGE_ROOT)),
                "sha256": sha256(GATE1_CONFIG),
            },
            "gate8_config": {
                "path": str(GATE8_CONFIG.relative_to(PACKAGE_ROOT)),
                "sha256": sha256(GATE8_CONFIG),
            },
        },
        "uniform_scale_to_330mm": scale,
        "selected_facets": [
            {
                "source_panel_id": outline.panel_id,
                "cap_id": outline.cap_id,
                "location": outline.location,
                "gate8_role": outline.gate8_role,
                "source_face_count": outline.source_face_count,
                "source_triangle_ids": list(outline.source_triangle_ids),
                "planarity_residual_mm": outline.planarity_residual_mm,
                "original_area_mm2": outline.original_area_mm2,
                "cap_area_mm2": outline.cap_area_mm2,
                "cap_dimensions_mm": list(outline.dimensions_mm),
                "cap_outline_vertex_count": len(outline.cap_points),
                "purpose": outline.purpose,
            }
            for outline in outlines
        ],
        "plate": {
            "printer_bed_mm": list(bed_mm),
            "occupied_bounds_mm": [
                minimum_x,
                minimum_y,
                maximum_x,
                maximum_y,
            ],
            "placements": [
                {
                    "source_panel_id": item.outline.panel_id,
                    "cap_id": item.outline.cap_id,
                    "rotation_degrees": item.rotation_degrees,
                    "offset_mm": list(item.offset_mm),
                }
                for item in placed
            ],
        },
        "first_physical_trial": {
            "side": first_trial["side"],
            "material": first_trial["material"],
            "density_g_cm3": trial_density,
            "build_sheet": first_trial["build_sheet"],
            "thickness_mm": trial_thickness,
            "cap_ids": trial_cap_ids,
            "occupied_bounds_mm": [
                trial_minimum_x,
                trial_minimum_y,
                trial_maximum_x,
                trial_maximum_y,
            ],
            "placements": [
                {
                    "source_panel_id": item.outline.panel_id,
                    "cap_id": item.outline.cap_id,
                    "rotation_degrees": item.rotation_degrees,
                    "offset_mm": list(item.offset_mm),
                }
                for item in trial_placed
            ],
            "estimated_mass_g": trial_mass_g,
            "mesh": trial_topology,
        },
        "thicknesses_mm": thicknesses,
        "estimated_black_asa_mass_g_by_plate": total_mass_by_thickness,
        "individual_meshes": individual_topologies,
        "plate_meshes": plate_topologies,
        "acceptance": acceptance,
        "limitations": [
            "Digital planarity and manifold checks do not validate adhesion, appearance, curling, or thermal cycling.",
            "The build-plate face is the visible film face; textured-sheet trials do not qualify final optical smoothness.",
            "The 0.8 mm corner treatment is a straight chamfer, not a machined radius.",
            "Mirror film and rear transfer adhesive are not included in the STL thickness or mass estimate.",
        ],
    }
    if not all(acceptance.values()):
        failures = [name for name, passed in acceptance.items() if not passed]
        residuals = {
            outline.cap_id: round(outline.planarity_residual_mm, 6)
            for outline in outlines
        }
        raise ValueError(
            "Mirror-cap prototype validation failed: "
            f"{failures}; planarity residuals mm: {residuals}"
        )

    if not args.dry_run:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for thickness in thicknesses:
            slug = thickness_slug(thickness)
            thickness_dir = args.output_dir / slug
            thickness_dir.mkdir(parents=True, exist_ok=True)
            for outline in outlines:
                triangles = extruded_triangles(outline.cap_points, thickness)
                write_ascii_stl(
                    thickness_dir / f"{outline.cap_id.lower()}_{slug}.stl",
                    f"{outline.cap_id}_{slug}",
                    triangles,
                )
            plate_triangles = combined_plate_triangles(placed, thickness)
            write_ascii_stl(
                args.output_dir / f"mirror-facet-cap-test-plate-{slug}.stl",
                f"mirror_facet_cap_test_plate_{slug}",
                plate_triangles,
            )
        trial_slug = thickness_slug(trial_thickness)
        trial_filename = (
            f"mirror-facet-cap-{first_trial['side']}-starter-plate-"
            f"{trial_slug}.stl"
        )
        write_ascii_stl(
            args.output_dir / trial_filename,
            f"mirror_facet_cap_{first_trial['side']}_starter_plate_{trial_slug}",
            trial_triangles,
        )
        # Preserve the previously shared generic path as an alias to the
        # corrected left-side plate so an already-open link cannot print the
        # obsolete right-side geometry by accident.
        write_ascii_stl(
            args.output_dir / f"mirror-facet-cap-starter-plate-{trial_slug}.stl",
            f"mirror_facet_cap_left_starter_plate_{trial_slug}_alias",
            trial_triangles,
        )
        write_plate_svg(
            args.output_dir / "mirror-facet-cap-test-plate-1to1.svg",
            placed,
            bed_mm,
            config,
        )
        write_manifest_csv(args.output_dir / "prototype-parts.csv", rows)
        (args.output_dir / "validation-report.json").write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )

    print(json.dumps(report, indent=2))
    if not args.dry_run:
        print(f"Wrote {args.output_dir.relative_to(PACKAGE_ROOT)}")


if __name__ == "__main__":
    main()
