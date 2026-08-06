# C002 Outer-Flange Upper-Head Review V1 Checkpoint — 2026-08-06

## Status

This is a visual-review candidate only. It removes the two rejected long
`R1_UNCL__*__C002__eye_mount` objects, reconstructs each outer flange from
the exact Gate 6 interface, and adds a compact hidden root that overlaps the
matching upper-head shell. No production upper-head Boolean, STL, G-code, or
print release has been made.

## Primary review files

- Blender: `output/00-current-review/c002-outer-flange-upper-head-review-v1.blend`
- Validation: `output/00-current-review/c002-outer-flange-upper-head-review-v1-validation.json`
- Renders: `output/00-current-review/renders/`

## Review colors and collections

- Purple, `E2_PROPOSED_OUTER_FLANGES_PURPLE`: proposed outer flanges and
  their compact roots.
- Blue, `E2_PRESERVED_EYE_BUCKETS_BLUE`: unchanged Gate 6 eye buckets.
- Green, `E2_PRESERVED_LOWER_C004_GREEN`: unchanged connected lower mounts.
- Gray, `E2_OWNER_UPPER_HEAD_SHELLS_GRAY`: unchanged upper-head owner shells.
- Dark gray, `E2_NEARBY_REINFORCEMENT_CONTEXT`: retained nearby context only.

## Accepted decisions and dimensions

- Preserve two mounting flanges per eye: connected lower C004 plus corrected
  outer C002 function.
- Preserve each side's exact Gate 6 flange location rather than forcing
  artificial symmetry.
- Preserved flange envelope: `12.0 x 8.0 x 2.4 mm`.
- Preserved M2.5 clearance hole: `2.8 mm`.
- Preserved front recess: `0.6 mm`.
- Preserved bucket-side face gap: `0.3 mm`.
- Owner shells: `left_upper_head` and `right_upper_head`.
- Tapered-root centerline length: `3.0 mm`.
- Root overlap into flange: `0.8 mm`; extension beyond flange: `2.2 mm`.
- Root depth: `3.0 mm` at flange to `4.0 mm` at shell.
- Root thickness: `1.6 mm` at flange to `2.0 mm` at shell.
- Measured flange-to-owner-shell source gaps: `0.0359 mm` left and
  `0.2520 mm` right.
- Root-to-bucket clearance before union: `0.9 mm` both sides.
- Final candidate-to-bucket gap: `0.3 mm` both sides.
- Inherited Gate 6 hole-center mirror delta: `0.502958 mm`; both original
  side-specific interfaces are preserved exactly.

## Validation performed and results

- Both rejected C002 objects are absent from the review.
- Exactly two closed, manifold replacement candidates are present.
- Both roots overlap their reconstructed flange and matching upper-head shell.
- Both roots clear their eye buckets by at least `0.8 mm`.
- Both complete candidates preserve the configured `0.3 mm` bucket gap.
- Both candidates overlap the old flange locations.
- All 141 unrelated source mesh fingerprints remain unchanged.
- C010/C012 are context only and are not used as mount anchors.
- Shared aluminum interface remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`.
- Saved whole-head viewport and renders explicitly include both eye buckets.
- C006 and all aluminum plate/rail geometry remain unchanged.
- No production-shell Boolean, STL, or G-code was generated.

## Rejected or unsafe variants

- Rejected lower-face diagonal gusset: the final retained lower-face shells
  were about `22 mm` from the preserved flanges, and the attempted bridge
  collided with the eye bucket. It was never committed.
- Rejected another long lower-face arm: it repeats the ugly detached C002
  geometry that prompted this redesign.
- Rejected forced mirroring: Gate 6's two source interfaces are not perfectly
  mirrored, so forcing symmetry would move the mating holes.
- Do not modify C006 or the aluminum plate/rail workstream in this review.

## Exact regeneration command

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/30-reinforcement-baselines/requested-reinforcement-additions-review-v1/requested-reinforcement-additions-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_c002_outer_flange_upper_head_review_v1.py
```

## Next physical review

1. Open the current Blender file; it opens in the whole-head three-quarter
   camera view.
2. Inspect the purple outer flange on both sides in the full-head context.
3. Use the two `root-detail` renders or isolate the purple and gray
   collections to confirm the small tapered root enters the upper-head shell.
4. Confirm the blue eye buckets and green lower C004 mounts are unchanged.
5. Check both exterior views for any visible protrusion or unwanted silhouette
   change.
6. Approve or reject this review before any production-shell integration.

## Metal workstream preservation

The shared aluminum interface remains at V0.5. No C006 connector, aluminum
plate, aluminum rail, hole pattern, stock dimension, or fabrication output is
changed by this candidate.
