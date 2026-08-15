# Right-Eye Flange Owner-Integration Review V16 Checkpoint — 2026-08-14

## Status

V16 is the current HS-11 right-side diagnostic and supersedes rejected V15, but it is now **HOLD / not approved**. The complete V3 upper-head context, repaired V13 lower-face component 001, unchanged components 002-060, V9 eye, and accepted flange leaves remain present. A new fail-closed Blender gate finds `6` non-adjacent triangle intersections in the eye plus eye-side roots. FreeCAD imports the separate triangulated transfer mesh as watertight and converts it to one closed solid with the expected `7264.86 mm3` volume, but OCCT rejects that solid with two self-intersecting wires and two unorientable regions. No repair, mirror, STL, G-code, slicing, ASA recommendation, or print release was performed.

## Current review/output files

- Blender review: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/CAT_HEAD_RIGHT_EYE_FLANGE_OWNER_INTEGRATION_REVIEW_V16.blend`
  - SHA-256: `de3145abee8254ca31dd349be83ec3507a404307aafb8686b79a36ea419de22e`
- Validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/validation-v16.json`
  - SHA-256: `9297634a05c7207cdfebdfeee93a4e060baee8f9999c1cd1c51e5417c6b68ce4`
- Integrated eye OBJ: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/objects/right_eye_bucket_with_both_eye_flange_roots_v16.obj`
  - SHA-256: `0df7a2f2bdfa3a75edbbcc096aa75b78ddb47797baeead742dfb0231d3f71472`
- Triangulated FreeCAD-transfer OBJ: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/objects/right_eye_bucket_with_both_eye_flange_roots_freecad_transfer_v16.obj`
  - SHA-256: `4df70cc1bf0cb08e57529823c1cff09e5f17b231ad6b7a27e18beb1d6f8fe781`
- Unchanged lower components 002-060 context OBJ: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/objects/right_lower_face_components_002_060_context_v16.obj`
  - SHA-256: `3de96977cdba33108cb0ccab6df84cdd4dffde144ea55a3140daa46a5799d8bb`
- Evidence renders: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/review/`
- Contract: `config/right-eye-flange-owner-integration-review-v16.json`
  - SHA-256: `71c66e0837a8cb9c7798a2e9431899fdf7458f4a0a4efad93526de6cd47734ec`
- Generator: `source/generate_right_eye_flange_owner_integration_review_v16.py`
  - SHA-256: `bf26d1384d9d33d242d600f3e0fff38b92092492057038584b1de4c047f4c90e`

There is no saved V16 FCStd yet. The FreeCAD GUI exited during the live second-eye Boolean.

## Accepted decisions and dimensions

- Right side only. Do not mirror until the right-side production-owner proof is approved.
- Use all 42 complete V3 right upper-head components; do not reuse V15 `right_upper_head`.
- Use repaired V13 lower-face component 001 and unchanged lower components 002-060.
- Keep the accepted exterior mating-leaf shape.
- Frozen/source outer and second pair gaps: `0.3000 mm`.
- Controlled inward Boolean epsilon: `0.0100 mm`.
- Proposed integrated outer and second pair gaps: `0.2900 mm`, within the frozen `0.0100 mm` tolerance.
- Eye-side interior root extension: `1.5000 mm`.
- Outer-eye owner engagement: `127.2767 mm3`.
- Second-eye owner engagement: `92.6241 mm3`.
- Outer-head/upper-head engagement: `122.5160 mm3`.
- Second-head/lower component 001 engagement: `35.4259 mm3`.
- C046/C048 engagement with lower component 001: `1.6006/59.4690 mm3`.
- C046/C048 eye clearance: `4.6063/4.0317 mm`.
- Rear-cassette ownership, C006, and `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` are frozen and unchanged.

## Validation performed

- Blender regeneration: HOLD because the permanent self-intersection gate reports `6` non-adjacent triangle pairs.
- Complete upper-head components: `42`.
- Lower-face components represented: `60`.
- Source eye topology: `481/1473/982` vertices/edges/faces, zero boundary edges, zero nonmanifold edges, volume `6649.6022 mm3`.
- Integrated eye topology: `1274/2836/1552` vertices/edges/faces, zero boundary edges, zero nonmanifold edges, one connected component, volume `7264.8617 mm3`.
- FreeCAD upper owner `PROPOSED__RIGHT_UPPER_HEAD_WITH_OUTER_HEAD_FLANGE__V16`: valid, watertight, self-intersection-free, 29 solids, 2623 faces, volume `120145.18 mm3`.
- FreeCAD lower owner `PROPOSED__RIGHT_LOWER_FACE_COMPONENT001_WITH_SECOND_HEAD_C046_C048__V16`: valid, watertight, self-intersection-free, one solid, 1148 faces, volume `79631.34 mm3`.
- The untriangulated OBJ imports into FreeCAD with only `1198` of `1274` vertices, is open, and is not a valid transfer path.
- The triangulated transfer imports all `1274` vertices as `2568` facets and is watertight.
- FreeCAD converts the triangulated transfer to one closed solid with volume `7264.86 mm3`, but `check_geometry` is false and OCCT reports two self-intersecting wires plus two unorientable regions.
- FreeCAD diagnostic auto-repair removes `102` facets and leaves the mesh open; it is rejected and was not used as production geometry.

## Rejected or unsafe variants

- V15 is rejected: it reused incomplete legacy `right_upper_head`, showed empty upper-shell sectors, and displayed owner parts as floating context.
- Exact tangent eye-leaf Boolean is rejected: it produced 9 boundary and 374 nonmanifold edges.
- Blender MANIFOLD Boolean is rejected: it produced four closed but disconnected islands.
- Live FreeCAD second-eye Boolean is rejected as a workflow path: OCCT hung/crashed the GUI. Re-import the already-proven integrated OBJ instead.
- The earlier Blender manifold-only pass is insufficient: it did not test non-adjacent triangle intersections.
- FreeCAD automatic mesh repair is rejected because it opens the owner mesh and changes topology.
- Do not mirror, export, slice, or print from V16 until the final FreeCAD solid and visual review pass.

## Exact regeneration command

From `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/`:

```bash
blender --background --python source/generate_right_eye_flange_owner_integration_review_v16.py -- --config config/right-eye-flange-owner-integration-review-v16.json
```

## Next physical/visual review

1. Identify and classify the exact six intersecting triangle pairs by source owner and location.
2. Correct only the defective eye-root union construction while preserving the accepted exterior leaves, `0.2900 mm` proposed gaps, `1.5000 mm` interior-root depth, eye geometry, and owner positions.
3. Require zero Blender non-adjacent intersections before importing the triangulated transfer into FreeCAD.
4. Require one valid closed OCCT solid with no self-intersection or unorientable-region errors.
5. Only then rebuild the full right-owner review, capture evidence, and request bounded visual approval.

HS-11 remains open. Structural ASA printing remains held.
