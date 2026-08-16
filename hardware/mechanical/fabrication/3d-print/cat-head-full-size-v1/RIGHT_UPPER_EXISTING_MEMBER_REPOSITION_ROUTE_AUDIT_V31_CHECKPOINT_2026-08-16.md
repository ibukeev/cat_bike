# Right Upper Existing-Member Reposition Route Audit V31 Checkpoint

Date: 2026-08-16

## Status

Read-only route audit complete. No CAD, FreeCAD geometry, STEP, STL, mirror,
production union, slicer project, G-code, or print release was created or
authorized.

Overall result:
`PARTIAL__ONE_EXISTING_MEMBER_HAS_A_TRANSLATION_ROUTE`.

## Current review/output files

- Contract:
  `source/cad-change-control/pilot/right-upper-existing-member-reposition-route-audit-v31.json`
- Generator:
  `source/cad-change-control/audit_right_upper_existing_member_reposition_routes.py`
- Authoritative validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-existing-member-reposition-route-audit-v31/validation-v31.json`
- There is deliberately no V31 geometry artifact.

Validation SHA-256:
`acb76da7731be52ec05713bfa4ffbea27905ca4574b7ab73a93c86d22bdd0725`.

Generator SHA-256:
`0289218c709ba44f6a513d9124829be63ac0a84f08ab7ddc320f7b7052bfd502`.

## Accepted and preserved decisions

- Keep the topology-repaired V4 eye unchanged.
- Keep the accepted V25 right-upper 42-component context unchanged.
- Keep V27 rejected. Its visible Y-root/planks must not be reused.
- Only rigid translation was audited; no rotation or deformation was used.
- The required route gates were:
  - repaired-eye clearance at least `4.0 mm`;
  - positive C001 owner engagement at least `0.1 mm3`;
  - zero positive intersection with every non-owner upper component;
  - translation length no greater than `20 mm`.
- The V26 tapered rail and C009 were evaluated as independent existing
  members. Their simultaneous compatibility was not audited.

## Validation results

### Existing V26 tapered rail

- Distance probes: `305`.
- Clean rigid-translation routes: `0`.
- Decision: reject rigid repositioning of this exact rail as the C001
  correction route.

### Existing C009 member

- Distance probes: `305`.
- Clean right-upper-context routes: `104`.
- Preferred shortest route:
  - translation: `[1.825092, 10.446536, 8.290829] mm`;
  - translation length: `13.4610148471 mm`;
  - repaired-eye clearance: `4.4763410511 mm`;
  - C001 engagement: `5.1278418525 mm3`;
  - other upper-component collisions: none;
  - translated member remains one valid closed solid;
  - volume remains `227.9211976005 mm3`.

This is candidate evidence only. It does not yet prove clearance from the
lower face, ears, eye rear cap, rear cassette, aluminum, hardware, or service
envelopes.

## Rejected or unsafe variants

- Do not reuse V27's added visible bridge/Y-root/planks.
- Do not move the V26 tapered rail rigidly; this audit found no compliant
  route in the controlled envelope.
- Do not delete C009. It remains a valid existing member and attaches to C001.
- Do not treat the preferred C009 vector as an approved CAD move until it
  passes the full-head-context audit and a review artifact is explicitly
  authorized.
- Do not mirror, production-union, export, slice, generate G-code, or release
  structural ASA from this checkpoint.

## Exact regeneration command

    env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
      /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
      hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/audit_right_upper_existing_member_reposition_routes.py \
      --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-upper-existing-member-reposition-route-audit-v31.json

The command intentionally exits nonzero for the partial result. The generated
validation JSON is authoritative.

## Next controlled step

Run a read-only full-head-context audit of the preferred C009 translation
against the frozen lower face, primary ear, eye rear cap, rear cassette,
aluminum interface, and available hardware/service envelopes. If and only if
that audit passes, create a review-only moved-C009 artifact for visual approval.

The separate C001/rail correction remains unresolved and requires a
non-visible strategy; this checkpoint does not authorize new support geometry.
