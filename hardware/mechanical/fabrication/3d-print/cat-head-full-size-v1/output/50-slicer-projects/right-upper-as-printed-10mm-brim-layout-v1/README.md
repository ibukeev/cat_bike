# Right Upper As-Printed 10 mm Brim Layout V1

Open in PrusaSlicer:

`CAT_HEAD_RIGHT_UPPER_AS_PRINTED_10MM_BRIM_LAYOUT_V1.3mf`

Status: `PASS_LAYOUT__HOLD_SOURCE_MESH_AND_PHYSICAL_FIRST_LAYER`.

The approved layout preserves the frozen `assembly.stl` geometry and scale,
adds `+22 deg` world-X tilt and `-9 deg` world-Z rotation, centers the result
on the Original Prusa MK4 bed, and enables a `10 mm` outer-only brim. Automatic
snug supports at `40 deg`, Prusament ASA, `0.20 mm` layers, `25%` grid infill,
and three perimeters remain unchanged.

The actual sliced first-layer extrusion margins are:

- left: `14.891 mm`;
- right: `14.304 mm`;
- front: `10.759 mm`;
- rear: `15.375 mm`.

Review `first-layer-brim-support-evidence-v1.png` and `validation-v1.json`.
The G-code is diagnostic and is not released for an unattended full print.
PrusaSlicer reports that the unchanged source mesh is non-manifold with 75
open edges, 16 reversed facets, 48 backwards edges, and 166 disconnected
parts. Before committing to the approximately 16-hour ASA print, observe the
complete first layer and stop if any brim or support island lifts.
