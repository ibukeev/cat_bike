# Gate 2 Topology Approval

Approved: 2026-07-15

The approved section topology contains seven structural pieces:

1. Right upper head
2. Left upper head
3. Right lower face
4. Left lower face
5. Rear base/backplate-interface section (`MANQ006` and `MANQ007` only)
6. Right ear
7. Left ear

The approved source is `config/gate2-section-layout.json`. Every section passed
the 240 × 200 × 210 mm orientation search as a face-level surface. Purple glow
panels and red mouth-opening facets are excluded from structural shells.

`QUAD002` and `QUAD004` remain opaque eye-adjacent surface islands. They must be
joined to their respective lower shells by internal rear frame ribs during
solid-shell modeling.

Post-review correction: the large center-bottom `MANQ008` surface is divided
on the centerline into `MANQ008_RIGHT` and `MANQ008_LEFT`. Those halves belong
to the corresponding lower-face shells and must be tied into them by internal
frame ribs. They are not part of the rear-base/backplate-interface section.

Gate 2 approval freezes section ownership and seam routing. It does not approve
wall thickness, flanges, keys, fastener placement, or print orientation after
those features are added.
