# Right A/B Under-Ear-Opening Print Orientation Review V2 Checkpoint — 2026-08-14

## Status

The user visually approved the exact displayed V2 placement on 2026-08-14.
The user also corrected its semantic description: the under-ear opening is not
bed-facing. Therefore the historical filename remains only as artifact identity;
it must not be interpreted as the approved bed datum.

No geometry changed in this orientation review. A later isolated A/B coupon 3MF
was created at output/40-prototypes/right-ab-short-insert-coupon-v1/; no
full-shell STL, G-code, or ASA shell release was created.

## Frozen source and ownership

- FreeCAD:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-owner-integration-review-v1/CAT_HEAD_RIGHT_AB_OWNER_INTEGRATION_REVIEW_V1.FCStd`
- Object: `PROPOSED__RIGHT_UPPER_HEAD_C001__A_B_INTEGRATED_V1`
- Source SHA-256:
  `e9974661a5a0a71a12bcb6ab6d0d66ceae354fd8744486ff08ce72e20cf0376c`
- Source approval: user `LGTM`, 2026-08-09.
- Source topology: valid, closed, self-intersection-free, one solid.
- Placement semantic: exact displayed V2 quaternion approved; the under-ear
  opening is explicitly not bed-facing.

Only the isolated review placement changes. Head and eye geometry, A/B insert
cavities, ears, lower face, rear cassette, reinforcement, C006, and
`CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` remain frozen.

## Numeric design contract

- Selected-contact-plane source outward normal:
  `[0.998906016, -0.036057804, 0.029776497]`.
- Optimized yaw around that fixed bed normal: `96.5 deg`.
- Exact rotation quaternion, WXYZ:
  `[0.463786364, -0.517753959, 0.496808916, 0.519628584]`.
- Conservative printer envelope: `240 x 200 x 210 mm`.
- Required XY reserve on every side: at least `10 mm`.
- Oriented XYZ envelope: `203.498 x 163.628 x 155.848 mm`.
- Reserve per side: `18.251 mm` in X and `18.186 mm` in Y.
- True bed-contact area: `3,437.37 mm2`.
- Estimated support-facing area at the 45-degree threshold: `3,457.07 mm2`.
- A/B insert axes from the layer normal: `83.899/57.421 deg`.
- Geometry change: `0.0 mm`.

The exact displayed placement fits the conservative envelope and exceeds the
reserve gate. Yaw was optimized only within that frozen orientation.

## Current review outputs

- Blender review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-under-ear-opening-print-orientation-review-v2/right-ab-under-ear-opening-print-orientation-review-v2.blend`
- Numeric validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-under-ear-opening-print-orientation-review-v2/orientation-validation-v2.json`
- Eleven-candidate audit retained for traceability:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-under-ear-opening-print-orientation-review-v2/orientation-candidate-ranking-v2.json`
- Evidence renders:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-under-ear-opening-print-orientation-review-v2/review/`
- Contract:
  `config/right-ab-under-ear-opening-print-orientation-review-v2.json`

The regenerated scene measured `203.4978 x 163.6278 x 155.8483 mm`, matching
the contract within `0.01 mm`: PASS.

## Rejected or unsafe variants

- V1 remains rejected because the user preferred the displayed V2 placement.
- The claim that V2 places the under-ear opening on the bed is rejected.
- Yaw variants violating `10 mm` reserve on any XY side remain rejected.
- No geometry was recut to force an orientation.
- This review does not claim PrusaSlicer support, brim, collision, or actual-bed
  acceptance; those remain independent gates.

## Exact regeneration

1. Open the frozen FreeCAD source above.
2. Export only `PROPOSED__RIGHT_UPPER_HEAD_C001__A_B_INTEGRATED_V1` as
   `/tmp/right_ab_c001_hs04_orientation_audit.stl` with no placement change.
3. From the repository root run:

   ```bash
   blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_ab_print_orientation_review_v1.py -- --input-stl /tmp/right_ab_c001_hs04_orientation_audit.stl --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/right-ab-under-ear-opening-print-orientation-review-v2.json --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-under-ear-opening-print-orientation-review-v2
   ```

## Next physical review

The exact isolated A/B coupon is now available as a two-object editable 3MF.
Its initial displayed-V2 orientation has zero planar bed contact, so the user
will rotate both objects and save the preferred PrusaSlicer project. Then
PrusaSlicer must confirm layer continuity, supports, brim/adhesion, collisions,
and actual bed clearance. Structural shell printing remains held.
