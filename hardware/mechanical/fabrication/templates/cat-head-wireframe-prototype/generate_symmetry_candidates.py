#!/usr/bin/env python3
"""Generate review-only symmetry candidates for the Gemini cat-head trace.

This does not alter the confirmed mapping table and does not regenerate the
3D model. It defines the front/top symmetry axis from confirmed centerline
nodes, mirrors confirmed right-side nodes, and matches those predicted mirror
locations back to visible trace nodes for review.
"""

from __future__ import annotations

import csv
import html
import math
import statistics
from collections import Counter
from pathlib import Path


WORKDIR = Path(__file__).resolve().parent
NODES_CSV = WORKDIR / "gemini_trace_nodes.csv"
EDGES_CSV = WORKDIR / "gemini_trace_edges.csv"
MAPPING_CSV = WORKDIR / "gemini_node_mapping.csv"
ALIASES_CSV = WORKDIR / "gemini_node_aliases.csv"
SOURCE_IMAGE_REL = "../../../../../assets/references/cat-head/Gemini_Generated_Image_orxfnrorxfnrorxf.png"

WIDTH = 2334
HEIGHT = 1824
CENTERLINE_PAIR_TOLERANCE_PX = 4.0
CENTER_NODE_TOLERANCE_PX = 9.0
MATCH_TOLERANCE_PX = 22.0
USER_CENTERLINE_NODES = {
    "Front": {"F010", "F017", "F003", "F004", "F027", "F033", "F034", "F038"},
    "Top": {"T038", "T035", "T018", "T012", "T022", "T001", "T003"},
}

VIEW_COLOR = {
    "Front": "#e11d48",
    "Side": "#2563eb",
    "Top": "#16a34a",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def node_sort_key(row: dict[str, str]) -> tuple[int, float, float, str]:
    order = {"Front": 0, "Side": 1, "Top": 2}
    return (order.get(row["view"], 9), float(row["y_px"]), float(row["x_px"]), row["node_id"])


def load_nodes() -> dict[tuple[str, str], dict[str, object]]:
    nodes: dict[tuple[str, str], dict[str, object]] = {}
    for row in read_csv(NODES_CSV):
        nodes[(row["view"], row["node_id"])] = {
            "view": row["view"],
            "node_id": row["node_id"],
            "x": float(row["x_px"]),
            "y": float(row["y_px"]),
            "degree": row.get("degree", ""),
        }
    return nodes


def active_mappings() -> list[dict[str, str]]:
    return [
        row
        for row in read_csv(MAPPING_CSV)
        if row.get("status", "").strip().lower() == "confirmed"
    ]


def active_aliases() -> list[dict[str, str]]:
    return [
        row
        for row in read_csv(ALIASES_CSV)
        if row.get("status", "").strip().lower() not in {"rejected", "removed", "no_match"}
    ]


def occupied_projection_nodes(mappings: list[dict[str, str]], aliases: list[dict[str, str]]) -> set[tuple[str, str]]:
    occupied: set[tuple[str, str]] = set()
    for row in mappings:
        if row.get("front_node", "").strip():
            occupied.add(("Front", row["front_node"].strip()))
        if row.get("side_node", "").strip():
            occupied.add(("Side", row["side_node"].strip()))
        if row.get("top_node", "").strip():
            occupied.add(("Top", row["top_node"].strip()))
    for row in aliases:
        occupied.add((row["view"].strip(), row["alias_node"].strip()))
        occupied.add((row["view"].strip(), row["canonical_node"].strip()))
    return occupied


def derive_axes(
    nodes: dict[tuple[str, str], dict[str, object]], mappings: list[dict[str, str]]
) -> tuple[float, float, list[dict[str, object]]]:
    raw_rows: list[dict[str, object]] = []

    for row in mappings:
        front_id = row.get("front_node", "").strip()
        top_id = row.get("top_node", "").strip()
        if not front_id or not top_id:
            continue
        front = nodes.get(("Front", front_id))
        top = nodes.get(("Top", top_id))
        if not front or not top:
            continue
        delta = abs(float(front["x"]) - float(top["x"]))
        if delta > CENTERLINE_PAIR_TOLERANCE_PX:
            continue
        raw_rows.append(
            {
                "physical_node_id": row["physical_node_id"],
                "front_node": front_id,
                "front_x_px": round(float(front["x"]), 3),
                "top_node": top_id,
                "top_x_px": round(float(top["x"]), 3),
                "front_top_x_delta_px": round(delta, 3),
                "notes": "front/top x agreement, then filtered to centerline x cluster",
            }
        )

    if len(raw_rows) < 2:
        raise RuntimeError("Not enough confirmed front/top centerline nodes to derive symmetry axes.")

    preliminary_front_axis = statistics.median(float(row["front_x_px"]) for row in raw_rows)
    preliminary_top_axis = statistics.median(float(row["top_x_px"]) for row in raw_rows)
    source_rows = [
        row
        for row in raw_rows
        if abs(float(row["front_x_px"]) - preliminary_front_axis) <= 20.0
        and abs(float(row["top_x_px"]) - preliminary_top_axis) <= 20.0
    ]
    if len(source_rows) < 2:
        source_rows = raw_rows

    front_axis_x = statistics.median(float(row["front_x_px"]) for row in source_rows)
    top_axis_x = statistics.median(float(row["top_x_px"]) for row in source_rows)
    return front_axis_x, top_axis_x, source_rows


def nearest_node(
    nodes: dict[tuple[str, str], dict[str, object]],
    occupied: set[tuple[str, str]],
    view: str,
    x: float,
    y: float,
    exclude_node_id: str,
) -> dict[str, object]:
    candidates = []
    for (node_view, node_id), node in nodes.items():
        if node_view != view or node_id == exclude_node_id:
            continue
        distance = math.hypot(float(node["x"]) - x, float(node["y"]) - y)
        candidates.append((distance, node_id, node))

    if not candidates:
        return {
            "node_id": "",
            "distance_px": "",
            "x_px": "",
            "y_px": "",
            "match_state": "no_trace_nodes",
        }

    candidates.sort(key=lambda item: (item[0], item[1]))
    nearest_unmapped = next(
        ((dist, node_id, node) for dist, node_id, node in candidates if (view, node_id) not in occupied),
        None,
    )
    nearest_any = candidates[0]
    selected = nearest_unmapped if nearest_unmapped and nearest_unmapped[0] <= MATCH_TOLERANCE_PX else nearest_any
    distance, node_id, node = selected

    if distance <= MATCH_TOLERANCE_PX and (view, node_id) not in occupied:
        match_state = "unmapped_trace_match"
    elif distance <= MATCH_TOLERANCE_PX:
        match_state = "occupied_trace_match"
    else:
        match_state = "no_close_trace_match"

    return {
        "node_id": node_id if distance <= MATCH_TOLERANCE_PX else "",
        "distance_px": round(distance, 3),
        "x_px": round(float(node["x"]), 3) if distance <= MATCH_TOLERANCE_PX else "",
        "y_px": round(float(node["y"]), 3) if distance <= MATCH_TOLERANCE_PX else "",
        "match_state": match_state,
    }


def candidate_status(front_match: dict[str, object] | None, top_match: dict[str, object] | None) -> str:
    states = []
    if front_match:
        states.append(str(front_match["match_state"]))
    if top_match:
        states.append(str(top_match["match_state"]))
    if states and all(state == "unmapped_trace_match" for state in states):
        return "ready_for_review"
    if any(state == "unmapped_trace_match" for state in states):
        return "partial_trace_match"
    if any(state == "occupied_trace_match" for state in states):
        return "conflicts_with_existing_mapping"
    return "needs_manual_trace_or_estimate"


def build_candidates(
    nodes: dict[tuple[str, str], dict[str, object]],
    mappings: list[dict[str, str]],
    occupied: set[tuple[str, str]],
    front_axis_x: float,
    top_axis_x: float,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    sequence = 1

    for row in mappings:
        front_id = row.get("front_node", "").strip()
        top_id = row.get("top_node", "").strip()
        side_id = row.get("side_node", "").strip()

        front = nodes.get(("Front", front_id)) if front_id else None
        top = nodes.get(("Top", top_id)) if top_id else None
        front_offset = float(front["x"]) - front_axis_x if front else None
        top_offset = float(top["x"]) - top_axis_x if top else None
        offsets = [offset for offset in [front_offset, top_offset] if offset is not None]
        if not offsets:
            continue
        if max(abs(offset) for offset in offsets) <= CENTER_NODE_TOLERANCE_PX:
            continue
        if max(offsets) <= CENTER_NODE_TOLERANCE_PX:
            continue

        front_match = None
        top_match = None
        predicted_front_x = predicted_front_y = ""
        predicted_top_x = predicted_top_y = ""

        if front:
            predicted_front_x = 2.0 * front_axis_x - float(front["x"])
            predicted_front_y = float(front["y"])
            front_match = nearest_node(nodes, occupied, "Front", predicted_front_x, predicted_front_y, front_id)

        if top:
            predicted_top_x = 2.0 * top_axis_x - float(top["x"])
            predicted_top_y = float(top["y"])
            top_match = nearest_node(nodes, occupied, "Top", predicted_top_x, predicted_top_y, top_id)

        status = candidate_status(front_match, top_match)
        row_id = f"SYM{sequence:03d}"
        sequence += 1
        rows.append(
            {
                "symmetry_candidate_id": row_id,
                "source_physical_node_id": row["physical_node_id"],
                "candidate_status": status,
                "source_front_node": front_id,
                "source_side_node": side_id,
                "source_top_node": top_id,
                "mirror_front_node": front_match["node_id"] if front_match else "",
                "mirror_side_node": "",
                "mirror_top_node": top_match["node_id"] if top_match else "",
                "front_match_state": front_match["match_state"] if front_match else "no_source_front",
                "top_match_state": top_match["match_state"] if top_match else "no_source_top",
                "predicted_front_x_px": "" if predicted_front_x == "" else round(float(predicted_front_x), 3),
                "predicted_front_y_px": "" if predicted_front_y == "" else round(float(predicted_front_y), 3),
                "front_match_distance_px": front_match["distance_px"] if front_match else "",
                "predicted_top_x_px": "" if predicted_top_x == "" else round(float(predicted_top_x), 3),
                "predicted_top_y_px": "" if predicted_top_y == "" else round(float(predicted_top_y), 3),
                "top_match_distance_px": top_match["distance_px"] if top_match else "",
                "front_offset_from_axis_px": "" if front_offset is None else round(front_offset, 3),
                "top_offset_from_axis_px": "" if top_offset is None else round(top_offset, 3),
                "notes": "review_only; no side projection is assigned because the mirrored point is on the hidden side of the side view",
            }
        )

    return rows


def build_centerline_rows(
    nodes: dict[tuple[str, str], dict[str, object]],
    front_axis_x: float,
    top_axis_x: float,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    axis_by_view = {"Front": front_axis_x, "Top": top_axis_x}

    for view in ["Front", "Top"]:
        axis_x = axis_by_view[view]
        requested_nodes = USER_CENTERLINE_NODES[view]
        for (node_view, node_id), node in nodes.items():
            if node_view != view:
                continue
            offset = float(node["x"]) - axis_x
            is_requested = node_id in requested_nodes
            is_on_axis = abs(offset) <= CENTER_NODE_TOLERANCE_PX
            if not is_requested and not is_on_axis:
                continue
            rows.append(
                {
                    "view": view,
                    "node_id": node_id,
                    "x_px": round(float(node["x"]), 3),
                    "y_px": round(float(node["y"]), 3),
                    "axis_x_px": round(axis_x, 3),
                    "offset_from_axis_px": round(offset, 3),
                    "status": "on_symmetry_plane" if is_on_axis else "outside_tolerance",
                    "source": "user_requested" if is_requested else "auto_detected",
                    "notes": "centerline nodes are not mirrored; they define or lie on the symmetry plane",
                }
            )

    return sorted(rows, key=lambda row: (row["view"], float(row["y_px"]), str(row["node_id"])))


def write_definition(front_axis_x: float, top_axis_x: float, axis_sources: list[dict[str, object]]) -> None:
    definition_rows = [
        {
            "parameter": "front_symmetry_axis_x_px",
            "value": round(front_axis_x, 3),
            "source": "median confirmed centerline front x",
            "notes": "mirror rule: x_prime = 2 * axis_x - x; y is unchanged",
        },
        {
            "parameter": "top_symmetry_axis_x_px",
            "value": round(top_axis_x, 3),
            "source": "median confirmed centerline top x",
            "notes": "mirror rule: x_prime = 2 * axis_x - x; y/depth is unchanged",
        },
        {
            "parameter": "side_projection_rule",
            "value": "do_not_assign_hidden_side_node",
            "source": "orthographic side projection",
            "notes": "the side reference shows the visible side/silhouette; hidden-side mirrored points do not get a side trace constraint",
        },
        {
            "parameter": "center_node_tolerance_px",
            "value": CENTER_NODE_TOLERANCE_PX,
            "source": "script constant",
            "notes": "nodes closer than this to both axes are treated as centerline, not mirrored",
        },
        {
            "parameter": "trace_match_tolerance_px",
            "value": MATCH_TOLERANCE_PX,
            "source": "script constant",
            "notes": "nearest visible trace node within this radius is treated as a candidate match",
        },
    ]
    write_csv(
        WORKDIR / "gemini_symmetry_definition.csv",
        ["parameter", "value", "source", "notes"],
        definition_rows,
    )
    write_csv(
        WORKDIR / "gemini_symmetry_axis_source_nodes.csv",
        ["physical_node_id", "front_node", "front_x_px", "top_node", "top_x_px", "front_top_x_delta_px", "notes"],
        axis_sources,
    )


def write_review(
    nodes: dict[tuple[str, str], dict[str, object]],
    candidates: list[dict[str, object]],
    centerline_rows: list[dict[str, object]],
    front_axis_x: float,
    top_axis_x: float,
) -> None:
    edges = read_csv(EDGES_CSV)
    node_by_key = nodes

    edge_svg = []
    for row in edges:
        view = row["view"]
        a = node_by_key[(view, row["node_a"])]
        b = node_by_key[(view, row["node_b"])]
        color = VIEW_COLOR.get(view, "#6b7280")
        edge_svg.append(
            f'<line x1="{a["x"]}" y1="{a["y"]}" x2="{b["x"]}" y2="{b["y"]}" '
            f'stroke="{color}" stroke-width="2.2" stroke-linecap="round" opacity="0.18" />'
        )

    axis_svg = [
        f'<line x1="{front_axis_x}" y1="245" x2="{front_axis_x}" y2="935" stroke="#111827" stroke-width="4" stroke-dasharray="12 10" opacity="0.85" />',
        f'<text x="{front_axis_x + 12}" y="265" font-size="18" font-family="monospace" font-weight="800" fill="#111827" stroke="#ffffff" stroke-width="3" paint-order="stroke">Front axis x={front_axis_x:.1f}</text>',
        f'<line x1="{top_axis_x}" y1="1260" x2="{top_axis_x}" y2="1728" stroke="#111827" stroke-width="4" stroke-dasharray="12 10" opacity="0.85" />',
        f'<text x="{top_axis_x + 12}" y="1282" font-size="18" font-family="monospace" font-weight="800" fill="#111827" stroke="#ffffff" stroke-width="3" paint-order="stroke">Top axis x={top_axis_x:.1f}</text>',
    ]

    node_marks = []
    for row in centerline_rows:
        if row["status"] != "on_symmetry_plane":
            continue
        view = str(row["view"])
        node_id = str(row["node_id"])
        node = nodes[(view, node_id)]
        requested = row["source"] == "user_requested"
        opacity = 0.95 if requested else 0.45
        radius = 7 if requested else 5
        label = html.escape(node_id)
        title = html.escape(f"{node_id} | {view} centerline | dx={row['offset_from_axis_px']} px | {row['source']}")
        node_marks.append(
            f'<circle cx="{node["x"]}" cy="{node["y"]}" r="{radius}" fill="#0ea5e9" stroke="#082f49" stroke-width="3" opacity="{opacity}"><title>{title}</title></circle>'
        )
        if requested:
            node_marks.append(
                f'<text x="{float(node["x"]) + 10}" y="{float(node["y"]) + 5}" font-size="14" font-family="monospace" font-weight="800" fill="#075985" stroke="#ffffff" stroke-width="4" paint-order="stroke">{label}</text>'
            )

    for row in candidates:
        cid = str(row["symmetry_candidate_id"])
        sid = str(row["source_physical_node_id"])
        front_id = str(row["source_front_node"])
        top_id = str(row["source_top_node"])
        mirror_front = str(row["mirror_front_node"])
        mirror_top = str(row["mirror_top_node"])
        status = str(row["candidate_status"])
        color = {
            "ready_for_review": "#22c55e",
            "partial_trace_match": "#f59e0b",
            "conflicts_with_existing_mapping": "#ef4444",
            "needs_manual_trace_or_estimate": "#a855f7",
        }.get(status, "#64748b")

        if front_id:
            source = nodes[("Front", front_id)]
            px = float(row["predicted_front_x_px"])
            py = float(row["predicted_front_y_px"])
            title = html.escape(
                f"{cid} from {sid} front: predicted ({px:.1f},{py:.1f}) -> {mirror_front} | {row['front_match_state']}"
            )
            node_marks.append(
                f'<line x1="{source["x"]}" y1="{source["y"]}" x2="{px}" y2="{py}" stroke="{color}" stroke-width="1.6" stroke-dasharray="6 6" opacity="0.65"><title>{title}</title></line>'
            )
            node_marks.append(
                f'<circle cx="{source["x"]}" cy="{source["y"]}" r="5" fill="#ffffff" stroke="{color}" stroke-width="3"><title>{title}</title></circle>'
            )
            node_marks.append(
                f'<path d="M {px - 8} {py} L {px + 8} {py} M {px} {py - 8} L {px} {py + 8}" stroke="{color}" stroke-width="4" stroke-linecap="round"><title>{title}</title></path>'
            )
            label = html.escape(f"{cid} {mirror_front}")
            node_marks.append(
                f'<text x="{px + 10}" y="{py - 8}" font-size="15" font-family="monospace" font-weight="800" fill="{color}" stroke="#ffffff" stroke-width="4" paint-order="stroke">{label}</text>'
            )

        if top_id:
            source = nodes[("Top", top_id)]
            px = float(row["predicted_top_x_px"])
            py = float(row["predicted_top_y_px"])
            title = html.escape(
                f"{cid} from {sid} top: predicted ({px:.1f},{py:.1f}) -> {mirror_top} | {row['top_match_state']}"
            )
            node_marks.append(
                f'<line x1="{source["x"]}" y1="{source["y"]}" x2="{px}" y2="{py}" stroke="{color}" stroke-width="1.6" stroke-dasharray="6 6" opacity="0.65"><title>{title}</title></line>'
            )
            node_marks.append(
                f'<circle cx="{source["x"]}" cy="{source["y"]}" r="5" fill="#ffffff" stroke="{color}" stroke-width="3"><title>{title}</title></circle>'
            )
            node_marks.append(
                f'<path d="M {px - 8} {py} L {px + 8} {py} M {px} {py - 8} L {px} {py + 8}" stroke="{color}" stroke-width="4" stroke-linecap="round"><title>{title}</title></path>'
            )
            label = html.escape(f"{cid} {mirror_top}")
            node_marks.append(
                f'<text x="{px + 10}" y="{py - 8}" font-size="15" font-family="monospace" font-weight="800" fill="{color}" stroke="#ffffff" stroke-width="4" paint-order="stroke">{label}</text>'
            )

    legend_items = [
        ("#0ea5e9", "centerline: lies on symmetry plane, not mirrored"),
        ("#22c55e", "ready: predicted mirror matches traced unmapped node(s)"),
        ("#f59e0b", "partial: only one available projection matched"),
        ("#ef4444", "conflict: mirror lands on an already mapped node"),
        ("#a855f7", "needs trace/estimate: no traced node near prediction"),
    ]
    legend_rows = ['<rect x="16" y="16" width="690" height="202" rx="8" fill="#ffffff" opacity="0.92" stroke="#cbd5e1" />']
    y = 48
    for color, label in legend_items:
        legend_rows.append(f'<path d="M 28 {y} L 52 {y}" stroke="{color}" stroke-width="5" stroke-linecap="round" />')
        legend_rows.append(f'<text x="66" y="{y + 6}" font-size="17" font-family="sans-serif">{html.escape(label)}</text>')
        y += 31

    (WORKDIR / "gemini-symmetry-candidates-review.svg").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <image href="{SOURCE_IMAGE_REL}" x="0" y="0" width="{WIDTH}" height="{HEIGHT}" opacity="0.44" />
  <g id="trace-edges">{"".join(edge_svg)}</g>
  <g id="symmetry-axis">{"".join(axis_svg)}</g>
  <g id="symmetry-candidates">{"".join(node_marks)}</g>
  <g id="legend">{"".join(legend_rows)}</g>
</svg>
""",
        encoding="utf-8",
    )

    (WORKDIR / "gemini-symmetry-candidates-review.html").write_text(
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Gemini Symmetry Candidates Review</title>
  <style>
    body { margin: 0; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f4f4f1; color: #202936; }
    header { position: sticky; top: 0; z-index: 2; display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 16px; align-items: center; padding: 12px 16px; border-bottom: 1px solid #d1d5db; background: rgba(244,244,241,.96); }
    h1 { margin: 0; font-size: 16px; }
    .meta { margin-top: 4px; color: #5b6472; font-size: 12px; }
    label { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; }
    input[type="range"] { width: 180px; }
    main { padding: 18px; }
    .scroll { overflow: auto; border: 1px solid #cbd5df; max-height: calc(100vh - 94px); background: #fff; }
    img { width: 2334px; height: 1824px; transform-origin: top left; display: block; }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Gemini Symmetry Candidates Review</h1>
      <div class="meta">Review-only mirror candidates. Confirmed mapping and 3D model are unchanged.</div>
    </div>
    <label>Zoom <input id="zoom" type="range" min="20" max="140" value="45" /></label>
  </header>
  <main>
    <div class="scroll">
      <img id="review" src="gemini-symmetry-candidates-review.svg" alt="Gemini symmetry candidates review" />
    </div>
  </main>
  <script>
    const zoom = document.getElementById("zoom");
    const review = document.getElementById("review");
    function setZoom() { review.style.transform = `scale(${Number(zoom.value) / 100})`; }
    zoom.addEventListener("input", setZoom);
    setZoom();
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )


def write_report(
    candidates: list[dict[str, object]],
    centerline_rows: list[dict[str, object]],
    front_axis_x: float,
    top_axis_x: float,
) -> None:
    counts = Counter(str(row["candidate_status"]) for row in candidates)
    centerline_counts = Counter(str(row["source"]) for row in centerline_rows if row["status"] == "on_symmetry_plane")
    lines = [
        "# Gemini Symmetry Candidate Report",
        "",
        f"- Front symmetry axis x: `{front_axis_x:.3f}` px",
        f"- Top symmetry axis x: `{top_axis_x:.3f}` px",
        f"- Candidate mirrored nodes: `{len(candidates)}`",
        f"- Centerline nodes on symmetry plane: `{sum(centerline_counts.values())}`",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- {status}: `{count}`")
    for source, count in sorted(centerline_counts.items()):
        lines.append(f"- centerline_{source}: `{count}`")
    lines.extend(
        [
            "",
            "## Rule",
            "",
            "- Front and top mirror rule: `x' = 2 * axis_x - x`; y is unchanged.",
            "- Centerline rule: nodes within `center_node_tolerance_px` of the axis are on the symmetry plane and are not mirrored.",
            "- Side projection rule: do not assign a side trace node to hidden-side mirrored points; the side reference shows the visible side/silhouette.",
            "- Green means the predicted mirror point landed on an existing traced node that is not already in the confirmed mapping table.",
            "- Yellow means only one of the available mirrored projections landed on a traced node; the other projection still needs a trace or estimate.",
            "- This is a review-only artifact. It does not update `gemini_node_mapping.csv` or any 3D files.",
            "",
            "## Files",
            "",
            "- `gemini_symmetry_definition.csv`",
            "- `gemini_symmetry_axis_source_nodes.csv`",
            "- `gemini_symmetry_centerline_nodes.csv`",
            "- `gemini_symmetry_candidates.csv`",
            "- `gemini-symmetry-candidates-review.html`",
            "- `gemini-symmetry-candidates-review.svg`",
        ]
    )
    (WORKDIR / "gemini_symmetry_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    nodes = load_nodes()
    mappings = active_mappings()
    aliases = active_aliases()
    occupied = occupied_projection_nodes(mappings, aliases)
    front_axis_x, top_axis_x, axis_sources = derive_axes(nodes, mappings)
    candidates = build_candidates(nodes, mappings, occupied, front_axis_x, top_axis_x)
    centerline_rows = build_centerline_rows(nodes, front_axis_x, top_axis_x)

    write_definition(front_axis_x, top_axis_x, axis_sources)
    write_csv(
        WORKDIR / "gemini_symmetry_centerline_nodes.csv",
        [
            "view",
            "node_id",
            "x_px",
            "y_px",
            "axis_x_px",
            "offset_from_axis_px",
            "status",
            "source",
            "notes",
        ],
        centerline_rows,
    )
    write_csv(
        WORKDIR / "gemini_symmetry_candidates.csv",
        [
            "symmetry_candidate_id",
            "source_physical_node_id",
            "candidate_status",
            "source_front_node",
            "source_side_node",
            "source_top_node",
            "mirror_front_node",
            "mirror_side_node",
            "mirror_top_node",
            "front_match_state",
            "top_match_state",
            "predicted_front_x_px",
            "predicted_front_y_px",
            "front_match_distance_px",
            "predicted_top_x_px",
            "predicted_top_y_px",
            "top_match_distance_px",
            "front_offset_from_axis_px",
            "top_offset_from_axis_px",
            "notes",
        ],
        candidates,
    )
    write_review(nodes, candidates, centerline_rows, front_axis_x, top_axis_x)
    write_report(candidates, centerline_rows, front_axis_x, top_axis_x)


if __name__ == "__main__":
    main()
