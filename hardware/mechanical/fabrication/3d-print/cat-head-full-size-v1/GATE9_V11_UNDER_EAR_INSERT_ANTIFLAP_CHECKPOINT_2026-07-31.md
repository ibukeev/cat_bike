# Gate 9 V11 Under-Ear Insert and Anti-Flap Checkpoint — 2026-07-31

## Scope and status

V11 replaces the failed under-ear insert attachment with printable, discrete,
serviceable retainers and adds a separate outer anti-flap tie. The digital CAD,
closed-manifold, seated-clearance, service-path, complete-aluminum-envelope,
mirror, exterior-skin, visual-review, and real Prusa MK4 ASA/PETG slice gates
pass.

This closes the digital portions of F-07 through F-14 and A-07 through A-11.
A-07 through A-12 still require physical final-material assembly checks. No
claim of physical validation or production G-code authorization is made.

The shared aluminum interface remains unchanged:

- `CAT-HEAD-SHELL-ALUMINUM-V0.5`
- metal handoff `CAT-HEAD-SHELL-ALUMINUM-V0.5-M2`

## Current source, review, and output

- Configuration:
  `config/gate9-under-ear-insert-antiflap-candidate-v11.json`
- Generator:
  `source/generate_gate9_under_ear_insert_antiflap_candidate_v11.py`
- Real-slice audit:
  `source/slice_gate9_under_ear_insert_antiflap_candidate_v11.py`
- Clean review renderer:
  `source/render_gate9_under_ear_insert_antiflap_v11.py`
- Tracked validation:
  `review/gate9-under-ear-insert-antiflap-v11-summary.json`
- Generated review model:
  `output/gate9-under-ear-insert-antiflap-candidate-v11/gate9-under-ear-insert-antiflap-v11.blend`
- Generated production candidates:
  `output/gate9-under-ear-insert-antiflap-candidate-v11/parts/`
- Generated slice report:
  `output/gate9-under-ear-insert-antiflap-candidate-v11/slicer-review/gate9-v11-under-ear-antiflap-slices.json`
- Generated visual review:
  `output/gate9-under-ear-insert-antiflap-candidate-v11/review-renders/`
- Regression test:
  `tests/automated/test_gate9_under_ear_insert_antiflap_v11_summary.py`

The seven generated deliverables are:

- ASA: left/right upper head, left/right ear, and rear bezel.
- PETG: left/right under-ear translucent insert.

The `output/` directory is intentionally ignored by Git. The configuration,
generator, audit, renderer, tracked summary, regression test, and this
checkpoint are the reproducible record.

## Accepted design

The illuminated insert preserves the original three visible planes. It is not
flattened into a generic panel and no continuous perimeter connector remains.

Insert geometry:

- 1.5 mm frosted or milky translucent PETG visible skin.
- 0.8 mm deep-body perimeter clearance.
- 0.6 mm deep-body surface setback.
- 0.15 mm shallow visible-cap perimeter clearance.
- 0.15 mm shallow visible-cap surface setback.
- 0.5 mm shallow non-structural cap thickness.
- 0.6 mm quantified final-shell local relief.
- 0.5 mm final constructed-part clearance.
- 0.4 mm captive-hardware pocket clearance.

Each insert uses two short spatially separated body retainers:

- M2.5 × 10 socket-cap screws.
- First station is a 2.8 mm round hole.
- Second station is a 2.8 × 4.0 mm tolerance slot.
- Insert-side captive M2.5 nyloc pockets and captive 5.0 × 0.5 mm washers.
- Shell/ear-side screw head and washer; only one driver path is required.
- Retainer tabs are 14 mm long × 8 mm deep × 5 mm thick.
- 0.6 mm tab-face clearance.
- First/second station fractions are 0.05 and 0.50.
- The slot root pad has 18 mm additional length.

Measured minimum body-retainer roots exceed their acceptance floors:

- Insert root pad: 14.146 mm³ minimum; 10 mm³ required.
- Insert tab root: 208.871 mm³ minimum; 20 mm³ required.
- Upper-head tab root: 119.165 mm³ minimum; 20 mm³ required.

Each ear also uses one separate outer anti-flap locator:

- M2.5 × 14 socket-cap screw.
- 2.8 mm clearance path.
- Insert-side captive M2.5 nyloc pocket and captive washer.
- Reinforced hidden insert-border lug, 14 × 7 × 6 mm.
- 0.6 mm lug-face clearance.
- Station fraction 0.95 on mirrored outer edges.
- 77.583 mm from the nearest primary M3 center; 60 mm minimum required.
- Explicitly not a primary ear load path.

Measured anti-flap roots exceed their acceptance floors:

- Insert root pad: 22.989 mm³; 10 mm³ required.
- Insert lug root: 256.885 mm³; 20 mm³ required.
- Ear tab root: 29.799 mm³; 20 mm³ required.

The service order is: seat and retain the insert, install the two primary M3
ear screws, install the separate outer M2.5 locator, and remove in reverse.
The right updated geometry and fastener centers are exact X mirrors of the
validated left side. The maximum mirror-center error is 0.0 mm.

## Validation performed

Digital geometry:

- All seven updated parts are one closed manifold each with zero boundary and
  nonmanifold edges.
- All seated insert/ear/head pairs have 0.0 mm³ positive overlap.
- Insert-then-ear service paths at 0, 2.5, 5, 10, 20, 40, and 80 mm are clear.
- All M2.5 drivers, screw heads, washers, nylocs, and nut-tool envelopes clear
  non-owned printed parts.
- Updated printed parts and tool envelopes clear the complete V0.5-M2 aluminum
  plate, angle bases, uprights, rails, plugs, spacers, cheeks, fasteners,
  washers, and access envelopes.
- External X/Y/top skin bounds remain inside the symmetric V10 source bounds.
- The only quantified growth is a hidden 5.1988 mm lower ear-root extension,
  below the 6.0 mm limit.

Real support/brim-inclusive Prusa MK4/MK4S audit:

- All seven parts pass bed, height, and 10 mm post-brim XY-margin gates.
- Minimum post-brim XY margin: 15.589 mm.
- Estimated complete set: 485.66 g.
- Estimated support: 172.981 g / 160.866 cm³.
- Estimated time: 175514 seconds, approximately 48 h 45 min.

Selected orientations:

- Left upper head ASA: `[95, 23, 6]`, 29.657 mm margin.
- Right upper head ASA: `[79, 160, 9]`, 28.555 mm margin.
- Left ear ASA: `[162, 106, 115]`, 57.303 mm margin.
- Right ear ASA: `[172, 75, 126]`, 55.855 mm margin.
- Rear bezel ASA: `[63, 122, 82]`, 15.589 mm margin.
- Left insert PETG: `[119, 38, 78]`, 66.914 mm margin.
- Right insert PETG: `[127, 142, 6]`, 66.315 mm margin.

Automated regression:

```bash
python3 -m unittest \
  tests.automated.test_gate9_under_ear_insert_antiflap_v11_summary
```

The complete Gate 9 summary suite passes 56 tests. The repository-wide suite
runs 77 tests with 76 passing and the pre-existing unrelated lighting-map
fixture error remaining: `KeyError: glow_pairs` in
`test_cat_head_lighting_map.py`.

## Rejected or unsafe variants

- The inherited Gate 7 long/continuous insert retainers were rejected because
  they over-constrained the insert, fought the shell planes, and were not
  reliably rooted.
- Using a tight clearance through the complete insert was rejected. The final
  design separates generous 0.8 mm deep-body clearance from the shallow 0.15 mm
  visible seam.
- Treating the primary M3 ear pair as the anti-flap tie was rejected because it
  did not provide the required spatial separation.
- Loading the 1.5 mm illuminated skin directly was rejected. The anti-flap lug
  is rooted through a local hidden reinforcement pad.
- Exposed two-sided M2.5 nut/driver stacks were rejected because they collided
  with adjacent shell and ear service envelopes. Captive insert-side nylocs
  leave a single accessible driver path.
- Early body stations and the former outer station had weak/asymmetric roots.
  The accepted 0.05/0.50 body stations and 0.95 outer station pass quantified
  root floors on both mirrored sides.
- Independently Booleaning the right side was rejected after inherited source
  asymmetry produced unstable results. Exact mirroring of the validated left
  updated parts is the accepted construction.
- Silent export of a hidden rear bezel produced an 84-byte zero-triangle STL.
  V11 now exports from isolated visible objects and fails closed on any STL of
  84 bytes or less.

## Exact regeneration

From the repository root:

```bash
blender --background \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_under_ear_insert_antiflap_candidate_v11.py \
  -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-under-ear-insert-antiflap-candidate-v11.json

python3 \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_under_ear_insert_antiflap_candidate_v11.py \
  --threads 8

blender --background \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-under-ear-insert-antiflap-candidate-v11/gate9-under-ear-insert-antiflap-v11.blend \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/render_gate9_under_ear_insert_antiflap_v11.py \
  -- \
  --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-under-ear-insert-antiflap-candidate-v11/review-renders

python3 -m unittest \
  tests.automated.test_gate9_under_ear_insert_antiflap_v11_summary
```

## Next physical review

No separate coupon is required by this checkpoint; V11 deliberately uses the
larger clearances accepted after the coupon discussion. The lowest-risk final
material sequence is still staged:

1. Print both small translucent inserts in PETG first and verify that the
   visible planes and vinyl/light treatment are acceptable.
2. Print the left upper head and left ear in black ASA using the selected real
   Prusa orientations, then hand-seat the left insert without screws.
3. Perform A-07 through A-11: hand fit, flush visible planes, no force fitting,
   independent round/slot retention, tightening without lateral slide, and
   anti-flap restraint without loading the illuminated skin.
4. Install the actual M2.5 × 10, M2.5 × 14, washers, nylocs, and primary M3
   hardware and perform the complete A-12 install/removal sequence.
5. If the left final-material assembly passes, print the mirrored right parts
   and rear bezel. If it does not, stop before committing the remaining ASA and
   record the measured interference or looseness against this checkpoint.
