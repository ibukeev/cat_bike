# Gate 9 V6 Socket Portals Checkpoint — 2026-07-29

## Scope and release state

V6 integrates the real square-tube socket geometry and corrected front/top
portal directions into the clean V5 upper shells. The socket axes, roll,
opening, insertion depth, lower targets, and M4 position come directly from
the frozen `CAT-HEAD-SHELL-ALUMINUM-V0.3` interface.

The digital socket gate passes. This is not authority to print the upper
shells, cut final rails, or drill final rails. The small black-ASA socket
coupon is the only next print authorized by this checkpoint.

Status:
`review_candidate_passed_digital_socket_gate_physical_coupon_required`.

## Current review and output files

- Config:
  `config/gate9-socket-portals-candidate-v6.json`
- Generator:
  `source/generate_gate9_socket_portals_candidate_v6.py`
- Slicer driver:
  `source/slice_gate9_socket_portals_candidate_v6.py`
- Tracked result:
  `review/gate9-socket-portals-v6-summary.json`
- Automated regression:
  `tests/automated/test_gate9_socket_portals_v6_summary.py`
- Generated Blender review:
  `output/gate9-socket-portals-candidate-v6/gate9-socket-portals-candidate-v6.blend`
- Generated geometry report:
  `output/gate9-socket-portals-candidate-v6/gate9-socket-portals-candidate-v6.json`
- Generated shell STLs:
  `output/gate9-socket-portals-candidate-v6/shells/`
- Generated coupon STL:
  `output/gate9-socket-portals-candidate-v6/test-coupons/gate9_v6_socket_fit_coupon.stl`
- Generated renders:
  `output/gate9-socket-portals-candidate-v6/renders/`
- Generated slice report:
  `output/gate9-socket-portals-candidate-v6/slicer-review/gate9-socket-portals-v6-slices.json`

The generated `output/` tree is intentionally ignored and is reproducible from
the tracked source and config.

## Accepted interface and construction

Frozen V0.3 values:

- User-measured tube: 19 x 19 x 2 mm.
- Socket opening: 20.5 x 20.5 mm.
- Nominal clearance: 0.75 mm per side.
- Socket insertion depth: 30.0 mm.
- Lower rail targets: X = -40/+40, Y = 267.336, Z = 147.132 mm.
- Accepted left axis: `[-0.09294, -0.94874, 0.30208]`.
- Accepted right axis: `[0.09294, -0.94874, 0.30208]`.
- Roll: head X projected perpendicular to each axis.
- M4 clearance path: 4.5 mm diameter, 10 mm inside the mouth.
- M4 axes: 5.333 degrees from head X.
- The 158.172 mm rail value is an installed reference, not a cut length.

Retained provisional printed construction:

- Blind internal sockets; no external tube pass-through and no removable cap.
- Socket wall: 6.0 mm; outside width: 32.5 mm.
- Broad portal pad: 68% of the selected source facet, 16.0 mm thick, with
  1.0 mm shell overlap.
- The pad is truly unioned to the upper shell and the socket is truly unioned
  through the pad. Append-only overlapping components are prohibited.
- Minimum socket recess behind the source exterior plane: 8.2045 mm.
- Portal-pad recess: 0.8 mm; neither side has an outside-plane vertex.
- Provisional modeled rail ends 0.5 mm before the blind stop for collision
  testing. Final cut length remains deferred.

## Validation performed and results

Geometry:

- The shared V0.3 interface validator passes.
- All six current printed parts and the coupon are one closed manifold
  component with zero boundary and nonmanifold edges.
- Each portal pad overlaps its shell in three triangle pairs before union.
- Each portal pad overlaps its socket in seven triangle pairs before union.
- Each upper shell gains approximately 43.94 cm3 of true-unioned portal
  material without changing its exterior bounding dimensions.
- Both 20.5 mm openings, frozen axes, mirrored lower targets, and head-X roll
  match the interface.
- Socket features and pads clear every other current printed part.
- The 19 mm seated rail envelopes clear the owner socket walls by the modeled
  0.5 mm end gap and clear the installed rear bezel by 16.441 mm.
- Straight withdrawal/insertion samples at 0, 20, 50, 100, and 160 mm are
  clear for both rails with the rear bezel removed for service.
- The M4 body paths, head/washer and nut/washer shell-skin envelopes, and
  10 mm straight tool approaches are clear. Bearing contact with the unioned
  socket faces is intentional.

Slicer:

- Both modified upper shells and the flat-wall coupon have real
  brim/support-inclusive Generic ASA slices on the Original Prusa MK4/MK4S.
- Left upper: 162.90 g, 98.441 g support, 39.718 mm minimum XY margin.
- Right upper: 112.73 g, 52.295 g support, 39.272 mm minimum XY margin.
- Coupon: 13.72 g, 2.057 g support, approximately 58 m 40 s, 86.258 mm
  minimum XY margin.
- Exact current eight-part roll-up: 774.66 g filament, 388.317 g support,
  362.904 cm3 support volume, and 258,373 s (about 71 h 46 m).
- The limiting current eight-part margin remains 15.011 mm at the rear bezel,
  above the required 10 mm.

Automated regression:

- The targeted V5/V6 suite passes all 14 tests.
- The repository-wide automated suite runs 34 tests with one unrelated existing
  error: `test_gate1_panel_ids_and_pair_order_match` raises `KeyError:
  glow_pairs` in `test_cat_head_lighting_map.py`. This V6 change does not modify
  the lighting-map inputs or test.

These slices prove printer-envelope feasibility only. They are not tuned
production settings.

## Rejected or unsafe variants

- The Gate 8 append-only socket integration is rejected because it left many
  disconnected shell components.
- Re-aiming a socket from a convenient local shell face is rejected; V6 uses
  the frozen V0.3 axes exactly.
- External rail pass-throughs and cutting the finished shell are rejected.
- A socket touching the shell at a few corners without a broad structural pad
  is rejected.
- Treating intended washer/nut bearing contact with the socket face as a shell
  collision is rejected; actual original-skin and tool envelopes are checked
  separately.
- The 158.172 mm reference must not be copied onto the stock as a final cut
  length.
- Digital 0.75 mm-per-side clearance is not a substitute for the ASA coupon:
  actual tube corner radius and ASA shrink remain unknown.

## Exact regeneration commands

Run from the repository root:

```bash
blender --background \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_rear_architecture_comparison_v4.py \
  -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-rear-architecture-comparison-v1.json \
  --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-rear-architecture-comparison-v1
```

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-rear-architecture-comparison-v1/gate9-rear-architecture-comparison-v1.blend \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_socket_portals_candidate_v6.py \
  -- --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-socket-portals-candidate-v6.json
```

The V6 generator runs the V5 generator internally before adding the sockets.
The current eight-part slicer roll-up uses the unchanged V5 lower shells,
ears, rear bezel, and keel, so regenerate the V5 slice report first when it is
not already present:

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_complementary_service_parts_candidate_v5.py \
  -- --threads 8
```

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_socket_portals_candidate_v6.py \
  -- --threads 8
```

```bash
python3 -m unittest tests.automated.test_gate9_socket_portals_v6_summary
```

## Next physical-review step

Print only:

`output/gate9-socket-portals-candidate-v6/test-coupons/gate9_v6_socket_fit_coupon.stl`

Use the intended black ASA process and the prescribed flat-wall orientation.
Allow the coupon to cool completely before testing.

1. Insert both ends of the real 19 x 19 x 2 mm tube without sanding the
   coupon.
2. Repeat with the tube clocked through multiple 90-degree orientations to
   expose stock squareness and corner-radius variation.
3. Confirm it reaches the blind stop by hand and removes without cracking,
   whitening, or tools.
4. Record fit as free, appropriately snug, excessively loose, or impossible.
5. Check for unacceptable rattle after full cooling.
6. If the fit is acceptable, use only a sacrificial tube offcut for the M4
   transfer-drill, bolt, washer, nut, and tool-access test. Do not drill a
   final rail.
7. Report the result before upper-shell printing. A failed coupon changes the
   socket allowance; it does not authorize sanding the production shells.

## Remaining production blockers

- Physical socket coupon and actual tube fit.
- Actual tube corner radius and ASA-process shrink.
- Final rail cut lengths, lower shoes, and anti-crush plugs.
- Backplate perimeter and lower-shoe holes.
- Complete lamp and steering-sweep envelope.
- Accepted two-bolt ears.
- Connected and structurally rooted eye modules.
- Wrapped-panel lands/connectors and physical adhesive coupons.
- Remaining complementary shell seams and final complete hardware/tool
  sweeps.
