# Right-Eye Flange Owner-Integration Review V16 Checkpoint — 2026-08-14

## Status

V16 is the current HS-11 right-side repair and supersedes rejected V15. The Blender owner proof passes: the complete V3 upper-head context is restored, the repaired V13 lower-face component 001 and unchanged components 002-060 are present, and the V9 eye plus both eye-side flange roots is one closed manifold component. FreeCAD validated the upper- and lower-head owner fusions before its live eye Boolean crashed the GUI. Final FreeCAD import and OCCT validation of the integrated eye OBJ are still required. No mirror, STL, G-code, slicing, ASA recommendation, or print release was performed.

## Current review/output files

- Blender review: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/CAT_HEAD_RIGHT_EYE_FLANGE_OWNER_INTEGRATION_REVIEW_V16.blend`
  - SHA-256: `0a48c4310372a4fdd371bf78d8da029375d14b8a267efc018bd3ba65117a8ab0`
- Validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/validation-v16.json`
  - SHA-256: `6c0282b312501ec8f4ce85379f2569e390a09be77aa7b015efcb7c38a801be41`
- Integrated eye OBJ: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/objects/right_eye_bucket_with_both_eye_flange_roots_v16.obj`
  - SHA-256: `0df7a2f2bdfa3a75edbbcc096aa75b78ddb47797baeead742dfb0231d3f71472`
- Unchanged lower components 002-060 context OBJ: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/objects/right_lower_face_components_002_060_context_v16.obj`
  - SHA-256: `3de96977cdba33108cb0ccab6df84cdd4dffde144ea55a3140daa46a5799d8bb`
- Evidence renders: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/review/`
- Contract: `config/right-eye-flange-owner-integration-review-v16.json`
- Generator: `source/generate_right_eye_flange_owner_integration_review_v16.py`

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

- Blender regeneration: PASS.
- Complete upper-head components: `42`.
- Lower-face components represented: `60`.
- Source eye topology: `481/1473/982` vertices/edges/faces, zero boundary edges, zero nonmanifold edges, volume `6649.6022 mm3`.
- Integrated eye topology: `1274/2836/1552` vertices/edges/faces, zero boundary edges, zero nonmanifold edges, one connected component, volume `7264.8617 mm3`.
- FreeCAD upper owner `PROPOSED__RIGHT_UPPER_HEAD_WITH_OUTER_HEAD_FLANGE__V16`: valid, watertight, self-intersection-free, 29 solids, 2623 faces, volume `120145.18 mm3`.
- FreeCAD lower owner `PROPOSED__RIGHT_LOWER_FACE_COMPONENT001_WITH_SECOND_HEAD_C046_C048__V16`: valid, watertight, self-intersection-free, one solid, 1148 faces, volume `79631.34 mm3`.
- Integrated eye OBJ still requires FreeCAD mesh-to-solid conversion, `check_solid`, self-intersection verification, and geometry validation after GUI restart.

## Rejected or unsafe variants

- V15 is rejected: it reused incomplete legacy `right_upper_head`, showed empty upper-shell sectors, and displayed owner parts as floating context.
- Exact tangent eye-leaf Boolean is rejected: it produced 9 boundary and 374 nonmanifold edges.
- Blender MANIFOLD Boolean is rejected: it produced four closed but disconnected islands.
- Live FreeCAD second-eye Boolean is rejected as a workflow path: OCCT hung/crashed the GUI. Re-import the already-proven integrated OBJ instead.
- Do not mirror, export, slice, or print from V16 until the final FreeCAD solid and visual review pass.

## Exact regeneration command

From `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/`:

```bash
blender --background --python source/generate_right_eye_flange_owner_integration_review_v16.py -- --config config/right-eye-flange-owner-integration-review-v16.json
```

## Next physical/visual review

1. Restart the FreeCAD GUI.
2. Import `right_eye_bucket_with_both_eye_flange_roots_v16.obj`, convert it to one OCCT solid, and run solid, geometry, watertightness, and self-intersection checks.
3. Rebuild or restore the two already-validated upper/lower owner fusions in the same review file.
4. Display the full right owner context and verify: complete upper shell with no empty sectors; both eye flange pairs internal; no lower-face neck/pole; C046/C048 clear of the eye; no exterior protrusion; all ownership visually coherent.
5. Save `CAT_HEAD_RIGHT_EYE_FLANGE_OWNER_INTEGRATION_REVIEW_V16.FCStd`, validate the saved ZIP, capture review screenshots, and request one bounded user approval.

HS-11 remains open. Structural ASA printing remains held.
