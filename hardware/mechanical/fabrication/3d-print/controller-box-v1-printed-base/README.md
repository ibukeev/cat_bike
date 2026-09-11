# Controller Box V1 — Printed Base

This base was physically approved and printed successfully on 2026-08-18,
as recorded in [its checkpoint](V1_PROPOSAL_CHECKPOINT.md). Keep the saved
print project in `output/Printing/`.

The user deleted the V0 and complete-enclosure proposal folders on 2026-09-10.
This package was renamed from controller-box-v1-flat-base-proposal to
controller-box-v1-printed-base. All CAD, slicer, configuration and generator
files retain their original bytes and historical filenames.

The saved [successful print project](output/Printing/controller-box-v1-flat-base-proposal-PROPOSED__FlatBottomBase.3mf)
and [FreeCAD model](output/controller-box-v1-flat-base-proposal.FCStd) are intact.
The historical generator still requires V0 source, configuration and base STL;
regeneration is unavailable until those dependencies are explicitly recovered.
The cleanup did not restore the folders you deleted.

The printed revision changed only the base and mounting-ear edge construction:

- flat bed datum at Z = 0;
- zero bottom-edge bevel;
- 4 mm XY-only base corner radius;
- 2 mm XY-only mounting-ear corner radius;
- unchanged 132 x 92 x 42 mm enclosure envelope;
- unchanged 132 x 116 mm maximum footprint, mounting slots, wall, floor,
  bosses, connector opening, and lid interface.

Retained build files are under `output/`. No CAD or slicer was run during cleanup.

Historical regeneration command (requires the missing V0 dependencies):

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/controller-box-v1-printed-base/source/generate_controller_box_v1_flat_base_proposal.py
```
