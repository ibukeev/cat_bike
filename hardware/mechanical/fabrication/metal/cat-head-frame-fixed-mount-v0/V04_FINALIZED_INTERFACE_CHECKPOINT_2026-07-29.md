# V0.4-M1 aluminum interface resumable checkpoint

Updated: 2026-07-29

## Current state

The aluminum-owned portion of `CAT-HEAD-SHELL-ALUMINUM-V0.4` is digitally
finalized for shell integration. The accepted rail targets, axes, roll,
21 mm straight socket opening, 1 mm lead-in, 30 mm insertion depth, and upper
M4 socket geometry did not change.

This checkpoint is not authorization to order, cut, drill, machine, assemble
for riding, or print the final ASA shell. The user has bought only the
19 x 19 x 2 mm rectangular aluminum rail stock; no plate is ordered or cut.

## Current review and output files

Tracked authority:

- `hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v04.json`
- `config/frame-fixed-mount-v04-final.json`
- `source/prepare_frame_fixed_mount_v04_interface.py`
- `source/generate_frame_fixed_mount_v04.py`
- `review/frame-fixed-mount-v04-final-summary.json`

Generated local review outputs:

- `output/v04-finalized-interface/flat-plates/head-rear-backplate-v04-1to1.svg`
- `output/v04-finalized-interface/flat-plates/head-rear-backplate-v04.dxf`
- `output/v04-finalized-interface/rail-cut-drill/rail-cut-and-drill-v04-1to1.svg`
- `output/v04-finalized-interface/machined-parts/lower-rail-shoe-v04-plan.svg`
- `output/v04-finalized-interface/machined-parts/lower-rail-shoe-left-v04.stl`
- `output/v04-finalized-interface/machined-parts/lower-rail-shoe-right-v04.stl`
- `output/v04-finalized-interface/review-model/frame-fixed-mount-v04-final-review.blend`
- `output/v04-finalized-interface/renders/v04-shell-integration-rear.png`
- `output/v04-finalized-interface/renders/v04-metal-and-shoes-rear.png`
- `output/v04-finalized-interface/renders/v04-right-shoe-detail.png`
- `output/v04-finalized-interface/validation/frame-fixed-mount-v04-validation.json`

The `output/` tree is ignored by Git and must be regenerated locally.

## Accepted decisions and dimensions

- The head remains frame-fixed. The handlebar, fork, and existing light steer
  independently below it.
- Primary bike-connector load paths are metal only; no weld and no printed
  polymer in the primary connector.
- Backplate remains 3 mm 6061-T6, 60 mm top width, 120 mm bottom width, and
  79.663819 mm high.
- Adapter holes remain four 6.6 mm paths at local X `±22`, V `±20` mm.
- Rail targets remain X `±40`, Y `267.336`, Z `147.132` mm.
- Accepted left/right rail axes, pitch `17.662°`, yaw `5.595°`, and
  head-X-projected cross-bolt roll remain frozen.
- V6.1 printed sockets remain 21 x 21 mm straight bores with 23 x 23 mm
  lead-in mouths, 30 mm insertion, and one M4 cross-bolt per socket.
- Finished rail length is `149.672 ±0.25 mm`; shop drawing callout is
  149.7 mm. Rough cut each rail to 151 mm and finish both ends square and
  deburred.
- Rail lower cut plane is 8 mm along the accepted axis from the rear-plane
  target. The seated upper end remains 0.5 mm short of the V6.1 stop.
- Upper M4 center is 130.972 mm from the lower cut end and 18.7 mm from the
  upper cut end.
- Lower M5 centers are 10 and 25 mm from the lower cut end.
- Each lower shoe is a mirrored, monolithic CNC-machined 6061-T6 part with a
  10 mm foot and fitted 14.7 x 14.7 mm nominal solid plug.
- Plug starts at axis offset 5.3 mm, ends at 45 mm, and inserts 37 mm into the
  tube. Four long edges receive 1.2 mm chamfers and the nose receives a
  1.0 mm chamfer.
- Each matched shoe/rail pair is clamped and jig-drilled together for two
  M5 x 30 through-bolts, washers, and nyloc nuts. The solid plug is the
  anti-crush load path. Bolt heads face the head centerline; nyloc nuts face
  outward. Each side uses 10 mm head/nut/washer envelopes and a 14 mm diameter
  by 25 mm straight tool approach.
- Three M5 x 12 screws and 10 mm washers attach each shoe to 8 mm minimum
  blind tapped engagement in the foot. Use removable medium-strength
  threadlocker.
- Right shoe/backplate centers are `(36,-30)`, `(47.4,-30)`, and `(38,-9)`
  mm in plate-local X/V. The left pattern mirrors X.
- Six backplate-to-shell M5 centers are `(-10,30)`, `(10,30)`, `(-20,0)`,
  `(20,0)`, `(-10,-30)`, and `(10,-30)` mm.
- There is no rail cutout in the backplate and no external shell
  pass-through. The rear bezel is removed for rail and metal service.

## Validation performed and results

The shared V0.4 interface validator, metal preflight, Blender generator, and
automated regressions pass.

Key digital results:

| Check | Result |
| --- | ---: |
| Rail cut derivation | 149.672 mm, exact |
| Frozen 21 mm socket / targets / axes | pass, unchanged |
| Minimum adapter-hole plate ligament | 11.1759 mm |
| Minimum shell-hole plate ligament | 7.0819 mm |
| Minimum shoe-hole plate ligament | 5.5766 mm |
| Minimum cut-hole pair ligament | 5.9 mm |
| Minimum hardware/tool envelope gap | 1.4 mm |
| Minimum solid-plug cross-hole end ligament | 9.25 mm |
| Adapter hardware to shoe-foot gap | 0.9691 mm |
| Minimum tapped-hole ligament in shoe foot | 3.8451 mm |
| Rails to installed rear bezel or bottom keel | 12.314 mm minimum |
| Lower M5 hardware/tool to fixed shell or keel | 62.8068 mm minimum |
| Shoes to fixed bottom keel | 112.4154 mm minimum |
| Backplate, rails, shoes vs. four fixed body shells | clear |
| Current provisional rear bezel vs. final shoes | localized conflict, 28 triangle-overlap pairs |

The provisional V6.1 rear bezel collision is an explicit shell-integration
handoff, not a reason to thin or shorten the finalized metal shoes. It is
isolated to the replaceable bezel. The shell session must regenerate the bezel
and six ASA pads around the exact V0.4-M1 metal envelope, then rerun the
complete A-39 inserted, seated, fastened, tool-access, and removal matrix.

## Rejected or unsafe variants

- Changing the accepted X `±40` rail targets, axes, roll, or 21 mm sockets in
  this metal pass: rejected.
- Reusing the old six-M5 rear pattern: rejected because its lower side paths
  overlap the accepted rail/shoe zones.
- Reducing the structural shoe merely to fit the provisional rear bezel:
  rejected; regenerate the replaceable ASA bezel.
- Square rail starting on the backplate midplane: rejected because its
  compound-angle lower corners interpenetrate the 3 mm plate. The finalized
  rail starts 8 mm inward on a solid plug.
- A hollow-tube lower cross-bolt without a fitted solid plug: rejected due to
  local wall crushing and unreliable clamp load.
- Separate unmatched drilling of rail and plug: rejected; each pair is
  transfer-drilled and labeled.
- Welding, printed primary connector features, forced oversize plugs, and
  unverified metal fabrication: rejected.

## Exact regeneration commands

From the repository root, run the metal preflight:

```bash
python3 hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/prepare_frame_fixed_mount_v04_interface.py
```

Regenerate the review pack against the locked V6.1 shell:

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-socket-portals-candidate-v6/gate9-socket-portals-candidate-v6.blend \
  --python hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/generate_frame_fixed_mount_v04.py
```

Run the focused automated regressions:

```bash
python3 -m unittest \
  tests.automated.test_cat_head_shared_interface \
  tests.automated.test_gate9_socket_portals_v6_summary
```

## Next physical and shell-review steps

1. Shell session reads the V0.4-M1 shared interface and tracked final summary.
   Regenerate the rear bezel and six large ASA structural pads without
   changing the metal hole pattern, rail axes, or 21 mm sockets.
2. Rerun A-39 using complete plate, shoe, rail, bolt, washer, nut, hand, and
   tool envelopes through inserted, seated, fastened, and removal states.
3. Measure the actual deburred tube inside width, inside height, and internal
   corner radii. Fit each 14.7 mm nominal plug to its labeled rail; do not
   force the plug.
4. Machine one rear-interface/shoe coupon. Confirm plate fit, plug insertion,
   stop contact, transfer drilling, M5 clamp behavior, washer/tool access, and
   repeatable disassembly.
5. Only after the regenerated shell and physical coupon pass, prepare a
   shop-reviewed fabrication package. Report quoted, ordered, cut, bent,
   drilled, machined, and received states before moving to the next state.
6. Validate the complete real headlight housing, beam, steering sweep, cables,
   independent metal tether, proof load, vibration, and progressive low-speed
   ride plan before riding.
