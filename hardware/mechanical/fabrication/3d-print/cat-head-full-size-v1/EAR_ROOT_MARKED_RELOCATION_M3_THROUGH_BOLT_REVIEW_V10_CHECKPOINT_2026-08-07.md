# Ear-root marked relocation and M3 through-bolt review V10 checkpoint — 2026-08-07

## Status

V10 is the current F-10/F-11/F-12 placement review. It does exactly the marked
change: retain the unmarked connector set, remove the crossed set, and relocate
that set to the checked adjacent forward seam. The same move is mirrored on the
left. The accepted V9 standard-flange and M3-hole concept is unchanged.

This is not print released. The placement and drilled interface are validated,
but the green tabs still need production-shell integration and physical
driver/washer/nyloc access review. Do not start ASA parts from V10.

## Current review files

- Blender: `output/00-current-review/ear-root-marked-relocation-m3-through-bolt-review-v10.blend`
- Validation: `output/00-current-review/ear-root-marked-relocation-m3-through-bolt-review-v10-validation.json`
- Full head: `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-full-head-context.png`
- Marked move in context: `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-{right,left}-user-marked-relocation-context.png`
- Two orange roots on each translucent piece: `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-{right,left}-translucent-piece-two-orange-roots.png`
- Isolated sets: `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-{right,left}-two-connector-sets-isolated.png`
- M3 close-ups: `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-{right,left}-{a,b}-m3-hole-alignment.png`
- Owner-root proofs: `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-{right,left}-{a,b}-{orange,green}-owner-root.png`

Useful Blender collections use the `EAR10_` prefix. Orange tabs belong to the
moving translucent pieces; green tabs are proposed fixed shell geometry. The
16 Boolean proof objects are hidden review aids, not fabrication parts.

## Source of truth and regeneration

- Generator: `source/generate_ear_root_marked_relocation_m3_through_bolt_review_v10.py`
- Config: `config/ear-root-marked-relocation-m3-through-bolt-review-v10.json`
- Accepted fit body remains V3.
- Required aluminum interface remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`.

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_ear_root_marked_relocation_m3_through_bolt_review_v10.py -- --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/ear-root-marked-relocation-m3-through-bolt-review-v10.json --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/00-current-review
```

## Accepted decisions and dimensions

- Set A is unchanged on the original lower seam at fraction `0.45`.
- Set B replaces the crossed set on the adjacent forward seam at fraction
  `0.73`, mirrored left/right.
- The selected point is about `1.9 mm` inward along that seam from the initially
  mapped check-mark point at fraction `0.75`; the exact point failed the left
  `80 mm³` owner-root gate.
- Same-side set separation is `45.115 mm`; V9 was `36.9166 mm`, and V8 was
  `34.9211 mm`.
- Two connector sets per translucent piece; four sets and eight tabs total.
- Every tab is a plain `22 × 12 × 4 mm` rectangle with a `0.3 mm` mating gap.
- One shared `3.4 mm` M3 clearance path per orange/green pair.
- Four aligned M3 paths and eight drilled tab holes total.
- Minimum bore-to-edge material is `4.05 mm`.
- Hardware remains four M3 × 16 through-bolts, eight 7 mm OD washers, and four
  M3 nyloc nuts, serviced from inside.
- No wedge, trapezoid, broad base, bridge, clamp, boss, loose connector, or
  exterior protrusion was added.

## Validation performed and results

- Blender V10 generation: pass.
- Four `3.2 mm` gauges clear all nominal `3.4 mm` paths; all bores align.
- Same-side separation: right/left `45.115 mm`, above the `45 mm` gate.
- Direct owner-root overlaps:
  - right A: orange `81.0001`, green `106.7681 mm³`;
  - left A: orange `80.1945`, green `106.7495 mm³`;
  - right B: orange `92.4415`, green `108.9017 mm³`;
  - left B: orange `82.9953`, green `112.4173 mm³`.
- All eight roots pass the `80 mm³` minimum; overlap never exceeds its source
  tab volume, and mirrored root results remain within the recorded tolerance.
- Blender's MANIFOLD solver is used for review-only owner intersections. Its
  difference-volume partition is recorded only as a diagnostic because the
  right/left B green difference result is numerically unstable; it does not
  alter connector geometry or weaken the hard overlap gates.
- Both body/two-tab moving composites are one closed manifold component.
- Actual seated shell collisions: none. Green unintended-shell collisions:
  none.
- Accepted V3 deep-body and actual moving geometry clear all 41 path samples on
  both sides.
- The conservative `0.4 mm` expanded tab envelope touches only at the seated,
  intentionally mated interface; physical tolerance remains a review hold.
- Front, left, right, and top exterior masks are pixel-identical.
- Exact Gate 8 source mesh count remains 31 and all source fingerprints are
  unchanged.
- No STL, G-code, slicer project, fabrication output, or print release exists.

## Rejected variants

- Adjacent-seam fractions `0.88` and `0.82` did not produce acceptable roots.
- The exact mapped fraction `0.75` gave only `69.085 mm³` in the weak left
  orange root under the final proof solver.
- Fractions `0.745` and `0.74` remained below the left-root gate.
- Fraction `0.73` is the closest tested position to the mark that passes the
  final root-strength, collision, motion, bore, and exterior checks.
- V9's old same-seam B location is archived and must not be restored.

## Preserved workstreams

V10 does not modify the accepted V3 fit body, exact ears, exact upper-head
source meshes, eyes, lower-face/rear-cassette ownership, reinforcement
direction, C006, or the aluminum plate/rail `CAT-HEAD-SHELL-ALUMINUM-V0.5`
workstream.

## Next physical review

1. Open the V10 blend and inspect `right-user-marked-relocation-context` first.
2. Confirm one flange set remained at the unmarked location and the other is at
   the checked forward seam; then mirror-check the left side.
3. Inspect the two translucent-piece context views and confirm two widely
   spaced orange roots per piece.
4. Inspect all four M3 close-ups and confirm a single common hole axis through
   each orange/green pair.
5. In Blender, confirm practical access for the driver, two washers, and nyloc
   at every location.
6. After placement approval, integrate only the green tabs into their owning
   shell meshes and re-run fabrication/slicer checks before any ASA release.
