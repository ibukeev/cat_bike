# Gate 9 Aperture-Frame and Bottom-Keel Checkpoint — 2026-07-28

## Current state

Two review-only topology corrections were generated after the pre-export
source audit:

1. recessed internal edge ribs and vertex hubs around the glow-facet gaps;
2. a separate bottom-keel partition carrying the point-connected MANQ008
   bottom-center facets and the two synthetic closure triangles.

Neither candidate is a production-print release.

## Current review/output files

Tracked source and configuration:

- `config/gate9-aperture-frame-candidate-v1.json`
- `config/gate9-aperture-frame-candidate-v2.json`
- `config/gate9-bottom-keel-partition-candidate.json`
- `source/generate_gate9_aperture_frame_candidate_v1.py`
- `source/generate_gate9_bottom_keel_partition_candidate.py`

Local generated review output:

- `output/gate9-aperture-frame-candidate-v2/`
- `output/gate9-bottom-keel-partition-candidate/`

The earlier Exact-solver run in
`output/gate9-aperture-frame-candidate-v1/` is a failed diagnostic artifact.

## Accepted decisions and dimensions

- Keep the 330 mm full-size exterior and `-70 mm` rear cassette.
- Keep interface revision `CAT-HEAD-SHELL-ALUMINUM-V0.3` and the X `+/-40 mm`
  lower rail targets.
- Use recessed, edge-parallel internal ribs as the working connection concept
  around glow openings. Do not use the rejected nearest-vertex flying
  cylinders.
- Treat a separate bottom keel as the leading lower-shell ownership candidate,
  subject to seam, service, slicer, and full-assembly validation.
- Bottom-keel clean-shell envelope:
  `181.069 x 149.018 x 49.585 mm`.
- Bottom-keel clean-shell volume:
  `23595.147 mm3`.

## Aperture-frame validation performed

Candidate V2 uses:

- edge-rib radius `4.5 mm` (`9 mm` diameter);
- vertex-hub radius `5.5 mm`;
- analytic minimum recess `0.3 mm` behind each source exterior plane;
- Blender Manifold boolean solver.

Results:

| Part | Components before | Components after | Exterior recess | Metal-envelope collisions | Cassette intersections |
| --- | ---: | ---: | ---: | ---: | ---: |
| Left upper | 2 | 1 | 0.3 mm | 0 | 1 |
| Right upper | 2 | 1 | 0.3 mm | 0 | 1 |
| Left lower | 2 | 2 | 0.3 mm | 0 | 3 |
| Right lower | 2 | 1 | 0.3 mm | 0 | 3 |

The upper-shell concept therefore proves it can create one true closed body.
The one upper collision on each side is the rear endpoint of the second
aperture rib:

- left edge vertices `41-47`;
- right edge vertices `14-23`.

Those ribs must stop short of the cassette seam while preserving adequate
overlap with the upper side component.

The lower V2 result is rejected as a final architecture. Its closure-edge ribs
cross the cassette ownership boundary, and the mirrored left/right boolean
result is not deterministic. The lower closure should not be forced back into
each lower shell.

The Exact-solver V1 run is also rejected. It left three boundary/nonmanifold
edges during the first left-lower union. Manifold-solver results are the only
usable candidate results.

## Bottom-keel validation performed

The bottom-keel candidate owns:

- source face `109`, panel `MANQ008_RIGHT`;
- source face `110`, panel `MANQ008_LEFT`;
- closure triangle `4, 26, 28`;
- closure triangle `32, 50, 52`.

Results:

- bottom keel: one closed manifold connected component;
- lower shells after keel extraction: two components each, exactly the
  remaining glow-aperture split that the recessed frame is intended to join;
- bottom keel clears the frozen aluminum backplate, rails, lower-shoe
  envelopes, tool envelopes, and adapter-hardware envelopes;
- bottom keel contacts the rear cassette, so a complementary keel/cassette seam
  remains required;
- the clean keel envelope fits comfortably within the raw MK4/MK4S build
  volume, but an actual support/brim-inclusive slice has not yet been run.

## Rejected or unsafe variants

- Aperture-frame V1 with Exact booleans.
- Aperture-frame V2 as a full lower-shell repair.
- Any lower architecture that retains the MANQ008 facets and synthetic closure
  triangles through point contact or arbitrary append-only overlap.
- Treating the current keel/cassette overlap as an approved seam.
- Printing any generated body-shell STL from these review namespaces.

## Next coordinated CAD work

Generate V3 as one combined partition:

1. rebuild each lower shell without faces `109/110` and without the synthetic
   closure triangles;
2. apply only the two recessed glow-aperture edge ribs and their shared hub to
   each lower shell;
3. retain the one-piece bottom keel as its own removable underside part;
4. shorten the second upper aperture rib at cassette-side vertices `47/23`;
5. design one complementary bottom-keel/rear-cassette seam owner, alignment
   datum, hidden flange, service fasteners, drainage break, and wire route;
6. require one closed manifold component for all five affected pieces;
7. run exact collision checks against cassette, all metal envelopes, the glow
   panel/skirt insertion volumes, and the eye assembly;
8. slice every actual left/right part, keel, and cassette with the V3
   post-brim margin parser.

## Exact regeneration commands

From repository root:

```bash
blender --background \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-rear-architecture-comparison-v1/gate9-rear-architecture-comparison-v1.blend \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_aperture_frame_candidate_v1.py \
  -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-aperture-frame-candidate-v2.json

blender --background \
  --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate9_bottom_keel_partition_candidate.py \
  -- \
  --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/gate9-bottom-keel-partition-candidate.json \
  --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/gate9-bottom-keel-partition-candidate
```

## Next physical-review steps

Do not print a complete shell. After the combined V3 digital checks pass,
generate:

1. one upper glow-edge frame coupon with the shortened cassette-side end;
2. one lower glow-edge frame coupon;
3. one bottom-keel/lower-shell/cassette seam strip;
4. the 19 mm rail / 20.5 mm socket / M4 cross-bolt coupon already required by
   the rear-interface checkpoint.
