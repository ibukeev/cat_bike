#!/usr/bin/env python3
"""Promote accepted symmetry candidates into a derived review mapping.

This keeps `gemini_node_mapping.csv` unchanged. The output is a separate
mapping table that contains the original confirmed points plus symmetry-derived
points accepted for the next 3D proof pass.
"""

from __future__ import annotations

import csv
import html
from pathlib import Path


WORKDIR = Path(__file__).resolve().parent
NODES_CSV = WORKDIR / "gemini_trace_nodes.csv"
EDGES_CSV = WORKDIR / "gemini_trace_edges.csv"
MAPPING_CSV = WORKDIR / "gemini_node_mapping.csv"
CANDIDATES_CSV = WORKDIR / "gemini_symmetry_candidates.csv"
SOURCE_IMAGE_REL = "../../../../../assets/references/cat-head/Gemini_Generated_Image_orxfnrorxfnrorxf.png"

WIDTH = 2334
HEIGHT = 1824
PROMOTED_STATUSES = {"ready_for_review", "partial_trace_match", "needs_manual_trace_or_estimate"}
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


def next_physical_id(existing_rows: list[dict[str, str]]) -> int:
    max_id = 0
    for row in existing_rows:
        pid = row.get("physical_node_id", "")
        if pid.startswith("P") and pid[1:].isdigit():
            max_id = max(max_id, int(pid[1:]))
    return max_id + 1


def load_nodes() -> dict[tuple[str, str], dict[str, object]]:
    nodes: dict[tuple[str, str], dict[str, object]] = {}
    for row in read_csv(NODES_CSV):
        nodes[(row["view"], row["node_id"])] = {
            "view": row["view"],
            "node_id": row["node_id"],
            "x": float(row["x_px"]),
            "y": float(row["y_px"]),
            "snap_count": row.get("snap_count", ""),
            "degree": row.get("degree", ""),
            "node_source": "trace",
        }
    return nodes


def build_promoted_rows() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    original_rows = [row for row in read_csv(MAPPING_CSV) if row.get("status", "").strip().lower() == "confirmed"]
    candidates = [row for row in read_csv(CANDIDATES_CSV) if row.get("candidate_status") in PROMOTED_STATUSES]
    start_id = next_physical_id(original_rows)

    mapping_rows: list[dict[str, object]] = []
    detail_rows: list[dict[str, object]] = []
    virtual_node_rows: list[dict[str, object]] = []

    for row in original_rows:
        mapping_rows.append(
            {
                "physical_node_id": row["physical_node_id"],
                "front_node": row.get("front_node", ""),
                "side_node": row.get("side_node", ""),
                "top_node": row.get("top_node", ""),
                "status": "confirmed",
                "notes": row.get("notes", ""),
            }
        )
        detail_rows.append(
            {
                "physical_node_id": row["physical_node_id"],
                "row_source": "manual_confirmed",
                "symmetry_candidate_id": "",
                "source_physical_node_id": "",
                "front_node": row.get("front_node", ""),
                "front_node_source": "trace" if row.get("front_node", "") else "",
                "side_node": row.get("side_node", ""),
                "side_node_source": "trace" if row.get("side_node", "") else "",
                "top_node": row.get("top_node", ""),
                "top_node_source": "trace" if row.get("top_node", "") else "",
                "candidate_status": "",
                "notes": row.get("notes", ""),
            }
        )

    for idx, row in enumerate(candidates):
        pid = f"P{start_id + idx:03d}"
        cid = row["symmetry_candidate_id"]
        front_node = row.get("mirror_front_node", "").strip()
        top_node = row.get("mirror_top_node", "").strip()
        side_node = row.get("mirror_side_node", "").strip()
        front_source = "trace"
        top_source = "trace"

        if not front_node and row.get("predicted_front_x_px", "").strip():
            front_node = f"F_EST_{cid}"
            front_source = "symmetry_estimate"
            virtual_node_rows.append(
                {
                    "view": "Front",
                    "node_id": front_node,
                    "x_px": row["predicted_front_x_px"],
                    "y_px": row["predicted_front_y_px"],
                    "snap_count": 0,
                    "degree": 0,
                    "node_source": "symmetry_estimate",
                    "symmetry_candidate_id": cid,
                    "notes": "estimated mirror projection; no traced Front node within tolerance",
                }
            )

        if not top_node and row.get("predicted_top_x_px", "").strip():
            top_node = f"T_EST_{cid}"
            top_source = "symmetry_estimate"
            virtual_node_rows.append(
                {
                    "view": "Top",
                    "node_id": top_node,
                    "x_px": row["predicted_top_x_px"],
                    "y_px": row["predicted_top_y_px"],
                    "snap_count": 0,
                    "degree": 0,
                    "node_source": "symmetry_estimate",
                    "symmetry_candidate_id": cid,
                    "notes": "estimated mirror projection; no traced Top node within tolerance",
                }
            )
        elif not top_node:
            top_source = ""

        notes = (
            f"symmetry promoted from {cid}; source={row['source_physical_node_id']}; "
            f"candidate_status={row['candidate_status']}; side projection intentionally omitted for hidden-side mirror"
        )
        mapping_rows.append(
            {
                "physical_node_id": pid,
                "front_node": front_node,
                "side_node": side_node,
                "top_node": top_node,
                "status": "confirmed",
                "notes": notes,
            }
        )
        detail_rows.append(
            {
                "physical_node_id": pid,
                "row_source": "symmetry_promoted",
                "symmetry_candidate_id": cid,
                "source_physical_node_id": row["source_physical_node_id"],
                "front_node": front_node,
                "front_node_source": front_source if front_node else "",
                "side_node": side_node,
                "side_node_source": "hidden_side_not_visible" if side_node else "",
                "top_node": top_node,
                "top_node_source": top_source if top_node else "",
                "candidate_status": row["candidate_status"],
                "notes": notes,
            }
        )

    return mapping_rows, detail_rows, virtual_node_rows


def write_nodes_with_estimates(virtual_node_rows: list[dict[str, object]]) -> None:
    trace_rows = read_csv(NODES_CSV)
    rows: list[dict[str, object]] = []
    for row in trace_rows:
        rows.append(
            {
                "view": row["view"],
                "node_id": row["node_id"],
                "x_px": row["x_px"],
                "y_px": row["y_px"],
                "snap_count": row.get("snap_count", ""),
                "degree": row.get("degree", ""),
                "node_source": "trace",
                "symmetry_candidate_id": "",
                "notes": "",
            }
        )
    rows.extend(virtual_node_rows)
    write_csv(
        WORKDIR / "gemini_trace_nodes_plus_symmetry_estimates.csv",
        ["view", "node_id", "x_px", "y_px", "snap_count", "degree", "node_source", "symmetry_candidate_id", "notes"],
        rows,
    )


def write_review(detail_rows: list[dict[str, object]], virtual_node_rows: list[dict[str, object]]) -> None:
    nodes = load_nodes()
    for row in virtual_node_rows:
        nodes[(str(row["view"]), str(row["node_id"]))] = {
            "view": row["view"],
            "node_id": row["node_id"],
            "x": float(row["x_px"]),
            "y": float(row["y_px"]),
            "node_source": "symmetry_estimate",
        }

    edge_svg = []
    for row in read_csv(EDGES_CSV):
        view = row["view"]
        a = nodes[(view, row["node_a"])]
        b = nodes[(view, row["node_b"])]
        color = VIEW_COLOR.get(view, "#6b7280")
        edge_svg.append(
            f'<line x1="{a["x"]}" y1="{a["y"]}" x2="{b["x"]}" y2="{b["y"]}" '
            f'stroke="{color}" stroke-width="2.1" stroke-linecap="round" opacity="0.16" />'
        )

    mark_svg = []
    for row in detail_rows:
        if row["row_source"] != "symmetry_promoted":
            continue
        color = {
            "ready_for_review": "#22c55e",
            "partial_trace_match": "#f59e0b",
            "needs_manual_trace_or_estimate": "#a855f7",
        }.get(str(row["candidate_status"]), "#64748b")
        pid = str(row["physical_node_id"])
        cid = str(row["symmetry_candidate_id"])
        for view, column, source_column in [
            ("Front", "front_node", "front_node_source"),
            ("Top", "top_node", "top_node_source"),
        ]:
            node_id = str(row[column])
            if not node_id:
                continue
            node = nodes[(view, node_id)]
            estimated = row[source_column] == "symmetry_estimate"
            x = float(node["x"])
            y = float(node["y"])
            title = html.escape(f"{pid} {cid} {view}:{node_id} {row[source_column]}")
            if estimated:
                mark_svg.append(
                    f'<rect x="{x - 8}" y="{y - 8}" width="16" height="16" fill="#ffffff" stroke="{color}" stroke-width="4" transform="rotate(45 {x} {y})"><title>{title}</title></rect>'
                )
            else:
                mark_svg.append(
                    f'<circle cx="{x}" cy="{y}" r="8" fill="{color}" stroke="#111827" stroke-width="3"><title>{title}</title></circle>'
                )
            label = html.escape(f"{pid}/{cid} {node_id}")
            mark_svg.append(
                f'<text x="{x + 11}" y="{y - 9}" font-size="14" font-family="monospace" font-weight="800" fill="{color}" stroke="#ffffff" stroke-width="4" paint-order="stroke">{label}</text>'
            )

    legend_rows = [
        '<rect x="16" y="16" width="660" height="172" rx="8" fill="#ffffff" opacity="0.92" stroke="#cbd5e1" />',
        '<circle cx="38" cy="50" r="8" fill="#22c55e" stroke="#111827" stroke-width="3" />',
        '<text x="58" y="56" font-size="18" font-family="sans-serif">green promoted: traced mirror node(s)</text>',
        '<circle cx="38" cy="84" r="8" fill="#f59e0b" stroke="#111827" stroke-width="3" />',
        '<text x="58" y="90" font-size="18" font-family="sans-serif">orange promoted: partial trace + estimated missing projection</text>',
        '<circle cx="38" cy="118" r="8" fill="#a855f7" stroke="#111827" stroke-width="3" />',
        '<text x="58" y="124" font-size="18" font-family="sans-serif">purple promoted: estimated mirror point(s), no traced node nearby</text>',
        '<rect x="30" y="145" width="16" height="16" fill="#ffffff" stroke="#f59e0b" stroke-width="4" transform="rotate(45 38 153)" />',
        '<text x="58" y="159" font-size="18" font-family="sans-serif">diamond: estimated projection point, not drawn in source SVG</text>',
    ]

    (WORKDIR / "gemini-symmetry-promotion-review.svg").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <image href="{SOURCE_IMAGE_REL}" x="0" y="0" width="{WIDTH}" height="{HEIGHT}" opacity="0.44" />
  <g id="trace-edges">{"".join(edge_svg)}</g>
  <g id="promoted-nodes">{"".join(mark_svg)}</g>
  <g id="legend">{"".join(legend_rows)}</g>
</svg>
""",
        encoding="utf-8",
    )

    (WORKDIR / "gemini-symmetry-promotion-review.html").write_text(
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Gemini Symmetry Promotion Review</title>
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
      <h1>Gemini Symmetry Promotion Review</h1>
      <div class="meta">Derived mapping only. Original manual mapping and 3D model are unchanged.</div>
    </div>
    <label>Zoom <input id="zoom" type="range" min="20" max="140" value="45" /></label>
  </header>
  <main>
    <div class="scroll">
      <img id="review" src="gemini-symmetry-promotion-review.svg" alt="Gemini symmetry promotion review" />
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
    mapping_rows: list[dict[str, object]],
    detail_rows: list[dict[str, object]],
    virtual_node_rows: list[dict[str, object]],
) -> None:
    promoted = [row for row in detail_rows if row["row_source"] == "symmetry_promoted"]
    green = [row for row in promoted if row["candidate_status"] == "ready_for_review"]
    orange = [row for row in promoted if row["candidate_status"] == "partial_trace_match"]
    purple = [row for row in promoted if row["candidate_status"] == "needs_manual_trace_or_estimate"]
    lines = [
        "# Gemini Symmetry Promotion Report",
        "",
        f"- Original confirmed mappings copied: `{len(mapping_rows) - len(promoted)}`",
        f"- Symmetry-promoted mappings added: `{len(promoted)}`",
        f"- Green promoted: `{len(green)}`",
        f"- Orange promoted with estimated projection: `{len(orange)}`",
        f"- Purple promoted as estimate-only symmetry points: `{len(purple)}`",
        f"- Estimated projection nodes created: `{len(virtual_node_rows)}`",
        "",
        "## Files",
        "",
        "- `gemini_node_mapping_plus_symmetry.csv`",
        "- `gemini_node_mapping_plus_symmetry_detail.csv`",
        "- `gemini_trace_nodes_plus_symmetry_estimates.csv`",
        "- `gemini_symmetry_promoted_virtual_nodes.csv`",
        "- `gemini-symmetry-promotion-review.html`",
        "- `gemini-symmetry-promotion-review.svg`",
        "",
        "Original `gemini_node_mapping.csv` is unchanged.",
    ]
    (WORKDIR / "gemini_symmetry_promotion_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    mapping_rows, detail_rows, virtual_node_rows = build_promoted_rows()
    write_csv(
        WORKDIR / "gemini_node_mapping_plus_symmetry.csv",
        ["physical_node_id", "front_node", "side_node", "top_node", "status", "notes"],
        mapping_rows,
    )
    write_csv(
        WORKDIR / "gemini_node_mapping_plus_symmetry_detail.csv",
        [
            "physical_node_id",
            "row_source",
            "symmetry_candidate_id",
            "source_physical_node_id",
            "front_node",
            "front_node_source",
            "side_node",
            "side_node_source",
            "top_node",
            "top_node_source",
            "candidate_status",
            "notes",
        ],
        detail_rows,
    )
    write_csv(
        WORKDIR / "gemini_symmetry_promoted_virtual_nodes.csv",
        ["view", "node_id", "x_px", "y_px", "snap_count", "degree", "node_source", "symmetry_candidate_id", "notes"],
        virtual_node_rows,
    )
    write_nodes_with_estimates(virtual_node_rows)
    write_review(detail_rows, virtual_node_rows)
    write_report(mapping_rows, detail_rows, virtual_node_rows)


if __name__ == "__main__":
    main()
