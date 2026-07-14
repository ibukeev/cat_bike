#!/usr/bin/env python3
"""Generate a proof 3D wireframe/rod model from confirmed Gemini mappings.

This is a proof artifact, not a fabrication model. It uses confirmed front,
side, and top projection correspondences to build a sparse 3D rod skeleton.
"""

from __future__ import annotations

import csv
import html
import json
import math
from collections import defaultdict
from pathlib import Path


WORKDIR = Path(__file__).resolve().parent
NODES_CSV = WORKDIR / "gemini_trace_nodes.csv"
EDGES_CSV = WORKDIR / "gemini_trace_edges.csv"
MAPPING_CSV = WORKDIR / "gemini_node_mapping.csv"

MODEL_HEIGHT_MM = 220.0
ROD_RADIUS_MM = 1.8
NODE_RADIUS_MM = 4.5
CYLINDER_SEGMENTS = 14
SPHERE_SEGMENTS = 12


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def linfit(xs: list[float], ys: list[float]) -> tuple[float, float]:
    if len(xs) < 2:
        return 1.0, 0.0
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    if abs(den) < 1e-9:
        return 1.0, 0.0
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den
    intercept = my - slope * mx
    return slope, intercept


def load_nodes() -> dict[tuple[str, str], dict[str, float]]:
    nodes: dict[tuple[str, str], dict[str, float]] = {}
    for row in read_csv(NODES_CSV):
        nodes[(row["view"], row["node_id"])] = {
            "x": float(row["x_px"]),
            "y": float(row["y_px"]),
        }
    return nodes


def active_mappings() -> list[dict[str, str]]:
    rows = []
    for row in read_csv(MAPPING_CSV):
        if row.get("status", "").strip().lower() != "confirmed":
            continue
        if not row.get("front_node") or not row.get("side_node"):
            continue
        rows.append(row)
    return rows


def build_projection_fits(nodes: dict[tuple[str, str], dict[str, float]], mappings: list[dict[str, str]]) -> dict[str, tuple[float, float]]:
    triples = []
    for row in mappings:
        top_node = row.get("top_node", "").strip()
        if not top_node:
            continue
        front = nodes.get(("Front", row["front_node"]))
        side = nodes.get(("Side", row["side_node"]))
        top = nodes.get(("Top", top_node))
        if front and side and top:
            triples.append((front, side, top))

    fits = {
        "top_x_to_front_x": (1.0, 0.0),
        "top_y_to_side_x": (-1.0, 3300.0),
        "side_y_to_front_y": (1.0, 0.0),
    }
    if len(triples) >= 2:
        fits["top_x_to_front_x"] = linfit([t["x"] for _, _, t in triples], [f["x"] for f, _, _ in triples])
        fits["top_y_to_side_x"] = linfit([t["y"] for _, _, t in triples], [s["x"] for _, s, t in triples])
        fits["side_y_to_front_y"] = linfit([s["y"] for _, s, _ in triples], [f["y"] for f, s, _ in triples])
    return fits


def transform_nodes(
    nodes: dict[tuple[str, str], dict[str, float]],
    mappings: list[dict[str, str]],
    fits: dict[str, tuple[float, float]],
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[tuple[str, str], str]]:
    pixel_rows: list[dict[str, object]] = []
    residual_rows: list[dict[str, object]] = []
    projection_to_physical: dict[tuple[str, str], str] = {}

    top_x_a, top_x_b = fits["top_x_to_front_x"]
    top_y_a, top_y_b = fits["top_y_to_side_x"]
    side_y_a, side_y_b = fits["side_y_to_front_y"]

    for row in mappings:
        pid = row["physical_node_id"]
        front = nodes[("Front", row["front_node"])]
        side = nodes[("Side", row["side_node"])]
        top = nodes.get(("Top", row.get("top_node", ""))) if row.get("top_node") else None

        projection_to_physical[("Front", row["front_node"])] = pid
        projection_to_physical[("Side", row["side_node"])] = pid
        if top:
            projection_to_physical[("Top", row["top_node"])] = pid

        front_x = front["x"]
        side_depth = side["x"]
        front_y = front["y"]
        side_y_as_front_y = side_y_a * side["y"] + side_y_b

        x_sources = [front_x]
        depth_sources = [side_depth]
        top_x_error = ""
        top_depth_error = ""
        if top:
            top_as_front_x = top_x_a * top["x"] + top_x_b
            top_as_side_depth = top_y_a * top["y"] + top_y_b
            top_x_error = top_as_front_x - front_x
            top_depth_error = top_as_side_depth - side_depth
            x_sources.append(top_as_front_x)
            depth_sources.append(top_as_side_depth)

        x_px = sum(x_sources) / len(x_sources)
        depth_px = sum(depth_sources) / len(depth_sources)
        z_y_px = (front_y + side_y_as_front_y) / 2.0
        z_error = side_y_as_front_y - front_y

        issues = []
        if top and abs(float(top_x_error)) > 12.0:
            issues.append("top_x_mismatch")
        if top and abs(float(top_depth_error)) > 40.0:
            issues.append("top_depth_mismatch")
        if abs(z_error) > 10.0:
            issues.append("front_side_height_mismatch")
        if not top:
            issues.append("no_top_constraint")

        pixel_rows.append(
            {
                "physical_node_id": pid,
                "front_node": row["front_node"],
                "side_node": row["side_node"],
                "top_node": row.get("top_node", ""),
                "x_px": x_px,
                "depth_px": depth_px,
                "z_y_px": z_y_px,
                "front_x_px": front_x,
                "side_depth_px": side_depth,
                "front_y_px": front_y,
                "side_y_as_front_y_px": side_y_as_front_y,
                "notes": row.get("notes", ""),
            }
        )
        residual_rows.append(
            {
                "physical_node_id": pid,
                "front_node": row["front_node"],
                "side_node": row["side_node"],
                "top_node": row.get("top_node", ""),
                "top_x_error_px": "" if top_x_error == "" else round(float(top_x_error), 3),
                "top_depth_error_px": "" if top_depth_error == "" else round(float(top_depth_error), 3),
                "front_side_height_error_px": round(z_error, 3),
                "issue": " ".join(issues),
            }
        )

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

    model_rows = []
    for row in pixel_rows:
        x = (float(row["x_px"]) - center_x) * scale
        y = (float(row["depth_px"]) - center_depth) * scale
        z = (center_z_y - float(row["z_y_px"])) * scale
        model_rows.append(
            {
                "physical_node_id": row["physical_node_id"],
                "front_node": row["front_node"],
                "side_node": row["side_node"],
                "top_node": row["top_node"],
                "x_mm": round(x, 3),
                "y_mm_depth": round(y, 3),
                "z_mm_up": round(z, 3),
                "x_px": round(float(row["x_px"]), 3),
                "depth_px": round(float(row["depth_px"]), 3),
                "z_y_px": round(float(row["z_y_px"]), 3),
                "notes": row["notes"],
            }
        )
    return model_rows, residual_rows, projection_to_physical


def build_rods(projection_to_physical: dict[tuple[str, str], str]) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    rods: dict[tuple[str, str], dict[str, object]] = {}
    skipped = []
    for row in read_csv(EDGES_CSV):
        view = row["view"]
        a = projection_to_physical.get((view, row["node_a"]))
        b = projection_to_physical.get((view, row["node_b"]))
        if not a or not b:
            if a or b:
                skipped.append(
                    {
                        "view": view,
                        "edge_id": row["edge_id"],
                        "node_a": row["node_a"],
                        "node_b": row["node_b"],
                        "mapped_a": a or "",
                        "mapped_b": b or "",
                        "reason": "one_endpoint_unmapped",
                    }
                )
            continue
        if a == b:
            continue
        key = tuple(sorted((a, b)))
        source = f"{view}:{row['edge_id']}"
        if key not in rods:
            rods[key] = {"rod_id": "", "node_a": key[0], "node_b": key[1], "source_views": view, "source_edges": source}
        else:
            rods[key]["source_edges"] = f"{rods[key]['source_edges']} {source}"
            rods[key]["source_views"] = " ".join(sorted(set(str(rods[key]["source_views"]).split() + [view])))

    rod_rows = list(rods.values())
    rod_rows.sort(key=lambda row: (row["node_a"], row["node_b"]))
    for idx, row in enumerate(rod_rows, start=1):
        row["rod_id"] = f"PR{idx:03d}"
    return rod_rows, skipped


def v_add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def v_sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def v_mul(a: tuple[float, float, float], s: float) -> tuple[float, float, float]:
    return (a[0] * s, a[1] * s, a[2] * s)


def v_dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def v_cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def v_len(a: tuple[float, float, float]) -> float:
    return math.sqrt(v_dot(a, a))


def v_norm(a: tuple[float, float, float]) -> tuple[float, float, float]:
    length = v_len(a)
    if length < 1e-9:
        return (0.0, 0.0, 1.0)
    return (a[0] / length, a[1] / length, a[2] / length)


class Mesh:
    def __init__(self) -> None:
        self.vertices: list[tuple[float, float, float]] = []
        self.faces: list[tuple[int, int, int]] = []

    def add_vertex(self, p: tuple[float, float, float]) -> int:
        self.vertices.append(p)
        return len(self.vertices)

    def add_face(self, a: int, b: int, c: int) -> None:
        self.faces.append((a, b, c))

    def add_cylinder(self, p1: tuple[float, float, float], p2: tuple[float, float, float], radius: float, segments: int) -> None:
        axis = v_sub(p2, p1)
        if v_len(axis) < 1e-6:
            return
        w = v_norm(axis)
        tmp = (0.0, 0.0, 1.0) if abs(w[2]) < 0.9 else (0.0, 1.0, 0.0)
        u = v_norm(v_cross(w, tmp))
        v = v_cross(w, u)
        a_ring = []
        b_ring = []
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            offset = v_add(v_mul(u, math.cos(angle) * radius), v_mul(v, math.sin(angle) * radius))
            a_ring.append(self.add_vertex(v_add(p1, offset)))
            b_ring.append(self.add_vertex(v_add(p2, offset)))
        center_a = self.add_vertex(p1)
        center_b = self.add_vertex(p2)
        for i in range(segments):
            j = (i + 1) % segments
            self.add_face(a_ring[i], b_ring[i], b_ring[j])
            self.add_face(a_ring[i], b_ring[j], a_ring[j])
            self.add_face(center_a, a_ring[j], a_ring[i])
            self.add_face(center_b, b_ring[i], b_ring[j])

    def add_sphere(self, center: tuple[float, float, float], radius: float, segments: int) -> None:
        rings: list[list[int]] = []
        for lat in range(segments + 1):
            phi = math.pi * lat / segments
            z = math.cos(phi) * radius
            ring_radius = math.sin(phi) * radius
            ring = []
            for lon in range(segments * 2):
                theta = 2.0 * math.pi * lon / (segments * 2)
                p = (
                    center[0] + math.cos(theta) * ring_radius,
                    center[1] + math.sin(theta) * ring_radius,
                    center[2] + z,
                )
                ring.append(self.add_vertex(p))
            rings.append(ring)
        cols = segments * 2
        for lat in range(segments):
            for lon in range(cols):
                nxt = (lon + 1) % cols
                a = rings[lat][lon]
                b = rings[lat + 1][lon]
                c = rings[lat + 1][nxt]
                d = rings[lat][nxt]
                if lat != 0:
                    self.add_face(a, b, d)
                if lat != segments - 1:
                    self.add_face(d, b, c)


def write_obj(path: Path, mesh: Mesh, node_rows: list[dict[str, object]], rod_rows: list[dict[str, object]]) -> None:
    points = {str(row["physical_node_id"]): (float(row["x_mm"]), float(row["y_mm_depth"]), float(row["z_mm_up"])) for row in node_rows}
    lines = ["# Gemini 3D proof wireframe mesh", "# scale: millimeters"]
    for v in mesh.vertices:
        lines.append(f"v {v[0]:.5f} {v[1]:.5f} {v[2]:.5f}")
    for face in mesh.faces:
        lines.append(f"f {face[0]} {face[1]} {face[2]}")
    lines.append("# logical rod centerlines")
    start = len(mesh.vertices)
    for pid in sorted(points):
        p = points[pid]
        lines.append(f"v {p[0]:.5f} {p[1]:.5f} {p[2]:.5f} # {pid}")
    point_index = {pid: start + idx for idx, pid in enumerate(sorted(points), start=1)}
    for rod in rod_rows:
        lines.append(f"l {point_index[str(rod['node_a'])]} {point_index[str(rod['node_b'])]} # {rod['rod_id']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def face_normal(a: tuple[float, float, float], b: tuple[float, float, float], c: tuple[float, float, float]) -> tuple[float, float, float]:
    return v_norm(v_cross(v_sub(b, a), v_sub(c, a)))


def write_stl(path: Path, mesh: Mesh) -> None:
    lines = ["solid gemini_3d_proof_wireframe"]
    for face in mesh.faces:
        a = mesh.vertices[face[0] - 1]
        b = mesh.vertices[face[1] - 1]
        c = mesh.vertices[face[2] - 1]
        n = face_normal(a, b, c)
        lines.append(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}")
        lines.append("    outer loop")
        lines.append(f"      vertex {a[0]:.6e} {a[1]:.6e} {a[2]:.6e}")
        lines.append(f"      vertex {b[0]:.6e} {b[1]:.6e} {b[2]:.6e}")
        lines.append(f"      vertex {c[0]:.6e} {c[1]:.6e} {c[2]:.6e}")
        lines.append("    endloop")
        lines.append("  endfacet")
    lines.append("endsolid gemini_3d_proof_wireframe")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(node_rows: list[dict[str, object]], rod_rows: list[dict[str, object]], residual_rows: list[dict[str, object]]) -> None:
    nodes_json = [
        {
            "id": row["physical_node_id"],
            "label": f"{row['physical_node_id']}\\nF:{row['front_node']} S:{row['side_node']} T:{row['top_node'] or '-'}",
            "x": float(row["x_mm"]),
            "y": float(row["y_mm_depth"]),
            "z": float(row["z_mm_up"]),
            "top": bool(row["top_node"]),
        }
        for row in node_rows
    ]
    rods_json = [
        {
            "id": row["rod_id"],
            "a": row["node_a"],
            "b": row["node_b"],
            "views": row["source_views"],
        }
        for row in rod_rows
    ]
    residual_by_id = {str(row["physical_node_id"]): row for row in residual_rows}
    warning_count = sum(1 for row in residual_rows if row["issue"])
    summary = f"{len(node_rows)} nodes, {len(rod_rows)} rods, {warning_count} nodes with warnings"
    warning_lines = []
    for row in residual_rows:
        if row["issue"]:
            warning_lines.append(
                f"<tr><td>{html.escape(str(row['physical_node_id']))}</td><td>{html.escape(str(row['issue']))}</td>"
                f"<td>{html.escape(str(row['top_x_error_px']))}</td><td>{html.escape(str(row['top_depth_error_px']))}</td>"
                f"<td>{html.escape(str(row['front_side_height_error_px']))}</td></tr>"
            )
    if not warning_lines:
        warning_lines.append('<tr><td colspan="5">No projection warnings.</td></tr>')

    (WORKDIR / "gemini-3d-proof-wireframe.html").write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Gemini 3D Proof Wireframe</title>
  <style>
    body {{ margin: 0; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f4f4f1; color: #172033; }}
    header {{ position: sticky; top: 0; z-index: 2; display: grid; grid-template-columns: 1fr auto; gap: 16px; align-items: center; padding: 12px 16px; border-bottom: 1px solid #d1d5db; background: rgba(244,244,241,.96); }}
    h1 {{ margin: 0; font-size: 16px; }}
    .meta {{ margin-top: 4px; color: #5b6472; font-size: 12px; }}
    button {{ border: 1px solid #aeb7c2; background: #fff; border-radius: 6px; padding: 7px 10px; cursor: pointer; }}
    main {{ display: grid; grid-template-columns: minmax(0, 1fr) 390px; min-height: calc(100vh - 62px); }}
    canvas {{ display: block; width: 100%; height: calc(100vh - 62px); background: #ffffff; }}
    aside {{ border-left: 1px solid #d1d5db; padding: 14px; overflow: auto; max-height: calc(100vh - 90px); }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ border-bottom: 1px solid #e2e8f0; padding: 6px 4px; text-align: left; vertical-align: top; }}
    th {{ font-weight: 650; color: #334155; }}
    .hint {{ margin: 0 0 12px; font-size: 12px; color: #5b6472; }}
    @media (max-width: 900px) {{ main {{ grid-template-columns: 1fr; }} aside {{ border-left: 0; border-top: 1px solid #d1d5db; max-height: none; }} canvas {{ height: 70vh; }} }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Gemini 3D Proof Wireframe</h1>
      <div class="meta">{html.escape(summary)}. Drag to rotate, wheel to zoom. Scale is arbitrary proof scale in mm.</div>
    </div>
    <button id="reset">Reset View</button>
  </header>
  <main>
    <canvas id="canvas"></canvas>
    <aside>
      <p class="hint">Gold nodes have top-view constraints. Gray nodes are only front+side. Warnings show where the traced projections disagree.</p>
      <table>
        <thead><tr><th>Node</th><th>Issue</th><th>Top X px</th><th>Top depth px</th><th>Z px</th></tr></thead>
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
    let rotX = -0.45;
    let rotZ = -0.62;
    let zoom = 4.0;
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
        const views = r.views;
        ctx.strokeStyle = views.includes("Top") ? "#7c3aed" : views.includes("Side") ? "#2563eb" : "#e11d48";
        ctx.globalAlpha = 0.78;
        ctx.lineWidth = 3.2 * devicePixelRatio;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }}
      const sortedNodes = nodes.slice().sort((a, b) => project(a).z - project(b).z);
      for (const n of sortedNodes) {{
        const p = projected.get(n.id);
        ctx.globalAlpha = 1;
        ctx.fillStyle = n.top ? "#f59e0b" : "#94a3b8";
        ctx.strokeStyle = "#111827";
        ctx.lineWidth = 1.5 * devicePixelRatio;
        ctx.beginPath();
        ctx.arc(p.x, p.y, (n.top ? 5.5 : 4.5) * devicePixelRatio, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        ctx.fillStyle = "#111827";
        ctx.font = `${{11 * devicePixelRatio}}px monospace`;
        ctx.fillText(n.id, p.x + 7 * devicePixelRatio, p.y - 7 * devicePixelRatio);
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
    document.getElementById("reset").addEventListener("click", () => {{ rotX = -0.45; rotZ = -0.62; zoom = 4.0; draw(); }});
    addEventListener("resize", resize);
    resize();
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )


def write_report(
    node_rows: list[dict[str, object]],
    rod_rows: list[dict[str, object]],
    residual_rows: list[dict[str, object]],
    skipped_rows: list[dict[str, object]],
    fits: dict[str, tuple[float, float]],
) -> None:
    top_count = sum(1 for row in node_rows if row["top_node"])
    warnings = [row for row in residual_rows if row["issue"]]
    top_errors = [abs(float(row["top_x_error_px"])) for row in residual_rows if row["top_x_error_px"] != ""]
    depth_errors = [abs(float(row["top_depth_error_px"])) for row in residual_rows if row["top_depth_error_px"] != ""]
    z_errors = [abs(float(row["front_side_height_error_px"])) for row in residual_rows]
    lines = [
        "# Gemini 3D Proof Model Report",
        "",
        "This is a proof model generated from confirmed node correspondences. It is not fabrication-ready CAD.",
        "",
        "## Counts",
        "",
        f"- 3D nodes: {len(node_rows)}",
        f"- Nodes with top-view constraint: {top_count}",
        f"- Rods generated from mapped projection edges: {len(rod_rows)}",
        f"- Skipped partially mapped projection edges: {len(skipped_rows)}",
        f"- Nodes with projection warnings: {len(warnings)}",
        "",
        "## Fit Summary",
        "",
        f"- top_x_to_front_x: x = {fits['top_x_to_front_x'][0]:.6f} * top_x + {fits['top_x_to_front_x'][1]:.3f}",
        f"- top_y_to_side_depth: y = {fits['top_y_to_side_x'][0]:.6f} * top_y + {fits['top_y_to_side_x'][1]:.3f}",
        f"- side_y_to_front_y: z_y = {fits['side_y_to_front_y'][0]:.6f} * side_y + {fits['side_y_to_front_y'][1]:.3f}",
        f"- mean abs top-x residual: {sum(top_errors) / len(top_errors):.2f}px" if top_errors else "- mean abs top-x residual: n/a",
        f"- mean abs top-depth residual: {sum(depth_errors) / len(depth_errors):.2f}px" if depth_errors else "- mean abs top-depth residual: n/a",
        f"- mean abs front/side height residual: {sum(z_errors) / len(z_errors):.2f}px" if z_errors else "- mean abs front/side height residual: n/a",
        "",
        "## Files",
        "",
        "- `gemini-3d-proof-wireframe.html`",
        "- `gemini-3d-proof-wireframe.obj`",
        "- `gemini-3d-proof-wireframe.stl`",
        "- `gemini_3d_proof_nodes.csv`",
        "- `gemini_3d_proof_rods.csv`",
        "- `gemini_3d_projection_residuals.csv`",
        "- `gemini_3d_skipped_edges.csv`",
    ]
    (WORKDIR / "gemini_3d_proof_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    nodes = load_nodes()
    mappings = active_mappings()
    fits = build_projection_fits(nodes, mappings)
    node_rows, residual_rows, projection_to_physical = transform_nodes(nodes, mappings, fits)
    rod_rows, skipped_rows = build_rods(projection_to_physical)

    write_csv(
        WORKDIR / "gemini_3d_proof_nodes.csv",
        ["physical_node_id", "front_node", "side_node", "top_node", "x_mm", "y_mm_depth", "z_mm_up", "x_px", "depth_px", "z_y_px", "notes"],
        node_rows,
    )
    write_csv(
        WORKDIR / "gemini_3d_projection_residuals.csv",
        ["physical_node_id", "front_node", "side_node", "top_node", "top_x_error_px", "top_depth_error_px", "front_side_height_error_px", "issue"],
        residual_rows,
    )
    write_csv(WORKDIR / "gemini_3d_proof_rods.csv", ["rod_id", "node_a", "node_b", "source_views", "source_edges"], rod_rows)
    write_csv(WORKDIR / "gemini_3d_skipped_edges.csv", ["view", "edge_id", "node_a", "node_b", "mapped_a", "mapped_b", "reason"], skipped_rows)

    points = {str(row["physical_node_id"]): (float(row["x_mm"]), float(row["y_mm_depth"]), float(row["z_mm_up"])) for row in node_rows}
    mesh = Mesh()
    for rod in rod_rows:
        mesh.add_cylinder(points[str(rod["node_a"])], points[str(rod["node_b"])], ROD_RADIUS_MM, CYLINDER_SEGMENTS)
    for point in points.values():
        mesh.add_sphere(point, NODE_RADIUS_MM, SPHERE_SEGMENTS)

    write_obj(WORKDIR / "gemini-3d-proof-wireframe.obj", mesh, node_rows, rod_rows)
    write_stl(WORKDIR / "gemini-3d-proof-wireframe.stl", mesh)
    write_html(node_rows, rod_rows, residual_rows)
    write_report(node_rows, rod_rows, residual_rows, skipped_rows, fits)


if __name__ == "__main__":
    main()
