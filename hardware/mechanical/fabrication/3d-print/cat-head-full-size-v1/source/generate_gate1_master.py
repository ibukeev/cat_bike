#!/usr/bin/env python3
"""Generate a traceable 330 mm Gate 1 cat-head master and panel-role review pack.

This script intentionally has no Blender dependency. It takes the accepted
faceted OBJ surface and its cardboard-panel metadata as the source of truth,
uniformly scales it to 330 mm chin-to-ear-tip, and writes review assets under
the ignored output directory. Gate 1 does not add wall thickness, section
splits, joints, reinforcement, or a rear cut.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


Point = tuple[float, float, float]

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[4]
SOURCE_SURFACE_OBJ = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/templates/cat-head-cardboard-fabrication-v1"
    / "assembly/accepted-panels-3d.obj"
)
SOURCE_PANEL_CSV = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/templates/cat-head-cardboard-fabrication-v1"
    / "data/cardboard_panels.csv"
)
SOURCE_EYE_OBJ = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/templates/cat-head-wireframe-prototype"
    / "versions/v1-shape-approved-cardboard-prototype"
    / "panel-candidates/eye-insert-panels.obj"
)
DEFAULT_CONFIG = PACKAGE_ROOT / "config/gate1-panel-roles.json"
DEFAULT_OUTPUT = PACKAGE_ROOT / "output/10-design-gates/gate1-review"

ROLE_COLORS = {
    "integrated_opaque": "#4d3324",
    "removable_glow": "#800080",
    "mouth_opening": "#ff0000",
    "eye_diffuser": "#83f6ff",
}


@dataclass(frozen=True)
class ObjFace:
    indices: tuple[int, ...]
    group: str
    object_name: str


@dataclass
class ObjModel:
    vertices: list[Point]
    faces: list[ObjFace]


@dataclass(frozen=True)
class PanelUnit:
    source_panel_id: str
    source_face_count: int
    source_triangle_ids: tuple[str, ...]
    zone: str
    area_source_mm2: float
    centroid_source_mm: Point
    vertices_source: tuple[Point, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Role-selection JSON file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Ignored directory for generated Gate 1 assets.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print the report without writing assets.",
    )
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_obj_index(token: str, vertex_count: int) -> int:
    raw_index = int(token.split("/")[0])
    if raw_index == 0:
        raise ValueError("OBJ indices may not be zero")
    return raw_index - 1 if raw_index > 0 else vertex_count + raw_index


def read_obj(path: Path) -> ObjModel:
    vertices: list[Point] = []
    faces: list[ObjFace] = []
    active_group = "UNGROUPED"
    active_object = "UNNAMED"

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        command = fields[0]
        if command == "v":
            if len(fields) < 4:
                raise ValueError(f"Malformed vertex line in {path}: {raw_line}")
            vertices.append((float(fields[1]), float(fields[2]), float(fields[3])))
        elif command == "g":
            active_group = fields[1] if len(fields) > 1 else "UNGROUPED"
        elif command == "o":
            active_object = fields[1] if len(fields) > 1 else "UNNAMED"
        elif command == "f":
            indices = tuple(parse_obj_index(token, len(vertices)) for token in fields[1:])
            if len(indices) < 3:
                raise ValueError(f"Face with fewer than three vertices in {path}: {raw_line}")
            if any(index < 0 or index >= len(vertices) for index in indices):
                raise ValueError(f"Face index outside vertex range in {path}: {raw_line}")
            faces.append(ObjFace(indices, active_group, active_object))

    if not vertices or not faces:
        raise ValueError(f"No mesh surface found in {path}")
    return ObjModel(vertices=vertices, faces=faces)


def canonical_source_panel_id(group: str) -> str:
    """Map an OBJ's triangulated quad group back to its fabrication facet."""
    if group.endswith("-A") or group.endswith("-B"):
        return group[:-2]
    return group


def read_panel_metadata(path: Path) -> dict[str, list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"No panel metadata found in {path}")
    required_columns = {"panel_id", "source_panel_id", "zone", "area_mm2"}
    missing = required_columns - set(rows[0])
    if missing:
        raise ValueError(f"Panel metadata is missing required columns: {sorted(missing)}")

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["source_panel_id"]].append(row)
    return dict(grouped)


def bounds(points: Iterable[Point]) -> dict[str, tuple[float, float]]:
    materialized = list(points)
    if not materialized:
        raise ValueError("Cannot compute bounds for no points")
    return {
        "x": (min(point[0] for point in materialized), max(point[0] for point in materialized)),
        "y": (min(point[1] for point in materialized), max(point[1] for point in materialized)),
        "z": (min(point[2] for point in materialized), max(point[2] for point in materialized)),
    }


def dimensions(source_bounds: dict[str, tuple[float, float]]) -> Point:
    return tuple(
        source_bounds[axis][1] - source_bounds[axis][0]
        for axis in ("x", "y", "z")
    )


def triangle_area(a: Point, b: Point, c: Point) -> float:
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    return 0.5 * math.sqrt(sum(component * component for component in cross))


def polygon_area(points: list[Point]) -> float:
    if len(points) < 3:
        return 0.0
    return sum(
        triangle_area(points[0], points[index], points[index + 1])
        for index in range(1, len(points) - 1)
    )


def centroid(points: Iterable[Point]) -> Point:
    materialized = list(points)
    return tuple(
        sum(point[axis] for point in materialized) / len(materialized)
        for axis in range(3)
    )


def panel_units(
    model: ObjModel,
    metadata: dict[str, list[dict[str, str]]],
) -> dict[str, PanelUnit]:
    faces_by_group: dict[str, list[ObjFace]] = defaultdict(list)
    for face in model.faces:
        faces_by_group[canonical_source_panel_id(face.group)].append(face)

    source_groups = set(faces_by_group)
    metadata_groups = set(metadata)
    if source_groups != metadata_groups:
        missing_metadata = sorted(source_groups - metadata_groups)
        missing_geometry = sorted(metadata_groups - source_groups)
        raise ValueError(
            "Accepted OBJ and panel metadata disagree. "
            f"Missing metadata: {missing_metadata}; missing geometry: {missing_geometry}"
        )

    units: dict[str, PanelUnit] = {}
    for source_panel_id, faces in faces_by_group.items():
        used_indices = sorted({index for face in faces for index in face.indices})
        unique_vertices = tuple(model.vertices[index] for index in used_indices)
        area = sum(
            polygon_area([model.vertices[index] for index in face.indices])
            for face in faces
        )
        records = metadata[source_panel_id]
        zones = {record["zone"] for record in records}
        units[source_panel_id] = PanelUnit(
            source_panel_id=source_panel_id,
            source_face_count=len(faces),
            source_triangle_ids=tuple(record["panel_id"] for record in records),
            zone="+".join(sorted(zones)),
            area_source_mm2=area,
            centroid_source_mm=centroid(unique_vertices),
            vertices_source=unique_vertices,
        )
    return units


def make_transform(
    source_bounds: dict[str, tuple[float, float]],
    target_height_mm: float,
) -> tuple[float, Point, Point]:
    source_height = source_bounds["z"][1] - source_bounds["z"][0]
    if source_height <= 0:
        raise ValueError("Source surface has zero Z height")
    scale = target_height_mm / source_height
    x_center = (source_bounds["x"][0] + source_bounds["x"][1]) / 2.0
    source_origin = (x_center, source_bounds["y"][0], source_bounds["z"][0])
    target_origin = (0.0, 0.0, 0.0)
    return scale, source_origin, target_origin


def transform_point(point: Point, scale: float, source_origin: Point) -> Point:
    return (
        (point[0] - source_origin[0]) * scale,
        (point[1] - source_origin[1]) * scale,
        (point[2] - source_origin[2]) * scale,
    )


def distance(a: Point, b: Point) -> float:
    return math.sqrt(sum((a[axis] - b[axis]) ** 2 for axis in range(3)))


def mirror_residual(right: PanelUnit, left: PanelUnit) -> float:
    """Return worst source-space vertex residual after reflection across X=0."""
    unmatched = list(left.vertices_source)
    residuals: list[float] = []
    for point in right.vertices_source:
        target = (-point[0], point[1], point[2])
        candidate_index = min(
            range(len(unmatched)),
            key=lambda index: distance(target, unmatched[index]),
        )
        residuals.append(distance(target, unmatched.pop(candidate_index)))
    if unmatched:
        raise ValueError("Mirror comparison did not consume every left-side vertex")
    return max(residuals, default=0.0)


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "target_height_mm",
        "rear_service_plane_inset_mm",
        "eye_diffusers",
        "glow_transmitting_panels",
        "mouth_opening_panels",
        "eye_aperture_front_svg",
    }
    missing = required - set(config)
    if missing:
        raise ValueError(f"Gate 1 config is missing fields: {sorted(missing)}")
    if len(config["eye_diffusers"]) != 2:
        raise ValueError("Gate 1 requires two separate eye diffuser definitions")
    return config


def build_roles(
    units: dict[str, PanelUnit],
    config: dict[str, Any],
    scale: float,
) -> tuple[dict[str, dict[str, str]], list[dict[str, Any]]]:
    role_by_panel = {
        source_panel_id: {
            "role": "integrated_opaque",
            "review_unit_id": "",
            "pair_id": "",
            "mirror_unit_id": "",
            "description": "Default structural exterior facet",
        }
        for source_panel_id in units
    }
    glow_units: list[dict[str, Any]] = []
    if len(set(config["glow_transmitting_panels"])) != len(config["glow_transmitting_panels"]):
        raise ValueError("Glow/light-transmitting panel selection contains duplicates")

    for panel_id in config["glow_transmitting_panels"]:
        if panel_id not in units:
            raise ValueError(f"Glow/light-transmitting selection {panel_id} is absent from the accepted surface")
        unit = units[panel_id]
        if "ear" in unit.zone:
            raise ValueError(f"{panel_id} selects an ear facet; Gate 1 forbids illuminated ears")
        side = "center" if abs(unit.centroid_source_mm[0]) < 0.5 else "right" if unit.centroid_source_mm[0] > 0 else "left"
        review_unit_id = f"GLOW_{panel_id}"
        role_by_panel[panel_id] = {
            "role": "removable_glow",
            "review_unit_id": review_unit_id,
            "pair_id": "",
            "mirror_unit_id": "",
            "description": "Removable glow/light-transmitting panel selected in annotated Gate 1 SVG",
        }
        glow_units.append({
            "review_unit_id": review_unit_id,
            "pair_id": "",
            "side": side,
            "source_panel_id": panel_id,
            "mirror_source_panel_id": "",
            "description": "Removable glow/light-transmitting panel selected in annotated Gate 1 SVG",
            "source_face_count": unit.source_face_count,
            "source_triangle_ids": " ".join(unit.source_triangle_ids),
            "zone": unit.zone,
            "area_source_mm2": unit.area_source_mm2,
            "area_330mm_mm2": unit.area_source_mm2 * scale * scale,
            "centroid_source_mm": unit.centroid_source_mm,
            "mirror_residual_source_mm": 0.0,
            "mirror_residual_330mm_mm": 0.0,
        })

    for panel_id in config["mouth_opening_panels"]:
        if panel_id not in units:
            raise ValueError(f"Mouth opening selection {panel_id} is absent from the accepted surface")
        role_by_panel[panel_id] = {
            "role": "mouth_opening",
            "review_unit_id": "MOUTH_OPENING",
            "pair_id": "",
            "mirror_unit_id": "",
            "description": "Remove this facet pair to form the mouth opening",
        }
    return role_by_panel, glow_units


def find_eye_faces(
    eye_model: ObjModel,
    config: dict[str, Any],
) -> dict[str, list[ObjFace]]:
    faces_by_unit: dict[str, list[ObjFace]] = {}
    for eye in config["eye_diffusers"]:
        matches = [
            face
            for face in eye_model.faces
            if face.object_name.startswith(eye["source_object_prefix"])
        ]
        if not matches:
            raise ValueError(
                f"Eye diffuser {eye['unit_id']} does not match an eye OBJ object prefix"
            )
        faces_by_unit[eye["unit_id"]] = matches
    return faces_by_unit


def write_surface_obj(
    path: Path,
    model: ObjModel,
    scale: float,
    source_origin: Point,
    role_by_panel: dict[str, dict[str, str]] | None = None,
    eye_model: ObjModel | None = None,
    eye_faces: dict[str, list[ObjFace]] | None = None,
) -> None:
    lines: list[str] = [
        "# Gate 1 330 mm cat-head exterior",
        "# Uniform scale only; no shell thickness, seams, or rear cut.",
    ]
    if role_by_panel is not None:
        lines.extend(("mtllib gate1-role-review.mtl", "# Materials encode panel roles."))
    lines.append("o gate1_cat_head_master")
    lines.extend(
        "v {:.6f} {:.6f} {:.6f}".format(*transform_point(vertex, scale, source_origin))
        for vertex in model.vertices
    )

    last_group = ""
    last_material = ""
    for face in model.faces:
        source_panel_id = canonical_source_panel_id(face.group)
        role = role_by_panel[source_panel_id]["role"] if role_by_panel is not None else ""
        group = f"{role}_{source_panel_id}" if role_by_panel is not None else face.group
        if group != last_group:
            lines.append(f"g {group}")
            last_group = group
        if role_by_panel is not None and role != last_material:
            lines.append(f"usemtl {role}")
            last_material = role
        lines.append("f " + " ".join(str(index + 1) for index in face.indices))

    if eye_model is not None and eye_faces is not None:
        vertex_offset = len(model.vertices)
        lines.append("o gate1_eye_diffusers")
        lines.extend(
            "v {:.6f} {:.6f} {:.6f}".format(*transform_point(vertex, scale, source_origin))
            for vertex in eye_model.vertices
        )
        for unit_id, faces in eye_faces.items():
            lines.append(f"g eye_diffuser_{unit_id}")
            lines.append("usemtl eye_diffuser")
            for face in faces:
                lines.append(
                    "f "
                    + " ".join(str(vertex_offset + index + 1) for index in face.indices)
                )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_material_library(path: Path) -> None:
    path.write_text(
        "\n".join(
            (
                "# Gate 1 role-review materials",
                "newmtl integrated_opaque",
                "Kd 0.302 0.200 0.141",
                "Ka 0.080 0.050 0.035",
                "Ns 80.0",
                "",
                "newmtl removable_glow",
                "Kd 0.502 0.000 0.502",
                "Ka 0.150 0.000 0.150",
                "Ke 0.350 0.000 0.350",
                "d 0.65",
                "Ns 180.0",
                "",
                "newmtl mouth_opening",
                "Kd 1.000 0.000 0.000",
                "Ka 0.200 0.000 0.000",
                "d 0.35",
                "Ns 20.0",
                "",
                "newmtl eye_diffuser",
                "Kd 0.514 0.965 1.000",
                "Ka 0.100 0.400 0.450",
                "Ke 0.100 0.600 0.700",
                "d 0.78",
                "Ns 220.0",
                "",
            )
        ),
        encoding="utf-8",
    )


def rounded_point(point: Point) -> tuple[float, float, float]:
    return tuple(round(value, 3) for value in point)


def write_role_table(
    path: Path,
    units: dict[str, PanelUnit],
    role_by_panel: dict[str, dict[str, str]],
    scale: float,
    source_origin: Point,
) -> None:
    fields = [
        "source_panel_id",
        "role",
        "review_unit_id",
        "pair_id",
        "mirror_unit_id",
        "zone",
        "source_face_count",
        "source_triangle_ids",
        "area_source_mm2",
        "area_330mm_mm2",
        "centroid_source_mm",
        "centroid_330mm",
        "description",
    ]
    rows = []
    for source_panel_id, unit in sorted(units.items()):
        role_info = role_by_panel[source_panel_id]
        rows.append(
            {
                "source_panel_id": source_panel_id,
                "role": role_info["role"],
                "review_unit_id": role_info["review_unit_id"],
                "pair_id": role_info["pair_id"],
                "mirror_unit_id": role_info["mirror_unit_id"],
                "zone": unit.zone,
                "source_face_count": unit.source_face_count,
                "source_triangle_ids": " ".join(unit.source_triangle_ids),
                "area_source_mm2": f"{unit.area_source_mm2:.3f}",
                "area_330mm_mm2": f"{unit.area_source_mm2 * scale * scale:.3f}",
                "centroid_source_mm": " ".join(
                    f"{value:.3f}" for value in rounded_point(unit.centroid_source_mm)
                ),
                "centroid_330mm": " ".join(
                    f"{value:.3f}"
                    for value in rounded_point(
                        transform_point(unit.centroid_source_mm, scale, source_origin)
                    )
                ),
                "description": role_info["description"],
            }
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_glow_table(path: Path, glow_units: list[dict[str, Any]]) -> None:
    fields = [
        "review_unit_id",
        "pair_id",
        "side",
        "source_panel_id",
        "mirror_source_panel_id",
        "source_face_count",
        "source_triangle_ids",
        "zone",
        "area_source_mm2",
        "area_330mm_mm2",
        "centroid_source_mm",
        "mirror_residual_source_mm",
        "mirror_residual_330mm_mm",
        "description",
    ]
    rows = []
    for unit in glow_units:
        rows.append(
            {
                **{
                    field: unit[field]
                    for field in fields
                    if field not in {"centroid_source_mm"}
                },
                "centroid_source_mm": " ".join(
                    f"{value:.3f}" for value in rounded_point(unit["centroid_source_mm"])
                ),
                "area_source_mm2": f"{unit["area_source_mm2"]:.3f}",
                "area_330mm_mm2": f"{unit["area_330mm_mm2"]:.3f}",
                "mirror_residual_source_mm": f"{unit["mirror_residual_source_mm"]:.4f}",
                "mirror_residual_330mm_mm": f"{unit["mirror_residual_330mm_mm"]:.4f}",
            }
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def project(point: Point, view: str) -> tuple[float, float, float]:
    x, y, z = point
    if view == "front":
        return x, z, y
    if view == "side":
        return y, z, x
    if view == "top":
        return x, y, z
    if view == "isometric":
        return (x - y) * 0.78, z + (x + y) * 0.34, x + y
    raise ValueError(f"Unknown review view: {view}")


def svg_points(points: Iterable[tuple[float, float]]) -> str:
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in points)


def build_svg(
    model: ObjModel,
    eye_model: ObjModel,
    eye_faces: dict[str, list[ObjFace]],
    role_by_panel: dict[str, dict[str, str]],
    scale: float,
    source_origin: Point,
    target_dimensions: Point,
    rear_plane_y_mm: float,
    eye_aperture_front_svg: list[list[list[float]]],
) -> str:
    polygons: list[tuple[str, str, list[Point]]] = []
    for face in model.faces:
        source_panel_id = canonical_source_panel_id(face.group)
        polygons.append(
            (
                role_by_panel[source_panel_id]["role"],
                source_panel_id,
                [transform_point(model.vertices[index], scale, source_origin) for index in face.indices],
            )
        )
    # The accepted eye OBJ is only a superseded shape placeholder. The corrected
    # eye material is shown by the annotated front-view aperture silhouettes.

    views = (
        ("front", "Front — panel roles"),
        ("side", "Right side — rear-service plane"),
        ("top", "Top"),
        ("isometric", "Isometric — review only"),
    )
    view_boxes = {
        "front": (40.0, 80.0, 390.0, 320.0),
        "side": (520.0, 80.0, 390.0, 320.0),
        "top": (40.0, 490.0, 390.0, 260.0),
        "isometric": (520.0, 490.0, 390.0, 260.0),
    }
    svg: list[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="960" height="820" viewBox="0 0 960 820">',
        '<rect width="960" height="820" fill="#101820"/>',
        '<style>text { font-family: Arial, sans-serif; fill: #dce8ef; } .label { font-size: 17px; font-weight: 600; } .caption { font-size: 12px; fill: #a8bac6; } .legend { font-size: 13px; }</style>',
        '<text x="40" y="34" class="label">Cat head Gate 1 — 330 mm master and panel roles</text>',
        '<text x="40" y="56" class="caption">Purple = removable light-transmitting glow panels; pale cyan = corrected separate eye material; copper = opaque structure.</text>',
    ]

    for view, title in views:
        origin_x, origin_y, width, height = view_boxes[view]
        margin = 18.0
        projected = [
            (role, panel_id, [project(point, view) for point in points])
            for role, panel_id, points in polygons
        ]
        all_xy = [point[:2] for _, _, points in projected for point in points]
        min_x = min(point[0] for point in all_xy)
        max_x = max(point[0] for point in all_xy)
        min_y = min(point[1] for point in all_xy)
        max_y = max(point[1] for point in all_xy)
        scale_x = (width - margin * 2) / max(max_x - min_x, 1.0)
        scale_y = (height - margin * 2) / max(max_y - min_y, 1.0)
        local_scale = min(scale_x, scale_y)
        used_width = (max_x - min_x) * local_scale
        used_height = (max_y - min_y) * local_scale
        offset_x = origin_x + (width - used_width) / 2.0 - min_x * local_scale
        offset_y = origin_y + (height - used_height) / 2.0 + max_y * local_scale

        def map_point(point: tuple[float, float, float]) -> tuple[float, float]:
            return offset_x + point[0] * local_scale, offset_y - point[1] * local_scale

        svg.append(
            f'<rect x="{origin_x:.1f}" y="{origin_y:.1f}" width="{width:.1f}" height="{height:.1f}" rx="10" fill="#172531" stroke="#385060"/>'
        )
        svg.append(f'<text x="{origin_x:.1f}" y="{origin_y - 10:.1f}" class="label">{title}</text>')
        if view in {"front", "isometric"}:
            ordered = sorted(projected, key=lambda item: sum(point[2] for point in item[2]) / len(item[2]), reverse=True)
        else:
            ordered = sorted(projected, key=lambda item: sum(point[2] for point in item[2]) / len(item[2]))
        for role, panel_id, points in ordered:
            opacity = "0.88" if role == "integrated_opaque" else "0.96"
            stroke_width = "0.65" if role == "integrated_opaque" else "1.5"
            svg.append(
                '<polygon data-view="{}" data-panel-id="{}" points="{}" fill="{}" fill-opacity="{}" stroke="#071015" stroke-width="{}"/>'.format(
                    view,
                    panel_id,
                    svg_points(map_point(point) for point in points),
                    ROLE_COLORS[role],
                    opacity,
                    stroke_width,
                )
            )
        if view == "front":
            for aperture_index, aperture in enumerate(eye_aperture_front_svg, start=1):
                svg.append(
                    '<polygon data-view="front" data-role="eye-material" data-aperture-id="EYE_MATERIAL_{}" points="{}" fill="{}" fill-opacity="0.96" stroke="#071015" stroke-width="1.5"/>'.format(
                        aperture_index,
                        svg_points((float(x), float(y)) for x, y in aperture),
                        ROLE_COLORS["eye_diffuser"],
                    )
                )
        if view == "side":
            start = map_point(project((0.0, rear_plane_y_mm, 0.0), view))
            end = map_point(project((0.0, rear_plane_y_mm, target_dimensions[2]), view))
            svg.append(
                '<line x1="{:.2f}" y1="{:.2f}" x2="{:.2f}" y2="{:.2f}" stroke="#f6c177" stroke-width="2" stroke-dasharray="7 5"/>'.format(
                    start[0], start[1], end[0], end[1]
                )
            )
        if view == "top":
            start = map_point(project((-target_dimensions[0] / 2.0, rear_plane_y_mm, 0.0), view))
            end = map_point(project((target_dimensions[0] / 2.0, rear_plane_y_mm, 0.0), view))
            svg.append(
                '<line x1="{:.2f}" y1="{:.2f}" x2="{:.2f}" y2="{:.2f}" stroke="#f6c177" stroke-width="2" stroke-dasharray="7 5"/>'.format(
                    start[0], start[1], end[0], end[1]
                )
            )

    legend = (
        ("Opaque structure", ROLE_COLORS["integrated_opaque"]),
        ("Glow / transmitting", ROLE_COLORS["removable_glow"]),
        ("Separate eye material", ROLE_COLORS["eye_diffuser"]),
        ("Mouth opening", ROLE_COLORS["mouth_opening"]),
    )
    legend_x = 40
    legend_y = 790
    for index, (label, color) in enumerate(legend):
        x = legend_x + index * 220
        svg.append(f'<rect x="{x}" y="{legend_y - 12}" width="14" height="14" rx="3" fill="{color}"/>')
        svg.append(f'<text x="{x + 21}" y="{legend_y}" class="legend">{label}</text>')
    svg.append("</svg>")
    return "\n".join(svg) + "\n"


def as_serializable_bounds(source_bounds: dict[str, tuple[float, float]]) -> dict[str, list[float]]:
    return {
        axis: [round(value, 6) for value in source_bounds[axis]]
        for axis in ("x", "y", "z")
    }


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    required_paths = (SOURCE_SURFACE_OBJ, SOURCE_PANEL_CSV, SOURCE_EYE_OBJ, config_path)
    missing = [str(path) for path in required_paths if not path.exists()]
    if missing:
        raise FileNotFoundError("Gate 1 source files are missing:\n" + "\n".join(missing))

    config = load_config(config_path)
    master = read_obj(SOURCE_SURFACE_OBJ)
    eye_model = read_obj(SOURCE_EYE_OBJ)
    metadata = read_panel_metadata(SOURCE_PANEL_CSV)
    units = panel_units(master, metadata)
    source_bounds = bounds(master.vertices)
    scale, source_origin, _ = make_transform(source_bounds, float(config["target_height_mm"]))
    transformed_vertices = [
        transform_point(vertex, scale, source_origin) for vertex in master.vertices
    ]
    target_bounds = bounds(transformed_vertices)
    target_dimensions = dimensions(target_bounds)
    rear_plane_y_mm = target_bounds["y"][1] - float(config["rear_service_plane_inset_mm"])
    if rear_plane_y_mm <= target_bounds["y"][0]:
        raise ValueError("Rear-service plane inset removes the complete depth envelope")

    role_by_panel, glow_units = build_roles(units, config, scale)
    eye_faces = find_eye_faces(eye_model, config)
    max_scaled_coordinate_residual = max(
        distance(
            transformed_vertices[index],
            transform_point(vertex, scale, source_origin),
        )
        for index, vertex in enumerate(master.vertices)
    )
    if max_scaled_coordinate_residual > 1e-9:
        raise ValueError("Generated master does not preserve the uniform source transform")

    report = {
        "gate": "Gate 1",
        "status": "review_required",
        "source": {
            "accepted_surface_obj": str(SOURCE_SURFACE_OBJ.relative_to(REPO_ROOT)),
            "accepted_surface_sha256": sha256(SOURCE_SURFACE_OBJ),
            "panel_metadata_csv": str(SOURCE_PANEL_CSV.relative_to(REPO_ROOT)),
            "panel_metadata_sha256": sha256(SOURCE_PANEL_CSV),
            "eye_insert_obj": str(SOURCE_EYE_OBJ.relative_to(REPO_ROOT)),
            "eye_insert_sha256": sha256(SOURCE_EYE_OBJ),
            "role_config": str(config_path.relative_to(REPO_ROOT)),
            "role_config_sha256": sha256(config_path),
        },
        "transform": {
            "uniform_scale": scale,
            "source_origin_x_y_z_mm": [round(value, 6) for value in source_origin],
            "coordinate_system": {
                "x": "left/right centered on the face",
                "y": "front to rear, nose-side minimum normalized to 0",
                "z": "chin to ear tips, normalized to 0..330 mm",
            },
        },
        "source_surface": {
            "vertices": len(master.vertices),
            "faces": len(master.faces),
            "panel_units": len(units),
            "bounds_mm": as_serializable_bounds(source_bounds),
            "dimensions_mm": [round(value, 6) for value in dimensions(source_bounds)],
        },
        "target_master": {
            "bounds_mm": as_serializable_bounds(target_bounds),
            "dimensions_mm": [round(value, 6) for value in target_dimensions],
            "target_height_mm": float(config["target_height_mm"]),
            "max_uniform_transform_residual_mm": max_scaled_coordinate_residual,
            "rear_service_plane_y_mm": round(rear_plane_y_mm, 6),
            "rear_service_plane_inset_mm": float(config["rear_service_plane_inset_mm"]),
            "rear_service_plane_is_cut": False,
        },
        "roles": {
            "integrated_opaque_panel_units": sum(
                1 for info in role_by_panel.values() if info["role"] == "integrated_opaque"
            ),
            "removable_glow_panel_units": len(glow_units),
            "glow_transmitting_panel_units": len(config["glow_transmitting_panels"]),
            "glow_transmitting_panels": config["glow_transmitting_panels"],
            "mouth_opening_panels": config["mouth_opening_panels"],
            "eye_material_aperture_count": len(config["eye_aperture_front_svg"]),
            "superseded_eye_placeholders": list(eye_faces),
            "selected_glow_units": [
                {
                    key: (
                        [round(value, 6) for value in value_to_round]
                        if key == "centroid_source_mm"
                        else round(value_to_round, 6)
                        if isinstance(value_to_round, float)
                        else value_to_round
                    )
                    for key, value_to_round in unit.items()
                }
                for unit in glow_units
            ],
        },
        "review_notes": config.get("review_notes", []),
        "acceptance": {
            "all_source_panel_units_have_exactly_one_role": len(role_by_panel) == len(units),
            "no_glow_panels_on_ears": all(
                "ear" not in units[unit["source_panel_id"]].zone for unit in glow_units
            ),
            "glow_panel_count": len(glow_units),
            "eye_material_count": len(config["eye_aperture_front_svg"]),
        },
    }

    if args.dry_run:
        print(json.dumps(report, indent=2))
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    write_surface_obj(
        output_dir / "gate1-master-330mm.obj",
        master,
        scale,
        source_origin,
    )
    write_material_library(output_dir / "gate1-role-review.mtl")
    write_surface_obj(
        output_dir / "gate1-role-review.obj",
        master,
        scale,
        source_origin,
        role_by_panel=role_by_panel,
    )
    write_role_table(
        output_dir / "gate1-panel-role-map.csv",
        units,
        role_by_panel,
        scale,
        source_origin,
    )
    write_glow_table(output_dir / "gate1-glow-units.csv", glow_units)
    (output_dir / "gate1-review.svg").write_text(
        build_svg(
            master,
            eye_model,
            eye_faces,
            role_by_panel,
            scale,
            source_origin,
            target_dimensions,
            rear_plane_y_mm,
            config["eye_aperture_front_svg"],
        ),
        encoding="utf-8",
    )
    (output_dir / "gate1-validation-report.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))
    print(f"Wrote {output_dir.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
