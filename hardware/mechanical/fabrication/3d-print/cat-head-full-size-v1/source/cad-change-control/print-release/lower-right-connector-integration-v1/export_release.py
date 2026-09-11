#!/usr/bin/env python3
"""Build and export the user-approved modular lower-right connector release.

The release regenerates only six changed modular parts.  It never overwrites
the manual assembly, approved review files, or any earlier print package.
Preflight writes only a JSON report under /tmp.  Release stages one FCStd and
six independent STLs under /tmp and copies them into a fresh FINAL_PRINT_SET
directory only after every BRep, connector, and mesh gate passes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
CONTRACT_PATH = HERE / "contract.json"
SCHEMA = "cat-head-lower-right-connector-integration-print-release-v1"

PART_IDS = (
    "opaque_component_001",
    "opaque_component_002",
    "opaque_right_ledge",
    "translucent_quad003_component_01",
    "translucent_central_component_03",
    "translucent_quad017_component_02",
)

PART_OBJECT_NAMES = {
    "opaque_component_001": "RIGHT_LOWER_OPAQUE_COMPONENT_001_WITH_BELOW_MOUTH_OUTER_TABS_PRINT",
    "opaque_component_002": "RIGHT_LOWER_OPAQUE_COMPONENT_002_WITH_NOSE_TOP_TAB_PRINT",
    "opaque_right_ledge": "RIGHT_LOWER_LEDGE_WITH_USER_EXTENSION_PRINT",
    "translucent_quad003_component_01": "RIGHT_TRANSLUCENT_QUAD003_COMPONENT_01_WITH_BELOW_MOUTH_TAB_PRINT",
    "translucent_central_component_03": "RIGHT_TRANSLUCENT_CENTRAL_CLUSTER_COMPONENT_03_WITH_NOSE_TOP_TAB_PRINT",
    "translucent_quad017_component_02": "RIGHT_TRANSLUCENT_QUAD017_COMPONENT_02_WITH_OUTER_TAB_PRINT",
}

PART_LABELS = {
    "opaque_component_001": "RIGHT LOWER — OPAQUE COMPONENT 001 — BELOW-MOUTH + OUTER TABS — PRINT",
    "opaque_component_002": "RIGHT LOWER — OPAQUE COMPONENT 002 — NOSE-TOP TAB — PRINT",
    "opaque_right_ledge": "RIGHT LOWER — LEDGE + USER EXTENSION — PRINT",
    "translucent_quad003_component_01": "RIGHT LOWER — TRANSLUCENT QUAD003 COMPONENT 01 — BELOW-MOUTH TAB — PRINT",
    "translucent_central_component_03": "RIGHT LOWER — TRANSLUCENT CENTRAL CLUSTER COMPONENT 03 — NOSE-TOP TAB — PRINT",
    "translucent_quad017_component_02": "RIGHT LOWER — TRANSLUCENT QUAD017 COMPONENT 02 — OUTER TAB — PRINT",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def project_path(value: str) -> Path:
    path = (PROJECT_ROOT / value).resolve()
    path.relative_to(PROJECT_ROOT.resolve())
    return path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_contract() -> dict[str, Any]:
    contract = load_json(CONTRACT_PATH)
    if contract.get("schema_version") != SCHEMA:
        raise RuntimeError("unexpected lower-right print-release contract schema")
    return contract


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify_pins(contract: dict[str, Any]) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    for key, item in contract["inputs"].items():
        path = project_path(str(item["path"]))
        actual = sha256(path)
        expected = str(item["sha256"])
        if actual != expected:
            raise RuntimeError(
                f"hash mismatch for inputs.{key}: expected {expected}, got {actual}"
            )
        records[key] = {"path": str(item["path"]), "sha256": actual}
    return records


def topology_counts(shape: Any) -> dict[str, int]:
    return {
        "vertices": len(shape.Vertexes),
        "edges": len(shape.Edges),
        "wires": len(shape.Wires),
        "faces": len(shape.Faces),
        "shells": len(shape.Shells),
        "solids": len(shape.Solids),
    }


def bounds(shape: Any) -> dict[str, list[float]]:
    box = shape.BoundBox
    return {
        "minimum": [float(box.XMin), float(box.YMin), float(box.ZMin)],
        "maximum": [float(box.XMax), float(box.YMax), float(box.ZMax)],
        "size": [float(box.XLength), float(box.YLength), float(box.ZLength)],
    }


def cylinder_radii(shape: Any) -> list[float]:
    values: list[float] = []
    for face in shape.Faces:
        surface = face.Surface
        if getattr(surface, "TypeId", "") == "Part::GeomCylinder":
            values.append(float(surface.Radius))
    return sorted(values)


def shape_record(shape: Any) -> dict[str, Any]:
    return {
        "shape_type": str(shape.ShapeType),
        "valid": bool(shape.isValid()),
        "closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids),
        "shell_count": len(shape.Shells),
        "volume_mm3": float(shape.Volume),
        "area_mm2": float(shape.Area),
        "topology": topology_counts(shape),
        "bounds_mm": bounds(shape),
        "cylinder_radii_mm": cylinder_radii(shape),
        "brep_sha256": digest_text(shape.exportBrepToString()),
    }


def clean_single_solid(shape: Any) -> bool:
    return bool(
        not shape.isNull()
        and shape.isValid()
        and shape.isClosed()
        and len(shape.Solids) == 1
    )


def common_volume(left: Any, right: Any) -> float:
    result = left.common(right)
    return 0.0 if result.isNull() else max(0.0, float(result.Volume))


def symmetric_difference(left: Any, right: Any) -> dict[str, float]:
    left_only = left.cut(right)
    right_only = right.cut(left)
    left_volume = 0.0 if left_only.isNull() else float(left_only.Volume)
    right_volume = 0.0 if right_only.isNull() else float(right_only.Volume)
    return {
        "left_only_mm3": left_volume,
        "right_only_mm3": right_volume,
        "total_mm3": left_volume + right_volume,
    }


def fuse_many(shapes: Sequence[Any]) -> Any:
    if not shapes:
        raise RuntimeError("cannot fuse an empty shape list")
    result = shapes[0].copy()
    for shape in shapes[1:]:
        result = result.fuse(shape).removeSplitter()
    return result


def condition_tab(tab: Any, opposite_owner: Any) -> Any:
    conditioned = tab.cut(opposite_owner).removeSplitter()
    if conditioned.isNull():
        raise RuntimeError("opposite-owner conditioning removed an entire tab")
    return conditioned


def mesh_record(
    part_id: str,
    shape: Any,
    contract: dict[str, Any],
    Mesh: Any,
    MeshPart: Any,
    App: Any,
    checker: Any,
) -> tuple[Any, dict[str, Any]]:
    specification = contract["mesh"]
    raw_mesh = MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=float(specification["linear_deflection_mm"]),
        AngularDeflection=float(specification["angular_deflection_rad"]),
        Relative=False,
    )
    raw = checker.mesh_topology(raw_mesh)
    raw["clean"] = bool(checker.clean_manifold_mesh(raw))
    record: dict[str, Any] = {
        "meshing_method": "FreeCAD MeshPart.meshFromShape",
        "linear_deflection_mm": float(specification["linear_deflection_mm"]),
        "angular_deflection_rad": float(
            specification["angular_deflection_rad"]
        ),
        "relative": False,
        "selection": "raw",
        "conditioning_allowed": False,
        "conditioning_applied": False,
        "conditioning_policy_checks": {},
        "conditioning": None,
        "raw": raw,
        "selected": dict(raw),
        "clean": bool(raw["clean"]),
    }
    if raw["clean"]:
        return raw_mesh, record

    policies = specification["deterministic_conditioning"]["parts"]
    policy = policies.get(part_id)
    if policy is None:
        record["selection"] = "raw_failure_without_authorized_conditioning"
        return raw_mesh, record

    record["conditioning_allowed"] = True
    configured_distance = float(policy["weld_distance_mm"])
    original_distance = float(checker.WELD_DISTANCE_MM)
    try:
        checker.WELD_DISTANCE_MM = configured_distance
        conditioned_mesh, conditioning = checker.condition_mesh(
            raw_mesh, Mesh, App
        )
    finally:
        checker.WELD_DISTANCE_MM = original_distance

    selected = checker.mesh_topology(conditioned_mesh)
    selected["clean"] = bool(checker.clean_manifold_mesh(selected))
    conditioning["release_algorithm_id"] = (
        "bounded-deterministic-submicron-weld-and-zero-area-filter-v1"
    )
    conditioning["configured_weld_distance_mm"] = configured_distance
    conditioning["conditioned"] = selected
    prohibited_flags = (
        "automatic_repair_used",
        "coordinate_search_used",
        "smoothing_used",
        "hole_filling_used",
        "remeshing_used",
        "scaling_used",
    )
    policy_checks = {
        "raw_mesh_failed_clean_gate": not bool(raw["clean"]),
        "reported_weld_distance_matches_contract": abs(
            float(conditioning["maximum_allowed_weld_distance_mm"])
            - configured_distance
        )
        <= 1.0e-15,
        "maximum_weld_displacement_within_contract": float(
            conditioning["maximum_weld_displacement_mm"]
        )
        <= float(policy["maximum_weld_displacement_mm"]),
        "weld_group_count_matches_contract": len(
            conditioning["weld_groups"]
        )
        == int(policy["expected_weld_group_count"]),
        "removed_degenerate_facet_count_matches_contract": len(
            conditioning["removed_degenerate_source_facets"]
        )
        == int(policy["expected_removed_degenerate_facets"]),
        "removed_duplicate_facet_count_matches_contract": len(
            conditioning["removed_duplicate_source_facets"]
        )
        == int(policy["expected_removed_duplicate_facets"]),
        "no_prohibited_mesh_operation_used": all(
            not bool(conditioning[name]) for name in prohibited_flags
        ),
        "conditioned_mesh_passes_clean_gate": bool(selected["clean"]),
    }
    record.update(
        {
            "selection": "bounded_conditioned",
            "conditioning_applied": True,
            "conditioning_policy_checks": policy_checks,
            "conditioning": conditioning,
            "selected": selected,
            "clean": bool(selected["clean"] and all(policy_checks.values())),
        }
    )
    return conditioned_mesh, record


def prepare() -> dict[str, Any]:
    import FreeCAD as App  # type: ignore
    import Mesh  # type: ignore
    import MeshPart  # type: ignore

    contract = load_contract()
    pins = verify_pins(contract)
    objects = contract["objects"]
    input_paths = {
        key: project_path(str(contract["inputs"][key]["path"]))
        for key in (
            "manual_baseline",
            "validated_closed_component_001_source",
            "approved_connector_v2",
            "approved_ledge_v2",
        )
    }
    documents = {
        key: App.openDocument(str(path)) for key, path in input_paths.items()
    }
    try:
        def copied(document_key: str, object_key: str) -> Any:
            name = str(objects[object_key])
            obj = documents[document_key].getObject(name)
            if obj is None or not hasattr(obj, "Shape") or obj.Shape.isNull():
                raise RuntimeError(f"missing source shape: {document_key}.{name}")
            return obj.Shape.copy()

        current_owner_001 = copied("manual_baseline", "opaque_component_001_owner")
        owner_001 = copied(
            "validated_closed_component_001_source",
            "opaque_component_001_owner",
        )
        owner_002 = copied("manual_baseline", "opaque_component_002_owner")
        ledge_base = copied("manual_baseline", "right_ledge_base")
        current_ledge_extension = copied("manual_baseline", "right_ledge_extension")
        approved_ledge_extension = copied("approved_ledge_v2", "right_ledge_extension")
        translucent_owners = {
            "below_mouth": copied(
                "manual_baseline", "below_mouth_translucent_owner"
            ),
            "nose_top": copied("manual_baseline", "nose_top_translucent_owner"),
            "outer_panel": copied(
                "manual_baseline", "outer_panel_translucent_owner"
            ),
        }
        opaque_owners = {
            "below_mouth": owner_001,
            "nose_top": owner_002,
            "outer_panel": owner_001,
        }
        source_tabs = {
            "below_mouth": {
                "opaque": copied("approved_connector_v2", "below_mouth_opaque_tab"),
                "translucent": copied(
                    "approved_connector_v2", "below_mouth_translucent_tab"
                ),
            },
            "nose_top": {
                "opaque": copied("approved_connector_v2", "nose_top_opaque_tab"),
                "translucent": copied(
                    "approved_connector_v2", "nose_top_translucent_tab"
                ),
            },
            "outer_panel": {
                "opaque": copied("approved_connector_v2", "outer_panel_opaque_tab"),
                "translucent": copied(
                    "approved_connector_v2", "outer_panel_translucent_tab"
                ),
            },
        }
    finally:
        for document in reversed(list(documents.values())):
            App.closeDocument(document.Name)

    conditioned_tabs: dict[str, dict[str, Any]] = {}
    station_records: dict[str, dict[str, Any]] = {}
    for station in ("below_mouth", "nose_top", "outer_panel"):
        opaque_owner = opaque_owners[station]
        translucent_owner = translucent_owners[station]
        opaque_source = source_tabs[station]["opaque"]
        translucent_source = source_tabs[station]["translucent"]
        opaque_tab = condition_tab(opaque_source, translucent_owner)
        translucent_tab = condition_tab(translucent_source, opaque_owner)
        conditioned_tabs[station] = {
            "opaque": opaque_tab,
            "translucent": translucent_tab,
        }
        station_records[station] = {
            "opaque_source_volume_mm3": float(opaque_source.Volume),
            "opaque_conditioned_volume_mm3": float(opaque_tab.Volume),
            "opaque_removed_cross_owner_mm3": max(
                0.0, float(opaque_source.Volume - opaque_tab.Volume)
            ),
            "translucent_source_volume_mm3": float(translucent_source.Volume),
            "translucent_conditioned_volume_mm3": float(translucent_tab.Volume),
            "translucent_removed_cross_owner_mm3": max(
                0.0, float(translucent_source.Volume - translucent_tab.Volume)
            ),
            "opaque_source_to_opposite_owner_mm3": common_volume(
                opaque_source, translucent_owner
            ),
            "translucent_source_to_opposite_owner_mm3": common_volume(
                translucent_source, opaque_owner
            ),
            "opaque_conditioned_to_opposite_owner_mm3": common_volume(
                opaque_tab, translucent_owner
            ),
            "translucent_conditioned_to_opposite_owner_mm3": common_volume(
                translucent_tab, opaque_owner
            ),
            "opaque_intended_owner_overlap_mm3": common_volume(
                opaque_tab, opaque_owner
            ),
            "translucent_intended_owner_overlap_mm3": common_volume(
                translucent_tab, translucent_owner
            ),
            "tab_pair_intersection_mm3": common_volume(
                opaque_tab, translucent_tab
            ),
            "tab_pair_clearance_mm": float(
                opaque_tab.distToShape(translucent_tab)[0]
            ),
            "opaque_tab": shape_record(opaque_tab),
            "translucent_tab": shape_record(translucent_tab),
        }

    parts = {
        "opaque_component_001": fuse_many(
            [
                owner_001,
                conditioned_tabs["below_mouth"]["opaque"],
                conditioned_tabs["outer_panel"]["opaque"],
            ]
        ),
        "opaque_component_002": fuse_many(
            [owner_002, conditioned_tabs["nose_top"]["opaque"]]
        ),
        "opaque_right_ledge": fuse_many(
            [ledge_base, approved_ledge_extension]
        ),
        "translucent_quad003_component_01": fuse_many(
            [
                translucent_owners["below_mouth"],
                conditioned_tabs["below_mouth"]["translucent"],
            ]
        ),
        "translucent_central_component_03": fuse_many(
            [
                translucent_owners["nose_top"],
                conditioned_tabs["nose_top"]["translucent"],
            ]
        ),
        "translucent_quad017_component_02": fuse_many(
            [
                translucent_owners["outer_panel"],
                conditioned_tabs["outer_panel"]["translucent"],
            ]
        ),
    }

    final_pairs = {
        "below_mouth": (
            parts["opaque_component_001"],
            parts["translucent_quad003_component_01"],
        ),
        "nose_top": (
            parts["opaque_component_002"],
            parts["translucent_central_component_03"],
        ),
        "outer_panel": (
            parts["opaque_component_001"],
            parts["translucent_quad017_component_02"],
        ),
    }
    cross_owner_records: dict[str, dict[str, float]] = {}
    for station, (opaque_final, translucent_final) in final_pairs.items():
        baseline_common = common_volume(
            opaque_owners[station], translucent_owners[station]
        )
        final_common = common_volume(opaque_final, translucent_final)
        cross_owner_records[station] = {
            "baseline_common_mm3": baseline_common,
            "final_common_mm3": final_common,
            "added_common_mm3": final_common - baseline_common,
        }

    mesh_checker = load_module(
        project_path(
            str(contract["inputs"]["mesh_topology_checker"]["path"])
        ),
        "_lower_right_release_mesh_checker",
    )
    meshes: dict[str, Any] = {}
    mesh_records: dict[str, dict[str, Any]] = {}
    for part_id, shape in parts.items():
        mesh, record = mesh_record(
            part_id,
            shape,
            contract,
            Mesh,
            MeshPart,
            App,
            mesh_checker,
        )
        meshes[part_id] = mesh
        mesh_records[part_id] = record

    return {
        "App": App,
        "Mesh": Mesh,
        "MeshPart": MeshPart,
        "mesh_checker": mesh_checker,
        "contract": contract,
        "pins": pins,
        "parts": parts,
        "meshes": meshes,
        "mesh_records": mesh_records,
        "station_records": station_records,
        "cross_owner_records": cross_owner_records,
        "source_evidence": {
            "component_001_current": shape_record(current_owner_001),
            "component_001_repair": shape_record(owner_001),
            "component_001_symmetric_difference": symmetric_difference(
                current_owner_001, owner_001
            ),
            "component_001_face_count_delta": (
                len(owner_001.Faces) - len(current_owner_001.Faces)
            ),
            "ledge_extension_current": shape_record(current_ledge_extension),
            "ledge_extension_approved": shape_record(approved_ledge_extension),
            "ledge_extension_symmetric_difference": symmetric_difference(
                current_ledge_extension, approved_ledge_extension
            ),
        },
    }


def evaluate(bundle: dict[str, Any]) -> dict[str, Any]:
    contract = bundle["contract"]
    gates = contract["numeric_gates"]
    epsilon = float(gates["volume_epsilon_mm3"])
    part_records = {
        part_id: shape_record(shape)
        for part_id, shape in bundle["parts"].items()
    }
    source = bundle["source_evidence"]
    stations = bundle["station_records"]

    component_repair_pass = bool(
        not source["component_001_current"]["valid"]
        and not source["component_001_current"]["closed"]
        and source["component_001_repair"]["valid"]
        and source["component_001_repair"]["closed"]
        and source["component_001_repair"]["solid_count"] == 1
        and source["component_001_face_count_delta"] == 1
        and source["component_001_symmetric_difference"]["total_mm3"]
        <= float(gates["component_001_maximum_symmetric_difference_mm3"])
    )
    ledge_identity_pass = bool(
        source["ledge_extension_symmetric_difference"]["total_mm3"] <= epsilon
    )
    tab_shapes_pass = all(
        record[side]["valid"]
        and record[side]["closed"]
        and record[side]["solid_count"] == 1
        for record in stations.values()
        for side in ("opaque_tab", "translucent_tab")
    )
    root_overlap_pass = all(
        record[f"{side}_intended_owner_overlap_mm3"]
        >= float(gates["minimum_intended_owner_overlap_mm3"])
        for record in stations.values()
        for side in ("opaque", "translucent")
    )
    pair_clearance_pass = all(
        record["tab_pair_intersection_mm3"]
        <= float(gates["maximum_tab_pair_intersection_mm3"])
        and record["tab_pair_clearance_mm"]
        >= float(gates["minimum_tab_pair_clearance_mm"])
        and record["tab_pair_clearance_mm"]
        <= float(gates["maximum_tab_pair_clearance_mm"])
        for record in stations.values()
    )
    cross_collision_pass = all(
        record["added_common_mm3"]
        <= float(gates["maximum_added_fused_pair_intersection_mm3"])
        for record in bundle["cross_owner_records"].values()
    )
    opposite_owner_trim_pass = all(
        record["opaque_conditioned_to_opposite_owner_mm3"] <= epsilon
        and record["translucent_conditioned_to_opposite_owner_mm3"] <= epsilon
        for record in stations.values()
    )
    bore_pass = all(
        any(
            abs(radius - float(gates["required_bore_radius_mm"]))
            <= float(gates["bore_radius_tolerance_mm"])
            for radius in record[side]["cylinder_radii_mm"]
        )
        for record in stations.values()
        for side in ("opaque_tab", "translucent_tab")
    )
    part_brep_pass = all(
        record["valid"] and record["closed"] and record["solid_count"] == 1
        for record in part_records.values()
    )
    mesh_pass = all(
        bool(record.get("clean"))
        for record in bundle["mesh_records"].values()
    )
    expected_conditioning = set(
        contract["mesh"]["deterministic_conditioning"]["parts"]
    )
    actual_conditioning = {
        part_id
        for part_id, record in bundle["mesh_records"].items()
        if record["conditioning_applied"]
    }
    conditioning_scope_pass = bool(
        actual_conditioning == expected_conditioning
        and all(
            all(record["conditioning_policy_checks"].values())
            for record in bundle["mesh_records"].values()
            if record["conditioning_applied"]
        )
        and all(
            record["raw"]["clean"]
            for part_id, record in bundle["mesh_records"].items()
            if part_id not in expected_conditioning
        )
    )
    output_directory = project_path(contract["outputs"]["directory"])
    checks = {
        "all_input_hashes_match": True,
        "component_001_zero_volume_closure_face_restored": component_repair_pass,
        "approved_right_ledge_extension_shape_is_exact": ledge_identity_pass,
        "all_six_conditioned_tabs_are_valid_closed_one_solid": tab_shapes_pass,
        "all_six_conditioned_tabs_keep_positive_intended_owner_overlap": root_overlap_pass,
        "all_three_tab_pairs_keep_approved_0p300_clearance_and_zero_intersection": pair_clearance_pass,
        "exact_opposite_owner_conditioning_removes_all_tab_cross_collision": opposite_owner_trim_pass,
        "final_fusions_add_no_cross_owner_collision": cross_collision_pass,
        "all_six_d4_bores_remain_in_conditioned_tabs": bore_pass,
        "all_six_print_parts_are_valid_closed_one_solid": part_brep_pass,
        "all_six_generated_meshes_are_clean_closed_manifold_single_components": mesh_pass,
        "only_two_named_raw_failures_receive_bounded_deterministic_conditioning": conditioning_scope_pass,
        "output_directory_is_fresh": not output_directory.exists(),
        "release_names_prohibit_3mf_and_gcode": all(
            not str(value).lower().endswith((".3mf", ".gcode"))
            for value in contract["outputs"]["parts"].values()
        ),
    }
    failed = [name for name, passed in checks.items() if not passed]
    return {
        "schema_version": "cat-head-lower-right-connector-integration-preflight-v1",
        "status": (
            "PREFLIGHT_PASS__LOWER_RIGHT_FCSTD_AND_STL_RELEASE_ALLOWED"
            if not failed
            else "PREFLIGHT_FAIL__NO_PRINT_OUTPUT"
        ),
        "authority": contract["authority"],
        "checks": checks,
        "failed_checks": failed,
        "source_evidence": source,
        "connector_station_evidence": stations,
        "cross_owner_collision_evidence": bundle["cross_owner_records"],
        "part_breps": part_records,
        "part_meshes": bundle["mesh_records"],
        "pins": {
            "contract_sha256": sha256(CONTRACT_PATH),
            "exporter_sha256": sha256(Path(__file__)),
            "verified_inputs": bundle["pins"],
        },
        "runtime": {
            "freecad_version": list(bundle["App"].Version()),
        },
        "io_trace": {
            "preflight_report_created": False,
            "fcstd_created": False,
            "stl_created": False,
            "three_mf_created": False,
            "gcode_created": False,
            "output_directory_created": False,
        },
    }


def add_part(
    document: Any,
    group: Any,
    part_id: str,
    shape: Any,
    authority: str,
) -> Any:
    obj = document.addObject("Part::Feature", PART_OBJECT_NAMES[part_id])
    obj.Label = PART_LABELS[part_id]
    obj.Shape = shape.copy()
    obj.addProperty("App::PropertyString", "Authority", "PrintRelease")
    obj.Authority = authority
    obj.addProperty("App::PropertyString", "PartId", "PrintRelease")
    obj.PartId = part_id
    obj.addProperty("App::PropertyString", "Integration", "PrintRelease")
    obj.Integration = "APPROVED_RIGHT_TABS__EXACT_OPPOSITE_OWNER_TRIM__OWNER_FUSION"
    group.addObject(obj)
    view = getattr(obj, "ViewObject", None)
    if view is not None:
        if part_id.startswith("translucent_"):
            view.ShapeColor = (0.35, 0.82, 0.96)
            view.Transparency = 45
        else:
            view.ShapeColor = (0.20, 0.22, 0.25)
            view.Transparency = 0
    return obj


def create_fcstd(bundle: dict[str, Any], destination: Path) -> dict[str, Any]:
    App = bundle["App"]
    document = App.newDocument("LOWER_RIGHT_CONNECTOR_INTEGRATION_PRINT_PARTS_V1")
    try:
        opaque = document.addObject(
            "App::DocumentObjectGroup", "OPAQUE_RIGHT_LOWER_CHANGED_PRINT_PARTS"
        )
        translucent = document.addObject(
            "App::DocumentObjectGroup", "TRANSLUCENT_RIGHT_MATING_CHANGED_PRINT_PARTS"
        )
        for part_id in PART_IDS:
            group = translucent if part_id.startswith("translucent_") else opaque
            add_part(
                document,
                group,
                part_id,
                bundle["parts"][part_id],
                bundle["contract"]["authority"],
            )
        metadata = document.addObject(
            "App::FeaturePython", "PRINT_RELEASE_METADATA"
        )
        metadata.addProperty("App::PropertyString", "Authority", "PrintRelease")
        metadata.Authority = bundle["contract"]["authority"]
        metadata.addProperty("App::PropertyString", "ContractSha256", "PrintRelease")
        metadata.ContractSha256 = sha256(CONTRACT_PATH)
        metadata.addProperty("App::PropertyString", "ExporterSha256", "PrintRelease")
        metadata.ExporterSha256 = sha256(Path(__file__))
        metadata.addProperty("App::PropertyString", "Scope", "PrintRelease")
        metadata.Scope = "RIGHT_SIDE_ONLY__SIX_CHANGED_MODULAR_PARTS"
        metadata.addProperty(
            "App::PropertyString", "ConditioningPolicy", "PrintRelease"
        )
        metadata.ConditioningPolicy = (
            "EXACT_OPPOSITE_OWNER_SUBTRACTION_ONLY__NO_OFFSET__NO_REDESIGN"
        )
        metadata.addProperty(
            "App::PropertyString", "MeshConditioningPolicy", "PrintRelease"
        )
        metadata.MeshConditioningPolicy = (
            "TWO_NAMED_RAW_FAILURES_ONLY__BOUNDED_SUBMICRON_VERTEX_WELD__"
            "COLLAPSED_ZERO_AREA_FACETS_REMOVED"
        )
        document.recompute()
        document.saveAs(str(destination))
    finally:
        App.closeDocument(document.Name)

    reopened = App.openDocument(str(destination))
    try:
        records: dict[str, Any] = {}
        for part_id in PART_IDS:
            obj = reopened.getObject(PART_OBJECT_NAMES[part_id])
            if obj is None:
                raise RuntimeError(f"saved FCStd missing part: {part_id}")
            records[part_id] = shape_record(obj.Shape)
            if not clean_single_solid(obj.Shape):
                raise RuntimeError(f"saved FCStd part is not clean: {part_id}")
        return records
    finally:
        App.closeDocument(reopened.Name)


def write_readme(destination: Path, manifest: dict[str, Any]) -> None:
    destination.write_text(
        "# Lower-right connector integration print release V1\n\n"
        "This package contains only the six modular parts changed by the approved "
        "right-side ledge and connector work. Other lower-right parts remain "
        "unchanged and are intentionally not duplicated here.\n\n"
        "The three opaque parts and three translucent mating-owner parts are "
        "separate STLs. The FCStd contains the same six BRep parts in assembly "
        "coordinates. The approved D4 tab holes and 0.300 mm tab-to-tab gaps are "
        "preserved.\n\n"
        "A minimal print-conditioning operation subtracts each exact opposite "
        "owner from its tab before fusion. This removes cross-owner collision "
        "volume without offsets, moving geometry, changing owner surfaces, or "
        "redesigning the connector.\n\n"
        "Two named STL meshes also receive deterministic sub-micron vertex "
        "welding only after their raw meshes fail the manifold gate. The "
        "maximum measured vertex movements are recorded in the release "
        "manifest; no smoothing, hole filling, remeshing, scaling, decimation, "
        "or coordinate search is used.\n\n"
        "No 3MF, slicing profile, G-code, or printer-specific orientation is "
        "included. Import each STL into the slicer and orient it for the selected "
        "printer and material.\n\n"
        f"Release status: {manifest['status']}\n",
        encoding="utf-8",
    )


def release(bundle: dict[str, Any], report: dict[str, Any]) -> Path:
    contract = bundle["contract"]
    output_dir = project_path(contract["outputs"]["directory"])
    if output_dir.exists():
        raise RuntimeError(f"release output already exists: {output_dir}")

    with tempfile.TemporaryDirectory(
        prefix="lower-right-connector-integration-v1-"
    ) as temporary:
        stage = Path(temporary) / "release"
        stage.mkdir()
        stl_dir = stage / str(contract["outputs"]["stl_directory"])
        stl_dir.mkdir()
        fcstd = stage / str(contract["outputs"]["fcstd"])
        saved_fcstd_records = create_fcstd(bundle, fcstd)

        reloaded_mesh_records: dict[str, Any] = {}
        for part_id in PART_IDS:
            destination = stl_dir / str(
                contract["outputs"]["parts"][part_id]
            )
            bundle["meshes"][part_id].write(str(destination))
            reloaded = bundle["Mesh"].Mesh(str(destination))
            record = bundle["mesh_checker"].mesh_topology(reloaded)
            record["clean"] = bool(
                bundle["mesh_checker"].clean_manifold_mesh(record)
            )
            if not record["clean"]:
                raise RuntimeError(
                    f"reloaded STL mesh failed for {part_id}: {record}"
                )
            reloaded_mesh_records[part_id] = record

        manifest = dict(report)
        manifest["schema_version"] = (
            "cat-head-lower-right-connector-integration-release-manifest-v1"
        )
        manifest["status"] = "PRINT_RELEASE_PASS__FCSTD_AND_SIX_STLS_READY"
        manifest["failed_checks"] = []
        manifest["saved_fcstd_part_breps"] = saved_fcstd_records
        manifest["reloaded_stl_meshes"] = reloaded_mesh_records
        manifest["io_trace"] = {
            "preflight_report_created": True,
            "fcstd_created": True,
            "stl_created": True,
            "stl_count": len(PART_IDS),
            "three_mf_created": False,
            "gcode_created": False,
            "slicing_performed": False,
            "output_directory_created": True,
        }

        readme = stage / str(contract["outputs"]["readme"])
        write_readme(readme, manifest)
        manifest_path = stage / str(contract["outputs"]["manifest"])
        manifest["output_files"] = {
            "fcstd": str(fcstd.name),
            "stls": {
                part_id: str(
                    Path(contract["outputs"]["stl_directory"])
                    / contract["outputs"]["parts"][part_id]
                )
                for part_id in PART_IDS
            },
            "readme": str(readme.name),
        }
        manifest["output_sha256"] = {
            "fcstd": sha256(fcstd),
            "stls": {
                part_id: sha256(
                    stl_dir / str(contract["outputs"]["parts"][part_id])
                )
                for part_id in PART_IDS
            },
            "readme": sha256(readme),
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        checksum_targets = [
            path
            for path in stage.rglob("*")
            if path.is_file()
            and path.name != str(contract["outputs"]["checksums"])
        ]
        checksum_path = stage / str(contract["outputs"]["checksums"])
        checksum_path.write_text(
            "".join(
                f"{sha256(path)}  {path.relative_to(stage)}\n"
                for path in sorted(checksum_targets)
            ),
            encoding="utf-8",
        )
        forbidden = [
            path
            for path in stage.rglob("*")
            if path.suffix.lower() in {".3mf", ".gcode"}
        ]
        if forbidden:
            raise RuntimeError(f"forbidden release files were staged: {forbidden}")

        output_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(stage, output_dir)

    for relative, expected in [
        (str(contract["outputs"]["fcstd"]), manifest["output_sha256"]["fcstd"]),
        (str(contract["outputs"]["readme"]), manifest["output_sha256"]["readme"]),
    ]:
        actual = sha256(output_dir / relative)
        if actual != expected:
            raise RuntimeError(f"post-copy hash mismatch: {relative}")
    for part_id, expected in manifest["output_sha256"]["stls"].items():
        relative = (
            Path(contract["outputs"]["stl_directory"])
            / contract["outputs"]["parts"][part_id]
        )
        actual = sha256(output_dir / relative)
        if actual != expected:
            raise RuntimeError(f"post-copy STL hash mismatch: {part_id}")
    return output_dir


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("preflight", "release"), required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--preflight-report", type=Path)
    parser.add_argument("--preflight-sha256")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    bundle = prepare()
    report = evaluate(bundle)

    if args.mode == "preflight":
        if args.report is None:
            raise RuntimeError("preflight requires --report")
        target = args.report.resolve()
        if not str(target).startswith("/tmp/"):
            raise RuntimeError("preflight report must be under /tmp")
        if target.exists():
            raise RuntimeError(f"preflight report already exists: {target}")
        report["io_trace"]["preflight_report_created"] = True
        target.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "status": report["status"],
                    "report": str(target),
                    "report_sha256": sha256(target),
                },
                sort_keys=True,
            )
        )
        return 0 if not report["failed_checks"] else 2

    if report["failed_checks"]:
        raise RuntimeError(
            "lower-right release gates failed: "
            + ", ".join(report["failed_checks"])
        )

    if args.preflight_report is None or args.preflight_sha256 is None:
        raise RuntimeError(
            "release requires --preflight-report and --preflight-sha256"
        )
    preflight_path = args.preflight_report.resolve()
    if sha256(preflight_path) != args.preflight_sha256:
        raise RuntimeError("preflight report hash mismatch")
    preflight = load_json(preflight_path)
    if (
        preflight.get("status")
        != "PREFLIGHT_PASS__LOWER_RIGHT_FCSTD_AND_STL_RELEASE_ALLOWED"
        or preflight.get("failed_checks") != []
    ):
        raise RuntimeError("preflight report did not authorize release")
    if preflight.get("pins") != report.get("pins"):
        raise RuntimeError("preflight pins do not match the release invocation")
    expected_breps = {
        key: value["brep_sha256"]
        for key, value in preflight["part_breps"].items()
    }
    actual_breps = {
        key: value["brep_sha256"]
        for key, value in report["part_breps"].items()
    }
    if expected_breps != actual_breps:
        raise RuntimeError("release BReps differ from pinned preflight BReps")
    output = release(bundle, report)
    print(
        json.dumps(
            {
                "status": "PRINT_RELEASE_PASS__FCSTD_AND_SIX_STLS_READY",
                "output": str(output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
