#!/usr/bin/env python3
"""Validate and render the approved right-upper 10 mm-brim slicer layout."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile


CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
MODEL_MEMBER = "3D/3dmodel.model"
PRINT_CONFIG_MEMBER = "Metadata/Slic3r_PE.config"
BED_SIZE_MM = (250.0, 210.0, 220.0)
MINIMUM_FIRST_LAYER_MARGIN_MM = 5.0
FIRST_LAYER_LINE_WIDTH_MM = 0.5
TRANSFORM_TOLERANCE = 1.0e-8
BOUNDS_TOLERANCE_MM = 1.0e-5


Matrix = tuple[tuple[float, float, float], ...]
Vector = tuple[float, float, float]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_transform(transform: str) -> tuple[Matrix, Vector]:
    values = [float(value) for value in transform.split()]
    if len(values) != 12:
        raise RuntimeError("Expected a 12-value 3MF transform")
    matrix: Matrix = (
        (values[0], values[3], values[6]),
        (values[1], values[4], values[7]),
        (values[2], values[5], values[8]),
    )
    return matrix, (values[9], values[10], values[11])


def flat_transform(matrix: Matrix, translation: Vector) -> list[float]:
    return [
        matrix[0][0], matrix[1][0], matrix[2][0],
        matrix[0][1], matrix[1][1], matrix[2][1],
        matrix[0][2], matrix[1][2], matrix[2][2],
        *translation,
    ]


def matrix_vector(matrix: Matrix, vector: Vector) -> Vector:
    return tuple(
        sum(matrix[row][index] * vector[index] for index in range(3))
        for row in range(3)
    )


def transform_point(matrix: Matrix, translation: Vector, point: Vector) -> Vector:
    rotated = matrix_vector(matrix, point)
    return tuple(rotated[index] + translation[index] for index in range(3))


def bounds(points: list[Vector]) -> tuple[Vector, Vector]:
    return (
        tuple(min(point[index] for point in points) for index in range(3)),
        tuple(max(point[index] for point in points) for index in range(3)),
    )


def setting(config: bytes, key: str) -> str:
    match = re.search(rb"(?m)^; " + re.escape(key.encode()) + rb" = ([^\r\n]+)$", config)
    if match is None:
        raise RuntimeError(f"Missing slicer setting: {key}")
    return match.group(1).decode("utf-8")


def replace_setting(config: bytes, key: str, value: str) -> bytes:
    pattern = rb"(?m)^; " + re.escape(key.encode()) + rb" = [^\r\n]+$"
    updated, count = re.subn(
        pattern,
        f"; {key} = {value}".encode("utf-8"),
        config,
    )
    if count != 1:
        raise RuntimeError(f"Expected exactly one {key} setting, found {count}")
    return updated


def archive_validation(
    source_project: Path,
    review_project: Path,
    contract: dict,
) -> dict:
    with zipfile.ZipFile(source_project, "r") as source_zip, zipfile.ZipFile(
        review_project, "r"
    ) as review_zip:
        source_names = [info.filename for info in source_zip.infolist()]
        review_names = [info.filename for info in review_zip.infolist()]
        if source_names != review_names:
            raise RuntimeError("3MF archive member order or set changed")

        source_model = source_zip.read(MODEL_MEMBER)
        review_model = review_zip.read(MODEL_MEMBER)
        source_config = source_zip.read(PRINT_CONFIG_MEMBER)
        review_config = review_zip.read(PRINT_CONFIG_MEMBER)

        namespace = {"m": CORE_NS}
        source_root = ET.fromstring(source_model)
        review_root = ET.fromstring(review_model)
        source_items = source_root.findall(".//m:build/m:item", namespace)
        review_items = review_root.findall(".//m:build/m:item", namespace)
        if len(source_items) != 1 or len(review_items) != 1:
            raise RuntimeError("Expected one build item in source and review 3MFs")
        source_transform = source_items[0].attrib["transform"]
        review_transform = review_items[0].attrib["transform"]

        review_transform_attribute = f'transform="{review_transform}"'.encode("utf-8")
        source_transform_attribute = f'transform="{source_transform}"'.encode("utf-8")
        restored_model, replacement_count = review_model.replace(
            review_transform_attribute,
            source_transform_attribute,
            1,
        ), review_model.count(review_transform_attribute)
        if replacement_count != 1 or restored_model != source_model:
            raise RuntimeError("3MF model changed beyond the approved build transform")

        restored_config = replace_setting(
            review_config,
            "brim_type",
            setting(source_config, "brim_type"),
        )
        restored_config = replace_setting(
            restored_config,
            "brim_width",
            setting(source_config, "brim_width"),
        )
        if restored_config != source_config:
            raise RuntimeError("Slicer config changed beyond brim_type and brim_width")

        changed_members: list[str] = []
        unchanged_member_hashes: dict[str, str] = {}
        for name in source_names:
            source_payload = source_zip.read(name)
            review_payload = review_zip.read(name)
            if source_payload != review_payload:
                changed_members.append(name)
            else:
                unchanged_member_hashes[name] = hashlib.sha256(source_payload).hexdigest()
        if changed_members != [MODEL_MEMBER, PRINT_CONFIG_MEMBER]:
            raise RuntimeError(f"Unexpected changed 3MF members: {changed_members}")

        matrix, translation = parse_transform(review_transform)
        actual_transform = flat_transform(matrix, translation)
        expected_transform = contract["approved_change"]["final_transform_3mf"]
        transform_residuals = [
            actual - expected for actual, expected in zip(actual_transform, expected_transform)
        ]
        if max(abs(residual) for residual in transform_residuals) > TRANSFORM_TOLERANCE:
            raise RuntimeError(f"Final transform mismatch: residuals={transform_residuals}")

        vertices = [
            tuple(float(vertex.attrib[key]) for key in ("x", "y", "z"))
            for vertex in review_root.findall(".//m:vertex", namespace)
        ]
        triangles = review_root.findall(".//m:triangle", namespace)
        expected_vertices = contract["frozen"]["mesh_vertices"]
        expected_triangles = contract["frozen"]["mesh_triangles"]
        if len(vertices) != expected_vertices or len(triangles) != expected_triangles:
            raise RuntimeError("Review mesh topology count changed")

        world_points = [transform_point(matrix, translation, vertex) for vertex in vertices]
        minimum, maximum = bounds(world_points)
        size = [maximum[index] - minimum[index] for index in range(3)]
        expected_size = contract["pre_slice_envelope"]["object_bbox_size_mm"]
        size_residuals = [actual - expected for actual, expected in zip(size, expected_size)]
        if max(abs(residual) for residual in size_residuals) > BOUNDS_TOLERANCE_MM:
            raise RuntimeError(f"Object bounds mismatch: residuals={size_residuals}")

        column_norms = [
            math.sqrt(sum(matrix[row][column] ** 2 for row in range(3)))
            for column in range(3)
        ]
        determinant = (
            matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
            - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
            + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
        )
        if max(abs(norm - 1.0) for norm in column_norms) > 1.0e-8:
            raise RuntimeError(f"Unexpected scale in transform: column_norms={column_norms}")
        if abs(determinant - 1.0) > 1.0e-8:
            raise RuntimeError(f"Unexpected transform determinant: {determinant}")

        return {
            "archive_member_set_and_order_unchanged": True,
            "changed_members_exactly": changed_members,
            "all_other_member_hashes_unchanged": True,
            "unchanged_member_hashes": unchanged_member_hashes,
            "model_change_only_build_transform": True,
            "config_change_only_brim_type_and_width": True,
            "mesh_vertices": len(vertices),
            "mesh_triangles": len(triangles),
            "mesh_topology_counts_unchanged": True,
            "scale": column_norms,
            "determinant": determinant,
            "final_transform": actual_transform,
            "transform_expected": expected_transform,
            "transform_tolerance": TRANSFORM_TOLERANCE,
            "transform_residuals": transform_residuals,
            "object_bounds_min_mm": list(minimum),
            "object_bounds_max_mm": list(maximum),
            "object_bbox_size_mm": size,
            "object_bbox_expected_mm": expected_size,
            "object_bbox_tolerance_mm": BOUNDS_TOLERANCE_MM,
            "object_bbox_residuals_mm": size_residuals,
            "brim_type": setting(review_config, "brim_type"),
            "brim_width_mm": float(setting(review_config, "brim_width")),
            "brim_separation_mm": float(setting(review_config, "brim_separation")),
        }


def parse_command_words(line: str) -> dict[str, float]:
    words: dict[str, float] = {}
    for key, value in re.findall(r"(?:^|\s)([XYZE])(-?(?:\d+(?:\.\d*)?|\.\d+))", line):
        words[key] = float(value)
    return words


def gcode_validation(gcode_path: Path) -> tuple[dict, dict[str, list[tuple[float, float, float, float]]]]:
    first_layer_started = False
    first_layer_complete = False
    layer_change_count = 0
    current_type = "Unclassified"
    current_x: float | None = None
    current_y: float | None = None
    segments: dict[str, list[tuple[float, float, float, float]]] = defaultdict(list)
    centerline_x: list[float] = []
    centerline_y: list[float] = []
    m555: dict[str, float] | None = None
    settings: dict[str, str] = {}
    metadata: dict[str, str | float] = {}
    generated_by = ""

    with gcode_path.open("r", encoding="utf-8", errors="strict") as stream:
        for line in stream:
            stripped = line.strip()
            if stripped.startswith("; generated by PrusaSlicer"):
                generated_by = stripped.removeprefix("; generated by ")
            if stripped.startswith("M555 "):
                values = {
                    key: float(value)
                    for key, value in re.findall(r"([XYWH])(-?(?:\d+(?:\.\d*)?|\.\d+))", stripped)
                }
                if set(values) == {"X", "Y", "W", "H"}:
                    m555 = values
            if stripped == ";LAYER_CHANGE":
                layer_change_count += 1
                if layer_change_count == 1:
                    first_layer_started = True
                elif layer_change_count == 2:
                    first_layer_complete = True
                    first_layer_started = False
            if first_layer_started and stripped.startswith(";TYPE:"):
                current_type = stripped.removeprefix(";TYPE:")
            if first_layer_started and not first_layer_complete and re.match(r"^G[01](?:\s|$)", stripped):
                words = parse_command_words(stripped)
                next_x = words.get("X", current_x)
                next_y = words.get("Y", current_y)
                extrusion = words.get("E", 0.0)
                if (
                    extrusion > 0.0
                    and current_x is not None
                    and current_y is not None
                    and next_x is not None
                    and next_y is not None
                    and (next_x != current_x or next_y != current_y)
                ):
                    segments[current_type].append((current_x, current_y, next_x, next_y))
                    centerline_x.extend((current_x, next_x))
                    centerline_y.extend((current_y, next_y))
                current_x, current_y = next_x, next_y

            setting_match = re.match(r"^; ([a-zA-Z0-9_]+) = (.*)$", stripped)
            if setting_match:
                settings[setting_match.group(1)] = setting_match.group(2)
            for label, key in (
                ("; filament used [mm] = ", "filament_length_mm"),
                ("; filament used [cm3] = ", "filament_volume_cm3"),
                ("; filament used [g] = ", "filament_mass_g"),
                ("; estimated printing time (normal mode) = ", "estimated_print_time"),
            ):
                if stripped.startswith(label):
                    raw = stripped.removeprefix(label)
                    metadata[key] = raw if key == "estimated_print_time" else float(raw)

    if not first_layer_complete or not centerline_x or not centerline_y:
        raise RuntimeError("Could not parse a complete extruded first layer")
    if m555 is None:
        raise RuntimeError("Generated G-code does not contain M555 footprint metadata")
    if settings.get("brim_type") != "outer_only" or settings.get("brim_width") != "10":
        raise RuntimeError(
            f"Generated G-code brim mismatch: {settings.get('brim_type')}/{settings.get('brim_width')}"
        )
    if settings.get("support_material") != "1" or settings.get("support_material_style") != "snug":
        raise RuntimeError("Generated G-code did not retain approved snug supports")
    if not segments.get("Skirt/Brim"):
        raise RuntimeError("No first-layer brim extrusion paths were found")
    support_segment_count = sum(
        len(type_segments)
        for path_type, type_segments in segments.items()
        if path_type.startswith("Support material")
    )
    if support_segment_count == 0:
        raise RuntimeError("No first-layer support extrusion paths were found")

    radius = FIRST_LAYER_LINE_WIDTH_MM / 2.0
    minimum = (min(centerline_x) - radius, min(centerline_y) - radius)
    maximum = (max(centerline_x) + radius, max(centerline_y) + radius)
    margins = {
        "left": minimum[0],
        "right": BED_SIZE_MM[0] - maximum[0],
        "front": minimum[1],
        "rear": BED_SIZE_MM[1] - maximum[1],
    }
    if min(margins.values()) < MINIMUM_FIRST_LAYER_MARGIN_MM:
        raise RuntimeError(f"First-layer bed margin failed: {margins}")

    result = {
        "prusa_slicer": generated_by,
        "slice_completed": True,
        "brim_type": settings["brim_type"],
        "brim_width_mm": float(settings["brim_width"]),
        "support_material": settings["support_material"] == "1",
        "support_material_auto": settings.get("support_material_auto") == "1",
        "support_material_style": settings["support_material_style"],
        "support_material_threshold_deg": float(settings["support_material_threshold"]),
        "first_layer_line_width_mm": FIRST_LAYER_LINE_WIDTH_MM,
        "first_layer_centerline_bounds_mm": [
            min(centerline_x), min(centerline_y), max(centerline_x), max(centerline_y)
        ],
        "first_layer_extrusion_bounds_mm": [*minimum, *maximum],
        "first_layer_extrusion_margins_mm": margins,
        "minimum_required_first_layer_margin_mm": MINIMUM_FIRST_LAYER_MARGIN_MM,
        "first_layer_margin_pass": True,
        "first_layer_segment_counts_by_type": {
            path_type: len(type_segments)
            for path_type, type_segments in sorted(segments.items())
        },
        "brim_segment_count": len(segments["Skirt/Brim"]),
        "support_segment_count": support_segment_count,
        "m555_probe_footprint": m555,
        **metadata,
    }
    return result, segments


def write_svg(
    path: Path,
    slice_result: dict,
    segments: dict[str, list[tuple[float, float, float, float]]],
) -> None:
    colors = {
        "Skirt/Brim": "#f59e0b",
        "Support material": "#38bdf8",
        "Support material interface": "#2563eb",
        "External perimeter": "#f8fafc",
        "Perimeter": "#cbd5e1",
        "Solid infill": "#94a3b8",
        "Internal infill": "#64748b",
        "Unclassified": "#a78bfa",
    }
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1008" viewBox="0 0 250 210">',
        '<rect width="250" height="210" fill="#111827"/>',
        '<rect x="0.5" y="0.5" width="249" height="209" fill="none" stroke="#f8fafc" stroke-width="0.5"/>',
        '<rect x="10" y="10" width="230" height="190" fill="none" stroke="#ef4444" stroke-width="0.35" stroke-dasharray="2 1"/>',
        '<g transform="translate(0 210) scale(1 -1)" fill="none" stroke-linecap="round" stroke-linejoin="round">',
    ]
    for path_type, type_segments in sorted(segments.items()):
        if not type_segments:
            continue
        color = colors.get(path_type, "#a3e635")
        path_commands = " ".join(
            f"M{x0:.3f},{y0:.3f} L{x1:.3f},{y1:.3f}"
            for x0, y0, x1, y1 in type_segments
        )
        lines.append(
            f'<path d="{path_commands}" stroke="{color}" stroke-width="0.5" opacity="0.92"/>'
        )
    lines.extend(
        [
            "</g>",
            '<g font-family="DejaVu Sans, sans-serif">',
            '<rect x="4" y="4" width="115" height="27" rx="1.5" fill="#020617" opacity="0.9"/>',
            '<text x="7" y="10" font-size="4" fill="#f8fafc">RIGHT UPPER — FIRST LAYER</text>',
            '<text x="7" y="16" font-size="3.3" fill="#f59e0b">orange: 10 mm outer brim</text>',
            '<text x="7" y="21" font-size="3.3" fill="#38bdf8">blue: snug supports</text>',
            '<text x="7" y="26" font-size="3.3" fill="#ef4444">red dashed: 10 mm bed inset</text>',
            '<rect x="126" y="4" width="120" height="27" rx="1.5" fill="#020617" opacity="0.9"/>',
        ]
    )
    margins = slice_result["first_layer_extrusion_margins_mm"]
    lines.extend(
        [
            f'<text x="129" y="10" font-size="3.5" fill="#f8fafc">Margins L/R: {margins["left"]:.2f} / {margins["right"]:.2f} mm</text>',
            f'<text x="129" y="16" font-size="3.5" fill="#f8fafc">Margins F/R: {margins["front"]:.2f} / {margins["rear"]:.2f} mm</text>',
            f'<text x="129" y="22" font-size="3.5" fill="#f8fafc">Brim: {slice_result["brim_width_mm"]:.0f} mm outer only</text>',
            f'<text x="129" y="27" font-size="3.5" fill="#f8fafc">PASS: ≥ {MINIMUM_FIRST_LAYER_MARGIN_MM:.0f} mm bed margin</text>',
            "</g>",
            "</svg>",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--source-project", type=Path, required=True)
    parser.add_argument("--source-stl", type=Path, required=True)
    parser.add_argument("--review-project", type=Path, required=True)
    parser.add_argument("--gcode", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--evidence-svg", type=Path, required=True)
    args = parser.parse_args()

    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    source_project_hash = sha256(args.source_project)
    source_stl_hash = sha256(args.source_stl)
    if source_project_hash != contract["source_project_sha256"]:
        raise RuntimeError("Source project hash does not match the approved contract")
    if source_stl_hash != contract["source_stl_sha256"]:
        raise RuntimeError("Source STL hash does not match the approved contract")

    archive_result = archive_validation(args.source_project, args.review_project, contract)
    slice_result, segments = gcode_validation(args.gcode)
    write_svg(args.evidence_svg, slice_result, segments)

    report_status = "PASS_LAYOUT__HOLD_SOURCE_MESH_AND_PHYSICAL_FIRST_LAYER"
    report = {
        "schema_version": 1,
        "status": report_status,
        "approved_scope": contract["scope"],
        "approval": contract["approval"],
        "source_project": str(args.source_project),
        "source_project_sha256": source_project_hash,
        "source_stl": str(args.source_stl),
        "source_stl_sha256": source_stl_hash,
        "review_project": str(args.review_project),
        "review_project_sha256": sha256(args.review_project),
        "gcode": str(args.gcode),
        "gcode_sha256": sha256(args.gcode),
        "gcode_size_bytes": args.gcode.stat().st_size,
        "evidence_svg": str(args.evidence_svg),
        "geometry_and_archive_preservation": archive_result,
        "slice": slice_result,
        "preexisting_source_mesh_slicer_info": contract["frozen"]["prusa_slicer_info"],
        "release_gates": {
            "source_hashes_match": "PASS",
            "mesh_geometry_and_topology_unchanged": "PASS",
            "scale_1": "PASS",
            "only_approved_3mf_members_changed": "PASS",
            "approved_transform_exact": "PASS",
            "outer_only_brim_10mm": "PASS",
            "automatic_snug_supports_retained": "PASS",
            "diagnostic_slice_completes": "PASS",
            "actual_first_layer_minimum_5mm_bed_margin": "PASS",
            "preexisting_non_manifold_source_mesh": "HOLD",
            "physical_first_layer_observation": "REQUIRED",
            "gcode_release_approved": False,
            "overall": report_status,
        },
        "next_action": (
            "Open the review 3MF in PrusaSlicer and inspect the first-layer brim/support preview. "
            "Before committing to the full ASA print, stop after the first layer and verify that "
            "every brim and support island is fully bonded with no lifted edge."
        ),
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": report_status,
        "review_project_sha256": report["review_project_sha256"],
        "gcode_sha256": report["gcode_sha256"],
        "first_layer_margins_mm": slice_result["first_layer_extrusion_margins_mm"],
        "estimated_print_time": slice_result.get("estimated_print_time"),
        "filament_mass_g": slice_result.get("filament_mass_g"),
    }, indent=2))


if __name__ == "__main__":
    main()
