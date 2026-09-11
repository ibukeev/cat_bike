#!/usr/bin/env python3
"""Build the approved V5 right lower/rear repartition from canonical owners.

Feasibility mode is no-save. Review mode saves only a non-authoritative FCStd
and validation JSON; it does not export STL/3MF/G-code or promote production.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
CONTRACT_PATH = HERE / "contract.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schema_version") != "cat-head-right-lower-rear-v5-production-repartition-review-v1":
        raise RuntimeError("unexpected contract schema")
    return contract


def require_hash(project_root: Path, item: dict[str, Any]) -> Path:
    path = (project_root / item["path"]).resolve()
    actual = sha256(path)
    if actual != item["sha256"]:
        raise RuntimeError(f"hash mismatch: {path}: {actual}")
    return path


def metrics(shape: Any) -> dict[str, Any]:
    return {
        "shape_type": shape.ShapeType,
        "solid_count": len(shape.Solids),
        "shell_count": len(shape.Shells),
        "face_count": len(shape.Faces),
        "volume_mm3": float(shape.Volume),
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
    }


def signed_range(shape: Any, point: Any, normal: Any) -> tuple[float, float]:
    values = [float((vertex.Point - point).dot(normal)) for vertex in shape.Vertexes]
    return min(values), max(values)


def curtain_mask(Part: Any, point: Any, axis_u: Any, axis_v: Any, normal: Any, side: int, gap: float) -> Any:
    span = 500.0
    surface_point = point + normal * (side * gap / 2.0)
    corners = [
        surface_point - axis_u * span - axis_v * span,
        surface_point + axis_u * span - axis_v * span,
        surface_point + axis_u * span + axis_v * span,
        surface_point - axis_u * span + axis_v * span,
    ]
    wire = Part.makePolygon([*corners, corners[0]])
    face = Part.Face(wire)
    mask = face.extrude(normal * (side * span * 2.0)).removeSplitter()
    if mask.isNull() or not mask.isValid() or not mask.isClosed():
        raise RuntimeError(f"failed to construct side mask {side}")
    return mask


def build() -> tuple[dict[str, Any], list[tuple[str, Any]], list[tuple[str, Any]], Any]:
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    contract = load_contract()
    canonical_path = require_hash(PROJECT_ROOT, contract["inputs"]["relieved_shell_reference"])
    v8_path = require_hash(PROJECT_ROOT, contract["inputs"]["user_manual_v8_reference"])
    curtain = contract["approved_v5_ownership"]["right_partition_curtain"]
    point = App.Vector(*map(float, curtain["seam_midpoint_mm"]))
    axis_u = App.Vector(*map(float, curtain["seam_direction_unit"]))
    axis_v = App.Vector(*map(float, curtain["shell_inward_unit"]))
    normal = App.Vector(*map(float, curtain["normal_toward_cassette_unit"]))
    axis_u.normalize(); axis_v.normalize(); normal.normalize()
    if abs(float(axis_u.dot(axis_v))) > 1.0e-5 or abs(float(axis_u.dot(normal))) > 1.0e-5 or abs(float(axis_v.dot(normal))) > 1.0e-5:
        raise RuntimeError("partition curtain basis is not orthonormal")
    gap = float(contract["right_reinforcement"]["mating_clearance_mm"])
    retained_mask = curtain_mask(Part, point, axis_u, axis_v, normal, -1, gap)
    cassette_mask = curtain_mask(Part, point, axis_u, axis_v, normal, +1, gap)

    canonical = App.openDocument(str(canonical_path))
    v8 = App.openDocument(str(v8_path))
    try:
        lower_main = canonical.getObject("FROZEN_RIGHT_LOWER_MAIN_V34")
        lower_mesh = canonical.getObject("FROZEN_RIGHT_LOWER_COMPONENTS_002_060_V34")
        manual_flange = next((obj for obj in v8.Objects if obj.Label == "HEAD_BOTTOM_FLANGE"), None)
        if lower_main is None or lower_mesh is None or manual_flange is None:
            raise RuntimeError("required canonical lower owners or manual flange missing")

        converted = Part.Shape()
        converted.makeShapeFromMesh(lower_mesh.Mesh.Topology, 0.01)
        sources: list[tuple[str, Any]] = [("component_001_relief_main", lower_main.Shape.copy())]
        for index, shell in enumerate(converted.Shells, start=2):
            solid = Part.makeSolid(shell)
            if not solid.isValid() or not solid.isClosed() or len(solid.Solids) != 1:
                raise RuntimeError(f"component {index:03d} conversion is not one valid closed solid")
            sources.append((f"component_{index:03d}", solid))
        if len(sources) != 60:
            raise RuntimeError(f"expected 60 canonical lower owners, found {len(sources)}")

        retained: list[tuple[str, Any]] = []
        cassette: list[tuple[str, Any]] = []
        split_records = []
        source_total = 0.0
        candidate_total = 0.0
        for name, shape in sources:
            source_total += float(shape.Volume)
            minimum, maximum = signed_range(shape, point, normal)
            if maximum < -gap / 2.0:
                retained.append((name, shape))
                candidate_total += float(shape.Volume)
                continue
            if minimum > gap / 2.0:
                cassette.append((name, shape))
                candidate_total += float(shape.Volume)
                continue
            retained_piece = shape.common(retained_mask).removeSplitter()
            cassette_piece = shape.common(cassette_mask).removeSplitter()
            if retained_piece.isNull() or cassette_piece.isNull():
                raise RuntimeError(f"crossing owner {name} did not produce both complementary pieces")
            for owner, piece in (("retained", retained_piece), ("cassette", cassette_piece)):
                if not piece.isValid() or not piece.isClosed() or len(piece.Solids) < 1:
                    raise RuntimeError(f"{name} {owner} split is not valid/closed")
            retained.append((f"{name}__retained", retained_piece))
            cassette.append((f"{name}__cassette", cassette_piece))
            candidate_total += float(retained_piece.Volume + cassette_piece.Volume)
            split_records.append({
                "source": name,
                "source_volume_mm3": float(shape.Volume),
                "retained_volume_mm3": float(retained_piece.Volume),
                "cassette_volume_mm3": float(cassette_piece.Volume),
                "gap_removed_volume_mm3": float(shape.Volume - retained_piece.Volume - cassette_piece.Volume),
            })

        component_007_index = next(index for index, (name, _shape) in enumerate(retained) if name == "component_007")
        component_007 = retained[component_007_index][1]
        common = component_007.common(manual_flange.Shape)
        common_volume = 0.0 if common.isNull() else float(common.Volume)
        if common_volume < 1.0:
            raise RuntimeError(f"manual flange root overlap too small: {common_volume}")
        fused = component_007.fuse(manual_flange.Shape).removeSplitter()
        if not fused.isValid() or not fused.isClosed() or len(fused.Solids) != 1:
            raise RuntimeError("manual bottom flange did not fuse into one valid retained solid")
        retained[component_007_index] = ("component_007__WITH_USER_HEAD_BOTTOM_FLANGE", fused)
        candidate_total += float(fused.Volume - component_007.Volume)

        retained_compound = Part.makeCompound([shape for _name, shape in retained])
        cassette_compound = Part.makeCompound([shape for _name, shape in cassette])
        result = {
            "schema_version": "cat-head-right-lower-rear-v5-production-repartition-feasibility-v1",
            "status": "PASS__REVIEW_GEOMETRY_READY__NOT_PRINT_RELEASED",
            "authority": contract["authority"],
            "canonical_sha256": contract["inputs"]["relieved_shell_reference"]["sha256"],
            "user_v8_sha256": contract["inputs"]["user_manual_v8_reference"]["sha256"],
            "mating_clearance_mm": gap,
            "canonical_lower_owner_count": len(sources),
            "retained_piece_count": len(retained),
            "cassette_piece_count": len(cassette),
            "crossing_split_count": len(split_records),
            "split_records": split_records,
            "manual_flange_root_owner": "component_007",
            "manual_flange_root_overlap_mm3": common_volume,
            "manual_flange_fused_one_solid": True,
            "source_total_volume_mm3": source_total,
            "candidate_total_volume_including_manual_flange_mm3": candidate_total,
            "retained_compound": metrics(retained_compound),
            "cassette_compound": metrics(cassette_compound),
            "review_hold": "Compounds preserve all canonical owners and the approved cut for visual review. Final one-body Boolean fusion and print release remain separate gates.",
            "io_trace": {"source_saved": False, "review_saved": False, "geometry_export_created": False, "production_output_created": False},
        }
        seam_marker = Part.makeLine(
            App.Vector(126.93900299072266, 200.65199279785156, 109.98899841308594),
            App.Vector(88.94550323486328, 188.3385009765625, 47.872501373291016),
        )
        return result, retained, cassette, seam_marker
    finally:
        App.closeDocument(v8.Name)
        App.closeDocument(canonical.Name)


def save_review(result: dict[str, Any], retained: list[tuple[str, Any]], cassette: list[tuple[str, Any]], seam_marker: Any) -> tuple[Path, Path]:
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    contract = load_contract()
    output_dir = (PROJECT_ROOT / contract["outputs"]["directory"]).resolve()
    if output_dir.exists():
        raise RuntimeError(f"review output already exists: {output_dir}")
    output_dir.mkdir(parents=True)
    document = App.newDocument("RIGHT_LOWER_REAR_V5_PRODUCTION_REPARTITION_REVIEW_ONLY_V1")
    try:
        document.addProperty if False else None
        retained_group = document.addObject("App::DocumentObjectGroup", "RETAINED_FRONT_LOWER_OWNERS")
        cassette_group = document.addObject("App::DocumentObjectGroup", "REAR_CASSETTE_LOWER_OWNERS")
        retained_objects = []
        cassette_objects = []
        for index, (name, shape) in enumerate(retained, start=1):
            obj = document.addObject("Part::Feature", f"RET_{index:03d}")
            obj.Label = f"RETAINED FRONT — {name}"
            obj.Shape = shape
            obj.addProperty("App::PropertyString", "Authority", "Review Control")
            obj.Authority = contract["authority"]
            retained_group.addObject(obj); retained_objects.append(obj)
        for index, (name, shape) in enumerate(cassette, start=1):
            obj = document.addObject("Part::Feature", f"CAS_{index:03d}")
            obj.Label = f"REAR CASSETTE — {name}"
            obj.Shape = shape
            obj.addProperty("App::PropertyString", "Authority", "Review Control")
            obj.Authority = contract["authority"]
            cassette_group.addObject(obj); cassette_objects.append(obj)
        retained_summary = document.addObject("Part::Feature", "RETAINED_FRONT_COMPOUND")
        retained_summary.Label = "PROPOSED — RIGHT RETAINED LOWER FRONT + USER BOTTOM FLANGE"
        retained_summary.Shape = Part.makeCompound([obj.Shape for obj in retained_objects])
        cassette_summary = document.addObject("Part::Feature", "REAR_CASSETTE_COMPOUND")
        cassette_summary.Label = "PROPOSED — RIGHT REAR CASSETTE LOWER SECTION"
        cassette_summary.Shape = Part.makeCompound([obj.Shape for obj in cassette_objects])
        marker = document.addObject("Part::Feature", "APPROVED_V5_DIAGONAL_SEAM")
        marker.Label = "REFERENCE — APPROVED V5 DIAGONAL SEAM"
        marker.Shape = seam_marker
        for obj in [*retained_objects, *cassette_objects]:
            if getattr(obj, "ViewObject", None) is not None:
                obj.ViewObject.Visibility = False
        if getattr(retained_summary, "ViewObject", None) is not None:
            retained_summary.ViewObject.ShapeColor = (0.25, 0.65, 0.95)
            retained_summary.ViewObject.Transparency = 0
        if getattr(cassette_summary, "ViewObject", None) is not None:
            cassette_summary.ViewObject.ShapeColor = (1.0, 0.48, 0.12)
            cassette_summary.ViewObject.Transparency = 12
        if getattr(marker, "ViewObject", None) is not None:
            marker.ViewObject.LineColor = (1.0, 1.0, 0.0)
            marker.ViewObject.LineWidth = 5.0
        document.recompute()
        fcstd = output_dir / contract["outputs"]["fcstd"]
        document.saveAs(str(fcstd))
    finally:
        App.closeDocument(document.Name)
    result["io_trace"]["review_saved"] = True
    result["generated_fcstd"] = str(fcstd.relative_to(PROJECT_ROOT))
    result["generated_fcstd_sha256"] = sha256(fcstd)
    validation = output_dir / contract["outputs"]["validation"]
    validation.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return fcstd, validation


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("feasibility", "review"), required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    result, retained, cassette, seam_marker = build()
    if args.mode == "feasibility":
        if args.report is None or not str(args.report.resolve()).startswith("/tmp/"):
            raise RuntimeError("feasibility requires a /tmp report")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["status"], "retained": len(retained), "cassette": len(cassette), "crossing": result["crossing_split_count"]}, sort_keys=True))
        return 0
    fcstd, validation = save_review(result, retained, cassette, seam_marker)
    print(json.dumps({"status": result["status"], "fcstd": str(fcstd), "validation": str(validation)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
