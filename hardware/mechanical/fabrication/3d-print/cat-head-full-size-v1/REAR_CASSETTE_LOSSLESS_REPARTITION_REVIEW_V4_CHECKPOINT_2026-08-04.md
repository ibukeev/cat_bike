# Rear Cassette Lossless Repartition Review V4 Checkpoint — 2026-08-04

## Status

V4 is ready for visual review only. It replaces rejected V3 with a lossless
exterior-facet repartition. No deep Boolean cutter is used, no source facet is
deleted, and no internal reinforcement is cut or reassigned.

## Primary review files

- Blender: `output/rear-cassette-lossless-repartition-review-v4/rear-cassette-lossless-repartition-review-v4.blend`
- Portable GLB: `output/rear-cassette-lossless-repartition-review-v4/rear-cassette-lossless-repartition-review-v4.glb`
- Validation: `output/rear-cassette-lossless-repartition-review-v4/rear-cassette-lossless-repartition-review-v4-validation.json`
- Renders: `output/rear-cassette-lossless-repartition-review-v4/renders/`

## Blender review structure

- `V4_RETAINED_LOWER_EXTERIORS`: blue left and green right lower shells after
  the approved rear facets change ownership.
- `V4_ENLARGED_REAR_CASSETTE_OWNERSHIP`: orange left/right moved rear shells
  plus an unchanged orange copy of `rear_base`.
- `V4_REPARTITION_BOUNDARIES`: yellow complete ownership boundaries.
- `UNCHANGED_GATE8_SOURCE_REFERENCE`: all original Gate 8 objects. The two
  original lower faces and original `rear_base` are hidden, not modified.

The default scene shows the complete assembled exterior. Isolate the retained
and cassette collections separately to review each side of the repartition.

## Accepted decisions and dimensions

- Upper heads, ears, eyes, `rear_base`, and the active V0.5 aluminum interface
  remain unchanged.
- Exactly five approved source facets per lower side move to cassette
  ownership, ten total.
- Every other lower-face source facet remains with its original lower side.
- Both Gate 3 lower closure faces remain with the retained lower shells.
- Review shells use the existing inward `1.8 mm` wall convention.
- The moved shells and unchanged `rear_base` are an ownership group, not yet a
  physically connected cassette or aluminum-ready design.

## Validation performed

- Original lower exterior ledger including closures: 45 faces.
- Candidate retained-plus-moved exterior ledger: 45 faces.
- Deleted source faces: 0.
- Unexpected added source faces: 0.
- Duplicated source faces: 0.
- Original/candidate exterior fingerprint:
  `92b6a2067a57f3baeaa20ca4b6d7c363a90e7a7ec7f95afc90284c101508e591`.
- All four regenerated review shells are closed, manifold, free of duplicate
  faces, and free of degenerate faces.
- Protected Gate 8 before/after mesh fingerprints match.
- No STL or G-code was generated.

## Reinforcement status

All original Gate 8 lower-face reinforcement remains preserved inside the
hidden source objects. V4 intentionally makes no reinforcement ownership
decision. After exterior approval, the next step is to inventory each complete
reinforcement component and assign it whole to either the retained lower shell
or cassette. Anything spanning the seam must be redesigned explicitly; nothing
may be chopped, floated, or silently deleted.

## Rejected or unsafe variants

- V3 commit `9be17c1` is reverted by commit `0d11a7f`.
- The V3 400 mm inward Boolean projected through the head, deleted middle
  geometry, chopped reinforcement, and left floating islands.
- Manifold and slicer success are not accepted as evidence of assembly
  connectivity.
- No V3 mesh is reused in V4.

## Exact regeneration command

From repository root:

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate8-full-size-structural-iteration/gate8-full-size-structural-review.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_rear_cassette_lossless_repartition_review_v4.py
```

## Next physical review

1. Inspect the default full assembly from front, rear, left, and right.
2. Confirm the assembled exterior is complete and visually unchanged.
3. Isolate `V4_RETAINED_LOWER_EXTERIORS`; confirm only the intended rear facets
   are absent from the two lower shells.
4. Isolate `V4_ENLARGED_REAR_CASSETTE_OWNERSHIP`; confirm those exact missing
   facets are present in orange with the unchanged rear base.
5. Do not review or approve printing from V4; there are no print files.
6. After explicit exterior approval, perform reinforcement ownership as the
   next separate feedback item, then reconcile the cassette with V0.5 aluminum.
