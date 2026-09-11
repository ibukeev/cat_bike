#!/usr/bin/env python3
"""Create the isolated V4 reinforcement-plank cleanup review.

This removes two complete V3 owner records and one duplicate display overlay.
It does not cut, fuse, heal, export, mirror, or alter the approved V3 seam.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from typing import Any, Sequence


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
    if contract.get("schema_version") != "cat-head-right-lower-rear-v5-seam-cleanup-review-v4":
        raise RuntimeError("unexpected V4 cleanup contract schema")
    return contract


def require_hash(item: dict[str, Any]) -> Path:
    path = (PROJECT_ROOT / item["path"]).resolve()
    actual = sha256(path)
    if actual != item["sha256"]:
        raise RuntimeError(
            f"hash mismatch: {path}: expected {item['sha256']}, got {actual}"
        )
    return path


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_exact(records: list[dict[str, Any]], spec: dict[str, Any]) -> dict[str, Any]:
    matches = [
        record
        for record in records
        if int(record["component_index"]) == int(spec["component_index"])
        and str(record["name"]) == str(spec["record_name"])
        and str(record["owner"]) == str(spec["record_owner"])
    ]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one cleanup owner, found {len(matches)}: {spec}")
    return matches[0]


def long_linear_directions(shape: Any) -> list[Any]:
    candidates: list[tuple[float, Any]] = []
    for edge in shape.Edges:
        vertices = edge.Vertexes
        if len(vertices) != 2:
            continue
        direction = vertices[1].Point - vertices[0].Point
        if float(direction.Length) <= 1.0e-12:
            continue
        candidates.append((float(edge.Length), direction))
    if not candidates:
        raise RuntimeError("cleanup owner has no measurable two-vertex edge")
    longest = max(item[0] for item in candidates)
    directions = []
    for length, direction in candidates:
        if length < longest * 0.80:
            continue
        direction.normalize()
        directions.append(direction)
    return directions


def shape_metrics(shape: Any) -> dict[str, Any]:
    return {
        "shape_type": str(shape.ShapeType),
        "solid_count": len(shape.Solids),
        "volume_mm3": float(shape.Volume),
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
    }


def disposable_finalization(
    front_component_001: Any,
    rear_component_001: Any,
    straight_marker: Any,
    contract: dict[str, Any],
) -> dict[str, bool]:
    import FreeCAD as App  # type: ignore

    document = App.newDocument("DISPOSABLE_V4_SEAM_CLEANUP_PREFLIGHT")
    try:
        for name, shape in (
            ("PRESERVED_V3_COMPONENT_001_FRONT", front_component_001),
            ("PRESERVED_V3_COMPONENT_001_REAR", rear_component_001),
            ("PRESERVED_V3_AXIS_STRAIGHT_SEAM", straight_marker),
        ):
            obj = document.addObject("Part::Feature", name)
            obj.Shape = shape
            obj.addProperty("App::PropertyString", "Authority", "Review Control")
            obj.Authority = contract["authority"]
        document.recompute()
        for name in (
            "PRESERVED_V3_COMPONENT_001_FRONT",
            "PRESERVED_V3_COMPONENT_001_REAR",
            "PRESERVED_V3_AXIS_STRAIGHT_SEAM",
        ):
            obj = document.getObject(name)
            if obj is None or obj.Shape.isNull():
                raise RuntimeError(f"disposable V4 assignment failed: {name}")
        return {
            "target_assignment_ran": True,
            "typed_metadata_assignment_ran": True,
            "document_recompute_ran": True,
            "save_as_called": False,
            "document_save_called": False,
            "geometry_export_created": False,
        }
    finally:
        App.closeDocument(document.Name)


def build() -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
    Any,
    list[tuple[str, Any]],
]:
    contract = load_contract()
    for item in contract["inputs"].values():
        require_hash(item)
    v3 = load_module(require_hash(contract["inputs"]["v3_generator"]), "v3_for_cleanup_v4")
    (
        v3_result,
        retained,
        cassette,
        mesh_only,
        _old_seam_marker,
        straight_marker,
        _duplicate_transfer_shape,
        eye_objects,
    ) = v3.build()
    expected_status = "PASS__V3_AXIS_STRAIGHT_SECTOR_REVIEW_READY__NOT_PRINT_RELEASED"
    if v3_result.get("status") != expected_status:
        raise RuntimeError("pinned V3 reconstruction did not pass")

    cleanup = contract["cleanup"]
    front_removed = find_exact(retained, cleanup["front_owner_to_remove"])
    rear_removed = find_exact(cassette, cleanup["rear_owner_to_remove"])
    front_shape = front_removed["shape"]
    rear_shape = rear_removed["shape"]
    front_volume = float(front_shape.Volume)
    rear_volume = float(rear_shape.Volume)
    pair_distance = float(front_shape.distToShape(rear_shape)[0])
    axis_dot = max(
        abs(float(front_axis.dot(rear_axis)))
        for front_axis in long_linear_directions(front_shape)
        for rear_axis in long_linear_directions(rear_shape)
    )

    retained_clean = [record for record in retained if record is not front_removed]
    cassette_clean = [record for record in cassette if record is not rear_removed]
    front_component_001_before = next(
        record["shape"] for record in retained if int(record["component_index"]) == 1
    )
    front_component_001_after = next(
        record["shape"] for record in retained_clean if int(record["component_index"]) == 1
    )
    rear_component_001_before = next(
        record["shape"] for record in cassette if int(record["component_index"]) == 1
    )
    rear_component_001_after = next(
        record["shape"] for record in cassette_clean if int(record["component_index"]) == 1
    )

    gates = contract["numeric_gates"]
    epsilon = float(gates["volume_epsilon_mm3"])
    checks = {
        "pinned_v3_reconstruction_passes": True,
        "exactly_one_front_record_removed": len(retained) - len(retained_clean) == 1,
        "exactly_one_rear_record_removed": len(cassette) - len(cassette_clean) == 1,
        "front_removed_owner_identity_exact": (
            abs(front_volume - float(cleanup["front_owner_to_remove"]["expected_volume_mm3"])) <= epsilon
        ),
        "rear_removed_owner_identity_exact": (
            abs(rear_volume - float(cleanup["rear_owner_to_remove"]["expected_volume_mm3"])) <= epsilon
        ),
        "front_and_rear_residuals_are_parallel_continuations": (
            axis_dot >= float(gates["minimum_pair_axis_absolute_dot"])
        ),
        "front_and_rear_residual_pair_distance_is_pinned": (
            abs(pair_distance - float(cleanup["pair_evidence"]["minimum_distance_mm"]))
            <= float(gates["pair_distance_tolerance_mm"])
        ),
        "all_kept_front_shape_objects_are_reused": all(
            any(record is original for original in retained)
            for record in retained_clean
        ),
        "all_kept_rear_shape_objects_are_reused": all(
            any(record is original for original in cassette)
            for record in cassette_clean
        ),
        "component_001_front_is_exact_same_shape_object": (
            front_component_001_before is front_component_001_after
        ),
        "component_001_rear_is_exact_same_shape_object": (
            rear_component_001_before is rear_component_001_after
        ),
        "no_geometry_was_added": True,
        "duplicate_transfer_overlay_is_not_part_of_clean_records": all(
            record.get("name") != cleanup["review_overlay_to_omit"]["internal_name"]
            for record in retained_clean + cassette_clean
        ),
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(f"V4 cleanup gates failed: {failed}")

    finalization = disposable_finalization(
        front_component_001_after,
        rear_component_001_after,
        straight_marker,
        contract,
    )
    result = {
        "schema_version": "cat-head-right-lower-rear-v5-seam-cleanup-validation-v4",
        "status": "PASS__V4_SEAM_CLEANUP_REVIEW_READY__NOT_PRINT_RELEASED",
        "authority": contract["authority"],
        "input_sha256": {
            name: item["sha256"] for name, item in contract["inputs"].items()
        },
        "cleanup": cleanup,
        "checks": checks,
        "measurements": {
            "front_removed_component_index": int(front_removed["component_index"]),
            "front_removed_volume_mm3": front_volume,
            "rear_removed_component_index": int(rear_removed["component_index"]),
            "rear_removed_volume_mm3": rear_volume,
            "removed_pair_minimum_distance_mm": pair_distance,
            "removed_pair_long_axis_absolute_dot": axis_dot,
            "retained_v3_count_before": len(retained),
            "retained_v4_count_after": len(retained_clean),
            "rear_v3_count_before": len(cassette),
            "rear_v4_count_after": len(cassette_clean),
        },
        "preserved_component_001_front_metrics": shape_metrics(front_component_001_after),
        "preserved_component_001_rear_metrics": shape_metrics(rear_component_001_after),
        "mesh_only_unchanged_count": len(mesh_only),
        "released_v3_eye_objects": {
            name: shape_metrics(shape) for name, shape in eye_objects
        },
        "disposable_finalization": finalization,
        "next_review_hold": "Long ledge and screw-interface geometry is a separate future change bucket.",
        "print_release_holds": [
            "This is a cleanup review, not a fused production body.",
            "No ledge, fastener, bed orientation, mirror, STL, 3MF, G-code, slicing, or print release is authorized."
        ],
        "io_trace": {
            "v3_saved": False,
            "canonical_saved": False,
            "review_saved": False,
            "geometry_export_created": False,
            "production_output_created": False,
        },
    }
    return result, retained_clean, cassette_clean, mesh_only, straight_marker, eye_objects


def add_feature(
    document: Any,
    group: Any,
    name: str,
    label: str,
    shape: Any,
    authority: str,
    color: tuple[float, float, float],
    transparency: int = 0,
) -> Any:
    obj = document.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "Authority", "Review Control")
    obj.Authority = authority
    group.addObject(obj)
    if getattr(obj, "ViewObject", None) is not None:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = transparency
    return obj


def save_review(
    result: dict[str, Any],
    retained: list[dict[str, Any]],
    cassette: list[dict[str, Any]],
    mesh_only: list[dict[str, Any]],
    straight_marker: Any,
    eye_objects: list[tuple[str, Any]],
) -> tuple[Path, Path]:
    import FreeCAD as App  # type: ignore

    contract = load_contract()
    output_dir = (PROJECT_ROOT / contract["outputs"]["directory"]).resolve()
    if output_dir.exists():
        raise RuntimeError(f"review output already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    document = App.newDocument("RIGHT_LOWER_REAR_V5_SEAM_CLEANUP_REVIEW_ONLY_V4")
    try:
        front_group = document.addObject("App::DocumentObjectGroup", "CLEAN_FRONT_LOWER_OWNERS")
        rear_group = document.addObject("App::DocumentObjectGroup", "CLEAN_REAR_LOWER_OWNERS")
        mesh_group = document.addObject("App::DocumentObjectGroup", "UNCHANGED_RETAINED_MESH_ONLY_OWNERS")
        review_group = document.addObject("App::DocumentObjectGroup", "V4_CLEANUP_DECISION")
        eye_group = document.addObject("App::DocumentObjectGroup", "REFERENCE_RELEASED_V3_RIGHT_EYE")
        for prefix, group, records, color, transparency in (
            ("FRONT", front_group, retained, (0.25, 0.65, 0.95), 0),
            ("REAR", rear_group, cassette, (1.0, 0.48, 0.12), 14),
            ("MESH", mesh_group, mesh_only, (0.65, 0.65, 0.68), 0),
        ):
            for index, record in enumerate(records, start=1):
                add_feature(
                    document,
                    group,
                    f"{prefix}_{index:03d}",
                    f"{record['owner'].upper()} — {record['name']}",
                    record["shape"],
                    contract["authority"],
                    color,
                    transparency,
                )
        marker = add_feature(
            document,
            review_group,
            "PRESERVED_V3_AXIS_STRAIGHT_SEAM",
            "PRESERVED — APPROVED V3 AXIS-STRAIGHT SEAM",
            straight_marker,
            contract["authority"],
            (0.2, 1.0, 0.25),
        )
        if getattr(marker, "ViewObject", None) is not None:
            marker.ViewObject.LineWidth = 6.0
        decision = document.addObject("App::FeaturePython", "CLEANUP_DECISION_RECORD")
        decision.Label = "DECISION — REMOVE COMPONENT 057 FRONT + COMPONENT 056 REAR"
        decision.addProperty("App::PropertyString", "Authority", "Review Control")
        decision.addProperty("App::PropertyString", "RemovedFront", "Review Control")
        decision.addProperty("App::PropertyString", "RemovedRear", "Review Control")
        decision.addProperty("App::PropertyString", "OmittedOverlay", "Review Control")
        decision.Authority = contract["authority"]
        decision.RemovedFront = "component_057 / former RET_043"
        decision.RemovedRear = "component_056__cassette"
        decision.OmittedOverlay = "PROPOSED_FACE30_SECTOR_TRANSFER display duplicate"
        review_group.addObject(decision)
        for index, (name, shape) in enumerate(eye_objects, start=1):
            add_feature(
                document,
                eye_group,
                f"EYE_{index:02d}",
                f"REFERENCE — RELEASED V3 — {name}",
                shape,
                contract["authority"],
                (0.35, 0.95, 0.55),
                76,
            )
        document.recompute()
        forbidden = contract["cleanup"]["review_overlay_to_omit"]["internal_name"]
        if document.getObject(forbidden) is not None:
            raise RuntimeError("duplicate green transfer overlay was unexpectedly created")
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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("feasibility", "review"), required=True)
    parser.add_argument("--report", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    built = build()
    result = built[0]
    if args.mode == "feasibility":
        if args.report is None or not str(args.report.resolve()).startswith("/tmp/"):
            raise RuntimeError("feasibility requires a fresh /tmp report")
        if args.report.exists():
            raise RuntimeError(f"feasibility report already exists: {args.report}")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": result["status"],
            "front_removed_volume_mm3": result["measurements"]["front_removed_volume_mm3"],
            "rear_removed_volume_mm3": result["measurements"]["rear_removed_volume_mm3"],
            "pair_axis_absolute_dot": result["measurements"]["removed_pair_long_axis_absolute_dot"],
        }, sort_keys=True))
        return 0
    fcstd, validation = save_review(*built)
    print(json.dumps({
        "status": result["status"],
        "fcstd": str(fcstd),
        "validation": str(validation),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
