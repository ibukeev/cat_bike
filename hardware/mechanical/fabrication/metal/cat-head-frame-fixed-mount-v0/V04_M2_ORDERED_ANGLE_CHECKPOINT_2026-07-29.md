# V0.4-M2 ordered-angle aluminum interface resumable checkpoint

Updated: 2026-07-29

## Current state

The aluminum-owned portion of `CAT-HEAD-SHELL-ALUMINUM-V0.4` now uses the
user-ordered Randall Manufacturing 6063-T6 equal-leg angle stock instead of
the superseded V0.4-M1 CNC lower shoes. The angle was ordered from Lowe's on
2026-07-29 but has not been received or measured. The 3 mm backplate has not
been ordered or cut. The previously purchased rail stock remains the only
other committed metal.

The accepted rail targets, axes, roll, 21 mm socket opening, 1 mm lead-in,
30 mm insertion depth, upper M4 locations, backplate outline, four adapter
holes, six shell M5 centers, and six lower connector M5 plate centers did not
change. This is a digitally generated shell-integration handoff, not a metal
fabrication or riding release.

## Current review and output files

Tracked authority:

- `hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v04.json`
- `config/frame-fixed-mount-v04-interface.json`
- `config/frame-fixed-mount-v04-final.json`
- `source/prepare_frame_fixed_mount_v04_interface.py`
- `source/generate_frame_fixed_mount_v04.py`
- `review/frame-fixed-mount-v04-final-summary.json`

Generated local review outputs:

- `output/v04-m2-angle-stock/flat-plates/head-rear-backplate-v04-1to1.svg`
- `output/v04-m2-angle-stock/flat-plates/head-rear-backplate-v04.dxf`
- `output/v04-m2-angle-stock/rail-cut-drill/rail-cut-and-drill-v04-m2-1to1.svg`
- `output/v04-m2-angle-stock/rail-cut-drill/rail-lower-compound-wrap-v04-m2-1to1.svg`
- `output/v04-m2-angle-stock/hand-fabricated-parts/lower-angle-connector-v04-m2-plan.svg`
- `output/v04-m2-angle-stock/review-model/frame-fixed-mount-v04-m2-angle-stock-review.blend`
- `output/v04-m2-angle-stock/renders/v04-m2-angle-frame-front.png`
- `output/v04-m2-angle-stock/renders/v04-m2-angle-frame-rear.png`
- `output/v04-m2-angle-stock/renders/v04-m2-right-connector-detail.png`
- `output/v04-m2-angle-stock/renders/v04-m2-right-connector-internal.png`
- `output/v04-m2-angle-stock/renders/v04-m2-shell-integration-rear.png`
- `output/v04-m2-angle-stock/validation/frame-fixed-mount-v04-validation.json`

The `output/` tree is ignored by Git and must be regenerated locally.

## Accepted decisions and dimensions

- Ordered connector stock: 6063-T6 equal angle, nominal `38.1 x 38.1 x
  3.175 mm`, length `914.4 mm`; actual received dimensions, inside radius,
  straightness, and marking remain a receipt gate.
- Four finished 45 mm segments are allocated: two primary angles and two
  outer-cheek source segments. Nominal consumption is 180 mm before kerf,
  leaving at least 734.4 mm before kerf.
- Each primary angle retains the full 38.1 mm upright and has its plate-side
  base trimmed to 29 mm. Each outer cheek is `45 x 25 x 3.175 mm`.
- Three flush M5 x 16 flat-head through-bolts attach each primary-angle base
  to the backplate. Right centers remain `(36,-30)`, `(47.4,-30)`, and
  `(38,-9)` mm in plate-local X/V; left mirrors X. Holes are transfer-drilled
  from the plate into the clamped angle, not measured from the angle edge.
- Each rail and its fitted 14.7 mm nominal solid plug receive the compound
  lower cut together and bear directly on the 3.175 mm angle base. The
  centerline-to-plate-normal angle is `25.8745 deg`.
- Rail centerline finished length is `152.476123 +/-0.25 mm`; shop callout is
  152.5 mm. Rough-cut each rail at 160 mm. The compound finished edges range
  from 147.0677 to 157.8845 mm.
- Lower M5 stations are 14 and 29 mm from the bearing-plane centerline. Upper
  M4 is 133.776123 mm from that datum and 18.7 mm from the square upper end.
- The fitted solid plug extends 45 mm from the bearing centerline and retains
  at least 39.5916 mm physical insertion at the shortest compound edge.
- Each lower M5 is transfer-drilled through the complete matched stack:
  primary angle, fitted metal taper spacer, 2 mm tube wall, solid plug, far
  wall, and outer cheek. Use M5 x 40 through-bolts, metal taper head seats,
  flat washers, and nylocs.
- Two hand-filed aluminum taper pads per rail compensate the measured/modelled
  4.8178 degree roll mismatch between a stock 90-degree angle upright and the
  frozen rail cross-bolt axis. Printed structural shims are prohibited.
- No backplate rail cutout or exterior shell pass-through is added. Service is
  through the open rear aperture.

## Validation performed and results

The shared-interface validator, metal preflight, Blender generator, and focused
automated regressions pass. The generator's plate-local vertical basis was
corrected to `across_plate.cross(rear_normal)`, matching
`cat_head_interface.py`; the reversed M1 generator basis is superseded.

| Check | Result |
| --- | ---: |
| Frozen 21 mm socket, targets, axes, and roll | pass; unchanged |
| Rail centerline derivation | 152.476214 mm calculated vs 152.476123 mm recorded |
| Compound finished edges | 147.067837 to 157.884590 mm calculated |
| Minimum adapter-hole plate ligament | 11.1759 mm |
| Minimum shell-hole plate ligament | 7.0819 mm |
| Minimum angle-base-hole plate ligament | 5.5766 mm |
| Minimum retained angle-base part ligament | 5.96 mm |
| Minimum cut-hole pair ligament | 5.9 mm |
| Sequential tool-to-installed-neighbor gap | 0.4 mm |
| Minimum solid-plug cross-hole end ligament | 5.8416 mm |
| Minimum plug insertion at compound edge | 39.5916 mm |
| Current V6.1 shell/metal modeled intersections | none in recorded nine-part matrix |
| Focused automated tests | 12 passed |

The current V6.1 shell happens to clear the M2 metal envelope digitally. Any
subsequent shell/rear-cassette revision must consume this exact envelope and
rerun A-39; current clearance does not authorize either workstream to alter
the shared interface independently.

## Rejected or unsafe variants

- V0.4-M1 monolithic CNC shoes: superseded because the user has no CNC and
  explicitly selected hand-fabricated ordered angle stock.
- Treating the rail as floating above the plate or clamping it only to a thin
  angle upright: rejected. The compound rail/plug face bears on the angle base
  and then the 3 mm backplate.
- Square-cutting the lower rail: rejected because it cannot make full contact
  with the angled bearing plane.
- Drilling angle holes from arbitrary drawing-edge dimensions: rejected. The
  three base holes and both crossbolt paths are transfer-drilled from matched
  parts.
- Tightening crossbolts through an empty hollow tube: rejected due to tube-wall
  crushing; a fitted solid plug is mandatory.
- Omitting metal roll-compensation pads or substituting printed structural
  shims: rejected because the stock 90-degree angle and frozen rail roll differ
  by about 4.82 degrees.
- Welding, changing X `+/-40` rail targets, moving the upper sockets, changing
  the six-plus-six plate-hole centers, or cutting metal before the receipt and
  coupon gates: rejected for this revision.

## Exact regeneration commands

From the repository root:

```bash
python3 hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/prepare_frame_fixed_mount_v04_interface.py

blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-socket-portals-candidate-v6/gate9-socket-portals-candidate-v6.blend \
  --python hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/generate_frame_fixed_mount_v04.py

python3 -m unittest \
  tests.automated.test_cat_head_shared_interface \
  tests.automated.test_gate9_socket_portals_v6_summary
```

## Next physical and shell-review steps

1. Shell session reads this checkpoint, the shared V0.4 JSON, and the tracked
   summary; it imports the M2 angle/base/upright/cheek/hardware envelope before
   changing the rear cassette, bezel, or six ASA pads.
2. When the angle arrives, measure both leg widths, wall thickness at several
   locations, inside radius, straightness, and any alloy/temper marking. Do not
   cut final parts if the received section differs materially from 38.1 x
   38.1 x 3.175 mm.
3. Measure actual deburred tube ID and corner radii; fit and label each solid
   plug without force.
4. Make one short receipt/fit coupon first. Prove the trimmed angle, flush
   countersink, compound rail/plug bearing, tapered spacer, M5 access, clamp
   behavior, and repeatable disassembly.
5. Only after shell reintegration and the coupon pass, create a shop-reviewed
   final fabrication sequence. No plate is currently ordered or cut.
6. Before riding, validate the real headlight, beam, steering sweep, cables,
   independent metal tether, stationary proof load, vibration, and progressive
   low-speed ride plan.
