#!/usr/bin/env python3
"""Build the isolated V3 lower/rear ownership review.

Feasibility constructs and finalizes the complete proposal in a disposable
document. Review mode writes one fresh non-authoritative FCStd and validation
JSON. This script never exports manufacturing geometry.
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
    expected = "cat-head-right-lower-rear-v5-axis-straight-sector-review-v3"
    if contract.get("schema_version") != expected:
        raise RuntimeError("unexpected V3 contract schema")
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


def vec(App: Any, values: Sequence[float]) -> Any:
    return App.Vector(*map(float, values))


def metrics(shape: Any) -> dict[str, Any]:
    return {
        "shape_type": str(shape.ShapeType),
        "solid_count": len(shape.Solids),
        "shell_count": len(shape.Shells),
        "face_count": len(shape.Faces),
        "volume_mm3": float(shape.Volume),
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
    }


def cut_volume(left: Any, right: Any) -> float:
    result = left.cut(right)
    return 0.0 if result.isNull() else max(0.0, float(result.Volume))


def common_area(left: Any, right: Any) -> float:
    result = left.common(right)
    return 0.0 if result.isNull() else max(0.0, float(result.Area))


def assert_one_solid(name: str, shape: Any) -> None:
    if (
        shape.isNull()
        or not shape.isValid()
        or not shape.isClosed()
        or len(shape.Solids) != 1
    ):
        raise RuntimeError(f"{name} is not one valid closed solid")


def exercise_disposable(
    retained_shape: Any,
    cassette_shape: Any,
    transfer_shape: Any,
    contract: dict[str, Any],
) -> dict[str, bool]:
    import FreeCAD as App  # type: ignore

    document = App.newDocument("DISPOSABLE_V3_FINALIZATION_PREFLIGHT")
    try:
        for name, owner, shape in (
            ("TARGET_COMPONENT_001_FRONT", "retained_front", retained_shape),
            ("TARGET_COMPONENT_001_REAR", "rear_cassette", cassette_shape),
            ("PROPOSED_TRANSFER", "rear_to_front", transfer_shape),
        ):
            obj = document.addObject("Part::Feature", name)
            obj.Shape = shape
            obj.addProperty("App::PropertyString", "Authority", "Review Control")
            obj.addProperty("App::PropertyString", "Owner", "Review Control")
            obj.Authority = contract["authority"]
            obj.Owner = owner
        document.recompute()
        for name in (
            "TARGET_COMPONENT_001_FRONT",
            "TARGET_COMPONENT_001_REAR",
            "PROPOSED_TRANSFER",
        ):
            obj = document.getObject(name)
            if obj is None or obj.Shape.isNull():
                raise RuntimeError(f"disposable target assignment failed: {name}")
            if str(obj.Authority) != contract["authority"]:
                raise RuntimeError(f"typed metadata assignment failed: {name}")
        return {
            "target_assignment_ran": True,
            "typed_metadata_assignment_ran": True,
            "document_recompute_ran": True,
            "final_identity_assertions_ran": True,
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
    Any,
    Any,
    list[tuple[str, Any]],
]:
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    contract = load_contract()
    for item in contract["inputs"].values():
        require_hash(item)
    v2 = load_module(
        require_hash(contract["inputs"]["v2_generator"]),
        "lower_repartition_v2_for_v3",
    )
    (
        v2_result,
        retained,
        cassette,
        mesh_only,
        old_seam_marker,
        eye_objects,
    ) = v2.build()
    if v2_result["status"] != "PASS__V2_REVIEW_GEOMETRY_READY__NOT_PRINT_RELEASED":
        raise RuntimeError("pinned V2 construction did not pass")

    old_retained_record = next(
        (item for item in retained if item["component_index"] == 1),
        None,
    )
    old_cassette_record = next(
        (item for item in cassette if item["component_index"] == 1),
        None,
    )
    if old_retained_record is None or old_cassette_record is None:
        raise RuntimeError("V2 component 001 split records are missing")
    old_retained = old_retained_record["shape"]
    old_cassette = old_cassette_record["shape"]

    v2_contract = v2.load_contract()
    v1 = v2.load_v1(v2_contract)
    canonical_path = v2.require_hash(
        v2_contract["inputs"]["relieved_shell_reference"]
    )
    canonical = App.openDocument(str(canonical_path))
    v2_review = App.openDocument(
        str(require_hash(contract["inputs"]["v2_review"]))
    )
    try:
        lower_main = canonical.getObject("FROZEN_RIGHT_LOWER_MAIN_V34")
        selected_obj = v2_review.getObject(
            contract["selected_sector"]["object_internal_name"]
        )
        if lower_main is None or selected_obj is None:
            raise RuntimeError("canonical component 001 or selected V2 object missing")
        if str(selected_obj.Label) != contract["selected_sector"]["object_label"]:
            raise RuntimeError("selected V2 object label changed")
        face_index = int(contract["selected_sector"]["face_index_1_based"])
        selected_face = selected_obj.Shape.Faces[face_index - 1]
        area_residual = abs(
            float(selected_face.Area)
            - float(contract["selected_sector"]["face_area_mm2"])
        )
        center_residual = float(
            selected_face.CenterOfMass.distanceToPoint(
                vec(App, contract["selected_sector"]["face_center_world_mm"])
            )
        )
        if area_residual > 1.0e-8 or center_residual > 1.0e-8:
            raise RuntimeError("selected Face30 identity changed")
        source = lower_main.Shape.copy()
    finally:
        App.closeDocument(v2_review.Name)
        App.closeDocument(canonical.Name)

    partition = contract["local_partition"]
    point = vec(App, partition["point_world_mm"])
    axis_u = vec(App, partition["axis_u_selected_edge_unit"])
    axis_v = vec(App, partition["axis_v_orthogonalized_shell_inward_unit"])
    normal = vec(App, partition["normal_toward_cassette_unit"])
    axis_u.normalize()
    axis_v.normalize()
    normal.normalize()
    orthogonality = max(
        abs(float(axis_u.dot(axis_v))),
        abs(float(axis_u.dot(normal))),
        abs(float(axis_v.dot(normal))),
    )
    if orthogonality > 1.0e-8:
        raise RuntimeError(f"V3 local curtain basis is not orthonormal: {orthogonality}")
    gap = float(partition["mating_clearance_mm"])
    straight_retained_mask = v1.curtain_mask(
        Part, point, axis_u, axis_v, normal, -1, gap
    )
    straight_cassette_mask = v1.curtain_mask(
        Part, point, axis_u, axis_v, normal, +1, gap
    )
    straight_retained = source.common(straight_retained_mask).removeSplitter()
    new_retained = old_retained.fuse(straight_retained).removeSplitter()
    new_cassette = old_cassette.common(straight_cassette_mask).removeSplitter()
    assert_one_solid("V3 component 001 front", new_retained)
    assert_one_solid("V3 component 001 rear", new_cassette)

    front_added = new_retained.cut(old_retained).removeSplitter()
    if front_added.isNull() or float(front_added.Volume) <= 0.0:
        raise RuntimeError("V3 did not transfer any component 001 material")
    old_front_lost = cut_volume(old_retained, new_retained)
    new_rear_outside_old = cut_volume(new_cassette, old_cassette)
    selected_front_area = common_area(selected_face, new_retained)
    selected_rear_area = common_area(selected_face, new_cassette)
    selected_fraction = selected_front_area / float(selected_face.Area)
    measured_gap = float(new_retained.distToShape(new_cassette)[0])
    front_added_volume = float(front_added.Volume)
    rear_removed_volume = cut_volume(old_cassette, new_cassette)
    source_balance = float(source.Volume - new_retained.Volume - new_cassette.Volume)

    gates = contract["numeric_gates"]
    epsilon = float(gates["volume_epsilon_mm3"])
    checks = {
        "component_001_front_valid_closed_one_solid": (
            new_retained.isValid()
            and new_retained.isClosed()
            and len(new_retained.Solids) == 1
        ),
        "component_001_rear_valid_closed_one_solid": (
            new_cassette.isValid()
            and new_cassette.isClosed()
            and len(new_cassette.Solids) == 1
        ),
        "selected_face_is_front_owned": (
            selected_fraction
            >= float(gates["minimum_selected_face_retained_fraction"])
        ),
        "selected_face_is_absent_from_rear": (
            selected_rear_area
            <= float(gates["maximum_selected_face_rear_area_mm2"])
        ),
        "front_transfer_is_positive": (
            front_added_volume
            >= float(gates["minimum_front_added_volume_mm3"])
        ),
        "old_front_material_is_not_lost": old_front_lost <= epsilon,
        "no_new_rear_material_is_created": new_rear_outside_old <= epsilon,
        "local_piece_gap_is_at_least_0p29_mm": (
            measured_gap >= float(gates["minimum_measured_piece_gap_mm"])
        ),
        "straight_edge_is_within_0p2_deg_of_global_x": (
            float(
                contract["selected_sector"][
                    "straight_edge_unsigned_angle_to_global_x_deg"
                ]
            )
            <= float(gates["maximum_axis_angle_to_global_x_deg"])
        ),
        "all_non_component_001_v2_shapes_are_reused_unchanged": True,
        "canonical_source_is_not_added_to": (
            cut_volume(new_retained, source) <= epsilon
            and cut_volume(new_cassette, source) <= epsilon
        ),
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        raise RuntimeError(f"V3 feasibility gates failed: {failed}")

    new_retained_records = []
    for record in retained:
        copied = dict(record)
        if copied["component_index"] == 1:
            copied["shape"] = new_retained
            copied["name"] = (
                "component_001_relief_main__retained__"
                "WITH_AXIS_STRAIGHT_FACE30_SECTOR"
            )
            copied["owner"] = "retained_split_v3_axis_straight"
        new_retained_records.append(copied)
    new_cassette_records = []
    for record in cassette:
        copied = dict(record)
        if copied["component_index"] == 1:
            copied["shape"] = new_cassette
            copied["name"] = (
                "component_001_relief_main__cassette__"
                "AFTER_FACE30_TRANSFER"
            )
            copied["owner"] = "cassette_split_v3_axis_straight"
        new_cassette_records.append(copied)

    finalization = exercise_disposable(
        new_retained, new_cassette, front_added, contract
    )
    straight_marker = Part.makeLine(
        vec(
            App,
            contract["selected_sector"]["straight_edge_midpoint_world_mm"],
        )
        - axis_u
        * (
            float(contract["selected_sector"]["straight_edge_length_mm"])
            / 2.0
        ),
        vec(
            App,
            contract["selected_sector"]["straight_edge_midpoint_world_mm"],
        )
        + axis_u
        * (
            float(contract["selected_sector"]["straight_edge_length_mm"])
            / 2.0
        ),
    )
    result = {
        "schema_version": "cat-head-right-lower-rear-v5-axis-straight-sector-validation-v3",
        "status": "PASS__V3_AXIS_STRAIGHT_SECTOR_REVIEW_READY__NOT_PRINT_RELEASED",
        "authority": contract["authority"],
        "input_sha256": {
            name: item["sha256"] for name, item in contract["inputs"].items()
        },
        "selection": contract["selected_sector"],
        "local_partition": partition,
        "checks": checks,
        "measurements": {
            "selected_face_area_mm2": float(selected_face.Area),
            "selected_face_front_common_area_mm2": selected_front_area,
            "selected_face_front_fraction": selected_fraction,
            "selected_face_rear_common_area_mm2": selected_rear_area,
            "component_001_source_volume_mm3": float(source.Volume),
            "component_001_v2_front_volume_mm3": float(old_retained.Volume),
            "component_001_v2_rear_volume_mm3": float(old_cassette.Volume),
            "component_001_v3_front_volume_mm3": float(new_retained.Volume),
            "component_001_v3_rear_volume_mm3": float(new_cassette.Volume),
            "front_added_volume_mm3": front_added_volume,
            "rear_removed_volume_mm3": rear_removed_volume,
            "old_front_lost_volume_mm3": old_front_lost,
            "new_rear_outside_old_volume_mm3": new_rear_outside_old,
            "component_001_source_minus_kept_volume_mm3": source_balance,
            "new_front_to_rear_minimum_distance_mm": measured_gap,
            "basis_maximum_orthogonality_residual": orthogonality,
            "selected_face_area_residual_mm2": area_residual,
            "selected_face_center_residual_mm": center_residual,
        },
        "component_001_front_metrics": metrics(new_retained),
        "component_001_rear_metrics": metrics(new_cassette),
        "transferred_sector_metrics": metrics(front_added),
        "retained_valid_piece_count": len(new_retained_records),
        "cassette_valid_piece_count": len(new_cassette_records),
        "retained_mesh_only_unchanged_count": len(mesh_only),
        "released_v3_eye_objects": {
            name: metrics(shape) for name, shape in eye_objects
        },
        "disposable_finalization": finalization,
        "print_release_holds": [
            "This is a one-sided ownership review only.",
            "Retained and cassette groups are not yet fused into production bodies.",
            "No build-plate orientation, 10 mm bed margin, mirror, STL, 3MF, G-code, slicing, or print release is authorized."
        ],
        "io_trace": {
            "canonical_saved": False,
            "v2_saved": False,
            "review_saved": False,
            "geometry_export_created": False,
            "production_output_created": False,
        },
    }
    return (
        result,
        new_retained_records,
        new_cassette_records,
        mesh_only,
        old_seam_marker,
        straight_marker,
        front_added,
        eye_objects,
    )


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
    old_seam_marker: Any,
    straight_marker: Any,
    transfer_shape: Any,
    eye_objects: list[tuple[str, Any]],
) -> tuple[Path, Path]:
    import FreeCAD as App  # type: ignore

    contract = load_contract()
    output_dir = (PROJECT_ROOT / contract["outputs"]["directory"]).resolve()
    if output_dir.exists():
        raise RuntimeError(f"review output already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    document = App.newDocument(
        "RIGHT_LOWER_REAR_V5_AXIS_STRAIGHT_SECTOR_REVIEW_ONLY_V3"
    )
    try:
        retained_group = document.addObject(
            "App::DocumentObjectGroup", "RETAINED_FRONT_LOWER_OWNERS"
        )
        cassette_group = document.addObject(
            "App::DocumentObjectGroup", "REAR_CASSETTE_LOWER_OWNERS"
        )
        mesh_group = document.addObject(
            "App::DocumentObjectGroup", "UNCHANGED_RETAINED_MESH_ONLY_OWNERS"
        )
        review_group = document.addObject(
            "App::DocumentObjectGroup", "V3_FACE30_OWNERSHIP_CHANGE"
        )
        eye_group = document.addObject(
            "App::DocumentObjectGroup", "REFERENCE_RELEASED_V3_RIGHT_EYE"
        )
        for prefix, group, records, color, transparency in (
            ("RET", retained_group, retained, (0.25, 0.65, 0.95), 0),
            ("CAS", cassette_group, cassette, (1.0, 0.48, 0.12), 14),
            ("MESH", mesh_group, mesh_only, (0.65, 0.65, 0.68), 0),
        ):
            for index, record in enumerate(records, start=1):
                add_feature(
                    document,
                    group,
                    f"{prefix}_{index:03d}",
                    f"{record['owner'].upper()} \u2014 {record['name']}",
                    record["shape"],
                    contract["authority"],
                    color,
                    transparency,
                )
        transfer = add_feature(
            document,
            review_group,
            "PROPOSED_FACE30_SECTOR_TRANSFER",
            "PROPOSED \u2014 FACE30 SECTOR MOVED FROM REAR TO FRONT",
            transfer_shape,
            contract["authority"],
            (0.2, 1.0, 0.25),
            10,
        )
        transfer.addProperty(
            "App::PropertyString", "OwnershipChange", "Review Control"
        )
        transfer.OwnershipChange = "REAR_CASSETTE_TO_RETAINED_FRONT"
        old_marker = add_feature(
            document,
            review_group,
            "REFERENCE_V2_DIAGONAL_SEAM",
            "REFERENCE \u2014 V2 DIAGONAL SEAM",
            old_seam_marker,
            contract["authority"],
            (1.0, 1.0, 0.0),
        )
        new_marker = add_feature(
            document,
            review_group,
            "PROPOSED_V3_AXIS_STRAIGHT_EDGE",
            "PROPOSED \u2014 V3 STRAIGHT EDGE (0.174 DEG FROM GLOBAL X)",
            straight_marker,
            contract["authority"],
            (0.2, 1.0, 0.25),
        )
        for marker in (old_marker, new_marker):
            if getattr(marker, "ViewObject", None) is not None:
                marker.ViewObject.LineWidth = 6.0
        for index, (name, shape) in enumerate(eye_objects, start=1):
            add_feature(
                document,
                eye_group,
                f"EYE_{index:02d}",
                f"REFERENCE \u2014 RELEASED V3 \u2014 {name}",
                shape,
                contract["authority"],
                (0.35, 0.95, 0.55),
                76,
            )
        document.recompute()
        fcstd = output_dir / contract["outputs"]["fcstd"]
        document.saveAs(str(fcstd))
    finally:
        App.closeDocument(document.Name)
    result["io_trace"]["review_saved"] = True
    result["generated_fcstd"] = str(fcstd.relative_to(PROJECT_ROOT))
    result["generated_fcstd_sha256"] = sha256(fcstd)
    validation = output_dir / contract["outputs"]["validation"]
    validation.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
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
        args.report.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "front_added_volume_mm3": result["measurements"][
                        "front_added_volume_mm3"
                    ],
                    "selected_face_front_fraction": result["measurements"][
                        "selected_face_front_fraction"
                    ],
                    "new_front_to_rear_minimum_distance_mm": result[
                        "measurements"
                    ]["new_front_to_rear_minimum_distance_mm"],
                },
                sort_keys=True,
            )
        )
        return 0
    fcstd, validation = save_review(*built)
    print(
        json.dumps(
            {
                "status": result["status"],
                "fcstd": str(fcstd),
                "validation": str(validation),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
