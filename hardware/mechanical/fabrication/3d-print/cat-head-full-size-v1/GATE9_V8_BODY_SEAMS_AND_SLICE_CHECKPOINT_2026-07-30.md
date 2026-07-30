# Gate 9 V8 Body Seams and Slice Checkpoint

Updated: 2026-07-30

## Current Review and Output Files

Source of truth:

- `config/gate9-body-seam-clearance-candidate-v8.json`
- `source/generate_gate9_body_seam_clearance_candidate_v8.py`
- `source/slice_gate9_body_seam_clearance_candidate_v8.py`
- `review/gate9-body-seam-clearance-v8-summary.json`

Generated review output:

- `output/gate9-body-seam-clearance-candidate-v8/gate9-body-seam-clearance-candidate-v8.blend`
- `output/gate9-body-seam-clearance-candidate-v8/parts/`
- `output/gate9-body-seam-clearance-candidate-v8/gate9-body-seam-clearance-v8.json`
- `output/gate9-body-seam-clearance-candidate-v8/slicer-review/gate9-v8-body-seam-slices.json`

The generated `output/` namespace is intentionally ignored by Git. Regenerate
it from the tracked config and sources when moving to another workstation.

## Accepted Decisions and Dimensions

- V8 starts from the digitally accepted V7 V0.5-M2 shell and does not move any
  aluminum-owned hole, rail axis, lower target, socket datum, or M4 station.
- The body-shell seam clearance is 0.6 mm around only the measured internal
  conflict components.
- Relief construction is subtractive only. Each actual overlap is split into
  local closed components, expanded by 0.6 mm in XYZ, and subtracted from the
  configured receiver.
- Seam ownership is explicit:
  - the rear bezel owns its perimeter and all four body shells receive relief;
  - each upper shell owns its same-side upper/lower seam;
  - the left upper shell owns the upper center seam;
  - the left lower shell owns the lower center seam.
- The rear bezel is removable along the accepted V0.5 rear-interface outward
  normal. Relief was generated at 2.5, 5.0, 7.5, 10.0, 12.5, and 15.0 mm and
  validated through 80 mm.
- A Boolean-created detached sliver may be discarded only below 5 mm3 per
  operation. Actual reported cleanup was 2.796 mm3 at the lower center seam,
  3.742 mm3 on the left upper bezel sweep, and 3.699 mm3 on the right.
- The inset/chamfered mirror-cap landing polygons remain protected. V8 relief
  cutters have zero triangle intersections with all selected landing polygons.
- Existing exterior extents are preserved. V8 construction permits only
  Boolean difference and reported sliver deletion; every final body volume is
  lower than its V7 source and remains inside the V7 XYZ extents.

## Validation Performed

The V8 generator passes every digital body-seam gate.

- All eight original seated conflict volumes are reduced to 0.0 mm3.
- The original measured conflicts included:
  - 442.920084 mm3 at the left upper/lower seam;
  - 434.583919 mm3 at the right upper/lower seam;
  - 430.717549 mm3 at the lower center seam;
  - 18.531887 mm3 at the upper center seam;
  - 163.487938 and 162.951252 mm3 at the upper rear-bezel seams.
- The complete rear-bezel service sweep is clear at 0, 2.5, 5, 7.5, 10,
  12.5, 15, 20, 40, and 80 mm.
- All eight production parts have one connected component, zero boundary
  edges, and zero nonmanifold edges.
- All 28 seated production-part pairs have zero positive overlap volume.
- Five assembly paths pass:
  - left lower shell away from left upper;
  - right lower shell away from right upper;
  - complete right-side module away from the complete left-side module;
  - rear bezel outward;
  - bottom keel downward.
- Every nonzero assembly-path sample is triangle-collision free. Seated
  exposed seam contact is allowed only when positive overlap volume is zero.
- All selected mirror-panel landing polygons remain untouched.
- The V0.5-M2 shell/aluminum interface revision remains unchanged.

Real support/brim-inclusive PrusaSlicer checks use the Original Prusa MK4/MK4S
0.4 mm nozzle and the tracked Generic ASA review profile.

- All eight V8 parts have a passing real slice.
- Minimum post-brim XY margin is 11.492 mm on `left_lower_face`.
- Exact eight-part total is 709.690 g filament.
- Support filament is 290.728 g.
- Support volume is 271.713 cm3.
- Estimated print time is 250,524 seconds, approximately 69.6 hours.
- The selected left-lower orientation is X 111, Y 30, Z 30 degrees.
- This is a feasibility result, not production G-code authorization.

## Rejected or Unsafe Variants

- A seated-only rear-bezel correction is rejected. It was clear at zero but
  collided with both upper shells during the first 10 to 15 mm of removal.
- Moving the rear bezel inward is rejected as a service path because it crosses
  the body cavity and remains collision-heavy.
- Removing the lower-center conflict without deleting tiny detached Boolean
  islands is rejected because the right lower shell becomes three components.
- A global clean-shell convex hull is rejected as an exterior acceptance test:
  valid internal rear structure intentionally extends behind the old open-shell
  envelope. V8 instead enforces difference-only construction, V7 extent
  containment, and direct mirror-landing protection.
- A positive-volume-free seated audit alone is rejected; complete insertion
  and removal paths are required.
- V8 is not permission to print the final ASA head. Seam retention, ears, eyes,
  glow panels, and the changed-angle lamp/steering portals remain unresolved.

## Exact Regeneration Commands

From the repository root:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_body_seam_clearance_candidate_v8.py
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_body_seam_clearance_candidate_v8.py --threads 8
python3 -m unittest tests.automated.test_gate9_body_seam_clearance_v8_summary
~~~

## Next Review Steps

1. Open the V8 review blend and inspect the eight seated parts, especially the
   lower center seam and the upper rear-bezel corners.
2. Design and validate the final internal seam retention. Do not restore
   opposing printed pins or overlapping reinforcement tabs; use single-owner
   lands or removable internal bridge plates with tool access.
3. Resolve the ear connector as bolt holes with robust, rooted pads and no
   pin-against-pin geometry.
4. Rebuild and validate the eye front frame/socket connection so every wall
   has a printable structural root.
5. Integrate the accepted glow-panel and mirror-cap landing requirements.
6. Revise the lamp and steering portals for the accepted aluminum/head angle.
7. Regenerate and repeat complete topology, assembly, aluminum insertion,
   mirror-landing, and real Prusa ASA validation before authorizing the full
   black-ASA print.
