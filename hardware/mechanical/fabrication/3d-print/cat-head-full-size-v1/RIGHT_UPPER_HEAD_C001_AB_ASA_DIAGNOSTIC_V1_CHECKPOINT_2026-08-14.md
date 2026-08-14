# Right Upper Head C001 A/B ASA Diagnostic V1 Checkpoint — 2026-08-14

## Status

`HOLD` — the exact user-saved orientation slices successfully, but it is not a
print release because the combined object/brim/support envelope violates the
frozen `10 mm` minimum margin on the MK4 bed.

No CAD geometry, A/B feature, aluminum interface, scale, or user-saved rotation
changed in this workstream.

## Current files

- Frozen user orientation source:
  `output/50-slicer-projects/right-upper-head-c001-ab-orientation-handoff-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ORIENTATION_HANDOFF_V1.3mf`
- ASA diagnostic slicer project:
  `output/50-slicer-projects/right-upper-head-c001-ab-asa-diagnostic-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ASA_DIAGNOSTIC_V1.3mf`
- Machine-readable validation:
  `output/50-slicer-projects/right-upper-head-c001-ab-asa-diagnostic-v1/validation-v1.json`
- Slicer contract:
  `config/right-upper-head-c001-ab-asa-diagnostic-v1.json`
- Deterministic preparation script:
  `source/prepare_right_upper_head_c001_ab_asa_diagnostic_v1.py`
- Local diagnostic G-code, deliberately not committed or released:
  `output/50-slicer-projects/right-upper-head-c001-ab-asa-diagnostic-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ASA_DIAGNOSTIC_V1.gcode`

## Accepted frozen decisions

- Source SHA-256:
  `0941d65a81594754d33382a584ad2963ed2c14f6034a1a8534d724d9cca8c8a6`
- Diagnostic 3MF SHA-256:
  `423584124419c803feff141521f7663c26b722ba686aa20acc7e15402f7343b1`
- Source and diagnostic `3D/3dmodel.model` SHA-256:
  `482d7ceba6420d2dbbdb104dbed70da5d1c2f69f0bb998e0054eeb5069eed6d5`
- One manifold part, `3418` facets, `77958.335938 mm3`, scale `1.0`.
- Exact saved 3MF transform:
  `[0.622046419, -0.267301093, -0.735940472, -0.069302815, -0.955029261, 0.288298858, -0.779907284, -0.128332526, -0.61259725, 111.575601, 105.453971, 55.0493613]`
- Frozen aluminum interface: `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2`.

## Diagnostic slicer contract

- Original Prusa MK4, `250 x 210 x 220 mm`, `0.4 mm` nozzle.
- `0.20 mm` layer height.
- Installed `Prusament ASA @MK4` baseline.
- Nozzle `260 C`; bed `105 C` first layer and `110 C` thereafter.
- Automatic snug supports, `45 deg` threshold.
- Outer-only `8 mm` brim with `0.1 mm` separation.

## Validation performed

The deterministic derivative preserves every source ZIP member byte-for-byte
except `Metadata/Slic3r_PE.config`. The geometry member and exact object
transform are unchanged.

Diagnostic slice command:

```bash
prusa-slicer --dont-arrange --export-gcode \
  --output hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-head-c001-ab-asa-diagnostic-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ASA_DIAGNOSTIC_V1.gcode \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-head-c001-ab-asa-diagnostic-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ASA_DIAGNOSTIC_V1.3mf
```

PrusaSlicer `2.7.4` completed the slice and generated supports and brim:

- Estimated time: `14h 17m 34s`.
- ASA: `54123.65 mm`, `130.18 cm3`, `139.30 g`.
- Diagnostic G-code SHA-256:
  `c421bb4995b725c1f31062324b3f61d3ce3e8c8917fb7255ea898c4be0ea12f2`.
- Diagnostic G-code size: `20259503` bytes.

Object bounding box is `201.086257 x 197.072832 x 126.379858 mm`.
The first-layer brim/support footprint reported by generated `M555` is
`207.248 x 189.492 mm`, from `(15.4146, 4.05255)` to
`(222.6626, 193.54455)`. Combining that with the full object envelope gives
edge margins:

- Left: `15.4146 mm` — pass.
- Right: `27.3374 mm` — pass.
- Front: `4.05255 mm` — fail.
- Rear: `1.874795 mm` — fail.

The `10 mm` edge-margin gate therefore fails. The G-code is diagnostic only,
is not committed, and must not be sent to the printer.

## Rejected or unsafe variants

- Direct PrusaSlicer `--export-3mf` was rejected because it preserved geometry
  but dropped the embedded print profile.
- A Snap-private `/tmp` export was rejected because it was not a stable,
  inspectable project artifact.
- The source orientation project remains unchanged and is not overwritten.
- The diagnostic G-code is not a print release because it fails the XY-margin
  gate.
- Yaw-only adjustment is insufficient: the earlier search found a best
  centered minimum margin of only `8.047983 mm` at `+5.8 deg` relative yaw.

## Exact regeneration

From repository root:

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/prepare_right_upper_head_c001_ab_asa_diagnostic_v1.py \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-head-c001-ab-orientation-handoff-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ORIENTATION_HANDOFF_V1.3mf \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-head-c001-ab-asa-diagnostic-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ASA_DIAGNOSTIC_V1.3mf
```

Then run the diagnostic slice command from the validation section.

## Next physical review

Open the ASA diagnostic 3MF and use the exact saved orientation as the visual
baseline. In a **new derivative only**, make a small non-yaw tilt adjustment
that reduces the projected Y footprint while keeping the under-ear opening as
the bed-facing region. Re-slice, then release only if the combined full object,
brim, and support envelope has at least `10 mm` margin on all four MK4 bed
edges. Do not change scale or CAD geometry.
