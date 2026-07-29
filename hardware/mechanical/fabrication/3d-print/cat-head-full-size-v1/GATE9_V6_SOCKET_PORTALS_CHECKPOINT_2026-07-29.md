# Gate 9 V6.1 Conservative-Fit Socket Portals Checkpoint — 2026-07-29

## Scope and release state

V6.1 integrates the real square-tube socket geometry and corrected front/top
portal directions into the clean V5 upper shells. The socket axes, roll,
opening, insertion depth, lower targets, and M4 position come directly from
the coordinated `CAT-HEAD-SHELL-ALUMINUM-V0.4` interface.

The digital socket gate passes. The user accepted bypassing the physical
socket coupon in favor of a conservative 21.0 mm bore and 1 mm lead-in. This
is still not authority to print the upper shells, cut final rails, or drill
final rails because the remaining aluminum, lamp, ear, eye, panel, and seam
gates are unresolved.

Status:
`review_candidate_passed_digital_socket_gate_user_accepted_coupon_bypass`.

## Current review and output files

- Shared interface: `hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v04.json`
- Metal preflight config: `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/config/frame-fixed-mount-v04-interface.json`
- Metal preflight: `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/prepare_frame_fixed_mount_v04_interface.py`
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
- Generated optional diagnostic coupon STL:
  `output/gate9-socket-portals-candidate-v6/test-coupons/gate9_v6_socket_fit_coupon.stl`
- Generated renders:
  `output/gate9-socket-portals-candidate-v6/renders/`
- Generated slice report:
  `output/gate9-socket-portals-candidate-v6/slicer-review/gate9-socket-portals-v6-slices.json`

The generated `output/` tree is intentionally ignored and is reproducible from
the tracked source and config.

## Accepted interface and construction

Coordinated V0.4 values:

V0.3 remains preserved for reproducibility. V0.4 changes only the printed socket
allowance and lead-in; rail axes, targets, profile, backplate, and M4 geometry
remain unchanged.

- User-measured tube: 19 x 19 x 2 mm.
- Socket straight opening: 21.0 x 21.0 mm.
- Nominal clearance: 1.0 mm per side.
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
- Socket wall: 5.75 mm; outside width remains 32.5 mm.
- Square 45-degree lead-in: 1.0 mm deep, expanding the mouth to 23.0 x 23.0 mm.
- Broad portal pad: 68% of the selected source facet, 16.0 mm thick, with
  1.0 mm shell overlap.
- The pad is truly unioned to the upper shell and the socket is truly unioned
  through the pad. Append-only overlapping components are prohibited.
- Minimum socket recess behind the source exterior plane: 8.3999 mm.
- Portal-pad recess: 0.8 mm; neither side has an outside-plane vertex.
- Provisional modeled rail ends 0.5 mm before the blind stop for collision
  testing. Final cut length remains deferred.

## Validation performed and results

Geometry:

- The shared V0.4 interface validator passes.
- All six current printed parts and the coupon are one closed manifold
  component with zero boundary and nonmanifold edges.
- Each portal pad overlaps its shell in three triangle pairs before union.
- Each portal pad overlaps its socket in seven triangle pairs before union.
- Each upper shell gains approximately 43.08 cm3 of true-unioned portal
  material without changing its exterior bounding dimensions.
- Both 21.0 mm straight openings and 23.0 mm lead-in mouths match the
  interface, together with the unchanged axes, mirrored lower targets, and
  head-X roll.
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

- The targeted shared-interface/V5/V6 suite passes all 18 tests.
- The repository-wide automated suite runs 35 tests with one unrelated existing
  error: `test_gate1_panel_ids_and_pair_order_match` raises `KeyError:
  glow_pairs` in `test_cat_head_lighting_map.py`. This V6.1 change does not modify
  the lighting-map inputs or test.

These slices prove printer-envelope feasibility only. They are not tuned
production settings.

## Rejected or unsafe variants

- The Gate 8 append-only socket integration is rejected because it left many
  disconnected shell components.
- Re-aiming a socket from a convenient local shell face is rejected; V6 uses
  the coordinated V0.4 axes exactly.
- External rail pass-throughs and cutting the finished shell are rejected.
- A socket touching the shell at a few corners without a broad structural pad
  is rejected.
- Treating intended washer/nut bearing contact with the socket face as a shell
  collision is rejected; actual original-skin and tool envelopes are checked
  separately.
- The 158.172 mm reference must not be copied onto the stock as a final cut
  length.
- No untested geometry can guarantee fit against tube burrs, damage, printer
  calibration, or ASA shrink. The user explicitly accepted this residual risk;
  use a thin hidden-face shim if bolted physical rattle is unacceptable.

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

The V6.1 generator runs the V5 generator internally before adding the sockets.
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

```bash
python3 hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/prepare_frame_fixed_mount_v04_interface.py
```

## Next engineering step

The socket coupon is no longer a required gate. Keep its STL only as an
optional diagnostic if the eventual physical fit or bolted rattle is rejected.

Proceed in this dependency order:

1. Use the V0.4 metal preflight to coordinate the aluminum session without
   changing the accepted rail axes, targets, or 19 x 19 x 2 mm profile.
2. Finalize the lower rail shoes, solid anti-crush load paths, actual rail cut
   lengths, and backplate perimeter/shoe holes as one revision.
3. Validate the complete lamp and steering-sweep envelopes against that
   coordinated metal and printed-shell assembly.
4. Close the remaining two-bolt ear, rooted-eye, wrapped-panel, and shell-seam
   gates.
5. Generate and review the complete prospective final ASA candidate before
   releasing any expensive upper-shell or full-head print.

## Remaining production blockers

- Final rail cut lengths, lower shoes, and anti-crush plugs.
- Backplate perimeter and lower-shoe holes.
- Complete lamp and steering-sweep envelope.
- Accepted two-bolt ears.
- Connected and structurally rooted eye modules.
- Wrapped-panel lands/connectors and physical adhesive coupons.
- Remaining complementary shell seams and final complete hardware/tool
  sweeps.
