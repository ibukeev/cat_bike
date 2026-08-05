#!/usr/bin/env python3
"""Generate a lossless lower-face/rear-cassette exterior repartition review.

V4 does not Boolean-cut the Gate 8 lower-face objects. It regenerates four
closed review shells from complementary source-facet sets: retained left and
right lower shells plus the exact left and right rear facets moved to cassette
ownership. Their assembled exterior is therefore the original exterior with
zero deleted or duplicated source facets. Gate 8 reinforcement remains hidden,
unchanged source reference and is deliberately not assigned in this review.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict, deque
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
    PACKAGE_ROOT / "config/rear-cassette-lossless-repartition-review-v4.json"
)
DEFAULT_OUTPUT = (
    PACKAGE_ROOT / "output/rear-cassette-lossless-repartition-review-v4"
)
LOWER_SECTIONS = ("left_lower_face", "right_lower_face")
PRODUCTION_PARTS = seam_v2.PRODUCTION_PARTS
PROTECTED_PARTS = (
    "left_upper_head",
    "right_upper_head",
    "left_ear",
    "right_ear",
    "rear_base",
)


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
    duplicate_faces = sum(
        count - 1
        for count in Counter(
            tuple(sorted(polygon.vertices)) for polygon in obj.data.polygons
        ).values()
        if count > 1
    )
    degenerate_faces = sum(
        1 for polygon in obj.data.polygons if polygon.area < 1e-9
    )
    return {
        "vertices": len(obj.data.vertices),
        "edges": len(obj.data.edges),
        "faces": len(obj.data.polygons),
        "connected_components": len(components(obj)),
        "boundary_edges": boundary,
        "nonmanifold_edges": nonmanifold,
        "duplicate_faces": duplicate_faces,
        "degenerate_faces": degenerate_faces,
        "volume_mm3": round(volume, 3),
        "dimensions_mm": [round(value, 3) for value in obj.dimensions],
    }


def require_valid_closed(obj: bpy.types.Object, label: str) -> dict[str, Any]:
    metrics = mesh_metrics(obj)
    defects = {
        key: metrics[key]
        for key in (
            "boundary_edges",
            "nonmanifold_edges",
            "duplicate_faces",
            "degenerate_faces",
        )
        if metrics[key]
    }
    probe = obj.data.copy()
    validator_changed = probe.validate(verbose=True, clean_customdata=False)
    bpy.data.meshes.remove(probe)
    if defects or validator_changed:
        raise ValueError(
            f"{label} failed closed-mesh validation: defects={defects}, "
            f"validator_changed={validator_changed}"
        )
    return metrics


def clean_gate8_scene() -> tuple[list[str], dict[str, str]]:
    missing = sorted(PRODUCTION_PARTS - set(bpy.data.objects.keys()))
    if missing:
        raise ValueError(f"Gate 8 blend is missing production parts: {missing}")
    protected = {
        name: mesh_fingerprint(bpy.data.objects[name]) for name in PROTECTED_PARTS
    }
    protected.update(
        {
            name: mesh_fingerprint(bpy.data.objects[name])
            for name in LOWER_SECTIONS
        }
    )
    removed: list[str] = []
    for obj in list(bpy.data.objects):
        if obj.name not in PRODUCTION_PARTS:
            removed.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)

    production = bpy.data.collections.new("UNCHANGED_GATE8_SOURCE_REFERENCE")
    bpy.context.scene.collection.children.link(production)
    for name in sorted(PRODUCTION_PARTS):
        obj = bpy.data.objects[name]
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        production.objects.link(obj)
        obj["geometry_role"] = "unchanged Gate 8 source object"
    for name in (*LOWER_SECTIONS, "rear_base"):
        obj = bpy.data.objects[name]
        obj.hide_viewport = True
        obj.hide_render = True
        obj["candidate_view_status"] = (
            "unchanged hidden source; V4 complementary review shells shown"
        )
    return sorted(removed), protected


def split_vertex_fans(
    vertices: list[tuple[float, float, float]],
    faces: list[tuple[int, ...]],
) -> tuple[list[tuple[float, float, float]], list[tuple[int, ...]], int]:
    output_vertices = list(vertices)
    output_faces = [list(face) for face in faces]
    split_count = 0
    original_vertex_count = len(vertices)
    for vertex_index in range(original_vertex_count):
        incident = [
            index for index, face in enumerate(output_faces)
            if vertex_index in face
        ]
        if len(incident) < 2:
            continue
        neighbors: dict[int, set[int]] = {index: set() for index in incident}
        for first_offset, first_index in enumerate(incident):
            first_face = output_faces[first_index]
            first_position = first_face.index(vertex_index)
            first_adjacent = {
                first_face[(first_position - 1) % len(first_face)],
                first_face[(first_position + 1) % len(first_face)],
            }
            for second_index in incident[first_offset + 1 :]:
                second_face = output_faces[second_index]
                second_position = second_face.index(vertex_index)
                second_adjacent = {
                    second_face[(second_position - 1) % len(second_face)],
                    second_face[(second_position + 1) % len(second_face)],
                }
                if first_adjacent & second_adjacent:
                    neighbors[first_index].add(second_index)
                    neighbors[second_index].add(first_index)
        remaining = set(incident)
        fans: list[list[int]] = []
        while remaining:
            start = remaining.pop()
            queue = deque([start])
            fan = [start]
            while queue:
                current = queue.popleft()
                for neighbor in neighbors[current]:
                    if neighbor in remaining:
                        remaining.remove(neighbor)
                        queue.append(neighbor)
                        fan.append(neighbor)
            fans.append(fan)
        for fan in fans[1:]:
            replacement = len(output_vertices)
            output_vertices.append(output_vertices[vertex_index])
            split_count += 1
            for face_index in fan:
                output_faces[face_index] = [
                    replacement if value == vertex_index else value
                    for value in output_faces[face_index]
                ]
    return (
        output_vertices,
        [tuple(face) for face in output_faces],
        split_count,
    )


def create_closed_shell(
    name: str,
    model: gate1.ObjModel,
    points: list[tuple[float, float, float]],
    face_indices: set[int],
    closure_faces: list[tuple[int, ...]],
    material: bpy.types.Material,
    collection: bpy.types.Collection,
    thickness_mm: float,
    solidify_offset: float,
    use_even_offset: bool,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    source_faces = [
        tuple(model.faces[index].indices) for index in sorted(face_indices)
    ]
    source_faces.extend(closure_faces)
    used = sorted({vertex for face in source_faces for vertex in face})
    remap = {source: local for local, source in enumerate(used)}
    vertices = [points[source] for source in used]
    faces = [tuple(remap[index] for index in face) for face in source_faces]
    vertices, faces, fan_splits = split_vertex_fans(vertices, faces)

    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.data.materials.append(material)

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")

    solidify = obj.modifiers.new("V4_INWARD_SHELL_1P8MM", "SOLIDIFY")
    solidify.thickness = thickness_mm
    solidify.offset = solidify_offset
    solidify.use_rim = True
    solidify.use_rim_only = False
    solidify.use_even_offset = use_even_offset
    solidify.use_quality_normals = True
    result = bpy.ops.object.modifier_apply(modifier=solidify.name)
    if "FINISHED" not in result:
        raise ValueError(f"Solidify failed for {name}: {result}")
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update(calc_edges=True)
    obj.select_set(False)
    obj["review_only"] = True
    obj["not_print_released"] = True
    obj["source_face_count"] = len(face_indices)
    obj["closure_face_count"] = len(closure_faces)
    obj["boundary_vertex_fan_splits"] = fan_splits
    return obj, require_valid_closed(obj, name)


def patch_boundary_edges(
    model: gate1.ObjModel,
    face_indices: set[int],
) -> set[tuple[int, int]]:
    counts: Counter[tuple[int, int]] = Counter()
    for face_index in face_indices:
        indices = model.faces[face_index].indices
        for offset, first in enumerate(indices):
            second = indices[(offset + 1) % len(indices)]
            counts[tuple(sorted((first, second)))] += 1
    invalid = {edge: count for edge, count in counts.items() if count > 2}
    if invalid:
        raise ValueError(f"Moved source patch is nonmanifold: {invalid}")
    return {edge for edge, count in counts.items() if count == 1}


def create_rear_base_review_copy(
    material: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    source = bpy.data.objects["rear_base"]
    review = source.copy()
    review.data = source.data.copy()
    review.name = "V4_CASSETTE__unchanged_rear_base"
    review.data.name = f"{review.name}_mesh"
    collection.objects.link(review)
    review.hide_viewport = False
    review.hide_render = False
    review.data.materials.clear()
    review.data.materials.append(material)
    for key in ("geometry_role", "candidate_view_status"):
        if key in review:
            del review[key]
    review["review_only"] = True
    review["meaning"] = "unchanged Gate 8 rear_base in V4 cassette ownership"
    return review


def face_token(
    points: list[tuple[float, float, float]],
    indices: tuple[int, ...],
) -> tuple[tuple[float, float, float], ...]:
    return tuple(
        sorted(
            tuple(round(value, 6) for value in points[index])
            for index in indices
        )
    )


def face_ledger(
    model: gate1.ObjModel,
    assignments: list[str],
    points: list[tuple[float, float, float]],
    selected_by_section: dict[str, set[int]],
    retained_by_section: dict[str, set[int]],
    closures_by_section: dict[str, list[tuple[int, ...]]],
) -> dict[str, Any]:
    source: Counter[tuple[tuple[float, float, float], ...]] = Counter()
    candidate: Counter[tuple[tuple[float, float, float], ...]] = Counter()
    for section in LOWER_SECTIONS:
        all_indices = {
            index for index, assignment in enumerate(assignments)
            if assignment == section
        }
        for index in all_indices:
            source[face_token(points, tuple(model.faces[index].indices))] += 1
        for closure in closures_by_section[section]:
            source[face_token(points, closure)] += 1
        for index in retained_by_section[section] | selected_by_section[section]:
            candidate[face_token(points, tuple(model.faces[index].indices))] += 1
        for closure in closures_by_section[section]:
            candidate[face_token(points, closure)] += 1
    deleted = source - candidate
    added = candidate - source
    duplicated = Counter(
        {
            token: candidate[token] - source[token]
            for token in candidate
            if candidate[token] > source[token]
        }
    )
    digest = hashlib.sha256()
    for token, count in sorted(source.items()):
        digest.update(f"{token}:{count}\n".encode())
    candidate_digest = hashlib.sha256()
    for token, count in sorted(candidate.items()):
        candidate_digest.update(f"{token}:{count}\n".encode())
    return {
        "source_exterior_face_count_including_closures": sum(source.values()),
        "candidate_exterior_face_count_including_closures": sum(
            candidate.values()
        ),
        "deleted_face_count": sum(deleted.values()),
        "unexpected_added_face_count": sum(added.values()),
        "duplicated_face_count": sum(duplicated.values()),
        "source_exterior_fingerprint": digest.hexdigest(),
        "candidate_exterior_fingerprint": candidate_digest.hexdigest(),
        "fingerprints_match": digest.hexdigest() == candidate_digest.hexdigest(),
    }


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def configure_scene(output_dir: Path, resolution_px: int) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.name = "Rear_Cassette_Lossless_Repartition_Review_V4"
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
    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    return camera


def render_named_views(
    camera: bpy.types.Object,
    output_dir: Path,
    prefix: str,
    target: Vector,
    views: tuple[tuple[str, Vector], ...],
) -> list[str]:
    scene = bpy.context.scene
    paths: list[str] = []
    for label, location in views:
        camera.location = location
        point_at(camera, target)
        path = output_dir / "renders" / f"{prefix}-{label}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        paths.append(str(path.relative_to(REPO_ROOT)))
    return paths


def render_reviews(
    camera: bpy.types.Object,
    output_dir: Path,
    retained: list[bpy.types.Object],
    cassette: list[bpy.types.Object],
    seams: list[bpy.types.Object],
) -> list[str]:
    full_views = (
        ("front", Vector((0.0, -610.0, 260.0))),
        ("rear", Vector((0.0, 650.0, 280.0))),
        ("rear-left", Vector((-430.0, 560.0, 330.0))),
        ("rear-right", Vector((430.0, 560.0, 330.0))),
        ("left", Vector((-620.0, 145.0, 270.0))),
        ("right", Vector((620.0, 145.0, 270.0))),
    )
    paths = render_named_views(
        camera,
        output_dir,
        "lossless-repartition-full",
        Vector((0.0, 175.0, 165.0)),
        full_views,
    )
    saved = {obj.name: obj.hide_render for obj in bpy.data.objects}
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_render = obj not in retained
    paths.extend(
        render_named_views(
            camera,
            output_dir,
            "lossless-repartition-retained-lower",
            Vector((0.0, 165.0, 105.0)),
            (
                ("front", Vector((0.0, -500.0, 210.0))),
                ("rear", Vector((0.0, 590.0, 220.0))),
                ("left", Vector((-520.0, 150.0, 210.0))),
                ("right", Vector((520.0, 150.0, 210.0))),
            ),
        )
    )
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_render = obj not in cassette and obj not in seams
    paths.extend(
        render_named_views(
            camera,
            output_dir,
            "lossless-repartition-cassette",
            Vector((0.0, 245.0, 155.0)),
            (
                ("front", Vector((0.0, -420.0, 230.0))),
                ("rear", Vector((0.0, 620.0, 250.0))),
                ("rear-left", Vector((-430.0, 530.0, 290.0))),
                ("rear-right", Vector((430.0, 530.0, 290.0))),
            ),
        )
    )
    for name, hidden in saved.items():
        bpy.data.objects[name].hide_render = hidden
    camera.location = Vector((0.0, 650.0, 280.0))
    point_at(camera, Vector((0.0, 175.0, 165.0)))
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
    removed_references, protected_before = clean_gate8_scene()
    selection_config = dict(config)
    selection_config["rear_cassette_cut"] = dict(config["repartition"])
    model, assignments, points, selected, _v2_seam = seam_v2.source_selection(
        selection_config, interface
    )
    all_by_section = {
        section: {
            index for index, assignment in enumerate(assignments)
            if assignment == section
        }
        for section in LOWER_SECTIONS
    }
    selected_by_section = {
        section: {index for index in selected if assignments[index] == section}
        for section in LOWER_SECTIONS
    }
    retained_by_section = {
        section: all_by_section[section] - selected_by_section[section]
        for section in LOWER_SECTIONS
    }
    if any(len(indices) != 5 for indices in selected_by_section.values()):
        raise ValueError(
            "V4 requires exactly the approved five moved facets per side: "
            f"{ {key: len(value) for key, value in selected_by_section.items()} }"
        )
    if any(
        retained_by_section[section] & selected_by_section[section]
        for section in LOWER_SECTIONS
    ):
        raise ValueError("Retained and moved source-facet sets overlap")
    if any(
        retained_by_section[section] | selected_by_section[section]
        != all_by_section[section]
        for section in LOWER_SECTIONS
    ):
        raise ValueError("Retained plus moved facets do not cover a lower section")

    gate3_config = json.loads(
        repo_path(config["source_gate3_config"]).read_text(encoding="utf-8")
    )
    closures_by_section = {
        section: [
            tuple(face)
            for face in gate3_config.get("bottom_closure_faces", {}).get(
                section, []
            )
        ]
        for section in LOWER_SECTIONS
    }
    ledger = face_ledger(
        model,
        assignments,
        points,
        selected_by_section,
        retained_by_section,
        closures_by_section,
    )
    if (
        ledger["deleted_face_count"]
        or ledger["unexpected_added_face_count"]
        or ledger["duplicated_face_count"]
        or not ledger["fingerprints_match"]
    ):
        raise ValueError(f"V4 exterior face ledger is not lossless: {ledger}")

    retained_collection = bpy.data.collections.new("V4_RETAINED_LOWER_EXTERIORS")
    cassette_collection = bpy.data.collections.new(
        "V4_ENLARGED_REAR_CASSETTE_OWNERSHIP"
    )
    seam_collection = bpy.data.collections.new("V4_REPARTITION_BOUNDARIES")
    bpy.context.scene.collection.children.link(retained_collection)
    bpy.context.scene.collection.children.link(cassette_collection)
    bpy.context.scene.collection.children.link(seam_collection)

    materials = {
        "left_lower_face": seam_v2.make_material(
            "V4__Retained_Left_Blue",
            config["review_display"]["left_retained_color"],
        ),
        "right_lower_face": seam_v2.make_material(
            "V4__Retained_Right_Green",
            config["review_display"]["right_retained_color"],
        ),
    }
    cassette_material = seam_v2.make_material(
        "V4__Cassette_Orange", config["review_display"]["cassette_color"]
    )
    seam_material = seam_v2.make_material(
        "V4__Boundary_Yellow", config["review_display"]["seam_color"]
    )
    thickness = float(config["repartition"]["shell_wall_thickness_mm"])
    solidify_offset = float(config["repartition"]["solidify_offset"])
    use_even_offset = bool(config["repartition"]["use_even_offset"])

    retained_objects: dict[str, bpy.types.Object] = {}
    moved_objects: dict[str, bpy.types.Object] = {}
    shell_metrics: dict[str, dict[str, Any]] = {}
    seam_objects: list[bpy.types.Object] = []
    for section in LOWER_SECTIONS:
        retained, retained_metrics = create_closed_shell(
            f"V4_RETAINED__{section}_exterior_shell",
            model,
            points,
            retained_by_section[section],
            closures_by_section[section],
            materials[section],
            retained_collection,
            thickness,
            solidify_offset,
            use_even_offset,
        )
        moved, moved_metrics = create_closed_shell(
            f"V4_CASSETTE__moved_from_{section}",
            model,
            points,
            selected_by_section[section],
            [],
            cassette_material,
            cassette_collection,
            thickness,
            solidify_offset,
            use_even_offset,
        )
        retained["ownership"] = "retained lower-face exterior"
        moved["ownership"] = "moved intact to rear-cassette exterior"
        retained_objects[section] = retained
        moved_objects[section] = moved
        shell_metrics[retained.name] = retained_metrics
        shell_metrics[moved.name] = moved_metrics

        boundary_edges = patch_boundary_edges(
            model, selected_by_section[section]
        )
        boundary_points = {
            vertex: points[vertex]
            for edge in boundary_edges
            for vertex in edge
        }
        seam = seam_v2.create_seam(
            f"V4_BOUNDARY__{section}",
            boundary_edges,
            boundary_points,
            float(config["review_display"]["seam_radius_mm"]),
            seam_material,
            seam_collection,
        )
        seam["meaning"] = "complete lossless ownership boundary"
        seam_objects.append(seam)

    rear_base_review = create_rear_base_review_copy(
        cassette_material, cassette_collection
    )
    cassette_objects = [*moved_objects.values(), rear_base_review]

    protected_after = {
        name: mesh_fingerprint(bpy.data.objects[name]) for name in protected_before
    }
    if protected_before != protected_after:
        changed = sorted(
            name
            for name in protected_before
            if protected_before[name] != protected_after[name]
        )
        raise ValueError(f"Protected Gate 8 source geometry changed: {changed}")

    camera = configure_scene(
        output_dir, int(config["review_display"]["render_resolution_px"])
    )
    render_paths = render_reviews(
        camera,
        output_dir,
        list(retained_objects.values()),
        cassette_objects,
        seam_objects,
    )

    scene = bpy.context.scene
    scene["review_status"] = config["status"]
    scene["lossless_exterior_repartition"] = True
    scene["source_gate8_geometry_modified"] = False
    scene["instructions"] = (
        "Blue/green are retained lower exterior shells. Orange rear shells "
        "plus orange rear_base are enlarged cassette ownership. Yellow is "
        "the exact ownership boundary. Hidden Gate 8 lower objects preserve "
        "all original reinforcement for the next separate assignment step."
    )
    blend_path = output_dir / "rear-cassette-lossless-repartition-review-v4.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    bpy.ops.object.select_all(action="DESELECT")
    export_objects = [
        bpy.data.objects[name]
        for name in sorted(PRODUCTION_PARTS - set(LOWER_SECTIONS) - {"rear_base"})
    ]
    export_objects.extend(retained_objects.values())
    export_objects.extend(cassette_objects)
    export_objects.extend(seam_objects)
    for obj in export_objects:
        obj.hide_viewport = False
        obj.select_set(True)
    glb_path = output_dir / "rear-cassette-lossless-repartition-review-v4.glb"
    bpy.ops.export_scene.gltf(
        filepath=str(glb_path), export_format="GLB", use_selection=True
    )

    selected_panels = sorted(
        {
            gate1.canonical_source_panel_id(model.faces[index].group)
            for index in selected
        }
    )
    report = {
        "status": config["status"],
        "source_gate8_blend": str(source_blend.relative_to(REPO_ROOT)),
        "source_gate8_blend_sha256": sha256(source_blend),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "shared_interface": str(interface_path.relative_to(REPO_ROOT)),
        "interface_revision": actual_revision,
        "repartition_equation": (
            "original lower exteriors = retained left/right lower shells + "
            "moved left/right cassette shells"
        ),
        "moved_source_face_count": len(selected),
        "moved_source_face_count_by_section": {
            section: len(indices)
            for section, indices in selected_by_section.items()
        },
        "retained_source_face_count_by_section": {
            section: len(indices)
            for section, indices in retained_by_section.items()
        },
        "retained_closure_face_count_by_section": {
            section: len(faces)
            for section, faces in closures_by_section.items()
        },
        "moved_source_panel_ids": selected_panels,
        "exterior_face_ledger": ledger,
        "shell_metrics": shell_metrics,
        "all_four_review_shells_closed_and_valid": all(
            metrics["boundary_edges"] == 0
            and metrics["nonmanifold_edges"] == 0
            and metrics["duplicate_faces"] == 0
            and metrics["degenerate_faces"] == 0
            for metrics in shell_metrics.values()
        ),
        "protected_geometry_fingerprints_before": protected_before,
        "protected_geometry_fingerprints_after": protected_after,
        "protected_gate8_geometry_unchanged": protected_before == protected_after,
        "source_gate8_lower_faces_modified": False,
        "reinforcement_status": (
            "all Gate 8 lower-face reinforcement is preserved unchanged in "
            "hidden source objects; V4 makes no reinforcement ownership claim"
        ),
        "cassette_connection_status": (
            "moved left/right rear shells and unchanged rear_base share cassette "
            "ownership but are not yet connected or reconciled with aluminum"
        ),
        "removed_gate8_review_references": removed_references,
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "glb": str(glb_path.relative_to(REPO_ROOT)),
            "renders": render_paths,
        },
        "no_stl_or_gcode_exported": True,
        "review_holds": config["review_holds"],
    }
    report_path = output_dir / (
        "rear-cassette-lossless-repartition-review-v4-validation.json"
    )
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "moved_source_face_count_by_section": report[
                    "moved_source_face_count_by_section"
                ],
                "exterior_face_ledger": ledger,
                "all_four_review_shells_closed_and_valid": report[
                    "all_four_review_shells_closed_and_valid"
                ],
                "protected_gate8_geometry_unchanged": report[
                    "protected_gate8_geometry_unchanged"
                ],
                "blend": report["generated_files"]["blend"],
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
