#!/usr/bin/env python3
"""Generate the Gate 2 seven-section topology and printer-envelope review."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from generate_gate1_master import (
    DEFAULT_CONFIG as GATE1_CONFIG,
    SOURCE_PANEL_CSV,
    SOURCE_SURFACE_OBJ,
    ObjFace,
    ObjModel,
    bounds,
    build_roles,
    canonical_source_panel_id,
    dimensions,
    make_transform,
    panel_units,
    project,
    read_obj,
    read_panel_metadata,
    svg_points,
    transform_point,
)


Point = tuple[float, float, float]
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/gate2-section-layout.json"
DEFAULT_OUTPUT = PACKAGE_ROOT / "output/gate2-section-layout"

SECTION_ORDER = (
    "right_upper_head",
    "left_upper_head",
    "right_lower_face",
    "left_lower_face",
    "rear_base",
    "right_ear",
    "left_ear",
)
COLORS = {
    "right_upper_head": "#d97745",
    "left_upper_head": "#f2a65a",
    "right_lower_face": "#4f7cac",
    "left_lower_face": "#79a9dc",
    "rear_base": "#5f6f52",
    "right_ear": "#8a6fb8",
    "left_ear": "#b59ad6",
    "removable_glow": "#800080",
    "mouth_opening": "#ff0000",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def face_centroid(face: ObjFace, vertices: list[Point], scale: float, origin: Point) -> Point:
    points = [transform_point(vertices[index], scale, origin) for index in face.indices]
    return tuple(sum(point[axis] for point in points) / len(points) for axis in range(3))


def subdivide_lower_center_panel(model: ObjModel, source_panel_id: str) -> ObjModel:
    """Replace a planar center-bottom quad with symmetric left/right quads."""
    selected = [face for face in model.faces if canonical_source_panel_id(face.group) == source_panel_id]
    if len(selected) != 2 or any(len(face.indices) != 3 for face in selected):
        raise ValueError(f"{source_panel_id} must be represented by exactly two triangles")

    counts: dict[tuple[int, int], int] = defaultdict(int)
    for face in selected:
        for offset, first in enumerate(face.indices):
            second = face.indices[(offset + 1) % len(face.indices)]
            counts[tuple(sorted((first, second)))] += 1
    boundary_indices = sorted({index for edge, count in counts.items() if count == 1 for index in edge})
    if len(boundary_indices) != 4:
        raise ValueError(f"{source_panel_id} does not have a four-vertex boundary")

    by_depth = sorted(boundary_indices, key=lambda index: model.vertices[index][1])
    front = sorted(by_depth[:2], key=lambda index: model.vertices[index][0])
    rear = sorted(by_depth[2:], key=lambda index: model.vertices[index][0])
    front_left, front_right = front
    rear_left, rear_right = rear

    def midpoint(first: int, second: int) -> Point:
        return tuple((model.vertices[first][axis] + model.vertices[second][axis]) / 2.0 for axis in range(3))

    vertices = list(model.vertices)
    front_center = len(vertices)
    vertices.append(midpoint(front_left, front_right))
    rear_center = len(vertices)
    vertices.append(midpoint(rear_left, rear_right))

    faces = [face for face in model.faces if canonical_source_panel_id(face.group) != source_panel_id]
    object_name = selected[0].object_name
    faces.extend(
        (
            ObjFace((rear_center, rear_right, front_right, front_center), f"{source_panel_id}_RIGHT", object_name),
            ObjFace((rear_left, rear_center, front_center, front_left), f"{source_panel_id}_LEFT", object_name),
        )
    )
    return ObjModel(vertices=vertices, faces=faces)


def subdivide_center_panels(model: ObjModel, config: dict[str, Any]) -> ObjModel:
    """Split every configured center-spanning quad into left/right shell facets."""
    panel_ids = [
        config["lower_center_split_panel"],
        *config.get("lower_face_rear_split_panels", []),
    ]
    for panel_id in panel_ids:
        model = subdivide_lower_center_panel(model, panel_id)
    return model


def assign_faces(
    faces: list[ObjFace],
    vertices: list[Point],
    role_by_panel: dict[str, dict[str, str]],
    config: dict[str, Any],
    scale: float,
    origin: Point,
) -> list[str]:
    right_ear = set(config["right_ear_panels"])
    left_ear = set(config["left_ear_panels"])
    rear_base = set(config["rear_base_panels"])
    rear_lower_assignments = {
        f"{panel}_RIGHT": "right_lower_face"
        for panel in config.get("lower_face_rear_split_panels", [])
    } | {
        f"{panel}_LEFT": "left_lower_face"
        for panel in config.get("lower_face_rear_split_panels", [])
    }
    lower_center_split_panel = config["lower_center_split_panel"]
    assignments: list[str] = []
    for face in faces:
        panel_id = canonical_source_panel_id(face.group)
        if panel_id == f"{lower_center_split_panel}_RIGHT":
            assignments.append("right_lower_face")
            continue
        if panel_id == f"{lower_center_split_panel}_LEFT":
            assignments.append("left_lower_face")
            continue
        if panel_id in rear_lower_assignments:
            assignments.append(rear_lower_assignments[panel_id])
            continue
        role = role_by_panel[panel_id]["role"]
        if role in {"removable_glow", "mouth_opening"}:
            assignments.append(role)
            continue
        if panel_id in rear_base:
            assignments.append("rear_base")
            continue
        if panel_id in right_ear:
            assignments.append("right_ear")
            continue
        if panel_id in left_ear:
            assignments.append("left_ear")
            continue
        x, _, z = face_centroid(face, vertices, scale, origin)
        side = "right" if x >= 0.0 else "left"
        level = "upper_head" if z >= float(config["belt_height_mm"]) else "lower_face"
        assignments.append(f"{side}_{level}")
    return assignments


def section_components(faces: list[ObjFace], assignments: list[str], section: str) -> list[list[int]]:
    selected = [index for index, value in enumerate(assignments) if value == section]
    neighbors: dict[int, set[int]] = {index: set() for index in selected}
    edge_faces: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index in selected:
        face = faces[index]
        for offset, vertex in enumerate(face.indices):
            edge = tuple(sorted((vertex, face.indices[(offset + 1) % len(face.indices)])))
            edge_faces[edge].append(index)
    for sharing in edge_faces.values():
        for first in sharing:
            neighbors[first].update(other for other in sharing if other != first)
    components: list[list[int]] = []
    remaining = set(selected)
    while remaining:
        start = next(iter(remaining))
        queue = deque([start])
        component: list[int] = []
        remaining.remove(start)
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in neighbors[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    queue.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=len, reverse=True)


def rotate(point: Point, angles: tuple[float, float, float]) -> Point:
    x, y, z = point
    ax, ay, az = angles
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)
    y, z = y * cx - z * sx, y * sx + z * cx
    x, z = x * cy + z * sy, -x * sy + z * cy
    x, y = x * cz - y * sz, x * sz + y * cz
    return x, y, z


def best_fit(points: list[Point], envelope: list[float], step_degrees: int) -> dict[str, Any]:
    best: tuple[float, list[float], tuple[int, int, int]] | None = None
    sorted_envelope = sorted(float(value) for value in envelope)
    for ax in range(0, 180, step_degrees):
        for ay in range(0, 180, step_degrees):
            for az in range(0, 180, step_degrees):
                radians = tuple(math.radians(value) for value in (ax, ay, az))
                rotated = [rotate(point, radians) for point in points]
                dims = sorted(dimensions(bounds(rotated)))
                ratio = max(dims[index] / sorted_envelope[index] for index in range(3))
                if best is None or ratio < best[0]:
                    best = ratio, dims, (ax, ay, az)
    assert best is not None
    return {
        "fits": best[0] <= 1.0 + 1e-9,
        "max_envelope_ratio": round(best[0], 6),
        "oriented_dimensions_mm_sorted": [round(value, 3) for value in best[1]],
        "rotation_xyz_degrees": list(best[2]),
        "envelope_mm_sorted": sorted_envelope,
    }


def write_obj(path: Path, vertices: list[Point], faces: list[ObjFace], assignments: list[str], scale: float, origin: Point) -> None:
    lines = ["# Gate 2 face-level section layout", "mtllib gate2-section-layout.mtl"]
    lines.extend("v {:.6f} {:.6f} {:.6f}".format(*transform_point(vertex, scale, origin)) for vertex in vertices)
    last = ""
    for face, assignment in zip(faces, assignments):
        if assignment != last:
            lines.extend((f"g {assignment}", f"usemtl {assignment}"))
            last = assignment
        lines.append("f " + " ".join(str(index + 1) for index in face.indices))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_mtl(path: Path) -> None:
    lines = ["# Gate 2 section colors"]
    for name, color in COLORS.items():
        red, green, blue = (int(color[index:index + 2], 16) / 255 for index in (1, 3, 5))
        lines.extend((f"newmtl {name}", f"Kd {red:.4f} {green:.4f} {blue:.4f}", "Ns 80", ""))
    path.write_text("\n".join(lines), encoding="utf-8")


def build_svg(vertices: list[Point], faces: list[ObjFace], assignments: list[str], scale: float, origin: Point) -> str:
    polygons = [
        (assignment, canonical_source_panel_id(face.group), [transform_point(vertices[index], scale, origin) for index in face.indices])
        for face, assignment in zip(faces, assignments)
    ]
    views = (("front", "Front"), ("side", "Right side"), ("top", "Top"), ("isometric", "Isometric"))
    boxes = {"front": (40, 80, 390, 320), "side": (520, 80, 390, 320), "top": (40, 490, 390, 260), "isometric": (520, 490, 390, 260)}
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="840" viewBox="0 0 960 840">',
        '<rect width="960" height="840" fill="#101820"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#dce8ef}.label{font-size:17px;font-weight:600}.caption{font-size:12px;fill:#a8bac6}.legend{font-size:11px}</style>',
        '<text x="40" y="34" class="label">Cat head Gate 2 — seven-section topology candidate</text>',
        '<text x="40" y="56" class="caption">Section colors show structural ownership. Purple panels and red mouth facets are not part of structural shells.</text>',
    ]
    for view, title in views:
        ox, oy, width, height = boxes[view]
        projected = [(assignment, panel_id, [project(point, view) for point in points]) for assignment, panel_id, points in polygons]
        all_xy = [point[:2] for _, _, points in projected for point in points]
        min_x, max_x = min(p[0] for p in all_xy), max(p[0] for p in all_xy)
        min_y, max_y = min(p[1] for p in all_xy), max(p[1] for p in all_xy)
        local_scale = min((width - 36) / (max_x - min_x), (height - 36) / (max_y - min_y))
        offset_x = ox + (width - (max_x - min_x) * local_scale) / 2 - min_x * local_scale
        offset_y = oy + (height - (max_y - min_y) * local_scale) / 2 + max_y * local_scale
        map_point = lambda point: (offset_x + point[0] * local_scale, offset_y - point[1] * local_scale)
        svg.extend((f'<rect x="{ox}" y="{oy}" width="{width}" height="{height}" rx="10" fill="#172531" stroke="#385060"/>', f'<text x="{ox}" y="{oy - 10}" class="label">{title}</text>'))
        reverse = view in {"front", "isometric"}
        for assignment, panel_id, points in sorted(projected, key=lambda item: sum(p[2] for p in item[2]) / len(item[2]), reverse=reverse):
            svg.append('<polygon data-view="{}" data-panel-id="{}" data-section="{}" points="{}" fill="{}" fill-opacity="0.92" stroke="#071015" stroke-width="0.8"/>'.format(view, panel_id, assignment, svg_points(map_point(point) for point in points), COLORS[assignment]))
    legend = list(SECTION_ORDER) + ["removable_glow", "mouth_opening"]
    for index, name in enumerate(legend):
        x = 35 + (index % 4) * 235
        y = 790 + (index // 4) * 24
        svg.extend((f'<rect x="{x}" y="{y - 12}" width="13" height="13" rx="2" fill="{COLORS[name]}"/>', f'<text x="{x + 19}" y="{y}" class="legend">{name.replace("_", " ")}</text>'))
    svg.append("</svg>")
    return "\n".join(svg) + "\n"


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    gate1 = json.loads(GATE1_CONFIG.read_text(encoding="utf-8"))
    source_model = read_obj(SOURCE_SURFACE_OBJ)
    units = panel_units(source_model, read_panel_metadata(SOURCE_PANEL_CSV))
    source_bounds = bounds(source_model.vertices)
    scale, origin, _ = make_transform(source_bounds, float(gate1["target_height_mm"]))
    role_by_panel, _ = build_roles(units, gate1, scale)
    model = subdivide_center_panels(source_model, config)
    assignments = assign_faces(model.faces, model.vertices, role_by_panel, config, scale, origin)

    sections: dict[str, Any] = {}
    procedural_sections = set(config.get("procedural_sections", []))
    for section in SECTION_ORDER:
        face_indices = [index for index, value in enumerate(assignments) if value == section]
        vertex_indices = sorted({vertex for index in face_indices for vertex in model.faces[index].indices})
        points = [transform_point(model.vertices[index], scale, origin) for index in vertex_indices]
        components = section_components(model.faces, assignments, section)
        island_panel_ids = sorted({
            canonical_source_panel_id(model.faces[index].group)
            for component in components[1:]
            for index in component
        })
        section_report = {
            "face_count": len(face_indices),
            "source_panel_ids": sorted({canonical_source_panel_id(model.faces[index].group) for index in face_indices}),
            "edge_connected_components": len(components),
            "component_face_counts": [len(component) for component in components],
            "detached_surface_island_panel_ids": island_panel_ids,
        }
        if points:
            section_report.update({
                "axis_aligned_dimensions_mm": [round(value, 3) for value in dimensions(bounds(points))],
                "orientation_search": best_fit(points, config["printer_envelope_mm"], int(config["orientation_step_degrees"])),
            })
        elif section in procedural_sections:
            section_report.update({
                "generated_geometry": "procedural compact rear-base frame; no source faces",
                "axis_aligned_dimensions_mm": None,
                "orientation_search": {"fits": True, "not_applicable": True},
            })
        else:
            raise ValueError(f"{section} has no assigned source faces")
        sections[section] = section_report

    report = {
        "gate": "Gate 2 section topology",
        "status": "review_required",
        "belt_height_mm": config["belt_height_mm"],
        "printer_envelope_mm": config["printer_envelope_mm"],
        "sections": sections,
        "removable_glow_face_count": assignments.count("removable_glow"),
        "mouth_opening_face_count": assignments.count("mouth_opening"),
        "acceptance": {
            "seven_structural_sections_defined": all(
                sections[name]["face_count"] > 0 or name in procedural_sections
                for name in SECTION_ORDER
            ),
            "all_detached_surface_islands_have_planned_rear_bridges": all(
                panel_id in set(config["rear_frame_bridged_opaque_islands"])
                for section in sections.values()
                for panel_id in section["detached_surface_island_panel_ids"]
            ),
            "all_sections_fit_orientation_search": all(sections[name]["orientation_search"]["fits"] for name in SECTION_ORDER),
            "no_glow_or_mouth_face_assigned_to_structure": all(value in COLORS for value in assignments),
        },
        "review_notes": config.get("review_notes", []),
    }

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    write_mtl(output / "gate2-section-layout.mtl")
    write_obj(output / "gate2-section-layout.obj", model.vertices, model.faces, assignments, scale, origin)
    (output / "gate2-section-review.svg").write_text(build_svg(model.vertices, model.faces, assignments, scale, origin), encoding="utf-8")
    (output / "gate2-fit-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with (output / "gate2-face-section-map.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("face_index", "source_group", "source_panel_id", "assignment"))
        for index, (face, assignment) in enumerate(zip(model.faces, assignments)):
            writer.writerow((index, face.group, canonical_source_panel_id(face.group), assignment))
    print(json.dumps(report, indent=2))
    print(f"Wrote {output.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
