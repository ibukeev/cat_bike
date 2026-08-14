# Right B Hole and Access Review V1 Checkpoint — 2026-08-09

## Status

The isolated right-B common M3 hole, panel-side hardware, driver path, and
surface-open short-insert V2 are geometrically validated and received user
visual approval (`LGTM`) on 2026-08-09. Nothing is production-unioned,
mirrored, exported for fabrication, sliced, or print-released. Right-B is
released only to the controlled right-side A/B integration gate.

The standard M3 through-bolt hardware and the first recessed short-insert
pocket are preserved as rejected evidence. The latter exposed the same
trapped-pocket error in the previously approved right-A written contract, so
right A is now held for an equivalent surface-open cavity audit before any
integration.

## Current source and review files

- Frozen source review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-legacy-small-flange-removal-review-v1/CAT_HEAD_RIGHT_UPPER_HEAD_LEGACY_SMALL_FLANGE_REMOVAL_REVIEW_V1.FCStd`
  - SHA-256:
    `9d18d60dc7db24c97fd7931fdda24c87bea546309d68eef325f62bae9ad4731e`
- Numeric contract and validation:
  `config/right-b-hole-access-review-v1.json`
- Current isolated review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-b-hole-access-review-v1/CAT_HEAD_RIGHT_B_HOLE_ACCESS_REVIEW_V1.FCStd`
  - SHA-256:
    `77f9580b46ece419f51e11f21ef6f753443ee0963fe6b98d0bceab52fdd63936`
  - size: `8,090,740` bytes
  - FCStd ZIP validation: PASS
- Review evidence:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-b-hole-access-review-v1/review/`
  - `06-right-b-surface-open-cavity-and-seated-insert.png`
  - `07-right-b-insert-installation-sweep.png`
  - `08-right-b-surface-open-v2-owner-context.png`

The full-head opaque context remains the frozen V10 render at
`output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-full-head-context.png`.

## Approved anchors and frozen workstreams

- Approved B datum:
  `REVIEW_ONLY__ANCHOR_CANDIDATE_B__REAR` at
  `(91.929535, 217.525665, 201.177658) mm`.
- Approved B panel mating face:
  `PROPOSED__RIGHT_B__PANEL_TAB__LOCAL_RELIEF_1P9_SWEEP_V1.Face5`.
- Approved B head mating face:
  `PROPOSED__RIGHT_B__HEAD_TAB__V2_26MM_SHAPE_ONLY.Face6`.
- Approved local axes:
  - tangent `(-0.48370078, 0.84843820, 0.21490952)`
  - interior `(-0.81416923, -0.34606928, -0.46622366)`
  - across `(-0.32118839, -0.40048546, 0.85816628)`

Frozen and unchanged: right-A owner geometry and bore, approved B relief and
legacy projection removal, panel/head/ear topology references, left side,
lower-face and rear-cassette ownership, reinforcement, eyes, C006, and
`CAT-HEAD-SHELL-ALUMINUM-V0.5-M2`.

## Final isolated B proposal

- Common M3 clearance axis:
  `(85.9860995385, 214.999359536, 197.774225817) mm`.
- Axis change from the centered trial: exactly `+0.05 mm` along the approved
  B interior axis; tangent shift remains `0.0 mm`.
- Bore: `3.4 mm` diameter through both proposal tabs.
- Panel-side hardware:
  - M3 x 8 low-profile socket screw
  - 7 mm OD x 0.8 mm washer
  - 25-degree ball-end driver path along positive B interior
- Head-side hardware:
  - M3 x 3 mm short heat-set insert
  - assumed maximum insert body diameter: `4.20 mm`
  - surface-open printable cavity: `4.25 mm` diameter x `3.20 mm` deep
  - insert seated `0.20 mm` below the mating face
  - remaining exterior wall: `0.80 mm`
  - calculated M3 x 8 thread engagement: `2.70 mm`
  - calculated unused insert depth: `0.30 mm`

Current printable proposal objects:

- `PROPOSED__RIGHT_B__PANEL_TAB__M3_BORE_PLUS_0P05_INTERIOR_V1`
- `PROPOSED__RIGHT_B__HEAD_TAB__M3X3_SHORT_INSERT_SURFACE_OPEN_V2`

All `VALIDATION_ONLY__` cylinders, insert bodies, envelopes, and root
intersections are review evidence and are absent from printable output.

## Validation results

- Both drilled proposal tabs: closed valid solids, no self-intersection: PASS.
- Pair gap: `0.3000 mm`: PASS.
- Panel owner root: `94.72 mm3` versus `80.00 mm3`: PASS.
- Head owner root: `124.93 mm3` versus `80.00 mm3`: PASS.
- Full radius-`5.625 mm` cavity edge envelope contained: PASS.
- Effective cavity depth from mating face: `3.2000 mm`: PASS.
- Seated insert recess: `0.2000 mm`: PASS.
- Exterior wall: `0.8000 mm`: PASS.
- Cavity to modified upper head: `2.6099 mm`: PASS.
- Head-tab bounding box before/after cavity: identical: PASS.
- Head-tab result volume: `1195.34 mm3`.
- Insert body versus cavity/tab: zero interference; intentional seated bottom
  contact only: PASS.
- Insert mating-side installation sweep:
  - tab interference: zero
  - modified head clearance: `2.6342 mm`
  - ear clearance: `2.1898 mm`
- Panel washer:
  - translucent panel clearance: `0.4684 mm`
  - modified head clearance: `4.6243 mm`
- Low-profile screw head:
  - translucent panel clearance: `0.7177 mm`
  - ear clearance: `9.6499 mm`
- Positive-interior 25-degree ball-end driver:
  - translucent panel clearance: `1.8243 mm`
  - modified head clearance: `8.3439 mm`
  - ear clearance: `4.9903 mm`
  - drilled panel-tab clearance: `1.7389 mm`

## Rejected or unsafe variants

1. Centered B axis: rejected because exact face-touch radius-`5.2 mm`
   envelopes retained numerical panel/head protrusions of `0.0051` and
   `0.0137 mm3`. The minimal `+0.05 mm` interior correction passes.
2. Standard M3 x 16 through-bolt, washers, and M3 nyloc: hardware bodies fit,
   but the 8 mm thin socket intersects the modified head by `1.3190 mm3` at
   engagement and `137.3681 mm3` along its approach.
3. Negative-interior 25-degree driver path: intersects the panel by
   `28.0016 mm3` and ear by `7.1733 mm3`.
4. `PROPOSED__RIGHT_B__HEAD_TAB__M3X3_SHORT_INSERT_RECESSED_V1`: rejected.
   Its 3.0 mm pocket begins 0.2 mm behind the mating surface and therefore
   leaves a 0.2 mm ring with only a 3.4 mm opening. A 4.20 mm insert cannot
   enter this trapped internal pocket.
5. The right-A written cavity contract describes the same trapped-pocket
   construction. Its earlier visual approval remains recorded, but production
   use is now blocked until A receives the surface-open correction and review.

## Exact controlled recreation

There is no arbitrary Python, macro, or headless command. Recreate in the
official FreeCAD GUI using only the allowlisted operations:

1. Open the frozen legacy-small-flange-removal source above and save a separate
   right-B review copy.
2. Insert copies of the approved B panel relief and B head tab.
3. Build one 3.4 mm bore cylinder on the final common axis and cut only those
   two proposal copies.
4. Insert a fresh copy of the drilled B head tab.
5. Create a radius-`2.125 mm`, height-`3.25 mm` cavity cutter at
   `(87.062080645, 216.340985827, 194.899368779) mm`.
6. Rotate that cutter in order:
   - X `25.017324398 deg`
   - Y `-18.734808918 deg`
   - Z `120.714694760 deg`
7. Cut the drilled head-tab copy and name the result
   `PROPOSED__RIGHT_B__HEAD_TAB__M3X3_SHORT_INSERT_SURFACE_OPEN_V2`.
   The extra 0.05 mm cutter length is only a mating-face Boolean overshoot;
   the effective cavity depth inside the 4 mm tab is exactly 3.20 mm.
8. Recreate the validation-only edge envelope, insert body, insertion sweep,
   owner-root common, hardware, and tool-path objects from the numeric contract
   and rerun every result above.

## Next physical review

1. Open the current right-B FCStd. Its default view shows the final surface-open
   V2 head tab selected with the panel, modified upper head, and ear in context.
2. Review `06-right-b-surface-open-cavity-and-seated-insert.png`: the blue
   validation insert must be visibly reachable through the large mating-face
   opening.
3. Review `07-right-b-insert-installation-sweep.png`: the highlighted sweep
   is installation evidence, not printable geometry.
4. Review `08-right-b-surface-open-v2-owner-context.png` and rotate the FCStd
   to confirm no visible exterior change.
5. Right-A V4 and Right-B V2 are now both visually approved. Build the
   exact-orientation ASA insert coupon and controlled right-side A/B owner
   integration next; mirroring and print release remain held.
