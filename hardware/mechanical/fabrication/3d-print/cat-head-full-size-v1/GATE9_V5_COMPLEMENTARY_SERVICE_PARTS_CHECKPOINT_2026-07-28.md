# Gate 9 V5 Complementary Service Parts Checkpoint — 2026-07-28

## Scope and release state

V5 closes the narrow service-part gate that V4 failed: the bottom keel and rear
service part are rebuilt as complementary boundary meshes. This is a digitally
validated review candidate, not authority to print the complete ASA head.

Status:
`review_candidate_passed_service_parts_not_production_release`.

The authoritative aluminum datum remains
`CAT-HEAD-SHELL-ALUMINUM-V0.3`. The full head remains 330 mm wide and the lower
rails remain at X = -40/+40 mm.

## Current review and output files

- Config:
  `config/gate9-complementary-service-parts-candidate-v5.json`
- Generator:
  `source/generate_gate9_complementary_service_parts_candidate_v5.py`
- Slicer driver:
  `source/slice_gate9_complementary_service_parts_candidate_v5.py`
- Tracked result:
  `review/gate9-complementary-service-parts-v5-summary.json`
- Automated regression:
  `tests/automated/test_gate9_complementary_service_parts_v5_summary.py`
- Generated Blender review:
  `output/gate9-complementary-service-parts-candidate-v5/gate9-complementary-service-parts-candidate-v5.blend`
- Generated geometry report:
  `output/gate9-complementary-service-parts-candidate-v5/gate9-complementary-service-parts-candidate-v5.json`
- Generated STLs:
  `output/gate9-complementary-service-parts-candidate-v5/shells/`
- Generated renders:
  `output/gate9-complementary-service-parts-candidate-v5/renders/`
- Generated slice report:
  `output/gate9-complementary-service-parts-candidate-v5/slicer-review/gate9-complementary-service-parts-v5-slices.json`

The generated `output/` tree is intentionally ignored; regenerate it from the
tracked config and source.

## Accepted construction and dimensions

### Bottom keel

- Built directly from two source-aligned exterior facets before solidification.
- No complete legacy shell-solid subtraction.
- Wall thickness: 1.8 mm.
- Exterior outset: 3.0 mm.
- Lower-shell side clearance: 2.5 mm.
- Rear-bezel clearance: 0.9 mm.
- Two forward open-boundary scuppers: 5.0 x 16.0 mm, 80.0 mm2 analytic area
  each; required minimum is 60.0 mm2 each.

### Rear bezel

- Rebuilt from the legacy outer source facets as a new open surface before
  solidification; it is not the legacy cassette with metal solids carved out.
- Wall thickness: 1.8 mm.
- Body seam inset: 3.0 mm.
- Frozen V0.3 metal aperture expansion: 14.0 mm horizontal and 10.0 mm
  vertical.
- Aperture normal offset: -8.0 mm.

### Service details retained from V4

- Eight M3 datum/slot fasteners with continuous shell-owned service spines.
- Provisional hardware: M3x8 button-head stainless screws into short brass
  heat-set inserts, 4.6 mm pocket diameter x 4.2 mm depth.
- Fasteners locate and seal the shell only; the aluminum mount carries the
  primary bike load.
- Two embedded cylindrical 3.0 mm wire ribs.
- 13.0 mm clear wire channel and 20.0 mm split rear exit.
- Removal order: keel downward first, rear bezel rearward second.

## Validation performed and results

Digital geometry gate:

- All six modified printed parts are one closed manifold component.
- Every part has zero boundary and zero nonmanifold edges.
- The keel and bezel are direct boundary constructions.
- Every checked seated printed-part triangle overlap count is zero.
- Minimum sampled seated clearance is 0.834 mm; required minimum is 0.6 mm.
- Rear bezel to frozen metal minimums include 8.7543 mm to the backplate,
  16.441 mm to either rail, 10.9475 mm to either shoe envelope, and
  14.0202 mm to either shoe-tool envelope.
- The sampled keel-downward offsets 0/5/15/30 mm are clear.
- The sampled bezel-rearward offsets 0/10/25/50/80 mm are clear after keel
  removal.
- Both scuppers meet the analytic opening requirement.
- Wire ribs, channel, and rear exit meet the retained envelope.

Prusa MK4/MK4S 0.4 mm Generic ASA architecture slice:

- Eight of eight parts have a margin-passing orientation.
- Required post-brim/support XY margin: 10.0 mm.
- Minimum measured margin: 15.011 mm at the rear bezel.
- Estimated filament: 706.95 g.
- Estimated support filament: 363.126 g.
- Estimated support volume: 339.361 cm3.
- Estimated aggregate print time: 236,838 s (about 65 h 47 m).

These slicer figures prove envelope feasibility only. They are not recommended
production settings and do not authorize a full ASA print.

## Rejected or unsafe variants

- V4 carved complete legacy solids and failed: keel/lower-shell and
  cassette/frozen-metal intersections remained.
- The initial V5 lower-shell side clearance of 1.5 mm did not provide the
  explicit 0.6 mm sampled minimum everywhere; 2.5 mm is retained.
- The initial V5 bezel body inset of 2.5 mm was increased to 3.0 mm to meet
  the explicit sampled-clearance gate.
- Positive aperture-normal displacement crossed toward the rear-mounted
  aluminum plate; -8.0 mm is the retained direction.
- Barely piercing cylindrical drain bores are rejected; the two edge
  scuppers are required.
- The legacy rear cassette and V4 keel remain rejected for physical printing.

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
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_complementary_service_parts_candidate_v5.py \
  -- --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-complementary-service-parts-candidate-v5.json
```

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_complementary_service_parts_candidate_v5.py \
  -- --threads 8
```

```bash
python3 -m unittest tests.automated.test_gate9_complementary_service_parts_v5_summary
```

The first command regenerates the ignored comparison Blender file and source
ear STLs. The V5 generator deliberately starts from that comparison file
because the V3/V4 source derivation imports frozen comparison collections from
it.

## Remaining production blockers and next physical-review steps

Do not order or print the final complete ASA set yet. Resolve these in order:

1. Integrate the real 20.5 mm rail sockets and revise front/top portals to the
   frozen aluminum angles; rerun all static and tool/hardware sweeps.
2. Integrate the accepted two-bolt ear interface and print a left-side ear
   joint coupon.
3. Replace the disconnected eye-frame geometry with a connected printable eye
   module and print an eye-frame coupon.
4. Integrate wrapped glow-panel adhesive lands and print one representative
   panel/land coupon using the ordered vinyl and 3M 300LSE.
5. Finish remaining shell seams, bolt/tool access, and assembly order; print a
   representative seam coupon.
6. Assemble the coupons against the actual aluminum hardware and measure fit,
   insertion, service removal, seal compression, and heat-set-insert behavior.
7. Only after those checks pass, regenerate and slice the complete ASA release
   set and authorize the full print.
