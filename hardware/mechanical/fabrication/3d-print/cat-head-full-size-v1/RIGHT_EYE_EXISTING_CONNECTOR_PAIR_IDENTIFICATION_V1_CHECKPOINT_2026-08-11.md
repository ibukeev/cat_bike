# Right Eye Existing Connector Pair Identification V1 Checkpoint

## User-confirmed behavior

Confirmed 2026-08-11: retain the complete lower existing connector set and
relocate the other complete existing set around the right eye-module perimeter.
Move both mating halves together: the bucket-side boss and removable-cap ear.
Preserve the existing cylindrical M2.5 construction. Do not add a connector to
the broad rear-cap face.

## Current review

`output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-bucket-cap-anchor-audit-v1/CAT_HEAD_RIGHT_EYE_EXISTING_CONNECTOR_PAIR_IDENTIFICATION_V1.FCStd`

The review contains separately named source components:

- retained lower bucket boss and cap ear;
- move-candidate bucket boss and cap ear;
- unchanged source bucket and rear-cap context.

Source component centers used only for identification:

- retained bucket boss: `(61.962, 74.637, 131.963) mm`;
- retained cap ear: `(60.776, 77.536, 131.310) mm`;
- move-candidate bucket boss: `(84.757, 87.593, 149.266) mm`;
- move-candidate cap ear: `(83.571, 90.492, 148.613) mm`.

No component has been moved, remodeled, unioned, mirrored, or exported for
printing. The sphere-datum review is rejected and must not be used.

## Frozen geometry

Visible aperture, diffuser, eye-to-head flanges, head/ear owners, lower/rear
ownership, reinforcement direction, C006, and
`CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` remain unchanged.

## Next structured selection

In the current FreeCAD review, select the narrow upper perimeter wall face or
its long exterior edge where the complete move-candidate pair should attach.
Do not select the broad rear-cap face. After selection, record the owning
object, sub-element ID, centroid, normal, dimensions, and edge distances before
creating any moved geometry.

## Regeneration/source command

Frozen Gate 6 baseline only:

```sh
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate6_eye_modules.py
```

This command recreates the known disconnected baseline and is not a print
release command.
