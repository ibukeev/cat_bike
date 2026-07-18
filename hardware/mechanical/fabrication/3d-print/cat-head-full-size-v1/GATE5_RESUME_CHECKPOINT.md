# Gate 5 Resume Checkpoint

Last updated: 2026-07-18

This is the restart point for the full-scale cat-head model. Gate 5 is a
review candidate, not yet cleared for production printing.

## Current review files

- `output/gate5-ribs-and-joints/gate5-internal-flange-tabs-review.blend` —
  primary visual review file.
- `output/gate5-ribs-and-joints/gate5-internal-flange-tabs-review.stl` —
  combined geometry review; print the seven files in `shells/`, not this file.
- `output/gate5-ribs-and-joints/gate5-validation-report.json` — final
  generated-check record.

Regenerate all Gate 5 outputs with:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate5_ribs_and_joints.py
~~~

## Current accepted design decisions

1. The head is seven printed shell sections. `joiners/` is intentionally empty.
2. Every structural seam has matching, plain rectangular flange tabs on both
   shells: 8 mm deep, 3.2 mm thick, M3.4 through-holes, 0.3 mm face gap.
3. Use internal M3 through-bolts, washers, and loose M3 nyloc nuts. There are
   no captive-nut pockets, dowels, receiver-only tabs, or exterior holes.
4. Adjacent panels are not always coplanar. Tab pairs therefore use the shared
   inner bisector, rather than an exact panel-parallel bolt axis, so neither
   tab protrudes through the exterior. The generator requires at least 0.25 mm
   clearance behind both source-face exterior planes.
5. Every source-panel connection internal to `left_lower_face`,
   `left_upper_head`, `right_lower_face`, and `right_upper_head` has one
   light, shell-integrated triangular gusset. There are 51 in total: 14 / 12 /
   13 / 12 by shell and 2,874.54 mm total length. Each gusset has a 2.5 mm
   foot width, 3 mm height, 0.5 mm inboard edge placement, 6 mm endpoint
   clearance, and at least 0.8 mm exterior recess.
6. Gussets are intentionally excluded from all inter-shell flange seams,
   exterior edges, rear-base geometry, and both ears. The future
   semi-transparent-panel attachment strategy may add its own reinforcement
   where needed.

## Validation snapshot

- Seven closed, manifold, single-component shell solids.
- 18 paired flange-tab modules and 20 internal M3 bolt paths.
- 51 integral triangular gussets; no separate printed reinforcement parts.
- Tabs and gussets clear the exterior skin; no exterior fastener holes.
- All parts fit the conservative 240 × 200 × 210 mm printer envelope.
- Estimated ASA shell mass: 367.82 g.
- Guardrail: every generated shell must retain at least 90% of its Gate 3
  baseline volume. This catches boolean failures that manifold checks alone
  can miss.

## Important rejected variant

Do **not** set the triangular-gusset endpoint clearance to `0.0`. An earlier
zero-clearance reinforcement trial at a seam vertex removed most of
`left_lower_face` while still leaving a formally manifold mesh. The current
6 mm endpoint clearance is intentional and validated. A two-gusset-per-edge
variant was also rejected: in tight faceted areas the paired wedges overlapped
and produced non-manifold Boolean results. The accepted design is one
low-profile triangular gusset per eligible internal connection.

## Next review / prototype tasks

1. Review the current `.blend` exterior and interior, especially tab access
   and the 51 internal triangular gussets.
2. Print full-size coupons for a matching tab pair with the intended M3 screw,
   washers, and nyloc nut; confirm tool access and clearance.
3. Do a mechanical load test before deciding whether to add dedicated eye
   reinforcement or rear-base/transparent-panel reinforcement.
4. Keep the rear connector flange, backplate/rail load path, lighting mounts,
   cover/gasket, ventilation, and drains deferred.
