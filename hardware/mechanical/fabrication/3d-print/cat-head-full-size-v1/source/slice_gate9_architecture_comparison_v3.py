#!/usr/bin/env python3
"""Re-evaluate Gate 9 margins while preserving MK4 purge positioning."""

from __future__ import annotations

import re
import sys
import tempfile
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import slice_gate9_architecture_comparison as comparison  # noqa: E402
import slice_gate9_architecture_comparison_v2 as cached_review  # noqa: E402


original_parse_gcode_metrics = (
    cached_review.original_parse_gcode_metrics
)


def parse_gcode_with_custom_travel_only(path: Path) -> dict[str, Any]:
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
            code, separator, comment = line.partition(";")
            code = re.sub(
                r"(?<![A-Za-z])E-?(?:\d+(?:\.\d*)?|\.\d+)",
                "",
                code,
            )
            line = code.rstrip()
            if separator:
                line += f" ;{comment}"
        filtered.append(line)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".gcode",
        prefix="gate9-custom-travel-only-",
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
        "V3 preserves Custom XY travel while stripping startup purge E"
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


cached_review.parse_gcode_without_custom_startup = (
    parse_gcode_with_custom_travel_only
)
comparison.parse_gcode_metrics = parse_gcode_with_custom_travel_only
comparison.slice_orientation = cached_review.cached_slice_orientation


if __name__ == "__main__":
    comparison.main()
