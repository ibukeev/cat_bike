# Gate 9 V7 / V0.5 Shell Correction Checkpoint

**Date:** 2026-07-29
**Status:** Rear-interface digital correction PASS; physical coupon, complete
head correction, and final ASA release remain held.

## Current authority and review files

- Shared interface:
  `hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v05.json`
- Aluminum handoff checkpoint:
  `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/V05_M2_COORDINATED_BOTTOM_M5_CHECKPOINT_2026-07-29.md`
- Aluminum source commit:
  `871f6be685ce78e06d6463d8465a7749917098d0`
- Shell configuration:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-m2-rear-interface-candidate-v7.json`
- Shell generator:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_m2_rear_interface_candidate_v7.py`
- Real-slice driver:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_m2_rear_interface_candidate_v7.py`
- Tracked validation:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/review/gate9-v7-v05-shell-correction-validation.json`
- Generated review model:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-m2-rear-interface-candidate-v7/gate9-m2-rear-interface-candidate-v7.blend`
- Generated geometry report:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-m2-rear-interface-candidate-v7/gate9-m2-rear-interface-candidate-v7.json`
- Generated real-slice report:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-m2-rear-interface-candidate-v7/slicer-review/gate9-v7-m2-rear-interface-slices.json`
- Review renders:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-m2-rear-interface-candidate-v7/renders/`

Generated outputs are ignored build artifacts. Regenerate them from the tracked
configuration and source; do not infer their state from filenames alone.

## Accepted decisions and dimensions

1. V0.5 remains locked. Only the coordinated bottom shell M5 pair is at local
   X `+/-7.4`, V `-30`. Every other plate hole, adapter hole, angle-base hole,
   rail axis, X `+/-40` lower target, 21 mm socket, M4 retention station, and
   compound rail datum is unchanged.
2. Six shell-side M5 pads are true-unioned into four owner shells. The narrow
   bottom pads remain `14 x 36 x 12 mm`.
3. All six joints use an M5x20 rear-loaded bolt and 10 mm outside-diameter
   washer into a shell-side captive M5 nyloc. Install each nyloc before
   inserting the complete M2 module.
4. The actual nyloc envelope is 8.0 mm across flats / 9.24 mm across corners.
   The printed pocket is 8.2 / 9.47 mm, 5.5 mm deep, with 0.1 mm flat
   clearance per side and 0.6 mm open-side overlap. The minimum retained pocket
   wall is 2.265 mm and the solid pad depth behind the pocket is 6.5 mm.
5. Each structural root is a 30 x 24 mm face (`720 mm2`) spanning 8 mm:
   nominally 1 mm controlled shell overlap and 7 mm cavity reach.
6. Preassembled crossbolt, head, and nut service tunnels use 0.6 mm radial and
   axial clearance across 31 mm socket withdrawal. They cut only the new
   internal upper truss, not the inherited V6 exterior shell.
7. The rigid blind-socket pair is not serviceable: it drifts 2.7882 mm across
   30 mm with only 1.0 mm lateral clearance. The accepted design therefore
   keeps removable outer ASA socket caps.
8. Each cap restores the frozen 21 mm cavity, has 0.3 mm receiver clearance,
   clears its shell by 0.3 mm and its rail by 1.0 mm, and uses four accessible
   M3 fasteners.

## Validation performed and results

The geometry report passes all 15 V7 rear-interface checks:

- V0.5-M2 contract and every locked datum match;
- all six pad bearing, staged hardware, and tool envelopes clear;
- all four roots have adequate area and controlled shell overlap;
- owner-shell unions are real, opposing structures are disjoint, and all six
  body parts plus both caps are individually one closed manifold component;
- seated metal clears the printed parts;
- all 14 socket-withdrawal positions plus four rear-clearance positions pass;
- cap-off removal and reverse insertion pass;
- cap-on rail, shell, and M3 tool clearances pass; and
- socket and cap cuts preserve the inherited exterior shell skin.

The real PrusaSlicer run used an Original Prusa MK4/MK4S, Generic ASA,
supports, and a 5 mm brim. All eight changed production parts pass the required
10 mm post-toolpath XY margin. The minimum is 11.935 mm on
`left_lower_face`; total estimated filament is 714.76 g, including
293.975 g of support, and total estimated print time is 252124 seconds
(about 70 hours 2 minutes).

The accepted left-lower pose is X/Y/Z `111 / 30.5 / 30.5 deg`. It produces
89.357 g support. STL hashes in the tracked validation match the STLs used for
the real G-code after the final hardware-reference correction.

## Rejected or unsafe variants

- Do not return to the rigid blind upper socket. The two frozen axes cannot
  share the required 30 mm withdrawal within the available clearance.
- Do not plan to place a wrench on a middle M5 nut after inserting the
  preassembled M2 module. The crossbolts block that operation; the captive nut
  must be installed first.
- Do not omit the crossbolt service tunnels. The inherited V0.5 preassembled
  crossbolt envelopes otherwise collide with new upper truss material.
- Do not use cap geometry coplanar with the receiver shell. It falsely passes
  intent but produces a real cap/shell collision; 0.3 mm receiver relief is
  required.
- Do not use the inherited left-lower slicer pose X/Y/Z `111 / 30 / 31 deg`;
  its real support/brim toolpath leaves only 8.1 mm front margin.
- Do not select the alternative left-lower passing pose X/Y/Z
  `58 / 132 / 136 deg`; it needs 379.457 g support versus 89.357 g for the
  accepted pose.

## Exact regeneration commands

From the repository root:

```sh
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-socket-portals-candidate-v6/gate9-socket-portals-candidate-v6.blend \
  --python-expr "import sys; sys.path.insert(0, 'hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source'); import generate_gate9_m2_rear_interface_candidate_v7 as candidate; candidate.v6.main=lambda: None; candidate.main()" \
  -- --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-m2-rear-interface-candidate-v7.json

python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_m2_rear_interface_candidate_v7.py --threads 8
```

The slicer driver reuses same-path G-code when present. Delete or relocate only
the specific candidate G-code when a fresh real slice is required; compare the
source STL SHA-256 values to the tracked review before accepting cached
results.

## Remaining release holds and next physical review

This checkpoint closes only the four non-bottom V7/V0.5 rear-interface defects.
It does **not** authorize the complete final ASA head print.

Before metal cutting or complete-head ASA printing:

1. receive and measure the ordered equal angle and the purchased rail stock;
2. approve and print a small rear-interface/angle/captive-nut coupon;
3. prove fastener fit, captive-nut retention, countersink and taper bearing,
   crossbolt service, cap fit, and repeatable assembly with actual hardware;
4. correct and validate the still-open ear, under-ear, eye, glow-panel, exterior,
   seam, and mirror-panel findings in
   `hardware/mechanical/CAT_HEAD_MOUNT_AND_SHELL_PHYSICAL_FIT_REVIEW_2026-07-28.md`;
5. validate actual headlight, beam, steering, and cable clearance; and
6. complete tether, proof-load, vibration, and progressive ride tests.

The next CAD slice should address the remaining complete-head physical-fit
findings as one traceable shell revision while preserving this locked rear
interface and its saved Prusa orientations.
