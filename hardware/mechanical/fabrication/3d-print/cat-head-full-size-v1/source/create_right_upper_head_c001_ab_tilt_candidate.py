#!/usr/bin/env python3
"""Create a centered, bed-dropped tilt derivative of the frozen ASA 3MF."""

from __future__ import annotations

import argparse
import hashlib
import math
import os
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import zipfile


SOURCE_SHA256 = "423584124419c803feff141521f7663c26b722ba686aa20acc7e15402f7343b1"
MODEL_MEMBER = "3D/3dmodel.model"
CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
BED_CENTER = (125.0, 105.0)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def multiply(left: tuple[tuple[float, ...], ...], right: tuple[tuple[float, ...], ...]) -> tuple[tuple[float, ...], ...]:
    return tuple(
        tuple(sum(left[row][k] * right[k][column] for k in range(3)) for column in range(3))
        for row in range(3)
    )


def matrix_vector(matrix: tuple[tuple[float, ...], ...], vector: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(sum(matrix[row][k] * vector[k] for k in range(3)) for row in range(3))


def transform_point(matrix: tuple[tuple[float, ...], ...], translation: tuple[float, ...], point: tuple[float, ...]) -> tuple[float, ...]:
    rotated = matrix_vector(matrix, point)
    return tuple(rotated[index] + translation[index] for index in range(3))


def bounds(points: list[tuple[float, ...]]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    return (
        tuple(min(point[index] for point in points) for index in range(3)),
        tuple(max(point[index] for point in points) for index in range(3)),
    )


def parse_transform(values: list[float]) -> tuple[tuple[tuple[float, ...], ...], tuple[float, ...]]:
    matrix = (
        (values[0], values[3], values[6]),
        (values[1], values[4], values[7]),
        (values[2], values[5], values[8]),
    )
    return matrix, (values[9], values[10], values[11])


def serialize_transform(matrix: tuple[tuple[float, ...], ...], translation: tuple[float, ...]) -> str:
    values = (
        matrix[0][0], matrix[1][0], matrix[2][0],
        matrix[0][1], matrix[1][1], matrix[2][1],
        matrix[0][2], matrix[1][2], matrix[2][2],
        *translation,
    )
    return " ".join(f"{value:.12g}" for value in values)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--tilt-deg", type=float, required=True)
    parser.add_argument("--shift-y-mm", type=float, default=0.0)
    args = parser.parse_args()

    if not -30.0 <= args.tilt_deg <= 0.0:
        raise RuntimeError("Controlled search permits only -30 to 0 degrees world-X tilt")
    actual_hash = sha256(args.source)
    if actual_hash != SOURCE_SHA256:
        raise RuntimeError(f"Frozen ASA source mismatch: expected {SOURCE_SHA256}, got {actual_hash}")

    with zipfile.ZipFile(args.source, "r") as source_zip:
        model_bytes = source_zip.read(MODEL_MEMBER)
        root = ET.fromstring(model_bytes)
        namespace = {"m": CORE_NS}
        item = root.find(".//m:build/m:item", namespace)
        if item is None or "transform" not in item.attrib:
            raise RuntimeError("Expected one transformed build item")
        old_transform = item.attrib["transform"]
        values = [float(value) for value in old_transform.split()]
        if len(values) != 12:
            raise RuntimeError("Expected a 12-value 3MF transform")
        matrix, translation = parse_transform(values)
        vertices = [
            tuple(float(vertex.attrib[key]) for key in ("x", "y", "z"))
            for vertex in root.findall(".//m:vertex", namespace)
        ]
        world_points = [transform_point(matrix, translation, vertex) for vertex in vertices]
        minimum, maximum = bounds(world_points)
        center = tuple((minimum[index] + maximum[index]) / 2.0 for index in range(3))

        radians = math.radians(args.tilt_deg)
        cosine = math.cos(radians)
        sine = math.sin(radians)
        tilt = ((1.0, 0.0, 0.0), (0.0, cosine, -sine), (0.0, sine, cosine))
        tilted_matrix = multiply(tilt, matrix)
        relative_translation = tuple(translation[index] - center[index] for index in range(3))
        tilted_relative_translation = matrix_vector(tilt, relative_translation)
        tilted_translation = tuple(tilted_relative_translation[index] + center[index] for index in range(3))
        tilted_points = [transform_point(tilted_matrix, tilted_translation, vertex) for vertex in vertices]
        tilted_minimum, tilted_maximum = bounds(tilted_points)

        shift = (
            BED_CENTER[0] - (tilted_minimum[0] + tilted_maximum[0]) / 2.0,
            BED_CENTER[1] - (tilted_minimum[1] + tilted_maximum[1]) / 2.0 + args.shift_y_mm,
            -tilted_minimum[2],
        )
        final_translation = tuple(tilted_translation[index] + shift[index] for index in range(3))
        final_points = [transform_point(tilted_matrix, final_translation, vertex) for vertex in vertices]
        final_minimum, final_maximum = bounds(final_points)
        final_transform = serialize_transform(tilted_matrix, final_translation)

        old_attribute = f'transform="{old_transform}"'.encode("utf-8")
        new_attribute = f'transform="{final_transform}"'.encode("utf-8")
        if len(re.findall(re.escape(old_attribute), model_bytes)) != 1:
            raise RuntimeError("Could not identify exactly one source transform attribute")
        updated_model = model_bytes.replace(old_attribute, new_attribute, 1)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = args.output.with_suffix(args.output.suffix + ".tmp")
        with zipfile.ZipFile(temporary, "w") as output_zip:
            for info in source_zip.infolist():
                payload = updated_model if info.filename == MODEL_MEMBER else source_zip.read(info.filename)
                output_zip.writestr(info, payload)
        os.replace(temporary, args.output)

    size = tuple(final_maximum[index] - final_minimum[index] for index in range(3))
    margins = (
        final_minimum[0], 250.0 - final_maximum[0],
        final_minimum[1], 210.0 - final_maximum[1],
    )
    print(f"tilt_deg={args.tilt_deg:.3f}")
    print(f"shift_y_mm={args.shift_y_mm:.3f}")
    print(f"transform={final_transform}")
    print("bbox_size_mm=" + ",".join(f"{value:.6f}" for value in size))
    print("object_margins_mm=" + ",".join(f"{value:.6f}" for value in margins))
    print(f"output_sha256={sha256(args.output)}")


if __name__ == "__main__":
    main()
