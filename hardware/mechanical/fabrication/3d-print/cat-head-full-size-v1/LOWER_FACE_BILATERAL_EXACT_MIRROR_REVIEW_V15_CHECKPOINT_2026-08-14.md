# Lower-Face Bilateral Exact-Mirror Review V15 Checkpoint — 2026-08-14

## Status

**REJECTED 2026-08-14.** Although the isolated bilateral numerical checks passed, the user found that V15 reused an incomplete legacy `right_upper_head` object, showed empty sectors in the upper shell, and left C046/C048/flange context appearing disconnected rather than integrated into its real owners. V15 must not be used as a source, mirror baseline, or print input. It is retained only as traceable rejected evidence. V16 supersedes it with a right-side owner-integration repair built from the complete V3 upper-head component set.

## Review/output files

- FreeCAD review: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/lower-face-bilateral-exact-mirror-review-v15/CAT_HEAD_LOWER_FACE_BILATERAL_EXACT_MIRROR_REVIEW_V15.FCStd`
- Blender review: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/lower-face-bilateral-exact-mirror-review-v15/CAT_HEAD_LOWER_FACE_BILATERAL_EXACT_MIRROR_REVIEW_V15.blend`
- Blender validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/lower-face-bilateral-exact-mirror-review-v15/validation-v15.json`
- FreeCAD handoff validation: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/lower-face-bilateral-exact-mirror-review-v15/freecad-validation-v15.json`
- Evidence renders: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/lower-face-bilateral-exact-mirror-review-v15/review/`
- Exported review objects: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/lower-face-bilateral-exact-mirror-review-v15/objects/`
- Approved left-upper-head context STEP/OBJ: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/lower-face-bilateral-exact-mirror-review-v15/source-context/`
- Contract: `config/lower-face-bilateral-exact-mirror-review-v15.json`
- Generator: `source/generate_lower_face_bilateral_exact_mirror_review_v15.py`

## Accepted decisions and locked dimensions

- The approved V14 right geometry is frozen and unchanged.
- Exact-mirror roles are lower face, C046, C048, outer head flange, outer eye flange, second head flange, and second eye flange.
- Mirror datum is `X = 0`; maximum indexed-coordinate and bounds error is `0.0 mm` for every mirrored role.
- Each side retains 60 deliberate lower-face review components.
- Both outer and second flange-pair gaps are `0.3000 mm` on both sides with `0.0 mm3` interference.
- C046-to-eye clearance is `4.6063 mm` and C048-to-eye clearance is `4.0317 mm` on both sides.
- Rear-cassette ownership, C006, and `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` are frozen and untouched.

## Validation performed and results

- Blender bilateral validation: PASS.
- Right-side V14 fingerprints: unchanged.
- Mirrored-role indexed coordinate error: `0.0 mm`; mirrored bounds error: `0.0 mm`.
- Lower-face mirrored volume difference: `0.0384 mm3` over approximately `120185 mm3`, below the `0.1 mm3` float-accumulation gate.
- Inherited lower-face center-seam overlap: `7.6095 mm3`, retained and below the `12.0 mm3` review gate.
- All other cross-side mirrored-role interference: `0.0 mm3`.
- Right owner engagement volumes: outer head/upper head `122.5160 mm3`; outer eye/eye `247.0317 mm3`; second head/lower face `26.2422 mm3`; second eye/eye `211.3736 mm3`.
- Left owner engagement volumes: outer head/approved left upper head `200.6612 mm3`; other three match the right side.
- Approved left upper-head OCCT source remains 41 valid closed solids, `2820/4410/1632` faces/edges/vertices, `147360.12 mm3`, and zero self-intersections. Its container hash drift is explicitly recorded; the named source object and exported STEP/OBJ are hash-locked.
- Saved FCStd is an intact `235002`-byte ZIP and contains all 18 expected up-to-date review objects.
- Representative right/left outer-head and second-eye flange meshes pass FreeCAD validation.
- FreeCAD flags each aggregate lower-face Mesh::Feature because it contains 60 disconnected solids and the retained center-seam contact. This is documented in `freecad-validation-v15.json`; it does not override the per-component Blender manifold evidence and it explicitly prevents treating V15 as a production-body or print release.

## Rejected or unsafe variants

- Mirroring the entire V14 right context was rejected because the approved left upper-head and eye sources already exist and are not replaceable by an invented symmetric context.
- Matrix-only mirroring was rejected for the verification path; coordinates are reflected directly and triangle winding is reversed so the stored mirror is exact and normals remain outward.
- The approved left upper-head OBJ has 40 connected mesh islands while its authoritative OCCT source has 41 valid solids because two valid solids touch. The counts are deliberately distinguished rather than forced to agree.
- A stale duplicate `review/review` evidence directory and Blender `.blend1` autosave were removed from the handoff output.
- No aggregate lower-face OBJ/FCStd mesh is approved for slicing. Production unification remains HS-18.

## Exact regeneration command

From `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/`:

```bash
blender --background --python source/generate_lower_face_bilateral_exact_mirror_review_v15.py -- --config config/lower-face-bilateral-exact-mirror-review-v15.json
```

The interactive FCStd is assembled through the FreeCAD MCP by importing the 18 generated OBJ review objects, fitting the axonometric view, and saving the path listed above.

## Historical review instructions

Open `CAT_HEAD_LOWER_FACE_BILATERAL_EXACT_MIRROR_REVIEW_V15.FCStd` and check only:

1. Both complete left/right head contexts are present and no side is missing.
2. Both flange pairs appear in matching positions on each side, remain internal, and show no exterior protrusions or old neck/pole geometry.
3. Both eye buckets retain clearance from C046/C048 and nearby reinforcements.
4. The left lower face follows the approved right V14 geometry as an exact bilateral counterpart without changing the approved asymmetric left upper head.

These instructions are historical only. V15 cannot close HS-11. Do not print structural ASA from V15.
