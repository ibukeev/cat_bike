# Cat Head True-Scale Paper Projections

This package generates front and side paper projections from the approved
100 mm printable cat-head shell. Use the projections to judge the sculpture's
physical size on the bike before building the modular full-scale model.

The default candidate is **280 mm from the lowest chin/bottom point to the
highest ear tip**. It preserves the proportions of the successful 100 mm test
print.

## Generated Print Packs

Generated files are under `output/280mm/`:

- `cat-head-280mm-letter-tiled-print-pack.pdf`: four US Letter landscape pages.
  - Pages 1-2: front projection, top and bottom.
  - Pages 3-4: side projection, top and bottom.
- `cat-head-280mm-a3-print-pack.pdf`: two A3 portrait pages, one projection per page.
- `svg/`: individual vector pages for inspection or direct printing.
- `validation-report.json`: source dimensions, target dimensions, and output list.

## Print at True Scale

In the print dialog:

- Select **Actual Size** or **100%**.
- Disable **Fit**, **Shrink**, and **Scale to printable area**.
- Use landscape orientation for the US Letter pack.
- Use portrait orientation for the A3 pack.
- Measure the printed calibration bar; it must be exactly 50 mm.

Do not use a projection if its calibration bar is not 50 mm.

## Join the US Letter Pages

For each view:

1. Match the top and bottom pages for that view.
2. Trim one page along the red dashed `JOIN / TRIM LINE`.
3. Align the three red registration crosses with the matching line on the
   other page.
4. Tape the pages from the back.
5. Cut around the outer silhouette if a physical cardboard stand-in is useful,
   or hold the complete paper projection at the intended bike mount location.

The paper projection validates visual scale only. It does not validate mount
strength, steering clearance, connector tolerances, or wind loading.

## Regenerate

Run from the repository root:

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-scale-projections/generate_scale_projection_pack.py
```

Generate another candidate height with:

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-scale-projections/generate_scale_projection_pack.py --height-mm 300
```

PDF generation requires local `inkscape` and `pdfunite` commands. Use
`--svg-only` when only the vector pages are needed.
