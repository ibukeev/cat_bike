#!/usr/bin/env python3
"""Generate construction-confidence status from Gemini node mappings."""

from __future__ import annotations

import csv
import html
from collections import Counter, defaultdict
from pathlib import Path


WORKDIR = Path(__file__).resolve().parent
NODES_CSV = WORKDIR / "gemini_trace_nodes.csv"
EDGES_CSV = WORKDIR / "gemini_trace_edges.csv"
MAPPING_CSV = WORKDIR / "gemini_node_mapping.csv"
ALIASES_CSV = WORKDIR / "gemini_node_aliases.csv"
SOURCE_IMAGE_REL = "../../../../../assets/references/cat-head/Gemini_Generated_Image_orxfnrorxfnrorxf.png"
WIDTH = 2334
HEIGHT = 1824

VIEW_COLUMN = {
    "Front": "front_node",
    "Side": "side_node",
    "Top": "top_node",
}
VIEW_COLOR = {
    "Front": "#e11d48",
    "Side": "#2563eb",
    "Top": "#16a34a",
}
STATUS_STYLE = {
    "confirmed_3view": {"fill": "#f59e0b", "stroke": "#7c2d12", "r": 7},
    "confirmed_front_side_no_top": {"fill": "#22c55e", "stroke": "#14532d", "r": 7},
    "confirmed_front_top_side_parked": {"fill": "#a855f7", "stroke": "#581c87", "r": 7},
    "confirmed_front_top": {"fill": "#a855f7", "stroke": "#581c87", "r": 7},
    "confirmed_partial": {"fill": "#94a3b8", "stroke": "#334155", "r": 7},
    "alias": {"fill": "#38bdf8", "stroke": "#075985", "r": 8},
    "unmapped": {"fill": "#facc15", "stroke": "#111827", "r": 8},
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


def mapping_status(row: dict[str, str]) -> tuple[str, str]:
    front = bool(row.get("front_node", "").strip())
    side = bool(row.get("side_node", "").strip())
    top = bool(row.get("top_node", "").strip())
    notes = row.get("notes", "").lower()
    if front and side and top:
        return "confirmed_3view", "ready_for_3d"
    if front and side:
        return "confirmed_front_side_no_top", "usable_depth_height_width_missing_top_check"
    if front and top and not side:
        if "parked" in notes:
            return "confirmed_front_top_side_parked", "needs_side_depth_or_estimate"
        return "confirmed_front_top", "needs_side_depth"
    if side and top and not front:
        return "confirmed_partial", "needs_front_width_or_symmetry"
    if front or side or top:
        return "confirmed_partial", "needs_more_projection_evidence"
    return "confirmed_partial", "empty_mapping_row"


def active_aliases() -> list[dict[str, str]]:
    return [
        row
        for row in read_csv(ALIASES_CSV)
        if row.get("status", "").strip().lower() not in {"rejected", "removed", "no_match"}
    ]


def build_status_rows() -> tuple[list[dict[str, object]], dict[tuple[str, str], dict[str, object]]]:
    rows: list[dict[str, object]] = []
    by_projection_node: dict[tuple[str, str], dict[str, object]] = {}
    confirmed_mappings = [
        row
        for row in read_csv(MAPPING_CSV)
        if row.get("status", "").strip().lower() == "confirmed"
    ]

    for row in confirmed_mappings:
        status, needs = mapping_status(row)
        source_views = " ".join(view.lower() for view, column in VIEW_COLUMN.items() if row.get(column, "").strip())
        out = {
            "row_type": "physical_node",
            "construction_id": row["physical_node_id"],
            "physical_node_id": row["physical_node_id"],
            "view": "",
            "node_id": "",
            "front_node": row.get("front_node", ""),
            "side_node": row.get("side_node", ""),
            "top_node": row.get("top_node", ""),
            "construction_status": status,
            "source_views": source_views,
            "canonical_node": "",
            "source_physical_node_id": "",
            "needs": needs,
            "notes": row.get("notes", ""),
        }
        rows.append(out)
        for view, column in VIEW_COLUMN.items():
            node_id = row.get(column, "").strip()
            if node_id:
                by_projection_node[(view, node_id)] = out

    for alias in active_aliases():
        view = alias["view"]
        alias_node = alias["alias_node"]
        canonical_node = alias["canonical_node"]
        canonical_row = by_projection_node.get((view, canonical_node))
        source_physical = str(canonical_row["physical_node_id"]) if canonical_row else ""
        out = {
            "row_type": "alias",
            "construction_id": f"{view}:{alias_node}",
            "physical_node_id": "",
            "view": view,
            "node_id": alias_node,
            "front_node": "",
            "side_node": "",
            "top_node": "",
            "construction_status": "alias",
            "source_views": view.lower(),
            "canonical_node": canonical_node,
            "source_physical_node_id": source_physical,
            "needs": "uses_canonical_node_geometry",
            "notes": alias.get("notes", ""),
        }
        rows.append(out)
        by_projection_node[(view, alias_node)] = out

    trace_nodes = read_csv(NODES_CSV)
    for node in sorted(trace_nodes, key=node_sort_key):
        key = (node["view"], node["node_id"])
        if key in by_projection_node:
            continue
        rows.append(
            {
                "row_type": "projection_node",
                "construction_id": f"{node['view']}:{node['node_id']}",
                "physical_node_id": "",
                "view": node["view"],
                "node_id": node["node_id"],
                "front_node": node["node_id"] if node["view"] == "Front" else "",
                "side_node": node["node_id"] if node["view"] == "Side" else "",
                "top_node": node["node_id"] if node["view"] == "Top" else "",
                "construction_status": "unmapped",
                "source_views": node["view"].lower(),
                "canonical_node": "",
                "source_physical_node_id": "",
                "needs": "map_to_physical_node_or_mark_estimated_or_ignore",
                "notes": "",
            }
        )
    return rows, by_projection_node


def write_review(rows: list[dict[str, object]], by_projection_node: dict[tuple[str, str], dict[str, object]]) -> None:
    nodes = read_csv(NODES_CSV)
    edges = read_csv(EDGES_CSV)
    node_by_key = {(row["view"], row["node_id"]): row for row in nodes}

    edge_svg = []
    for row in edges:
        view = row["view"]
        a = node_by_key[(view, row["node_a"])]
        b = node_by_key[(view, row["node_b"])]
        color = VIEW_COLOR.get(view, "#6b7280")
        edge_svg.append(
            f'<line x1="{a["x_px"]}" y1="{a["y_px"]}" x2="{b["x_px"]}" y2="{b["y_px"]}" '
            f'stroke="{color}" stroke-width="2.3" stroke-linecap="round" opacity="0.26" />'
        )

    node_svg = []
    for node in sorted(nodes, key=node_sort_key):
        view = node["view"]
        node_id = node["node_id"]
        x = float(node["x_px"])
        y = float(node["y_px"])
        status_row = by_projection_node.get((view, node_id))
        if status_row:
            status = str(status_row["construction_status"])
            construction_id = str(status_row["construction_id"])
            needs = str(status_row["needs"])
        else:
            status = "unmapped"
            construction_id = f"{view}:{node_id}"
            needs = "map_to_physical_node_or_mark_estimated_or_ignore"
        style = STATUS_STYLE.get(status, STATUS_STYLE["confirmed_partial"])
        label = html.escape(node_id)
        title = html.escape(f"{node_id} | {construction_id} | {status} | {needs}")
        node_svg.append(
            f'<circle cx="{x}" cy="{y}" r="{style["r"]}" fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="3">'
            f"<title>{title}</title></circle>"
        )
        font_size = 16 if status in {"alias", "unmapped"} else 12
        suffix = ""
        if status == "alias":
            suffix = f"->{html.escape(str(status_row['canonical_node']))}" if status_row else ""
        node_svg.append(
            f'<text x="{x + 9}" y="{y - 8}" font-size="{font_size}" font-family="monospace" '
            f'font-weight="700" fill="#111827" stroke="#ffffff" stroke-width="3" paint-order="stroke">{label}{suffix}</text>'
        )

    legend_items = [
        ("confirmed_3view", "3-view confirmed"),
        ("confirmed_front_side_no_top", "front+side"),
        ("confirmed_front_top_side_parked", "front+top, side parked"),
        ("alias", "alias"),
        ("unmapped", "unmapped"),
    ]
    legend_rows = ['<rect x="16" y="16" width="430" height="190" rx="8" fill="#ffffff" opacity="0.9" stroke="#cbd5e1" />']
    y = 48
    for status, label in legend_items:
        style = STATUS_STYLE[status]
        legend_rows.append(f'<circle cx="38" cy="{y}" r="{style["r"]}" fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="3" />')
        legend_rows.append(f'<text x="58" y="{y + 7}" font-size="18" font-family="sans-serif">{html.escape(label)}</text>')
        y += 32

    (WORKDIR / "gemini-construction-status-review.svg").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <image href="{SOURCE_IMAGE_REL}" x="0" y="0" width="{WIDTH}" height="{HEIGHT}" opacity="0.44" />
  <g id="edges">{"".join(edge_svg)}</g>
  <g id="nodes">{"".join(node_svg)}</g>
  <g id="legend">{"".join(legend_rows)}</g>
</svg>
""",
        encoding="utf-8",
    )

    (WORKDIR / "gemini-construction-status-review.html").write_text(
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Gemini Construction Status Review</title>
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
      <h1>Gemini Construction Status Review</h1>
      <div class="meta">Construction confidence by node. 3D model not regenerated by this view.</div>
    </div>
    <label>Zoom <input id="zoom" type="range" min="20" max="140" value="45" /></label>
  </header>
  <main>
    <div class="scroll">
      <img id="review" src="gemini-construction-status-review.svg" alt="Gemini construction status review" />
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


def write_report(rows: list[dict[str, object]]) -> None:
    counts = Counter(str(row["construction_status"]) for row in rows)
    lines = [
        "# Gemini Construction Status Report",
        "",
        f"- Total construction-status rows: {len(rows)}",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- {status}: {count}")
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `gemini_node_construction_status.csv`",
            "- `gemini-construction-status-review.html`",
            "- `gemini-construction-status-review.svg`",
        ]
    )
    (WORKDIR / "gemini_construction_status_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows, by_projection_node = build_status_rows()
    write_csv(
        WORKDIR / "gemini_node_construction_status.csv",
        [
            "row_type",
            "construction_id",
            "physical_node_id",
            "view",
            "node_id",
            "front_node",
            "side_node",
            "top_node",
            "construction_status",
            "source_views",
            "canonical_node",
            "source_physical_node_id",
            "needs",
            "notes",
        ],
        rows,
    )
    write_review(rows, by_projection_node)
    write_report(rows)


if __name__ == "__main__":
    main()
