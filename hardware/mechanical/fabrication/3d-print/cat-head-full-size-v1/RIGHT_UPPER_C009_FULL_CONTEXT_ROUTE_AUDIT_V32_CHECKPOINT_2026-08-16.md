# Right Upper C009 Full-Context Route Audit V32 Checkpoint

Date: 2026-08-16

## Status

Read-only full-context audit complete. No CAD or FreeCAD geometry, STEP, STL,
mirror, production union, slicer project, G-code, or print release was created
or authorized.

Overall result: `PASS__DECLARED_FROZEN_FULL_CONTEXT_CLEAR`.

The exact existing C009 member may now be used at the audited rigid translation
in a review-only one-sided CAD preview. That preview remains subject to visual
approval and must not be treated as an integrated or printable owner.

## Current review/output files

- Contract:
  `source/cad-change-control/pilot/right-upper-c009-full-context-route-audit-v32.json`
- Audit generator:
  `source/cad-change-control/audit_right_upper_c009_full_context_route.py`
- Authoritative validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c009-full-context-route-audit-v32/validation-v32.json`
- There is deliberately no V32 geometry artifact.

SHA-256:

- generator:
  `00af29cecf54e8276c12a52a06026236f9a0263946bb106b3301d888eec5aea6`
- contract:
  `5f8a92c64d38957467eab0bcf90a4d4eb4463339814a6d702e17dc07c11c5635`
- validation:
  `eb95f2c742266b5bc2910d3b6f6dfe98d5a6e2d2758e420b2d77d5eec2ac4f65`

## Accepted and preserved decisions

- Keep the topology-repaired V4 eye unchanged.
- Keep the accepted V25 right-upper 42-component context unchanged except for
  the future review-only rigid translation of the exact existing C009 member.
- Keep V27 rejected. Its visible Y-root/planks must not be reused.
- Keep the exact V26 tapered rail in place; V31 proved that it has no clean
  rigid-translation route.
- Use only the V31 preferred C009 translation:
  `[1.825092, 10.446536, 8.290829] mm`.
- Do not rotate, resize, trim, deform, replace, or add material to C009.
- Preserve the separate unresolved C001/rail problem as a distinct work item.

## Validation performed and results

The translated C009 remains one valid closed solid with `38` faces and volume
`227.9211976005 mm3`.

Primary relationship gates:

- repaired-eye clearance: `4.4763410511 mm`;
- C001 owner engagement: `5.1278418525 mm3`;
- non-owner right-upper collisions: zero.

Exact frozen-neighbor checks all have zero intersection:

- right primary ear: `51.0448 mm` clearance;
- right eye rear cap: `3.3412 mm` clearance;
- outer head flange: `28.3230 mm` clearance;
- lower head flange: `75.2365 mm` clearance;
- approved C046: `97.0926 mm` clearance;
- approved C048: `94.4302 mm` clearance;
- right lower-face component 001: `58.6636 mm` clearance.

Conservative declared-context checks:

- lower-face components 002-060: no AABB overlap; nearest AABB separation is
  `57.6835 mm`;
- V5 rear-cassette owners: no AABB overlap;
- right aluminum rail: `26.9254 mm` conservative clearance after including the
  full `19 x 19 mm` profile radius.

The audit hash-pins every declared input. It reconstructs only the accepted
rigid translation in memory and writes deterministic JSON. It does not save
FreeCAD geometry or export a fabrication artifact.

## Rejected or unsafe variants

- Do not reuse V27's visible bridge/Y-root/planks.
- Do not rigidly reposition the V26 tapered rail.
- Do not use the old destructive C009 cap trim; it would remove about `96.85%`
  of the member.
- Do not delete C009; it retains positive C001 engagement in the accepted
  route.
- Do not infer full service-sweep approval from this static context audit.
- Do not mirror, production-union, export, slice, generate G-code, or release
  structural ASA from V32.

## Exact regeneration command

    env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
      /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
      hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/audit_right_upper_c009_full_context_route.py \
      --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-upper-c009-full-context-route-audit-v32.json

## Next physical/visual review step

Create one review-only FreeCAD file that shows the accepted V25 right-upper
context, repaired V4 eye, and exact C009 member moved by the V32 vector. The
file must contain no added support geometry and must clearly distinguish the
moved existing member from the frozen context. The user should review only
whether the moved C009 is visually unobtrusive and plausibly rooted to C001.

After that review, preserve or reject this C009 route explicitly. The separate
C001/rail correction still requires a non-visible strategy before HS-11 can
advance to exact bilateral validation.
