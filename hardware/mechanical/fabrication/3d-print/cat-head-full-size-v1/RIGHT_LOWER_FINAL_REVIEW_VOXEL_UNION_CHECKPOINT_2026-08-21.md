# Right lower final-review voxel-union checkpoint

Date: 2026-08-21

## Working FreeCAD derivative

`output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-as-printed-working-assembly-v1/RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V2.FCStd`

## In-document source collection

`RIGHT_LOWER_PRINT_SOURCE_COMPOUND` was created from 32 authorized mutable
working objects:

- `WORKING_RIGHT_LOWER_STRUCTURAL_V1`
- all available `RIGHT_LOWER_3MM_INWARD_PREVIEW*` objects
- `Cut001`
- `PROPOSED_RIGHT_LOWER_OUTBOARD_FACE_THICKEN_2MM`

Frozen context was excluded. This compound is an in-document source collection,
not a successful OCCT/BRep Boolean fusion.

## Review artifacts

- Input STL: `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/right-lower/input-overlap-compound.stl`
- Voxel-union STL: `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/right-lower/right-lower-final-review-voxel-union-025mm.stl`
- Health report: `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/right-lower/mesh-health.json`
- Union resolution: 0.25 mm

## Validation result

- boundary edges: 0
- non-manifold edges: 0
- wire edges: 0
- connected components: 27
- `watertight_single_component`: false

The exported review STL is watertight but remains a 27-shell mesh. It must not
be treated as one connected printable structural solid until the remaining
shell-to-shell bridges are designed, reviewed, and rerun through this pipeline.
