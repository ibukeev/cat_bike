# V0.2 rear-backplate handoff resumable checkpoint

Updated: 2026-07-28

## Current state

V0.2 corrects the shell interference in the earlier external-rail concept. The
bike connector now stops at a compact adapter and 3 mm aluminum rear backplate.
Two separate rails live inside the head and run from lower machined shoes to the
blind upper Gate8 sockets. The head remains fixed to the bicycle frame.

The integration geometry is generated and passes its automated checks. This is
not a complete cut release: lower rail shoes, rear-base pass-throughs,
backplate perimeter holes, lamp clearance, physical coupons, and load tests are
still open.

Current review files:

- `output/renders/v02-assembly-front-oblique.png`
- `output/renders/v02-assembly-side.png`
- `output/renders/v02-rear-backplate-handoff.png`
- `output/renders/v02-internal-rails.png`
- `output/review-model/frame-fixed-mount-v02-review.blend`
- `output/review-model/frame-fixed-mount-v02-review.glb`
- `output/flat-plates/rear-boss-plate-1to1.svg`
- `output/flat-plates/bike-adapter-plate-1to1.svg`
- `output/flat-plates/head-rear-backplate-review-only.svg`
- `output/formed-parts/side-web-formed-drawing.svg`
- `output/formed-parts/lower-rail-shoe-concept-review.svg`
- `output/review-drawings/v02-side-integration-review.svg`
- `output/validation/frame-fixed-mount-v02-validation.json`

## Accepted decisions and dimensions

- No weld; aluminum primary connector structure.
- Frame-fixed head; handlebar and fork steer independently.
- Four factory boss centers: 30 x 90 mm; boss faces: 18 mm diameter.
- Rear plate: 60 x 115 x 4.75 mm 6061, with four 6.6 mm frame holes and
  independent tether slot.
- Two 3.18 mm 5052 side webs connect the rear plate to a 90 x 80 x 4.75 mm
  6061 compact adapter at 60 mm forward and 75 mm upward.
- Side-web centerline is 96.047 mm; bend-line height is 64 mm; end flanges are
  15 mm. Formed geometry only is released for review.
- Adapter mating pitch is -18.894665 degrees relative to the estimated boss
  plane so it opposes the actual head rear-plane normal.
- Head backplate is a 3 mm 6061 trapezoid: 60 mm top, 120 mm bottom, and
  79.663819 mm high.
- Adapter/backplate holes are four 6.6 mm holes at X +/-22 and V +/-20 mm.
- Rails are nominal 19.05 mm square aluminum tube with 158.172 mm modeled
  reference length.
- Revised rail pitch is 17.662 degrees, yaw is 5.595 degrees, and M4 socket
  axes are 5.333 degrees from head-horizontal.
- Lower rail targets lie on the backplate plane at X +/-40, Y 267.336,
  Z 147.132 mm, 15 mm above its lower edge.
- Socket minimum exterior recess is 8.205 mm.
- Existing fork-mounted headlight remains, but its clearance is unvalidated.

## Validation performed

Python compilation and Blender 5.2 generation completed. Gate8 was regenerated
after the socket aim and roll correction; both upper shell meshes and the
integrated socket coupon remain closed manifold, and all Gate8 acceptance flags
pass. Gate8 review renders were refreshed.

The V0.2 mount report status is `PASS - INTEGRATION GEOMETRY REVIEW ONLY`:

| Check | Result | Threshold |
| --- | ---: | ---: |
| Rear M6 minimum edge ligament | 9.2 mm | at least 8.0 mm |
| Boss face supported past plate edge | 3.5 mm | at least 0 mm |
| Adapter M6 minimum edge ligament | 16.7 mm | at least 10.0 mm |
| Adapter M5-to-M6 hole ligament | 5.45 mm | at least 4.0 mm |
| Backplate top-row M6 edge ligament | 12.168 mm | at least 8.0 mm |
| Rail-target maximum backplate-plane error | 0.000083 mm | at most 0.01 mm |
| Socket M4 axis from head-horizontal | 5.333 degrees | at most 10 degrees |
| Socket minimum exterior recess | 8.205 mm | at least 8.0 mm |
| Blind sockets integral with upper shells | pass | required |
| No external rail through shell | pass | required |
| No weld in primary load path | pass | required |

Estimated aluminum connector and backplate mass is 323 g excluding rails,
lower shoes, bolts, washers, nuts, and tether. No stress FEA or physical proof
load has been completed.

Visual QA covered all four V0.2 renders, three plate profiles, the formed side
web, the lower-shoe concept, and actual-shell side projection. The full Gate8
shell was imported into the mount GLB; the rails terminate inside the shell.

## Rejected or unsafe variants

- Steering-mounted head: rejected due to steering inertia, wind torque, and
  handlebar sweep.
- Front rack required solely as a connector: unnecessary; use the four factory
  bosses directly.
- Welded aluminum structure: rejected by user.
- Printed polymer as the bike connector primary load path: rejected for creep,
  fatigue, heat, and vibration uncertainty.
- V0.1 external rails passing through the plastic shell: geometrically false;
  Gate8 sockets are blind internal features.
- V0.1 portal axes: rejected because they miss the rear plate by 14.179 mm and
  roll the M4 axes 54.831 degrees from head-horizontal.
- The old 30.02 mm lamp-clearance claim: invalid because it used a simplified
  260 mm-high box instead of the actual 330 mm shell.
- Cutting the review-only backplate or rail shoes now: unsafe because perimeter
  fasteners, pass-throughs, drainage, and shoe details are unresolved.
- Selecting frame-bolt length from the current model: unsafe because blind-hole
  bottoming can imitate clamp torque.
- Printing upper-head G-code generated before the 2026-07-28 socket correction:
  obsolete geometry.

## Exact regeneration commands

From `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/`:

```bash
blender --background --python source/generate_frame_fixed_mount_v0.py
```

From the repository root for the matching Gate8 sockets:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate8_full_size_iteration.py
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/render_gate8_review.py
```

## Next physical-review steps

1. Print the rear and adapter `*-1to1.svg` templates at 100 percent; verify a
   ruler scale, all boss centers, full boss-face bearing, flatness, and cables.
2. Verify M6 pitch and probe all four blind depths from their boss faces.
3. Print the current integrated socket coupon. Test the actual 19.05 mm tube,
   bridge quality, insertion, rattle, M4 marking, drilling, and retention.
4. Make a rear-base/backplate coupon that resolves both rail pass-throughs,
   backplate perimeter attachment, drainage, and wiring access.
5. Detail and machine one mirrored lower-shoe pair with solid tube plugs and
   anti-crush load paths; transfer-drill only after full fit-up.
6. Measure the lamp housing width, height, front/back depth, and its center
   relative to the boss pattern. Add it to the GLB or make an accurate full-size
   cardboard volume, then check steering sweep and beam.
7. Have the selected shop return side-web bend radii and flat patterns for
   approval.
8. After metal fit-up, install the tether, proof-load, inspect, vibration-test,
   and perform progressive low-speed rides before normal use.
