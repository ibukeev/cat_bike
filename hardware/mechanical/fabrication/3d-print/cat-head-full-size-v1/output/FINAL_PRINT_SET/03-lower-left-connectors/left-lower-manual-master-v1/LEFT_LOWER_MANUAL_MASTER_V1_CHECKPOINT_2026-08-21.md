# Left-lower manual master V1 checkpoint — 2026-08-21

## Current files

- CAD master: `LEFT_LOWER_COMPLETE_OPAQUE_UNION_WITH_CONNECTORS_V1.FCStd`
- 3MF companion: `LEFT_LOWER_COMPLETE_OPAQUE_UNION_WITH_CONNECTORS_V1-Compound.3mf`
- Authority record: `master-manifest.json`
- Integrity record: `SHA256SUMS.txt`

## Accepted decision

The user manually edited the left-lower piece and explicitly designated these
two exact files as the master. All later left-lower sessions must build from
the hash-matched FCStd in this package. The original review-directory files
remain unchanged.

## Validation performed

- Source and copied FCStd SHA-256 match:
  `3e52d392a40d570a0c0a04a3089bd496e30ff8197307e377c6236a01c982cbd4`.
- Source and copied 3MF SHA-256 match:
  `ed00bfadbb2120cb7dfc6c54085fccaff5169eaeaca246abc03970f18acfe8bc`.
- Read-only ZIP integrity test passed for both archives.
- No FreeCAD geometry, topology, collision, slicing, or physical-fit validation
  was run during this promotion.

## Superseded starting sources

Earlier automated unions, reconstructed left assemblies, mirrored whole
assemblies, and review-only left-lower files remain evidence only. They must
not replace this manually edited master as the starting source.

## Exact promotion command

From the repository root:

```bash
mkdir -p hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/FINAL_PRINT_SET/03-lower-left-connectors/left-lower-manual-master-v1
cp --preserve=all hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/review-only/left-side-flange-completion-v2/LEFT_LOWER_COMPLETE_OPAQUE_UNION_WITH_CONNECTORS_V1.FCStd hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/70-freecad-pilots/review-only/left-side-flange-completion-v2/LEFT_LOWER_COMPLETE_OPAQUE_UNION_WITH_CONNECTORS_V1-Compound.3mf hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/FINAL_PRINT_SET/03-lower-left-connectors/left-lower-manual-master-v1/
```

## Next review step

For any later change, copy the master FCStd to a fresh review package first,
make only the newly authorized change, and stop for the user's visual review.
Never save changes back into this master package.
