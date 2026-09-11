# Active working lower print sources

Status date: 2026-08-22

## User decision

The operator approved the following two working lower-shell STLs for the
current physical print run. They are the source of truth for this active print
iteration and any physical-fit feedback from it.

## Active print artifacts

| Side | Active STL |
| --- | --- |
| Right lower | `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/right-lower/right-lower-final-review-voxel-union-025mm.stl` |
| Left lower | `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/working/left-lower/left-lower-final-review-voxel-union-025mm.stl` |

## Active editable CAD source

`output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-as-printed-working-assembly-v1/RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V2.FCStd`

The FreeCAD document contains the working source collections:

- `RIGHT_LOWER_PRINT_SOURCE_COMPOUND`
- `LEFT_LOWER_PRINT_SOURCE_COMPOUND`

## Known validation state

Both artifacts are 0.25 mm voxel-union review meshes. They are watertight but
are not validated as monolithic structural solids:

| Side | Connected shells | Other known condition |
| --- | ---: | --- |
| Right lower | 27 | PrusaSlicer reported auto-repair of 8 errors during handoff. |
| Left lower | 16 | No single-solid claim has been made. |

These print artifacts supersede earlier lower-shell preview exports for the
current physical iteration only. They do **not** replace frozen canonical
context, create a general fabrication release, or waive future geometry,
load-path, slicer, or physical-fit verification.

## Next physical-review action

After printing, record fit, seam closure, mounting clearance, and any
shell-to-shell movement. Use that evidence to decide which remaining gaps need
explicit bridge geometry before the next source-of-truth print iteration.
