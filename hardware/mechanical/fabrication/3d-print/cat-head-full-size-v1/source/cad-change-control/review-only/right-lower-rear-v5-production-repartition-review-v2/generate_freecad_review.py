#!/usr/bin/env python3
"""Construct the approved V5 lower/rear split without rewriting retained meshes.

Feasibility is no-save. Review mode writes one fresh non-authoritative FCStd
and JSON only. This lineage never exports STL/3MF/G-code.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
CONTRACT_PATH = HERE / "contract.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schema_version") != "cat-head-right-lower-rear-v5-production-repartition-review-v2":
        raise RuntimeError("unexpected V2 contract schema")
    return contract


def require_hash(item: dict[str, Any]) -> Path:
    path = (PROJECT_ROOT / item["path"]).resolve()
    actual = sha256(path)
    if actual != item["sha256"]:
        raise RuntimeError(f"hash mismatch: {path}: {actual}")
    return path


def load_v1(contract: dict[str, Any]) -> Any:
    path = require_hash(contract["inputs"]["v1_generator"])
    spec = importlib.util.spec_from_file_location("lower_repartition_v1", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load pinned V1 generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metrics(shape: Any) -> dict[str, Any]:
    return {
        "shape_type": shape.ShapeType,
        "solid_count": len(shape.Solids),
        "shell_count": len(shape.Shells),
        "face_count": len(shape.Faces),
        "volume_mm3": float(shape.Volume),
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
    }


def expected_kept_sides(minimum: float, maximum: float, gap: float,
                        tolerance: float = 1.0e-9) -> tuple[bool, bool]:
    return (
        minimum < -gap / 2.0 - tolerance,
        maximum > +gap / 2.0 + tolerance,
    )


def build() -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], Any, list[tuple[str, Any]]]:
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    contract = load_contract()
    require_hash(contract["inputs"]["v1_contract"])
    require_hash(contract["inputs"]["released_v3_manifest"])
    v1 = load_v1(contract)
    canonical_path = require_hash(contract["inputs"]["relieved_shell_reference"])
    v8_path = require_hash(contract["inputs"]["user_manual_v8_reference"])
    eye_path = require_hash(contract["inputs"]["released_v3_right_eye"])

    curtain = contract["partition"]
    point = App.Vector(*map(float, curtain["seam_midpoint_mm"]))
    axis_u = App.Vector(*map(float, curtain["seam_direction_unit"]))
    axis_v = App.Vector(*map(float, curtain["shell_inward_unit"]))
    normal = App.Vector(*map(float, curtain["normal_toward_cassette_unit"]))
    axis_u.normalize(); axis_v.normalize(); normal.normalize()
    if max(abs(float(axis_u.dot(axis_v))), abs(float(axis_u.dot(normal))), abs(float(axis_v.dot(normal)))) > 1.0e-5:
        raise RuntimeError("partition curtain basis is not orthonormal")
    gap = float(curtain["mating_clearance_mm"])
    retained_mask = v1.curtain_mask(Part, point, axis_u, axis_v, normal, -1, gap)
    cassette_mask = v1.curtain_mask(Part, point, axis_u, axis_v, normal, +1, gap)
    allowed_mesh_only = set(map(int, contract["canonical_owner_policy"]["known_retained_mesh_only_owner_indices"]))

    canonical = App.openDocument(str(canonical_path))
    v8 = App.openDocument(str(v8_path))
    eye = App.openDocument(str(eye_path))
    try:
        lower_main = canonical.getObject("FROZEN_RIGHT_LOWER_MAIN_V34")
        lower_mesh = canonical.getObject("FROZEN_RIGHT_LOWER_COMPONENTS_002_060_V34")
        manual_flange = next((obj for obj in v8.Objects if obj.Label == "HEAD_BOTTOM_FLANGE"), None)
        if lower_main is None or lower_mesh is None or manual_flange is None:
            raise RuntimeError("required canonical lower owners or manual bottom flange missing")

        eye_objects = []
        for name in contract["required_v3_eye_objects"]:
            obj = eye.getObject(name)
            if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
                raise RuntimeError(f"released V3 eye object missing: {name}")
            if not obj.Shape.isValid() or not obj.Shape.isClosed() or len(obj.Shape.Solids) != 1:
                raise RuntimeError(f"released V3 eye object is not one valid closed solid: {name}")
            eye_objects.append((name, obj.Shape.copy()))

        converted = Part.Shape()
        converted.makeShapeFromMesh(lower_mesh.Mesh.Topology, 0.01)
        if len(converted.Shells) != int(contract["canonical_owner_policy"]["expected_converted_shell_count"]):
            raise RuntimeError(f"unexpected converted shell count: {len(converted.Shells)}")

        raw_sources: list[tuple[int, str, Any]] = [(1, "component_001_relief_main", lower_main.Shape.copy())]
        for index, shell in enumerate(converted.Shells, start=2):
            raw_sources.append((index, f"component_{index:03d}", Part.makeSolid(shell)))
        if len(raw_sources) != int(contract["canonical_owner_policy"]["expected_owner_count"]):
            raise RuntimeError(f"unexpected canonical owner count: {len(raw_sources)}")

        retained: list[dict[str, Any]] = []
        cassette: list[dict[str, Any]] = []
        mesh_only: list[dict[str, Any]] = []
        split_records = []
        owner_records = []
        source_total = 0.0
        gap_removed_total = 0.0
        for index, name, shape in raw_sources:
            source_total += float(shape.Volume)
            minimum, maximum = v1.signed_range(shape, point, normal)
            valid_closed = bool(shape.isValid() and shape.isClosed() and len(shape.Solids) == 1)
            owner_record = {
                "component_index": index,
                "name": name,
                "minimum_signed_mm": minimum,
                "maximum_signed_mm": maximum,
                "valid_closed_one_solid_brep": valid_closed,
                "source_volume_mm3": float(shape.Volume),
            }
            if not valid_closed:
                if index not in allowed_mesh_only:
                    raise RuntimeError(f"unexpected invalid canonical owner: {name}")
                if maximum >= -gap / 2.0:
                    raise RuntimeError(f"mesh-only owner is not wholly retained: {name}")
                record = {**owner_record, "owner": "retained_mesh_only_unchanged", "shape": shape}
                mesh_only.append(record)
                owner_records.append({key: value for key, value in record.items() if key != "shape"})
                continue

            if maximum < -gap / 2.0:
                record = {**owner_record, "owner": "retained", "shape": shape}
                retained.append(record)
            elif minimum > gap / 2.0:
                record = {**owner_record, "owner": "cassette", "shape": shape}
                cassette.append(record)
            else:
                retained_piece = shape.common(retained_mask).removeSplitter()
                cassette_piece = shape.common(cassette_mask).removeSplitter()
                expect_retained, expect_cassette = expected_kept_sides(minimum, maximum, gap)
                has_retained = (
                    not retained_piece.isNull()
                    and float(retained_piece.Volume) > 1.0e-7
                    and len(retained_piece.Solids) >= 1
                )
                has_cassette = (
                    not cassette_piece.isNull()
                    and float(cassette_piece.Volume) > 1.0e-7
                    and len(cassette_piece.Solids) >= 1
                )
                if has_retained != expect_retained or has_cassette != expect_cassette:
                    raise RuntimeError(
                        f"signed-span/Boolean kept-side mismatch: {name}: "
                        f"expected=({expect_retained},{expect_cassette}) "
                        f"actual=({has_retained},{has_cassette})"
                    )
                for label, piece, present in (
                    ("retained", retained_piece, has_retained),
                    ("cassette", cassette_piece, has_cassette),
                ):
                    if present and (not piece.isValid() or not piece.isClosed() or len(piece.Solids) < 1):
                        raise RuntimeError(f"{name} {label} split is not valid/closed")
                removed = float(shape.Volume - retained_piece.Volume - cassette_piece.Volume)
                if removed < -1.0e-5:
                    raise RuntimeError(f"negative seam-gap removal balance: {name}: {removed}")
                gap_removed_total += max(0.0, removed)
                if has_retained:
                    retained.append({**owner_record, "name": f"{name}__retained", "owner": "retained_split", "shape": retained_piece})
                if has_cassette:
                    cassette.append({**owner_record, "name": f"{name}__cassette", "owner": "cassette_split", "shape": cassette_piece})
                kept_class = (
                    "retained_and_cassette"
                    if has_retained and has_cassette
                    else ("retained_only_after_gap_trim" if has_retained else "cassette_only_after_gap_trim")
                )
                split_records.append({
                    "component_index": index,
                    "source": name,
                    "kept_class": kept_class,
                    "source_volume_mm3": float(shape.Volume),
                    "retained_volume_mm3": float(retained_piece.Volume),
                    "cassette_volume_mm3": float(cassette_piece.Volume),
                    "gap_removed_volume_mm3": removed,
                })
                record = {**owner_record, "owner": kept_class}
                owner_records.append(record)
                continue
            owner_records.append({key: value for key, value in record.items() if key != "shape"})

        if {item["component_index"] for item in mesh_only} != allowed_mesh_only:
            raise RuntimeError("known retained mesh-only owner set changed")

        component_007 = next((item for item in retained if item["component_index"] == 7), None)
        if component_007 is None:
            raise RuntimeError("component_007 is not a retained valid owner")
        common = component_007["shape"].common(manual_flange.Shape)
        common_volume = 0.0 if common.isNull() else float(common.Volume)
        if common_volume < 1.0:
            raise RuntimeError(f"manual flange root overlap too small: {common_volume}")
        fused = component_007["shape"].fuse(manual_flange.Shape).removeSplitter()
        if not fused.isValid() or not fused.isClosed() or len(fused.Solids) != 1:
            raise RuntimeError("manual bottom flange did not fuse into one valid retained solid")
        component_007["shape"] = fused
        component_007["name"] = "component_007__WITH_USER_HEAD_BOTTOM_FLANGE"

        carrier_shape = dict(eye_objects)["RIGHT_EYE_CARRIER_V3_CORNER_REPAIR_PRINT"]
        flange_eye_common = manual_flange.Shape.common(carrier_shape)
        flange_eye_common_volume = 0.0 if flange_eye_common.isNull() else float(flange_eye_common.Volume)
        flange_eye_distance = float(manual_flange.Shape.distToShape(carrier_shape)[0])
        if flange_eye_common_volume > 1.0e-6:
            raise RuntimeError(f"manual head flange penetrates released V3 eye: {flange_eye_common_volume}")

        result = {
            "schema_version": "cat-head-right-lower-rear-v5-production-repartition-feasibility-v2",
            "status": "PASS__V2_REVIEW_GEOMETRY_READY__NOT_PRINT_RELEASED",
            "authority": contract["authority"],
            "input_sha256": {key: item["sha256"] for key, item in contract["inputs"].items()},
            "approved_seam": curtain,
            "canonical_owner_count": len(raw_sources),
            "retained_valid_piece_count": len(retained),
            "cassette_valid_piece_count": len(cassette),
            "retained_mesh_only_unchanged_count": len(mesh_only),
            "retained_mesh_only_owner_indices": [item["component_index"] for item in mesh_only],
            "crossing_split_count": len(split_records),
            "split_records": split_records,
            "owner_records": owner_records,
            "source_total_volume_mm3": source_total,
            "seam_gap_removed_total_mm3": gap_removed_total,
            "manual_flange_root_owner": "component_007",
            "manual_flange_root_overlap_mm3": common_volume,
            "manual_flange_to_released_v3_eye_common_mm3": flange_eye_common_volume,
            "manual_flange_to_released_v3_eye_distance_mm": flange_eye_distance,
            "released_v3_eye_objects": {name: metrics(shape) for name, shape in eye_objects},
            "print_release_holds": [
                "Three retained canonical owners remain mesh-only and are deliberately not rewritten by this review.",
                "Retained and cassette ownership groups are not yet each proven as one connected printable body.",
                "No bilateral mirror, STL, 3MF, G-code, slicing, or print release is produced by this lineage."
            ],
            "io_trace": {
                "canonical_saved": False,
                "v8_saved": False,
                "released_v3_eye_saved": False,
                "review_saved": False,
                "geometry_export_created": False,
                "production_output_created": False
            }
        }
        seam_marker = Part.makeLine(
            App.Vector(*map(float, curtain["seam_endpoints_mm"][0])),
            App.Vector(*map(float, curtain["seam_endpoints_mm"][1])),
        )
        return result, retained, cassette, mesh_only, seam_marker, eye_objects
    finally:
        App.closeDocument(eye.Name)
        App.closeDocument(v8.Name)
        App.closeDocument(canonical.Name)


def save_review(result: dict[str, Any], retained: list[dict[str, Any]], cassette: list[dict[str, Any]],
                mesh_only: list[dict[str, Any]], seam_marker: Any, eye_objects: list[tuple[str, Any]]) -> tuple[Path, Path]:
    import FreeCAD as App  # type: ignore

    contract = load_contract()
    output_dir = (PROJECT_ROOT / contract["outputs"]["directory"]).resolve()
    if output_dir.exists():
        raise RuntimeError(f"review output already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    document = App.newDocument("RIGHT_LOWER_REAR_V5_PRODUCTION_REPARTITION_REVIEW_ONLY_V2")
    try:
        retained_group = document.addObject("App::DocumentObjectGroup", "RETAINED_FRONT_LOWER_OWNERS")
        cassette_group = document.addObject("App::DocumentObjectGroup", "REAR_CASSETTE_LOWER_OWNERS")
        mesh_group = document.addObject("App::DocumentObjectGroup", "UNCHANGED_RETAINED_MESH_ONLY_OWNERS")
        eye_group = document.addObject("App::DocumentObjectGroup", "REFERENCE_RELEASED_V3_RIGHT_EYE")
        for prefix, group, records, color, transparency in (
            ("RET", retained_group, retained, (0.25, 0.65, 0.95), 0),
            ("CAS", cassette_group, cassette, (1.0, 0.48, 0.12), 12),
            ("MESH", mesh_group, mesh_only, (0.65, 0.65, 0.68), 0),
        ):
            for index, record in enumerate(records, start=1):
                obj = document.addObject("Part::Feature", f"{prefix}_{index:03d}")
                obj.Label = f"{record['owner'].upper()} — {record['name']}"
                obj.Shape = record["shape"]
                obj.addProperty("App::PropertyString", "Authority", "Review Control")
                obj.Authority = contract["authority"]
                group.addObject(obj)
                if getattr(obj, "ViewObject", None) is not None:
                    obj.ViewObject.ShapeColor = color
                    obj.ViewObject.Transparency = transparency
        for index, (name, shape) in enumerate(eye_objects, start=1):
            obj = document.addObject("Part::Feature", f"EYE_{index:02d}")
            obj.Label = f"REFERENCE — RELEASED V3 — {name}"
            obj.Shape = shape
            eye_group.addObject(obj)
            if getattr(obj, "ViewObject", None) is not None:
                obj.ViewObject.ShapeColor = (0.35, 0.95, 0.55)
                obj.ViewObject.Transparency = 72
        marker = document.addObject("Part::Feature", "APPROVED_V5_DIAGONAL_SEAM")
        marker.Label = "REFERENCE — APPROVED V5 DIAGONAL SEAM"
        marker.Shape = seam_marker
        if getattr(marker, "ViewObject", None) is not None:
            marker.ViewObject.LineColor = (1.0, 1.0, 0.0)
            marker.ViewObject.LineWidth = 5.0
        document.recompute()
        fcstd = output_dir / contract["outputs"]["fcstd"]
        document.saveAs(str(fcstd))
    finally:
        App.closeDocument(document.Name)
    result["io_trace"]["review_saved"] = True
    result["generated_fcstd"] = str(fcstd.relative_to(PROJECT_ROOT))
    result["generated_fcstd_sha256"] = sha256(fcstd)
    validation = output_dir / contract["outputs"]["validation"]
    validation.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return fcstd, validation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("feasibility", "review"), required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result, retained, cassette, mesh_only, seam_marker, eye_objects = build()
    if args.mode == "feasibility":
        if args.report is None or not str(args.report.resolve()).startswith("/tmp/"):
            raise RuntimeError("feasibility requires a /tmp report")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": result["status"],
            "retained_valid": len(retained),
            "cassette_valid": len(cassette),
            "retained_mesh_only": len(mesh_only),
            "crossing": result["crossing_split_count"]
        }, sort_keys=True))
        return 0
    fcstd, validation = save_review(result, retained, cassette, mesh_only, seam_marker, eye_objects)
    print(json.dumps({"status": result["status"], "fcstd": str(fcstd), "validation": str(validation)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
