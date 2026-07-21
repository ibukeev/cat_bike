# Controller Box V0

## Purpose

Provide a review-first, 3D-printable enclosure for the Cat Bike's standalone
Pixelblaze controller. This V0 intentionally excludes the battery, branch fuse
block, main disconnect, and Pixelblaze Pro Output Expander.

## Review File

Open `output/controller-box-v0-review.blend` in Blender. The file is saved as an
exploded assembly with two collections:

- `PRINT_PARTS`: the seven printable enclosure parts.
- `REFERENCE_COMPONENTS_PROVISIONAL`: simplified Pixelblaze, converter, wire
  exit, antenna keepout, and KAN-28 reference geometry.

The fastest review workflow is to toggle the two collections, then inspect:

1. `PRINT_base` and its four external mounting slots.
2. `PRINT_electronics_tray` with the provisional converter and Pixelblaze.
3. `PRINT_blank_connector_panel` and the open end of the base.
4. `PRINT_lid`, `PRINT_switch_carrier`,
   `PRINT_TPU_switch_membrane`, and `PRINT_switch_bezel`.

## Current Geometry

- Base nominal envelope: 132 x 92 x 42 mm, excluding mounting ears.
- Maximum base footprint with mounting ears: 132 x 116 mm.
- Lid: 136 x 96 x 8 mm with 5 mm overlap and 0.35 mm clearance per side.
- Wall: 2.8 mm; floor: 3.0 mm.
- Removable electronics tray: 118 x 78 x 2.4 mm plus guides.
- Replaceable blank connector panel: 80 x 35 x 3 mm.
- TPU diaphragm: 0.8 mm central membrane with 1.2 mm compressed perimeter.
- Four M3 lid positions and four M3 tray positions.
- Four M2 switch-bezel positions.

## Provisional Inputs

The converter reference is deliberately conservative at 60 x 20 x 30 mm with
12 mm of rigid wire-exit allowance at each end. Its tray retention uses two zip
ties rather than a dimension-locked snap fit. Replace these values with physical
measurements before printing a final tray.

Pixelblaze plan dimensions are 39.5 x 34.2 mm. Board height, component locations,
terminal selection, and the exact antenna end still need a physical-board check.

The connector panel is blank because the battery input, single-chain data output,
and any 12 V distribution connector families are not yet frozen.

## Print Direction

- Base: floor on the build plate.
- Lid: exterior top face on the build plate.
- Tray, bezel, and TPU membrane: largest flat face on the build plate.
- Connector panel: exterior face on the build plate.
- Switch carrier: flat mounting face on the build plate.

Use PETG or ASA for rigid parts and 95A TPU for the membrane. Do not use PLA for
the final sun-exposed bike enclosure. The TPU membrane is a dust/splash design,
not a certified IP seal.

## Generate

From the repository root:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/controller-box-v0/source/generate_controller_box_v0.py
```

The command regenerates the Blender review file, GLB, render, seven STLs, and
`output/controller-box-v0-validation.json`.

## Current Validation

The generated validation report passes:

- Seven expected printable parts exist.
- Every printable mesh is closed/manifold.
- Every printable mesh has positive volume.
- The provisional 30 mm converter clears the lid.
- The Pixelblaze plan envelope fits the tray.
- Lid fit allowance is at least 0.25 mm per side.
- The TPU diaphragm is at least three 0.2 mm layers.
- The Pro Output Expander is excluded.

This validates the digital geometry only. No physical fit, heat, dust, splash,
vibration, Wi-Fi, or button-force test has been performed.
