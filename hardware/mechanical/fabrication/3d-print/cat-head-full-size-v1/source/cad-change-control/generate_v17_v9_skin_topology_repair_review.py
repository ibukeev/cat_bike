#!/usr/bin/env python3
"""Generate the approved isolated V17/V9 skin topology repair review.

The frozen STEP is never modified.  The only permitted geometry operation is
the contract-pinned diagonal flip over source Face582 and Face587.  No vertex
is moved, no automatic healing/refinement is used, and no STEP/STL is exported.
The FCStd review is saved only after every fail-closed gate passes in memory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from itertools import combinations
from pathlib import Path
from typing import Any

import FreeCAD as App
import Part

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bop_diagnostics import parse_bop_diagnostics  # noqa: E402
from validate_change_contract import find_repository_root  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def vector(values: list[float]) -> App.Vector:
    return App.Vector(float(values[0]), float(values[1]), float(values[2]))


def point(value: App.Vector) -> list[float]:
    return [round(float(value.x), 12), round(float(value.y), 12), round(float(value.z), 12)]


def bbox(shape) -> dict[str, list[float]]:
    box = shape.BoundBox
    return {
        "minimum_mm": [float(box.XMin), float(box.YMin), float(box.ZMin)],
        "maximum_mm": [float(box.XMax), float(box.YMax), float(box.ZMax)],
    }


def bbox_deltas(first, second) -> list[float]:
    a = first.BoundBox
    b = second.BoundBox
    return [
        float(b.XMin - a.XMin),
        float(b.YMin - a.YMin),
        float(b.ZMin - a.ZMin),
        float(b.XMax - a.XMax),
        float(b.YMax - a.YMax),
        float(b.ZMax - a.ZMax),
    ]


def check_messages(shape) -> list[str]:
    try:
        raw = shape.check(True)
        return [str(item) for item in raw] if raw else []
    except Exception as exc:
        return [f"OCCT check raised: {exc}"]


def boxes_overlap(first, second, tolerance: float = 1.0e-7) -> bool:
    return not (
        first.XMax < second.XMin - tolerance
        or first.XMin > second.XMax + tolerance
        or first.YMax < second.YMin - tolerance
        or first.YMin > second.YMax + tolerance
        or first.ZMax < second.ZMin - tolerance
        or first.ZMin > second.ZMax + tolerance
    )


def nearest_vertex_error(shape, target: App.Vector) -> float:
    return min(vertex.Point.distanceToPoint(target) for vertex in shape.Vertexes)


def max_bidirectional_vertex_error(first, second) -> float:
    def directed(source, target) -> float:
        return max(nearest_vertex_error(target, vertex.Point) for vertex in source.Vertexes)

    return max(directed(first, second), directed(second, first))


def find_edge_by_points(shape, first: App.Vector, second: App.Vector, tolerance: float):
    for index, edge in enumerate(shape.Edges, start=1):
        if len(edge.Vertexes) != 2:
            continue
        a, b = (vertex.Point for vertex in edge.Vertexes)
        direct = max(a.distanceToPoint(first), b.distanceToPoint(second))
        reverse = max(a.distanceToPoint(second), b.distanceToPoint(first))
        if min(direct, reverse) <= tolerance:
            return index, edge
    raise RuntimeError(f"edge not found between {point(first)} and {point(second)}")


def make_face(edges, reference_face):
    face = Part.Face(Part.Wire(Part.__sortEdges__(edges)))
    if face.normalAt(0.0, 0.0).dot(reference_face.normalAt(0.0, 0.0)) < 0.0:
        face.reverse()
    return face


def source_neighbor_face_indices(shape, removed: set[int]) -> set[int]:
    boundary_edges = []
    for face_index in removed:
        for edge in shape.Faces[face_index - 1].Edges:
            uses = sum(
                any(candidate.isSame(edge) for candidate in face.Edges)
                for face in shape.Faces
            )
            if uses == 1:
                continue
            if not any(candidate.isSame(edge) for candidate in boundary_edges):
                boundary_edges.append(edge)
    neighbors: set[int] = set()
    for face_index, face in enumerate(shape.Faces, start=1):
        if face_index in removed:
            continue
        if any(
            any(candidate.isSame(edge) for candidate in face.Edges)
            for edge in boundary_edges
        ):
            neighbors.add(face_index)
    return neighbors


def local_pair_diagnostics(named_shapes: list[tuple[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for (first_name, first), (second_name, second) in combinations(named_shapes, 2):
        if not boxes_overlap(first.BoundBox, second.BoundBox):
            continue
        if float(first.distToShape(second)[0]) > 1.0e-7:
            continue
        diagnostics = parse_bop_diagnostics(check_messages(Part.makeCompound([first, second])))
        shared_vertex_count = sum(
            any(
                first_vertex.Point.distanceToPoint(second_vertex.Point) <= 1.0e-7
                for second_vertex in second.Vertexes
            )
            for first_vertex in first.Vertexes
        )
        if diagnostics and shared_vertex_count == 0:
            records.append(
                {
                    "pair": [first_name, second_name],
                    "diagnostics": diagnostics,
                    "shared_vertex_count": shared_vertex_count,
                    "common_area_mm2": float(first.common(second).Area),
                    "common_length_mm": float(first.common(second).Length),
                }
            )
    return records


def faces_match_geometrically(first, second, tolerance: float = 1.0e-7) -> bool:
    if len(first.Vertexes) != len(second.Vertexes):
        return False
    if len(first.Edges) != len(second.Edges):
        return False
    if abs(float(first.Area - second.Area)) > tolerance:
        return False
    if max(abs(value) for value in bbox_deltas(first, second)) > tolerance:
        return False
    if first.CenterOfMass.distanceToPoint(second.CenterOfMass) > tolerance:
        return False
    return max_bidirectional_vertex_error(first, second) <= tolerance


def retained_face_count(candidate, retained_faces) -> int:
    return sum(
        any(
            faces_match_geometrically(source_face, candidate_face)
            for candidate_face in candidate.Faces
        )
        for source_face in retained_faces
    )


def add_shape(document, name: str, label: str, shape, color, transparency: int, visible: bool):
    obj = document.addObject("PartDesign::Feature", name)
    obj.Label = label
    obj.Shape = shape
    if obj.ViewObject is not None:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineColor = (0.12, 0.12, 0.12)
        obj.ViewObject.Transparency = transparency
        obj.ViewObject.Visibility = visible
    return obj


def main() -> int:
    args = parse_args()
    root = find_repository_root(args.contract)
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    source_path = root / contract["source"]["path"]
    source_hash = sha256_file(source_path)
    if source_hash != contract["source"]["sha256"]:
        raise RuntimeError("frozen V17 source SHA-256 mismatch")

    source = Part.Shape()
    source.read(str(source_path))
    if source.isNull():
        raise RuntimeError("frozen V17 STEP imported as a null shape")

    operation = contract["operation"]
    gates = contract["gates"]
    points = {name: vector(values) for name, values in operation["points_mm"].items()}
    anchor_errors = {
        name: nearest_vertex_error(source, target) for name, target in points.items()
    }
    if max(anchor_errors.values()) > float(gates["maximum_anchor_error_mm"]):
        raise RuntimeError(f"contract anchors do not match frozen source: {anchor_errors}")

    removed = set(int(index) for index in operation["remove_source_faces"])
    host = source.Faces[int(operation["host_face"]) - 1]
    sliver = source.Faces[int(operation["sliver_face"]) - 1]
    source_patch_facets = sum(
        len(source.Faces[index - 1].tessellate(0.001)[1]) for index in removed
    )

    boundary = {}
    for name, first, second in (
        ("AB", points["A"], points["B"]),
        ("BD", points["B"], points["D"]),
        ("DP", points["D"], points["P"]),
        ("PC", points["P"], points["C"]),
        ("CA", points["C"], points["A"]),
    ):
        boundary[name] = find_edge_by_points(
            source, first, second, float(gates["maximum_anchor_error_mm"])
        )

    ad = Part.makeLine(points["A"], points["D"])
    ap = Part.makeLine(points["A"], points["P"])
    replacements = [
        make_face([boundary["AB"][1], boundary["BD"][1], ad], host),
        make_face([boundary["CA"][1], boundary["PC"][1], ap], host),
        make_face([ap, boundary["DP"][1], ad], sliver),
    ]
    replacement_patch_facets = sum(len(face.tessellate(0.001)[1]) for face in replacements)

    retained_faces = [
        face for index, face in enumerate(source.Faces, start=1) if index not in removed
    ]
    shell = Part.makeShell([*retained_faces, *replacements])
    candidate = Part.makeSolid(shell) if shell.isClosed() else shell

    neighbor_indices = source_neighbor_face_indices(source, removed)
    local_indices = sorted(
        neighbor_indices
        | set(int(index) for index in operation["diagnostic_partner_faces"])
        | set(int(index) for index in operation["penetrating_edge_owner_faces"])
    )
    local_shapes = [(f"replacement_{index}", face) for index, face in enumerate(replacements, 1)]
    local_shapes.extend(
        (f"source_Face{index}", source.Faces[index - 1])
        for index in local_indices
        if index not in removed
    )
    local_diagnostics = local_pair_diagnostics(local_shapes)

    bounds_delta = bbox_deltas(source, candidate)
    vertex_motion = max_bidirectional_vertex_error(source, candidate)
    volume_delta = float(candidate.Volume - source.Volume)
    local_surface_deviation = float(Part.Vertex(points["P"]).distToShape(host)[0])
    retained_count = retained_face_count(candidate, retained_faces)
    protected_face_retention = {
        f"Face{index}": any(
            face.isSame(source.Faces[index - 1]) for face in candidate.Faces
        )
        for index in operation["protected_source_faces"]
    }

    checks = {
        "source_sha256_matches": source_hash == contract["source"]["sha256"],
        "anchors_match": max(anchor_errors.values())
        <= float(gates["maximum_anchor_error_mm"]),
        "source_patch_facet_count": source_patch_facets
        == int(gates["required_source_patch_facet_count"]),
        "replacement_patch_facet_count": replacement_patch_facets
        == int(gates["required_replacement_patch_facet_count"]),
        "candidate_valid": bool(candidate.isValid()) == bool(gates["require_valid"]),
        "candidate_closed": bool(candidate.isClosed()) == bool(gates["require_closed"]),
        "candidate_solid_count": len(candidate.Solids) == int(gates["required_solid_count"]),
        "vertex_motion": vertex_motion <= float(gates["maximum_vertex_motion_mm"]),
        "bounds_unchanged": max(abs(value) for value in bounds_delta)
        <= float(gates["maximum_bounds_delta_mm"]),
        "volume_unchanged": abs(volume_delta)
        <= float(gates["maximum_absolute_volume_delta_mm3"]),
        "local_surface_deviation": local_surface_deviation
        <= float(gates["maximum_local_surface_deviation_mm"]),
        "local_bop_diagnostics": len(local_diagnostics)
        == int(gates["required_local_bop_diagnostic_count"]),
        "all_unmodified_faces_retained": retained_count == len(retained_faces),
        "protected_faces_retained": all(protected_face_retention.values()),
    }
    passed = all(checks.values())
    result = {
        "schema_version": "1.0",
        "generator": "freecad-v17-v9-local-diagonal-flip-review-v1",
        "freecad_version": App.Version(),
        "contract_id": contract["contract_id"],
        "status": "PASS__REVIEW_ONLY_PROPOSAL" if passed else "FAIL__NO_CAD_SAVED",
        "source": {
            "path": contract["source"]["path"],
            "sha256": source_hash,
            "face_count": len(source.Faces),
            "volume_mm3": float(source.Volume),
            "bounds": bbox(source),
        },
        "operation": {
            "type": operation["type"],
            "removed_source_faces": sorted(removed),
            "boundary_edges": {name: value[0] for name, value in boundary.items()},
            "new_diagonals": ["A-D", "A-P"],
            "replacement_triangles": operation["replacement_triangles"],
            "automatic_healing_used": False,
            "broad_boolean_used": False,
            "vertex_motion_used": False,
        },
        "measurements": {
            "anchor_errors_mm": anchor_errors,
            "source_patch_facet_count": source_patch_facets,
            "replacement_patch_facet_count": replacement_patch_facets,
            "candidate_face_count": len(candidate.Faces),
            "candidate_volume_mm3": float(candidate.Volume),
            "volume_delta_mm3": volume_delta,
            "bounds_delta_mm": bounds_delta,
            "maximum_vertex_motion_mm": vertex_motion,
            "local_surface_deviation_mm": local_surface_deviation,
            "retained_source_face_count": retained_count,
            "expected_retained_source_face_count": len(retained_faces),
            "protected_face_retention": protected_face_retention,
            "local_face_indices_audited": local_indices,
            "local_bop_diagnostic_count": len(local_diagnostics),
            "local_bop_diagnostics": local_diagnostics,
            "global_occt_check_messages": check_messages(candidate),
        },
        "checks": checks,
        "release_holds": contract["release_holds"],
    }

    if not passed:
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "checks": checks,
                    "failed_checks": [name for name, ok in checks.items() if not ok],
                    "measurements": {
                        key: value
                        for key, value in result["measurements"].items()
                        if key != "global_occt_check_messages"
                    },
                    "global_occt_check_message_count": len(
                        result["measurements"]["global_occt_check_messages"]
                    ),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    output_dir = root / contract["output"]["directory"]
    fcstd_path = output_dir / contract["output"]["fcstd"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    output_dir.mkdir(parents=True)

    document = App.newDocument("CAT_HEAD_RIGHT_EYE_V17_V9_SKIN_TOPOLOGY_REPAIR_REVIEW_V1")
    try:
        frozen = add_shape(
            document,
            "FROZEN_RIGHT_EYE_V17",
            "FROZEN__RIGHT_EYE_V17__UNCHANGED",
            source,
            (0.62, 0.66, 0.70),
            75,
            False,
        )
        proposal = add_shape(
            document,
            "PROPOSED_RIGHT_EYE_V17_V9_SKIN_REPAIRED",
            "PROPOSED__RIGHT_EYE_V17_V9_SKIN_REPAIRED__REVIEW_ONLY",
            candidate,
            (0.72, 0.78, 0.84),
            0,
            True,
        )
        old_patch = add_shape(
            document,
            "REVIEW_OLD_HOST_AND_SLIVER",
            "REVIEW_ONLY__OLD_FACE582_FACE587__REMOVED_BY_PROPOSAL",
            Part.makeCompound([sliver, host]),
            (0.90, 0.25, 0.12),
            20,
            False,
        )
        new_patch = add_shape(
            document,
            "REVIEW_NEW_DIAGONAL_FLIP_PATCH",
            "REVIEW_ONLY__NEW_A_D_A_P_DIAGONAL_PATCH",
            Part.makeCompound(replacements),
            (0.15, 0.85, 0.28),
            0,
            True,
        )
        for obj in (frozen, proposal, old_patch, new_patch):
            obj.addProperty("App::PropertyString", "ContractId", "ChangeControl")
            obj.ContractId = contract["contract_id"]
            obj.addProperty("App::PropertyString", "SourceSha256", "ChangeControl")
            obj.SourceSha256 = source_hash
            obj.addProperty("App::PropertyString", "ReleaseState", "ChangeControl")
            obj.ReleaseState = "REVIEW_ONLY__NO_MIRROR_NO_STL_NO_PRINT"
        document.recompute()
        document.saveAs(str(fcstd_path))
    finally:
        App.closeDocument(document.Name)

    result["output"] = {
        "fcstd": str(fcstd_path.relative_to(root)),
        "fcstd_sha256": sha256_file(fcstd_path),
        "validation": str(validation_path.relative_to(root)),
        "step_exported": False,
        "stl_exported": False,
    }
    validation_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": result["status"],
                "checks": checks,
                "output": result["output"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
