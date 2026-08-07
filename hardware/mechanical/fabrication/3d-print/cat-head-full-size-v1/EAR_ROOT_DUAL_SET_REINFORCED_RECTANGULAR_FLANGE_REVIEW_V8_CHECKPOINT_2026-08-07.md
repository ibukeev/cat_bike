# Ear-root dual-set reinforced rectangular-flange review V8 checkpoint — 2026-08-07

## Status

V8 is the current placement and root-strength review for F-10/F-11/F-12. It
contains exactly two connector sets on each translucent ear piece: four sets
and eight plain rectangular tabs total.

This is not print released. Do not add holes or hardware, integrate green tabs
into source shells, export STL/G-code, or start ASA parts until the user accepts
the full left/right layout and the conservative-clearance hold is resolved or
explicitly accepted.

## Current review files

- Blender:
  `output/00-current-review/ear-root-dual-set-reinforced-rectangular-flange-review-v8.blend`
- Validation:
  `output/00-current-review/ear-root-dual-set-reinforced-rectangular-flange-review-v8-validation.json`
- Full head:
  `output/00-current-review/renders/ear-root-dual-set-reinforced-rectangular-full-head-context.png`
- Right translucent piece with both moving roots:
  `output/00-current-review/renders/ear-root-dual-set-reinforced-rectangular-right-translucent-piece-two-orange-roots.png`
- Right isolated sets:
  `output/00-current-review/renders/ear-root-dual-set-reinforced-rectangular-right-two-connector-sets-isolated.png`
- Left equivalents replace `right` with `left`.
- Eight owner-root cutaways:
  `output/00-current-review/renders/ear-root-dual-set-reinforced-rectangular-{left,right}-{a,b}-{orange,green}-owner-root.png`
- Exterior occupancy masks:
  `output/00-current-review/renders/ear-root-dual-set-reinforced-rectangular-exterior-{front,left,right,top}-{baseline,candidate}.png`

Useful Blender collections:

- `EAR8_EXACT_STRUCTURAL_HEAD_MUTED__UNCHANGED`;
- `EAR8_EXACT_EARS_CYAN__UNCHANGED`;
- `EAR8_ACCEPTED_V3_TRANSLUCENT_BODIES_YELLOW__UNCHANGED`;
- `EAR8_RIGHT_INSERT_FLANGES_ORANGE__TWO_SETS`;
- `EAR8_LEFT_INSERT_FLANGES_ORANGE__TWO_SETS`;
- `EAR8_RIGHT_HEAD_FLANGES_GREEN__TWO_SETS_UNINTEGRATED`;
- `EAR8_LEFT_HEAD_FLANGES_GREEN__TWO_SETS_UNINTEGRATED`;
- `EAR8_REVIEW_ONLY__OWNER_ROOT_BOOLEAN_CUTAWAY_PROOFS__HIDDEN`.

The 16 cutaway objects are direct Boolean display proofs for the eight actual
left/right owner roots. They are hidden by default and are not fabrication
parts.

## Source of truth and regeneration

- Generator:
  `source/generate_ear_root_dual_set_reinforced_rectangular_flange_review_v8.py`
- Config:
  `config/ear-root-dual-set-reinforced-rectangular-flange-review-v8.json`
- Accepted fit-body source remains V3:
  `config/ear-root-insertion-fit-review-v3.json`
- Required aluminum interface remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`.

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_ear_root_dual_set_reinforced_rectangular_flange_review_v8.py -- --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/ear-root-dual-set-reinforced-rectangular-flange-review-v8.json --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/00-current-review
```

## Decisions and dimensions

- Two sets per translucent piece; four sets total.
- Four orange moving tabs and four green fixed tabs; eight tabs total.
- Each tab: `22 × 12 × 4 mm`.
- Each pair gap: `0.3 mm` measured.
- Locations A/B use fractions `0.45/0.80` of the proven primary seam and are
  `34.9211 mm` apart on each side.
- Both tabs start `1.0 mm` inside the shared seam plane.
- Orange moving tabs receive `0.5 mm` additional interior relief.
- Minimum direct owner-overlap volume: `80 mm³` required.
- No separate root, broad base, wedge, trapezoid, bridge, clamp, boss, hole,
  hardware, or access envelope.

## Structural improvement over V7

V7 had one connector set and approximately `55.5905 mm³` orange / `57.0315
mm³` green owner overlap.

V8 direct Boolean overlaps are:

- right A: orange `80.9705`, green `106.7680 mm³`;
- right B: orange `88.3390`, green `104.9140 mm³`;
- left A: orange `80.1946`, green `106.7496 mm³`;
- left B: orange `87.9388`, green `104.8813 mm³`.

Per translucent piece, total orange attachment volume is approximately three
times V7 and total green attachment volume approximately 3.7 times V7. The tab
section is also 25% thicker, 37.5% longer, and 20% deeper.

## Validation performed and results

- Generator syntax and config JSON: pass.
- Shared shell/aluminum interface regression: 9 tests pass.
- Reopened blend audit: four orange, four green, 16 hidden proofs, zero holes
  and zero hardware.
- Exact Gate 8 source mesh count: 31; all fingerprints unchanged.
- Four connector sets, eight actual tabs, zero extra connector objects.
- A/B center separation: `34.9211 mm` on each side; mirror center error `0`.
- All four measured gaps: `0.3 mm`.
- All eight direct owner overlaps exceed `80 mm³`; minimum `80.1946 mm³`.
- Both moving body/two-orange-tab composites: one connected component, zero
  boundary edges, zero non-manifold edges.
- Actual seated shell hits: none on either side.
- Green unintended-shell hits: none.
- Accepted V3 deep-body paths: clear on both sides for all 41 samples with a
  `0.4 mm` margin.
- Actual full moving geometry paths: clear on both sides for all 41 samples.
- Conservative `0.4 mm` expanded orange-tab envelopes: **not clear at the
  seated sample**. Right maximum is 20 and left maximum is 18 triangle pairs
  against their upper heads. No later motion sample conflicts.
- Flat exterior occupancy masks: front, left, right, and top baseline/candidate
  pairs are pixel-identical with zero changed channels and zero maximum delta.
- No STL, G-code, slicer project, fabrication output, or print release created.

## Rejected or unsafe variants

- V4 loose clamp and V5 compound bridge remain rejected.
- V6 exterior broad-base/hardware construction remains rejected.
- V7 one-set/small-root layout is conceptually superseded.
- A proposed `3 mm` shared embed was tested and rejected: it caused the moving
  composite to collide with the upper head (`14` triangle pairs on the first
  failing right-side diagnostic).
- Secondary rear boundary locations were rejected because the enlarged moving
  tab intersected the upper head.
- A `1.0 mm` orange relief cleared the conservative margin but reduced the
  weakest orange root to about `49.55 mm³`; it was rejected in favor of the
  stronger `0.5 mm` relief and its explicit conservative-clearance hold.
- Do not treat the clear actual path as physical tolerance approval.

## Preserved workstreams

V8 does not modify the accepted V3 fit body, exact ears, exact upper-head source
geometry, eyes, lower-face/rear-cassette ownership, reinforcement direction,
C006, or the aluminum plate/rail `CAT-HEAD-SHELL-ALUMINUM-V0.5` workstream.

## Next visual review

1. Open the V8 blend and confirm the whole head remains intact.
2. Review each yellow translucent-piece context and verify two orange roots are
   present and separated.
3. Review each isolated side and confirm two ordinary orange/green flange pairs,
   not one set and not a compound connector.
4. Review all eight owner-root cutaways. The narrow yellow/gray band is the
   measured portion inside that actual owner.
5. Review the flat baseline/candidate occupancy masks; they should be identical.
6. Approve or reject the count, spacing, dimensions, and visible owner overlap.
   Hole/hardware work remains the next gate only after this review.
