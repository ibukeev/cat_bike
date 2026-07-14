#!/usr/bin/env python3
"""Generate a visual review of mapped vs unmapped Gemini trace nodes."""

from __future__ import annotations

import csv
import html
from collections import defaultdict
from pathlib import Path


WORKDIR = Path(__file__).resolve().parent
NODES_CSV = WORKDIR / "gemini_trace_nodes.csv"
EDGES_CSV = WORKDIR / "gemini_trace_edges.csv"
MAPPING_CSV = WORKDIR / "gemini_node_mapping.csv"
ALIASES_CSV = WORKDIR / "gemini_node_aliases.csv"
SOURCE_IMAGE_REL = "../../../../../assets/references/cat-head/Gemini_Generated_Image_orxfnrorxfnrorxf.png"
WIDTH = 2334
HEIGHT = 1824

VIEW_COLOR = {
    "Front": "#e11d48",
    "Side": "#2563eb",
    "Top": "#16a34a",
}
VIEW_COLUMN = {
    "Front": "front_node",
    "Side": "side_node",
    "Top": "top_node",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def active_aliases() -> dict[tuple[str, str], tuple[str, str]]:
    aliases: dict[tuple[str, str], tuple[str, str]] = {}
    if not ALIASES_CSV.exists():
        return aliases
    for row in read_csv(ALIASES_CSV):
        status = row.get("status", "").strip().lower()
        if status in {"rejected", "removed", "no_match"}:
            continue
        view = row.get("view", "").strip()
        alias_node = row.get("alias_node", "").strip()
        canonical_node = row.get("canonical_node", "").strip()
        if view and alias_node and canonical_node:
            aliases[(view, alias_node)] = (view, canonical_node)

    def resolve(key: tuple[str, str]) -> tuple[str, str]:
        seen: set[tuple[str, str]] = set()
        while key in aliases and key not in seen:
            seen.add(key)
            key = aliases[key]
        return key

    return {alias: resolve(canonical) for alias, canonical in aliases.items()}


def mapped_nodes() -> tuple[set[tuple[str, str]], dict[tuple[str, str], list[str]], dict[tuple[str, str], tuple[str, str]]]:
    mapped: set[tuple[str, str]] = set()
    uses: dict[tuple[str, str], list[str]] = defaultdict(list)
    alias_uses: dict[tuple[str, str], tuple[str, str]] = {}
    if not MAPPING_CSV.exists():
        return mapped, uses, alias_uses
    for row in read_csv(MAPPING_CSV):
        status = row.get("status", "").strip().lower()
        if status in {"rejected", "removed", "no_match"}:
            continue
        physical_id = row.get("physical_node_id", "")
        for view, column in VIEW_COLUMN.items():
            node_id = row.get(column, "").strip()
            if not node_id:
                continue
            key = (view, node_id)
            mapped.add(key)
            uses[key].append(physical_id)
    for alias_key, canonical_key in active_aliases().items():
        if canonical_key in mapped:
            mapped.add(alias_key)
            uses[alias_key].extend(uses[canonical_key])
            alias_uses[alias_key] = canonical_key
    return mapped, uses, alias_uses


def node_sort_key(row: dict[str, str]) -> tuple[int, float, float, str]:
    order = {"Front": 0, "Side": 1, "Top": 2}
    return (order.get(row["view"], 9), float(row["y_px"]), float(row["x_px"]), row["node_id"])


def generate() -> None:
    nodes = read_csv(NODES_CSV)
    edges = read_csv(EDGES_CSV)
    mapped, uses, alias_uses = mapped_nodes()
    node_by_key = {(row["view"], row["node_id"]): row for row in nodes}

    unmapped_rows: list[dict[str, object]] = []
    alias_rows: list[dict[str, object]] = []
    duplicate_rows: list[dict[str, object]] = []
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "mapped": 0, "unmapped": 0, "aliased": 0})

    for row in sorted(nodes, key=node_sort_key):
        key = (row["view"], row["node_id"])
        counts[row["view"]]["total"] += 1
        if key in mapped:
            counts[row["view"]]["mapped"] += 1
            if key in alias_uses:
                counts[row["view"]]["aliased"] += 1
                alias_rows.append(
                    {
                        "view": row["view"],
                        "alias_node": row["node_id"],
                        "canonical_node": alias_uses[key][1],
                        "physical_node_ids": " ".join(uses[key]),
                    }
                )
        else:
            counts[row["view"]]["unmapped"] += 1
            unmapped_rows.append(
                {
                    "view": row["view"],
                    "node_id": row["node_id"],
                    "x_px": row["x_px"],
                    "y_px": row["y_px"],
                    "degree": row["degree"],
                }
            )
    for key, physical_ids in sorted(uses.items()):
        if len(physical_ids) > 1:
            duplicate_rows.append(
                {
                    "view": key[0],
                    "node_id": key[1],
                    "physical_node_ids": " ".join(physical_ids),
                }
            )

    write_csv(WORKDIR / "gemini_unmapped_nodes.csv", ["view", "node_id", "x_px", "y_px", "degree"], unmapped_rows)
    write_csv(WORKDIR / "gemini_alias_mapped_nodes.csv", ["view", "alias_node", "canonical_node", "physical_node_ids"], alias_rows)
    write_csv(WORKDIR / "gemini_mapping_duplicate_uses.csv", ["view", "node_id", "physical_node_ids"], duplicate_rows)

    edge_svg = []
    for row in edges:
        view = row["view"]
        a = node_by_key[(view, row["node_a"])]
        b = node_by_key[(view, row["node_b"])]
        color = VIEW_COLOR.get(view, "#6b7280")
        edge_svg.append(
            f'<line x1="{a["x_px"]}" y1="{a["y_px"]}" x2="{b["x_px"]}" y2="{b["y_px"]}" '
            f'stroke="{color}" stroke-width="2.5" stroke-linecap="round" opacity="0.32" />'
        )

    node_svg = []
    for row in sorted(nodes, key=node_sort_key):
        view = row["view"]
        node_id = row["node_id"]
        x = float(row["x_px"])
        y = float(row["y_px"])
        key = (view, node_id)
        view_color = VIEW_COLOR.get(view, "#6b7280")
        label = html.escape(node_id)
        if key in alias_uses:
            canonical = html.escape(alias_uses[key][1])
            physical = html.escape(",".join(uses.get(key, [])))
            node_svg.append(
                f'<circle cx="{x}" cy="{y}" r="8" fill="#38bdf8" stroke="{view_color}" stroke-width="3" opacity="0.9">'
                f"<title>{label} aliases {canonical}, mapped to {physical}</title></circle>"
            )
            node_svg.append(
                f'<text x="{x + 10}" y="{y - 9}" font-size="15" font-family="monospace" font-weight="700" '
                f'fill="#075985" opacity="0.9">{label}->{canonical}</text>'
            )
        elif key in mapped:
            physical = html.escape(",".join(uses.get(key, [])))
            node_svg.append(
                f'<circle cx="{x}" cy="{y}" r="6" fill="#22c55e" stroke="{view_color}" stroke-width="3" opacity="0.82">'
                f"<title>{label} mapped to {physical}</title></circle>"
            )
            node_svg.append(
                f'<text x="{x + 8}" y="{y - 7}" font-size="12" font-family="monospace" '
                f'fill="#166534" opacity="0.72">{label}</text>'
            )
        else:
            node_svg.append(
                f'<circle cx="{x}" cy="{y}" r="10" fill="#facc15" stroke="#111827" stroke-width="3">'
                f"<title>{label} is unmapped</title></circle>"
            )
            node_svg.append(
                f'<text x="{x + 12}" y="{y - 12}" font-size="19" font-family="monospace" font-weight="700" '
                f'fill="#fff7ed" stroke="#111827" stroke-width="5" paint-order="stroke">{label}</text>'
            )

    legend_rows = [
        '<rect x="16" y="16" width="470" height="206" rx="8" fill="#ffffff" opacity="0.88" stroke="#cbd5e1" />',
        '<circle cx="38" cy="48" r="10" fill="#facc15" stroke="#111827" stroke-width="3" />',
        '<text x="58" y="55" font-size="20" font-family="sans-serif">unmapped node</text>',
        '<circle cx="38" cy="82" r="7" fill="#22c55e" stroke="#166534" stroke-width="3" />',
        '<text x="58" y="89" font-size="20" font-family="sans-serif">mapped node</text>',
        '<circle cx="38" cy="116" r="8" fill="#38bdf8" stroke="#075985" stroke-width="3" />',
        '<text x="58" y="123" font-size="20" font-family="sans-serif">alias of mapped node</text>',
    ]
    y = 158
    for view in ["Front", "Side", "Top"]:
        data = counts.get(view, {"total": 0, "mapped": 0, "unmapped": 0, "aliased": 0})
        color = VIEW_COLOR[view]
        text = f'{view}: {data["mapped"]}/{data["total"]} mapped, {data["unmapped"]} unmapped, {data["aliased"]} alias'
        legend_rows.append(f'<circle cx="38" cy="{y}" r="6" fill="{color}" />')
        legend_rows.append(f'<text x="58" y="{y + 7}" font-size="18" font-family="sans-serif">{html.escape(text)}</text>')
        y += 28

    (WORKDIR / "gemini-mapping-coverage-review.svg").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <image href="{SOURCE_IMAGE_REL}" x="0" y="0" width="{WIDTH}" height="{HEIGHT}" opacity="0.48" />
  <g id="edges">{"".join(edge_svg)}</g>
  <g id="nodes">{"".join(node_svg)}</g>
  <g id="legend">{"".join(legend_rows)}</g>
</svg>
""",
        encoding="utf-8",
    )

    (WORKDIR / "gemini-mapping-coverage-review.html").write_text(
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Gemini Mapping Coverage Review</title>
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
      <h1>Gemini Mapping Coverage Review</h1>
      <div class="meta">Yellow nodes are not mapped yet. Green nodes are mapped. Blue nodes alias an already mapped node.</div>
    </div>
    <label>Zoom <input id="zoom" type="range" min="20" max="140" value="45" /></label>
  </header>
  <main>
    <div class="scroll">
      <img id="review" src="gemini-mapping-coverage-review.svg" alt="Gemini mapping coverage review" />
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

    report = [
        "# Gemini Mapping Coverage Report",
        "",
        f"- Physical mapping rows: {len(read_csv(MAPPING_CSV)) if MAPPING_CSV.exists() else 0}",
        f"- Confirmed alias nodes: {len(alias_rows)}",
    ]
    for view in ["Front", "Side", "Top"]:
        data = counts.get(view, {"total": 0, "mapped": 0, "unmapped": 0, "aliased": 0})
        report.append(f"- {view}: {data['mapped']}/{data['total']} mapped, {data['unmapped']} unmapped, {data['aliased']} alias")
    report.extend(
        [
            f"- Duplicate projection-node uses: {len(duplicate_rows)}",
            "",
            "## Files",
            "",
            "- `gemini-mapping-coverage-review.html`",
            "- `gemini-mapping-coverage-review.svg`",
            "- `gemini_unmapped_nodes.csv`",
            "- `gemini_alias_mapped_nodes.csv`",
            "- `gemini_mapping_duplicate_uses.csv`",
        ]
    )
    (WORKDIR / "gemini_mapping_coverage_report.md").write_text("\n".join(report) + "\n", encoding="utf-8")


if __name__ == "__main__":
    generate()
