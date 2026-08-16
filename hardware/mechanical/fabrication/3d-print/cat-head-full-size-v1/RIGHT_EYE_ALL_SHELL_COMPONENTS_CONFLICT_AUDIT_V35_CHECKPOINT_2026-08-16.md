# Right Eye All-Shell Components Conflict Audit V35 Checkpoint — 2026-08-16

## Status

`FAIL__EYE_INTERSECTS_FROZEN_SHELL__NO_PRINT_RELEASE`

V35 is a complete, read-only right-eye-versus-right-shell collision matrix.
It changes no CAD geometry and creates no CAD document. The frozen repaired
right eye is not collision-free and must not be used for final ASA printing.

## Approved scope

- Use the hash-pinned V4 repaired right-eye STEP without any transform.
- Check it against all 41 V34 retained right-upper components, C001 through
  C042 excluding deleted C009.
- Check it against all 60 V14 right-lower components, including the repaired
  V13 lower C001 and frozen V14 C002 through C060.
- Run exact OCCT common/distance operations wherever the component imports as
  a valid solid.
- A non-sewn OBJ may be classified clear only when its frozen bounding box has
  a strictly positive separation from the eye bounding box.
- Fail on any intersection volume greater than `0.000001 mm3`.
- Do not trim, move, cut, fuse, heal, mirror, export, slice, or approve print
  geometry.

## Current review files

- Validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-shell-components-conflict-audit-v35/validation-v35.json`
- Contract:
  `source/cad-change-control/pilot/right-eye-all-shell-components-conflict-audit-v35.json`
- Validator:
  `source/cad-change-control/audit_right_eye_all_shell_components_conflicts_v35.py`
- Frozen V34 visual context:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c009-deletion-review-v34/CAT_HEAD_RIGHT_UPPER_C009_DELETION_REVIEW_V34.FCStd`

## Output hashes

- Validation SHA-256:
  `bdc523254a8688e2c858fb4c9024edf0c62b2ac5de09689ddc9c4023a6b173c6`
- Contract SHA-256:
  `0727a368f06a4ec88cca5d5c1666cf7932b3c4474d4dfd2b729d361a6f6b3977`
- Validator SHA-256:
  `b3eefa68d307cba8d7f32d171286962de8165a8dd663f018731c31b546d657de`

## Validation result

All 101 required shell components were resolved with zero Boolean errors and
all source hashes matching.

| Owner | Component | Intersection volume | Intersection bounds, minimum → maximum (mm) |
| --- | --- | ---: | --- |
| Right upper | C001 | `100.599044497 mm3` | `(55.122082, 70.783736, 118.477333)` → `(103.736830, 94.689428, 178.656998)` |
| Right lower | C001 | `7.090875007 mm3` | `(32.576833, 49.621489, 118.477333)` → `(103.466622, 73.157206, 126.394501)` |
| Right lower | C012 | `1.045758674 mm3` | `(31.388871, 49.328976, 123.994954)` → `(33.507938, 52.312822, 126.056635)` |
| Right lower | C013 | `7.726050942 mm3` | `(32.496249, 49.328976, 124.604873)` → `(39.969063, 60.900548, 154.740775)` |

Total positive intersection volume is `116.461729119 mm3`. C009 is absent as
required by V34 and is not one of these contacts.

Fifty-five of the 59 frozen lower OBJ components reconstructed as valid OCCT
solids. Four source OBJs did not sew in OCCT, but their frozen bounding boxes
prove they cannot touch the eye:

| Lower component | Strict distance lower bound |
| --- | ---: |
| C009 | `78.582916 mm` |
| C016 | `66.615013 mm` |
| C022 | `94.158269 mm` |
| C033 | `73.218373 mm` |

This is an exhaustive collision test, not a containment test. It does not by
itself prove that all eye material remains behind the exterior skin, and it
does not validate insertion path, access, service, bilateral geometry,
connected production bodies, slicing, or physical fit.

## Rejected or unsafe interpretations

- V34's successful C009 deletion validation is not global eye clearance.
- The cyan corner visible outside the shell is not dismissed as a rendering
  artifact; V35 confirms real eye/shell intersections.
- Do not fix these contacts by adding unexplained planks, moving the eye, or
  deleting arbitrary shell faces.
- Do not use the incomplete first V35 run as evidence. It was moved to
  `/tmp/right-eye-all-shell-components-conflict-audit-v35-incomplete`; the
  hash-pinned validation above is the authoritative result.

## Exact regeneration command

From the repository root, first remove or archive the existing V35 output
directory because the validator intentionally refuses to overwrite evidence,
then run:

```bash
env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/audit_right_eye_all_shell_components_conflicts_v35.py \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-eye-all-shell-components-conflict-audit-v35.json
```

Exit code `1` is the expected fail-closed result while the four intersections
remain.

## Next review steps

1. Compare the independent audit from the other Codex session against these
   four component identities, volumes, and locations.
2. Resolve any discrepancy before changing geometry.
3. Create one explicit change contract per confirmed interfering component;
   preserve the eye, exterior surfaces, aluminum interface, ears, translucent
   panels, and already approved clearances.
4. Rerun this full 101-component matrix after each accepted geometry change.
5. Do not start final structural ASA printing until the matrix has zero
   positive contacts and the separate containment, topology, bilateral,
   service, slicer, and physical gates also pass.
