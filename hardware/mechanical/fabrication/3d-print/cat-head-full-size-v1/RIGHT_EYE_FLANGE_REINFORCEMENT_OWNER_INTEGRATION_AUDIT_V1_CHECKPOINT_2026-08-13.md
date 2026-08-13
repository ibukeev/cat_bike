# Right Eye Flange + Reinforcement Owner Integration Audit V1 — 2026-08-13

## Status

HS-11 right-side integration is **fail-closed**. The approved locations and
clearances remain accepted, but they cannot yet be promoted as printable owner
unions. FreeCAD/OCCT proves that the two eye-side V3 flange roots and approved
C048 meet their intended copied owners at `0.0000 mm` without measurable
volumetric embed. The resulting Boolean is empty/invalid, so no integration,
mirror, STL, G-code, or print release was accepted.

## Audit files

- FreeCAD:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-reinforcement-owner-integration-review-v1/CAT_HEAD_RIGHT_EYE_FLANGE_REINFORCEMENT_OWNER_INTEGRATION_AUDIT_V1.FCStd`
- Blender staging/context:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-reinforcement-owner-integration-review-v1/CAT_HEAD_RIGHT_EYE_FLANGE_REINFORCEMENT_OWNER_INTEGRATION_REVIEW_V1.blend`
- Staging validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-reinforcement-owner-integration-review-v1/validation-v1.json`
- Contract:
  `config/right-eye-flange-reinforcement-owner-integration-review-v1.json`

## Frozen accepted geometry

- V3 flange centers, axes, mating faces, `2.8 mm` bores, and `0.3 mm` gaps.
- C046 rigid offset `4.2290 mm`; V9-eye clearance `4.6063 mm`.
- C048 eye-side trim `8.4611 mm`; V9-eye clearance `4.0317 mm`.
- V9 bucket and separate cap; cap service gap remains `0.0239 mm`.
- V10 shell exterior, C006, and aluminum V0.5-M2.

## Validation performed

- Frozen right upper/lower containers are closed mesh collections with `42`
  and `63` connected solids respectively; whole-container Boolean fusion is
  unsafe because it can discard untouched solids.
- OCCT owner-root checks:
  - outer head flange to upper head: `160.1687 mm3` overlap;
  - lower head flange to lower face: `269.2872 mm3` overlap;
  - C046 to lower face: `38.4261 mm3` overlap;
  - C048 to lower face: `0.0000 mm` contact only;
  - outer/lower eye flanges to V9 bucket: `0.0000 mm` contact only.
- The attempted eye-bucket fuse produced an empty zero-solid result and was
  deleted. The upper/lower whole-owner fuses also failed and were not saved as
  approved geometry.
- The audit FCStd passes ZIP validation (`1,695,245` bytes).

## Required minimal correction

Create an **internal root-embed-only** one-side proposal. Extend only the owner
side of the two eye flanges and C048 by a small controlled depth into their
receiving solids. Do not move holes, mating faces, flange axes, shell exterior,
eye exterior, or the approved eye-clearance surfaces. Validate positive root
volume, component-local OCCT unions, all original owner-solid preservation,
the two M2.5 through paths, and the V9 cap service gap before review.

## Rejected or unsafe methods

- Do not use a Blender whole-owner Boolean: it drops unrelated solids in the
  42/63-solid source containers.
- Do not use a compound or joined mesh as proof of structural integration.
- Do not accept zero-depth face contact as a printable owner root.

## Exact regeneration command

```sh
python3 -m py_compile hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_flange_reinforcement_owner_integration_review_v1.py
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/30-reinforcement-baselines/requested-reinforcement-additions-review-v1/requested-reinforcement-additions-review-v1.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_flange_reinforcement_owner_integration_review_v1.py
```

## Next review

Review only the minimal internal root extensions for the two eye flanges and
C048 in receiving-owner context. Once approved and digitally fused, complete
the right-side HS-11 validation, then exact-mirror and repeat bilaterally.
