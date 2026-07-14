#!/usr/bin/env python3
"""Generate a 3D proof model from manual + symmetry-derived mappings.

This is still a proof/checking artifact, not fabrication-ready CAD. It uses
the derived symmetry mapping and explicitly labels nodes whose 3D positions are
estimated from weak projection constraints.
"""

from __future__ import annotations

import csv
import html
import json
from collections import Counter, defaultdict
from pathlib import Path

from generate_3d_proof_model import Mesh, linfit, read_csv, write_csv, write_obj, write_stl


WORKDIR = Path(__file__).resolve().parent
NODES_CSV = WORKDIR / "gemini_trace_nodes_plus_symmetry_estimates.csv"
EDGES_CSV = WORKDIR / "gemini_trace_edges.csv"
DETAIL_CSV = WORKDIR / "gemini_node_mapping_plus_symmetry_detail.csv"

OUT_PREFIX = "gemini-3d-plus-symmetry-wireframe"
MODEL_HEIGHT_MM = 220.0
ROD_RADIUS_MM = 0.9
NODE_RADIUS_MM = 1.6
HEAVY_ESTIMATE_NODE_RADIUS_MM = 1.6
HEAVY_BACK_NODE_RADIUS_MM = 1.6
BACK_REVIEW_MARKER_RADIUS_MM = 16.0
CYLINDER_SEGMENTS = 14
SPHERE_SEGMENTS = 12

QUALITY_STYLE = {
    "high_confidence": {
        "color": "#16a34a",
        "label": "manual 3-view trace",
        "risk": 0,
    },
    "symmetry_traced": {
        "color": "#2563eb",
        "label": "symmetry, traced mirror nodes",
        "risk": 1,
    },
    "manual_partial": {
        "color": "#64748b",
        "label": "manual partial constraints",
        "risk": 2,
    },
    "moderate_estimate": {
        "color": "#f59e0b",
        "label": "some estimated projection",
        "risk": 3,
    },
    "heavy_estimate": {
        "color": "#dc2626",
        "label": "heavily estimated",
        "risk": 4,
    },
}

MANUAL_ADDED_NODES = [
    {
        "physical_node_id": "P059",
        "front_node": "F027",
        "placement": "midpoint_between_nodes",
        "between": ("P002", "P034"),
        "notes": "iterative edit: F027 placed at midpoint of F026/P002 and F025/P034",
    }
]

MANUAL_NODE_MIRROR_OVERRIDES = {
    "P005": {
        "source": "P035",
        "notes": "reviewer edit: P005 forced to exact mirror of P035 for bottom panel symmetry",
    },
    "P033": {
        "source": "P001",
        "notes": "reviewer edit: P033 forced to exact mirror of P001 across symmetry plane",
    },
    "P034": {
        "source": "P002",
        "notes": "iterative edit: F025/P034 forced to exact mirror of F026/P002 across symmetry plane",
    },
    "P039": {
        "source": "P009",
        "notes": "reviewer edit: P039 forced to exact mirror of P009 across symmetry plane",
    },
    "P036": {"source": "P006", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P037": {"source": "P007", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P038": {"source": "P008", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P040": {"source": "P011", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P041": {"source": "P012", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P042": {"source": "P013", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P043": {"source": "P014", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P044": {"source": "P015", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P045": {"source": "P016", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P046": {"source": "P017", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P047": {"source": "P018", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P048": {"source": "P019", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P049": {"source": "P020", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P050": {"source": "P021", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P052": {"source": "P026", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P053": {"source": "P027", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P055": {"source": "P029", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P056": {"source": "P030", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P057": {"source": "P031", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
    "P058": {"source": "P032", "notes": "symmetry enforcement: estimated mirror forced from reviewed source"},
}

MANUAL_NODE_REMOVALS = {
    "P006",  # reviewer removed right ear intermediate node at 80.547, 56.406, 14.945
    "P036",  # reviewer removed left ear intermediate node at -80.547, 56.406, 14.945
}

MANUAL_NODE_COORDINATE_OVERRIDES = {
    "P052": {
        "x_mm": -82.174,
        "y_mm_depth": 41.495,
        "z_mm_up": 14.838,
        "notes": "reviewer edit: moved left ear endpoint onto head edge",
    },
    "P026": {
        "x_mm": 82.174,
        "y_mm_depth": 41.495,
        "z_mm_up": 14.838,
        "notes": "reviewer edit: mirror of P052 moved onto head edge",
    },
    "P069": {
        "x_mm": 54.945,
        "y_mm_depth": 73.222,
        "z_mm_up": 32.900,
        "notes": "reviewer edit: projected right ear edge node onto plane P067-P026-P028",
    },
    "P066": {
        "x_mm": -54.945,
        "y_mm_depth": 73.222,
        "z_mm_up": 32.900,
        "notes": "reviewer edit: mirror of P069 projected onto left head surface plane P064-P052-P054",
    },
}

MANUAL_SIDE_ONLY_PORT_NODES = [
    {"physical_node_id": "P060", "side_node": "S029", "x_mm": -20.0, "near": "S024/P050 and S031/P057; reviewer moved S029 halfway toward symmetry plane"},
    {"physical_node_id": "P062", "side_node": "S019", "x_mm": -60.0, "near": "S024/P050 and S029/P060; reviewer moved S019 halfway toward symmetry plane"},
    {"physical_node_id": "P063", "side_node": "S020", "x_mm": -40.0, "near": "S029/P060, S019/P062, S011/P064; reviewer moved S020 halfway toward symmetry plane"},
    {"physical_node_id": "P064", "side_node": "S011", "x_mm": -50.0, "near": "S007/P066 and S019/P062; reviewer moved S011 halfway toward symmetry plane"},
    {"physical_node_id": "P065", "side_node": "S009", "x_mm": -20.0, "near": "S020/P063 and S011/P064; reviewer moved S009 halfway toward symmetry plane"},
    {"physical_node_id": "P066", "side_node": "S007", "x_mm": -74.0, "near": "former S013/P036 path removed; near S011/P064"},
]

MANUAL_SIDE_ONLY_MIRROR_NODES = [
    {"physical_node_id": "P067", "source_physical_node_id": "P064", "source_side_node": "S011"},
    {"physical_node_id": "P068", "source_physical_node_id": "P065", "source_side_node": "S009"},
    {"physical_node_id": "P069", "source_physical_node_id": "P066", "source_side_node": "S007"},
    {"physical_node_id": "P070", "source_physical_node_id": "P063", "source_side_node": "S020"},
    {"physical_node_id": "P071", "source_physical_node_id": "P062", "source_side_node": "S019"},
    {"physical_node_id": "P072", "source_physical_node_id": "P060", "source_side_node": "S029"},
]

MANUAL_TOP_ONLY_NODES = []

MANUAL_ROD_REMOVALS = {
    tuple(sorted(("P002", "P003"))),  # remove direct F026-F034 rod
    tuple(sorted(("P026", "P071"))),  # reviewer removed direct right rear edge
    tuple(sorted(("P008", "P028"))),  # split right ear-base edge through head-top waypoint P027
    tuple(sorted(("P038", "P054"))),  # split left ear-base edge through head-top waypoint P053
    tuple(sorted(("P069", "P071"))),  # reviewer removed right rear ear edge
    tuple(sorted(("P069", "P067"))),  # reviewer removed right rear ear edge
    tuple(sorted(("P064", "P066"))),  # reviewer removed left rear ear edge
    tuple(sorted(("P066", "P061"))),  # reviewer removed left rear ear edge
}

MANUAL_ROD_ADDITIONS = [
    ("P003", "P059", "manual:F034-F027"),
    ("P059", "P002", "manual:F027-F026"),
    ("P059", "P034", "manual:F027-F025"),
    ("P004", "P035", "manual:F038-F042"),
    ("P050", "P060", "manual-side:S024-S029"),
    ("P060", "P057", "manual-side:S029-S031"),
    ("P050", "P062", "manual-side:S024-S019"),
    ("P066", "P064", "manual-side:S007-S011"),
    ("P060", "P063", "manual-side:S029-S020"),
    ("P063", "P062", "manual-side:S020-S019"),
    ("P062", "P060", "manual-side:S019-S029"),
    ("P062", "P064", "manual-side:S019-S011"),
    ("P064", "P063", "manual-side:S011-S020"),
    ("P063", "P065", "manual-side:S020-S009"),
    ("P065", "P064", "manual-side:S009-S011"),
    ("P036", "P066", "manual-side:S013-S007"),
    ("P065", "P024", "manual-connect:S009-P024"),
    ("P064", "P024", "manual-connect:S011-P024"),
    ("P064", "P054", "manual-connect:S011-P054"),
    ("P066", "P054", "manual-connect:S007-P054"),
    ("P072", "P060", "manual-mirror-connect:P072-P060"),
    ("P067", "P068", "manual-mirror-connect:P067-P068"),
    ("P068", "P024", "manual-mirror-connect:P068-P024"),
    ("P067", "P024", "manual-mirror-connect:P067-P024"),
    ("P070", "P068", "manual-mirror-connect:P070-P068"),
    ("P071", "P067", "manual-mirror-connect:P071-P067"),
    ("P071", "P070", "manual-coordinate-connect:P071-P070"),
    ("P070", "P072", "manual-coordinate-connect:P070-P072"),
    ("P072", "P071", "manual-coordinate-connect:P072-P071"),
    ("P072", "P031", "manual-coordinate-connect:P072-P031"),
    ("P031", "P071", "manual-coordinate-connect:P031-P071"),
    ("P071", "P021", "manual-coordinate-connect:P071-P021"),
    ("P006", "P069", "manual-coordinate-connect:P006-P069"),
    ("P069", "P028", "manual-coordinate-connect:P069-P028"),
    ("P068", "P065", "manual-coordinate-connect:P068-P065"),
    ("P069", "P067", "manual-coordinate-connect:P069-P067"),
    ("P067", "P028", "manual-coordinate-connect:P067-P028"),
    ("P026", "P067", "manual-ear-edge:P026-P067"),
    ("P052", "P064", "manual-ear-edge:P052-P064"),
    ("P052", "P066", "manual-ear-corner-direct:P052-P066"),
    ("P026", "P069", "manual-ear-corner-direct:P026-P069"),
    ("P069", "P007", "manual-coordinate-connect:P069-P007"),
    ("P066", "P037", "manual-coordinate-connect:P066-P037"),
    ("P008", "P027", "manual-ear-base-split:P008-P027"),
    ("P027", "P028", "manual-ear-base-split:P027-P028"),
    ("P007", "P027", "manual-ear-base-crease:P007-P027"),
    ("P038", "P053", "manual-ear-base-split:P038-P053"),
    ("P053", "P054", "manual-ear-base-split:P053-P054"),
    ("P037", "P053", "manual-ear-base-crease:P037-P053"),
]

MANUAL_VIEWER_PART_X_PULLS = []



def load_nodes() -> dict[tuple[str, str], dict[str, object]]:
    nodes: dict[tuple[str, str], dict[str, object]] = {}
    for row in read_csv(NODES_CSV):
        nodes[(row["view"], row["node_id"])] = {
            "x": float(row["x_px"]),
            "y": float(row["y_px"]),
            "node_source": row.get("node_source", "trace"),
        }
    return nodes


def active_detail_rows() -> list[dict[str, str]]:
    rows = []
    for row in read_csv(DETAIL_CSV):
        if not row.get("front_node", "").strip():
            continue
        if row.get("row_source") == "symmetry_promoted":
            rows.append(row)
            continue
        if not row.get("side_node", "").strip() and not row.get("top_node", "").strip():
            continue
        rows.append(row)
    return rows


def build_projection_fits(
    nodes: dict[tuple[str, str], dict[str, object]],
    rows: list[dict[str, str]],
) -> dict[str, tuple[float, float]]:
    triples = []
    for row in rows:
        if row.get("row_source") != "manual_confirmed":
            continue
        if not row.get("front_node") or not row.get("side_node") or not row.get("top_node"):
            continue
        if row.get("front_node_source") != "trace" or row.get("side_node_source") != "trace" or row.get("top_node_source") != "trace":
            continue
        front = nodes.get(("Front", row["front_node"]))
        side = nodes.get(("Side", row["side_node"]))
        top = nodes.get(("Top", row["top_node"]))
        if front and side and top:
            triples.append((front, side, top))

    if len(triples) < 2:
        raise RuntimeError("Need at least two manual 3-view nodes to fit projections.")

    return {
        "top_x_to_front_x": linfit([float(t["x"]) for _, _, t in triples], [float(f["x"]) for f, _, _ in triples]),
        "top_y_to_side_x": linfit([float(t["y"]) for _, _, t in triples], [float(s["x"]) for _, s, t in triples]),
        "side_y_to_front_y": linfit([float(s["y"]) for _, s, _ in triples], [float(f["y"]) for f, s, _ in triples]),
    }


def estimate_count(row: dict[str, str]) -> int:
    return sum(
        1
        for key in ["front_node_source", "side_node_source", "top_node_source"]
        if row.get(key, "") == "symmetry_estimate"
    )


def classify_quality(
    row: dict[str, str],
    missing_side: bool,
    missing_top: bool,
    source_depth_estimated: bool,
) -> tuple[str, str]:
    row_source = row.get("row_source", "")
    candidate_status = row.get("candidate_status", "")
    est_count = estimate_count(row)
    notes = []
    if row_source == "symmetry_promoted":
        notes.append("symmetry promoted")
    if est_count:
        notes.append(f"{est_count} estimated projection(s)")
    if row.get("side_node_source") == "trace_reused_by_symmetry":
        notes.append("legacy side projection reuse")
    if missing_side:
        notes.append("hidden side has no visible side-view constraint")
    if missing_top:
        notes.append("no top-view depth cross-check")
    if source_depth_estimated:
        notes.append("depth estimated from symmetric source mate")

    if row_source == "manual_confirmed" and not missing_side and not missing_top and est_count == 0:
        return "high_confidence", "manual front+side+top trace"
    if row_source == "symmetry_promoted" and candidate_status == "ready_for_review" and est_count == 0 and not missing_top:
        return "symmetry_traced", "; ".join(notes) or "symmetry traced"
    if row_source == "manual_confirmed":
        return "manual_partial", "; ".join(notes) or "manual partial"
    if candidate_status == "needs_manual_trace_or_estimate" or est_count >= 2 or source_depth_estimated:
        return "heavy_estimate", "; ".join(notes) or "heavily estimated"
    return "moderate_estimate", "; ".join(notes) or "moderately estimated"


def transform_nodes(
    nodes: dict[tuple[str, str], dict[str, object]],
    rows: list[dict[str, str]],
    fits: dict[str, tuple[float, float]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[tuple[str, str], list[str]], dict[str, dict[str, str]]]:
    pixel_rows = []
    residual_rows = []
    projection_to_physical: dict[tuple[str, str], list[str]] = defaultdict(list)
    detail_by_pid: dict[str, dict[str, str]] = {}

    top_x_a, top_x_b = fits["top_x_to_front_x"]
    top_y_a, top_y_b = fits["top_y_to_side_x"]
    side_y_a, side_y_b = fits["side_y_to_front_y"]

    skipped = []
    pixel_by_pid: dict[str, dict[str, object]] = {}
    for row in rows:
        pid = row["physical_node_id"]
        detail_by_pid[pid] = row
        front = nodes.get(("Front", row["front_node"]))
        side = nodes.get(("Side", row.get("side_node", ""))) if row.get("side_node") else None
        top = nodes.get(("Top", row.get("top_node", ""))) if row.get("top_node") else None
        if not front:
            skipped.append({"physical_node_id": pid, "reason": "missing_front_node"})
            continue

        projection_to_physical[("Front", row["front_node"])].append(pid)
        if side:
            projection_to_physical[("Side", row["side_node"])].append(pid)
        if top:
            projection_to_physical[("Top", row["top_node"])].append(pid)

        front_x = float(front["x"])
        front_y = float(front["y"])
        x_sources = [front_x]
        depth_sources = []
        z_sources = [front_y]
        top_x_error = ""
        top_depth_error = ""
        source_depth_estimated = False

        if side:
            depth_sources.append(float(side["x"]))
            side_y_as_front_y = side_y_a * float(side["y"]) + side_y_b
            z_sources.append(side_y_as_front_y)
        else:
            side_y_as_front_y = ""

        if top:
            top_as_front_x = top_x_a * float(top["x"]) + top_x_b
            top_as_side_depth = top_y_a * float(top["y"]) + top_y_b
            top_x_error = top_as_front_x - front_x
            if side:
                top_depth_error = top_as_side_depth - float(side["x"])
            x_sources.append(top_as_front_x)
            depth_sources.append(top_as_side_depth)

        if not depth_sources:
            source_pid = row.get("source_physical_node_id", "")
            source_pixel = pixel_by_pid.get(source_pid)
            if source_pixel:
                depth_sources.append(float(source_pixel["depth_px"]))
                source_depth_estimated = True
            else:
                skipped.append({"physical_node_id": pid, "reason": "missing_depth_constraint"})
                continue

        x_px = sum(x_sources) / len(x_sources)
        depth_px = sum(depth_sources) / len(depth_sources)
        z_y_px = sum(z_sources) / len(z_sources)
        z_error = "" if side_y_as_front_y == "" else float(side_y_as_front_y) - front_y
        missing_side = side is None
        missing_top = top is None
        quality, quality_notes = classify_quality(row, missing_side, missing_top, source_depth_estimated)

        issues = []
        if top and abs(float(top_x_error)) > 12.0:
            issues.append("top_x_mismatch")
        if top and side and abs(float(top_depth_error)) > 40.0:
            issues.append("top_depth_mismatch")
        if z_error != "" and abs(float(z_error)) > 10.0:
            issues.append("front_side_height_mismatch")
        if missing_side:
            issues.append("no_visible_side_constraint")
        if source_depth_estimated:
            issues.append("source_depth_estimate")
        if missing_top:
            issues.append("no_top_constraint")
        if estimate_count(row):
            issues.append("estimated_projection")
        if quality == "heavy_estimate":
            issues.append("heavy_estimate")

        pixel_rows.append(
            {
                "physical_node_id": pid,
                "row_source": row.get("row_source", ""),
                "candidate_status": row.get("candidate_status", ""),
                "source_physical_node_id": row.get("source_physical_node_id", ""),
                "front_node": row.get("front_node", ""),
                "side_node": row.get("side_node", ""),
                "top_node": row.get("top_node", ""),
                "front_node_source": row.get("front_node_source", ""),
                "side_node_source": row.get("side_node_source", ""),
                "top_node_source": row.get("top_node_source", ""),
                "constraint_quality": quality,
                "constraint_risk": QUALITY_STYLE[quality]["risk"],
                "node_color": QUALITY_STYLE[quality]["color"],
                "quality_notes": quality_notes,
                "source_depth_estimated": source_depth_estimated,
                "x_px": x_px,
                "depth_px": depth_px,
                "z_y_px": z_y_px,
                "front_x_px": front_x,
                "side_depth_px": "" if not side else float(side["x"]),
                "top_depth_as_side_px": "" if not top else top_y_a * float(top["y"]) + top_y_b,
                "front_y_px": front_y,
                "side_y_as_front_y_px": side_y_as_front_y,
                "notes": row.get("notes", ""),
            }
        )
        residual_rows.append(
            {
                "physical_node_id": pid,
                "constraint_quality": quality,
                "front_node": row.get("front_node", ""),
                "side_node": row.get("side_node", ""),
                "top_node": row.get("top_node", ""),
                "top_x_error_px": "" if top_x_error == "" else round(float(top_x_error), 3),
                "top_depth_error_px": "" if top_depth_error == "" else round(float(top_depth_error), 3),
                "front_side_height_error_px": "" if z_error == "" else round(float(z_error), 3),
                "issue": " ".join(issues),
                "quality_notes": quality_notes,
            }
        )
        pixel_by_pid[pid] = pixel_rows[-1]

    if skipped:
        write_csv(WORKDIR / "gemini_3d_plus_symmetry_skipped_nodes.csv", ["physical_node_id", "reason"], skipped)

    min_z_y = min(float(row["z_y_px"]) for row in pixel_rows)
    max_z_y = max(float(row["z_y_px"]) for row in pixel_rows)
    scale = MODEL_HEIGHT_MM / max(max_z_y - min_z_y, 1.0)

    min_x = min(float(row["x_px"]) for row in pixel_rows)
    max_x = max(float(row["x_px"]) for row in pixel_rows)
    min_depth = min(float(row["depth_px"]) for row in pixel_rows)
    max_depth = max(float(row["depth_px"]) for row in pixel_rows)
    center_x = (min_x + max_x) / 2.0
    center_depth = (min_depth + max_depth) / 2.0
    center_z_y = (min_z_y + max_z_y) / 2.0
    depth_span = max(max_depth - min_depth, 1.0)

    model_rows = []
    for row in pixel_rows:
        x = (float(row["x_px"]) - center_x) * scale
        y = (float(row["depth_px"]) - center_depth) * scale
        z = (center_z_y - float(row["z_y_px"])) * scale
        depth_pct = (float(row["depth_px"]) - min_depth) / depth_span
        depth_region = "back/deep half" if depth_pct >= 0.55 else "front/shallow half"
        model_rows.append(
            {
                **row,
                "x_mm": round(x, 3),
                "y_mm_depth": round(y, 3),
                "z_mm_up": round(z, 3),
                "x_px": round(float(row["x_px"]), 3),
                "depth_px": round(float(row["depth_px"]), 3),
                "z_y_px": round(float(row["z_y_px"]), 3),
                "depth_percent": round(depth_pct, 3),
                "depth_region": depth_region,
            }
        )
    return model_rows, residual_rows, projection_to_physical, detail_by_pid


def apply_manual_node_removals(
    node_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
    projection_to_physical: dict[tuple[str, str], list[str]],
    detail_by_pid: dict[str, dict[str, str]],
) -> None:
    if not MANUAL_NODE_REMOVALS:
        return
    node_rows[:] = [row for row in node_rows if str(row["physical_node_id"]) not in MANUAL_NODE_REMOVALS]
    residual_rows[:] = [row for row in residual_rows if str(row["physical_node_id"]) not in MANUAL_NODE_REMOVALS]
    for key, pids in list(projection_to_physical.items()):
        kept = [pid for pid in pids if pid not in MANUAL_NODE_REMOVALS]
        if kept:
            projection_to_physical[key] = kept
        else:
            del projection_to_physical[key]
    for pid in MANUAL_NODE_REMOVALS:
        detail_by_pid.pop(pid, None)


def apply_manual_node_mirror_overrides(
    node_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
) -> None:
    node_by_id = {str(row["physical_node_id"]): row for row in node_rows}
    residual_by_id = {str(row["physical_node_id"]): row for row in residual_rows}
    for target_id, spec in MANUAL_NODE_MIRROR_OVERRIDES.items():
        source_id = str(spec["source"])
        if target_id not in node_by_id or source_id not in node_by_id:
            continue
        target = node_by_id[target_id]
        source = node_by_id[source_id]
        note = str(spec["notes"])
        target["x_mm"] = round(-float(source["x_mm"]), 3)
        target["y_mm_depth"] = round(float(source["y_mm_depth"]), 3)
        target["z_mm_up"] = round(float(source["z_mm_up"]), 3)
        for field in ["depth_px", "z_y_px", "front_y_px", "depth_percent", "depth_region"]:
            target[field] = source[field]
        target["quality_notes"] = f"{target['quality_notes']}; {note}"
        target["notes"] = f"{target['notes']}; {note}"
        residual = residual_by_id.get(target_id)
        if residual:
            residual["issue"] = f"{residual['issue']} manual_mirror_override".strip()
            residual["quality_notes"] = f"{residual['quality_notes']}; {note}"


def apply_manual_node_coordinate_overrides(
    node_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
) -> None:
    node_by_id = {str(row["physical_node_id"]): row for row in node_rows}
    residual_by_id = {str(row["physical_node_id"]): row for row in residual_rows}
    y_values = [float(row["y_mm_depth"]) for row in node_rows]
    min_y = min(y_values)
    max_y = max(y_values)
    y_span = max(max_y - min_y, 1.0)

    for target_id, spec in MANUAL_NODE_COORDINATE_OVERRIDES.items():
        row = node_by_id.get(target_id)
        if not row:
            continue
        old = (float(row["x_mm"]), float(row["y_mm_depth"]), float(row["z_mm_up"]))
        new = (float(spec["x_mm"]), float(spec["y_mm_depth"]), float(spec["z_mm_up"]))
        note = (
            f"{spec['notes']}: "
            f"({old[0]:.3f}, {old[1]:.3f}, {old[2]:.3f}) -> "
            f"({new[0]:.3f}, {new[1]:.3f}, {new[2]:.3f})"
        )
        row["x_mm"] = round(new[0], 3)
        row["y_mm_depth"] = round(new[1], 3)
        row["z_mm_up"] = round(new[2], 3)
        row["depth_percent"] = round((new[1] - min_y) / y_span, 3)
        row["depth_region"] = "back/deep half" if float(row["depth_percent"]) >= 0.55 else "front/shallow half"
        row["quality_notes"] = f"{row['quality_notes']}; {note}"
        row["notes"] = f"{row['notes']}; {note}"
        if int(row["constraint_risk"]) < QUALITY_STYLE["manual_partial"]["risk"]:
            row["constraint_quality"] = "manual_partial"
            row["constraint_risk"] = QUALITY_STYLE["manual_partial"]["risk"]
            row["node_color"] = QUALITY_STYLE["manual_partial"]["color"]
        residual = residual_by_id.get(target_id)
        if residual:
            residual["issue"] = f"{residual['issue']} manual_coordinate_override".strip()
            residual["quality_notes"] = f"{residual['quality_notes']}; {note}"


def infer_scale_from_model_rows(node_rows: list[dict[str, object]]) -> tuple[float, float, float, float, float]:
    numeric = [row for row in node_rows if row.get("depth_px") not in {"", None}]
    min_depth_row = min(numeric, key=lambda row: float(row["depth_px"]))
    max_depth_row = max(numeric, key=lambda row: float(row["depth_px"]))
    depth_delta = float(max_depth_row["depth_px"]) - float(min_depth_row["depth_px"])
    y_delta = float(max_depth_row["y_mm_depth"]) - float(min_depth_row["y_mm_depth"])
    scale = y_delta / depth_delta if abs(depth_delta) > 1e-9 else 1.0
    center_depth = float(min_depth_row["depth_px"]) - float(min_depth_row["y_mm_depth"]) / scale

    z_numeric = [row for row in node_rows if row.get("z_y_px") not in {"", None}]
    center_z_y = sum(float(row["z_y_px"]) + float(row["z_mm_up"]) / scale for row in z_numeric) / len(z_numeric)
    min_depth = min(float(row["depth_px"]) for row in numeric)
    max_depth = max(float(row["depth_px"]) for row in numeric)
    return scale, center_depth, center_z_y, min_depth, max_depth


def add_manual_side_only_port_nodes(
    node_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
    trace_nodes: dict[tuple[str, str], dict[str, object]],
    fits: dict[str, tuple[float, float]],
) -> None:
    node_by_id = {str(row["physical_node_id"]): row for row in node_rows}
    scale, center_depth, center_z_y, min_depth, max_depth = infer_scale_from_model_rows(node_rows)
    side_y_a, side_y_b = fits["side_y_to_front_y"]
    depth_span = max(max_depth - min_depth, 1.0)

    for spec in MANUAL_SIDE_ONLY_PORT_NODES:
        pid = spec["physical_node_id"]
        if pid in node_by_id:
            continue
        side_node = spec["side_node"]
        side = trace_nodes[("Side", side_node)]
        depth_px = float(side["x"])
        z_y_px = side_y_a * float(side["y"]) + side_y_b
        y_mm = float(spec.get("y_mm_depth", (depth_px - center_depth) * scale))
        z_mm = float(spec.get("z_mm_up", (center_z_y - z_y_px) * scale))
        depth_percent = (depth_px - min_depth) / depth_span
        depth_region = "back/deep half" if depth_percent >= 0.55 else "front/shallow half"
        coordinate_note = "manual y/z override used" if "y_mm_depth" in spec or "z_mm_up" in spec else "side-view depth/height used directly"
        note = (
            f"manual side-only port placement: {side_node}; x estimated at {spec['x_mm']}mm "
            f"near {spec['near']}; {coordinate_note}"
        )
        row = {
            "physical_node_id": pid,
            "row_source": "manual_side_only_port_estimate",
            "candidate_status": "manual_side_only",
            "source_physical_node_id": str(spec["near"]),
            "front_node": "",
            "side_node": side_node,
            "top_node": "",
            "front_node_source": "",
            "side_node_source": "trace_side_only",
            "top_node_source": "",
            "constraint_quality": "heavy_estimate",
            "constraint_risk": QUALITY_STYLE["heavy_estimate"]["risk"],
            "node_color": QUALITY_STYLE["heavy_estimate"]["color"],
            "quality_notes": note,
            "source_depth_estimated": False,
            "depth_region": depth_region,
            "depth_percent": round(depth_percent, 3),
            "x_mm": round(float(spec["x_mm"]), 3),
            "y_mm_depth": round(y_mm, 3),
            "z_mm_up": round(z_mm, 3),
            "x_px": "",
            "depth_px": round(depth_px, 3),
            "z_y_px": round(z_y_px, 3),
            "front_x_px": "",
            "side_depth_px": round(depth_px, 3),
            "top_depth_as_side_px": "",
            "front_y_px": "",
            "side_y_as_front_y_px": round(z_y_px, 3),
            "notes": note,
        }
        node_rows.append(row)
        node_by_id[pid] = row
        residual_rows.append(
            {
                "physical_node_id": pid,
                "constraint_quality": "heavy_estimate",
                "front_node": "",
                "side_node": side_node,
                "top_node": "",
                "top_x_error_px": "",
                "top_depth_error_px": "",
                "front_side_height_error_px": "",
                "issue": "manual_side_only_port_estimate no_front_constraint no_top_constraint x_estimated",
                "quality_notes": note,
            }
        )


def add_manual_side_only_mirror_nodes(
    node_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
) -> None:
    node_by_id = {str(row["physical_node_id"]): row for row in node_rows}

    def matching_existing_node(source: dict[str, object]) -> str:
        target_x = -float(source["x_mm"])
        target_y = float(source["y_mm_depth"])
        target_z = float(source["z_mm_up"])
        for row in node_rows:
            if row is source:
                continue
            if (
                abs(float(row["x_mm"]) - target_x) < 0.001
                and abs(float(row["y_mm_depth"]) - target_y) < 0.001
                and abs(float(row["z_mm_up"]) - target_z) < 0.001
            ):
                return str(row["physical_node_id"])
        return ""

    for spec in MANUAL_SIDE_ONLY_MIRROR_NODES:
        pid = str(spec["physical_node_id"])
        if pid in node_by_id:
            continue
        source_id = str(spec["source_physical_node_id"])
        source = node_by_id.get(source_id)
        if not source:
            continue
        existing = matching_existing_node(source)
        if existing:
            continue
        side_node = str(spec["source_side_node"])
        note = (
            f"manual mirrored backside point for {side_node}; source={source_id}; "
            "same y/z, opposite x"
        )
        row = {
            "physical_node_id": pid,
            "row_source": "manual_side_only_mirror_estimate",
            "candidate_status": "manual_mirror_of_side_only",
            "source_physical_node_id": source_id,
            "front_node": "",
            "side_node": f"{side_node}_MIRROR",
            "top_node": "",
            "front_node_source": "",
            "side_node_source": "manual_mirror",
            "top_node_source": "",
            "constraint_quality": "heavy_estimate",
            "constraint_risk": QUALITY_STYLE["heavy_estimate"]["risk"],
            "node_color": QUALITY_STYLE["heavy_estimate"]["color"],
            "quality_notes": note,
            "source_depth_estimated": True,
            "depth_region": source["depth_region"],
            "depth_percent": source["depth_percent"],
            "x_mm": round(-float(source["x_mm"]), 3),
            "y_mm_depth": source["y_mm_depth"],
            "z_mm_up": source["z_mm_up"],
            "x_px": "",
            "depth_px": source["depth_px"],
            "z_y_px": source["z_y_px"],
            "front_x_px": "",
            "side_depth_px": source["side_depth_px"],
            "top_depth_as_side_px": "",
            "front_y_px": "",
            "side_y_as_front_y_px": source["side_y_as_front_y_px"],
            "notes": note,
        }
        node_rows.append(row)
        node_by_id[pid] = row
        residual_rows.append(
            {
                "physical_node_id": pid,
                "constraint_quality": "heavy_estimate",
                "front_node": "",
                "side_node": f"{side_node}_MIRROR",
                "top_node": "",
                "top_x_error_px": "",
                "top_depth_error_px": "",
                "front_side_height_error_px": "",
                "issue": "manual_side_only_mirror no_front_constraint no_top_constraint no_side_trace",
                "quality_notes": note,
            }
        )


def infer_center_x_from_model_rows(node_rows: list[dict[str, object]], scale: float) -> float:
    numeric = [row for row in node_rows if row.get("x_px") not in {"", None}]
    if not numeric:
        return 0.0
    return sum(float(row["x_px"]) - float(row["x_mm"]) / scale for row in numeric) / len(numeric)


def add_manual_top_only_nodes(
    node_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
    trace_nodes: dict[tuple[str, str], dict[str, object]],
    fits: dict[str, tuple[float, float]],
) -> None:
    node_by_id = {str(row["physical_node_id"]): row for row in node_rows}
    scale, center_depth, center_z_y, min_depth, max_depth = infer_scale_from_model_rows(node_rows)
    center_x = infer_center_x_from_model_rows(node_rows, scale)
    top_x_a, top_x_b = fits["top_x_to_front_x"]
    top_y_a, top_y_b = fits["top_y_to_side_x"]
    depth_span = max(max_depth - min_depth, 1.0)

    for spec in MANUAL_TOP_ONLY_NODES:
        pid = str(spec["physical_node_id"])
        if pid in node_by_id:
            continue
        top_node = str(spec["top_node"])
        top = trace_nodes[("Top", top_node)]
        x_px = top_x_a * float(top["x"]) + top_x_b
        depth_px = top_y_a * float(top["y"]) + top_y_b
        x_mm = (x_px - center_x) * scale if spec.get("x_mm") is None else float(spec["x_mm"])
        refs = [node_by_id[str(ref)] for ref in spec["z_reference_nodes"]]
        z_mm = sum(float(ref["z_mm_up"]) for ref in refs) / len(refs)
        z_y_px = center_z_y - z_mm / scale
        y_mm = (depth_px - center_depth) * scale
        depth_percent = (depth_px - min_depth) / depth_span
        depth_region = "back/deep half" if depth_percent >= 0.55 else "front/shallow half"
        note = str(spec["notes"])
        row = {
            "physical_node_id": pid,
            "row_source": "manual_top_only_estimate",
            "candidate_status": "manual_top_only",
            "source_physical_node_id": " ".join(str(ref) for ref in spec["z_reference_nodes"]),
            "front_node": "",
            "side_node": "",
            "top_node": top_node,
            "front_node_source": "",
            "side_node_source": "",
            "top_node_source": "trace_top_only",
            "constraint_quality": "heavy_estimate",
            "constraint_risk": QUALITY_STYLE["heavy_estimate"]["risk"],
            "node_color": QUALITY_STYLE["heavy_estimate"]["color"],
            "quality_notes": note,
            "source_depth_estimated": True,
            "depth_region": depth_region,
            "depth_percent": round(depth_percent, 3),
            "x_mm": round(x_mm, 3),
            "y_mm_depth": round(y_mm, 3),
            "z_mm_up": round(z_mm, 3),
            "x_px": round(x_px, 3),
            "depth_px": round(depth_px, 3),
            "z_y_px": round(z_y_px, 3),
            "front_x_px": "",
            "side_depth_px": "",
            "top_depth_as_side_px": round(depth_px, 3),
            "front_y_px": "",
            "side_y_as_front_y_px": "",
            "notes": note,
        }
        node_rows.append(row)
        node_by_id[pid] = row
        residual_rows.append(
            {
                "physical_node_id": pid,
                "constraint_quality": "heavy_estimate",
                "front_node": "",
                "side_node": "",
                "top_node": top_node,
                "top_x_error_px": "",
                "top_depth_error_px": "",
                "front_side_height_error_px": "",
                "issue": "manual_top_only_estimate no_front_constraint no_side_constraint z_estimated",
                "quality_notes": note,
            }
        )


def add_manual_nodes(
    node_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
) -> None:
    node_by_id = {str(row["physical_node_id"]): row for row in node_rows}
    for spec in MANUAL_ADDED_NODES:
        pid = spec["physical_node_id"]
        if pid in node_by_id:
            continue
        a_id, b_id = spec["between"]
        a = node_by_id[str(a_id)]
        b = node_by_id[str(b_id)]

        def avg(field: str) -> float:
            return (float(a[field]) + float(b[field])) / 2.0

        depth_percent = avg("depth_percent")
        depth_region = "back/deep half" if depth_percent >= 0.55 else "front/shallow half"
        quality = "moderate_estimate"
        notes = str(spec["notes"])
        row = {
            "physical_node_id": pid,
            "row_source": "manual_iterative_edit",
            "candidate_status": "manual_midpoint",
            "source_physical_node_id": f"{a_id} {b_id}",
            "front_node": spec["front_node"],
            "side_node": "",
            "top_node": "",
            "front_node_source": "trace_label_midpoint_placement",
            "side_node_source": "",
            "top_node_source": "",
            "constraint_quality": quality,
            "constraint_risk": QUALITY_STYLE[quality]["risk"],
            "node_color": QUALITY_STYLE[quality]["color"],
            "quality_notes": f"{notes}; no independent side/top constraint",
            "source_depth_estimated": True,
            "depth_region": depth_region,
            "depth_percent": round(depth_percent, 3),
            "x_mm": round(avg("x_mm"), 3),
            "y_mm_depth": round(avg("y_mm_depth"), 3),
            "z_mm_up": round(avg("z_mm_up"), 3),
            "x_px": round(avg("x_px"), 3),
            "depth_px": round(avg("depth_px"), 3),
            "z_y_px": round(avg("z_y_px"), 3),
            "front_x_px": round(avg("front_x_px"), 3),
            "side_depth_px": "",
            "top_depth_as_side_px": "",
            "front_y_px": round(avg("front_y_px"), 3),
            "side_y_as_front_y_px": "",
            "notes": notes,
        }
        node_rows.append(row)
        node_by_id[pid] = row
        residual_rows.append(
            {
                "physical_node_id": pid,
                "constraint_quality": quality,
                "front_node": spec["front_node"],
                "side_node": "",
                "top_node": "",
                "top_x_error_px": "",
                "top_depth_error_px": "",
                "front_side_height_error_px": "",
                "issue": "manual_midpoint_estimate no_visible_side_constraint no_top_constraint",
                "quality_notes": row["quality_notes"],
            }
        )




def apply_manual_rod_edits(
    rod_rows: list[dict[str, object]],
    node_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    available_nodes = {str(row["physical_node_id"]) for row in node_rows}
    filtered = [
        row
        for row in rod_rows
        if tuple(sorted((str(row["node_a"]), str(row["node_b"])))) not in MANUAL_ROD_REMOVALS
    ]
    existing = {tuple(sorted((str(row["node_a"]), str(row["node_b"])))) for row in filtered}
    for node_a, node_b, source_edge in MANUAL_ROD_ADDITIONS:
        if node_a not in available_nodes or node_b not in available_nodes:
            continue
        key = tuple(sorted((node_a, node_b)))
        if key in MANUAL_ROD_REMOVALS:
            continue
        if key in existing:
            continue
        filtered.append(
            {
                "rod_id": "",
                "node_a": key[0],
                "node_b": key[1],
                "source_views": "ManualEdit",
                "source_edges": source_edge,
            }
        )
        existing.add(key)
    filtered.sort(key=lambda row: (str(row["node_a"]), str(row["node_b"]), str(row["source_edges"])))
    for idx, row in enumerate(filtered, start=1):
        row["rod_id"] = f"PSR{idx:03d}"
    return filtered


def apply_manual_viewer_part_x_pulls(
    node_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
    rod_rows: list[dict[str, object]],
) -> None:
    """Pull reviewer-selected OBJ/import parts toward the symmetry plane.

    The exported OBJ is a rod/node mesh; moving a rod as a disconnected mesh
    would break the carcass. Instead, selected rod parts move their endpoint
    nodes in X only. If a node is shared by selected rods, apply the strongest
    requested pull once.
    """
    node_by_id = {str(row["physical_node_id"]): row for row in node_rows}
    residual_by_id = {str(row["physical_node_id"]): row for row in residual_rows}
    rod_by_id = {str(row["rod_id"]): row for row in rod_rows}
    pulls_by_node: dict[str, dict[str, object]] = {}

    for spec in MANUAL_VIEWER_PART_X_PULLS:
        rod_id = str(spec["rod_id"])
        rod = rod_by_id.get(rod_id)
        if not rod:
            continue
        fraction = float(spec["closer_fraction"])
        for endpoint in (str(rod["node_a"]), str(rod["node_b"])):
            current = pulls_by_node.get(endpoint)
            if current is None or fraction > float(current["closer_fraction"]):
                pulls_by_node[endpoint] = {
                    "closer_fraction": fraction,
                    "parts": [rod_id],
                    "notes": [str(spec["notes"])],
                }
            else:
                current["parts"].append(rod_id)
                current["notes"].append(str(spec["notes"]))

    for pid, pull in sorted(pulls_by_node.items()):
        row = node_by_id.get(pid)
        if not row:
            continue
        old_x = float(row["x_mm"])
        fraction = float(pull["closer_fraction"])
        new_x = old_x * (1.0 - fraction)
        parts = "/".join(str(part) for part in pull["parts"])
        note = f"manual x-pull from {parts}: {old_x:.3f}mm -> {new_x:.3f}mm ({fraction:.3f} closer to X=0)"
        row["x_mm"] = round(new_x, 3)
        row["quality_notes"] = f"{row['quality_notes']}; {note}"
        row["notes"] = f"{row['notes']}; {note}"
        if int(row["constraint_risk"]) < QUALITY_STYLE["moderate_estimate"]["risk"]:
            row["constraint_quality"] = "moderate_estimate"
            row["constraint_risk"] = QUALITY_STYLE["moderate_estimate"]["risk"]
            row["node_color"] = QUALITY_STYLE["moderate_estimate"]["color"]
        residual = residual_by_id.get(pid)
        if residual:
            residual["constraint_quality"] = row["constraint_quality"]
            residual["quality_notes"] = row["quality_notes"]
            issue = str(residual.get("issue", "")).strip()
            residual["issue"] = f"{issue} manual_x_pull_override".strip()



def add_rod(
    rods: dict[tuple[str, str], dict[str, object]],
    node_a: str,
    node_b: str,
    source_view: str,
    source_edge: str,
) -> None:
    if not node_a or not node_b or node_a == node_b:
        return
    key = tuple(sorted((node_a, node_b)))
    if key not in rods:
        rods[key] = {
            "rod_id": "",
            "node_a": key[0],
            "node_b": key[1],
            "source_views": source_view,
            "source_edges": source_edge,
        }
        return
    views = set(str(rods[key]["source_views"]).split())
    views.add(source_view)
    edges = set(str(rods[key]["source_edges"]).split())
    edges.add(source_edge)
    rods[key]["source_views"] = " ".join(sorted(views))
    rods[key]["source_edges"] = " ".join(sorted(edges))


def build_rods(
    projection_to_physical: dict[tuple[str, str], list[str]],
    detail_by_pid: dict[str, dict[str, str]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rods: dict[tuple[str, str], dict[str, object]] = {}
    skipped = []

    def manual_only(pids: list[str]) -> list[str]:
        return [pid for pid in pids if detail_by_pid[pid].get("row_source") == "manual_confirmed"]

    for row in read_csv(EDGES_CSV):
        view = row["view"]
        edge_id = row["edge_id"]
        pids_a = projection_to_physical.get((view, row["node_a"]), [])
        pids_b = projection_to_physical.get((view, row["node_b"]), [])
        if view == "Side":
            pids_a = manual_only(pids_a)
            pids_b = manual_only(pids_b)
        if not pids_a or not pids_b:
            if pids_a or pids_b:
                skipped.append(
                    {
                        "view": view,
                        "edge_id": edge_id,
                        "node_a": row["node_a"],
                        "node_b": row["node_b"],
                        "mapped_a": " ".join(pids_a),
                        "mapped_b": " ".join(pids_b),
                        "reason": "one_endpoint_unmapped_or_side_reuse_suppressed",
                    }
                )
            continue
        for a in pids_a:
            for b in pids_b:
                add_rod(rods, a, b, view, f"{view}:{edge_id}")

    source_to_promoted = {
        row["source_physical_node_id"]: pid
        for pid, row in detail_by_pid.items()
        if row.get("row_source") == "symmetry_promoted" and row.get("source_physical_node_id")
    }
    centerline_pids = {
        pid
        for pid, row in detail_by_pid.items()
        if row.get("row_source") == "manual_confirmed"
        and not row.get("source_physical_node_id")
        and row.get("side_node_source", "") == ""
        and row.get("top_node", "")
    }

    base_rods = list(rods.values())
    for rod in base_rods:
        a = str(rod["node_a"])
        b = str(rod["node_b"])
        a_mirror = source_to_promoted.get(a)
        b_mirror = source_to_promoted.get(b)
        if a_mirror and b_mirror:
            add_rod(rods, a_mirror, b_mirror, "Symmetry", f"mirror:{rod['rod_id'] or a + '-' + b}")
        elif a_mirror and b in centerline_pids:
            add_rod(rods, a_mirror, b, "Symmetry", f"mirror_to_center:{a}-{b}")
        elif b_mirror and a in centerline_pids:
            add_rod(rods, a, b_mirror, "Symmetry", f"mirror_to_center:{a}-{b}")

    rod_rows = list(rods.values())
    rod_rows.sort(key=lambda row: (row["node_a"], row["node_b"]))
    for idx, row in enumerate(rod_rows, start=1):
        row["rod_id"] = f"PSR{idx:03d}"
    return rod_rows, skipped


def annotate_rods(rod_rows: list[dict[str, object]], node_by_id: dict[str, dict[str, object]]) -> None:
    for row in rod_rows:
        a = node_by_id[str(row["node_a"])]
        b = node_by_id[str(row["node_b"])]
        risk = max(int(a["constraint_risk"]), int(b["constraint_risk"]))
        quality = next(key for key, style in QUALITY_STYLE.items() if style["risk"] == risk)
        row["constraint_quality"] = quality
        row["rod_color"] = QUALITY_STYLE[quality]["color"]


def write_html(node_rows: list[dict[str, object]], rod_rows: list[dict[str, object]], residual_rows: list[dict[str, object]]) -> None:
    nodes_json = [
        {
            "id": row["physical_node_id"],
            "label": f"{row['physical_node_id']} F:{row['front_node']} S:{row['side_node'] or '-'} T:{row['top_node'] or '-'}",
            "x": float(row["x_mm"]),
            "y": float(row["y_mm_depth"]),
            "z": float(row["z_mm_up"]),
            "quality": row["constraint_quality"],
            "color": row["node_color"],
            "risk": int(row["constraint_risk"]),
            "depthRegion": row["depth_region"],
            "qualityNotes": row["quality_notes"],
        }
        for row in node_rows
    ]
    rods_json = [
        {
            "id": row["rod_id"],
            "a": row["node_a"],
            "b": row["node_b"],
            "views": row["source_views"],
            "quality": row["constraint_quality"],
            "color": row["rod_color"],
        }
        for row in rod_rows
    ]
    quality_counts = Counter(str(row["constraint_quality"]) for row in node_rows)
    warning_rows = [
        row
        for row in residual_rows
        if row["issue"] or row["constraint_quality"] in {"moderate_estimate", "heavy_estimate", "manual_partial"}
    ]
    warning_rows.sort(
        key=lambda row: (
            -QUALITY_STYLE[str(row["constraint_quality"])]["risk"],
            str(row["physical_node_id"]),
        )
    )
    warning_lines = []
    node_by_id = {str(row["physical_node_id"]): row for row in node_rows}
    for row in warning_rows:
        node = node_by_id[str(row["physical_node_id"])]
        color = html.escape(str(node["node_color"]))
        warning_lines.append(
            f'<tr><td><span class="dot" style="background:{color}"></span>{html.escape(str(row["physical_node_id"]))}</td>'
            f'<td>{html.escape(str(row["constraint_quality"]))}</td>'
            f'<td>{html.escape(str(node["depth_region"]))}</td>'
            f'<td>{html.escape(str(row["issue"]))}</td>'
            f'<td>{html.escape(str(row["quality_notes"]))}</td></tr>'
        )
    if not warning_lines:
        warning_lines.append('<tr><td colspan="5">No weak-constraint nodes.</td></tr>')

    legend_lines = []
    for quality, style in QUALITY_STYLE.items():
        legend_lines.append(
            f'<span class="legend-item"><span class="dot" style="background:{html.escape(style["color"])}"></span>'
            f'{html.escape(style["label"])} ({quality_counts.get(quality, 0)})</span>'
        )

    summary = f"{len(node_rows)} nodes, {len(rod_rows)} rods, {quality_counts.get('heavy_estimate', 0)} heavy-estimate nodes"
    (WORKDIR / f"{OUT_PREFIX}.html").write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Gemini 3D Plus Symmetry Wireframe</title>
  <style>
    body {{ margin: 0; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f4f4f1; color: #172033; }}
    header {{ position: sticky; top: 0; z-index: 2; display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 16px; align-items: center; padding: 12px 16px; border-bottom: 1px solid #d1d5db; background: rgba(244,244,241,.96); }}
    h1 {{ margin: 0; font-size: 16px; }}
    .meta {{ margin-top: 4px; color: #5b6472; font-size: 12px; }}
    button {{ border: 1px solid #aeb7c2; background: #fff; border-radius: 6px; padding: 7px 10px; cursor: pointer; }}
    main {{ display: grid; grid-template-columns: minmax(0, 1fr) 450px; min-height: calc(100vh - 62px); }}
    canvas {{ display: block; width: 100%; height: calc(100vh - 62px); background: #ffffff; }}
    aside {{ border-left: 1px solid #d1d5db; padding: 14px; overflow: auto; max-height: calc(100vh - 90px); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ border-bottom: 1px solid #e2e8f0; padding: 6px 4px; text-align: left; vertical-align: top; }}
    th {{ font-weight: 650; color: #334155; }}
    .hint {{ margin: 0 0 12px; font-size: 12px; color: #5b6472; }}
    .legend {{ display: grid; gap: 6px; margin: 0 0 14px; font-size: 12px; }}
    .legend-item {{ display: flex; gap: 7px; align-items: center; }}
    .dot {{ display: inline-block; width: 10px; height: 10px; margin-right: 6px; border-radius: 50%; border: 1px solid #111827; vertical-align: -1px; }}
    @media (max-width: 900px) {{ main {{ grid-template-columns: 1fr; }} aside {{ border-left: 0; border-top: 1px solid #d1d5db; max-height: none; }} canvas {{ height: 70vh; }} }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Gemini 3D Plus Symmetry Wireframe</h1>
      <div class="meta">{html.escape(summary)}. Red nodes are the heavily estimated locations to review first.</div>
    </div>
    <button id="reset">Reset View</button>
  </header>
  <main>
    <canvas id="canvas"></canvas>
    <aside>
      <p class="hint">Node colors show constraint quality. The back/deep-half tag is inferred from side-view depth, so use it as a review aid, not a fabrication datum.</p>
      <div class="legend">{"".join(legend_lines)}</div>
      <table>
        <thead><tr><th>Node</th><th>Quality</th><th>Region</th><th>Issues</th><th>Why</th></tr></thead>
        <tbody>{"".join(warning_lines)}</tbody>
      </table>
    </aside>
  </main>
  <script>
    const nodes = {json.dumps(nodes_json)};
    const rods = {json.dumps(rods_json)};
    const byId = new Map(nodes.map(n => [n.id, n]));
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");
    let rotX = -0.48;
    let rotZ = -0.72;
    let zoom = 3.5;
    let dragging = false;
    let last = null;

    function resize() {{
      const rect = canvas.getBoundingClientRect();
      canvas.width = Math.max(1, Math.floor(rect.width * devicePixelRatio));
      canvas.height = Math.max(1, Math.floor(rect.height * devicePixelRatio));
      draw();
    }}

    function transform(p) {{
      const cz = Math.cos(rotZ), sz = Math.sin(rotZ);
      const cx = Math.cos(rotX), sx = Math.sin(rotX);
      let x = p.x * cz - p.y * sz;
      let y = p.x * sz + p.y * cz;
      let z = p.z;
      let y2 = y * cx - z * sx;
      let z2 = y * sx + z * cx;
      return {{x, y: y2, z: z2}};
    }}

    function project(p) {{
      const t = transform(p);
      const scale = zoom * devicePixelRatio;
      return {{
        x: canvas.width / 2 + t.x * scale,
        y: canvas.height / 2 - t.y * scale,
        z: t.z
      }};
    }}

    function draw() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.lineCap = "round";
      const projected = new Map(nodes.map(n => [n.id, project(n)]));
      const sortedRods = rods.slice().sort((a, b) => ((projected.get(a.a).z + projected.get(a.b).z) - (projected.get(b.a).z + projected.get(b.b).z)));
      for (const r of sortedRods) {{
        const a = projected.get(r.a), b = projected.get(r.b);
        ctx.strokeStyle = r.color;
        ctx.globalAlpha = r.quality === "heavy_estimate" ? 0.86 : 0.58;
        ctx.lineWidth = (r.quality === "heavy_estimate" ? 3.8 : 2.7) * devicePixelRatio;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }}
      const sortedNodes = nodes.slice().sort((a, b) => project(a).z - project(b).z);
      for (const n of sortedNodes) {{
        const p = projected.get(n.id);
        const radius = 3.0 * devicePixelRatio;
        ctx.globalAlpha = 1;
        ctx.fillStyle = n.color;
        ctx.strokeStyle = "#111827";
        ctx.lineWidth = 1.8 * devicePixelRatio;
        ctx.beginPath();
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        if (n.quality === "heavy_estimate") {{
          ctx.strokeStyle = "#ffffff";
          ctx.lineWidth = 2.4 * devicePixelRatio;
          ctx.beginPath();
          ctx.arc(p.x, p.y, radius + 4 * devicePixelRatio, 0, Math.PI * 2);
          ctx.stroke();
        }}
        ctx.fillStyle = "#111827";
        ctx.font = `${{11 * devicePixelRatio}}px monospace`;
        ctx.fillText(n.id, p.x + 8 * devicePixelRatio, p.y - 8 * devicePixelRatio);
      }}
    }}

    canvas.addEventListener("pointerdown", e => {{ dragging = true; last = {{x: e.clientX, y: e.clientY}}; canvas.setPointerCapture(e.pointerId); }});
    canvas.addEventListener("pointermove", e => {{
      if (!dragging) return;
      const dx = e.clientX - last.x;
      const dy = e.clientY - last.y;
      last = {{x: e.clientX, y: e.clientY}};
      rotZ += dx * 0.008;
      rotX += dy * 0.008;
      draw();
    }});
    canvas.addEventListener("pointerup", () => {{ dragging = false; }});
    canvas.addEventListener("wheel", e => {{
      e.preventDefault();
      zoom *= Math.exp(-e.deltaY * 0.001);
      zoom = Math.max(0.8, Math.min(12, zoom));
      draw();
    }}, {{passive: false}});
    document.getElementById("reset").addEventListener("click", () => {{ rotX = -0.48; rotZ = -0.72; zoom = 3.5; draw(); }});
    addEventListener("resize", resize);
    resize();
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )


def marker_octahedron(center: tuple[float, float, float], radius: float) -> tuple[list[tuple[float, float, float]], list[tuple[int, int, int]]]:
    x, y, z = center
    vertices = [
        (x + radius, y, z),
        (x - radius, y, z),
        (x, y + radius, z),
        (x, y - radius, z),
        (x, y, z + radius),
        (x, y, z - radius),
    ]
    faces = [
        (1, 3, 5), (3, 2, 5), (2, 4, 5), (4, 1, 5),
        (3, 1, 6), (2, 3, 6), (4, 2, 6), (1, 4, 6),
    ]
    return vertices, faces


def write_back_review_markers(node_rows: list[dict[str, object]]) -> None:
    marker_rows = [
        row
        for row in node_rows
        if row["constraint_quality"] == "heavy_estimate" and row["depth_region"] == "back/deep half"
    ]
    marker_csv_rows = [
        {
            "physical_node_id": row["physical_node_id"],
            "front_node": row["front_node"],
            "source_physical_node_id": row["source_physical_node_id"],
            "x_mm": row["x_mm"],
            "y_mm_depth": row["y_mm_depth"],
            "z_mm_up": row["z_mm_up"],
            "quality_notes": row["quality_notes"],
            "notes": row["notes"],
        }
        for row in marker_rows
    ]
    write_csv(
        WORKDIR / "gemini_3d_back_review_nodes.csv",
        [
            "physical_node_id",
            "front_node",
            "source_physical_node_id",
            "x_mm",
            "y_mm_depth",
            "z_mm_up",
            "quality_notes",
            "notes",
        ],
        marker_csv_rows,
    )

    mtl_path = WORKDIR / "gemini-3d-back-review-markers.mtl"
    mtl_path.write_text(
        "newmtl heavy_back_estimate\n"
        "Kd 1.000 0.050 0.050\n"
        "Ka 0.250 0.000 0.000\n"
        "Ks 0.150 0.150 0.150\n"
        "Ns 20\n",
        encoding="utf-8",
    )

    lines = [
        "# Named review markers for heavily estimated back-side points",
        "mtllib gemini-3d-back-review-markers.mtl",
        "usemtl heavy_back_estimate",
    ]
    vertex_offset = 0
    for row in marker_rows:
        pid = str(row["physical_node_id"])
        front = str(row["front_node"] or "no_front")
        source = str(row["source_physical_node_id"] or "no_source")
        name = f"BACK_REVIEW_{pid}_{front}_from_{source}".replace(" ", "_")
        center = (float(row["x_mm"]), float(row["y_mm_depth"]), float(row["z_mm_up"]))
        vertices, faces = marker_octahedron(center, BACK_REVIEW_MARKER_RADIUS_MM)
        lines.append(f"o {name}")
        lines.append("usemtl heavy_back_estimate")
        for vx, vy, vz in vertices:
            lines.append(f"v {vx:.5f} {vy:.5f} {vz:.5f}")
        for a, b, c in faces:
            lines.append(f"f {a + vertex_offset} {b + vertex_offset} {c + vertex_offset}")
        vertex_offset += len(vertices)
    (WORKDIR / "gemini-3d-back-review-markers.obj").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_obj_part_map(node_rows: list[dict[str, object]], rod_rows: list[dict[str, object]]) -> None:
    rows: list[dict[str, object]] = []
    for idx, rod in enumerate(rod_rows, start=1):
        rows.append(
            {
                "obj_part_1_based": idx,
                "obj_part_0_based": idx - 1,
                "object_type": "rod_cylinder",
                "rod_id": rod["rod_id"],
                "node_a": rod["node_a"],
                "node_b": rod["node_b"],
                "physical_node_id": "",
                "source_edges": rod["source_edges"],
                "constraint_quality": rod.get("constraint_quality", ""),
                "x_mm": "",
                "y_mm_depth": "",
                "z_mm_up": "",
            }
        )
    offset = len(rod_rows)
    for idx, node in enumerate(node_rows, start=1):
        rows.append(
            {
                "obj_part_1_based": offset + idx,
                "obj_part_0_based": offset + idx - 1,
                "object_type": "node_sphere",
                "rod_id": "",
                "node_a": "",
                "node_b": "",
                "physical_node_id": node["physical_node_id"],
                "source_edges": "",
                "constraint_quality": node["constraint_quality"],
                "x_mm": node["x_mm"],
                "y_mm_depth": node["y_mm_depth"],
                "z_mm_up": node["z_mm_up"],
            }
        )
    write_csv(
        WORKDIR / "gemini_obj_part_map.csv",
        [
            "obj_part_1_based",
            "obj_part_0_based",
            "object_type",
            "rod_id",
            "node_a",
            "node_b",
            "physical_node_id",
            "source_edges",
            "constraint_quality",
            "x_mm",
            "y_mm_depth",
            "z_mm_up",
        ],
        rows,
    )



def write_report(
    node_rows: list[dict[str, object]],
    rod_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
    skipped_rows: list[dict[str, object]],
    fits: dict[str, tuple[float, float]],
) -> None:
    quality_counts = Counter(str(row["constraint_quality"]) for row in node_rows)
    heavy_back = [
        row
        for row in node_rows
        if row["constraint_quality"] == "heavy_estimate" and row["depth_region"] == "back/deep half"
    ]
    lines = [
        "# Gemini 3D Plus Symmetry Model Report",
        "",
        "This is a proof model generated from manual mappings plus accepted symmetry-derived points. It is not fabrication-ready CAD.",
        "",
        "## Counts",
        "",
        f"- 3D nodes: {len(node_rows)}",
        f"- Rods generated: {len(rod_rows)}",
        f"- Skipped projection edges: {len(skipped_rows)}",
        f"- Heavy-estimate nodes: {quality_counts.get('heavy_estimate', 0)}",
        f"- Heavy-estimate nodes in inferred back/deep half: {len(heavy_back)}",
    ]
    for quality, style in QUALITY_STYLE.items():
        lines.append(f"- {style['label']}: {quality_counts.get(quality, 0)}")
    lines.extend(
        [
            "",
            "## Fit Summary",
            "",
            f"- top_x_to_front_x: x = {fits['top_x_to_front_x'][0]:.6f} * top_x + {fits['top_x_to_front_x'][1]:.3f}",
            f"- top_y_to_side_depth: y = {fits['top_y_to_side_x'][0]:.6f} * top_y + {fits['top_y_to_side_x'][1]:.3f}",
            f"- side_y_to_front_y: z_y = {fits['side_y_to_front_y'][0]:.6f} * side_y + {fits['side_y_to_front_y'][1]:.3f}",
            "",
            "## Files",
            "",
            f"- `{OUT_PREFIX}.html`",
            f"- `{OUT_PREFIX}.obj`",
            f"- `{OUT_PREFIX}.stl`",
            "- `gemini_3d_plus_symmetry_nodes.csv`",
            "- `gemini_3d_plus_symmetry_rods.csv`",
            "- `gemini_obj_part_map.csv`",
            "- `gemini_3d_plus_symmetry_projection_residuals.csv`",
            "- `gemini_3d_plus_symmetry_skipped_edges.csv`",
            "- `gemini-3d-back-review-markers.obj`",
            "- `gemini-3d-back-review-markers.mtl`",
            "- `gemini_3d_back_review_nodes.csv`",
        ]
    )
    (WORKDIR / "gemini_3d_plus_symmetry_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    nodes = load_nodes()
    rows = active_detail_rows()
    fits = build_projection_fits(nodes, rows)
    node_rows, residual_rows, projection_to_physical, detail_by_pid = transform_nodes(nodes, rows, fits)
    apply_manual_node_mirror_overrides(node_rows, residual_rows)
    add_manual_side_only_port_nodes(node_rows, residual_rows, nodes, fits)
    add_manual_side_only_mirror_nodes(node_rows, residual_rows)
    add_manual_top_only_nodes(node_rows, residual_rows, nodes, fits)
    add_manual_nodes(node_rows, residual_rows)
    apply_manual_node_coordinate_overrides(node_rows, residual_rows)
    apply_manual_node_removals(node_rows, residual_rows, projection_to_physical, detail_by_pid)
    rod_rows, skipped_rows = build_rods(projection_to_physical, detail_by_pid)
    rod_rows = apply_manual_rod_edits(rod_rows, node_rows)
    apply_manual_viewer_part_x_pulls(node_rows, residual_rows, rod_rows)
    node_by_id = {str(row["physical_node_id"]): row for row in node_rows}
    annotate_rods(rod_rows, node_by_id)

    node_fields = [
        "physical_node_id",
        "row_source",
        "candidate_status",
        "source_physical_node_id",
        "front_node",
        "side_node",
        "top_node",
        "front_node_source",
        "side_node_source",
        "top_node_source",
        "constraint_quality",
        "constraint_risk",
        "node_color",
        "quality_notes",
        "source_depth_estimated",
        "depth_region",
        "depth_percent",
        "x_mm",
        "y_mm_depth",
        "z_mm_up",
        "x_px",
        "depth_px",
        "z_y_px",
        "front_x_px",
        "side_depth_px",
        "top_depth_as_side_px",
        "front_y_px",
        "side_y_as_front_y_px",
        "notes",
    ]
    write_csv(WORKDIR / "gemini_3d_plus_symmetry_nodes.csv", node_fields, node_rows)
    write_csv(
        WORKDIR / "gemini_3d_plus_symmetry_projection_residuals.csv",
        [
            "physical_node_id",
            "constraint_quality",
            "front_node",
            "side_node",
            "top_node",
            "top_x_error_px",
            "top_depth_error_px",
            "front_side_height_error_px",
            "issue",
            "quality_notes",
        ],
        residual_rows,
    )
    write_csv(
        WORKDIR / "gemini_3d_plus_symmetry_rods.csv",
        ["rod_id", "node_a", "node_b", "source_views", "source_edges", "constraint_quality", "rod_color"],
        rod_rows,
    )
    write_obj_part_map(node_rows, rod_rows)
    write_csv(
        WORKDIR / "gemini_3d_plus_symmetry_skipped_edges.csv",
        ["view", "edge_id", "node_a", "node_b", "mapped_a", "mapped_b", "reason"],
        skipped_rows,
    )

    points = {
        str(row["physical_node_id"]): (float(row["x_mm"]), float(row["y_mm_depth"]), float(row["z_mm_up"]))
        for row in node_rows
    }
    mesh = Mesh()
    for rod in rod_rows:
        mesh.add_cylinder(points[str(rod["node_a"])], points[str(rod["node_b"])], ROD_RADIUS_MM, CYLINDER_SEGMENTS)
    for row in node_rows:
        point = points[str(row["physical_node_id"])]
        mesh.add_sphere(point, NODE_RADIUS_MM, SPHERE_SEGMENTS)

    write_obj(WORKDIR / f"{OUT_PREFIX}.obj", mesh, node_rows, rod_rows)
    write_stl(WORKDIR / f"{OUT_PREFIX}.stl", mesh)
    write_html(node_rows, rod_rows, residual_rows)
    write_back_review_markers(node_rows)
    write_report(node_rows, rod_rows, residual_rows, skipped_rows, fits)


if __name__ == "__main__":
    main()
