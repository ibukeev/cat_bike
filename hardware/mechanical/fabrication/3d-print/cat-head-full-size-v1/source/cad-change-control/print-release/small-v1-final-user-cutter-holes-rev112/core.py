#!/usr/bin/env python3
"""Shared, source-preserving FreeCAD kernel for the Rev112 user-cutter release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import FreeCAD as App
import MeshPart
import Part


def _find_repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("Repository root could not be located")


REPO_ROOT = _find_repo_root()
CONTRACT_PATH = REPO_ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-small-v1/config/v2/"
    "small-v1-final-user-cutter-holes-rev112.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _quantity_value(value) -> float:
    return float(value.Value if hasattr(value, "Value") else value)


def _vector_record(vector) -> list[float]:
    return [float(vector.x), float(vector.y), float(vector.z)]


def _bbox(shape) -> dict:
    bounds = shape.BoundBox
    return {
        "min_mm": [float(bounds.XMin), float(bounds.YMin), float(bounds.ZMin)],
        "max_mm": [float(bounds.XMax), float(bounds.YMax), float(bounds.ZMax)],
        "size_mm": [float(bounds.XLength), float(bounds.YLength), float(bounds.ZLength)],
    }


def _brep_sha256(shape) -> str:
    payload = shape.exportBrepToString()
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def shape_record(shape) -> dict:
    return {
        "shape_type": str(shape.ShapeType),
        "is_null": bool(shape.isNull()),
        "is_valid": bool(shape.isValid()),
        "is_closed": bool(shape.isClosed()),
        "solid_count": len(shape.Solids),
        "shell_count": len(shape.Shells),
        "face_count": len(shape.Faces),
        "edge_count": len(shape.Edges),
        "vertex_count": len(shape.Vertexes),
        "volume_mm3": float(shape.Volume),
        "surface_area_mm2": float(shape.Area),
        "bbox": _bbox(shape),
        "brep_sha256": _brep_sha256(shape),
    }


def require_closed_solids(shape, label: str, expected_count: int = 1) -> dict:
    record = shape_record(shape)
    if record["is_null"]:
        raise RuntimeError(f"{label} is null")
    if not record["is_valid"]:
        raise RuntimeError(f"{label} is invalid")
    if record["solid_count"] != expected_count:
        raise RuntimeError(
            f"{label} contains {record['solid_count']} solids; expected {expected_count}"
        )
    if any(not solid.isClosed() for solid in shape.Solids):
        raise RuntimeError(f"{label} contains an open solid")
    return record


def _symmetric_difference_record(first, second) -> dict:
    return {
        "first_minus_second_mm3": float(first.cut(second).Volume),
        "second_minus_first_mm3": float(second.cut(first).Volume),
    }


def _bbox_residual(first, second) -> float:
    first_values = _bbox(first)["min_mm"] + _bbox(first)["max_mm"]
    second_values = _bbox(second)["min_mm"] + _bbox(second)["max_mm"]
    return max(abs(a - b) for a, b in zip(first_values, second_values))


def _require_authority(contract: dict) -> None:
    approval = contract["approval"]
    for key in (
        "subtract_all_four_user_cutters_authorized",
        "create_new_final_head_body_authorized",
        "export_head_and_four_translucent_panels_authorized",
    ):
        if not approval[key]:
            raise RuntimeError(f"Rev112 lacks authority for {key}")
    for key in (
        "overwrite_source_fcstd_authorized",
        "change_translucent_panels_authorized",
        "change_existing_zip_tie_slots_authorized",
        "slicer_profile_or_gcode_authorized",
        "unrelated_geometry_authorized",
    ):
        if approval[key]:
            raise RuntimeError(f"Rev112 forbidden authority unexpectedly enabled: {key}")
    if contract["operation"]["method"] != "TARGET_MINUS_CUMULATIVE_CUTTER_BODY_ONCE":
        raise RuntimeError("Rev112 Boolean method changed")


def _required_object(document, name: str):
    obj = document.getObject(name)
    if obj is None:
        raise RuntimeError(f"Required source object is absent: {name}")
    return obj


def _mesh_record(shape, contract: dict) -> dict:
    validation = contract["validation"]
    mesh = MeshPart.meshFromShape(
        Shape=shape,
        LinearDeflection=validation["mesh_linear_deflection_mm"],
        AngularDeflection=validation["mesh_angular_deflection_rad"],
        Relative=False,
    )
    if mesh.CountFacets <= 0:
        raise RuntimeError("In-memory mesh preflight produced no facets")
    return {
        "facets": int(mesh.CountFacets),
        "points": int(mesh.CountPoints),
        "volume_mm3": float(mesh.Volume),
    }


def construct_package(contract: dict) -> dict:
    """Read the pinned user file, apply its cumulative cutter body once, and close it unsaved."""
    _require_authority(contract)
    source = contract["source"]
    validation = contract["validation"]
    source_path = REPO_ROOT / source["path"]
    source_hash_before = sha256(source_path)
    if source_hash_before != source["sha256"]:
        raise RuntimeError("Pinned CAT_HEAD_MEDIUM_Ilya_FINAL_EDITS.FCStd hash mismatch")

    print("Rev112 stage 1 of 7: open the hash-pinned user FCStd read-only", flush=True)
    document = App.openDocument(str(source_path))
    try:
        head_object = _required_object(document, source["approved_head_object"])
        cutter_body = _required_object(document, source["cutter_body_object"])
        if cutter_body.Label != source["cutter_body_label"]:
            raise RuntimeError("The pinned cutter body label changed")
        if cutter_body.Tip is None or cutter_body.Tip.Name != source["cumulative_tip_object"]:
            raise RuntimeError("Cutter4/Pad003 is no longer the cumulative cutter body tip")

        head = head_object.Shape.copy()
        cutter_compound = cutter_body.Shape.copy()
        head_record = require_closed_solids(head, "Rev112 source head", 1)
        compound_record = require_closed_solids(
            cutter_compound,
            "Rev112 cumulative user cutter compound",
            source["expected_cutter_compound_solid_count"],
        )

        print("Rev112 stage 2 of 7: inventory the four individual AddSubShape cutters", flush=True)
        individual_cutters = []
        cutter_records = []
        for index, cutter_contract in enumerate(source["individual_cutters"], start=1):
            obj = _required_object(document, cutter_contract["object"])
            if obj.Label != cutter_contract["label"]:
                raise RuntimeError(f"Cutter{index} label changed")
            length = _quantity_value(obj.Length)
            if abs(length - cutter_contract["expected_length_mm"]) > validation["length_tolerance_mm"]:
                raise RuntimeError(f"Cutter{index} length changed from the approved -10 mm")
            property_name = source["individual_cutter_shape_property"]
            if property_name not in obj.PropertiesList:
                raise RuntimeError(f"Cutter{index} lacks {property_name}")
            shape = getattr(obj, property_name).copy()
            record = require_closed_solids(shape, f"Rev112 Cutter{index} AddSubShape", 1)
            direction = _vector_record(obj.Direction) if hasattr(obj, "Direction") else None
            record.update({
                "index": index,
                "object": obj.Name,
                "label": obj.Label,
                "length_mm": length,
                "direction": direction,
            })
            individual_cutters.append(shape)
            cutter_records.append(record)
        if len(individual_cutters) != source["expected_cutter_count"]:
            raise RuntimeError("Rev112 cutter count changed")

        individual_compound = Part.makeCompound(individual_cutters)
        compound_equivalence = _symmetric_difference_record(cutter_compound, individual_compound)
        if max(compound_equivalence.values()) > validation["boolean_residual_volume_maximum_mm3"]:
            raise RuntimeError("The Cutter4 body tip is not exactly the four individual cutter solids")

        print("Rev112 stage 3 of 7: prove every individual cutter intersects the Rev108 head", flush=True)
        individual_overlaps = []
        for index, shape in enumerate(individual_cutters, start=1):
            overlap = float(head.common(shape).Volume)
            if overlap < validation["minimum_individual_cutter_overlap_mm3"]:
                raise RuntimeError(f"Cutter{index} does not remove enough head material")
            individual_overlaps.append(overlap)
            cutter_records[index - 1]["source_head_overlap_mm3"] = overlap
        aggregate_overlap = float(head.common(cutter_compound).Volume)
        overlap_sum_residual = abs(aggregate_overlap - sum(individual_overlaps))
        if overlap_sum_residual > validation["shape_volume_tolerance_mm3"]:
            raise RuntimeError("Individual cutter overlaps do not reconcile with the cumulative tool")

        pane_sources = {}
        pane_source_records = {}
        for key, object_name in source["protected_panes"].items():
            pane = _required_object(document, object_name).Shape.copy()
            pane_sources[key] = pane
            pane_source_records[key] = require_closed_solids(pane, f"Rev112 protected {key} pane", 1)
        if len(pane_sources) != contract["operation"]["expected_protected_pane_count"]:
            raise RuntimeError("Protected pane count changed")

        zip_corridors = {}
        zip_source_residuals = {}
        for side, object_name in source["existing_zip_tie_corridors"].items():
            corridor = _required_object(document, object_name).Shape.copy()
            require_closed_solids(corridor, f"Rev112 {side} zip-tie corridor", 1)
            zip_corridors[side] = corridor
            zip_source_residuals[side] = float(head.common(corridor).Volume)
        if max(zip_source_residuals.values()) > validation["zip_tie_corridor_residual_volume_maximum_mm3"]:
            raise RuntimeError("A source zip-tie corridor is not through-open before Rev112")
    finally:
        App.closeDocument(document.Name)

    source_hash_after_read = sha256(source_path)
    if source_hash_after_read != source_hash_before:
        raise RuntimeError("Source FCStd changed while its shapes were copied")

    print("Rev112 stage 4 of 7: subtract the cumulative four-solid cutter body exactly once", flush=True)
    final_head = head.cut(cutter_compound)
    final_head_record = require_closed_solids(
        final_head,
        "Rev112 final printable head",
        contract["operation"]["expected_final_head_solid_count"],
    )

    print("Rev112 stage 5 of 7: verify Boolean conservation and zero cutter residual", flush=True)
    removed_volume = float(head.Volume) - float(final_head.Volume)
    removed_volume_residual = abs(removed_volume - aggregate_overlap)
    if removed_volume_residual > validation["shape_volume_tolerance_mm3"]:
        raise RuntimeError("Rev112 removed volume disagrees with source/cutter intersection")
    cutter_residual = float(final_head.common(cutter_compound).Volume)
    if cutter_residual > validation["boolean_residual_volume_maximum_mm3"]:
        raise RuntimeError("Rev112 final head still occupies the cutter compound")
    added_volume = float(final_head.cut(head).Volume)
    if added_volume > validation["boolean_residual_volume_maximum_mm3"]:
        raise RuntimeError("Rev112 subtraction added material outside the source head")
    bbox_residual = _bbox_residual(final_head, head)
    if bbox_residual > validation["bbox_tolerance_mm"]:
        raise RuntimeError("Rev112 subtraction changed the frozen head bounds")

    print("Rev112 stage 6 of 7: prove panes unchanged and both zip-tie slots still open", flush=True)
    pane_preservation = {}
    pane_head_overlaps = {}
    panes = {key: shape.copy() for key, shape in pane_sources.items()}
    for key, pane in panes.items():
        difference = _symmetric_difference_record(pane_sources[key], pane)
        if max(difference.values()) > validation["pane_shape_residual_volume_maximum_mm3"]:
            raise RuntimeError(f"Rev112 changed the protected {key} pane")
        pane_preservation[key] = difference
        pane_head_overlaps[key] = float(pane.common(final_head).Volume)
    if max(pane_head_overlaps.values()) > validation["pane_head_overlap_maximum_mm3"]:
        raise RuntimeError("A protected translucent pane collides with the final head")
    zip_final_residuals = {
        side: float(final_head.common(shape).Volume) for side, shape in zip_corridors.items()
    }
    if max(zip_final_residuals.values()) > validation["zip_tie_corridor_residual_volume_maximum_mm3"]:
        raise RuntimeError("A Rev112 zip-tie corridor is no longer through-open")

    print("Rev112 stage 7 of 7: tessellate all five print parts in memory", flush=True)
    mesh_preflight = {"head": _mesh_record(final_head, contract)}
    mesh_preflight.update({key: _mesh_record(shape, contract) for key, shape in panes.items()})
    source_hash_after = sha256(source_path)
    if source_hash_after != source_hash_before:
        raise RuntimeError("Source FCStd changed during Rev112 construction")

    return {
        "head_before": head,
        "final_head": final_head,
        "cutter_compound": cutter_compound,
        "individual_cutters": individual_cutters,
        "panes": panes,
        "zip_corridors": zip_corridors,
        "evidence": {
            "construction_method": contract["operation"]["method"],
            "source_sha256_before": source_hash_before,
            "source_sha256_after": source_hash_after,
            "source_head": head_record,
            "cutter_compound": compound_record,
            "cutter_compound_equivalence": compound_equivalence,
            "individual_cutters": cutter_records,
            "individual_cutter_overlaps_mm3": individual_overlaps,
            "aggregate_cutter_overlap_mm3": aggregate_overlap,
            "aggregate_overlap_sum_residual_mm3": overlap_sum_residual,
            "final_head": final_head_record,
            "removed_volume_mm3": removed_volume,
            "removed_volume_residual_mm3": removed_volume_residual,
            "cutter_residual_volume_mm3": cutter_residual,
            "added_volume_outside_source_mm3": added_volume,
            "bbox_residual_mm": bbox_residual,
            "protected_panes": pane_source_records,
            "pane_preservation_residuals_mm3": pane_preservation,
            "pane_final_head_overlaps_mm3": pane_head_overlaps,
            "zip_tie_source_residuals_mm3": zip_source_residuals,
            "zip_tie_final_residuals_mm3": zip_final_residuals,
            "mesh_preflight": mesh_preflight,
            "slicer_project_created_or_changed": False,
            "gcode_created": False,
        },
    }


def set_property(obj, property_type: str, name: str, value, group: str = "Revision 112") -> None:
    if name not in obj.PropertiesList:
        obj.addProperty(property_type, name, group)
    setattr(obj, name, value)


def finalize_document(document, package: dict, contract: dict) -> dict:
    """Assign Rev112 shapes to a clean document. This function never saves or exports."""
    print_group = document.addObject("App::DocumentObjectGroup", "PRINT_PARTS__REV112")
    print_group.Label = "PRINT PARTS — Rev112 final head body plus four unchanged translucent panes"

    head_body = document.addObject("PartDesign::Body", "FINAL_HEAD_BODY_REV112")
    head_body.Label = "PRINT — FINAL HEAD BODY REV112; four user-cutter holes"
    head_feature = head_body.newObject("PartDesign::Feature", "PRINT__CAT_HEAD_FINAL_CUT_HOLES_REV112")
    head_feature.Label = "PRINT — final head; 4 user-cutter holes; 12 stops; 2 zip slots open"
    head_feature.Shape = package["final_head"].copy()
    set_property(head_feature, "App::PropertyString", "DesignId", contract["design_id"])
    set_property(head_feature, "App::PropertyString", "SourceSha256", contract["source"]["sha256"])
    set_property(head_feature, "App::PropertyInteger", "UserCutterHoleCount", 4)
    set_property(head_feature, "App::PropertyInteger", "IntegratedStopCount", 12)
    set_property(head_feature, "App::PropertyInteger", "ZipTieThroughSlotCount", 2)
    set_property(head_feature, "App::PropertyBool", "Printable", True)
    print_group.addObject(head_body)

    pane_names = {
        "right_eye": ("PRINT__RIGHT_EYE_TRANSLUCENT_PANE_REV112", "PRINT — unchanged right-eye translucent pane"),
        "left_eye": ("PRINT__LEFT_EYE_TRANSLUCENT_PANE_REV112", "PRINT — unchanged left-eye translucent pane"),
        "mouth_TRI005": ("PRINT__MOUTH_TRI005_TRANSLUCENT_PANE_REV112", "PRINT — unchanged mouth TRI005 translucent pane"),
        "mouth_TRI006": ("PRINT__MOUTH_TRI006_TRANSLUCENT_PANE_REV112", "PRINT — unchanged mouth TRI006 translucent pane"),
    }
    pane_objects = {}
    for key, (name, label) in pane_names.items():
        pane = document.addObject("Part::Feature", name)
        pane.Label = label
        pane.Shape = package["panes"][key].copy()
        set_property(pane, "App::PropertyLength", "PETGThickness", 2.0)
        set_property(pane, "App::PropertyInteger", "HoleCount", 0)
        set_property(pane, "App::PropertyBool", "GeometryProtectedFromRev108", True)
        set_property(pane, "App::PropertyBool", "Printable", True)
        print_group.addObject(pane)
        pane_objects[key] = pane

    evidence_group = document.addObject("App::DocumentObjectGroup", "REVIEW_EVIDENCE__REV112")
    evidence_group.Label = "REVIEW EVIDENCE — hidden source head, four cutters, and zip corridors"
    evidence_shapes = {
        "REFERENCE__REV108_HEAD_BEFORE_USER_CUTTERS": package["head_before"],
        "REVIEW_ONLY__USER_CUTTER_COMPOUND_REV112": package["cutter_compound"],
        "REVIEW_ONLY__CUTTER1_REV112": package["individual_cutters"][0],
        "REVIEW_ONLY__CUTTER2_REV112": package["individual_cutters"][1],
        "REVIEW_ONLY__CUTTER3_REV112": package["individual_cutters"][2],
        "REVIEW_ONLY__CUTTER4_REV112": package["individual_cutters"][3],
        "REVIEW_ONLY__RIGHT_ZIP_TIE_CORRIDOR_REV112": package["zip_corridors"]["right"],
        "REVIEW_ONLY__LEFT_ZIP_TIE_CORRIDOR_REV112": package["zip_corridors"]["left"],
    }
    evidence_objects = {}
    for name, shape in evidence_shapes.items():
        obj = document.addObject("Part::Feature", name)
        obj.Label = name.replace("__", " — ").replace("_", " ")
        obj.Shape = shape.copy()
        evidence_group.addObject(obj)
        evidence_objects[name] = obj

    parameters = document.addObject("Spreadsheet::Sheet", "Rev112FinalCutParameters")
    values = (
        ("A1", "Parameter"), ("B1", "Value"),
        ("A2", "SourceRevision"), ("B2", "REV108 user-edited final MVP"),
        ("A3", "BooleanMethod"), ("B3", "head minus Cutters/Pad003 once"),
        ("A4", "UserCutterCount"), ("B4", "4"),
        ("A5", "FinalHeadSolidCount"), ("B5", "1"),
        ("A6", "IntegratedStopCount"), ("B6", "12"),
        ("A7", "ZipTieThroughSlotCount"), ("B7", "2"),
        ("A8", "ProtectedPaneCount"), ("B8", "4"),
        ("A9", "SlicerProjectChanged"), ("B9", "NO"),
    )
    for cell, value in values:
        parameters.set(cell, value)
    document.recompute()

    require_closed_solids(head_feature.Shape, "Finalized Rev112 head body", 1)
    for key, pane in pane_objects.items():
        require_closed_solids(pane.Shape, f"Finalized Rev112 {key} pane", 1)
    if head_feature.Placement != App.Placement():
        raise RuntimeError("Rev112 final head feature placement is not identity")
    if any(pane.Placement != App.Placement() for pane in pane_objects.values()):
        raise RuntimeError("A Rev112 pane placement is not identity")

    return {
        "print_group": print_group.Name,
        "head_body": head_body.Name,
        "head_object": head_feature.Name,
        "pane_objects": {key: obj.Name for key, obj in pane_objects.items()},
        "review_evidence_group": evidence_group.Name,
        "review_evidence_objects": list(evidence_objects),
        "parameter_sheet": parameters.Name,
        "target_assignment_performed": True,
        "typed_metadata_assignment_performed": True,
        "recompute_performed": True,
        "final_assertions_performed": True,
    }
