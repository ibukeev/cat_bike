#!/usr/bin/env python3
"""Pure packaging-contract preflight; never opens CAD or writes artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import sys
from pathlib import Path
from typing import Any


SCHEMA = "cat-head-right-eye-print-packaging-tooling-v1"
PART_IDS = ("front_carrier", "translucent_eye_glass")
PROFILE_REQUIRED_KEYS = {
    "printer_technology", "nozzle_diameter", "filament_diameter",
    "filament_type", "layer_height", "first_layer_height",
    "perimeters", "top_solid_layers",
    "bottom_solid_layers", "fill_density", "fill_pattern",
    "support_material", "brim_width", "temperature",
    "first_layer_temperature", "bed_temperature",
    "first_layer_bed_temperature", "ironing",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_root(path: Path) -> Path:
    for candidate in (path.resolve(), *path.resolve().parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError(f"repository root not found from {path}")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected a JSON object: {path}")
    return value


def parse_profile(path: Path) -> tuple[dict[str, str], list[str]]:
    values: dict[str, str] = {}
    errors: list[str] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if "=" not in line:
            errors.append(f"{path.name}:{number}: expected key = value")
            continue
        key, value = (item.strip() for item in line.split("=", 1))
        if not key or not value:
            errors.append(f"{path.name}:{number}: empty key or value")
        elif key in values:
            errors.append(f"{path.name}:{number}: duplicate key {key}")
        else:
            values[key] = value
    missing = sorted(PROFILE_REQUIRED_KEYS - values.keys())
    if missing:
        errors.append(f"{path.name}: missing required keys {missing}")
    return values, errors


def safe_repo_path(root: Path, value: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(value, str) or not value or Path(value).is_absolute():
        errors.append(f"{label}: required non-empty repository-relative path")
        return None
    path = (root / value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label}: path escapes repository")
        return None
    return path


def normalized(vector: Any) -> bool:
    return (
        isinstance(vector, list)
        and len(vector) == 3
        and all(isinstance(value, (int, float)) for value in vector)
        and abs(math.sqrt(sum(float(value) ** 2 for value in vector)) - 1.0) <= 1.0e-6
    )


def contract_errors(contract: dict[str, Any], contract_path: Path) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_version") != SCHEMA:
        errors.append("schema_version mismatch")
    if contract.get("authority") != "TOOLING_ONLY__NO_EXPORT_NO_SLICE_NO_PRINT_RELEASE":
        errors.append("authority must remain tooling-only")

    source = contract.get("source_release", {})
    parts = source.get("parts", [])
    if [item.get("id") for item in parts] != list(PART_IDS):
        errors.append("part order/identity must be exactly front carrier and eye lens")
    stl_names = [item.get("stl_name") for item in parts]
    project_names = [item.get("project_name") for item in parts]
    for label, names, suffix in (
        ("STL", stl_names, ".stl"), ("3MF", project_names, ".3mf")
    ):
        if len(names) != len(set(names)):
            errors.append(f"{label} names must be unique")
        for name in names:
            if not isinstance(name, str) or Path(name).name != name or not name.endswith(suffix):
                errors.append(f"invalid {label} name: {name!r}")
            elif name != name.upper().replace(suffix.upper(), suffix):
                errors.append(f"{label} stem must be uppercase: {name}")

    geometry = contract.get("geometry_gates", {})
    if int(geometry.get("required_solid_count_each", 0)) != 1:
        errors.append("each part must require exactly one solid")
    if float(geometry.get("minimum_wall_mm", 0.0)) < 0.7:
        errors.append("minimum wall cannot be below 0.7 mm")
    if float(geometry.get("eye_glass_thickness_mm", 0.0)) != 0.9:
        errors.append("eye-lens thickness target must remain exactly 0.90 mm")
    if float(geometry.get("eye_glass_thickness_measurement_tolerance_mm", 0.0)) != 0.01:
        errors.append("eye-lens measurement tolerance must remain 0.01 mm")
    for obsolete in (
        "preserved_m2_5_bore_diameter_mm",
        "bore_measurement_tolerance_mm",
        "require_preserved_mount_bore_centers_axes_and_seats",
    ):
        if obsolete in geometry:
            errors.append(f"obsolete mount-hardware gate must be absent: {obsolete}")

    mesh = contract.get("mesh_gates", {})
    if int(mesh.get("required_connected_components_each", 0)) != 1:
        errors.append("mesh must require one connected component")
    for key in (
        "maximum_boundary_edges",
        "maximum_nonmanifold_edges",
        "maximum_degenerate_facets",
        "maximum_duplicate_facets",
    ):
        if int(mesh.get(key, -1)) != 0:
            errors.append(f"{key} must remain zero")
    if mesh.get("allow_automatic_repair") is not False:
        errors.append("automatic mesh repair must remain forbidden")
    if float(mesh.get("scale", 0.0)) != 1.0:
        errors.append("mesh scale must remain 1.0")
    conditioning = mesh.get("front_carrier_manufacturing_conditioning", {})
    exact_conditioning = {
        "required": True,
        "algorithm_id": "micron-weld-and-zero-area-filter-v1",
        "maximum_weld_distance_mm": 0.00002,
        "maximum_weld_displacement_mm": 0.00002,
        "hidden_seam_groove_width_mm": 0.025,
        "automatic_repair": False,
        "smoothing": False,
        "hole_filling": False,
        "remeshing": False,
        "scaling": False,
    }
    for key, expected in exact_conditioning.items():
        if conditioning.get(key) != expected:
            errors.append(
                f"front carrier manufacturing conditioning {key} "
                f"must remain {expected!r}"
            )
    root = repository_root(contract_path)
    conditioner_path = safe_repo_path(
        root,
        conditioning.get("module_path"),
        "front carrier conditioning module_path",
        errors,
    )
    conditioner_hash = conditioning.get("module_sha256")
    if not isinstance(conditioner_hash, str) or not SHA256_RE.fullmatch(
        conditioner_hash
    ):
        errors.append("front carrier conditioning module SHA-256 is invalid")
    elif conditioner_path is not None:
        if not conditioner_path.is_file():
            errors.append("front carrier conditioning module is missing")
        elif sha256_file(conditioner_path) != conditioner_hash:
            errors.append("front carrier conditioning module hash mismatch")
    if (
        mesh.get("translucent_eye_glass_manufacturing_conditioning")
        != "none; raw lens mesh must pass"
    ):
        errors.append("lens must pass as a raw mesh without conditioning")

    printer = contract.get("printer", {})
    if printer.get("conservative_build_envelope_mm") != [240.0, 200.0, 210.0]:
        errors.append("conservative MK4S envelope changed")
    if float(printer.get("required_xy_edge_reserve_each_side_mm", 0.0)) < 10.0:
        errors.append("XY edge reserve cannot be below 10 mm per side")
    if float(printer.get("nozzle_diameter_mm", 0.0)) != 0.4:
        errors.append("packaging contract is specifically for a 0.4 mm nozzle")

    materials = contract.get("materials", {})
    if materials.get("front_carrier_default") != "conditioned opaque PETG":
        errors.append("front carrier must specify conditioned opaque PETG")

    assembly = contract.get("assembly", {})
    retention = str(assembly.get("primary_retention", ""))
    if not all(token in retention for token in ("three tiny", "clear", "neutral-cure silicone")):
        errors.append("primary retention must be three tiny clear neutral-cure silicone dabs")
    if int(assembly.get("retention_dab_count", 0)) != 3:
        errors.append("retention_dab_count must remain exactly three")
    if "cyanoacrylate" not in str(assembly.get("adhesive_warning", "")):
        errors.append("CA-blooming warning is missing")
    fastener_warning = str(assembly.get("fastener_warning", "")).lower()
    if "screws are prohibited" not in fastener_warning or "unnecessary screws" not in fastener_warning:
        errors.append("explicit unnecessary lens-screw prohibition is missing")

    lens_defaults = contract.get("slicer_defaults", {}).get("eye_glass", {})
    if (
        float(lens_defaults.get("layer_height_mm", 0.0)) != 0.15
        or float(lens_defaults.get("first_layer_height_mm", 0.0)) != 0.15
        or int(lens_defaults.get("exact_total_layers", 0)) != 6
        or int(lens_defaults.get("top_solid_layers", 0)) != 6
        or int(lens_defaults.get("bottom_solid_layers", 0)) != 6
    ):
        errors.append("eye-lens slicer defaults must remain six 0.15 mm solid layers")

    for item in parts:
        profile = contract_path.parent / str(item.get("profile", ""))
        if not profile.is_file():
            errors.append(f"missing slicer profile for {item.get('id')}: {profile}")
            continue
        values, profile_errors = parse_profile(profile)
        errors.extend(profile_errors)
        if values.get("filament_type") != "PETG":
            errors.append(f"{profile.name}: filament_type must be PETG")
        if values.get("nozzle_diameter") != "0.4":
            errors.append(f"{profile.name}: nozzle_diameter must be 0.4")
        if item.get("id") == "translucent_eye_glass":
            exact_lens_values = {
                "layer_height": "0.15",
                "first_layer_height": "0.15",
                "top_solid_layers": "6",
                "bottom_solid_layers": "6",
                "fill_density": "100%",
                "support_material": "0",
                "ironing": "0",
            }
            for key, expected in exact_lens_values.items():
                if values.get(key) != expected:
                    errors.append(f"{profile.name}: {key} must remain {expected}")
    return errors


def release_errors(contract: dict[str, Any], contract_path: Path) -> list[str]:
    errors = contract_errors(contract, contract_path)
    root = repository_root(contract_path)
    source = contract["source_release"]
    if source.get("printing_authorized") is not True:
        errors.append("source_release.printing_authorized is not true")
    paths: dict[str, Path] = {}
    for key in ("fcstd_path", "validation_path"):
        path = safe_repo_path(root, source.get(key), f"source_release.{key}", errors)
        if path is not None:
            paths[key] = path
            if not path.is_file():
                errors.append(f"source_release.{key}: file not found")
    for path_key, hash_key in (("fcstd_path", "fcstd_sha256"), ("validation_path", "validation_sha256")):
        expected = source.get(hash_key)
        if not isinstance(expected, str) or not SHA256_RE.fullmatch(expected):
            errors.append(f"source_release.{hash_key}: required lowercase SHA-256")
        elif path_key in paths and paths[path_key].is_file() and sha256_file(paths[path_key]) != expected:
            errors.append(f"source_release.{path_key}: SHA-256 mismatch")
    for item in source["parts"]:
        if not isinstance(item.get("object_name"), str) or not item["object_name"]:
            errors.append(f"{item['id']}: final object_name is missing")
        if not normalized(item.get("bed_face_outward_normal")):
            errors.append(f"{item['id']}: normalized measured bed-face outward normal is missing")

    validation_path = paths.get("validation_path")
    if validation_path is not None and validation_path.is_file():
        validation = load_json(validation_path)
        prefix = str(source["required_validation_status_prefix"])
        if not str(validation.get("status", "")).startswith(prefix):
            errors.append("source validation status is not PASS")
        if validation.get("printing_authorized") is not True:
            errors.append("source validation does not explicitly authorize printing")
        evidence = validation.get("print_packaging", {}).get("parts", {})
        gates = contract["geometry_gates"]
        for part_id in PART_IDS:
            item = evidence.get(part_id, {})
            if item.get("valid") is not True or item.get("closed") is not True:
                errors.append(f"{part_id}: valid/closed evidence missing")
            if int(item.get("solid_count", 0)) != 1:
                errors.append(f"{part_id}: one-solid evidence missing")
            if item.get("occt_check_messages", ["missing"]):
                errors.append(f"{part_id}: clean OCCT evidence missing")
            if float(item.get("minimum_wall_mm", 0.0)) < float(gates["minimum_wall_mm"]):
                errors.append(f"{part_id}: measured wall below 0.7 mm")
            if int(item.get("self_intersection_count", -1)) != 0:
                errors.append(f"{part_id}: zero self-intersection evidence missing")
            manufacturing_mesh = item.get("manufacturing_mesh", {})
            for key in (
                "boundary_edges",
                "nonmanifold_edges",
                "degenerate_facets",
                "duplicate_facets",
                "self_intersection_count",
            ):
                if int(manufacturing_mesh.get(key, -1)) != 0:
                    errors.append(
                        f"{part_id}: manufacturing mesh {key} is not zero"
                    )
            if int(manufacturing_mesh.get("connected_components", 0)) != 1:
                errors.append(
                    f"{part_id}: manufacturing mesh is not one component"
                )
            if manufacturing_mesh.get("outward_normals") is not True:
                errors.append(
                    f"{part_id}: manufacturing mesh is not outward"
                )
        glass = evidence.get("translucent_eye_glass", {})
        thickness = float(glass.get("thickness_mm", 0.0))
        target = float(gates["eye_glass_thickness_mm"])
        tolerance = float(gates["eye_glass_thickness_measurement_tolerance_mm"])
        if abs(thickness - target) > tolerance:
            errors.append(
                "translucent_eye_glass: thickness misses "
                f"{target:.2f} +/- {tolerance:.2f} mm; measured {thickness:.6f} mm"
            )
        if evidence.get("front_carrier", {}).get("aperture_preserved") is not True:
            errors.append("front_carrier: exact aperture preservation evidence missing")
        if evidence.get("front_carrier", {}).get("rear_eye_glass_seat_continuous") is not True:
            errors.append("front_carrier: continuous rear eye-glass seat evidence missing")
        names = validation.get("print_packaging", {}).get(
            "object_names", {}
        )
        for item in source["parts"]:
            if names.get(item["id"]) != item["object_name"]:
                errors.append(
                    f"{item['id']}: source object name differs from validation"
                )
        conditioning = validation.get(
            "manufacturing_conditioning", {}
        ).get("front_mesh", {})
        required_conditioning = contract["mesh_gates"][
            "front_carrier_manufacturing_conditioning"
        ]
        if conditioning.get("algorithm_id") != required_conditioning[
            "algorithm_id"
        ]:
            errors.append("front conditioning algorithm evidence mismatch")
        if conditioning.get("automatic_repair_used") is not False:
            errors.append("front conditioning used generic automatic repair")
        if float(
            conditioning.get("maximum_weld_displacement_mm", math.inf)
        ) > float(required_conditioning["maximum_weld_displacement_mm"]):
            errors.append("front conditioning displacement exceeds bound")
        if (
            validation.get("pins", {}).get("mesh_conditioner_sha256")
            != required_conditioning["module_sha256"]
        ):
            errors.append("front conditioning module evidence is not pinned")
    return errors


def command_plan(contract: dict[str, Any], contract_path: Path) -> list[str]:
    base = contract_path.parent
    output = contract["outputs"]["directory"]
    commands = [
        f"python3 {base.relative_to(repository_root(contract_path)) / 'preflight.py'} --contract {contract_path.relative_to(repository_root(contract_path))} --release-ready",
        "timeout 180s env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib "
        f"/tmp/freecad-1.1.3-extract/squashfs-root/AppRun python -B {base.relative_to(repository_root(contract_path)) / 'export_print_package.py'} --contract {contract_path.relative_to(repository_root(contract_path))} --export-if-pass",
    ]
    for item in contract["source_release"]["parts"]:
        commands.append(
            f"prusa-slicer --load {base.relative_to(repository_root(contract_path)) / item['profile']} "
            f"--export-3mf --dont-arrange --no-ensure-on-bed "
            f"--output {output}/{item['project_name']} {output}/{item['stl_name']}"
        )
        commands.append(f"prusa-slicer --info {output}/{item['project_name']}")
    return commands


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=Path(__file__).with_name("contract.json"))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--contract-only", action="store_true")
    mode.add_argument("--release-ready", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    contract_path = args.contract.resolve()
    contract = load_json(contract_path)
    errors = release_errors(contract, contract_path) if args.release_ready else contract_errors(contract, contract_path)
    result = {
        "schema_version": "cat-head-right-eye-print-packaging-preflight-v1",
        "status": "PASS__TOOLING_READY" if not errors else (
            "BLOCKED__RELEASE_INPUTS_INCOMPLETE" if args.release_ready else "FAIL__TOOLING_CONTRACT"
        ),
        "mode": "release-ready" if args.release_ready else "contract-only",
        "candidate_opened": False,
        "artifact_written": False,
        "automatic_repair_used": False,
        "prusaslicer_available": shutil.which("prusa-slicer") is not None,
        "contract_sha256": sha256_file(contract_path),
        "errors": errors,
        "commands_after_review_pass": command_plan(contract, contract_path),
        "hard_blockers": contract["missing_inputs"]["hard_blockers"],
        "conservative_defaults": contract["missing_inputs"]["conservative_defaults_not_blocking_first_print"],
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
