#!/usr/bin/env python3
"""Re-evaluate Gate 9 slices while excluding MK4 startup custom extrusion."""

from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import slice_gate9_architecture_comparison as comparison  # noqa: E402


original_parse_gcode_metrics = comparison.parse_gcode_metrics
original_slice_orientation = comparison.slice_orientation


def parse_gcode_without_custom_startup(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    custom_role = False
    filtered: list[str] = []
    for line in lines:
        if line.startswith(";TYPE:"):
            custom_role = (
                line.split(":", 1)[1].strip().lower() == "custom"
            )
            filtered.append(line)
            continue
        if custom_role and (
            line.startswith("G0 ")
            or line.startswith("G1 ")
            or line.startswith("G2 ")
            or line.startswith("G3 ")
        ):
            continue
        filtered.append(line)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".gcode",
        prefix="gate9-no-custom-",
        encoding="utf-8",
        delete=False,
    ) as temporary:
        temporary.write("\n".join(filtered) + "\n")
        temporary_path = Path(temporary.name)
    try:
        metrics = original_parse_gcode_metrics(temporary_path)
    finally:
        temporary_path.unlink(missing_ok=True)
    metrics["margin_parser_revision"] = (
        "V2 excludes Prusa MK4 startup Custom/purge extrusion"
    )
    metrics["extrusion_roles"].pop("Custom", None)
    role_total = sum(metrics["extrusion_roles"].values())
    support_total = sum(
        value
        for role, value in metrics["extrusion_roles"].items()
        if "support" in role.lower()
    )
    brim_total = sum(
        value
        for role, value in metrics["extrusion_roles"].items()
        if "brim" in role.lower() or "skirt" in role.lower()
    )
    support_ratio = support_total / role_total if role_total else 0.0
    brim_ratio = brim_total / role_total if role_total else 0.0
    metrics["support_extrusion_ratio"] = round(support_ratio, 6)
    if metrics["filament_g"] is not None:
        metrics["support_filament_g"] = round(
            metrics["filament_g"] * support_ratio, 3
        )
        metrics["brim_filament_g"] = round(
            metrics["filament_g"] * brim_ratio, 3
        )
    if metrics["filament_cm3"] is not None:
        metrics["support_volume_cm3"] = round(
            metrics["filament_cm3"] * support_ratio, 3
        )
    return metrics


def cached_slice_orientation(
    source_stl: Path,
    orientation: comparison.Orientation,
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
    if not gcode_path.exists():
        return original_slice_orientation(
            source_stl,
            orientation,
            target_dir,
            config_path,
            threads,
            candidate_index,
        )
    exact_dimensions = orientation.dimensions_mm
    return {
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
        "slicer_elapsed_seconds": 0.0,
        "slicer_returncode": 0,
        "slicer_stdout_tail": "reused existing Gate 9 review G-code",
        "slicer_stderr_tail": "",
        "oriented_stl": (
            str(oriented_path.relative_to(comparison.REPO_ROOT))
            if oriented_path.exists()
            else None
        ),
        "gcode": str(gcode_path.relative_to(comparison.REPO_ROOT)),
        "metrics": parse_gcode_without_custom_startup(gcode_path),
    }


comparison.parse_gcode_metrics = parse_gcode_without_custom_startup
comparison.slice_orientation = cached_slice_orientation


if __name__ == "__main__":
    comparison.main()
