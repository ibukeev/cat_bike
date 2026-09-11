#!/usr/bin/env python3
"""Read-only ownership inventory for the approved bilateral cleanup feedback.

This tool reconstructs pinned predecessor geometry, reports exact BRep feature
ownership, and writes JSON only under /tmp. It never saves a CAD document or
exports geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def project_path(value: str) -> Path:
    return (PROJECT_ROOT / value).resolve()


def bbox(shape: Any) -> dict[str, list[float]]:
    box = shape.BoundBox
    return {
        "minimum_mm": [float(box.XMin), float(box.YMin), float(box.ZMin)],
        "maximum_mm": [float(box.XMax), float(box.YMax), float(box.ZMax)],
        "lengths_mm": [float(box.XLength), float(box.YLength), float(box.ZLength)],
    }


def metrics(shape: Any) -> dict[str, Any]:
    return {
        "shape_type": str(shape.ShapeType),
        "solid_count": len(shape.Solids),
        "face_count": len(shape.Faces),
        "edge_count": len(shape.Edges),
        "volume_mm3": float(shape.Volume),
        "area_mm2": float(shape.Area),
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "bbox": bbox(shape),
    }


def common_volume(left: Any, right: Any) -> float:
    common = left.common(right)
    return 0.0 if common.isNull() else max(0.0, float(common.Volume))


def face_record(face: Any, index: int) -> dict[str, Any]:
    record: dict[str, Any] = {
        "index_1_based": index,
        "area_mm2": float(face.Area),
        "center_mm": [
            float(face.CenterOfMass.x),
            float(face.CenterOfMass.y),
            float(face.CenterOfMass.z),
        ],
        "bbox": bbox(face),
        "surface_type": type(face.Surface).__name__,
    }
    try:
        u0, u1, v0, v1 = map(float, face.ParameterRange)
        normal = face.normalAt((u0 + u1) / 2.0, (v0 + v1) / 2.0)
        normal.normalize()
        record["normal"] = [float(normal.x), float(normal.y), float(normal.z)]
    except Exception:
        record["normal"] = None
    return record


def feature_record(shape: Any, small_limit: int = 24) -> dict[str, Any]:
    faces = [face_record(face, index) for index, face in enumerate(shape.Faces, 1)]
    by_area = sorted(faces, key=lambda item: item["area_mm2"])
    edges = sorted(float(edge.Length) for edge in shape.Edges)
    return {
        "metrics": metrics(shape),
        "smallest_faces": by_area[:small_limit],
        "largest_faces": list(reversed(by_area[-12:])),
        "smallest_edge_lengths_mm": edges[:32],
    }


def nearest_face_records(shape: Any, point: Any, limit: int = 16) -> list[dict[str, Any]]:
    records = []
    for index, face in enumerate(shape.Faces, 1):
        item = face_record(face, index)
        vertex = face.Vertexes[0] if face.Vertexes else None
        try:
            distance = float(face.distToShape(point)[0])
        except Exception:
            distance = (
                float(vertex.Point.distanceToPoint(point.Point))
                if vertex is not None else float("inf")
            )
        item["distance_to_feedback_point_mm"] = distance
        records.append(item)
    return sorted(records, key=lambda item: item["distance_to_feedback_point_mm"])[:limit]


def all_face_records(shape: Any) -> list[dict[str, Any]]:
    return [face_record(face, index) for index, face in enumerate(shape.Faces, 1)]


def verify_contract_inputs(contract_path: Path) -> dict[str, Any]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    for name, item in contract.get("inputs", {}).items():
        if "path_from_repo_root" in item:
            continue
        path = project_path(str(item["path"]))
        actual = sha256(path)
        if actual != str(item["sha256"]):
            raise RuntimeError(f"input hash mismatch: {name}: {actual}")
    return contract


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = args.report.resolve()
    if not str(report).startswith("/tmp/") or report.exists():
        raise RuntimeError("report must be a fresh /tmp path")

    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    v1_dir = HERE.parent / "lower-front-bilateral-modular-closure-review-v1"
    v1_contract = verify_contract_inputs(v1_dir / "contract.json")
    v5_path = project_path(v1_contract["inputs"]["v5_generator"]["path"])
    if sha256(v5_path) != v1_contract["inputs"]["v5_generator"]["sha256"]:
        raise RuntimeError("V1-pinned V5 generator hash mismatch")
    v5 = load_module(v5_path, "feedback_inventory_v5")
    v5_result, v5_shapes = v5.build()
    if not str(v5_result.get("status", "")).startswith("PASS__"):
        raise RuntimeError("pinned V5 reconstruction did not pass")

    v5_contract = v5.load_contract()
    v4_contract_path = project_path(v5_contract["inputs"]["v4_contract"]["path"])
    v4_contract = verify_contract_inputs(v4_contract_path)
    v3_path = project_path(v4_contract["inputs"]["v3_generator"]["path"])
    if sha256(v3_path) != v4_contract["inputs"]["v3_generator"]["sha256"]:
        raise RuntimeError("V4-pinned V3 generator hash mismatch")
    v3 = load_module(v3_path, "feedback_inventory_v3")
    v3_built = v3.build()
    new_component_001 = next(
        item["shape"] for item in v3_built[1]
        if int(item["component_index"]) == 1
    )
    front_added = v3_built[6]

    v3_contract = v3.load_contract()
    v2_path = project_path(v3_contract["inputs"]["v2_generator"]["path"])
    if sha256(v2_path) != v3_contract["inputs"]["v2_generator"]["sha256"]:
        raise RuntimeError("V3-pinned V2 generator hash mismatch")
    v2 = load_module(v2_path, "feedback_inventory_v2")
    v2_contract = v2.load_contract()
    canonical_path = v2.require_hash(v2_contract["inputs"]["relieved_shell_reference"])
    v8_path = v2.require_hash(v2_contract["inputs"]["user_manual_v8_reference"])
    eye_path = v2.require_hash(v2_contract["inputs"]["released_v3_right_eye"])
    v1_review_path = project_path(
        "output/70-freecad-pilots/review-only/"
        "lower-front-bilateral-modular-closure-review-v1/"
        "LOWER_FRONT_BILATERAL_MODULAR_CLOSURE_REVIEW_ONLY_V1.FCStd"
    )
    if sha256(v1_review_path) != "4130bdd05fc75e7d258c39c6adb99afe58d716c7005de2e6c1b63e41131605d6":
        raise RuntimeError("V1 review hash mismatch")

    canonical = App.openDocument(str(canonical_path))
    manual = App.openDocument(str(v8_path))
    eye = App.openDocument(str(eye_path))
    v1_review = App.openDocument(str(v1_review_path))
    try:
        lower_mesh = canonical.getObject("FROZEN_RIGHT_LOWER_COMPONENTS_002_060_V34")
        if lower_mesh is None:
            raise RuntimeError("canonical lower component mesh missing")
        converted = Part.Shape()
        converted.makeShapeFromMesh(lower_mesh.Mesh.Topology, 0.01)
        raw = {
            index: Part.makeSolid(shell).removeSplitter()
            for index, shell in enumerate(converted.Shells, start=2)
        }
        for index in (7, 14, 21):
            if index not in raw:
                raise RuntimeError(f"canonical component {index:03d} missing")

        retained = {
            int(item["component_index"]): item["shape"]
            for item in v5_shapes["retained"]
        }
        manual_shapes = {
            str(obj.Label): obj.Shape.copy()
            for obj in manual.Objects
            if hasattr(obj, "Shape") and not obj.Shape.isNull()
        }
        eye_shapes = {
            str(obj.Name): obj.Shape.copy()
            for obj in eye.Objects
            if hasattr(obj, "Shape") and not obj.Shape.isNull()
        }
        head_manual = manual_shapes.get("HEAD_BOTTOM_FLANGE")
        if head_manual is None:
            raise RuntimeError("HEAD_BOTTOM_FLANGE missing from pinned V8")
        component_007_manual_addition = retained[7].cut(raw[7]).removeSplitter()
        manual_legacy_common = head_manual.common(raw[7]).removeSplitter()
        legacy_shell_common = raw[7].common(retained[1]).removeSplitter()
        root_union_box = manual_legacy_common.BoundBox
        root_union_box.add(legacy_shell_common.BoundBox)
        manual_root_trials = []
        for margin in (0.0, 0.10, 0.25, 0.50, 1.0):
            root_box = Part.makeBox(
                float(root_union_box.XLength) + 2.0 * margin,
                float(root_union_box.YLength) + 2.0 * margin,
                float(root_union_box.ZLength) + 2.0 * margin,
                App.Vector(
                    float(root_union_box.XMin) - margin,
                    float(root_union_box.YMin) - margin,
                    float(root_union_box.ZMin) - margin,
                ),
            )
            root = raw[7].common(root_box).removeSplitter()
            finished = head_manual.fuse(root).removeSplitter()
            visible = root.cut(
                head_manual.fuse(retained[1]).removeSplitter()
            ).removeSplitter()
            manual_root_trials.append({
                "bbox_margin_mm": margin,
                "root_metrics": metrics(root),
                "finished_metrics": metrics(finished),
                "manual_common_mm3": common_volume(root, head_manual),
                "shell_common_mm3": common_volume(root, retained[1]),
                "root_outside_manual_and_shell_mm3": (
                    0.0 if visible.isNull() else float(visible.Volume)
                ),
            })
        manual_attachment_records = []
        canonical_007_attachment_records = []
        for index, other in sorted(retained.items()):
            if index == 7:
                continue
            manual_common = common_volume(head_manual, other)
            manual_distance = float(head_manual.distToShape(other)[0])
            if manual_common > 0.0 or manual_distance <= 3.0:
                manual_attachment_records.append({
                    "component_index": index,
                    "distance_mm": manual_distance,
                    "common_mm3": manual_common,
                })
            canonical_common = common_volume(raw[7], other)
            canonical_distance = float(raw[7].distToShape(other)[0])
            if canonical_common > 0.0 or canonical_distance <= 3.0:
                canonical_007_attachment_records.append({
                    "component_index": index,
                    "distance_mm": canonical_distance,
                    "common_mm3": canonical_common,
                })
        feedback_point = Part.Vertex(App.Vector(36.86, 178.52, 32.46))
        component_014_neighbors = []
        for index, other in sorted(raw.items()):
            if index == 14:
                continue
            distance = float(raw[14].distToShape(other)[0])
            common = common_volume(raw[14], other)
            if distance <= 3.0 or common > 0.0:
                component_014_neighbors.append({
                    "component_index": index,
                    "distance_mm": distance,
                    "common_mm3": common,
                })
        component_021_neighbors = []
        for index, other in sorted(raw.items()):
            if index == 21:
                continue
            common = raw[21].common(other)
            volume = 0.0 if common.isNull() else max(0.0, float(common.Volume))
            distance = float(raw[21].distToShape(other)[0])
            if distance <= 3.0 or volume > 0.0:
                component_021_neighbors.append({
                    "component_index": index,
                    "distance_mm": distance,
                    "common_mm3": volume,
                    "common_bbox": None if common.isNull() else bbox(common),
                })
        fin_trim_trials = []
        for x_min in (70.0, 75.0, 80.0, 85.0):
            cutter = Part.makeBox(
                25.0, 45.0, 25.0, App.Vector(x_min, 150.0, 30.0)
            )
            trimmed = new_component_001.cut(cutter).removeSplitter()
            fin_trim_trials.append({
                "outboard_x_min_mm": x_min,
                "component_volume_removed_mm3": (
                    float(new_component_001.Volume) - float(trimmed.Volume)
                ),
                "transfer_volume_removed_mm3": common_volume(front_added, cutter),
                "result_valid_closed_one_solid": (
                    trimmed.isValid() and trimmed.isClosed()
                    and len(trimmed.Solids) == 1
                ),
            })
        nose_trim_trials = []
        nose_box = raw[21].BoundBox
        z_min = float(nose_box.ZMin)
        z_max = float(nose_box.ZMax)
        z_mid = (z_min + z_max) / 2.0
        half_length = (z_max - z_min) / 4.0
        for name, keep_min, keep_max in (
            ("lower_half", z_min, z_mid),
            ("center_half", z_mid - half_length, z_mid + half_length),
            ("upper_half", z_mid, z_max),
        ):
            keep = Part.makeBox(
                float(nose_box.XLength) + 2.0,
                float(nose_box.YLength) + 2.0,
                keep_max - keep_min,
                App.Vector(float(nose_box.XMin) - 1.0,
                           float(nose_box.YMin) - 1.0, keep_min),
            )
            trimmed = raw[21].common(keep).removeSplitter()
            nose_trim_trials.append({
                "name": name,
                "keep_z_min_mm": keep_min,
                "keep_z_max_mm": keep_max,
                "metrics": metrics(trimmed),
                "component_002_root_common_mm3": common_volume(trimmed, raw[2]),
                "component_003_common_mm3": common_volume(trimmed, raw[3]),
            })
        v1_component_001 = []
        for obj in v1_review.Objects:
            label = str(getattr(obj, "Label", ""))
            if (
                "RIGHT LOWER" in label
                and "component_001" in label
                and hasattr(obj, "Shape")
                and not obj.Shape.isNull()
            ):
                v1_component_001.append({
                    "name": str(obj.Name),
                    "label": label,
                    "metrics": metrics(obj.Shape),
                    "face_6": (
                        face_record(obj.Shape.Faces[5], 6)
                        if len(obj.Shape.Faces) >= 6 else None
                    ),
                    "nearest_faces_to_feedback_point": nearest_face_records(
                        obj.Shape, feedback_point
                    ),
                })

        frame = v5_contract["seam_frame"]
        origin = App.Vector(*map(float, frame["origin_world_mm"]))
        axis_u = App.Vector(*map(float, frame["axis_u"]))
        axis_u.normalize()
        axis_v = App.Vector(*map(float, frame["axis_v_shell_inward"]))
        axis_v.normalize()
        axis_n = App.Vector(*map(float, frame["axis_n_toward_rear"]))
        axis_n.normalize()
        slope = float(frame["surface_v_per_n"])
        cross_per_n = axis_n + axis_v * slope
        inward = axis_v - axis_n * slope
        inward.normalize()
        rear_001 = next(
            item["shape"] for item in v5_shapes["cassette"]
            if int(item["component_index"]) == 1
        )
        candidate_stations = []
        existing = [float(value) for value in v5_contract["fasteners"]["station_u_mm"]]
        station_n = float(v5_contract["fasteners"]["station_n_mm"])
        for station_u in (28.0, 30.0, 32.0, 36.0, 40.0, 42.0, 44.0, 46.0):
            center = origin + axis_u * station_u + cross_per_n * station_n
            intersections = v5.line_intersections_along_axis(
                Part, rear_001, center, inward
            )
            bore = Part.makeCylinder(1.7, 18.0, center - inward * 5.0, inward)
            corridor = Part.makeCylinder(4.0, 12.0, center - inward * 18.0, inward)
            retained_contacts = v5.per_record_common(
                corridor, v5_shapes["retained"]
            )
            cassette_contacts = v5.per_record_common(
                corridor, v5_shapes["cassette"]
            )
            candidate_stations.append({
                "u_mm": station_u,
                "nearest_existing_station_mm": min(
                    abs(station_u - value) for value in existing
                ),
                "center_world_mm": [
                    float(center.x), float(center.y), float(center.z)
                ],
                "rear_axis_intersections_inward_mm": intersections,
                "rear_bore_common_mm3": common_volume(rear_001, bore),
                "driver_retained_common_mm3": sum(
                    item["common_mm3"] for item in retained_contacts
                ),
                "driver_cassette_common_mm3": sum(
                    item["common_mm3"] for item in cassette_contacts
                ),
                "driver_contacts": [
                    item for item in retained_contacts + cassette_contacts
                    if item["common_mm3"] > 1.0e-7
                ],
            })

        output = {
            "schema_version": "cat-head-lower-front-feedback-inventory-v2",
            "status": "PASS__READ_ONLY_FEEDBACK_INVENTORY",
            "pins": {
                "v1_contract": sha256(v1_dir / "contract.json"),
                "v5_generator": sha256(v5_path),
                "v3_generator": sha256(v3_path),
                "v2_generator": sha256(v2_path),
                "canonical": sha256(canonical_path),
                "manual_v8": sha256(v8_path),
                "released_right_eye": sha256(eye_path),
            },
            "face30_transfer": {
                **feature_record(front_added),
                "feedback_point_world_mm": [36.86, 178.52, 32.46],
                "feedback_point_distance_to_transfer_mm": float(
                    feedback_point.distToShape(front_added)[0]
                ),
                "nearest_transfer_faces": nearest_face_records(
                    front_added, feedback_point
                ),
                "nearest_finished_component_faces": nearest_face_records(
                    new_component_001, feedback_point
                ),
                "finished_component_metrics": metrics(new_component_001),
                "outboard_trim_trials": fin_trim_trials,
            },
            "component_007": {
                "canonical_before_manual": feature_record(raw[7]),
                "v5_after_manual": feature_record(retained[7]),
                "manual_head_flange": feature_record(head_manual),
                "manual_addition_beyond_canonical": feature_record(
                    component_007_manual_addition
                ),
                "canonical_manual_common_mm3": common_volume(raw[7], head_manual),
                "manual_addition_volume_mm3": float(
                    component_007_manual_addition.Volume
                ),
                "manual_legacy_common": feature_record(manual_legacy_common),
                "legacy_shell_common": feature_record(legacy_shell_common),
                "manual_common_to_shell_common_distance_mm": float(
                    manual_legacy_common.distToShape(legacy_shell_common)[0]
                ),
                "bounded_hidden_root_trials": manual_root_trials,
                "manual_attachment_records_excluding_component_007":
                    manual_attachment_records,
                "canonical_attachment_records_excluding_component_007":
                    canonical_007_attachment_records,
            },
            "component_014": {
                **feature_record(raw[14]),
                "nearby_or_intersecting_owner_records": component_014_neighbors,
            },
            "component_021": {
                **feature_record(raw[21]),
                "all_faces": all_face_records(raw[21]),
                "nearby_or_intersecting_owner_records": component_021_neighbors,
                "half_length_trim_trials": nose_trim_trials,
            },
            "v1_saved_component_001": v1_component_001,
            "manual_v8_objects": {
                name: metrics(shape) for name, shape in manual_shapes.items()
            },
            "released_eye_objects": {
                name: metrics(shape) for name, shape in eye_shapes.items()
            },
            "ledge": {
                "proposal": feature_record(v5_shapes["proposal"]),
                "origin_world_mm": frame["origin_world_mm"],
                "axis_u": frame["axis_u"],
                "inward": [float(inward.x), float(inward.y), float(inward.z)],
                "existing_station_u_mm": existing,
                "candidate_outboard_stations": candidate_stations,
            },
            "io_trace": {
                "source_saved": False,
                "review_saved": False,
                "geometry_export_created": False,
                "production_output_created": False,
            },
        }
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            json.dumps(output, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({
            "status": output["status"],
            "face30_transfer_volume_mm3": float(front_added.Volume),
            "manual_v8_object_labels": sorted(manual_shapes),
            "candidate_outboard_station_count": len(candidate_stations),
        }, sort_keys=True))
    finally:
        App.closeDocument(v1_review.Name)
        App.closeDocument(eye.Name)
        App.closeDocument(manual.Name)
        App.closeDocument(canonical.Name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
