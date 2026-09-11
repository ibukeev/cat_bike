# Large-head working print files

Selected lower-shell packages relocated unchanged from reports on 2026-09-10.
These are working physical-print records, not a new structural/fabrication release.

| Part | Geometry | Saved slicer project |
| --- | --- | --- |
| Right lower | [STL](right-lower/right-lower-final-review-voxel-union-025mm.stl) | [3MF](right-lower/right-lower-final-review-voxel-union-025mm.3mf) |
| Left lower | [STL](left-lower/left-lower-final-review-voxel-union-025mm.stl) | [3MF](left-lower/left-lower-final-review-voxel-union-025mm.3mf) |

Each directory also contains input-overlap-compound.stl and mesh-health.json.
All eight files match their original SHA-256 hashes.

See the [rebuild index](../README.md) for V6/V5 working assemblies, manual masters,
eye releases and frozen shape references retained in the large-head cleanup.

## Source and known limits

Editable source remains:

`../output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-as-printed-working-assembly-v1/RIGHT_UPPER_AS_PRINTED_WORKING_ASSEMBLY_V2.FCStd`

Its collections are RIGHT_LOWER_PRINT_SOURCE_COMPOUND and
LEFT_LOWER_PRINT_SOURCE_COMPOUND. The source was not opened or resaved.

The meshes use 0.25 mm voxel union. Saved health records report 27 connected
shells on the right and 16 on the left; the historical right-hand slicer
handoff reported eight auto-repaired errors. These are not validated
monolithic structural solids. The earlier 34-component 3 mm preview was
held from printing and is now in recovery, not this working set.

See [the print decision](../ACTIVE_WORKING_LOWER_PRINT_SOURCES_2026-08-22.md),
[right checkpoint](../RIGHT_LOWER_FINAL_REVIEW_VOXEL_UNION_CHECKPOINT_2026-08-21.md)
and [left checkpoint](../LEFT_LOWER_FINAL_REVIEW_VOXEL_UNION_CHECKPOINT_2026-08-22.md)
for provenance and historical regeneration commands. Scripts now use these
working paths; none were run. Future generation requires explicit authorization
and must not overwrite this retained print evidence.

## Verification and recovery

From the repository root:

```bash
python3 -B .cleanup-recovery/2026-09-10-large-head/cleanup.py verify
```

See [the cleanup record](../../../../../../docs/PROJECT_CLEANUP_PLAN.md) for
the recovery archive and old/new path/hash mapping. Reports is empty, with no
legacy links.

Next physical review: record print history, fit, seams, mounting clearance
and shell-to-shell movement before selecting another print iteration.
