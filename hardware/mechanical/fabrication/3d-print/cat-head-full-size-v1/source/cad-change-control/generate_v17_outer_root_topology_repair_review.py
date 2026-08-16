#!/usr/bin/env python3
"""Generate an isolated review for the V17 outer eye-root T-junction repair.

The hash-pinned V2 STEP is opened read-only.  Five contract-pinned faces are
replaced by four faces that collapse one 0.0000007 mm^2 folded sliver onto its
host edge.  Only the sliver apex moves, by about four nanometres.  No broad
boolean, automatic healing, mirror, production union, or print export occurs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import Counter
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


def face_geometry_signature(face) -> tuple[object, ...]:
    box = face.BoundBox
    center = face.CenterOfMass
    return (
        len(face.Vertexes),
        len(face.Edges),
        round(float(face.Area), 8),
        *(round(float(value), 8) for value in (
            box.XMin,
            box.YMin,
            box.ZMin,
            box.XMax,
            box.YMax,
            box.ZMax,
            center.x,
            center.y,
            center.z,
        )),
    )


def retained_face_count(candidate, retained_faces) -> int:
    retained = Counter(face_geometry_signature(face) for face in retained_faces)
    available = Counter(face_geometry_signature(face) for face in candidate.Faces)
    return sum(min(count, available[signature]) for signature, count in retained.items())


def local_pair_diagnostics(named_shapes: list[tuple[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for (first_name, first), (second_name, second) in combinations(named_shapes, 2):
        if not boxes_overlap(first.BoundBox, second.BoundBox):
            continue
        if float(first.distToShape(second)[0]) > 1.0e-7:
            continue
        diagnostics = parse_bop_diagnostics(check_messages(Part.makeCompound([first, second])))
        common = first.common(second)
        shared_vertices = sum(
            any(
                first_vertex.Point.distanceToPoint(second_vertex.Point) <= 1.0e-7
                for second_vertex in second.Vertexes
            )
            for first_vertex in first.Vertexes
        )
        if diagnostics and shared_vertices == 0:
            records.append(
                {
                    "pair": [first_name, second_name],
                    "diagnostics": diagnostics,
                    "shared_vertex_count": shared_vertices,
                    "common_area_mm2": float(common.Area),
                    "common_length_mm": float(common.Length),
                }
            )
    return records


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
        raise RuntimeError("source STEP SHA-256 mismatch")

    source = Part.Shape()
    source.read(str(source_path))
    if source.isNull():
        raise RuntimeError("source STEP imported as a null shape")

    operation = contract["operation"]
    gates = contract["gates"]
    points = {name: vector(values) for name, values in operation["points_mm"].items()}
    source_anchor_names = ["Q1", "Q2", "Q3", "Q4", "T1", "T2", "T3"]
    anchor_errors = {name: nearest_vertex_error(source, points[name]) for name in source_anchor_names}
    if max(anchor_errors.values()) > float(gates["maximum_anchor_error_mm"]):
        raise RuntimeError(f"contract anchors do not match source: {anchor_errors}")

    collapsed_distance = points["T2"].distanceToPoint(points["P"])
    removed = set(int(index) for index in operation["remove_source_faces"])
    retained_faces = [face for index, face in enumerate(source.Faces, start=1) if index not in removed]
    source_patch_facets = sum(len(source.Faces[index - 1].tessellate(0.001)[1]) for index in removed)

    boundary = {}
    for name, first, second in (
        ("Q3Q4", points["Q3"], points["Q4"]),
        ("Q4Q2", points["Q4"], points["Q2"]),
        ("Q3Q1", points["Q3"], points["Q1"]),
        ("Q2T3", points["Q2"], points["T3"]),
        ("Q1T1", points["Q1"], points["T1"]),
        ("T3T1", points["T3"], points["T1"]),
    ):
        boundary[name] = find_edge_by_points(
            source, first, second, float(gates["maximum_anchor_error_mm"])
        )

    q2p = Part.makeLine(points["Q2"], points["P"])
    pq1 = Part.makeLine(points["P"], points["Q1"])
    pt3 = Part.makeLine(points["P"], points["T3"])
    pt1 = Part.makeLine(points["P"], points["T1"])
    replacements = [
        make_face(
            [boundary["Q3Q4"][1], boundary["Q4Q2"][1], q2p, pq1, boundary["Q3Q1"][1]],
            source.Faces[int(operation["host_face"]) - 1],
        ),
        make_face([q2p, boundary["Q2T3"][1], pt3], source.Faces[int(operation["fan_face_q2"]) - 1]),
        make_face([pq1, boundary["Q1T1"][1], pt1], source.Faces[int(operation["fan_face_q1"]) - 1]),
        make_face([pt3, boundary["T3T1"][1], pt1], source.Faces[int(operation["cap_face"]) - 1]),
    ]
    replacement_patch_facets = sum(len(face.tessellate(0.001)[1]) for face in replacements)

    shell = Part.makeShell([*retained_faces, *replacements])
    candidate = Part.makeSolid(shell) if shell.isClosed() else shell
    local_shapes = [(f"replacement_{index}", face) for index, face in enumerate(replacements, 1)]
    local_shapes.extend(
        (f"source_Face{index}", source.Faces[index - 1])
        for index in operation["local_partner_faces"]
        if int(index) not in removed
    )
    local_diagnostics = local_pair_diagnostics(local_shapes)

    bounds_delta = bbox_deltas(source, candidate)
    vertex_motion = max_bidirectional_vertex_error(source, candidate)
    volume_delta = float(candidate.Volume - source.Volume)
    retained_count = retained_face_count(candidate, retained_faces)
    checks = {
        "source_sha256_matches": source_hash == contract["source"]["sha256"],
        "anchors_match": max(anchor_errors.values()) <= float(gates["maximum_anchor_error_mm"]),
        "collapse_distance_matches": abs(collapsed_distance - float(operation["collapse_distance_mm"]))
        <= float(gates["maximum_collapse_distance_error_mm"]),
        "source_patch_facet_count": source_patch_facets == int(gates["required_source_patch_facet_count"]),
        "replacement_patch_facet_count": replacement_patch_facets == int(gates["required_replacement_patch_facet_count"]),
        "candidate_valid": bool(candidate.isValid()) == bool(gates["require_valid"]),
        "candidate_closed": bool(candidate.isClosed()) == bool(gates["require_closed"]),
        "candidate_solid_count": len(candidate.Solids) == int(gates["required_solid_count"]),
        "candidate_face_count": len(candidate.Faces) == int(gates["required_face_count"]),
        "vertex_motion": vertex_motion <= float(gates["maximum_vertex_motion_mm"]),
        "bounds_unchanged": max(abs(value) for value in bounds_delta) <= float(gates["maximum_bounds_delta_mm"]),
        "volume_unchanged": abs(volume_delta) <= float(gates["maximum_absolute_volume_delta_mm3"]),
        "local_bop_diagnostics": len(local_diagnostics) == int(gates["required_local_bop_diagnostic_count"]),
        "all_unmodified_faces_retained": retained_count == len(retained_faces),
    }
    passed = all(checks.values())
    result = {
        "schema_version": "1.0",
        "generator": "freecad-v17-outer-root-folded-sliver-collapse-review-v3",
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
            "collapsed_vertex_from_mm": point(points["T2"]),
            "collapsed_vertex_to_mm": point(points["P"]),
            "collapsed_distance_mm": collapsed_distance,
            "automatic_healing_used": False,
            "broad_boolean_used": False,
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
            "retained_source_face_count": retained_count,
            "expected_retained_source_face_count": len(retained_faces),
            "local_bop_diagnostic_count": len(local_diagnostics),
            "local_bop_diagnostics": local_diagnostics,
            "global_occt_check_messages": check_messages(candidate),
        },
        "checks": checks,
        "release_holds": contract["release_holds"],
    }

    if not passed:
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1

    output_dir = root / contract["output"]["directory"]
    fcstd_path = output_dir / contract["output"]["fcstd"]
    validation_path = output_dir / contract["output"]["validation"]
    if output_dir.exists():
        raise FileExistsError(f"refusing to overwrite review output: {output_dir}")
    output_dir.mkdir(parents=True)

    document = App.newDocument("CAT_HEAD_RIGHT_EYE_V17_OUTER_ROOT_TOPOLOGY_REPAIR_REVIEW_V3")
    try:
        frozen = add_shape(document, "FROZEN_SOURCE_V2", "FROZEN__RIGHT_EYE_V17_V9_REPAIRED_STEP_V2", source, (0.62, 0.66, 0.70), 75, False)
        proposal = add_shape(document, "PROPOSED_OUTER_ROOT_REPAIRED_V3", "PROPOSED__RIGHT_EYE_V17_OUTER_ROOT_TOPOLOGY_REPAIRED_V3__REVIEW_ONLY", candidate, (0.72, 0.78, 0.84), 0, True)
        old_patch = add_shape(document, "REVIEW_OLD_FOLDED_PATCH", "REVIEW_ONLY__OLD_FACE72_178_340_341_489", Part.makeCompound([source.Faces[index - 1] for index in sorted(removed)]), (0.90, 0.25, 0.12), 20, False)
        new_patch = add_shape(document, "REVIEW_NEW_WATERTIGHT_PATCH", "REVIEW_ONLY__NEW_SHARED_EDGE_PATCH_V3", Part.makeCompound(replacements), (0.15, 0.85, 0.28), 0, True)
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
    validation_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "checks": checks, "output": result["output"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
