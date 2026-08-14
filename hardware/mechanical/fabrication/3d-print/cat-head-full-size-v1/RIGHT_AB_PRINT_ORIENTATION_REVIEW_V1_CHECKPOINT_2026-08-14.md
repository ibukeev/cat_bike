# Right A/B Print Orientation Review V1 Checkpoint — 2026-08-14

## Status

**Rejected and superseded on 2026-08-14.** The user prints this owner with the
under-ear opening on the bed. Use the V2 checkpoint and review instead:
`RIGHT_AB_UNDER_EAR_OPENING_PRINT_ORIENTATION_REVIEW_V2_CHECKPOINT_2026-08-14.md`.

This historical isolated, zero-geometry-change proposal was generated for the
approved right upper-head C001 A/B owner. The numeric audit checks the real
integrated solid against the conservative `240 x 200 x 210 mm` MK4S envelope
and the project requirement for at least `10 mm` XY reserve on every side.

This is not yet user-approved. No production STL, 3MF, G-code, slicer project,
coupon, or ASA shell print release was created.

## Frozen source

- FreeCAD:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-owner-integration-review-v1/CAT_HEAD_RIGHT_AB_OWNER_INTEGRATION_REVIEW_V1.FCStd`
- Object: `PROPOSED__RIGHT_UPPER_HEAD_C001__A_B_INTEGRATED_V1`
- Source SHA-256:
  `e9974661a5a0a71a12bcb6ab6d0d66ceae354fd8744486ff08ce72e20cf0376c`
- Source approval: user `LGTM`, 2026-08-09.
- Source topology: valid, closed, self-intersection-free, one solid.

The audit changes placement only inside an isolated review scene. Geometry,
A/B cavity placement, ears, eyes, lower face, rear cassette, reinforcement,
C006, and `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` remain frozen.

## Selected orientation proposal

- Source outward face normal placed toward the bed:
  `[0.185925633, 0.551883638, 0.812930584]`.
- Optimized bed-plane yaw: `138.5 deg`.
- Exact rotation quaternion, WXYZ:
  `[0.108354397, -0.603910148, -0.736042023, 0.285996497]`.
- Oriented XYZ envelope: `194.385 x 172.420 x 164.737 mm`.
- Reserve per side: `22.808 mm` in X and `13.790 mm` in Y.
- True bed-contact area: `2,253.51 mm2`.
- Estimated support-facing area at the 45-degree threshold: `1,213.31 mm2`.
- A insert axis from layer normal: `62.385 deg`.
- B insert axis from layer normal: `39.288 deg`.

This candidate has the lowest support-facing/contact ratio among the stable
candidate facets that satisfy the full `10 mm` per-side reserve. Ten other
true-contact candidates were evaluated; the retained candidate is a proposal,
not a production approval.

## Current review outputs

- Blender review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-print-orientation-review-v1/right-ab-print-orientation-review-v1.blend`
- Numeric validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-print-orientation-review-v1/orientation-validation-v1.json`
- Candidate ranking:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-print-orientation-review-v1/orientation-candidate-ranking-v1.json`
- Evidence renders:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-print-orientation-review-v1/review/`
- Contract:
  `config/right-ab-print-orientation-review-v1.json`

The regenerated scene measured `194.3847 x 172.4200 x 164.7370 mm`, matching
the contract within `0.01 mm`: PASS.

## Rejected or unsafe paths

- Large faces that were not the true lowest plane after rotation were rejected.
- Any orientation with less than `10 mm` reserve on one or more XY sides was
  rejected even if it fit the nominal bed.
- No orientation was selected solely because an insert axis looked favorable;
  bed contact, support exposure, height, and full footprint were evaluated.
- The review does not claim PrusaSlicer support/brim acceptance. That remains a
  later independent gate.

## Exact regeneration

1. Open the frozen FreeCAD source above.
2. Export only `PROPOSED__RIGHT_UPPER_HEAD_C001__A_B_INTEGRATED_V1` as
   `/tmp/right_ab_c001_hs04_orientation_audit.stl` with no placement change.
3. From the repository root run:

   ```bash
   blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_ab_print_orientation_review_v1.py -- --input-stl /tmp/right_ab_c001_hs04_orientation_audit.stl --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/right-ab-print-orientation-review-v1.json --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-print-orientation-review-v1
   ```

## Next physical review

Open `right-ab-print-orientation-review-v1.blend` and check:

1. the blue C001 owner rests on the bed rather than floating or intersecting it;
2. the complete top footprint stays inside the orange `10 mm` reserve boundary;
3. the selected bed face is a credible stable printing face;
4. no A/B flange or cavity is accidentally omitted from the owner;
5. explicitly approve or reject this orientation.

Only after approval may HS-04 generate and slice the exact-orientation A/B ASA
insert coupon. Structural shell printing remains held.
