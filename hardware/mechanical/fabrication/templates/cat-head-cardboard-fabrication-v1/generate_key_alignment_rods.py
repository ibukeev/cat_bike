#!/usr/bin/env python3
"""Generate key cardboard jig rods and visual assembly instructions."""

from __future__ import annotations

import csv
import html
import math
from collections import defaultdict
from pathlib import Path


WORKDIR = Path(__file__).resolve().parent
SOURCE_DIR = WORKDIR.parent / "cat-head-wireframe-prototype" / "versions" / "v1-shape-approved-cardboard-prototype"
NODES_CSV = SOURCE_DIR / "data" / "gemini_3d_plus_symmetry_nodes.csv"
RODS_CSV = SOURCE_DIR / "data" / "gemini_3d_plus_symmetry_rods.csv"

OUT_DATA = WORKDIR / "data"
OUT_ASSEMBLY = WORKDIR / "assembly"


KEY_RODS = [
    {
        "key_rod_id": "K001",
        "step": 1,
        "step_name": "Center spine",
        "rod_kind": "surface_edge",
        "node_a": "P024",
        "node_b": "P010",
        "role": "front centerline upper spine",
        "install": "Tape this first as the upper centerline reference.",
        "keep": "temporary_or_keep",
        "criticality": "high",
    },
    {
        "key_rod_id": "K002",
        "step": 1,
        "step_name": "Center spine",
        "rod_kind": "temporary_gauge",
        "node_a": "P010",
        "node_b": "P022",
        "role": "front centerline nose gauge",
        "install": "Add after K001 to locate the nose centerline.",
        "keep": "temporary",
        "criticality": "high",
    },
    {
        "key_rod_id": "K003",
        "step": 1,
        "step_name": "Center spine",
        "rod_kind": "temporary_gauge",
        "node_a": "P022",
        "node_b": "P003",
        "role": "nose to lower center gauge",
        "install": "Completes the centerline from forehead through nose to lower center.",
        "keep": "temporary",
        "criticality": "high",
    },
    {
        "key_rod_id": "K004",
        "step": 2,
        "step_name": "Bottom width frame",
        "rod_kind": "surface_edge",
        "node_a": "P005",
        "node_b": "P035",
        "role": "front lower chin width",
        "install": "Install square to the center spine; this sets the lower front width.",
        "keep": "temporary_or_keep",
        "criticality": "high",
    },
    {
        "key_rod_id": "K005",
        "step": 2,
        "step_name": "Bottom width frame",
        "rod_kind": "temporary_gauge",
        "node_a": "P031",
        "node_b": "P057",
        "role": "rear lower width gauge",
        "install": "Use as a removable spacer across the rear/lower side points.",
        "keep": "temporary",
        "criticality": "medium",
    },
    {
        "key_rod_id": "K006",
        "step": 2,
        "step_name": "Bottom width frame",
        "rod_kind": "surface_edge",
        "node_a": "P060",
        "node_b": "P072",
        "role": "rear bottom width edge",
        "install": "Sets the back-bottom width and keeps the rear from pinching.",
        "keep": "temporary_or_keep",
        "criticality": "high",
    },
    {
        "key_rod_id": "K007",
        "step": 3,
        "step_name": "Upper width gauges",
        "rod_kind": "temporary_gauge",
        "node_a": "P028",
        "node_b": "P054",
        "role": "upper cheek / forehead width",
        "install": "Use as an across-head spacer while taping forehead and cheek panels.",
        "keep": "temporary",
        "criticality": "high",
    },
    {
        "key_rod_id": "K008",
        "step": 3,
        "step_name": "Upper width gauges",
        "rod_kind": "temporary_gauge",
        "node_a": "P026",
        "node_b": "P052",
        "role": "ear-base lower width",
        "install": "Locks the left/right ear-base lower corners before ear panels go on.",
        "keep": "temporary",
        "criticality": "high",
    },
    {
        "key_rod_id": "K009",
        "step": 3,
        "step_name": "Upper width gauges",
        "rod_kind": "temporary_gauge",
        "node_a": "P064",
        "node_b": "P067",
        "role": "rear upper width gauge",
        "install": "Use at the back/top area to keep the shell symmetric.",
        "keep": "temporary",
        "criticality": "medium",
    },
    {
        "key_rod_id": "K010",
        "step": 3,
        "step_name": "Upper width gauges",
        "rod_kind": "temporary_gauge",
        "node_a": "P007",
        "node_b": "P037",
        "role": "ear-tip width gauge",
        "install": "Use only as a temporary ear-tip spacing gauge; remove after ears are taped.",
        "keep": "temporary",
        "criticality": "medium",
    },
    {
        "key_rod_id": "K011",
        "step": 4,
        "step_name": "Ear anchors",
        "rod_kind": "surface_edge",
        "node_a": "P026",
        "node_b": "P069",
        "role": "right ear lower surface anchor",
        "install": "Install on the right side after K008; this anchors the projected ear edge to the head surface.",
        "keep": "keep",
        "criticality": "high",
    },
    {
        "key_rod_id": "K012",
        "step": 4,
        "step_name": "Ear anchors",
        "rod_kind": "surface_edge",
        "node_a": "P052",
        "node_b": "P066",
        "role": "left ear lower surface anchor",
        "install": "Mirror of K011; install at the same time so the ears stay symmetric.",
        "keep": "keep",
        "criticality": "high",
    },
    {
        "key_rod_id": "K013",
        "step": 4,
        "step_name": "Ear anchors",
        "rod_kind": "surface_edge",
        "node_a": "P007",
        "node_b": "P069",
        "role": "right ear outer anchor",
        "install": "Connects the right ear tip to the projected ear edge node.",
        "keep": "keep",
        "criticality": "high",
    },
    {
        "key_rod_id": "K014",
        "step": 4,
        "step_name": "Ear anchors",
        "rod_kind": "surface_edge",
        "node_a": "P037",
        "node_b": "P066",
        "role": "left ear outer anchor",
        "install": "Mirror of K013; keep both ear tips at matching angles.",
        "keep": "keep",
        "criticality": "high",
    },
    {
        "key_rod_id": "K015",
        "step": 4,
        "step_name": "Ear anchors",
        "rod_kind": "temporary_gauge",
        "node_a": "P007",
        "node_b": "P026",
        "role": "right ear height gauge",
        "install": "Temporary straight gauge for right ear height and rake.",
        "keep": "temporary",
        "criticality": "medium",
    },
    {
        "key_rod_id": "K016",
        "step": 4,
        "step_name": "Ear anchors",
        "rod_kind": "temporary_gauge",
        "node_a": "P037",
        "node_b": "P052",
        "role": "left ear height gauge",
        "install": "Temporary straight gauge for left ear height and rake.",
        "keep": "temporary",
        "criticality": "medium",
    },
    {
        "key_rod_id": "K017",
        "step": 5,
        "step_name": "Twist locks",
        "rod_kind": "temporary_gauge",
        "node_a": "P024",
        "node_b": "P071",
        "role": "right rear-depth diagonal",
        "install": "Temporary diagonal from forehead center to right rear depth point; prevents twist.",
        "keep": "temporary",
        "criticality": "medium",
    },
    {
        "key_rod_id": "K018",
        "step": 5,
        "step_name": "Twist locks",
        "rod_kind": "temporary_gauge",
        "node_a": "P024",
        "node_b": "P062",
        "role": "left rear-depth diagonal",
        "install": "Mirror of K017; use both diagonals together.",
        "keep": "temporary",
        "criticality": "medium",
    },
    {
        "key_rod_id": "K019",
        "step": 5,
        "step_name": "Twist locks",
        "rod_kind": "temporary_gauge",
        "node_a": "P003",
        "node_b": "P031",
        "role": "right lower-depth diagonal",
        "install": "Temporary lower diagonal to prevent the bottom from skewing.",
        "keep": "temporary",
        "criticality": "medium",
    },
    {
        "key_rod_id": "K020",
        "step": 5,
        "step_name": "Twist locks",
        "rod_kind": "temporary_gauge",
        "node_a": "P003",
        "node_b": "P057",
        "role": "left lower-depth diagonal",
        "install": "Mirror of K019; remove after enough panels are taped.",
        "keep": "temporary",
        "criticality": "medium",
    },
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def point(row: dict[str, str]) -> tuple[float, float, float]:
    return (float(row["x_mm"]), float(row["y_mm_depth"]), float(row["z_mm_up"]))


def dist(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((aa - bb) ** 2 for aa, bb in zip(a, b)))


def edge_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def build_rows() -> tuple[list[dict[str, object]], dict[str, dict[str, str]]]:
    nodes = {row["physical_node_id"]: row for row in read_csv(NODES_CSV)}
    wire_rods = {edge_key(row["node_a"], row["node_b"]): row for row in read_csv(RODS_CSV)}
    rows = []
    for spec in KEY_RODS:
        a = nodes[spec["node_a"]]
        b = nodes[spec["node_b"]]
        pa = point(a)
        pb = point(b)
        length = dist(pa, pb)
        wire = wire_rods.get(edge_key(spec["node_a"], spec["node_b"]))
        rows.append(
            {
                **spec,
                "wireframe_rod_id": "" if wire is None else wire["rod_id"],
                "is_existing_wireframe_edge": "yes" if wire else "no",
                "node_a_x_mm": round(pa[0], 3),
                "node_a_y_depth_mm": round(pa[1], 3),
                "node_a_z_up_mm": round(pa[2], 3),
                "node_b_x_mm": round(pb[0], 3),
                "node_b_y_depth_mm": round(pb[1], 3),
                "node_b_z_up_mm": round(pb[2], 3),
                "gauge_length_mm": round(length, 2),
                "cardboard_strip_cut_length_mm": round(length + 20.0, 2),
                "fabrication_note": "Mark the gauge length on the strip; leave about 10 mm extra at each end for tape tabs.",
            }
        )
    return rows, nodes


def project(point_xyz: tuple[float, float, float], view: str) -> tuple[float, float]:
    x, y, z = point_xyz
    if view == "front":
        return x, z
    if view == "side":
        return y, z
    if view == "top":
        return x, y
    raise ValueError(view)


def svg_view(
    title: str,
    view: str,
    nodes: dict[str, dict[str, str]],
    all_rows: list[dict[str, object]],
    current_rows: list[dict[str, object]],
    previous_rows: list[dict[str, object]],
    width: int = 420,
    height: int = 320,
) -> str:
    all_points = [project(point(row), view) for row in nodes.values()]
    min_u = min(p[0] for p in all_points)
    max_u = max(p[0] for p in all_points)
    min_v = min(p[1] for p in all_points)
    max_v = max(p[1] for p in all_points)
    pad = 32
    scale = min((width - pad * 2) / max(max_u - min_u, 1.0), (height - pad * 2) / max(max_v - min_v, 1.0))
    mid_u = (min_u + max_u) / 2.0
    mid_v = (min_v + max_v) / 2.0

    def sp(pid: str) -> tuple[float, float]:
        u, v = project(point(nodes[pid]), view)
        sx = width / 2 + (u - mid_u) * scale
        sy = height / 2 - (v - mid_v) * scale
        return sx, sy

    current_ids = {str(row["key_rod_id"]) for row in current_rows}
    previous_ids = {str(row["key_rod_id"]) for row in previous_rows}
    endpoint_ids = {
        str(row["node_a"])
        for row in current_rows
    } | {
        str(row["node_b"])
        for row in current_rows
    }

    lines = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#fbfaf7" rx="8"/>',
        f'<text x="14" y="22" font-size="14" font-weight="700" fill="#172033">{html.escape(title)}</text>',
    ]

    for row in all_rows:
        if row["key_rod_id"] not in current_ids and row["key_rod_id"] not in previous_ids:
            continue
        x1, y1 = sp(str(row["node_a"]))
        x2, y2 = sp(str(row["node_b"]))
        if row["key_rod_id"] in current_ids:
            color = "#f59e0b"
            stroke_width = 3.2
            opacity = 1.0
        else:
            color = "#64748b"
            stroke_width = 1.5
            opacity = 0.42
        dash = " stroke-dasharray=\"7 4\"" if row["rod_kind"] == "temporary_gauge" else ""
        lines.append(
            f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{color}" stroke-width="{stroke_width}" opacity="{opacity}" stroke-linecap="round"{dash}/>'
        )

    for pid in sorted(endpoint_ids):
        x, y = sp(pid)
        lines.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.2" fill="#111827"/>')
        lines.append(
            f'<text x="{x + 6:.2f}" y="{y - 6:.2f}" font-size="10" fill="#111827">{html.escape(pid)}</text>'
        )
    lines.append("</svg>")
    return "\n".join(lines)


def write_html(rows: list[dict[str, object]], nodes: dict[str, dict[str, str]]) -> None:
    by_step: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_step[int(row["step"])].append(row)

    step_notes = {
        1: "Build this flat on the table first. It defines the centerline and keeps front panels from drifting.",
        2: "Add lower width gauges square to the center spine. These stop the chin and rear bottom from pinching.",
        3: "Add temporary across-head gauges. Do not glue these permanently; they are spacers while taping panels.",
        4: "Add the ear anchors. These are the important ear reference edges; keep left and right symmetric.",
        5: "Add diagonal twist locks only if the shell feels floppy. Remove them after enough panels are taped.",
    }

    cards = []
    previous: list[dict[str, object]] = []
    for step in sorted(by_step):
        current = by_step[step]
        step_name = str(current[0]["step_name"])
        views = "\n".join(
            svg_view(
                f"{label} view",
                view,
                nodes,
                rows,
                current,
                previous,
            )
            for label, view in [("Front", "front"), ("Side", "side"), ("Top", "top")]
        )
        rod_rows = []
        for row in current:
            rod_rows.append(
                "<tr>"
                f"<td>{html.escape(str(row['key_rod_id']))}</td>"
                f"<td><code>{html.escape(str(row['node_a']))}-{html.escape(str(row['node_b']))}</code></td>"
                f"<td>{html.escape(str(row['gauge_length_mm']))} mm</td>"
                f"<td>{html.escape(str(row['cardboard_strip_cut_length_mm']))} mm</td>"
                f"<td>{html.escape(str(row['rod_kind']))}</td>"
                f"<td>{html.escape(str(row['install']))}</td>"
                "</tr>"
            )
        cards.append(
            f"""
      <section class="step">
        <h2>Step {step}: {html.escape(step_name)}</h2>
        <p>{html.escape(step_notes[step])}</p>
        <div class="views">{views}</div>
        <table>
          <thead>
            <tr><th>Rod</th><th>Nodes</th><th>Gauge length</th><th>Strip cut</th><th>Kind</th><th>Install note</th></tr>
          </thead>
          <tbody>{''.join(rod_rows)}</tbody>
        </table>
      </section>
"""
        )
        previous.extend(current)

    legend = """
      <div class="legend">
        <span><b class="solid"></b> surface edge / may remain</span>
        <span><b class="dash"></b> temporary gauge / remove later</span>
        <span><b class="current"></b> current step</span>
        <span><b class="previous"></b> previous rods</span>
      </div>
"""
    html_text = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Cat Head Cardboard Key Alignment Rods</title>
  <style>
    body {{ margin: 0; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f3f0ea; color: #172033; }}
    header {{ padding: 18px 22px; background: #fff; border-bottom: 1px solid #d6d3ca; }}
    h1 {{ margin: 0; font-size: 22px; }}
    .meta {{ margin-top: 6px; color: #64748b; font-size: 13px; line-height: 1.45; max-width: 980px; }}
    main {{ max-width: 1280px; margin: 0 auto; padding: 18px; }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 14px; padding: 12px 14px; background: #fff; border: 1px solid #d6d3ca; border-radius: 8px; margin-bottom: 16px; font-size: 13px; }}
    .legend span {{ display: inline-flex; align-items: center; gap: 6px; }}
    .legend b {{ display: inline-block; width: 34px; height: 0; border-top: 4px solid #334155; }}
    .legend .dash {{ border-top-style: dashed; }}
    .legend .current {{ border-color: #f59e0b; }}
    .legend .previous {{ border-color: #64748b; opacity: 0.5; }}
    .step {{ background: #fff; border: 1px solid #d6d3ca; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
    h2 {{ margin: 0 0 6px; font-size: 18px; }}
    p {{ margin: 0 0 12px; color: #475569; line-height: 1.45; }}
    .views {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 12px; }}
    svg {{ width: 100%; height: auto; border: 1px solid #e5e1d8; border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ padding: 7px 8px; border-bottom: 1px solid #e5e7eb; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }}
    @media (max-width: 900px) {{ .views {{ grid-template-columns: 1fr; }} }}
    @media print {{ body {{ background: #fff; }} main {{ max-width: none; padding: 0; }} .step {{ break-inside: avoid; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Cat Head Cardboard Key Alignment Rods</h1>
    <div class="meta">
      100% scale jig for the 220 mm tall cardboard test version. Rod lengths are node-to-node gauge lengths.
      For cardboard strips, cut the strip longer than the gauge length and mark the true node positions on the strip.
    </div>
  </header>
  <main>
    {legend}
    {''.join(cards)}
  </main>
</body>
</html>
"""
    (OUT_ASSEMBLY / "key-alignment-rod-assembly-guide.html").write_text(html_text, encoding="utf-8")


def main() -> None:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_ASSEMBLY.mkdir(parents=True, exist_ok=True)
    rows, nodes = build_rows()
    fields = [
        "key_rod_id",
        "step",
        "step_name",
        "rod_kind",
        "role",
        "node_a",
        "node_b",
        "wireframe_rod_id",
        "is_existing_wireframe_edge",
        "node_a_x_mm",
        "node_a_y_depth_mm",
        "node_a_z_up_mm",
        "node_b_x_mm",
        "node_b_y_depth_mm",
        "node_b_z_up_mm",
        "gauge_length_mm",
        "cardboard_strip_cut_length_mm",
        "keep",
        "criticality",
        "install",
        "fabrication_note",
    ]
    write_csv(OUT_DATA / "key_alignment_rods.csv", fields, rows)
    write_html(rows, nodes)
    print(f"Wrote {len(rows)} key rods to {OUT_DATA / 'key_alignment_rods.csv'}")
    print(f"Wrote visual guide to {OUT_ASSEMBLY / 'key-alignment-rod-assembly-guide.html'}")


if __name__ == "__main__":
    main()
