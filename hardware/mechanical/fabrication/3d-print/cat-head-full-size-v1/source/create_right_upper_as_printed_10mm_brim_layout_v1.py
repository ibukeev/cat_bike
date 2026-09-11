#!/usr/bin/env python3
"""Create the approved right-upper MK4 layout with a 10 mm outer brim."""

from __future__ import annotations

import argparse
import hashlib
import math
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile


SOURCE_PROJECT_SHA256 = "ac800ac7470c61cf4d640af6d652b25ac080142826aaadb4d24842bb9440720b"
SOURCE_STL_SHA256 = "6b7ced6a6cb86e5d7635f622f6e18df53bf616a378823443f98dd8aa1e4c2f4d"
MODEL_MEMBER = "3D/3dmodel.model"
PRINT_CONFIG_MEMBER = "Metadata/Slic3r_PE.config"
MODEL_CONFIG_MEMBER = "Metadata/Slic3r_PE_model.config"
CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
BED_SIZE_MM = (250.0, 210.0, 220.0)
BED_CENTER_MM = (BED_SIZE_MM[0] / 2.0, BED_SIZE_MM[1] / 2.0)
APPROVED_X_TILT_DEG = 22.0
APPROVED_Z_ROTATION_DEG = -9.0
APPROVED_BRIM_WIDTH_MM = 10.0
EXPECTED_SETTINGS = {
    "bed_shape": "0x0,250x0,250x210,0x210",
    "filament_type": "ASA",
    "layer_height": "0.2",
    "fill_density": "25%",
    "perimeters": "3",
    "printer_model": "MK4IS",
    "support_material": "1",
    "support_material_auto": "1",
    "support_material_style": "snug",
    "support_material_threshold": "40",
}


Matrix = tuple[tuple[float, float, float], ...]
Vector = tuple[float, float, float]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def multiply(left: Matrix, right: Matrix) -> Matrix:
    return tuple(
        tuple(
            sum(left[row][index] * right[index][column] for index in range(3))
            for column in range(3)
        )
        for row in range(3)
    )


def matrix_vector(matrix: Matrix, vector: Vector) -> Vector:
    return tuple(
        sum(matrix[row][index] * vector[index] for index in range(3))
        for row in range(3)
    )


def transform_point(matrix: Matrix, translation: Vector, point: Vector) -> Vector:
    rotated = matrix_vector(matrix, point)
    return tuple(rotated[index] + translation[index] for index in range(3))


def bounds(points: list[Vector]) -> tuple[Vector, Vector]:
    return (
        tuple(min(point[index] for point in points) for index in range(3)),
        tuple(max(point[index] for point in points) for index in range(3)),
    )


def parse_transform(values: list[float]) -> tuple[Matrix, Vector]:
    matrix = (
        (values[0], values[3], values[6]),
        (values[1], values[4], values[7]),
        (values[2], values[5], values[8]),
    )
    return matrix, (values[9], values[10], values[11])


def serialize_transform(matrix: Matrix, translation: Vector) -> str:
    values = (
        matrix[0][0],
        matrix[1][0],
        matrix[2][0],
        matrix[0][1],
        matrix[1][1],
        matrix[2][1],
        matrix[0][2],
        matrix[1][2],
        matrix[2][2],
        *translation,
    )
    return " ".join(f"{value:.12g}" for value in values)


def setting(config: bytes, key: str) -> str:
    match = re.search(rb"(?m)^; " + re.escape(key.encode()) + rb" = ([^\r\n]+)$", config)
    if match is None:
        raise RuntimeError(f"Missing required slicer setting: {key}")
    return match.group(1).decode("utf-8")


def replace_setting(config: bytes, key: str, value: str) -> bytes:
    pattern = rb"(?m)^; " + re.escape(key.encode()) + rb" = [^\r\n]+$"
    replacement = f"; {key} = {value}".encode("utf-8")
    updated, count = re.subn(pattern, replacement, config)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {key} setting, found {count}")
    return updated


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_project", type=Path)
    parser.add_argument("source_stl", type=Path)
    parser.add_argument("output_project", type=Path)
    args = parser.parse_args()

    source_project_hash = sha256(args.source_project)
    source_stl_hash = sha256(args.source_stl)
    if source_project_hash != SOURCE_PROJECT_SHA256:
        raise RuntimeError(
            f"Frozen source 3MF mismatch: expected {SOURCE_PROJECT_SHA256}, got {source_project_hash}"
        )
    if source_stl_hash != SOURCE_STL_SHA256:
        raise RuntimeError(
            f"Frozen source STL mismatch: expected {SOURCE_STL_SHA256}, got {source_stl_hash}"
        )
    if args.output_project.exists():
        raise RuntimeError(f"Refusing to overwrite existing output: {args.output_project}")

    with zipfile.ZipFile(args.source_project, "r") as source_zip:
        member_names = {info.filename for info in source_zip.infolist()}
        required_members = {MODEL_MEMBER, PRINT_CONFIG_MEMBER, MODEL_CONFIG_MEMBER}
        if not required_members.issubset(member_names):
            missing = sorted(required_members - member_names)
            raise RuntimeError(f"Source 3MF is missing members: {missing}")

        model_bytes = source_zip.read(MODEL_MEMBER)
        print_config = source_zip.read(PRINT_CONFIG_MEMBER)
        model_config = source_zip.read(MODEL_CONFIG_MEMBER)

        for key, expected in EXPECTED_SETTINGS.items():
            actual = setting(print_config, key)
            if actual != expected:
                raise RuntimeError(
                    f"Frozen slicer setting mismatch for {key}: expected {expected}, got {actual}"
                )
        if setting(print_config, "brim_type") != "inner_only":
            raise RuntimeError("Expected the frozen project to have brim_type=inner_only")
        if setting(print_config, "brim_width") != "0":
            raise RuntimeError("Expected the frozen project to have brim_width=0")
        if b'value="assembly.stl"' not in model_config:
            raise RuntimeError("The 3MF model config does not identify assembly.stl")

        root = ET.fromstring(model_bytes)
        namespace = {"m": CORE_NS}
        items = root.findall(".//m:build/m:item", namespace)
        if len(items) != 1 or "transform" not in items[0].attrib:
            raise RuntimeError("Expected exactly one transformed 3MF build item")
        item = items[0]
        old_transform = item.attrib["transform"]
        values = [float(value) for value in old_transform.split()]
        if len(values) != 12:
            raise RuntimeError("Expected a 12-value 3MF transform")
        source_matrix, _source_translation = parse_transform(values)

        vertices = [
            tuple(float(vertex.attrib[key]) for key in ("x", "y", "z"))
            for vertex in root.findall(".//m:vertex", namespace)
        ]
        triangles = root.findall(".//m:triangle", namespace)
        if len(vertices) != 5036 or len(triangles) != 9556:
            raise RuntimeError(
                "Frozen mesh topology mismatch: "
                f"expected 5036 vertices/9556 triangles, got {len(vertices)}/{len(triangles)}"
            )

        x_radians = math.radians(APPROVED_X_TILT_DEG)
        z_radians = math.radians(APPROVED_Z_ROTATION_DEG)
        x_cosine, x_sine = math.cos(x_radians), math.sin(x_radians)
        z_cosine, z_sine = math.cos(z_radians), math.sin(z_radians)
        world_x_rotation: Matrix = (
            (1.0, 0.0, 0.0),
            (0.0, x_cosine, -x_sine),
            (0.0, x_sine, x_cosine),
        )
        world_z_rotation: Matrix = (
            (z_cosine, -z_sine, 0.0),
            (z_sine, z_cosine, 0.0),
            (0.0, 0.0, 1.0),
        )
        final_matrix = multiply(
            world_z_rotation,
            multiply(world_x_rotation, source_matrix),
        )

        zero_translation: Vector = (0.0, 0.0, 0.0)
        rotated_points = [
            transform_point(final_matrix, zero_translation, vertex) for vertex in vertices
        ]
        rotated_minimum, rotated_maximum = bounds(rotated_points)
        final_translation: Vector = (
            BED_CENTER_MM[0] - (rotated_minimum[0] + rotated_maximum[0]) / 2.0,
            BED_CENTER_MM[1] - (rotated_minimum[1] + rotated_maximum[1]) / 2.0,
            -rotated_minimum[2],
        )
        final_points = [
            transform_point(final_matrix, final_translation, vertex) for vertex in vertices
        ]
        final_minimum, final_maximum = bounds(final_points)
        final_transform = serialize_transform(final_matrix, final_translation)

        old_attribute = f'transform="{old_transform}"'.encode("utf-8")
        new_attribute = f'transform="{final_transform}"'.encode("utf-8")
        if len(re.findall(re.escape(old_attribute), model_bytes)) != 1:
            raise RuntimeError("Could not identify exactly one source transform attribute")
        updated_model = model_bytes.replace(old_attribute, new_attribute, 1)

        updated_print_config = replace_setting(print_config, "brim_type", "outer_only")
        updated_print_config = replace_setting(
            updated_print_config, "brim_width", f"{APPROVED_BRIM_WIDTH_MM:g}"
        )

        args.output_project.parent.mkdir(parents=True, exist_ok=False)
        temporary = args.output_project.with_suffix(args.output_project.suffix + ".tmp")
        try:
            with zipfile.ZipFile(temporary, "w") as output_zip:
                for info in source_zip.infolist():
                    if info.filename == MODEL_MEMBER:
                        payload = updated_model
                    elif info.filename == PRINT_CONFIG_MEMBER:
                        payload = updated_print_config
                    else:
                        payload = source_zip.read(info.filename)
                    output_zip.writestr(info, payload)
            os.replace(temporary, args.output_project)
        finally:
            if temporary.exists():
                temporary.unlink()

    size = tuple(final_maximum[index] - final_minimum[index] for index in range(3))
    object_margins = (
        final_minimum[0],
        BED_SIZE_MM[0] - final_maximum[0],
        final_minimum[1],
        BED_SIZE_MM[1] - final_maximum[1],
    )
    conservative_reserve = tuple(
        margin - APPROVED_BRIM_WIDTH_MM for margin in object_margins
    )
    if min(conservative_reserve) < 5.0:
        raise RuntimeError(
            "Approved conservative 10 mm envelope reserve failed: "
            + ",".join(f"{value:.6f}" for value in conservative_reserve)
        )

    print(f"relative_world_x_tilt_deg={APPROVED_X_TILT_DEG:.3f}")
    print(f"relative_world_z_rotation_deg={APPROVED_Z_ROTATION_DEG:.3f}")
    print(f"brim_type={setting(updated_print_config, 'brim_type')}")
    print(f"brim_width_mm={setting(updated_print_config, 'brim_width')}")
    print(f"transform={final_transform}")
    print("bbox_size_mm=" + ",".join(f"{value:.6f}" for value in size))
    print("object_margins_mm=" + ",".join(f"{value:.6f}" for value in object_margins))
    print(
        "conservative_10mm_envelope_reserve_mm="
        + ",".join(f"{value:.6f}" for value in conservative_reserve)
    )
    print(f"output_sha256={sha256(args.output_project)}")


if __name__ == "__main__":
    main()
