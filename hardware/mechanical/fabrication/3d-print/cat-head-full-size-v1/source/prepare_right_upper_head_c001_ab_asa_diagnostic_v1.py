#!/usr/bin/env python3
"""Create an ASA diagnostic 3MF without changing the saved model or transform."""

from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import zipfile


SOURCE_SHA256 = "0941d65a81594754d33382a584ad2963ed2c14f6034a1a8534d724d9cca8c8a6"
CONFIG_MEMBER = "Metadata/Slic3r_PE.config"

OVERRIDES = {
    "bed_temperature": "110",
    "bridge_fan_speed": "30",
    "brim_separation": "0.1",
    "brim_type": "outer_only",
    "brim_width": "8",
    "cooling": "1",
    "default_filament_profile": '"Prusament ASA @MK4"',
    "disable_fan_first_layers": "4",
    "fan_always_on": "1",
    "filament_cost": "42.69",
    "filament_density": "1.07",
    "filament_max_volumetric_speed": "12",
    "filament_settings_id": '"Prusament ASA @MK4"',
    "filament_type": "ASA",
    "first_layer_bed_temperature": "105",
    "first_layer_temperature": "260",
    "max_fan_speed": "10",
    "min_fan_speed": "10",
    "support_material": "1",
    "support_material_auto": "1",
    "support_material_style": "snug",
    "support_material_threshold": "45",
    "temperature": "260",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def replace_config(source: str) -> str:
    found: dict[str, int] = {key: 0 for key in OVERRIDES}
    output: list[str] = []
    for line in source.splitlines(keepends=True):
        replaced = False
        for key, value in OVERRIDES.items():
            prefix = f"; {key} = "
            if line.startswith(prefix):
                ending = "\n" if line.endswith("\n") else ""
                output.append(f"{prefix}{value}{ending}")
                found[key] += 1
                replaced = True
                break
        if not replaced:
            output.append(line)
    invalid = {key: count for key, count in found.items() if count != 1}
    if invalid:
        raise RuntimeError(f"Expected exactly one embedded setting per key: {invalid}")
    return "".join(output)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    actual_hash = sha256(args.source)
    if actual_hash != SOURCE_SHA256:
        raise RuntimeError(
            f"Frozen source hash mismatch: expected {SOURCE_SHA256}, got {actual_hash}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    with zipfile.ZipFile(args.source, "r") as source_zip:
        names = source_zip.namelist()
        if CONFIG_MEMBER not in names:
            raise RuntimeError(f"Missing {CONFIG_MEMBER}")
        updated_config = replace_config(
            source_zip.read(CONFIG_MEMBER).decode("utf-8")
        ).encode("utf-8")
        with zipfile.ZipFile(temporary, "w") as output_zip:
            for info in source_zip.infolist():
                payload = (
                    updated_config
                    if info.filename == CONFIG_MEMBER
                    else source_zip.read(info.filename)
                )
                output_zip.writestr(info, payload)
    os.replace(temporary, args.output)
    print(f"source_sha256={actual_hash}")
    print(f"output_sha256={sha256(args.output)}")


if __name__ == "__main__":
    main()
