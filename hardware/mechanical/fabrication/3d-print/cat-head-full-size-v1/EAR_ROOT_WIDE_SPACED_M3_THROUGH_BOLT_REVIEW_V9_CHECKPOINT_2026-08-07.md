# Ear-root maximum-safe spacing and M3 through-bolt review V9 checkpoint — 2026-08-07

## Status

V9 is archived. Its two-set rectangular-flange and M3 through-bolt concept was
accepted, but its same-seam placement was superseded by the user's marked
relocation in V10. Do not use V9 as the current placement reference.

This is not print released. The drilled review geometry is valid, but the green
tabs are not yet integrated into production shell meshes and physical internal
tool/washer/nut access has not been confirmed. Do not start ASA parts from V9.

## Archived review files

All V9 review files are under:
`output/60-ear-root-reviews/ear-root-wide-spaced-m3-through-bolt-review-v9-screw-hole-concept-accepted-placement-superseded-by-marked-relocation/`.

- Blender:
  `output/60-ear-root-reviews/ear-root-wide-spaced-m3-through-bolt-review-v9-screw-hole-concept-accepted-placement-superseded-by-marked-relocation/ear-root-wide-spaced-m3-through-bolt-review-v9.blend`
- Validation:
  `output/60-ear-root-reviews/ear-root-wide-spaced-m3-through-bolt-review-v9-screw-hole-concept-accepted-placement-superseded-by-marked-relocation/ear-root-wide-spaced-m3-through-bolt-review-v9-validation.json`
- Renders are in that directory's `renders/` subfolder.

Useful Blender collections use the `EAR9_` prefix. Orange tabs belong to the
moving translucent pieces; green tabs are proposed fixed shell geometry. The
16 owner-root cutaway objects are hidden review proofs, not fabrication parts.

## Source of truth and regeneration

- Generator:
  `source/generate_ear_root_wide_spaced_m3_through_bolt_review_v9.py`
- Config:
  `config/ear-root-wide-spaced-m3-through-bolt-review-v9.json`
- Accepted fit body remains V3.
- Required aluminum interface remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`.

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_ear_root_wide_spaced_m3_through_bolt_review_v9.py -- --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/ear-root-wide-spaced-m3-through-bolt-review-v9.json --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/00-current-review
```

## Accepted dimensions and hardware proposal

- Two connector sets per translucent piece; four sets total.
- Eight rectangular tabs total: four orange and four green.
- Tab dimensions remain `22 × 12 × 4 mm`.
- Measured mating gap is `0.3 mm` for every pair.
- Final tested seam fractions are `0.45/0.82`.
- Center separation is `36.9166 mm` per side; V8 was `34.9211 mm`.
- One common `3.4 mm` M3 clearance axis per pair.
- Four aligned fastener paths and eight drilled tab holes total.
- Minimum modeled bore-to-edge material is `4.05 mm`.
- Proposed hardware: four M3 × 16 through-bolts, eight 7 mm OD washers, and
  four M3 nyloc nuts, all serviced from inside the head.
- If physical fit requires adjustment, enlarge only the orange hole, retain the
  7 mm washer, and leave at least `3 mm` of material to the nearest tab edge.
- No broad base, wedge, bridge, clamp, boss, heat-set insert, or exterior
  connector was added.

## Validation performed and results

- Generator syntax and config JSON: pass.
- Shared cat-head/aluminum interface regression: 9 tests pass.
- Reopened Blender audit: four orange tabs, four green tabs, four aligned M3
  paths, eight drilled tab holes, and 16 hidden owner proofs.
- Blender generation under the formal `80 mm³` owner-root gate: pass.
- Four `3.2 mm` bore gauges pass through all four nominal `3.4 mm` paths with
  zero orange or green intersections.
- Direct drilled owner overlaps:
  - right A: orange `80.9704`, green `106.7681 mm³`;
  - right B: orange `88.7493`, green `104.8076 mm³`;
  - left A: orange `80.1945`, green `106.7493 mm³`;
  - left B: orange `88.3960`, green `104.7739 mm³`.
- Both moving body/two-tab composites are one connected manifold component.
- Actual seated shell hits: none.
- Green unintended-shell hits: none.
- Accepted V3 deep-body paths clear all 41 samples with the `0.4 mm` margin.
- Actual full moving geometry clears all 41 samples on both sides.
- The conservative `0.4 mm` expanded moving-tab envelopes touch the upper
  heads and intentionally mated green tabs at the seated sample. This remains
  a physical-tolerance review hold; later motion samples are clear.
- Front, left, right, and top exterior occupancy masks are pixel-identical.
- Exact Gate 8 source count remains 31 and all fingerprints are unchanged.
- No STL, G-code, slicer project, or print release was generated.

## Rejected spacing variants

- `0.22/0.82` produced approximately `59.9 mm` spacing but the drilled forward
  orange root fell to `75.284 mm³`, below the retained strength gate.
- Increasing tab tangent length to `26 mm` restored root material but collided
  with the upper head.
- Increasing tab thickness to `5 mm` also collided with the upper head.
- Same-seam forward positions `0.27`, `0.35`, `0.40`, `0.43`, and `0.44` were
  rejected by actual right or left upper-head collisions in tested layouts.
- A second-long-seam layout gave approximately `49 mm` spatial separation but
  its moving B tab intersected the upper head.
- Do not recover spacing by cutting the accepted upper-head pieces or lowering
  the `80 mm³` final root-strength requirement.

## Preserved workstreams

V9 does not modify the accepted V3 fit body, exact ears, exact upper-head source
geometry, eyes, lower-face/rear-cassette ownership, reinforcement direction,
C006, or the aluminum plate/rail `CAT-HEAD-SHELL-ALUMINUM-V0.5` workstream.

## Next physical review

V9 needs no further review. Use the V10 checkpoint and current-review folder.
