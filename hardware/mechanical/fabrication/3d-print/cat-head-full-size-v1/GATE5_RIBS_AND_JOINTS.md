# Gate 5 Internal Flange Tabs and Panel Gussets

Status: generated and automatically validated. This is a full-size joint-layout
candidate, not a production-print release. Physical fit and tool-access coupons
are required before printing the complete shell set.

## Joint system

Gate 5 now exports only seven ASA shell parts: four body sections, the rear
base, and two ears. It does not export separate printed joiners, alignment
dowels, or exterior reinforcement parts.

- Each of the 18 seam modules has a pair of matching, plain rectangular
  shell-integrated flange tabs: the same 8 mm-deep by 3.2 mm-thick tab on each
  shell, with 1.2 mm of overlap at its shell attachment.
- A 0.3 mm face gap separates the mating tabs. At an angled seam the M3 axis
  follows the shared interior bisector rather than either panel exactly: that
  keeps both matching tabs entirely inside the head. Every tab pair has at
  least 0.25 mm of clearance behind both adjacent exterior face planes.
- Both tabs have the same M3.4 through-hole. Use a normal M3 through-bolt,
  washers, and a loose M3 nyloc nut; there is no receiver-only geometry,
  captive-nut pocket, alignment dowel, or printed joiner. Screw heads, nuts,
  and tool access are entirely inside the head; the exterior has no fastener
  holes.
- Every source-panel connection internal to `left_lower_face`,
  `left_upper_head`, `right_lower_face`, and `right_upper_head` carries one
  shell-integrated triangular gusset: 2.5 mm foot width by 3 mm height. The
  gusset is inset 0.5 mm from the shared panel edge, has 6 mm endpoint
  clearances, and retains at least 0.8 mm of exterior skin. There are 51
  gussets over 2,874.54 mm total length (14 / 12 / 13 / 12 by shell).
- These gussets deliberately do not cross the inter-shell seams that already
  have flange tabs, and they are not generated on outer edges, the rear base,
  or either ear. This leaves the future semi-transparent-panel connection
  strategy independent.
- The lower-shell eye islands become connected through nearby required flange
  tabs, but this is not a dedicated eye-reinforcement solution. Do not treat
  it as the final reinforcement design; that will be revisited from your next
  direction.
- The rear base retains its 100 x 80 mm service opening, 10 x 10 mm internal
  rim, and lower tie rails for access and local rear stiffness.

## Hardware for this gate

- 20 black stainless M3 socket-head screws.
- 20 M3 nyloc nuts and 40 M3 washers (one on each side of each tab pair).
- No dowel pins in this flange-tab revision.
- Medium-strength removable threadlocker only on metal-to-metal threads after
  physical validation.

Use a full-size coupon with the selected screw head, washer, and nyloc nut to choose
the final M3 length. The current starting assumption is M3 x 10–12 mm for body
tabs and M3 x 12 mm at the ears.

## Assembly order

1. Print the seven files in `shells/`; `joiners/` is intentionally empty.
2. Mate the lower-center seam, then add M3 screws, washers, and loose nyloc
   nuts from inside.
3. Fit the rear base from the back and use the service opening for its hidden
   fasteners.
4. Mate the upper-center seam, then join each upper shell to its lower shell.
5. Fit the ears last with their two internal screws per ear root.
6. Tighten progressively after all tabs are seated; do not torque a seam in
   isolation.

The modeled access direction is internal, but actual driver reach, screw-head
clearance, and nut loading still require the 100 mm assembly and full-size
coupon test.

## Automated result

- Seven closed, manifold shell meshes, each a single connected solid.
- 18 paired matching-rectangle flange-tab modules with 20 internal M3
  through-bolt paths and 20 loose M3 nyloc nuts.
- Every tab pair is recessed behind both adjacent exterior planes; no exterior
  fastener holes are generated.
- 51 shell-integrated triangular gussets reinforce every eligible internal
  source-panel connection in the four body shells. There are zero separate
  joiners and zero alignment dowels.
- Every shell fits the conservative 240 x 200 x 210 mm printer envelope.
- Estimated printed ASA mass for these seven structural shells: **367.82 g**.

The mass excludes panels, hardware, lighting, wiring, rear cover, connector
flange, backplate, rails, and bike-side mount.

## Deferred work

- Dedicated eye-island reinforcement and a mechanical coupon/load test of the
  new internal panel gussets.
- Rear bike connector flange, aluminum backplate, and rail load path.
- LED cassette attachment points, rear cover/gasket, ventilation, and drains.
