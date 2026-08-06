# Ear-Root Insertion-Fit Review V3 Checkpoint — 2026-08-06

## Status

This is the single current ear-root review. It addresses only physical-fit
feedback F-07, F-08, and F-09: both upper-corner collisions, the lower-center
collision/insertion failure, and excessive deep-body snugness.

V3 is a fit-envelope review, not a finished or printable insert. Retention,
seated datums, flange strength, and tool access remain deferred to
F-10/F-11/F-12. No STL, G-code, slicer project, or ASA output was generated.

## Open this file

- Blender: `output/00-current-review/ear-root-insertion-fit-review-v3.blend`
- Validation: `output/00-current-review/ear-root-insertion-fit-review-v3-validation.json`
- Renders: `output/00-current-review/renders/`
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
- Service order for this check: remove the ear, rotate the insert free edge
  `25 degrees` inward, then translate it `30 mm` inward. Installation is the
  exact reverse.

## Validation performed and results

- Two candidates, one per side; both have one connected component, zero
  boundary edges, and zero non-manifold edges.
- Left is an exact mirror of the canonical right body; maximum bounds error is
  `0.0 mm`.
- Seated intersections with the seven exact structural shell sections: zero on
  both sides, with the corresponding ear installed for the seated check.
- Insertion path: `41` samples per side (`82` total), with the corresponding ear
  removed and all other structural shell sections assembled.
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
- Blue: hidden-by-default `25-degree` rotated path ghosts.
- Green: hidden-by-default `30 mm` translated path ghosts.
- Unrelated exact source geometry is retained hidden for traceability.

## Visual review steps

1. Open the current Blender file and inspect both yellow seated bodies with the
   cyan ears and gray upper heads visible.
2. Orbit around both upper corners and the lower-center edge. Confirm there is
   no visible shell overlap, missing panel island, stick, or exterior block.
3. Hide the ears and inspect the left and right path renders in order:
   yellow seated, blue rotated, green translated.
4. Toggle `EAR3_PATH_GHOSTS__HIDDEN_BY_DEFAULT` only when comparing the motion
   envelope; do not mistake ghosts for printable geometry.
5. Confirm the `13/9 mm` visible saddle notch still looks acceptable.

## Rejected or unsafe variants

- Reject the inherited `0.35 mm` deep-body clearance and `0.05 mm` cap clearance;
  they reproduce an over-snug physical fit.
- Reject reusing the old hidden capture pads or M2.5 retainer.
- Reject deep-body clearance above the selected `2.5 mm` without redesign; the
  tested `2.6 mm` family disconnected the cap from the body.
- Do not validate the insertion path with the ear installed; documented service
  order removes the ear first. The ear is checked separately in the seated state.
- Do not edit the exact Gate 8 ears or upper-head shells to make this insert fit.
- Do not print V3: it intentionally has no retention or seated datum design.

## Exact regeneration command

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_ear_root_insertion_fit_review_v3.py
```

## Next physical-review step

The user reviews only the yellow seated coverage and the blue/green insertion
sequence. If accepted, the next logical iteration is F-10/F-11/F-12: define
seated datums and two or three short accessible retention points without
reintroducing the removed interference. Only after that integrated geometry
passes the same full-shell/path checks should a small fit coupon be prepared.

## Preserved workstreams

The accepted V3 eight-flange eye layout, rear-cassette/lower-face ownership,
requested reinforcement direction, C006 decision, and aluminum plate/rail
workstream remain preserved and unchanged.
