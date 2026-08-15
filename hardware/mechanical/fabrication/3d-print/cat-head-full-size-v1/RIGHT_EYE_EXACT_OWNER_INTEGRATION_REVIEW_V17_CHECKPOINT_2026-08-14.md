# Right Eye Exact Owner Integration V17 Checkpoint — 2026-08-14

## Status

The right production eye bucket and both approved eye-side flange roots now form
one exact, valid, closed solid. The exported STEP passes an independent FreeCAD
re-import check with zero self-intersections. This clears the V16 mesh-union
failure, but it is not yet HS-11 closure or a structural ASA print release: the
V17 owner must still be reviewed in the complete right head context.

## Current review and output files

- FreeCAD review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-exact-owner-integration-review-v17/CAT_HEAD_RIGHT_EYE_EXACT_OWNER_INTEGRATION_REVIEW_V17.FCStd`
  - SHA-256: `861c11381ac4a47b4acce10c50706126605cb4e85417a96f2467dd22a9e8228a`
- Exact integrated STEP:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-exact-owner-integration-review-v17/right_eye_bucket_with_both_exact_flange_roots_v17.step`
  - SHA-256: `1b1e2430c369fb563602a056340c1d5f88f6a857f9cecf2014bac191443646de`

## Frozen exact sources

- Production V9 right-eye STEP:
  `production/eye-modules-v9/right/right_eye_bucket_production_owner_v9.step`
  - SHA-256: `f952fd29451518eb8a019e8810fdfd043266486b568ec1d5c78a0525f2e2b2de`
- Approved V5 four-flange FreeCAD review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-plain-flange-thickness-review-v5/CAT_HEAD_RIGHT_EYE_ALL_FOUR_PLAIN_FLANGE_THICKNESS_REVIEW_V5.FCStd`
  - SHA-256: `8dace070de103c167e343b4bfda0a26b789a87da9cb2c698ce5999635f9b398f`

## Accepted decisions and dimensions

- Right side only. No left mirror, shell-wide integration, STL, G-code, or print
  release was performed.
- The exact V9 eye body is unchanged. Its imported STEP is valid, closed, one
  solid, and self-intersection-free.
- The original approved V5 eye-side flange leaves remain 4.8 mm thick.
- Each flange root is extended inward by 1.5000 mm, using the established local
  inward directions mapped into FreeCAD coordinates:
  - outer pair: `(-1.419, 0.062, -0.483) mm`
  - second/lower pair: `(0.218, -1.398, 0.498) mm`
- A 0.0100 mm coplanar-union overlap is used only to make each exact Boolean
  root deterministic.
- Positive eye/root engagement is proven:
  - outer eye-side root intersection: `253.4144 mm3`
  - second eye-side root intersection: `274.7895 mm3`
- Exact final clearance from the completed eye owner to each approved head-side
  flange is `0.3000 mm`. This is the measured value; the V16 arithmetic claim of
  `0.2900 mm` is not carried forward.
- C006, C046, C048, ears, rear cassette, lower-face ownership, and aluminum
  V0.5-M2 geometry were not edited.

## Validation performed

- Integrated eye plus both exact roots:
  - valid: yes
  - closed: yes
  - solids: 1
  - shells: 1
  - faces: 1178
  - edges: 2342
  - vertices: 1156
  - volume: `7269.56 mm3`
  - self-intersections: 0
- Exported STEP re-import:
  - valid: yes
  - closed: yes
  - solids: 1
  - faces/edges/vertices: `1178 / 2342 / 1156`
  - volume: `7269.55 mm3`
  - self-intersections: 0
- Exact final gaps to the two V5 head-side flange references:
  - outer pair: `0.3000 mm`
  - second pair: `0.3000 mm`

## Rejected or unsafe variants

- V16 remains a held mesh diagnostic. Its triangulated union reports six
  non-adjacent triangle intersections, and OCCT reports two self-intersecting
  wires plus two unorientable regions. Do not use its transfer OBJ as final CAD.
- FreeCAD mesh auto-repair was rejected because it removed 102 facets and opened
  the mesh.
- Microscopic vertex welding from `0.000001` through `0.001 mm` failed to remove
  the V16 intersection set without increasing geometric risk.
- The two apparent intersections in the tessellated V9 derivative are not
  defects in the authoritative V9 STEP, which passes exact solid validation.

## Exact regeneration procedure

There is no standalone shell regeneration command for V17. Rebuild only through
the controlled FreeCAD exact-solid workflow:

1. Import the frozen V9 production STEP.
2. Insert the exact V5 outer and second eye-side flange solids twice each.
3. Translate one copy of each by the full 1.5000 mm inward vector and the other
   by the normalized 0.0100 mm overlap vector.
4. Fuse the two copies per pair, then fuse both roots to the V9 eye owner.
5. Validate one closed solid and zero self-intersections.
6. Export STEP, re-import it, and repeat the solid and intersection checks.

The saved FCStd and re-import-validated STEP are therefore the resumable exact
artifacts. Lack of a scripted exact rebuild remains a documentation limitation,
not authorization to substitute the V16 mesh generator.

## Next physical/visual review

Build one complete right-side context review containing the V17 eye owner, the
complete repaired V3 upper-head owner, the approved V13/V14 lower-face owner,
the two exact V5 head-side flanges, and frozen C046/C048 reinforcement context.
Review that single file for placement, exterior protrusion, flange alignment,
root continuity, reinforcement clearance, and absence of regressions. Only an
accepted right-side assembly may proceed toward the left mirror and HS-11
closure.
