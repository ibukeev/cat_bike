# Gate 9 V9 Body-Seam Retention Checkpoint — 2026-07-30

## Current state

V9 resolves the final body-shell seam-retention blocker digitally without
reintroducing the opposing-tab and reinforcement collisions observed in the
full-size PLA model.

The four body shells now seat first through the accepted V8 assembly paths.
Five separate arched bridge plates are then installed from the open interior.
No integrated pad, boss, pin, tab, or flange crosses a body seam during shell
assembly.

This is not final ASA print authorization. The heat-set-insert coupon, physical
shell fit, and the remaining ear, eye, glow, lamp, and steering systems remain
blocking.

## Current review and output files

Tracked inputs and generators:

- `config/gate9-body-seam-retention-candidate-v9.json`
- `source/generate_gate9_body_seam_retention_candidate_v9.py`
- `source/slice_gate9_body_seam_retention_candidate_v9.py`
- `review/gate9-body-seam-retention-v9-summary.json`
- `../../../../../tests/automated/test_gate9_body_seam_retention_v9_summary.py`

Generated local review output:

- `output/gate9-body-seam-retention-candidate-v9/gate9-body-seam-retention-candidate-v9.blend`
- `output/gate9-body-seam-retention-candidate-v9/parts/`
- `output/gate9-body-seam-retention-candidate-v9/slicer-review/gate9-v9-body-retention-slices.json`

The output namespace contains thirteen production STLs:

- four body shells;
- rear bezel;
- bottom keel;
- two socket caps;
- five separately named removable body-seam bridges.

## Accepted architecture and dimensions

Retention architecture:

1. seat left upper to left lower;
2. seat right upper to right lower;
3. join the right body module to the left body module;
4. install five bridge plates from the open interior;
5. attach later service parts only after the main shell is retained.

Selected bridge sites:

- `left_lower_face__left_upper_head_02`;
- `right_lower_face__right_upper_head_02`;
- `left_upper_head__right_upper_head_02`;
- `left_upper_head__right_upper_head_03`;
- `left_lower_face__right_lower_face_05`.

Per bridge:

- two M3 x 8 socket-cap screws;
- two nominal 4.6 x 5.7 mm M3 heat-set inserts;
- one 4.1 x 5.8 mm blind pilot per shell pad;
- one 3.6 mm clearance hole per bridge end.

Totals:

- five removable bridges;
- ten M3 screws;
- ten M3 heat-set inserts.

Integrated shell pads:

- 12.0 mm diameter;
- 12.0 mm deep;
- 4.0 mm seam setback;
- 1.3 mm overlap into the 1.8 mm source wall;
- 0.5 mm analytic minimum recess behind the approved exterior face;
- minimum measured root intersection 134.547 mm3;
- all ten insert-bearing support ratios 1.0.

Bridge geometry:

- 8.0 mm diameter end bearings;
- 3.5 mm end thickness;
- 6.5 mm arched spine and legs;
- 1.5 mm inward spine arch;
- 0.25 mm modeled contact-face clearance;
- all ten bridge-bearing support ratios 1.0.

Tool envelope:

- 8.0 mm diameter;
- 55.0 mm straight engagement length.

## Validation performed and results

All digital geometry flags pass:

- V0.5-M2 interface revision and aluminum datums unchanged;
- five bridges and ten M3 stations generated;
- all selected pads have broad roots in the final V8 shells;
- all blind insert pilots are open;
- all insert and bridge bearings are fully supported;
- all thirteen STLs contain exactly one closed manifold component;
- every final seated production-part pair has zero positive overlap;
- left and right upper/lower assembly paths pass;
- complete left/right body-module assembly path passes;
- rear-bezel and bottom-keel service paths remain clear;
- all five bridges pass their straight inward seating paths;
- all ten driver envelopes clear every non-owned printed part;
- V9 introduces no new collision with the complete V0.5-M2 aluminum model;
- all five bridges and all ten driver envelopes clear the complete aluminum
  model;
- all wrapped-panel landing polygons remain untouched;
- all V9 body bounds remain inside V8 bounds.

The lower-center bridge required the only local internal relief:

- left lower pre-relief overlap: 7.083153 mm3;
- right lower pre-relief overlap: 6.964024 mm3;
- configured local clearance: 0.35 mm;
- final overlap: 0.0 mm3 on both sides;
- both relieved shells remain one closed manifold component;
- neither relief cutter intersects a wrapped-panel landing.

Real PrusaSlicer validation used the Original Prusa MK4/MK4S, 0.4 mm nozzle,
Generic ASA review profile, supports, and brim:

- all thirteen parts pass;
- minimum post-brim XY margin: 11.61 mm;
- limiting part: `left_lower_face`;
- selected left-lower rotation: `(111, 30, 30)` degrees;
- exact estimated filament: 734.770 g;
- exact estimated support filament: 304.728 g;
- exact estimated support volume: 284.794 cm3;
- exact estimated print time: 266,202 seconds, about 73.9 hours.

Compared with V8:

- total filament increases by 25.080 g;
- support filament increases by 14.000 g;
- estimated time increases by 15,678 seconds, about 4.36 hours;
- the five bridge STLs themselves total about 5.55 g;
- minimum build-plate margin improves from 11.492 to 11.61 mm.

Automated regression:

- focused V9 suite: 9/9 pass;
- repository-wide suite: 56 pass and one pre-existing unrelated error;
- unchanged unrelated error:
  `test_cat_head_lighting_map.CatHeadLightingMapTest.test_gate1_panel_ids_and_pair_order_match`
  raises `KeyError: 'glow_pairs'`.

## Rejected or unsafe variants

- Reusing the old Gate 5/Gate 8 opposing rectangular tabs. Those tabs no
  longer exist in the clean Gate 9 body source and physically caused the
  pin/tab/reinforcement collisions documented in F-27.
- Treating the historical 28 bore axes as surviving structural lands. The V8
  audit found open space at most axes but no supporting plastic.
- Adding pads at all fourteen historical source modules. Nine sites have no
  broad root on both final V8 bodies because Gate 9 moved those regions to
  glow openings, rear service architecture, or the bottom-keel partition.
- A single convex-hull bridge between shallow angled end pads. It intersected
  the inward V-shaped shell corners.
- A straight dogbone spine through the end-pad midplanes. Its spine radius
  intruded into the shell pads.
- Reducing bridge ends below 8 mm merely to remove the lower-center corner
  interference. The accepted design preserves useful M3 head bearing area and
  applies a small, allowlisted internal clearance pocket instead.
- Any bridge installed before the four body shells reach their final seated
  state.
- Printing final body shells before proving the actual heat-set insert in ASA.

## Exact regeneration commands

From repository root:

```bash
blender --background \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_body_seam_retention_candidate_v9.py

python3 \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_body_seam_retention_candidate_v9.py \
  --threads 8

python3 -m unittest \
  tests.automated.test_gate9_body_seam_retention_v9_summary
```

## Next physical-review steps

1. Obtain the actual nominal 4.6 x 5.7 mm M3 heat-set inserts and M3 x 8
   socket-cap screws.
2. Print one small ASA coupon containing:
   - a 12 mm diameter, 12 mm deep body pad;
   - a 4.1 x 5.8 mm blind insert pilot;
   - one 8 mm bridge end with a 3.6 mm clearance hole.
3. Heat-set the insert and verify:
   - the insert seats flush without splitting or bulging the pad;
   - the M3 x 8 screw reaches useful thread engagement without bottoming;
   - the bridge end clamps without crushing;
   - the screw can be installed and removed repeatedly;
   - the insert does not spin or pull out under firm hand torque.
4. After the coupon passes, continue CAD integration of the ears, eyes, glow
   modules, lamp portal, and steering portal against V9.
5. Do not print a complete black ASA body shell until those systems and the
   final complete-system collision/service validation pass.
