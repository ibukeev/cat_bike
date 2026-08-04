# Cat head frame-fixed aluminum mount V0.2

Status: **integration geometry review candidate; not released as a complete
metal assembly or for riding**.

This is the no-weld connector between the four RadRunner 2 head-tube bosses
and the 330 mm Gate8 cat head. The head stays fixed to the bicycle frame while
the fork, handlebar, and existing headlight steer below it.

## Corrected architecture

The earlier V0.1 concept incorrectly continued the aluminum rails through the
exterior plastic shell. Gate8 has blind sockets inside the upper shells, not
exterior portals. V0.2 separates the two systems at a removable aluminum rear
backplate:

1. A 4.75 mm 6061 rear plate bears on all four factory bosses.
2. Two formed 3.18 mm 5052 side webs place a compact adapter 60 mm forward and
   75 mm above the boss-pattern center.
3. The 90 x 80 x 4.75 mm 6061 adapter bolts to a 3 mm 6061 trapezoidal
   backplate fitted to the head rear service plane.
4. Inside the head, two independent 19.05 mm square rails start at mirrored
   machined lower shoes and end in the blind integral upper-shell sockets.
5. Each upper socket retains its rail with one transverse M4 bolt. The planned
   lower shoe uses a solid plug and two M5 cross-bolts; its exact geometry is
   intentionally deferred.
6. A separate metal safety tether connects the bike-side rear plate to the
   frame.

There is no weld and no printed polymer in the bike-connector primary load
path. The printed socket shells still require physical coupon and load testing.

## Selected dimensions

| Feature | V0.2 value |
| --- | ---: |
| Factory boss pattern | 30 mm horizontal x 90 mm vertical, center-to-center |
| Boss face diameter | 18 mm |
| Existing blank bolt under-head length | 14 mm; thread and blind depth unverified |
| Rear boss plate | 60 x 115 x 4.75 mm 6061-T6 |
| Rear frame holes | 4 x 6.6 mm at X +/-15, Z +/-45 mm |
| Twin side-web centerline | 60 mm forward, 75 mm upward, 96.047 mm long |
| Side webs | 3.18 mm 5052-H32, 64 mm bend-line height, 15 mm end flanges |
| Compact bike adapter | 90 x 80 x 4.75 mm 6061-T6 |
| Adapter to backplate | 4 x 6.6 mm at X +/-22, V +/-20 mm |
| Head rear backplate | trapezoid, 60 mm top, 120 mm bottom, 79.664 mm high, 3 mm 6061 |
| Rear-plane mating pitch | -18.894665 degrees relative to estimated boss plane |
| Internal rails | nominal 19.05 mm square aluminum tube |
| Modeled rail reference length | 158.172 mm; not a final cut length |

## Portal angle verification

The visible socket angle was genuinely wrong in V0.1. The old straight axes
missed the rear backplate plane by 14.179 mm and rolled the M4 cross-bolt axes
54.831 degrees away from head-horizontal.

The revised Gate8 sockets and rails use a full compound orientation:

| Quantity | Revised value |
| --- | ---: |
| Lower rail targets in head coordinates | X +/-40, Y 267.336, Z 147.132 mm |
| Height above rear-plane lower edge | 15 mm |
| Rail pitch above head-forward | 17.662 degrees |
| Rail yaw away from centerline | 5.595 degrees |
| M4 axis deviation from head-horizontal | 5.333 degrees |
| Minimum socket recess behind exterior plane | 8.205 mm |

Socket roll is defined by head X projected perpendicular to each rail axis.
This makes the M4 paths nearly horizontal while preserving socket recess and
shell integration. There are no new exterior openings.

## Fabrication and review files

The rear boss plate and compact bike adapter profiles are suitable for 1:1
paper checking and quote discussion:

- `output/flat-plates/rear-boss-plate.dxf`
- `output/flat-plates/rear-boss-plate-1to1.svg`
- `output/flat-plates/bike-adapter-plate.dxf`
- `output/flat-plates/bike-adapter-plate-1to1.svg`

These remain **review-only** and must not be sent for cutting yet:

- `output/flat-plates/head-rear-backplate-review-only.dxf`
- `output/flat-plates/head-rear-backplate-review-only.svg`
- `output/formed-parts/lower-rail-shoe-concept-review.svg`

The backplate perimeter holes, rail-shoe holes, rear-base pass-throughs, and
machined shoe dimensions are not defined. The side-web drawing specifies formed
geometry only; the selected shop must calculate bend allowance for its tooling:

- `output/formed-parts/side-web-formed-drawing.svg`

Review assets:

- `output/review-model/frame-fixed-mount-v02-review.blend`
- `output/review-model/frame-fixed-mount-v02-review.glb`
- `output/renders/v02-assembly-front-oblique.png`
- `output/renders/v02-assembly-side.png`
- `output/renders/v02-rear-backplate-handoff.png`
- `output/renders/v02-internal-rails.png`
- `output/review-drawings/v02-side-integration-review.svg`
- `output/validation/frame-fixed-mount-v02-validation.json`

## Headlight and steering status

The user confirmed that handlebar turning does not enter the four-boss
connector area. The existing fork-mounted headlight remains.

The reported 60 mm distance from the upper boss center to the top of the light
is only a vertical datum. The actual 330 mm Gate8 shell overlaps that elevation
in side projection, so the former 30.02 mm clearance claim is invalid. Housing
and beam clearance cannot be approved until the real lamp position and size are
added to the 3D model or checked with an accurate full-size mockup through the
complete steering sweep.

## Provisional hardware

- Four frame M6 bolts; length is not released. Verify thread pitch, blind depth,
  factory engagement, washer stack, and non-bottoming first.
- Eight M5 bolts, washers, and locknuts for the two formed side webs.
- Four M6 bolts, washers, and locknuts for the removable adapter/backplate
  interface.
- One M4 transverse bolt per upper printed socket.
- Lower rail-shoe, solid-plug, cross-bolt, and backplate-perimeter hardware are
  not released.
- One independent metal safety tether and positive-lock attachment hardware.

Use verified torque guidance for the selected fastener grade and interface.
Control stainless-on-aluminum galling and galvanic corrosion with an appropriate
assembly compound or isolation system.

## Release gates

Before metal ordering:

1. Print the boss and adapter SVGs at 100 percent and verify a ruler scale.
2. Confirm all four boss centers, complete 18 mm boss-face support, plate
   flatness, cables, M6 pitch, and every blind-hole depth.
3. Print the revised integrated socket coupon and test the actual square tube,
   M4 drilling, socket bridge, fit, and rattle.
4. Design and coupon-test the rear-base pass-through, mirrored lower shoes,
   backplate perimeter fasteners, drainage, and wiring route.
5. Put the actual lamp housing and Gate8 head into one full-size 3D or cardboard
   mockup. Check the complete steering sweep, beam, rider sightline, cables, and
   control access.
6. Have the fabricator return bend radii, deductions, material, and drawings for
   approval before cutting the 5052 webs.

Before riding, install the safety tether and proof-load the complete stationary
assembly in forward, rearward, up, down, and torsional directions to the greater
of 60 N or five times installed head weight. Follow with vibration testing and
progressive low-speed rides away from traffic. Stop for slip, noise, fretting,
cracks, permanent bend, cable contact, steering interference, or beam blockage.

## Regeneration

From this directory:

```bash
blender --background --python source/generate_frame_fixed_mount_v0.py
```

The authoritative inputs are `config/frame-fixed-mount-v0.json` and
`source/generate_frame_fixed_mount_v0.py`.
