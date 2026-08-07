# Ear-root standard paired-flange review V6 checkpoint — 2026-08-06

## Status

V6 is the current visual-review iteration for F-10/F-11/F-12. It intentionally
contains only one prototype at the primary right-side ear-root location. It
copies the accepted eye-mount construction: two parallel rectangular tabs, one
tapered broad owner base per tab, and one coaxial M3 fastener.

This is **not print released**. Do not mirror it, integrate it into source
shells, export STL/G-code, or start ASA parts until the user accepts this one
real-world assembly interface.

## Current review files

- Blender review: `output/00-current-review/ear-root-standard-paired-flange-review-v6.blend`
- Validation: `output/00-current-review/ear-root-standard-paired-flange-review-v6-validation.json`
- Review renders: `output/00-current-review/renders/ear-root-standard-pair-*.png`
- Rejected V5 archive: `output/60-ear-root-reviews/ear-root-direct-flange-review-v5-rejected-complex-bridge/`

Useful Blender collections:

- `EAR6_ACCEPTED_V3_BODIES_YELLOW__UNCHANGED`: accepted insert/body owners;
- `EAR6_RIGHT_INSERT_FLANGE_ORANGE__SINGLE_PROTOTYPE`: moving orange member;
- `EAR6_RIGHT_HEAD_FLANGE_GREEN__SINGLE_PROTOTYPE_UNINTEGRATED`: fixed green member;
- `EAR6_M3_HARDWARE_BRASS__SINGLE_PROTOTYPE`: screw, washer, and heat-set insert;
- `EAR6_ACCESS_ENVELOPES_WHITE__HIDDEN_BY_DEFAULT`: driver/finger review envelopes.

## Source of truth and regeneration

- Generator: `source/generate_ear_root_standard_paired_flange_review_v6.py`
- Config: `config/ear-root-standard-paired-flange-review-v6.json`
- Accepted fit-body source remains V3: `config/ear-root-insertion-fit-review-v3.json`
- Accepted eye-flange pattern reference: `source/generate_eye_all_eight_flange_broad_base_review_v3.py`
- Required aluminum interface remains `CAT-HEAD-SHELL-ALUMINUM-V0.5`.

Exact regeneration command from repository root:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_ear_root_standard_paired_flange_review_v6.py
```

## Decisions and dimensions

- Exactly one prototype: right side, location A. No mirrored or replicated copy.
- Orange and green are parallel rectangular tabs in one shared orthonormal frame.
- Each tab has exactly one tapered broad base fused toward its owner.
- Tab: 16 × 10 × 3.2 mm.
- Mating gap: 0.3 mm measured.
- Hole depth from front: 5.5 mm.
- Orange M3 clearance hole: 3.4 mm.
- Green proposed heat-set cavity: 4.6 mm diameter × 4.5 mm depth.
- Proposed insert: 4.2 mm diameter × 4.0 mm length.
- Washer: 7.0 mm OD × 0.8 mm.
- Broad base: 5.0 mm backing depth with 1.0 mm tab overlap; tapers from
  16 × 10 mm at the tab to 24 × 18 mm at the owner.
- Only the orange clearance hole may be enlarged during physical fit-up;
  retain the washer and verify edge distance.

## Validation performed and results

- Generator syntax and config JSON validation: pass.
- V6 imports/calls no code from the rejected V5 generator.
- Exact Gate 8 source mesh count: 31; all fingerprints unchanged.
- Reopened Blender audit: one orange flange, one green flange, four brass
  hardware objects, two hidden access envelopes, zero left prototypes, and zero bridge/clamp/convex-hull objects.
- Both broad bases overlap their rectangular tab and intended owner.
- Orange/green measured gap: 0.3 mm; coaxial-axis error: 0.0 mm.
- Moving yellow-body/orange-flange composite: one connected component, zero
  boundary edges, zero non-manifold edges.
- Seated actual structural hits: none. Green unintended-shell hits: none.
- Accepted V3 deep-body path: clear at all 41 samples with 0.4 mm margin.
- Actual paired geometry path conflicts: none.
- Conservative 0.4 mm expanded moving-flange envelope: **not clear at the
  seated sample**; it touches the right upper head and green flange.
- Driver/finger envelopes intersect the accepted yellow body in the conservative
  volume check. Physical tool approach remains a review item.
- Shared cat-head/aluminum interface regression: 9 tests pass.
- No STL, G-code, slicer project, fabrication output, or print release was created.

## Rejected or unsafe variants

- V4 loose clamp/bridge construction remains rejected.
- V5 compound bridge geometry remains rejected even when fused into orange.
- Do not recreate a convex-hull transition, wedge, clamp, or loose connector.
- Do not replicate V6 before the single interface is visually approved.
- Do not treat the uninflated path result as physical tolerance proof; the
  0.4 mm envelope and tool access are unresolved.
- Do not enlarge the orange hole without washer coverage and edge-distance checks.
- Do not integrate the green member until the interface and heat-set coupon are approved.

## Preserved workstreams

V6 does not modify the accepted V3 fit body, exact ears, exact upper-head source
geometry, eyes, lower-face/rear-cassette ownership, reinforcement direction,
C006, or the aluminum plate/rail `CAT-HEAD-SHELL-ALUMINUM-V0.5` workstream.

## Next physical/visual review

1. Open the V6 Blender file in full-head context first.
2. Isolate the orange and green prototype collections and confirm they read as
   two ordinary parallel screw flanges, not a clamp or compound connector.
3. Confirm the orange broad base visibly joins the yellow insert/body and the
   green broad base visibly joins the gray right upper-head owner.
4. Toggle the brass hardware and confirm one M3 screw/washer passes through
   orange into the green insert on one shared axis.
5. Toggle the white access envelopes and judge whether a real driver and fingers
   can approach after the ear panel is removed.
6. Decide whether this single interface is accepted, needs relocation/clearance
   changes, or should use through-bolt/nut hardware before any replication.
