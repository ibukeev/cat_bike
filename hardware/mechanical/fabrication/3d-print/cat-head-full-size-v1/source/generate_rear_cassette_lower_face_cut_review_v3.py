#!/usr/bin/env python3
"""Cut only the V2-approved rear facets from duplicated Gate 8 lower faces.

This is a review generator, not a production release.  It keeps every Gate 8
production object in the scene, hides (but does not alter) the two original
lower-face objects, and creates closed review duplicates with the approved
rear-facet regions subtracted.  Upper heads, ears, rear_base, and aluminum
interface geometry are not edited.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import bmesh
import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate1_master as gate1  # noqa: E402
import generate_rear_cassette_seam_review_v2 as seam_v2  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/rear-cassette-lower-face-cut-review-v3.json"
)
DEFAULT_OUTPUT = (
    PACKAGE_ROOT / "output/rear-cassette-lower-face-cut-review-v3"
)
LOWER_SECTIONS = ("left_lower_face", "right_lower_face")
PRODUCTION_PARTS = seam_v2.PRODUCTION_PARTS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def mesh_fingerprint(obj: bpy.types.Object) -> str:
    digest = hashlib.sha256()
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        digest.update(f"v:{point.x:.9f},{point.y:.9f},{point.z:.9f}\n".encode())
    for polygon in obj.data.polygons:
        digest.update(
            ("f:" + ",".join(str(value) for value in polygon.vertices) + "\n").encode()
        )
    return digest.hexdigest()


def components(obj: bpy.types.Object) -> list[list[int]]:
    neighbors: dict[int, set[int]] = defaultdict(set)
    for edge in obj.data.edges:
        first, second = edge.vertices
        neighbors[first].add(second)
        neighbors[second].add(first)
    remaining = set(range(len(obj.data.vertices)))
    found: list[list[int]] = []
    while remaining:
        start = remaining.pop()
        stack = [start]
        component = [start]
        while stack:
            current = stack.pop()
            for neighbor in neighbors[current]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
                    component.append(neighbor)
        found.append(component)
    return sorted(found, key=len, reverse=True)


def mesh_metrics(obj: bpy.types.Object) -> dict[str, Any]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
    nonmanifold = sum(1 for edge in bm.edges if not edge.is_manifold)
    volume = abs(bm.calc_volume(signed=True))
    bm.free()
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    minimum = Vector((min(point.x for point in points), min(point.y for point in points), min(point.z for point in points)))
    maximum = Vector((max(point.x for point in points), max(point.y for point in points), max(point.z for point in points)))
    dimensions = maximum - minimum
    return {
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "faces": len(obj.data.polygons),
        "connected_components": len(components(obj)),
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "volume_mm3": round(volume, 3),
        "dimensions_mm": [round(value, 3) for value in dimensions],
        "bounds_mm": {
            "minimum": [round(value, 3) for value in minimum],
            "maximum": [round(value, 3) for value in maximum],
        },
    }


def require_closed(obj: bpy.types.Object, label: str) -> dict[str, Any]:
    metrics = mesh_metrics(obj)
    if metrics["boundary_edges"] or metrics["nonmanifold_edges"]:
        raise ValueError(
            f"{label} is not closed/manifold: boundary="
            f"{metrics['boundary_edges']}, nonmanifold="
            f"{metrics['nonmanifold_edges']}"
        )
    return metrics


def clean_gate8_scene() -> tuple[list[str], dict[str, str]]:
    missing = sorted(PRODUCTION_PARTS - set(bpy.data.objects.keys()))
    if missing:
        raise ValueError(f"Gate 8 blend is missing production parts: {missing}")
    protected = {
        name: mesh_fingerprint(bpy.data.objects[name])
        for name in ("left_upper_head", "right_upper_head", "left_ear", "right_ear", "rear_base")
    }
    removed: list[str] = []
    for obj in list(bpy.data.objects):
        if obj.name not in PRODUCTION_PARTS:
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)

    production = bpy.data.collections.new("UNCHANGED_GATE8_PRODUCTION")
    bpy.context.scene.collection.children.link(production)
    for name in sorted(PRODUCTION_PARTS):
        obj = bpy.data.objects[name]
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        production.objects.link(obj)
        obj["geometry_role"] = "unchanged Gate 8 production object"
    for name in LOWER_SECTIONS:
        source = bpy.data.objects[name]
        source.hide_viewport = True
        source.hide_render = True
        source["candidate_view_status"] = (
            "unchanged original hidden; V3 cut duplicate shown"
        )
    return sorted(removed), protected


def make_material(name: str, color_hex: str, alpha: float = 1.0) -> bpy.types.Material:
    return seam_v2.make_material(name, color_hex, alpha=alpha)


def selected_patch_edges(
    model: gate1.ObjModel,
    face_indices: set[int],
) -> tuple[list[tuple[int, int]], Counter[tuple[int, int]]]:
    directed: dict[tuple[int, int], tuple[int, int]] = {}
    counts: Counter[tuple[int, int]] = Counter()
    for face_index in sorted(face_indices):
        indices = model.faces[face_index].indices
        for offset, first in enumerate(indices):
            second = indices[(offset + 1) % len(indices)]
            key = tuple(sorted((first, second)))
            counts[key] += 1
            directed[key] = (first, second)
    invalid = {edge: count for edge, count in counts.items() if count > 2}
    if invalid:
        raise ValueError(f"Selected source patch has nonmanifold edges: {invalid}")
    return [directed[key] for key, count in counts.items() if count == 1], counts


def create_prism_cutter(
    name: str,
    model: gate1.ObjModel,
    points: list[tuple[float, float, float]],
    face_indices: set[int],
    plane_normal: Vector,
    outward_mm: float,
    inward_mm: float,
    boundary_clearance_mm: float,
    collection: bpy.types.Collection,
) -> tuple[bpy.types.Object, list[tuple[int, int]]]:
    used = sorted(
        {
            vertex
            for face_index in face_indices
            for vertex in model.faces[face_index].indices
        }
    )
    remap = {source: local for local, source in enumerate(used)}
    patch_points = [Vector(points[source]) for source in used]
    patch_center = sum(patch_points, Vector()) / len(patch_points)
    expanded_points: list[Vector] = []
    for point in patch_points:
        radial = point - patch_center
        tangent = radial - plane_normal * radial.dot(plane_normal)
        if tangent.length > 1e-9:
            point = point + tangent.normalized() * boundary_clearance_mm
        expanded_points.append(point)
    outer = [tuple(point + plane_normal * outward_mm) for point in expanded_points]
    inner = [tuple(point - plane_normal * inward_mm) for point in expanded_points]
    vertices = outer + inner
    count = len(used)
    faces: list[tuple[int, ...]] = []
    for face_index in sorted(face_indices):
        local = tuple(remap[index] for index in model.faces[face_index].indices)
        faces.append(local)
        faces.append(tuple(count + index for index in reversed(local)))
    boundary_directed, _edge_counts = selected_patch_edges(model, face_indices)
    for first, second in boundary_directed:
        a = remap[first]
        b = remap[second]
        faces.append((a, b, count + b, count + a))

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    cutter = bpy.data.objects.new(name, mesh)
    collection.objects.link(cutter)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(mesh)
    bm.free()
    mesh.update(calc_edges=True)
    require_closed(cutter, f"{name} cutter")
    cutter.display_type = "WIRE"
    cutter.hide_render = True
    cutter["review_only_boolean_cutter"] = True
    return cutter, boundary_directed


def duplicate_and_cut(
    source_name: str,
    cutter: bpy.types.Object,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
) -> tuple[bpy.types.Object, dict[str, Any], dict[str, Any]]:
    source = bpy.data.objects[source_name]
    before = require_closed(source, f"unchanged {source_name}")
    candidate = source.copy()
    candidate.data = source.data.copy()
    candidate.name = f"REVIEW_V3_CUT__{source_name}"
    candidate.data.name = f"{candidate.name}_mesh"
    collection.objects.link(candidate)
    candidate.hide_viewport = False
    candidate.hide_render = False
    candidate.data.materials.clear()
    candidate.data.materials.append(material)
    if "geometry_role" in candidate:
        del candidate["geometry_role"]
    if "candidate_view_status" in candidate:
        del candidate["candidate_view_status"]

    # Gate 8 intentionally stores the shell and its internal reinforcement as
    # many independent closed components in one object. Applying one Boolean
    # across all overlapping components can create shared nonmanifold edges.
    # Preserve that architecture: separate the existing loose components, cut
    # each closed component independently, then join them without a union.
    bpy.ops.object.select_all(action="DESELECT")
    candidate.select_set(True)
    bpy.context.view_layer.objects.active = candidate
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    loose_parts = [
        obj for obj in bpy.context.selected_objects if obj.type == "MESH"
    ]
    source_component_count = int(before["connected_components"])
    if len(loose_parts) != source_component_count:
        raise ValueError(
            f"{source_name} loose-part separation mismatch: "
            f"{len(loose_parts)} != {source_component_count}"
        )

    retained_parts: list[bpy.types.Object] = []
    removed_components = 0
    cleanup_duplicate_faces = 0
    cleanup_degenerate_faces = 0
    cleanup_cap_faces = 0
    for index, part in enumerate(loose_parts, start=1):
        bpy.context.view_layer.objects.active = part
        modifier = part.modifiers.new(
            f"V3_APPROVED_REAR_FACET_CUT_{index:03d}", "BOOLEAN"
        )
        modifier.operation = "DIFFERENCE"
        modifier.solver = "MANIFOLD"
        modifier.object = cutter
        result = bpy.ops.object.modifier_apply(modifier=modifier.name)
        if "FINISHED" not in result:
            raise ValueError(
                f"Boolean modifier failed for {source_name} component "
                f"{index}: {result}"
            )
        part.data.update(calc_edges=True)
        if not part.data.vertices or not part.data.polygons:
            bpy.data.objects.remove(part, do_unlink=True)
            removed_components += 1
            continue

        part_duplicate_faces = sum(
            count - 1
            for count in Counter(
                tuple(sorted(polygon.vertices))
                for polygon in part.data.polygons
            ).values()
            if count > 1
        )
        part_degenerate_faces = sum(
            1 for polygon in part.data.polygons if polygon.area < 1e-9
        )
        validation_changed = part.data.validate(
            verbose=True, clean_customdata=False
        )
        part.data.update(calc_edges=True)
        if validation_changed and (
            len(part.data.vertices) < 4 or len(part.data.polygons) < 4
        ):
            cleanup_duplicate_faces += part_duplicate_faces
            cleanup_degenerate_faces += part_degenerate_faces
            bpy.data.objects.remove(part, do_unlink=True)
            removed_components += 1
            continue
        cap_faces_added = 0
        if validation_changed:
            bm = bmesh.new()
            bm.from_mesh(part.data)
            boundary_edges = [
                edge for edge in bm.edges if len(edge.link_faces) == 1
            ]
            if boundary_edges and not (
                part_duplicate_faces or part_degenerate_faces
            ):
                bm.free()
                raise ValueError(
                    f"{source_name} component {index} needs an unaccounted cap"
                )
            if boundary_edges:
                fill_result = bmesh.ops.holes_fill(
                    bm, edges=boundary_edges, sides=0
                )
                cap_faces_added = len(fill_result.get("faces", []))
                bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
                bm.to_mesh(part.data)
            bm.free()
            part.data.update(calc_edges=True)
        require_closed(part, f"cut {source_name} component {index}")
        if part.data.validate(verbose=True, clean_customdata=False):
            raise ValueError(
                f"{source_name} component {index} remains invalid after recapping"
            )
        cleanup_duplicate_faces += part_duplicate_faces
        cleanup_degenerate_faces += part_degenerate_faces
        cleanup_cap_faces += cap_faces_added
        retained_parts.append(part)
    if not retained_parts:
        raise ValueError(f"Cut removed every component from {source_name}")

    bpy.ops.object.select_all(action="DESELECT")
    for part in retained_parts:
        part.select_set(True)
    bpy.context.view_layer.objects.active = retained_parts[0]
    bpy.ops.object.join()
    candidate = retained_parts[0]
    candidate.name = f"REVIEW_V3_CUT__{source_name}"
    candidate.data.name = f"{candidate.name}_mesh"
    duplicate_face_count = sum(
        count - 1
        for count in Counter(
            tuple(sorted(polygon.vertices))
            for polygon in candidate.data.polygons
        ).values()
        if count > 1
    )
    degenerate_face_count = sum(
        1 for polygon in candidate.data.polygons if polygon.area < 1e-9
    )
    mesh_validation_changed = candidate.data.validate(
        verbose=True, clean_customdata=False
    )
    if duplicate_face_count or degenerate_face_count or mesh_validation_changed:
        raise ValueError(
            f"Joined {source_name} still required mesh cleanup: "
            f"duplicates={duplicate_face_count}, "
            f"degenerate={degenerate_face_count}, "
            f"changed={mesh_validation_changed}"
        )
    candidate.data.update(calc_edges=True)
    after = require_closed(candidate, f"cut {source_name}")
    if after["volume_mm3"] >= before["volume_mm3"] - 0.001:
        raise ValueError(
            f"{source_name} did not lose volume: "
            f"{before['volume_mm3']} -> {after['volume_mm3']}"
        )
    candidate["review_only"] = True
    candidate["not_production_released"] = True
    candidate["cut_scope"] = "V2-approved rear facets from this lower face only"
    candidate["source_closed_component_count"] = source_component_count
    candidate["fully_removed_component_count"] = removed_components
    candidate["boolean_duplicate_faces_removed"] = cleanup_duplicate_faces
    candidate["boolean_degenerate_faces_removed"] = cleanup_degenerate_faces
    candidate["boolean_cap_faces_added"] = cleanup_cap_faces
    candidate["joined_mesh_validation_changed"] = mesh_validation_changed
    return candidate, before, after


def export_stl(obj: bpy.types.Object, path: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(
        filepath=str(path), export_selected_objects=True, ascii_format=False
    )
    obj.select_set(False)


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def configure_scene(output_dir: Path, resolution_px: int) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.name = "Rear_Cassette_Lower_Face_Cut_Review_V3"
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "MATERIAL"
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    shading.curvature_ridge_factor = 1.8
    shading.curvature_valley_factor = 1.4
    shading.background_type = "VIEWPORT"
    shading.background_color = (0.055, 0.065, 0.085)
    scene.render.resolution_x = resolution_px
    scene.render.resolution_y = resolution_px
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.world.color = (0.014, 0.018, 0.028)
    camera_data = bpy.data.cameras.new("REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("REVIEW_ONLY__Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 58.0
    output_dir.joinpath("renders").mkdir(parents=True, exist_ok=True)
    return camera


def render_views(
    camera: bpy.types.Object,
    output_dir: Path,
    candidates: list[bpy.types.Object],
    overlays: list[bpy.types.Object],
) -> list[str]:
    scene = bpy.context.scene
    target = Vector((0.0, 175.0, 165.0))
    full_views = (
        ("front", Vector((0.0, -610.0, 260.0))),
        ("rear", Vector((0.0, 650.0, 280.0))),
        ("rear-left", Vector((-430.0, 560.0, 330.0))),
        ("rear-right", Vector((430.0, 560.0, 330.0))),
        ("left", Vector((-620.0, 145.0, 270.0))),
        ("right", Vector((620.0, 145.0, 270.0))),
    )
    paths: list[str] = []
    for label, location in full_views:
        camera.location = location
        point_at(camera, target)
        path = output_dir / "renders" / f"lower-face-cut-{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        paths.append(str(path.relative_to(REPO_ROOT)))

    saved = {obj.name: obj.hide_render for obj in bpy.data.objects}
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_render = obj not in candidates and obj not in overlays
    isolated_target = Vector((0.0, 225.0, 125.0))
    for label, location in (
        ("isolated-rear", Vector((0.0, 620.0, 240.0))),
        ("isolated-front", Vector((0.0, -500.0, 220.0))),
        ("isolated-left", Vector((-520.0, 180.0, 220.0))),
        ("isolated-right", Vector((520.0, 180.0, 220.0))),
    ):
        camera.location = location
        point_at(camera, isolated_target)
        path = output_dir / "renders" / f"lower-face-cut-{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        paths.append(str(path.relative_to(REPO_ROOT)))
    for name, hidden in saved.items():
        bpy.data.objects[name].hide_render = hidden
    camera.location = Vector((0.0, 650.0, 280.0))
    point_at(camera, target)
    return paths


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_blend = repo_path(config["source_gate8_blend"])
    if Path(bpy.data.filepath).resolve() != source_blend:
        raise ValueError(
            f"Open the configured Gate 8 blend before running: {source_blend}"
        )
    interface_path = repo_path(config["shared_interface_path"])
    interface = json.loads(interface_path.read_text(encoding="utf-8"))
    actual_revision = interface["interface_revision"]
    required_revision = config["required_interface_revision"]
    if actual_revision != required_revision:
        raise ValueError(f"Interface mismatch: {actual_revision} != {required_revision}")

    output_dir.mkdir(parents=True, exist_ok=True)
    stl_dir = output_dir / "review-stl-not-production"
    stl_dir.mkdir(parents=True, exist_ok=True)
    removed_references, protected_before = clean_gate8_scene()

    selection_config = dict(config)
    selection_config["rear_cassette_cut"] = dict(config["lower_face_cut"])
    model, assignments, points, selected, _v2_seam = seam_v2.source_selection(
        selection_config, interface
    )
    selected_by_section = {
        section: {index for index in selected if assignments[index] == section}
        for section in LOWER_SECTIONS
    }
    if any(len(indices) != 5 for indices in selected_by_section.values()):
        raise ValueError(
            "V3 expected the approved V2 selection to contain five facets per side: "
            f"{ {key: len(value) for key, value in selected_by_section.items()} }"
        )

    review_collection = bpy.data.collections.new("REVIEW_V3_CUT_LOWER_FACES")
    cutter_collection = bpy.data.collections.new("REVIEW_V3_HIDDEN_CUTTERS")
    overlay_collection = bpy.data.collections.new("REVIEW_V3_REMOVED_REGION_OVERLAY")
    bpy.context.scene.collection.children.link(review_collection)
    bpy.context.scene.collection.children.link(cutter_collection)
    bpy.context.scene.collection.children.link(overlay_collection)

    materials = {
        "left_lower_face": make_material(
            "REVIEW_V3__Left_Cut_Blue", config["review_display"]["left_cut_color"]
        ),
        "right_lower_face": make_material(
            "REVIEW_V3__Right_Cut_Green", config["review_display"]["right_cut_color"]
        ),
    }
    removed_material = make_material(
        "REVIEW_V3__Removed_Region_Orange",
        config["review_display"]["removed_region_color"],
        alpha=0.82,
    )
    seam_material = make_material(
        "REVIEW_V3__Cut_Boundary_Yellow",
        config["review_display"]["seam_color"],
    )
    plane = interface["rear_interface_plane"]
    plane_normal = Vector(plane["outward_normal_head"]).normalized()
    outward_mm = float(config["lower_face_cut"]["cutter_outward_extension_mm"])
    inward_mm = float(config["lower_face_cut"]["cutter_inward_extension_mm"])
    boundary_clearance_mm = float(
        config["lower_face_cut"]["cutter_boundary_clearance_mm"]
    )

    candidates: dict[str, bpy.types.Object] = {}
    cutters: dict[str, bpy.types.Object] = {}
    source_metrics: dict[str, dict[str, Any]] = {}
    candidate_metrics: dict[str, dict[str, Any]] = {}
    boundary_edges_by_section: dict[str, list[tuple[int, int]]] = {}
    overlays: list[bpy.types.Object] = []
    for section in LOWER_SECTIONS:
        cutter, boundary_edges = create_prism_cutter(
            f"REVIEW_V3_CUTTER__{section}",
            model,
            points,
            selected_by_section[section],
            plane_normal,
            outward_mm,
            inward_mm,
            boundary_clearance_mm,
            cutter_collection,
        )
        cutters[section] = cutter
        boundary_edges_by_section[section] = boundary_edges
        candidate, before, after = duplicate_and_cut(
            section, cutter, materials[section], review_collection
        )
        candidates[section] = candidate
        source_metrics[section] = before
        candidate_metrics[section] = after

        display_points = seam_v2.outward_offset_points(
            model,
            points,
            selected_by_section[section],
            float(config["review_display"]["overlay_offset_mm"]),
        )
        overlay = seam_v2.create_surface(
            f"REVIEW_V3_REMOVED__{section}",
            model,
            display_points,
            selected_by_section[section],
            removed_material,
            overlay_collection,
        )
        overlay["meaning"] = "exact V2-approved lower-face region removed in V3"
        seam = seam_v2.create_seam(
            f"REVIEW_V3_CUT_BOUNDARY__{section}",
            {tuple(sorted(edge)) for edge in boundary_edges},
            display_points,
            float(config["review_display"]["seam_radius_mm"]),
            seam_material,
            overlay_collection,
        )
        seam["meaning"] = "complete boundary of the actual V3 subtraction volume"
        overlays.extend((overlay, seam))

    for cutter in cutters.values():
        cutter.hide_viewport = True
        cutter.hide_render = True

    stl_paths: dict[str, str] = {}
    for section, candidate in candidates.items():
        path = stl_dir / f"{section}_cut_review_v3.stl"
        export_stl(candidate, path)
        stl_paths[section] = str(path.relative_to(REPO_ROOT))

    camera = configure_scene(
        output_dir, int(config["review_display"]["render_resolution_px"])
    )
    render_paths = render_views(
        camera, output_dir, list(candidates.values()), overlays
    )

    protected_after = {
        name: mesh_fingerprint(bpy.data.objects[name]) for name in protected_before
    }
    if protected_before != protected_after:
        changed = sorted(
            name
            for name in protected_before
            if protected_before[name] != protected_after[name]
        )
        raise ValueError(f"Protected Gate 8 geometry changed: {changed}")

    scene = bpy.context.scene
    scene["review_status"] = config["status"]
    scene["production_source_geometry_modified"] = False
    scene["actual_review_duplicate_lower_faces_cut"] = True
    scene["instructions"] = (
        "Blue/green are the actual cut lower-face review duplicates. Orange is "
        "the removed V2-approved region. Yellow is the complete cut boundary. "
        "Original lower faces remain hidden and unchanged."
    )
    blend_path = output_dir / "rear-cassette-lower-face-cut-review-v3.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    bpy.ops.object.select_all(action="DESELECT")
    glb_objects = [
        bpy.data.objects[name]
        for name in sorted(PRODUCTION_PARTS - set(LOWER_SECTIONS))
    ] + list(candidates.values()) + overlays
    for obj in glb_objects:
        obj.hide_viewport = False
        obj.select_set(True)
    glb_path = output_dir / "rear-cassette-lower-face-cut-review-v3.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path), export_format="GLB", use_selection=True
    )

    used_vertices = {
        vertex
        for face_index in selected
        for vertex in model.faces[face_index].indices
    }
    exact_bounds = gate1.bounds([points[index] for index in sorted(used_vertices)])
    selected_panels = sorted(
        {
            gate1.canonical_source_panel_id(model.faces[index].group)
            for index in selected
        }
    )
    slice_report_path = (
        output_dir
        / "slicer-review/rear-cassette-lower-face-cut-review-v3-slicer.json"
    )
    report = {
        "status": config["status"],
        "source_gate8_blend": str(source_blend.relative_to(REPO_ROOT)),
        "source_gate8_blend_sha256": sha256(source_blend),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "shared_interface": str(interface_path.relative_to(REPO_ROOT)),
        "interface_revision": actual_revision,
        "cut_scope": list(LOWER_SECTIONS),
        "selected_source_face_count": len(selected),
        "selected_source_face_count_by_section": {
            section: len(indices) for section, indices in selected_by_section.items()
        },
        "selected_source_panel_ids": selected_panels,
        "exact_selected_surface_dimensions_mm": [
            round(value, 3) for value in gate1.dimensions(exact_bounds)
        ],
        "complete_cut_boundary_edge_count_by_section": {
            section: len(edges) for section, edges in boundary_edges_by_section.items()
        },
        "cutter_extensions_mm": {
            "outward": outward_mm,
            "inward": inward_mm,
            "boundary_clearance": boundary_clearance_mm,
        },
        "source_lower_face_metrics": source_metrics,
        "cut_lower_face_metrics": candidate_metrics,
        "volume_removed_mm3": {
            section: round(
                source_metrics[section]["volume_mm3"]
                - candidate_metrics[section]["volume_mm3"],
                3,
            )
            for section in LOWER_SECTIONS
        },
        "both_cut_bodies_closed_manifold": all(
            metrics["boundary_edges"] == 0 and metrics["nonmanifold_edges"] == 0
            for metrics in candidate_metrics.values()
        ),
        "protected_geometry_fingerprints_before": protected_before,
        "protected_geometry_fingerprints_after": protected_after,
        "upper_heads_ears_rear_base_byte_equivalent_in_scene": (
            protected_before == protected_after
        ),
        "original_gate8_lower_face_objects_modified": False,
        "boolean_component_handling": {
            section: {
                "source_closed_components": candidates[section].get(
                    "source_closed_component_count"
                ),
                "fully_removed_components_inside_cut": candidates[section].get(
                    "fully_removed_component_count"
                ),
                "remaining_closed_components_after_cut": candidate_metrics[
                    section
                ]["connected_components"],
                "duplicate_boolean_faces_removed": candidates[section].get(
                    "boolean_duplicate_faces_removed"
                ),
                "degenerate_boolean_faces_removed": candidates[section].get(
                    "boolean_degenerate_faces_removed"
                ),
                "cut_boundary_cap_faces_added": candidates[section].get(
                    "boolean_cap_faces_added"
                ),
                "joined_mesh_validator_changed_geometry": candidates[
                    section
                ].get("joined_mesh_validation_changed"),
            }
            for section in LOWER_SECTIONS
        },
        "removed_gate8_review_references": removed_references,
        "production_parts_present": sorted(PRODUCTION_PARTS),
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "glb": str(glb_path.relative_to(REPO_ROOT)),
            "review_stls_not_production": stl_paths,
            "renders": render_paths,
        },
        "slice_validation": {
            "status": "complete" if slice_report_path.exists() else "pending",
            "report": str(slice_report_path.relative_to(REPO_ROOT)),
        },
        "review_holds": config["review_holds"],
    }
    report_path = output_dir / "rear-cassette-lower-face-cut-review-v3-validation.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "selected_source_face_count_by_section": report[
                    "selected_source_face_count_by_section"
                ],
                "both_cut_bodies_closed_manifold": report[
                    "both_cut_bodies_closed_manifold"
                ],
                "source_dimensions_mm": {
                    section: metrics["dimensions_mm"]
                    for section, metrics in source_metrics.items()
                },
                "cut_dimensions_mm": {
                    section: metrics["dimensions_mm"]
                    for section, metrics in candidate_metrics.items()
                },
                "blend": report["generated_files"]["blend"],
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
