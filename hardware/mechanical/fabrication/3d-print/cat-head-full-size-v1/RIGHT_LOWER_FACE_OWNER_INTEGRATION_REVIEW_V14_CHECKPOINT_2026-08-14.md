# Right Lower-Face Owner Integration V14 Checkpoint — 2026-08-14

## Status

V13 and the resulting V14 right-side owner assembly were visually approved by the user on 2026-08-14. V14 substitutes only approved component 001 into a copied V11 right lower-face owner. It remains a right-side review assembly: no production-owner Boolean, left mirror, STL, G-code, slicing, or print release was performed. The head-shell tracker remains 9 of 20 gates complete until exact mirroring and bilateral validation close HS-11.

## Review/output files

- FreeCAD review: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-owner-integration-review-v14/CAT_HEAD_RIGHT_LOWER_FACE_OWNER_INTEGRATION_REVIEW_V14.FCStd`
- Blender review: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-owner-integration-review-v14/CAT_HEAD_RIGHT_LOWER_FACE_OWNER_INTEGRATION_REVIEW_V14.blend`
- Integrated owner review OBJ: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-owner-integration-review-v14/right_lower_face_v14_owner_review.obj`
- Blender validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-owner-integration-review-v14/validation-v14.json`
- FreeCAD validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-owner-integration-review-v14/freecad-validation-v14.json`
- Evidence renders: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-owner-integration-review-v14/review/`
- Contract: `config/right-lower-face-owner-integration-review-v14.json`
- Frozen component SHA manifest: `config/right-lower-face-owner-integration-review-v14-components-sha256.json`
- Generator: `source/generate_right_lower_face_owner_integration_review_v14.py`

## Accepted decisions and dimensions

- V13 component 001 is explicitly visually approved and is the only substituted geometry.
- The complete V14 right-side owner/context review is explicitly visually approved.
- Components 002–060 are extracted directly from the SHA-locked V11 source mesh and match the frozen V12 inventory by exact fingerprint, topology, and bounds.
- V14 lower face remains 60 deliberate loose solids for review; no production Boolean was attempted.
- Both right flange-pair gaps remain `0.3000 mm`; both pair interference volumes remain `0.0 mm3`.
- C046-to-eye clearance remains `4.6063 mm`; C048-to-eye clearance remains `4.0317 mm`.
- Upper head, eye bucket, all four right flange objects, C046, and C048 retain their exact V11 fingerprints.
- Rear-cassette ownership, C006, and `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` remain frozen and untouched.

## Validation performed and results

- Blender integrated owner: 60 components; 1553 vertices, 3546 edges, 2073 faces; zero boundary edges and zero non-manifold edges; PASS.
- V13 component 001: 713 vertices, 2229 edges, 1486 faces; zero boundary/non-manifold edges and zero Blender BVH intersections; exterior deviation `0.00654787 mm`; unchanged bounds.
- All 59 unchanged components match their frozen V12 fingerprints and exact per-file SHA-256 manifest.
- Both four-flange fingerprints and both `0.3000 mm` mating gaps match V11 exactly; no pair interference.
- FreeCAD/OCCT rechecked the changed component as one valid, closed, self-intersection-free solid: 1027 faces, 1747 edges, 706 vertices, volume `78628.23 mm3`.
- Saved V14 FCStd ZIP integrity: PASS.

## Rejected or unsafe variants

- Importing the unchanged components through their triangulated OBJ files was rejected because that round trip changes n-gon edge counts and can split a seam. V14 instead extracts them directly from the locked V11 mesh.
- Converting the joined 60-loose-solid review OBJ to one OCCT solid was rejected: OBJ vertex merging created an invalid 131-shell shape. That failed conversion was deleted and is not in the saved review.
- Do not treat the review OBJ as a production one-body export. HS-18 remains open.

## Exact regeneration command

From `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/`:

```bash
blender --background --python source/generate_right_lower_face_owner_integration_review_v14.py -- --config config/right-lower-face-owner-integration-review-v14.json
```

The FreeCAD review is then assembled through the FreeCAD MCP by importing the generated owner OBJ plus the eight V11 context OBJs, inserting the validated V13 OCCT solid as hidden audit evidence, and saving the FCStd path above.

## Next physical/visual review

V14 passed the user's full right-side visual review. The next bounded step is an exact `X = 0` left mirror of this approved result followed by bilateral validation of topology, bounds, flange gaps, C046/C048-equivalent eye clearances, exterior containment, and frozen-context equality. Print release remains held.
