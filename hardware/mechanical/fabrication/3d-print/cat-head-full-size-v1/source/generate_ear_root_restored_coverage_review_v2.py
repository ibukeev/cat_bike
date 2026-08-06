#!/usr/bin/env python3
"""Generate isolated mirrored ear-root inserts with restored coverage."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_c002_outer_flange_dual_root_upper_head_review_v2 as v2  # noqa: E402
import generate_gate2_section_layout as gate2  # noqa: E402
import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_gate7_glow_panel_inserts as gate7  # noqa: E402
import generate_rear_cassette_lossless_repartition_review_v5 as v5  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = PACKAGE_ROOT / "config/ear-root-restored-coverage-review-v2.json"
DEFAULT_OUTPUT = PACKAGE_ROOT / "output/00-current-review"


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
    scene.name = "Ear_Root_Restored_Coverage_Review_V2"
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
    camera_data = bpy.data.cameras.new("EAR2_REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("EAR2_REVIEW_ONLY__Camera", camera_data)
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
    path = output_dir / "renders" / f"ear-root-restored-{name}.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return str(path.relative_to(REPO_ROOT))


def require_single_ear_record(
    manifest: dict[str, Any], joint_pair: str
) -> dict[str, Any]:
    matches = [
        record
        for record in manifest["flange_tab_manifest"]
        if record["name"].startswith(
            f"internal_flange_tab_{joint_pair}_"
        )
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Expected one integrated saddle record for {joint_pair}, "
            f"found {len(matches)}"
        )
    return matches[0]


def serialize_mesh(obj: bpy.types.Object) -> dict[str, Any]:
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        matrix = obj.matrix_world
        return {
            "vertices": [
                [float(value) for value in matrix @ vertex.co]
                for vertex in mesh.vertices
            ],
            "faces": [list(poly.vertices) for poly in mesh.polygons],
        }
    finally:
        evaluated.to_mesh_clear()


def deserialize_mesh(name: str, payload: dict[str, Any]) -> bpy.types.Object:
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(payload["vertices"], [], payload["faces"])
    mesh.update(calc_edges=True)
    obj = bpy.data.objects.new(name, mesh)
    return obj


def mesh_bounds(obj: bpy.types.Object) -> dict[str, list[float]]:
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return {
        "minimum": [min(point[index] for point in points) for index in range(3)],
        "maximum": [max(point[index] for point in points) for index in range(3)],
    }


def prove_redundant_quad_face(
    group: dict[str, Any], context: dict[str, Any]
) -> dict[str, Any]:
    quad_faces = [
        face_index
        for face_index in group["face_indices"]
        if context["panel_by_face"][face_index].startswith("QUAD")
    ]
    if len(quad_faces) != 2:
        raise ValueError(f"{group['name']} no longer has two QUAD triangles")

    def area(face_index: int) -> float:
        points = [
            context["transformed"][index]
            for index in context["model"].faces[face_index].indices
        ]
        return (
            (points[1] - points[0]).cross(points[2] - points[0]).length
            / 2.0
        )

    larger, smaller = sorted(quad_faces, key=area, reverse=True)
    larger_indices = tuple(context["model"].faces[larger].indices)
    smaller_indices = tuple(context["model"].faces[smaller].indices)
    shared = set(larger_indices) & set(smaller_indices)
    if len(shared) != 2:
        raise ValueError(f"{group['name']} QUAD triangles do not share an edge")
    test_index = next(index for index in smaller_indices if index not in shared)
    a, b, c = [context["transformed"][index] for index in larger_indices]
    point = context["transformed"][test_index]
    v0 = b - a
    v1 = c - a
    v2_point = point - a
    d00 = v0.dot(v0)
    d01 = v0.dot(v1)
    d11 = v1.dot(v1)
    d20 = v2_point.dot(v0)
    d21 = v2_point.dot(v1)
    denominator = d00 * d11 - d01 * d01
    second = (d11 * d20 - d01 * d21) / denominator
    third = (d00 * d21 - d01 * d20) / denominator
    first = 1.0 - second - third
    plane_normal = v0.cross(v1).normalized()
    plane_error = abs(v2_point.dot(plane_normal))
    barycentric = [first, second, third]
    contained = min(barycentric) >= -1e-6 and plane_error < 0.01
    if not contained:
        raise ValueError(f"{group['name']} omitted QUAD face is not redundant")
    return {
        "panel": context["panel_by_face"][larger],
        "retained_face_index": larger,
        "omitted_face_index": smaller,
        "omitted_unique_vertex": test_index,
        "barycentric_in_retained_triangle": [
            round(value, 6) for value in barycentric
        ],
        "plane_error_mm": round(plane_error, 6),
        "fully_contained_and_coplanar": contained,
        "safe_to_add_as_overlapping_face": False,
    }


def generate_candidate_payloads(
    config: dict[str, Any], source_gate6: Path
) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    bpy.ops.wm.open_mainfile(filepath=str(source_gate6))
    original_config = gate7.CONFIG
    gate7.CONFIG = copy.deepcopy(original_config)
    relief = config["candidate_relief"]
    gate7.CONFIG["ear_root_interfaces"]["connector_clearance_mm"] = float(
        relief["connector_clearance_mm"]
    )
    gate7.CONFIG["ear_root_interfaces"][
        "connector_corner_relief_depth_mm"
    ] = float(relief["connector_corner_relief_depth_mm"])
    gate7.CONFIG["ear_root_interfaces"][
        "connector_side_tip_setback_mm"
    ] = float(relief["connector_side_tip_setback_mm"])
    try:
        context = gate7.source_context()
        groups = {
            group["name"]: group
            for group in gate7.connected_panel_groups(context)
        }
        shells = {
            name: bpy.data.objects[name] for name in gate2.SECTION_ORDER
        }
        material = gate5.material(
            "EAR2_CANDIDATE__frosted_insert", (0.96, 0.77, 0.18, 0.8)
        )
        inserts: list[bpy.types.Object] = []
        object_by_side: dict[str, bpy.types.Object] = {}
        redundancy: dict[str, Any] = {}
        for side, names in config["sides"].items():
            group = groups[names["candidate_group"]]
            redundancy[side] = prove_redundant_quad_face(group, context)
            boundary = gate7.group_boundary(group, context)
            hooks, screws = gate7.choose_mounts(group, boundary)
            insert = gate7.create_insert(
                group,
                boundary,
                [*hooks, *screws],
                context,
                material,
            )
            gate7.add_visual_seam_cap(
                group, insert, boundary, context, material
            )
            gate7.add_ear_root_bridge(
                group, insert, context, material
            )
            for hook_number, record in enumerate(hooks, start=1):
                owner = shells[record["owner"]]
                gate7.add_fixed_hook(
                    group["name"],
                    hook_number,
                    record,
                    owner,
                    owner.data.materials[0],
                )
            for mount_number, record in enumerate(screws, start=1):
                owner = shells[record["owner"]]
                gate7.add_screw_mount(
                    group["name"],
                    mount_number,
                    record,
                    insert,
                    owner,
                    material,
                    owner.data.materials[0],
                )
            inserts.append(insert)
            object_by_side[side] = insert
        clearance = gate7.validate_ear_connector_clearance(inserts)
        payloads = {
            side: serialize_mesh(obj) for side, obj in object_by_side.items()
        }
        for side, obj in object_by_side.items():
            boundary_edges, nonmanifold_edges = gate5.topology_counts(obj)
            if boundary_edges or nonmanifold_edges:
                raise ValueError(f"{side} candidate insert is not manifold")
            if len(gate5.components(obj)) != 1:
                raise ValueError(f"{side} candidate insert is disconnected")
        return payloads, clearance, redundancy
    finally:
        gate7.CONFIG = original_config


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

    payloads, clearance, redundant_faces = generate_candidate_payloads(
        config, source_gate6
    )
    bpy.ops.wm.open_mainfile(filepath=str(source_gate8))

    protected_names = {
        names[key]
        for names in config["sides"].values()
        for key in ("ear", "upper_head")
    }
    protected_before = {
        name: v5.mesh_fingerprint(v2.require_object(name))
        for name in protected_names
    }
    collection_names = (
        "EAR2_EXACT_EARS_CYAN__UNCHANGED",
        "EAR2_EXACT_UPPER_HEADS_GRAY__UNCHANGED",
        "EAR2_RESTORED_COVERAGE_INSERTS_YELLOW__REVIEW",
        "EAR2_REJECTED_38x18_INSERTS__HIDDEN",
        "EAR2_OTHER_SOURCE_GEOMETRY__HIDDEN",
    )
    collections = {}
    for name in collection_names:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
        collections[name] = collection

    candidate_material = gate5.material(
        "EAR2_CANDIDATE__yellow", v2.hex_color(
            config["display"]["candidate_insert_color"]
        )
    )
    side_visible: dict[str, set[bpy.types.Object]] = {}
    all_visible: set[bpy.types.Object] = set()
    candidates: set[bpy.types.Object] = set()
    side_reports = []
    for side, names in config["sides"].items():
        ear = v2.require_object(names["ear"])
        upper = v2.require_object(names["upper_head"])
        rejected = v2.require_object(names["rejected_insert"])
        candidate = deserialize_mesh(names["candidate_name"], payloads[side])
        collections[
            "EAR2_RESTORED_COVERAGE_INSERTS_YELLOW__REVIEW"
        ].objects.link(candidate)
        candidate.data.materials.append(candidate_material)
        ear.color = v2.hex_color(config["display"]["ear_color"])
        upper.color = v2.hex_color(config["display"]["upper_head_color"])
        candidate.color = v2.hex_color(
            config["display"]["candidate_insert_color"]
        )
        candidate.show_in_front = True
        ear.show_wire = True
        upper.show_wire = True
        for obj in (ear, upper, candidate):
            obj.hide_viewport = False
            obj.hide_render = False
            obj.hide_set(False)
        rejected.hide_viewport = True
        rejected.hide_render = True
        rejected.hide_set(True)
        v2.link_reference(ear, collections["EAR2_EXACT_EARS_CYAN__UNCHANGED"])
        v2.link_reference(
            upper,
            collections["EAR2_EXACT_UPPER_HEADS_GRAY__UNCHANGED"],
        )
        v2.link_reference(
            rejected, collections["EAR2_REJECTED_38x18_INSERTS__HIDDEN"]
        )
        boundary_edges, nonmanifold_edges = gate5.topology_counts(candidate)
        components = len(gate5.components(candidate))
        if boundary_edges or nonmanifold_edges or components != 1:
            raise ValueError(f"{side} deserialized candidate failed topology")
        saddle = require_single_ear_record(stage5_report, names["joint_pair"])
        if saddle["internal_m3_screws"] != 4:
            raise ValueError(f"{side} saddle no longer has four M3 paths")
        if saddle["alignment_dowels"] or saddle["exterior_fastener_holes"]:
            raise ValueError(f"{side} saddle gained an exterior artifact")
        clearance_record = clearance[names["candidate_group"]]
        if clearance_record[
            "minimum_connector_vertex_to_insert_surface_gap_mm"
        ] < float(config["candidate_relief"]["connector_clearance_mm"]):
            raise ValueError(f"{side} candidate saddle clearance is too small")
        visible = {ear, upper, candidate}
        side_visible[side] = visible
        all_visible |= visible
        candidates.add(candidate)
        side_reports.append(
            {
                "side": side,
                "ear": ear.name,
                "upper_head": upper.name,
                "candidate_insert": candidate.name,
                "rejected_insert_hidden": rejected.name,
                "joint_pair": names["joint_pair"],
                "one_integrated_saddle": True,
                "internal_m3_paths": saddle["internal_m3_screws"],
                "alignment_dowels": saddle["alignment_dowels"],
                "exterior_fastener_holes": saddle[
                    "exterior_fastener_holes"
                ],
                "candidate_topology": {
                    "connected_components": components,
                    "boundary_edges": boundary_edges,
                    "nonmanifold_edges": nonmanifold_edges,
                },
                "connector_clearance_validation": clearance_record,
                "redundant_quad_face_proof": redundant_faces[side],
                "bounds_mm": mesh_bounds(candidate),
            }
        )

    for obj in bpy.data.objects:
        if obj.type != "MESH" or obj in all_visible:
            continue
        if obj.name not in {
            names["rejected_insert"] for names in config["sides"].values()
        }:
            v2.link_reference(
                obj, collections["EAR2_OTHER_SOURCE_GEOMETRY__HIDDEN"]
            )
        obj.hide_viewport = True
        obj.hide_render = True
        obj.hide_set(True)

    left_bounds = next(
        record["bounds_mm"] for record in side_reports if record["side"] == "left"
    )
    right_bounds = next(
        record["bounds_mm"] for record in side_reports if record["side"] == "right"
    )
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
        raise ValueError(
            f"Candidate inserts are not mirrored: {symmetry_error:.4f} mm"
        )

    camera = configure_scene(
        output_dir, int(config["display"]["render_resolution_px"])
    )
    renders = [
        render_view(
            camera,
            output_dir,
            "both-interior",
            Vector((0.0, 430.0, 270.0)),
            Vector((0.0, 166.0, 222.0)),
            all_visible,
        ),
        render_view(
            camera,
            output_dir,
            "left-interior",
            Vector((-285.0, 365.0, 270.0)),
            Vector((-92.0, 168.0, 220.0)),
            side_visible["left"],
        ),
        render_view(
            camera,
            output_dir,
            "right-interior",
            Vector((285.0, 365.0, 270.0)),
            Vector((92.0, 168.0, 220.0)),
            side_visible["right"],
        ),
        render_view(
            camera,
            output_dir,
            "left-exterior",
            Vector((-285.0, -100.0, 270.0)),
            Vector((-92.0, 168.0, 220.0)),
            side_visible["left"],
        ),
        render_view(
            camera,
            output_dir,
            "right-exterior",
            Vector((285.0, -100.0, 270.0)),
            Vector((92.0, 168.0, 220.0)),
            side_visible["right"],
        ),
        render_view(
            camera,
            output_dir,
            "left-coverage-cutaway",
            Vector((-255.0, 345.0, 255.0)),
            Vector((-92.0, 168.0, 220.0)),
            {
                v2.require_object(config["sides"]["left"]["ear"]),
                next(
                    obj
                    for obj in candidates
                    if obj.name == config["sides"]["left"]["candidate_name"]
                ),
            },
        ),
        render_view(
            camera,
            output_dir,
            "right-coverage-cutaway",
            Vector((255.0, 345.0, 255.0)),
            Vector((92.0, 168.0, 220.0)),
            {
                v2.require_object(config["sides"]["right"]["ear"]),
                next(
                    obj
                    for obj in candidates
                    if obj.name == config["sides"]["right"]["candidate_name"]
                ),
            },
        ),
        render_view(
            camera,
            output_dir,
            "candidate-inserts-only",
            Vector((0.0, 430.0, 250.0)),
            Vector((0.0, 168.0, 214.0)),
            candidates,
        ),
    ]

    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in all_visible
            obj.hide_render = obj not in all_visible
    camera.location = Vector((0.0, 430.0, 270.0))
    point_at(camera, Vector((0.0, 166.0, 222.0)))

    protected_after = {
        name: v5.mesh_fingerprint(v2.require_object(name))
        for name in protected_names
    }
    if protected_before != protected_after:
        raise ValueError("Candidate review changed an exact source shell mesh")
    old_relief = config["rejected_gate8_relief"]
    new_relief = config["candidate_relief"]
    if not (
        new_relief["connector_corner_relief_depth_mm"]
        < old_relief["connector_corner_relief_depth_mm"]
        and new_relief["connector_side_tip_setback_mm"]
        < old_relief["connector_side_tip_setback_mm"]
    ):
        raise ValueError("Candidate does not reduce both rejected relief values")

    scene = bpy.context.scene
    scene["review_status"] = config["status"]
    scene["geometry_changed"] = True
    scene["source_shell_geometry_changed"] = False
    scene["candidate_insert_count"] = len(candidates)
    scene["ear_saddle_m3_paths_per_side"] = 4
    scene["candidate_corner_relief_mm"] = new_relief[
        "connector_corner_relief_depth_mm"
    ]
    scene["candidate_side_setback_mm"] = new_relief[
        "connector_side_tip_setback_mm"
    ]
    scene["candidate_minimum_saddle_gap_mm"] = min(
        record["connector_clearance_validation"]
        ["minimum_connector_vertex_to_insert_surface_gap_mm"]
        for record in side_reports
    )
    blend_path = output_dir / "ear-root-restored-coverage-review-v2.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "source_gate8_blend": str(source_gate8.relative_to(REPO_ROOT)),
        "source_gate6_blend": str(source_gate6.relative_to(REPO_ROOT)),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "interface_revision": shared_interface["interface_revision"],
        "candidate_insert_geometry_changed": True,
        "exact_gate8_ear_and_upper_head_meshes_unchanged": True,
        "protected_source_meshes": sorted(protected_names),
        "rejected_gate8_relief": old_relief,
        "candidate_relief": new_relief,
        "corner_relief_reduction_percent": round(
            100.0
            * (
                1.0
                - new_relief["connector_corner_relief_depth_mm"]
                / old_relief["connector_corner_relief_depth_mm"]
            ),
            1,
        ),
        "side_setback_reduction_percent": round(
            100.0
            * (
                1.0
                - new_relief["connector_side_tip_setback_mm"]
                / old_relief["connector_side_tip_setback_mm"]
            ),
            1,
        ),
        "mirrored_candidate_count": len(candidates),
        "maximum_mirror_bounds_error_mm": round(symmetry_error, 6),
        "side_records": side_reports,
        "visible_mesh_objects": sorted(obj.name for obj in all_visible),
        "visible_round_stick_or_external_block_objects": [],
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": renders,
        },
        "no_stl_or_gcode_exported": True,
        "not_print_released": True,
        "review_holds": config["review_holds"],
    }
    report_path = (
        output_dir
        / "ear-root-restored-coverage-review-v2-validation.json"
    )
    report_path.write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
