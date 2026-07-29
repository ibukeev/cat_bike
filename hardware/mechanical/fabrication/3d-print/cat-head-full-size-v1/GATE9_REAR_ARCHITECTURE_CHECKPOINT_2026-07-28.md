# Gate 9 Rear Architecture Resumable Checkpoint — 2026-07-28

## Current state

Gate 9 rear-architecture comparison is complete. The selected working
architecture is a full-size rear-loaded cassette using the -70 mm rear-plane
facet threshold and frozen interface revision
`CAT-HEAD-SHELL-ALUMINUM-V0.3`.

This checkpoint is not a production print, aluminum cut, hole, or drilling
release.

## Authoritative tracked review files

- `hardware/mechanical/CAT_HEAD_GATE9_REAR_ARCHITECTURE_DECISION_2026-07-28.md`
- `hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/review/gate9-rear-architecture-summary-v1.json`
- `hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v03.json`
- `hardware/mechanical/CAT_HEAD_MOUNT_AND_SHELL_PHYSICAL_FIT_REVIEW_2026-07-28.md`
- `hardware/mechanical/CAT_HEAD_FINAL_ASA_FIX_CHECKLIST_2026-07-28.md`

## Local generated review outputs

The generated directory is intentionally not a production artifact namespace:

`hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-rear-architecture-comparison-v1/`

Key local files:

- `gate9-rear-architecture-comparison-v1.blend`
- `gate9-rear-architecture-comparison-v1.glb`
- `gate9-rear-architecture-comparison-v1.json`
- `cassette-threshold-topology.json`
- `gate9-cassette-tradeoffs.json`
- `gate9-hybrid-cassette-variant.json`
- `slicer-review/gate9-slicer-comparison.json`
- `slicer-review/gate9-cassette-tradeoff-slices.json`
- `slicer-review/gate9-hybrid-cassette-slices.json`
- `renders/`
- `variants/`

## Accepted decisions and dimensions

- Preserve the 330 mm full-size head.
- Reject global scaling as the architecture fix.
- Use the full-size -70 mm rear cassette as the topology-rebuild baseline.
- Keep V0.3 rail lower targets at X `+/-40 mm` until exact final-envelope
  validation proves a coordinated change is needed.
- Measured rail stock remains 19 x 19 x 2 mm square aluminum tube.
- Selected clean-shell envelopes:
  - left lower: 158.406 x 200.784 x 126.395 mm;
  - right lower: 128.291 x 200.784 x 126.395 mm;
  - left upper: 127.408 x 137.661 x 158.217 mm;
  - right upper: 127.203 x 137.661 x 158.217 mm;
  - rear cassette: 253.878 x 107.550 x 220.280 mm.

## Validation performed

- Generated retained, six uniform-scale, deep-cassette, two shallow-cassette,
  and two hybrid comparison variants.
- Generated meshes are closed with zero boundary and nonmanifold edges.
- Selected raw cassette is one connected component.
- Coarse selected-architecture collision review reports zero unintended
  intersections between the retained body shells and:
  - V0.3 aluminum backplate;
  - both 19 mm rails;
  - 30 x 30 x 40 mm raw shoe envelopes;
  - 24 mm tool envelopes;
  - 14 mm adapter-hardware envelopes.
- PrusaSlicer 2.7.4 MK4/MK4S comparison used:
  - Generic ASA review profile;
  - 0.20 mm layer height;
  - three perimeters;
  - 15% infill;
  - automatic snug supports everywhere;
  - 5 mm brim;
  - required 10 mm XY margin after support and brim.
- Canonical G-code margin parser is V3. It preserves MK4 Custom travel
  coordinates while stripping startup purge extrusion.
- Every selected representative toolpath passes the 10 mm margin rule.
- Selected architecture estimates:
  - 61.84 h;
  - 713.68 g total filament;
  - 405.07 g / 378.56 cm3 support;
  - 12.887 mm minimum representative XY margin.

## Rejected or unsafe variants

- Retained full-size partition: printable in a carefully optimized clean-shell
  orientation, but approximately 92.32 h and 702 g of estimated support.
- Uniform 98% scale: only about 5% improvement and does not resolve metal or
  section-ownership problems.
- -35 mm cassette: worse than retained full size.
- -45 mm cassette: good margin but more total time and support than selected.
- Mirrored stepped hybrid: about 1.3% faster but heavier, more support
  intensive, and adds a right-lower topology island.
- Raw generated body sections remain unsafe for release because upper and
  lower source islands have not yet been rebuilt as single connected bodies.
- Thin flying tabs, exposed reinforcement blocks, append-only overlaps, and
  opposing reinforcement collisions remain explicitly rejected.

## Exact regeneration commands

From repository root:

```bash
blender --background \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_rear_architecture_comparison_v4.py \
  -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-rear-architecture-comparison-v1.json \
  --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-rear-architecture-comparison-v1

blender --background \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/analyze_gate9_cassette_thresholds_blender.py \
  -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-rear-architecture-comparison-v1.json \
  --output hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-rear-architecture-comparison-v1/cassette-threshold-topology.json

python3 -u \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_architecture_comparison_v3.py \
  --threads 8
```

Tradeoff audit commands:

```bash
blender --background \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_cassette_tradeoff_variants.py

python3 -u \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_cassette_tradeoffs.py

blender --background \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_hybrid_cassette_variant_v2.py

python3 -u \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/slice_gate9_hybrid_cassette.py
```

## Next CAD work

1. Rebuild the selected body parts so every output is one connected closed
   manifold body.
2. Replace disconnected upper and eye-adjacent islands with broad inboard
   bridges designed against the complete keep-out set.
3. Design the rear cassette seam flange, alignment, service fastening, seal,
   drainage, wiring, and removal path.
4. Add real 20.5 mm rail sockets and pass-throughs plus metal lower shoes and
   anti-crush load paths.
5. Coordinate the revised front/top portals with the accepted aluminum rail
   axes.
6. Run exact collisions and slice every actual left and right part.

## Next physical review

Do not print a complete ASA head next. First print:

- a 19 mm tube / 20.5 mm socket coupon with M4 cross bolt;
- a rear cassette seam and hidden-flange strip;
- an internal bridge coupon representing the upper-shell reconnection;
- a backplate/pass-through/tool-access coupon using the real tube and proposed
  shoe hardware.

