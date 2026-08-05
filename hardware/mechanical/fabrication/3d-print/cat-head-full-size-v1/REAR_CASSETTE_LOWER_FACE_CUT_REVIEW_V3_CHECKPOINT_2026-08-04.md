# Rear Cassette Lower-Face Cut Review V3 Checkpoint — 2026-08-04

## Status

Review-only V3 is generated and validated. It cuts only duplicated Gate 8
`left_lower_face` and `right_lower_face` bodies at the V2-approved rear facet
group. It is not a production print, cassette, or aluminum-fabrication release.

## Review files

- Primary Blender review: `output/rear-cassette-lower-face-cut-review-v3/rear-cassette-lower-face-cut-review-v3.blend`
- Portable review: `output/rear-cassette-lower-face-cut-review-v3/rear-cassette-lower-face-cut-review-v3.glb`
- Geometry report: `output/rear-cassette-lower-face-cut-review-v3/rear-cassette-lower-face-cut-review-v3-validation.json`
- Slicer report: `output/rear-cassette-lower-face-cut-review-v3/slicer-review/rear-cassette-lower-face-cut-review-v3-slicer.json`
- Review-only STLs: `output/rear-cassette-lower-face-cut-review-v3/review-stl-not-production/`
- PNG views: `output/rear-cassette-lower-face-cut-review-v3/renders/`

In Blender, hide collection `REVIEW_V3_REMOVED_REGION_OVERLAY` to see only the
actual cut bodies. Blue is the cut left lower face, green is the cut right
lower face, orange is the removed region, and yellow is the complete cut
boundary. The original Gate 8 lower faces remain hidden and unchanged.

## Accepted scope and dimensions

- Cut ownership is exactly five V2-approved source facets per side, ten total.
- Each side has a nine-edge cut outline.
- The selected two-side exterior region is `253.878 x 81.006 x 88.130 mm`.
- The hidden cutter extends `5 mm` outward and `400 mm` inward.
- A declared `0.05 mm` tangential boundary overlap prevents tangent Boolean
  faces; it does not move upper-head, ear, rear-base, or aluminum datums.
- Upper heads, ears, `rear_base`, eyes, and the V0.5 aluminum interface are
  unchanged. Their before/after mesh fingerprints match exactly.
- Original Gate 8 lower-face objects are retained unchanged in the review file.

## Geometry validation

- Left source: 61 closed components; V3 result: 41 closed components.
  24 source components fully inside the subtraction were removed; some
  intersected components split into multiple retained closed components.
- Right source: 63 closed components; V3 result: 38 closed components.
  29 source components fully inside the subtraction were removed; some
  intersected components split into multiple retained closed components.
- Both final bodies: zero boundary edges and zero non-manifold edges.
- Blender mesh validation reports no remaining duplicate or degenerate faces.
- One zero-volume duplicate-face Boolean remnant per side was discarded; no
  cut-boundary cap faces were fabricated (`0` added on both sides).
- Left STL SHA-256: `af2c9962b12e62236fd97bceed8063bb2e34a316f158c0c021781a3a0de1fbc9`.
- Right STL SHA-256: `af7587efd4715ec610ae1a083ea38395682711999d316f1408bdee672872a105`.

## Independent MK4S ASA slice review

Settings: MK4S `250 x 210 x 220 mm`, ASA, `0.2 mm` layers, 3 perimeters,
15% infill, automatic snug supports everywhere, and `5 mm` brim. Acceptance
requires at least `10 mm` XY margin after actual brim/support toolpaths.

- Left selected orientation: `(100, 54, 178)°`; oriented envelope
  `215.273 x 177.807 x 216.350 mm`; minimum XY margin `13.335 mm`;
  estimated `12h 08m 06s`, `95.32 g`, including estimated `54.144 g` support.
- Right selected orientation: `(104, 130, 6)°`; oriented envelope
  `216.384 x 177.543 x 217.320 mm`; minimum XY margin `12.738 mm`;
  estimated `8h 07m 07s`, `59.42 g`, including estimated `22.381 g` support.
- Both actual V3 pieces pass the 10 mm margin and 220 mm height gates.
- Generated G-code remains review-only and must not be printed as a release.

## Rejected or unsafe variants

- One Boolean across the full multi-component lower-face object: rejected;
  introduced non-manifold edges.
- Raw `EXACT`, `FLOAT`, and `MANIFOLD` results without per-component handling:
  rejected by duplicate/non-manifold validation.
- `0.25 mm` boundary-overlap experiment: rejected; it increased defects.
- Cosmetic mesh cleanup without revalidating closure: rejected.
- Upper-head recutting, ear changes, rear-base changes, reinforcement redesign,
  and aluminum reconciliation were outside this feedback step and not done.

## Exact regeneration

From repository root:

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate8-full-size-structural-iteration/gate8-full-size-structural-review.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_rear_cassette_lower_face_cut_review_v3.py
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_rear_cassette_lower_face_cut_review_v3.py
```

## Next physical review

1. Open the primary V3 blend and inspect the full head in rear, front, and both
   side views.
2. Hide `REVIEW_V3_REMOVED_REGION_OVERLAY`; isolate
   `REVIEW_V3_CUT__left_lower_face` and `REVIEW_V3_CUT__right_lower_face`.
3. Confirm the opening is the intended portion that will belong to the rear
   cassette and that no retained visible lower-face facet was removed.
4. Do not start ASA printing from V3 review G-code yet.
5. After explicit visual approval, address the cassette connection around the
   preserved V0.5 aluminum plate/rails as the next separate feedback item.
