#!/usr/bin/env python3
"""Build the modular bilateral lower-front closure review.

Every opaque owner, mirrored owner, translucent component, mouth facet,
center seal, mounting tab, cutter, and hardware reference remains a separate
document object.  This review never overwrites, fuses into, or exports any
accepted source.
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
from typing import Any, Iterable, Sequence


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
REPO_ROOT = PROJECT_ROOT.parents[4]
CONTRACT_PATH = HERE / "contract.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    expected = "cat-head-lower-front-bilateral-modular-closure-review-v1"
    if contract.get("schema_version") != expected:
        raise RuntimeError("unexpected lower-front modular closure contract schema")
    return contract


def input_path(item: dict[str, Any]) -> Path:
    if "path_from_repo_root" in item:
        return (REPO_ROOT / item["path_from_repo_root"]).resolve()
    return (PROJECT_ROOT / item["path"]).resolve()


def require_hash(item: dict[str, Any]) -> Path:
    path = input_path(item)
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


def vec(App: Any, values: Sequence[float]) -> Any:
    return App.Vector(*map(float, values))


def unit(vector: Any) -> Any:
    result = vector * 1.0
    if float(result.Length) <= 1.0e-12:
        raise RuntimeError("zero-length vector")
    result.normalize()
    return result


def point_values(point: Any) -> list[float]:
    return [float(point.x), float(point.y), float(point.z)]


def progress(stage: str, **values: Any) -> None:
    print(json.dumps({"progress": stage, **values}, sort_keys=True), flush=True)


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_")
    return cleaned or "OBJECT"


def common_volume(left: Any, right: Any) -> float:
    common = left.common(right)
    return 0.0 if common.isNull() else max(0.0, float(common.Volume))


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


def records_common(
    left: Sequence[dict[str, Any]],
    right: Sequence[dict[str, Any]],
) -> tuple[float, list[dict[str, Any]]]:
    total = 0.0
    contacts = []
    for a in left:
        for b in right:
            if not bbox_overlaps(a["shape"], b["shape"]):
                continue
            volume = common_volume(a["shape"], b["shape"])
            if volume <= 0.0:
                continue
            total += volume
            contacts.append({
                "left": str(a["name"]),
                "right": str(b["name"]),
                "common_mm3": volume,
            })
    return total, contacts


def records_distance(
    left: Sequence[dict[str, Any]],
    right: Sequence[dict[str, Any]],
) -> tuple[float, dict[str, Any]]:
    def lower_bound(a: Any, b: Any) -> float:
        dx = max(
            0.0,
            float(a.XMin) - float(b.XMax),
            float(b.XMin) - float(a.XMax),
        )
        dy = max(
            0.0,
            float(a.YMin) - float(b.YMax),
            float(b.YMin) - float(a.YMax),
        )
        dz = max(
            0.0,
            float(a.ZMin) - float(b.ZMax),
            float(b.ZMin) - float(a.ZMax),
        )
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    candidates = sorted(
        (
            (lower_bound(a["shape"].BoundBox, b["shape"].BoundBox), a, b)
            for a in left for b in right
        ),
        key=lambda item: item[0],
    )
    best = math.inf
    owner: dict[str, Any] = {}
    exact_pair_count = 0
    for bound, a, b in candidates:
        if bound >= best:
            break
        distance = float(a["shape"].distToShape(b["shape"])[0])
        exact_pair_count += 1
        if distance < best:
            best = distance
            owner = {
                "left": str(a["name"]),
                "right": str(b["name"]),
                "distance_mm": distance,
                "bounding_lower_bound_mm": bound,
                "exact_pair_count": exact_pair_count,
            }
            if best <= 0.0:
                break
    return best, owner


def volume_weighted_center(shape: Any, App: Any) -> Any:
    solids = [solid for solid in shape.Solids if float(solid.Volume) > 0.0]
    if solids:
        total = sum(float(solid.Volume) for solid in solids)
        center = App.Vector(0.0, 0.0, 0.0)
        for solid in solids:
            center += solid.CenterOfMass * (float(solid.Volume) / total)
        return center
    box = shape.BoundBox
    return App.Vector(
        (float(box.XMin) + float(box.XMax)) / 2.0,
        (float(box.YMin) + float(box.YMax)) / 2.0,
        (float(box.ZMin) + float(box.ZMax)) / 2.0,
    )


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


def valid_closed(shape: Any) -> bool:
    return (
        not shape.isNull()
        and shape.isValid()
        and shape.isClosed()
        and len(shape.Solids) >= 1
        and float(shape.Volume) > 0.0
    )


def mirror_x0(shape: Any, App: Any) -> Any:
    mirrored = shape.copy()
    returned = mirrored.mirror(App.Vector(0.0, 0.0, 0.0), App.Vector(1.0, 0.0, 0.0))
    if returned is not None:
        mirrored = returned
    if mirrored is None or mirrored.isNull():
        raise RuntimeError("X=0 mirror returned a null shape")
    return mirrored.removeSplitter()


def declared_group_anchors(
    evidence: dict[str, Any], App: Any
) -> list[dict[str, Any]]:
    anchors = []
    for kind in ("hooks", "screw_mounts"):
        for mount in evidence.get(kind, []):
            anchors.append({
                "kind": kind,
                "owner_shell": str(mount.get("owner_shell", "")),
                "point": vec(App, mount["anchor_mm"]),
            })
    return anchors


def resolve_translucent_opaque_conflicts(
    records: Sequence[dict[str, Any]],
    opaque: Sequence[dict[str, Any]],
    group_evidence: dict[str, Any],
    radius: float,
    epsilon: float,
    App: Any,
    Part: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Clear review copies outside declared Gate8 attachment zones only."""
    resolved = []
    audit = []
    for record in records:
        source = record["shape"]
        work = source
        anchors = declared_group_anchors(
            group_evidence.get(record["group_name"], {}), App
        )
        cuts = []
        candidates = [
            owner for owner in opaque
            if bbox_overlaps(source, owner["shape"])
        ]
        common = (
            source.common(Part.makeCompound([owner["shape"] for owner in candidates]))
            if candidates else Part.Shape()
        )
        rejected = []
        for solid_index, solid in enumerate(common.Solids, start=1):
            if float(solid.Volume) <= epsilon:
                continue
            center = solid.CenterOfMass
            nearest_distance = min(
                (float((center - anchor["point"]).Length) for anchor in anchors),
                default=math.inf,
            )
            if nearest_distance > radius:
                rejected.append((solid_index, solid, nearest_distance))
        for solid_index, cutter, nearest_distance in rejected:
            before = float(work.Volume)
            work = work.cut(cutter).removeSplitter()
            if work.isNull():
                raise RuntimeError(
                    f"opaque clearance consumed translucent component: {record['name']}"
                )
            cuts.append({
                "opaque_owner": "aggregate_immutable_opaque_owner_set",
                "intersection_solid_index": solid_index,
                "outside_attachment_zone_common_mm3": float(cutter.Volume),
                "nearest_declared_anchor_distance_mm": nearest_distance,
                "component_volume_removed_mm3": before - float(work.Volume),
            })
        if not valid_closed(work):
            raise RuntimeError(
                f"clearanced translucent component is not valid and closed: {record['name']}"
            )
        item = dict(record)
        item["shape"] = work
        item["label"] = (
            f"CLEARANCED REVIEW COPY — {record['group_name']} — "
            f"COMPONENT {record['component_index']:02d}"
        )
        resolved.append(item)
        audit.append({
            "name": record["name"],
            "group_name": record["group_name"],
            "source_volume_mm3": float(source.Volume),
            "resolved_volume_mm3": float(work.Volume),
            "volume_removed_mm3": float(source.Volume) - float(work.Volume),
            "declared_anchor_count": len(anchors),
            "cuts": cuts,
        })
    return resolved, audit


def resolve_right_lower_ownership(
    records: Sequence[dict[str, Any]],
    right_upper: Sequence[dict[str, Any]],
    App: Any,
    Part: Any,
    epsilon: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    half_space = Part.makeBox(
        500.0, 1000.0, 1000.0, App.Vector(0.0, -500.0, -500.0)
    )
    resolved = []
    audit = []
    for record in records:
        source = record["shape"]
        work = source
        midline_removed = 0.0
        if float(source.BoundBox.XMin) < -epsilon:
            clipped = source.common(half_space).removeSplitter()
            if clipped.isNull():
                raise RuntimeError(f"X=0 clip removed entire right owner: {record['name']}")
            midline_removed = max(0.0, float(source.Volume) - float(clipped.Volume))
            work = clipped
        upper_contacts = []
        for upper in right_upper:
            if not bbox_overlaps(work, upper["shape"]):
                continue
            overlap = common_volume(work, upper["shape"])
            if overlap <= epsilon:
                continue
            before = float(work.Volume)
            work = work.cut(upper["shape"]).removeSplitter()
            if work.isNull():
                raise RuntimeError(
                    f"canonical upper ownership removed entire lower owner: {record['name']}"
                )
            upper_contacts.append({
                "upper_owner": upper["name"],
                "common_before_cut_mm3": overlap,
                "lower_volume_removed_mm3": before - float(work.Volume),
            })
        if not valid_closed(work):
            raise RuntimeError(
                f"resolved lower owner is not valid and closed: {record['name']}"
            )
        item = dict(record)
        item["shape"] = work
        item["label"] = f"RESOLVED LOWER OWNER — {record['label']}"
        resolved.append(item)
        audit.append({
            "lower_owner": record["name"],
            "source_volume_mm3": float(source.Volume),
            "resolved_volume_mm3": float(work.Volume),
            "midline_volume_removed_mm3": midline_removed,
            "canonical_upper_contacts_removed": upper_contacts,
        })
    return resolved, audit


def load_v34_upper(path: Path, App: Any) -> list[dict[str, Any]]:
    document = App.openDocument(str(path))
    records = []
    try:
        for obj in document.Objects:
            shape = getattr(obj, "Shape", None)
            if shape is None or shape.isNull():
                continue
            identity = f"{obj.Name} {obj.Label}".upper()
            if re.search(r"RETAINED_RIGHT_UPPER_C[0-9]+", identity) is None:
                continue
            records.append({
                "name": str(obj.Name),
                "label": str(obj.Label),
                "owner": "right_upper",
                "shape": shape.copy(),
            })
    finally:
        App.closeDocument(document.Name)
    if not records:
        raise RuntimeError("canonical V34 contains no retained right-upper objects")
    return records


def load_stl_solids(path: Path, tolerance: float, Part: Any, Mesh: Any) -> list[Any]:
    mesh = Mesh.Mesh(str(path))
    converted = Part.Shape()
    converted.makeShapeFromMesh(mesh.Topology, tolerance)
    solids = []
    for shell in converted.Shells:
        if not shell.isClosed():
            continue
        solid = Part.makeSolid(shell)
        if solid.isNull() or float(solid.Volume) <= 0.0:
            continue
        solids.append(solid.removeSplitter())
    if not solids:
        raise RuntimeError(f"STL has no closed convertible solid: {path}")
    return solids


def line_intersection_2d(
    a: tuple[float, float],
    da: tuple[float, float],
    b: tuple[float, float],
    db: tuple[float, float],
) -> tuple[float, float]:
    denominator = da[0] * db[1] - da[1] * db[0]
    if abs(denominator) <= 1.0e-12:
        raise RuntimeError("parallel polygon offset lines")
    delta = (b[0] - a[0], b[1] - a[1])
    scale = (delta[0] * db[1] - delta[1] * db[0]) / denominator
    return (a[0] + da[0] * scale, a[1] + da[1] * scale)


def inset_polygon(points: Sequence[Any], normal: Any, clearance: float, App: Any) -> list[Any]:
    axis_u = unit(points[1] - points[0])
    axis_v = unit(normal.cross(axis_u))
    origin = points[0]
    xy = [
        (float((point - origin).dot(axis_u)), float((point - origin).dot(axis_v)))
        for point in points
    ]
    area2 = sum(
        xy[index][0] * xy[(index + 1) % len(xy)][1]
        - xy[(index + 1) % len(xy)][0] * xy[index][1]
        for index in range(len(xy))
    )
    orientation = 1.0 if area2 > 0.0 else -1.0
    lines = []
    for index, start in enumerate(xy):
        end = xy[(index + 1) % len(xy)]
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        direction = (dx / length, dy / length)
        inward = (-direction[1] * orientation, direction[0] * orientation)
        lines.append((
            (start[0] + inward[0] * clearance, start[1] + inward[1] * clearance),
            direction,
        ))
    result = []
    for index in range(len(xy)):
        previous = lines[(index - 1) % len(lines)]
        current = lines[index]
        x, y = line_intersection_2d(previous[0], previous[1], current[0], current[1])
        result.append(origin + axis_u * x + axis_v * y)
    return result


def polygon_prism(
    points: Sequence[Any],
    direction: Any,
    start: float,
    thickness: float,
    Part: Any,
) -> Any:
    base = [point + direction * start for point in points]
    face = Part.Face(Part.makePolygon(base + [base[0]]))
    return face.extrude(direction * thickness).removeSplitter()


def oriented_box(
    center: Any,
    axis_u: Any,
    axis_v: Any,
    axis_n: Any,
    u_length: float,
    v_min: float,
    v_max: float,
    n_min: float,
    n_max: float,
    Part: Any,
) -> Any:
    half_u = u_length / 2.0
    base = center - axis_u * half_u + axis_v * v_min + axis_n * n_min
    points = [
        base,
        base + axis_u * u_length,
        base + axis_u * u_length + axis_v * (v_max - v_min),
        base + axis_v * (v_max - v_min),
    ]
    face = Part.Face(Part.makePolygon(points + [points[0]]))
    return face.extrude(axis_n * (n_max - n_min)).removeSplitter()


def make_annular_washer(
    center: Any,
    axis: Any,
    outer_diameter: float,
    inner_diameter: float,
    thickness: float,
    Part: Any,
) -> Any:
    outer = Part.makeCylinder(outer_diameter / 2.0, thickness, center, axis)
    inner = Part.makeCylinder(
        inner_diameter / 2.0, thickness + 0.02, center - axis * 0.01, axis
    )
    return outer.cut(inner).removeSplitter()


def mouth_geometry(contract: dict[str, Any], App: Any, Part: Any) -> dict[str, Any]:
    mouth = contract["mouth"]
    raw_panels = {
        "TRI005": {
            "points": [
                vec(App, [0.189, 0.0, 47.8035]),
                vec(App, [-1.3515, 20.3535, 24.0585]),
                vec(App, [40.5045, 16.551, 20.421]),
            ],
            "outward": vec(App, [-0.1245121902, -0.7573151362, -0.6410698082]),
        },
        "TRI006": {
            "points": [
                vec(App, [0.189, 0.0, 47.8035]),
                vec(App, [-1.3515, 20.3535, 24.0585]),
                vec(App, [-40.5045, 16.551, 20.421]),
            ],
            "outward": vec(App, [0.1330519506, -0.7482143448, -0.6499788248]),
        },
    }
    panel_records = []
    panel_tabs = []
    head_tabs = []
    bores = []
    screws = []
    washers = []
    diagnostics = []
    mount = mouth["mount_pair"]
    for panel_id, source in raw_panels.items():
        points = source["points"]
        outward = unit(source["outward"])
        inward = outward * -1.0
        deep_spec = mouth["deep_body"]
        cap_spec = mouth["visible_cap"]
        deep_points = inset_polygon(
            points, outward, float(deep_spec["perimeter_clearance_mm"]), App
        )
        cap_points = inset_polygon(
            points, outward, float(cap_spec["perimeter_clearance_mm"]), App
        )
        deep = polygon_prism(
            deep_points, inward, float(deep_spec["surface_setback_mm"]),
            float(deep_spec["thickness_mm"]), Part,
        )
        cap = polygon_prism(
            cap_points, inward, float(cap_spec["surface_setback_mm"]),
            float(cap_spec["thickness_mm"]), Part,
        )
        panel = cap.fuse(deep).removeSplitter()
        if not valid_closed(panel):
            raise RuntimeError(f"{panel_id} mouth insert is not valid and closed")
        panel_records.append({
            "name": panel_id,
            "shape": panel,
            "cap": cap,
            "deep": deep,
            "outward": outward,
            "inward": inward,
            "points": points,
        })

        edge_start, edge_end = points[1], points[2]
        edge_axis = unit(edge_end - edge_start)
        edge_midpoint = edge_start + (edge_end - edge_start) * 0.5
        centroid = sum(points[1:], points[0]) * (1.0 / 3.0)
        toward_panel = unit(
            (centroid - edge_midpoint)
            - edge_axis * float((centroid - edge_midpoint).dot(edge_axis))
        )
        depth_axis = inward
        tab_depth = float(mount["tab_depth_mm"])
        tab_thickness = float(mount["tab_face_thickness_mm"])
        surface_setback = float(mount["surface_setback_mm"])
        gap = float(mount["face_gap_mm"])
        panel_tab_raw = oriented_box(
            edge_midpoint, edge_axis, toward_panel, depth_axis,
            float(mount["edge_length_mm"]),
            -1.2, 1.2 + float(mount["panel_root_extension_mm"]),
            surface_setback, surface_setback + tab_depth,
            Part,
        )
        head_tab_raw = oriented_box(
            edge_midpoint, edge_axis, toward_panel, depth_axis,
            float(mount["edge_length_mm"]),
            -1.2 - gap - tab_thickness, -1.2 - gap,
            surface_setback, surface_setback + tab_depth,
            Part,
        )
        bore_center = edge_midpoint + depth_axis * float(mount["bore_depth_position_mm"])
        bore_axis = toward_panel
        bore = Part.makeCylinder(
            float(mount["bore_diameter_mm"]) / 2.0,
            6.6,
            bore_center + bore_axis * (-4.4),
            bore_axis,
        )
        panel_tab = panel_tab_raw.cut(bore).removeSplitter()
        head_tab = head_tab_raw.cut(bore).removeSplitter()
        panel_tabs.append({
            "name": f"{panel_id}_PANEL_FLANGE",
            "panel_id": panel_id,
            "shape": panel_tab,
        })
        head_tabs.append({
            "name": f"{panel_id}_HEAD_FLANGE",
            "panel_id": panel_id,
            "shape": head_tab,
        })
        bores.append({"name": f"{panel_id}_M2P5_BORE", "shape": bore})
        screw = Part.makeCylinder(
            1.25, 8.0, bore_center + bore_axis * (-4.0), bore_axis
        )
        screws.append({"name": f"{panel_id}_M2P5_SHAFT", "shape": screw})
        washer_one = make_annular_washer(
            bore_center + bore_axis * (-1.7), bore_axis,
            float(mount["washer_od_mm"]), float(mount["bore_diameter_mm"]),
            float(mount["washer_thickness_mm"]), Part,
        )
        washer_two = make_annular_washer(
            bore_center + bore_axis * 1.2, bore_axis,
            float(mount["washer_od_mm"]), float(mount["bore_diameter_mm"]),
            float(mount["washer_thickness_mm"]), Part,
        )
        washers.extend([
            {"name": f"{panel_id}_WASHER_PANEL", "shape": washer_one},
            {"name": f"{panel_id}_WASHER_HEAD", "shape": washer_two},
        ])
        diagnostics.append({
            "panel_id": panel_id,
            "edge_start_world_mm": point_values(edge_start),
            "edge_end_world_mm": point_values(edge_end),
            "edge_midpoint_world_mm": point_values(edge_midpoint),
            "toward_panel_axis": point_values(toward_panel),
            "depth_axis": point_values(depth_axis),
            "panel_root_common_mm3": common_volume(panel, panel_tab),
            "pair_common_mm3": common_volume(panel_tab, head_tab),
            "pair_distance_mm": float(panel_tab.distToShape(head_tab)[0]),
        })

    shared_start = vec(App, [-1.3515, 20.3535, 24.0585])
    shared_end = vec(App, [0.189, 0.0, 47.8035])
    seam_axis = unit(shared_end - shared_start)
    average_inward = unit(panel_records[0]["inward"] + panel_records[1]["inward"])
    transverse = unit(average_inward.cross(seam_axis))
    trim = float(mouth["center_seam"]["end_trim_mm"])
    seam_center = (shared_start + shared_end) * 0.5
    seam_length = float((shared_end - shared_start).Length) - 2.0 * trim
    seam = oriented_box(
        seam_center, seam_axis, transverse, average_inward,
        seam_length,
        -float(mouth["center_seam"]["width_mm"]) / 2.0,
        float(mouth["center_seam"]["width_mm"]) / 2.0,
        float(mouth["center_seam"]["surface_setback_mm"]),
        float(mouth["center_seam"]["surface_setback_mm"])
        + float(mouth["center_seam"]["thickness_mm"]),
        Part,
    )
    return {
        "panels": panel_records,
        "seam": seam,
        "panel_tabs": panel_tabs,
        "head_tabs": head_tabs,
        "bores": bores,
        "screws": screws,
        "washers": washers,
        "diagnostics": diagnostics,
    }


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
    obj = document.addObject("Part::Feature", safe_name(name))
    obj.Label = label
    obj.Shape = shape
    obj.addProperty("App::PropertyString", "Authority", "Review Control")
    obj.addProperty("App::PropertyString", "ModularOwner", "Review Control")
    obj.Authority = authority
    obj.ModularOwner = name
    group.addObject(obj)
    if getattr(obj, "ViewObject", None) is not None:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.Transparency = int(transparency)
    return obj


def disposable_finalization(
    shapes: dict[str, Any], contract: dict[str, Any], App: Any
) -> dict[str, bool]:
    document = App.newDocument("DISPOSABLE_LOWER_FRONT_MODULAR_CLOSURE_V1")
    try:
        required = [
            ("RIGHT_LOWER", shapes["right_lower"][0]["shape"]),
            ("LEFT_LOWER", shapes["left_lower"][0]["shape"]),
            ("RIGHT_UPPER", shapes["right_upper"][0]["shape"]),
            ("LEFT_UPPER", shapes["left_upper"][0]["shape"]),
            ("MOUTH_RIGHT", shapes["mouth"]["panels"][0]["shape"]),
            ("MOUTH_LEFT", shapes["mouth"]["panels"][1]["shape"]),
            ("MOUTH_SEAM", shapes["mouth"]["seam"]),
        ]
        for name, shape in required:
            obj = document.addObject("Part::Feature", name)
            obj.Shape = shape
            obj.addProperty("App::PropertyString", "Authority", "Review Control")
            obj.Authority = contract["authority"]
        document.recompute()
        assigned = all(
            document.getObject(name) is not None
            and not document.getObject(name).Shape.isNull()
            for name, _shape in required
        )
        return {
            "target_assignment_ran": True,
            "typed_metadata_assignment_ran": True,
            "document_recompute_ran": True,
            "all_required_modular_shapes_assigned": assigned,
            "save_as_called": False,
            "document_save_called": False,
            "geometry_export_created": False,
        }
    finally:
        App.closeDocument(document.Name)


def build() -> tuple[dict[str, Any], dict[str, Any]]:
    import FreeCAD as App  # type: ignore
    import Mesh  # type: ignore
    import Part  # type: ignore

    contract = load_contract()
    resolved_inputs = {
        name: require_hash(item) for name, item in contract["inputs"].items()
    }
    v5 = load_module(resolved_inputs["v5_generator"], "v5_for_bilateral_closure_v1")
    v5_result, v5_shapes = v5.build()
    if v5_result.get("status") != "PASS__V5_LONG_LEDGE_INTERFACE_REVIEW_READY__NOT_PRINT_RELEASED":
        raise RuntimeError("pinned V5 reconstruction did not pass")
    progress("v5_reconstructed")

    right_lower_raw = [
        {
            "name": f"RIGHT_LOWER_{record['component_index']:03d}_{safe_name(str(record['name']))}",
            "label": f"RIGHT LOWER — {record['name']}",
            "owner": str(record["owner"]),
            "shape": record["shape"],
        }
        for record in v5_shapes["retained"]
    ]
    right_mesh = [
        {
            "name": f"RIGHT_MESH_{index:03d}_{safe_name(str(record['name']))}",
            "label": f"RIGHT MESH CONTEXT — {record['name']}",
            "owner": str(record["owner"]),
            "shape": record["shape"],
        }
        for index, record in enumerate(v5_shapes["mesh_only"], start=1)
    ]
    left_mesh = [
        {
            "name": record["name"].replace("RIGHT_", "LEFT_", 1),
            "label": record["label"].replace("RIGHT ", "LEFT ", 1),
            "owner": "left_mesh_context",
            "shape": mirror_x0(record["shape"], App),
        }
        for record in right_mesh
    ]
    right_upper = load_v34_upper(resolved_inputs["canonical_v34"], App)
    right_lower, lower_ownership_audit = resolve_right_lower_ownership(
        right_lower_raw,
        right_upper,
        App,
        Part,
        float(contract["numeric_gates"]["volume_epsilon_mm3"]),
    )
    left_lower = [
        {
            "name": record["name"].replace("RIGHT_", "LEFT_", 1),
            "label": record["label"].replace("RIGHT ", "LEFT ", 1),
            "owner": "left_lower",
            "shape": mirror_x0(record["shape"], App),
        }
        for record in right_lower
    ]
    left_upper = [
        {
            "name": f"LEFT_{record['name']}",
            "label": str(record["label"]).replace("RIGHT", "LEFT"),
            "owner": "left_upper",
            "shape": mirror_x0(record["shape"], App),
        }
        for record in right_upper
    ]
    progress(
        "opaque_owners_loaded",
        right_lower=len(right_lower),
        right_upper=len(right_upper),
    )
    right_ledge = [{
        "name": "RIGHT_V5_LONG_LEDGE",
        "label": "RIGHT — APPROVED V5 LONG LEDGE (SEPARATE)",
        "owner": "right_lower_front_interface",
        "shape": v5_shapes["proposal"],
    }]
    left_ledge = [{
        "name": "LEFT_V5_LONG_LEDGE",
        "label": "LEFT — MIRRORED V5 LONG LEDGE (SEPARATE)",
        "owner": "left_lower_front_interface",
        "shape": mirror_x0(v5_shapes["proposal"], App),
    }]

    gate8 = json.loads(
        resolved_inputs["gate8_mount_validation"].read_text(encoding="utf-8")
    )
    group_evidence = {
        str(group["name"]): group for group in gate8.get("groups", [])
    }
    translucent = []
    tolerance = float(contract["numeric_gates"]["mesh_conversion_tolerance_mm"])
    for input_name, item in contract["inputs"].items():
        if not input_name.startswith("insert_"):
            continue
        group_name = str(item["group_name"])
        solids = load_stl_solids(resolved_inputs[input_name], tolerance, Part, Mesh)
        for index, solid in enumerate(solids, start=1):
            translucent.append({
                "name": f"{safe_name(group_name).upper()}_COMPONENT_{index:02d}",
                "label": f"TRANSLUCENT — {group_name} — COMPONENT {index:02d}",
                "group_name": group_name,
                "component_index": index,
                "shape": solid,
            })
    progress("translucent_stls_loaded", component_count=len(translucent))

    mouth = mouth_geometry(contract, App, Part)
    progress("mouth_constructed")
    right_left_common, right_left_contacts = records_common(right_lower, left_lower)
    progress(
        "right_left_common_measured",
        common_mm3=right_left_common,
        contacts=right_left_contacts,
    )
    right_lower_upper_common, right_lower_upper_contacts = records_common(
        right_lower, right_upper
    )
    progress(
        "right_lower_upper_common_measured",
        common_mm3=right_lower_upper_common,
        contacts=right_lower_upper_contacts,
    )
    left_lower_upper_common, left_lower_upper_contacts = records_common(
        left_lower, left_upper
    )
    progress(
        "left_lower_upper_common_measured",
        common_mm3=left_lower_upper_common,
        contacts=left_lower_upper_contacts,
    )
    right_left_distance, right_left_nearest = (
        (0.0, {"left": "positive_common", "right": "positive_common", "distance_mm": 0.0})
        if right_left_common > 0.0 else records_distance(right_lower, left_lower)
    )
    right_lower_upper_distance, right_lower_upper_nearest = (
        (0.0, {"left": "positive_common", "right": "positive_common", "distance_mm": 0.0})
        if right_lower_upper_common > 0.0 else records_distance(right_lower, right_upper)
    )
    left_lower_upper_distance, left_lower_upper_nearest = (
        (0.0, {"left": "positive_common", "right": "positive_common", "distance_mm": 0.0})
        if left_lower_upper_common > 0.0 else records_distance(left_lower, left_upper)
    )
    progress("opaque_distances_measured")

    opaque = right_lower + left_lower + right_upper + left_upper + right_ledge + left_ledge
    opaque_compound = Part.makeCompound([record["shape"] for record in opaque])
    right_lower_compound = Part.makeCompound([record["shape"] for record in right_lower])
    left_lower_compound = Part.makeCompound([record["shape"] for record in left_lower])
    gates = contract["numeric_gates"]
    radius = float(contract["numeric_gates"]["mount_attribution_radius_mm"])
    epsilon = float(contract["numeric_gates"]["volume_epsilon_mm3"])
    translucent, translucent_resolution_audit = resolve_translucent_opaque_conflicts(
        translucent, opaque, group_evidence, radius, epsilon, App, Part
    )
    progress("translucent_review_copies_clearanced")
    translucent_audit = []
    unclassified_common = 0.0
    declared_lower_groups = set()
    retained_lower_groups = set()
    for record in translucent:
        progress("translucent_audit_started", component=record["name"])
        evidence = group_evidence.get(record["group_name"], {})
        anchors = declared_group_anchors(evidence, App)
        for anchor in anchors:
            if "lower" in anchor["owner_shell"].lower():
                declared_lower_groups.add(record["group_name"])
        contacts = []
        allowed_common = 0.0
        rejected_common = 0.0
        candidates = [
            owner for owner in opaque
            if bbox_overlaps(record["shape"], owner["shape"])
        ]
        common = (
            record["shape"].common(
                Part.makeCompound([owner["shape"] for owner in candidates])
            )
            if candidates else Part.Shape()
        )
        common_solids = [
            solid for solid in common.Solids
            if float(solid.Volume) > epsilon
        ]
        for solid_index, solid in enumerate(common_solids, start=1):
            volume = float(solid.Volume)
            center = solid.CenterOfMass
            nearest = min(
                (
                    (float((center - anchor["point"]).Length), anchor)
                    for anchor in anchors
                ),
                default=(math.inf, None),
                key=lambda item: item[0],
            )
            attributed = nearest[0] <= radius
            if attributed:
                allowed_common += volume
                if (
                    nearest[1] is not None
                    and "lower" in nearest[1]["owner_shell"].lower()
                    and volume
                    >= float(gates["minimum_retained_lower_mount_common_mm3"])
                ):
                    retained_lower_groups.add(record["group_name"])
            else:
                rejected_common += volume
                unclassified_common += volume
            contacts.append({
                "opaque_owner": "aggregate_immutable_opaque_owner_set",
                "intersection_solid_index": solid_index,
                "common_mm3": volume,
                "common_center_world_mm": point_values(center),
                "nearest_declared_anchor_distance_mm": nearest[0],
                "nearest_declared_anchor_owner": (
                    None if nearest[1] is None else nearest[1]["owner_shell"]
                ),
                "classified_as_declared_attachment": attributed,
            })
        translucent_audit.append({
            "name": record["name"],
            "group_name": record["group_name"],
            "metrics": shape_metrics(record["shape"]),
            "declared_anchor_count": len(anchors),
            "allowed_attachment_common_mm3": allowed_common,
            "unclassified_common_mm3": rejected_common,
            "contacts": contacts,
        })
        progress("translucent_audit_finished", component=record["name"])

    mouth_panel_audit = []
    mouth_minimum_clearance = math.inf
    mouth_common = 0.0
    for panel in mouth["panels"]:
        progress("mouth_panel_audit_started", panel=panel["name"])
        contacts = []
        candidates = [
            owner for owner in opaque
            if bbox_overlaps(panel["shape"], owner["shape"], padding=0.10)
        ]
        candidate_compound = (
            Part.makeCompound([owner["shape"] for owner in candidates])
            if candidates else None
        )
        minimum = (
            float(panel["shape"].distToShape(candidate_compound)[0])
            if candidate_compound is not None
            else float(panel["shape"].distToShape(opaque_compound)[0])
        )
        common = (
            panel["shape"].common(candidate_compound)
            if candidate_compound is not None else Part.Shape()
        )
        volume = 0.0 if common.isNull() else max(0.0, float(common.Volume))
        if volume > epsilon:
            mouth_common += volume
            contacts.append({
                "owner": "aggregate_immutable_opaque_owner_set",
                "common_mm3": volume,
            })
        mouth_minimum_clearance = min(mouth_minimum_clearance, minimum)
        mouth_panel_audit.append({
            "name": panel["name"],
            "metrics": shape_metrics(panel["shape"]),
            "minimum_opaque_clearance_mm": minimum,
            "contacts": contacts,
        })
        progress("mouth_panel_audit_finished", panel=panel["name"])

    tab_audit = []
    for index, diagnostic in enumerate(mouth["diagnostics"]):
        side_opaque = (
            right_lower_compound
            if diagnostic["panel_id"] == "TRI005"
            else left_lower_compound
        )
        head_tab = mouth["head_tabs"][index]["shape"]
        head_common = common_volume(head_tab, side_opaque)
        item = dict(diagnostic)
        item["head_root_common_mm3"] = head_common
        item["panel_tab_metrics"] = shape_metrics(mouth["panel_tabs"][index]["shape"])
        item["head_tab_metrics"] = shape_metrics(head_tab)
        tab_audit.append(item)

    seam_distances = [
        float(mouth["seam"].distToShape(panel["shape"])[0])
        for panel in mouth["panels"]
    ]
    mouth_mount = contract["mouth"]["mount_pair"]
    all_opaque_records = right_lower + left_lower + right_upper + left_upper
    checks = {
        "all_inputs_hash_match": True,
        "pinned_v5_reconstruction_passes": True,
        "right_lower_and_upper_owner_sets_are_nonempty": (
            len(right_lower) > 0 and len(right_upper) > 0
        ),
        "bilateral_owner_counts_are_exact": (
            len(right_lower) == len(left_lower)
            and len(right_upper) == len(left_upper)
        ),
        "all_opaque_owners_are_valid_closed": all(
            valid_closed(record["shape"]) for record in all_opaque_records
        ),
        "right_left_opaque_common_is_zero": (
            right_left_common <= float(gates["maximum_right_left_opaque_common_mm3"])
        ),
        "lower_upper_opaque_common_is_zero": (
            right_lower_upper_common <= float(gates["maximum_lower_upper_opaque_common_mm3"])
            and left_lower_upper_common <= float(gates["maximum_lower_upper_opaque_common_mm3"])
        ),
        "all_translucent_components_are_valid_closed": all(
            valid_closed(record["shape"]) for record in translucent
        ),
        "translucent_common_is_only_at_declared_mounts": (
            unclassified_common
            <= float(gates["maximum_unclassified_translucent_head_common_mm3"])
        ),
        "declared_lower_translucent_mount_groups_exist": (
            len(declared_lower_groups)
            >= int(gates["minimum_declared_lower_translucent_mount_groups"])
        ),
        "declared_lower_translucent_mount_roots_remain_positive": (
            len(retained_lower_groups)
            >= int(gates["minimum_declared_lower_translucent_mount_groups"])
        ),
        "mouth_facets_are_valid_closed": all(
            valid_closed(panel["shape"]) for panel in mouth["panels"]
        ),
        "mouth_facets_do_not_intersect_opaque_head": (
            mouth_common <= float(gates["mouth_maximum_head_common_mm3"])
        ),
        "mouth_facets_meet_head_clearance": (
            mouth_minimum_clearance + float(gates["distance_epsilon_mm"])
            >= float(gates["mouth_minimum_head_clearance_mm"])
        ),
        "mouth_center_seal_is_valid_closed": valid_closed(mouth["seam"]),
        "mouth_center_seal_reaches_both_facets": all(
            distance <= 0.05 for distance in seam_distances
        ),
        "panel_flange_roots_meet_minimum": all(
            item["panel_root_common_mm3"]
            >= float(mouth_mount["minimum_panel_root_overlap_mm3"])
            for item in tab_audit
        ),
        "head_flange_roots_meet_minimum": all(
            item["head_root_common_mm3"]
            >= float(mouth_mount["minimum_head_root_overlap_mm3"])
            for item in tab_audit
        ),
        "mount_pair_faces_have_exact_gap": all(
            item["pair_common_mm3"] <= epsilon
            and abs(item["pair_distance_mm"] - float(mouth_mount["face_gap_mm"])) <= 0.01
            for item in tab_audit
        ),
        "all_four_mouth_tabs_are_valid_closed": all(
            valid_closed(record["shape"])
            for record in mouth["panel_tabs"] + mouth["head_tabs"]
        ),
        "review_objects_remain_modular": True,
        "no_source_saved_or_geometry_exported": True,
    }
    status = (
        "PASS__LOWER_FRONT_BILATERAL_MODULAR_CLOSURE_REVIEW_READY__NOT_PRINT_RELEASED"
        if all(checks.values())
        else "HOLD__LOWER_FRONT_BILATERAL_MODULAR_CLOSURE_GATE_FAILURE"
    )
    shapes = {
        "right_lower": right_lower,
        "left_lower": left_lower,
        "right_mesh": right_mesh,
        "left_mesh": left_mesh,
        "right_upper": right_upper,
        "left_upper": left_upper,
        "right_ledge": right_ledge,
        "left_ledge": left_ledge,
        "translucent": translucent,
        "mouth": mouth,
    }
    finalization = disposable_finalization(shapes, contract, App)
    result = {
        "schema_version": "cat-head-lower-front-bilateral-modular-closure-validation-v1",
        "status": status,
        "authority": contract["authority"],
        "input_sha256": {
            name: item["sha256"] for name, item in contract["inputs"].items()
        },
        "checks": checks,
        "failed_checks": [name for name, value in checks.items() if not value],
        "measurements": {
            "right_lower_owner_count": len(right_lower),
            "left_lower_owner_count": len(left_lower),
            "right_upper_owner_count": len(right_upper),
            "left_upper_owner_count": len(left_upper),
            "right_left_opaque_common_mm3": right_left_common,
            "right_left_contacts": right_left_contacts,
            "right_left_minimum_distance_mm": right_left_distance,
            "right_left_nearest": right_left_nearest,
            "right_lower_upper_common_mm3": right_lower_upper_common,
            "right_lower_upper_contacts": right_lower_upper_contacts,
            "right_lower_upper_minimum_distance_mm": right_lower_upper_distance,
            "right_lower_upper_nearest": right_lower_upper_nearest,
            "left_lower_upper_common_mm3": left_lower_upper_common,
            "left_lower_upper_contacts": left_lower_upper_contacts,
            "left_lower_upper_minimum_distance_mm": left_lower_upper_distance,
            "left_lower_upper_nearest": left_lower_upper_nearest,
            "translucent_component_count": len(translucent),
            "translucent_ownership_resolution": translucent_resolution_audit,
            "lower_opaque_ownership_resolution": lower_ownership_audit,
            "declared_lower_translucent_mount_groups": sorted(declared_lower_groups),
            "retained_lower_translucent_mount_groups": sorted(retained_lower_groups),
            "unclassified_translucent_common_mm3": unclassified_common,
            "translucent_audit": translucent_audit,
            "mouth_panel_audit": mouth_panel_audit,
            "mouth_common_mm3": mouth_common,
            "mouth_minimum_opaque_clearance_mm": mouth_minimum_clearance,
            "mouth_center_seal_distances_mm": seam_distances,
            "mouth_tab_audit": tab_audit,
        },
        "disposable_finalization": finalization,
        "modular_object_policy": contract["decision"]["modularity"],
        "review_holds": [
            "Review-only assembly; no opaque owner is fused to another owner.",
            "Existing translucent insert STL components remain separately selectable.",
            "Mouth facets, center seal, panel flanges, head flanges, bores, washers, and shafts remain separate.",
            "No STL, STEP, 3MF, G-code, slicing, promotion, or print release is created."
        ],
        "io_trace": {
            "v5_saved": False,
            "v34_saved": False,
            "source_stl_saved": False,
            "review_saved": False,
            "geometry_export_created": False,
            "production_output_created": False,
        },
    }
    return result, shapes


def save_records(
    document: Any,
    group: Any,
    records: Sequence[dict[str, Any]],
    authority: str,
    color: tuple[float, float, float],
    transparency: int,
) -> None:
    for record in records:
        add_feature(
            document, group, record["name"], record.get("label", record["name"]),
            record["shape"], authority, color, transparency,
        )


def save_review(result: dict[str, Any], shapes: dict[str, Any]) -> tuple[Path, Path]:
    import FreeCAD as App  # type: ignore

    if not result["status"].startswith("PASS__"):
        raise RuntimeError(
            "review save is blocked by failed gates: "
            + ", ".join(result["failed_checks"])
        )
    contract = load_contract()
    output_dir = (PROJECT_ROOT / contract["outputs"]["directory"]).resolve()
    if output_dir.exists():
        raise RuntimeError(f"review output already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    document = App.newDocument("LOWER_FRONT_BILATERAL_MODULAR_CLOSURE_REVIEW_ONLY_V1")
    try:
        groups = {
            "right_lower": document.addObject("App::DocumentObjectGroup", "OPAQUE_RIGHT_LOWER_OWNERS"),
            "left_lower": document.addObject("App::DocumentObjectGroup", "OPAQUE_LEFT_LOWER_OWNERS"),
            "right_upper": document.addObject("App::DocumentObjectGroup", "OPAQUE_RIGHT_UPPER_OWNERS"),
            "left_upper": document.addObject("App::DocumentObjectGroup", "OPAQUE_LEFT_UPPER_OWNERS"),
            "right_mesh": document.addObject("App::DocumentObjectGroup", "REFERENCE_RIGHT_MESH_ONLY"),
            "left_mesh": document.addObject("App::DocumentObjectGroup", "REFERENCE_LEFT_MESH_ONLY"),
            "ledges": document.addObject("App::DocumentObjectGroup", "SEPARATE_V5_LOWER_REAR_LEDGES"),
            "translucent": document.addObject("App::DocumentObjectGroup", "EXISTING_TRANSLUCENT_INSERT_COMPONENTS"),
            "mouth": document.addObject("App::DocumentObjectGroup", "PROPOSED_TRANSLUCENT_MOUTH_COMPONENTS"),
            "mounts": document.addObject("App::DocumentObjectGroup", "PROPOSED_MOUTH_M2P5_FLANGE_COMPONENTS"),
            "hardware": document.addObject("App::DocumentObjectGroup", "REFERENCE_MOUTH_FASTENERS_AND_CUTTERS"),
        }
        save_records(document, groups["right_lower"], shapes["right_lower"], contract["authority"], (0.32, 0.55, 0.88), 12)
        save_records(document, groups["left_lower"], shapes["left_lower"], contract["authority"], (0.32, 0.55, 0.88), 12)
        save_records(document, groups["right_upper"], shapes["right_upper"], contract["authority"], (0.70, 0.72, 0.76), 18)
        save_records(document, groups["left_upper"], shapes["left_upper"], contract["authority"], (0.70, 0.72, 0.76), 18)
        save_records(document, groups["right_mesh"], shapes["right_mesh"], contract["authority"], (0.55, 0.55, 0.58), 72)
        save_records(document, groups["left_mesh"], shapes["left_mesh"], contract["authority"], (0.55, 0.55, 0.58), 72)
        save_records(document, groups["ledges"], shapes["right_ledge"] + shapes["left_ledge"], contract["authority"], (0.25, 0.92, 0.30), 0)
        save_records(document, groups["translucent"], shapes["translucent"], contract["authority"], (0.30, 0.95, 1.00), 35)
        for index, panel in enumerate(shapes["mouth"]["panels"], start=1):
            add_feature(
                document, groups["mouth"], f"MOUTH_FACET_{index}_{panel['name']}",
                f"PROPOSED — TRANSLUCENT MOUTH FACET {panel['name']}",
                panel["shape"], contract["authority"], (0.35, 1.00, 0.90), 32,
            )
        add_feature(
            document, groups["mouth"], "MOUTH_CENTER_SEAM_SEAL",
            "PROPOSED — TRANSLUCENT CENTER-SEAM DUST SEAL",
            shapes["mouth"]["seam"], contract["authority"], (0.10, 0.85, 0.95), 25,
        )
        save_records(
            document, groups["mounts"],
            shapes["mouth"]["panel_tabs"], contract["authority"], (0.10, 0.75, 1.00), 0,
        )
        save_records(
            document, groups["mounts"],
            shapes["mouth"]["head_tabs"], contract["authority"], (0.95, 0.55, 0.15), 0,
        )
        save_records(
            document, groups["hardware"],
            shapes["mouth"]["bores"], contract["authority"], (0.95, 0.15, 0.15), 80,
        )
        save_records(
            document, groups["hardware"],
            shapes["mouth"]["screws"], contract["authority"], (0.28, 0.28, 0.32), 0,
        )
        save_records(
            document, groups["hardware"],
            shapes["mouth"]["washers"], contract["authority"], (0.70, 0.70, 0.74), 0,
        )
        decision = document.addObject("App::FeaturePython", "MODULAR_REVIEW_DECISION")
        decision.Label = "REVIEW — MODULAR LOWER FRONT + TRANSLUCENT MOUTH"
        decision.addProperty("App::PropertyString", "Authority", "Review Control")
        decision.addProperty("App::PropertyString", "Editability", "Review Control")
        decision.addProperty("App::PropertyString", "ReleaseHold", "Review Control")
        decision.Authority = contract["authority"]
        decision.Editability = "All opaque, mirrored, translucent, mouth, flange, seam, cutter, and hardware components are separate selectable objects."
        decision.ReleaseHold = "Not a print source; morning visual feedback is required."
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
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
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
        args.report.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps({
            "status": result["status"],
            "failed_checks": result["failed_checks"],
            "right_left_common_mm3": result["measurements"]["right_left_opaque_common_mm3"],
            "right_lower_upper_common_mm3": result["measurements"]["right_lower_upper_common_mm3"],
            "left_lower_upper_common_mm3": result["measurements"]["left_lower_upper_common_mm3"],
            "unclassified_translucent_common_mm3": result["measurements"]["unclassified_translucent_common_mm3"],
            "mouth_common_mm3": result["measurements"]["mouth_common_mm3"],
            "mouth_minimum_clearance_mm": result["measurements"]["mouth_minimum_opaque_clearance_mm"],
        }, sort_keys=True))
        return 0 if result["status"].startswith("PASS__") else 1
    fcstd, validation = save_review(result, shapes)
    print(json.dumps({
        "status": result["status"],
        "fcstd": str(fcstd),
        "validation": str(validation),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
