# Right Upper As-Printed 10 mm Brim Layout V1 Checkpoint — 2026-08-25

## Status

`PASS_LAYOUT__HOLD_SOURCE_MESH_AND_PHYSICAL_FIRST_LAYER`

The user approved `RIGHT-UPPER 10MM BRIM LAYOUT V1` on 2026-08-25. The
approved slicer placement and 10 mm outer brim fit the Original Prusa MK4 bed.
No CAD object, STL triangle, scale, FreeCAD file, or source 3MF was changed.

This is a slicer-layout pass, not an unconditional print release. The frozen
source is non-manifold, and the full first layer still requires direct physical
observation before committing to the approximately 16-hour ASA job.

## Current review and output files

- PrusaSlicer project:
  `output/50-slicer-projects/right-upper-as-printed-10mm-brim-layout-v1/CAT_HEAD_RIGHT_UPPER_AS_PRINTED_10MM_BRIM_LAYOUT_V1.3mf`
- Diagnostic G-code, not release-approved:
  `output/50-slicer-projects/right-upper-as-printed-10mm-brim-layout-v1/CAT_HEAD_RIGHT_UPPER_AS_PRINTED_10MM_BRIM_LAYOUT_V1.gcode`
- First-layer review evidence:
  `output/50-slicer-projects/right-upper-as-printed-10mm-brim-layout-v1/first-layer-brim-support-evidence-v1.png`
- Vector evidence:
  `output/50-slicer-projects/right-upper-as-printed-10mm-brim-layout-v1/first-layer-brim-support-evidence-v1.svg`
- Validation:
  `output/50-slicer-projects/right-upper-as-printed-10mm-brim-layout-v1/validation-v1.json`
- Numeric contract:
  `config/right-upper-as-printed-10mm-brim-layout-v1.json`
- Deterministic generator:
  `source/create_right_upper_as_printed_10mm_brim_layout_v1.py`
- Independent validator and evidence renderer:
  `source/validate_right_upper_as_printed_10mm_brim_layout_v1.py`

## Frozen sources

- Source `assembly.3mf` SHA-256:
  `ac800ac7470c61cf4d640af6d652b25ac080142826aaadb4d24842bb9440720b`
- Source `assembly.stl` SHA-256:
  `6b7ced6a6cb86e5d7635f622f6e18df53bf616a378823443f98dd8aa1e4c2f4d`
- Review 3MF SHA-256:
  `8b2efa7a9d77a46f7fe0a82187518ffebf55d02b86a6eeb080362611293b2c4a`
- Diagnostic G-code SHA-256:
  `c55b2455556b814c166e98b1ef7d6679641cc40c193c8eff15360c8346e29509`

Archive comparison proves that only `3D/3dmodel.model` and
`Metadata/Slic3r_PE.config` changed. Within those members, only the single
build-item transform plus `brim_type` and `brim_width` changed. The 5,036 mesh
vertices, 9,556 triangles, all other archive members, and scale `1.0` are
unchanged.

## Accepted placement and process contract

- Additional world-X tilt: `+22.0 deg`.
- Additional world-Z rotation: `-9.0 deg`.
- Bed center: `X 125.0 mm`, `Y 105.0 mm`.
- Lowest mesh point: `Z 0.0 mm`.
- Final 3MF transform:
  `[-0.362612279462, -0.819482334334, 0.443802927262, -0.664989563555, 0.561156369453, 0.492841160774, -0.652917464179, -0.116414057070, -0.748429390465, 116.437612950, 110.220650427, 58.350728023]`.
- Outer-only brim: `10.0 mm`, separation `0.1 mm`.
- Retained profile: Prusament ASA, MK4IS 0.4 mm nozzle, `0.20 mm` layers,
  `25%` grid infill, three perimeters, automatic snug supports at `40 deg`.

## Validation performed

- Generator source/hash/topology checks: `PASS`.
- Source preservation and exact permitted archive-difference check: `PASS`.
- Transform, orthonormal scale, determinant, and centered bounds: `PASS`.
- PrusaSlicer 2.7.4 diagnostic slice: `PASS`.
- Actual first-layer extrusion bed margin gate, required `>=5 mm`: `PASS`.
- Actual margins left/right/front/rear:
  `14.891 / 14.304 / 10.759 / 15.375 mm`.
- Brim path found: `PASS`, outer-only `10 mm`.
- First-layer support paths found: `PASS`, automatic snug support retained.
- Estimated print time: `16h 12m 34s`.
- Estimated filament: `91,082.53 mm`, `219.08 cm3`, `234.41 g`.

## Rejected or unsafe variants

- Frozen source placement: approximately `214.0 x 201.9 mm`; rejected for a
  10 mm perimeter allowance because front/rear clearance is insufficient.
- Z rotation alone: best observed footprint approximately
  `214.83 x 198.96 mm`; rejected because it still cannot provide the approved
  10 mm allowance.
- `+15 deg` X tilt: only approximately `0.15 mm` reserve outside the
  conservative 10 mm envelope; rejected as too tight.
- Printing without a brim: physically failed in the user-provided print.
- Unattended full print from the diagnostic G-code: held because the source
  mesh remains non-manifold and the support islands require first-layer
  physical confirmation.

PrusaSlicer `--info` reports the unchanged source as: 9,556 facets,
non-manifold, 75 open edges, 16 reversed facets, 48 backwards edges, and 166
parts. Slicing completes, but slicer repair is not proof of a structurally
valid CAD owner.

## Exact regeneration

From the repository root:

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/create_right_upper_as_printed_10mm_brim_layout_v1.py \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-as-printed-working-assembly-v1/assembly.3mf \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-as-printed-working-assembly-v1/assembly.stl \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-as-printed-10mm-brim-layout-v1/CAT_HEAD_RIGHT_UPPER_AS_PRINTED_10MM_BRIM_LAYOUT_V1.3mf
```

```bash
prusa-slicer --dont-arrange --export-gcode \
  --output hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-as-printed-10mm-brim-layout-v1/CAT_HEAD_RIGHT_UPPER_AS_PRINTED_10MM_BRIM_LAYOUT_V1.gcode \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-as-printed-10mm-brim-layout-v1/CAT_HEAD_RIGHT_UPPER_AS_PRINTED_10MM_BRIM_LAYOUT_V1.3mf
```

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/validate_right_upper_as_printed_10mm_brim_layout_v1.py \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/right-upper-as-printed-10mm-brim-layout-v1.json \
  --source-project hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-as-printed-working-assembly-v1/assembly.3mf \
  --source-stl hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-as-printed-working-assembly-v1/assembly.stl \
  --review-project hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-as-printed-10mm-brim-layout-v1/CAT_HEAD_RIGHT_UPPER_AS_PRINTED_10MM_BRIM_LAYOUT_V1.3mf \
  --gcode hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-as-printed-10mm-brim-layout-v1/CAT_HEAD_RIGHT_UPPER_AS_PRINTED_10MM_BRIM_LAYOUT_V1.gcode \
  --report hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-as-printed-10mm-brim-layout-v1/validation-v1.json \
  --evidence-svg hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-as-printed-10mm-brim-layout-v1/first-layer-brim-support-evidence-v1.svg
```

## Next physical-review steps

1. Open the review 3MF and inspect layer 1. Orange is the 10 mm model brim;
   the broad blue/cyan regions are separate support first-layer paths.
2. Clean the satin sheet with the preparation appropriate for ASA and verify
   the enclosure is at the intended temperature.
3. Start the print while present and observe the entire first layer.
4. Stop immediately if the central brim or any separate support island curls,
   gaps, or lifts. Do not let a detached island turn into another spaghetti
   failure.
5. If every island remains bonded, record a photograph before authorizing the
   remainder of the print or treating this layout as physically proven.
