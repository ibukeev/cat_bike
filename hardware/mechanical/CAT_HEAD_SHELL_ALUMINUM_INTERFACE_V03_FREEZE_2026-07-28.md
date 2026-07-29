# Cat Head Shell / Aluminum Interface V0.3 Freeze

**Date:** 2026-07-28
**Revision:** `CAT-HEAD-SHELL-ALUMINUM-V0.3`
**Status:** Frozen for coordinated rear-architecture comparison; not a print,
cut, drilling, or riding release
**Supersedes:** the unmeasured nominal-rail assumption in C-005 and the active
shared dimensions duplicated in the Gate 8 and aluminum V0.2 configs

## 1. Authority

The machine-readable authority is:

`hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v03.json`

Both new workstreams resolve that file rather than treating their historical
configs as shared-interface authorities:

- shell:
  `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-coordinated-asa-candidate-v1.json`
- aluminum:
  `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/config/frame-fixed-mount-v03-interface.json`

Gate 8 and aluminum V0.2 remain immutable historical/review baselines. Their
generated outputs are not relabeled as V0.3.

## 2. Measured rail stock

The user physically measured and confirmed:

| Property | V0.3 value |
|---|---:|
| Outside width | 19.0 mm |
| Outside height | 19.0 mm |
| Wall thickness | 2.0 mm |
| Derived inside width/height | 15.0 x 15.0 mm |
| Available stock length | 36 in = 914.4 mm |
| Dimensional consistency | Reported the same along the stock |
| Corner radius | Not measured |
| Alloy/temper | Not confirmed |

Final rail cut lengths remain deferred until the lower shoes, solid plugs,
socket seating depth, rear cassette, and complete fit-up are fixed.

## 3. Frozen comparison interface

- Preserve the 330 mm full-size head exterior for the primary comparison.
- Rear plane center: `[0, 264.01125, 171.74025]` mm.
- Rear plane outward normal: `[0, 0.990996, 0.133894]`.
- Aluminum backplate: 3 mm 6061-T6 trapezoid, 60 mm top, 120 mm bottom,
  79.663819 mm high.
- Adapter pattern: four 6.6 mm paths at X `±22` and local V `±20` mm.
- Lower rail targets: X `±40`, Y `267.336`, Z `147.132` mm.
- Accepted rail axes:
  - left `[-0.09294, -0.94874, 0.30208]`;
  - right `[0.09294, -0.94874, 0.30208]`.
- Rail pitch `17.662°`; yaw `5.595°`.
- Socket roll: head X projected perpendicular to each rail axis.
- Socket opening: 20.5 x 20.5 mm.
- Nominal clearance from measured stock: 1.5 mm total, 0.75 mm per side.
- Socket insertion depth: 30 mm.
- Upper retention: one 4.5 mm M4 clearance path 10 mm inside the mouth.
- Expected M4-axis deviation from head X: `5.333°`.
- Primary bike connector load path remains metal only.
- Rear service direction remains rear-loaded after joining the main shells.

Changing any frozen value requires one coordinated revision affecting the
shell, backplate, lower shoes, rails, sockets, validation, and checkpoints.

## 4. Validation performed

The standalone interface validator passed:

- rear-plane normal unit error within `0.0001`;
- lower-target plane error `0.0000831` mm, below the `0.01` mm limit;
- rail-axis unit and symmetry checks;
- measured-wall derivation of the 15 x 15 mm inside profile;
- 0.75 mm nominal socket clearance on every side, within the frozen 0.5–1.0
  mm review range;
- 914.4 mm stock covers two 158.172 mm modeled routes before final fit/cut
  allowance;
- raw 19 mm tube envelope leaves approximately 4.851 mm to the sloped
  backplate edge at each X `±40` lower target.

The 4.851 mm value covers only the raw tube. It is not clearance approval for
the lower shoe, flange, bolt, washer, nut, manufacturing tolerance, hand, or
tool envelope.

Both consumer preflights passed and reported the identical revision:

- `PASS - GATE 9 SHARED INTERFACE PREFLIGHT`;
- `PASS - METAL V0.3 SHARED INTERFACE PREFLIGHT`.

Python compilation and JSON parsing passed. Blender, STL export, drawing
export, rendering, PrusaSlicer, and physical coupon tests were intentionally
not run.

## 5. Generation holds

V0.3 geometry generation remains disabled because:

1. the rear cassette, retained partition, and scale alternatives have not been
   compared and selected;
2. Gate 8 append-only structural mesh joins still violate the required
   single-body topology contract;
3. lower shoes and anti-crush plugs are not detailed;
4. rail pass-throughs and backplate perimeter/shoe holes are not released;
5. the complete shell/aluminum/hardware/tool collision matrix does not exist;
6. a matching Gate 9 shell validation report does not exist; and
7. physical rear-interface and socket coupons have not passed.

## 6. Rejected or unsafe variants

- Do not restore the nominal 19.05 mm active-stock assumption.
- Do not resize the 20.5 mm socket solely from nominal catalog dimensions; use
  a full-scale coupon to account for ASA shrinkage and printer variation.
- Do not move the X `±40` rail targets independently.
- Do not treat raw tube-to-plate edge clearance as lower-shoe clearance.
- Do not overwrite or relabel Gate 8 or aluminum V0.2 outputs as V0.3.
- Do not cut rails to the 158.172 mm modeled reference length.
- Do not release backplate or shoe holes before the rear architecture and
  complete service sequence are selected.

## 7. Exact preflight commands

Run from the repository root:

```bash
python3 hardware/mechanical/interfaces/cat_head_interface.py
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/prepare_gate9_shared_interface.py
python3 hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/prepare_frame_fixed_mount_v03_interface.py
```

There is intentionally no V0.3 Blender regeneration command yet. The next
versioned generators must consume the preflight loaders, write the V0.3
revision and interface hash into their validation reports, and use the new
Gate 9/V0.3 output namespaces before generation is enabled.

Historical commands remain documented in the Gate 8 and aluminum V0.2
checkpoints but are not V0.3 release commands.

## 8. Next review steps

1. Build review-only geometry for the retained partition, smallest-useful
   uniform scale, and full-size rear-cassette/moved-seam alternatives.
2. Include complete backplate, rail, raw lower-shoe allowance, hardware, and
   tool envelopes in every comparison.
3. Slice each alternative with the required brim/support policy and record
   actual bed margin, support volume, time, supported exterior area, and
   removal risk.
4. User selects the architecture and service sequence.
5. Repair the single-body topology and validation foundation before detailed
   subsystem geometry or any full structural print.
