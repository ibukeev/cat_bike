# Right Lower-Face Topology Repair V12 Checkpoint — 2026-08-14

Status: **HOLD — bounded legacy topology defect identified; no production owner, mirror, STL, G-code, or print release.**

## Frozen input and scope

- Source review: `right-eye-neck-removal-clearance-regression-fix-review-v11/CAT_HEAD_RIGHT_EYE_NECK_REMOVAL_CLEARANCE_REGRESSION_FIX_REVIEW_V11.FCStd`
- Source object: `PROPOSED__RIGHT_LOWER_FACE__V10_NECK_REMOVAL_WITH_V2_CLEARANCE_RESTORED_V11`
- Locked source fingerprint: `b216b1d6fc2614c6415785870681c5ab58e2ef6824c292b2bb518076aa57d2e0`
- Preserve V10 neck deletion, approved V2 C046/C048, V9 eye, all four flange locations and 0.3000 mm pair gaps, right upper head, rear cassette, C006, and aluminum interface `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2`.
- Topology only: maximum exterior-surface deviation 0.01 mm; maximum bounding-box deviation 0.001 mm; required final result one valid closed solid with zero self-intersections.

## Current files

- Contract: `config/right-lower-face-topology-repair-review-v12.json`
- Exact component exporter: `source/export_right_lower_face_v11_components_for_v12.py`
- Isolated solver audit: `source/generate_right_lower_face_component001_self_union_review_v12.py`
- Component inventory: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-topology-repair-review-v12/component-inventory-v12.json`
- Sixty unchanged component OBJs: `.../right-lower-face-topology-repair-review-v12/components/`
- Working FreeCAD document: `CAT_HEAD_RIGHT_LOWER_FACE_TOPOLOGY_REPAIR_REVIEW_V12` (not production-approved).

## Validation and findings

- Frozen V11 lower aggregate: 1,529 vertices, 60 connected components; FreeCAD reports non-watertight/self-intersecting aggregate.
- All 60 components were exported without changing coordinates and converted individually in FreeCAD.
- The largest owner component (`001`) is closed but geometrically invalid in FreeCAD; component `018` is valid and closed.
- Component `001` contains 41 triangle intersections mapping to 21 original legacy face pairs:
  `51/53`, `49/53`, `51/78`, `53/72`, `49/78`, `53/75`, `50/53`, `23/73`, `73/78`, `72/80`, `20/55`, `20/44`, `20/43`, `16/20`, `20/28`, `48/53`, `48/78`, `50/78`, `43/49`, `77/78`, and `54/75`.
- The defect is concentrated in inherited panel skins and seam/slot faces `16`, `20`, `23`, `28`, `43`, `44`, `48–55`, `72`, `73`, `75`, `77`, `78`, and `80`; it is not in the approved eye, flange, C046, or C048 geometry.
- Direct BEAUTY triangulation preserves all vertices and the bounding box but retains 41 intersections, proving this is not merely an OBJ/FreeCAD diagonal-choice defect.

## Rejected variants

- FreeCAD all-at-once and pairwise fusion: rejected; the apparent first fusion produced a null shape because component `001` is invalid.
- Blender EXACT self-union: rejected; zero intersections but seven non-manifold edges and loss of source-surface correspondence.
- Blender MANIFOLD self-union: rejected; four non-manifold edges and 58 intersections.
- No rejected result is authorized for owner integration or printing.

## Exact regeneration commands

```bash
blender --background right-eye-neck-removal-clearance-regression-fix-review-v11/CAT_HEAD_RIGHT_EYE_NECK_REMOVAL_CLEARANCE_REGRESSION_FIX_REVIEW_V11.blend --python source/export_right_lower_face_v11_components_for_v12.py
blender --background --python source/generate_right_lower_face_component001_self_union_review_v12.py -- --config config/right-lower-face-topology-repair-review-v12.json
```

Run these from `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/` or use the repository-relative paths recorded in the scripts/config.

## Next review/action

Repartition only the mapped legacy seam/slot faces into non-overlapping skin regions, then rerun Blender and FreeCAD gates. The first acceptable proposal must show the isolated right lower face and must not change the exterior silhouette, approved eye clearances, flange gaps, or aluminum interface. Until that proposal exists, HS-11 remains open.
