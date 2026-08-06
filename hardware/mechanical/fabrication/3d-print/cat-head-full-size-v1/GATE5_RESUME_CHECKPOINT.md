# Gate 5 Resume Checkpoint

Last updated: 2026-07-19

This is the restart point for the full-scale cat-head model. Gate 5 is a
review candidate, not yet cleared for production printing.

## Current review files

- `output/10-design-gates/gate5-ribs-and-joints/gate5-internal-flange-tabs-review.blend` —
  primary visual review file.
- `output/10-design-gates/gate5-ribs-and-joints/gate5-internal-flange-tabs-review.stl` —
  combined geometry review; print the seven files in `shells/`, not this file.
- `output/10-design-gates/gate5-ribs-and-joints/gate5-validation-report.json` — final
  generated-check record.

Regenerate all Gate 5 outputs with:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate5_ribs_and_joints.py
~~~

## Current accepted design decisions

1. The head is seven printed shell sections. `joiners/` is intentionally empty.
2. Every source-section seam has matching, plain rectangular flange tabs on
   both shells: 8 mm deep, 3.2 mm thick, M3.4 through-holes, 0.3 mm face gap.
   Each broad body reaches the shell through two narrow 2.0 x 1.2 mm root webs
   with 0.3 mm boolean overlap. The rear-base interfaces instead use four
   continuous shell-side rails.
3. Use internal M3 through-bolts, washers, and loose M3 nyloc nuts. There are
   no captive-nut pockets, dowels, receiver-only tabs, or exterior holes.
4. Adjacent source panels are not always coplanar. Their tab pairs use the
   shared inner bisector, rather than an exact panel-parallel bolt axis, so
   neither tab protrudes through the exterior. The rear-base rails and their
   six through-bores use the sloped rear-frame plane so each bolt axis remains
   parallel to the corresponding shell surface. The generator requires at
   least 3.0 mm exterior recess for ordinary broad seam tabs, 8.0 mm for broad
   ear tabs, and 0.35 mm for their narrow embedded roots. The enclosed
   rear-base rails keep their separate 0.25 mm recess.
5. `MANQ006` and `MANQ007` are split on the centerline and carried by the two
   lower-face shells, replacing the large rear opaque-panel section. The
   separate `rear_base` is a 60 mm-top / 120 mm-bottom closed trapezoidal frame
   with a 20 mm structural surround and 18 mm of depth extending inward along
   the sloped upper-head rear plane. The tapered opening is approximately
   20 mm top width, 80 mm bottom width, and 39 mm high. It provides wiring,
   inspection, and M3 nut access but is not a hand-service opening. Four
   continuous concealed shell-side rails attach it to all four adjacent
   shells: one along each upper-head side edge and one along each lower-face
   rear edge. The upper rails carry two M3 paths each; the lower rails carry
   one each. Rails stop 1.8 mm short at their ends to prevent printed-part
   collisions, and bores through the continuous rear-frame surround terminate
   at the opening without an exterior hole. There are zero isolated planks or
   tabs on the inside of the opening. The lower rear panels
   remain continuous: the lower service cut and center spine are removed, and
   the MANQ006/MANQ007 center seams have hidden flange modules. The old
   rectangular rim and lower tie rails are removed. Its final cover/backplate
   attachment is deferred.
6. Every source-panel connection internal to `left_lower_face`,
   `left_upper_head`, `right_lower_face`, and `right_upper_head` has two
   light, shell-integrated triangular gussets, one on each panel side. There
   are 110 in total: 32 / 24 / 30 / 24 by shell and 6,065.53 mm total length.
   The 55 main gussets are 2.5 mm foot by 3 mm high, 0.5 mm inboard, with 6 mm
   endpoint clearance and 1.3 mm exterior recess. The 55 compact opposite-side
   gussets are 1.2 mm by 1.5 mm, 0.75 mm inboard, 8 mm clear of endpoints, and
   retain 0.4 mm exterior skin.
7. Gussets are intentionally excluded from all inter-shell flange seams,
   exterior edges, rear-base geometry, and both ears. The future
   semi-transparent-panel attachment strategy may add its own reinforcement
   where needed.
8. Thirty-eight triangulated internal truss hubs connect every shared **main**
   gusset endpoint (11 / 8 / 10 / 9 by target shell). Each hub overlaps the
   complete triangular end section of every incident main gusset by 3 mm and
   retains the same 1.3 mm exterior recess. Compact opposite-side gussets stop
   outside each hub zone. The hub graph includes degree-two through joints and
   degree-three/four branches, but excludes flange seams, outer edges,
   rear-base geometry, and ears.

## Validation snapshot

- Seven closed, manifold shell STLs. Recessed gussets/hubs are closed,
  overlapping internal volumes for slicer union, not fragile CAD-boolean joins.
- 16 paired source-seam flange modules plus four continuous rear connector
  rails and 24 internal M3 bolt paths. Six of those paths attach the deep rear
  frame to all four adjacent body shells.
- The rear-frame opening contains zero isolated tabs; `rear_base.stl` is one
  closed manifold component with six usable internal bores.
- 110 integral triangular gussets: 55 main and 55 compact opposite-side;
  no separate printed reinforcement parts.
- 38 integral triangulated hubs joining every shared internal main-gusset
  endpoint.
- Broad ordinary tabs clear both adjacent exterior planes by at least 3.0 mm;
  broad ear tabs clear by at least 8.0 mm. Every source-seam flange uses two
  compact shell roots recessed at least 0.35 mm. No exterior fastener holes.
- All parts fit the conservative 240 × 200 × 210 mm printer envelope.
- Estimated mesh-volume ASA shell mass: 432.53 g.
- Guardrail: every generated shell must retain at least 90% of its Gate 3
  baseline volume. This catches boolean failures that manifold checks alone
  can miss.

## Important rejected variant

Do **not** set the triangular-gusset endpoint clearance to `0.0`. An earlier
zero-clearance reinforcement trial at a seam vertex removed most of
`left_lower_face` while still leaving a formally manifold mesh. The current
6 mm endpoint clearance is intentional and validated. A two-gusset-per-edge
variant was also rejected: in tight faceted areas the paired wedges overlapped
and produced non-manifold Boolean results. The accepted design is a full-size
main triangular gusset plus a compact opposing-side triangular gusset per
eligible internal connection. The 38 truss hubs join the main-gusset graph;
the compact gussets stop clear of hub geometry rather than merely touching it.

## Next review / prototype tasks

1. Review the current `.blend` exterior and interior, especially the four
   continuous rear connector rails, access to their six concealed bolt paths,
   the reduced service opening, the 110 internal triangular
   gussets on both panel sides, and the 38 connected main-gusset truss hubs.
2. Print full-size coupons for a matching tab pair and a rear-frame rail path
   with the intended M3 screws, washers, and nyloc nuts; confirm tool access,
   clearance, and the likely M3 x 25–30 mm rear screw length.
3. Do a mechanical load test before deciding whether to add dedicated eye
   reinforcement or rear-base/transparent-panel reinforcement.
4. Keep the rear connector flange, backplate/rail load path, lighting mounts,
   cover/gasket, ventilation, and drains deferred.
