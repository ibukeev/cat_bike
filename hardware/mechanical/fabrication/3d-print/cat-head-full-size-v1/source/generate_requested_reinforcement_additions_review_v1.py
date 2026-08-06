#!/usr/bin/env python3
"""Generate all user-requested post-H1 reinforcement additions for review.

The review adds three left tie rails, two exact X-mirrored right ties, one
independently surface-fitted right long tie, and an exact right mirror of the
asymmetric L C056 rib. Existing meshes remain unchanged.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree


SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import generate_gate5_ribs_and_joints as gate5  # noqa: E402
import generate_horizontal_seam_interface_review_v1 as horizontal_v1  # noqa: E402
import generate_rear_cassette_lossless_repartition_review_v5 as v5  # noqa: E402


PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]
DEFAULT_CONFIG = (
    PACKAGE_ROOT / "config/requested-reinforcement-additions-review-v1.json"
)
DEFAULT_OUTPUT = (
    PACKAGE_ROOT / "output/00-current-review"
)


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


def world_geometry(
    obj: bpy.types.Object,
) -> tuple[list[Vector], list[tuple[int, ...]]]:
    vertices = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    faces = [tuple(polygon.vertices) for polygon in obj.data.polygons]
    return vertices, faces


def world_bvh(obj: bpy.types.Object) -> BVHTree:
    vertices, faces = world_geometry(obj)
    return BVHTree.FromPolygons(vertices, faces, all_triangles=False)


def closest_surface_pair(
    first: bpy.types.Object,
    second: bpy.types.Object,
) -> tuple[Vector, Vector, float]:
    first_vertices, _faces = world_geometry(first)
    second_vertices, _faces = world_geometry(second)
    first_bvh = world_bvh(first)
    second_bvh = world_bvh(second)
    best_first = first_vertices[0]
    best_second = second_vertices[0]
    best_distance = float("inf")
    for point in first_vertices:
        nearest = second_bvh.find_nearest(point)
        if nearest is not None and nearest[3] < best_distance:
            best_first = point
            best_second = nearest[0]
            best_distance = nearest[3]
    for point in second_vertices:
        nearest = first_bvh.find_nearest(point)
        if nearest is not None and nearest[3] < best_distance:
            best_first = nearest[0]
            best_second = point
            best_distance = nearest[3]
    return best_first.copy(), best_second.copy(), float(best_distance)


def surfaces_overlap(first: bpy.types.Object, second: bpy.types.Object) -> bool:
    return bool(world_bvh(first).overlap(world_bvh(second)))


def surface_distance(first: bpy.types.Object, second: bpy.types.Object) -> float:
    return closest_surface_pair(first, second)[2]


def move_to_collection(
    obj: bpy.types.Object,
    collection: bpy.types.Collection,
) -> None:
    for source_collection in list(obj.users_collection):
        source_collection.objects.unlink(obj)
    collection.objects.link(obj)


def create_tie_rail(
    tie_id: str,
    first: bpy.types.Object,
    second: bpy.types.Object,
    values: dict[str, Any],
    collection: bpy.types.Collection,
    material: bpy.types.Material,
    side: str,
) -> tuple[bpy.types.Object, dict[str, Any]]:
    first_point, second_point, gap = closest_surface_pair(first, second)
    if gap <= 0.1:
        raise ValueError(
            f"Requested tie {tie_id} has no verified gap: {first.name}, {second.name}"
        )
    tangent = (second_point - first_point).normalized()
    overlap = float(values["endpoint_overlap_mm"])
    width, height = (float(value) for value in values["cross_section_mm"])
    length = gap + 2.0 * overlap
    center = first_point.lerp(second_point, 0.5)
    reference = Vector((0.0, 0.0, 1.0))
    if abs(tangent.dot(reference)) > 0.92:
        reference = Vector((0.0, 1.0, 0.0))
    width_axis = tangent.cross(reference).normalized()
    height_axis = tangent.cross(width_axis).normalized()
    name = f"A1_PROPOSED__{side}_tie_{tie_id}"
    rail = gate5.box(
        name,
        center,
        (tangent, width_axis, height_axis),
        (length, width, height),
        material,
    )
    move_to_collection(rail, collection)
    rail["review_only"] = True
    rail["requested_tie_id"] = tie_id
    rail["source_attachment_objects"] = json.dumps([first.name, second.name])
    rail["source_surface_gap_mm"] = gap
    rail["endpoint_overlap_mm"] = overlap
    boundary, nonmanifold = gate5.topology_counts(rail)
    return rail, {
        "id": tie_id,
        "left_attachment_objects": [first.name, second.name],
        "left_surface_attachment_points_mm": [list(first_point), list(second_point)],
        "source_surface_gap_mm": gap,
        "endpoint_overlap_mm": overlap,
        "rail_dimensions_mm": [length, width, height],
        "left_review_object": rail.name,
        "left_boundary_edges": boundary,
        "left_nonmanifold_edges": nonmanifold,
        "left_attachment_surface_overlap": {
            first.name: surfaces_overlap(rail, first),
            second.name: surfaces_overlap(rail, second),
        },
    }


def mirrored_copy(
    source: bpy.types.Object,
    name: str,
    collection: bpy.types.Collection,
    material: bpy.types.Material,
) -> bpy.types.Object:
    source_vertices, source_faces = world_geometry(source)
    vertices = [(-point.x, point.y, point.z) for point in source_vertices]
    faces = [tuple(reversed(face)) for face in source_faces]
    mesh = bpy.data.meshes.new(f"{name}_mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update(calc_edges=True)
    mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj["review_only"] = True
    obj["exact_x_mirror_of"] = source.name
    return obj


def mirrored_vertex_tokens(
    obj: bpy.types.Object,
    mirror_x: bool,
) -> list[tuple[float, float, float]]:
    output = []
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        if mirror_x:
            point.x = -point.x
        output.append(tuple(round(axis, 5) for axis in point))
    return sorted(output)


def attachment_audit(
    rail: bpy.types.Object,
    targets: list[bpy.types.Object],
) -> dict[str, Any]:
    return {
        target.name: {
            "surface_overlap": surfaces_overlap(rail, target),
            "minimum_surface_distance_mm": round(surface_distance(rail, target), 5),
        }
        for target in targets
    }


def point_at(obj: bpy.types.Object, target: Vector) -> None:
    obj.rotation_euler = (target - obj.location).to_track_quat("-Z", "Y").to_euler()


def configure_scene(output_dir: Path, resolution_px: int) -> bpy.types.Object:
    scene = bpy.context.scene
    scene.name = "Requested_Reinforcement_Additions_Review_V1"
    scene.render.engine = "BLENDER_WORKBENCH"
    shading = scene.display.shading
    shading.light = "STUDIO"
    shading.color_type = "OBJECT"
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
    camera_data = bpy.data.cameras.new("A1_REVIEW_ONLY__Camera")
    camera = bpy.data.objects.new("A1_REVIEW_ONLY__Camera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera.data.lens = 54.0
    (output_dir / "renders").mkdir(parents=True, exist_ok=True)
    return camera


def render_views(
    camera: bpy.types.Object,
    output_dir: Path,
    prefix: str,
    visible: set[bpy.types.Object],
) -> list[str]:
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_render = obj not in visible
    target = Vector((0.0, 115.0, 70.0))
    views = (
        ("rear", Vector((0.0, 560.0, 205.0))),
        ("rear-left", Vector((-390.0, 490.0, 230.0))),
        ("rear-right", Vector((390.0, 490.0, 230.0))),
        ("front", Vector((0.0, -490.0, 190.0))),
        ("left", Vector((-510.0, 120.0, 190.0))),
        ("right", Vector((510.0, 120.0, 190.0))),
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
    source_blend = repo_path(config["source_horizontal_review_blend"])
    if Path(bpy.data.filepath).resolve() != source_blend:
        raise ValueError(f"Open the configured H1 blend before running: {source_blend}")
    interface = json.loads(
        repo_path(config["shared_interface_path"]).read_text(encoding="utf-8")
    )
    if interface["interface_revision"] != config["required_interface_revision"]:
        raise ValueError("Shared shell/aluminum interface revision changed")
    output_dir.mkdir(parents=True, exist_ok=True)

    protected_meshes_before = {
        obj.name: v5.mesh_fingerprint(obj)
        for obj in bpy.data.objects
        if obj.type == "MESH"
    }
    protected_boundaries_before = {
        obj.name: horizontal_v1.curve_fingerprint(obj)
        for obj in bpy.data.objects
        if obj.name.startswith("V5_BOUNDARY__")
    }

    tie_collection = bpy.data.collections.new("A1_PROPOSED_REQUESTED_TIE_RAILS")
    mirror_collection = bpy.data.collections.new("A1_PROPOSED_C056_RIGHT_MIRROR")
    reference_collection = bpy.data.collections.new(
        "A1_UNCHANGED_REINFORCEMENT_REFERENCE"
    )
    boundary_collection = bpy.data.collections.new("A1_APPROVED_V5_BOUNDARY_REFERENCE")
    rejected_collection = bpy.data.collections.new("A1_REJECTED_SOURCE_REFERENCE")
    for collection in (
        tie_collection,
        mirror_collection,
        reference_collection,
        boundary_collection,
        rejected_collection,
    ):
        bpy.context.scene.collection.children.link(collection)

    tie_material = gate5.material(
        "A1__Requested_Tie_Rails_Cyan",
        hex_color(config["review_display"]["new_tie_color"]),
    )
    mirror_material = gate5.material(
        "A1__Requested_C056_Mirror_Purple",
        hex_color(config["review_display"]["new_mirror_color"]),
    )

    mirror_source_name = config["requested_mirror"]["source_object"]
    mirror_source = bpy.data.objects.get(mirror_source_name)
    if mirror_source is None:
        raise ValueError(f"Missing requested mirror source {mirror_source_name}")
    mirror_object = mirrored_copy(
        mirror_source,
        config["requested_mirror"]["output_object"],
        mirror_collection,
        mirror_material,
    )
    mirror_object.color = hex_color(config["review_display"]["new_mirror_color"])
    mirror_matches = mirrored_vertex_tokens(
        mirror_source, mirror_x=True
    ) == mirrored_vertex_tokens(mirror_object, mirror_x=False)
    mirror_boundary, mirror_nonmanifold = gate5.topology_counts(mirror_object)
    if not mirror_matches or mirror_boundary or mirror_nonmanifold:
        raise ValueError("The proposed C056 right mirror is not an exact closed mirror")
    existing_exact_mirror = any(
        obj.type == "MESH"
        and obj.name.startswith("R1_")
        and "__R__" in obj.name
        and mirrored_vertex_tokens(obj, mirror_x=False)
        == mirrored_vertex_tokens(mirror_source, mirror_x=True)
        for obj in bpy.data.objects
    )
    if existing_exact_mirror:
        raise ValueError("An exact right-side C056 mirror already exists")

    tie_objects = []
    tie_records = []
    for tie_config in config["requested_ties"]:
        left_targets = [bpy.data.objects.get(name) for name in tie_config["left_objects"]]
        if any(obj is None for obj in left_targets):
            raise ValueError(f"Missing left tie target for {tie_config['id']}")
        left_rail, record = create_tie_rail(
            tie_config["id"],
            left_targets[0],
            left_targets[1],
            config["tie_rail"],
            tie_collection,
            tie_material,
            "left",
        )
        left_rail.color = hex_color(config["review_display"]["new_tie_color"])
        right_targets = [
            mirror_object
            if name == mirror_object.name
            else bpy.data.objects.get(name)
            for name in tie_config["right_attachment_objects"]
        ]
        if any(obj is None for obj in right_targets):
            raise ValueError(f"Missing right tie target for {tie_config['id']}")
        right_fit_policy = tie_config["right_fit_policy"]
        right_fit_record = None
        if right_fit_policy == "exact_x_mirror":
            right_name = f"A1_PROPOSED__right_tie_{tie_config['id']}"
            right_rail = mirrored_copy(
                left_rail, right_name, tie_collection, tie_material
            )
        elif right_fit_policy == "independent_closest_surface":
            right_rail, right_fit_record = create_tie_rail(
                tie_config["id"],
                right_targets[0],
                right_targets[1],
                config["tie_rail"],
                tie_collection,
                tie_material,
                "right",
            )
        else:
            raise ValueError(
                f"Unsupported right fit policy for {tie_config['id']}: "
                f"{right_fit_policy}"
            )
        right_rail.color = hex_color(config["review_display"]["new_tie_color"])
        right_rail["requested_tie_id"] = tie_config["id"]
        right_rail["right_attachment_objects"] = json.dumps(
            tie_config["right_attachment_objects"]
        )
        right_boundary, right_nonmanifold = gate5.topology_counts(right_rail)
        exact_mirror = mirrored_vertex_tokens(
            left_rail, mirror_x=True
        ) == mirrored_vertex_tokens(right_rail, mirror_x=False)
        right_audit = attachment_audit(right_rail, right_targets)
        if right_boundary or right_nonmanifold:
            raise ValueError(f"Right tie {tie_config['id']} is not closed and manifold")
        if right_fit_policy == "exact_x_mirror" and not exact_mirror:
            raise ValueError(f"Right tie {tie_config['id']} is not an exact X mirror")
        if not all(
            values["surface_overlap"]
            or values["minimum_surface_distance_mm"] <= 0.25
            for values in right_audit.values()
        ):
            raise ValueError(
                f"Mirrored tie {tie_config['id']} does not attach to right targets: "
                f"{right_audit}"
            )
        record["right_attachment_objects"] = [obj.name for obj in right_targets]
        record["right_fit_policy"] = right_fit_policy
        record["right_fit_reason"] = tie_config.get("right_fit_reason")
        record["right_review_object"] = right_rail.name
        record["right_attachment_audit"] = right_audit
        record["right_surface_attachment_points_mm"] = (
            right_fit_record["left_surface_attachment_points_mm"]
            if right_fit_record
            else [
                [-point[0], point[1], point[2]]
                for point in record["left_surface_attachment_points_mm"]
            ]
        )
        record["right_source_surface_gap_mm"] = (
            right_fit_record["source_surface_gap_mm"]
            if right_fit_record
            else record["source_surface_gap_mm"]
        )
        record["right_rail_dimensions_mm"] = (
            right_fit_record["rail_dimensions_mm"]
            if right_fit_record
            else record["rail_dimensions_mm"]
        )
        record["right_boundary_edges"] = right_boundary
        record["right_nonmanifold_edges"] = right_nonmanifold
        record["exact_x_mirror"] = exact_mirror
        tie_objects.extend((left_rail, right_rail))
        tie_records.append(record)

    if any(
        not all(record["left_attachment_surface_overlap"].values())
        for record in tie_records
    ):
        raise ValueError(f"A left requested tie does not overlap both sources: {tie_records}")

    approved_horizontal_objects = []
    for name in config["approved_horizontal_rail_objects"]:
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise ValueError(f"Missing approved H1 rail {name}")
        obj.color = hex_color(
            config["review_display"]["approved_horizontal_rail_color"]
        )
        reference_collection.objects.link(obj)
        approved_horizontal_objects.append(obj)

    rejected_objects = []
    for name in config["rejected_source_objects"]:
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise ValueError(f"Missing rejected source reference {name}")
        rejected_collection.objects.link(obj)
        obj.hide_viewport = True
        obj.hide_render = True
        rejected_objects.append(obj)

    integrated_collection_name = "R1_INTEGRATED_SHELL_PLUS_REINFORCEMENT"
    unchanged_objects = []
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.name.startswith("R1_"):
            continue
        if obj in rejected_objects:
            continue
        if any(collection.name == integrated_collection_name for collection in obj.users_collection):
            continue
        reference_collection.objects.link(obj)
        obj.color = hex_color(
            config["review_display"]["unchanged_reinforcement_color"]
        )
        unchanged_objects.append(obj)

    seam_objects = []
    for name in ("V5_BOUNDARY__left_lower_face", "V5_BOUNDARY__right_lower_face"):
        obj = bpy.data.objects.get(name)
        if obj is None:
            raise ValueError(f"Missing approved V5 boundary {name}")
        boundary_collection.objects.link(obj)
        obj.color = hex_color(config["review_display"]["boundary_color"])
        obj.show_in_front = True
        seam_objects.append(obj)

    context_shells = {
        obj
        for obj in bpy.data.objects
        if obj.type == "MESH"
        and (
            obj.name.startswith("V5_RETAINED__")
            or obj.name.startswith("V5_CASSETTE__moved_from_")
        )
    }
    for obj in context_shells:
        obj.display_type = "WIRE"
        obj.show_in_front = True

    new_objects = set(tie_objects) | {mirror_object}
    reference_objects = set(unchanged_objects) | set(approved_horizontal_objects)
    seam_set = set(seam_objects)
    default_visible = new_objects | reference_objects | seam_set | context_shells
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in default_visible
            obj.hide_render = True

    camera = configure_scene(
        output_dir, int(config["review_display"]["render_resolution_px"])
    )
    render_paths = render_views(
        camera,
        output_dir,
        "requested-additions-with-existing-frame",
        new_objects | reference_objects | seam_set,
    )
    render_paths.extend(
        render_views(
            camera,
            output_dir,
            "requested-additions-isolated",
            new_objects | set(approved_horizontal_objects) | seam_set,
        )
    )
    for obj in bpy.data.objects:
        if obj.type not in {"CAMERA", "LIGHT"}:
            obj.hide_viewport = obj not in default_visible
            obj.hide_render = obj not in (new_objects | reference_objects | seam_set)
    camera.location = Vector((0.0, 560.0, 205.0))
    point_at(camera, Vector((0.0, 115.0, 70.0)))

    protected_meshes_after = {
        name: v5.mesh_fingerprint(bpy.data.objects[name])
        for name in protected_meshes_before
    }
    protected_boundaries_after = {
        name: horizontal_v1.curve_fingerprint(bpy.data.objects[name])
        for name in protected_boundaries_before
    }
    if protected_meshes_before != protected_meshes_after:
        raise ValueError("A pre-existing source/review mesh changed")
    if protected_boundaries_before != protected_boundaries_after:
        raise ValueError("An approved V5 boundary changed")

    mirror_overlap_objects = sorted(
        obj.name
        for obj in unchanged_objects
        if "__R__" in obj.name and surfaces_overlap(mirror_object, obj)
    )
    scene = bpy.context.scene
    scene["review_status"] = config["status"]
    scene["new_geometry_count"] = len(new_objects)
    scene["source_geometry_unchanged"] = True
    blend_path = output_dir / "requested-reinforcement-additions-review-v1.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    report = {
        "status": config["status"],
        "source_horizontal_review_blend": str(source_blend.relative_to(REPO_ROOT)),
        "config": str(config_path.relative_to(REPO_ROOT)),
        "interface_revision": interface["interface_revision"],
        "tie_rail_rule": config["tie_rail"],
        "new_tie_rail_count": len(tie_objects),
        "new_mirrored_rib_count": 1,
        "new_geometry_count": len(new_objects),
        "tie_records": tie_records,
        "requested_mirror": {
            "source_object": mirror_source.name,
            "review_object": mirror_object.name,
            "exact_x_mirror": mirror_matches,
            "boundary_edges": mirror_boundary,
            "nonmanifold_edges": mirror_nonmanifold,
            "existing_exact_mirror_before_review": existing_exact_mirror,
            "overlapping_right_reference_objects": mirror_overlap_objects,
        },
        "all_new_geometry_closed_and_manifold": all(
            not gate5.topology_counts(obj)[0] and not gate5.topology_counts(obj)[1]
            for obj in new_objects
        ),
        "exact_mirrored_tie_pair_count": sum(
            record["right_fit_policy"] == "exact_x_mirror"
            for record in tie_records
        ),
        "independently_surface_fitted_right_tie_count": sum(
            record["right_fit_policy"] == "independent_closest_surface"
            for record in tie_records
        ),
        "all_exact_mirror_policy_ties_are_exact_x_mirrors": all(
            record["exact_x_mirror"]
            for record in tie_records
            if record["right_fit_policy"] == "exact_x_mirror"
        ),
        "all_left_ties_overlap_both_named_sources": all(
            all(record["left_attachment_surface_overlap"].values())
            for record in tie_records
        ),
        "all_right_ties_attach_to_named_targets": all(
            all(
                values["surface_overlap"]
                or values["minimum_surface_distance_mm"] <= 0.25
                for values in record["right_attachment_audit"].values()
            )
            for record in tie_records
        ),
        "approved_horizontal_rail_objects_unchanged": config[
            "approved_horizontal_rail_objects"
        ],
        "rejected_source_objects_preserved_but_hidden": all(
            obj.hide_viewport and obj.hide_render for obj in rejected_objects
        ),
        "protected_preexisting_mesh_count": len(protected_meshes_before),
        "protected_preexisting_mesh_geometry_unchanged": protected_meshes_before
        == protected_meshes_after,
        "approved_v5_boundary_geometry_unchanged": protected_boundaries_before
        == protected_boundaries_after,
        "generated_files": {
            "blend": str(blend_path.relative_to(REPO_ROOT)),
            "renders": render_paths,
        },
        "no_stl_or_gcode_exported": True,
        "review_holds": config["review_holds"],
    }
    report_path = output_dir / (
        "requested-reinforcement-additions-review-v1-validation.json"
    )
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "new_tie_rail_count": report["new_tie_rail_count"],
                "new_mirrored_rib_count": report["new_mirrored_rib_count"],
                "tie_gap_and_length_mm": {
                    record["id"]: {
                        "surface_gap": round(record["source_surface_gap_mm"], 3),
                        "rail_length": round(record["rail_dimensions_mm"][0], 3),
                    }
                    for record in tie_records
                },
                "all_new_geometry_closed_and_manifold": report[
                    "all_new_geometry_closed_and_manifold"
                ],
                "exact_mirrored_tie_pair_count": report[
                    "exact_mirrored_tie_pair_count"
                ],
                "independently_surface_fitted_right_tie_count": report[
                    "independently_surface_fitted_right_tie_count"
                ],
                "all_exact_mirror_policy_ties_are_exact_x_mirrors": report[
                    "all_exact_mirror_policy_ties_are_exact_x_mirrors"
                ],
                "all_left_ties_overlap_both_named_sources": report[
                    "all_left_ties_overlap_both_named_sources"
                ],
                "all_right_ties_attach_to_named_targets": report[
                    "all_right_ties_attach_to_named_targets"
                ],
                "protected_preexisting_mesh_geometry_unchanged": report[
                    "protected_preexisting_mesh_geometry_unchanged"
                ],
                "approved_v5_boundary_geometry_unchanged": report[
                    "approved_v5_boundary_geometry_unchanged"
                ],
                "blend": report["generated_files"]["blend"],
                "report": str(report_path.relative_to(REPO_ROOT)),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
