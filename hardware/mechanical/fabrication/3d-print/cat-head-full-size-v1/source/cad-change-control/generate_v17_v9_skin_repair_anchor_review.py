#!/usr/bin/env python3
"""Generate an exact, review-only anchor view for the inherited V9 skin defect.

The frozen V17 STEP is never modified. The output contains copies of the exact
host face, its two intersecting partner faces, and the exact penetrating source
edge identified by its two frozen endpoints. Review markers are visually
separate and explicitly non-production geometry.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import FreeCAD as App
import FreeCADGui as Gui
import Part

from validate_change_contract import load_json, validate_files


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    return parser.parse_args(argv)


def repository_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise RuntimeError("cannot locate repository root")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in manifest["artifacts"]}


def vector(value) -> list[float]:
    return [round(float(value.x), 9), round(float(value.y), 9), round(float(value.z), 9)]


def edge_endpoints(edge) -> tuple[App.Vector, App.Vector]:
    vertices = edge.Vertexes
    if len(vertices) != 2:
        raise RuntimeError("expected a two-vertex source edge")
    return vertices[0].Point, vertices[1].Point


def endpoint_match_error(edge, expected: tuple[App.Vector, App.Vector]) -> float:
    first, second = edge_endpoints(edge)
    direct = max(first.distanceToPoint(expected[0]), second.distanceToPoint(expected[1]))
    reversed_error = max(first.distanceToPoint(expected[1]), second.distanceToPoint(expected[0]))
    return min(direct, reversed_error)


def find_edge(shape, expected: tuple[App.Vector, App.Vector], tolerance: float):
    candidates = []
    for index, edge in enumerate(shape.Edges, start=1):
        if len(edge.Vertexes) != 2:
            continue
        candidates.append((endpoint_match_error(edge, expected), index, edge))
    if not candidates:
        raise RuntimeError("source contains no two-vertex edges")
    error, index, edge = min(candidates, key=lambda item: item[0])
    if error > tolerance:
        raise RuntimeError(
            f"no edge matched the frozen endpoints: best Edge{index} error {error:.9f} mm"
        )
    return index, edge, error


def face_contains_edge(face, source_edge) -> bool:
    return any(candidate.isSame(source_edge) for candidate in face.Edges)


def add_shape(document, name: str, shape, label: str):
    obj = document.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape.copy()
    return obj


def add_traceability(obj, source_face: str, role: str) -> None:
    obj.addProperty("App::PropertyString", "SourceArtifact", "Traceability")
    obj.addProperty("App::PropertyString", "SourceSubshape", "Traceability")
    obj.addProperty("App::PropertyString", "ReviewRole", "Review")
    obj.addProperty("App::PropertyString", "AllowedAction", "ChangeControl")
    obj.SourceArtifact = "right_eye_v17"
    obj.SourceSubshape = source_face
    obj.ReviewRole = role
    obj.AllowedAction = "REVIEW_ONLY__NO_REPAIR_AUTHORIZED"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = repository_root(args.manifest)
    preflight = validate_files(args.manifest, args.contract, verify_files=True)
    if preflight["status"] != "PASS":
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return 1

    manifest = load_json(args.manifest)
    contract = load_json(args.contract)
    if contract.get("contract_id") != "read-only-v17-v9-skin-repair-anchor-review-v1":
        raise RuntimeError("wrong contract for V9 skin anchor review")
    if contract.get("geometry_changes_allowed") is not False:
        raise RuntimeError("geometry changes must remain forbidden")

    artifacts = artifact_map(manifest)
    anchor = contract["anchor_review"]
    source_path = root / artifacts["right_eye_v17"]["path"]
    lineage_path = root / artifacts["right_eye_v17_lineage_fcstd"]["path"]
    output_fcstd = root / anchor["output_fcstd"]
    report_dir = root / contract["output_directory"]
    output_report = report_dir / "validation-v1.json"
    if output_fcstd.exists() or output_report.exists():
        raise RuntimeError("refusing to overwrite an existing anchor-review artifact")

    source_hash_before = sha256_file(source_path)
    lineage_hash_before = sha256_file(lineage_path)
    source_shape = Part.read(str(source_path))
    if source_shape.isNull():
        raise RuntimeError("V17 STEP imported as a null shape")

    host_index = int(anchor["host_face"])
    partner_indices = [int(value) for value in anchor["partner_faces"]]
    expected = tuple(App.Vector(*point) for point in anchor["penetrating_edge_endpoints_mm"])
    edge_index, source_edge, match_error = find_edge(
        source_shape, expected, float(anchor["edge_match_tolerance_mm"])
    )
    host_face = source_shape.Faces[host_index - 1]
    partner_faces = [source_shape.Faces[index - 1] for index in partner_indices]
    edge_owner_indices = [int(value) for value in anchor["penetrating_edge_owner_faces"]]
    relevant_indices = [host_index, *partner_indices, *edge_owner_indices]
    membership = {
        f"Face{host_index}": face_contains_edge(host_face, source_edge),
        **{
            f"Face{index}": face_contains_edge(source_shape.Faces[index - 1], source_edge)
            for index in relevant_indices
            if index != host_index
        },
    }
    if membership[f"Face{host_index}"]:
        raise RuntimeError("candidate edge is already a host-face boundary edge")
    source_edge_owner_faces = [
        index
        for index, face in enumerate(source_shape.Faces, start=1)
        if face_contains_edge(face, source_edge)
    ]
    if source_edge_owner_faces != edge_owner_indices:
        raise RuntimeError(
            "candidate edge owner faces differ from the frozen contract: "
            f"expected {edge_owner_indices}, observed {source_edge_owner_faces}"
        )

    section = source_edge.section(host_face)
    section_points = [vertex.Point for vertex in section.Vertexes]
    if not section_points:
        raise RuntimeError("candidate edge does not intersect the host face")

    output_fcstd.parent.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    Gui.showMainWindow()
    Gui.updateGui()
    document = App.newDocument("CAT_HEAD_RIGHT_EYE_V17_V9_SKIN_REPAIR_ANCHOR_REVIEW_V1")
    try:
        context_group = document.addObject("App::DocumentObjectGroup", "FROZEN_V17_CONTEXT")
        context = add_shape(
            document,
            "FROZEN_EXACT_RIGHT_EYE_V17",
            source_shape,
            "FROZEN exact V17 right eye — translucent context",
        )
        add_traceability(context, "WholeShape", "FROZEN_CONTEXT")
        context.ViewObject.ShapeColor = (0.74, 0.74, 0.76)
        context.ViewObject.Transparency = 86
        context.ViewObject.Visibility = False
        context_group.addObject(context)

        anchor_group = document.addObject("App::DocumentObjectGroup", "EXACT_REPAIR_ANCHORS")
        host = add_shape(
            document,
            "REVIEW_ONLY__HOST_FACE__V17_FACE587",
            host_face,
            "HOST FACE — V17 Face587",
        )
        add_traceability(host, f"Face{host_index}", "HOST_FACE__PRESERVE_SURFACE")
        host.ViewObject.ShapeColor = (0.15, 0.95, 0.25)
        host.ViewObject.LineColor = (0.05, 0.40, 0.10)
        host.ViewObject.Transparency = 35
        host.ViewObject.LineWidth = 5.0
        anchor_group.addObject(host)

        partner_colors = [(1.0, 0.48, 0.05), (1.0, 0.86, 0.05)]
        for index, face, color in zip(partner_indices, partner_faces, partner_colors):
            obj = add_shape(
                document,
                f"REVIEW_ONLY__PARTNER_FACE__V17_FACE{index}",
                face,
                f"PARTNER FACE — V17 Face{index}",
            )
            add_traceability(obj, f"Face{index}", "PARTNER_FACE__EDGE_OWNER")
            obj.ViewObject.ShapeColor = color
            obj.ViewObject.LineColor = color
            obj.ViewObject.Transparency = 35
            obj.ViewObject.LineWidth = 5.0
            anchor_group.addObject(obj)

        owner_group = document.addObject("App::DocumentObjectGroup", "PENETRATING_EDGE_OWNER_FACES")
        for index in edge_owner_indices:
            face = source_shape.Faces[index - 1]
            obj = add_shape(
                document,
                f"REVIEW_ONLY__EDGE_OWNER_FACE__V17_FACE{index}",
                face,
                f"EDGE OWNER FACE — V17 Face{index}",
            )
            add_traceability(obj, f"Face{index}", "PENETRATING_EDGE_OWNER_FACE")
            obj.ViewObject.ShapeColor = (0.10, 0.75, 1.0)
            obj.ViewObject.LineColor = (0.0, 0.35, 0.75)
            obj.ViewObject.Transparency = 55
            obj.ViewObject.LineWidth = 4.0
            obj.ViewObject.Visibility = False
            owner_group.addObject(obj)

        edge_obj = add_shape(
            document,
            f"REVIEW_ONLY__PENETRATING_EDGE__V17_EDGE{edge_index}",
            source_edge,
            f"PENETRATING EDGE — V17 Edge{edge_index}",
        )
        add_traceability(edge_obj, f"Edge{edge_index}", "PENETRATING_EDGE__SPLIT_WELD_CANDIDATE")
        edge_obj.ViewObject.LineColor = (1.0, 0.0, 1.0)
        edge_obj.ViewObject.PointColor = (1.0, 0.0, 1.0)
        edge_obj.ViewObject.LineWidth = 10.0
        edge_obj.ViewObject.PointSize = 10.0
        anchor_group.addObject(edge_obj)

        marker_group = document.addObject("App::DocumentObjectGroup", "REVIEW_HELPERS__NOT_GEOMETRY")
        edge_first, edge_second = edge_endpoints(source_edge)
        marker_points = [edge_first, edge_second, *section_points]
        marker_roles = ["EDGE_ENDPOINT_A", "EDGE_ENDPOINT_B"] + [
            f"HOST_INTERSECTION_{index}" for index in range(1, len(section_points) + 1)
        ]
        for index, (point, role) in enumerate(zip(marker_points, marker_roles), start=1):
            marker = add_shape(
                document,
                f"REVIEW_HELPER__{role}",
                Part.makeSphere(0.22, point),
                f"{role} — visual marker only",
            )
            add_traceability(marker, "None", "REVIEW_HELPER__NOT_PRODUCTION_GEOMETRY")
            marker.ViewObject.ShapeColor = (1.0, 0.0, 1.0) if index <= 2 else (0.0, 0.85, 1.0)
            marker.ViewObject.Transparency = 15
            marker_group.addObject(marker)

        read_me = document.addObject("App::FeaturePython", "READ_ME__ANCHOR_REVIEW")
        read_me.addProperty("App::PropertyString", "Status", "Review")
        read_me.addProperty("App::PropertyString", "HostFace", "ExactAnchors")
        read_me.addProperty("App::PropertyStringList", "PartnerFaces", "ExactAnchors")
        read_me.addProperty("App::PropertyStringList", "EdgeOwnerFaces", "ExactAnchors")
        read_me.addProperty("App::PropertyString", "PenetratingEdge", "ExactAnchors")
        read_me.addProperty("App::PropertyVectorList", "EdgeEndpoints", "ExactAnchors")
        read_me.addProperty("App::PropertyString", "ProposedOperation", "ChangeControl")
        read_me.addProperty("App::PropertyString", "GeometryAuthorization", "ChangeControl")
        read_me.addProperty("App::PropertyString", "ReleaseStatus", "ChangeControl")
        read_me.Status = "EXACT_ANCHORS_LOCALIZED__USER_APPROVAL_REQUIRED"
        read_me.HostFace = f"Face{host_index}"
        read_me.PartnerFaces = [f"Face{index}" for index in partner_indices]
        read_me.EdgeOwnerFaces = [f"Face{index}" for index in edge_owner_indices]
        read_me.PenetratingEdge = f"Edge{edge_index}"
        read_me.EdgeEndpoints = [edge_first, edge_second]
        read_me.ProposedOperation = "LOCAL_TOPOLOGICAL_SPLIT_AND_WELD__ZERO_VERTEX_MOTION"
        read_me.GeometryAuthorization = "NONE__ANCHOR_REVIEW_ONLY"
        read_me.ReleaseStatus = "NO_STL__NO_GCODE__NO_ASA_PRINT_RELEASE"

        document.recompute()
        Gui.activeDocument().activeView().viewAxonometric()
        Gui.activeDocument().activeView().fitAll()
        Gui.updateGui()
        document.saveAs(str(output_fcstd))
    finally:
        App.closeDocument(document.Name)

    source_hash_after = sha256_file(source_path)
    lineage_hash_after = sha256_file(lineage_path)
    if source_hash_after != source_hash_before or lineage_hash_after != lineage_hash_before:
        raise RuntimeError("a frozen source artifact changed during anchor review generation")

    edge_first, edge_second = edge_endpoints(source_edge)
    report = {
        "status": "PASS__EXACT_REVIEW_ANCHORS_GENERATED",
        "contract_id": contract["contract_id"],
        "source": {
            "path": artifacts["right_eye_v17"]["path"],
            "sha256_before": source_hash_before,
            "sha256_after": source_hash_after,
            "valid": bool(source_shape.isValid()),
            "closed": bool(source_shape.isClosed()),
            "solid_count": len(source_shape.Solids),
        },
        "lineage_sha256_before": lineage_hash_before,
        "lineage_sha256_after": lineage_hash_after,
        "anchors": {
            "host_face": f"Face{host_index}",
            "partner_faces": [f"Face{index}" for index in partner_indices],
            "edge_owner_faces": [f"Face{index}" for index in edge_owner_indices],
            "penetrating_edge": f"Edge{edge_index}",
            "edge_length_mm": round(float(source_edge.Length), 9),
            "edge_endpoints_mm": [vector(edge_first), vector(edge_second)],
            "endpoint_match_error_mm": round(float(match_error), 12),
            "face_membership": membership,
            "host_intersection_points_mm": [vector(point) for point in section_points],
        },
        "proposed_operation": "LOCAL_TOPOLOGICAL_SPLIT_AND_WELD__ZERO_VERTEX_MOTION",
        "geometry_changes": 0,
        "production_geometry_authorized": False,
        "review_file": str(output_fcstd.relative_to(root)),
        "review_file_sha256": sha256_file(output_fcstd),
        "release_holds": contract["release_holds"],
    }
    output_report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
