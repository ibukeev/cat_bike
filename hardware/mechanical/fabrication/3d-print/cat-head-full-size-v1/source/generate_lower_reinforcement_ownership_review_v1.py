#!/usr/bin/env python3
"""Inventory whole Gate 8 lower-head reinforcement against the approved V5 seam.

This is an ownership-only review. Existing connected reinforcement components
are copied without changing their geometry, then classified by verified contact
with retained and/or cassette source facets. Components are never split here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector
from mathutils.geometry import closest_point_on_tri


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_rear_cassette_lossless_repartition_review_v5 as v5  # noqa: E402
import generate_rear_cassette_seam_review_v2 as seam_v2  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/lower-reinforcement-ownership-review-v1.json"
DEFAULT_OUTPUT = PACKAGE_ROOT / "output/lower-reinforcement-ownership-review-v1"
CLASSIFICATIONS = ("retained", "cassette", "crossing", "unclassified")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def hex_color(value: str) -> tuple[float, float, float, float]:
    clean = value.lstrip("#")
    return tuple(int(clean[offset : offset + 2], 16) / 255.0 for offset in (0, 2, 4)) + (1.0,)


def canonical_face(points: list[Vector]) -> tuple[tuple[float, float, float], ...]:
    return tuple(sorted(tuple(round(axis, 7) for axis in point) for point in points))


def polygon_fingerprint(
    obj: bpy.types.Object,
    polygon_indices: list[int] | None = None,
) -> str:
    transform = obj.matrix_world
    polygons = (
        obj.data.polygons
        if polygon_indices is None
        else (obj.data.polygons[index] for index in polygon_indices)
    )
    tokens = []
    for polygon in polygons:
        tokens.append(
            canonical_face(
                [transform @ obj.data.vertices[index].co for index in polygon.vertices]
            )
        )
    digest = hashlib.sha256()
    for token in sorted(tokens):
        digest.update(f"{token}\n".encode())
    return digest.hexdigest()


def build_ownership_sets(
    review_config: dict[str, Any],
    interface: dict[str, Any],
) -> tuple[Any, list[str], list[Vector], dict[str, set[int]], dict[str, set[int]]]:
    v5_config = json.loads(
        repo_path(review_config["source_v5_config"]).read_text(encoding="utf-8")
    )
    selection_config = dict(v5_config)
    selection_config["rear_cassette_cut"] = dict(v5_config["repartition"])
    model, assignments, points, selected, _seam = seam_v2.source_selection(
        selection_config, interface
    )
    points = [Vector(value) for value in points]
    sections = tuple(review_config["target_sections"])

    gate8_config = json.loads(
        repo_path(review_config["source_gate8_config"]).read_text(encoding="utf-8")
    )
    expected_opaque = {
        section: set(
            gate8_config["opaque_muzzle_frame"]["opaque_panel_groups"][section]
        )
        for section in sections
    }
    configured_opaque = {
        section: set(v5_config["restored_gate8_lower_opaque_panels"][section])
        for section in sections
    }
    if expected_opaque != configured_opaque:
        raise ValueError(
            "Approved V5 opaque lower-panel ownership no longer matches Gate 8"
        )
    panel_owner = {
        panel_id: section
        for section, panel_ids in configured_opaque.items()
        for panel_id in panel_ids
    }
    opaque_indices = {section: set() for section in sections}
    for index, face in enumerate(model.faces):
        panel_id = gate1.canonical_source_panel_id(face.group)
        owner = panel_owner.get(panel_id)
        if owner is not None:
            if assignments[index] != "removable_glow":
                raise ValueError(
                    f"Expected {panel_id} to retain its removable_glow source tag"
                )
            opaque_indices[owner].add(index)
    if any(len(indices) != 3 for indices in opaque_indices.values()):
        raise ValueError(f"Expected three opaque source faces per side: {opaque_indices}")

    all_by_section = {
        section: {
            index
            for index, assignment in enumerate(assignments)
            if assignment == section
        }
        | opaque_indices[section]
        for section in sections
    }
    selected_by_section = {
        section: {
            index for index in selected if assignments[index] == section
        }
        for section in sections
    }
    retained_by_section = {
        section: all_by_section[section] - selected_by_section[section]
        for section in sections
    }
    if any(len(indices) != 5 for indices in selected_by_section.values()):
        raise ValueError("Approved V5 moved-facet selection is no longer five per side")
    return model, assignments, points, retained_by_section, selected_by_section


def triangulated_face_records(
    model: Any,
    points: list[Vector],
    face_indices: set[int],
) -> list[dict[str, Any]]:
    records = []
    for face_index in sorted(face_indices):
        face = model.faces[face_index]
        vertices = [points[index] for index in face.indices]
        for offset in range(1, len(vertices) - 1):
            records.append(
                {
                    "face_index": face_index,
                    "panel_id": gate1.canonical_source_panel_id(face.group),
                    "triangle": (vertices[0], vertices[offset], vertices[offset + 1]),
                }
            )
    return records


def closest_record(
    point: Vector,
    records: list[dict[str, Any]],
) -> tuple[float, dict[str, Any]]:
    best_distance = float("inf")
    best_record = records[0]
    for record in records:
        closest = closest_point_on_tri(point, *record["triangle"])
        distance = (point - closest).length
        if distance < best_distance:
            best_distance = distance
            best_record = record
    return best_distance, best_record


def classify_component(
    source: bpy.types.Object,
    vertex_indices: list[int],
    retained_faces: list[dict[str, Any]],
    cassette_faces: list[dict[str, Any]],
    maximum_distance: float,
    tie_tolerance: float,
) -> dict[str, Any]:
    contacts = Counter()
    contact_faces = {"retained": set(), "cassette": set()}
    contact_panels = {"retained": set(), "cassette": set()}
    minimum = {"retained": float("inf"), "cassette": float("inf")}
    transform = source.matrix_world
    for vertex_index in vertex_indices:
        point = transform @ source.data.vertices[vertex_index].co
        retained_distance, retained_record = closest_record(point, retained_faces)
        cassette_distance, cassette_record = closest_record(point, cassette_faces)
        minimum["retained"] = min(minimum["retained"], retained_distance)
        minimum["cassette"] = min(minimum["cassette"], cassette_distance)
        retained_close = retained_distance <= maximum_distance
        cassette_close = cassette_distance <= maximum_distance
        owners = []
        if retained_close and cassette_close and abs(retained_distance - cassette_distance) <= tie_tolerance:
            owners = ["retained", "cassette"]
        elif retained_close and (not cassette_close or retained_distance < cassette_distance):
            owners = ["retained"]
        elif cassette_close:
            owners = ["cassette"]
        for owner in owners:
            record = retained_record if owner == "retained" else cassette_record
            contacts[owner] += 1
            contact_faces[owner].add(record["face_index"])
            contact_panels[owner].add(record["panel_id"])

    owners = {owner for owner in ("retained", "cassette") if contacts[owner]}
    if owners == {"retained"}:
        classification = "retained"
    elif owners == {"cassette"}:
        classification = "cassette"
    elif owners == {"retained", "cassette"}:
        classification = "crossing"
    else:
        classification = "unclassified"
    return {
        "classification": classification,
        "contact_vertex_count": dict(contacts),
        "contact_face_indices": {
            owner: sorted(values) for owner, values in contact_faces.items()
        },
        "contact_panel_ids": {
            owner: sorted(values) for owner, values in contact_panels.items()
        },
        "minimum_surface_distance_mm": {
            owner: round(value, 4) for owner, value in minimum.items()
        },
    }


def component_inventory(
    source: bpy.types.Object,
    target_materials: set[str],
) -> list[dict[str, Any]]:
    material_names = [material.name if material else None for material in source.data.materials]
    target_indices = {
        index for index, name in enumerate(material_names) if name in target_materials
    }
    components = gate5.components(source)
    component_at_vertex = {
        vertex_index: component_index
        for component_index, vertices in enumerate(components)
        for vertex_index in vertices
    }
    polygons_by_component: dict[int, list[int]] = defaultdict(list)
    area_by_component_material: dict[int, Counter] = defaultdict(Counter)
    for polygon in source.data.polygons:
        component_index = component_at_vertex[polygon.vertices[0]]
        if any(component_at_vertex[index] != component_index for index in polygon.vertices):
            raise ValueError(f"{source.name} polygon spans connected components")
        polygons_by_component[component_index].append(polygon.index)
        area_by_component_material[component_index][polygon.material_index] += polygon.area

    output = []
    for component_index, vertex_indices in enumerate(components):
        area_by_material = area_by_component_material[component_index]
        total_area = sum(area_by_material.values())
        reinforcement_area = sum(
            area for material_index, area in area_by_material.items()
            if material_index in target_indices
        )
        if total_area <= 0.0 or reinforcement_area <= 0.0:
            continue
        dominant_index = max(
            (
                material_index
                for material_index in area_by_material
                if material_index in target_indices
            ),
            key=area_by_material.get,
        )
        dominant_material = material_names[dominant_index]
        output.append(
            {
                "source_component_index": component_index,
                "vertex_indices": sorted(vertex_indices),
                "polygon_indices": polygons_by_component[component_index],
                "dominant_material": dominant_material,
                "reinforcement_area_fraction": reinforcement_area / total_area,
                "volume_mm3": gate5.component_volume(source, vertex_indices),
                "source_fingerprint": polygon_fingerprint(
                    source, polygons_by_component[component_index]
                ),
            }
        )
    return output


def target_material_coverage(
    source: bpy.types.Object,
    records: list[dict[str, Any]],
    target_materials: set[str],
) -> dict[str, Any]:
    material_names = [material.name if material else None for material in source.data.materials]
    target_indices = {
        index for index, name in enumerate(material_names) if name in target_materials
    }
    source_target_polygons = {
        polygon.index
        for polygon in source.data.polygons
        if polygon.material_index in target_indices
    }
    covered_target_polygons = {
        polygon_index
        for record in records
        for polygon_index in record["polygon_indices"]
        if source.data.polygons[polygon_index].material_index in target_indices
    }
    coverage = Counter()
    for record in records:
        for polygon_index in record["polygon_indices"]:
            if polygon_index in source_target_polygons:
                coverage[polygon_index] += 1
    duplicate_count = sum(count - 1 for count in coverage.values() if count > 1)
    missing = source_target_polygons - covered_target_polygons
    return {
        "source_target_material_polygon_count": len(source_target_polygons),
        "inventoried_target_material_polygon_count": len(covered_target_polygons),
        "missing_target_material_polygon_count": len(missing),
        "duplicated_target_material_polygon_count": duplicate_count,
        "all_target_material_polygons_inventoried_once": not missing
        and duplicate_count == 0,
    }


def material_short_name(name: str | None) -> str:
    mapping = {
        "Gate5_internal_flange_tabs": "flange",
        "Gate5_internal_panel_ribs": "rib",
        "Gate6_eye_head_mount_flange": "eye_mount",
        "Gate8_continuous_inter_shell_edge_rails": "seam_rail",
    }
    return mapping.get(name, "reinforcement")


def create_component_copy(
    source: bpy.types.Object,
    section: str,
    record: dict[str, Any],
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> bpy.types.Object:
    used = sorted(record["vertex_indices"])
    remap = {source_index: local_index for local_index, source_index in enumerate(used)}
    faces = [
        tuple(remap[index] for index in source.data.polygons[polygon_index].vertices)
        for polygon_index in record["polygon_indices"]
    ]
    section_short = "L" if section.startswith("left") else "R"
    classification_short = {
        "retained": "RET",
        "cassette": "CAS",
        "crossing": "CROSS",
        "unclassified": "UNCL",
    }[record["classification"]]
    name = (
        f"R1_{classification_short}__{section_short}__C"
        f"{record['source_component_index']:03d}__"
        f"{material_short_name(record['dominant_material'])}"
    )
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata([tuple(source.data.vertices[index].co) for index in used], [], faces)
    mesh.update(calc_edges=True)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.matrix_world = source.matrix_world.copy()
    obj["review_only"] = True
    obj["source_section"] = section
    obj["source_component_index"] = record["source_component_index"]
    obj["dominant_source_material"] = record["dominant_material"] or "None"
    obj["ownership_classification"] = record["classification"]
    obj["contact_panel_ids"] = json.dumps(record["contact_panel_ids"], sort_keys=True)
    obj["source_geometry_fingerprint"] = record["source_fingerprint"]
    return obj


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def configure_scene(output_dir: Path, resolution_px: int) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.name = "Lower_Reinforcement_Ownership_Review_V1"
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    shading.curvature_ridge_factor = 2.0
    shading.curvature_valley_factor = 1.5
    shading.background_type = "VIEWPORT"
    shading.background_color = (0.035, 0.045, 0.06)
    scene.render.resolution_x = resolution_px
    scene.render.resolution_y = resolution_px
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    camera_data = bpy.data.cameras.new("R1_REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("R1_REVIEW_ONLY__Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 54.0
    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    return camera


def render_views(
    camera: bpy.types.Object,
    output_dir: Path,
    prefix: str,
    visible_objects: set[bpy.types.Object],
) -> list[str]:
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_render = obj not in visible_objects
    target = Vector((0.0, 175.0, 105.0))
    views = (
        ("rear", Vector((0.0, 570.0, 205.0))),
        ("rear-left", Vector((-390.0, 500.0, 235.0))),
        ("rear-right", Vector((390.0, 500.0, 235.0))),
        ("front", Vector((0.0, -500.0, 190.0))),
        ("left", Vector((-500.0, 145.0, 190.0))),
        ("right", Vector((500.0, 145.0, 190.0))),
    )
    paths = []
    for label, location in views:
        camera.location = location
        point_at(camera, target)
        path = output_dir / "renders" / f"{prefix}-{label}.png"
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        paths.append(str(path.relative_to(REPO_ROOT)))
    return paths


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_blend = repo_path(config["source_v5_blend"])
    if Path(bpy.data.filepath).resolve() != source_blend:
        raise ValueError(f"Open the configured V5 blend before running: {source_blend}")
    interface_path = repo_path(config["shared_interface_path"])
    interface = json.loads(interface_path.read_text(encoding="utf-8"))
    if interface["interface_revision"] != config["required_interface_revision"]:
        raise ValueError("Shared shell/aluminum interface revision changed")
    output_dir.mkdir(parents=True, exist_ok=True)

    protected_before = {
        obj.name: v5.mesh_fingerprint(obj)
        for obj in bpy.data.objects
        if obj.type == "MESH"
    }
    model, _assignments, points, retained_sets, cassette_sets = build_ownership_sets(
        config, interface
    )
    target_materials = set(config["reinforcement_materials"])
    maximum_distance = float(
        config["ownership_contact"]["maximum_surface_distance_mm"]
    )
    tie_tolerance = float(
        config["ownership_contact"]["retained_cassette_tie_tolerance_mm"]
    )

    materials = {
        "retained": gate5.material(
            "R1__Retained_Lower_Reinforcement_Cyan",
            hex_color(config["review_display"]["retained_reinforcement_color"]),
        ),
        "cassette": gate5.material(
            "R1__Cassette_Reinforcement_Orange",
            hex_color(config["review_display"]["cassette_reinforcement_color"]),
        ),
        "crossing": gate5.material(
            "R1__Crosses_Approved_Seam_Red",
            hex_color(config["review_display"]["crossing_reinforcement_color"]),
        ),
        "unclassified": gate5.material(
            "R1__Unclassified_Reinforcement_Magenta",
            hex_color(config["review_display"]["unclassified_reinforcement_color"]),
        ),
    }
    collection_names = {
        "retained": "R1_REINFORCEMENT__RETAINED_LOWER",
        "cassette": "R1_REINFORCEMENT__REAR_CASSETTE",
        "crossing": "R1_REINFORCEMENT__CROSSES_APPROVED_SEAM",
        "unclassified": "R1_REINFORCEMENT__UNCLASSIFIED",
    }
    collections = {}
    for classification, name in collection_names.items():
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        collections[classification] = collection
    integrated_collection = bpy.data.collections.new(
        "R1_INTEGRATED_SHELL_PLUS_REINFORCEMENT"
    )
    bpy.context.scene.collection.children.link(integrated_collection)

    review_objects = []
    standalone_review_objects = []
    records = []
    material_coverage_by_section = {}
    for section in config["target_sections"]:
        source = bpy.data.objects.get(section)
        if source is None or source.type != "MESH":
            raise ValueError(f"Missing unchanged Gate 8 source object {section}")
        retained_faces = triangulated_face_records(model, points, retained_sets[section])
        cassette_faces = triangulated_face_records(model, points, cassette_sets[section])
        inventory_records = component_inventory(source, target_materials)
        material_coverage = target_material_coverage(
            source, inventory_records, target_materials
        )
        material_coverage_by_section[section] = material_coverage
        if not material_coverage["all_target_material_polygons_inventoried_once"]:
            raise ValueError(
                f"Reinforcement material coverage is incomplete for {section}: "
                f"{material_coverage}"
            )
        for inventory_record in inventory_records:
            classification = classify_component(
                source,
                inventory_record["vertex_indices"],
                retained_faces,
                cassette_faces,
                maximum_distance,
                tie_tolerance,
            )
            record = {
                "section": section,
                **inventory_record,
                **classification,
            }
            record["shell_integrated"] = (
                record["reinforcement_area_fraction"]
                < float(
                    config[
                        "standalone_component_minimum_reinforcement_area_fraction"
                    ]
                )
            )
            destination_collection = (
                integrated_collection
                if record["shell_integrated"]
                else collections[record["classification"]]
            )
            review = create_component_copy(
                source,
                section,
                record,
                destination_collection,
                materials[record["classification"]],
            )
            record["review_object"] = review.name
            record["review_fingerprint"] = polygon_fingerprint(review)
            boundary, nonmanifold = gate5.topology_counts(review)
            record["boundary_edges"] = boundary
            record["nonmanifold_edges"] = nonmanifold
            review_objects.append(review)
            if not record["shell_integrated"]:
                standalone_review_objects.append(review)
            records.append(record)

    protected_after = {
        name: v5.mesh_fingerprint(bpy.data.objects[name])
        for name in protected_before
    }
    source_digest = hashlib.sha256()
    review_digest = hashlib.sha256()
    for record in sorted(records, key=lambda value: (value["section"], value["source_component_index"])):
        source_digest.update(f"{record['source_fingerprint']}\n".encode())
        review_digest.update(f"{record['review_fingerprint']}\n".encode())
    if source_digest.hexdigest() != review_digest.hexdigest():
        raise ValueError("Reinforcement review copies do not match source geometry")
    if protected_before != protected_after:
        raise ValueError("A protected V5/Gate 8 mesh changed during review generation")
    if any(record["boundary_edges"] or record["nonmanifold_edges"] for record in records):
        raise ValueError("A copied reinforcement component is not closed and manifold")

    context_objects = {
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and (
            obj.name.startswith("V5_RETAINED__")
            or obj.name.startswith("V5_CASSETTE__moved_from_")
        )
    }
    seam_objects = {
        obj for obj in bpy.data.objects if obj.name.startswith("V5_BOUNDARY__")
    }
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in set(review_objects) | context_objects | seam_objects
            obj.hide_render = True
    for obj in context_objects:
        obj.display_type = "WIRE"
        obj.show_in_front = True
    for obj in seam_objects:
        obj.show_in_front = True

    camera = configure_scene(
        output_dir, int(config["review_display"]["render_resolution_px"])
    )
    render_paths = render_views(
        camera,
        output_dir,
        "reinforcement-ownership-isolated",
        set(standalone_review_objects),
    )
    render_paths.extend(
        render_views(
            camera,
            output_dir,
            "reinforcement-ownership-with-v5-seam",
            set(standalone_review_objects) | seam_objects,
        )
    )

    default_visible = set(standalone_review_objects) | context_objects | seam_objects
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in default_visible
            obj.hide_render = obj not in default_visible
    camera.location = Vector((0.0, 570.0, 205.0))
    point_at(camera, Vector((0.0, 175.0, 105.0)))

    counts_by_classification = Counter(
        record["classification"] for record in records
    )
    standalone_counts_by_classification = Counter(
        record["classification"]
        for record in records
        if not record["shell_integrated"]
    )
    integrated_counts_by_classification = Counter(
        record["classification"]
        for record in records
        if record["shell_integrated"]
    )
    counts_by_section = Counter(record["section"] for record in records)
    counts_by_material = Counter(record["dominant_material"] for record in records)
    integrated_count = sum(1 for record in records if record["shell_integrated"])
    scene = bpy.context.scene
    scene["review_status"] = config["status"]
    scene["classification_legend"] = (
        "cyan=retained lower; orange=rear cassette; red=crosses approved seam; "
        "magenta=unclassified"
    )
    scene["source_geometry_unchanged"] = True
    scene["reinforcement_component_count"] = len(records)

    blend_path = output_dir / "lower-reinforcement-ownership-review-v1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    report = {
        "status": config["status"],
        "source_v5_blend": str(source_blend.relative_to(REPO_ROOT)),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "interface_revision": interface["interface_revision"],
        "classification_rule": config["ownership_contact"],
        "target_reinforcement_materials": sorted(target_materials),
        "target_material_coverage_by_section": material_coverage_by_section,
        "component_count": len(records),
        "standalone_component_count": len(standalone_review_objects),
        "integrated_shell_plus_reinforcement_component_count": integrated_count,
        "component_count_by_classification": dict(sorted(counts_by_classification.items())),
        "standalone_component_count_by_classification": dict(
            sorted(standalone_counts_by_classification.items())
        ),
        "integrated_component_count_by_classification": dict(
            sorted(integrated_counts_by_classification.items())
        ),
        "component_count_by_section": dict(sorted(counts_by_section.items())),
        "component_count_by_dominant_material": dict(sorted(counts_by_material.items())),
        "source_component_fingerprint": source_digest.hexdigest(),
        "review_component_fingerprint": review_digest.hexdigest(),
        "all_review_geometry_matches_source": source_digest.hexdigest() == review_digest.hexdigest(),
        "all_review_components_closed_and_manifold": all(
            record["boundary_edges"] == 0 and record["nonmanifold_edges"] == 0
            for record in records
        ),
        "protected_source_mesh_count": len(protected_before),
        "protected_source_geometry_unchanged": protected_before == protected_after,
        "component_records": [
            {
                key: value
                for key, value in record.items()
                if key not in {"vertex_indices", "polygon_indices"}
            }
            for record in records
        ],
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": render_paths,
        },
        "no_stl_or_gcode_exported": True,
        "review_holds": config["review_holds"],
    }
    report_path = output_dir / "lower-reinforcement-ownership-review-v1-validation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "component_count": report["component_count"],
                "component_count_by_classification": report[
                    "component_count_by_classification"
                ],
                "component_count_by_section": report["component_count_by_section"],
                "all_review_geometry_matches_source": report[
                    "all_review_geometry_matches_source"
                ],
                "all_review_components_closed_and_manifold": report[
                    "all_review_components_closed_and_manifold"
                ],
                "protected_source_geometry_unchanged": report[
                    "protected_source_geometry_unchanged"
                ],
                "blend": report["generated_files"]["blend"],
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
