# Gate 5 Internal Flange Tabs and Panel Gussets

Status: generated and automatically validated. This is a full-size joint-layout
candidate, not a production-print release. Physical fit and tool-access coupons
are required before printing the complete shell set.

## Joint system

Gate 5 now exports only seven ASA shell parts: four body sections, the rear
base, and two ears. It does not export separate printed joiners, alignment
dowels, or exterior reinforcement parts.

- Sixteen source-seam modules have pairs of matching, plain rectangular
  shell-integrated flange tabs: the same 8 mm-deep by 3.2 mm-thick tab on each
  shell. Each broad tab body attaches through two compact 2.0 mm-long by
  1.2 mm-thick root webs rather than extending its whole face to the exterior
  seam. The roots retain at least 0.35 mm exterior recess and overlap the tab
  by 0.3 mm for a reliable manifold union. The rear base uses a separate
  continuous-rail strategy described below.
- A 0.3 mm face gap separates the mating tabs. At an angled source-panel
  seam the M3 axis follows the shared interior bisector rather than either
  panel exactly. The rear-base connector rails instead use the sloped
  rear-frame plane, keeping each bolt axis parallel to the adjacent shell
  surface and all geometry inside the head. Ordinary broad source-seam tabs
  are at least 3.0 mm behind both adjacent exterior planes. The ear broad tabs
  use an 8.0 mm recess so they are not visible at the translucent ear-root
  opening. The enclosed rear-base rails retain their separate 0.25 mm recess.
- Both tabs have the same M3.4 through-hole. Use a normal M3 through-bolt,
  washers, and a loose M3 nyloc nut; there is no receiver-only geometry,
  captive-nut pocket, alignment dowel, or printed joiner. Screw heads, nuts,
  and tool access are entirely inside the head; the exterior has no fastener
  holes.
- Every source-panel connection internal to `left_lower_face`,
  `left_upper_head`, `right_lower_face`, and `right_upper_head` carries two
  shell-integrated triangular gussets, one on each adjacent panel face. The
  main gusset is 2.5 mm foot width by 3 mm height, inset 0.5 mm from its seam
  with 6 mm endpoint clearances and at least 1.3 mm exterior skin. The compact
  opposing-side gusset is 1.2 mm by 1.5 mm, inset 0.75 mm, with 8 mm endpoint
  clearances and at least 0.4 mm exterior skin. There are 110 gussets over
  6,065.53 mm total length (32 / 24 / 30 / 24 by shell).
- These gussets deliberately do not cross the inter-shell seams that already
  have flange tabs, and they are not generated on outer edges, the rear base,
  or either ear. This leaves the future semi-transparent-panel connection
  strategy independent.
- Thirty-eight triangulated internal truss hubs bridge every shared **main**
  gusset endpoint: 11 / 8 / 10 / 9 by shell. Each hub overlaps the full
  triangular end section of every connected main gusset by 3 mm, including
  degree-two through joints and degree-three/four branch joints, while
  retaining the same 0.8 mm exterior recess. Compact opposing-side gussets
  stop outside the hub zone to avoid crowding tight facets.
- `MANQ006` and `MANQ007`, the rear-facing opaque facets, are center-split and
  carried by the left and right lower-face shells. They create the rear panels
  without a large separate back frame.
- `rear_base` is a closed, deep trapezoidal frame on the same sloped plane as
  the rear edges of `left_upper_head` and `right_upper_head`: 60 mm across its
  upper edge, 120 mm across its lower edge, a 20 mm structural surround, and
  18 mm of depth extending inward into the head. This deliberately reduces the
  central opening while making the frame a load-spreading ring rather than a
  thin skin.
- The remaining tapered access opening is approximately 20 mm wide at the top,
  80 mm wide at the bottom, and 39 mm high. It supports wiring, visual
  inspection, and loading the six M3 nuts; it is intentionally not sized for a
  hand. Until the dedicated service cover is designed, larger service requires
  removing a major head section.
- Four continuous concealed connector rails attach that frame to all four
  adjacent shells: one along each sloped upper-head side edge and one along
  each lower-face rear edge. The upper rails each carry two M3 paths and the
  lower rails each carry one. The rails stop 1.8 mm short of their endpoints to
  avoid collisions between separately printed shells, while the deep rear
  frame and six clamped bolts complete the load path. Matching bores pass
  through the rear-frame surround and terminate at the access opening; no
  isolated tab or plank remains along the opening and no bolt hole reaches the
  exterior. `MANQ006` and `MANQ007` remain
  continuous; the former lower service cut and center spine are removed, while
  their center seams retain hidden flange modules so the lower shells are fully
  joined.
- The compact rear frame's final cover/backplate attachment remains deferred;
  this revision adds no exterior fasteners.

## Hardware for this gate

- 24 black stainless M3 socket-head screws.
- 24 M3 nyloc nuts and 48 M3 washers (one on each side of each tab pair).
- No dowel pins in this flange-tab revision.
- Medium-strength removable threadlocker only on metal-to-metal threads after
  physical validation.

Use a full-size coupon with the selected screw head, washer, and nyloc nut to
choose the final M3 length. The current starting assumption is M3 x 10–12 mm
for ordinary body tabs, M3 x 12 mm at the ears, and M3 x 25–30 mm for the
longer rear-frame rail paths. Measure the printed rear interface before buying
the final rear screws.

## Assembly order

1. Print the seven files in `shells/`; `joiners/` is intentionally empty.
2. Mate the lower-center seam, then add M3 screws, washers, and loose nyloc
   nuts from inside.
3. Seat the deep rear-base frame against the four continuous shell rails and
   install its six internal M3 through-bolts: two into each upper shell and one
   into each lower shell. Load the nuts through the reduced opening. Its final
   cover/backplate attachment is deliberately deferred.
4. Mate the upper-center seam, then join each upper shell to its lower shell.
5. Fit the ears last with their two internal screws per ear root.
6. Tighten progressively after all tabs are seated; do not torque a seam in
   isolation.

The modeled access direction is internal, but actual driver reach, screw-head
clearance, and nut loading still require the 100 mm assembly and full-size
coupon test.

## Automated result

- Seven closed, manifold shell meshes. Each print part is exported as one STL;
  recessed gussets and hubs are closed overlapping internal volumes that the
  slicer unions, avoiding a fragile CAD boolean at multi-panel vertex fans.
- Sixteen paired matching-rectangle source-seam flange modules plus four
  continuous rear connector rails. Together they provide 24 internal M3
  through-bolt paths and use 24 loose M3 nyloc nuts; six of those paths attach
  the rear frame to all four adjacent head shells.
- The rear opening contains zero isolated connector tabs. The rear-base STL is
  one closed manifold component with six usable internal bores.
- Every tab pair is recessed behind both adjacent exterior planes; no exterior
  fastener holes are generated. Ordinary broad tab bodies clear the exterior
  by at least 3.0 mm, ear tab bodies by 8.0 mm, and their two narrow attachment
  roots by at least 0.35 mm.
- 110 shell-integrated triangular gussets reinforce both sides of every
  eligible internal source-panel connection in the four body shells: 55 main
  and 55 compact opposing-side gussets. 38 full-overlap triangulated hubs
  connect every shared main-gusset endpoint. There are zero separate joiners
  and zero alignment dowels.
- Every shell fits the conservative 240 x 200 x 210 mm printer envelope.
- Estimated mesh-volume ASA mass for these seven structural shells: **432.53 g**.

The mass excludes panels, hardware, lighting, wiring, rear cover, connector
flange, backplate, rails, and bike-side mount.

## Deferred work

- Dedicated eye-island reinforcement and a mechanical coupon/load test of the
  new internal panel gussets.
- Rear bike connector flange, aluminum backplate, and rail load path.
- LED cassette attachment points, rear cover/gasket, ventilation, and drains.
