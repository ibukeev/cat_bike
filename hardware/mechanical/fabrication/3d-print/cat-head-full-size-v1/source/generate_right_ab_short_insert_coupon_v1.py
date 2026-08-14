#!/usr/bin/env python3
"""Build the exact-orientation right A/B short-insert coupon plate."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


SCRIPT_DIR = Path(__file__).resolve().parent
PACKAGE_ROOT = SCRIPT_DIR.parent
REPO_ROOT = PACKAGE_ROOT.parents[4]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    return parser.parse_args(argv)


def repo_path(value: str) -> Path:
    return (REPO_ROOT / value).resolve()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def material(name: str, rgba: tuple[float, float, float, float], roughness: float = 0.45):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = rgba
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def import_stl(path: Path, name: str, mat) -> bpy.types.Object:
    bpy.ops.wm.stl_import(filepath=str(path))
    selected = list(bpy.context.selected_objects)
    if len(selected) != 1:
        raise RuntimeError(f"Expected one imported object from {path}, got {len(selected)}")
    obj = selected[0]
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def world_vertices(obj: bpy.types.Object) -> list[Vector]:
    return [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]


def bounds(obj: bpy.types.Object) -> dict[str, list[float]]:
    points = world_vertices(obj)
    return {
        "min_mm": [min(point[axis] for point in points) for axis in range(3)],
        "max_mm": [max(point[axis] for point in points) for axis in range(3)],
        "size_mm": [
            max(point[axis] for point in points) - min(point[axis] for point in points)
            for axis in range(3)
        ],
    }


def topology_and_volume(obj: bpy.types.Object) -> dict[str, float | int]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    try:
        boundary = sum(1 for edge in bm.edges if len(edge.link_faces) == 1)
        nonmanifold = sum(1 for edge in bm.edges if len(edge.link_faces) != 2)
        unseen = set(bm.faces)
        components = 0
        while unseen:
            components += 1
            stack = [unseen.pop()]
            while stack:
                face = stack.pop()
                for edge in face.edges:
                    for linked in edge.link_faces:
                        if linked in unseen:
                            unseen.remove(linked)
                            stack.append(linked)
        return {
            "vertices": len(bm.verts),
            "edges": len(bm.edges),
            "faces": len(bm.faces),
            "boundary_edges": boundary,
            "nonmanifold_edges": nonmanifold,
            "connected_components": components,
            "volume_mm3": abs(float(bm.calc_volume(signed=True))),
        }
    finally:
        bm.free()


def bed_contact_area(obj: bpy.types.Object, tolerance: float) -> float:
    obj.data.calc_loop_triangles()
    area = 0.0
    for polygon in obj.data.polygons:
        zs = [(obj.matrix_world @ obj.data.vertices[index].co).z for index in polygon.vertices]
        if max(zs) <= tolerance:
            area += float(polygon.area)
    return area


def place_with_orientation(
    obj: bpy.types.Object,
    quaternion: list[float],
    desired_x: float,
    desired_y: float,
) -> None:
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = quaternion
    bpy.context.view_layer.update()
    current = bounds(obj)
    center_x = (current["min_mm"][0] + current["max_mm"][0]) * 0.5
    center_y = (current["min_mm"][1] + current["max_mm"][1]) * 0.5
    obj.location.x += desired_x - center_x
    obj.location.y += desired_y - center_y
    obj.location.z += -current["min_mm"][2]
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def export_stl(obj: bpy.types.Object, destination: Path) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.wm.stl_export(
        filepath=str(destination),
        export_selected_objects=True,
        apply_modifiers=True,
        ascii_format=False,
    )


def add_box(name: str, location, scale, mat):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj


def look_at(camera, target) -> None:
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def render(scene, camera, path: Path, location, target) -> None:
    camera.location = location
    look_at(camera, target)
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def rounded(values):
    return [round(float(value), 4) for value in values]


def main() -> None:
    args = parse_args()
    config = json.loads(args.config.resolve().read_text(encoding="utf-8"))
    source = config["source"]
    contract = config["numeric_contract"]
    outputs = config["outputs"]
    output_dir = repo_path(outputs["output_dir"])
    review_dir = output_dir / "review"
    output_dir.mkdir(parents=True, exist_ok=True)
    review_dir.mkdir(parents=True, exist_ok=True)

    a_path = repo_path(source["a_source_stl"])
    b_path = repo_path(source["b_source_stl"])
    if sha256(a_path) != source["a_source_stl_sha256"]:
        raise RuntimeError("Right-A source STL hash mismatch")
    if sha256(b_path) != source["b_source_stl_sha256"]:
        raise RuntimeError("Right-B source STL hash mismatch")

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    a_mat = material("Approved Right A V4", (0.12, 0.46, 0.95, 1.0))
    b_mat = material("Approved Right B V2", (0.98, 0.43, 0.08, 1.0))
    bed_mat = material("Coupon Bed", (0.13, 0.15, 0.18, 1.0), roughness=0.75)
    a = import_stl(a_path, "COUPON__RIGHT_A__SURFACE_OPEN_V4", a_mat)
    b = import_stl(b_path, "COUPON__RIGHT_B__SURFACE_OPEN_V2", b_mat)

    quaternion = contract["selected_rotation_quaternion_wxyz"]
    a.rotation_mode = "QUATERNION"
    b.rotation_mode = "QUATERNION"
    a.rotation_quaternion = quaternion
    b.rotation_quaternion = quaternion
    bpy.context.view_layer.update()
    a_rotated = bounds(a)
    b_rotated = bounds(b)
    gap = float(contract["packing_gap_mm"])
    total_x = a_rotated["size_mm"][0] + gap + b_rotated["size_mm"][0]
    a_center_x = -total_x * 0.5 + a_rotated["size_mm"][0] * 0.5
    b_center_x = total_x * 0.5 - b_rotated["size_mm"][0] * 0.5
    place_with_orientation(a, quaternion, a_center_x, 0.0)
    place_with_orientation(b, quaternion, b_center_x, 0.0)

    a_bounds = bounds(a)
    b_bounds = bounds(b)
    a_topology = topology_and_volume(a)
    b_topology = topology_and_volume(b)
    for name, result in (("A", a_topology), ("B", b_topology)):
        if result["connected_components"] != 1:
            raise RuntimeError(f"{name} coupon is not one connected component: {result}")
        if result["boundary_edges"] != 0 or result["nonmanifold_edges"] != 0:
            raise RuntimeError(f"{name} coupon is not closed manifold: {result}")

    tolerance = float(contract["bed_contact_tolerance_mm"])
    a_contact = bed_contact_area(a, tolerance)
    b_contact = bed_contact_area(b, tolerance)
    all_points = world_vertices(a) + world_vertices(b)
    combined_min = [min(point[axis] for point in all_points) for axis in range(3)]
    combined_max = [max(point[axis] for point in all_points) for axis in range(3)]
    combined_size = [combined_max[i] - combined_min[i] for i in range(3)]
    envelope = contract["conservative_printer_envelope_mm"]
    reserve = contract["required_xy_reserve_each_side_mm"]
    xy_reserve = [(envelope[i] - combined_size[i]) * 0.5 for i in range(2)]
    if min(xy_reserve) < reserve:
        raise RuntimeError(f"Coupon reserve failed: {xy_reserve}")

    a_output = output_dir / outputs["a_stl"]
    b_output = output_dir / outputs["b_stl"]
    export_stl(a, a_output)
    export_stl(b, b_output)

    pad_x = combined_size[0] * 0.5 + 12.0
    pad_y = combined_size[1] * 0.5 + 12.0
    add_box("CONTEXT__COUPON_BED", (0, 0, -0.55), (pad_x, pad_y, 0.5), bed_mat)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 1000
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.view_settings.look = "AgX - Medium High Contrast"
    scene.view_settings.exposure = 1.2
    scene.world.use_nodes = True
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.11, 0.11, 0.13, 1.0)
    scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7
    bpy.ops.object.light_add(type="AREA", location=(70, -90, 110))
    bpy.context.object.data.energy = 1800
    bpy.context.object.data.size = 80
    bpy.ops.object.light_add(type="AREA", location=(-70, 60, 70))
    bpy.context.object.data.energy = 1200
    bpy.context.object.data.size = 60
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.lens = 58
    scene.camera = camera

    target = (0, 0, combined_size[2] * 0.35)
    distance = max(combined_size[0], combined_size[1]) * 2.2
    render(scene, camera, review_dir / "01-coupon-pair-isometric.png", (distance, -distance, distance * 0.85), target)
    render(scene, camera, review_dir / "02-coupon-pair-opposite.png", (-distance, distance, distance * 0.7), target)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(combined_size[0], combined_size[1]) + 24.0
    render(scene, camera, review_dir / "03-coupon-pair-top.png", (0, 0, distance * 2.0), (0, 0, 0))
    camera.data.ortho_scale = max(combined_size[0], combined_size[2]) + 20.0
    render(scene, camera, review_dir / "04-coupon-pair-side.png", (0, -distance * 2.0, combined_size[2] * 0.5), target)
    render(scene, camera, review_dir / "05-coupon-pair-underside.png", (0, distance * 1.6, -distance * 0.8), target)

    validation = {
        "review_id": config["review_id"],
        "status": "PASS",
        "geometry_change_mm": 0.0,
        "scale": 1.0,
        "rotation_quaternion_wxyz": quaternion,
        "packing_gap_mm": gap,
        "combined_oriented_xyz_mm": rounded(combined_size),
        "xy_reserve_each_side_mm": rounded(xy_reserve),
        "a": {
            "source_object": source["a_object"],
            "bounds": {key: rounded(value) for key, value in a_bounds.items()},
            "topology": a_topology,
            "bed_contact_area_within_tolerance_mm2": round(a_contact, 4),
            "stl": outputs["a_stl"],
            "stl_sha256": sha256(a_output),
        },
        "b": {
            "source_object": source["b_object"],
            "bounds": {key: rounded(value) for key, value in b_bounds.items()},
            "topology": b_topology,
            "bed_contact_area_within_tolerance_mm2": round(b_contact, 4),
            "stl": outputs["b_stl"],
            "stl_sha256": sha256(b_output),
        },
        "full_shell_export_created": False,
        "gcode_created": False,
        "physical_qualification_complete": False,
    }
    (output_dir / outputs["validation"]).write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(output_dir / outputs["blend"]))


if __name__ == "__main__":
    main()
