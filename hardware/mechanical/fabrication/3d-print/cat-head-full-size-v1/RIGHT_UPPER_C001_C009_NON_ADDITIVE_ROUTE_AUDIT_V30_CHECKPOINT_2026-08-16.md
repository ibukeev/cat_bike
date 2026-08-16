# Right Upper C001/C009 Non-Additive Route Audit V30 Checkpoint

Date: 2026-08-16

## Scope and status

V30 is a read-only, JSON-only audit. It does not create, move, trim, union,
mirror, or export geometry. Its result is:

`FAIL__NO_COMPLETE_NON_ADDITIVE_ROUTE`

The audit tested whether a deterministic `4.0 mm` offset of the repaired eye
could support a safe non-additive correction of the accepted C001/C009 owner
context. OCC failed safely while constructing the global offset at both tested
tolerances (`0.01 mm` and `0.05 mm`) with
`NCollection_DataMap::Find`. No cut was attempted and no geometry was saved.

## Preserved decisions and dimensions

- The repaired V4 eye and accepted V25 upper context remain frozen.
- V27's visible Y-root/planks remain rejected and must not be reused.
- Required eye clearance remains `4.0 mm`.
- Minimum positive owner engagement remains `0.1 mm3`.
- C009 remains one valid closed solid with volume `227.9211976005 mm3`.
- C009 still intersects the repaired eye by `27.7282968690 mm3`.
- C009's only positive neighboring-owner attachment is C001.
- Deleting C009 remains held because its structural function has not been
  proven redundant.

## Current files

- Audit script:
  `source/cad-change-control/audit_right_upper_c001_c009_non_additive_routes.py`
- Input contract:
  `source/cad-change-control/pilot/right-upper-c001-c009-non-additive-route-audit-v30.json`
- Validation result:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c001-c009-non-additive-route-audit-v30/validation-v30.json`
- Validation SHA-256:
  `c0e73d7db9b2726ad8021c181691e1a29f9fa259e73defdc4c11ba529d49408a`

## Validation performed

- The checked-in audit script compiles with `python3 -m py_compile`.
- The input and output JSON files parse successfully.
- The audit fails closed when OCC cannot create the requested offset.
- No review geometry, STEP, STL, slicer project, or G-code was generated.

## Exact regeneration command

```bash
env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/audit_right_upper_c001_c009_non_additive_routes.py \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-upper-c001-c009-non-additive-route-audit-v30.json
```

The command is expected to exit non-zero because the audit status is a
controlled failure. The validation JSON is still the authoritative result.

## Next controlled step

Run V31 as a read-only rigid-reposition audit of the existing V26 tapered rail
and C009. Preserve each exact shape and orientation, search translations only,
and require all of the following before proposing any review geometry:

- at least `4.0 mm` repaired-eye clearance;
- at least `0.1 mm3` positive owner overlap;
- zero positive overlap with every non-owner upper component;
- no new bridge, plank, flange, root, or exterior material.

Mirror, production union, STEP/STL export, slicing, G-code, and structural ASA
release remain held.
