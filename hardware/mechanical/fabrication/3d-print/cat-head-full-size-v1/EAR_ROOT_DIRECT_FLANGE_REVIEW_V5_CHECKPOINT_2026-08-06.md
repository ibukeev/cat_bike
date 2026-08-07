# Ear-root direct-flange review V5 checkpoint — 2026-08-06 — REJECTED

## Status

V5 is rejected and archived. It removed the loose V4 clamps, but its orange
members still used nonparallel owner/flange frames joined by compound bridge
geometry. That did not match the already accepted simple eye-mount flange
construction and made the real assembly difficult to understand.

The archived V5 contained:

- three orange insert-owned flanges per side;
- one M3 button-head screw and 7 mm washer per flange;
- each screw passes through a 3.4 mm orange clearance hole into a green shell-owned boss with an M3 heat-set insert;
- no blue clamps and no loose connector pieces.

Do not continue, mirror, integrate, export, or print V5. V6 supersedes it with
one right-side standard paired-flange prototype for review.

## Current review files

- Blender review: `output/60-ear-root-reviews/ear-root-direct-flange-review-v5-rejected-complex-bridge/ear-root-direct-flange-review-v5.blend`
- Validation: `output/60-ear-root-reviews/ear-root-direct-flange-review-v5-rejected-complex-bridge/ear-root-direct-flange-review-v5-validation.json`
- Review renders: `output/60-ear-root-reviews/ear-root-direct-flange-review-v5-rejected-complex-bridge/renders/ear-root-direct-flange-*.png`
- Rejected V4 archive: `output/60-ear-root-reviews/ear-root-removable-clamp-review-v4/`

The Blender file opens in full structural-head context. For connector inspection, use:

- `EAR5_DIRECT_FLANGES_ORANGE__PROPOSED`
- `EAR5_FIXED_SHELL_ANCHORS_GREEN__PROPOSED_NOT_INTEGRATED`
- `EAR5_M3_HARDWARE_BRASS__PROPOSED`
- `EAR5_ACCESS_ENVELOPES_WHITE__HIDDEN_BY_DEFAULT`

The per-side `*-retention-context.png` renders hide only the masking yellow insert body so the orange/green relationship remains visible against the ear and upper shell.

## Source of truth and regeneration

- Generator: `source/generate_ear_root_direct_flange_review_v5.py`
- Config: `config/ear-root-direct-flange-review-v5.json`
- Accepted fit-body source remains V3: `config/ear-root-insertion-fit-review-v3.json`
- Required aluminum interface remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`.

Exact regeneration command from repository root:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_ear_root_direct_flange_review_v5.py
  -- --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/60-ear-root-reviews/ear-root-direct-flange-review-v5-rejected-complex-bridge
```

## Recorded V5 geometry and dimensions — rejected

- Preserve the accepted V3 yellow fit body, ear clearance, 13/9 mm visible saddle relief, and the three reviewed mount locations per side.
- Orange root: 20 mm tangent length, radial range 1.5–12 mm, 4.0 mm thick.
- Orange direct tab: 20 mm tangent length, 3.5 mm thick, fused into its root with 0.4 mm configured overlap.
- Green boss: 24 mm tangent length, radial range −14 to −4 mm, 9.0 mm thick.
- Orange-to-green nominal bearing: 0.0 mm gap, 6.0 mm radial overlap, 120 mm² per flange.
- Standard M3 clearance hole: 3.4 mm.
- Washer: 7.0 mm OD.
- Heat-set cavity: 4.6 mm diameter × 4.5 mm depth; proposed insert is 4.2 mm diameter × 4.0 mm length.
- Minor physical adjustment may enlarge only the orange clearance hole. Retain the 7 mm washer and re-check edge distance.

## Validation performed

- Exact Gate 8 source mesh count: 31; fingerprints unchanged.
- Accepted V3 body mirror-bounds error: 0.0 mm.
- Both validation composites are one connected manifold with 0 boundary and 0 non-manifold edges.
- Orange root/tab intersection pairs are `[14, 21, 22]` on both sides.
- Orange flange/body intersections are left `[18, 20, 16]`, right `[15, 18, 15]`.
- Green boss/upper-head root intersections are left `[60, 8, 37]`, right `[70, 8, 32]`.
- No orange flange hits an unintended fixed boss.
- No green boss hits an unintended structural shell.
- Screw/tool access envelopes have no hits with the ear removed.
- Accepted V3 deep-body clearance remains clear at all 41 samples with the 0.4 mm margin.

The permanent orange flanges themselves do **not** pass through the old fully assembled 60 mm outward/upward service path. The sweep intersects the green bosses first and then the upper-head shell. V5 therefore requires loosening/removing the applicable upper-head shell for later insert service. This is the explicit simplicity-versus-serviceability tradeoff selected for this review.

## Rejected or unsafe variants

- V4 loose blue bridging clamps are rejected as unnecessary assembly complexity; preserved only in the archive above.
- Do not force the permanent orange flanges through the old V3 path.
- Do not enlarge a hole without retaining washer coverage and safe edge distance.
- Do not merge or print the green bosses yet: their exact source-shell topology is still unresolved.
- No STL, G-code, slicer project, or fabrication output was created.

## Preserved workstreams

This V5 iteration does not alter the accepted eye mounts, lower-face/rear-cassette ownership, reinforcement direction, C006 interface, exact ears, exact upper-head source geometry, or aluminum plate/rail V0.5 workstream.

## Superseded next step

Do not review V5 for approval. Review the single right-side V6 prototype first.
Only after that interface is accepted may it be replicated to the other five
ear-root locations.
