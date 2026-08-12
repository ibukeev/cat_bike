# Right Eye Delete Strips / Extend Walls Review V6 — 2026-08-12

## Status

Isolated right-side review ready. V5 is rejected. V6 omits the two detached
front strip solids and replaces them by extending the complete corresponding
main-wall bodies to the user-selected `Face55` termination plane.

No left mirror, production integration, STL print export, slicing, ASA print,
or fabrication release is authorized.

## Review file

Open:

`output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-delete-strips-extend-walls-review-v6/CAT_HEAD_RIGHT_EYE_DELETE_STRIPS_EXTEND_WALLS_REVIEW_V6.FCStd`

Leave visible:

- `PROPOSED__RIGHT_EYE_BUCKET__DELETE_STRIPS_EXTEND_WALLS_V6`
- `PROPOSED__RIGHT_EYE_REAR_CAP__ONE_BODY_V1_ref_ref`

## Selected structured anchors

| Role | Face | Normal | Center mm | Area mm2 |
|---|---:|---|---|---:|
| Upper outer main wall | `Face679` / source `Face28` | `(-0.2180, 0.1259, 0.9678)` | `(69.77, 84.46, 172.11)` | `825.88` |
| Upper inner main wall | source `Face26` | `(0.2275, -0.1218, -0.9661)` | `(70.48, 84.52, 171.16)` | `820.90` |
| Side outer main wall | `Face682` / source `Face9` | `(-0.9045, -0.2936, 0.3092)` | `(36.99, 65.25, 152.67)` | `304.39` |
| Side inner main wall | source `Face21` | `(0.9004, 0.2883, -0.3259)` | `(38.55, 65.68, 152.35)` | `289.95` |
| Termination plane | `Face55` | `(0.3092, -0.9106, 0.2742)` | `(94.18, 76.89, 146.67)` | `859.82` |

Opposing upper normals differ by `0.60 deg`; opposing side normals differ by
`1.03 deg`, caused by source tessellation.

## Frozen numeric contract

- Omit original detached front bezel segments `0` and `1`.
- Preserve exact bezel segments `2` and `3`.
- Extend complete main-wall segment `0` (outer and inner faces) to `Face55`.
- Extend complete main-wall segment `1` (outer and inner faces) to `Face55`.
- Preserve `2.0 mm` existing wall thickness.
- Keep `0.15 mm` overlap into the unchanged main wall.
- Preserve remaining bucket components, post pockets, rear cap, connectors,
  and aluminum `CAT-HEAD-SHELL-ALUMINUM-V0.5` workstream.

## Validation

- Result: valid closed solid.
- Shells: `1`; solids: `1`.
- Faces: `655`.
- Result volume: `6518.97 mm3`.
- OCCT self-intersection: PASS.
- Rear-cap interference: `0.0000 mm3`.
- Known unrelated minimum bucket/cap clearance: `0.0239 mm` unchanged.
- Saved FCStd integrity: PASS; `962,111` bytes.

## Rejected variants

- V4: butchered/replaced the main body.
- V5: retained the unwanted detached front strips and added separate bridge
  material; failed user visual review.
- Zero-thickness surface extension: explicitly rejected. V6 extends paired
  outer/inner faces as full wall solids.

## Regeneration

```sh
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_right_eye_delete_strips_extend_walls_review_v6.py
```

## Next review

1. Confirm the two former detached strips are gone.
2. Confirm the upper and side main walls now run continuously to the `Face55`
   plane.
3. Inspect from inside and outside to confirm each is a full-thickness wall,
   not a surface sheet.
4. Confirm the rest of the bucket and rear cap remain unchanged.
