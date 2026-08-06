# Gate 7 100 mm Test Print

This package is a uniformly scaled visual and assembly-fit test of the current
Gate 7 cat head. The assembled head is 100 mm tall, or 30.303% of full size.

Generate it with:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate7_small_test_print.py
~~~

Review
`output/10-design-gates/gate7-small-test-print-100mm/cat_head_100mm_test_print_review.blend`
before slicing. Print the individual files in `shells/`, `glow-inserts/`, and
`eye-modules/`. The combined `cat_head_100mm_visual_assembly.stl` is a visual
reference, not the recommended multi-part print file.

Suggested first test:

1. Print the seven shell pieces in opaque material.
2. Print the seven glow inserts and two eye diffusers in translucent material.
3. Print eye buckets and rear caps in opaque material, or omit the rear caps
   for the first silhouette test.
4. Assemble with tiny spots of removable glue, thin double-sided tape, or
   temporary wire pins.

This is a uniform scale model. M3 and M2.5 holes are only about 30.3% of their
full-size diameter and do not accept the intended hardware. Walls, ribs, roots,
and retainers are also scaled; use slicer thin-wall support and preferably a
0.25 mm nozzle. With a 0.4 mm nozzle, inspect the preview carefully and expect
some internal connector details to merge or disappear. Use the full-size
coupons for actual fastener and strength validation.

`test-print-manifest.json` records every part's topology and the final package
acceptance checks so this export can be regenerated after another laptop or
Codex restart. It now also refuses the export if Gate 6 reports an unattached
eye-mount tab or if any shell contains a component separated from the rest by
an empty horizontal layer interval.

The 2026-07-20 regression check was prompted by PrusaSlicer reporting an empty
layer from 36.4 to 37.0 mm in `small_left_lower_face.stl`. The cause was a
floating outer eye-mount tab. After adding the hidden attachment bridges, both
lower-face STLs slice to G-code in PrusaSlicer 2.7.4 without an empty-layer
warning. Normal orientation-dependent support, bed-adhesion, and thin-feature
warnings may still appear and should be handled in the print profile.
