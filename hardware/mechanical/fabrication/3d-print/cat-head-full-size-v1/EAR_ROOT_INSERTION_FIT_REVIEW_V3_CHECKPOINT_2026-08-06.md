# Ear-Root Insertion-Fit Review V3 Checkpoint — 2026-08-06

## Status

The user visually accepted the yellow seated fit-body geometry on 2026-08-06.
This is the archived accepted fit-envelope baseline; V4 is now the current
retention review. V3 addresses only physical-fit feedback F-07, F-08, and F-09: both
upper-corner collisions, the lower-center collision/insertion failure, and
excessive deep-body snugness.

The cyan/blue-looking geometry visible in the default view is the unchanged
exact ear, not a new connector. The blue 30 mm and green 60 mm outward/upward
bodies are motion ghosts hidden by default. They were not separately reviewed
visually; their clearance is covered by the corrected world-space path validation.

V3 is a fit-envelope review, not a finished or printable insert. Retention,
seated datums, flange strength, and tool access remain deferred to
F-10/F-11/F-12. No STL, G-code, slicer project, or ASA output was generated.

## Open this file

- Blender: `output/60-ear-root-reviews/ear-root-insertion-fit-review-v3/ear-root-insertion-fit-review-v3.blend`
- Validation: `output/60-ear-root-reviews/ear-root-insertion-fit-review-v3/ear-root-insertion-fit-review-v3-validation.json`
- Renders: `output/60-ear-root-reviews/ear-root-insertion-fit-review-v3/renders/`
- Accepted V2 coverage baseline: `output/60-ear-root-reviews/ear-root-restored-coverage-review-v2/`

## Accepted decisions and dimensions

- Preserve the V2 visible saddle relief: `13 mm` corner-relief depth, `9 mm`
  side-tip setback, and `1.2 mm` required saddle clearance.
- Increase the hidden deep-body perimeter clearance from `0.35 mm` to `2.5 mm`.
- Increase the shallow visible-cap perimeter clearance from `0.05 mm` to
  `1.0 mm` so a tight exterior seam does not over-constrain the deep body.
- Add `0.4 mm` localized clearance to the exact Gate 8 ear geometry.
- Require a digitally clear `0.4 mm` expanded hidden-body insertion-path margin.
- Generate the right fit body canonically after the ear-clearance cut and mirror
  it exactly to the left.
- Exclude inherited overlap/capture pads and the M2.5 retainer from this fit-only
  body. They were the dominant upper-head obstruction and are not accepted as
  the future retention design.
- Service order for this check: remove the ear and retainers, then translate the
  insert `60 mm` at `45 degrees` outward and `45 degrees` upward. Mirror the X
  direction on the left; installation is the exact reverse.

## Validation performed and results

- Two candidates, one per side; both have one connected component, zero
  boundary edges, and zero non-manifold edges.
- Left is an exact mirror of the canonical right body; maximum bounds error is
  `0.0 mm`.
- Seated intersections with the seven exact structural shell sections: zero on
  both sides, with the corresponding ear installed for the seated check.
- Insertion path: `41` samples per side (`82` total) over `60 mm`, with the
  corresponding ear and retainers removed and all other structural shell
  sections assembled.
- The corrected world-space escape-cone audit tested `266` spherical directions;
  `41` cleared the short 0.5/1/2/3/5 mm samples and the full 60 mm removal.
  The selected path is the simplest symmetric clear result: 45 degrees outward
- Maximum actual-body triangle-intersection pairs across every path sample:
  zero on both sides.
- Maximum triangle-intersection pairs for the `0.4 mm` expanded hidden-body
  margin across every path sample: zero on both sides.
- The exact 31 Gate 8 source meshes have unchanged fingerprints.
- Each ear/upper-head saddle remains present with four internal M3 paths, zero
  alignment dowels, and zero exterior fastener holes.
- Shared metal interface remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`.
- No accepted eye, lower-face, rear-cassette, reinforcement, C006, or aluminum
  geometry changed.

Physical acceptance A-07 remains pending a later coupon because digital
clearance and path validation cannot prove real ASA tolerance or hand assembly.

## Review colors and collections

- Cyan: exact Gate 8 ears, unchanged.
- Gray: exact Gate 8 upper heads, unchanged.
- Yellow: seated V3 fit-body-only candidates.
- Blue: hidden-by-default `30 mm` outward/upward midpoint ghosts.
- Green: hidden-by-default `60 mm` outward/upward endpoint ghosts.
- Unrelated exact source geometry is retained hidden for traceability.

## Visual review steps

1. Open the archived V3 Blender file and inspect both yellow seated bodies with the
   cyan ears and gray upper heads visible.
2. Orbit around both upper corners and the lower-center edge. Confirm there is
   no visible shell overlap, missing panel island, stick, or exterior block.
3. Hide the ears and inspect the left and right path renders in order:
   yellow seated, blue at 30 mm, green at 60 mm.
4. Toggle `EAR3_PATH_GHOSTS__HIDDEN_BY_DEFAULT` only when comparing the motion
   envelope; do not mistake ghosts for printable geometry.
5. Confirm the `13/9 mm` visible saddle notch still looks acceptable.

## Rejected or unsafe variants

- Reject the inherited `0.35 mm` deep-body clearance and `0.05 mm` cap clearance;
  they reproduce an over-snug physical fit.
- Reject reusing the old hidden capture pads or M2.5 retainer.
- Reject the previously documented `25-degree` rotate plus `30 mm` inward path.
  Its earlier apparent pass came from a transform-local BVH check that did not
  apply moved-object transforms. Correct world-space validation finds upper-head
  collisions along that path. The accepted seated yellow geometry itself remains
  clear and unchanged.
- Reject deep-body clearance above the selected `2.5 mm` without redesign; the
  tested `2.6 mm` family disconnected the cap from the body.
- Do not validate the insertion path with the ear installed; documented service
  order removes the ear and retainers first. The ear is checked separately in
  the seated state.
- Do not edit the exact Gate 8 ears or upper-head shells to make this insert fit.
- Do not print V3: it intentionally has no retention or seated datum design.

## Exact regeneration command

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_ear_root_insertion_fit_review_v3.py
```

## Next physical-review step

The yellow seated fit envelope is visually accepted. V4 now carries the
F-10/F-11/F-12 retention proposal without changing this body. Review V4's three
interior clamp joints per side and clean exterior before any physical coupon.
Only after that review should a small fit, heat-set pull-out, and tool-access
coupon be prepared.

## Preserved workstreams

The accepted V3 eight-flange eye layout, rear-cassette/lower-face ownership,
requested reinforcement direction, C006 decision, and aluminum plate/rail
workstream remain preserved and unchanged.
