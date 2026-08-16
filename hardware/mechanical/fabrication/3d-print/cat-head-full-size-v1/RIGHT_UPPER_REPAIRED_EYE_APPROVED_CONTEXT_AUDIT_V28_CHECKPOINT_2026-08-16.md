# Right Upper Repaired-Eye Approved-Context Audit V28 Checkpoint

Status: **read-only JSON audit complete; fail-closed on a `0.000044 mm` C012 precision delta; no geometry artifact created and not a print source**.

## Purpose and scope

Substitute the topology-repaired V4 right-eye STEP into the last accepted V25
42-component right-upper context at zero transform and measure every exact
component/eye contact. This audit changes no upper component, creates no CAD
review file, and explicitly excludes the user-rejected V27 rail-root proposal.

## Controlled inputs

- V25 accepted context FCStd SHA-256: `ef3f1668f9c55e8c3744b1bac98c7f599a98251929aaed46c549db3b1214a775`.
- V25 validation SHA-256: `26bcaff8685fa8983dd961a1f3953ca5301afb0e6d83e09bc8739185053e8b6c`.
- V4 repaired-eye STEP SHA-256: `1ae9408d908edc9cf7e8d5ac2dd0c5bdd8a36f0f184d2bab3e05dafa1ef41258`.
- V4 validation SHA-256: `8f0f6e29774e8e6278b2fe6e05876844707876779db825102b69273750284bb1`.

## Current output

- Validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-repaired-eye-approved-context-audit-v28/validation-v28.json`.
- Validation SHA-256: `62f5de699ab3f27ef50e283026d53084f85eca1b3a1d75108db7deda831c8d03`.
- Contract: `source/cad-change-control/pilot/right-upper-repaired-eye-approved-context-audit-v28.json`.
- Generator: `source/cad-change-control/generate_right_upper_repaired_eye_approved_context_audit.py`.
- No FCStd, STEP, STL, mesh, slice, or other geometry artifact was written.

## Exact results

- All 42 accepted upper-component Boolean checks completed.
- Positive-volume contacts above `1e-6 mm3`: only C001 and C009.
- C001/eye intersection: `100.5990444968 mm3`.
- C009/eye intersection: `27.7282968690 mm3`.
- C019: `4.22075409e-8 mm3`, below the positive-contact threshold.
- Approved C027: zero intersection and `5.3207643447 mm` clearance — pass.
- Approved upper C012: zero intersection and `3.9999557582 mm` measured clearance. The strict V28 gate expected `4.000000 mm` with only `0.000020 mm` tolerance, so it fails by `0.000024 mm` beyond that audit tolerance. This is `0.000044 mm` below nominal and is not a material collision.
- The repaired eye and original V25 eye give the same per-component contact results within `0.01 mm3`; the repair introduces no new upper-head contact.
- Repaired eye: one valid closed solid, `1178` faces, unchanged bounds, maximum bidirectional vertex delta `0.000004075 mm`, volume delta `-0.006629 mm3`.
- V27 geometry is absent.

## Decision and holds

- Preserve the repaired V4 eye and accepted V25 C012/C027 components unchanged.
- Do not disguise the C012 precision-gate miss as a V28 pass; retain the JSON result as fail-closed evidence.
- HS-11 geometry work is now narrowed to C001 and C009. C019 is not a trim target. C012 and C027 have zero positive overlap.
- The V27 added rectangular Y-root/plank construction is rejected by the user because it creates unexplained material in front of the eye. Do not reuse it.
- Mirror, production union, STEP/STL export, slicing, G-code, and structural ASA release remain held.

## Exact regeneration

From the repository root:

```bash
env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/generate_right_upper_repaired_eye_approved_context_audit.py \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-upper-repaired-eye-approved-context-audit-v28.json
```

The generator refuses to overwrite an existing output directory.

## Next controlled step

Design the minimum subtractive/relocation solution for C001 and C009 using the existing V22/V23 exact anchors and the repaired V4 eye. It must add no visible bridge, stick, horn, or loose block; preserve the exterior; keep intentional reinforcement owner-connected; and satisfy the `4.0 mm` internal clearance contract before any bilateral work.
