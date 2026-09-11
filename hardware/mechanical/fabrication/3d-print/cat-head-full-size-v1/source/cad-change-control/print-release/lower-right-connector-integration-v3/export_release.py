#!/usr/bin/env python3
"""Create the corrected lower-right connector print release V3.

V3 keeps the approved 10 mm connector tabs, clips the negative-X half of the
bilateral central translucent owner from this right-side print part, and
removes the user-rejected long zero-area Face6 from opaque component 001.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[3]
CONTRACT_PATH = HERE / "contract.json"
V2_HELPERS_PATH = HERE.parent / "lower-right-connector-integration-v2" / "export_release.py"
SCHEMA = "cat-head-lower-right-connector-integration-print-release-v3"
PREFLIGHT_PASS = "PREFLIGHT_PASS__LOWER_RIGHT_V3_CORRECTION_RELEASE_ALLOWED"
RELEASE_PASS = "PRINT_RELEASE_PASS__V3_CORRECTED_FCSTD_AND_SIX_STLS_READY"

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
    "translucent_central_component_03": "RIGHT_TRANSLUCENT_CENTRAL_CLUSTER_RIGHT_HALF_WITH_NOSE_TOP_TAB_PRINT",
    "translucent_quad017_component_02": "RIGHT_TRANSLUCENT_QUAD017_COMPONENT_02_WITH_OUTER_TAB_PRINT",
}

PART_LABELS = {
    "opaque_component_001": "RIGHT LOWER — OPAQUE COMPONENT 001 — BELOW-MOUTH + OUTER TABS — FACE6 REMOVED — PRINT",
    "opaque_component_002": "RIGHT LOWER — OPAQUE COMPONENT 002 — APPROVED NOSE-TOP TAB — PRINT",
    "opaque_right_ledge": "RIGHT LOWER — LEDGE + USER EXTENSION — PRINT",
    "translucent_quad003_component_01": "RIGHT LOWER — TRANSLUCENT QUAD003 COMPONENT 01 — BELOW-MOUTH TAB — PRINT",
    "translucent_central_component_03": "RIGHT LOWER — TRANSLUCENT CENTRAL CLUSTER RIGHT HALF — APPROVED NOSE-TOP TAB — PRINT",
    "translucent_quad017_component_02": "RIGHT LOWER — TRANSLUCENT QUAD017 COMPONENT 02 — OUTER TAB — PRINT",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def project_path(value: str) -> Path:
    path = (PROJECT_ROOT / value).resolve()
    path.relative_to(PROJECT_ROOT.resolve())
    return path


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_contract() -> dict[str, Any]:
    contract = load_json(CONTRACT_PATH)
    if contract.get("schema_version") != SCHEMA:
        raise RuntimeError("unexpected V3 lower-right print-release schema")
    return contract


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


def clip_positive_x(
    App: Any,
    Part: Any,
    shape: Any,
    specification: dict[str, Any],
) -> tuple[Any, Any, dict[str, Any]]:
    plane_x = float(specification["plane_x_mm"])
    bounds = shape.BoundBox
    margin = 10.0
    halfspace = Part.makeBox(
        float(bounds.XMax - plane_x + margin),
        float(bounds.YLength + 2.0 * margin),
        float(bounds.ZLength + 2.0 * margin),
        App.Vector(
            plane_x,
            float(bounds.YMin - margin),
            float(bounds.ZMin - margin),
        ),
    )
    retained = shape.common(halfspace).removeSplitter()
    removed = shape.cut(halfspace).removeSplitter()
    return retained, removed, {
        "plane_x_mm": plane_x,
        "source_min_x_mm": float(bounds.XMin),
        "source_max_x_mm": float(bounds.XMax),
        "retained_min_x_mm": float(retained.BoundBox.XMin),
        "retained_max_x_mm": float(retained.BoundBox.XMax),
        "removed_min_x_mm": float(removed.BoundBox.XMin),
        "removed_max_x_mm": float(removed.BoundBox.XMax),
        "source_volume_mm3": float(shape.Volume),
        "retained_volume_mm3": float(retained.Volume),
        "removed_volume_mm3": float(removed.Volume),
        "volume_conservation_residual_mm3": float(
            shape.Volume - retained.Volume - removed.Volume
        ),
    }


def prepare() -> dict[str, Any]:
    import FreeCAD as App  # type: ignore
    import Mesh  # type: ignore
    import MeshPart  # type: ignore
    import Part  # type: ignore

    contract = load_contract()
    pins = verify_pins(contract)
    v2 = load_module(V2_HELPERS_PATH, "_lower_right_release_v2_helpers")
    v1 = load_module(v2.V1_EXPORTER_PATH, "_lower_right_release_v1_helpers_for_v3")
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
        repair_owner_001 = copied(
            "validated_closed_component_001_source",
            "opaque_component_001_owner",
        )
        owner_002 = copied("manual_baseline", "opaque_component_002_owner")
        ledge_base = copied("manual_baseline", "right_ledge_base")
        current_ledge_extension = copied(
            "manual_baseline", "right_ledge_extension"
        )
        approved_ledge_extension = copied(
            "approved_ledge_v2", "right_ledge_extension"
        )
        translucent_owner_sources = {
            "below_mouth": copied(
                "manual_baseline", "below_mouth_translucent_owner"
            ),
            "nose_top": copied(
                "manual_baseline", "nose_top_translucent_owner"
            ),
            "outer_panel": copied(
                "manual_baseline", "outer_panel_translucent_owner"
            ),
        }
        source_tabs = {
            "below_mouth": {
                "opaque": copied(
                    "approved_connector_v2", "below_mouth_opaque_tab"
                ),
                "translucent": copied(
                    "approved_connector_v2", "below_mouth_translucent_tab"
                ),
            },
            "nose_top": {
                "opaque": copied(
                    "approved_connector_v2", "nose_top_opaque_tab"
                ),
                "translucent": copied(
                    "approved_connector_v2", "nose_top_translucent_tab"
                ),
            },
            "outer_panel": {
                "opaque": copied(
                    "approved_connector_v2", "outer_panel_opaque_tab"
                ),
                "translucent": copied(
                    "approved_connector_v2", "outer_panel_translucent_tab"
                ),
            },
        }
    finally:
        for document in reversed(list(documents.values())):
            App.closeDocument(document.Name)

    owner_001, healing = v2.heal_component_001(
        Part, repair_owner_001, contract["component_001_healing"]
    )
    signature = contract["component_001_healing"]["rejected_face_signature"]
    healing.update(
        {
            "source": v1.shape_record(repair_owner_001),
            "corrected": v1.shape_record(owner_001),
            "symmetric_difference": v1.symmetric_difference(
                repair_owner_001, owner_001
            ),
            "absolute_volume_delta_mm3": abs(
                float(repair_owner_001.Volume) - float(owner_001.Volume)
            ),
            "rejected_face_before": v2.rejected_face_records(
                repair_owner_001, signature
            ),
            "rejected_face_after": v2.rejected_face_records(
                owner_001, signature
            ),
        }
    )

    central_source = translucent_owner_sources["nose_top"]
    central_retained, central_removed, central_metrics = clip_positive_x(
        App, Part, central_source, contract["central_owner_clip"]
    )
    central_metrics.update(
        {
            "source": v1.shape_record(central_source),
            "retained": v1.shape_record(central_retained),
            "removed": v1.shape_record(central_removed),
            "retained_to_removed_intersection_mm3": v1.common_volume(
                central_retained, central_removed
            ),
        }
    )
    translucent_owners = {
        "below_mouth": translucent_owner_sources["below_mouth"],
        "nose_top": central_retained,
        "outer_panel": translucent_owner_sources["outer_panel"],
    }
    opaque_owners = {
        "below_mouth": owner_001,
        "nose_top": owner_002,
        "outer_panel": owner_001,
    }

    conditioned_tabs: dict[str, dict[str, Any]] = {}
    station_records: dict[str, dict[str, Any]] = {}
    for station in ("below_mouth", "nose_top", "outer_panel"):
        opaque_owner = opaque_owners[station]
        translucent_owner = translucent_owners[station]
        opaque_source = source_tabs[station]["opaque"]
        translucent_source = source_tabs[station]["translucent"]
        opaque_tab = v1.condition_tab(opaque_source, translucent_owner)
        translucent_tab = v1.condition_tab(
            translucent_source, opaque_owner
        )
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
            "translucent_source_volume_mm3": float(
                translucent_source.Volume
            ),
            "translucent_conditioned_volume_mm3": float(
                translucent_tab.Volume
            ),
            "translucent_removed_cross_owner_mm3": max(
                0.0,
                float(translucent_source.Volume - translucent_tab.Volume),
            ),
            "opaque_conditioned_to_opposite_owner_mm3": v1.common_volume(
                opaque_tab, translucent_owner
            ),
            "translucent_conditioned_to_opposite_owner_mm3": v1.common_volume(
                translucent_tab, opaque_owner
            ),
            "opaque_intended_owner_overlap_mm3": v1.common_volume(
                opaque_tab, opaque_owner
            ),
            "translucent_intended_owner_overlap_mm3": v1.common_volume(
                translucent_tab, translucent_owner
            ),
            "tab_pair_intersection_mm3": v1.common_volume(
                opaque_tab, translucent_tab
            ),
            "tab_pair_clearance_mm": float(
                opaque_tab.distToShape(translucent_tab)[0]
            ),
            "opaque_tab": v1.shape_record(opaque_tab),
            "translucent_tab": v1.shape_record(translucent_tab),
        }

    parts = {
        "opaque_component_001": v1.fuse_many(
            [
                owner_001,
                conditioned_tabs["below_mouth"]["opaque"],
                conditioned_tabs["outer_panel"]["opaque"],
            ]
        ),
        "opaque_component_002": v1.fuse_many(
            [owner_002, conditioned_tabs["nose_top"]["opaque"]]
        ),
        "opaque_right_ledge": v1.fuse_many(
            [ledge_base, approved_ledge_extension]
        ),
        "translucent_quad003_component_01": v1.fuse_many(
            [
                translucent_owners["below_mouth"],
                conditioned_tabs["below_mouth"]["translucent"],
            ]
        ),
        "translucent_central_component_03": v1.fuse_many(
            [
                translucent_owners["nose_top"],
                conditioned_tabs["nose_top"]["translucent"],
            ]
        ),
        "translucent_quad017_component_02": v1.fuse_many(
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
        baseline_common = v1.common_volume(
            opaque_owners[station], translucent_owners[station]
        )
        final_common = v1.common_volume(opaque_final, translucent_final)
        cross_owner_records[station] = {
            "baseline_common_mm3": baseline_common,
            "final_common_mm3": final_common,
            "added_common_mm3": final_common - baseline_common,
        }

    mesh_checker = load_module(
        project_path(
            str(contract["inputs"]["mesh_topology_checker"]["path"])
        ),
        "_lower_right_release_v3_mesh_checker",
    )
    meshes: dict[str, Any] = {}
    mesh_records: dict[str, dict[str, Any]] = {}
    for part_id, shape in parts.items():
        mesh, record = v1.mesh_record(
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
        "v1": v1,
        "v2": v2,
        "mesh_checker": mesh_checker,
        "contract": contract,
        "pins": pins,
        "parts": parts,
        "meshes": meshes,
        "mesh_records": mesh_records,
        "station_records": station_records,
        "cross_owner_records": cross_owner_records,
        "source_evidence": {
            "component_001_current": v1.shape_record(current_owner_001),
            "component_001_healing": healing,
            "central_translucent_owner_clip": central_metrics,
            "ledge_extension_current": v1.shape_record(
                current_ledge_extension
            ),
            "ledge_extension_approved": v1.shape_record(
                approved_ledge_extension
            ),
            "ledge_extension_symmetric_difference": v1.symmetric_difference(
                current_ledge_extension, approved_ledge_extension
            ),
        },
    }


def evaluate(bundle: dict[str, Any]) -> dict[str, Any]:
    contract = bundle["contract"]
    v1 = bundle["v1"]
    v2 = bundle["v2"]
    gates = contract["numeric_gates"]
    epsilon = float(gates["volume_epsilon_mm3"])
    source = bundle["source_evidence"]
    healing = source["component_001_healing"]
    central = source["central_translucent_owner_clip"]
    stations = bundle["station_records"]
    part_records = {
        part_id: v1.shape_record(shape)
        for part_id, shape in bundle["parts"].items()
    }

    expected_topology = contract["component_001_healing"][
        "expected_topology"
    ]
    corrected_topology = healing["corrected"]["topology"]
    healing_pass = bool(
        healing["operation_result"]
        and healing["source"]["valid"]
        and healing["source"]["closed"]
        and healing["source"]["solid_count"] == 1
        and healing["corrected"]["valid"]
        and healing["corrected"]["closed"]
        and healing["corrected"]["solid_count"] == 1
        and corrected_topology["faces"] == int(expected_topology["faces"])
        and corrected_topology["edges"] == int(expected_topology["edges"])
        and corrected_topology["vertices"]
        == int(expected_topology["vertices"])
        and corrected_topology["solids"] == int(expected_topology["solids"])
        and len(healing["rejected_face_before"]) == 1
        and healing["rejected_face_before"][0]["face_index"]
        == int(
            contract["component_001_healing"]["rejected_face_signature"][
                "source_face_index"
            ]
        )
        and healing["rejected_face_after"] == []
        and healing["symmetric_difference"]["total_mm3"]
        <= float(
            gates[
                "component_001_maximum_symmetric_difference_mm3"
            ]
        )
        and healing["absolute_volume_delta_mm3"]
        <= float(gates["component_001_maximum_volume_delta_mm3"])
    )
    current_defect_evidence_pass = bool(
        not source["component_001_current"]["valid"]
        and not source["component_001_current"]["closed"]
    )
    final_artifact_absent = (
        v2.rejected_face_records(
            bundle["parts"]["opaque_component_001"],
            contract["component_001_healing"]["rejected_face_signature"],
        )
        == []
    )

    clip = contract["central_owner_clip"]
    coordinate_tolerance = float(clip["coordinate_tolerance_mm"])
    volume_tolerance = float(clip["volume_tolerance_mm3"])
    central_clip_pass = bool(
        central["source"]["valid"]
        and central["source"]["closed"]
        and central["source"]["solid_count"] == 1
        and central["retained"]["valid"]
        and central["retained"]["closed"]
        and central["retained"]["solid_count"] == 1
        and central["removed"]["valid"]
        and central["removed"]["closed"]
        and central["removed"]["solid_count"] == 1
        and abs(
            central["source_min_x_mm"]
            - float(clip["expected_source_min_x_mm"])
        )
        <= coordinate_tolerance
        and abs(
            central["source_max_x_mm"]
            - float(clip["expected_source_max_x_mm"])
        )
        <= coordinate_tolerance
        and central["retained_min_x_mm"]
        >= float(clip["plane_x_mm"]) - coordinate_tolerance
        and central["removed_max_x_mm"]
        <= float(clip["plane_x_mm"]) + coordinate_tolerance
        and abs(
            central["retained_volume_mm3"]
            - float(clip["expected_retained_volume_mm3"])
        )
        <= volume_tolerance
        and abs(
            central["removed_volume_mm3"]
            - float(clip["expected_removed_volume_mm3"])
        )
        <= volume_tolerance
        and abs(central["volume_conservation_residual_mm3"])
        <= float(clip["maximum_volume_conservation_residual_mm3"])
        and central["retained_to_removed_intersection_mm3"]
        <= float(clip["maximum_partition_intersection_mm3"])
        and part_records["translucent_central_component_03"]["bounds_mm"][
            "minimum"
        ][0]
        >= float(clip["plane_x_mm"]) - coordinate_tolerance
    )
    approved_nose = contract["approved_nose_tabs"]
    approved_nose_tabs_pass = bool(
        abs(
            stations["nose_top"]["opaque_source_volume_mm3"]
            - float(approved_nose["expected_opaque_source_volume_mm3"])
        )
        <= float(approved_nose["volume_tolerance_mm3"])
        and abs(
            stations["nose_top"]["translucent_source_volume_mm3"]
            - float(
                approved_nose[
                    "expected_translucent_source_volume_mm3"
                ]
            )
        )
        <= float(approved_nose["volume_tolerance_mm3"])
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
        and float(gates["minimum_tab_pair_clearance_mm"])
        <= record["tab_pair_clearance_mm"]
        <= float(gates["maximum_tab_pair_clearance_mm"])
        for record in stations.values()
    )
    opposite_owner_trim_pass = all(
        record["opaque_conditioned_to_opposite_owner_mm3"] <= epsilon
        and record["translucent_conditioned_to_opposite_owner_mm3"]
        <= epsilon
        for record in stations.values()
    )
    cross_collision_pass = all(
        record["added_common_mm3"]
        <= float(gates["maximum_added_fused_pair_intersection_mm3"])
        for record in bundle["cross_owner_records"].values()
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
        "all_input_hashes_match_and_v1_v2_rejections_are_immutable": True,
        "manual_component_001_defect_is_recorded": current_defect_evidence_pass,
        "native_component_001_healing_removes_rejected_face6_within_bound": healing_pass,
        "rejected_face6_signature_absent_from_final_opaque_part": final_artifact_absent,
        "negative_x_central_owner_plank_is_removed_at_global_x0": central_clip_pass,
        "approved_10mm_nose_tabs_are_restored_exactly_from_source": approved_nose_tabs_pass,
        "approved_right_ledge_extension_shape_is_exact": ledge_identity_pass,
        "all_six_conditioned_tabs_are_valid_closed_one_solid": tab_shapes_pass,
        "all_six_conditioned_tabs_keep_positive_intended_owner_overlap": root_overlap_pass,
        "all_three_tab_pairs_keep_0p300_clearance_and_zero_intersection": pair_clearance_pass,
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
        "schema_version": "cat-head-lower-right-connector-integration-preflight-v3",
        "status": PREFLIGHT_PASS if not failed else "PREFLIGHT_FAIL__NO_PRINT_OUTPUT",
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
        "runtime": {"freecad_version": list(bundle["App"].Version())},
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
    contract: dict[str, Any],
) -> Any:
    obj = document.addObject("Part::Feature", PART_OBJECT_NAMES[part_id])
    obj.Label = PART_LABELS[part_id]
    obj.Shape = shape.copy()
    obj.addProperty("App::PropertyString", "Authority", "PrintRelease")
    obj.Authority = contract["authority"]
    obj.addProperty("App::PropertyString", "PartId", "PrintRelease")
    obj.PartId = part_id
    obj.addProperty("App::PropertyString", "Integration", "PrintRelease")
    obj.Integration = (
        "USER_CORRECTED_V3__NEGATIVE_X_CENTRAL_OWNER_CLIP__"
        "APPROVED_NOSE_TABS__FACE6_NATIVE_HEAL__"
        "EXACT_OPPOSITE_OWNER_TRIM__OWNER_FUSION"
    )
    if part_id == "opaque_component_001":
        obj.addProperty(
            "App::PropertyString", "Component001Correction", "PrintRelease"
        )
        obj.Component001Correction = (
            "REJECTED_LONG_ZERO_AREA_FACE6_REMOVED__"
            "SHAPEFIX_SMALL_STRIP_TOLERANCE_0P00002_MM"
        )
    if part_id == "translucent_central_component_03":
        obj.addProperty(
            "App::PropertyString", "CentralOwnerCorrection", "PrintRelease"
        )
        obj.CentralOwnerCorrection = (
            "OPPOSITE_SIDE_NEGATIVE_X_PLANK_REMOVED__RETAIN_X_GTE_0"
        )
        obj.addProperty(
            "App::PropertyLength", "CentralOwnerClipPlaneX", "PrintRelease"
        )
        obj.CentralOwnerClipPlaneX = float(
            contract["central_owner_clip"]["plane_x_mm"]
        )
        obj.addProperty(
            "App::PropertyLength", "ApprovedNoseTabDepth", "PrintRelease"
        )
        obj.ApprovedNoseTabDepth = float(
            contract["approved_nose_tabs"]["inward_depth_mm"]
        )
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
    contract = bundle["contract"]
    document = App.newDocument("LOWER_RIGHT_CONNECTOR_INTEGRATION_PRINT_PARTS_V3")
    try:
        opaque = document.addObject(
            "App::DocumentObjectGroup", "OPAQUE_RIGHT_LOWER_CHANGED_PRINT_PARTS"
        )
        translucent = document.addObject(
            "App::DocumentObjectGroup", "TRANSLUCENT_RIGHT_MATING_CHANGED_PRINT_PARTS"
        )
        for part_id in PART_IDS:
            group = (
                translucent if part_id.startswith("translucent_") else opaque
            )
            add_part(
                document,
                group,
                part_id,
                bundle["parts"][part_id],
                contract,
            )
        metadata = document.addObject(
            "App::FeaturePython", "PRINT_RELEASE_METADATA"
        )
        metadata.addProperty("App::PropertyString", "Authority", "PrintRelease")
        metadata.Authority = contract["authority"]
        metadata.addProperty(
            "App::PropertyString", "ContractSha256", "PrintRelease"
        )
        metadata.ContractSha256 = sha256(CONTRACT_PATH)
        metadata.addProperty(
            "App::PropertyString", "ExporterSha256", "PrintRelease"
        )
        metadata.ExporterSha256 = sha256(Path(__file__))
        metadata.addProperty("App::PropertyString", "Scope", "PrintRelease")
        metadata.Scope = "RIGHT_SIDE_ONLY__SIX_CHANGED_MODULAR_PARTS"
        metadata.addProperty(
            "App::PropertyString", "RejectedPredecessors", "PrintRelease"
        )
        metadata.RejectedPredecessors = (
            "V1_USER_REJECTED__V2_WITHHELD_AFTER_SANITY_RENDER"
        )
        metadata.addProperty(
            "App::PropertyString", "CorrectionPolicy", "PrintRelease"
        )
        metadata.CorrectionPolicy = (
            "CENTRAL_OWNER_RETAIN_X_GTE_0__APPROVED_10MM_NOSE_TABS__"
            "FACE6_NATIVE_SMALL_STRIP_HEAL"
        )
        document.recompute()
        document.saveAs(str(destination))
    finally:
        App.closeDocument(document.Name)

    with zipfile.ZipFile(destination, "r") as archive:
        if archive.testzip() is not None:
            raise RuntimeError("saved FCStd ZIP integrity check failed")

    reopened = App.openDocument(str(destination))
    try:
        records: dict[str, Any] = {}
        for part_id in PART_IDS:
            obj = reopened.getObject(PART_OBJECT_NAMES[part_id])
            if obj is None:
                raise RuntimeError(f"saved FCStd missing part: {part_id}")
            records[part_id] = bundle["v1"].shape_record(obj.Shape)
            if not bundle["v1"].clean_single_solid(obj.Shape):
                raise RuntimeError(f"saved FCStd part is not clean: {part_id}")
        central = reopened.getObject(
            PART_OBJECT_NAMES["translucent_central_component_03"]
        )
        tolerance = float(
            contract["central_owner_clip"]["coordinate_tolerance_mm"]
        )
        if central.Shape.BoundBox.XMin < -tolerance:
            raise RuntimeError("saved FCStd reintroduced the negative-X plank")
        opaque_001 = reopened.getObject(
            PART_OBJECT_NAMES["opaque_component_001"]
        )
        if bundle["v2"].rejected_face_records(
            opaque_001.Shape,
            contract["component_001_healing"]["rejected_face_signature"],
        ):
            raise RuntimeError("saved FCStd reintroduced rejected Face6")
        return records
    finally:
        App.closeDocument(reopened.Name)


def write_readme(destination: Path, manifest: dict[str, Any]) -> None:
    destination.write_text(
        "# Lower-right connector integration print release V3\n\n"
        "Use this V3 package. V1 was rejected by the user; V2 was withheld after "
        "the final sanity render showed it had shortened the wrong feature. Both "
        "older packages remain unchanged as evidence.\n\n"
        "V3 makes the requested corrections:\n\n"
        "- The actual plank was the negative-X opposite-side half of the "
        "bilateral central translucent owner. V3 splits it exactly at global "
        "X=0 and keeps only X>=0 in this lower-right part.\n"
        "- Both approved 10 mm nose-top tabs are restored unchanged from the "
        "approved connector source.\n"
        "- The long zero-area Face6 is removed from opaque component 001 with "
        "the fixed 0.00002 mm native OCCT small-strip heal.\n\n"
        "All six STLs passed closed-manifold, single-component, outward-normal, "
        "zero-boundary-edge, zero-nonmanifold-edge, and zero-self-intersection "
        "checks. No 3MF, slicer profile, G-code, or printer-specific orientation "
        "is included.\n\n"
        f"Release status: {manifest['status']}\n",
        encoding="utf-8",
    )


def write_checkpoint(destination: Path, manifest: dict[str, Any]) -> None:
    central = manifest["source_evidence"]["central_translucent_owner_clip"]
    healing = manifest["source_evidence"]["component_001_healing"]
    destination.write_text(
        "# Lower-right connector V3 print-release checkpoint — 2026-08-21\n\n"
        f"Status: {manifest['status']}\n\n"
        "Use V3 only. V1 is user-rejected and V2 is withheld.\n\n"
        "Corrections:\n\n"
        f"- Central translucent owner: source X "
        f"[{central['source_min_x_mm']:.6f}, "
        f"{central['source_max_x_mm']:.6f}] mm; retained X "
        f"[{central['retained_min_x_mm']:.6f}, "
        f"{central['retained_max_x_mm']:.6f}] mm. Removed volume "
        f"{central['removed_volume_mm3']:.9f} mm^3 lies entirely at X<=0.\n"
        "- Approved 10 mm nose-top tabs restored directly from the pinned "
        "connector source.\n"
        f"- Component 001 rejected Face6 matches before="
        f"{len(healing['rejected_face_before'])}, after="
        f"{len(healing['rejected_face_after'])}; corrected valid/closed/"
        f"one-solid={healing['corrected']['valid']}/"
        f"{healing['corrected']['closed']}/"
        f"{healing['corrected']['solid_count']}.\n\n"
        "Validation: every manifest check passed; six FCStd BReps are valid, "
        "closed one-solids; six reloaded STL meshes are clean closed manifold "
        "single components.\n\n"
        "Regeneration command (from the cat-head project root):\n\n"
        "    env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib "
        "/tmp/freecad-1.1.3-extract/squashfs-root/AppRun python "
        "source/cad-change-control/print-release/"
        "lower-right-connector-integration-v3/export_release.py "
        "--mode preflight --report /tmp/lower-right-v3-preflight.json\n\n"
        "Then invoke --mode release with that report and its exact SHA-256.\n\n"
        "Next physical step: choose printer/material/orientation in the slicer; "
        "no slicing or G-code was authorized here.\n",
        encoding="utf-8",
    )


def release(bundle: dict[str, Any], report: dict[str, Any]) -> Path:
    contract = bundle["contract"]
    output_dir = project_path(contract["outputs"]["directory"])
    if output_dir.exists():
        raise RuntimeError(f"release output already exists: {output_dir}")

    with tempfile.TemporaryDirectory(
        prefix="lower-right-connector-integration-v3-"
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
            "cat-head-lower-right-connector-integration-release-manifest-v3"
        )
        manifest["status"] = RELEASE_PASS
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
        checkpoint = stage / str(contract["outputs"]["checkpoint"])
        write_readme(readme, manifest)
        write_checkpoint(checkpoint, manifest)
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
            "checkpoint": str(checkpoint.name),
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
            "checkpoint": sha256(checkpoint),
        }
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        checksum_path = stage / str(contract["outputs"]["checksums"])
        checksum_targets = [
            path
            for path in stage.rglob("*")
            if path.is_file() and path != checksum_path
        ]
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

    if verify_pins(contract) != bundle["pins"]:
        raise RuntimeError("an input changed during V3 release")
    for relative, expected in (
        (contract["outputs"]["fcstd"], manifest["output_sha256"]["fcstd"]),
        (contract["outputs"]["readme"], manifest["output_sha256"]["readme"]),
        (
            contract["outputs"]["checkpoint"],
            manifest["output_sha256"]["checkpoint"],
        ),
    ):
        if sha256(output_dir / str(relative)) != expected:
            raise RuntimeError(f"post-copy hash mismatch: {relative}")
    for part_id, expected in manifest["output_sha256"]["stls"].items():
        relative = (
            Path(contract["outputs"]["stl_directory"])
            / contract["outputs"]["parts"][part_id]
        )
        if sha256(output_dir / relative) != expected:
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
                    "failed_checks": report["failed_checks"],
                },
                sort_keys=True,
            )
        )
        return 0 if not report["failed_checks"] else 2

    if report["failed_checks"]:
        raise RuntimeError(
            "lower-right V3 release gates failed: "
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
        preflight.get("status") != PREFLIGHT_PASS
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
    print(json.dumps({"status": RELEASE_PASS, "output": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
