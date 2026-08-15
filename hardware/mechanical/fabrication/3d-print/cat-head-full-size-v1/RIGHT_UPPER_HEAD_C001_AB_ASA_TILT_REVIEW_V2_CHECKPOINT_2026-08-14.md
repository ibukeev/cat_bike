# Right Upper Head C001 A/B ASA Tilt Review V2 Checkpoint — 2026-08-14

## Status

`HOLD_VISUAL_REVIEW` — the isolated `-20 deg` world-X tilt candidate passes the
numeric MK4 object/support/brim margin gate. It is not a print release until the
user visually confirms the bed-facing under-ear region and support layout.

No CAD geometry, scale, A/B feature, or aluminum interface changed.

## Current review files

- Open in PrusaSlicer:
  `output/50-slicer-projects/right-upper-head-c001-ab-asa-tilt-review-v2/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ASA_TILT_REVIEW_V2.3mf`
- Validation:
  `output/50-slicer-projects/right-upper-head-c001-ab-asa-tilt-review-v2/validation-v2.json`
- Contract:
  `config/right-upper-head-c001-ab-asa-tilt-review-v2.json`
- Reproducible transform tool:
  `source/create_right_upper_head_c001_ab_tilt_candidate.py`
- Local diagnostic G-code, not committed or released:
  `output/50-slicer-projects/right-upper-head-c001-ab-asa-tilt-review-v2/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ASA_TILT_REVIEW_V2.gcode`

## Frozen source and exact change

- ASA source SHA-256:
  `423584124419c803feff141521f7663c26b722ba686aa20acc7e15402f7343b1`.
- Review 3MF SHA-256:
  `6d25a11556a28ee9152acde62cd05e2ed7d4236d383b5e2cda4a038ef79d7174`.
- Relative world-X tilt: `-20.0 deg`.
- Relative yaw: `0.0 deg`.
- Final measured Y recenter: `+1.958 mm`.
- Scale: `1.0`.
- Final transform:
  `[0.622046419, -0.502887330333, -0.600135472737, -0.069302815, -0.798829932463, 0.597551554171, -0.779907284, -0.330113726935, -0.531760806403, 117.533548087, 103.110816519, 72.4984271569]`.

The script changes only the 3MF build-item transform. Mesh vertices,
triangles, part count, manifold state, volume, ASA settings, automatic snug
supports, and `8 mm` outer brim remain unchanged.

## Search and rejected orientations

- `-12 deg`: first layer `207.149 x 195.359 mm`; rejected.
- `-16 deg`: first layer `205.297 x 191.189 mm`; rejected.
- `-18 deg`: first layer `205.308 x 190.847 mm`; rejected.
- `-20 deg` plus measured Y recenter: first layer
  `205.824 x 186.924 mm`; numeric pass.

The final generated `M555` footprint is
`X20.7661 Y11.538 W205.824 H186.924`, producing margins:

- Left: `20.7661 mm`.
- Right: `23.4099 mm`.
- Front: `11.538 mm`.
- Rear: `11.538 mm`.

## Slice result

- PrusaSlicer `2.7.4`.
- Estimated time: `14h 36m 5s`.
- ASA: `53909.71 mm`, `129.67 cm3`, `138.74 g`.
- Local G-code SHA-256:
  `e7e3e0f9b3014f33866168bcdc2e3730723770ab3ad0d3b0708e1b1e18331062`.
- Local G-code is not committed and must not be printed before visual approval.

## Exact regeneration

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/create_right_upper_head_c001_ab_tilt_candidate.py \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-head-c001-ab-asa-diagnostic-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ASA_DIAGNOSTIC_V1.3mf \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-head-c001-ab-asa-tilt-review-v2/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ASA_TILT_REVIEW_V2.3mf \
  --tilt-deg -20 --shift-y-mm 1.958
```

Then slice with:

```bash
prusa-slicer --dont-arrange --export-gcode \
  --output hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-head-c001-ab-asa-tilt-review-v2/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ASA_TILT_REVIEW_V2.gcode \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-head-c001-ab-asa-tilt-review-v2/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ASA_TILT_REVIEW_V2.3mf
```

## Next physical review

Open the V2 3MF in PrusaSlicer. Confirm from several angles that the under-ear
opening remains the intended bed-facing region. Switch to Preview after slicing
and inspect the first layer, all support contact regions, and the complete brim.
Approve only if the orientation is physically acceptable; numeric bed margins
already pass. No CAD edit or metal-interface review is required for this step.
