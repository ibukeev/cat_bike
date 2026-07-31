# Gate 9 V10 Primary Ear Interface Checkpoint — 2026-07-30

## Scope and status

V10 replaces the failed four-path/pin-like primary ear connection with a
complementary two-fastener M3 interface on both ears. The digital geometry and
real Prusa MK4 Generic ASA slice audit pass.

This checkpoint closes only the primary ear-to-upper-head interface work.
Final ASA printing remains held until the separate under-ear translucent insert
and spatially separated outer anti-flap tie are redesigned and validated.

Resolved requirements:

- F-12: primary under-ear flange access and structural weakness.
- F-22: pin-against-pin ear interface.
- A-18: accessible, broad-root primary ear flange.
- A-27: complementary two-path round-and-slot ear interface.

Still open:

- F-13/F-14 and A-11: under-ear translucent insert plus a reinforced M2.5 outer
  anti-flap tie.
- A-12: complete physical installation and removal sequence with the insert and
  anti-flap tie present.

## Current source, review, and output

- Configuration:
  `config/gate9-ear-primary-interface-candidate-v10.json`
- Generator:
  `source/generate_gate9_ear_primary_interface_candidate_v10.py`
- Real-slice audit:
  `source/slice_gate9_ear_primary_interface_candidate_v10.py`
- Tracked validation:
  `review/gate9-ear-primary-interface-v10-summary.json`
- Generated review model:
  `output/gate9-ear-primary-interface-candidate-v10/gate9-ear-primary-interface-v10.blend`
- Generated production candidates:
  `output/gate9-ear-primary-interface-candidate-v10/parts/left_upper_head.stl`
  `right_upper_head.stl`, `left_ear.stl`, and `right_ear.stl`
- Generated real-slice report:
  `output/gate9-ear-primary-interface-candidate-v10/slicer-review/gate9-v10-primary-ear-slices.json`
- Regression test:
  `tests/automated/test_gate9_ear_primary_interface_v10_summary.py`

The `output/` files are local generated artifacts and are intentionally ignored
by Git. The configuration, generator, tracked summary, slicer audit, regression
test, and this checkpoint are the reproducible record.

## Accepted design

The V9 shell body is the source. The original Gate 8 ear meshes are re-imported
and receive complementary internal relief.

Each side has exactly two M3 paths:

- First/lower station: 3.4 mm round clearance.
- Second/upper station: 3.4 × 5.0 mm capsule slot.
- M3 × 20 socket-cap screws.
- 7.0 mm OD × 0.5 mm washers.
- M3 nyloc nuts modeled at 5.5 mm across flats and 4.0 mm high.
- 9.0 mm driver and 10.0 mm nut-tool envelopes, each 45.0 mm long.

The accepted saddle construction is:

- The shallow legacy four-bore saddle is encapsulated inside a larger solid
  V10 saddle.
- The two middle legacy bores are filled.
- Only the outer round and slot stations are recut.
- Flange face clearance: 0.50 mm.
- Tab thickness: 5.0 mm.
- Tab depth: 12.0 mm.
- Shell overlap: 2.6 mm.
- Minimum tab exterior recess: 5.0 mm.
- Root web: 8.0 mm long × 4.5 mm thick, with 0.75 mm end margin and
  2.0 mm Boolean overlap.
- Complementary ear relief clearance: 0.50 mm.

Measured root intersections are:

- Left upper head: 494.991 mm³.
- Left ear: 1418.019 mm³.
- Right upper head: 502.325 mm³.
- Right ear: 1372.436 mm³.

All exceed the 35 mm³ acceptance floor. The minimum modeled root-web exterior
recess is 0.369 mm; the minimum complete tab exterior recess is 5.019 mm.

The full head-side interface shifted outward by the 0.50 mm joint clearance is
subtracted from each ear. Small residual overlap components are then relieved
locally with 0.10 mm hull clearances. The final seated positive overlap is
0.0 mm³ on both sides.

The complete aluminum interface remains locked to:

- `CAT-HEAD-SHELL-ALUMINUM-V0.5`
- metal handoff `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2`

No aluminum-owned CAD, rail axis, socket, or shared datum changed.

## Validation performed

Geometry validation:

- All four updated parts are one closed manifold with zero boundary and
  nonmanifold edges.
- Both seated ear/head pairs have 0.0 mm³ positive overlap.
- Ear removal offsets 0, 2.5, 5, 10, 20, 40, and 80 mm are collision-free.
- All M3 screw, driver, washer/nut, and nut-tool envelopes clear non-owned
  printed parts.
- Updated printed parts and tools clear the complete V0.5-M2 aluminum model.
- Exterior bounds stay inside their source extents.
- Mirrored fastener-center maximum error is 0.0035 mm.

Real Prusa MK4 Generic ASA slice audit:

- Four of four parts pass support/brim-inclusive bed and height validation.
- Minimum post-brim XY margin: 28.484 mm.
- Estimated complete set: 340.09 g.
- Estimated support: 140.561 g / 131.369 cm³.
- Estimated time: 125857 seconds, approximately 34 h 57 min.

Selected orientations:

- Left upper head: `[95, 23, 6]`, 29.657 mm margin.
- Right upper head: `[75, 160, 9]`, 28.484 mm margin.
- Left ear: `[17, 80, 51]`, 55.492 mm margin.
- Right ear: `[17, 100, 51]`, 57.260 mm margin.

Automated regression:

```bash
python3 -m unittest \
  tests.automated.test_gate9_ear_primary_interface_v10_summary
```

## Rejected or unsafe variants

- Directly subtracting the old four-bore saddle produced detached components
  and unstable Boolean results.
- A deeper 8 mm enlarged saddle did not overlap the owning shell reliably and
  could become a floating connector.
- A 6 mm root thickness spanning the joint caused substantial mutual ear/head
  interference; narrowing it still left unacceptable overlap.
- A clipped/deep-only complementary relief missed the shallow root conflict.
- Treating the primary M3 pair as the outer anti-flap restraint was rejected:
  that would falsely close F-13/F-14/A-11 and would not provide the required
  spatially separated restraint.

The accepted approach is encapsulate, fill, and recut the saddle, then subtract
the complete shifted complementary interface and remove only quantified local
residuals.

## Exact regeneration

From the repository root:

```bash
blender --background \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_ear_primary_interface_candidate_v10.py \
  -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-ear-primary-interface-candidate-v10.json

python3 \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_ear_primary_interface_candidate_v10.py \
  --threads 8

python3 -m unittest \
  tests.automated.test_gate9_ear_primary_interface_v10_summary
```

## Next physical and CAD review

1. Do not start the full V10 ear/upper-head ASA print yet.
2. Print and test the already generated V9 M3 insert/bridge coupon.
3. If the actual M3 × 20 washer and nyloc stack differs, print a small local
   round/slot interface coupon before the complete ears.
4. Build V11 around the under-ear translucent insert:
   preserve its light aperture, add printable clearance and discrete rooted
   connectors, and add the spatially separated reinforced M2.5 anti-flap tie.
5. Rerun the complete seated, fastened, tool-access, removal, mirror-landing,
   aluminum-envelope, topology, and real Prusa ASA validation before authorizing
   the final print.
