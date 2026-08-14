# Right Upper Head C001 A/B User Orientation V1 Checkpoint — 2026-08-14

## Status

The user rotated and saved the complete one-object shell project. The exact
saved transform is preserved and synced. Geometry and scale are unchanged.

Validation status is **HOLD**, not print release. The shell fits the configured
MK4 bed nominally, but the rear margin is only `1.8748 mm`, planar bed contact
is `0.0 mm2`, brim is disabled, and the embedded material profile is Generic
PLA rather than ASA.

## Frozen source and accepted facts

- Project: `output/50-slicer-projects/right-upper-head-c001-ab-orientation-handoff-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ORIENTATION_HANDOFF_V1.3mf`
- Project SHA-256: `0941d65a81594754d33382a584ad2963ed2c14f6034a1a8534d724d9cca8c8a6`.
- Complete shell: one manifold part, `3418` facets, `77958.335938 mm3`.
- Scale: `1.0`; geometry change: `0.0 mm`.
- Saved 3MF transform: `[0.622046419, -0.267301093, -0.735940472, -0.069302815, -0.955029261, 0.288298858, -0.779907284, -0.128332526, -0.61259725, 111.575601, 105.453971, 55.0493613]`.
- Configured printer: Original Prusa MK4, `250 x 210 x 220 mm`, `0.4 mm` nozzle.
- Placed envelope: `201.0863 x 197.0728 x 126.3799 mm`.
- Bed position: X `18.4989..219.5852`, Y `11.0524..208.1252`, Z `0.0..126.3799 mm`.
- Margins: left `18.4989`, right `30.4148`, front `11.0524`, rear `1.8748 mm`.

All head-shell geometry, the A/B features, eyes, ears, lower face, rear
cassette, C006, reinforcement, and `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2` remain
frozen. This validation does not edit CAD geometry.

## Validation and rejected shortcuts

- Topology, one-part identity, volume, and unit scale: PASS.
- Nominal MK4 bed containment: PASS.
- Required `10 mm` XY reserve on every side: FAIL.
- Planar bed contact within `0.05 mm`: `0.0 mm2`; HOLD.
- Yaw-only search cannot obtain `10 mm` on all sides; its best centered minimum
  margin is `8.0480 mm`. A small tilt change or an explicitly relaxed margin
  gate is required.
- The embedded Generic PLA profile is not an ASA release profile.
- Automatic snug supports are enabled, but brim width is `0 mm`.
- No G-code or diagnostic slice was generated.
- Do not translate the part alone to solve the rear margin: the `197.0728 mm`
  Y footprint allows only `6.4636 mm` per side when centered on a 210 mm bed.

## Current validation output

`output/50-slicer-projects/right-upper-head-c001-ab-orientation-handoff-v1/user-orientation-validation-v1.json`

## Next physical-review step

Keep this orientation as the visual reference. Make a small tilt adjustment
that reduces the Y footprint below `190 mm`, then center the object. Select the
intended ASA profile and choose brim/support settings. After explicit approval
to generate a diagnostic slice, validate first-layer/support footprint, layer
continuity through the integrated A/B features, print time, and material use.
