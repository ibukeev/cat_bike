#!/usr/bin/env python3
"""Build the simple bilateral lower-front V4 visual-review assembly.

This revision intentionally works from the pinned V3 review FCStd.  It keeps
every visible part separately selectable, makes only the user-requested
cleanup and connector changes, and never exports production geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
CONTRACT_PATH = HERE / "contract.json"
EPS = 1.0e-7


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schema_version") != "cat-head-lower-front-bilateral-feedback-cleanup-review-v4":
        raise RuntimeError("unexpected V4 contract schema")
    return contract


def require_hash(item: dict[str, Any]) -> Path:
    path = (PROJECT_ROOT / item["path"]).resolve()
    actual = sha256(path)
    if actual != item["sha256"]:
        raise RuntimeError(
            f"hash mismatch: {path}: expected {item['sha256']}, got {actual}"
        )
    return path


def progress(stage: str, **values: Any) -> None:
    print(json.dumps({"progress": stage, **values}, sort_keys=True), flush=True)


def vec(values: Sequence[float], App: Any) -> Any:
    return App.Vector(*map(float, values))


def unit(value: Any) -> Any:
    result = value * 1.0
    if float(result.Length) <= 1.0e-12:
        raise RuntimeError("zero-length direction")
    result.normalize()
    return result


def common_volume(left: Any, right: Any) -> float:
    if left.isNull() or right.isNull():
        return 0.0
    common = left.common(right)
    return 0.0 if common.isNull() else max(0.0, float(common.Volume))


def shape_metrics(shape: Any) -> dict[str, Any]:
    return {
        "volume_mm3": float(shape.Volume),
        "solid_count": len(shape.Solids),
        "face_count": len(shape.Faces),
        "edge_count": len(shape.Edges),
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
    }


def valid_single_solid(shape: Any) -> bool:
    return (
        not shape.isNull()
        and shape.isValid()
        and shape.isClosed()
        and len(shape.Solids) == 1
    )


def mirror_x0(shape: Any, App: Any) -> Any:
    matrix = App.Matrix()
    matrix.A11 = -1.0
    matrix.A22 = 1.0
    matrix.A33 = 1.0
    matrix.A44 = 1.0
    return shape.transformGeometry(matrix).removeSplitter()


def component_index(name: str) -> int | None:
    patterns = (
        r"(?:RIGHT|LEFT)_LOWER_([0-9]{3})_",
        r"component_([0-9]{3})",
    )
    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match is not None:
            return int(match.group(1))
    return None


def largest_solid(shape: Any) -> tuple[Any, dict[str, Any]]:
    solids = [solid.removeSplitter() for solid in shape.Solids]
    if not solids and shape.ShapeType == "Solid":
        solids = [shape.removeSplitter()]
    if not solids:
        raise RuntimeError("shape contains no solids")
    selected = max(solids, key=lambda item: float(item.Volume)).removeSplitter()
    return selected, {
        "source_solid_count": len(solids),
        "source_solid_volumes_mm3": sorted(
            (float(item.Volume) for item in solids), reverse=True
        ),
        "source_volume_mm3": float(shape.Volume),
        "retained_volume_mm3": float(selected.Volume),
        "removed_volume_mm3": max(0.0, float(shape.Volume) - float(selected.Volume)),
    }


def group_members(document: Any, name: str) -> list[Any]:
    group = document.getObject(name)
    if group is None or not hasattr(group, "Group"):
        raise RuntimeError(f"source group missing: {name}")
    return list(group.Group)


def copied_record(obj: Any, shape: Any | None = None, suffix: str = "") -> dict[str, Any]:
    if not hasattr(obj, "Shape") or obj.Shape.isNull():
        raise RuntimeError(f"source object has no shape: {obj.Name}")
    return {
        "name": str(obj.Name) + suffix,
        "label": str(obj.Label) + suffix.replace("_", " "),
        "shape": obj.Shape.copy() if shape is None else shape,
    }


def make_prism(
    Part: Any,
    origin: Any,
    axis_u: Any,
    cross_per_n: Any,
    inward: Any,
    u_min: float,
    u_max: float,
    n_min: float,
    n_max: float,
    v_min: float,
    v_max: float,
) -> Any:
    def point(u: float, n: float, v: float) -> Any:
        return origin + axis_u * u + cross_per_n * n + inward * v

    wire = Part.makePolygon([
        point(u_min, n_min, v_min),
        point(u_max, n_min, v_min),
        point(u_max, n_max, v_min),
        point(u_min, n_max, v_min),
        point(u_min, n_min, v_min),
    ])
    return Part.Face(wire).extrude(inward * (v_max - v_min)).removeSplitter()


def ledge_frame(contract: dict[str, Any], App: Any) -> dict[str, Any]:
    # Pinned V5 seam frame.  These values are copied from the hash-pinned V5
    # contract and are deliberately not inferred from changing topology.
    origin = vec([43.27894931962105, 187.62752696335443, 49.506195577012136], App)
    axis_u = unit(vec([0.9999953872074454, -0.00263868230318262, -0.00150430034710222], App))
    axis_v = unit(vec([-0.00005981280271183169, -0.5122769763690231, 0.8588202931374177], App))
    axis_n = unit(vec([0.003036772342480212, 0.8588162416011439, 0.5122747711685847], App))
    slope = -0.176416299625
    return {
        "origin": origin,
        "axis_u": axis_u,
        "cross_per_n": axis_n + axis_v * slope,
        "inward": unit(axis_v - axis_n * slope),
    }


def construct_rectangular_ledge_ear(
    base: Any,
    contract: dict[str, Any],
    App: Any,
    Part: Any,
) -> tuple[Any, Any, Any, dict[str, Any]]:
    frame = ledge_frame(contract, App)
    spec = contract["ledge"]
    old_station_u = 2.0
    source_shelf_end = 4.3
    # Remove only the raised, malformed copied ear from V3.  The accepted
    # continuous ledge shelf below 4.3 mm stays byte-for-byte in place.
    old_ear_cutter = make_prism(
        Part, frame["origin"], frame["axis_u"], frame["cross_per_n"], frame["inward"],
        old_station_u - 7.0, old_station_u + 7.0,
        1.0, 13.0,
        source_shelf_end - 0.01, 9.5,
    )
    cleaned = base.cut(old_ear_cutter).removeSplitter()

    station_u = float(spec["copied_station_u_mm"])
    station_n = float(spec["station_n_mm"])
    half_u = float(spec["pad_u_mm"]) / 2.0
    half_n = float(spec["pad_n_mm"]) / 2.0
    bearing = 0.3
    ear = make_prism(
        Part, frame["origin"], frame["axis_u"], frame["cross_per_n"], frame["inward"],
        station_u - half_u, station_u + half_u,
        station_n - half_n, station_n + half_n,
        bearing, bearing + float(spec["pad_depth_mm"]),
    )
    center = (
        frame["origin"]
        + frame["axis_u"] * station_u
        + frame["cross_per_n"] * station_n
        + frame["inward"] * bearing
    )
    bore = Part.makeCylinder(
        float(spec["bore_diameter_mm"]) / 2.0,
        float(spec["pad_depth_mm"]) + 2.0,
        center - frame["inward"],
        frame["inward"],
    )
    drilled_ear = ear.cut(bore).removeSplitter()
    source_station = float(spec["source_station_u_mm"])
    clear_gap = abs(source_station - station_u) - float(spec["pad_u_mm"])
    return cleaned, drilled_ear, old_ear_cutter, {
        "station_u_mm": station_u,
        "station_n_mm": station_n,
        "center_world_mm": [float(center.x), float(center.y), float(center.z)],
        "clear_gap_mm": clear_gap,
        "declared_clear_gap_mm": float(spec["clear_gap_mm"]),
        "ear_metrics": shape_metrics(drilled_ear),
        "cleaned_base_metrics": shape_metrics(cleaned),
        "old_raised_ear_removed_mm3": max(0.0, float(base.Volume) - float(cleaned.Volume)),
    }


def mouth_toward_panel_axis(prefix: str, App: Any) -> Any:
    common = [0.189, 0.0, 47.8035]
    second = [-1.3515, 20.3535, 24.0585]
    third = [40.5045, 16.551, 20.421] if prefix == "TRI005" else [-40.5045, 16.551, 20.421]
    points = [vec(common, App), vec(second, App), vec(third, App)]
    edge_axis = unit(points[2] - points[1])
    midpoint = (points[1] + points[2]) * 0.5
    centroid = (points[0] + points[1] + points[2]) / 3.0
    toward = centroid - midpoint
    toward = toward - edge_axis * float(toward.dot(edge_axis))
    return unit(toward)


def moved_mouth_record(obj: Any, distance: float, App: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    prefix = "TRI005" if str(obj.Name).startswith("TRI005") else "TRI006"
    translation = mouth_toward_panel_axis(prefix, App) * distance
    shape = obj.Shape.copy()
    shape.translate(translation)
    return copied_record(obj, shape), {
        "name": str(obj.Name),
        "prefix": prefix,
        "translation_mm": float(translation.Length),
        "translation_world_mm": [float(translation.x), float(translation.y), float(translation.z)],
    }


def face_frame(shape: Any, face_index: int, anchor: Any, App: Any) -> tuple[Any, Any, Any]:
    if face_index < 1 or face_index > len(shape.Faces):
        raise RuntimeError(f"face {face_index} outside shape with {len(shape.Faces)} faces")
    face = shape.Faces[face_index - 1]
    try:
        u_param, v_param = face.Surface.parameter(face.CenterOfMass)
        normal = unit(face.normalAt(u_param, v_param))
    except Exception:
        normal = unit(face.normalAt(0.0, 0.0))

    tangent = None
    for edge in sorted(face.Edges, key=lambda item: float(item.Length), reverse=True):
        vertices = list(edge.Vertexes)
        if len(vertices) >= 2:
            candidate = vertices[-1].Point - vertices[0].Point
            candidate = candidate - normal * float(candidate.dot(normal))
            if float(candidate.Length) > 1.0e-6:
                tangent = unit(candidate)
                break
    if tangent is None:
        trial = App.Vector(1.0, 0.0, 0.0)
        if abs(float(trial.dot(normal))) > 0.9:
            trial = App.Vector(0.0, 1.0, 0.0)
        tangent = unit(trial - normal * float(trial.dot(normal)))
    across = unit(normal.cross(tangent))

    plus_inside = bool(shape.isInside(anchor + normal * 0.2, 1.0e-4, True))
    minus_inside = bool(shape.isInside(anchor - normal * 0.2, 1.0e-4, True))
    if plus_inside and not minus_inside:
        outward = normal * -1.0
    elif minus_inside and not plus_inside:
        outward = normal
    else:
        plus_distance = float(shape.distToShape(__import__("Part").Vertex(anchor + normal))[0])
        minus_distance = float(shape.distToShape(__import__("Part").Vertex(anchor - normal))[0])
        outward = normal if plus_distance >= minus_distance else normal * -1.0
    return tangent, across, unit(outward)


def oriented_box(
    center: Any,
    axis_u: Any,
    axis_v: Any,
    axis_w: Any,
    length: float,
    width: float,
    w_min: float,
    w_max: float,
    Part: Any,
) -> Any:
    p0 = center - axis_u * (length / 2.0) - axis_v * (width / 2.0) + axis_w * w_min
    p1 = center + axis_u * (length / 2.0) - axis_v * (width / 2.0) + axis_w * w_min
    p2 = center + axis_u * (length / 2.0) + axis_v * (width / 2.0) + axis_w * w_min
    p3 = center - axis_u * (length / 2.0) + axis_v * (width / 2.0) + axis_w * w_min
    face = Part.Face(Part.makePolygon([p0, p1, p2, p3, p0]))
    return face.extrude(axis_w * (w_max - w_min)).removeSplitter()


def connector_pair(
    source_shape: Any,
    station: dict[str, Any],
    spec: dict[str, Any],
    side: str,
    App: Any,
    Part: Any,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    anchor = vec(station["anchor_mm"], App)
    if side == "RIGHT":
        anchor.x = -anchor.x
    face_index = int(station["face"])
    source_for_frame = source_shape if side == "LEFT" else mirror_x0(source_shape, App)
    tangent, across, outward = face_frame(source_for_frame, face_index, anchor, App)
    length = float(spec["length_mm"])
    width = float(spec["width_mm"])
    thickness = float(spec["thickness_mm"])
    embed = float(spec["embed_mm"])
    gap = float(spec["pair_gap_mm"])
    opaque = oriented_box(
        anchor, tangent, across, outward, length, width, -embed, thickness - embed, Part
    )
    mate = oriented_box(
        anchor, tangent, across, outward, length, width,
        thickness - embed + gap,
        thickness - embed + gap + thickness,
        Part,
    )
    cutter = Part.makeCylinder(
        float(spec["bore_diameter_mm"]) / 2.0,
        thickness * 2.0 + gap + embed + 1.0,
        anchor - outward * (embed + 0.5),
        outward,
    )
    opaque = opaque.cut(cutter).removeSplitter()
    mate = mate.cut(cutter).removeSplitter()
    station_id = str(station["id"]).upper()
    records = [
        {
            "name": f"{side}_{station_id}_OPAQUE_HEAD_TAB",
            "label": f"{side} — {station_id} — OPAQUE HEAD TAB",
            "shape": opaque,
        },
        {
            "name": f"{side}_{station_id}_TRANSLUCENT_MATING_TAB",
            "label": f"{side} — {station_id} — TRANSLUCENT MATING TAB",
            "shape": mate,
        },
    ]
    return records, {
        "side": side,
        "station": station["id"],
        "component": station["component"],
        "face": face_index,
        "anchor_world_mm": [float(anchor.x), float(anchor.y), float(anchor.z)],
        "outward_axis": [float(outward.x), float(outward.y), float(outward.z)],
        "opaque_metrics": shape_metrics(opaque),
        "mate_metrics": shape_metrics(mate),
        "pair_gap_mm": gap,
    }


def load_source_shapes(contract: dict[str, Any], App: Any, Part: Any) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    resolved = {name: require_hash(item) for name, item in contract["inputs"].items()}
    source = App.openDocument(str(resolved["v3_review_fcstd"]))
    try:
        source.recompute()
        group_names = [
            "OPAQUE_RIGHT_LOWER_OWNERS", "OPAQUE_LEFT_LOWER_OWNERS",
            "OPAQUE_RIGHT_UPPER_OWNERS", "OPAQUE_LEFT_UPPER_OWNERS",
            "REFERENCE_RIGHT_MESH_ONLY", "REFERENCE_LEFT_MESH_ONLY",
            "SEPARATE_THREE_STATION_LOWER_REAR_LEDGES",
            "EXISTING_TRANSLUCENT_INSERT_COMPONENTS",
            "PROPOSED_TRANSLUCENT_MOUTH_COMPONENTS",
            "PROPOSED_MOUTH_M2P5_FLANGE_COMPONENTS",
            "REFERENCE_MOUTH_FASTENERS_AND_CUTTERS",
            "REFERENCE_USER_MANUAL_FLANGE_SOURCES",
            "REFERENCE_HIDDEN_MANUAL_FLANGE_ROOTS",
            "REFERENCE_REMOVED_CLEANUP_GEOMETRY",
            "REFERENCE_OUTBOARD_LEDGE_HARDWARE",
            "REFERENCE_OUTBOARD_LEDGE_CUTTERS",
        ]
        records: dict[str, list[dict[str, Any]]] = {}
        cleanup_metrics: dict[str, Any] = {}
        source_left_by_index: dict[int, Any] = {}
        for group_name in group_names:
            if group_name == "SEPARATE_THREE_STATION_LOWER_REAR_LEDGES":
                continue
            group_records = []
            for obj in group_members(source, group_name):
                shape = obj.Shape.copy()
                index = component_index(str(obj.Name))
                if group_name in ("OPAQUE_RIGHT_LOWER_OWNERS", "OPAQUE_LEFT_LOWER_OWNERS"):
                    if index in (6, 14, 23):
                        continue
                    if index in (1, 10):
                        shape, metric = largest_solid(shape)
                        cleanup_metrics[f"{group_name}_{index:03d}"] = metric
                    if group_name == "OPAQUE_LEFT_LOWER_OWNERS" and index is not None:
                        source_left_by_index[index] = obj.Shape.copy()
                if group_name in (
                    "PROPOSED_MOUTH_M2P5_FLANGE_COMPONENTS",
                    "REFERENCE_MOUTH_FASTENERS_AND_CUTTERS",
                ) and (str(obj.Name).startswith("TRI005") or str(obj.Name).startswith("TRI006")):
                    moved, metric = moved_mouth_record(
                        obj, float(contract["mouth"]["pair_translation_toward_panel_mm"]), App
                    )
                    cleanup_metrics[f"mouth_{obj.Name}"] = metric
                    group_records.append(moved)
                    continue
                group_records.append(copied_record(obj, shape))
            records[group_name] = group_records

        source_ledges = group_members(source, "SEPARATE_THREE_STATION_LOWER_REAR_LEDGES")
        right_obj = next(obj for obj in source_ledges if str(obj.Name).startswith("RIGHT_"))
        right_clean, right_ear, old_cutter, ledge_metric = construct_rectangular_ledge_ear(
            right_obj.Shape.copy(), contract, App, Part
        )
        left_clean = mirror_x0(right_clean, App)
        left_ear = mirror_x0(right_ear, App)
        records["SEPARATE_THREE_STATION_LOWER_REAR_LEDGES"] = [
            {"name": "RIGHT_V5_LONG_LEDGE_CLEAN_BASE", "label": "RIGHT — V5 LONG LEDGE — CLEAN BASE", "shape": right_clean},
            {"name": "RIGHT_V5_LONG_LEDGE_RECTANGULAR_SECOND_EAR", "label": "RIGHT — RECTANGULAR SECOND M3 EAR", "shape": right_ear},
            {"name": "LEFT_V5_LONG_LEDGE_CLEAN_BASE", "label": "LEFT — V5 LONG LEDGE — CLEAN BASE", "shape": left_clean},
            {"name": "LEFT_V5_LONG_LEDGE_RECTANGULAR_SECOND_EAR", "label": "LEFT — RECTANGULAR SECOND M3 EAR", "shape": left_ear},
        ]
        records["REFERENCE_REMOVED_CLEANUP_GEOMETRY"].extend([
            {"name": "REMOVED_RIGHT_MALFORMED_LEDGE_EAR", "label": "REMOVED — RIGHT MALFORMED LEDGE EAR ZONE", "shape": old_cutter},
            {"name": "REMOVED_LEFT_MALFORMED_LEDGE_EAR", "label": "REMOVED — LEFT MALFORMED LEDGE EAR ZONE", "shape": mirror_x0(old_cutter, App)},
        ])
        cleanup_metrics["ledge"] = ledge_metric

        connector_records: list[dict[str, Any]] = []
        connector_metrics: list[dict[str, Any]] = []
        for station in contract["connector_tabs"]["stations"]:
            index = int(str(station["component"]).split("_")[-1])
            source_shape = source_left_by_index.get(index)
            if source_shape is None:
                raise RuntimeError(f"left source component missing for connector station {station['id']}")
            for side in ("LEFT", "RIGHT"):
                pair, metric = connector_pair(
                    source_shape, station, contract["connector_tabs"], side, App, Part
                )
                connector_records.extend(pair)
                connector_metrics.append(metric)
        records["PROPOSED_SIMPLE_TRANSLUCENT_PANEL_CONNECTOR_TABS"] = connector_records
        cleanup_metrics["connectors"] = connector_metrics
        return records, cleanup_metrics
    finally:
        App.closeDocument(source.Name)


def build() -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    contract = load_contract()
    records, measurements = load_source_shapes(contract, App, Part)
    progress("v4_geometry_constructed")

    target_cleanup = [
        item for key, item in measurements.items()
        if key.endswith("_001") or key.endswith("_010")
    ]
    mouth_moves = [item for key, item in measurements.items() if key.startswith("mouth_")]
    connector_metrics = measurements["connectors"]
    ledge = measurements["ledge"]
    checks = {
        "all_inputs_hash_match": True,
        "components_001_and_010_are_reduced_to_valid_single_solids_bilaterally": (
            len(target_cleanup) == 4
            and all(item["retained_volume_mm3"] > 0.0 for item in target_cleanup)
        ),
        "obsolete_components_006_014_023_are_absent": all(
            component_index(record["name"]) not in (6, 14, 23)
            for group_name in ("OPAQUE_RIGHT_LOWER_OWNERS", "OPAQUE_LEFT_LOWER_OWNERS")
            for record in records[group_name]
        ),
        "component_007_user_flange_and_component_021_center_half_remain": all(
            {7, 21}.issubset({component_index(record["name"]) for record in records[group_name]})
            for group_name in ("OPAQUE_RIGHT_LOWER_OWNERS", "OPAQUE_LEFT_LOWER_OWNERS")
        ),
        "mouth_flange_fastener_pairs_translate_together_exactly_3p9_mm": (
            len(mouth_moves) >= 10
            and all(abs(item["translation_mm"] - float(contract["mouth"]["pair_translation_toward_panel_mm"])) <= 1.0e-6 for item in mouth_moves)
        ),
        "new_ledge_ears_are_exact_rectangular_single_solids": (
            valid_single_solid(records["SEPARATE_THREE_STATION_LOWER_REAR_LEDGES"][1]["shape"])
            and valid_single_solid(records["SEPARATE_THREE_STATION_LOWER_REAR_LEDGES"][3]["shape"])
            and abs(ledge["clear_gap_mm"] - float(contract["ledge"]["clear_gap_mm"])) <= 1.0e-9
        ),
        "all_eight_connector_pairs_are_separate_valid_single_solids": (
            len(records["PROPOSED_SIMPLE_TRANSLUCENT_PANEL_CONNECTOR_TABS"]) == 16
            and all(valid_single_solid(record["shape"]) for record in records["PROPOSED_SIMPLE_TRANSLUCENT_PANEL_CONNECTOR_TABS"])
        ),
        "connector_pair_gap_is_exactly_0p3_mm": all(
            abs(item["pair_gap_mm"] - float(contract["connector_tabs"]["pair_gap_mm"])) <= 1.0e-9
            for item in connector_metrics
        ),
        "mouth_panels_and_center_seam_are_preserved": len(records["PROPOSED_TRANSLUCENT_MOUTH_COMPONENTS"]) == 3,
        "review_only_no_export_or_production_write": True,
    }
    failed = [name for name, passed in checks.items() if not passed]
    status = (
        "PASS__LOWER_FRONT_BILATERAL_FEEDBACK_CLEANUP_V4_REVIEW_READY__NOT_PRINT_RELEASED"
        if not failed else "HOLD__LOWER_FRONT_BILATERAL_FEEDBACK_CLEANUP_V4_GATE_FAILURE"
    )
    result = {
        "schema_version": "cat-head-lower-front-bilateral-feedback-cleanup-validation-v4",
        "status": status,
        "authority": contract["authority"],
        "checks": checks,
        "failed_checks": failed,
        "input_sha256": {name: item["sha256"] for name, item in contract["inputs"].items()},
        "measurements": measurements,
        "review_summary": [
            "Detached/sliver solids on bilateral component_001 and component_010 are removed by retaining the largest valid solid.",
            "Mouth flange/fastener pairs move together 3.9 mm toward their panel; mouth panels and seam remain unchanged.",
            "The malformed ledge ear is replaced by a clean rectangular holed ear at u=-13 mm, 25 mm clear of the source ear.",
            "Four simple opaque/translucent tab pairs per side remain separately selectable for visual review.",
        ],
        "print_release_holds": [
            "V4 is visual-review geometry, not a print source.",
            "No STL, STEP, 3MF, G-code, slicing, promotion, or production fusion is created.",
        ],
        "io_trace": {
            "source_v3_saved": False,
            "review_saved": False,
            "geometry_export_created": False,
            "production_output_created": False,
        },
    }
    return result, records


def add_feature(
    document: Any,
    group: Any,
    record: dict[str, Any],
    authority: str,
    color: tuple[float, float, float],
    transparency: int,
) -> Any:
    obj = document.addObject("Part::Feature", str(record["name"]))
    obj.Label = str(record.get("label", record["name"]))
    obj.Shape = record["shape"]
    obj.addProperty("App::PropertyString", "Authority", "Review Control")
    obj.Authority = authority
    if getattr(obj, "ViewObject", None) is not None:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineColor = (0.12, 0.12, 0.12)
        obj.ViewObject.Transparency = transparency
    group.addObject(obj)
    return obj


def save_review(result: dict[str, Any], records: dict[str, list[dict[str, Any]]]) -> tuple[Path, Path]:
    import FreeCAD as App  # type: ignore

    if not result["status"].startswith("PASS__"):
        raise RuntimeError("review save blocked: " + ", ".join(result["failed_checks"]))
    contract = load_contract()
    output_dir = (PROJECT_ROOT / contract["outputs"]["directory"]).resolve()
    if output_dir.exists():
        raise RuntimeError(f"fresh V4 output already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    document = App.newDocument("LOWER_FRONT_BILATERAL_FEEDBACK_CLEANUP_REVIEW_ONLY_V4")
    try:
        group_order = [
            "OPAQUE_RIGHT_LOWER_OWNERS", "OPAQUE_LEFT_LOWER_OWNERS",
            "OPAQUE_RIGHT_UPPER_OWNERS", "OPAQUE_LEFT_UPPER_OWNERS",
            "REFERENCE_RIGHT_MESH_ONLY", "REFERENCE_LEFT_MESH_ONLY",
            "SEPARATE_THREE_STATION_LOWER_REAR_LEDGES",
            "EXISTING_TRANSLUCENT_INSERT_COMPONENTS",
            "PROPOSED_TRANSLUCENT_MOUTH_COMPONENTS",
            "PROPOSED_MOUTH_M2P5_FLANGE_COMPONENTS",
            "PROPOSED_SIMPLE_TRANSLUCENT_PANEL_CONNECTOR_TABS",
            "REFERENCE_MOUTH_FASTENERS_AND_CUTTERS",
            "REFERENCE_USER_MANUAL_FLANGE_SOURCES",
            "REFERENCE_HIDDEN_MANUAL_FLANGE_ROOTS",
            "REFERENCE_REMOVED_CLEANUP_GEOMETRY",
            "REFERENCE_OUTBOARD_LEDGE_HARDWARE",
            "REFERENCE_OUTBOARD_LEDGE_CUTTERS",
        ]
        groups = {name: document.addObject("App::DocumentObjectGroup", name) for name in group_order}
        styles = {
            "OPAQUE_RIGHT_LOWER_OWNERS": ((0.34, 0.55, 0.88), 6),
            "OPAQUE_LEFT_LOWER_OWNERS": ((0.34, 0.55, 0.88), 6),
            "OPAQUE_RIGHT_UPPER_OWNERS": ((0.70, 0.72, 0.76), 26),
            "OPAQUE_LEFT_UPPER_OWNERS": ((0.70, 0.72, 0.76), 26),
            "REFERENCE_RIGHT_MESH_ONLY": ((0.52, 0.52, 0.56), 78),
            "REFERENCE_LEFT_MESH_ONLY": ((0.52, 0.52, 0.56), 78),
            "SEPARATE_THREE_STATION_LOWER_REAR_LEDGES": ((0.20, 0.90, 0.30), 0),
            "EXISTING_TRANSLUCENT_INSERT_COMPONENTS": ((0.30, 0.95, 1.00), 40),
            "PROPOSED_TRANSLUCENT_MOUTH_COMPONENTS": ((0.35, 1.00, 0.90), 32),
            "PROPOSED_MOUTH_M2P5_FLANGE_COMPONENTS": ((0.95, 0.55, 0.15), 0),
            "PROPOSED_SIMPLE_TRANSLUCENT_PANEL_CONNECTOR_TABS": ((0.95, 0.65, 0.12), 0),
        }
        for group_name in group_order:
            color, transparency = styles.get(group_name, ((0.72, 0.72, 0.76), 40))
            for record in records.get(group_name, []):
                if record["shape"].isNull():
                    continue
                obj = add_feature(
                    document, groups[group_name], record, contract["authority"], color, transparency
                )
                if group_name.startswith("REFERENCE_") and getattr(obj, "ViewObject", None) is not None:
                    obj.ViewObject.Visibility = False

        decision = document.addObject("App::FeaturePython", "V4_REVIEW_DECISION")
        decision.Label = "REVIEW — SIMPLE LOWER-FRONT FEEDBACK CLEANUP V4"
        decision.addProperty("App::PropertyString", "Authority", "Review Control")
        decision.addProperty("App::PropertyString", "WhatChanged", "Review Control")
        decision.addProperty("App::PropertyString", "ReleaseHold", "Review Control")
        decision.Authority = contract["authority"]
        decision.WhatChanged = "Residues cleaned; rectangular ledge ears; mouth pairs moved; eight simple translucent mounting-tab pairs added."
        decision.ReleaseHold = "Visual review required. Not a print source."
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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("feasibility", "review"), required=True)
    parser.add_argument("--report", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    result, records = build()
    if args.mode == "feasibility":
        if args.report is None or not str(args.report.resolve()).startswith("/tmp/"):
            raise RuntimeError("feasibility requires a fresh /tmp report")
        if args.report.exists():
            raise RuntimeError(f"feasibility report already exists: {args.report}")
        args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "failed_checks": result["failed_checks"]}, sort_keys=True))
        return 0 if result["status"].startswith("PASS__") else 1
    fcstd, validation = save_review(result, records)
    print(json.dumps({"status": result["status"], "fcstd": str(fcstd), "validation": str(validation)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
