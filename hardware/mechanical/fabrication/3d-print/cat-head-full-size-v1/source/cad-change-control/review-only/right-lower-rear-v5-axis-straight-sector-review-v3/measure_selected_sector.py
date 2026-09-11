#!/usr/bin/env python3
"""Read-only measurement of the user-selected V2 cassette sector."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
CAT_HEAD_ROOT = HERE.parents[3]
DEFAULT_CONTRACT = HERE / "measurement-contract.json"
AXES = {
    "X": (1.0, 0.0, 0.0),
    "Y": (0.0, 1.0, 0.0),
    "Z": (0.0, 0.0, 1.0),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def vector_record(vector: Any) -> list[float]:
    return [float(vector.x), float(vector.y), float(vector.z)]


def unit(vector: Any) -> Any:
    result = type(vector)(float(vector.x), float(vector.y), float(vector.z))
    length = float(result.Length)
    if length <= 1.0e-12:
        raise RuntimeError("cannot normalize zero-length vector")
    result.normalize()
    return result


def axis_alignment(vector: Any, App: Any) -> dict[str, Any]:
    direction = unit(vector)
    records = []
    for name, values in AXES.items():
        axis = App.Vector(*values)
        dot = float(direction.dot(axis))
        records.append(
            {
                "axis": name,
                "signed_dot": dot,
                "absolute_dot": abs(dot),
                "unsigned_angle_deg": math.degrees(
                    math.acos(max(-1.0, min(1.0, abs(dot))))
                ),
            }
        )
    records.sort(key=lambda item: (item["unsigned_angle_deg"], item["axis"]))
    return {"closest": records[0], "all": records}


def edge_record(edge: Any, index: int, App: Any) -> dict[str, Any]:
    first, last = map(float, edge.ParameterRange)
    midpoint = (first + last) / 2.0
    point = edge.valueAt(midpoint)
    tangents = edge.tangentAt(midpoint)
    tangent = tangents[0] if isinstance(tangents, tuple) else tangents
    vertices = [vector_record(vertex.Point) for vertex in edge.Vertexes]
    return {
        "edge_index_1_based": index,
        "curve_type": type(edge.Curve).__name__,
        "length_mm": float(edge.Length),
        "vertices_world_mm": vertices,
        "midpoint_world_mm": vector_record(point),
        "midpoint_tangent": vector_record(unit(tangent)),
        "axis_alignment": axis_alignment(tangent, App),
    }


def load_contract(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_text(encoding="utf-8"))
    expected = "cat-head-right-lower-rear-v5-axis-straight-sector-measurement-v3"
    if contract.get("schema_version") != expected:
        raise RuntimeError("unexpected measurement contract schema")
    return contract


def measure(contract_path: Path) -> dict[str, Any]:
    contract = load_contract(contract_path)
    input_record = contract["input"]
    for path_key, hash_key in (
        ("path", "sha256"),
        ("contract_path", "contract_sha256"),
        ("generator_path", "generator_sha256"),
    ):
        path = CAT_HEAD_ROOT / input_record[path_key]
        actual = sha256(path)
        if actual != input_record[hash_key]:
            raise RuntimeError(
                f"hash mismatch for {path_key}: expected "
                f"{input_record[hash_key]}, got {actual}"
            )

    import FreeCAD as App  # type: ignore

    input_path = CAT_HEAD_ROOT / input_record["path"]
    document = App.openDocument(str(input_path))
    try:
        selection = contract["selection"]
        obj = document.getObject(selection["object_internal_name"])
        if obj is None:
            raise RuntimeError("selected object is absent")
        if str(obj.Label) != selection["object_label"]:
            raise RuntimeError(
                f"selected object label mismatch: {obj.Label!r}"
            )
        face_index = int(selection["face_index_1_based"])
        if face_index < 1 or face_index > len(obj.Shape.Faces):
            raise RuntimeError("selected face index is out of range")
        face = obj.Shape.Faces[face_index - 1]
        u_min, u_max, v_min, v_max = map(float, face.ParameterRange)
        normal = unit(face.normalAt((u_min + u_max) / 2.0, (v_min + v_max) / 2.0))
        edges = [
            edge_record(edge, index, App)
            for index, edge in enumerate(face.Edges, start=1)
        ]
        edges_by_axis = sorted(
            edges,
            key=lambda item: (
                item["axis_alignment"]["closest"]["unsigned_angle_deg"],
                -item["length_mm"],
                item["edge_index_1_based"],
            ),
        )
        longest = max(
            edges,
            key=lambda item: (item["length_mm"], -item["edge_index_1_based"]),
        )
        straight_edge = edges_by_axis[0]
        axis_u = unit(App.Vector(*straight_edge["midpoint_tangent"]))
        v2_contract = json.loads(
            (CAT_HEAD_ROOT / input_record["contract_path"]).read_text(
                encoding="utf-8"
            )
        )
        shell_inward = App.Vector(
            *map(float, v2_contract["partition"]["shell_inward_unit"])
        )
        axis_v = shell_inward - axis_u * float(shell_inward.dot(axis_u))
        axis_v = unit(axis_v)
        straight_normal = unit(axis_u.cross(axis_v))
        plane_point = App.Vector(*straight_edge["midpoint_world_mm"])
        selected_face_signed = float(
            (face.CenterOfMass - plane_point).dot(straight_normal)
        )
        if selected_face_signed > 0.0:
            straight_normal = straight_normal * -1.0
            selected_face_signed *= -1.0
        selected_vertex_signed = [
            float((vertex.Point - plane_point).dot(straight_normal))
            for vertex in face.Vertexes
        ]
        bbox = face.BoundBox
        return {
            "schema_version": "cat-head-selected-sector-measurement-v3",
            "status": "PASS__SELECTED_FACE_MEASURED__NO_GEOMETRY_CHANGE",
            "authority": contract["authority"],
            "input": {
                "path": input_record["path"],
                "sha256": input_record["sha256"],
                "document_label": str(document.Label),
            },
            "selection": {
                **selection,
                "resolved_object_internal_name": str(obj.Name),
                "resolved_object_label": str(obj.Label),
                "object_solid_count": len(obj.Shape.Solids),
                "object_face_count": len(obj.Shape.Faces),
            },
            "face": {
                "surface_type": type(face.Surface).__name__,
                "area_mm2": float(face.Area),
                "center_of_mass_world_mm": vector_record(face.CenterOfMass),
                "normal": vector_record(normal),
                "normal_axis_alignment": axis_alignment(normal, App),
                "bbox_minimum_world_mm": [
                    float(bbox.XMin),
                    float(bbox.YMin),
                    float(bbox.ZMin),
                ],
                "bbox_maximum_world_mm": [
                    float(bbox.XMax),
                    float(bbox.YMax),
                    float(bbox.ZMax),
                ],
                "vertices_world_mm": [
                    vector_record(vertex.Point) for vertex in face.Vertexes
                ],
                "edges": edges,
                "edge_closest_to_global_axis": edges_by_axis[0],
                "longest_edge": longest,
            },
            "proposed_straight_local_seam": {
                "point_world_mm": vector_record(plane_point),
                "axis_u_selected_edge_unit": vector_record(axis_u),
                "axis_v_orthogonalized_shell_inward_unit": vector_record(axis_v),
                "normal_toward_cassette_unit": vector_record(straight_normal),
                "selected_face_center_signed_mm": selected_face_signed,
                "selected_face_vertex_signed_mm": selected_vertex_signed,
                "mating_clearance_mm": float(
                    v2_contract["partition"]["mating_clearance_mm"]
                ),
                "construction": "front is the union of the old retained half-space and the new selected-edge retained half-space; rear is the intersection of the old cassette half-space and the new selected-edge cassette half-space"
            },
            "io_trace": {
                "input_saved": False,
                "geometry_created": False,
                "review_saved": False,
                "geometry_export_created": False,
                "production_output_created": False,
            },
        }
    finally:
        App.closeDocument(document.Name)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--contract",
        type=Path,
        default=DEFAULT_CONTRACT,
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    print(json.dumps(measure(args.contract), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
