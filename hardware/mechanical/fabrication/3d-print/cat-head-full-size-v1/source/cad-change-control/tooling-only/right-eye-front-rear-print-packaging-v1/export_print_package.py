#!/usr/bin/env python3
"""Fail-closed future STL exporter for the print-authorized two-part eye package.

Contract-only work never calls this file.  The exporter opens the pinned FCStd
read-only, works on copies, stages meshes under /tmp, and creates the fresh
packaging directory only after every CAD, orientation, and mesh gate passes.
It deliberately does not create 3MF or G-code.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import importlib.util
import json
import math
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import preflight  # noqa: E402


def align_to_bed(shape: Any, normal_values: Sequence[float], bed: Sequence[float],
                 reserve: float, App: Any) -> tuple[Any, dict[str, Any]]:
    result = shape.copy()
    source = App.Vector(*map(float, normal_values))
    source.normalize()
    target = App.Vector(0.0, 0.0, -1.0)
    dot = max(-1.0, min(1.0, float(source.dot(target))))
    angle = math.degrees(math.acos(dot))
    axis = source.cross(target)
    if axis.Length <= 1.0e-12 and dot < 0.0:
        axis = source.cross(App.Vector(1.0, 0.0, 0.0))
        if axis.Length <= 1.0e-12:
            axis = source.cross(App.Vector(0.0, 1.0, 0.0))
    if angle > 1.0e-12:
        axis.normalize()
        result.rotate(App.Vector(0.0, 0.0, 0.0), axis, angle)

    candidates = []
    for yaw in range(180):
        trial = result.copy()
        if yaw:
            trial.rotate(App.Vector(0.0, 0.0, 0.0), App.Vector(0.0, 0.0, 1.0), yaw)
        box = trial.BoundBox
        dimensions = (float(box.XLength), float(box.YLength), float(box.ZLength))
        margins = ((float(bed[0]) - dimensions[0]) / 2.0,
                   (float(bed[1]) - dimensions[1]) / 2.0)
        fits = dimensions[2] <= float(bed[2]) and min(margins) >= reserve
        candidates.append((fits, min(margins), -dimensions[2], yaw, trial, dimensions, margins))
    passing = [item for item in candidates if item[0]]
    if not passing:
        best = max(candidates, key=lambda item: (item[1], item[2]))
        raise RuntimeError(
            "no yaw satisfies conservative bed/reserve gate; best "
            f"yaw={best[3]} dimensions={best[5]} margins={best[6]}"
        )
    selected = max(passing, key=lambda item: (item[1], item[2], -item[3]))
    result = selected[4]
    box = result.BoundBox
    result.translate(App.Vector(
        float(bed[0]) / 2.0 - (float(box.XMin) + float(box.XMax)) / 2.0,
        float(bed[1]) / 2.0 - (float(box.YMin) + float(box.YMax)) / 2.0,
        -float(box.ZMin),
    ))
    return result, {
        "bed_face_alignment_axis": [float(axis.x), float(axis.y), float(axis.z)] if angle > 1.0e-12 else [0.0, 0.0, 1.0],
        "bed_face_alignment_angle_deg": angle,
        "selected_yaw_deg": selected[3],
        "oriented_dimensions_mm": list(selected[5]),
        "centered_xy_margins_mm": list(selected[6]),
        "scale": 1.0,
    }


def mesh_topology(mesh: Any) -> dict[str, Any]:
    points, facets = mesh.Topology
    point_values = [(float(item.x), float(item.y), float(item.z)) for item in points]
    facet_values = [tuple(map(int, item)) for item in facets]
    edges: Counter[tuple[int, int]] = Counter()
    adjacency: dict[int, set[int]] = defaultdict(set)
    edge_facets: dict[tuple[int, int], list[int]] = defaultdict(list)
    degenerate = 0
    duplicate = 0
    seen: set[tuple[int, int, int]] = set()
    signed_volume = 0.0
    for index, facet in enumerate(facet_values):
        if len(facet) != 3:
            raise RuntimeError(f"non-triangular mesh facet at index {index}")
        a, b, c = (point_values[item] for item in facet)
        ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        cross = (ab[1] * ac[2] - ab[2] * ac[1],
                 ab[2] * ac[0] - ab[0] * ac[2],
                 ab[0] * ac[1] - ab[1] * ac[0])
        if math.sqrt(sum(value * value for value in cross)) <= 1.0e-12:
            degenerate += 1
        key = tuple(sorted(facet))
        if key in seen:
            duplicate += 1
        seen.add(key)
        signed_volume += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + a[1] * (b[2] * c[0] - b[0] * c[2])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6.0
        for first, second in ((facet[0], facet[1]), (facet[1], facet[2]), (facet[2], facet[0])):
            edge = tuple(sorted((first, second)))
            edges[edge] += 1
            edge_facets[edge].append(index)
    for linked in edge_facets.values():
        for first in linked:
            adjacency[first].update(item for item in linked if item != first)
    unseen = set(range(len(facet_values)))
    components = 0
    while unseen:
        components += 1
        queue = deque([unseen.pop()])
        while queue:
            for neighbor in adjacency[queue.popleft()]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    queue.append(neighbor)
    self_intersection_count: int | None = None
    getter = getattr(mesh, "getSelfIntersections", None)
    if callable(getter):
        self_intersection_count = len(getter())
    else:
        checker = getattr(mesh, "hasSelfIntersections", None)
        if callable(checker):
            self_intersection_count = 1 if bool(checker()) else 0
    return {
        "vertices": len(point_values), "facets": len(facet_values),
        "connected_components": components,
        "boundary_edges": sum(1 for count in edges.values() if count == 1),
        "nonmanifold_edges": sum(1 for count in edges.values() if count > 2),
        "degenerate_facets": degenerate,
        "duplicate_facets": duplicate,
        "signed_volume_mm3": signed_volume,
        "outward_normals": signed_volume > 0.0,
        "self_intersection_count": self_intersection_count,
    }


def enforce_mesh(metrics: dict[str, Any], gates: dict[str, Any], label: str) -> None:
    failures = []
    if metrics["connected_components"] != int(gates["required_connected_components_each"]):
        failures.append("connected_components")
    for metric, gate in (("boundary_edges", "maximum_boundary_edges"),
                         ("nonmanifold_edges", "maximum_nonmanifold_edges"),
                         ("degenerate_facets", "maximum_degenerate_facets"),
                         ("duplicate_facets", "maximum_duplicate_facets")):
        if int(metrics[metric]) > int(gates[gate]):
            failures.append(metric)
    if gates["require_positive_volume"] and float(metrics["signed_volume_mm3"]) <= 0.0:
        failures.append("positive_volume")
    if gates["require_outward_normals"] and not metrics["outward_normals"]:
        failures.append("outward_normals")
    if gates["require_no_self_intersections"] and metrics["self_intersection_count"] != 0:
        failures.append("self_intersections_or_checker_unavailable")
    if failures:
        raise RuntimeError(f"{label}: mesh gates failed: {failures}")


def shape_metrics(shape: Any) -> dict[str, Any]:
    messages = []
    raw = shape.check(True)
    if raw:
        messages = [str(item) for item in raw]
    return {
        "valid": bool(shape.isValid()), "closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids), "volume_mm3": float(shape.Volume),
        "occt_check_messages": messages,
    }


def load_conditioner(
    root: Path,
    conditioning: dict[str, Any],
) -> Any:
    path = (root / str(conditioning["module_path"])).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as error:
        raise RuntimeError("mesh conditioner path escapes repository") from error
    if preflight.sha256_file(path) != conditioning["module_sha256"]:
        raise RuntimeError("mesh conditioner SHA-256 mismatch")
    spec = importlib.util.spec_from_file_location(
        "_right_eye_package_conditioner", path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import mesh conditioner")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if (
        module.ALGORITHM_ID != conditioning["algorithm_id"]
        or float(module.WELD_DISTANCE_MM)
        != float(conditioning["maximum_weld_distance_mm"])
    ):
        raise RuntimeError("mesh conditioner identity/parameters mismatch")
    return module


def runtime_probe() -> dict[str, Any]:
    import FreeCAD as App  # type: ignore
    import MeshPart  # type: ignore
    import Part  # type: ignore
    shape = Part.makeBox(10.0, 10.0, 10.0)
    mesh = MeshPart.meshFromShape(
        Shape=shape, LinearDeflection=0.05,
        AngularDeflection=math.radians(10.0), Relative=False,
    )
    metrics = mesh_topology(mesh)
    return {
        "status": "PASS__RUNTIME_PROBE" if (
            metrics["connected_components"] == 1
            and metrics["boundary_edges"] == 0
            and metrics["nonmanifold_edges"] == 0
            and metrics["degenerate_facets"] == 0
            and metrics["self_intersection_count"] == 0
        ) else "FAIL__RUNTIME_PROBE",
        "freecad_version": App.Version(), "fixture": "in-memory 10 mm cube",
        "candidate_opened": False, "artifact_written": False,
        "mesh": metrics,
    }


def export_package(contract_path: Path) -> dict[str, Any]:
    started = time.monotonic()
    contract = preflight.load_json(contract_path)
    errors = preflight.release_errors(contract, contract_path)
    if errors:
        return {"status": "BLOCKED__RELEASE_INPUTS_INCOMPLETE", "errors": errors,
                "candidate_opened": False, "artifact_written": False}
    root = preflight.repository_root(contract_path)
    source = contract["source_release"]
    conditioning_spec = contract["mesh_gates"][
        "front_carrier_manufacturing_conditioning"
    ]
    conditioner = load_conditioner(root, conditioning_spec)
    output = root / contract["outputs"]["directory"]
    if output.exists():
        raise FileExistsError(f"refusing to overwrite output directory: {output}")

    import FreeCAD as App  # type: ignore
    import MeshPart  # type: ignore
    document = App.openDocument(str(root / source["fcstd_path"]))
    try:
        shapes = {}
        cad_records = {}
        for item in source["parts"]:
            obj = document.getObject(item["object_name"])
            if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
                raise RuntimeError(f"missing source object: {item['object_name']}")
            shape = obj.Shape.copy()
            metrics = shape_metrics(shape)
            if not (metrics["valid"] and metrics["closed"]
                    and metrics["solid_count"] == 1
                    and not metrics["occt_check_messages"]):
                raise RuntimeError(f"{item['id']}: CAD gates failed: {metrics}")
            oriented, orientation = align_to_bed(
                shape, item["bed_face_outward_normal"],
                contract["printer"]["conservative_build_envelope_mm"],
                float(contract["printer"]["required_xy_edge_reserve_each_side_mm"]), App,
            )
            shapes[item["id"]] = oriented
            cad_records[item["id"]] = {"source": metrics, "orientation": orientation}
    finally:
        App.closeDocument(document.Name)

    with tempfile.TemporaryDirectory(prefix="right-eye-front-lens-package-") as temporary:
        staging = Path(temporary)
        mesh_records = {}
        staged = {}
        gates = contract["mesh_gates"]
        for item in source["parts"]:
            raw_mesh = MeshPart.meshFromShape(
                Shape=shapes[item["id"]],
                LinearDeflection=float(gates["linear_deflection_mm"]),
                AngularDeflection=math.radians(float(gates["angular_deflection_deg"])),
                Relative=False,
            )
            if item["id"] == "front_carrier":
                mesh, conditioning = conditioner.condition_mesh(
                    raw_mesh, __import__("Mesh"), App
                )
                if (
                    conditioning["algorithm_id"]
                    != conditioning_spec["algorithm_id"]
                    or conditioning["automatic_repair_used"] is not False
                    or float(
                        conditioning["maximum_weld_displacement_mm"]
                    )
                    > float(
                        conditioning_spec[
                            "maximum_weld_displacement_mm"
                        ]
                    )
                ):
                    raise RuntimeError(
                        "front manufacturing conditioning exceeded contract"
                    )
            else:
                mesh = raw_mesh
                conditioning = {
                    "algorithm_id": "none",
                    "automatic_repair_used": False,
                    "raw": conditioner.mesh_topology(raw_mesh),
                    "conditioned": conditioner.mesh_topology(raw_mesh),
                }
            metrics = mesh_topology(mesh)
            enforce_mesh(metrics, gates, item["id"])
            destination = staging / item["stl_name"]
            mesh.write(str(destination))
            reloaded = __import__("Mesh").Mesh(str(destination))
            reload_metrics = mesh_topology(reloaded)
            enforce_mesh(reload_metrics, gates, item["id"] + " reloaded STL")
            staged[item["id"]] = destination
            mesh_records[item["id"]] = {
                "generated": metrics, "reloaded": reload_metrics,
                "stl_sha256": preflight.sha256_file(destination),
                "manufacturing_conditioning": conditioning,
            }
        output.mkdir(parents=True, exist_ok=False)
        for item in source["parts"]:
            shutil.copy2(staged[item["id"]], output / item["stl_name"])
        report = {
            "schema_version": "cat-head-right-eye-print-package-export-v1",
            "status": "PASS__STL_ONLY__3MF_AND_PRINT_RELEASE_HELD",
            "authority": "TOOLING_DERIVATIVE__NOT_GCODE",
            "source_fcstd_sha256": source["fcstd_sha256"],
            "source_validation_sha256": source["validation_sha256"],
            "contract_sha256": preflight.sha256_file(contract_path),
            "cad": cad_records, "meshes": mesh_records,
            "outputs": {item["id"]: {
                "stl": str((output / item["stl_name"]).relative_to(root)),
                "sha256": preflight.sha256_file(output / item["stl_name"]),
                "planned_3mf": str((output / item["project_name"]).relative_to(root)),
            } for item in source["parts"]},
            "candidate_opened_read_only": True, "candidate_saved": False,
            "automatic_repair_used": False, "three_mf_created": False,
            "manufacturing_conditioning_used": {
                "front_carrier": conditioning_spec["algorithm_id"],
                "translucent_eye_glass": "none",
            },
            "gcode_created": False, "print_released": False,
            "elapsed_seconds": time.monotonic() - started,
        }
        manifest = output / contract["outputs"]["manifest"]
        manifest.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return report


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=SCRIPT_DIR / "contract.json")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--runtime-probe", action="store_true")
    mode.add_argument("--export-if-pass", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    result = runtime_probe() if args.runtime_probe else export_package(args.contract.resolve())
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"].startswith("PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())
