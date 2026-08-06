# Rear Cassette Lossless Repartition Review V5 Checkpoint — 2026-08-04

## Status

V5 is ready for visual review only. It keeps the V4-approved rear-cassette
ownership seam unchanged and restores the accepted Gate 8 opaque panels
between the nose and eyes to the retained lower-face pieces. No source facet is
deleted, duplicated, or newly invented, and no reinforcement is changed.

## Primary review files

- Blender: `output/20-rear-cassette/current-baseline-v5/rear-cassette-lossless-repartition-review-v5.blend`
- Portable GLB: `output/20-rear-cassette/current-baseline-v5/rear-cassette-lossless-repartition-review-v5.glb`
- Validation: `output/20-rear-cassette/current-baseline-v5/rear-cassette-lossless-repartition-review-v5-validation.json`
- Renders: `output/20-rear-cassette/current-baseline-v5/renders/`

## Blender review structure

- `V5_RETAINED_LOWER_EXTERIORS`: blue left and green right retained lower
  shells, including the restored nose-to-eye opaque panels.
- `V5_ENLARGED_REAR_CASSETTE_OWNERSHIP`: orange left/right moved rear shells
  plus an unchanged orange copy of `rear_base`.
- `V5_REPARTITION_BOUNDARIES`: yellow complete ownership boundaries.
- `UNCHANGED_GATE8_SOURCE_REFERENCE`: all original Gate 8 objects. The two
  original lower faces and original `rear_base` are hidden, not modified.

The default scene shows the complete assembled exterior. Isolate the retained
and cassette collections separately to review each side of the repartition.

## Accepted decisions and dimensions

- The V4-approved cassette seam is unchanged: exactly five approved source
  facets per lower side move to cassette ownership, ten total.
- Gate 8 panels `QUAD001` and `TRI003` remain owned by `right_lower_face`.
- Gate 8 panels `QUAD022` and `TRI042` remain owned by `left_lower_face`.
- Each split quad contributes two source triangles, so three source faces per
  side are restored to the retained lower shells.
- Upper heads, ears, eyes, `rear_base`, and the active V0.5 aluminum interface
  remain unchanged.
- Both Gate 3 lower closure faces remain with the retained lower shells.
- Review shells use the existing inward `1.8 mm` wall convention.
- The moved shells and unchanged `rear_base` are an ownership group, not yet a
  physically connected cassette or aluminum-ready design.

## Cause of the V4 regression

The accepted Gate 8 nose-to-eye panels are intentionally classified as opaque
shell panels, but their source assignment remains `removable_glow`. V4
collected only faces whose assignment was directly `left_lower_face` or
`right_lower_face`, so it omitted those six reclassified source faces. V5
cross-checks the panel IDs against the Gate 8 configuration and assigns them
explicitly to their accepted lower-face owners.

## Validation performed

- Original lower exterior ledger including closures: 51 faces.
- Candidate retained-plus-moved exterior ledger: 51 faces.
- Deleted source faces: 0.
- Unexpected added source faces: 0.
- Duplicated source faces: 0.
- Original/candidate exterior fingerprint:
  `4787ed3e5bf7d8ae2540aa90894bcb9fcc97dd0c0aa54883b12db9127eb25b55`.
- All four regenerated review shells are closed, manifold, free of duplicate
  faces, and free of degenerate faces.
- Protected Gate 8 before/after mesh fingerprints match.
- Front-view visual comparison confirms the retained lower shells again extend
  through the accepted nose-to-eye panels while the V4 cassette seam remains
  unchanged.
- No STL or G-code was generated.

## Reinforcement status

All original Gate 8 lower-face reinforcement remains preserved inside the
hidden source objects. V5 intentionally makes no reinforcement ownership
decision. After exterior approval, inventory each complete reinforcement
component and assign it whole to either the retained lower shell or cassette.
Anything spanning the seam must be redesigned explicitly; nothing may be
chopped, floated, or silently deleted.

## Rejected or unsafe variants

- V3 commit `9be17c1` is reverted by commit `0d11a7f`; its deep Boolean result
  remains rejected.
- V4 remains valid as a seam concept but is incomplete as an exterior review
  because it omits the six accepted Gate 8 lower-owned nose-to-eye faces.
- V5 does not reuse V3 mesh or change the V4 cassette selection.
- Manifold and slicer success alone are not evidence of assembly connectivity.

## Exact regeneration command

From repository root:

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/10-design-gates/gate8-full-size-structural-iteration/gate8-full-size-structural-review.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_rear_cassette_lossless_repartition_review_v5.py
```

## Next physical review

1. Open the V5 `.blend` and inspect the default full assembly from the front.
2. Confirm the nose-to-eye opaque areas match the previously accepted Gate 8
   shape on both sides.
3. Isolate `V5_RETAINED_LOWER_EXTERIORS`; confirm both tall inner panels remain
   with the lower faces and only the approved rear facets are absent.
4. Isolate `V5_ENLARGED_REAR_CASSETTE_OWNERSHIP`; confirm the cassette contains
   the same ten rear facets approved in V4 and no nose-to-eye panels.
5. Do not print from V5; there are no print files.
6. After explicit exterior approval, perform reinforcement ownership as the
   next separate feedback item, then reconcile the cassette with V0.5 aluminum.
