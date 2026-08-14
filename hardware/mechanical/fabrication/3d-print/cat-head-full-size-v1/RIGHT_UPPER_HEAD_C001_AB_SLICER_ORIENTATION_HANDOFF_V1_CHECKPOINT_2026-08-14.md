# Right Upper Head C001 A/B Slicer Orientation Handoff V1 Checkpoint — 2026-08-14

## Status

The editable PrusaSlicer project contains one complete reviewed right upper-head
C001 shell owner with its approved A/B features integrated. It does not contain
detached coupons. This handoff exists only so the user can set and return the
intended physical print orientation.

No geometry, scale, supports, brim, G-code, or print-release state changed.

## Frozen source and numeric contract

- FreeCAD source: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-owner-integration-review-v1/CAT_HEAD_RIGHT_AB_OWNER_INTEGRATION_REVIEW_V1.FCStd`
- Source object: `PROPOSED__RIGHT_UPPER_HEAD_C001__A_B_INTEGRATED_V1`
- Source FreeCAD SHA-256: `e9974661a5a0a71a12bcb6ab6d0d66ceae354fd8744486ff08ce72e20cf0376c`
- Geometry change: `0.0 mm`; scale: `1.0`.
- Slicer object count: `1` complete shell object.
- PrusaSlicer envelope: `156.938995 x 206.289024 x 158.395645 mm`.
- Topology: `3418` facets, manifold, one part, `77958.335938 mm3`.
- Exact STL SHA-256: `e660e0537f17a7462d2c1a1c9201de89f3fa45601b41a3a016d76e8c8a38009a`.
- 3MF SHA-256: `c41b8582f5aebe04909b90c25db7431baa150f76eb4f82437d8206420c60cfed`.

The accepted head/eye geometry, ears, lower face, rear cassette,
reinforcement, C006, and `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` remain frozen and
are not modified by this packaging step.

## Current outputs

- Editable complete-shell project: `output/50-slicer-projects/right-upper-head-c001-ab-orientation-handoff-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ORIENTATION_HANDOFF_V1.3mf`
- Exact full-shell STL: `output/50-slicer-projects/right-upper-head-c001-ab-orientation-handoff-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_EXACT.stl`
- Validation: `output/50-slicer-projects/right-upper-head-c001-ab-orientation-handoff-v1/validation-v1.json`

## Rejected or unsafe variants

- The earlier standalone A/B coupon project is rejected as the requested
  orientation handoff because the user prints the connectors as integrated
  parts of the shell. It remains only as traceable historical evidence.
- Do not scale, split, or substitute geometry in the slicer.
- This handoff is not sliced G-code and is not permission to start the full ASA
  shell print. Supports, brim, layer continuity, collision, and actual-printer
  bed clearance remain to be checked after the user saves the orientation.

## Exact regeneration

1. Open the frozen FreeCAD source.
2. Export only `PROPOSED__RIGHT_UPPER_HEAD_C001__A_B_INTEGRATED_V1` as the exact STL with no placement or scale change.
3. Run from the repository root:

   ```bash
   prusa-slicer --export-3mf --output hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-head-c001-ab-orientation-handoff-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ORIENTATION_HANDOFF_V1.3mf hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-head-c001-ab-orientation-handoff-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_EXACT.stl
   prusa-slicer --info hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/50-slicer-projects/right-upper-head-c001-ab-orientation-handoff-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ORIENTATION_HANDOFF_V1.3mf
   ```

## Next physical review

Open the 3MF, select the one complete shell object, rotate it so the under-ear
opening has the intended relationship to the bed, do not scale it, and save as
`CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_USER_ORIENTED_V1.3mf`. Return that project
for final bed-envelope, layer-continuity, support, brim, and collision checks.
