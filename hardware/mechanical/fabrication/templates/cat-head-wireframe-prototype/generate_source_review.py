#!/usr/bin/env python3
"""Create gate-zero review artifacts for the Gemini ORX cat-head reference."""

from __future__ import annotations

import csv
from pathlib import Path


WORKDIR = Path(__file__).resolve().parent
SOURCE_REL = "../../../../../assets/references/cat-head/Gemini_Generated_Image_orxfnrorxfnrorxf.png"
SOURCE_ABS = (WORKDIR / SOURCE_REL).resolve()
WIDTH = 2334
HEIGHT = 1824


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def write_metadata() -> None:
    with (WORKDIR / "source_metadata.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["key", "value"],
        )
        writer.writeheader()
        writer.writerows(
            [
                {"key": "source_path", "value": str(SOURCE_ABS)},
                {"key": "source_relative_path", "value": SOURCE_REL},
                {"key": "source_width_px", "value": WIDTH},
                {"key": "source_height_px", "value": HEIGHT},
                {"key": "workflow_status", "value": "gate_0_source_review"},
            ]
        )


def write_readme() -> None:
    write_text(
        WORKDIR / "README.md",
        f"""# Cat Head From Gemini ORX V2

This is a clean restart from:

`{SOURCE_REL}`

Source size: `{WIDTH} x {HEIGHT}` px.

## Current Gate

Gate 0: source review and manual trace setup.

No 3D geometry should be generated from this reference until the 2D trace views are accepted. The previous failure mode was guessing cross-projection correspondence too early.

## Files

- `source-reference-review.html`: browser review board with pixel coordinates and grid.
- `manual-trace-template.svg`: Inkscape SVG with the source image locked underneath empty trace layers.
- `source_metadata.csv`: source path and dimensions.

## Next Decision

Open the review board and decide which views in the image are usable as projection evidence:

- front
- side
- back
- 3/4 or isometric reference only

If the source has only a perspective/isometric view and no orthographic views, it can guide aesthetics but cannot fully constrain a rod skeleton by itself.
""",
    )


def write_trace_svg() -> None:
    grid_lines = []
    for x in range(0, WIDTH + 1, 100):
        stroke = "#60a5fa" if x % 500 else "#2563eb"
        opacity = "0.20" if x % 500 else "0.38"
        grid_lines.append(
            f'<line x1="{x}" y1="0" x2="{x}" y2="{HEIGHT}" stroke="{stroke}" stroke-width="1" opacity="{opacity}" />'
        )
    for y in range(0, HEIGHT + 1, 100):
        stroke = "#60a5fa" if y % 500 else "#2563eb"
        opacity = "0.20" if y % 500 else "0.38"
        grid_lines.append(
            f'<line x1="0" y1="{y}" x2="{WIDTH}" y2="{y}" stroke="{stroke}" stroke-width="1" opacity="{opacity}" />'
        )

    write_text(
        WORKDIR / "manual-trace-template.svg",
        f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<svg
   width="{WIDTH}"
   height="{HEIGHT}"
   viewBox="0 0 {WIDTH} {HEIGHT}"
   version="1.1"
   xmlns="http://www.w3.org/2000/svg"
   xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
   xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd">
  <sodipodi:namedview
     id="namedview"
     pagecolor="#ffffff"
     bordercolor="#666666"
     borderopacity="1.0"
     inkscape:pageopacity="0.0"
     inkscape:pageshadow="2"
     inkscape:document-units="px"
     inkscape:zoom="0.35"
     inkscape:cx="{WIDTH / 2:.1f}"
     inkscape:cy="{HEIGHT / 2:.1f}"
     inkscape:window-width="1600"
     inkscape:window-height="1000"
     inkscape:current-layer="front_candidate_edges" />

  <g inkscape:groupmode="layer" inkscape:label="source_reference_locked" id="source_reference_locked" style="display:inline">
    <image
       id="source_image"
       href="{SOURCE_REL}"
       x="0"
       y="0"
       width="{WIDTH}"
       height="{HEIGHT}"
       opacity="0.55"
       style="image-rendering:auto" />
  </g>

  <g inkscape:groupmode="layer" inkscape:label="grid_locked" id="grid_locked" style="display:inline">
    {"".join(grid_lines)}
  </g>

  <g inkscape:groupmode="layer" inkscape:label="front_candidate_edges" id="front_candidate_edges" style="display:inline">
  </g>

  <g inkscape:groupmode="layer" inkscape:label="side_candidate_edges" id="side_candidate_edges" style="display:inline">
  </g>

  <g inkscape:groupmode="layer" inkscape:label="back_candidate_edges" id="back_candidate_edges" style="display:inline">
  </g>

  <g inkscape:groupmode="layer" inkscape:label="perspective_reference_edges" id="perspective_reference_edges" style="display:inline">
  </g>

  <g inkscape:groupmode="layer" inkscape:label="node_labels" id="node_labels" style="display:inline">
  </g>

  <g inkscape:groupmode="layer" inkscape:label="reject_notes" id="reject_notes" style="display:inline">
  </g>
</svg>
""",
    )


def write_review_html() -> None:
    write_text(
        WORKDIR / "source-reference-review.html",
        f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Gemini ORX Source Review</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f5f2;
      color: #1f2933;
    }}
    body {{
      margin: 0;
    }}
    header {{
      position: sticky;
      top: 0;
      z-index: 10;
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto auto;
      gap: 16px;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid #d4d7d2;
      background: rgba(245, 245, 242, 0.96);
      backdrop-filter: blur(8px);
    }}
    h1 {{
      margin: 0;
      font-size: 16px;
      line-height: 1.2;
      font-weight: 650;
    }}
    .meta {{
      margin-top: 4px;
      color: #5b6472;
      font-size: 12px;
    }}
    label {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 13px;
      color: #344052;
    }}
    input[type="range"] {{
      width: 160px;
    }}
    .readout {{
      min-width: 156px;
      padding: 8px 10px;
      border: 1px solid #cbd5df;
      border-radius: 6px;
      background: #fff;
      font-variant-numeric: tabular-nums;
      font-size: 13px;
    }}
    main {{
      padding: 18px;
    }}
    .stage-wrap {{
      overflow: auto;
      border: 1px solid #cbd5df;
      background: #e9ecef;
      max-height: calc(100vh - 108px);
    }}
    .stage {{
      position: relative;
      width: {WIDTH}px;
      height: {HEIGHT}px;
      transform-origin: top left;
      background: #fff;
    }}
    .stage img,
    .grid {{
      position: absolute;
      inset: 0;
      width: {WIDTH}px;
      height: {HEIGHT}px;
    }}
    .grid {{
      pointer-events: none;
    }}
    .crosshair {{
      position: absolute;
      inset: 0;
      pointer-events: none;
    }}
    .vline,
    .hline {{
      position: absolute;
      background: rgba(220, 38, 38, 0.85);
      display: none;
    }}
    .vline {{ width: 1px; height: 100%; }}
    .hline {{ height: 1px; width: 100%; }}
    @media (max-width: 760px) {{
      header {{
        grid-template-columns: 1fr;
      }}
      input[type="range"] {{
        width: min(70vw, 260px);
      }}
      .readout {{
        min-width: 0;
      }}
    }}
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Gemini ORX Source Review</h1>
      <div class="meta">{WIDTH} x {HEIGHT}px · gate 0 · no inferred geometry</div>
    </div>
    <label>
      Zoom
      <input id="zoom" type="range" min="20" max="160" value="45" />
    </label>
    <div id="readout" class="readout">x: -, y: -</div>
  </header>
  <main>
    <div class="stage-wrap">
      <div id="stage" class="stage">
        <img src="{SOURCE_REL}" alt="Gemini generated cat-head reference" draggable="false" />
        <svg class="grid" viewBox="0 0 {WIDTH} {HEIGHT}" aria-hidden="true">
          <defs>
            <pattern id="smallGrid" width="100" height="100" patternUnits="userSpaceOnUse">
              <path d="M 100 0 L 0 0 0 100" fill="none" stroke="#60a5fa" stroke-width="1" opacity="0.22"/>
            </pattern>
            <pattern id="largeGrid" width="500" height="500" patternUnits="userSpaceOnUse">
              <rect width="500" height="500" fill="url(#smallGrid)"/>
              <path d="M 500 0 L 0 0 0 500" fill="none" stroke="#2563eb" stroke-width="1.5" opacity="0.45"/>
            </pattern>
          </defs>
          <rect width="{WIDTH}" height="{HEIGHT}" fill="url(#largeGrid)" />
        </svg>
        <div class="crosshair">
          <div id="vline" class="vline"></div>
          <div id="hline" class="hline"></div>
        </div>
      </div>
    </div>
  </main>
  <script>
    const stage = document.getElementById("stage");
    const zoom = document.getElementById("zoom");
    const readout = document.getElementById("readout");
    const vline = document.getElementById("vline");
    const hline = document.getElementById("hline");

    function setZoom() {{
      const scale = Number(zoom.value) / 100;
      stage.style.transform = `scale(${{scale}})`;
      stage.parentElement.style.minHeight = `${{Math.min({HEIGHT} * scale + 2, window.innerHeight - 108)}}px`;
    }}

    stage.addEventListener("pointermove", (event) => {{
      const rect = stage.getBoundingClientRect();
      const scale = Number(zoom.value) / 100;
      const x = Math.max(0, Math.min({WIDTH}, (event.clientX - rect.left) / scale));
      const y = Math.max(0, Math.min({HEIGHT}, (event.clientY - rect.top) / scale));
      readout.textContent = `x: ${{x.toFixed(1)}}, y: ${{y.toFixed(1)}}`;
      vline.style.display = "block";
      hline.style.display = "block";
      vline.style.left = `${{x}}px`;
      hline.style.top = `${{y}}px`;
    }});

    stage.addEventListener("pointerleave", () => {{
      readout.textContent = "x: -, y: -";
      vline.style.display = "none";
      hline.style.display = "none";
    }});

    zoom.addEventListener("input", setZoom);
    window.addEventListener("resize", setZoom);
    setZoom();
  </script>
</body>
</html>
""",
    )


def main() -> None:
    if not SOURCE_ABS.exists():
        raise SystemExit(f"Missing source image: {SOURCE_ABS}")
    write_metadata()
    write_readme()
    write_trace_svg()
    write_review_html()


if __name__ == "__main__":
    main()
