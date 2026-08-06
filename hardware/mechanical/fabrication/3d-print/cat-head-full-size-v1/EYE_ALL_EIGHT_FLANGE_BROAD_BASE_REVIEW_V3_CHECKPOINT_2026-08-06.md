# Eye All-Eight-Flange Broad-Base Review V3 Checkpoint — 2026-08-06

## Status

This is the current visual and structural-layout review. V2's narrow end-root
concept was rejected. V3 preserves the Gate 6 flange positions and M2.5
interfaces while adding a broad continuous owner-side base to all eight
physical flanges: four on the left and four on the right.

This is not a production Boolean, vibration certification, or print release.

## Primary review files

- Blender: `output/00-current-review/eye-all-eight-flange-broad-base-review-v3.blend`
- Validation: `output/00-current-review/eye-all-eight-flange-broad-base-review-v3-validation.json`
- Renders: `output/00-current-review/renders/`

## Review colors and collections

- Purple, `E4_PROPOSED_HEAD_FLANGES_PURPLE`: four proposed head-shell
  flanges with broad bases.
- Orange, `E4_PROPOSED_EYE_FLANGES_ORANGE`: four matching eye-bucket
  flanges with broad bases.
- Blue, `E4_PRESERVED_EYE_BUCKETS_BLUE`: unchanged eye buckets.
- Gray, `E4_OWNER_SHELLS_GRAY`: unchanged upper/lower head owner shells.
- `E4_SOURCE_MOUNT_REFERENCES_HIDDEN`: rejected C002 and superseded C004
  source mount references, hidden and not reused as candidates.

## Exact flange count and ownership

Each side has exactly four candidates:

1. Outer head flange -> upper-head shell.
2. Outer eye flange -> eye bucket.
3. Lower head flange -> lower-face shell.
4. Lower eye flange -> eye bucket.

Total: eight candidates, comprising four head-side flanges and four
eye-bucket-side flanges.

## Preserved interface decisions

- Preserve every Gate 6 flange center and side-specific orientation.
- Preserve mating-tab envelope: `12.0 x 8.0 x 2.4 mm`.
- Preserve M2.5 clearance diameter: `2.8 mm`.
- Preserve the paired M2.5 axes and hole centers.
- Preserve front recess: `0.6 mm`.
- Preserve mating gap: `0.3 mm`.
- Reinforcement extends only away from the mating gap into its owner.
- Preserve eye buckets, shell exterior geometry, accepted reinforcement,
  C006 hold, and aluminum interface V0.5.

## Broad-base review dimensions

Every flange receives one continuous flared base:

- Total base depth along the owner direction: `4.0 mm`.
- Overlap into the original flange: `0.8 mm`.
- Extension beyond the original owner-side face: `3.2 mm`.
- Footprint at the flange: `12.0 x 8.0 mm`.
- Footprint at the owner: `16.0 x 12.0 mm`.
- Base volume before union: approximately `565.333 mm3` each.
- Complete reinforced flange volume: approximately `684.844 mm3` each.

These dimensions are review parameters, not fabrication approval.

## Validation performed and results

- Exactly four flange candidates per side and eight total.
- Exactly four head-side and four eye-bucket-side candidates.
- All eight broad bases overlap their original flange envelope.
- All eight broad bases overlap their intended shell or bucket owner.
- All eight broad bases clear the opposing mating flange.
- All eight complete candidates preserve the `0.3 mm` mating gap.
- All four flange pairs retain coaxial M2.5 holes; maximum projected
  centerline error is below `0.0001 mm`.
- All eight candidates are closed and manifold.
- Both eye buckets are visible in the saved whole-head review.
- All 143 source mesh fingerprints remain unchanged.
- No source shell or eye-bucket mesh was modified.
- No production owner Boolean, STL, G-code, or print release was generated.

## Rejected or unsafe variants

- V2 is rejected: it reinforced only the two outer head-side flanges and used
  narrow end roots instead of broad bases across the complete flange system.
- Do not fabricate V1 or V2.
- Do not reuse the long rejected C002 bridge pieces.
- Do not alter the mating gap or move the accepted flange/hole interfaces.
- Do not modify C006 or aluminum geometry in this eye-mount review.
- CAD overlap/manifold checks do not replace physical vibration testing.

## Exact regeneration command

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/30-reinforcement-baselines/requested-reinforcement-additions-review-v1/requested-reinforcement-additions-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_eye_all_eight_flange_broad_base_review_v3.py
```

## Next physical review

1. Open the current V3 Blender file in its saved whole-head view.
2. Isolate `E4_PROPOSED_HEAD_FLANGES_PURPLE` and
   `E4_PROPOSED_EYE_FLANGES_ORANGE`.
3. On each side, count four candidates: outer head, outer eye, lower head,
   and lower eye.
4. Inspect each purple/orange pair and confirm the `0.3 mm` mating gap and
   coaxial M2.5 holes remain visible.
5. Inspect behind every flange: the base must be a broad continuous flare into
   the gray shell or blue bucket, not a narrow stick or end root.
6. Check the whole-head exterior views for visible protrusions.
7. Approve or reject V3 before any production-shell or bucket integration.

## Metal workstream preservation

The shared aluminum interface remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`. No
C006 connector, aluminum plate, aluminum rail, hole pattern, stock dimension,
or fabrication output is changed by V3.
