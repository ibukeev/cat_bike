# Right Eye V17 / V9 Skin Topology Repair Review V1 Checkpoint

Date completed: 2026-08-16
User approval authorizing this bounded one-side proposal: 2026-08-15 (`LGTM`)

## Status

The inherited V9 eye-skin crossing inside the frozen V17 right-eye owner has a
**passing review-only local topology repair proposal**. The proposal replaces
the two approved source faces with three triangles over the same five anchor
points. It does not move any source vertex, change the exterior bounds, perform
a broad Boolean, heal the whole owner, or touch the protected outer-root
defect.

This is not a production owner, mirrored owner, STEP/STL export, slicer source,
G-code source, or ASA print release. Those permissions remain false in the
machine-readable contract and release remains held.

## Current review files

- FreeCAD review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-v9-skin-topology-repair-review-v1/CAT_HEAD_RIGHT_EYE_V17_V9_SKIN_TOPOLOGY_REPAIR_REVIEW_V1.FCStd`
- FreeCAD SHA-256:
  `3e272318f2065b83329583338fe17182c05fc40c2c47d72d39cc558ecd3701d1`
- Validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-v9-skin-topology-repair-review-v1/validation-v1.json`
- Validation SHA-256:
  `a0d52c101c60f32b2aca2098d573aad263fc6af62569e5c24d4391444d90c9b3`
- Validation status: `PASS__REVIEW_ONLY_PROPOSAL`
- Source analyzer:
  `source/cad-change-control/analyze_v17_v9_skin_topology.py`
- Generator:
  `source/cad-change-control/generate_v17_v9_skin_topology_repair_review.py`
- Approved contract:
  `source/cad-change-control/pilot/right-eye-v17-v9-skin-topology-repair-proposal-v1.json`

## Frozen source

- V17 STEP:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-exact-owner-integration-review-v17/right_eye_bucket_with_both_exact_flange_roots_v17.step`
- Source STEP SHA-256:
  `1b1e2430c369fb563602a056340c1d5f88f6a857f9cecf2014bac191443646de`
- Frozen lineage FCStd SHA-256:
  `861c11381ac4a47b4acce10c50706126605cb4e85417a96f2467dd22a9e8228a`
- Source bounds, owner position, V17 flange roots, mating gaps, and engagement
  geometry are frozen.
- Protected source faces `Face72` and `Face489` remain unchanged for the
  separate outer-root repair bucket.

## Approved local operation

- Remove source `Face582` and `Face587` only.
- Preserve exact anchor points, millimetres:
  - `A = (69.45553762207, 87.777007897949, 174.49552180175)`
  - `B = (69.683687036133, 87.805671533203, 174.21144892578)`
  - `C = (68.000558679199, 91.415801843262, 173.69416071777)`
  - `D = (68.228708093262, 91.444465478516, 173.41008784179)`
  - `P = (68.118020837402, 91.430557092285, 173.5479052246)`
- Replace old facets `B-A-D`, `A-C-D`, and `C-P-D` with:
  - `B-A-D`
  - `A-C-P`
  - `A-P-D`
- New internal diagonals: `A-D` and `A-P`.
- Boundary edges and all five coordinates remain unchanged.
- No automatic healing, facet deletion, broad Boolean, whole-owner remesh,
  mirroring, or owner union is permitted by this review.

## Validation results

All machine-readable gates pass:

- one valid, closed solid: PASS;
- source SHA-256: PASS;
- anchor error: `0.0 mm` for A/B/C/D/P;
- maximum source-vertex motion: `1.04244e-12 mm`;
- exterior bounds delta: all six values `0.0 mm`;
- source/replacement patch facet counts: `3 / 3`;
- untouched source faces retained: `1176 / 1176`;
- candidate face count: `1179`;
- source volume: `7269.553010791169 mm3`;
- candidate volume: `7269.553009399428 mm3`;
- volume delta: `-1.39174e-06 mm3`;
- maximum local surface deviation: `1.64093e-06 mm`;
- non-adjacent local V9 BOP diagnostic count: `0`;
- protected `Face72` and `Face489`: retained.

FreeCAD archive validation also passed: the FCStd is an intact `754967`-byte
archive. No STEP or STL was exported.

The validation JSON deliberately preserves the global OCCT diagnostic output.
Those messages include the already-known, protected outer-root defect and must
not be interpreted as a failure of this bounded V9 patch. They do mean the
complete V17 owner is still not globally clean and cannot be released yet.

## Review object map

Open the FCStd above. The file contains only these four named objects:

- `PROPOSED__RIGHT_EYE_V17_V9_SKIN_REPAIRED__REVIEW_ONLY` — complete proposed
  owner;
- `REVIEW_ONLY__NEW_A_D_A_P_DIAGONAL_PATCH` — green replacement patch;
- `FROZEN__RIGHT_EYE_V17__UNCHANGED` — frozen source, hidden by default;
- `REVIEW_ONLY__OLD_FACE582_FACE587__REMOVED_BY_PROPOSAL` — removed old patch,
  hidden by default.

Visually confirm that the green patch lies flush in the eye skin, introduces no
silhouette step or hole, and does not change the eye or flange-root position.
Toggle the frozen owner and old patch only for before/after comparison.

## Rejected or unsafe variants

- deleting the tiny output facets instead of changing the local topology;
- automatic repair, global healing, broad self-union, or remeshing;
- moving any of the five approved anchors;
- changing exterior surfaces or bounds to hide the crossing;
- modifying the clean second-eye root;
- modifying protected `Face72` or `Face489` in this work bucket;
- treating the global OCCT warnings as permission for an unbounded repair;
- mirroring, production union, STEP/STL export, slicing, G-code, or ASA release
  from this review artifact.

## Exact regeneration command

The output directory is fail-closed and must not already exist:

```bash
env PYTHONPATH=/tmp/freecad-1.1.3-extract/squashfs-root/usr/lib \
  /tmp/freecad-1.1.3-extract/squashfs-root/AppRun python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/generate_v17_v9_skin_topology_repair_review.py \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/pilot/right-eye-v17-v9-skin-topology-repair-proposal-v1.json
```

Accept regeneration only when the source SHA matches, every JSON gate is true,
the FCStd archive validates, and the output hashes are recorded again.

## Next review and technical steps

1. User visually reviews the complete proposed owner plus the green local patch
   in the FCStd above.
2. After visual approval, create a new one-side exact STEP review export from
   this repaired owner; do not overwrite V17.
3. Run the full exact OCCT/deep crossing audit. The V9 `Face587` diagnostic
   pairs must be gone and only the separately protected outer-root defect may
   remain.
4. Repair the outer-root `Face72/Face489` defect under a separate approved
   anchor and numeric contract.
5. Only after the exact right-eye owner is globally clean may bilateral
   validation, production owner integration, STL export, or later print gates
   resume.
