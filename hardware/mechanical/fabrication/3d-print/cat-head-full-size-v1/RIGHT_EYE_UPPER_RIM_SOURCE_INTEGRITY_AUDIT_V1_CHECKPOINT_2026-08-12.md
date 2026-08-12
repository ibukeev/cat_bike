# Right Eye Upper-Rim Source-Integrity Audit V1 Checkpoint — 2026-08-12

## Status

Diagnostic complete. The current right-eye "one-body" review is not a safe
production source: its upper-rim source is a separate valid solid that is only
point-tangent to the exported bucket owner. This records the fault; it does not
approve a repair, mirror, STL, slicing, or ASA print release.

## Review file

- FreeCAD: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-upper-rim-source-integrity-audit-v1/CAT_HEAD_RIGHT_EYE_UPPER_RIM_SOURCE_INTEGRITY_AUDIT_V1.FCStd`

The file contains copied, unchanged audit references for the current bucket,
the dropped upper-rim component, and the removable rear cap.

## Measured failure

- Bucket owner: valid, closed, watertight, one solid, `656` faces,
  `6398.56 mm3`.
- Dropped upper-rim source: valid, closed, watertight, one solid, `29` faces,
  `2603.47 mm3`.
- Bucket/rim volumetric intersection: `0.0000 mm3`.
- Bucket/rim minimum distance: `0.0000 mm`.
- Sole reported contact point: `(103.74, 91.15, 178.89) mm`.

Therefore a successful-looking fuse can retain only the bucket body while
silently omitting the rim. A result of "one solid" is insufficient; the repair
must prove positive retained volume from every required source component.

## Rejected variants

- Global `(+0.5,+0.5,+0.5) mm` rim shift: changed intended placement and left
  a visible local opening.
- Diagonal `(+0.35,+0.35,+0.35) mm` shift: misleading Boolean result and no
  reliable closure of the visible opening.
- `8 x 8 x 6 mm` and `4 x 4 x 4 mm` bridge blocks: visible square artifacts.
- Tucked `2 x 8 x 2 mm` and `3 x 8 x 3 mm` blocks: touched both sources, but
  the final audit still contained two solids.

None was saved as an approved review or production owner.

## Required repair contract

1. Preserve original rim placement and the current bucket exterior bounds.
2. Use actual selected mating faces/edge envelope, not a global translation or
   axis-aligned cosmetic patch.
3. Produce exactly one valid closed solid.
4. Prove positive retained material from every required bucket source.
5. Preserve the rear-cap interface and prove zero rear-cap interference.
6. Recheck four post pockets, both connector pairs, tool paths, wire port, and
   the visible upper-rim opening before any left mirror.

## Exact regeneration command

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/split_right_eye_owner_components_for_freecad_review_v1.py
```

## Next review

Rebuild the right bucket from the six clean source owners using a deterministic
overlap/union sequence with per-source retained-volume evidence. Present only
the corrected right bucket plus unchanged rear cap. Do not mirror, export,
slice, or print until the one-side result passes and is visually approved.
