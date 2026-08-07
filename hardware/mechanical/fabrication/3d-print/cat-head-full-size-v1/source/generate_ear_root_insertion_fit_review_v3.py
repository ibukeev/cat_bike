#!/usr/bin/env python3
"""Generate the F-07/F-08/F-09 ear-root insertion-fit review."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_c002_outer_flange_dual_root_upper_head_review_v2 as c002_v2  # noqa: E402
import generate_ear_root_restored_coverage_review_v2 as ear_v2  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate7_glow_panel_inserts as gate7  # noqa: E402
import generate_gate8_full_size_iteration as gate8  # noqa: E402
import generate_rear_cassette_lossless_repartition_review_v5 as rear_v5  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/ear-root-insertion-fit-review-v3.json"
DEFAULT_OUTPUT = PACKAGE_ROOT / "output/60-ear-root-reviews/ear-root-insertion-fit-review-v3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(args)


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def point_at(camera: bpy.types.Object, target: Vector) -> None:
    camera.rotation_euler = (
        target - camera.location
    ).to_track_quat("-Z", "Y").to_euler()


def configure_scene(output_dir: Path, resolution_px: int) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.name = "Ear_Root_Insertion_Fit_Review_V3"
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "OBJECT"
    shading.show_shadows = True
    shading.show_cavity = True
    shading.cavity_type = "WORLD"
    shading.background_type = "VIEWPORT"
    shading.background_color = (0.035, 0.045, 0.06)
    scene.render.resolution_x = resolution_px
    scene.render.resolution_y = resolution_px
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    camera_data = bpy.data.cameras.new("EAR3_REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("EAR3_REVIEW_ONLY__Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 58.0
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            space.shading.type = "SOLID"
            space.shading.color_type = "OBJECT"
            space.region_3d.view_perspective = "CAMERA"
    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    return camera


def render_view(
    camera: bpy.types.Object,
    output_dir: Path,
    name: str,
    location: Vector,
    target: Vector,
    visible: set[bpy.types.Object],
) -> str:
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_render = obj not in visible
    camera.location = location
    point_at(camera, target)
    path = output_dir / "renders" / f"ear-root-fit-{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path.relative_to(REPO_ROOT))


def create_fit_skin(
    group: dict[str, Any],
    boundary: list[dict[str, Any]],
    context: dict[str, Any],
    material: bpy.types.Material,
) -> bpy.types.Object:
    """Create only the deep fit skin, excluding all legacy capture pads."""
    transformed = context["transformed"]
    surface_faces = gate7.group_surface_faces(group, context)
    used = sorted(
        {
            index
            for surface_face in surface_faces
            for index in surface_face["indices"]
        }
    )
    remap = {source: local for local, source in enumerate(used)}
    oriented = [
        (
            surface_face["indices"],
            surface_face["normal"],
            surface_face["center"],
        )
        for surface_face in surface_faces
    ]
    normals_by_vertex: dict[int, list[Vector]] = defaultdict(list)
    centers_by_vertex: dict[int, list[Vector]] = defaultdict(list)
    for indices, normal, center in oriented:
        for index in indices:
            normals_by_vertex[index].append(normal)
            centers_by_vertex[index].append(center)
    boundary_vertices = {
        index for record in boundary for index in record["edge"]
    }
    clearance = float(gate7.CONFIG["insert"]["perimeter_clearance_mm"])
    setback = float(gate7.CONFIG["insert"]["surface_setback_mm"])
    ear_interface = gate7.CONFIG.get("ear_root_interfaces", {}).get(
        group["name"]
    )
    ear_notch_vertices = {
        int(index)
        for index in (ear_interface or {}).get(
            "connector_source_vertices",
            [(ear_interface or {}).get("connector_source_vertex")],
        )
        if index is not None
    }
    if not ear_notch_vertices <= set(used):
        raise ValueError(
            f"{group['name']} is missing configured connector vertices"
        )
    side_tip_directions = {}
    for source_index in ear_notch_vertices:
        side_edges = [
            record
            for record in boundary
            if source_index in record["edge"]
            and not set(record["edge"]) <= ear_notch_vertices
        ]
        if len(side_edges) != 1:
            raise ValueError(
                f"{group['name']} connector tip {source_index} has "
                f"{len(side_edges)} exterior side edges"
            )
        other_index = next(
            index
            for index in side_edges[0]["edge"]
            if index != source_index
        )
        side_tip_directions[source_index] = (
            transformed[other_index] - transformed[source_index]
        ).normalized()

    output_vertices = []
    for index in used:
        point = transformed[index].copy()
        normal = sum(normals_by_vertex[index], Vector()).normalized()
        if index in boundary_vertices:
            target = sum(centers_by_vertex[index], Vector()) / len(
                centers_by_vertex[index]
            )
            direction = target - point
            direction -= normal * direction.dot(normal)
            if direction.length > 0.01:
                point += direction.normalized() * clearance
        if index in side_tip_directions:
            point += side_tip_directions[index] * float(
                gate7.CONFIG["ear_root_interfaces"]
                ["connector_side_tip_setback_mm"]
            )
        point -= normal * setback
        output_vertices.append(point)
    output_faces = [
        tuple(remap[index] for index in indices) for indices, _, _ in oriented
    ]
    gate7.localize_bridge_connector_notch(
        output_vertices,
        output_faces,
        remap,
        surface_faces,
        transformed,
        ear_interface,
    )
    obj = gate7.finish_surface_insert(
        f"EAR3_FIT_SKIN__{group['name']}",
        output_vertices,
        output_faces,
        material,
    )
    if len(gate5.components(obj)) != 1:
        raise ValueError(f"{group['name']} deep fit skin is disconnected")
    return obj


def frame_record(record: dict[str, Any]) -> dict[str, list[float]]:
    return {
        key: [float(value) for value in record[key]]
        for key in ("midpoint", "tangent", "inward", "radial")
    }


def generate_source_payloads(
    config: dict[str, Any], source_gate6: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    bpy.ops.wm.open_mainfile(filepath=str(source_gate6))
    original_config = gate7.CONFIG
    gate7.CONFIG = copy.deepcopy(original_config)
    relief = config["accepted_v2_relief"]
    fit = config["fit_clearance"]
    ear_values = gate7.CONFIG["ear_root_interfaces"]
    ear_values["connector_clearance_mm"] = float(
        relief["connector_clearance_mm"]
    )
    ear_values["connector_corner_relief_depth_mm"] = float(
        relief["connector_corner_relief_depth_mm"]
    )
    ear_values["connector_side_tip_setback_mm"] = float(
        relief["connector_side_tip_setback_mm"]
    )
    gate7.CONFIG["insert"]["perimeter_clearance_mm"] = float(
        fit["candidate_deep_body_perimeter_clearance_mm"]
    )
    gate7.CONFIG["visible_seam_cap"]["perimeter_clearance_mm"] = float(
        fit["candidate_visible_cap_perimeter_clearance_mm"]
    )
    try:
        context = gate7.source_context()
        groups = {
            group["name"]: group
            for group in gate7.connected_panel_groups(context)
        }
        material = gate5.material(
            "EAR3_FIT_BODY__yellow_source", (0.96, 0.77, 0.18, 0.8)
        )
        right_group = groups[
            config["sides"]["right"]["candidate_group"]
        ]
        boundary = gate7.group_boundary(right_group, context)
        deep = create_fit_skin(right_group, boundary, context, material)
        deep_payload = ear_v2.serialize_mesh(deep)
        gate7.add_visual_seam_cap(
            right_group, deep, boundary, context, material
        )
        if len(gate5.components(deep)) != 1:
            raise ValueError("Right fit cap did not unite with the deep body")
        full_payload = ear_v2.serialize_mesh(deep)

        frames = {}
        redundancy = {}
        for side, names in config["sides"].items():
            group = groups[names["candidate_group"]]
            side_boundary = gate7.group_boundary(group, context)
            hooks, screws = gate7.choose_mounts(group, side_boundary)
            if len(hooks) != 1 or len(screws) != 1:
                raise ValueError(f"{side} no longer has one path datum pair")
            frames[side] = {
                "pivot": frame_record(hooks[0]),
                "free_edge": frame_record(screws[0]),
            }
            redundancy[side] = ear_v2.prove_redundant_quad_face(
                group, context
            )
        return (
            {"deep": deep_payload, "full": full_payload},
            frames,
            redundancy,
        )
    finally:
        gate7.CONFIG = original_config


def apply_exact_ear_clearance(
    obj: bpy.types.Object,
    ear: bpy.types.Object,
    clearance_mm: float,
) -> dict[str, Any]:
    volume_before = gate5.mesh_volume(obj)
    faces_before = len(obj.data.polygons)
    cutter = gate8.expanded_insert_cutter(
        ear, clearance_mm, f"exact_ear_clearance_for_{obj.name}"
    )
    applied = 0
    for component in gate8.split_closed_components(cutter):
        if not gate8.bounding_boxes_overlap(obj, component):
            bpy.data.objects.remove(component, do_unlink=True)
            continue
        gate5.apply_boolean(obj, component, "DIFFERENCE", solver="EXACT")
        applied += 1
    boundary, nonmanifold = gate5.topology_counts(obj)
    components = len(gate5.components(obj))
    if boundary or nonmanifold or components != 1:
        raise ValueError(
            f"{obj.name} failed topology after exact-ear clearance: "
            f"components={components}, boundary={boundary}, "
            f"nonmanifold={nonmanifold}"
        )
    volume_after = gate5.mesh_volume(obj)
    return {
        "clearance_mm": clearance_mm,
        "cutter_components_applied": applied,
        "faces_before": faces_before,
        "faces_after": len(obj.data.polygons),
        "volume_before_mm3": round(volume_before, 4),
        "volume_after_mm3": round(volume_after, 4),
        "volume_removed_mm3": round(volume_before - volume_after, 4),
        "volume_removed_percent": round(
            100.0 * (volume_before - volume_after) / volume_before, 4
        ),
    }


def mirror_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "vertices": [
            [-vertex[0], vertex[1], vertex[2]]
            for vertex in payload["vertices"]
        ],
        "faces": [list(reversed(face)) for face in payload["faces"]],
    }


def world_triangle_intersection_count(
    first: bpy.types.Object, second: bpy.types.Object
) -> int:
    """Count intersections in world space, including object motion."""
    bpy.context.view_layer.update()
    def tree(obj: bpy.types.Object) -> BVHTree:
        obj.data.calc_loop_triangles()
        return BVHTree.FromPolygons(
            [obj.matrix_world @ vertex.co for vertex in obj.data.vertices],
            [tuple(triangle.vertices) for triangle in obj.data.loop_triangles],
            all_triangles=True,
        )

    return len(tree(first).overlap(tree(second)))


def collision_hits(
    obj: bpy.types.Object, targets: list[bpy.types.Object]
) -> dict[str, int]:
    hits = {}
    for target in targets:
        if not gate8.bounding_boxes_overlap(obj, target):
            continue
        count = world_triangle_intersection_count(obj, target)
        if count:
            hits[target.name] = count
    return hits


def path_samples(
    frame: dict[str, Any], values: dict[str, Any]
) -> list[dict[str, Any]]:
    if values.get("motion_mode") == "mirrored_world_outward_up":
        right_direction = Vector(values["right_direction"])
        side_sign = (
            1.0 if Vector(frame["pivot"]["midpoint"]).x > 0.0 else -1.0
        )
        direction = Vector(
            (
                abs(right_direction.x) * side_sign,
                right_direction.y,
                right_direction.z,
            )
        ).normalized()
        sample_count = int(values["total_sample_count"])
        total_translation = float(values["translation_mm"])
        return [
            {
                "phase": "translate_outward_up",
                "step": index,
                "rotation_degrees": 0.0,
                "translation_mm": round(
                    total_translation * index / (sample_count - 1), 4
                ),
                "matrix": Matrix.Translation(
                    direction
                    * total_translation
                    * index
                    / (sample_count - 1)
                ),
            }
            for index in range(sample_count)
        ]
    raise ValueError("Only the verified mirrored outward/upward path is supported")


def validate_path(
    side: str,
    full: bpy.types.Object,
    deep: bpy.types.Object,
    frame: dict[str, Any],
    config: dict[str, Any],
    structural_targets: list[bpy.types.Object],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    targets = [
        target for target in structural_targets if target.name != f"{side}_ear"
    ]
    margin = float(config["fit_clearance"]["deep_body_path_margin_mm"])
    envelope = gate8.expanded_insert_cutter(
        deep, margin, f"{side}_deep_body_path_margin"
    )
    samples = path_samples(frame, config["insertion_path"])
    actual_conflicts = []
    margin_conflicts = []
    maximum_actual = 0
    maximum_margin = 0
    for sample in samples:
        full.matrix_world = sample["matrix"]
        envelope.matrix_world = sample["matrix"]
        actual_hits = collision_hits(full, targets)
        margin_hits = collision_hits(envelope, targets)
        maximum_actual = max(maximum_actual, sum(actual_hits.values()))
        maximum_margin = max(maximum_margin, sum(margin_hits.values()))
        metadata = {
            key: value for key, value in sample.items() if key != "matrix"
        }
        if actual_hits:
            actual_conflicts.append({**metadata, "hits": actual_hits})
        if margin_hits:
            margin_conflicts.append({**metadata, "hits": margin_hits})
    full.matrix_world = Matrix.Identity(4)
    envelope.matrix_world = Matrix.Identity(4)
    bpy.data.objects.remove(envelope, do_unlink=True)
    if actual_conflicts or margin_conflicts:
        raise ValueError(
            f"{side} insertion path is not clear: "
            f"actual={actual_conflicts}, margin={margin_conflicts}"
        )
    keyframes = [samples[0], samples[len(samples) // 2], samples[-1]]
    return (
        {
            "side": side,
            "ear_removed_during_path": True,
            "checked_structural_shells": sorted(
                target.name for target in targets
            ),
            "sample_count": len(samples),
            "maximum_actual_triangle_intersection_pairs": maximum_actual,
            "deep_body_margin_mm": margin,
            "maximum_deep_margin_triangle_intersection_pairs": maximum_margin,
            "actual_path_clear": not actual_conflicts,
            "deep_margin_path_clear": not margin_conflicts,
            "keyframes": [
                {
                    key: value
                    for key, value in sample.items()
                    if key != "matrix"
                }
                for sample in keyframes
            ],
        },
        samples,
    )


def require_saddle(
    stage5_report: dict[str, Any], joint_pair: str
) -> dict[str, Any]:
    matches = [
        record
        for record in stage5_report["flange_tab_manifest"]
        if record["name"].startswith(
            f"internal_flange_tab_{joint_pair}_"
        )
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected one saddle for {joint_pair}")
    record = matches[0]
    if record["internal_m3_screws"] != 4:
        raise ValueError(f"{joint_pair} no longer has four internal M3 paths")
    if record["alignment_dowels"] or record["exterior_fastener_holes"]:
        raise ValueError(f"{joint_pair} gained an exterior artifact")
    return record


def make_ghost(
    source: bpy.types.Object,
    name: str,
    matrix: Matrix,
    material: bpy.types.Material,
    collection: bpy.types.Collection,
) -> bpy.types.Object:
    ghost = source.copy()
    ghost.data = source.data.copy()
    ghost.name = name
    ghost.data.materials.clear()
    ghost.data.materials.append(material)
    ghost.color = material.diffuse_color
    ghost.matrix_world = matrix
    ghost.show_in_front = True
    collection.objects.link(ghost)
    ghost.hide_viewport = True
    ghost.hide_render = True
    ghost.hide_set(True)
    return ghost


def main() -> None:
    args = parse_args()
    config_path = args.config.resolve()
    output_dir = args.output_dir.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    source_gate8 = repo_path(config["source_gate8_blend"])
    source_gate6 = repo_path(config["source_gate6_blend"])
    stage5_report = json.loads(
        repo_path(config["stage5_validation"]).read_text(encoding="utf-8")
    )
    shared_interface = json.loads(
        repo_path(config["shared_interface_path"]).read_text(encoding="utf-8")
    )
    if (
        shared_interface["interface_revision"]
        != config["required_interface_revision"]
    ):
        raise ValueError("Shared shell/aluminum interface revision changed")
    output_dir.mkdir(parents=True, exist_ok=True)

    source_payloads, path_frames, redundant_faces = generate_source_payloads(
        config, source_gate6
    )
    bpy.ops.wm.open_mainfile(filepath=str(source_gate8))
    source_mesh_names = sorted(
        obj.name for obj in bpy.data.objects if obj.type == "MESH"
    )
    protected_before = {
        name: rear_v5.mesh_fingerprint(bpy.data.objects[name])
        for name in source_mesh_names
    }
    structural_targets = [
        c002_v2.require_object(name) for name in gate2.SECTION_ORDER
    ]
    for target in structural_targets:
        target.hide_set(False)
        target.hide_viewport = False

    right_deep = ear_v2.deserialize_mesh(
        "EAR3_VALIDATION__right_deep_fit_body", source_payloads["deep"]
    )
    bpy.context.scene.collection.objects.link(right_deep)
    right_full = ear_v2.deserialize_mesh(
        config["sides"]["right"]["candidate_name"],
        source_payloads["full"],
    )
    bpy.context.scene.collection.objects.link(right_full)
    ear_clearance = float(
        config["fit_clearance"]["exact_ear_local_clearance_mm"]
    )
    right_deep_trim = apply_exact_ear_clearance(
        right_deep, bpy.data.objects["right_ear"], ear_clearance
    )
    right_full_trim = apply_exact_ear_clearance(
        right_full, bpy.data.objects["right_ear"], ear_clearance
    )
    right_deep_payload = ear_v2.serialize_mesh(right_deep)
    right_full_payload = ear_v2.serialize_mesh(right_full)
    left_deep = ear_v2.deserialize_mesh(
        "EAR3_VALIDATION__left_deep_fit_body",
        mirror_payload(right_deep_payload),
    )
    bpy.context.scene.collection.objects.link(left_deep)
    left_full = ear_v2.deserialize_mesh(
        config["sides"]["left"]["candidate_name"],
        mirror_payload(right_full_payload),
    )
    bpy.context.scene.collection.objects.link(left_full)
    candidates = {"left": left_full, "right": right_full}
    deep_bodies = {"left": left_deep, "right": right_deep}

    display = config["display"]
    candidate_material = gate5.material(
        "EAR3_FIT_BODY_ONLY__yellow",
        c002_v2.hex_color(display["candidate_insert_color"]),
    )
    for candidate in candidates.values():
        candidate.data.materials.clear()
        candidate.data.materials.append(candidate_material)
        candidate.color = c002_v2.hex_color(
            display["candidate_insert_color"]
        )
        candidate.show_in_front = True

    side_reports = []
    path_reports = {}
    path_samples_by_side = {}
    for side, names in config["sides"].items():
        candidate = candidates[side]
        deep = deep_bodies[side]
        boundary, nonmanifold = gate5.topology_counts(candidate)
        components = len(gate5.components(candidate))
        if boundary or nonmanifold or components != 1:
            raise ValueError(f"{side} final fit body failed topology")
        seated_hits = collision_hits(candidate, structural_targets)
        if seated_hits:
            raise ValueError(f"{side} seated fit body collides: {seated_hits}")
        saddle = require_saddle(stage5_report, names["joint_pair"])
        path_report, samples = validate_path(
            side,
            candidate,
            deep,
            path_frames[side],
            config,
            structural_targets,
        )
        path_reports[side] = path_report
        path_samples_by_side[side] = samples
        side_reports.append(
            {
                "side": side,
                "candidate": candidate.name,
                "topology": {
                    "connected_components": components,
                    "boundary_edges": boundary,
                    "nonmanifold_edges": nonmanifold,
                },
                "seated_structural_shell_intersections": seated_hits,
                "seated_all_structural_shells_clear": not seated_hits,
                "ear_installed_for_seated_check": True,
                "ear_removed_for_insertion_path": True,
                "saddle": {
                    "name": saddle["name"],
                    "internal_m3_paths": saddle["internal_m3_screws"],
                    "alignment_dowels": saddle["alignment_dowels"],
                    "exterior_fastener_holes": saddle[
                        "exterior_fastener_holes"
                    ],
                },
                "redundant_quad_face_proof": redundant_faces[side],
                "path_validation": path_report,
            }
        )

    left_bounds = ear_v2.mesh_bounds(left_full)
    right_bounds = ear_v2.mesh_bounds(right_full)
    symmetry_error = max(
        abs(left_bounds["minimum"][0] + right_bounds["maximum"][0]),
        abs(left_bounds["maximum"][0] + right_bounds["minimum"][0]),
        *(
            abs(left_bounds[key][axis] - right_bounds[key][axis])
            for key in ("minimum", "maximum")
            for axis in (1, 2)
        ),
    )
    if symmetry_error > 0.01:
        raise ValueError(f"V3 fit bodies are not mirrored: {symmetry_error}")

    collection_names = (
        "EAR3_EXACT_EARS_CYAN__UNCHANGED",
        "EAR3_EXACT_UPPER_HEADS_GRAY__UNCHANGED",
        "EAR3_FIT_BODY_ONLY_YELLOW__NO_RETENTION",
        "EAR3_PATH_GHOSTS__HIDDEN_BY_DEFAULT",
        "EAR3_OTHER_SOURCE_GEOMETRY__HIDDEN",
    )
    collections = {}
    for name in collection_names:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        collections[name] = collection
    all_visible: set[bpy.types.Object] = set()
    side_visible: dict[str, set[bpy.types.Object]] = {}
    ghosts: dict[str, dict[str, bpy.types.Object]] = {}
    mid_path_material = gate5.material(
        "EAR3_PATH__outward_up_30mm_blue",
        c002_v2.hex_color(display["mid_path_color"]),
    )
    final_path_material = gate5.material(
        "EAR3_PATH__outward_up_60mm_green",
        c002_v2.hex_color(display["final_path_color"]),
    )
    for side, names in config["sides"].items():
        ear = c002_v2.require_object(names["ear"])
        upper = c002_v2.require_object(names["upper_head"])
        candidate = candidates[side]
        ear.color = c002_v2.hex_color(display["ear_color"])
        upper.color = c002_v2.hex_color(display["upper_head_color"])
        ear.show_wire = True
        upper.show_wire = True
        for obj in (ear, upper, candidate):
            obj.hide_viewport = False
            obj.hide_render = False
            obj.hide_set(False)
        c002_v2.link_reference(
            ear, collections["EAR3_EXACT_EARS_CYAN__UNCHANGED"]
        )
        c002_v2.link_reference(
            upper, collections["EAR3_EXACT_UPPER_HEADS_GRAY__UNCHANGED"]
        )
        c002_v2.link_reference(
            candidate,
            collections["EAR3_FIT_BODY_ONLY_YELLOW__NO_RETENTION"],
        )
        visible = {ear, upper, candidate}
        side_visible[side] = visible
        all_visible |= visible
        samples = path_samples_by_side[side]
        midpoint_index = len(samples) // 2
        ghosts[side] = {
            "mid_path": make_ghost(
                candidate,
                f"EAR3_PATH_GHOST__{side}__outward_up_30mm",
                samples[midpoint_index]["matrix"],
                mid_path_material,
                collections["EAR3_PATH_GHOSTS__HIDDEN_BY_DEFAULT"],
            ),
            "final_path": make_ghost(
                candidate,
                f"EAR3_PATH_GHOST__{side}__outward_up_60mm",
                samples[-1]["matrix"],
                final_path_material,
                collections["EAR3_PATH_GHOSTS__HIDDEN_BY_DEFAULT"],
            ),
        }

    for deep in deep_bodies.values():
        bpy.data.objects.remove(deep, do_unlink=True)
    source_set = {bpy.data.objects[name] for name in source_mesh_names}
    for obj in source_set:
        if obj in all_visible:
            continue
        c002_v2.link_reference(
            obj, collections["EAR3_OTHER_SOURCE_GEOMETRY__HIDDEN"]
        )
        obj.hide_viewport = True
        obj.hide_render = True
        obj.hide_set(True)
    for obj in all_visible:
        obj.hide_viewport = False
        obj.hide_render = False
        obj.hide_set(False)

    camera = configure_scene(
        output_dir, int(display["render_resolution_px"])
    )
    renders = [
        render_view(
            camera,
            output_dir,
            "both-seated-interior",
            Vector((0.0, 430.0, 270.0)),
            Vector((0.0, 166.0, 222.0)),
            all_visible,
        ),
        render_view(
            camera,
            output_dir,
            "left-seated-exterior",
            Vector((-285.0, -100.0, 270.0)),
            Vector((-92.0, 168.0, 220.0)),
            side_visible["left"],
        ),
        render_view(
            camera,
            output_dir,
            "right-seated-exterior",
            Vector((285.0, -100.0, 270.0)),
            Vector((92.0, 168.0, 220.0)),
            side_visible["right"],
        ),
        render_view(
            camera,
            output_dir,
            "left-seated-interior",
            Vector((-285.0, 365.0, 270.0)),
            Vector((-92.0, 168.0, 220.0)),
            side_visible["left"],
        ),
        render_view(
            camera,
            output_dir,
            "right-seated-interior",
            Vector((285.0, 365.0, 270.0)),
            Vector((92.0, 168.0, 220.0)),
            side_visible["right"],
        ),
    ]
    for side, sign in (("left", -1.0), ("right", 1.0)):
        upper = c002_v2.require_object(config["sides"][side]["upper_head"])
        candidate = candidates[side]
        location = Vector((sign * 285.0, 365.0, 270.0))
        target = Vector((sign * 92.0, 168.0, 220.0))
        renders.extend(
            [
                render_view(
                    camera,
                    output_dir,
                    f"{side}-path-01-seated-ear-removed",
                    location,
                    target,
                    {upper, candidate},
                ),
                render_view(
                    camera,
                    output_dir,
                    f"{side}-path-02-outward-up-30mm",
                    location,
                    target,
                    {upper, ghosts[side]["mid_path"]},
                ),
                render_view(
                    camera,
                    output_dir,
                    f"{side}-path-03-outward-up-60mm",
                    location,
                    target,
                    {upper, ghosts[side]["final_path"]},
                ),
            ]
        )

    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in all_visible
            obj.hide_render = obj not in all_visible
            obj.hide_set(obj not in all_visible)
    camera.location = Vector((0.0, 430.0, 270.0))
    point_at(camera, Vector((0.0, 166.0, 222.0)))

    protected_after = {
        name: rear_v5.mesh_fingerprint(bpy.data.objects[name])
        for name in source_mesh_names
    }
    if protected_before != protected_after:
        raise ValueError("V3 fit review changed exact Gate 8 source geometry")
    scene = bpy.context.scene
    scene["review_status"] = config["status"]
    scene["feedback_ids"] = "F-07,F-08,F-09"
    scene["fit_body_only_no_retention"] = True
    scene["deep_body_clearance_mm"] = config["fit_clearance"][
        "candidate_deep_body_perimeter_clearance_mm"
    ]
    scene["visible_cap_clearance_mm"] = config["fit_clearance"][
        "candidate_visible_cap_perimeter_clearance_mm"
    ]
    scene["path_sample_count_per_side"] = config["insertion_path"][
        "total_sample_count"
    ]
    scene["all_digital_path_samples_clear"] = True
    scene["source_shell_geometry_changed"] = False
    blend_path = output_dir / "ear-root-insertion-fit-review-v3.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "feedback_scope": ["F-07", "F-08", "F-09"],
        "physical_acceptance_test": "A-07 remains pending a physical coupon",
        "source_gate8_blend": str(source_gate8.relative_to(REPO_ROOT)),
        "source_gate6_blend": str(source_gate6.relative_to(REPO_ROOT)),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "physical_fit_feedback": config["physical_fit_feedback"],
        "interface_revision": shared_interface["interface_revision"],
        "exact_gate8_source_mesh_count": len(source_mesh_names),
        "exact_gate8_source_meshes_unchanged": True,
        "accepted_v2_relief_preserved": config["accepted_v2_relief"],
        "fit_clearance": config["fit_clearance"],
        "right_canonical_deep_body_ear_trim": right_deep_trim,
        "right_canonical_full_body_ear_trim": right_full_trim,
        "left_is_exact_mirror_of_right_after_ear_trim": True,
        "maximum_mirror_bounds_error_mm": round(symmetry_error, 6),
        "side_records": side_reports,
        "path_validation": path_reports,
        "total_path_samples_both_sides": sum(
            record["sample_count"] for record in path_reports.values()
        ),
        "all_seated_structural_shell_checks_clear": all(
            record["seated_all_structural_shells_clear"]
            for record in side_reports
        ),
        "all_actual_path_samples_clear": all(
            record["actual_path_clear"] for record in path_reports.values()
        ),
        "all_deep_margin_path_samples_clear": all(
            record["deep_margin_path_clear"]
            for record in path_reports.values()
        ),
        "legacy_retention_geometry_in_candidate": False,
        "retention_redesign_deferred": ["F-10", "F-11", "F-12"],
        "candidate_is_printable_finished_part": False,
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": renders,
        },
        "no_stl_or_gcode_exported": True,
        "not_print_released": True,
        "review_holds": config["review_holds"],
    }
    report_path = output_dir / "ear-root-insertion-fit-review-v3-validation.json"
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
