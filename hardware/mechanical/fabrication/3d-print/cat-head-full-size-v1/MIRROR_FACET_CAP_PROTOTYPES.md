# Mirror Facet Cap Prototypes

## Purpose

This package tests a replaceable mirror-surface system without refinishing the
full ASA head. The structural shell remains satin black. Thin black ASA caps
sit inside selected opaque facet boundaries, receive adhesive mirror film on
their smooth build-plate faces, and leave deliberate black reveals at panel
edges.

Four representative Gate 8 source facets produce six printable caps:

| Cap | Location | Full-size cap bounds | Why it is included |
| --- | --- | ---: | --- |
| `TRI014` | Right forehead | 87.03 x 51.57 mm | Ordinary visible triangular finish sample |
| `QUAD014_A` | Right cheek | 66.74 x 16.82 mm | First planar half of the cheek source quad |
| `QUAD014_B` | Right cheek | 94.72 x 40.00 mm | Second planar half and diagonal-seam test |
| `TRI003` | Right center muzzle frame | 37.24 x 17.64 mm | Small Gate 8 opaque conversion and corner test |
| `QUAD008_A` | Right ear | 124.75 x 11.49 mm | Long, narrow curl test |
| `QUAD008_B` | Right ear | 140.17 x 61.68 mm | Largest cap and broad flatness test |

`QUAD014` and `QUAD008` cannot use one rigid cap each. Their full source
quads have 1.996 mm and 0.870 mm planarity residuals at 330 mm scale. Each is
therefore split along its existing printed diagonal into two truly planar
mirror caps. Bridging either bend with one rigid part is rejected.

## Generate

From the repository root:

~~~bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_mirror_facet_cap_prototypes.py
~~~

Tracked settings are in
`config/mirror-facet-cap-prototypes.json`. Generated assets are written under
`output/mirror-facet-cap-prototypes/`:

- `mirror-facet-cap-left-starter-plate-0p8mm.stl`
- `mirror-facet-cap-starter-plate-0p8mm.stl` — compatibility alias for the
  same corrected left-side plate
- `mirror-facet-cap-test-plate-0p6mm.stl`
- `mirror-facet-cap-test-plate-0p8mm.stl`
- six individual STLs under each thickness directory
- `mirror-facet-cap-test-plate-1to1.svg`
- `prototype-parts.csv`
- `validation-report.json`

The two complete plates fit the conservative 240 x 200 mm MK4S bed. The
0.6 mm plate contains about 6.59 g of modeled ASA; the 0.8 mm plate contains
about 8.79 g.

## Print the Three-Cap Starter Plate

The first physical trial uses
`mirror-facet-cap-left-starter-plate-0p8mm.stl`. It contains three actual
left-side Gate 8 caps that fit the currently printed left shell:

- `TRI042`, the small left muzzle-frame corner and trimming test;
- `TRI019`, the medium left forehead triangle and ordinary wrap sample;
- `QUAD025_B`, the largest left ear plane and broad bubbling/flatness test.

These are the accepted-surface counterparts of right-side `TRI003`, `TRI014`,
and `QUAD008-B`. The left forehead is slightly asymmetric in the source model,
so a slicer-mirrored right cap is not used for fit validation.

Print this starter plate in the available black PETG on the textured
powder-coated PEI sheet:

- 0.4 mm nozzle and 0.20 mm layers;
- four solid layers for the exact 0.8 mm modeled thickness;
- no supports, ironing, raft, or scaling;
- no glue stick on the textured sheet;
- let the sheet and parts cool fully before flexing the sheet for removal.

The three parts contain about 5.60 cm3 of material, or approximately 7.12 g of
PETG at the tracked 1.27 g/cm3 density. The textured build-plate face is
acceptable for testing trimming, adhesive handling, fit, and broad optical
behavior. It is not the final optical-quality test because the texture may
telegraph through mirror film. Repeat the accepted cap later on the smooth
sheet with a thin glue-stick release layer before approving the final mirror
finish.

## Print Both Thicknesses

Use the qualified black-ASA profile for the enclosed MK4S:

- 0.4 mm nozzle and 0.20 mm layers;
- no supports;
- no ironing;
- future mirror face flat against the smooth build plate;
- allow the entire plate and parts to cool before removal;
- add a modest removable brim only if the large ear piece begins to lift.

Do not flip the STLs. The surface touching the smooth build plate is the surface
that receives mirror film.

Print the 0.8 mm plate first because it is the safer stiffness baseline. Print
the 0.6 mm plate to determine whether the approximately 25-percent mass
reduction is worth any additional curling or handling difficulty.

## Film Application

1. Let the caps relax flat for at least 24 hours after printing.
2. Reject or record any cap with a lifted corner or visible bow before film.
3. Clean the smooth face with a lint-free wipe and plastic-safe isopropyl
   alcohol. Let it dry fully.
4. Apply mirror film dry while the cap lies fully supported on a flat table.
5. Use a clean felt squeegee and light overlapping strokes from the center
   outward.
6. Trim the film flush to the black cap edge with a fresh blade. In this
   prototype, "wrapped" means face-laminated and flush-trimmed; do not fold
   film onto the rear adhesive surface.
7. Leave any front protective liner in place until handling and trimming are
   complete.
8. For the first shell fit, use small removable adhesive tabs. Use full-face
   3M 9472LE/300LSE transfer adhesive only after the cap thickness, gap, and
   color are accepted.

The model already includes a 0.9 mm inset from every source-plane boundary and
a 0.8 mm straight corner chamfer. Two neighboring caps therefore create an
approximately 1.8 mm black reveal before ordinary print and assembly tolerance.

## Amazon Film Shortlist

Amazon inventory and sellers change. These links intentionally search the
exact product name; verify the listing still says **adhesive mirror chrome
vinyl**, not heat-transfer vinyl, brushed metallic, glitter, or holographic
film.

### Recommended two-film comparison

1. [ORACAL 351 #911 Mirror Gold Chrome, 12 x 24 inches](https://www.amazon.com/s?k=ORACAL+351+911+Mirror+Gold+Chrome+Vinyl+12+x+24)
   - Preferred thin, dimensionally stable flat-facet control.
   - Strong yellow-gold mirror appearance.
   - The manufacturer's flat/simple-curve product data makes this the lowest-risk
     first material.
   - [Official ORAFOL 351 specifications](https://www.orafol.com/en/americas/products/oracal-351-metalized-polyester-craft-vinyl)

2. [TECKWRAP Rose Gold Mirror Chrome adhesive craft vinyl, 1 ft x 5 ft](https://www.amazon.com/s?k=TECKWRAP+Rose+Gold+Mirror+Chrome+Adhesive+Craft+Vinyl+1ft+x+5ft)
   - Best match for the warm rose-gold/cyan concept.
   - Treat as a prototype candidate until the actual roll passes adhesion,
     heat, and scratch testing.

### Useful third color

3. [TECKWRAP Champagne Gold bubble-free mirror chrome, 1 ft x 5 ft](https://www.amazon.com/s?k=TECKWRAP+Champagne+Gold+Bubble+Free+Mirror+Chrome+Vinyl+1ft+x+5ft)
   - Warmer and less yellow than ordinary chrome gold.
   - Air-channel construction may be easier to place, but compare its reflection
     closely against the smooth ORACAL control.

### Optional neutral control

4. [ORACAL 351 Silver Chrome, 12 x 24 inches](https://www.amazon.com/s?k=ORACAL+351+Silver+Chrome+Vinyl+12+x+24)
   - Useful for separating color preference from actual reflection quality.
   - Not required if the project will definitely remain warm gold.

A single 12 x 24 inch sheet is ample for all six prototype caps. A 1 ft x 5 ft
roll provides about 5 square feet, compared with about 1.92 square feet of
current Gate 8 opaque surface before nesting waste. One five-foot roll should
therefore cover the complete head once with careful nesting; a ten-foot roll is
safer if replacement facets and application mistakes are expected.

For final cap-to-shell attachment, search Amazon for
[3M 9472LE / 300LSE transfer adhesive sheets or roll](https://www.amazon.com/s?k=3M+9472LE+300LSE+adhesive+transfer+tape+sheets).
Do not purchase a full-head quantity until a small piece passes the actual
ASA/paint adhesion test.

## Physical Acceptance

Photograph both thicknesses in direct sun, open shade, and under the intended
cyan LEDs. For every cap record:

- free-state corner lift after 24 hours;
- whether first-layer/build-plate texture is visible in reflection at 1 m;
- wrinkles, bubbles, adhesive channels, and edge damage;
- ease of trimming without tearing the mirror coating;
- shell fit and actual black-reveal width;
- whether a cheek or ear diagonal needs more than the designed reveal;
- appearance after the planned 65 C heat exposure;
- scratch response using a sacrificial offcut, not an installed show face.

Accept 0.6 mm only if it remains visibly flat and handles cleanly. Otherwise
use 0.8 mm. Do not scale the outlines to tune fit; update the tracked inset or
corner-chamfer setting and regenerate.
