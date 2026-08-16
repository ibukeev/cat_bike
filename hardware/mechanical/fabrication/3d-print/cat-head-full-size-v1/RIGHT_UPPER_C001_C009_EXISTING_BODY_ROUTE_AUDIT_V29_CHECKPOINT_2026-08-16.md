# Right Upper C001/C009 Existing-Body Route Audit V29 Checkpoint

Status: **read-only route audit complete; direct C001 rail continuation rejected; no geometry artifact created and not a print source**.

## Purpose and scope

Test whether the existing tapered C001 rail from the V26 diagnostic can be
continued directly into the accepted C001 owner without adding another
visible stick, bridge, horn, or block. Separately measure C009's accepted-owner
attachment and eye contact. This audit writes deterministic JSON only and
explicitly excludes the user-rejected V27 Y-root construction.

## Controlled inputs

- V25 accepted upper context FCStd SHA-256: `ef3f1668f9c55e8c3744b1bac98c7f599a98251929aaed46c549db3b1214a775`.
- V26 diagnostic FCStd SHA-256: `2ff7be047b3b2a3ddf52cfaacad932f7fa8a002c4180c373552d685762dd7dae`.
- V4 repaired-eye STEP SHA-256: `1ae9408d908edc9cf7e8d5ac2dd0c5bdd8a36f0f184d2bab3e05dafa1ef41258`.
- V26 transient diagnostic rail offset: `(+2.1930, -5.7405, +1.9350) mm`.
- Required eye clearance: at least `4.0 mm`.
- Required direct-root overlap with C001: at least `0.1 mm3`.
- Maximum direct continuation envelope: `30.0 mm`.

## Current output

- Validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c001-c009-existing-body-route-audit-v29/validation-v29.json`.
- Validation SHA-256: `d0a89a0763ee9a8a012967e548b4b5f96ec3a46b5b2ce069802b70678d5c9d7b`.
- Contract: `source/cad-change-control/pilot/right-upper-c001-c009-existing-body-route-audit-v29.json`.
- Audit generator: `source/cad-change-control/audit_right_upper_c001_c009_existing_body_routes.py`.
- No FCStd, STEP, STL, mesh, slice, G-code, or other geometry artifact was written.

## Exact results

- The V26 tapered rail was identified by its `174.417269 mm3` volume and the
  documented transient offset.
- Its repaired-eye clearance is `4.261594 mm` and its C001 distance is
  `4.277956 mm` in the audited position.
- Every planar cap direction was tested with a maximum-envelope contact check
  followed by bounded binary refinement.
- Clean direct existing-face continuation routes: **zero**.
- Therefore extending this rail directly into C001 is not a viable bounded
  correction under the `4.0 mm` eye-clearance and `0.1 mm3` root-overlap
  contracts.
- C009 is one valid closed solid, volume `227.921198 mm3`.
- C009 intersects the repaired eye by `27.728297 mm3`.
- C009's only positive-volume upper-component neighbor is C001; it is not an
  independently rooted owner.

## Accepted decisions and rejected variants

- Keep the repaired V4 eye and the accepted V25 C012/C027 components unchanged.
- Do not create or reuse the rejected V27 rectangular Y-root/plank geometry.
- Do not create a direct extension from the V26 rail: V29 proves that route has
  no clean solution inside the controlled envelope.
- Do not delete or trim C009 yet. Its eye collision is proven, but its only
  owner attachment is C001 and removal still requires an owner-preserving
  replacement/absorption contract.
- Mirror, production union, STEP/STL export, slicing, G-code, and structural
  ASA release remain held.

## Validation performed

- All three inputs were SHA-256 verified before audit.
- Accepted V25 C001/C009 owner identities were checked against the full
  42-component manifest.
- Candidate continuations were transient measurements only; the audit saved no
  shape and modified no source document.
- The audit script compiles with `python3 -m py_compile`.
- Interrupted pre-optimization audit runs produced no retained output; V29 is
  the sole deterministic result.

## Exact regeneration

From the repository root:

```bash
env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/audit_right_upper_c001_c009_existing_body_routes.py \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-upper-c001-c009-existing-body-route-audit-v29.json
```

The audit refuses to overwrite an existing output directory.

## Next controlled step

Audit two non-additive paths against the accepted V25 context: (1) whether C009
can be removed and its required root function absorbed by existing C001 wall
material, and (2) whether C001's interfering local material can be shortened or
locally clipped while preserving its existing owner connection and exterior.
Generate no visible bridge/root candidate until one route has exact numeric
clearance and owner-engagement evidence.
