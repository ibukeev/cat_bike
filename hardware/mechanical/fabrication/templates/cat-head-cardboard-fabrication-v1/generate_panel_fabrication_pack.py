#!/usr/bin/env python3
"""Generate buildable cardboard panels from the approved V1 review model."""

from __future__ import annotations

import csv
import html
import math
from collections import defaultdict
from pathlib import Path


WORKDIR = Path(__file__).resolve().parent
SOURCE_DIR = WORKDIR.parent / "cat-head-wireframe-prototype" / "versions" / "v1-shape-approved-cardboard-prototype"
NODES_CSV = SOURCE_DIR / "data" / "gemini_3d_plus_symmetry_nodes.csv"
PANELS_CSV = SOURCE_DIR / "panel-candidates" / "candidate_panels.csv"
APPROVED_OBJ = SOURCE_DIR / "panel-candidates" / "candidate-panels-3d.obj"
EYE_CUTOUTS_CSV = SOURCE_DIR / "panel-candidates" / "eye_cutouts.csv"
SUPPRESSED_EYE_CSV = SOURCE_DIR / "panel-candidates" / "suppressed_eye_fill_panels.csv"
SUPPRESSED_REVIEW_CSV = SOURCE_DIR / "panel-candidates" / "suppressed_reviewer_removed_panels.csv"

OUT_DATA = WORKDIR / "data"
OUT_TEMPLATES = WORKDIR / "templates"
OUT_ASSEMBLY = WORKDIR / "assembly"

SHEET_W_MM = 279.4
SHEET_H_MM = 215.9
SHEET_MARGIN_MM = 10.0
GUTTER_MM = 8.0
PANEL_PAD_MM = 8.0

FIRST_BATCH_EXCLUDE_NODES = {
    # Ear tips / outer ear cap
    "P007",
    "P037",
    "P025",
    "P051",
    # Side/back/depth points
    "P021",
    "P050",
    "P031",
    "P057",
    "P060",
    "P072",
    "P063",
    "P070",
    "P062",
    "P071",
    "P064",
    "P067",
    "P065",
    "P068",
    "P066",
    "P069",
    # Bottom/lower rear points
    "P005",
    "P035",
    "P029",
    "P055",
    "P030",
    "P056",
    "P032",
    "P058",
}


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


def vsub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vdot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vcross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def vlen(a: tuple[float, float, float]) -> float:
    return math.sqrt(vdot(a, a))


def vnorm(a: tuple[float, float, float]) -> tuple[float, float, float]:
    length = vlen(a)
    if length < 1e-9:
        return (1.0, 0.0, 0.0)
    return (a[0] / length, a[1] / length, a[2] / length)


def dist(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return vlen(vsub(a, b))


def edge_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def panel_key(row: dict[str, str]) -> frozenset[str]:
    return frozenset(row["node_ids"].split())


def choose_panel(existing: dict[str, str], candidate: dict[str, str]) -> dict[str, str]:
    """Prefer manually reviewed panels, then lower planarity error."""
    if candidate["status"] == "manual_candidate_review" and existing["status"] != "manual_candidate_review":
        return candidate
    if candidate["status"] == existing["status"] and float(candidate["planarity_error_mm"]) < float(existing["planarity_error_mm"]):
        return candidate
    return existing


def dedupe_panels(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    by_nodes: dict[frozenset[str], dict[str, str]] = {}
    for row in rows:
        key = panel_key(row)
        by_nodes[key] = row if key not in by_nodes else choose_panel(by_nodes[key], row)
    return list(by_nodes.values())


def load_approved_obj() -> tuple[dict[str, tuple[float, float, float]], dict[str, tuple[str, ...]]]:
    """Read panel coordinates and panel membership from the approved OBJ."""
    vertices: list[tuple[float, float, float]] = []
    object_name = ""
    obj_nodes: dict[str, tuple[float, float, float]] = {}
    obj_panels: dict[str, tuple[str, ...]] = {}

    for raw_line in APPROVED_OBJ.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("o "):
            object_name = line[2:]
        elif line.startswith("v "):
            _, x, y, z = line.split()[:4]
            vertices.append((float(x), float(y), float(z)))
        elif line.startswith("f ") and object_name.startswith("panel_"):
            name_parts = object_name.split("_")
            panel_id = name_parts[1]
            node_ids = tuple(name_parts[2:])
            indices = [int(part.split("/")[0]) - 1 for part in line.split()[1:]]
            if len(indices) != len(node_ids):
                raise ValueError(f"{panel_id}: OBJ face/node count mismatch")
            obj_panels[panel_id] = node_ids
            for node_id, index in zip(node_ids, indices):
                coord = vertices[index]
                previous = obj_nodes.get(node_id)
                if previous is not None and dist(previous, coord) > 0.001:
                    raise ValueError(f"{node_id}: inconsistent coordinates inside approved OBJ")
                obj_nodes[node_id] = coord

    if not obj_panels:
        raise ValueError(f"No panel faces found in {APPROVED_OBJ}")
    return obj_nodes, obj_panels


def approved_nodes() -> dict[str, dict[str, str]]:
    """Use OBJ coordinates while retaining node metadata from the frozen CSV."""
    obj_nodes, _ = load_approved_obj()
    rows = {row["physical_node_id"]: row for row in read_csv(NODES_CSV)}
    for node_id, coord in obj_nodes.items():
        if node_id not in rows:
            raise ValueError(f"{node_id}: approved OBJ node missing from node CSV")
        csv_coord = point(rows[node_id])
        if dist(csv_coord, coord) > 0.001:
            raise ValueError(f"{node_id}: OBJ and node CSV coordinates disagree")
        rows[node_id] = {
            **rows[node_id],
            "x_mm": f"{coord[0]:.6f}",
            "y_mm_depth": f"{coord[1]:.6f}",
            "z_mm_up": f"{coord[2]:.6f}",
        }
    return rows


def select_coherent_panels(
    panels: list[dict[str, str]], obj_panels: dict[str, tuple[str, ...]]
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Select one connected surface while preventing third faces on an edge."""
    for row in panels:
        panel_id = row["panel_id"]
        if panel_id not in obj_panels:
            raise ValueError(f"{panel_id}: candidate CSV panel missing from approved OBJ")
        if frozenset(row["node_ids"].split()) != frozenset(obj_panels[panel_id]):
            raise ValueError(f"{panel_id}: OBJ and candidate CSV node membership disagree")

    triangles = [row for row in panels if len(row["node_ids"].split()) == 3]
    quads = [row for row in panels if len(row["node_ids"].split()) == 4]
    selected = list(triangles)
    edge_use: dict[tuple[str, str], int] = defaultdict(int)
    for row in triangles:
        ids = row["node_ids"].split()
        for a, b in zip(ids, ids[1:] + ids[:1]):
            edge_use[edge_key(a, b)] += 1

    # Manual additions encode prior review. Generated alternatives are accepted
    # flatter/larger first, unless they would create a third face on an edge.
    quads.sort(
        key=lambda row: (
            row["status"] != "manual_candidate_review",
            float(row["planarity_error_mm"]),
            -float(row["area_mm2"]),
            row["panel_id"],
        )
    )
    decisions: list[dict[str, str]] = []
    for row in quads:
        ids = row["node_ids"].split()
        edges = [edge_key(a, b) for a, b in zip(ids, ids[1:] + ids[:1])]
        blocked = [f"{a}-{b}" for a, b in edges if edge_use[edge_key(a, b)] >= 2]
        if blocked:
            decisions.append(
                {
                    "source_panel_id": row["panel_id"],
                    "decision": "excluded_conflicting_alternative",
                    "reason": "would create a third face on " + " ".join(blocked),
                }
            )
            continue
        selected.append(row)
        for edge in edges:
            edge_use[edge] += 1
        decisions.append(
            {
                "source_panel_id": row["panel_id"],
                "decision": "accepted_then_triangulated",
                "reason": "fits approved surface without overusing an edge",
            }
        )
    for row in triangles:
        decisions.append(
            {
                "source_panel_id": row["panel_id"],
                "decision": "accepted_triangle",
                "reason": "exact planar face from approved OBJ",
            }
        )
    decisions.sort(key=lambda row: row["source_panel_id"])
    return selected, decisions


def triangle_area(a: tuple[float, float, float], b: tuple[float, float, float], c: tuple[float, float, float]) -> float:
    return 0.5 * vlen(vcross(vsub(b, a), vsub(c, a)))


def triangle_row(
    source: dict[str, str], panel_id: str, node_ids: tuple[str, str, str], nodes: dict[str, dict[str, str]]
) -> dict[str, str]:
    pts = [point(nodes[node_id]) for node_id in node_ids]
    lengths = [dist(pts[i], pts[(i + 1) % 3]) for i in range(3)]
    center = tuple(sum(p[axis] for p in pts) / 3.0 for axis in range(3))
    return {
        **source,
        "panel_id": panel_id,
        "panel_type": "triangle",
        "status": "accepted_from_approved_obj",
        "node_ids": " ".join(node_ids),
        "edge_lengths_mm": " ".join(f"{length:.2f}" for length in lengths),
        "area_mm2": f"{triangle_area(*pts):.2f}",
        "perimeter_mm": f"{sum(lengths):.2f}",
        "min_edge_mm": f"{min(lengths):.2f}",
        "max_edge_mm": f"{max(lengths):.2f}",
        "planarity_error_mm": "0.0",
        "center_x_mm": f"{center[0]:.3f}",
        "center_y_depth_mm": f"{center[1]:.3f}",
        "center_z_up_mm": f"{center[2]:.3f}",
        "source_panel_id": source["panel_id"],
    }


def triangulate_panels(
    panels: list[dict[str, str]], nodes: dict[str, dict[str, str]]
) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for row in panels:
        ids = tuple(row["node_ids"].split())
        if len(ids) == 3:
            result.append(triangle_row(row, row["panel_id"], ids, nodes))
        elif len(ids) == 4:
            result.append(triangle_row(row, f"{row['panel_id']}-A", (ids[0], ids[1], ids[2]), nodes))
            result.append(triangle_row(row, f"{row['panel_id']}-B", (ids[0], ids[2], ids[3]), nodes))
        else:
            raise ValueError(f"{row['panel_id']}: unsupported face with {len(ids)} nodes")
    return result


def classify_zone(row: dict[str, str]) -> str:
    x = float(row["center_x_mm"])
    y = float(row["center_y_depth_mm"])
    z = float(row["center_z_up_mm"])
    nodes = set(row["node_ids"].split())
    if nodes & {"P007", "P037", "P025", "P051"}:
        return "ear_or_outer_top"
    if z < -70:
        return "bottom"
    if y > 75:
        return "back"
    if z > 45 and abs(x) <= 45:
        return "forehead"
    if abs(x) <= 18:
        return "center_face"
    if x > 0:
        return "right_cheek"
    return "left_cheek"


def first_batch_reason(row: dict[str, str]) -> str:
    nodes = set(row["node_ids"].split())
    if nodes & FIRST_BATCH_EXCLUDE_NODES:
        return ""
    x = float(row["center_x_mm"])
    y = float(row["center_y_depth_mm"])
    z = float(row["center_z_up_mm"])
    reasons = []
    if y <= 45.0 and z >= -60.0:
        reasons.append("front_depth")
    if abs(x) <= 25.0 and y <= 45.0 and z >= -40.0:
        reasons.append("centerline")
    if abs(x) <= 45.0 and z >= 45.0 and y <= 50.0:
        reasons.append("forehead")
    return " ".join(reasons)


def build_edge_index(panels: list[dict[str, str]]) -> tuple[dict[tuple[str, str], str], dict[tuple[str, str], list[dict[str, object]]]]:
    edge_ids: dict[tuple[str, str], str] = {}
    edge_refs: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in panels:
        node_ids = row["node_ids"].split()
        for idx, (a, b) in enumerate(zip(node_ids, node_ids[1:] + node_ids[:1]), start=1):
            key = edge_key(a, b)
            if key not in edge_ids:
                edge_ids[key] = f"E{len(edge_ids) + 1:03d}"
            edge_refs[key].append({"panel_id": row["panel_id"], "edge_index": idx, "node_a": a, "node_b": b})
    return edge_ids, edge_refs


def edge_length(nodes: dict[str, dict[str, str]], a: str, b: str) -> float:
    return dist(point(nodes[a]), point(nodes[b]))


def build_edge_rows(
    panels: list[dict[str, str]],
    nodes: dict[str, dict[str, str]],
    edge_ids: dict[tuple[str, str], str],
    edge_refs: dict[tuple[str, str], list[dict[str, object]]],
    first_batch_ids: set[str],
) -> list[dict[str, object]]:
    panel_by_id = {row["panel_id"]: row for row in panels}
    rows = []
    for panel in sorted(panels, key=lambda row: row["panel_id"]):
        node_ids = panel["node_ids"].split()
        for idx, (a, b) in enumerate(zip(node_ids, node_ids[1:] + node_ids[:1]), start=1):
            key = edge_key(a, b)
            refs = [
                ref
                for ref in edge_refs[key]
                if not (ref["panel_id"] == panel["panel_id"] and int(ref["edge_index"]) == idx)
            ]
            rows.append(
                {
                    "edge_id": edge_ids[key],
                    "panel_id": panel["panel_id"],
                    "panel_type": panel["panel_type"],
                    "zone": classify_zone(panel),
                    "first_batch": "yes" if panel["panel_id"] in first_batch_ids else "no",
                    "edge_index": idx,
                    "node_a": a,
                    "node_b": b,
                    "edge_length_mm": round(edge_length(nodes, a, b), 2),
                    "matching_panel_ids": " ".join(str(ref["panel_id"]) for ref in refs),
                    "matching_edge_indexes": " ".join(str(ref["edge_index"]) for ref in refs),
                    "matching_zones": " ".join(classify_zone(panel_by_id[str(ref["panel_id"])]) for ref in refs),
                    "match_count": len(refs),
                    "candidate_boundary": "yes" if not refs else "no",
                }
            )
    return rows


def flat_coords(node_ids: list[str], nodes: dict[str, dict[str, str]]) -> list[tuple[float, float]]:
    pts = [point(nodes[node_id]) for node_id in node_ids]
    p0, p1, p2 = pts[0], pts[1], pts[2]
    e1 = vnorm(vsub(p1, p0))
    normal = vnorm(vcross(vsub(p1, p0), vsub(p2, p0)))
    e2 = vnorm(vcross(normal, e1))
    coords = [(vdot(vsub(p, p0), e1), vdot(vsub(p, p0), e2)) for p in pts]
    min_x = min(x for x, _ in coords)
    min_y = min(y for _, y in coords)
    return [(x - min_x, y - min_y) for x, y in coords]


def rotate_if_needed(coords: list[tuple[float, float]]) -> tuple[list[tuple[float, float]], bool]:
    width = max(x for x, _ in coords) - min(x for x, _ in coords)
    height = max(y for _, y in coords) - min(y for _, y in coords)
    if width <= SHEET_W_MM - SHEET_MARGIN_MM * 2 and height <= SHEET_H_MM - SHEET_MARGIN_MM * 2:
        return coords, False
    rotated = [(y, -x) for x, y in coords]
    min_x = min(x for x, _ in rotated)
    min_y = min(y for _, y in rotated)
    return [(x - min_x, y - min_y) for x, y in rotated], True


def layout_panels(template_rows: list[dict[str, object]]) -> None:
    current_sheet = 1
    cursor_x = SHEET_MARGIN_MM
    cursor_y = SHEET_MARGIN_MM
    shelf_h = 0.0
    usable_w = SHEET_W_MM - SHEET_MARGIN_MM
    usable_h = SHEET_H_MM - SHEET_MARGIN_MM

    for row in template_rows:
        coords = row["flat_coords"]
        width = max(x for x, _ in coords) - min(x for x, _ in coords) + PANEL_PAD_MM * 2
        height = max(y for _, y in coords) - min(y for _, y in coords) + PANEL_PAD_MM * 2
        if cursor_x + width > usable_w:
            cursor_x = SHEET_MARGIN_MM
            cursor_y += shelf_h + GUTTER_MM
            shelf_h = 0.0
        if cursor_y + height > usable_h:
            current_sheet += 1
            cursor_x = SHEET_MARGIN_MM
            cursor_y = SHEET_MARGIN_MM
            shelf_h = 0.0
        row["sheet_id"] = f"S{current_sheet:02d}"
        row["sheet_index"] = current_sheet
        row["sheet_x_mm"] = round(cursor_x + PANEL_PAD_MM, 3)
        row["sheet_y_mm"] = round(cursor_y + PANEL_PAD_MM, 3)
        row["template_width_mm"] = round(width, 2)
        row["template_height_mm"] = round(height, 2)
        cursor_x += width + GUTTER_MM
        shelf_h = max(shelf_h, height)


def build_template_rows(
    panels: list[dict[str, str]],
    nodes: dict[str, dict[str, str]],
    edge_ids: dict[tuple[str, str], str],
) -> list[dict[str, object]]:
    selected = []
    for row in panels:
        node_ids = row["node_ids"].split()
        coords, rotated = rotate_if_needed(flat_coords(node_ids, nodes))
        edge_id_list = []
        edge_length_list = []
        for a, b in zip(node_ids, node_ids[1:] + node_ids[:1]):
            edge_id_list.append(edge_ids[edge_key(a, b)])
            edge_length_list.append(f"{edge_length(nodes, a, b):.2f}")
        selected.append(
            {
                **row,
                "zone": classify_zone(row),
                "selection_reason": "approved_obj_coherent_surface",
                "cut_recommendation": "single_piece_ok",
                "edge_ids": " ".join(edge_id_list),
                "computed_edge_lengths_mm": " ".join(edge_length_list),
                "flat_coords": coords,
                "rotated_on_sheet": "yes" if rotated else "no",
            }
        )
    selected.sort(
        key=lambda row: (
            {"center_face": 0, "right_cheek": 1, "left_cheek": 2, "forehead": 3}.get(str(row["zone"]), 9),
            float(row["center_z_up_mm"]),
            float(row["center_x_mm"]),
        )
    )
    layout_panels(selected)
    return selected


def svg_polygon(points: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.3f},{y:.3f}" for x, y in points)


def panel_color(zone: str) -> str:
    return {
        "center_face": "#fef3c7",
        "right_cheek": "#dbeafe",
        "left_cheek": "#e0f2fe",
        "forehead": "#dcfce7",
    }.get(zone, "#e5e7eb")


def edge_label_position(a: tuple[float, float], b: tuple[float, float]) -> tuple[float, float, float]:
    mx = (a[0] + b[0]) / 2.0
    my = (a[1] + b[1]) / 2.0
    angle = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    if angle > 90:
        angle -= 180
    if angle < -90:
        angle += 180
    return mx, my, angle


def render_panel_svg(row: dict[str, object], nodes: dict[str, dict[str, str]]) -> str:
    ox = float(row["sheet_x_mm"])
    oy = float(row["sheet_y_mm"])
    coords = [(ox + x, oy + y) for x, y in row["flat_coords"]]
    node_ids = str(row["node_ids"]).split()
    edge_ids = str(row["edge_ids"]).split()
    edge_lengths = str(row["computed_edge_lengths_mm"]).split()
    cx = sum(x for x, _ in coords) / len(coords)
    cy = sum(y for _, y in coords) / len(coords)
    zone = str(row["zone"])
    lines = [
        f'<polygon points="{svg_polygon(coords)}" fill="{panel_color(zone)}" stroke="#111827" stroke-width="0.35"/>',
        f'<text x="{cx:.3f}" y="{cy - 4:.3f}" font-size="4.2" text-anchor="middle" font-weight="700">{html.escape(str(row["panel_id"]))}</text>',
        f'<text x="{cx:.3f}" y="{cy + 1.5:.3f}" font-size="3.1" text-anchor="middle">{html.escape(zone)}</text>',
    ]
    if row["cut_recommendation"] != "single_piece_ok":
        lines.append(
            f'<text x="{cx:.3f}" y="{cy + 7:.3f}" font-size="2.8" text-anchor="middle" fill="#b91c1c">warp {float(row["planarity_error_mm"]):.1f}mm</text>'
        )
        if len(coords) == 4:
            lines.append(
                f'<line x1="{coords[0][0]:.3f}" y1="{coords[0][1]:.3f}" x2="{coords[2][0]:.3f}" y2="{coords[2][1]:.3f}" stroke="#b91c1c" stroke-width="0.25" stroke-dasharray="2 1"/>'
            )
    for idx, node_id in enumerate(node_ids):
        x, y = coords[idx]
        lines.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="1.15" fill="#111827"/>')
        lines.append(f'<text x="{x + 1.8:.3f}" y="{y - 1.8:.3f}" font-size="2.5">{html.escape(node_id)}</text>')
    for idx, (a, b) in enumerate(zip(coords, coords[1:] + coords[:1])):
        mx, my, angle = edge_label_position(a, b)
        label = f"{edge_ids[idx]} {edge_lengths[idx]}mm"
        lines.append(
            f'<text x="{mx:.3f}" y="{my:.3f}" font-size="2.7" text-anchor="middle" '
            f'transform="rotate({angle:.2f} {mx:.3f} {my:.3f})" fill="#1f2937">{html.escape(label)}</text>'
        )
    return "\n".join(lines)


def write_sheet_svgs(template_rows: list[dict[str, object]], nodes: dict[str, dict[str, str]]) -> None:
    by_sheet: dict[int, list[dict[str, object]]] = defaultdict(list)
    for row in template_rows:
        by_sheet[int(row["sheet_index"])].append(row)
    for sheet_idx, rows in sorted(by_sheet.items()):
        lines = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{SHEET_W_MM}mm" height="{SHEET_H_MM}mm" viewBox="0 0 {SHEET_W_MM} {SHEET_H_MM}">',
            '<rect x="0" y="0" width="100%" height="100%" fill="white"/>',
            f'<text x="10" y="7" font-size="4.5" font-weight="700">Cat head cardboard panels - sheet {sheet_idx:02d} - print at 100%</text>',
            '<rect x="10" y="10" width="259.4" height="195.9" fill="none" stroke="#d1d5db" stroke-width="0.3" stroke-dasharray="3 2"/>',
        ]
        for row in rows:
            lines.append(render_panel_svg(row, nodes))
        lines.append("</svg>")
        (OUT_TEMPLATES / f"cardboard-panels-sheet-{sheet_idx:02d}.svg").write_text("\n".join(lines), encoding="utf-8")


def write_overview_svg(template_rows: list[dict[str, object]], nodes: dict[str, dict[str, str]]) -> None:
    max_sheet = max(int(row["sheet_index"]) for row in template_rows)
    gap = 16.0
    width = SHEET_W_MM
    height = max_sheet * SHEET_H_MM + (max_sheet - 1) * gap
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}mm" height="{height}mm" viewBox="0 0 {width} {height}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="white"/>',
    ]
    for sheet_idx in range(1, max_sheet + 1):
        yoff = (sheet_idx - 1) * (SHEET_H_MM + gap)
        lines.append(f'<g transform="translate(0 {yoff:.3f})">')
        lines.append(f'<text x="10" y="7" font-size="4.5" font-weight="700">Sheet {sheet_idx:02d}</text>')
        lines.append(f'<rect x="0" y="0" width="{SHEET_W_MM}" height="{SHEET_H_MM}" fill="none" stroke="#9ca3af" stroke-width="0.35"/>')
        for row in template_rows:
            if int(row["sheet_index"]) != sheet_idx:
                continue
            lines.append(render_panel_svg(row, nodes))
        lines.append("</g>")
    lines.append("</svg>")
    (OUT_TEMPLATES / "cardboard-panels-overview.svg").write_text("\n".join(lines), encoding="utf-8")


def project_model(point_xyz: tuple[float, float, float], view: str) -> tuple[float, float]:
    x, y, z = point_xyz
    if view == "front":
        return x, z
    if view == "side":
        return y, z
    if view == "top":
        return x, y
    raise ValueError(view)


def view_svg(
    title: str,
    view: str,
    panels: list[dict[str, object]],
    nodes: dict[str, dict[str, str]],
    width: int = 520,
    height: int = 380,
) -> str:
    pts = [project_model(point(row), view) for row in nodes.values()]
    min_u = min(u for u, _ in pts)
    max_u = max(u for u, _ in pts)
    min_v = min(v for _, v in pts)
    max_v = max(v for _, v in pts)
    pad = 32
    scale = min((width - pad * 2) / max(max_u - min_u, 1.0), (height - pad * 2) / max(max_v - min_v, 1.0))
    mid_u = (min_u + max_u) / 2.0
    mid_v = (min_v + max_v) / 2.0

    def sp(pid: str) -> tuple[float, float]:
        u, v = project_model(point(nodes[pid]), view)
        return (width / 2 + (u - mid_u) * scale, height / 2 - (v - mid_v) * scale)

    lines = [
        f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{html.escape(title)}">',
        '<rect x="0" y="0" width="100%" height="100%" fill="#fbfaf7" rx="8"/>',
        f'<text x="14" y="22" font-size="14" font-weight="700" fill="#172033">{html.escape(title)}</text>',
    ]
    for row in panels:
        coords = [sp(pid) for pid in str(row["node_ids"]).split()]
        lines.append(
            f'<polygon points="{svg_polygon(coords)}" fill="{panel_color(str(row["zone"]))}" stroke="#111827" stroke-width="0.8" opacity="0.82"/>'
        )
    for row in panels:
        coords = [sp(pid) for pid in str(row["node_ids"]).split()]
        cx = sum(x for x, _ in coords) / len(coords)
        cy = sum(y for _, y in coords) / len(coords)
        lines.append(f'<text x="{cx:.2f}" y="{cy:.2f}" font-size="9" text-anchor="middle" fill="#111827">{html.escape(str(row["panel_id"]))}</text>')
    lines.append("</svg>")
    return "\n".join(lines)


def write_assembly_html(template_rows: list[dict[str, object]], nodes: dict[str, dict[str, str]]) -> None:
    zone_order = ["center_face", "right_cheek", "left_cheek", "forehead"]
    by_zone: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in template_rows:
        by_zone[str(row["zone"])].append(row)
    zone_cards = []
    for zone in zone_order:
        rows = sorted(by_zone.get(zone, []), key=lambda row: (float(row["center_z_up_mm"]), float(row["center_x_mm"])))
        if not rows:
            continue
        items = "".join(
            f"<tr><td>{html.escape(str(row['panel_id']))}</td><td><code>{html.escape(str(row['node_ids']))}</code></td>"
            f"<td>{html.escape(str(row['edge_ids']))}</td><td>{html.escape(str(row['cut_recommendation']))}</td></tr>"
            for row in rows
        )
        zone_cards.append(
            f"""
      <section class="zone">
        <h2>{html.escape(zone.replace('_', ' ').title())}</h2>
        <table>
          <thead><tr><th>Panel</th><th>Nodes</th><th>Edge IDs</th><th>Cut note</th></tr></thead>
          <tbody>{items}</tbody>
        </table>
      </section>
"""
        )
    views = "\n".join(
        view_svg(label, view, template_rows, nodes)
        for label, view in [("Front Projection", "front"), ("Side Projection", "side"), ("Top Projection", "top")]
    )
    sheet_links = []
    for sheet_idx in sorted({int(row["sheet_index"]) for row in template_rows}):
        sheet_links.append(f'<li><a href="../templates/cardboard-panels-sheet-{sheet_idx:02d}.svg">Sheet {sheet_idx:02d}</a></li>')

    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Cat Head Cardboard Prototype Guide</title>
  <style>
    body {{ margin: 0; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f3f0ea; color: #172033; }}
    header {{ padding: 18px 22px; background: #fff; border-bottom: 1px solid #d6d3ca; }}
    h1 {{ margin: 0; font-size: 22px; }}
    .meta {{ margin-top: 6px; color: #64748b; font-size: 13px; line-height: 1.45; max-width: 1000px; }}
    main {{ max-width: 1320px; margin: 0 auto; padding: 18px; }}
    .views {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }}
    svg {{ width: 100%; height: auto; border: 1px solid #e5e1d8; border-radius: 8px; }}
    .panel {{ background: #fff; border: 1px solid #d6d3ca; border-radius: 8px; padding: 14px; margin-bottom: 16px; }}
    .zone {{ background: #fff; border: 1px solid #d6d3ca; border-radius: 8px; padding: 14px; margin-bottom: 14px; }}
    h2 {{ margin: 0 0 8px; font-size: 17px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ padding: 7px 8px; border-bottom: 1px solid #e5e7eb; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }}
    a {{ color: #1d4ed8; }}
    @media (max-width: 900px) {{ .views {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Cat Head Cardboard Prototype Guide</h1>
    <div class="meta">
      Cut these panels first to test the edge labels and face curvature before cutting the full shell.
      Use masking tape and the key alignment rods from <code>key-alignment-rod-assembly-guide.html</code>.
    </div>
  </header>
  <main>
    <section class="panel">
      <h2>Printable Sheets</h2>
      <ul>{''.join(sheet_links)}</ul>
      <p>Print SVG sheets at 100% scale. The grey rectangle is the safe printable area reference for US Letter landscape.</p>
    </section>
    <section class="panel">
      <h2>Accepted Shell Projections</h2>
      <div class="views">{views}</div>
    </section>
    {''.join(zone_cards)}
  </main>
</body>
</html>
"""
    (OUT_ASSEMBLY / "cardboard-panel-assembly-guide.html").write_text(content, encoding="utf-8")


def write_sheet_guides(template_rows: list[dict[str, object]], nodes: dict[str, dict[str, str]]) -> None:
    guide_dir = OUT_ASSEMBLY / "sheet-guides"
    guide_dir.mkdir(parents=True, exist_ok=True)
    sheet_indexes = sorted({int(row["sheet_index"]) for row in template_rows})

    for sheet_idx in sheet_indexes:
        rows = [row for row in template_rows if int(row["sheet_index"]) == sheet_idx]
        rows.sort(key=lambda row: str(row["panel_id"]))
        views = "\n".join(
            view_svg(label, view, rows, nodes, width=640, height=460)
            for label, view in [
                ("Front Placement", "front"),
                ("Side Placement", "side"),
                ("Top Placement", "top"),
            ]
        )
        table_rows = "".join(
            "<tr>"
            f"<td><strong>{html.escape(str(row['panel_id']))}</strong></td>"
            f"<td>{html.escape(str(row['source_panel_id']))}</td>"
            f"<td><code>{html.escape(str(row['node_ids']))}</code></td>"
            f"<td><code>{html.escape(str(row['edge_ids']))}</code></td>"
            f"<td>{html.escape(str(row['computed_edge_lengths_mm']))}</td>"
            f"<td>{html.escape(str(row['zone']).replace('_', ' '))}</td>"
            "</tr>"
            for row in rows
        )
        previous_link = (
            f'<a href="sheet-{sheet_idx - 1:02d}-guide.html">Previous sheet</a>'
            if sheet_idx > sheet_indexes[0]
            else ""
        )
        next_link = (
            f'<a href="sheet-{sheet_idx + 1:02d}-guide.html">Next sheet</a>'
            if sheet_idx < sheet_indexes[-1]
            else ""
        )
        content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Cat Head Sheet {sheet_idx:02d} Guide</title>
  <style>
    body {{ margin: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #172033; background: #f3f0ea; }}
    header {{ padding: 16px 20px; background: white; border-bottom: 1px solid #d6d3ca; }}
    h1 {{ margin: 0; font-size: 24px; }}
    .meta {{ margin-top: 6px; font-size: 14px; color: #475569; }}
    main {{ max-width: 1500px; margin: 0 auto; padding: 16px; }}
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 14px; align-items: center; margin-bottom: 14px; }}
    a {{ color: #1d4ed8; }}
    .views {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }}
    .views svg {{ width: 100%; height: auto; background: white; border: 1px solid #d6d3ca; border-radius: 6px; }}
    .table-wrap {{ overflow-x: auto; background: white; border: 1px solid #d6d3ca; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ padding: 9px 10px; border-bottom: 1px solid #e5e7eb; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; }}
    code {{ white-space: nowrap; }}
    @media (max-width: 900px) {{ .views {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Sheet {sheet_idx:02d} Assembly Guide</h1>
    <div class="meta">{len(rows)} pieces. Match identical E-labels; node labels identify each 3D corner.</div>
  </header>
  <main>
    <nav class="toolbar">
      <a href="../../templates/cardboard-panels-sheet-{sheet_idx:02d}.svg">Open printable sheet</a>
      <a href="../cardboard-panel-assembly-guide.html">Overall guide</a>
      <a href="index.html">All sheet guides</a>
      {previous_link}
      {next_link}
    </nav>
    <section class="views">{views}</section>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Piece</th><th>Source face</th><th>Nodes</th><th>Edge IDs</th><th>Lengths (mm)</th><th>Zone</th></tr></thead>
        <tbody>{table_rows}</tbody>
      </table>
    </div>
  </main>
</body>
</html>
"""
        (guide_dir / f"sheet-{sheet_idx:02d}-guide.html").write_text(content, encoding="utf-8")

    links = "".join(
        f'<li><a href="sheet-{sheet_idx:02d}-guide.html">Sheet {sheet_idx:02d}</a></li>'
        for sheet_idx in sheet_indexes
    )
    index = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Cat Head Sheet Guides</title><style>
body {{ font-family: system-ui, sans-serif; margin: 0; padding: 24px; color: #172033; background: #f3f0ea; }}
main {{ max-width: 760px; margin: 0 auto; background: white; border: 1px solid #d6d3ca; padding: 20px; }}
h1 {{ margin-top: 0; }} ul {{ columns: 2; padding-left: 24px; }} li {{ margin: 8px 0; }} a {{ color: #1d4ed8; }}
</style></head><body><main><h1>Cat Head Sheet Guides</h1><p>Open the guide matching the sheet you are cutting or assembling.</p><ul>{links}</ul></main></body></html>"""
    (guide_dir / "index.html").write_text(index, encoding="utf-8")


def write_panel_csv(rows: list[dict[str, object]]) -> None:
    fields = [
        "panel_id",
        "source_panel_id",
        "panel_type",
        "zone",
        "selection_reason",
        "node_ids",
        "edge_ids",
        "computed_edge_lengths_mm",
        "area_mm2",
        "perimeter_mm",
        "planarity_error_mm",
        "max_constraint_risk",
        "cut_recommendation",
        "sheet_id",
        "sheet_x_mm",
        "sheet_y_mm",
        "template_width_mm",
        "template_height_mm",
        "rotated_on_sheet",
    ]
    clean = [{key: row[key] for key in fields} for row in rows]
    write_csv(OUT_DATA / "cardboard_panels.csv", fields, clean)


def validate_panels(
    panels: list[dict[str, str]],
    selected_sources: list[dict[str, str]],
    nodes: dict[str, dict[str, str]],
    edge_refs: dict[tuple[str, str], list[dict[str, object]]],
) -> dict[str, object]:
    overused = {edge: refs for edge, refs in edge_refs.items() if len(refs) > 2}
    if overused:
        details = ", ".join(f"{a}-{b} ({len(refs)})" for (a, b), refs in sorted(overused.items()))
        raise ValueError(f"Nonmanifold panel edges: {details}")

    adjacency: dict[str, set[str]] = {row["panel_id"]: set() for row in panels}
    for refs in edge_refs.values():
        ids = [str(ref["panel_id"]) for ref in refs]
        for panel_id in ids:
            adjacency[panel_id].update(other for other in ids if other != panel_id)
    seen: set[str] = set()
    components = 0
    for panel_id in adjacency:
        if panel_id in seen:
            continue
        components += 1
        stack = [panel_id]
        seen.add(panel_id)
        while stack:
            current = stack.pop()
            for neighbor in adjacency[current]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
    if components != 1:
        raise ValueError(f"Accepted surface has {components} disconnected components")

    max_flattening_error = 0.0
    for row in panels:
        ids = row["node_ids"].split()
        if len(ids) != 3:
            raise ValueError(f"{row['panel_id']}: final fabrication panel is not a triangle")
        coords = flat_coords(ids, nodes)
        for index, (a, b) in enumerate(zip(ids, ids[1:] + ids[:1])):
            p1 = coords[index]
            p2 = coords[(index + 1) % len(coords)]
            flat_length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            max_flattening_error = max(max_flattening_error, abs(flat_length - edge_length(nodes, a, b)))
    if max_flattening_error > 0.01:
        raise ValueError(f"Flattened edge error is {max_flattening_error:.4f} mm")

    selected_sets = {frozenset(row["node_ids"].split()) for row in selected_sources}
    suppressed_sets = {
        frozenset(row["node_ids"].split())
        for path in (SUPPRESSED_EYE_CSV, SUPPRESSED_REVIEW_CSV)
        for row in read_csv(path)
    }
    restored = selected_sets & suppressed_sets
    if restored:
        raise ValueError(f"Suppressed panel was restored: {sorted(map(sorted, restored))}")

    eye_edges = set()
    for cutout in read_csv(EYE_CUTOUTS_CSV):
        ids = cutout["node_ids"].split()
        eye_edges.update(edge_key(a, b) for a, b in zip(ids, ids[1:] + ids[:1]))
    bad_eye_edges = [edge for edge in eye_edges if len(edge_refs.get(edge, [])) != 1]
    if bad_eye_edges:
        raise ValueError(f"Eye opening boundary is not preserved: {bad_eye_edges}")

    return {
        "connected_components": components,
        "unique_edges": len(edge_refs),
        "boundary_edges": sum(len(refs) == 1 for refs in edge_refs.values()),
        "interior_edges": sum(len(refs) == 2 for refs in edge_refs.values()),
        "overused_edges": len(overused),
        "eye_boundary_edges": len(eye_edges),
        "max_flattening_error_mm": max_flattening_error,
    }


def write_accepted_obj(panels: list[dict[str, str]], nodes: dict[str, dict[str, str]]) -> None:
    used_nodes = sorted(
        {node_id for row in panels for node_id in row["node_ids"].split()},
        key=lambda node_id: int(node_id[1:]),
    )
    indices = {node_id: index for index, node_id in enumerate(used_nodes, start=1)}
    lines = [
        "# Buildable cardboard shell derived from the approved V1 candidate-panels-3d.obj",
        "# Coordinates are millimeters: X left/right, Y depth, Z up.",
        "o accepted_cardboard_shell",
    ]
    for node_id in used_nodes:
        x, y, z = point(nodes[node_id])
        lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
    for row in panels:
        ids = row["node_ids"].split()
        lines.append(f"g {row['panel_id']}")
        lines.append("f " + " ".join(str(indices[node_id]) for node_id in ids))
    (OUT_ASSEMBLY / "accepted-panels-3d.obj").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_validation_report(
    raw_count: int,
    deduped_count: int,
    selected_sources: list[dict[str, str]],
    panels: list[dict[str, str]],
    decisions: list[dict[str, str]],
    validation: dict[str, object],
) -> None:
    excluded = [row for row in decisions if row["decision"].startswith("excluded")]
    lines = [
        "# Cardboard Panel Validation",
        "",
        "Status: **PASS**",
        "",
        f"- Approved baseline: `{APPROVED_OBJ.relative_to(WORKDIR.parent.parent.parent.parent)}`",
        f"- Raw candidate faces: {raw_count}",
        f"- Deduplicated candidate faces: {deduped_count}",
        f"- Accepted source faces: {len(selected_sources)}",
        f"- Exact triangular cardboard pieces: {len(panels)}",
        f"- Excluded conflicting alternatives: {len(excluded)}",
        f"- Connected components: {validation['connected_components']}",
        f"- Boundary edges: {validation['boundary_edges']}",
        f"- Interior edges: {validation['interior_edges']}",
        f"- Overused edges: {validation['overused_edges']}",
        f"- Preserved eye-opening edges: {validation['eye_boundary_edges']}",
        f"- Maximum flattening error: {float(validation['max_flattening_error_mm']):.6f} mm",
        "",
        "## Excluded Alternatives",
        "",
    ]
    lines.extend(f"- `{row['source_panel_id']}`: {row['reason']}" for row in excluded)
    (OUT_DATA / "validation-report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DATA.mkdir(parents=True, exist_ok=True)
    OUT_TEMPLATES.mkdir(parents=True, exist_ok=True)
    OUT_ASSEMBLY.mkdir(parents=True, exist_ok=True)

    raw_panels = read_csv(PANELS_CSV)
    nodes = approved_nodes()
    _, obj_panels = load_approved_obj()
    candidates = dedupe_panels(raw_panels)
    selected_sources, decisions = select_coherent_panels(candidates, obj_panels)
    panels = triangulate_panels(selected_sources, nodes)
    panels.sort(key=lambda row: row["panel_id"])

    edge_ids, edge_refs = build_edge_index(panels)
    validation = validate_panels(panels, selected_sources, nodes, edge_refs)
    template_rows = build_template_rows(panels, nodes, edge_ids)
    included_ids = {str(row["panel_id"]) for row in template_rows}
    edge_rows = build_edge_rows(panels, nodes, edge_ids, edge_refs, included_ids)

    write_csv(
        OUT_DATA / "panel_edge_matching.csv",
        [
            "edge_id",
            "panel_id",
            "panel_type",
            "zone",
            "first_batch",
            "edge_index",
            "node_a",
            "node_b",
            "edge_length_mm",
            "matching_panel_ids",
            "matching_edge_indexes",
            "matching_zones",
            "match_count",
            "candidate_boundary",
        ],
        edge_rows,
    )
    write_csv(
        OUT_DATA / "panel-selection-decisions.csv",
        ["source_panel_id", "decision", "reason"],
        decisions,
    )
    write_panel_csv(template_rows)
    write_accepted_obj(panels, nodes)
    write_validation_report(len(raw_panels), len(candidates), selected_sources, panels, decisions, validation)
    write_sheet_svgs(template_rows, nodes)
    write_overview_svg(template_rows, nodes)
    write_assembly_html(template_rows, nodes)
    write_sheet_guides(template_rows, nodes)

    print(f"Approved OBJ candidates: {len(raw_panels)}")
    print(f"Accepted source faces: {len(selected_sources)}")
    print(f"Exact triangular cardboard pieces: {len(template_rows)}")
    print(f"Printable sheets: {max(int(row['sheet_index']) for row in template_rows)}")
    print(f"Topology: {validation['connected_components']} component, {validation['overused_edges']} overused edges")
    print(f"Maximum flattening error: {float(validation['max_flattening_error_mm']):.6f} mm")
    print(f"Wrote {OUT_DATA / 'validation-report.md'}")
    print(f"Wrote {OUT_DATA / 'cardboard_panels.csv'}")
    print(f"Wrote {OUT_TEMPLATES / 'cardboard-panels-overview.svg'}")
    print(f"Wrote {OUT_ASSEMBLY / 'accepted-panels-3d.obj'}")


if __name__ == "__main__":
    main()
