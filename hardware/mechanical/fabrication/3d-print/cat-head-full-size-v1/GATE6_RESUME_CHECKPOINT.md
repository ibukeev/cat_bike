# Gate 6 Resume Checkpoint

Last updated: 2026-07-20

This is the restart point for the full-scale cat-head model after adding the
isolated eye lightboxes. Gate 6 is a review/test-print candidate, not yet
cleared for production printing.

## Current review files

- `output/10-design-gates/gate6-eye-modules/gate6-eye-modules-review.blend` - primary review.
- `output/10-design-gates/gate6-eye-modules/gate6-eye-modules-review.stl` - combined geometry
  review; do not use it as an individual print part.
- `output/10-design-gates/gate6-eye-modules/gate6-eye-module-validation.json` - generated
  validation record.
- `output/10-design-gates/gate6-eye-modules/eyes/` - six full-size eye parts.
- `output/10-design-gates/gate6-eye-modules/shells/` - complete seven-shell set containing the
  matching paired eye-mount tabs in both lower-face shells.
- `output/10-design-gates/gate6-eye-modules/small-model-100mm/` - scaled visual eye parts and
  combined per-eye assembly STLs.

Regenerate with:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate6_eye_modules.py
~~~

## Accepted design state

1. Preserve every accepted Gate 5 shell joint, rear frame, gusset, and truss
   hub. Gate 6 only adds eye modules and two matching mount tabs to each lower
   shell.
2. Each eye is an independent light-tight chamber with one bucket/bezel, one
   1.5 mm diffuser, and one removable opaque LED rear cap.
3. The corrected four-vertex eye silhouettes remain the visible apertures. The
   opaque bezel fills the rest of the older oversized eye opening.
4. Use four independently addressable 5 V RGB pixels per eye with an 11 mm
   diffuser gap. The actual strip pitch remains a physical-selection item; the
   cap provides a flat adhesive carrier rather than locking in a specific PCB.
5. The fitted bezel locates each module. Two recessed internal M2.5 flange
   bolts retain each eye at the outer-side and lower edge and resist rocking;
   both axes are parallel to the eye plane and produce no exterior holes. A
   hidden 4 x 2 mm bridge connects each outer-side head tab across the corrected
   eye-opening gap to the structural lower-face shell.
6. Each rear cap uses two internal M2.5 through-bolts. Both bosses are hidden
   beneath the broad opaque eye-surround wedge.
7. Four rear-cap posts hold the diffuser against a 0.3 mm black perimeter
   gasket. A 4 mm rear wire port must be sealed around the cable.
8. Buckets and caps are opaque ASA with a white reflective chamber liner.
   Diffusers are nominally 1.5 mm frosted or milky PETG.
9. The 100 mm-head-scale exports are visual-fit models only. Do not use their
   scaled M2.5 holes or wall thickness as a hardware validation.

## Validation snapshot

- Two independent eye lightboxes and six full-size printable eye parts.
- Two recessed head-mount flanges at the outer-side and lower eye edges, with
  two M2.5 retention paths per eye.
- Outer-side attachment bridges span 21.4169 mm right and 20.9853 mm left;
  generated BVH checks prove every head tab overlaps its shell and every module
  tab overlaps its bucket.
- Two removable-cap M2.5 paths per eye.
- Eight LED reference positions total and 11 mm diffuser clearance.
- All six eye parts and all seven revised shells are closed manifold.
- Every full-size eye part fits the 240 x 200 x 210 mm printer envelope.
- No eye fastener holes reach the exterior.
- Both 100 mm visual eye assemblies were exported.
- All automated acceptance checks pass.

## Next review / prototype tasks

1. Review the front silhouette, opaque bezel coverage, both head flanges, cap
   access, and wire-port direction in the Gate 6 `.blend` file.
2. Print one complete full-size eye plus the corresponding lower-shell eye
   region or a derived head-tab coupon.
3. Test diffuser fit, gasket compression, M2.5 access, hotspots, light leakage,
   and a 30-minute heat soak using four real pixels.
4. Print the 100 mm visual assemblies with the small head; do not attempt to
   use scaled M2.5 hardware.
5. Completed in Gate 7: the twenty approved glow facets are represented by
   nine mechanically retained inserts. LED light chambers remain deferred.
