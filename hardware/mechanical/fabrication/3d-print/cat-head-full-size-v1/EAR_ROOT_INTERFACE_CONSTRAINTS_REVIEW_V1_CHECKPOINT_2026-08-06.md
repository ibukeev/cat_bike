# Ear-Root Interface Constraints Review V1 Checkpoint — 2026-08-06

## Status

This is the current read-only constraints review for the next task bucket. It
isolates the exact Gate 8 ear shells, upper-head owners, integrated four-M3
saddles, and current ear-root glow inserts. It changes no mesh geometry.

The large-relief ear-root insert variant is rejected because it leaves missing
coverage beneath the ears. No replacement geometry is proposed in this file.

## Primary review files

- Blender: `output/00-current-review/ear-root-interface-constraints-review-v1.blend`
- Validation: `output/00-current-review/ear-root-interface-constraints-review-v1-validation.json`
- Renders: `output/00-current-review/renders/`

## Review colors and collections

- Cyan, `EAR1_EXACT_EARS_CYAN`: unchanged left and right ear shells.
- Gray, `EAR1_EXACT_UPPER_HEADS_GRAY`: unchanged upper-head owner shells.
- Purple, `EAR1_CURRENT_REJECTED_RELIEF_INSERTS_PURPLE`: unchanged current
  ear-root translucent inserts with the rejected large relief.
- `EAR1_OTHER_SOURCE_GEOMETRY_HIDDEN`: unrelated Gate 8 geometry hidden,
  not deleted or modified.

## Structural facts preserved

Each side has exactly one integrated four-M3 saddle between its ear and upper
head:

- Saddle module length: `23.973 mm`.
- Tab depth: `8.0 mm`.
- Tab thickness: `3.8 mm`.
- Mating-face clearance: `0.35 mm`.
- Internal M3 paths: four per side.
- Alignment dowels: zero.
- Exterior fastener holes: zero.
- Minimum tab exterior recess: `8.019 mm`.
- Minimum root-web exterior recess: `0.369 mm`.
- Two `2.0 x 1.2 mm` root webs per tab, converted to a continuous solid
  root base.

The saddle is integrated into the shell meshes. The earlier round stick-like
objects were review artifacts, not production ear geometry, and must not be
reintroduced.

## Current insert problem

The original Gate 7 ear-root insert relief was:

- Connector clearance: `0.8 mm`.
- Corner-relief depth: `25.0 mm`.
- Side-tip setback: `10.0 mm`.

Gate 8 enlarged those effective values to:

- Connector clearance: `1.2 mm`.
- Corner-relief depth: `38.0 mm`.
- Side-tip setback: `18.0 mm`.

That aggressive relief explains the missing translucent coverage/opening
beneath each ear. The current insert variant is therefore rejected even though
its mesh is closed and manifold.

## Validation performed and results

- Exactly one four-M3 saddle manifest record exists per side.
- Both saddle records contain zero dowels and zero exterior holes.
- No independently named bolt, dowel, rod, alignment, or stick mesh exists in
  the production Gate 8 ear geometry.
- Both current ear-root inserts are closed and manifold.
- Gate 8 relief is confirmed larger than the Gate 7 base relief.
- All 31 source mesh fingerprints remain unchanged.
- No eye, lower-face, rear-cassette, C006, aluminum, STL, G-code, or print
  output was changed or generated.

## Rejected or unsafe variants

- Reject the current `38/18 mm` ear-root insert relief.
- Do not reintroduce the round sticks or external-looking reference cylinders.
- Do not expose the internal M3 paths through the exterior shell.
- Do not sacrifice independent ear removal.
- Do not redesign eyes, rear ownership, C006, or aluminum in this bucket.
- Do not release ASA parts before the ear saddle and restored insert coverage
  are visually and physically reviewed together.

## Exact regeneration command

```bash
blender --background hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/10-design-gates/gate8-full-size-structural-iteration/gate8-full-size-structural-review.blend --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_ear_root_interface_constraints_review_v1.py
```

## Next design review

Create one mirrored ear-root candidate set that:

1. Restores complete translucent coverage beneath both ears.
2. Uses only localized clearance around the real four-M3 internal saddle.
3. Preserves the four-M3 load path and independent ear removal.
4. Shows no round sticks, external blocks, or exterior fastener holes.
5. Reviews the saddle and translucent insert together before any production
   Boolean or STL export.

## Preserved workstreams

The accepted V3 eight-flange eye layout is archived unchanged. Lower-face and
rear-cassette ownership remain unchanged. The shared aluminum interface remains
`CAT-HEAD-SHELL-ALUMINUM-V0.5`; C006, plate, rails, holes, and stock
dimensions are untouched.
