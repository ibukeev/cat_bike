# Ear-Root Restored-Coverage Review V2 Checkpoint — 2026-08-06

## Status

This is the single current ear-root review awaiting visual approval. It changes
only the two review glow-insert meshes. The exact Gate 8 ear and upper-head
meshes, their integrated four-M3 saddles, the accepted eye V3 layout,
lower-face/rear-cassette ownership, reinforcement direction, C006, and aluminum
V0.5 remain unchanged.

This is not a print release. No STL, G-code, slicer project, or ASA fabrication
output was generated.

## Open this file

- Blender: `output/00-current-review/ear-root-restored-coverage-review-v2.blend`
- Validation: `output/00-current-review/ear-root-restored-coverage-review-v2-validation.json`
- Renders: `output/00-current-review/renders/`

The completed constraints-only baseline is archived at
`output/60-ear-root-reviews/ear-root-interface-constraints-review-v1/`.

## What changed

The rejected Gate 8 insert relief was:

- Connector clearance: `1.2 mm`.
- Corner-relief depth: `38.0 mm`.
- Side-tip setback: `18.0 mm`.

The V2 candidate uses:

- Connector clearance requirement: `1.2 mm`.
- Corner-relief depth: `13.0 mm`.
- Side-tip setback: `9.0 mm`.

This reduces corner relief by `65.8%` and side setback by `50.0%`. The large
opening beneath each ear is closed; only localized clearance around the real
internal saddle remains.

A `12/10 mm` sweep candidate technically passed at approximately
`1.213 mm`, only `0.013 mm` above the requirement, and was rejected as too
fragile. The selected `13/9 mm` candidate provides useful margin on both sides.

## Review colors and collections

- Cyan, `EAR2_EXACT_EARS_CYAN__UNCHANGED`: exact Gate 8 ears.
- Gray, `EAR2_EXACT_UPPER_HEADS_GRAY__UNCHANGED`: exact Gate 8 upper heads.
- Yellow, `EAR2_RESTORED_COVERAGE_INSERTS_YELLOW__REVIEW`: the two candidate
  replacement inserts.
- `EAR2_REJECTED_38x18_INSERTS__HIDDEN`: the old large-cutout inserts retained
  hidden for traceability.
- `EAR2_OTHER_SOURCE_GEOMETRY__HIDDEN`: unrelated source geometry hidden.

## Validation performed and results

- Candidate count: two, one per side.
- Mirror bounds error: `0.0 mm`.
- Each candidate has one connected component.
- Each candidate has zero boundary edges and zero non-manifold edges.
- Left saddle intersections: zero.
- Right saddle intersections: zero.
- Left minimum sampled saddle gap: `1.5238 mm`.
- Right minimum sampled saddle gap: `1.5262 mm`.
- Required saddle gap: `1.2 mm`.
- Each side retains one integrated saddle with four internal M3 paths.
- Alignment dowels: zero.
- Exterior ear fastener holes: zero.
- Exact left/right ear and upper-head mesh fingerprints remain unchanged.
- Shared metal interface remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`.
- Visible round-stick or external-block objects: zero.

The smaller coplanar triangle in each QUAD source panel remains omitted because
its unique vertex lies inside the retained triangle with positive barycentric
coordinates and less than `0.0001 mm` plane error. Adding it would create an
overlapping surface and would not add coverage.

## Visual review steps

1. Open the Blender file and use the default both-sides interior view.
2. Inspect the yellow insert directly beneath each cyan ear.
3. Orbit to each exterior side and confirm the former large black opening is
   gone.
4. Toggle the gray upper-head collection off to inspect each yellow insert as a
   complete part.
5. Confirm the only remaining notch is immediately around the internal saddle.
6. Confirm left and right appear mirrored and there are no sticks, floating
   blocks, or rectangular connectors added outside the shell.

The renders named `left-coverage-cutaway` and `right-coverage-cutaway` are
the fastest static views for checking the restored panel area.

## Rejected or unsafe variants

- Reject the Gate 8 `38/18 mm` relief.
- Reject the barely passing `12/10 mm` candidate.
- Do not add the contained coplanar triangle as overlapping mesh.
- Do not reintroduce round sticks, dowels, or exterior connector blocks.
- Do not cut or alter the exact ear or upper-head shell meshes in this review.
- Do not release ASA parts before this visual review is accepted and the
  resulting insert geometry is integrated and revalidated in the full head.

## Exact regeneration command

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_ear_root_restored_coverage_review_v2.py
```

## Next physical-review step

User reviews only the restored yellow coverage and localized saddle notch in
the V2 Blender file. If accepted, the next engineering step is to integrate the
two candidate inserts into the full source-of-truth assembly, rerun full-head
collision/interface validation, and only then decide whether any ear-root test
print is warranted.

## Preserved workstreams

The accepted V3 eight-flange eye layout is archived unchanged. Lower-face and
rear-cassette ownership remain unchanged. Requested reinforcements remain
preserved. C006 and the aluminum plate/rail workstream are untouched.
