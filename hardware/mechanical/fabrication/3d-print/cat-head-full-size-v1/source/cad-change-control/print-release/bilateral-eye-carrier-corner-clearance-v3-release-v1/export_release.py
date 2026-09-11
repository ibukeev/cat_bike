#!/usr/bin/env python3
"""Create the user-approved bilateral V3 eye print release.

The approved right-side BRep is reconstructed from its pinned generator.  The
left side is an exact X=0 mirror.  Preflight writes only a JSON report under
/tmp; release stages two FCStd files and six independent STLs under /tmp and
copies them into a fresh FINAL_PRINT_SET directory only after every gate passes.
No 3MF or G-code is created.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
REPOSITORY_ROOT = PROJECT_ROOT.parents[4]
CONTRACT_PATH = HERE / "contract.json"
SCHEMA = "cat-head-bilateral-eye-corner-clearance-print-release-v1"
PART_IDS = ("carrier", "lens", "rear_plate")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def project_path(value: str) -> Path:
    path = (PROJECT_ROOT / value).resolve()
    path.relative_to(PROJECT_ROOT.resolve())
    return path


def pinned_path(item: dict[str, Any]) -> Path:
    root = REPOSITORY_ROOT if item.get("root") == "repository" else PROJECT_ROOT
    path = (root / str(item["path"])).resolve()
    path.relative_to(root.resolve())
    return path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import pinned module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_contract() -> dict[str, Any]:
    contract = load_json(CONTRACT_PATH)
    if contract.get("schema_version") != SCHEMA:
        raise RuntimeError("unexpected print-release contract schema")
    return contract


def verify_pins(contract: dict[str, Any]) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for namespace in ("inputs", "tooling"):
        for key, item in contract[namespace].items():
            expected = str(item["sha256"])
            if expected.startswith("__"):
                raise RuntimeError(f"unresolved hash pin: {namespace}.{key}")
            path = pinned_path(item)
            actual = sha256(path)
            if actual != expected:
                raise RuntimeError(
                    f"hash mismatch for {namespace}.{key}: {actual} != {expected}"
                )
            records[f"{namespace}.{key}"] = {
                "path": str(item["path"]), "sha256": actual,
            }
    return records


def topology_counts(shape: Any) -> dict[str, int]:
    return {
        "vertices": len(shape.Vertexes), "edges": len(shape.Edges),
        "wires": len(shape.Wires), "faces": len(shape.Faces),
        "shells": len(shape.Shells), "solids": len(shape.Solids),
    }


def bounds(shape: Any) -> list[float]:
    box = shape.BoundBox
    return [
        float(box.XMin), float(box.YMin), float(box.ZMin),
        float(box.XMax), float(box.YMax), float(box.ZMax),
    ]


def expected_mirrored_bounds(values: Sequence[float]) -> list[float]:
    x0, y0, z0, x1, y1, z1 = map(float, values)
    return [-x1, y0, z0, -x0, y1, z1]


def maximum_coordinate_error(first: Sequence[float], second: Sequence[float]) -> float:
    return max((abs(float(a) - float(b)) for a, b in zip(first, second)), default=0.0)


def vertex_hausdorff_error(right: Any, left: Any) -> float:
    expected = [
        (-float(vertex.Point.x), float(vertex.Point.y), float(vertex.Point.z))
        for vertex in right.Vertexes
    ]
    actual = [
        (float(vertex.Point.x), float(vertex.Point.y), float(vertex.Point.z))
        for vertex in left.Vertexes
    ]
    if len(expected) != len(actual):
        return math.inf

    def directed(source: Sequence[tuple[float, float, float]],
                 target: Sequence[tuple[float, float, float]]) -> float:
        return max(
            min(math.dist(point, candidate) for candidate in target)
            for point in source
        ) if source else 0.0

    return max(directed(expected, actual), directed(actual, expected))


def mirror_x0(shape: Any, App: Any) -> Any:
    mirrored = shape.copy()
    returned = mirrored.mirror(App.Vector(0.0, 0.0, 0.0), App.Vector(1.0, 0.0, 0.0))
    if returned is not None:
        mirrored = returned
    if mirrored is None or mirrored.isNull():
        raise RuntimeError("X=0 mirror returned a null shape")
    return mirrored.removeSplitter()


def shape_record(shape: Any) -> dict[str, Any]:
    messages: list[str] = []
    try:
        raw = shape.check(True)
        if raw:
            messages = [str(item) for item in raw]
    except Exception as error:  # fail closed on deep OCCT diagnostic exceptions
        messages = [f"{type(error).__name__}: {error}"]
    return {
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids),
        "volume_mm3": float(shape.Volume),
        "topology": topology_counts(shape),
        "bounds_mm": bounds(shape),
        "deep_check_messages": messages,
    }


def mesh_record(shape: Any, contract: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    mesh_spec = contract["mesh"]
    mesh = context["MeshPart"].meshFromShape(
        Shape=shape,
        LinearDeflection=float(mesh_spec["linear_deflection_mm"]),
        AngularDeflection=float(mesh_spec["angular_deflection_rad"]),
        Relative=False,
    )
    record = context["mesh_checker"].mesh_topology(mesh)
    record["clean"] = bool(context["mesh_checker"].clean_manifold_mesh(record))
    return record


def enforce_clean_mesh(record: dict[str, Any], label: str) -> None:
    if not bool(record.get("clean")):
        raise RuntimeError(f"{label} mesh is not clean: {record}")


def prepare() -> dict[str, Any]:
    contract = load_contract()
    pins = verify_pins(contract)
    validation = load_json(project_path(contract["inputs"]["approved_v3_validation"]["path"]))
    if validation.get("failed_checks") != []:
        raise RuntimeError("approved V3 validation contains failed checks")
    if validation.get("review_fcstd_sha256") != contract["inputs"]["approved_v3_review_fcstd"]["sha256"]:
        raise RuntimeError("approved V3 review FCStd pin disagrees with validation")
    mirror_contract = load_json(project_path(contract["inputs"]["approved_x0_mirror_contract"]["path"]))
    if mirror_contract.get("status") != "VISUALLY_APPROVED_AND_PROMOTED_2026-08-13":
        raise RuntimeError("bilateral X=0 mirror datum is not approved")
    if mirror_contract.get("mirror_datum") != {"plane": "YZ", "equation": "X=0"}:
        raise RuntimeError("unexpected bilateral mirror datum")

    v3 = load_module(
        project_path(contract["inputs"]["approved_v3_generator"]["path"]),
        "_approved_v3_eye_repair_for_print_release",
    )
    context = v3.prepare()
    v3.construct(context)
    result = v3.evaluate(context)
    if result.get("failed_checks") != [] or result.get("status") != "FEASIBILITY_PASS__V3_REVIEW_ALLOWED":
        raise RuntimeError(f"approved V3 reconstruction no longer passes: {result.get('failed_checks')}")
    right = {
        "carrier": context["candidate"].copy(),
        "lens": context["final_shapes"]["lens"].copy(),
        "rear_plate": context["final_shapes"]["rear_plate"].copy(),
    }
    left = {key: mirror_x0(value, context["App"]) for key, value in right.items()}
    return {
        "contract": contract, "pins": pins, "validation": validation,
        "mirror_contract": mirror_contract, "v3": v3, "v3_context": context,
        "v3_result": result, "right": right, "left": left,
    }


def in_memory_document_check(bundle: dict[str, Any]) -> None:
    App = bundle["v3_context"]["App"]
    for side in ("right", "left"):
        doc = App.newDocument(f"Disposable{side.title()}EyePrintRelease")
        try:
            for part_id in PART_IDS:
                obj = doc.addObject("Part::Feature", f"{side.upper()}_{part_id.upper()}_PRINT")
                obj.Shape = bundle[side][part_id].copy()
                obj.addProperty("App::PropertyString", "Authority", "PrintRelease")
                obj.Authority = "DISPOSABLE_IN_MEMORY__NOT_SAVED"
            doc.recompute()
            for part_id in PART_IDS:
                obj = doc.getObject(f"{side.upper()}_{part_id.upper()}_PRINT")
                if obj is None or obj.Shape.isNull() or len(obj.Shape.Solids) != 1:
                    raise RuntimeError(f"in-memory assignment failed: {side}.{part_id}")
        finally:
            App.closeDocument(doc.Name)


def evaluate(bundle: dict[str, Any]) -> dict[str, Any]:
    contract = bundle["contract"]
    shape_records: dict[str, dict[str, Any]] = {"right": {}, "left": {}}
    mesh_records: dict[str, dict[str, Any]] = {"right": {}, "left": {}}
    mirror_records: dict[str, dict[str, Any]] = {}
    volume_tolerance = float(contract["mirror"]["required_volume_tolerance_mm3"])
    bounds_tolerance = float(contract["mirror"]["required_bounds_tolerance_mm"])
    for side in ("right", "left"):
        for part_id in PART_IDS:
            shape_records[side][part_id] = shape_record(bundle[side][part_id])
            mesh_records[side][part_id] = mesh_record(
                bundle[side][part_id], contract, bundle["v3_context"]
            )
    for part_id in PART_IDS:
        right_shape = bundle["right"][part_id]
        left_shape = bundle["left"][part_id]
        mirror_records[part_id] = {
            "topology_matches": topology_counts(right_shape) == topology_counts(left_shape),
            "volume_difference_mm3": abs(float(right_shape.Volume) - float(left_shape.Volume)),
            "bounds_error_mm": maximum_coordinate_error(
                expected_mirrored_bounds(bounds(right_shape)), bounds(left_shape)
            ),
            "vertex_hausdorff_error_mm": vertex_hausdorff_error(right_shape, left_shape),
        }

    all_shape_clean = all(
        record["valid"] and record["closed"] and record["solid_count"] == 1
        and not record["deep_check_messages"]
        for side in shape_records.values() for record in side.values()
    )
    all_mesh_clean = all(
        bool(record["clean"])
        for side in mesh_records.values() for record in side.values()
    )
    mirrors_exact = all(
        record["topology_matches"]
        and record["volume_difference_mm3"] <= volume_tolerance
        and record["bounds_error_mm"] <= bounds_tolerance
        and record["vertex_hausdorff_error_mm"] <= bounds_tolerance
        for record in mirror_records.values()
    )
    checks = {
        "approved_v3_validation_has_zero_failed_checks": bundle["validation"].get("failed_checks") == [],
        "approved_v3_reconstruction_passes_all_original_gates": bundle["v3_result"].get("failed_checks") == [],
        "all_six_breps_are_valid_closed_deep_clean_single_solids": all_shape_clean,
        "all_six_generated_meshes_are_clean_closed_manifold_single_components": all_mesh_clean,
        "all_three_left_parts_are_exact_x0_mirrors": mirrors_exact,
        "output_directory_is_fresh": not project_path(contract["outputs"]["directory"]).exists(),
        "release_contains_no_3mf_or_gcode_names": all(
            not str(value).lower().endswith((".3mf", ".gcode"))
            for side in ("right", "left")
            for value in contract["outputs"][side].values()
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema_version": "cat-head-bilateral-eye-corner-clearance-preflight-v1",
        "status": "PREFLIGHT_PASS__BILATERAL_PRINT_RELEASE_ALLOWED" if not failed else "PREFLIGHT_FAIL__NO_PRINT_OUTPUT",
        "authority": contract["authority"],
        "checks": checks, "failed_checks": failed,
        "right_and_left_shapes": shape_records,
        "right_and_left_meshes": mesh_records,
        "mirror_evidence": mirror_records,
        "v3_repair_measurements": {
            "minimum_added_material_shell_clearance_mm": bundle["v3_result"]["measurements"]["minimum_new_material_to_any_shell_clearance_mm"],
            "source_carrier_removed_mm3": bundle["v3_result"]["measurements"]["source_removed_mm3"],
            "manual_flange_missing_mm3": bundle["v3_result"]["measurements"]["manual_flange_missing_mm3"],
            "structural_backing_missing_mm3": bundle["v3_result"]["measurements"]["v2_structural_backing_missing_mm3"],
        },
        "pins": {
            "contract_sha256": sha256(CONTRACT_PATH),
            "exporter_sha256": sha256(Path(__file__)),
            "verified": bundle["pins"],
        },
        "io_trace": {
            "in_memory_documents_checked": False,
            "fcstd_created": False, "stl_created": False,
            "three_mf_created": False, "gcode_created": False,
            "output_directory_created": False,
        },
    }


def add_print_part(doc: Any, name: str, label: str, shape: Any,
                   authority: str, color: tuple[float, float, float],
                   transparency: int = 0) -> Any:
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape.copy()
    obj.addProperty("App::PropertyString", "Authority", "PrintRelease")
    obj.Authority = authority
    obj.addProperty("App::PropertyString", "SourceRepair", "PrintRelease")
    obj.SourceRepair = "APPROVED_V3_CORNER_CLEARANCE_STRUCTURAL_REPAIR"
    view = getattr(obj, "ViewObject", None)
    if view is not None:
        view.ShapeColor = color
        view.Transparency = transparency
    return obj


def create_side_fcstd(bundle: dict[str, Any], side: str, destination: Path) -> dict[str, str]:
    App = bundle["v3_context"]["App"]
    doc = App.newDocument(f"{side.title()}EyeV3CornerRepairPrintModulesV1")
    names = {
        "carrier": f"{side.upper()}_EYE_CARRIER_V3_CORNER_REPAIR_PRINT",
        "lens": f"{side.upper()}_EYE_TRANSLUCENT_LENS_WITH_SIDE_FLANGES_PRINT",
        "rear_plate": f"{side.upper()}_EYE_REMOVABLE_LED_REAR_PLATE_PRINT",
    }
    try:
        add_print_part(doc, names["carrier"], f"{side.upper()} EYE — V3 REPAIRED CARRIER — PRINT", bundle[side]["carrier"], bundle["contract"]["authority"], (0.18, 0.18, 0.20))
        add_print_part(doc, names["lens"], f"{side.upper()} EYE — TRANSLUCENT LENS — PRINT", bundle[side]["lens"], bundle["contract"]["authority"], (0.38, 0.88, 0.96), 45)
        add_print_part(doc, names["rear_plate"], f"{side.upper()} EYE — REMOVABLE LED REAR PLATE — PRINT", bundle[side]["rear_plate"], bundle["contract"]["authority"], (0.12, 0.28, 0.14))
        doc.addObject("App::FeaturePython", "PRINT_RELEASE_METADATA")
        meta = doc.getObject("PRINT_RELEASE_METADATA")
        meta.addProperty("App::PropertyString", "Authority", "PrintRelease")
        meta.Authority = bundle["contract"]["authority"]
        meta.addProperty("App::PropertyString", "MirrorDatum", "PrintRelease")
        meta.MirrorDatum = "RIGHT: approved V3; LEFT: exact X=0 / YZ mirror"
        meta.addProperty("App::PropertyString", "Slicing", "PrintRelease")
        meta.Slicing = "NOT INCLUDED — USER WILL SLICE"
        doc.recompute()
        destination.parent.mkdir(parents=True, exist_ok=True)
        doc.saveAs(str(destination))
    finally:
        App.closeDocument(doc.Name)
    return names


def verify_reopened_fcstd(bundle: dict[str, Any], side: str, path: Path,
                          names: dict[str, str]) -> dict[str, Any]:
    App = bundle["v3_context"]["App"]
    doc = App.openDocument(str(path))
    records: dict[str, Any] = {}
    try:
        for part_id in PART_IDS:
            obj = doc.getObject(names[part_id])
            if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
                raise RuntimeError(f"reopened FCStd missing {side}.{part_id}")
            record = shape_record(obj.Shape)
            original = shape_record(bundle[side][part_id])
            if not (record["valid"] and record["closed"] and record["solid_count"] == 1):
                raise RuntimeError(f"reopened FCStd invalid {side}.{part_id}: {record}")
            if abs(record["volume_mm3"] - original["volume_mm3"]) > 1.0e-5:
                raise RuntimeError(f"reopened FCStd volume changed for {side}.{part_id}")
            records[part_id] = record
    finally:
        App.closeDocument(doc.Name)
    return records


def write_stl(bundle: dict[str, Any], shape: Any, destination: Path,
              label: str) -> dict[str, Any]:
    mesh_spec = bundle["contract"]["mesh"]
    mesh = bundle["v3_context"]["MeshPart"].meshFromShape(
        Shape=shape,
        LinearDeflection=float(mesh_spec["linear_deflection_mm"]),
        AngularDeflection=float(mesh_spec["angular_deflection_rad"]),
        Relative=False,
    )
    generated = bundle["v3_context"]["mesh_checker"].mesh_topology(mesh)
    generated["clean"] = bundle["v3_context"]["mesh_checker"].clean_manifold_mesh(generated)
    enforce_clean_mesh(generated, label)
    mesh.write(str(destination))
    Mesh = __import__("Mesh")
    reloaded_mesh = Mesh.Mesh(str(destination))
    reloaded = bundle["v3_context"]["mesh_checker"].mesh_topology(reloaded_mesh)
    reloaded["clean"] = bundle["v3_context"]["mesh_checker"].clean_manifold_mesh(reloaded)
    enforce_clean_mesh(reloaded, label + " reloaded STL")
    return {"generated": generated, "reloaded": reloaded, "sha256": sha256(destination)}


def release_readme() -> str:
    return """# Bilateral eye modules — V3 corner-repair print release V1

This is the current real-print eye release. It replaces the physically failed
V1 carrier STLs. Do not print the old V1 carrier files.

Each side contains one FreeCAD assembly and three independent source-coordinate
STLs: repaired carrier (including the manual mounting flange), translucent lens,
and removable LED rear plate. The left parts are exact X=0 mirrors of the approved
right parts.

No 3MF or G-code is included. Slice each STL using the actual printer/material
profile. Print the structural carrier and rear plate in opaque structural
filament; print the lens separately in natural/translucent PETG. The lens and rear
plate geometry are unchanged from the previously approved eye design.
"""


def write_release(bundle: dict[str, Any], preflight: dict[str, Any],
                  preflight_path: Path, preflight_sha: str) -> Path:
    contract = bundle["contract"]
    output = project_path(contract["outputs"]["directory"])
    if output.exists():
        raise FileExistsError(f"refusing to overwrite print release: {output}")
    with tempfile.TemporaryDirectory(prefix="bilateral-eye-v3-print-release-") as temporary:
        staging = Path(temporary) / "release"
        staging.mkdir()
        file_records: dict[str, Any] = {"right": {}, "left": {}}
        fcstd_records: dict[str, Any] = {}
        for side in ("right", "left"):
            spec = contract["outputs"][side]
            side_dir = staging / spec["directory"]
            side_dir.mkdir()
            fcstd = side_dir / spec["fcstd"]
            names = create_side_fcstd(bundle, side, fcstd)
            fcstd_records[side] = {
                "path": str(fcstd.relative_to(staging)),
                "sha256": sha256(fcstd),
                "objects": names,
                "reopened": verify_reopened_fcstd(bundle, side, fcstd, names),
            }
            for part_id, key in (
                ("carrier", "carrier_stl"), ("lens", "lens_stl"),
                ("rear_plate", "rear_plate_stl"),
            ):
                destination = side_dir / spec[key]
                metrics = write_stl(bundle, bundle[side][part_id], destination, f"{side}.{part_id}")
                file_records[side][part_id] = {
                    "path": str(destination.relative_to(staging)), **metrics,
                }

        readme = staging / contract["outputs"]["readme"]
        readme.write_text(release_readme(), encoding="utf-8")
        manifest = {
            "schema_version": "cat-head-bilateral-eye-v3-print-release-manifest-v1",
            "status": "PRINT_RELEASE_PASS__RIGHT_AND_LEFT_FCSTD_AND_STL_READY",
            "authority": contract["authority"],
            "user_will_slice": True,
            "gcode_created": False, "three_mf_created": False,
            "preflight_report_path": str(preflight_path),
            "preflight_report_sha256": preflight_sha,
            "preflight_checks": preflight["checks"],
            "contract_sha256": sha256(CONTRACT_PATH),
            "exporter_sha256": sha256(Path(__file__)),
            "source_pins": bundle["pins"],
            "fcstd": fcstd_records, "stl": file_records,
        }
        manifest_path = staging / contract["outputs"]["manifest"]
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        checksum_entries = []
        for path in sorted(item for item in staging.rglob("*") if item.is_file()):
            if path.name == contract["outputs"]["checksums"]:
                continue
            checksum_entries.append(f"{sha256(path)}  {path.relative_to(staging)}")
        (staging / contract["outputs"]["checksums"]).write_text(
            "\n".join(checksum_entries) + "\n", encoding="utf-8"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(staging, output)
    return output


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "release"), required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--preflight-report", type=Path)
    parser.add_argument("--preflight-sha256")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    started = time.monotonic()
    bundle = prepare()
    result = evaluate(bundle)
    if result["status"].startswith("PREFLIGHT_PASS"):
        in_memory_document_check(bundle)
        result["io_trace"]["in_memory_documents_checked"] = True
    result["elapsed_seconds"] = time.monotonic() - started
    if args.mode == "preflight":
        if args.report is None:
            raise RuntimeError("preflight requires --report")
        report = args.report.resolve()
        if not str(report).startswith("/tmp/"):
            raise RuntimeError("preflight report must remain under /tmp")
        if report.exists():
            raise FileExistsError(f"refusing to overwrite preflight report: {report}")
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(result["status"])
        return 0 if result["status"].startswith("PREFLIGHT_PASS") else 1

    if not result["status"].startswith("PREFLIGHT_PASS"):
        print(json.dumps(result, indent=2, sort_keys=True))
        return 1
    if args.preflight_report is None or not args.preflight_sha256:
        raise RuntimeError("release requires --preflight-report and --preflight-sha256")
    preflight_path = args.preflight_report.resolve()
    if sha256(preflight_path) != args.preflight_sha256:
        raise RuntimeError("preflight report hash mismatch")
    preflight = load_json(preflight_path)
    if preflight.get("status") != "PREFLIGHT_PASS__BILATERAL_PRINT_RELEASE_ALLOWED":
        raise RuntimeError("preflight report is not passing")
    if preflight.get("pins", {}).get("contract_sha256") != sha256(CONTRACT_PATH):
        raise RuntimeError("preflight contract pin differs from current contract")
    if preflight.get("pins", {}).get("exporter_sha256") != sha256(Path(__file__)):
        raise RuntimeError("preflight exporter pin differs from current exporter")
    output = write_release(bundle, preflight, preflight_path, args.preflight_sha256)
    print(json.dumps({
        "status": "PRINT_RELEASE_PASS__RIGHT_AND_LEFT_FCSTD_AND_STL_READY",
        "output": str(output), "elapsed_seconds": time.monotonic() - started,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
