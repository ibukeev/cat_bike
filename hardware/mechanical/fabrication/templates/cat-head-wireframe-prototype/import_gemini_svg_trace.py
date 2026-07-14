#!/usr/bin/env python3
"""Import the hand-drawn Gemini SVG trace into labeled nodes and edges."""

from __future__ import annotations

import csv
import html
import math
import re
import xml.etree.ElementTree as ET
from collections import defaultdict, deque
from pathlib import Path


WORKDIR = Path(__file__).resolve().parent
SOURCE_SVG = WORKDIR.parents[4] / "assets/references/cat-head/gemini_SVG.svg"
SOURCE_IMAGE_REL = "../../../../../assets/references/cat-head/Gemini_Generated_Image_orxfnrorxfnrorxf.png"
WIDTH = 2334
HEIGHT = 1824
SNAP_TOLERANCE_PX = 5.0

INKSCAPE = "{http://www.inkscape.org/namespaces/inkscape}"
SVG = "{http://www.w3.org/2000/svg}"
VIEW_PREFIX = {
    "Front": "F",
    "Side": "S",
    "Top": "T",
}
VIEW_COLOR = {
    "Front": "#e11d48",
    "Side": "#2563eb",
    "Top": "#16a34a",
}


COMMAND_RE = re.compile(r"[MmLlHhVvZz]|[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?")


def read_svg_root() -> ET.Element:
    if not SOURCE_SVG.exists():
        raise SystemExit(f"Missing SVG trace: {SOURCE_SVG}")
    return ET.parse(SOURCE_SVG).getroot()


def iter_layer_paths(root: ET.Element) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for group in root.iter(f"{SVG}g"):
        label = group.attrib.get(f"{INKSCAPE}label", "")
        if label not in VIEW_PREFIX:
            continue
        for path in group.findall(f"{SVG}path"):
            d = path.attrib.get("d", "").strip()
            if not d:
                continue
            rows.append(
                {
                    "view": label,
                    "svg_path_id": path.attrib.get("id", ""),
                    "d": d,
                }
            )
    return rows


def tokenize_path(d: str) -> list[str]:
    return COMMAND_RE.findall(d.replace(",", " "))


def is_command(token: str) -> bool:
    return len(token) == 1 and token.isalpha()


def parse_path_points(d: str) -> list[tuple[float, float]]:
    tokens = tokenize_path(d)
    idx = 0
    cmd = ""
    x = 0.0
    y = 0.0
    subpath_start: tuple[float, float] | None = None
    points: list[tuple[float, float]] = []

    def number() -> float:
        nonlocal idx
        if idx >= len(tokens) or is_command(tokens[idx]):
            raise ValueError(f"Expected number near token {idx}: {tokens[idx:idx + 4]}")
        value = float(tokens[idx])
        idx += 1
        return value

    while idx < len(tokens):
        if is_command(tokens[idx]):
            cmd = tokens[idx]
            idx += 1
        if not cmd:
            raise ValueError("Path data starts without a command")

        if cmd in ("M", "m"):
            relative_move = cmd == "m"
            first = True
            while idx < len(tokens) and not is_command(tokens[idx]):
                nx = number()
                ny = number()
                if relative_move:
                    x += nx
                    y += ny
                else:
                    x = nx
                    y = ny
                points.append((x, y))
                if first:
                    subpath_start = (x, y)
                    first = False
                cmd = "l" if relative_move else "L"
        elif cmd in ("L", "l"):
            while idx < len(tokens) and not is_command(tokens[idx]):
                nx = number()
                ny = number()
                if cmd == "l":
                    x += nx
                    y += ny
                else:
                    x = nx
                    y = ny
                points.append((x, y))
        elif cmd in ("H", "h"):
            while idx < len(tokens) and not is_command(tokens[idx]):
                nx = number()
                x = x + nx if cmd == "h" else nx
                points.append((x, y))
        elif cmd in ("V", "v"):
            while idx < len(tokens) and not is_command(tokens[idx]):
                ny = number()
                y = y + ny if cmd == "v" else ny
                points.append((x, y))
        elif cmd in ("Z", "z"):
            if subpath_start is not None and points and points[-1] != subpath_start:
                points.append(subpath_start)
            cmd = ""
        else:
            raise ValueError(f"Unsupported SVG path command: {cmd}")
    return points


def segmentize(points: list[tuple[float, float]]) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    for a, b in zip(points, points[1:]):
        if math.dist(a, b) >= 0.5:
            segments.append((a, b))
    return segments


def snap_points(raw_points: list[tuple[str, tuple[float, float]]]) -> tuple[list[dict[str, object]], dict[tuple[str, int], str]]:
    by_view: dict[str, list[tuple[int, tuple[float, float]]]] = defaultdict(list)
    for idx, (view, point) in enumerate(raw_points):
        by_view[view].append((idx, point))

    node_rows: list[dict[str, object]] = []
    raw_to_node: dict[tuple[str, int], str] = {}
    for view in sorted(by_view):
        prefix = VIEW_PREFIX[view]
        clusters: list[list[tuple[int, tuple[float, float]]]] = []
        for raw_idx, point in by_view[view]:
            best_cluster = None
            best_dist = SNAP_TOLERANCE_PX
            for cluster_idx, cluster in enumerate(clusters):
                cx = sum(p[0] for _, p in cluster) / len(cluster)
                cy = sum(p[1] for _, p in cluster) / len(cluster)
                dist = math.dist(point, (cx, cy))
                if dist <= best_dist:
                    best_cluster = cluster_idx
                    best_dist = dist
            if best_cluster is None:
                clusters.append([(raw_idx, point)])
            else:
                clusters[best_cluster].append((raw_idx, point))

        clusters.sort(key=lambda cluster: (sum(p[1] for _, p in cluster) / len(cluster), sum(p[0] for _, p in cluster) / len(cluster)))
        for node_num, cluster in enumerate(clusters, start=1):
            x = sum(point[0] for _, point in cluster) / len(cluster)
            y = sum(point[1] for _, point in cluster) / len(cluster)
            node_id = f"{prefix}{node_num:03d}"
            for raw_idx, _ in cluster:
                raw_to_node[(view, raw_idx)] = node_id
            node_rows.append(
                {
                    "view": view,
                    "node_id": node_id,
                    "x_px": round(x, 3),
                    "y_px": round(y, 3),
                    "snap_count": len(cluster),
                }
            )
    return node_rows, raw_to_node


def angle_degrees(a: tuple[float, float], b: tuple[float, float]) -> float:
    angle = math.degrees(math.atan2(-(b[1] - a[1]), b[0] - a[0]))
    while angle <= -180:
        angle += 360
    while angle > 180:
        angle -= 360
    return angle


def connected_components(view: str, node_ids: set[str], edge_pairs: list[tuple[str, str]]) -> list[set[str]]:
    adjacency: dict[str, set[str]] = {node: set() for node in node_ids}
    for a, b in edge_pairs:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)
    seen: set[str] = set()
    components: list[set[str]] = []
    for node in sorted(adjacency):
        if node in seen:
            continue
        queue = deque([node])
        seen.add(node)
        component: set[str] = set()
        while queue:
            current = queue.popleft()
            component.add(current)
            for nxt in adjacency[current]:
                if nxt not in seen:
                    seen.add(nxt)
                    queue.append(nxt)
        if component:
            components.append(component)
    components.sort(key=lambda c: (-len(c), sorted(c)))
    return components


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_review_svg(node_rows: list[dict[str, object]], edge_rows: list[dict[str, object]]) -> None:
    node_by_key = {(row["view"], row["node_id"]): row for row in node_rows}
    edge_svg = []
    for row in edge_rows:
        a = node_by_key[(row["view"], row["node_a"])]
        b = node_by_key[(row["view"], row["node_b"])]
        color = VIEW_COLOR[str(row["view"])]
        edge_svg.append(
            f'<line x1="{a["x_px"]}" y1="{a["y_px"]}" x2="{b["x_px"]}" y2="{b["y_px"]}" '
            f'stroke="{color}" stroke-width="4" stroke-linecap="round" opacity="0.88" />'
        )

    node_svg = []
    for row in node_rows:
        color = VIEW_COLOR[str(row["view"])]
        x = float(row["x_px"])
        y = float(row["y_px"])
        node_id = html.escape(str(row["node_id"]))
        node_svg.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{color}" stroke="#111827" stroke-width="2" />')
        node_svg.append(
            f'<text x="{x + 9}" y="{y - 9}" font-size="18" font-family="monospace" '
            f'fill="#ffffff" stroke="#111827" stroke-width="4" paint-order="stroke">{node_id}</text>'
        )

    legend_y = 32
    legend = []
    for view, color in VIEW_COLOR.items():
        legend.append(f'<circle cx="28" cy="{legend_y}" r="7" fill="{color}" />')
        legend.append(f'<text x="44" y="{legend_y + 6}" font-size="20" font-family="sans-serif">{html.escape(view)}</text>')
        legend_y += 30

    (WORKDIR / "gemini-trace-node-review.svg").write_text(
        f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" xmlns="http://www.w3.org/2000/svg">
  <image href="{SOURCE_IMAGE_REL}" x="0" y="0" width="{WIDTH}" height="{HEIGHT}" opacity="0.62" />
  <g id="legend">{"".join(legend)}</g>
  <g id="edges">{"".join(edge_svg)}</g>
  <g id="nodes">{"".join(node_svg)}</g>
</svg>
""",
        encoding="utf-8",
    )


def write_review_html() -> None:
    (WORKDIR / "gemini-trace-node-review.html").write_text(
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Gemini Trace Node Review</title>
  <style>
    body {
      margin: 0;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f4f4f1;
      color: #202936;
    }
    header {
      position: sticky;
      top: 0;
      z-index: 2;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 16px;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid #d1d5db;
      background: rgba(244, 244, 241, 0.96);
    }
    h1 {
      margin: 0;
      font-size: 16px;
    }
    .meta {
      margin-top: 4px;
      color: #5b6472;
      font-size: 12px;
    }
    label {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
    }
    input[type="range"] {
      width: 180px;
    }
    main {
      padding: 18px;
    }
    .scroll {
      overflow: auto;
      border: 1px solid #cbd5df;
      max-height: calc(100vh - 94px);
      background: #fff;
    }
    img {
      width: 2334px;
      height: 1824px;
      transform-origin: top left;
      display: block;
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Gemini Trace Node Review</h1>
      <div class="meta">Red = Front, blue = Side, green = Top. Confirm layer placement before mapping nodes.</div>
    </div>
    <label>Zoom <input id="zoom" type="range" min="20" max="140" value="45" /></label>
  </header>
  <main>
    <div class="scroll">
      <img id="review" src="gemini-trace-node-review.svg" alt="Labeled Gemini trace" />
    </div>
  </main>
  <script>
    const zoom = document.getElementById("zoom");
    const review = document.getElementById("review");
    function setZoom() {
      review.style.transform = `scale(${Number(zoom.value) / 100})`;
    }
    zoom.addEventListener("input", setZoom);
    setZoom();
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )


def write_mapping_template() -> None:
    mapping_path = WORKDIR / "gemini_node_mapping.csv"
    if mapping_path.exists():
        return
    write_csv(
        mapping_path,
        ["physical_node_id", "front_node", "side_node", "top_node", "status", "notes"],
        [],
    )


def write_report(
    path_rows: list[dict[str, object]],
    node_rows: list[dict[str, object]],
    edge_rows: list[dict[str, object]],
    warnings: list[str],
) -> None:
    by_view_nodes: dict[str, int] = defaultdict(int)
    by_view_edges: dict[str, int] = defaultdict(int)
    for row in node_rows:
        by_view_nodes[str(row["view"])] += 1
    for row in edge_rows:
        by_view_edges[str(row["view"])] += 1

    lines = [
        "# Gemini SVG Trace Import Report",
        "",
        f"Source SVG: `{SOURCE_SVG}`",
        f"Snap tolerance: `{SNAP_TOLERANCE_PX:.1f}px`",
        "",
        "## Counts",
        "",
    ]
    for view in sorted(set(by_view_nodes) | set(by_view_edges)):
        lines.append(f"- {view}: {by_view_nodes[view]} nodes, {by_view_edges[view]} edges")
    lines.extend(
        [
            "",
            "## Warnings",
            "",
        ]
    )
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Outputs",
            "",
            "- `gemini_trace_paths.csv`",
            "- `gemini_trace_nodes.csv`",
            "- `gemini_trace_edges.csv`",
            "- `gemini_trace_components.csv`",
            "- `gemini_node_mapping.csv`",
            "- `gemini-trace-node-review.svg`",
            "- `gemini-trace-node-review.html`",
        ]
    )
    (WORKDIR / "gemini_trace_import_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    root = read_svg_root()
    raw_paths = iter_layer_paths(root)
    path_rows: list[dict[str, object]] = []
    raw_points: list[tuple[str, tuple[float, float]]] = []
    raw_segments: list[dict[str, object]] = []

    path_count_by_view: dict[str, int] = defaultdict(int)
    for row in raw_paths:
        view = str(row["view"])
        path_count_by_view[view] += 1
        path_id = f"{VIEW_PREFIX[view]}P{path_count_by_view[view]:03d}"
        points = parse_path_points(str(row["d"]))
        segments = segmentize(points)
        if points:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            bbox = (min(xs), min(ys), max(xs), max(ys))
        else:
            bbox = (0.0, 0.0, 0.0, 0.0)
        path_rows.append(
            {
                "path_id": path_id,
                "view": view,
                "svg_path_id": row["svg_path_id"],
                "point_count": len(points),
                "segment_count": len(segments),
                "bbox_x_min": round(bbox[0], 3),
                "bbox_y_min": round(bbox[1], 3),
                "bbox_x_max": round(bbox[2], 3),
                "bbox_y_max": round(bbox[3], 3),
            }
        )
        for a, b in segments:
            a_idx = len(raw_points)
            raw_points.append((view, a))
            b_idx = len(raw_points)
            raw_points.append((view, b))
            raw_segments.append({"view": view, "path_id": path_id, "a_raw": a_idx, "b_raw": b_idx, "a": a, "b": b})

    node_rows, raw_to_node = snap_points(raw_points)
    node_lookup = {(row["view"], row["node_id"]): row for row in node_rows}
    degree: dict[tuple[str, str], int] = defaultdict(int)
    edge_rows: list[dict[str, object]] = []
    seen_edges: set[tuple[str, str, str]] = set()
    edge_count_by_view: dict[str, int] = defaultdict(int)
    for raw in raw_segments:
        view = str(raw["view"])
        a_node = raw_to_node[(view, int(raw["a_raw"]))]
        b_node = raw_to_node[(view, int(raw["b_raw"]))]
        if a_node == b_node:
            continue
        key = (view, *sorted((a_node, b_node)))
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edge_count_by_view[view] += 1
        a = raw["a"]
        b = raw["b"]
        assert isinstance(a, tuple) and isinstance(b, tuple)
        degree[(view, a_node)] += 1
        degree[(view, b_node)] += 1
        edge_rows.append(
            {
                "view": view,
                "edge_id": f"{VIEW_PREFIX[view]}E{edge_count_by_view[view]:03d}",
                "node_a": a_node,
                "node_b": b_node,
                "length_px": round(math.dist(a, b), 3),
                "angle_deg_from_x": round(angle_degrees(a, b), 2),
                "source_path_id": raw["path_id"],
            }
        )

    for row in node_rows:
        row["degree"] = degree.get((str(row["view"]), str(row["node_id"])), 0)

    component_rows: list[dict[str, object]] = []
    warnings: list[str] = []
    for view in sorted({str(row["view"]) for row in node_rows}):
        view_nodes = {str(row["node_id"]) for row in node_rows if row["view"] == view}
        view_edges = [(str(row["node_a"]), str(row["node_b"])) for row in edge_rows if row["view"] == view]
        components = connected_components(view, view_nodes, view_edges)
        if len(components) > 1:
            warnings.append(f"{view} layer has {len(components)} disconnected components. Check if all paths belong in that projection layer.")
        for idx, component in enumerate(components, start=1):
            xs = [float(node_lookup[(view, node)]["x_px"]) for node in component]
            ys = [float(node_lookup[(view, node)]["y_px"]) for node in component]
            component_rows.append(
                {
                    "view": view,
                    "component_id": f"{VIEW_PREFIX[view]}C{idx:02d}",
                    "node_count": len(component),
                    "nodes": " ".join(sorted(component)),
                    "bbox_x_min": round(min(xs), 3),
                    "bbox_y_min": round(min(ys), 3),
                    "bbox_x_max": round(max(xs), 3),
                    "bbox_y_max": round(max(ys), 3),
                }
            )

    write_csv(
        WORKDIR / "gemini_trace_paths.csv",
        ["path_id", "view", "svg_path_id", "point_count", "segment_count", "bbox_x_min", "bbox_y_min", "bbox_x_max", "bbox_y_max"],
        path_rows,
    )
    write_csv(
        WORKDIR / "gemini_trace_nodes.csv",
        ["view", "node_id", "x_px", "y_px", "snap_count", "degree"],
        node_rows,
    )
    write_csv(
        WORKDIR / "gemini_trace_edges.csv",
        ["view", "edge_id", "node_a", "node_b", "length_px", "angle_deg_from_x", "source_path_id"],
        edge_rows,
    )
    write_csv(
        WORKDIR / "gemini_trace_components.csv",
        ["view", "component_id", "node_count", "nodes", "bbox_x_min", "bbox_y_min", "bbox_x_max", "bbox_y_max"],
        component_rows,
    )
    write_mapping_template()
    write_review_svg(node_rows, edge_rows)
    write_review_html()
    write_report(path_rows, node_rows, edge_rows, warnings)


if __name__ == "__main__":
    main()
