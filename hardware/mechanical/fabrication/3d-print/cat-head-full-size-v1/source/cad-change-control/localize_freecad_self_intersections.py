#!/usr/bin/env python3
"""Read-only localization of OCCT self-intersection diagnostics.

The script opens a hash-pinned FCStd lineage document, runs OCCT checks on its
saved stages and on each final subshape, and writes deterministic JSON inside
the contract's generated-report directory. It never saves, heals, refines,
fuses, cuts, moves, or exports geometry.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import FreeCAD as App

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


def source_matches(subshape, source_objects: list[tuple[str, Any]]) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for owner, source in source_objects:
        distance = float(subshape.distToShape(source.Shape)[0])
        if distance > 1e-6:
            continue
        common = subshape.common(source.Shape)
        matches.append(
            {
                "owner": owner,
                "distance_mm": round(distance, 12),
                "common_area_mm2": round(float(common.Area), 9),
                "common_length_mm": round(float(common.Length), 9),
                "common_vertex_count": len(common.Vertexes),
            }
        )
    matches.sort(
        key=lambda item: (
            item["common_area_mm2"],
            item["common_length_mm"],
            item["common_vertex_count"],
            item["owner"],
        ),
        reverse=True,
    )
    return matches


def localize_collection(
    collection,
    subshape_type: str,
    source_objects: list[tuple[str, Any]],
) -> list[dict[str, Any]]:
    localized: list[dict[str, Any]] = []
    for index, subshape in enumerate(collection, start=1):
        messages = check_messages(subshape)
        diagnostics = parse_bop_diagnostics(messages)
        if not diagnostics:
            continue
        record: dict[str, Any] = {
            "subshape": f"{subshape_type}{index}",
            "subshape_type": subshape_type,
            "diagnostics": diagnostics,
            "diagnostic_count": len(diagnostics),
            "bounds": bbox_dict(subshape),
            "center_of_mass_mm": vector_tuple(subshape.CenterOfMass),
            "source_owner_candidates": source_matches(subshape, source_objects),
        }
        if subshape_type == "Face":
            record["area_mm2"] = round(float(subshape.Area), 9)
        elif subshape_type == "Edge":
            record["length_mm"] = round(float(subshape.Length), 9)
        localized.append(record)
    return localized


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
    localization = contract.get("self_intersection_localization", {})
    lineage_id = localization.get("lineage_artifact_id")
    lineage = artifacts.get(lineage_id)
    if lineage is None or lineage.get("format") != "fcstd":
        raise ValueError("localization requires a declared FCStd lineage artifact")

    report_path = args.report if args.report.is_absolute() else root / args.report
    output_root = root / contract["output_directory"]
    try:
        report_path.resolve().relative_to(output_root.resolve())
    except ValueError:
        raise ValueError("report path must be inside the contracted output_directory")
    if report_path.exists():
        raise FileExistsError(f"refusing to overwrite existing report: {report_path}")

    document = App.openDocument(str(root / lineage["path"]))
    try:
        final_name = localization.get("final_object_name")
        final_object = document.getObject(final_name)
        if final_object is None or final_object.Shape.isNull():
            raise ValueError(f"final object missing from lineage document: {final_name!r}")

        source_objects: list[tuple[str, Any]] = []
        for definition in localization.get("source_owners", []):
            source = document.getObject(definition["object_name"])
            if source is None or source.Shape.isNull():
                raise ValueError(f"source owner missing: {definition['object_name']!r}")
            source_objects.append((definition["owner"], source))

        stage_reports: dict[str, Any] = {}
        for name in localization.get("stage_object_names", []):
            stage = document.getObject(name)
            if stage is None or stage.Shape.isNull():
                raise ValueError(f"stage object missing: {name!r}")
            messages = check_messages(stage.Shape)
            stage_reports[name] = {
                "face_count": len(stage.Shape.Faces),
                "edge_count": len(stage.Shape.Edges),
                "vertex_count": len(stage.Shape.Vertexes),
                "volume_mm3": round(float(stage.Shape.Volume), 9),
                "diagnostics": parse_bop_diagnostics(messages),
                "raw_check_messages": messages,
            }

        final_messages = check_messages(final_object.Shape)
        global_diagnostics = parse_bop_diagnostics(final_messages)
        localized = []
        localized.extend(localize_collection(final_object.Shape.Faces, "Face", source_objects))
        localized.extend(localize_collection(final_object.Shape.Edges, "Edge", source_objects))
        localized.extend(localize_collection(final_object.Shape.Vertexes, "Vertex", source_objects))
        localized.sort(key=lambda item: (item["subshape_type"], item["subshape"]))

        result = {
            "schema_version": "1.0",
            "validator": "read-only-freecad-occt-self-intersection-localizer-v1",
            "freecad_version": App.Version(),
            "contract_id": contract["contract_id"],
            "status": "LOCALIZED" if localized else "NOT_LOCALIZED",
            "geometry_mutated": False,
            "automatic_healing_used": False,
            "source_document_saved": False,
            "lineage_artifact": {
                "id": lineage_id,
                "path": lineage["path"],
                "sha256": sha256_file(root / lineage["path"]),
            },
            "final_object": final_name,
            "global_diagnostic_count": len(global_diagnostics),
            "global_diagnostics": global_diagnostics,
            "global_raw_check_messages": final_messages,
            "localized_subshape_count": len(localized),
            "localized_diagnostic_count": sum(
                item["diagnostic_count"] for item in localized
            ),
            "localized_subshapes": localized,
            "stage_reports": stage_reports,
            "release_holds": contract["release_holds"],
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if localized else 1
    finally:
        App.closeDocument(document.Name)


if __name__ == "__main__" or App.ConfigGet("RunMode") == "Script":
    raise SystemExit(main())
