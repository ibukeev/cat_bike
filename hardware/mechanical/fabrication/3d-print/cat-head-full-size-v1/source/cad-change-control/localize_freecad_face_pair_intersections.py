#!/usr/bin/env python3
"""Read-only pairwise face localization for OCCT self-intersections.

The exact hash-pinned STEP is the diagnostic target. The hash-pinned V17 FCStd
is opened only to classify faulty faces against its saved source owners. No
document is saved and no production geometry is changed or exported.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterator

import FreeCAD as App
import Part

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bop_diagnostics import parse_bop_diagnostics  # noqa: E402
from validate_change_contract import (  # noqa: E402
    find_repository_root,
    load_json,
    sha256_file,
    validate_files,
)


def check_messages(shape) -> list[str]:
    try:
        result = shape.check(True)
        return [str(item) for item in result] if result else []
    except Exception as exc:
        return [str(exc)]


def bbox_dict(shape) -> dict[str, list[float]]:
    box = shape.BoundBox
    return {
        "minimum_mm": [round(box.XMin, 9), round(box.YMin, 9), round(box.ZMin, 9)],
        "maximum_mm": [round(box.XMax, 9), round(box.YMax, 9), round(box.ZMax, 9)],
    }


def vector_tuple(vector) -> list[float]:
    return [round(float(vector.x), 9), round(float(vector.y), 9), round(float(vector.z), 9)]


def boxes_overlap(first, second, tolerance: float = 1e-7) -> bool:
    return not (
        first.XMax < second.XMin - tolerance
        or first.XMin > second.XMax + tolerance
        or first.YMax < second.YMin - tolerance
        or first.YMin > second.YMax + tolerance
        or first.ZMax < second.ZMin - tolerance
        or first.ZMin > second.ZMax + tolerance
    )


def overlapping_face_pairs(faces) -> Iterator[tuple[int, Any, int, Any]]:
    indexed = sorted(
        ((face.BoundBox.XMin, index, face) for index, face in enumerate(faces, start=1)),
        key=lambda item: (item[0], item[1]),
    )
    active: list[tuple[int, Any]] = []
    tolerance = 1e-7
    for x_min, index, face in indexed:
        active = [
            (other_index, other)
            for other_index, other in active
            if other.BoundBox.XMax >= x_min - tolerance
        ]
        for other_index, other in active:
            if boxes_overlap(face.BoundBox, other.BoundBox, tolerance):
                yield other_index, other, index, face
        active.append((index, face))


def vertex_keys(shape) -> set[tuple[float, float, float]]:
    return {
        (
            round(vertex.Point.x, 7),
            round(vertex.Point.y, 7),
            round(vertex.Point.z, 7),
        )
        for vertex in shape.Vertexes
    }


def source_matches(face, source_objects: list[tuple[str, Any]]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for owner, source in source_objects:
        distance = float(face.distToShape(source.Shape)[0])
        if distance > 1e-6:
            continue
        common = face.common(source.Shape)
        matches.append(
            {
                "owner": owner,
                "distance_mm": round(distance, 12),
                "common_area_mm2": round(float(common.Area), 9),
                "common_length_mm": round(float(common.Length), 9),
            }
        )
    matches.sort(
        key=lambda item: (
            item["common_area_mm2"],
            item["common_length_mm"],
            item["owner"],
        ),
        reverse=True,
    )
    return matches


def face_record(index: int, face, source_objects) -> dict[str, Any]:
    return {
        "face": f"Face{index}",
        "area_mm2": round(float(face.Area), 9),
        "center_of_mass_mm": vector_tuple(face.CenterOfMass),
        "bounds": bbox_dict(face),
        "source_owner_candidates": source_matches(face, source_objects),
    }


def load_step(path: Path):
    shape = Part.Shape()
    shape.read(str(path))
    if shape.isNull():
        raise ValueError(f"STEP import produced a null shape: {path}")
    return shape


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    preflight = validate_files(args.manifest, args.contract, verify_files=True)
    if preflight["status"] != "PASS":
        print(json.dumps(preflight, indent=2, sort_keys=True))
        return 1

    root = find_repository_root(args.manifest)
    manifest = load_json(args.manifest)
    contract = load_json(args.contract)
    artifacts = {item["id"]: item for item in manifest["artifacts"]}
    target = artifacts[contract["target_owner"]]
    localization = contract["self_intersection_localization"]
    lineage = artifacts[localization["lineage_artifact_id"]]

    report_path = args.report if args.report.is_absolute() else root / args.report
    output_root = root / contract["output_directory"]
    try:
        report_path.resolve().relative_to(output_root.resolve())
    except ValueError:
        raise ValueError("report path must be inside the contracted output_directory")
    if report_path.exists():
        raise FileExistsError(f"refusing to overwrite existing report: {report_path}")

    exact_shape = load_step(root / target["path"])
    document = App.openDocument(str(root / lineage["path"]))
    try:
        source_objects: list[tuple[str, Any]] = []
        for definition in localization["source_owners"]:
            source = document.getObject(definition["object_name"])
            if source is None or source.Shape.isNull():
                raise ValueError(f"source owner missing: {definition['object_name']!r}")
            source_objects.append((definition["owner"], source))

        global_messages = check_messages(exact_shape)
        global_diagnostics = parse_bop_diagnostics(global_messages)
        faulty_pairs = []
        bbox_candidate_count = 0
        touching_candidate_count = 0
        for first_index, first, second_index, second in overlapping_face_pairs(exact_shape.Faces):
            bbox_candidate_count += 1
            distance = float(first.distToShape(second)[0])
            if distance > 1e-7:
                continue
            touching_candidate_count += 1
            pair_shape = Part.makeCompound([first, second])
            messages = check_messages(pair_shape)
            diagnostics = parse_bop_diagnostics(messages)
            if not diagnostics:
                continue
            common = first.common(second)
            shared_vertices = vertex_keys(first).intersection(vertex_keys(second))
            faulty_pairs.append(
                {
                    "pair": [f"Face{first_index}", f"Face{second_index}"],
                    "diagnostics": diagnostics,
                    "distance_mm": round(distance, 12),
                    "shared_vertex_count": len(shared_vertices),
                    "common_area_mm2": round(float(common.Area), 9),
                    "common_length_mm": round(float(common.Length), 9),
                    "common_bounds": bbox_dict(common) if not common.isNull() else None,
                    "first": face_record(first_index, first, source_objects),
                    "second": face_record(second_index, second, source_objects),
                }
            )

        faulty_pairs.sort(key=lambda item: tuple(item["pair"]))
        result = {
            "schema_version": "1.0",
            "validator": "read-only-freecad-occt-face-pair-localizer-v1",
            "freecad_version": App.Version(),
            "contract_id": contract["contract_id"],
            "status": "LOCALIZED" if faulty_pairs else "NOT_LOCALIZED",
            "geometry_mutated": False,
            "automatic_healing_used": False,
            "source_document_saved": False,
            "target_artifact": {
                "id": contract["target_owner"],
                "path": target["path"],
                "sha256": sha256_file(root / target["path"]),
            },
            "lineage_artifact": {
                "id": localization["lineage_artifact_id"],
                "path": lineage["path"],
                "sha256": sha256_file(root / lineage["path"]),
            },
            "face_count": len(exact_shape.Faces),
            "global_diagnostic_count": len(global_diagnostics),
            "global_diagnostics": global_diagnostics,
            "bbox_candidate_pair_count": bbox_candidate_count,
            "touching_candidate_pair_count": touching_candidate_count,
            "faulty_face_pair_count": len(faulty_pairs),
            "faulty_face_pairs": faulty_pairs,
            "release_holds": contract["release_holds"],
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(
            json.dumps(
                {
                    "status": result["status"],
                    "global_diagnostic_count": result["global_diagnostic_count"],
                    "bbox_candidate_pair_count": bbox_candidate_count,
                    "touching_candidate_pair_count": touching_candidate_count,
                    "faulty_face_pair_count": len(faulty_pairs),
                    "report": str(report_path),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if faulty_pairs else 1
    finally:
        App.closeDocument(document.Name)


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
