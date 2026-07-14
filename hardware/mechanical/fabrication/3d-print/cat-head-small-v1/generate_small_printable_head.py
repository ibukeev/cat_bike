#!/usr/bin/env python3
"""Generate the 100 mm phase-1 printable cat-head shell in Blender."""

from __future__ import annotations

import json
import math
import struct
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector


WORKDIR = Path(__file__).resolve().parent
REPO_ROOT = WORKDIR.parents[4]
INPUT_OBJ = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/templates/cat-head-cardboard-fabrication-v1"
    / "assembly/accepted-panels-3d.obj"
)
APPROVED_PACKAGE = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/templates/cat-head-wireframe-prototype"
    / "versions/v1-shape-approved-cardboard-prototype"
)
OUT_DIR = WORKDIR / "output"

TARGET_HEIGHT_MM = 100.0
WALL_THICKNESS_MM = 1.2
REAR_OPENING_INSET_MM = 7.0
MK4S_BUILD_VOLUME_MM = (250.0, 210.0, 220.0)


def reset_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for datablock in list(datablocks):
            datablocks.remove(datablock)


def load_obj_surface(path: Path) -> bpy.types.Object:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("v "):
            _, x, y, z = line.split()[:4]
            vertices.append((float(x), float(y), float(z)))
        elif line.startswith("f "):
            face = tuple(int(token.split("/")[0]) - 1 for token in line.split()[1:])
            if len(face) >= 3:
                faces.append(face)
    if not vertices or not faces:
        raise ValueError(f"No printable surface found in {path}")

    mesh = bpy.data.meshes.new("CatHeadApprovedSurface")
    mesh.from_pydata(vertices, [], faces)
    mesh.validate(verbose=True)
    mesh.update()
    obj = bpy.data.objects.new("CatHead_Phase1_100mm_Shell", mesh)
    bpy.context.collection.objects.link(obj)
    return obj


def close_source_openings(obj: bpy.types.Object) -> tuple[int, int]:
    """Fill accidental shell gaps while keeping the two intended ear openings."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary = [edge for edge in bm.edges if len(edge.link_faces) == 1]
    boundary_count = len(boundary)
    if not boundary:
        bm.free()
        return 0, 0

    remaining = set(boundary)
    boundary_components: list[list[bmesh.types.BMEdge]] = []
    while remaining:
        seed = remaining.pop()
        component = [seed]
        stack = [seed]
        while stack:
            edge = stack.pop()
            for vertex in edge.verts:
                for linked in vertex.link_edges:
                    if linked in remaining and len(linked.link_faces) == 1:
                        remaining.remove(linked)
                        component.append(linked)
                        stack.append(linked)
        boundary_components.append(component)

    ear_edges: set[bmesh.types.BMEdge] = set()
    ear_loops = 0
    for component in boundary_components:
        vertices = {vertex for edge in component for vertex in edge.verts}
        center = sum((vertex.co for vertex in vertices), Vector()) / len(vertices)
        # These are the symmetric high/outboard loops visible as inner ear voids
        # in the approved front view. Their rims become part of the printed shell.
        if abs(center.x) > 60.0 and center.z > 30.0:
            ear_edges.update(component)
            ear_loops += 1

    if ear_loops != 2:
        raise ValueError(f"Expected two inner-ear opening loops, found {ear_loops}")

    bmesh.ops.holes_fill(bm, edges=[edge for edge in boundary if edge not in ear_edges], sides=0)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    return boundary_count, ear_loops


def scale_to_height(obj: bpy.types.Object, height_mm: float) -> float:
    coords = [vertex.co.copy() for vertex in obj.data.vertices]
    min_z = min(co.z for co in coords)
    max_z = max(co.z for co in coords)
    source_height = max_z - min_z
    if source_height <= 0:
        raise ValueError("Source model has zero height")
    scale = height_mm / source_height
    center_x = (min(co.x for co in coords) + max(co.x for co in coords)) / 2.0
    center_z = (min_z + max_z) / 2.0
    for vertex in obj.data.vertices:
        vertex.co.x = (vertex.co.x - center_x) * scale
        vertex.co.y *= scale
        vertex.co.z = (vertex.co.z - center_z) * scale
    obj.data.update()
    return scale


def cut_flat_rear_opening(obj: bpy.types.Object, inset_mm: float) -> float:
    max_y = max(vertex.co.y for vertex in obj.data.vertices)
    cut_y = max_y - inset_mm
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    geometry = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(
        bm,
        geom=geometry,
        dist=0.0001,
        plane_co=(0.0, cut_y, 0.0),
        plane_no=(0.0, 1.0, 0.0),
        clear_outer=True,
        clear_inner=False,
    )
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    boundary_count = sum(1 for edge in obj.data.edges if edge.is_loose)
    if not obj.data.polygons:
        raise ValueError("Rear cut removed the complete model")
    return cut_y


def solidify_shell(obj: bpy.types.Object, thickness_mm: float) -> None:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    modifier = obj.modifiers.new(name="PrintableWall", type="SOLIDIFY")
    modifier.thickness = thickness_mm
    modifier.offset = -1.0
    modifier.use_even_offset = True
    modifier.use_quality_normals = True
    bpy.ops.object.modifier_apply(modifier=modifier.name)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.0001)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=0.0001)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.validate(verbose=True)
    obj.data.update()


def orient_rear_down(obj: bpy.types.Object, cut_y: float) -> None:
    # Original X remains printer X, original Z becomes printer Y, and the
    # rear cut plane becomes printer Z=0.
    for vertex in obj.data.vertices:
        x, y, z = vertex.co
        vertex.co = (x, z, cut_y - y)

    min_x = min(vertex.co.x for vertex in obj.data.vertices)
    max_x = max(vertex.co.x for vertex in obj.data.vertices)
    min_y = min(vertex.co.y for vertex in obj.data.vertices)
    max_y = max(vertex.co.y for vertex in obj.data.vertices)
    min_z = min(vertex.co.z for vertex in obj.data.vertices)
    for vertex in obj.data.vertices:
        vertex.co.x -= (min_x + max_x) / 2.0
        vertex.co.y -= (min_y + max_y) / 2.0
        vertex.co.z -= min_z
    obj.data.update()


def mesh_dimensions(obj: bpy.types.Object) -> tuple[float, float, float]:
    xs = [vertex.co.x for vertex in obj.data.vertices]
    ys = [vertex.co.y for vertex in obj.data.vertices]
    zs = [vertex.co.z for vertex in obj.data.vertices]
    return max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)


def validate_mesh(obj: bpy.types.Object) -> dict[str, float | int | bool | list[float]]:
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    nonmanifold_edges = [edge for edge in bm.edges if len(edge.link_faces) != 2]
    degenerate_faces = [face for face in bm.faces if face.calc_area() < 1e-8]

    components = 0
    unseen = set(bm.faces)
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

    volume = abs(bm.calc_volume(signed=True))
    dimensions = mesh_dimensions(obj)
    report = {
        "vertices": len(bm.verts),
        "triangles": len(bm.faces),
        "edges": len(bm.edges),
        "nonmanifold_edges": len(nonmanifold_edges),
        "degenerate_faces": len(degenerate_faces),
        "connected_components": components,
        "volume_mm3": round(volume, 3),
        "dimensions_mm": [round(value, 3) for value in dimensions],
        "fits_mk4s": all(dim <= limit for dim, limit in zip(dimensions, MK4S_BUILD_VOLUME_MM)),
    }
    bm.free()

    if report["nonmanifold_edges"] != 0:
        raise ValueError(f"Printable shell has {report['nonmanifold_edges']} nonmanifold edges")
    if report["degenerate_faces"] != 0:
        raise ValueError(f"Printable shell has {report['degenerate_faces']} degenerate faces")
    if report["connected_components"] != 1:
        raise ValueError(f"Printable shell has {report['connected_components']} components")
    if not report["fits_mk4s"]:
        raise ValueError(f"Printable shell exceeds MK4S volume: {report['dimensions_mm']}")
    if volume <= 0:
        raise ValueError("Printable shell has zero volume")
    return report


def write_binary_stl(obj: bpy.types.Object, path: Path) -> None:
    mesh = obj.data
    mesh.calc_loop_triangles()
    triangles = mesh.loop_triangles
    header = b"Cat head phase-1 100 mm shell"[:80].ljust(80, b" ")
    with path.open("wb") as handle:
        handle.write(header)
        handle.write(struct.pack("<I", len(triangles)))
        for triangle in triangles:
            coords = [mesh.vertices[index].co for index in triangle.vertices]
            normal = (coords[1] - coords[0]).cross(coords[2] - coords[0]).normalized()
            values = (
                normal.x,
                normal.y,
                normal.z,
                coords[0].x,
                coords[0].y,
                coords[0].z,
                coords[1].x,
                coords[1].y,
                coords[1].z,
                coords[2].x,
                coords[2].y,
                coords[2].z,
            )
            handle.write(struct.pack("<12fH", *values, 0))


def write_obj(obj: bpy.types.Object, path: Path) -> None:
    lines = [
        "# Phase-1 100 mm printable cat-head shell",
        "# Print orientation: flat rear opening on Z=0",
        f"o {obj.name}",
    ]
    lines.extend(f"v {v.co.x:.6f} {v.co.y:.6f} {v.co.z:.6f}" for v in obj.data.vertices)
    for polygon in obj.data.polygons:
        lines.append("f " + " ".join(str(index + 1) for index in polygon.vertices))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def add_render_setup(obj: bpy.types.Object) -> None:
    material = bpy.data.materials.new("WarmGreyPLA")
    material.diffuse_color = (0.62, 0.68, 0.73, 1.0)
    material.roughness = 0.72
    obj.data.materials.append(material)
    for polygon in obj.data.polygons:
        polygon.use_smooth = False

    bpy.ops.mesh.primitive_plane_add(size=360, location=(0, 0, -0.25))
    plane = bpy.context.object
    plane.name = "BuildPlate"
    plate_material = bpy.data.materials.new("BuildPlateMaterial")
    plate_material.diffuse_color = (0.18, 0.20, 0.22, 1.0)
    plate_material.roughness = 0.88
    plane.data.materials.append(plate_material)

    camera_data = bpy.data.cameras.new("Camera")
    camera = bpy.data.objects.new("Camera", camera_data)
    bpy.context.collection.objects.link(camera)
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "MATERIAL"
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.show_object_outline = True
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.92, 0.93, 0.94)
    scene.render.resolution_x = 1100
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"


def aim_camera(camera: bpy.types.Object, location: tuple[float, float, float], target: Vector) -> None:
    camera.location = location
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_previews(obj: bpy.types.Object) -> None:
    add_render_setup(obj)
    camera = bpy.context.scene.camera
    plate = bpy.data.objects.get("BuildPlate")
    dimensions = mesh_dimensions(obj)
    target = Vector((0.0, 0.0, dimensions[2] * 0.43))

    camera.data.type = "PERSP"
    camera.data.lens = 58
    aim_camera(camera, (180.0, -190.0, 175.0), target)
    bpy.context.scene.render.filepath = str(OUT_DIR / "cat-head-100mm-shell-print-orientation.png")
    bpy.ops.render.render(write_still=True)

    # The front is the highest-Z side in print orientation.
    if plate is not None:
        plate.hide_render = True
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 135.0
    aim_camera(camera, (0.0, 0.0, dimensions[2] + 200.0), Vector((0.0, 0.0, dimensions[2] * 0.50)))
    bpy.context.scene.render.filepath = str(OUT_DIR / "cat-head-100mm-shell-front.png")
    bpy.ops.render.render(write_still=True)


def main() -> None:
    if not INPUT_OBJ.exists():
        raise FileNotFoundError(f"Generate the accepted panel mesh first: {INPUT_OBJ}")
    if not APPROVED_PACKAGE.exists():
        raise FileNotFoundError(f"Approved V1 package is missing: {APPROVED_PACKAGE}")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    reset_scene()
    obj = load_obj_surface(INPUT_OBJ)
    source_boundary_edges, preserved_ear_openings = close_source_openings(obj)
    source_scale = scale_to_height(obj, TARGET_HEIGHT_MM)
    cut_y = cut_flat_rear_opening(obj, REAR_OPENING_INSET_MM)
    solidify_shell(obj, WALL_THICKNESS_MM)
    orient_rear_down(obj, cut_y)
    report = validate_mesh(obj)
    report.update(
        {
            "target_concept_height_mm": TARGET_HEIGHT_MM,
            "wall_thickness_mm": WALL_THICKNESS_MM,
            "rear_opening_inset_mm": REAR_OPENING_INSET_MM,
            "source_scale": round(source_scale, 8),
            "source_boundary_edges_closed": source_boundary_edges,
            "preserved_inner_ear_openings": preserved_ear_openings,
            "source_obj": str(INPUT_OBJ.relative_to(REPO_ROOT)),
            "approved_package": str(APPROVED_PACKAGE.relative_to(REPO_ROOT)),
            "print_orientation": "flat rear opening on printer Z=0",
            "mk4s_build_volume_mm": list(MK4S_BUILD_VOLUME_MM),
        }
    )

    stl_path = OUT_DIR / "cat-head-100mm-shell-mk4s.stl"
    obj_path = OUT_DIR / "cat-head-100mm-shell-mk4s.obj"
    write_binary_stl(obj, stl_path)
    write_obj(obj, obj_path)
    (OUT_DIR / "validation-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    render_previews(obj)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT_DIR / "cat-head-100mm-shell-mk4s.blend"))

    print(json.dumps(report, indent=2))
    print(f"Wrote {stl_path}")
    print(f"Wrote {obj_path}")


if __name__ == "__main__":
    main()
