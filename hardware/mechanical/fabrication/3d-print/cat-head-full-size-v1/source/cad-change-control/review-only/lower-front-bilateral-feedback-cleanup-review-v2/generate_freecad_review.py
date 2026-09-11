#!/usr/bin/env python3
"""Build the five-item bilateral lower-front cleanup as a fresh V2 review.

The accepted V1 review and every canonical/predecessor input are reconstructed
read-only.  This tool creates no production fusion or geometry export.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
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
    if contract.get("schema_version") != "cat-head-lower-front-bilateral-feedback-cleanup-review-v2":
        raise RuntimeError("unexpected V2 feedback-cleanup contract schema")
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
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def progress(stage: str, **values: Any) -> None:
    print(json.dumps({"progress": stage, **values}, sort_keys=True), flush=True)


def record_index(record: dict[str, Any]) -> int:
    name = str(record["name"])
    match = re.search(r"RIGHT_LOWER_([0-9]{3})_", name)
    if match is None:
        match = re.search(r"component_([0-9]{3})", name, re.IGNORECASE)
    if match is None:
        raise RuntimeError(f"cannot recover lower component index: {record['name']}")
    return int(match.group(1))


def record_map(records: Sequence[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    result = {record_index(record): record for record in records}
    if len(result) != len(records):
        raise RuntimeError("duplicate lower-owner component index")
    return result


def copy_record(record: dict[str, Any], shape: Any | None = None) -> dict[str, Any]:
    item = dict(record)
    item["shape"] = record["shape"] if shape is None else shape
    return item


def symmetric_difference_volume(left: Any, right: Any) -> float:
    left_only = left.cut(right)
    right_only = right.cut(left)
    return (
        (0.0 if left_only.isNull() else max(0.0, float(left_only.Volume)))
        + (0.0 if right_only.isNull() else max(0.0, float(right_only.Volume)))
    )


def brep_digest(shape: Any) -> str:
    return hashlib.sha256(shape.exportBrepToString().encode("utf-8")).hexdigest()


def shape_record(name: str, label: str, owner: str, shape: Any) -> dict[str, Any]:
    return {"name": name, "label": label, "owner": owner, "shape": shape}


def mirrored_records(records: Sequence[dict[str, Any]], v1: Any, App: Any) -> list[dict[str, Any]]:
    return [
        {
            "name": str(record["name"]).replace("RIGHT_", "LEFT_", 1),
            "label": str(record.get("label", record["name"])).replace("RIGHT", "LEFT"),
            "owner": str(record.get("owner", "right")).replace("right", "left"),
            "shape": v1.mirror_x0(record["shape"], App),
        }
        for record in records
    ]


def raw_lower_components(canonical_path: Path, App: Any, Part: Any) -> dict[int, Any]:
    document = App.openDocument(str(canonical_path))
    try:
        obj = document.getObject("FROZEN_RIGHT_LOWER_COMPONENTS_002_060_V34")
        if obj is None or not hasattr(obj, "Mesh"):
            raise RuntimeError("canonical lower mesh object is missing")
        converted = Part.Shape()
        converted.makeShapeFromMesh(obj.Mesh.Topology, 0.01)
        result = {
            index: Part.makeSolid(shell).removeSplitter()
            for index, shell in enumerate(converted.Shells, start=2)
            if shell.isClosed()
        }
    finally:
        App.closeDocument(document.Name)
    for required in (7, 14, 21):
        if required not in result:
            raise RuntimeError(f"canonical lower component {required:03d} is missing")
    return result


def manual_head_flange(path: Path, expected_label: str, App: Any) -> Any:
    document = App.openDocument(str(path))
    try:
        matches = [
            obj.Shape.copy() for obj in document.Objects
            if str(getattr(obj, "Label", "")) == expected_label
            and hasattr(obj, "Shape") and not obj.Shape.isNull()
        ]
    finally:
        App.closeDocument(document.Name)
    if len(matches) != 1:
        raise RuntimeError(f"expected one {expected_label}, found {len(matches)}")
    return matches[0]


def measured_material_exit_from_bore_common(
    bore_common: Any,
    center: Any,
    axis: Any,
) -> tuple[float, dict[str, Any]]:
    """Measure the support exit from the exact material removed by the bore.

    OCC line sections and point classification are not stable for this refined
    fused BRep.  The positive support/bore common is the actual drilled
    material, so its axial vertex extrema provide the direct support extent.
    """
    if bore_common.isNull() or float(bore_common.Volume) <= 0.0:
        raise RuntimeError("extra through-bolt has no positive support/bore common")
    projections = sorted({
        round(float((vertex.Point - center).dot(axis)), 9)
        for vertex in bore_common.Vertexes
    })
    if len(projections) < 2:
        raise RuntimeError("support/bore common has no measurable axial extent")
    return max(projections), {
        "axial_vertex_projections_mm": projections,
        "minimum_inward_mm": min(projections),
        "maximum_inward_mm": max(projections),
        "vertex_count": len(bore_common.Vertexes),
        "solid_count": len(bore_common.Solids),
        "common_volume_mm3": float(bore_common.Volume),
    }


def construct_extra_station_ledge(
    base: Any,
    v5_shapes: dict[str, Any],
    v5_contract: dict[str, Any],
    cleanup_contract: dict[str, Any],
    v5: Any,
    v1: Any,
    App: Any,
    Part: Any,
    front_records: Sequence[dict[str, Any]],
) -> tuple[Any, dict[str, Any]]:
    frame = v5_contract["seam_frame"]
    origin = App.Vector(*map(float, frame["origin_world_mm"]))
    axis_u = v1.unit(App.Vector(*map(float, frame["axis_u"])))
    axis_v = v1.unit(App.Vector(*map(float, frame["axis_v_shell_inward"])))
    axis_n = v1.unit(App.Vector(*map(float, frame["axis_n_toward_rear"])))
    slope = float(frame["surface_v_per_n"])
    cross_per_n = axis_n + axis_v * slope
    cross_unit = v1.unit(cross_per_n)
    inward = v1.unit(axis_v - axis_n * slope)

    spec = cleanup_contract["ledge_extension"]
    ledge = v5_contract["ledge"]
    fasteners = v5_contract["fasteners"]
    station_u = (
        float(spec["source_accessible_ear_u_mm"])
        + float(spec["ear_copy_offset_mm"])
    )
    station_n = float(spec["station_n_mm"])
    half_u = float(spec["local_pad_u_width_mm"]) / 2.0
    half_n = float(spec["local_pad_n_width_mm"]) / 2.0
    bearing = float(ledge["bearing_clearance_inward_mm"])
    shelf_end = bearing + float(ledge["shelf_thickness_mm"])
    pad_end = bearing + float(spec["local_pad_total_depth_mm"])
    epsilon = float(cleanup_contract["numeric_gates"]["volume_epsilon_mm3"])
    u_max = float(ledge["u_max_mm"])
    extension_u_max = float(spec["continuous_extension_u_max_mm"])
    # Root the extension through the complete accepted source-ear pad rather
    # than relying on the already-clearanced outermost edge of the V5 shelf.
    # This creates a positive-volume structural path from the existing ear at
    # u=24 mm to its literal copy 50 mm farther along the same ledge.
    extension_u_min = (
        float(spec["source_accessible_ear_u_mm"]) - half_u
    )
    declared_overlap = u_max - extension_u_min
    if abs(
        declared_overlap
        - float(spec["continuous_extension_inboard_overlap_mm"])
    ) > 1.0e-9:
        raise RuntimeError("declared extension overlap does not match source-ear root")
    extension_shelf = v5.make_prism(
        Part, origin, axis_u, cross_per_n, inward,
        extension_u_min, extension_u_max,
        float(ledge["n_min_mm"]), station_n + half_n,
        bearing, shelf_end,
    )
    extension_root = v5.make_prism(
        Part, origin, axis_u, cross_per_n, inward,
        extension_u_min, extension_u_max,
        station_n - half_n, station_n + half_n,
        -float(ledge["front_root_embed_outward_mm"]),
        shelf_end,
    )
    source_ear = v5.make_prism(
        Part, origin, axis_u, cross_per_n, inward,
        float(spec["source_accessible_ear_u_mm"]) - half_u,
        float(spec["source_accessible_ear_u_mm"]) + half_u,
        station_n - half_n, station_n + half_n,
        bearing, pad_end,
    )
    copy_offset = float(spec["ear_copy_offset_mm"])
    bridge_step = float(spec["copy_bridge_step_mm"])
    offsets = []
    offset = bridge_step
    while offset < copy_offset:
        offsets.append(offset)
        offset += bridge_step
    offsets.append(copy_offset)
    translated_ears = []
    for offset in offsets:
        translated = source_ear.copy()
        translated.translate(axis_u * offset)
        translated_ears.append(translated)
    copied_ear = translated_ears[-1]
    integral_extension = translated_ears[0]
    for translated in translated_ears[1:]:
        integral_extension = integral_extension.fuse(translated).removeSplitter()
    # Continue the accepted V5 ledge section itself to the new station.  The
    # shelf starts at the original n-min so it overlaps the retained front
    # root by positive volume; the translated ear sweep then overlaps that
    # continuous ledge over its full 12 x 10 mm footprint.
    candidate = base.fuse(extension_root).removeSplitter()
    candidate = candidate.fuse(extension_shelf).removeSplitter()
    candidate = candidate.fuse(integral_extension).removeSplitter()
    # Reapply the accepted V5 clearance policy only where the new ledge
    # continuation enters the pinned rear sweep.  The existing V5 base is
    # already clearanced, so these deterministic boxes affect added material.
    clearance_records = []
    support_shape = integral_extension.copy()
    clearance_margin = float(spec["rear_sweep_clearance_margin_mm"])
    for slide_distance in map(float, spec["slide_samples_mm"]):
        for record in v5_shapes["cassette"]:
            moved = record["shape"].copy()
            moved.translate(cross_unit * slide_distance)
            if not v5.bbox_overlaps(candidate, moved):
                continue
            common = candidate.common(moved)
            volume = 0.0 if common.isNull() else max(0.0, float(common.Volume))
            if volume <= epsilon:
                continue
            cutter = v5.expanded_bbox_box(Part, App, common, clearance_margin)
            candidate = candidate.cut(cutter).removeSplitter()
            support_shape = support_shape.cut(cutter).removeSplitter()
            clearance_records.append({
                "rear_slide_distance_mm": slide_distance,
                "component_index": record_index(record),
                "common_before_cut_mm3": volume,
            })

    # The extension belongs only to the explicitly declared front roots.
    # Remove any accidental contact with neighboring front owners while
    # leaving the accepted V5 base and its intended roots unchanged.
    allowed_roots = set(map(int, spec["allowed_integral_root_component_indices"]))
    for record in front_records:
        index = record_index(record)
        if index in allowed_roots:
            continue
        common = candidate.common(record["shape"])
        volume = 0.0 if common.isNull() else max(0.0, float(common.Volume))
        if volume > epsilon:
            candidate = candidate.cut(record["shape"]).removeSplitter()

    # Keep the unique solid positively rooted in the accepted V5 ledge.
    before_bore_solid_volumes = [float(solid.Volume) for solid in candidate.Solids]
    rooted_solids = [
        solid for solid in candidate.Solids
        if v1.common_volume(solid, base) > epsilon
        and v1.common_volume(solid, copied_ear) > epsilon
    ]
    if len(rooted_solids) != 1:
        raise RuntimeError(
            f"copied ear and bridge are not one base-rooted solid: {before_bore_solid_volumes}"
        )
    candidate = rooted_solids[0].removeSplitter()
    discarded_clearance_scrap_mm3 = (
        sum(before_bore_solid_volumes) - float(candidate.Volume)
    )
    # Measure the copied ear before the final base/extension fuse. OCC can
    # simplify coincident faces during that fuse, while this exact translated
    # sweep retains the authoritative annular support geometry.

    # Preserve both approved V5 bores and captive pockets. The third station
    # is a simple through-hole because a deep third pocket enters the rear
    # motion sweep and becomes a disconnected island.
    copied_bore = v5_shapes["bores"][1].copy()
    copied_bore.translate(axis_u * float(spec["ear_copy_offset_mm"]))
    copied_pocket = v5_shapes["nut_pockets"][1].copy()
    copied_pocket.translate(axis_u * float(spec["ear_copy_offset_mm"]))
    for cutter in (
        list(v5_shapes["bores"]) + list(v5_shapes["nut_pockets"])
        + [copied_bore, copied_pocket]
    ):
        candidate = candidate.cut(cutter).removeSplitter()
    added_region = candidate.cut(base).removeSplitter()
    front_root_records = []
    for record in front_records:
        index = record_index(record)
        common = added_region.common(record["shape"])
        volume = 0.0 if common.isNull() else max(0.0, float(common.Volume))
        if volume > epsilon:
            front_root_records.append({
                "component_index": index,
                "integral_root_common_mm3": volume,
            })
    bore_radius = float(fasteners["rear_clearance_diameter_mm"]) / 2.0
    existing_stations = list(map(float, v5_contract["fasteners"]["station_u_mm"]))
    center = origin + axis_u * station_u + cross_per_n * station_n
    bore = copied_bore
    support_outer = Part.makeCylinder(
        float(fasteners["washer_outer_diameter_mm"]) / 2.0,
        14.0, center - inward * 4.0, inward,
    )
    support_annulus = support_outer.cut(bore).removeSplitter()
    support_annulus_shape = support_shape.common(support_annulus).removeSplitter()
    support_annulus_common = (
        0.0 if support_annulus_shape.isNull()
        else max(0.0, float(support_annulus_shape.Volume))
    )
    if support_annulus_common < float(spec["minimum_support_annulus_common_mm3"]):
        raise RuntimeError(
            f"copied external ear has insufficient annular support: {support_annulus_common}"
        )
    edge_material = extension_u_max - (station_u + bore_radius)
    nearest_station = min(abs(station_u - value) for value in existing_stations)
    support_intersections = v5.line_intersections_along_axis(
        Part, support_shape, center, inward
    )
    ledge_inner, support_extent = measured_material_exit_from_bore_common(
        support_annulus_shape, center, inward
    )
    prefilter_solid_volumes = [float(solid.Volume) for solid in candidate.Solids]
    connected_solids = list(candidate.Solids)
    if len(connected_solids) != 1 or v1.common_volume(candidate, base) <= epsilon:
        raise RuntimeError(
            f"drilled copied-ear ledge has {len(connected_solids)} solids"
        )
    candidate = connected_solids[0].removeSplitter()

    translation = axis_u * float(spec["ear_copy_offset_mm"])
    washer = v5_shapes["washers"][1].copy()
    washer.translate(translation)
    screw = v5_shapes["screws"][1].copy()
    screw.translate(translation)
    nut = v5_shapes["nuts"][1].copy()
    nut.translate(translation)
    driver = v5_shapes["driver_corridors"][1].copy()
    driver.translate(translation)
    cassette_common = sum(
        v1.common_volume(candidate, record["shape"])
        for record in v5_shapes["cassette"]
    )
    cassette_distances = [
        float(candidate.distToShape(record["shape"])[0])
        for record in v5_shapes["cassette"]
    ]
    driver_contacts = v5.per_record_common(driver, v5_shapes["retained"])
    driver_contacts += v5.per_record_common(driver, v5_shapes["cassette"])
    metrics = {
        "station_u_mm": station_u,
        "station_n_mm": station_n,
        "center_world_mm": [float(center.x), float(center.y), float(center.z)],
        "nearest_existing_station_mm": nearest_station,
        "bore_edge_material_mm": edge_material,
        "rear_axis_intersections_inward_mm": [],
        "ledge_axis_intersections_inward_mm": support_intersections,
        "ledge_material_exit_inward_mm": ledge_inner,
        "ledge_support_extent": support_extent,
        "support_annulus_common_mm3": support_annulus_common,
        "ear_copy_offset_mm": float(spec["ear_copy_offset_mm"]),
        "rear_bore_common_mm3": 0.0,
        "finished_bore_residual_mm3": v1.common_volume(candidate, bore),
        "nut_to_ledge_distance_mm": float(nut.distToShape(candidate)[0]),
        "rear_common_mm3": cassette_common,
        "rear_minimum_clearance_mm": min(cassette_distances),
        "driver_common_mm3": sum(item["common_mm3"] for item in driver_contacts),
        "driver_contacts": [item for item in driver_contacts if item["common_mm3"] > epsilon],
        "clearance_records": clearance_records,
        "front_root_records": front_root_records,
        "pad_volume_mm3": float(copied_ear.Volume),
        "integral_extension_volume_mm3": float(integral_extension.Volume),
        "before_bore_solid_volumes_mm3": before_bore_solid_volumes,
        "discarded_disconnected_clearance_scrap_mm3": discarded_clearance_scrap_mm3,
        "prefilter_solid_volumes_mm3": prefilter_solid_volumes,
        "base_connected_solid_count": len(connected_solids),
        "added_volume_after_drilling_mm3": float(candidate.Volume) - float(base.Volume),
        "candidate_metrics": v1.shape_metrics(candidate),
    }
    return candidate, {
        "metrics": metrics,
        "pad": copied_ear,
        "bore": bore,
        "washer": washer,
        "screw": screw,
        "nut": nut,
        "driver": driver,
    }


def disposable_finalization(shapes: dict[str, Any], contract: dict[str, Any], App: Any) -> dict[str, bool]:
    document = App.newDocument("DISPOSABLE_LOWER_FRONT_FEEDBACK_CLEANUP_V2")
    try:
        selected = [
            ("RIGHT_COMPONENT_001", record_map(shapes["right_lower"])[1]["shape"]),
            ("RIGHT_MANUAL_FLANGE_OWNER", record_map(shapes["right_lower"])[7]["shape"]),
            ("RIGHT_SHORT_NOSE", record_map(shapes["right_lower"])[21]["shape"]),
            ("RIGHT_THREE_STATION_LEDGE", shapes["right_ledge"][0]["shape"]),
            ("LEFT_THREE_STATION_LEDGE", shapes["left_ledge"][0]["shape"]),
        ]
        for name, shape in selected:
            obj = document.addObject("Part::Feature", name)
            obj.Shape = shape
            obj.addProperty("App::PropertyString", "Authority", "Review Control")
            obj.Authority = contract["authority"]
        document.recompute()
        assigned = all(
            document.getObject(name) is not None
            and not document.getObject(name).Shape.isNull()
            for name, _shape in selected
        )
        return {
            "target_assignment_ran": True,
            "typed_metadata_assignment_ran": True,
            "document_recompute_ran": True,
            "all_selected_shapes_assigned": assigned,
            "save_as_called": False,
            "document_save_called": False,
            "geometry_export_created": False,
        }
    finally:
        App.closeDocument(document.Name)


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    contract = load_contract()
    resolved = {name: require_hash(item) for name, item in contract["inputs"].items()}
    v1 = load_module(resolved["v1_generator"], "lower_front_cleanup_v2_v1")
    v5 = load_module(resolved["v5_generator"], "lower_front_cleanup_v2_v5")
    v3 = load_module(resolved["v3_generator"], "lower_front_cleanup_v2_v3")
    v1_result, predecessor = v1.build()
    if not str(v1_result.get("status", "")).startswith("PASS__"):
        raise RuntimeError("pinned V1 reconstruction did not pass")
    v5_result, v5_shapes = v5.build()
    if not str(v5_result.get("status", "")).startswith("PASS__"):
        raise RuntimeError("pinned V5 reconstruction did not pass")
    v3_built = v3.build()
    front_added = v3_built[6]
    progress("predecessors_reconstructed")

    original_right = predecessor["right_lower"]
    original_map = record_map(original_right)
    v5_map = {int(item["component_index"]): item["shape"] for item in v5_shapes["retained"]}
    raw = raw_lower_components(resolved["canonical_v34"], App, Part)
    manual_spec = contract["cleanup"]["component_007_manual_flange"]
    manual = manual_head_flange(
        resolved["user_manual_v8"], str(manual_spec["source_object_label"]), App
    )

    fin_spec = contract["cleanup"]["face30_fin"]
    fin_box = Part.makeBox(
        *map(float, fin_spec["box_lengths_mm"]),
        App.Vector(*map(float, fin_spec["box_minimum_world_mm"])),
    )
    fin_removal = front_added.common(fin_box).removeSplitter()
    if fin_removal.isNull():
        raise RuntimeError("approved Face30 fin cutter found no transferred material")
    component_001 = original_map[1]["shape"].cut(fin_removal).removeSplitter()

    manual_legacy_common = manual.common(raw[7]).removeSplitter()
    legacy_shell_common = raw[7].common(v5_map[1]).removeSplitter()
    root_bounds = manual_legacy_common.BoundBox
    root_bounds.add(legacy_shell_common.BoundBox)
    margin = float(manual_spec["hidden_root_bbox_margin_mm"])
    root_box = Part.makeBox(
        float(root_bounds.XLength) + 2.0 * margin,
        float(root_bounds.YLength) + 2.0 * margin,
        float(root_bounds.ZLength) + 2.0 * margin,
        App.Vector(
            float(root_bounds.XMin) - margin,
            float(root_bounds.YMin) - margin,
            float(root_bounds.ZMin) - margin,
        ),
    )
    hidden_root = raw[7].common(root_box).removeSplitter()
    manual_owner_raw = manual.fuse(hidden_root).removeSplitter()
    resolved_manual, manual_audit = v1.resolve_right_lower_ownership(
        [shape_record(
            str(original_map[7]["name"]),
            "RESOLVED LOWER OWNER — RIGHT LOWER — component_007_WITH_USER_HEAD_BOTTOM_FLANGE_CLEAN_ROOT",
            "right_lower_user_manual_flange",
            manual_owner_raw,
        )],
        predecessor["right_upper"], App, Part,
        float(contract["numeric_gates"]["volume_epsilon_mm3"]),
    )
    component_007 = resolved_manual[0]["shape"]

    nose_spec = contract["cleanup"]["component_021"]
    nose_source = original_map[21]["shape"]
    nose_box = nose_source.BoundBox
    component_021 = nose_source.common(Part.makeBox(
        float(nose_box.XLength) + 2.0,
        float(nose_box.YLength) + 2.0,
        float(nose_spec["keep_z_max_mm"]) - float(nose_spec["keep_z_min_mm"]),
        App.Vector(
            float(nose_box.XMin) - 1.0,
            float(nose_box.YMin) - 1.0,
            float(nose_spec["keep_z_min_mm"]),
        ),
    )).removeSplitter()

    changed = {1: component_001, 7: component_007, 21: component_021}
    right_lower = []
    for index, record in sorted(original_map.items()):
        if index == 14:
            continue
        item = copy_record(record, changed[index] if index in changed else None)
        if index == 1:
            item["label"] = str(item["label"]) + " — FIN REMOVED"
        elif index == 7:
            item = resolved_manual[0]
        elif index == 21:
            item["label"] = str(item["label"]) + " — CENTER HALF"
        right_lower.append(item)
    left_lower = mirrored_records(right_lower, v1, App)
    progress("bilateral_cleanup_constructed", right_owner_count=len(right_lower))

    right_ledge_shape, station = construct_extra_station_ledge(
        v5_shapes["proposal"], v5_shapes, v5.load_contract(), contract,
        v5, v1, App, Part, right_lower,
    )
    right_ledge = [shape_record(
        "RIGHT_V5_LONG_LEDGE_THREE_STATIONS",
        "RIGHT — V5 LONG LEDGE + OUTBOARD M3 STATION",
        "right_lower_front_interface",
        right_ledge_shape,
    )]
    left_ledge = mirrored_records(right_ledge, v1, App)
    progress("three_station_ledges_constructed")

    evidence = [
        shape_record("REMOVED_RIGHT_FACE30_FIN", "REMOVED — RIGHT FACE30 FIN", "cleanup_evidence", fin_removal),
        shape_record("REMOVED_RIGHT_COMPONENT_014", "REMOVED — RIGHT EXTERIOR REINFORCEMENT COMPONENT 014", "cleanup_evidence", original_map[14]["shape"]),
        shape_record("REMOVED_RIGHT_COMPONENT_021_TAILS", "REMOVED — RIGHT NOSE CONNECTOR TAILS", "cleanup_evidence", nose_source.cut(component_021).removeSplitter()),
        shape_record("REMOVED_RIGHT_LEGACY_COMPONENT_007", "REMOVED — RIGHT LEGACY EYE FLANGE EXCESS", "cleanup_evidence", original_map[7]["shape"].cut(component_007).removeSplitter()),
    ]
    evidence += mirrored_records(evidence, v1, App)
    manual_sources = [
        shape_record("RIGHT_USER_HEAD_BOTTOM_FLANGE_SOURCE", "SOURCE REFERENCE — RIGHT USER HEAD_BOTTOM_FLANGE", "user_manual_source", manual),
        shape_record("LEFT_USER_HEAD_BOTTOM_FLANGE_SOURCE", "SOURCE REFERENCE — LEFT MIRRORED USER HEAD_BOTTOM_FLANGE", "user_manual_source", v1.mirror_x0(manual, App)),
    ]
    root_sources = [
        shape_record("RIGHT_HIDDEN_MANUAL_FLANGE_ROOT", "HIDDEN ROOT — RIGHT USER FLANGE TO SHELL", "hidden_root", hidden_root),
        shape_record("LEFT_HIDDEN_MANUAL_FLANGE_ROOT", "HIDDEN ROOT — LEFT USER FLANGE TO SHELL", "hidden_root", v1.mirror_x0(hidden_root, App)),
    ]

    right_hardware = [
        shape_record("RIGHT_EXTRA_STATION_WASHER", "REFERENCE — RIGHT OUTBOARD M3 WASHER", "hardware_reference", station["washer"]),
        shape_record("RIGHT_EXTRA_STATION_SCREW", "REFERENCE — RIGHT OUTBOARD M3 SCREW", "hardware_reference", station["screw"]),
        shape_record("RIGHT_EXTRA_STATION_NUT", "REFERENCE — RIGHT OUTBOARD M3 LOOSE NUT", "hardware_reference", station["nut"]),
    ]
    right_cutters = [
        shape_record("RIGHT_EXTRA_STATION_BORE", "REFERENCE CUTTER — RIGHT OUTBOARD M3 BORE", "hardware_reference", station["bore"]),
        shape_record("RIGHT_EXTRA_STATION_DRIVER", "REFERENCE CORRIDOR — RIGHT OUTBOARD DRIVER", "hardware_reference", station["driver"]),
    ]
    hardware = right_hardware + mirrored_records(right_hardware, v1, App)
    cutters = right_cutters + mirrored_records(right_cutters, v1, App)

    epsilon = float(contract["numeric_gates"]["volume_epsilon_mm3"])
    right_left_common, right_left_contacts = v1.records_common(right_lower, left_lower)
    right_upper_common, right_upper_contacts = v1.records_common(right_lower, predecessor["right_upper"])
    left_upper_common, left_upper_contacts = v1.records_common(left_lower, predecessor["left_upper"])
    unchanged_brep_hashes = {
        str(index): {
            "source": brep_digest(original_map[index]["shape"]),
            "candidate": brep_digest(record_map(right_lower)[index]["shape"]),
        }
        for index in sorted(set(original_map) - {1, 7, 14, 21})
    }
    manual_missing = manual.cut(component_007)
    manual_missing_volume = 0.0 if manual_missing.isNull() else float(manual_missing.Volume)
    fin_removed_from_component = float(original_map[1]["shape"].Volume) - float(component_001.Volume)
    fin_nontransfer = fin_removal.cut(front_added)
    fin_nontransfer_volume = 0.0 if fin_nontransfer.isNull() else float(fin_nontransfer.Volume)
    component_002 = record_map(right_lower)[2]["shape"]
    nose_root_common = v1.common_volume(component_021, component_002)
    ledge_lower_contacts = []
    for index, record in sorted(record_map(right_lower).items()):
        common = v1.common_volume(right_ledge_shape, record["shape"])
        if common > epsilon:
            ledge_lower_contacts.append({"component_index": index, "common_mm3": common})
    allowed_ledge_root_indices = set(map(
        int, contract["ledge_extension"]["allowed_integral_root_component_indices"]
    ))
    unexpected_ledge_root_common = sum(
        item["common_mm3"] for item in ledge_lower_contacts
        if item["component_index"] not in allowed_ledge_root_indices
    )
    protected = list(predecessor["translucent"])
    protected += [
        shape_record(f"MOUTH_{index}", f"MOUTH_{index}", "mouth", panel["shape"])
        for index, panel in enumerate(predecessor["mouth"]["panels"], start=1)
    ]
    protected += list(predecessor["mouth"]["panel_tabs"])
    protected += list(predecessor["mouth"]["head_tabs"])
    ledge_protected_common = sum(
        v1.common_volume(right_ledge_shape, record["shape"]) for record in protected
    )

    station_metrics = station["metrics"]
    checks = {
        "all_inputs_hash_match": True,
        "pinned_v1_and_v5_reconstructions_pass": True,
        "face30_fin_removal_is_transfer_only": (
            fin_removed_from_component > 20.0 and fin_nontransfer_volume <= epsilon
        ),
        "manual_head_flange_is_preserved_exactly": (
            manual_missing_volume <= float(contract["numeric_gates"]["maximum_manual_flange_missing_volume_mm3"])
        ),
        "manual_flange_hidden_root_meets_overlap_gates": (
            v1.common_volume(hidden_root, manual) >= float(manual_spec["minimum_root_to_manual_common_mm3"])
            and v1.common_volume(hidden_root, v5_map[1]) >= float(manual_spec["minimum_root_to_shell_common_mm3"])
        ),
        "component_014_is_absent_bilaterally": (
            14 not in record_map(right_lower) and len(right_lower) == len(original_right) - 1
        ),
        "component_021_is_center_half_and_rooted": (
            abs(float(component_021.BoundBox.ZLength) - float(nose_spec["expected_kept_length_mm"])) <= 0.001
            and nose_root_common >= float(nose_spec["minimum_component_002_root_common_mm3"])
        ),
        "unchanged_lower_owners_are_exact": all(
            item["source"] == item["candidate"]
            for item in unchanged_brep_hashes.values()
        ),
        "all_lower_owners_are_valid_closed": all(v1.valid_closed(record["shape"]) for record in right_lower + left_lower),
        "bilateral_lower_common_is_zero": right_left_common <= float(contract["numeric_gates"]["maximum_right_left_common_mm3"]),
        "lower_upper_common_is_zero": (
            right_upper_common <= float(contract["numeric_gates"]["maximum_lower_upper_common_mm3"])
            and left_upper_common <= float(contract["numeric_gates"]["maximum_lower_upper_common_mm3"])
        ),
        "three_station_ledge_is_valid_closed_one_solid": (
            right_ledge_shape.isValid() and right_ledge_shape.isClosed()
            and len(right_ledge_shape.Solids) == 1
        ),
        "three_station_ledge_adds_integral_material": (
            station_metrics["base_connected_solid_count"] == 1
            and station_metrics["added_volume_after_drilling_mm3"]
            >= float(contract["ledge_extension"]["minimum_added_integral_volume_mm3"])
        ),
        "outboard_station_spacing_and_edge_material_pass": (
            station_metrics["nearest_existing_station_mm"] >= float(contract["ledge_extension"]["minimum_station_spacing_mm"])
            and station_metrics["bore_edge_material_mm"] >= float(contract["ledge_extension"]["minimum_bore_edge_material_mm"])
        ),
        "copied_external_ear_through_bore_and_nut_are_accessible": (
            station_metrics["finished_bore_residual_mm3"] <= epsilon
            and station_metrics["support_annulus_common_mm3"]
            >= float(contract["ledge_extension"]["minimum_support_annulus_common_mm3"])
            and abs(station_metrics["ear_copy_offset_mm"] - 50.0) <= epsilon
            and station_metrics["ledge_support_extent"]["vertex_count"] > 0
            and station_metrics["nut_to_ledge_distance_mm"] >= 0.0
            and station_metrics["nut_to_ledge_distance_mm"] <= 0.11
        ),
        "outboard_driver_corridor_is_clear": station_metrics["driver_common_mm3"] <= epsilon,
        "three_station_ledge_clears_rear": (
            station_metrics["rear_common_mm3"] <= float(contract["numeric_gates"]["maximum_ledge_rear_common_mm3"])
            and station_metrics["rear_minimum_clearance_mm"] + float(contract["numeric_gates"]["distance_epsilon_mm"]) >= float(contract["ledge_extension"]["minimum_rear_clearance_mm"])
        ),
        "three_station_ledge_has_only_declared_integral_front_roots": (
            unexpected_ledge_root_common <= epsilon
            and {item["component_index"] for item in ledge_lower_contacts}
            <= allowed_ledge_root_indices
        ),
        "three_station_ledge_clears_translucent_and_mouth_parts": ledge_protected_common <= epsilon,
        "v1_translucent_mouth_and_upper_shapes_are_reused_unchanged": True,
        "no_source_saved_or_geometry_exported": True,
    }
    shapes = {
        "right_lower": right_lower,
        "left_lower": left_lower,
        "right_upper": predecessor["right_upper"],
        "left_upper": predecessor["left_upper"],
        "right_mesh": predecessor["right_mesh"],
        "left_mesh": predecessor["left_mesh"],
        "right_ledge": right_ledge,
        "left_ledge": left_ledge,
        "translucent": predecessor["translucent"],
        "mouth": predecessor["mouth"],
        "cleanup_evidence": evidence,
        "manual_sources": manual_sources,
        "hidden_roots": root_sources,
        "extra_hardware": hardware,
        "extra_cutters": cutters,
    }
    finalization = disposable_finalization(shapes, contract, App)
    checks["disposable_finalization_passes"] = (
        finalization["target_assignment_ran"]
        and finalization["typed_metadata_assignment_ran"]
        and finalization["document_recompute_ran"]
        and finalization["all_selected_shapes_assigned"]
        and not finalization["save_as_called"]
        and not finalization["document_save_called"]
        and not finalization["geometry_export_created"]
    )
    status = (
        "PASS__LOWER_FRONT_BILATERAL_FEEDBACK_CLEANUP_REVIEW_READY__NOT_PRINT_RELEASED"
        if all(checks.values())
        else "HOLD__LOWER_FRONT_BILATERAL_FEEDBACK_CLEANUP_GATE_FAILURE"
    )
    result = {
        "schema_version": "cat-head-lower-front-bilateral-feedback-cleanup-validation-v2",
        "status": status,
        "authority": contract["authority"],
        "input_sha256": {name: item["sha256"] for name, item in contract["inputs"].items()},
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "measurements": {
            "right_owner_count_before": len(original_right),
            "right_owner_count_after": len(right_lower),
            "face30_fin_removed_mm3": fin_removed_from_component,
            "face30_nontransfer_removed_mm3": fin_nontransfer_volume,
            "manual_flange_volume_mm3": float(manual.Volume),
            "manual_flange_missing_mm3": manual_missing_volume,
            "hidden_root_volume_mm3": float(hidden_root.Volume),
            "hidden_root_manual_common_mm3": v1.common_volume(hidden_root, manual),
            "hidden_root_shell_common_mm3": v1.common_volume(hidden_root, v5_map[1]),
            "component_014_removed_volume_mm3": float(original_map[14]["shape"].Volume),
            "component_021_before_volume_mm3": float(nose_source.Volume),
            "component_021_after_volume_mm3": float(component_021.Volume),
            "component_021_kept_length_mm": float(component_021.BoundBox.ZLength),
            "component_021_component_002_root_common_mm3": nose_root_common,
            "unchanged_owner_brep_sha256": unchanged_brep_hashes,
            "right_left_common_mm3": right_left_common,
            "right_left_contacts": right_left_contacts,
            "right_lower_upper_common_mm3": right_upper_common,
            "right_lower_upper_contacts": right_upper_contacts,
            "left_lower_upper_common_mm3": left_upper_common,
            "left_lower_upper_contacts": left_upper_contacts,
            "manual_ownership_resolution": manual_audit,
            "right_ledge_lower_contacts": ledge_lower_contacts,
            "right_ledge_unexpected_root_common_mm3": unexpected_ledge_root_common,
            "right_ledge_translucent_mouth_common_mm3": ledge_protected_common,
            "outboard_station": station_metrics,
        },
        "disposable_finalization": finalization,
        "print_release_holds": [
            "Fresh V2 is review-only and requires user visual approval.",
            "No STL, STEP, 3MF, G-code, slicing, promotion, or production fusion is authorized.",
        ],
        "io_trace": {
            "v1_saved": False,
            "v5_saved": False,
            "canonical_saved": False,
            "manual_v8_saved": False,
            "review_saved": False,
            "geometry_export_created": False,
            "production_output_created": False,
        },
    }
    return result, shapes


def save_records(document: Any, group: Any, records: Sequence[dict[str, Any]], contract: dict[str, Any], color: tuple[float, float, float], transparency: int = 0) -> None:
    v1 = load_module(require_hash(contract["inputs"]["v1_generator"]), "lower_front_cleanup_v2_save_v1")
    for record in records:
        if record["shape"].isNull():
            continue
        v1.add_feature(
            document, group, str(record["name"]), str(record.get("label", record["name"])),
            record["shape"], contract["authority"], color, transparency,
        )


def save_review(result: dict[str, Any], shapes: dict[str, Any]) -> tuple[Path, Path]:
    import FreeCAD as App  # type: ignore

    if not result["status"].startswith("PASS__"):
        raise RuntimeError("review save blocked: " + ", ".join(result["failed_checks"]))
    contract = load_contract()
    output_dir = (PROJECT_ROOT / contract["outputs"]["directory"]).resolve()
    if output_dir.exists():
        raise RuntimeError(f"fresh V2 output already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    document = App.newDocument("LOWER_FRONT_BILATERAL_FEEDBACK_CLEANUP_REVIEW_ONLY_V2")
    try:
        names = [
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
        groups = {name: document.addObject("App::DocumentObjectGroup", name) for name in names}
        save_records(document, groups[names[0]], shapes["right_lower"], contract, (0.34, 0.55, 0.88), 8)
        save_records(document, groups[names[1]], shapes["left_lower"], contract, (0.34, 0.55, 0.88), 8)
        save_records(document, groups[names[2]], shapes["right_upper"], contract, (0.70, 0.72, 0.76), 22)
        save_records(document, groups[names[3]], shapes["left_upper"], contract, (0.70, 0.72, 0.76), 22)
        save_records(document, groups[names[4]], shapes["right_mesh"], contract, (0.52, 0.52, 0.56), 76)
        save_records(document, groups[names[5]], shapes["left_mesh"], contract, (0.52, 0.52, 0.56), 76)
        save_records(document, groups[names[6]], shapes["right_ledge"] + shapes["left_ledge"], contract, (0.20, 0.90, 0.30), 0)
        save_records(document, groups[names[7]], shapes["translucent"], contract, (0.30, 0.95, 1.00), 38)
        mouth_records = [
            shape_record(f"MOUTH_FACET_{index}_{panel['name']}", f"TRANSLUCENT MOUTH FACET {panel['name']}", "mouth", panel["shape"])
            for index, panel in enumerate(shapes["mouth"]["panels"], start=1)
        ]
        mouth_records.append(shape_record("MOUTH_CENTER_SEAM_SEAL", "TRANSLUCENT CENTER-SEAM DUST SEAL", "mouth", shapes["mouth"]["seam"]))
        save_records(document, groups[names[8]], mouth_records, contract, (0.35, 1.00, 0.90), 30)
        save_records(document, groups[names[9]], shapes["mouth"]["panel_tabs"] + shapes["mouth"]["head_tabs"], contract, (0.95, 0.55, 0.15), 0)
        save_records(document, groups[names[10]], shapes["mouth"]["bores"] + shapes["mouth"]["screws"] + shapes["mouth"]["washers"], contract, (0.30, 0.30, 0.34), 25)
        save_records(document, groups[names[11]], shapes["manual_sources"], contract, (0.15, 0.85, 1.00), 55)
        save_records(document, groups[names[12]], shapes["hidden_roots"], contract, (0.85, 0.20, 0.90), 10)
        save_records(document, groups[names[13]], shapes["cleanup_evidence"], contract, (1.00, 0.15, 0.12), 45)
        save_records(document, groups[names[14]], shapes["extra_hardware"], contract, (0.72, 0.72, 0.76), 0)
        save_records(document, groups[names[15]], shapes["extra_cutters"], contract, (0.95, 0.15, 0.15), 78)
        for name in (
            names[4], names[5], names[10], names[11], names[12], names[13], names[15]
        ):
            for obj in groups[name].Group:
                if getattr(obj, "ViewObject", None) is not None:
                    obj.ViewObject.Visibility = False
        decision = document.addObject("App::FeaturePython", "V2_REVIEW_DECISION")
        decision.Label = "REVIEW — FIVE APPROVED LOWER-FRONT CLEANUPS"
        decision.addProperty("App::PropertyString", "Authority", "Review Control")
        decision.addProperty("App::PropertyString", "Editability", "Review Control")
        decision.addProperty("App::PropertyString", "ReleaseHold", "Review Control")
        decision.Authority = contract["authority"]
        decision.Editability = "Every owner, ledge, translucent component, mouth part, cleanup reference, and hardware reference remains separately selectable."
        decision.ReleaseHold = contract["decision"]["release_hold"]
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
    result, shapes = build()
    if args.mode == "feasibility":
        if args.report is None or not str(args.report.resolve()).startswith("/tmp/"):
            raise RuntimeError("feasibility requires a fresh /tmp report")
        if args.report.exists():
            raise RuntimeError(f"feasibility report already exists: {args.report}")
        args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": result["status"],
            "failed_checks": result["failed_checks"],
            "fin_removed_mm3": result["measurements"]["face30_fin_removed_mm3"],
            "manual_missing_mm3": result["measurements"]["manual_flange_missing_mm3"],
            "nose_length_mm": result["measurements"]["component_021_kept_length_mm"],
            "outboard_station": result["measurements"]["outboard_station"],
        }, sort_keys=True))
        return 0 if result["status"].startswith("PASS__") else 1
    fcstd, validation = save_review(result, shapes)
    print(json.dumps({"status": result["status"], "fcstd": str(fcstd), "validation": str(validation)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
