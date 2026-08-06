# C002 Outer-Flange Dual-Root Upper-Head Review V2 Checkpoint — 2026-08-06

## Status

Rejected by the user on 2026-08-06. V2 reinforced only the two outer head-side
flanges with narrow end roots. It did not reinforce the matching eye-bucket
flanges or the lower head/eye flange pair on either side, so it did not address
the complete eight-flange load path. Preserve it only as rejected history; it
is not approved for fabrication.

## Primary review files

- Blender: `output/50-eye-mount-reviews/c002-outer-flange-dual-root-upper-head-review-v2/c002-outer-flange-dual-root-upper-head-review-v2.blend`
- Validation: `output/50-eye-mount-reviews/c002-outer-flange-dual-root-upper-head-review-v2/c002-outer-flange-dual-root-upper-head-review-v2-validation.json`
- Renders: `output/50-eye-mount-reviews/c002-outer-flange-dual-root-upper-head-review-v2/renders/`

## Review colors and collections

- Purple, `E3_PROPOSED_OUTER_FLANGES_PURPLE`: accepted flange positions plus
  two proposed roots per connector.
- Blue, `E3_PRESERVED_EYE_BUCKETS_BLUE`: unchanged Gate 6 eye buckets.
- Green, `E3_PRESERVED_LOWER_C004_GREEN`: unchanged connected lower mounts.
- Gray, `E3_OWNER_UPPER_HEAD_SHELLS_GRAY`: unchanged upper-head owner shells.
- Dark gray, `E3_NEARBY_REINFORCEMENT_CONTEXT`: retained context only.

## Accepted decisions and dimensions

- Preserve the V1 connector positions, M2.5 hole centers, and side-specific
  Gate 6 orientation exactly.
- Preserve flange envelope: `12.0 x 8.0 x 2.4 mm`.
- Preserve M2.5 clearance hole: `2.8 mm`.
- Preserve front recess: `0.6 mm`.
- Preserve bucket-side face gap: `0.3 mm`.
- Use exactly two roots per connector at opposite ends of the 12 mm flange.
- Each root centerline length: `3.0 mm`.
- Each root overlap into flange: `0.8 mm`; extension beyond flange:
  `2.2 mm`.
- Each root depth: `3.0 mm` at flange to `4.0 mm` at shell.
- Each root thickness: `1.6 mm` at flange to `2.0 mm` at shell.
- Minimum root-to-bucket clearance: `0.9 mm` for all four roots.
- Final connector-to-bucket gap: `0.3 mm` both sides.
- Candidate volume: `245.4986 mm3` left and `245.4975 mm3` right.

## Validation performed and results

- Exactly two connector candidates and four roots are present.
- Both candidates are closed and manifold after two unions and the M2.5 cut.
- Every root overlaps its flange and matching upper-head shell.
- All four roots retain `0.9 mm` bucket clearance.
- Both complete connectors retain the accepted `0.3 mm` bucket gap.
- Both candidates overlap the accepted V1/old flange locations.
- Both eye buckets are visible in the saved whole-head viewport and renders.
- All 141 unrelated source mesh fingerprints remain unchanged.
- C010/C012 are context only and are not mount anchors.
- Shared interface remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`.
- No production-shell Boolean, STL, G-code, or print release was generated.

## Rejected or unsafe variants

- Do not fabricate single-root V1: its connector placement is accepted, but its
  resistance to vibration-driven twisting was not established.
- Do not return to the old approximately 22 mm lower-face bridge.
- Do not force artificial mirroring; preserve each Gate 6 interface.
- Do not modify C006 or the aluminum plate/rail workstream in this review.
- CAD overlap/manifold checks do not replace a physical vibration test.

## Exact regeneration command

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/30-reinforcement-baselines/requested-reinforcement-additions-review-v1/requested-reinforcement-additions-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_c002_outer_flange_dual_root_upper_head_review_v2.py
```

## Superseding review

Do not fabricate V2. Review V3, which covers all eight physical flanges:
outer head, outer eye, lower head, and lower eye on both left and right sides.
V3 uses a broad continuous owner-side base at every flange junction while
preserving the accepted locations, holes, and mating gaps.

## Metal workstream preservation

The shared aluminum interface remains at V0.5. No C006 connector, aluminum
plate, aluminum rail, hole pattern, stock dimension, or fabrication output is
changed by V2.
