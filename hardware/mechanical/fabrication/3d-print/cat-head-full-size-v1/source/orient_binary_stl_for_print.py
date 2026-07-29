#!/usr/bin/env python3
"""Apply a documented print transform to a binary STL."""

from __future__ import annotations

import argparse
import math
import struct
from pathlib import Path


STL_HEADER_BYTES = 80
STL_TRIANGLE_BYTES = 50


def rotate_xyz(point: tuple[float, float, float], degrees: tuple[float, float, float]) -> tuple[float, float, float]:
    x, y, z = point
    ax, ay, az = (math.radians(value) for value in degrees)

    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)

    y, z = y * cx - z * sx, y * sx + z * cx
    x, z = x * cy + z * sy, -x * sy + z * cy
    x, y = x * cz - y * sz, x * sz + y * cz
    return x, y, z


def map_axes(point: tuple[float, float, float], axis_order: str) -> tuple[float, float, float]:
    coordinates = dict(zip("xyz", point))
    return tuple(coordinates[axis] for axis in axis_order)


def transform_stl(
    input_path: Path,
    output_path: Path,
    rotation_degrees: tuple[float, float, float],
    axis_order: str,
) -> tuple[float, float, float]:
    data = input_path.read_bytes()
    if len(data) < STL_HEADER_BYTES + 4:
        raise ValueError(f"{input_path} is too short to be a binary STL")

    triangle_count = struct.unpack_from("<I", data, STL_HEADER_BYTES)[0]
    expected_size = STL_HEADER_BYTES + 4 + triangle_count * STL_TRIANGLE_BYTES
    if len(data) != expected_size:
        raise ValueError(
            f"{input_path} is not a supported binary STL: "
            f"expected {expected_size} bytes, found {len(data)}"
        )

    triangles: list[tuple[tuple[float, float, float], list[tuple[float, float, float]], int]] = []
    all_vertices: list[tuple[float, float, float]] = []
    offset = STL_HEADER_BYTES + 4
    for _ in range(triangle_count):
        values = struct.unpack_from("<12fH", data, offset)
        normal = map_axes(rotate_xyz(tuple(values[0:3]), rotation_degrees), axis_order)
        vertices = [
            map_axes(rotate_xyz(tuple(values[index : index + 3]), rotation_degrees), axis_order)
            for index in (3, 6, 9)
        ]
        triangles.append((normal, vertices, values[12]))
        all_vertices.extend(vertices)
        offset += STL_TRIANGLE_BYTES

    minimum = [min(vertex[axis] for vertex in all_vertices) for axis in range(3)]
    maximum = [max(vertex[axis] for vertex in all_vertices) for axis in range(3)]
    translation = (
        -(minimum[0] + maximum[0]) / 2.0,
        -(minimum[1] + maximum[1]) / 2.0,
        -minimum[2],
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = b"Cat head MK4S print orientation".ljust(STL_HEADER_BYTES, b"\0")
    with output_path.open("wb") as output:
        output.write(header)
        output.write(struct.pack("<I", triangle_count))
        for normal, vertices, attribute in triangles:
            translated = [
                tuple(vertex[axis] + translation[axis] for axis in range(3))
                for vertex in vertices
            ]
            output.write(
                struct.pack(
                    "<12fH",
                    *normal,
                    *translated[0],
                    *translated[1],
                    *translated[2],
                    attribute,
                )
            )

    return tuple(maximum[axis] - minimum[axis] for axis in range(3))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--rotate-x", type=float, default=0.0)
    parser.add_argument("--rotate-y", type=float, default=0.0)
    parser.add_argument("--rotate-z", type=float, default=0.0)
    parser.add_argument(
        "--axis-order",
        choices=("xyz", "yzx", "zxy"),
        default="xyz",
        help="Positive-determinant axis permutation applied after rotation",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dimensions = transform_stl(
        args.input,
        args.output,
        (args.rotate_x, args.rotate_y, args.rotate_z),
        args.axis_order,
    )
    print(
        "Wrote {} with dimensions {:.3f} x {:.3f} x {:.3f} mm".format(
            args.output, *dimensions
        )
    )


if __name__ == "__main__":
    main()
