#!/usr/bin/env python3
"""Build the isolated V5 long-ledge lower/rear connection review.

The proposal is one separate front-owned ledge with two drilled M3 stations.
V4 front/rear shapes are reconstructed and measured but never cut, fused,
healed, translated in place, saved, mirrored, or exported.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
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
    expected = "cat-head-right-lower-rear-v5-long-ledge-interface-review-v5"
    if contract.get("schema_version") != expected:
        raise RuntimeError("unexpected V5 long-ledge contract schema")
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


def common_volume(left: Any, right: Any) -> float:
    common = left.common(right)
    if common.isNull():
        return 0.0
    return max(0.0, float(common.Volume))


def shape_metrics(shape: Any) -> dict[str, Any]:
    return {
        "shape_type": str(shape.ShapeType),
        "solid_count": len(shape.Solids),
        "shell_count": len(shape.Shells),
        "face_count": len(shape.Faces),
        "volume_mm3": float(shape.Volume),
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
    }


def one_valid_closed_solid(shape: Any) -> bool:
    return (
        not shape.isNull()
        and shape.isValid()
        and shape.isClosed()
        and len(shape.Solids) == 1
        and float(shape.Volume) > 0.0
    )


def bbox_overlaps(left: Any, right: Any, padding: float = 1.0e-7) -> bool:
    a = left.BoundBox
    b = right.BoundBox
    return not (
        float(a.XMax) < float(b.XMin) - padding
        or float(b.XMax) < float(a.XMin) - padding
        or float(a.YMax) < float(b.YMin) - padding
        or float(b.YMax) < float(a.YMin) - padding
        or float(a.ZMax) < float(b.ZMin) - padding
        or float(b.ZMax) < float(a.ZMin) - padding
    )


def per_record_common(shape: Any, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = []
    for record in records:
        owner_shape = record["shape"]
        volume = 0.0
        if bbox_overlaps(shape, owner_shape):
            volume = common_volume(shape, owner_shape)
        results.append({
            "component_index": int(record["component_index"]),
            "name": str(record["name"]),
            "owner": str(record["owner"]),
            "common_mm3": volume,
        })
    return results


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
    inward_min: float,
    inward_max: float,
) -> Any:
    def point(u_value: float, n_value: float) -> Any:
        return (
            origin
            + axis_u * u_value
            + cross_per_n * n_value
            + inward * inward_min
        )

    points = [
        point(u_min, n_min),
        point(u_max, n_min),
        point(u_max, n_max),
        point(u_min, n_max),
    ]
    wire = Part.makePolygon(points + [points[0]])
    face = Part.Face(wire)
    return face.extrude(inward * (inward_max - inward_min)).removeSplitter()


def make_hex_prism(
    Part: Any,
    center: Any,
    axis_u: Any,
    axis_cross: Any,
    inward: Any,
    inward_start: float,
    height: float,
    across_flats: float,
) -> Any:
    radius = across_flats / math.sqrt(3.0)
    base = center + inward * inward_start
    points = []
    for index in range(6):
        angle = math.radians(30.0 + index * 60.0)
        points.append(
            base
            + axis_u * (radius * math.cos(angle))
            + axis_cross * (radius * math.sin(angle))
        )
    face = Part.Face(Part.makePolygon(points + [points[0]]))
    return face.extrude(inward * height).removeSplitter()


def expanded_bbox_box(Part: Any, App: Any, shape: Any, margin: float) -> Any:
    box = shape.BoundBox
    base = App.Vector(
        float(box.XMin) - margin,
        float(box.YMin) - margin,
        float(box.ZMin) - margin,
    )
    return Part.makeBox(
        float(box.XLength) + 2.0 * margin,
        float(box.YLength) + 2.0 * margin,
        float(box.ZLength) + 2.0 * margin,
        base,
    )


def make_valid_clearance_offset(
    shape: Any,
    distance: float,
    tolerances: Sequence[float],
    volume_epsilon: float,
) -> tuple[Any | None, list[dict[str, Any]]]:
    attempts = []
    for tolerance in map(float, tolerances):
        try:
            offset = shape.makeOffsetShape(
                distance,
                tolerance,
                False,
                False,
                0,
                0,
                True,
            )
            source_outside = 0.0 if offset.isNull() else float(shape.cut(offset).Volume)
            valid = (
                not offset.isNull()
                and offset.isValid()
                and offset.isClosed()
                and len(offset.Solids) >= 1
                and source_outside <= volume_epsilon
            )
            attempts.append({
                "tolerance_mm": tolerance,
                "valid_closed_offset": valid,
                "solid_count": 0 if offset.isNull() else len(offset.Solids),
                "source_outside_offset_mm3": source_outside,
            })
            if valid:
                return offset, attempts
        except Exception as exc:
            attempts.append({
                "tolerance_mm": tolerance,
                "valid_closed_offset": False,
                "error": f"{type(exc).__name__}: {exc}",
            })
    return None, attempts


def line_intersections_along_axis(
    Part: Any,
    shape: Any,
    base: Any,
    axis: Any,
    minimum: float = -8.0,
    maximum: float = 12.0,
) -> list[float]:
    line = Part.makeLine(base + axis * minimum, base + axis * maximum)
    section = shape.section(line)
    return sorted({
        round(float((vertex.Point - base).dot(axis)), 9)
        for vertex in section.Vertexes
    })


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


def disposable_finalization(
    proposal: Any,
    bores: list[Any],
    nut_pockets: list[Any],
    contract: dict[str, Any],
) -> dict[str, bool]:
    import FreeCAD as App  # type: ignore

    document = App.newDocument("DISPOSABLE_V5_LONG_LEDGE_FINALIZATION")
    try:
        target = document.addObject("Part::Feature", "TARGET_LONG_LEDGE")
        target.Shape = proposal
        target.addProperty("App::PropertyString", "Authority", "Review Control")
        target.addProperty("App::PropertyString", "Owner", "Review Control")
        target.Authority = contract["authority"]
        target.Owner = contract["ledge"]["owner"]
        for index, (bore, pocket) in enumerate(zip(bores, nut_pockets), start=1):
            for kind, shape in (("BORE", bore), ("POCKET", pocket)):
                obj = document.addObject("Part::Feature", f"{kind}_{index}")
                obj.Shape = shape
                obj.addProperty("App::PropertyString", "Authority", "Review Control")
                obj.Authority = contract["authority"]
        document.recompute()
        if target.Shape.isNull() or not one_valid_closed_solid(target.Shape):
            raise RuntimeError("disposable V5 target assignment failed")
        if str(target.Owner) != contract["ledge"]["owner"]:
            raise RuntimeError("disposable V5 typed owner assignment failed")
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


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    contract = load_contract()
    for item in contract["inputs"].values():
        require_hash(item)
    v4 = load_module(require_hash(contract["inputs"]["v4_generator"]), "v4_for_ledge_v5")
    (
        v4_result,
        retained,
        cassette,
        mesh_only,
        straight_marker,
        eye_objects,
    ) = v4.build()
    if v4_result.get("status") != "PASS__V4_SEAM_CLEANUP_REVIEW_READY__NOT_PRINT_RELEASED":
        raise RuntimeError("pinned V4 reconstruction did not pass")

    front_001_record = next(
        record for record in retained if int(record["component_index"]) == 1
    )
    rear_001_record = next(
        record for record in cassette if int(record["component_index"]) == 1
    )
    front_001 = front_001_record["shape"]
    rear_001 = rear_001_record["shape"]
    front_volume_before = float(front_001.Volume)
    rear_volume_before = float(rear_001.Volume)
    rear_all = Part.makeCompound([record["shape"] for record in cassette])

    frame = contract["seam_frame"]
    origin = vec(App, frame["origin_world_mm"])
    axis_u = vec(App, frame["axis_u"])
    axis_v = vec(App, frame["axis_v_shell_inward"])
    axis_n = vec(App, frame["axis_n_toward_rear"])
    axis_u.normalize()
    axis_v.normalize()
    axis_n.normalize()
    slope = float(frame["surface_v_per_n"])
    cross_per_n = axis_n + axis_v * slope
    cross_unit = App.Vector(cross_per_n.x, cross_per_n.y, cross_per_n.z)
    cross_unit.normalize()
    inward = axis_v - axis_n * slope
    inward.normalize()
    basis_max_dot = max(
        abs(float(axis_u.dot(cross_unit))),
        abs(float(axis_u.dot(inward))),
        abs(float(cross_unit.dot(inward))),
    )
    if basis_max_dot > 1.0e-8:
        raise RuntimeError(f"V5 measured seam basis is not orthogonal: {basis_max_dot}")

    ledge = contract["ledge"]
    u_min = float(ledge["u_min_mm"])
    u_max = float(ledge["u_max_mm"])
    n_min = float(ledge["n_min_mm"])
    n_max = float(ledge["n_max_mm"])
    bearing = float(ledge["bearing_clearance_inward_mm"])
    shelf_end = bearing + float(ledge["shelf_thickness_mm"])
    shelf = make_prism(
        Part, origin, axis_u, cross_per_n, inward,
        u_min, u_max, n_min, n_max, bearing, shelf_end,
    )
    root = make_prism(
        Part, origin, axis_u, cross_per_n, inward,
        u_min, u_max,
        float(ledge["front_root_n_min_mm"]),
        float(ledge["front_root_n_max_mm"]),
        -float(ledge["front_root_embed_outward_mm"]),
        shelf_end,
    )
    raw_ledge = shelf.fuse(root).removeSplitter()

    fasteners = contract["fasteners"]
    station_n = float(fasteners["station_n_mm"])
    stations = [float(value) for value in fasteners["station_u_mm"]]
    pad_half_u = float(ledge["local_pad_u_width_mm"]) / 2.0
    pad_half_n = float(ledge["local_pad_n_width_mm"]) / 2.0
    pad_end = bearing + float(ledge["local_pad_total_depth_mm"])
    pads = []
    for station_u in stations:
        pad = make_prism(
            Part, origin, axis_u, cross_per_n, inward,
            station_u - pad_half_u, station_u + pad_half_u,
            station_n - pad_half_n, station_n + pad_half_n,
            bearing, pad_end,
        )
        pads.append(pad)
        raw_ledge = raw_ledge.fuse(pad).removeSplitter()

    # Preserve the approved outer envelope while recessing only the measured
    # positive rear-owner sweep conflicts. The expanded intersection boxes are
    # deterministic, conservative, and remain part of this interface bucket.
    clearance_margin = float(ledge["rear_sweep_clearance_margin_mm"])
    clearance_boxes = []
    clearance_records = []
    for slide_distance in map(float, contract["numeric_gates"]["slide_samples_mm"]):
        for record in cassette:
            moved = record["shape"].copy()
            moved.translate(cross_unit * slide_distance)
            if not bbox_overlaps(raw_ledge, moved):
                continue
            intersection = raw_ledge.common(moved)
            volume = 0.0 if intersection.isNull() else max(0.0, float(intersection.Volume))
            if volume <= float(contract["numeric_gates"]["volume_epsilon_mm3"]):
                continue
            clearance_boxes.append(expanded_bbox_box(Part, App, intersection, clearance_margin))
            clearance_records.append({
                "rear_slide_distance_mm": slide_distance,
                "component_index": int(record["component_index"]),
                "name": str(record["name"]),
                "exact_common_before_clearance_mm3": volume,
            })
    for clearance_box in clearance_boxes:
        raw_ledge = raw_ledge.cut(clearance_box).removeSplitter()

    # Positive-common sweep pockets do not cover close-but-disjoint owners at
    # the seated pose. Attribution proved only components 015 and 045 are below
    # the gate. Cut their deterministic 0.30 mm expanded bounding pockets; the
    # final topology, root, penetration, and distance gates remain fail closed.
    volume_epsilon = float(contract["numeric_gates"]["volume_epsilon_mm3"])
    assembled_margin = float(ledge["rear_assembled_clearance_margin_mm"])
    assembled_required = float(contract["numeric_gates"]["minimum_rear_clearance_mm"])
    assembled_owner_indices = {
        int(value) for value in ledge["rear_assembled_clearance_owner_indices"]
    }
    assembled_clearance_records = []
    selected_records = [
        record for record in cassette
        if int(record["component_index"]) in assembled_owner_indices
    ]
    if {int(record["component_index"]) for record in selected_records} != assembled_owner_indices:
        raise RuntimeError("V5 measured rear clearance owners are missing")
    for record in sorted(selected_records, key=lambda item: int(item["component_index"])):
        component_index = int(record["component_index"])
        distance_before = float(raw_ledge.distToShape(record["shape"])[0])
        pocket = expanded_bbox_box(Part, App, record["shape"], assembled_margin)
        overlap = common_volume(raw_ledge, pocket)
        if overlap <= volume_epsilon:
            raise RuntimeError(
                f"V5 measured rear bounding pocket did not reach ledge: {record['name']}"
            )
        before_volume = float(raw_ledge.Volume)
        raw_ledge = raw_ledge.cut(pocket).removeSplitter()
        box = record["shape"].BoundBox
        assembled_clearance_records.append({
            "method": "measured_owner_expanded_bounding_pocket",
            "component_index": component_index,
            "name": str(record["name"]),
            "owner": str(record["owner"]),
            "distance_before_cut_mm": distance_before,
            "bounding_margin_mm": assembled_margin,
            "owner_world_bbox_minimum_mm": [float(box.XMin), float(box.YMin), float(box.ZMin)],
            "owner_world_bbox_maximum_mm": [float(box.XMax), float(box.YMax), float(box.ZMax)],
            "cutter_common_before_cut_mm3": overlap,
            "ledge_volume_removed_mm3": before_volume - float(raw_ledge.Volume),
        })

    bore_radius = float(fasteners["rear_clearance_diameter_mm"]) / 2.0
    pocket_af = float(fasteners["captive_nyloc_across_flats_mm"])
    pocket_start = shelf_end - 0.10
    pocket_height = pad_end - pocket_start + 0.50
    bores = []
    nut_pockets = []
    centers = []
    for station_u in stations:
        center = origin + axis_u * station_u + cross_per_n * station_n
        centers.append(center)
        bore = Part.makeCylinder(bore_radius, 14.0, center + inward * -4.0, inward)
        pocket = make_hex_prism(
            Part, center, axis_u, cross_unit, inward,
            pocket_start, pocket_height, pocket_af,
        )
        bores.append(bore)
        nut_pockets.append(pocket)

    proposal = raw_ledge
    for cutter in bores + nut_pockets:
        proposal = proposal.cut(cutter).removeSplitter()
    if not one_valid_closed_solid(proposal):
        raise RuntimeError("V5 drilled ledge is not one valid closed solid")

    station_records = []
    washers = []
    screws = []
    nuts = []
    driver_corridors = []
    nut_actual_af = pocket_af - 0.20
    for station_u, center, bore, pocket in zip(stations, centers, bores, nut_pockets):
        intersections = line_intersections_along_axis(Part, rear_001, center, inward)
        if len(intersections) < 2:
            raise RuntimeError(f"rear skin interval missing at M3 station u={station_u}")
        rear_outer = min(intersections)
        rear_inner = max(intersections)
        washer_thickness = float(fasteners["washer_thickness_mm"])
        washer_outer = Part.makeCylinder(
            float(fasteners["washer_outer_diameter_mm"]) / 2.0,
            washer_thickness,
            center + inward * (rear_outer - washer_thickness),
            inward,
        )
        washer_inner = Part.makeCylinder(
            bore_radius,
            washer_thickness + 0.02,
            center + inward * (rear_outer - washer_thickness - 0.01),
            inward,
        )
        washer = washer_outer.cut(washer_inner).removeSplitter()
        washers.append(washer)

        shaft_start = rear_outer - washer_thickness
        shaft = Part.makeCylinder(
            1.5,
            float(fasteners["screw_length_mm"]),
            center + inward * shaft_start,
            inward,
        )
        head_height = float(fasteners["screw_head_height_mm"])
        head = Part.makeCylinder(
            float(fasteners["screw_head_diameter_mm"]) / 2.0,
            head_height,
            center + inward * (shaft_start - head_height),
            inward,
        )
        screws.append(shaft.fuse(head).removeSplitter())

        nut_outer = make_hex_prism(
            Part, center, axis_u, cross_unit, inward,
            pocket_start + 0.10,
            float(fasteners["captive_nyloc_height_mm"]),
            nut_actual_af,
        )
        nut_hole = Part.makeCylinder(
            1.5,
            float(fasteners["captive_nyloc_height_mm"]) + 0.02,
            center + inward * (pocket_start + 0.09),
            inward,
        )
        nuts.append(nut_outer.cut(nut_hole).removeSplitter())

        corridor_length = float(fasteners["driver_corridor_length_mm"])
        corridor = Part.makeCylinder(
            float(fasteners["driver_corridor_diameter_mm"]) / 2.0,
            corridor_length,
            center + inward * (shaft_start - head_height - 0.10 - corridor_length),
            inward,
        )
        driver_corridors.append(corridor)
        station_records.append({
            "u_mm": station_u,
            "n_mm": station_n,
            "rear_axis_intersections_inward_mm": intersections,
            "rear_outer_inward_mm": rear_outer,
            "rear_inner_inward_mm": rear_inner,
            "rear_skin_thickness_mm": rear_inner - rear_outer,
            "rear_clearance_common_mm3": common_volume(rear_001, bore),
            "finished_ledge_bore_residual_mm3": common_volume(proposal, bore),
            "finished_ledge_nut_pocket_residual_mm3": common_volume(proposal, pocket),
            "nut_to_finished_ledge_distance_mm": float(nuts[-1].distToShape(proposal)[0]),
        })

    front_root_overlap = common_volume(proposal, front_001)
    rear_common_records = per_record_common(proposal, cassette)
    rear_common_total = sum(item["common_mm3"] for item in rear_common_records)
    rear_distance_records = sorted(
        [
            {
                "component_index": int(record["component_index"]),
                "name": str(record["name"]),
                "owner": str(record["owner"]),
                "distance_mm": float(proposal.distToShape(record["shape"])[0]),
            }
            for record in cassette
        ],
        key=lambda item: item["distance_mm"],
    )
    rear_minimum_clearance = rear_distance_records[0]["distance_mm"]
    other_front = [record for record in retained if record is not front_001_record]
    non_target_front_records = per_record_common(proposal, other_front)
    non_target_front_common = sum(item["common_mm3"] for item in non_target_front_records)

    driver_records = []
    all_existing_records = retained + cassette
    for station_u, corridor in zip(stations, driver_corridors):
        contacts = per_record_common(corridor, all_existing_records)
        driver_records.append({
            "u_mm": station_u,
            "driver_corridor_common_mm3": sum(item["common_mm3"] for item in contacts),
            "contacts": [item for item in contacts if item["common_mm3"] > 0.0],
        })

    slide_records = []
    for distance in map(float, contract["numeric_gates"]["slide_samples_mm"]):
        relative_ledge = proposal.copy()
        relative_ledge.translate(cross_unit * -distance)
        contacts = per_record_common(relative_ledge, cassette)
        slide_records.append({
            "rear_slide_distance_mm": distance,
            "rear_slide_common_mm3": sum(item["common_mm3"] for item in contacts),
            "contacts": [item for item in contacts if item["common_mm3"] > 0.0],
        })

    u_edge = min(stations[0] - u_min, u_max - stations[-1]) - bore_radius
    n_edge = min(station_n - n_min, n_max - station_n) - bore_radius
    bore_edge_material = min(u_edge, n_edge)
    gates = contract["numeric_gates"]
    epsilon = float(gates["volume_epsilon_mm3"])
    checks = {
        "pinned_v4_reconstruction_passes": True,
        "measured_frame_is_orthogonal": basis_max_dot <= 1.0e-8,
        "ledge_is_one_valid_closed_solid": one_valid_closed_solid(proposal),
        "front_root_overlap_meets_minimum": (
            front_root_overlap >= float(gates["minimum_front_root_overlap_mm3"])
        ),
        "non_target_front_owner_penetration_is_zero": (
            non_target_front_common <= float(gates["maximum_non_target_front_common_mm3"])
        ),
        "rear_penetration_is_zero": rear_common_total <= epsilon,
        "rear_minimum_clearance_meets_gate": (
            rear_minimum_clearance + float(gates["distance_epsilon_mm"])
            >= float(gates["minimum_rear_clearance_mm"])
        ),
        "two_rear_clearance_paths_exist": (
            len(station_records) == 2
            and all(
                record["rear_clearance_common_mm3"]
                >= float(gates["minimum_rear_hole_common_mm3"])
                for record in station_records
            )
        ),
        "finished_ledge_bores_are_open": all(
            record["finished_ledge_bore_residual_mm3"] <= epsilon
            for record in station_records
        ),
        "finished_nut_pockets_are_open": all(
            record["finished_ledge_nut_pocket_residual_mm3"] <= epsilon
            for record in station_records
        ),
        "captive_nuts_have_radial_clearance": (
            (pocket_af - nut_actual_af) / 2.0
            >= float(gates["minimum_nut_radial_clearance_mm"])
            and all(record["nut_to_finished_ledge_distance_mm"] > 0.0 for record in station_records)
        ),
        "bore_edge_material_meets_gate": (
            bore_edge_material >= float(gates["minimum_bore_to_edge_material_mm"])
        ),
        "fastener_station_span_is_exact": (
            abs(stations[-1] - stations[0] - float(fasteners["station_span_mm"])) <= 1.0e-12
        ),
        "driver_corridors_clear_existing_geometry": all(
            record["driver_corridor_common_mm3"] <= epsilon
            for record in driver_records
        ),
        "rear_removal_slide_is_clear": all(
            record["rear_slide_common_mm3"] <= epsilon
            for record in slide_records
        ),
        "v4_front_component_001_unmodified": (
            abs(float(front_001.Volume) - front_volume_before) <= epsilon
        ),
        "v4_rear_component_001_unmodified": (
            abs(float(rear_001.Volume) - rear_volume_before) <= epsilon
        ),
        "v4_component_001_volumes_match_pinned_validation": (
            abs(
                front_volume_before
                - float(v4_result["preserved_component_001_front_metrics"]["volume_mm3"])
            ) <= epsilon
            and abs(
                rear_volume_before
                - float(v4_result["preserved_component_001_rear_metrics"]["volume_mm3"])
            ) <= epsilon
        ),
    }
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        diagnostic = {
            "failed": failed,
            "front_root_overlap_mm3": front_root_overlap,
            "non_target_front_common_mm3": non_target_front_common,
            "non_target_front_contacts": [
                item for item in non_target_front_records if item["common_mm3"] > epsilon
            ],
            "rear_common_mm3": rear_common_total,
            "rear_contacts": [item for item in rear_common_records if item["common_mm3"] > epsilon],
            "rear_minimum_clearance_mm": rear_minimum_clearance,
            "nearest_rear_distance_records": rear_distance_records[:8],
            "stations": station_records,
            "driver": driver_records,
            "slide": slide_records,
            "bore_edge_material_mm": bore_edge_material,
        }
        raise RuntimeError("V5 long-ledge gates failed: " + json.dumps(diagnostic, sort_keys=True))

    finalization = disposable_finalization(proposal, bores, nut_pockets, contract)
    result = {
        "schema_version": "cat-head-right-lower-rear-v5-long-ledge-interface-validation-v5",
        "status": "PASS__V5_LONG_LEDGE_INTERFACE_REVIEW_READY__NOT_PRINT_RELEASED",
        "authority": contract["authority"],
        "input_sha256": {
            name: item["sha256"] for name, item in contract["inputs"].items()
        },
        "measurement_evidence": contract["measurement_evidence"],
        "checks": checks,
        "measurements": {
            "basis_max_absolute_dot": basis_max_dot,
            "surface_cross_unit": [float(cross_unit.x), float(cross_unit.y), float(cross_unit.z)],
            "inward_unit": [float(inward.x), float(inward.y), float(inward.z)],
            "ledge_metrics": shape_metrics(proposal),
            "front_root_overlap_mm3": front_root_overlap,
            "non_target_front_common_mm3": non_target_front_common,
            "rear_common_mm3": rear_common_total,
            "rear_minimum_clearance_mm": rear_minimum_clearance,
            "nearest_rear_distance_records": rear_distance_records[:8],
            "bore_edge_material_mm": bore_edge_material,
            "fastener_station_span_mm": stations[-1] - stations[0],
            "nut_radial_clearance_mm": (pocket_af - nut_actual_af) / 2.0,
            "rear_sweep_clearance_margin_mm": clearance_margin,
            "rear_sweep_clearance_pocket_count": len(clearance_boxes),
            "rear_sweep_clearance_sources": clearance_records,
            "rear_assembled_clearance_margin_mm": assembled_margin,
            "rear_assembled_clearance_required_mm": assembled_required,
            "rear_assembled_clearance_pocket_count": len(assembled_clearance_records),
            "rear_assembled_clearance_sources": assembled_clearance_records,
            "stations": station_records,
            "driver_corridors": driver_records,
            "rear_slide": slide_records,
        },
        "disposable_finalization": finalization,
        "print_release_holds": [
            "The ledge remains a separate review proposal and is not fused into the front lower head.",
            "The rear clearance bores remain reference cutters and are not cut into the rear lower head.",
            "No left mirror, STL, STEP, 3MF, G-code, slicing, or print release is authorized."
        ],
        "io_trace": {
            "v4_saved": False,
            "canonical_saved": False,
            "review_saved": False,
            "geometry_export_created": False,
            "production_output_created": False,
        },
    }
    shapes = {
        "retained": retained,
        "cassette": cassette,
        "mesh_only": mesh_only,
        "straight_marker": straight_marker,
        "eye_objects": eye_objects,
        "proposal": proposal,
        "bores": bores,
        "nut_pockets": nut_pockets,
        "washers": washers,
        "screws": screws,
        "nuts": nuts,
        "driver_corridors": driver_corridors,
    }
    return result, shapes


def save_review(result: dict[str, Any], shapes: dict[str, Any]) -> tuple[Path, Path]:
    import FreeCAD as App  # type: ignore

    contract = load_contract()
    output_dir = (PROJECT_ROOT / contract["outputs"]["directory"]).resolve()
    if output_dir.exists():
        raise RuntimeError(f"review output already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    document = App.newDocument("RIGHT_LOWER_REAR_V5_LONG_LEDGE_INTERFACE_REVIEW_ONLY_V5")
    try:
        front_group = document.addObject("App::DocumentObjectGroup", "REFERENCE_V4_FRONT_LOWER")
        rear_group = document.addObject("App::DocumentObjectGroup", "REFERENCE_V4_REAR_LOWER")
        mesh_group = document.addObject("App::DocumentObjectGroup", "REFERENCE_V4_MESH_ONLY")
        proposal_group = document.addObject("App::DocumentObjectGroup", "PROPOSED_V5_LONG_LEDGE")
        hardware_group = document.addObject("App::DocumentObjectGroup", "REFERENCE_TWO_M3_FASTENERS")
        cutter_group = document.addObject("App::DocumentObjectGroup", "REFERENCE_REAR_HOLES_AND_TOOL_ACCESS")
        eye_group = document.addObject("App::DocumentObjectGroup", "REFERENCE_RELEASED_V3_RIGHT_EYE")
        for prefix, group, records, color, transparency in (
            ("FRONT", front_group, shapes["retained"], (0.30, 0.62, 0.94), 18),
            ("REAR", rear_group, shapes["cassette"], (1.00, 0.47, 0.10), 72),
            ("MESH", mesh_group, shapes["mesh_only"], (0.65, 0.65, 0.68), 60),
        ):
            for index, record in enumerate(records, start=1):
                add_feature(
                    document, group, f"{prefix}_{index:03d}",
                    f"REFERENCE — {record['owner'].upper()} — {record['name']}",
                    record["shape"], contract["authority"], color, transparency,
                )
        ledge_obj = add_feature(
            document, proposal_group, "PROPOSED_CONTINUOUS_LONG_LEDGE",
            "PROPOSED — 72 MM CONTINUOUS FRONT-OWNED LEDGE",
            shapes["proposal"], contract["authority"], (0.25, 0.95, 0.30), 0,
        )
        ledge_obj.addProperty("App::PropertyString", "Owner", "Review Control")
        ledge_obj.addProperty("App::PropertyLength", "BearingClearance", "Interface")
        ledge_obj.addProperty("App::PropertyLength", "ShelfThickness", "Interface")
        ledge_obj.Owner = contract["ledge"]["owner"]
        ledge_obj.BearingClearance = float(contract["ledge"]["bearing_clearance_inward_mm"])
        ledge_obj.ShelfThickness = float(contract["ledge"]["shelf_thickness_mm"])
        marker = add_feature(
            document, proposal_group, "PRESERVED_V4_AXIS_STRAIGHT_SEAM",
            "REFERENCE — APPROVED V4 AXIS-STRAIGHT SEAM",
            shapes["straight_marker"], contract["authority"], (0.10, 1.00, 0.20), 0,
        )
        if getattr(marker, "ViewObject", None) is not None:
            marker.ViewObject.LineWidth = 6.0
        for index, (bore, pocket, washer, screw, nut, corridor) in enumerate(zip(
            shapes["bores"], shapes["nut_pockets"], shapes["washers"],
            shapes["screws"], shapes["nuts"], shapes["driver_corridors"],
        ), start=1):
            add_feature(
                document, cutter_group, f"REAR_CLEARANCE_CUTTER_{index}",
                f"REFERENCE — REAR Ø3.4 CLEARANCE CUTTER {index}", bore,
                contract["authority"], (0.95, 0.15, 0.15), 74,
            )
            add_feature(
                document, cutter_group, f"CAPTIVE_NUT_POCKET_{index}",
                f"REFERENCE — CAPTIVE M3 NYLOC POCKET {index}", pocket,
                contract["authority"], (0.85, 0.20, 0.85), 82,
            )
            add_feature(
                document, cutter_group, f"DRIVER_CORRIDOR_{index}",
                f"REFERENCE — Ø8 DRIVER CORRIDOR {index}", corridor,
                contract["authority"], (1.00, 0.82, 0.10), 84,
            )
            add_feature(
                document, hardware_group, f"WASHER_{index}",
                f"REFERENCE — 7 MM WASHER {index}", washer,
                contract["authority"], (0.72, 0.72, 0.75), 0,
            )
            add_feature(
                document, hardware_group, f"M3X16_SCREW_{index}",
                f"REFERENCE — M3×16 SCREW {index}", screw,
                contract["authority"], (0.38, 0.38, 0.42), 0,
            )
            add_feature(
                document, hardware_group, f"M3_NYLOC_{index}",
                f"REFERENCE — CAPTIVE M3 NYLOC {index}", nut,
                contract["authority"], (0.55, 0.55, 0.60), 0,
            )
        for index, (name, shape) in enumerate(shapes["eye_objects"], start=1):
            add_feature(
                document, eye_group, f"EYE_{index:02d}",
                f"REFERENCE — RELEASED V3 — {name}", shape,
                contract["authority"], (0.35, 0.95, 0.55), 88,
            )
        decision = document.addObject("App::FeaturePython", "V5_INTERFACE_DECISION")
        decision.Label = "REVIEW — ONE LONG LEDGE + TWO M3 STATIONS"
        decision.addProperty("App::PropertyString", "Authority", "Review Control")
        decision.addProperty("App::PropertyString", "Installation", "Review Control")
        decision.addProperty("App::PropertyString", "Hold", "Review Control")
        decision.Authority = contract["authority"]
        decision.Installation = "Rear bears on front ledge; insert two M3×16 screws from rear; captive M3 nylocs on inward side."
        decision.Hold = "Proposal only: ledge not fused and rear holes not cut."
        proposal_group.addObject(decision)
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
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": result["status"],
            "front_root_overlap_mm3": result["measurements"]["front_root_overlap_mm3"],
            "rear_minimum_clearance_mm": result["measurements"]["rear_minimum_clearance_mm"],
            "bore_edge_material_mm": result["measurements"]["bore_edge_material_mm"],
        }, sort_keys=True))
        return 0
    fcstd, validation = save_review(result, shapes)
    print(json.dumps({
        "status": result["status"],
        "fcstd": str(fcstd),
        "validation": str(validation),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
