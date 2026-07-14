#!/usr/bin/env python3
"""Generate candidate cardboard panel faces from the V1 cat-head rod graph."""

from __future__ import annotations

import csv
import html
import json
import math
from collections import defaultdict
from itertools import combinations
from pathlib import Path


WORKDIR = Path(__file__).resolve().parent
V1_DIR = WORKDIR / "versions" / "v1-shape-approved-cardboard-prototype"
DATA_DIR = V1_DIR / "data"
OUT_DIR = V1_DIR / "panel-candidates"

NODES_CSV = DATA_DIR / "gemini_3d_plus_symmetry_nodes.csv"
RODS_CSV = DATA_DIR / "gemini_3d_plus_symmetry_rods.csv"

MANUAL_PANEL_CANDIDATES = [
    {
        "panel_id": "MANQ001",
        "panel_type": "quad",
        "node_ids": ("P033", "P001", "P002", "P034"),
        "status": "manual_candidate_review",
        "notes": "reviewer requested center symmetry quad; perimeter uses virtual P002-P034 edge because the rod graph splits that lower edge through P059",
    },
    {
        "panel_id": "MANQ002",
        "panel_type": "quad",
        "node_ids": ("P024", "P010", "P053", "P054"),
        "status": "manual_candidate_review",
        "notes": "reviewer requested missing left/top-side quad from coordinate feedback",
    },
    {
        "panel_id": "MANQ003",
        "panel_type": "quad",
        "node_ids": ("P024", "P010", "P027", "P028"),
        "status": "manual_candidate_review",
        "notes": "symmetric counterpart of MANQ002 using existing right-side nodes",
    },
    {
        "panel_id": "MANT001",
        "panel_type": "triangle",
        "node_ids": ("P061", "P053", "P052"),
        "status": "manual_candidate_review",
        "notes": "reviewer requested missing left-side triangle from coordinate feedback",
    },
    {
        "panel_id": "MANT002",
        "panel_type": "triangle",
        "node_ids": ("P073", "P027", "P026"),
        "status": "manual_candidate_review",
        "notes": "symmetric counterpart of MANT001; P073 is the new mirror of P061/S015",
    },
    {
        "panel_id": "MANQ004",
        "panel_type": "quad",
        "node_ids": ("P061", "P053", "P054", "P064"),
        "status": "manual_candidate_review",
        "notes": "reviewer requested missing left-side quad from coordinate feedback",
    },
    {
        "panel_id": "MANQ005",
        "panel_type": "quad",
        "node_ids": ("P073", "P027", "P028", "P067"),
        "status": "manual_candidate_review",
        "notes": "symmetric counterpart of MANQ004; P073 is the new mirror of P061/S015",
    },
    {
        "panel_id": "MANT003",
        "panel_type": "triangle",
        "node_ids": ("P069", "P071", "P067"),
        "status": "manual_candidate_review",
        "notes": "reviewer requested missing right/back-side triangle from coordinate feedback",
    },
    {
        "panel_id": "MANT004",
        "panel_type": "triangle",
        "node_ids": ("P067", "P071", "P073"),
        "status": "manual_candidate_review",
        "notes": "reviewer requested missing triangle after projecting P073 onto P071-P026 edge",
    },
    {
        "panel_id": "MANQ006",
        "panel_type": "quad",
        "node_ids": ("P070", "P063", "P060", "P072"),
        "status": "manual_candidate_review",
        "notes": "reviewer requested rear/bottom symmetry quad from coordinate feedback",
    },
    {
        "panel_id": "MANQ007",
        "panel_type": "quad",
        "node_ids": ("P072", "P060", "P057", "P031"),
        "status": "manual_candidate_review",
        "notes": "reviewer requested bottom panel upper band from coordinate feedback",
    },
    {
        "panel_id": "MANQ008",
        "panel_type": "quad",
        "node_ids": ("P057", "P031", "P005", "P035"),
        "status": "manual_candidate_review",
        "notes": "reviewer requested bottom panel lower band; P005 forced to mirror P035",
    },
]

EYE_CUTOUTS = [
    {
        "cutout_id": "EYE_RIGHT",
        "node_ids": ("P015", "P017", "P016", "P019"),
        "internal_nodes": ("P018",),
        "notes": "right/front traced 4-edge eye opening; no cardboard panel should fill this loop",
    },
    {
        "cutout_id": "EYE_LEFT",
        "node_ids": ("P044", "P046", "P045", "P048"),
        "internal_nodes": ("P047",),
        "notes": "mirrored 4-edge eye opening; no cardboard panel should fill this loop",
    },
]

REVIEWER_REMOVED_PANEL_NODE_SETS = {
    frozenset(("P054", "P066", "P064")),
    frozenset(("P028", "P069", "P067")),
    frozenset(("P064", "P066", "P061")),
    frozenset(("P067", "P069", "P073")),
    frozenset(("P069", "P071", "P067")),
    frozenset(("P053", "P052", "P051", "P037")),
    frozenset(("P027", "P026", "P025", "P007")),
    frozenset(("P026", "P027", "P007")),
    frozenset(("P052", "P053", "P037")),
    frozenset(("P007", "P027", "P026", "P069")),
    frozenset(("P037", "P053", "P052", "P066")),
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def vsub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vcross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def vdot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def vlen(a: tuple[float, float, float]) -> float:
    return math.sqrt(vdot(a, a))


def vnorm(a: tuple[float, float, float]) -> tuple[float, float, float]:
    length = vlen(a)
    if length < 1e-9:
        return (0.0, 0.0, 0.0)
    return (a[0] / length, a[1] / length, a[2] / length)


def dist(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return vlen(vsub(a, b))


def triangle_area(points: list[tuple[float, float, float]]) -> float:
    return 0.5 * vlen(vcross(vsub(points[1], points[0]), vsub(points[2], points[0])))


def polygon_area(points: list[tuple[float, float, float]]) -> float:
    if len(points) == 3:
        return triangle_area(points)
    return triangle_area([points[0], points[1], points[2]]) + triangle_area([points[0], points[2], points[3]])


def plane_error(points: list[tuple[float, float, float]]) -> float:
    if len(points) < 4:
        return 0.0
    normal = vnorm(vcross(vsub(points[1], points[0]), vsub(points[2], points[0])))
    return abs(vdot(vsub(points[3], points[0]), normal))


def face_normal(points: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    return vnorm(vcross(vsub(points[1], points[0]), vsub(points[2], points[0])))


def canonical_cycle(cycle: tuple[str, ...]) -> tuple[str, ...]:
    rotations = []
    n = len(cycle)
    for seq in (cycle, tuple(reversed(cycle))):
        for i in range(n):
            rotations.append(seq[i:] + seq[:i])
    return min(rotations)


def edge_key(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def load_graph() -> tuple[dict[str, dict[str, object]], list[dict[str, str]], dict[str, set[str]], dict[tuple[str, str], dict[str, str]]]:
    nodes = {}
    for row in read_csv(NODES_CSV):
        pid = row["physical_node_id"]
        nodes[pid] = {
            **row,
            "point": (float(row["x_mm"]), float(row["y_mm_depth"]), float(row["z_mm_up"])),
            "risk": int(row["constraint_risk"]),
        }

    rods = read_csv(RODS_CSV)
    graph: dict[str, set[str]] = defaultdict(set)
    rod_by_edge = {}
    for row in rods:
        a = row["node_a"]
        b = row["node_b"]
        graph[a].add(b)
        graph[b].add(a)
        rod_by_edge[edge_key(a, b)] = row
    return nodes, rods, graph, rod_by_edge


def find_triangles(graph: dict[str, set[str]]) -> set[tuple[str, str, str]]:
    triangles = set()
    for a in sorted(graph):
        for b, c in combinations(sorted(graph[a]), 2):
            if c in graph[b]:
                triangles.add(canonical_cycle((a, b, c)))
    return triangles


def find_chordless_quads(graph: dict[str, set[str]]) -> set[tuple[str, str, str, str]]:
    quads = set()
    for a in sorted(graph):
        for b in graph[a]:
            for c in graph[b]:
                if c == a:
                    continue
                for d in graph[c]:
                    if d in {a, b}:
                        continue
                    if a not in graph[d]:
                        continue
                    if c in graph[a] or d in graph[b]:
                        continue
                    quads.add(canonical_cycle((a, b, c, d)))
    return quads


def panel_row(
    panel_id: str,
    panel_type: str,
    node_ids: tuple[str, ...],
    nodes: dict[str, dict[str, object]],
    rod_by_edge: dict[tuple[str, str], dict[str, str]],
    status: str = "candidate_review",
    notes: str = "",
) -> dict[str, object]:
    points = [nodes[node_id]["point"] for node_id in node_ids]
    edges = [edge_key(node_ids[i], node_ids[(i + 1) % len(node_ids)]) for i in range(len(node_ids))]
    edge_lengths = [dist(points[i], points[(i + 1) % len(points)]) for i in range(len(points))]
    center = tuple(sum(point[i] for point in points) / len(points) for i in range(3))
    normal = face_normal(points)
    risks = [int(nodes[node_id]["risk"]) for node_id in node_ids]
    source_edges = [
        rod_by_edge[edge]["rod_id"] if edge in rod_by_edge else f"virtual:{edge[0]}-{edge[1]}"
        for edge in edges
    ]
    area = polygon_area(points)
    perimeter = sum(edge_lengths)
    return {
        "panel_id": panel_id,
        "panel_type": panel_type,
        "status": status,
        "node_ids": " ".join(node_ids),
        "rod_ids": " ".join(source_edges),
        "edge_lengths_mm": " ".join(f"{length:.2f}" for length in edge_lengths),
        "area_mm2": round(area, 2),
        "perimeter_mm": round(perimeter, 2),
        "min_edge_mm": round(min(edge_lengths), 2),
        "max_edge_mm": round(max(edge_lengths), 2),
        "planarity_error_mm": round(plane_error(points), 3),
        "max_constraint_risk": max(risks),
        "center_x_mm": round(center[0], 3),
        "center_y_depth_mm": round(center[1], 3),
        "center_z_up_mm": round(center[2], 3),
        "normal_x": round(normal[0], 5),
        "normal_y": round(normal[1], 5),
        "normal_z": round(normal[2], 5),
        "notes": notes,
    }




def suppresses_reviewer_removed_panel(row: dict[str, object]) -> bool:
    return frozenset(str(row["node_ids"]).split()) in REVIEWER_REMOVED_PANEL_NODE_SETS


def suppresses_eye_cutout(row: dict[str, object]) -> bool:
    """Return true for generated panels that would fill a protected eye opening."""
    if str(row.get("status", "")) == "manual_candidate_review":
        return False
    node_ids = set(str(row["node_ids"]).split())
    for cutout in EYE_CUTOUTS:
        boundary = set(cutout["node_ids"])
        allowed = boundary | set(cutout.get("internal_nodes", ()))
        if node_ids <= allowed and len(node_ids) >= 3:
            return True
    return False


def write_eye_cutouts_csv(nodes: dict[str, dict[str, object]]) -> None:
    rows = []
    for cutout in EYE_CUTOUTS:
        node_ids = tuple(cutout["node_ids"])
        points = [nodes[node_id]["point"] for node_id in node_ids]
        edge_lengths = [dist(points[i], points[(i + 1) % len(points)]) for i in range(len(points))]
        rows.append(
            {
                "cutout_id": cutout["cutout_id"],
                "node_ids": " ".join(node_ids),
                "edge_lengths_mm": " ".join(f"{length:.2f}" for length in edge_lengths),
                "planarity_error_mm": round(plane_error(points), 3),
                "notes": cutout["notes"],
            }
        )
    write_csv(
        OUT_DIR / "eye_cutouts.csv",
        ["cutout_id", "node_ids", "edge_lengths_mm", "planarity_error_mm", "notes"],
        rows,
    )


def eye_insert_panel_rows(nodes: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for cutout in EYE_CUTOUTS:
        node_ids = tuple(cutout["node_ids"])
        points = [nodes[node_id]["point"] for node_id in node_ids]
        edge_lengths = [dist(points[i], points[(i + 1) % len(points)]) for i in range(len(points))]
        center = tuple(sum(point[i] for point in points) / len(points) for i in range(3))
        rows.append(
            {
                "insert_id": f"INSERT_{cutout['cutout_id']}",
                "insert_type": "translucent_eye_quad",
                "node_ids": " ".join(node_ids),
                "edge_lengths_mm": " ".join(f"{length:.2f}" for length in edge_lengths),
                "area_mm2": round(polygon_area(points), 2),
                "perimeter_mm": round(sum(edge_lengths), 2),
                "planarity_error_mm": round(plane_error(points), 3),
                "center_x_mm": round(center[0], 3),
                "center_y_depth_mm": round(center[1], 3),
                "center_z_up_mm": round(center[2], 3),
                "notes": f"translucent insert panel for {cutout['cutout_id']}; shares boundary with eye cutout",
            }
        )
    return rows


def write_eye_insert_panels_csv(nodes: dict[str, dict[str, object]]) -> None:
    write_csv(
        OUT_DIR / "eye_insert_panels.csv",
        [
            "insert_id",
            "insert_type",
            "node_ids",
            "edge_lengths_mm",
            "area_mm2",
            "perimeter_mm",
            "planarity_error_mm",
            "center_x_mm",
            "center_y_depth_mm",
            "center_z_up_mm",
            "notes",
        ],
        eye_insert_panel_rows(nodes),
    )

def build_candidates(
    nodes: dict[str, dict[str, object]],
    graph: dict[str, set[str]],
    rod_by_edge: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, object]]:
    rows = []
    suppressed_eye_fillers = []
    for idx, cycle in enumerate(sorted(find_triangles(graph)), start=1):
        row = panel_row(f"TRI{idx:03d}", "triangle", cycle, nodes, rod_by_edge)
        if suppresses_eye_cutout(row):
            suppressed_eye_fillers.append(row)
        else:
            rows.append(row)
    for idx, cycle in enumerate(sorted(find_chordless_quads(graph)), start=1):
        row = panel_row(f"QUAD{idx:03d}", "quad", cycle, nodes, rod_by_edge)
        if suppresses_eye_cutout(row):
            suppressed_eye_fillers.append(row)
        else:
            rows.append(row)
    for spec in MANUAL_PANEL_CANDIDATES:
        if any(node_id not in nodes for node_id in spec["node_ids"]):
            continue
        rows.append(
            panel_row(
                spec["panel_id"],
                spec["panel_type"],
                spec["node_ids"],
                nodes,
                rod_by_edge,
                status=spec["status"],
                notes=spec["notes"],
            )
        )
    reviewer_removed_panels = [row for row in rows if suppresses_reviewer_removed_panel(row)]
    rows = [row for row in rows if not suppresses_reviewer_removed_panel(row)]
    rows.sort(key=lambda row: (row["panel_type"], -float(row["area_mm2"]), row["panel_id"]))
    write_csv(
        OUT_DIR / "suppressed_reviewer_removed_panels.csv",
        [
            "panel_id",
            "panel_type",
            "status",
            "node_ids",
            "rod_ids",
            "edge_lengths_mm",
            "area_mm2",
            "perimeter_mm",
            "min_edge_mm",
            "max_edge_mm",
            "planarity_error_mm",
            "max_constraint_risk",
            "center_x_mm",
            "center_y_depth_mm",
            "center_z_up_mm",
            "normal_x",
            "normal_y",
            "normal_z",
            "notes",
        ],
        reviewer_removed_panels,
    )
    write_csv(
        OUT_DIR / "suppressed_eye_fill_panels.csv",
        [
            "panel_id",
            "panel_type",
            "status",
            "node_ids",
            "rod_ids",
            "edge_lengths_mm",
            "area_mm2",
            "perimeter_mm",
            "min_edge_mm",
            "max_edge_mm",
            "planarity_error_mm",
            "max_constraint_risk",
            "center_x_mm",
            "center_y_depth_mm",
            "center_z_up_mm",
            "normal_x",
            "normal_y",
            "normal_z",
            "notes",
        ],
        suppressed_eye_fillers,
    )
    return rows


def write_summary(panel_rows: list[dict[str, object]]) -> None:
    triangle_count = sum(1 for row in panel_rows if row["panel_type"] == "triangle")
    quad_count = sum(1 for row in panel_rows if row["panel_type"] == "quad")
    high_risk = sum(1 for row in panel_rows if int(row["max_constraint_risk"]) >= 4)
    manual_count = sum(1 for row in panel_rows if row["status"] == "manual_candidate_review")
    lines = [
        "# V1 Candidate Cardboard Panels",
        "",
        "Generated from the frozen V1 node/rod graph.",
        "",
        "## Counts",
        "",
        f"- Candidate cardboard panels: {len(panel_rows)}",
        f"- Triangles: {triangle_count}",
        f"- Chordless quads/manual quads: {quad_count}",
        f"- Protected eye cutouts: {len(EYE_CUTOUTS)}",
        f"- Translucent eye insert panels: {len(EYE_CUTOUTS)}",
        f"- Reviewer-removed panel node sets: {len(REVIEWER_REMOVED_PANEL_NODE_SETS)}",
        f"- Panels touching heavy-estimate nodes: {high_risk}",
        f"- Manual reviewer-added panels: {manual_count}",
        "",
        "## Review Files",
        "",
        "- `candidate_panels.csv`: candidate cardboard panel list with node IDs, rod IDs, edge lengths, area, risk, and planarity.",
        "- `eye_cutouts.csv`: protected 4-edge eye openings that should not be filled by ordinary cardboard panels.",
        "- `eye_insert_panels.csv`: translucent insert panels that fill those eye openings as separate material pieces.",
        "- `suppressed_eye_fill_panels.csv`: auto-generated candidates suppressed because they would fill the eye openings.",
        "- `suppressed_reviewer_removed_panels.csv`: candidate panels explicitly removed by reviewer feedback.",
        "- `candidate-panel-review.html`: interactive 3D visual review UI for accepting/rejecting candidate panels.",
        "- `candidate-panel-review-multiview.html`: front/side/top/iso panel review UI.",
        "- `candidate-panels-3d.obj`: main cardboard/skin review mesh with eye openings preserved and cutout boundary loops shown.",
        "- `eye-insert-panels.obj`: separate translucent insert faces for the eye openings; import alongside the main OBJ when needed.",
        "- `candidate-panels-combined.obj`: combined all-pieces review mesh with skin panels and translucent eye insert panels as separate objects/materials.",
        "",
        "## Review Guidance",
        "",
        "Use the multiview HTML or OBJ to inspect panels in 3D, not a single projection.",
        "Start by accepting large visible front/cheek/forehead facets and rejecting internal-looking or confusing crossings.",
        "The accepted panel list should be smaller than this candidate set.",
        "The eye cutout loops are intentionally not cardboard panels in the main OBJ; they are filled by separate translucent eye insert panels.",
    ]
    (OUT_DIR / "candidate_panels_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def color_for_risk(risk: int, panel_type: str) -> str:
    if risk >= 4:
        return "#ef4444"
    if risk == 3:
        return "#f59e0b"
    if risk == 2:
        return "#64748b"
    return "#2563eb" if panel_type == "triangle" else "#7c3aed"


def hex_to_rgb01(hex_color: str) -> tuple[float, float, float]:
    color = hex_color.lstrip("#")
    return (
        int(color[0:2], 16) / 255.0,
        int(color[2:4], 16) / 255.0,
        int(color[4:6], 16) / 255.0,
    )


def safe_obj_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in name)


def panel_json_rows(panel_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for row in panel_rows:
        rows.append(
            {
                "id": row["panel_id"],
                "type": row["panel_type"],
                "nodes": str(row["node_ids"]).split(),
                "area": row["area_mm2"],
                "risk": int(row["max_constraint_risk"]),
                "planarity": row["planarity_error_mm"],
                "color": color_for_risk(int(row["max_constraint_risk"]), str(row["panel_type"])),
                "edgeLengths": row["edge_lengths_mm"],
            }
        )
    return rows


def write_panel_obj(nodes: dict[str, dict[str, object]], rods: list[dict[str, str]], panel_rows: list[dict[str, object]]) -> None:
    # Write candidate panels as separate OBJ objects for CAD/viewer review.
    obj_path = OUT_DIR / "candidate-panels-3d.obj"
    mtl_path = OUT_DIR / "candidate-panels-3d.mtl"

    material_rows = [
        ("rod_context", "#334155", 1.0),
        ("panel_risk_0", "#16a34a", 0.45),
        ("panel_risk_1", "#2563eb", 0.45),
        ("panel_risk_2", "#64748b", 0.45),
        ("panel_risk_3", "#f59e0b", 0.50),
        ("panel_risk_4", "#ef4444", 0.55),
        ("eye_translucent_insert", "#7dd3fc", 0.62),
        ("eye_cutout_edge", "#00d5ff", 1.0),
    ]
    mtl_lines = []
    for name, color, alpha in material_rows:
        r, g, b = hex_to_rgb01(color)
        mtl_lines.extend(
            [
                f"newmtl {name}",
                f"Kd {r:.6f} {g:.6f} {b:.6f}",
                "Ka 0.050000 0.050000 0.050000",
                "Ks 0.120000 0.120000 0.120000",
                f"d {alpha:.3f}",
                f"Tr {1.0 - alpha:.3f}",
                "illum 2",
                "",
            ]
        )
    mtl_path.write_text("\n".join(mtl_lines), encoding="utf-8")

    obj_lines = [
        "# V1 candidate cardboard panel review mesh",
        "# Coordinates are millimeters: X left/right, Y depth, Z up.",
        f"mtllib {mtl_path.name}",
        "",
    ]

    vertex_index = 1
    context_indices = {}
    obj_lines.extend(["o rod_context_lines", "usemtl rod_context"])
    for node_id, node in sorted(nodes.items()):
        x, y, z = node["point"]
        context_indices[node_id] = vertex_index
        obj_lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
        vertex_index += 1
    for rod in rods:
        obj_lines.append(f"l {context_indices[rod['node_a']]} {context_indices[rod['node_b']]}")
    obj_lines.append("")

    for row in panel_rows:
        node_ids = str(row["node_ids"]).split()
        risk = min(4, max(0, int(row["max_constraint_risk"])))
        name = safe_obj_name(f"panel_{row['panel_id']}_{'_'.join(node_ids)}")
        obj_lines.extend([f"o {name}", f"usemtl panel_risk_{risk}"])

        face_indices = []
        for node_id in node_ids:
            x, y, z = nodes[node_id]["point"]
            face_indices.append(vertex_index)
            obj_lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
            vertex_index += 1

        if len(face_indices) == 3:
            obj_lines.append("f " + " ".join(str(idx) for idx in face_indices))
        elif len(face_indices) == 4:
            obj_lines.append("f " + " ".join(str(idx) for idx in face_indices))
        obj_lines.append("")

    for cutout in EYE_CUTOUTS:
        node_ids = tuple(cutout["node_ids"])
        obj_lines.extend([
            f"o cutout_{safe_obj_name(cutout['cutout_id'])}_{'_'.join(node_ids)}",
            "usemtl eye_cutout_edge",
            "# Boundary loop for the translucent eye insert panel.",
        ])
        cutout_indices = []
        for node_id in node_ids:
            x, y, z = nodes[node_id]["point"]
            cutout_indices.append(vertex_index)
            obj_lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
            vertex_index += 1
        for i, idx in enumerate(cutout_indices):
            obj_lines.append(f"l {idx} {cutout_indices[(i + 1) % len(cutout_indices)]}")
        obj_lines.append("")

    obj_path.write_text("\n".join(obj_lines), encoding="utf-8")


def write_eye_insert_obj(nodes: dict[str, dict[str, object]]) -> None:
    obj_path = OUT_DIR / "eye-insert-panels.obj"
    mtl_path = OUT_DIR / "eye-insert-panels.mtl"
    material_rows = [
        ("eye_translucent_insert", "#7dd3fc", 0.62),
        ("eye_insert_edge", "#00d5ff", 1.0),
    ]
    mtl_lines = []
    for name, color, alpha in material_rows:
        r, g, b = hex_to_rgb01(color)
        mtl_lines.extend(
            [
                f"newmtl {name}",
                f"Kd {r:.6f} {g:.6f} {b:.6f}",
                "Ka 0.050000 0.050000 0.050000",
                "Ks 0.120000 0.120000 0.120000",
                f"d {alpha:.3f}",
                f"Tr {1.0 - alpha:.3f}",
                "illum 2",
                "",
            ]
        )
    mtl_path.write_text("\n".join(mtl_lines), encoding="utf-8")

    obj_lines = [
        "# V1 translucent eye insert panels",
        "# Coordinates are millimeters: X left/right, Y depth, Z up.",
        "# Import this with candidate-panels-3d.obj when you want the filled eye pieces.",
        f"mtllib {mtl_path.name}",
        "",
    ]
    vertex_index = 1
    for row in eye_insert_panel_rows(nodes):
        node_ids = str(row["node_ids"]).split()
        obj_lines.extend([
            f"o insert_{safe_obj_name(str(row['insert_id']))}_{'_'.join(node_ids)}",
            "usemtl eye_translucent_insert",
        ])
        face_indices = []
        for node_id in node_ids:
            x, y, z = nodes[node_id]["point"]
            face_indices.append(vertex_index)
            obj_lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
            vertex_index += 1
        obj_lines.append("f " + " ".join(str(idx) for idx in face_indices))
        obj_lines.append("usemtl eye_insert_edge")
        for i, idx in enumerate(face_indices):
            obj_lines.append(f"l {idx} {face_indices[(i + 1) % len(face_indices)]}")
        obj_lines.append("")
    obj_path.write_text("\n".join(obj_lines), encoding="utf-8")




def write_combined_panel_obj(nodes: dict[str, dict[str, object]], rods: list[dict[str, str]], panel_rows: list[dict[str, object]]) -> None:
    # Combined review mesh: cardboard/skin panels plus separate translucent eye insert faces.
    obj_path = OUT_DIR / "candidate-panels-combined.obj"
    mtl_path = OUT_DIR / "candidate-panels-combined.mtl"

    material_rows = [
        ("rod_context", "#334155", 1.0),
        ("panel_risk_0", "#16a34a", 0.45),
        ("panel_risk_1", "#2563eb", 0.45),
        ("panel_risk_2", "#64748b", 0.45),
        ("panel_risk_3", "#f59e0b", 0.50),
        ("panel_risk_4", "#ef4444", 0.55),
        ("eye_translucent_insert", "#7dd3fc", 0.62),
        ("eye_cutout_edge", "#00d5ff", 1.0),
    ]
    mtl_lines = []
    for name, color, alpha in material_rows:
        r, g, b = hex_to_rgb01(color)
        mtl_lines.extend(
            [
                f"newmtl {name}",
                f"Kd {r:.6f} {g:.6f} {b:.6f}",
                "Ka 0.050000 0.050000 0.050000",
                "Ks 0.120000 0.120000 0.120000",
                f"d {alpha:.3f}",
                f"Tr {1.0 - alpha:.3f}",
                "illum 2",
                "",
            ]
        )
    mtl_path.write_text("\n".join(mtl_lines), encoding="utf-8")

    obj_lines = [
        "# V1 combined panel review mesh",
        "# Contains cardboard/skin panels, translucent eye insert faces, and cutout boundary loops.",
        "# Coordinates are millimeters: X left/right, Y depth, Z up.",
        f"mtllib {mtl_path.name}",
        "",
    ]

    vertex_index = 1
    context_indices = {}
    obj_lines.extend(["o rod_context_lines", "usemtl rod_context"])
    for node_id, node in sorted(nodes.items()):
        x, y, z = node["point"]
        context_indices[node_id] = vertex_index
        obj_lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
        vertex_index += 1
    for rod in rods:
        obj_lines.append(f"l {context_indices[rod['node_a']]} {context_indices[rod['node_b']]}")
    obj_lines.append("")

    for row in panel_rows:
        node_ids = str(row["node_ids"]).split()
        risk = min(4, max(0, int(row["max_constraint_risk"])))
        name = safe_obj_name(f"panel_{row['panel_id']}_{'_'.join(node_ids)}")
        obj_lines.extend([f"o {name}", f"usemtl panel_risk_{risk}"])

        face_indices = []
        for node_id in node_ids:
            x, y, z = nodes[node_id]["point"]
            face_indices.append(vertex_index)
            obj_lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
            vertex_index += 1
        obj_lines.append("f " + " ".join(str(idx) for idx in face_indices))
        obj_lines.append("")

    for row in eye_insert_panel_rows(nodes):
        node_ids = str(row["node_ids"]).split()
        obj_lines.extend([
            f"o insert_{safe_obj_name(str(row['insert_id']))}_{'_'.join(node_ids)}",
            "usemtl eye_translucent_insert",
        ])
        face_indices = []
        for node_id in node_ids:
            x, y, z = nodes[node_id]["point"]
            face_indices.append(vertex_index)
            obj_lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
            vertex_index += 1
        obj_lines.append("f " + " ".join(str(idx) for idx in face_indices))
        obj_lines.append("")

    for cutout in EYE_CUTOUTS:
        node_ids = tuple(cutout["node_ids"])
        obj_lines.extend([
            f"o cutout_{safe_obj_name(cutout['cutout_id'])}_{'_'.join(node_ids)}",
            "usemtl eye_cutout_edge",
            "# Boundary loop for the translucent eye insert panel.",
        ])
        cutout_indices = []
        for node_id in node_ids:
            x, y, z = nodes[node_id]["point"]
            cutout_indices.append(vertex_index)
            obj_lines.append(f"v {x:.6f} {y:.6f} {z:.6f}")
            vertex_index += 1
        for i, idx in enumerate(cutout_indices):
            obj_lines.append(f"l {idx} {cutout_indices[(i + 1) % len(cutout_indices)]}")
        obj_lines.append("")

    obj_path.write_text("\n".join(obj_lines), encoding="utf-8")


def write_multiview_html(nodes: dict[str, dict[str, object]], rods: list[dict[str, str]], panel_rows: list[dict[str, object]]) -> None:
    node_json = [
        {
            "id": node_id,
            "x": node["point"][0],
            "y": node["point"][1],
            "z": node["point"][2],
            "risk": node["risk"],
        }
        for node_id, node in sorted(nodes.items())
    ]
    rod_json = [{"a": row["node_a"], "b": row["node_b"], "id": row["rod_id"]} for row in rods]
    panel_json = panel_json_rows(panel_rows)
    rows_html = []
    for idx, row in enumerate(panel_rows):
        rows_html.append(
            f"<tr data-index='{idx}'><td>{html.escape(str(row['panel_id']))}</td>"
            f"<td>{html.escape(str(row['panel_type']))}</td>"
            f"<td>{html.escape(str(row['node_ids']))}</td>"
            f"<td>{html.escape(str(row['max_constraint_risk']))}</td>"
            f"<td>{html.escape(str(row['planarity_error_mm']))}</td></tr>"
        )

    (OUT_DIR / "candidate-panel-review-multiview.html").write_text(
        f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>V1 Candidate Panel Multiview Review</title>
  <style>
    body {{ margin: 0; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f5f2; color: #172033; }}
    header {{ padding: 12px 16px; background: #fff; border-bottom: 1px solid #d1d5db; }}
    h1 {{ margin: 0; font-size: 16px; }}
    .meta {{ margin-top: 4px; color: #64748b; font-size: 12px; }}
    main {{ display: grid; grid-template-columns: minmax(0, 1fr) 480px; min-height: calc(100vh - 58px); }}
    .views {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1px; background: #cbd5e1; }}
    .view {{ position: relative; min-height: 320px; background: #fff; }}
    .view h2 {{ position: absolute; left: 10px; top: 8px; margin: 0; font-size: 12px; color: #475569; z-index: 1; }}
    canvas {{ display: block; width: 100%; height: 100%; }}
    aside {{ background: #fafafa; border-left: 1px solid #d1d5db; overflow: auto; max-height: calc(100vh - 58px); }}
    .details, .controls {{ padding: 10px; border-bottom: 1px solid #e5e7eb; font-size: 12px; line-height: 1.45; }}
    button, select {{ border: 1px solid #aeb7c2; background: #fff; border-radius: 6px; padding: 6px 8px; cursor: pointer; }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }}
    label {{ display: inline-flex; gap: 5px; align-items: center; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
    th, td {{ padding: 5px 4px; border-bottom: 1px solid #e5e7eb; text-align: left; white-space: nowrap; }}
    tr {{ cursor: pointer; }}
    tr.selected {{ background: #dbeafe; }}
    code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; }}
    @media (max-width: 1100px) {{
      main {{ grid-template-columns: 1fr; }}
      aside {{ max-height: none; }}
      .view {{ min-height: 250px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>V1 Candidate Panel Multiview Review</h1>
    <div class="meta">Click a row to highlight the same candidate in front, side, top, and isometric views.</div>
  </header>
  <main>
    <section class="views">
      <div class="view"><h2>Front: X / Z</h2><canvas data-view="front"></canvas></div>
      <div class="view"><h2>Side: depth / Z</h2><canvas data-view="side"></canvas></div>
      <div class="view"><h2>Top: X / depth</h2><canvas data-view="top"></canvas></div>
      <div class="view"><h2>Iso</h2><canvas data-view="iso"></canvas></div>
    </section>
    <aside>
      <div class="controls">
        <button id="prev">Prev</button>
        <button id="next">Next</button>
        <label><input id="showAll" type="checkbox" checked /> all candidates</label>
        <label><input id="showRods" type="checkbox" checked /> rods</label>
        <select id="risk">
          <option value="4">all risks</option>
          <option value="3">risk <= 3</option>
          <option value="2">risk <= 2</option>
          <option value="1">risk <= 1</option>
        </select>
      </div>
      <div class="details" id="details"></div>
      <table>
        <thead><tr><th>ID</th><th>Type</th><th>Nodes</th><th>Risk</th><th>Planar</th></tr></thead>
        <tbody id="rows">{"".join(rows_html)}</tbody>
      </table>
    </aside>
  </main>
  <script>
    const nodes = {json.dumps(node_json)};
    const rods = {json.dumps(rod_json)};
    const panels = {json.dumps(panel_json)};
    const byId = new Map(nodes.map(n => [n.id, n]));
    const canvases = [...document.querySelectorAll("canvas[data-view]")];
    const details = document.getElementById("details");
    const rowsEl = document.getElementById("rows");
    let selected = 0;

    function projectPoint(node, view) {{
      if (view === "front") return {{u: node.x, v: node.z, d: node.y}};
      if (view === "side") return {{u: node.y, v: node.z, d: node.x}};
      if (view === "top") return {{u: node.x, v: node.y, d: node.z}};
      const rz = -0.72, rx = -0.48;
      const cz = Math.cos(rz), sz = Math.sin(rz), cx = Math.cos(rx), sx = Math.sin(rx);
      const x = node.x * cz - node.y * sz;
      const y = node.x * sz + node.y * cz;
      const z = node.z;
      return {{u: x, v: y * cx - z * sx, d: y * sx + z * cx}};
    }}

    function boundsFor(view) {{
      const pts = nodes.map(n => projectPoint(n, view));
      return {{
        minU: Math.min(...pts.map(p => p.u)),
        maxU: Math.max(...pts.map(p => p.u)),
        minV: Math.min(...pts.map(p => p.v)),
        maxV: Math.max(...pts.map(p => p.v)),
      }};
    }}

    function screenProject(node, view, w, h) {{
      const b = boundsFor(view);
      const p = projectPoint(node, view);
      const pad = 38 * devicePixelRatio;
      const sx = (w - pad * 2) / Math.max(1, b.maxU - b.minU);
      const sy = (h - pad * 2) / Math.max(1, b.maxV - b.minV);
      const s = Math.min(sx, sy);
      return {{
        x: w / 2 + (p.u - (b.minU + b.maxU) / 2) * s,
        y: h / 2 - (p.v - (b.minV + b.maxV) / 2) * s,
        d: p.d,
      }};
    }}

    function filteredPanels() {{
      const maxRisk = Number(document.getElementById("risk").value);
      return panels.map((p, i) => [p, i]).filter(([p]) => p.risk <= maxRisk);
    }}

    function resizeCanvases() {{
      for (const canvas of canvases) {{
        const rect = canvas.getBoundingClientRect();
        canvas.width = Math.max(1, Math.floor(rect.width * devicePixelRatio));
        canvas.height = Math.max(1, Math.floor(rect.height * devicePixelRatio));
      }}
      draw();
    }}

    function drawPanel(ctx, canvas, view, panel, strong) {{
      const pts = panel.nodes.map(id => screenProject(byId.get(id), view, canvas.width, canvas.height));
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for (const p of pts.slice(1)) ctx.lineTo(p.x, p.y);
      ctx.closePath();
      ctx.globalAlpha = strong ? 0.62 : 0.12;
      ctx.fillStyle = panel.color;
      ctx.fill();
      ctx.globalAlpha = strong ? 1 : 0.28;
      ctx.strokeStyle = strong ? "#111827" : panel.color;
      ctx.lineWidth = (strong ? 3 : 1) * devicePixelRatio;
      ctx.stroke();
    }}

    function drawRods(ctx, canvas, view) {{
      ctx.globalAlpha = 0.28;
      ctx.strokeStyle = "#334155";
      ctx.lineWidth = 1 * devicePixelRatio;
      for (const rod of rods) {{
        const a = screenProject(byId.get(rod.a), view, canvas.width, canvas.height);
        const b = screenProject(byId.get(rod.b), view, canvas.width, canvas.height);
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }}
    }}

    function drawNodes(ctx, canvas, view, panel) {{
      for (const id of panel.nodes) {{
        const p = screenProject(byId.get(id), view, canvas.width, canvas.height);
        ctx.globalAlpha = 1;
        ctx.fillStyle = "#111827";
        ctx.beginPath();
        ctx.arc(p.x, p.y, 4.5 * devicePixelRatio, 0, Math.PI * 2);
        ctx.fill();
        ctx.font = `${{11 * devicePixelRatio}}px ui-monospace, SFMono-Regular, Menlo, monospace`;
        ctx.fillText(id, p.x + 7 * devicePixelRatio, p.y - 7 * devicePixelRatio);
      }}
    }}

    function draw() {{
      const selectedPanel = panels[selected] || panels[0];
      for (const canvas of canvases) {{
        const view = canvas.dataset.view;
        const ctx = canvas.getContext("2d");
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (document.getElementById("showAll").checked) {{
          for (const [panel] of filteredPanels()) {{
            if (panel.id !== selectedPanel.id) drawPanel(ctx, canvas, view, panel, false);
          }}
        }}
        drawPanel(ctx, canvas, view, selectedPanel, true);
        if (document.getElementById("showRods").checked) drawRods(ctx, canvas, view);
        drawNodes(ctx, canvas, view, selectedPanel);
      }}
      details.innerHTML = `<strong>${{selectedPanel.id}}</strong> ${{selectedPanel.type}}<br>` +
        `Nodes: <code>${{selectedPanel.nodes.join(" ")}}</code><br>` +
        `Area: ${{selectedPanel.area}} mm2; risk: ${{selectedPanel.risk}}; planarity: ${{selectedPanel.planarity}} mm<br>` +
        `Edges: <code>${{selectedPanel.edgeLengths}}</code>`;
      for (const tr of rowsEl.querySelectorAll("tr")) tr.classList.toggle("selected", Number(tr.dataset.index) === selected);
    }}

    rowsEl.addEventListener("click", e => {{
      const tr = e.target.closest("tr[data-index]");
      if (!tr) return;
      selected = Number(tr.dataset.index);
      draw();
    }});
    document.getElementById("prev").addEventListener("click", () => {{ selected = (selected - 1 + panels.length) % panels.length; draw(); }});
    document.getElementById("next").addEventListener("click", () => {{ selected = (selected + 1) % panels.length; draw(); }});
    document.getElementById("showAll").addEventListener("change", draw);
    document.getElementById("showRods").addEventListener("change", draw);
    document.getElementById("risk").addEventListener("change", draw);
    addEventListener("resize", resizeCanvases);
    resizeCanvases();
  </script>
</body>
</html>
''',
        encoding="utf-8",
    )


def write_html(nodes: dict[str, dict[str, object]], rods: list[dict[str, str]], panel_rows: list[dict[str, object]]) -> None:
    node_json = [
        {
            "id": node_id,
            "x": node["point"][0],
            "y": node["point"][1],
            "z": node["point"][2],
            "risk": node["risk"],
            "label": f"{node_id} F:{node.get('front_node') or '-'} S:{node.get('side_node') or '-'} T:{node.get('top_node') or '-'}",
        }
        for node_id, node in sorted(nodes.items())
    ]
    rod_json = [{"a": row["node_a"], "b": row["node_b"], "id": row["rod_id"]} for row in rods]
    panel_json = []
    for row in panel_rows:
        panel_json.append(
            {
                "id": row["panel_id"],
                "type": row["panel_type"],
                "nodes": str(row["node_ids"]).split(),
                "area": row["area_mm2"],
                "risk": int(row["max_constraint_risk"]),
                "planarity": row["planarity_error_mm"],
                "color": color_for_risk(int(row["max_constraint_risk"]), str(row["panel_type"])),
                "edgeLengths": row["edge_lengths_mm"],
                "center": [row["center_x_mm"], row["center_y_depth_mm"], row["center_z_up_mm"]],
            }
        )

    rows_html = []
    for idx, row in enumerate(panel_rows):
        rows_html.append(
            f"<tr data-index='{idx}'><td>{html.escape(str(row['panel_id']))}</td>"
            f"<td>{html.escape(str(row['panel_type']))}</td>"
            f"<td>{html.escape(str(row['node_ids']))}</td>"
            f"<td>{html.escape(str(row['area_mm2']))}</td>"
            f"<td>{html.escape(str(row['max_constraint_risk']))}</td>"
            f"<td>{html.escape(str(row['planarity_error_mm']))}</td></tr>"
        )

    (OUT_DIR / "candidate-panel-review.html").write_text(
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>V1 Candidate Cardboard Panel Review</title>
  <style>
    body {{ margin: 0; font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: #172033; background: #f5f5f2; }}
    header {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 12px 16px; border-bottom: 1px solid #d1d5db; background: #ffffff; }}
    h1 {{ margin: 0; font-size: 16px; }}
    .meta {{ margin-top: 4px; color: #64748b; font-size: 12px; }}
    main {{ display: grid; grid-template-columns: minmax(0, 1fr) 520px; min-height: calc(100vh - 60px); }}
    canvas {{ display: block; width: 100%; height: calc(100vh - 60px); background: #fff; }}
    aside {{ border-left: 1px solid #d1d5db; background: #fafafa; overflow: auto; max-height: calc(100vh - 60px); }}
    .controls {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 10px; border-bottom: 1px solid #e5e7eb; font-size: 12px; }}
    button, select {{ border: 1px solid #aeb7c2; background: #fff; border-radius: 6px; padding: 6px 8px; cursor: pointer; }}
    label {{ display: inline-flex; gap: 5px; align-items: center; }}
    .panel-card {{ padding: 10px; border-bottom: 1px solid #e5e7eb; font-size: 12px; line-height: 1.45; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 11px; }}
    th, td {{ padding: 5px 4px; border-bottom: 1px solid #e5e7eb; text-align: left; white-space: nowrap; }}
    tr {{ cursor: pointer; }}
    tr.selected {{ background: #dbeafe; }}
    .hint {{ color: #64748b; }}
    @media (max-width: 1000px) {{ main {{ grid-template-columns: 1fr; }} canvas {{ height: 68vh; }} aside {{ max-height: none; }} }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>V1 Candidate Cardboard Panel Review</h1>
      <div class="meta">{len(panel_rows)} candidates from the frozen V1 rod graph. Click rows to inspect a panel.</div>
    </div>
    <button id="reset">Reset View</button>
  </header>
  <main>
    <canvas id="canvas"></canvas>
    <aside>
      <div class="controls">
        <button id="prev">Prev</button>
        <button id="next">Next</button>
        <label><input type="checkbox" id="showPanels" checked /> panels</label>
        <label><input type="checkbox" id="showRods" checked /> rods</label>
        <label><input type="checkbox" id="triangles" checked /> triangles</label>
        <label><input type="checkbox" id="quads" checked /> quads</label>
        <select id="risk">
          <option value="4">all risks</option>
          <option value="3">risk <= 3</option>
          <option value="2">risk <= 2</option>
          <option value="1">risk <= 1</option>
        </select>
      </div>
      <div class="panel-card" id="details"></div>
      <table>
        <thead><tr><th>ID</th><th>Type</th><th>Nodes</th><th>Area</th><th>Risk</th><th>Planar</th></tr></thead>
        <tbody id="rows">{"".join(rows_html)}</tbody>
      </table>
    </aside>
  </main>
  <script>
    const nodes = {json.dumps(node_json)};
    const rods = {json.dumps(rod_json)};
    const panels = {json.dumps(panel_json)};
    const byId = new Map(nodes.map(n => [n.id, n]));
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");
    const rowsEl = document.getElementById("rows");
    const details = document.getElementById("details");
    let selected = 0;
    let rotX = -0.48;
    let rotZ = -0.72;
    let zoom = 3.1;
    let dragging = false;
    let last = null;

    function filteredPanels() {{
      const showTri = document.getElementById("triangles").checked;
      const showQuad = document.getElementById("quads").checked;
      const maxRisk = Number(document.getElementById("risk").value);
      return panels.map((p, i) => [p, i]).filter(([p]) => (p.type === "triangle" ? showTri : showQuad) && p.risk <= maxRisk);
    }}

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
      return {{ x: canvas.width / 2 + t.x * scale, y: canvas.height / 2 - t.y * scale, z: t.z }};
    }}

    function panelDepth(panel) {{
      return panel.nodes.reduce((sum, id) => sum + project(byId.get(id)).z, 0) / panel.nodes.length;
    }}

    function drawPanel(panel, selectedPanel) {{
      const pts = panel.nodes.map(id => project(byId.get(id)));
      ctx.beginPath();
      ctx.moveTo(pts[0].x, pts[0].y);
      for (const p of pts.slice(1)) ctx.lineTo(p.x, p.y);
      ctx.closePath();
      ctx.globalAlpha = selectedPanel ? 0.55 : 0.16;
      ctx.fillStyle = panel.color;
      ctx.fill();
      ctx.globalAlpha = selectedPanel ? 1 : 0.36;
      ctx.strokeStyle = selectedPanel ? "#111827" : panel.color;
      ctx.lineWidth = (selectedPanel ? 3.2 : 1.4) * devicePixelRatio;
      ctx.stroke();
    }}

    function draw() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      const projected = new Map(nodes.map(n => [n.id, project(n)]));
      const visible = filteredPanels();
      const selectedPanel = panels[selected] || panels[0];

      if (document.getElementById("showPanels").checked) {{
        for (const [panel] of visible.slice().sort((a, b) => panelDepth(a[0]) - panelDepth(b[0]))) {{
          if (panel.id !== selectedPanel.id) drawPanel(panel, false);
        }}
        drawPanel(selectedPanel, true);
      }}

      if (document.getElementById("showRods").checked) {{
        ctx.globalAlpha = 0.42;
        ctx.strokeStyle = "#334155";
        ctx.lineWidth = 1.3 * devicePixelRatio;
        for (const r of rods) {{
          const a = projected.get(r.a), b = projected.get(r.b);
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }}
      }}

      ctx.globalAlpha = 1;
      for (const n of nodes) {{
        const p = projected.get(n.id);
        ctx.fillStyle = n.risk >= 4 ? "#ef4444" : n.risk >= 3 ? "#f59e0b" : n.risk >= 2 ? "#64748b" : "#16a34a";
        ctx.strokeStyle = "#111827";
        ctx.lineWidth = 1.2 * devicePixelRatio;
        ctx.beginPath();
        ctx.arc(p.x, p.y, 3.5 * devicePixelRatio, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      }}

      for (const id of selectedPanel.nodes) {{
        const p = projected.get(id);
        ctx.fillStyle = "#111827";
        ctx.font = `${{12 * devicePixelRatio}}px monospace`;
        ctx.fillText(id, p.x + 7 * devicePixelRatio, p.y - 7 * devicePixelRatio);
      }}
      updateDetails();
      updateTableSelection();
    }}

    function updateDetails() {{
      const p = panels[selected] || panels[0];
      details.innerHTML = `<strong>${{p.id}}</strong> <span class="hint">${{p.type}}</span><br>` +
        `Nodes: <code>${{p.nodes.join(" ")}}</code><br>` +
        `Area: ${{p.area}} mm2, Risk: ${{p.risk}}, Planarity: ${{p.planarity}} mm<br>` +
        `Edges: <code>${{p.edgeLengths}}</code>`;
    }}

    function updateTableSelection() {{
      for (const tr of rowsEl.querySelectorAll("tr")) tr.classList.toggle("selected", Number(tr.dataset.index) === selected);
    }}

    rowsEl.addEventListener("click", e => {{
      const tr = e.target.closest("tr[data-index]");
      if (!tr) return;
      selected = Number(tr.dataset.index);
      draw();
    }});
    document.getElementById("prev").addEventListener("click", () => {{ selected = (selected - 1 + panels.length) % panels.length; draw(); }});
    document.getElementById("next").addEventListener("click", () => {{ selected = (selected + 1) % panels.length; draw(); }});
    for (const id of ["showPanels", "showRods", "triangles", "quads", "risk"]) document.getElementById(id).addEventListener("change", draw);
    document.getElementById("reset").addEventListener("click", () => {{ rotX = -0.48; rotZ = -0.72; zoom = 3.1; draw(); }});
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
      zoom = Math.max(0.6, Math.min(10, zoom));
      draw();
    }}, {{passive: false}});
    addEventListener("resize", resize);
    resize();
  </script>
</body>
</html>
""",
        encoding="utf-8",
    )


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    nodes, rods, graph, rod_by_edge = load_graph()
    panel_rows = build_candidates(nodes, graph, rod_by_edge)
    write_eye_cutouts_csv(nodes)
    write_eye_insert_panels_csv(nodes)
    write_csv(
        OUT_DIR / "candidate_panels.csv",
        [
            "panel_id",
            "panel_type",
            "status",
            "node_ids",
            "rod_ids",
            "edge_lengths_mm",
            "area_mm2",
            "perimeter_mm",
            "min_edge_mm",
            "max_edge_mm",
            "planarity_error_mm",
            "max_constraint_risk",
            "center_x_mm",
            "center_y_depth_mm",
            "center_z_up_mm",
            "normal_x",
            "normal_y",
            "normal_z",
            "notes",
        ],
        panel_rows,
    )
    write_summary(panel_rows)
    write_html(nodes, rods, panel_rows)
    write_multiview_html(nodes, rods, panel_rows)
    write_panel_obj(nodes, rods, panel_rows)
    write_eye_insert_obj(nodes)
    write_combined_panel_obj(nodes, rods, panel_rows)
    print(f"Wrote {len(panel_rows)} panel candidates to {OUT_DIR}")


if __name__ == "__main__":
    main()
