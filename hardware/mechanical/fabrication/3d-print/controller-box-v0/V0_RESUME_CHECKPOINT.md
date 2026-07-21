# Controller Box V0 Resume Checkpoint

## Current Review and Output Files

- `output/controller-box-v0-review.blend`: primary user review file, saved as an
  exploded assembly.
- `output/controller-box-v0-review.png`: rendered review image.
- `output/controller-box-v0-review.glb`: portable 3D review export.
- `output/controller-box-v0-validation.json`: mesh and envelope validation.
- `output/controller-box-v0-*.stl`: seven individually printable parts.
- `config/controller-box-v0.json`: all current dimensions and provisional part
  envelopes.
- `source/generate_controller_box_v0.py`: authoritative generator.

## Accepted Decisions and Dimensions

- V0 is controller-only: Pixelblaze V3 Standard, one Magnolora 12-to-5 V 3 A
  converter, and one KAN-28 controller switch.
- Battery, master disconnect, branch fuse block, and Pro Output Expander are
  outside this enclosure.
- The KAN-28 is operated through a replaceable 95A TPU diaphragm compressed by
  a separate PETG bezel.
- The connector face is a replaceable blank panel so connector selection does
  not invalidate the base.
- The converter uses adjustable zip-tie retention because its physical dimensions
  have not been measured.
- Base nominal envelope is 132 x 92 x 42 mm; maximum width with mounting ears is
  116 mm.
- Lid overlap is 5 mm with 0.35 mm clearance per side.
- Rigid print material is PETG or ASA; final PLA use is rejected.

## Validation Performed

Regenerated with Blender 5.2.0 LTS. `controller-box-v0-validation.json` reports:

- 7/7 expected printable parts generated.
- All parts closed/manifold: pass.
- All parts positive volume: pass.
- Provisional converter vertical clearance: pass.
- Pixelblaze plan-envelope fit: pass.
- Lid clearance: pass.
- TPU minimum layer count: pass.
- Pro Output Expander excluded: pass.

The Python generator also passes `python3 -m py_compile`.

## Rejected or Unsafe Variants

- Do not use the KAN-28 as the battery or whole-bike emergency disconnect.
- Do not expose the bare KAN-28 through an unsealed lid opening.
- Do not place the Pro Output Expander in this box; the user is reserving it for
  larger projects.
- Do not parallel Magnolora converter 5 V outputs.
- Do not freeze cable glands or module connectors into the base before their
  exact families are selected.
- Do not claim an IP rating from the digital membrane design.
- Do not print the final sun-exposed enclosure in PLA.

## Exact Regeneration Command

Run from the repository root:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/controller-box-v0/source/generate_controller_box_v0.py
```

## Next Physical-Review Steps

1. Review `output/controller-box-v0-review.blend` and comment on overall size,
   mounting-ear direction, lid appearance, connector-panel location, tray layout,
   and switch position.
2. Measure the actual Magnolora body and rigid wire exits.
3. Obtain or measure the physical Pixelblaze, including maximum component height,
   terminal choice, antenna end, and any keepout areas.
4. Select the battery-side master disconnect and the connector family or families
   that must pass through the replaceable panel.
5. Print the lid's switch area, TPU diaphragm, bezel, carrier, and a KAN-28 fit
   coupon before printing the full enclosure.
6. Bench-check button force and latching through TPU, then perform dust/splash
   inspection without electronics installed.
7. Only after component fit, run a powered thermal and Wi-Fi test with the lid
   closed.
