#!/usr/bin/env python3
"""Slice both actual V3 cut lower faces on the MK4S ASA review envelope.

This is a fit and support review, not a production print release. It searches
3D orientations for each actual left/right V3 STL and enforces the verified
post-brim and post-support XY safety margin.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import subprocess
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import orient_binary_stl_for_print as orient_stl


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_COMPARISON_DIR = (
    PACKAGE_ROOT / "output/rear-cassette-lower-face-cut-review-v3"
)
DEFAULT_BASELINE_3MF = (
    PACKAGE_ROOT
    / "output/gate8-full-size-structural-iteration/Printing"
    / "left_lower_face_MK4S_one_piece_V1_5.3mf"
)
DEFAULT_OUTPUT = DEFAULT_COMPARISON_DIR / "slicer-review"
BED_MM = (250.0, 210.0, 220.0)
REQUIRED_XY_MARGIN_MM = 10.0
BRIM_WIDTH_MM = 5.0
MODEL_SEARCH_ENVELOPE_MM = (
    BED_MM[0] - 2.0 * (REQUIRED_XY_MARGIN_MM + BRIM_WIDTH_MM),
    BED_MM[1] - 2.0 * (REQUIRED_XY_MARGIN_MM + BRIM_WIDTH_MM),
    BED_MM[2],
)
STL_HEADER_BYTES = 80
STL_TRIANGLE_BYTES = 50


@dataclass(frozen=True)
class Orientation:
    rotation_xyz_degrees: tuple[float, float, float]
    dimensions_mm: tuple[float, float, float]
    envelope_score: float


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--comparison-dir",
        type=Path,
        default=DEFAULT_COMPARISON_DIR,
    )
    parser.add_argument(
        "--baseline-3mf",
        type=Path,
        default=DEFAULT_BASELINE_3MF,
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--threads", type=int, default=8)
    return parser.parse_args()


def read_binary_stl_points(
    path: Path,
) -> list[tuple[float, float, float]]:
    data = path.read_bytes()
    if len(data) < STL_HEADER_BYTES + 4:
        raise ValueError(f"{path} is too short to be a binary STL")
    triangle_count = struct.unpack_from("<I", data, STL_HEADER_BYTES)[0]
    expected_size = (
        STL_HEADER_BYTES + 4 + triangle_count * STL_TRIANGLE_BYTES
    )
    if len(data) != expected_size:
        raise ValueError(
            f"{path} is not a supported binary STL: "
            f"expected {expected_size} bytes, found {len(data)}"
        )
    points: set[tuple[float, float, float]] = set()
    offset = STL_HEADER_BYTES + 4
    for _ in range(triangle_count):
        values = struct.unpack_from("<12fH", data, offset)
        for index in (3, 6, 9):
            points.add(
                (
                    float(values[index]),
                    float(values[index + 1]),
                    float(values[index + 2]),
                )
            )
        offset += STL_TRIANGLE_BYTES
    return sorted(points)


def rotate_point(
    point: tuple[float, float, float],
    degrees: tuple[float, float, float],
) -> tuple[float, float, float]:
    x, y, z = point
    ax, ay, az = (math.radians(value) for value in degrees)
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)
    y, z = y * cx - z * sx, y * sx + z * cx
    x, z = x * cy + z * sy, -x * sy + z * cy
    x, y = x * cz - y * sz, x * sz + y * cz
    return x, y, z


def rotated_dimensions(
    points: list[tuple[float, float, float]],
    degrees: tuple[float, float, float],
) -> tuple[float, float, float]:
    minimum = [math.inf, math.inf, math.inf]
    maximum = [-math.inf, -math.inf, -math.inf]
    for point in points:
        rotated = rotate_point(point, degrees)
        for axis in range(3):
            minimum[axis] = min(minimum[axis], rotated[axis])
            maximum[axis] = max(maximum[axis], rotated[axis])
    return tuple(maximum[axis] - minimum[axis] for axis in range(3))


def orientation_score(dimensions_mm: tuple[float, float, float]) -> float:
    return max(
        dimensions_mm[index] / MODEL_SEARCH_ENVELOPE_MM[index]
        for index in range(3)
    )


def circular_angle_distance(first: float, second: float) -> float:
    difference = abs(first - second) % 180.0
    return min(difference, 180.0 - difference)


def orientation_distance(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
) -> float:
    return math.sqrt(
        sum(
            circular_angle_distance(first[index], second[index]) ** 2
            for index in range(3)
        )
    )


def best_distinct(
    candidates: Iterable[Orientation],
    count: int,
    minimum_angle_distance: float,
) -> list[Orientation]:
    selected: list[Orientation] = []
    for candidate in sorted(candidates, key=lambda item: item.envelope_score):
        if all(
            orientation_distance(
                candidate.rotation_xyz_degrees,
                existing.rotation_xyz_degrees,
            )
            >= minimum_angle_distance
            for existing in selected
        ):
            selected.append(candidate)
            if len(selected) >= count:
                break
    return selected


def search_orientations(
    points: list[tuple[float, float, float]],
    requested_count: int,
) -> list[Orientation]:
    coarse: list[Orientation] = []
    for ax in range(0, 180, 10):
        for ay in range(0, 180, 10):
            for az in range(0, 180, 10):
                rotation = (float(ax), float(ay), float(az))
                dimensions = rotated_dimensions(points, rotation)
                coarse.append(
                    Orientation(
                        rotation,
                        dimensions,
                        orientation_score(dimensions),
                    )
                )
    seeds = best_distinct(coarse, 8, 18.0)
    refined: list[Orientation] = []
    for seed in seeds:
        for dx in range(-10, 11, 2):
            for dy in range(-10, 11, 2):
                for dz in range(-10, 11, 2):
                    rotation = tuple(
                        (
                            seed.rotation_xyz_degrees[index] + delta
                        )
                        % 180.0
                        for index, delta in enumerate((dx, dy, dz))
                    )
                    dimensions = rotated_dimensions(points, rotation)
                    refined.append(
                        Orientation(
                            rotation,
                            dimensions,
                            orientation_score(dimensions),
                        )
                    )
    return best_distinct(
        refined,
        requested_count,
        minimum_angle_distance=12.0,
    )


def extract_prusa_config(
    baseline_3mf: Path,
    output_path: Path,
) -> dict[str, str]:
    with zipfile.ZipFile(baseline_3mf) as archive:
        text = archive.read("Metadata/Slic3r_PE.config").decode("utf-8")
    settings: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^;\s+([A-Za-z0-9_]+)\s+=\s?(.*)$", line)
        if match:
            settings[match.group(1)] = match.group(2)
    settings.update(
        {
            "bed_shape": "0x0,250x0,250x210,0x210",
            "max_print_height": "220",
            "layer_height": "0.2",
            "first_layer_height": "0.2",
            "perimeters": "3",
            "fill_density": "15%",
            "support_material": "1",
            "support_material_auto": "1",
            "support_material_buildplate_only": "0",
            "support_material_style": "snug",
            "support_material_threshold": "45",
            "brim_width": f"{BRIM_WIDTH_MM:g}",
            "brim_separation": "0",
            "brim_type": "outer_only",
            "skirts": "0",
            "draft_shield": "disabled",
            "gcode_comments": "1",
            "binary_gcode": "0",
            "filament_type": "ASA",
            "filament_density": "1.07",
            "filament_cost": "30",
            "filament_settings_id": '"Generic ASA architecture review"',
            "filament_max_volumetric_speed": "11",
            "temperature": "260",
            "first_layer_temperature": "260",
            "bed_temperature": "105",
            "first_layer_bed_temperature": "105",
            "fan_always_on": "0",
            "disable_fan_first_layers": "3",
            "min_fan_speed": "0",
            "max_fan_speed": "20",
            "output_filename_format": "{input_filename_base}.gcode",
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "\n".join(
            f"{key} = {value}" for key, value in sorted(settings.items())
        )
        + "\n",
        encoding="utf-8",
    )
    return settings


def parse_duration_seconds(value: str) -> int | None:
    total = 0
    matched = False
    for number, unit in re.findall(r"(\d+)\s*([dhms])", value):
        matched = True
        multiplier = {
            "d": 86400,
            "h": 3600,
            "m": 60,
            "s": 1,
        }[unit]
        total += int(number) * multiplier
    return total if matched else None


def parse_gcode_metrics(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    filament_g = None
    filament_cm3 = None
    print_time_text = None
    for line in text.splitlines():
        if line.startswith("; filament used [g] ="):
            filament_g = float(line.split("=", 1)[1].strip())
        elif line.startswith("; filament used [cm3] ="):
            filament_cm3 = float(line.split("=", 1)[1].strip())
        elif line.startswith(
            "; estimated printing time (normal mode) ="
        ):
            print_time_text = line.split("=", 1)[1].strip()

    current_x = 0.0
    current_y = 0.0
    current_z = 0.0
    current_e = 0.0
    relative_e = True
    active_role: str | None = None
    extents = {
        "min_x": math.inf,
        "max_x": -math.inf,
        "min_y": math.inf,
        "max_y": -math.inf,
        "min_z": math.inf,
        "max_z": -math.inf,
    }
    extrusion_by_role: dict[str, float] = {}
    command_pattern = re.compile(
        r"([XYZE])(-?(?:\d+(?:\.\d*)?|\.\d+))"
    )
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith(";TYPE:"):
            active_role = line.split(":", 1)[1].strip()
            continue
        if line == "M82":
            relative_e = False
            continue
        if line == "M83":
            relative_e = True
            continue
        if line.startswith("G92"):
            values = {
                letter: float(value)
                for letter, value in command_pattern.findall(line)
            }
            if "E" in values:
                current_e = values["E"]
            continue
        if not (line.startswith("G0 ") or line.startswith("G1 ")):
            continue
        code = line.split(";", 1)[0]
        values = {
            letter: float(value)
            for letter, value in command_pattern.findall(code)
        }
        next_x = values.get("X", current_x)
        next_y = values.get("Y", current_y)
        next_z = values.get("Z", current_z)
        extrusion_delta = 0.0
        if "E" in values:
            if relative_e:
                extrusion_delta = values["E"]
                current_e += values["E"]
            else:
                extrusion_delta = values["E"] - current_e
                current_e = values["E"]
        if (
            extrusion_delta > 0.0
            and active_role is not None
            and active_role.lower() != "custom"
        ):
            extents["min_x"] = min(
                extents["min_x"], current_x, next_x
            )
            extents["max_x"] = max(
                extents["max_x"], current_x, next_x
            )
            extents["min_y"] = min(
                extents["min_y"], current_y, next_y
            )
            extents["max_y"] = max(
                extents["max_y"], current_y, next_y
            )
            extents["min_z"] = min(
                extents["min_z"], current_z, next_z
            )
            extents["max_z"] = max(
                extents["max_z"], current_z, next_z
            )
            extrusion_by_role[active_role] = (
                extrusion_by_role.get(active_role, 0.0)
                + extrusion_delta
            )
        current_x, current_y, current_z = next_x, next_y, next_z

    if not math.isfinite(extents["min_x"]):
        raise ValueError(f"No role-tagged extrusion found in {path}")
    rounded_extents = {
        key: round(value, 3) for key, value in extents.items()
    }
    margins = {
        "left": extents["min_x"],
        "right": BED_MM[0] - extents["max_x"],
        "front": extents["min_y"],
        "rear": BED_MM[1] - extents["max_y"],
    }
    total_role_e = sum(extrusion_by_role.values())
    support_e = sum(
        value
        for role, value in extrusion_by_role.items()
        if "support" in role.lower()
    )
    brim_e = sum(
        value
        for role, value in extrusion_by_role.items()
        if "brim" in role.lower() or "skirt" in role.lower()
    )
    support_ratio = (
        support_e / total_role_e if total_role_e > 0.0 else 0.0
    )
    brim_ratio = brim_e / total_role_e if total_role_e > 0.0 else 0.0
    passes_margin = (
        min(margins.values()) >= REQUIRED_XY_MARGIN_MM - 1e-6
        and extents["max_z"] <= BED_MM[2] + 1e-6
    )
    return {
        "margin_parser_revision": "V3 excludes MK4 startup Custom/purge extrusion",
        "toolpath_extents_mm": rounded_extents,
        "xy_margins_after_brim_and_support_mm": {
            key: round(value, 3) for key, value in margins.items()
        },
        "minimum_xy_margin_mm": round(min(margins.values()), 3),
        "required_xy_margin_mm": REQUIRED_XY_MARGIN_MM,
        "passes_xy_margin_and_z_height": passes_margin,
        "filament_g": filament_g,
        "filament_cm3": filament_cm3,
        "estimated_print_time": print_time_text,
        "estimated_print_time_seconds": (
            parse_duration_seconds(print_time_text)
            if print_time_text
            else None
        ),
        "support_extrusion_ratio": round(support_ratio, 6),
        "support_filament_g": (
            round(filament_g * support_ratio, 3)
            if filament_g is not None
            else None
        ),
        "support_volume_cm3": (
            round(filament_cm3 * support_ratio, 3)
            if filament_cm3 is not None
            else None
        ),
        "brim_filament_g": (
            round(filament_g * brim_ratio, 3)
            if filament_g is not None
            else None
        ),
        "extrusion_roles": {
            role: round(value, 3)
            for role, value in sorted(extrusion_by_role.items())
        },
    }


def slice_orientation(
    source_stl: Path,
    orientation: Orientation,
    target_dir: Path,
    config_path: Path,
    threads: int,
    candidate_index: int,
) -> dict[str, Any]:
    rotation = orientation.rotation_xyz_degrees
    label = (
        f"orientation_{candidate_index:02d}_"
        f"x{rotation[0]:05.1f}_y{rotation[1]:05.1f}_z{rotation[2]:05.1f}"
        .replace(".", "p")
    )
    oriented_path = target_dir / f"{label}.stl"
    gcode_path = target_dir / f"{label}.gcode"
    target_dir.mkdir(parents=True, exist_ok=True)
    exact_dimensions = orient_stl.transform_stl(
        source_stl,
        oriented_path,
        rotation,
        "xyz",
    )
    command = [
        "prusa-slicer",
        "--load",
        str(config_path),
        "--export-gcode",
        "--dont-arrange",
        "--center",
        f"{BED_MM[0] / 2.0:g},{BED_MM[1] / 2.0:g}",
        "--threads",
        str(threads),
        "--output",
        str(gcode_path),
        str(oriented_path),
    ]
    started = time.monotonic()
    process = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.monotonic() - started
    result: dict[str, Any] = {
        "candidate_index": candidate_index,
        "rotation_xyz_degrees": [
            round(value, 3) for value in rotation
        ],
        "search_dimensions_mm": [
            round(value, 3) for value in orientation.dimensions_mm
        ],
        "oriented_stl_dimensions_mm": [
            round(value, 3) for value in exact_dimensions
        ],
        "model_envelope_score_before_support": round(
            orientation.envelope_score, 6
        ),
        "slicer_elapsed_seconds": round(elapsed, 3),
        "slicer_returncode": process.returncode,
        "slicer_stdout_tail": process.stdout[-1000:],
        "slicer_stderr_tail": process.stderr[-1000:],
        "oriented_stl": str(oriented_path.relative_to(REPO_ROOT)),
        "gcode": (
            str(gcode_path.relative_to(REPO_ROOT))
            if gcode_path.exists()
            else None
        ),
    }
    if process.returncode == 0 and gcode_path.exists():
        result["metrics"] = parse_gcode_metrics(gcode_path)
    else:
        result["metrics"] = None
    return result


def choose_best_slice(
    candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    successful = [
        candidate
        for candidate in candidates
        if candidate.get("metrics") is not None
    ]
    if not successful:
        return None
    passing = [
        candidate
        for candidate in successful
        if candidate["metrics"]["passes_xy_margin_and_z_height"]
    ]
    pool = passing if passing else successful
    return min(
        pool,
        key=lambda candidate: (
            candidate["metrics"]["support_filament_g"]
            if candidate["metrics"]["support_filament_g"] is not None
            else math.inf,
            candidate["metrics"]["estimated_print_time_seconds"]
            if candidate["metrics"]["estimated_print_time_seconds"]
            is not None
            else math.inf,
            -candidate["metrics"]["minimum_xy_margin_mm"],
        ),
    )


def slice_part(
    architecture: str,
    part: str,
    stl_path: Path,
    orientation_count: int,
    output_dir: Path,
    config_path: Path,
    threads: int,
) -> dict[str, Any]:
    print(
        f"[slice] {architecture}/{part}: searching orientations",
        flush=True,
    )
    points = read_binary_stl_points(stl_path)
    orientations = search_orientations(points, orientation_count)
    candidates = []
    for index, orientation in enumerate(orientations, start=1):
        print(
            f"[slice] {architecture}/{part}: "
            f"candidate {index}/{len(orientations)} "
            f"{orientation.rotation_xyz_degrees} "
            f"score={orientation.envelope_score:.4f}",
            flush=True,
        )
        candidates.append(
            slice_orientation(
                stl_path,
                orientation,
                output_dir / architecture / part,
                config_path,
                threads,
                index,
            )
        )
    selected = choose_best_slice(candidates)
    return {
        "source_stl": str(stl_path.relative_to(REPO_ROOT)),
        "orientation_search_envelope_mm": list(
            MODEL_SEARCH_ENVELOPE_MM
        ),
        "orientation_candidates": candidates,
        "selected_candidate_index": (
            selected["candidate_index"] if selected else None
        ),
        "selected": selected,
        "has_margin_passing_candidate": any(
            candidate.get("metrics", {}).get(
                "passes_xy_margin_and_z_height", False
            )
            if candidate.get("metrics")
            else False
            for candidate in candidates
        ),
    }


def selected_metrics(part_report: dict[str, Any]) -> dict[str, Any] | None:
    selected = part_report.get("selected")
    return selected.get("metrics") if selected else None


def main() -> None:
    args = parse_args()
    comparison_dir = args.comparison_dir.resolve()
    output_dir = args.output_dir.resolve()
    baseline_3mf = args.baseline_3mf.resolve()
    config_path = output_dir / "v3-mk4s-asa-review.ini"
    settings = extract_prusa_config(baseline_3mf, config_path)

    stl_dir = comparison_dir / "review-stl-not-production"
    parts: dict[str, dict[str, Any]] = {}
    for part in ("left_lower_face", "right_lower_face"):
        source_stl = stl_dir / f"{part}_cut_review_v3.stl"
        if not source_stl.exists():
            raise FileNotFoundError(f"Missing actual V3 review STL: {source_stl}")
        parts[part] = slice_part(
            "v3_actual_cut",
            part,
            source_stl,
            3,
            output_dir,
            config_path,
            args.threads,
        )

    selected_metrics_by_part = {
        part: selected_metrics(part_report)
        for part, part_report in parts.items()
    }
    all_parts_sliced = all(
        metrics is not None for metrics in selected_metrics_by_part.values()
    )
    all_parts_pass_margin = all_parts_sliced and all(
        bool(metrics["passes_xy_margin_and_z_height"])
        for metrics in selected_metrics_by_part.values()
        if metrics is not None
    )
    report = {
        "status": "review_only_not_a_production_print_release",
        "scope": "actual V3 cut left and right Gate 8 lower-face meshes",
        "machine_baseline_3mf": str(baseline_3mf.relative_to(REPO_ROOT)),
        "generated_config": str(config_path.relative_to(REPO_ROOT)),
        "key_slicer_settings": {
            key: settings[key]
            for key in (
                "bed_shape",
                "max_print_height",
                "layer_height",
                "perimeters",
                "fill_density",
                "support_material",
                "support_material_auto",
                "support_material_style",
                "brim_width",
                "filament_type",
                "filament_density",
                "temperature",
                "bed_temperature",
            )
        },
        "bed_mm": list(BED_MM),
        "required_xy_margin_after_brim_and_support_mm": (
            REQUIRED_XY_MARGIN_MM
        ),
        "brim_width_mm": BRIM_WIDTH_MM,
        "orientation_model_search_envelope_mm": list(
            MODEL_SEARCH_ENVELOPE_MM
        ),
        "parts": parts,
        "acceptance": {
            "both_actual_parts_sliced": all_parts_sliced,
            "both_actual_parts_have_margin_passing_orientation": (
                all_parts_pass_margin
            ),
            "minimum_selected_xy_margin_mm": (
                min(
                    float(metrics["minimum_xy_margin_mm"])
                    for metrics in selected_metrics_by_part.values()
                    if metrics is not None
                )
                if all_parts_sliced
                else None
            ),
        },
        "limitations": [
            "These are actual V3 cut review meshes, but the cassette connection and aluminum reconciliation are still deferred.",
            "G-code is review-only and must not be treated as a production print release.",
            "The selected orientation is the best of three geometry-searched candidates per side, not a proof of the global support minimum.",
            "Support mass is estimated from role-tagged relative extrusion in PrusaSlicer G-code.",
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = (
        output_dir
        / "rear-cassette-lower-face-cut-review-v3-slicer.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "acceptance": report["acceptance"],
                "selected": {
                    part: part_report.get("selected")
                    for part, part_report in parts.items()
                },
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
