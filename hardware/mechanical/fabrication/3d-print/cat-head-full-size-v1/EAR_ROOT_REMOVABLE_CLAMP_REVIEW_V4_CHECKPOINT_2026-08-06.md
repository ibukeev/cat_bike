# Ear-Root Removable-Clamp Review V4 Checkpoint — 2026-08-06

## Status

V4 is the single current cat-head review. It addresses only physical-fit
feedback F-10/F-11/F-12: retain the already accepted under-ear fit body,
provide repeatable seating, and make retention strong and serviceable without
reintroducing the previous interference.

The accepted yellow V3 fit bodies and exact Gate 8 ears/upper-head shells are
unchanged. F-13/F-14 outer-ear anti-flap work remains a later independent
bucket. No STL, G-code, slicer project, ASA output, or print release exists.

## Open this file

- Blender: `output/00-current-review/ear-root-removable-clamp-review-v4.blend`
- Validation: `output/00-current-review/ear-root-removable-clamp-review-v4-validation.json`
- Renders: `output/00-current-review/renders/`
- Accepted V3 fit baseline:
  `output/60-ear-root-reviews/ear-root-insertion-fit-review-v3/`
- Rejected old transform-local path proof:
  `output/60-ear-root-reviews/ear-root-insertion-fit-review-v3-rejected-local-bvh-path/`

## Accepted decisions and dimensions

- Preserve the accepted V3 yellow fit body exactly: `13/9 mm` visible saddle
  relief, `2.5 mm` deep-body clearance, `1.0 mm` shallow-cap clearance, and
  `0.4 mm` exact-ear clearance.
- Use three short, separated retention points per side. The minimum pairwise
  spacing is `49.4267 mm`.
- Orange moving flange at each point: `20 mm` tangent length, radial range
  `1.5..12 mm`, outer depth `1.7 mm`, and `4 mm` thickness. It is broadly
  unioned to the yellow body and has no fastener hole.
- Green fixed owner-shell anchor at each point: `24 mm` tangent length, radial
  range `-14..-4 mm`, and depth `1..10 mm`. Each anchor follows the actual
  neighboring gray upper-head facet frame, not the yellow insert facet frame.
- Blue removable clamp: `20 mm` tangent length and `3.5 mm` pad thickness.
  It is a manifold wedge bridging the two different facet planes.
- Each clamp has `120 mm²` fixed-anchor bearing area at zero gap and
  `130 mm²` moving-flange bearing area across a `0.3 mm` compressible pad.
- Proposed hardware is one interior-access M3 button-head screw, `7 mm`
  washer, and M3 heat-set insert per point. The clearance hole is `3.4 mm`;
  proposed insert cavity is `4.6 mm` diameter by `4.5 mm` deep.
- The accepted V3 shallow cap and exterior planes remain the broad seating
  datum. No fixed ledge enters the moving envelope.
- Service order: remove ear, all three blue clamps, and screws; remove the
  insert `60 mm` at 45 degrees outward and 45 degrees upward. Installation is
  the exact reverse.

## Validation performed and results

- Exact Gate 8 source mesh count: `31`; source fingerprints unchanged.
- Both yellow-plus-orange moving composites are one connected manifold with
  zero boundary and non-manifold edges.
- All six orange flanges have broad positive body overlap.
- All six green anchors have positive owner-shell root overlap and no contact
  with unintended structural shells.
- Fixed-anchor integration into source shells is not validated. Direct
  cavity-bearing and solid-first trial unions both damaged right-shell topology
  and are rejected from this review.
- Assembled blue clamps have zero unintended intersection with the exact
  structural shells, moving composites, or other fixed anchors.
- M3 tool corridors (`12 mm` diameter by `30 mm`) and finger envelopes
  (`18 mm` diameter by `14 mm`) have zero obstruction with the ear removed.
- Left and right service paths each pass `41` samples: zero actual moving-part
  intersections, zero `0.4 mm` deep-body-margin intersections, and zero
  `0.4 mm` orange-retention-margin intersections.
- Exterior renders show no green fixed anchors or blue removable clamps.
- Shared metal interface remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`.
- No eye, lower-face, rear-cassette, reinforcement, C006, or aluminum geometry
  changed.

Physical tests A-08/A-09/A-10/A-12/A-18 remain pending. Digital checks cannot
prove ASA tolerance, heat-set pull-out strength, vibration life, or hand-tool
access on the printed assembly.

## Review colors and collections

- Orange: moving flanges attached to the accepted insert.
- Green: proposed fixed upper-head anchors.
- Blue: removable wedge clamps; remove before insert motion.
- Brass/gold: proposed M3 hardware.
- Yellow: accepted V3 bodies, hidden in the default isolated retention view.
- Gray and cyan: exact upper heads and ears, hidden in the default isolated
  retention view.
- White: tool/finger envelopes, hidden by default.

## Visual review steps

1. Open the V4 Blender file. The default view isolates all six retention joints
   so the colored parts cannot hide behind the shells.
2. Inspect each side's three orange–blue–green joints. Confirm the blue wedge
   bears on both pads and is not an exterior horn, stick, or block.
3. Toggle `EAR4_ACCEPTED_V3_BODIES_YELLOW__UNCHANGED` for insert context.
4. Toggle `EAR4_EXACT_UPPER_HEADS_GRAY__UNCHANGED` and
   `EAR4_EXACT_EARS_CYAN__UNCHANGED` only when checking placement in the head.
5. Review the left/right `retention-isolated`, `insertion-ready`,
   `tool-access-isolated`, and `exterior-clean` renders.
6. In both exterior-clean renders, confirm no green or blue retention geometry
   is visible.

## Rejected or unsafe variants

- Reject the flat same-plane blue clamp: it intersected the existing upper-head
  interior geometry.
- Reject extruding green anchors along the yellow insert normal: the neighboring
  gray facets use different normals, causing ugly exterior rectangular blocks.
- Reject adding a fixed datum ledge inside the moving envelope.
- Reject applying the orange `0.4 mm` margin by expanding the entire yellow
  body; V3 already validates its deep body separately.
- Reject the old 25-degree rotate plus 30 mm inward path. Its apparent pass used
  a transform-local BVH check; corrected world-space validation finds
  collisions.
- Do not treat the green-anchor geometry as a finished shell proof. Both direct
  union of the cavity-bearing anchor and solid-first union damaged right-shell
  topology; source-shell integration remains explicitly unresolved.
- Do not integrate the green anchors or print V4 before visual approval,
  physical coupons, and a separate topology-safe shell-integration pass.

## Exact regeneration command

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_ear_root_removable_clamp_review_v4.py
```

## Next physical-review step

First review the isolated joints and clean exterior in V4. If accepted, prepare
small ASA coupons for insert fit, heat-set pull-out, clamp-pad compression, and
real tool/finger access. After those coupons pass, make and validate a separate
topology-safe anchor integration into the upper-head source. Only then can the
upper-head pieces become printable. F-13/F-14 outer-ear anti-flap work remains
the next independent design bucket.

## Preserved workstreams

The accepted eight-flange eye layout, rear-cassette/lower-face ownership,
requested reinforcement direction, C006 decision, and aluminum plate/rail
workstream remain preserved and unchanged.
