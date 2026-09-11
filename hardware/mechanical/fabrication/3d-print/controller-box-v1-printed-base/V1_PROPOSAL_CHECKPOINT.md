# Controller Box V1 Printed-Base Checkpoint

## Cleanup update — 2026-09-10

Package renamed to controller-box-v1-printed-base at the user's request.
All 13 files were byte-identical immediately after rename; only this checkpoint
and README received documentation edits. CAD, 3MF, scripts and configuration
were not changed. The user separately deleted V0 and the complete-enclosure
proposal; they were not restored. The generator's V0 source/config/base-STL
dependencies are therefore missing. The historical commands and review steps
below are not an instruction to regenerate or repeat already granted approval.

Next physical record: document installed fit, mounting behavior and field wear.
A new design change or regeneration requires separate scope and recovered inputs.

## Status

Physically approved and printed successfully by the user on 2026-08-18. V0 is
unchanged. The exact successful base 3MF is retained at
`output/Printing/controller-box-v1-flat-base-proposal-PROPOSED__FlatBottomBase.3mf`
with SHA-256
`0ab6c2710bc5ab1706f6e4cfe605b10d8d444bfc37eeb3cd141428eeb32a4f3f`.

## Current Review and Output Files

- `output/controller-box-v1-flat-base-proposal.FCStd`: FreeCAD review model.
- `output/controller-box-v1-flat-base-proposal.blend`: Blender review source.
- `output/controller-box-v1-flat-base-proposal.glb`: portable 3D review.
- `output/controller-box-v1-flat-base-proposal-isometric.png`: overall review.
- `output/controller-box-v1-flat-base-proposal-bottom.png`: bed-contact review.
- `output/controller-box-v1-flat-base-proposal-validation.json`: Blender mesh,
  bounding-box, and bottom-contact validation.
- `output/controller-box-v1-flat-base-proposal-freecad-validation.json`:
  independent FreeCAD mesh and FCStd integrity validation.

## Frozen V0 Baseline

- Generator SHA-256:
  `fbd1181eaa6e25136e7474f757d2e65e45b4b479a98bd136066d2529f186b5e9`
- Configuration SHA-256:
  `bc70051193fae52c1bbf89d68f0cbc271190f24a1cfd30f0670a9ddff27a7c59`
- Base STL SHA-256:
  `59e1957b117d6584ce26e3d5fd4076a0d70529f0b5ad9710dcae0bccc9d7dc12`

## Approved Numeric Contract

- Physical problem: remove bed-facing bevels that reduced ASA adhesion.
- Authoritative bed datum: Z = 0 mm.
- Base corners: 4 mm radius in the XY outline only.
- Mounting-ear corners: 2 mm radius in the XY outline only.
- Bed-facing edge radius: 0 mm.
- Preserve enclosure envelope: 132 x 92 x 42 mm.
- Preserve maximum footprint: 132 x 116 mm.
- Preserve 2.8 mm wall, 3.0 mm floor, lid interface, bosses, connector opening,
  mounting-ear positions, and mounting slots.

## Validation Performed

Blender 5.2.0 LTS:

- Closed/manifold: pass.
- Positive volume: pass, 93,147.55 mm3.
- Bounding box: pass, min `[-66, -58, 0]`, max `[66, 58, 42]` mm.
- Flat bed datum: pass.
- Bottom contact area: pass, 13,188.869 mm2 against a 12,000 mm2 minimum.
- No bottom-edge radius: pass.

FreeCAD 1.1.3, `auto_repair=false`:

- OFF import: 3,210 points and 6,436 facets.
- Bounding box: 132 x 116 x 42 mm.
- Mesh validation: pass.
- FCStd ZIP integrity: pass, 89,155 bytes.

The temporary OBJ exchange was rejected because smoothing-boundary vertex
splits produced false open seams. Binary and ASCII PLY were rejected because
the FreeCAD bridge imported incomplete meshes. Those were tooling failures and
did not alter or consume the proposal. The connectivity-preserving OFF exchange
passed.

## Rejected or Unsafe Variants

- Do not keep the V0 6 mm all-edge base bevel or 3 mm all-edge ear bevel; both
  reduce bed contact.
- Do not square the XY outline completely; the approved radii reduce stress
  concentration while preserving a flat bottom.
- Do not release an STL or G-code until the user explicitly approves the visual
  proposal.
- Do not treat a brim as a substitute for correcting the bed-facing geometry;
  use both the flat-bottom revision and an ASA brim after release.

## Exact Regeneration Command

From the repository root:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/controller-box-v1-printed-base/source/generate_controller_box_v1_flat_base_proposal.py
```

## Next Physical Review

1. Open the FCStd or review images.
2. Confirm the base wall outline, four flat mounting ears, slots, connector-panel
   opening, and retained lid-boss arrangement.
3. Explicitly approve or reject the V1 proposal.
4. After approval, generate the base STL, revalidate it in FreeCAD, and prepare
   a short first-5-mm ASA adhesion test with a 10 mm brim before a full print.
