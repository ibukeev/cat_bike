# Cat-head CAD project constraints

## Sources to read

- `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/OUTPUT_NAVIGATION.md`
- The current checkpoint named by that navigation file.
- `hardware/mechanical/CAT_HEAD_MOUNT_AND_SHELL_PHYSICAL_FIT_REVIEW_2026-07-28.md`
- `hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v05.json`

## Frozen baseline

- The current V10 Blender review is a frozen reference, not a production or
  print release.
- Preserve the accepted V3 fit body and exact ears.
- Preserve exact upper-head source meshes and eye geometry.
- Preserve lower-face/rear-cassette ownership and accepted reinforcement
  direction.
- Preserve C006 and the `CAT-HEAD-SHELL-ALUMINUM-V0.5` plate/rail workstream.
- Do not use cuts to accepted upper-head pieces to recover connector placement.

## Current connector defaults

Treat these as frozen defaults until the user explicitly changes them:

- two connector sets per translucent piece;
- plain rectangular flange tabs, currently `22 x 12 x 4 mm`;
- `0.3 mm` mating gap;
- one common `3.4 mm` M3 clearance axis per flange pair;
- M3 x 16 through-bolt, two 7 mm OD washers, and M3 nyloc per pair;
- at least `3.5 mm` modeled bore-to-edge material;
- at least `80 mm3` direct owner-root overlap;
- internal assembly access only;
- no wedge, trapezoid, broad base, bridge, clamp, boss, loose connector, or
  exterior protrusion without explicit approval.

The stability requirement controls placement: the two connector sets must sit
near opposite usable sides of the panel and maximize resistance to flapping.
Do not satisfy this requirement using only a center-to-center minimum. Measure
and report each connector's distance from its corresponding panel extreme and
the resulting usable span.

## Review and release holds

- Build and review one side before mirroring.
- Require user-selected faces, edges, or approved datum coordinates.
- Show all related owner pieces in context; never show unexplained floating
  connector geometry as the primary review.
- Require a dimensioned anchor view and an interior hardware-access section.
- Green/fixed flange geometry is not integrated until a production union is
  created and verified.
- No STL, G-code, slicer project, ASA recommendation, or print release without
  explicit user approval.

## Checkpoint contents

After each meaningful CAD change, record:

- current source and review files;
- selected object/sub-element anchor IDs and measurements;
- accepted decisions and dimensions;
- validation commands and results;
- rejected variants and why they failed physically;
- exact regeneration/export command;
- next user-selection or physical-review action.
