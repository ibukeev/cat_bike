# V9 M3 insert and bridge coupon checkpoint — 2026-07-30

## Outcome

A compact two-part ASA coupon is ready for the one physical calibration that
cannot be inferred reliably from CAD: selecting the pilot diameter for the
actual nominal 4.6 x 5.7 mm M3 heat-set inserts in the user's printer/material
combination.

This does not release the V9 shells for production printing. It prevents ten
full-shell insert stations, and the forthcoming ear fasteners, from being
committed to an untested pilot.

## Current review and output

- Configuration:
  `config/v9-m3-insert-bridge-coupon.json`
- Generator:
  `source/generate_v9_m3_insert_bridge_coupon.py`
- Real Prusa slicer audit:
  `source/slice_v9_m3_insert_bridge_coupon.py`
- Machine-readable review:
  `review/v9-m3-insert-bridge-coupon-summary.json`
- Local Blender review model:
  `output/v9-m3-insert-bridge-coupon/v9-m3-insert-bridge-coupon.blend`
- Printable local STLs:
  - `output/v9-m3-insert-bridge-coupon/parts/v9_m3_insert_coupon_base.stl`
  - `output/v9-m3-insert-bridge-coupon/parts/v9_m3_insert_coupon_bridge.stl`
- Local real-slice report:
  `output/v9-m3-insert-bridge-coupon/slicer-review/v9-m3-insert-bridge-coupon-slices.json`

The `output/` products are generated and intentionally ignored by Git. They can
be recreated exactly with the commands below.

## Accepted design and dimensions

- One 58 x 20 x 1.8 mm base carries three V9-style bosses.
- Every boss is 12 mm diameter, 12 mm total depth, and overlaps the base skin by
  1.3 mm.
- Blind pilots are 5.8 mm deep.
- Pilot order is **left 4.0 mm, center 4.1 mm, right 4.2 mm**.
- The separate bridge has 18 mm hole spacing, 8 mm diameter ends, a 6.5 mm
  spine, 3.5 mm thickness, and 3.6 mm M3 clearances.
- M3 x 8 screws leave 4.5 mm of nominal threaded engagement through the bridge,
  below the 5.7 mm nominal insert length.
- The coupon intentionally matches the V9 shell pad, bridge end, pilot depth,
  clearance, screw, and 1.8 mm skin dimensions.

## Validation performed

- Both STL parts are one closed manifold component with zero boundary and
  non-manifold edges.
- All three blind pilots are open with zero measured residual volume.
- Each boss has 147.027 mm3 analytic root overlap.
- Minimum boss radial sidewall is 3.9 mm.
- Minimum bridge radial bearing width is 2.2 mm.
- Real Original Prusa MK4/MK4S Generic ASA slices pass for both parts in the
  prescribed flat orientation.
- Exact two-part slice estimate:
  - 5.300 g ASA total
  - 0 g / 0 cm3 generated support
  - 1,782 seconds (29 minutes 42 seconds)
  - 90.858 mm minimum brim-inclusive XY margin

## Rejected or unsafe variants

- Do not choose 4.1 mm only because it is the current CAD value. ASA shrinkage,
  actual insert knurl diameter, extrusion width, and printer calibration can
  move the correct pilot.
- Do not test only a loose hole in a thin plate. This coupon duplicates the
  production boss depth, root, sidewall, bridge bearing, and M3 x 8 stack.
- Do not use the coupon result to release the entire head. Ear, eye, glow,
  lamp/steering portal, full assembly, wiring, drainage, vibration, and service
  checks remain.

## Exact regeneration

From the repository root:

```bash
blender --background \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_v9_m3_insert_bridge_coupon.py \
  -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/v9-m3-insert-bridge-coupon.json

python3 \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_v9_m3_insert_bridge_coupon.py \
  --threads 8

python3 -m unittest \
  tests.automated.test_v9_m3_insert_bridge_coupon_summary
```

## Next physical review

1. Print both STLs flat in the actual black ASA and final print profile.
2. Before removing the base from the sheet, mark the underside left/center/right
   as 4.0/4.1/4.2.
3. Heat-set one actual insert in each station until flush.
4. Reject a station if it splits, bulges badly, spins, tilts, or will not seat.
5. Move the bridge between the left/center and center/right pairs and clamp with
   two M3 x 8 socket-cap screws. Confirm free screw start, firm clamp, no
   bottoming, and clean removal/reinstallation.
6. Select the smallest pilot that installs reliably without damage.
7. Record the winner here. If it is not 4.1 mm, update and regenerate V9 before
   any body or ear production print.

The CAD work can continue on the ear geometry while this coupon is waiting for
physical testing, but final insert-bearing ear and shell release remains held.
