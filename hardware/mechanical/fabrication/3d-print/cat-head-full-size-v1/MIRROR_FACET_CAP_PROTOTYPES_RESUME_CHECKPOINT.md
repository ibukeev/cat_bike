# Mirror Facet Cap Prototype Resume Checkpoint

Updated: 2026-07-27

## Current Review and Output Files

Generate and review:

- `output/mirror-facet-cap-prototypes/mirror-facet-cap-test-plate-0p6mm.stl`
- `output/mirror-facet-cap-prototypes/mirror-facet-cap-test-plate-0p8mm.stl`
- `output/mirror-facet-cap-prototypes/mirror-facet-cap-left-starter-plate-0p8mm.stl`
- `output/mirror-facet-cap-prototypes/mirror-facet-cap-starter-plate-0p8mm.stl`
  — compatibility alias containing the same corrected left-side geometry
- `output/mirror-facet-cap-prototypes/mirror-facet-cap-test-plate-1to1.svg`
- `output/mirror-facet-cap-prototypes/prototype-parts.csv`
- `output/mirror-facet-cap-prototypes/validation-report.json`

Source of truth:

- `config/mirror-facet-cap-prototypes.json`
- `source/generate_mirror_facet_cap_prototypes.py`
- `MIRROR_FACET_CAP_PROTOTYPES.md`

## Accepted Decisions and Dimensions

- The printed Gate 8 shell remains structural; mirror caps are cosmetic,
  replaceable parts.
- The generated comparison plates retain black ASA as the qualified baseline.
- The first physical starter plate uses available black PETG at 0.8 mm on the
  textured powder-coated PEI sheet.
- The starter plate contains actual left-shell facets `TRI042`, `TRI019`, and
  `QUAD025_B`, covering small-corner trimming, an ordinary medium facet, and
  the largest broad flatness/bubbling case.
- Their accepted-surface right-side counterparts are `TRI003`, `TRI014`, and
  `QUAD008-B`. The left forehead is slightly asymmetric, so the actual left
  geometry is generated rather than relying on a slicer mirror operation.
- Two thicknesses are under review: 0.6 mm and 0.8 mm.
- Each cap is inset 0.9 mm from its real planar source boundary.
- Every corner receives a 0.8 mm straight chamfer.
- The smooth build-plate face is the mirror-film face.
- Four representative source facets are used: forehead `TRI014`, cheek
  `QUAD014`, Gate 8 opaque muzzle facet `TRI003`, and ear `QUAD008`.
- Six STLs are required per thickness because each selected source quad has a
  real diagonal bend and becomes two planar caps.

## Validation Performed

The generator completed successfully on 2026-07-26 and was regenerated with
the three-cap starter plate on 2026-07-27.

- All six selected cap planes resolve to Gate 8 `integrated_opaque`.
- Maximum planar residual after splitting the quads is below
  0.0000001 mm at reported precision.
- Both thickness plates fit 240 x 200 mm.
- Occupied plate bounds are 6.0, 6.0 to 218.906, 142.730 mm.
- All twelve individual STLs have zero boundary and nonmanifold edges.
- Both combined plate STLs have zero boundary and nonmanifold edges.
- The starter plate contains three closed manifold parts and 60 facets with
  zero boundary or nonmanifold edges.
- PrusaSlicer imports the starter plate as three manifold parts at exactly
  0.800 mm Z thickness and 221.210 x 86.890 mm overall size.
- Starter occupied bounds are 6.0, 6.0 to 227.210, 92.890 mm, inside the
  conservative 240 x 200 mm bed.
- Starter modeled volume is 5.604 cm3, approximately 7.12 g at the tracked
  black-PETG density of 1.27 g/cm3.
- PrusaSlicer `--info` imports both plates as manifold, reports six parts per
  plate, and preserves exact 0.600 mm and 0.800 mm Z thicknesses.
- Modeled black-ASA mass is 6.59 g for the 0.6 mm plate and 8.79 g for the
  0.8 mm plate.
- Python compilation and repository whitespace validation pass.

Digital validation does not approve optical quality, real curling, adhesion,
heat behavior, or vibration.

## Rejected or Unsafe Variants

- One rigid cap across `QUAD014` is rejected: 1.996 mm full-size planarity
  residual.
- One rigid cap across `QUAD008` is rejected: 0.870 mm full-size planarity
  residual.
- Metallic or silk filament alone is rejected as a mirror finish.
- A cap that bridges a shell seam, illuminated insert, eye opening, or printed
  diagonal plane change is rejected.
- Applying permanent full-face transfer adhesive before color, gap, and
  thickness approval is rejected.
- Treating the textured PETG face as final mirror-surface approval is rejected;
  its build-plate texture may telegraph through the film.
- Using the previously generated right-side starter geometry to validate the
  already printed left shell is rejected. The generic starter filename now
  aliases the corrected left geometry.

## Exact Regeneration Command

From the repository root:

~~~bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_mirror_facet_cap_prototypes.py
~~~

## Next Physical-Review Steps

1. Record the exact ordered mirror-vinyl product, color, size, and seller when
   the order details are available.
2. Print the left-side three-cap 0.8 mm black-PETG starter plate on the
   textured sheet.
3. Let the three caps rest flat for 24 hours and measure/photograph corner
   lift.
4. Face-laminate and flush-trim the ordered film; keep the rear PETG bare for
   the mounting adhesive.
5. Temporarily fit the caps to the physical shell and photograph direct front,
   three-quarter, and side views in sun and at night with cyan lighting.
6. Repeat the selected cap on a smooth sheet with a glue-stick release layer
   before accepting final optical quality.
7. Print the complete 0.8 mm comparison plate, then the 0.6 mm plate only if a
   thinner cap remains desirable after handling the starter set.
8. Run the planned 65 C coupon heat exposure before selecting the production
   cap thickness or permanent adhesive.
9. Record the accepted film SKU/roll batch, cap thickness, actual reveal, and
   cleaning method in this checkpoint before generating the full-head set.
