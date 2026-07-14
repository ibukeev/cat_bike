#!/usr/bin/env python3
"""Generate true-scale front/side paper projections of the approved cat head."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Iterable


WORKDIR = Path(__file__).resolve().parent
REPO_ROOT = WORKDIR.parents[4]
DEFAULT_INPUT = (
    REPO_ROOT
    / "hardware/mechanical/fabrication/3d-print/cat-head-small-v1"
    / "output/cat-head-100mm-shell-mk4s.obj"
)

LETTER_LANDSCAPE_MM = (279.4, 215.9)
A3_PORTRAIT_MM = (297.0, 420.0)
JOIN_Y_MM = 140.0
TOP_PAGE_MODEL_OFFSET_Y_MM = 40.0
BOTTOM_PAGE_MODEL_OFFSET_Y_MM = -105.0
CALIBRATION_BAR_MM = 50.0

Vec3 = tuple[float, float, float]
Face = tuple[int, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--height-mm",
        type=float,
        default=280.0,
        help="Total chin-to-highest-ear-tip height in millimeters (default: 280)",
    )
    parser.add_argument(
        "--input-obj",
        type=Path,
        default=DEFAULT_INPUT,
        help="Approved printable shell OBJ used for the projections",
    )
    parser.add_argument(
        "--svg-only",
        action="store_true",
        help="Generate SVG pages without invoking Inkscape/pdfunite",
    )
    return parser.parse_args()


def load_obj(path: Path) -> tuple[list[Vec3], list[Face]]:
    vertices: list[Vec3] = []
    faces: list[Face] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        parts = raw_line.strip().split()
        if not parts:
            continue
        if parts[0] == "v" and len(parts) >= 4:
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif parts[0] == "f" and len(parts) >= 4:
            face = tuple(int(token.split("/")[0]) - 1 for token in parts[1:])
            faces.append(face)
    if not vertices or not faces:
        raise ValueError(f"No mesh geometry found in {path}")
    return vertices, faces


def bounds(vertices: Iterable[Vec3]) -> tuple[Vec3, Vec3]:
    points = list(vertices)
    return (
        tuple(min(point[axis] for point in points) for axis in range(3)),
        tuple(max(point[axis] for point in points) for axis in range(3)),
    )  # type: ignore[return-value]


def subtract(a: Vec3, b: Vec3) -> Vec3:
    return a[0] - b[0], a[1] - b[1], a[2] - b[2]


def cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def face_normal(face: Face, vertices: list[Vec3]) -> Vec3:
    origin, second, third = (vertices[index] for index in face[:3])
    return cross(subtract(second, origin), subtract(third, origin))


def format_number(value: float) -> str:
    return f"{value:.4f}".rstrip("0").rstrip(".")


def svg_header(width_mm: float, height_mm: float, title: str) -> list[str]:
    return [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{format_number(width_mm)}mm" '
            f'height="{format_number(height_mm)}mm" '
            f'viewBox="0 0 {format_number(width_mm)} {format_number(height_mm)}">'
        ),
        f"  <title>{title}</title>",
        "  <rect width=\"100%\" height=\"100%\" fill=\"white\"/>",
        "  <style>",
        "    text { font-family: Arial, Helvetica, sans-serif; fill: #111827; }",
        "    .title { font-size: 6px; font-weight: 700; }",
        "    .subtitle { font-size: 3.6px; }",
        "    .small { font-size: 3px; }",
        "    .dimension { font-size: 3.2px; font-weight: 700; }",
        "  </style>",
    ]


def page_border(width_mm: float, height_mm: float) -> str:
    return (
        f'<rect x="5" y="5" width="{format_number(width_mm - 10)}" '
        f'height="{format_number(height_mm - 10)}" fill="none" '
        'stroke="#d1d5db" stroke-width="0.25"/>'
    )


def projected_faces(
    vertices: list[Vec3],
    faces: list[Face],
    view: str,
    scale: float,
    lower: Vec3,
    upper: Vec3,
) -> list[tuple[list[tuple[float, float]], float, float]]:
    if view == "front":
        camera_axis = 2

        def project(vertex: Vec3) -> tuple[float, float]:
            return (vertex[0] - lower[0]) * scale, (upper[1] - vertex[1]) * scale

    elif view == "side":
        camera_axis = 0

        def project(vertex: Vec3) -> tuple[float, float]:
            # Rear opening is at the left; nose/front is at the right.
            return (vertex[2] - lower[2]) * scale, (upper[1] - vertex[1]) * scale

    else:
        raise ValueError(f"Unsupported view: {view}")

    result: list[tuple[list[tuple[float, float]], float, float]] = []
    for face in faces:
        normal = face_normal(face, vertices)
        magnitude = math.sqrt(sum(component * component for component in normal))
        if magnitude <= 1e-12:
            continue
        facing = normal[camera_axis] / magnitude
        if facing <= 1e-7:
            continue
        depth = sum(vertices[index][camera_axis] for index in face) / len(face)
        result.append(([project(vertices[index]) for index in face], depth, facing))
    result.sort(key=lambda item: item[1])
    return result


def model_group(
    projected: list[tuple[list[tuple[float, float]], float, float]],
    offset_x: float,
    offset_y: float,
) -> list[str]:
    lines = [
        f'<g transform="translate({format_number(offset_x)} {format_number(offset_y)})" '
        'stroke-linejoin="round">'
    ]
    for polygon, _depth, facing in projected:
        shade = max(226, min(250, round(250 - 20 * facing)))
        points = " ".join(
            f"{format_number(x)},{format_number(y)}" for x, y in polygon
        )
        lines.append(
            f'  <polygon points="{points}" fill="rgb({shade},{shade},{shade})" '
            'stroke="#6b7280" stroke-width="0.24"/>'
        )
    lines.append("</g>")
    return lines


def registration_line(page_y: float, width_mm: float, label: str) -> list[str]:
    lines = [
        (
            f'<line x1="7" y1="{format_number(page_y)}" x2="{format_number(width_mm - 7)}" '
            f'y2="{format_number(page_y)}" stroke="white" stroke-width="1.4"/>'
        ),
        (
            f'<line x1="7" y1="{format_number(page_y)}" x2="{format_number(width_mm - 7)}" '
            f'y2="{format_number(page_y)}" stroke="#dc2626" stroke-width="0.35" '
            'stroke-dasharray="3 2"/>'
        ),
    ]
    for x in (20.0, width_mm / 2.0, width_mm - 20.0):
        lines.extend(
            [
                (
                    f'<line x1="{format_number(x - 3)}" y1="{format_number(page_y)}" '
                    f'x2="{format_number(x + 3)}" y2="{format_number(page_y)}" '
                    'stroke="#dc2626" stroke-width="0.45"/>'
                ),
                (
                    f'<line x1="{format_number(x)}" y1="{format_number(page_y - 3)}" '
                    f'x2="{format_number(x)}" y2="{format_number(page_y + 3)}" '
                    'stroke="#dc2626" stroke-width="0.45"/>'
                ),
            ]
        )
    lines.append(
        f'<text x="{format_number(width_mm - 8)}" y="{format_number(page_y - 2)}" '
        f'class="small" text-anchor="end" fill="#b91c1c">{label}</text>'
    )
    return lines


def calibration_bar(x: float, y: float) -> list[str]:
    end = x + CALIBRATION_BAR_MM
    return [
        f'<line x1="{x}" y1="{y}" x2="{end}" y2="{y}" stroke="#111827" stroke-width="0.6"/>',
        f'<line x1="{x}" y1="{y - 2.5}" x2="{x}" y2="{y + 2.5}" stroke="#111827" stroke-width="0.6"/>',
        f'<line x1="{end}" y1="{y - 2.5}" x2="{end}" y2="{y + 2.5}" stroke="#111827" stroke-width="0.6"/>',
        f'<text x="{format_number((x + end) / 2)}" y="{format_number(y - 3.5)}" class="dimension" text-anchor="middle">50 mm calibration</text>',
    ]


def letter_page_svg(
    view: str,
    half: str,
    target_height: float,
    projection_width: float,
    projected: list[tuple[list[tuple[float, float]], float, float]],
) -> str:
    page_width, page_height = LETTER_LANDSCAPE_MM
    model_x = (page_width - projection_width) / 2.0
    is_top = half == "top"
    model_y = TOP_PAGE_MODEL_OFFSET_Y_MM if is_top else BOTTOM_PAGE_MODEL_OFFSET_Y_MM
    join_page_y = JOIN_Y_MM + model_y
    page_code = "TOP" if is_top else "BOTTOM"
    lines = svg_header(
        page_width,
        page_height,
        f"Cat head {target_height:g} mm {view} projection - {page_code}",
    )
    lines.append(page_border(page_width, page_height))
    lines.extend(model_group(projected, model_x, model_y))
    lines.extend(
        registration_line(
            join_page_y,
            page_width,
            "JOIN / TRIM LINE",
        )
    )
    if is_top:
        lines.extend(
            [
                f'<text x="10" y="14" class="title">CAT HEAD {target_height:g} mm — {view.upper()} — TOP</text>',
                '<text x="10" y="21" class="subtitle">Print landscape at 100% / Actual Size. Do not Fit to Page.</text>',
                '<text x="10" y="27" class="small">Keep the silhouette above the red line; align it with the matching bottom sheet.</text>',
            ]
        )
    else:
        lines.extend(calibration_bar(18.0, 201.0))
        lines.extend(
            [
                f'<text x="{format_number(page_width - 10)}" y="192" class="title" text-anchor="end">CAT HEAD {target_height:g} mm — {view.upper()} — BOTTOM</text>',
                f'<text x="{format_number(page_width - 10)}" y="199" class="small" text-anchor="end">Measure the calibration bar before joining pages.</text>',
            ]
        )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def dimension_line_vertical(x: float, top: float, bottom: float, label: str) -> list[str]:
    return [
        f'<line x1="{x}" y1="{top}" x2="{x}" y2="{bottom}" stroke="#111827" stroke-width="0.35"/>',
        f'<line x1="{x - 2.5}" y1="{top}" x2="{x + 2.5}" y2="{top}" stroke="#111827" stroke-width="0.35"/>',
        f'<line x1="{x - 2.5}" y1="{bottom}" x2="{x + 2.5}" y2="{bottom}" stroke="#111827" stroke-width="0.35"/>',
        f'<text x="{x - 3.5}" y="{format_number((top + bottom) / 2)}" class="dimension" text-anchor="middle" transform="rotate(-90 {x - 3.5} {format_number((top + bottom) / 2)})">{label}</text>',
    ]


def dimension_line_horizontal(left: float, right: float, y: float, label: str) -> list[str]:
    return [
        f'<line x1="{left}" y1="{y}" x2="{right}" y2="{y}" stroke="#111827" stroke-width="0.35"/>',
        f'<line x1="{left}" y1="{y - 2.5}" x2="{left}" y2="{y + 2.5}" stroke="#111827" stroke-width="0.35"/>',
        f'<line x1="{right}" y1="{y - 2.5}" x2="{right}" y2="{y + 2.5}" stroke="#111827" stroke-width="0.35"/>',
        f'<text x="{format_number((left + right) / 2)}" y="{y + 6}" class="dimension" text-anchor="middle">{label}</text>',
    ]


def a3_page_svg(
    view: str,
    target_height: float,
    projection_width: float,
    projected: list[tuple[list[tuple[float, float]], float, float]],
) -> str:
    page_width, page_height = A3_PORTRAIT_MM
    model_x = (page_width - projection_width) / 2.0
    model_y = 68.0
    lines = svg_header(
        page_width,
        page_height,
        f"Cat head {target_height:g} mm {view} projection - A3",
    )
    lines.append(page_border(page_width, page_height))
    lines.extend(
        [
            f'<text x="12" y="18" class="title">CAT HEAD {target_height:g} mm — {view.upper()} PROJECTION</text>',
            '<text x="12" y="28" class="subtitle">A3 portrait · Print at 100% / Actual Size · Do not Fit to Page</text>',
            '<text x="12" y="37" class="small">Use as a visual-size silhouette only; verify the 50 mm calibration bar after printing.</text>',
        ]
    )
    lines.extend(model_group(projected, model_x, model_y))
    lines.extend(
        dimension_line_vertical(
            max(8.0, model_x - 6.0),
            model_y,
            model_y + target_height,
            f"{target_height:g} mm",
        )
    )
    lines.extend(
        dimension_line_horizontal(
            model_x,
            model_x + projection_width,
            model_y + target_height + 8.0,
            f"{projection_width:.1f} mm",
        )
    )
    lines.extend(calibration_bar(18.0, 397.0))
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def export_pdf(svg_path: Path, pdf_path: Path, inkscape: str) -> None:
    subprocess.run(
        [
            inkscape,
            str(svg_path),
            "--export-type=pdf",
            f"--export-filename={pdf_path}",
        ],
        check=True,
    )


def combine_pdfs(page_paths: list[Path], output_path: Path, pdfunite: str) -> None:
    output_path.unlink(missing_ok=True)
    subprocess.run([pdfunite, *(str(path) for path in page_paths), str(output_path)], check=True)


def main() -> None:
    args = parse_args()
    if args.height_mm <= 0:
        raise ValueError("--height-mm must be positive")
    input_obj = args.input_obj.resolve()
    if not input_obj.exists():
        raise FileNotFoundError(input_obj)

    vertices, faces = load_obj(input_obj)
    lower, upper = bounds(vertices)
    source_dimensions = [upper[axis] - lower[axis] for axis in range(3)]
    source_height = source_dimensions[1]
    scale = args.height_mm / source_height
    target_width = source_dimensions[0] * scale
    target_depth = source_dimensions[2] * scale

    output_dir = WORKDIR / "output" / f"{args.height_mm:g}mm"
    svg_dir = output_dir / "svg"
    pdf_page_dir = output_dir / "pdf-pages"
    svg_dir.mkdir(parents=True, exist_ok=True)
    pdf_page_dir.mkdir(parents=True, exist_ok=True)

    projections = {
        "front": projected_faces(vertices, faces, "front", scale, lower, upper),
        "side": projected_faces(vertices, faces, "side", scale, lower, upper),
    }
    widths = {"front": target_width, "side": target_depth}

    svg_pages: dict[str, Path] = {}
    for view in ("front", "side"):
        for half in ("top", "bottom"):
            key = f"{view}-letter-{half}"
            path = svg_dir / f"cat-head-{args.height_mm:g}mm-{key}.svg"
            path.write_text(
                letter_page_svg(
                    view,
                    half,
                    args.height_mm,
                    widths[view],
                    projections[view],
                ),
                encoding="utf-8",
            )
            svg_pages[key] = path

        key = f"{view}-a3"
        path = svg_dir / f"cat-head-{args.height_mm:g}mm-{key}.svg"
        path.write_text(
            a3_page_svg(
                view,
                args.height_mm,
                widths[view],
                projections[view],
            ),
            encoding="utf-8",
        )
        svg_pages[key] = path

    output_files: dict[str, str] = {
        key: str(path.relative_to(REPO_ROOT)) for key, path in svg_pages.items()
    }
    if not args.svg_only:
        inkscape = shutil.which("inkscape")
        pdfunite = shutil.which("pdfunite")
        if not inkscape or not pdfunite:
            raise RuntimeError("PDF generation requires both inkscape and pdfunite")

        pdf_pages: dict[str, Path] = {}
        for key, svg_path in svg_pages.items():
            pdf_path = pdf_page_dir / f"{svg_path.stem}.pdf"
            export_pdf(svg_path, pdf_path, inkscape)
            pdf_pages[key] = pdf_path

        letter_pack = output_dir / f"cat-head-{args.height_mm:g}mm-letter-tiled-print-pack.pdf"
        combine_pdfs(
            [
                pdf_pages["front-letter-top"],
                pdf_pages["front-letter-bottom"],
                pdf_pages["side-letter-top"],
                pdf_pages["side-letter-bottom"],
            ],
            letter_pack,
            pdfunite,
        )
        a3_pack = output_dir / f"cat-head-{args.height_mm:g}mm-a3-print-pack.pdf"
        combine_pdfs(
            [pdf_pages["front-a3"], pdf_pages["side-a3"]],
            a3_pack,
            pdfunite,
        )
        output_files["letter_pdf"] = str(letter_pack.relative_to(REPO_ROOT))
        output_files["a3_pdf"] = str(a3_pack.relative_to(REPO_ROOT))

    report = {
        "source_obj": str(input_obj.relative_to(REPO_ROOT)),
        "source_dimensions_print_orientation_mm": [round(value, 4) for value in source_dimensions],
        "target_height_chin_to_ear_tip_mm": args.height_mm,
        "target_front_width_mm": round(target_width, 4),
        "target_side_depth_mm": round(target_depth, 4),
        "uniform_scale_from_source_obj": round(scale, 8),
        "visible_projection_faces": {
            view: len(projections[view]) for view in ("front", "side")
        },
        "letter_page_size_mm": list(LETTER_LANDSCAPE_MM),
        "a3_page_size_mm": list(A3_PORTRAIT_MM),
        "letter_join_height_from_head_top_mm": JOIN_Y_MM,
        "calibration_bar_mm": CALIBRATION_BAR_MM,
        "print_instruction": "Print at 100% / Actual Size; disable Fit to Page",
        "outputs": output_files,
    }
    report_path = output_dir / "validation-report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
