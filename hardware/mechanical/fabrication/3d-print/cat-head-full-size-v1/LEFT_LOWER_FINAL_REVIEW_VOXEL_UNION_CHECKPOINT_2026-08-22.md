# Left lower final-review voxel-union checkpoint

Date: 2026-08-22

## In-document source collection

`LEFT_LOWER_PRINT_SOURCE_COMPOUND` was created in the active mutable FreeCAD
derivative from 41 objects:

- `WORKING_LEFT_LOWER_STRUCTURAL_V1`
- `LEFT_LOWER_3MM_INWARD_PREVIEW_001` through `_038`
- visible local cut results `Cut003` and `Cut004`

Hidden seam-fill source previews were excluded because the visible cut results
supersede them. Frozen context and right-side work were excluded.

## Review outputs

- input compound STL:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/left-lower/input-overlap-compound.stl`
- voxel-unioned review STL:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/left-lower/left-lower-final-review-voxel-union-025mm.stl`
- health report:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/left-lower/mesh-health.json`
- voxel size: 0.25 mm

## Validation

- boundary edges: 0
- non-manifold edges: 0
- wire edges: 0
- connected components: 16
- watertight single component: false

This is a watertight review mesh suitable for slicer inspection as one job, but
it is not a verified monolithic left structural solid. Further bridge geometry
is required before claiming a one-piece load path.
