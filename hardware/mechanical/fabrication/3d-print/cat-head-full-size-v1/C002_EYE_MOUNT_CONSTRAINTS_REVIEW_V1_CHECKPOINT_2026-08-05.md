# C002 Eye-Mount Constraints Review V1 Checkpoint — 2026-08-05

## Status

This is the first review in the C002 eye-mount redesign bucket. It creates no
replacement mount. It isolates the preserved eye system, the rejected outer
C002 pieces, and the nearest accepted reinforcement anchors so the interface
can be approved before any bracket shape is invented.

## Primary review files

- Blender: `output/00-current-review/c002-eye-mount-constraints-review-v1.blend`
- Validation: `output/00-current-review/c002-eye-mount-constraints-review-v1-validation.json`
- Renders: `output/00-current-review/renders/`

## Review colors

- Red: rejected outer C002 mount; diagnostic reference only.
- Blue: preserved Gate 6 eye bucket.
- Green: preserved lower C004 eye mount.
- Yellow: accepted outer seam rail identified as the possible new anchor.
- Gray: nearby accepted reinforcement.
- Gray wireframe: retained lower-face exterior shell.

## Accepted assumptions for this bucket

- Preserve the existing Gate 6 eye bucket/lightbox.
- Preserve the retained lower C004 mount.
- Replace only the outer C002 mounting function.
- Keep all replacement geometry internal and invisible from the exterior.
- Preserve the accepted reinforcement review and aluminum interface V0.5.

## Measured interfaces

- Both rejected C002 pieces retain the intended `0.3 mm` face gap to their eye
  bucket.
- Left rejected C002 to `R1_RET__L__C012__seam_rail`: `0.0065 mm`.
- Right rejected C002 to `R1_RET__R__C010__seam_rail`: `0.4884 mm`.
- Both retained lower C004 mounts retain the intended `0.3 mm` face gap to
  their eye bucket.
- The rejected C002 pieces are `4.9327 mm` left and `5.8347 mm` right from the
  final retained exterior shells. That gap explains the old long bridge and
  why it became an ugly detached rectangular exterior-side feature after later
  shell repartitioning.

## Rejected or unsafe approaches

- Do not reuse, trim, or cosmetically hide the old C002 solids.
- Do not bridge outward to the exterior shell again.
- Do not redesign the complete eye lightbox unless the preserved-bucket
  assumption is explicitly rejected.
- Do not modify the C006/aluminum connector workstream in this bucket.
- Do not create STL or G-code before mount geometry is visually approved.

## Validation performed

- Source accepted reinforcement blend opens from its workstream baseline.
- No mesh object was added or removed.
- Every pre-existing mesh fingerprint is unchanged.
- Both C002 pieces, eye buckets, lower C004 mounts, seam-rail anchors, retained
  shells, and nearby reinforcement are present in the isolated review.
- Seven close-up context and isolated renders are generated.
- Shared interface revision remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`.
- No STL or G-code is generated.

## Exact regeneration command

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/30-reinforcement-baselines/requested-reinforcement-additions-review-v1/requested-reinforcement-additions-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_c002_eye_mount_constraints_review_v1.py
```

## Next physical review

1. Open the current Blender file in its saved interior view.
2. Confirm the blue eye buckets and green lower C004 mounts should remain.
3. Confirm the red C002 pieces should be removed completely.
4. Confirm the yellow C012/C010 seam rails are acceptable internal anchors for
   a low-profile replacement outer mount.
5. Only after those four points are approved, generate one mirrored bracket
   concept for visual review.
