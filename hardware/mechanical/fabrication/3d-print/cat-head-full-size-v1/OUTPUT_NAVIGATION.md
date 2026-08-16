# Cat Head Output Navigation

The generated `output/` directory is organized by workstream so the single
current review is always easy to find.

## Open this first
- Current V32 C009 full-context route audit — **JSON-only pass; no geometry
  artifact and not a print source**. The exact existing C009 member moved by
  `[1.825092, 10.446536, 8.290829] mm` remains one valid closed solid, retains
  `5.1278 mm3` C001 engagement, clears the repaired eye by `4.4763 mm`, and has
  zero intersection with every declared frozen exact neighbor. Conservative
  lower-face, rear-cassette, and right-aluminum checks also pass. Read:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c009-full-context-route-audit-v32/validation-v32.json` and
  `RIGHT_UPPER_C009_FULL_CONTEXT_ROUTE_AUDIT_V32_CHECKPOINT_2026-08-16.md`.

- Current V31 existing-member reposition route audit — **JSON-only partial
  result; no geometry artifact and not a print source**. The exact V26 tapered
  rail has zero clean rigid-translation routes and that route is rejected.
  Existing C009 has 104 clean right-upper-context candidates; the preferred
  shortest translation is `[1.825092, 10.446536, 8.290829] mm`, retaining
  `5.1278 mm3` C001 engagement and `4.4763 mm` repaired-eye clearance with
  zero other upper-component collisions. Full-head context is not yet audited.
  Read:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-existing-member-reposition-route-audit-v31/validation-v31.json` and
  `RIGHT_UPPER_EXISTING_MEMBER_REPOSITION_ROUTE_AUDIT_V31_CHECKPOINT_2026-08-16.md`.
- Current V30 C001/C009 non-additive route audit — **JSON-only negative
  result; no geometry artifact and not a print source**. The global repaired-eye
  `4.0 mm` offset failed safely in OCC at both `0.01 mm` and `0.05 mm`
  tolerances, so no cut was attempted. C009 remains a valid closed solid,
  intersects the repaired eye by `27.7283 mm3`, and attaches only to C001;
  deletion remains held. Read:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c001-c009-non-additive-route-audit-v30/validation-v30.json` and
  `RIGHT_UPPER_C001_C009_NON_ADDITIVE_ROUTE_AUDIT_V30_CHECKPOINT_2026-08-16.md`.
- Current V29 C001/C009 existing-body route audit — **JSON-only negative
  result; no geometry artifact and not a print source**. It proves there is no
  clean direct continuation of the existing V26 tapered rail into C001 within
  the controlled `30 mm` envelope while preserving `4.0 mm` eye clearance and
  `0.1 mm3` owner overlap. C009 intersects the repaired eye by `27.7283 mm3`
  and attaches only to C001. V27 remains rejected and absent. Read:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c001-c009-existing-body-route-audit-v29/validation-v29.json` and
  `RIGHT_UPPER_C001_C009_EXISTING_BODY_ROUTE_AUDIT_V29_CHECKPOINT_2026-08-16.md`.
- Current V28 repaired-eye/accepted-upper audit — **JSON-only, fail-closed
  precision audit; no geometry artifact and not a print source**. It substitutes
  the repaired V4 eye into the accepted V25 42-component context and proves
  that only C001 (`100.5990 mm3`) and C009 (`27.7283 mm3`) retain positive
  material contact. C027 remains clear at `5.3208 mm`; C012 has zero overlap
  and measures `3.999956 mm`, missing V28's strict nominal/tolerance gate by
  `0.000024 mm`. V27 is absent and remains rejected. Read:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-repaired-eye-approved-context-audit-v28/validation-v28.json` and
  `RIGHT_UPPER_REPAIRED_EYE_APPROVED_CONTEXT_AUDIT_V28_CHECKPOINT_2026-08-16.md`.
- Current topology-repaired right-eye full-context V5 — **review-only
  one-sided assembly; not mirrored, production-unioned, or print-released**.
  The repaired V4 eye replaces only the frozen V18 eye at zero transform. All
  four approved assembly relationships have exactly `0.0 mm` clearance change:
  outer/lower mating gaps remain approximately `0.300 mm`, C046 remains
  `4.6063 mm`, and C048 remains `4.0317 mm`. Open:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-topology-repaired-full-context-review-v5/CAT_HEAD_RIGHT_EYE_TOPOLOGY_REPAIRED_FULL_CONTEXT_REVIEW_V5.FCStd`.
- V5 validation and resumable checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-topology-repaired-full-context-review-v5/validation-v5.json` and
  `RIGHT_EYE_TOPOLOGY_REPAIRED_FULL_CONTEXT_REVIEW_V5_CHECKPOINT_2026-08-16.md`.
- No new geometry or user face selection is required for this topology bucket.
  Mirror, production union, STL, slicing, G-code, and ASA release remain held.
- Current V17 full topology-repaired exact STEP V4 — **review-only one-sided
  owner; not mirrored, integrated, or print-released**. The repaired owner is
  one valid closed `1178`-face solid. STEP round-trip bounds are unchanged,
  maximum vertex error is `7.43e-12 mm`, and the exact all-face audit finds
  **zero non-adjacent crossing pairs**. Open:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-full-topology-repair-step-review-v4/CAT_HEAD_RIGHT_EYE_V17_FULL_TOPOLOGY_REPAIR_STEP_REVIEW_V4.FCStd`.
- V4 exact STEP, validation, and resumable checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-full-topology-repair-step-review-v4/right_eye_v17_full_topology_repaired_review_v4.step`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-full-topology-repair-step-review-v4/validation-v4.json`, and
  `RIGHT_EYE_V17_FULL_TOPOLOGY_REPAIR_STEP_REVIEW_V4_CHECKPOINT_2026-08-16.md`.
- The isolated outer-root repair collapses a `0.000004075 mm` folded sliver to
  its exact host edge. It preserves all `1174` untouched source faces,
  unchanged exterior bounds, mating geometry, and the clean second-eye root.
  Mirror, production union, STL, slicing, G-code, and ASA release remain held.
- Current V17/V9 repaired exact STEP V2 — **review-only exact round-trip and
  audit; superseded by V4 as the current topology candidate**. The repaired owner is
  one valid closed `1179`-face solid; bounds are unchanged, STEP vertex error is
  `8.75e-12 mm`, and both former V9 defect pairs are gone. Open:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-v9-skin-topology-repair-step-review-v2/CAT_HEAD_RIGHT_EYE_V17_V9_SKIN_TOPOLOGY_REPAIR_STEP_REVIEW_V2.FCStd`.
- V2 exact STEP, validation, and checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-v9-skin-topology-repair-step-review-v2/right_eye_v17_v9_skin_topology_repaired_review_v2.step`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-v9-skin-topology-repair-step-review-v2/validation-v2.json`, and
  `RIGHT_EYE_V17_V9_REPAIRED_STEP_AUDIT_V2_CHECKPOINT_2026-08-16.md`.
- The V2 exact audit left the protected outer-root crossing `Face72 / Face489`;
  V3/V4 now repair and validate that separate defect. Retain V2 as immutable
  pre-repair evidence.
- Current V17/V9 skin topology repair proposal — **review-only bounded
  one-side repair; all local gates pass; not a STEP/STL or print source**. The
  complete proposed eye owner and the green replacement patch are visible;
  the unchanged frozen V17 owner and removed old patch are hidden for optional
  before/after comparison. Open:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-v9-skin-topology-repair-review-v1/CAT_HEAD_RIGHT_EYE_V17_V9_SKIN_TOPOLOGY_REPAIR_REVIEW_V1.FCStd`.
- Topology-repair validation/checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-v9-skin-topology-repair-review-v1/validation-v1.json` and
  `RIGHT_EYE_V17_V9_SKIN_TOPOLOGY_REPAIR_REVIEW_V1_CHECKPOINT_2026-08-15.md`.
- This bounded repair has zero anchor motion, unchanged exterior bounds,
  `1176/1176` untouched faces retained, and zero local non-adjacent crossing
  diagnostics. The separate protected outer-root defect remains; mirror,
  production union, STEP/STL, slicing, G-code, and ASA release remain held.
- Current V17/V9 skin repair exact-anchor review — **review only; zero geometry
  changes; not a repair or print source**. Green is host `Face587`, magenta is
  penetrating `Edge1278`, orange/yellow are diagnostic partner faces
  `Face263/Face400`, and the hidden cyan group contains the true edge-owner
  faces `Face581/Face582`. Open:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-v9-skin-repair-anchor-review-v1/CAT_HEAD_RIGHT_EYE_V17_V9_SKIN_REPAIR_ANCHOR_REVIEW_V1.FCStd`.
- V17/V9 anchor validation/checkpoint:
  `../../../../../reports/generated/cat-head-cad-validation/v17-v9-skin-repair-anchor-review-v1/validation-v1.json` and
  `RIGHT_EYE_V17_V9_SKIN_REPAIR_ANCHOR_REVIEW_V1_CHECKPOINT_2026-08-15.md`.
- Current V17 exact-eye defect visualization — **defect localization visually
  approved 2026-08-15; zero geometry changes; not a repair or print source**.
  Toggle `DEFECT_REGION__V9_SKIN` to
  inspect the red/orange/yellow V9 skin faces, then toggle
  `DEFECT_REGION__OUTER_INWARD_ROOT` to inspect the purple/cyan outer-root
  faces. The grey translucent eye is the unchanged frozen V17 owner, and the
  clean second-eye root must not be modified. Open:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-v17-defect-visualization-v1/CAT_HEAD_RIGHT_EYE_V17_DEFECT_VISUALIZATION_V1.FCStd`.
- Visualization validation/checkpoint:
  `../../../../../reports/generated/cat-head-cad-validation/v17-defect-visualization-v1/validation-v1.json` and
  `RIGHT_EYE_V17_DEFECT_VISUALIZATION_V1_CHECKPOINT_2026-08-15.md`.
- Current right-upper approved C027/C012 context V25 — **complete 42-solid review context; residual legacy C001/C009/C019 eye contacts remain; not a print source**. The old C012 and C027 are absent; approved V24 C012 has `4.0000 mm` eye clearance and approved V19 C027 has `5.3208 mm`. Open: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-approved-c027-c012-context-review-v25/CAT_HEAD_RIGHT_UPPER_APPROVED_C027_C012_CONTEXT_REVIEW_V25.FCStd`.
- V25 validation/checkpoint: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-approved-c027-c012-context-review-v25/validation-v25.json` and `RIGHT_UPPER_APPROVED_C027_C012_CONTEXT_REVIEW_V25_CHECKPOINT_2026-08-15.md`.
- Rejected V27 C001 preserved-rail root — **do not reopen or reuse**. The user
  rejected its added rectangular Y-root/planks because they create unexplained
  material in front of the eye. Retain only as negative evidence:
  `RIGHT_UPPER_C001_PRESERVED_RAIL_ROOT_REVIEW_V27_CHECKPOINT_2026-08-15.md`.
- Current right-upper C012 eye-clearance V24 — **one-side proposed change; awaiting visual approval; not a print source**. The authorized `5.21 mm` shortening produces one valid closed `606.54 mm3` solid, zero exact-eye intersection, `4.0000 mm` clearance, and `150.5311 mm3` C001 engagement. C009 is unchanged and held. Open: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c012-eye-clearance-review-v24/CAT_HEAD_RIGHT_UPPER_C012_EYE_CLEARANCE_REVIEW_V24.FCStd`.
- V24 validation/checkpoint: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c012-eye-clearance-review-v24/validation-v24.json` and `RIGHT_UPPER_C012_EYE_CLEARANCE_REVIEW_V24_CHECKPOINT_2026-08-15.md`.
- Current C009/upper-C012 exact-anchor V23 — **review only; no geometry
  change; superseded by V24 for upper C012; not a print source**. Exact BREP identities are C009 eye cap
  `Face17` / root `Face13`, and upper-C012 eye cap `Face4` / root `Face18`.
  C009 remains structurally held; upper-C012 `Face4` was approved and is the source anchor for V24.
  Open:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-eye-c009-c012-exact-anchor-review-v23/CAT_HEAD_RIGHT_UPPER_EYE_C009_C012_EXACT_ANCHOR_REVIEW_V23.FCStd`.
- V23 validation and checkpoint: `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-eye-c009-c012-exact-anchor-review-v23/validation-v23.json` and `RIGHT_UPPER_EYE_C009_C012_EXACT_ANCHOR_REVIEW_V23_CHECKPOINT_2026-08-15.md`.
- Current C001 exact-anchor V22 — **review only; no geometry change; not a
  print source**. The corrected exact candidates are top `Face382` and side
  `Face324`, `Face536`, and `Face554`. The previous `Face364/Face385` guesses
  are explicitly rejected and were never cut. Open:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-eye-c001-exact-anchor-review-v22/CAT_HEAD_RIGHT_UPPER_EYE_C001_EXACT_ANCHOR_REVIEW_V22.FCStd`.
- V22 validation and resumable checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-eye-c001-exact-anchor-review-v22/validation-v22.json` and
  `RIGHT_UPPER_EYE_C001_EXACT_ANCHOR_REVIEW_V22_CHECKPOINT_2026-08-15.md`.
- C009 remains held: the audited `>=13.98 mm` trim reaches the clearance target
  but removes approximately `96.85%` of the component. Upper C012 has a
  plausible `>=5.21 mm` shortening contract but still lacks a user-approved
  FreeCAD BREP face. Neither trim is authorized.
- Current upper/eye V21 — **review-only exact collision localization; source
  owners unchanged; modification anchors not selected; not a print source**.
  The exact Boolean-common diagnostics are separately toggleable for C001
  (`100.60 mm3`), C009 (`27.73 mm3`), upper C012 (`0.04 mm3`), and C019.
  C019 is only an invalid degenerate zero-volume touch and is not a trim
  target. Open:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-eye-residual-collision-localization-review-v21/CAT_HEAD_RIGHT_UPPER_EYE_RESIDUAL_COLLISION_LOCALIZATION_REVIEW_V21.FCStd`.
- V21 validation and resumable checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-eye-residual-collision-localization-review-v21/validation-v21.json` and
  `RIGHT_UPPER_EYE_RESIDUAL_COLLISION_LOCALIZATION_REVIEW_V21_CHECKPOINT_2026-08-15.md`.
- Current upper context V20 — **approved C027 substituted into the complete
  42-component right-upper context; audit only; not a print source**. C027
  remains collision-free at `5.3208 mm` eye clearance. The remaining upper-eye
  contacts are C001 (`100.5990 mm3`), C009 (`27.7283 mm3`), upper C012
  (`0.0366 mm3`), and a near-zero C019 sliver. Open:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c027-approved-context-review-v20/CAT_HEAD_RIGHT_UPPER_C027_APPROVED_CONTEXT_REVIEW_V20.FCStd`.
- V20 validation and resumable checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c027-approved-context-review-v20/validation-v20.json` and
  `RIGHT_UPPER_C027_APPROVED_CONTEXT_REVIEW_V20_CHECKPOINT_2026-08-15.md`.
- V19 is the user-approved isolated C027 source proposal. It has zero eye
  interference, `5.3208 mm` clearance, one valid closed solid, and positive
  C001/C032 root overlap. Its validation and checkpoint remain at:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-c027-eye-clearance-review-v19/validation-v19.json` and
  `RIGHT_UPPER_C027_EYE_CLEARANCE_REVIEW_V19_CHECKPOINT_2026-08-15.md`.
- V18 remains the last complete right-side display context, but it is
  superseded as collision evidence: the subsequent complete upper-component
  audit found eye contact at C001, C009, C012, C019, and C027.

- Current HS-11 V18 complete right-side context — **exact displayed owners pass;
  awaiting user visual approval; not a print source**. V18 uses zero-transform
  references to the complete V3 upper head, approved V13 repaired lower owner,
  exact V17 eye, both exact V5 head flanges, unchanged lower-face context, and
  frozen C046/C048 evidence. Both flange gaps are `0.3000 mm`; eye-to-C046/C048
  clearances are `4.6063/4.0317 mm`. Open:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-full-context-review-v18/CAT_HEAD_RIGHT_EYE_FULL_CONTEXT_REVIEW_V18.FCStd`.
- V18 validation and resumable checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-full-context-review-v18/validation-v18.json` and
  `RIGHT_EYE_FULL_CONTEXT_REVIEW_V18_CHECKPOINT_2026-08-15.md`.
- The unchanged lower-face components 002–060 are visual context only in V18;
  their aggregate mesh remains non-watertight/non-manifold and is not a
  production or print owner.
- Current HS-11 V17 exact right-eye owner — **exact-solid pass; awaiting full
  right-side context review; superseded by V18 for visual review; not a print source**. V17 uses the unchanged V9
  production eye STEP and exact V5 eye-side flange leaves. The completed owner
  is one valid closed `7269.56 mm3` solid with zero self-intersections; its STEP
  re-import preserves one solid, matching topology, and `7269.55 mm3` volume.
  Both roots positively engage the eye owner, and both exact clearances to the
  V5 head-side flange references measure `0.3000 mm`. Open:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-exact-owner-integration-review-v17/CAT_HEAD_RIGHT_EYE_EXACT_OWNER_INTEGRATION_REVIEW_V17.FCStd`.
- V17 exact STEP and checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-exact-owner-integration-review-v17/right_eye_bucket_with_both_exact_flange_roots_v17.step` and
  `RIGHT_EYE_EXACT_OWNER_INTEGRATION_REVIEW_V17_CHECKPOINT_2026-08-14.md`.
- V16 is retained only as a rejected triangulated diagnostic. A later
  read-only exact triangle audit found 30 non-zero crossing pairs rather than
  the validator's BVH-candidate count of six; OCCT also reports two
  self-intersecting wires and two unorientable regions. These defects do not
  occur in the authoritative exact V17 solid.
- V16 validation, objects, renders, contract, generator, and checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/validation-v16.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/objects/`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-owner-integration-review-v16/review/`,
  `config/right-eye-flange-owner-integration-review-v16.json`,
  `source/generate_right_eye_flange_owner_integration_review_v16.py`, and
  `RIGHT_EYE_FLANGE_OWNER_INTEGRATION_REVIEW_V16_CHECKPOINT_2026-08-14.md`.
- V15 is rejected because the displayed upper head was incomplete and the
  flange/reinforcement context was not integrated into the real owners. Keep
  it only as historical evidence; do not mirror or print from V15.

- Approved print-orientation reference: open
  `output/50-slicer-projects/right-upper-head-c001-ab-asa-tilt-review-v2/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ASA_TILT_REVIEW_V2.3mf`
  in PrusaSlicer. This isolated derivative applies `-20 deg` world-X tilt and
  `+1.958 mm` Y recenter without changing geometry or scale. Its real sliced
  object/support/`8 mm` brim margins pass at
  `20.7661/23.4099/11.538/11.538 mm` left/right/front/rear. Status remains
  **visually approved 2026-08-14** for orientation, supports, and brim. This is
  not a structural print release: HS-11 through HS-20 remain unresolved, and
  the local G-code is not committed or released.
- V2 validation and resumable checkpoint:
  `output/50-slicer-projects/right-upper-head-c001-ab-asa-tilt-review-v2/validation-v2.json`
  and `RIGHT_UPPER_HEAD_C001_AB_ASA_TILT_REVIEW_V2_CHECKPOINT_2026-08-14.md`.
- Open the ASA diagnostic project for the current right C001 A/B shell:
  `output/50-slicer-projects/right-upper-head-c001-ab-asa-diagnostic-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ASA_DIAGNOSTIC_V1.3mf`.
  It preserves the user's exact saved rotation and geometry, embeds the
  installed Prusament ASA/MK4 baseline, automatic snug supports at `45 deg`,
  and an `8 mm` outer brim. PrusaSlicer completes the diagnostic slice
  (`14h 17m`, `139.30 g`), but this remains **HOLD / not print-ready**: the
  combined object/brim/support margins are `15.4146/27.3374/4.05255/1.874795
  mm` left/right/front/rear, failing the frozen `10 mm` front and rear gates.
  The local G-code is diagnostic only and is intentionally not committed.
- Validation and resumable checkpoint:
  `output/50-slicer-projects/right-upper-head-c001-ab-asa-diagnostic-v1/validation-v1.json`
  and `RIGHT_UPPER_HEAD_C001_AB_ASA_DIAGNOSTIC_V1_CHECKPOINT_2026-08-14.md`.
- Open the editable complete-shell HS-04 orientation project first:
  `output/50-slicer-projects/right-upper-head-c001-ab-orientation-handoff-v1/CAT_HEAD_RIGHT_UPPER_HEAD_C001_AB_ORIENTATION_HANDOFF_V1.3mf`.
  The user rotated and saved this one-object complete right upper-head C001
  shell with its approved A/B features integrated. The exact saved transform is
  preserved. Validation is HOLD: rear MK4 bed margin is `1.8748 mm`, planar bed
  contact is `0.0 mm2`, brim is `0 mm`, and the embedded profile is Generic PLA.
  No G-code or print release exists.
- Validation and resumable checkpoint:
  `output/50-slicer-projects/right-upper-head-c001-ab-orientation-handoff-v1/user-orientation-validation-v1.json`
  and `RIGHT_UPPER_HEAD_C001_AB_USER_ORIENTATION_V1_CHECKPOINT_2026-08-14.md`.
- The earlier standalone A/B coupon project is rejected as the requested
  orientation handoff and remains only as traceable historical evidence.

- HS-04 displayed V2 orientation — **visually approved 2026-08-14; not a
  full-shell print source**. The user explicitly confirmed that the under-ear
  opening is not bed-facing; the historical artifact name must not be treated as
  a datum description. Preserve the exact approved quaternion. The measured
  envelope is `203.498 x 163.628 x 155.848 mm`, with `18.251/18.186 mm` reserve
  per side. The editable full-shell orientation handoff exists above; no G-code
  or full-shell print release has been issued:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-under-ear-opening-print-orientation-review-v2/right-ab-under-ear-opening-print-orientation-review-v2.blend`.
- HS-04 V2 contract, evidence, and resumable checkpoint:
  `config/right-ab-under-ear-opening-print-orientation-review-v2.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-under-ear-opening-print-orientation-review-v2/review/`, and
  `RIGHT_AB_UNDER_EAR_OPENING_PRINT_ORIENTATION_REVIEW_V2_CHECKPOINT_2026-08-14.md`.
- The prior V1 optimizer-selected placement is rejected and retained only as
  traceable evidence.
- Current HS-11 V13 isolated topology proposal — **awaiting visual approval; not a print source**. It changes only lower-face component 001: the 1486-face exterior exact-union region is retained, three internal regions totaling 10 faces are removed, and one Boolean-only corner is snapped `0.0459405 mm` to the exact frozen source corner. Blender passes one closed manifold component with zero intersections, `0.00654787 mm` maximum exterior deviation, and unchanged bounds. FreeCAD/OCCT passes one valid closed solid. Open:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-topology-repair-review-v13/CAT_HEAD_RIGHT_LOWER_FACE_TOPOLOGY_REPAIR_REVIEW_V13.FCStd`.
- V13 Blender review, validation, contract, generator, and resumable checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-topology-repair-review-v13/CAT_HEAD_RIGHT_LOWER_FACE_TOPOLOGY_REPAIR_REVIEW_V13.blend`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-topology-repair-review-v13/validation-v13.json`,
  `config/right-lower-face-topology-repair-review-v13.json`,
  `source/generate_right_lower_face_topology_repair_review_v13.py`, and
  `RIGHT_LOWER_FACE_TOPOLOGY_REPAIR_REVIEW_V13_CHECKPOINT_2026-08-14.md`.
- V13 remains isolated: no V11 owner substitution, eye/flange/C046/C048 integration, mirror, STL, G-code, or print release has occurred.
- Current HS-11 V12 topology diagnostic — **HOLD, not a review approval or
  print source**. The approved V11 geometry is frozen. Sixty unchanged
  lower-face components were isolated; the inherited primary owner component
  is closed/manifold as a mesh but contains `41` triangle intersections across
  `21` mapped legacy seam/slot face pairs. FreeCAD fusion, Blender EXACT
  self-union, and Blender MANIFOLD self-union were rejected. Use the checkpoint
  and component inventory to resume the bounded seam repartition:
  `RIGHT_LOWER_FACE_TOPOLOGY_REPAIR_REVIEW_V12_CHECKPOINT_2026-08-14.md` and
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-lower-face-topology-repair-review-v12/component-inventory-v12.json`.
- V12 contract and reproducible component exporter:
  `config/right-lower-face-topology-repair-review-v12.json` and
  `source/export_right_lower_face_v11_components_for_v12.py`.
- Current HS-11 V11 regression-repair review — preserves the user-accepted V10
  outer-neck deletion and restores the exact user-approved V2 C046/C048
  clearance geometry. The stale original C046/C048 components are absent;
  restored C046/C048 clear the unchanged V9 eye by `4.6063/4.0317 mm`, retain
  lower-face and mutual structural contact, and both unchanged flange-pair gaps
  remain `0.3000 mm` with zero interference:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-neck-removal-clearance-regression-fix-review-v11/CAT_HEAD_RIGHT_EYE_NECK_REMOVAL_CLEARANCE_REGRESSION_FIX_REVIEW_V11.FCStd`
- V11 Blender review, evidence, validation, contract, and resumable checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-neck-removal-clearance-regression-fix-review-v11/CAT_HEAD_RIGHT_EYE_NECK_REMOVAL_CLEARANCE_REGRESSION_FIX_REVIEW_V11.blend`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-neck-removal-clearance-regression-fix-review-v11/review/`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-neck-removal-clearance-regression-fix-review-v11/validation-v11.json`,
  `config/right-eye-neck-removal-clearance-regression-fix-review-v11.json`, and
  `RIGHT_EYE_NECK_REMOVAL_CLEARANCE_REGRESSION_FIX_REVIEW_V11_CHECKPOINT_2026-08-14.md`.
- V9 is rejected because it removed the wrong component. V10's neck deletion is
  accepted, but V10 is superseded as a combined-context review because it
  resurrected the pre-clearance C046/C048 positions. V11 is still an isolated
  review, not an owner Boolean, mirror, STL, G-code, or print release. The
  inherited lower-face mesh still requires topology repair before production
  integration.

- Cleaned HS-11 V8 identification review — **rejected as a structural
  proposal**. The fabricated inner-upper pair has been removed from the
  interactive FreeCAD file and the unchanged validated V7 second pair has
  been restored. Use this file only to confirm pair identity and context. Its
  head leaf is `25.4458 mm` from the upper head, has `0.0 mm3` upper-head
  overlap, and remains lower-face owned, so HS-11 is unresolved:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-upper-head-only-dual-pair-review-v8/CAT_HEAD_RIGHT_EYE_UPPER_HEAD_ONLY_DUAL_PAIR_REVIEW_V8.FCStd`
- Historical V8 contract/validation/evidence and the corrected resumable
  checkpoint:
  `config/right-eye-upper-head-only-dual-pair-review-v8.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-upper-head-only-dual-pair-review-v8/validation-v8.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-upper-head-only-dual-pair-review-v8/review/`, and
  `RIGHT_EYE_UPPER_HEAD_ONLY_DUAL_PAIR_REVIEW_V8_CHECKPOINT_2026-08-13.md`.
- V7 remains rejected for incorrect lower-face ownership; V8 remains rejected
  for duplicate wrong-interface geometry. No owner Boolean, left mirror, STL,
  G-code, or print release exists.

- Current HS-11 all-four V5 — replaces rejected V4 with four real standalone
  plain flange solids: outer-eye, outer-head, lower-eye, and lower-head. Each
  is `12 x 8 x 4.8 mm`, with `2.4 mm` added only on its owner side. All
  mating faces and `2.8 mm` M2.5 axes remain fixed; both pair gaps remain
  `0.3000 mm`. All four exact objects are valid one-solids with no pair
  interference. Shape review is ready, but production integration remains
  held because outer-head owner overlap is `56.2443 mm3`, below the
  `80 mm3` direct-root gate:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-plain-flange-thickness-review-v5/CAT_HEAD_RIGHT_EYE_ALL_FOUR_PLAIN_FLANGE_THICKNESS_REVIEW_V5.FCStd`
- V5 contract, Blender context, validation, and checkpoint:
  `config/right-eye-all-four-plain-flange-thickness-review-v5.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-plain-flange-thickness-review-v5/CAT_HEAD_RIGHT_EYE_ALL_FOUR_PLAIN_FLANGE_THICKNESS_REVIEW_V5.blend`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-plain-flange-thickness-review-v5/validation-v5.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-all-four-plain-flange-thickness-review-v5/freecad-validation-v5.json`, and
  `RIGHT_EYE_ALL_FOUR_PLAIN_FLANGE_THICKNESS_REVIEW_V5_CHECKPOINT_2026-08-13.md`
- Rejected V4 is retained only as traceable evidence at
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-pair-radial-thickness-review-v4/`.
- Rejected V3 wrong-axis depth extension is retained only as traceable evidence
  at `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-outer-pair-face879-depth-extension-review-v3/`.
- Rejected V2 broad-base proposal is retained only as traceable evidence at
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-rectangular-root-review-v2/`.
- Rejected V1 is retained only as traceable evidence at
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-internal-root-embed-review-v1/`.
- Current HS-11 owner-integration audit — fail-closed because the two approved
  eye-side V3 flange roots and C048 have zero-depth owner contact; no printable
  Boolean was accepted. Open this to inspect the exact staged owners/features:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-reinforcement-owner-integration-review-v1/CAT_HEAD_RIGHT_EYE_FLANGE_REINFORCEMENT_OWNER_INTEGRATION_AUDIT_V1.FCStd`
- Audit checkpoint and staging validation:
  `RIGHT_EYE_FLANGE_REINFORCEMENT_OWNER_INTEGRATION_AUDIT_V1_CHECKPOINT_2026-08-13.md` and
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-flange-reinforcement-owner-integration-review-v1/validation-v1.json`
- Current HS-11 right-eye reinforcement-clearance V2 — gives both C046 and
  C048 at least `4.0 mm` clearance from the V9 eye; visually approved
  2026-08-13 and preserved by the current root proposal:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-reinforcement-clearance-review-v2/CAT_HEAD_RIGHT_EYE_REINFORCEMENT_CLEARANCE_REVIEW_V2.FCStd`
- V2 Blender comparison, validation, evidence, and checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-reinforcement-clearance-review-v2/CAT_HEAD_RIGHT_EYE_REINFORCEMENT_CLEARANCE_REVIEW_V2.blend`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-reinforcement-clearance-review-v2/validation-v2.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-reinforcement-clearance-review-v2/review/`, and
  `RIGHT_EYE_REINFORCEMENT_CLEARANCE_REVIEW_V2_CHECKPOINT_2026-08-13.md`
- Approved FreeCAD bilateral-eye exact-mirror review V9 — visually approved
  and promoted 2026-08-13; still not a print release:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/eye-bilateral-exact-mirror-review-v9/CAT_HEAD_EYE_BILATERAL_EXACT_MIRROR_REVIEW_V9.FCStd`
- Current bilateral-eye Blender context review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/eye-bilateral-exact-mirror-review-v9/CAT_HEAD_EYE_BILATERAL_EXACT_MIRROR_REVIEW_V9.blend`
- Current bilateral-eye validation and checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/eye-bilateral-exact-mirror-review-v9/validation-v9.json` and
  `EYE_BILATERAL_EXACT_MIRROR_REVIEW_V9_CHECKPOINT_2026-08-13.md`
- Controlled bilateral production owners:
  `production/eye-modules-v9/`
- Current Blender review:
  `output/00-current-review/ear-root-marked-relocation-m3-through-bolt-review-v10.blend`
- Current validation:
  `output/00-current-review/ear-root-marked-relocation-m3-through-bolt-review-v10-validation.json`
- Full-head context:
  `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-full-head-context.png`
- Right user-marked relocation context:
  `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-right-user-marked-relocation-context.png`
- Left user-marked relocation context:
  `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-left-user-marked-relocation-context.png`
- Right translucent piece with both orange roots:
  `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-right-translucent-piece-two-orange-roots.png`
- Right-side two-set isolated view:
  `output/00-current-review/renders/ear-root-marked-relocation-m3-through-bolt-right-two-connector-sets-isolated.png`
- Left equivalents use the same names with `left` in place of `right`.
- M3 bore close-ups are named
  `ear-root-marked-relocation-m3-through-bolt-{left,right}-{a,b}-m3-hole-alignment.png`.
- Per-owner cutaways are named
  `ear-root-marked-relocation-m3-through-bolt-{left,right}-{a,b}-{orange,green}-owner-root.png`.

## FreeCAD controlled-change pilot

- Current HS-11 reinforcement-clearance V2 — the user accepted the C048 V1
  direction but identified minor crowding at triangular C046. V2 moves C046
  rigidly `4.229 mm` away and trims `8.4611 mm` from C048's eye-side end.
  C046/C048 clear the V9 eye by `4.6063/4.0317 mm`, remain closed, retain
  lower-face contact, and overlap each other. Awaiting visual approval; no
  owner Boolean, mirror, STL, slicing, or print release:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-reinforcement-clearance-review-v2/CAT_HEAD_RIGHT_EYE_REINFORCEMENT_CLEARANCE_REVIEW_V2.FCStd`
- V2 contract, validation, evidence, and checkpoint:
  `config/right-eye-reinforcement-clearance-review-v2.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-reinforcement-clearance-review-v2/validation-v2.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-reinforcement-clearance-review-v2/review/`, and
  `RIGHT_EYE_REINFORCEMENT_CLEARANCE_REVIEW_V2_CHECKPOINT_2026-08-13.md`
- Current bilateral-eye exact-mirror V9 review — the user-approved V8 right
  bucket and removable rear cap are unchanged; the left owners are exact
  `X=0` mirrors. All four are valid, watertight, one-solid owners with matching
  bilateral topology/volume, no self-intersection, and no owner interference.
  The left STEP round-trip also passes. User visually approved V9 and the
  owners were promoted unchanged on 2026-08-13. No flange union, STL, slicing,
  ASA recommendation, or print release:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/eye-bilateral-exact-mirror-review-v9/CAT_HEAD_EYE_BILATERAL_EXACT_MIRROR_REVIEW_V9.FCStd`
- V9 full-head evidence, validation, contract, and checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/eye-bilateral-exact-mirror-review-v9/review/`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/eye-bilateral-exact-mirror-review-v9/validation-v9.json`,
  `config/eye-bilateral-exact-mirror-review-v9.json`, and
  `EYE_BILATERAL_EXACT_MIRROR_REVIEW_V9_CHECKPOINT_2026-08-13.md`
- The right-eye V8 review below is the accepted source for V9, not the active
  review.
- Current right-eye production-owner review V8 — exact promotion of the
  user-approved V6 continuous-wall bucket and V7 post-free removable cap.
  The clean file contains only the bucket, cap, and frozen diffuser context;
  no left mirror, STL, slicing, or print release:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-production-owner-review-v8/CAT_HEAD_RIGHT_EYE_PRODUCTION_OWNER_REVIEW_V8.FCStd`
- V8 validation and checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-production-owner-review-v8/validation-v8.json` and
  `RIGHT_EYE_PRODUCTION_OWNER_REVIEW_V8_CHECKPOINT_2026-08-12.md`
- Controlled right production inputs:
  `production/eye-modules-v8/right/`

- Current right primary-ear integrated through-channel V3 — the V4 clean
  owners are cut first, then unioned to the unchanged compact flanges. Two
  full-length 3.0 mm shaft proofs clear both integrated owners by at least
  `0.1946 mm` radially. The head retains two round 3.4 mm channels; the ear
  retains one round channel plus one `3.4 x 5.0 mm` slot. Awaiting visual
  approval; no left mirror, export, or print release:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-integrated-through-channel-review-v3/CAT_HEAD_RIGHT_PRIMARY_EAR_INTEGRATED_THROUGH_CHANNEL_REVIEW_V3.FCStd`
- Integration contract, validation, and checkpoint:
  `config/right-primary-ear-integrated-through-channel-review-v3.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-integrated-through-channel-review-v3/validation-v3.json`, and
  `RIGHT_PRIMARY_EAR_INTEGRATED_THROUGH_CHANNEL_REVIEW_V3_CHECKPOINT_2026-08-11.md`
- The clean-owner compact-pair V4 below is the preserved isolated source
  review for this integration, not the active review. It uses the untouched
  repaired upper head and flush-clean ear. The
  approved-direction V3 flange solids are copied without geometric change:
  existing two bolt axes, `21.5 x 10.4 x 4.0 mm` envelopes, `1.20 mm` owner
  embed, and exact `0.3500 mm` pair gap. Digital gates pass; awaiting visual
  approval. The flanges are separate proposals and do not drill the owners.
  No mirroring, export, or print release:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-clean-owner-compact-pair-review-v4/CAT_HEAD_RIGHT_PRIMARY_EAR_CLEAN_OWNER_COMPACT_PAIR_REVIEW_V4.FCStd`
- V4 contract, validation, evidence, and checkpoint:
  `config/right-primary-ear-clean-owner-compact-pair-review-v4.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-clean-owner-compact-pair-review-v4/validation-v4.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-clean-owner-compact-pair-review-v4/review/`, and
  `RIGHT_PRIMARY_EAR_CLEAN_OWNER_COMPACT_PAIR_REVIEW_V4_CHECKPOINT_2026-08-11.md`
- Corrected structured source audit — proves the exact `623.007 mm3`
  rectangular four-hole legacy extrusion belongs to the ear owner, not the
  upper-head owner:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-owner-source-audit-v1/CAT_HEAD_RIGHT_PRIMARY_EAR_OWNER_SOURCE_AUDIT_V1.FCStd`
- Superseded Face2 compact-pair V3 — flange geometry remains reusable, but its
  owner context used an upper-head copy with an unnecessary `8.09 mm3` cut.
  Do not use V3 as an integration, mirror, export, or print source:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-face2-compact-pair-review-v3/CAT_HEAD_RIGHT_PRIMARY_EAR_FACE2_COMPACT_PAIR_REVIEW_V3.FCStd`

- Rejected Face2 compact V2 — `20.0 mm` width left only `2.75 mm` outside
  the ear-side slot, below the `3.50 mm` material gate:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-face2-compact-pair-review-v2/CAT_HEAD_RIGHT_PRIMARY_EAR_FACE2_COMPACT_PAIR_REVIEW_V2.FCStd`
- Rejected Face2 compact V1 — `1.10 mm` embed left only `76.4957 mm3`
  ear-owner overlap, below the `80.0 mm3` gate. See
  `RIGHT_PRIMARY_EAR_FACE2_COMPACT_PAIR_REVIEW_V1_CHECKPOINT_2026-08-11.md`.

- Superseded clean-owner recovery V2 remains the preserved broad-pair
  baseline before the approved compacting direction:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-clean-owner-dual-bolt-flange-pair-recovery-review-v2/CAT_HEAD_RIGHT_PRIMARY_EAR_CLEAN_OWNER_DUAL_BOLT_FLANGE_PAIR_RECOVERY_REVIEW_V2.FCStd`

- Rejected recovery V1 — it restored the correct original flange pair but
  reused stale upper-head context containing the obsolete four-aperture lattice:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-original-dual-bolt-flange-pair-recovery-review-v1/CAT_HEAD_RIGHT_PRIMARY_EAR_ORIGINAL_DUAL_BOLT_FLANGE_PAIR_RECOVERY_REVIEW_V1.FCStd`

- Rejected compact replacement review — digital gates passed, but it
  misunderstood the request and visually buried/partially destroyed the
  established pair; do not integrate, mirror, export, or print:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-legacy-style-compact-two-hole-review-v1/CAT_HEAD_RIGHT_PRIMARY_EAR_LEGACY_STYLE_COMPACT_TWO_HOLE_REVIEW_V1.FCStd`
- Rejected compact review contract, validation, and checkpoint:
  `config/right-primary-ear-legacy-style-compact-two-hole-review-v1.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-legacy-style-compact-two-hole-review-v1/validation-v1.json`, and
  `RIGHT_PRIMARY_EAR_LEGACY_STYLE_COMPACT_TWO_HOLE_REVIEW_V1_CHECKPOINT_2026-08-11.md`

- Rejected right primary-ear inboard-lateral flange review — V4 passed
  topology and owner-root checks but failed user visual review because the
  flange still protrudes beyond the local ear surface; do not integrate,
  mirror, export, or print:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-flange-inboard-lateral-review-v4/CAT_HEAD_RIGHT_PRIMARY_EAR_FLANGE_INBOARD_LATERAL_REVIEW_V4.FCStd`
- V4 contract, validation, and checkpoint:
  `config/right-primary-ear-flange-inboard-lateral-review-v4.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-flange-inboard-lateral-review-v4/validation-v4.json`, and
  `RIGHT_PRIMARY_EAR_FLANGE_INBOARD_LATERAL_REVIEW_V4_CHECKPOINT_2026-08-11.md`
- Restored clean pre-relocation baseline for the next controlled proposal:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-primary-ear-legacy-flange-flush-owner-cut-review-v2/CAT_HEAD_RIGHT_PRIMARY_EAR_LEGACY_FLANGE_FLUSH_OWNER_CUT_REVIEW_V2.FCStd`

- Pilot document:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_OPPOSITE_SIDE_FLANGE_PILOT_V1.FCStd`
- Current anchor-marker review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_ANCHOR_CANDIDATES_V3.FCStd`
- Previous anchor-marker review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_ANCHOR_CANDIDATES_V2.FCStd`
- Original anchor-marker review:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_ANCHOR_CANDIDATES_V1.FCStd`
- Current flange-shape review — display-corrected source solids, no geometry
  change from V2:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_PROPOSED_FLANGE_SHAPE_V3_DISPLAY_FIXED.FCStd`
- Current right-panel topology proposal:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-panel-topology-repair-v1/CAT_HEAD_RIGHT_PANEL_TOPOLOGY_REPAIR_REVIEW_V1.FCStd`
- Current right upper-head topology proposal:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-deterministic-topology-repair-v3/CAT_HEAD_RIGHT_UPPER_HEAD_TOPOLOGY_REPAIR_REVIEW_V3.FCStd`
- Right upper-head topology validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-deterministic-topology-repair-v3/freecad-validation.json`
- Right upper-head context screenshot:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-deterministic-topology-repair-v3/review/01-right-upper-head-context-isometric.png`
- Right upper-head isolated screenshot:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-deterministic-topology-repair-v3/review/02-right-upper-head-isolated-isometric.png`
- Current right-ear topology reference — user-approved 2026-08-08:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ear-deterministic-topology-repair-v1/CAT_HEAD_RIGHT_EAR_TOPOLOGY_REPAIR_REVIEW_V1.FCStd`
- Right-ear topology validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ear-deterministic-topology-repair-v1/freecad-validation.json`
- Right-ear context screenshot:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ear-deterministic-topology-repair-v1/review/01-right-ear-context-isometric.png`
- Right-ear isolated screenshot:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ear-deterministic-topology-repair-v1/review/02-right-ear-isolated-front.png`
- Right A panel-tab clearance proposal — user visually approved 2026-08-08:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-panel-tab-clearance-review-v1/CAT_HEAD_RIGHT_A_PANEL_TAB_CLEARANCE_REVIEW_V1.FCStd`
- Right A panel-tab validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-panel-tab-clearance-review-v1/freecad-validation.json`
- Right A panel-tab visual evidence:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-panel-tab-clearance-review-v1/review/`
- Right A M3 drilled pair — user-approved 2026-08-08; tool access held:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-m3-hole-axis-review-v1/CAT_HEAD_RIGHT_A_M3_HOLE_AXIS_REVIEW_V1.FCStd`
- Right B panel-tab local-relief proposal — user visually approved 2026-08-08:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-b-panel-tab-clearance-review-v1/CAT_HEAD_RIGHT_B_PANEL_TAB_CLEARANCE_REVIEW_V1.FCStd`
- Right B local-relief numeric contract and validation:
  `config/right-b-panel-tab-local-clearance-review-v1.json`
- Selected right upper-head legacy small-flange removal — user visually
  approved 2026-08-09; isolated review only:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-legacy-small-flange-removal-review-v1/CAT_HEAD_RIGHT_UPPER_HEAD_LEGACY_SMALL_FLANGE_REMOVAL_REVIEW_V1.FCStd`
- Legacy small-flange removal numeric contract:
  `config/right-upper-head-legacy-small-flange-removal-review-v1.json`
- Legacy small-flange removal checkpoint and review instructions:
  `RIGHT_UPPER_HEAD_LEGACY_SMALL_FLANGE_REMOVAL_REVIEW_V1_CHECKPOINT_2026-08-08.md`
- Legacy small-flange clean context and internal before/after evidence:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-upper-head-legacy-small-flange-removal-review-v1/review/`
- Right A tool-access and short-insert proposal — user visually approved
  2026-08-09; ASA coupon and integration held:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-tool-access-audit-v1/CAT_HEAD_RIGHT_A_TOOL_ACCESS_AUDIT_V1.FCStd`
- Right A tool-access numeric contract and validation:
  `config/right-a-tool-access-audit-v1.json`
- Corrected right-A surface-open insert review — digitally validated and user
  visually approved 2026-08-09; prior trapped V3 pocket rejected:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-a-surface-open-insert-correction-v1/CAT_HEAD_RIGHT_A_SURFACE_OPEN_INSERT_CORRECTION_V1.FCStd`
- Corrected right-A contract and checkpoint:
  `config/right-a-surface-open-insert-correction-v1.json` and
  `RIGHT_A_SURFACE_OPEN_INSERT_CORRECTION_V1_CHECKPOINT_2026-08-09.md`
- Final right-B surface-open hole/access review — digitally validated and user
  visually approved 2026-08-09:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-b-hole-access-review-v1/CAT_HEAD_RIGHT_B_HOLE_ACCESS_REVIEW_V1.FCStd`
- Final right-B contract and checkpoint:
  `config/right-b-hole-access-review-v1.json` and
  `RIGHT_B_HOLE_ACCESS_REVIEW_V1_CHECKPOINT_2026-08-09.md`
- Integrated right-side A/B owner review — digital pass and user visually
  approved 2026-08-09; not print-ready:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-ab-owner-integration-review-v1/CAT_HEAD_RIGHT_AB_OWNER_INTEGRATION_REVIEW_V1.FCStd`
- Integrated right-side contract and checkpoint:
  `config/right-ab-owner-integration-review-v1.json` and
  `RIGHT_AB_OWNER_INTEGRATION_REVIEW_V1_CHECKPOINT_2026-08-09.md`
- Bilateral A/B mirror review — left panel integrated successfully; mirrored
  left head-tab placement visually approved and frozen 2026-08-09; left C001
  production union remains blocked and this is not a print release:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/bilateral-ab-mirror-review-v1/CAT_HEAD_BILATERAL_AB_MIRROR_REVIEW_V1.FCStd`
- Bilateral review evidence, contract, and checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/bilateral-ab-mirror-review-v1/review/`,
  `config/bilateral-ab-mirror-review-v1.json`, and
  `BILATERAL_AB_MIRROR_REVIEW_V1_CHECKPOINT_2026-08-09.md`
- Current isolated left-C001 topology/integration review — FreeCAD Part and
  A/B review-copy union gates pass; one marked `0.2343 mm` exterior
  triangulation reinterpretation awaits visual approval; not print-ready:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/left-upper-head-c001-topology-repair-v2/CAT_HEAD_LEFT_UPPER_HEAD_C001_AB_INTEGRATION_REVIEW_V2.FCStd`
- Left-C001 V2 evidence, numeric contract, and checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/left-upper-head-c001-topology-repair-v2/review/`,
  `config/left-upper-head-c001-topology-repair-review-v2.json`, and
  `LEFT_UPPER_HEAD_C001_TOPOLOGY_REPAIR_V2_CHECKPOINT_2026-08-09.md`
- Complete-left-owner C001 integration review — user visually approved
  2026-08-10; C001 V2 and A/B are integrated; C002-C041 are exact; inherited
  C003 remains a separate OCCT-invalid hold; not print-ready:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/left-upper-head-full-owner-c001-integration-v1/CAT_HEAD_LEFT_FULL_OWNER_C001_AB_BILATERAL_VALIDATION_V1.FCStd`
- Complete-left-owner evidence, contract, validation, and checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/left-upper-head-full-owner-c001-integration-v1/review/`,
  `config/left-upper-head-full-owner-c001-integration-v1.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/left-upper-head-full-owner-c001-integration-v1/validation.json`, and
  `LEFT_UPPER_HEAD_FULL_OWNER_C001_INTEGRATION_V1_CHECKPOINT_2026-08-10.md`
- Current C003 isolated topology proposal — Blender and FreeCAD/OCCT gates
  pass; the minimal five-object FCStd is saved; awaiting visual approval before
  owner integration:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/left-upper-head-c003-topology-repair-v1/CAT_HEAD_LEFT_UPPER_HEAD_C003_TOPOLOGY_REPAIR_REVIEW_V1.FCStd`
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/left-upper-head-c003-topology-repair-v1/CAT_HEAD_LEFT_UPPER_HEAD_C003_TOPOLOGY_REPAIR_REVIEW_V1.blend`
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/left-upper-head-c003-topology-repair-v1/PROPOSED__LEFT_UPPER_HEAD_C003__TOPOLOGY_REPAIR_V1.stl`
- C003 proposal evidence, contract, validation, and checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/left-upper-head-c003-topology-repair-v1/review/`,
  `config/left-upper-head-c003-topology-repair-review-v1.json`,
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/left-upper-head-c003-topology-repair-v1/validation.json`, and
  `LEFT_UPPER_HEAD_C003_TOPOLOGY_REPAIR_V1_CHECKPOINT_2026-08-10.md`
- Frozen C003 anchor diagnostic (source-only):
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/left-upper-head-c003-topology-repair-v1/CAT_HEAD_LEFT_UPPER_HEAD_C003_ANCHOR_DIAGNOSTIC_V1.FCStd`
- Pre-proposal diagnostic copy — does not contain the proposal and must not be approved:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/left-upper-head-c003-topology-repair-v1/CAT_HEAD_LEFT_UPPER_HEAD_C003_PRE_PROPOSAL_DIAGNOSTIC_COPY_V1.FCStd`
- Current print-readiness dashboard:
  `PRINT_READINESS_DASHBOARD_2026-08-08.md`
- Canonical head-shell completion tracker:
  `HEAD_SHELL_COMPLETION_TRACKER.md`
- Short return review queue:
  `RETURN_REVIEW_QUEUE_2026-08-08.md`
- Physical-feedback closure matrix:
  `FEEDBACK_CLOSURE_MATRIX_2026-08-08.md`
- Strict topology/margin validation checkpoint:
  `PRINT_READINESS_VALIDATION_CHECKPOINT_2026-08-08.md`
- Panel topology validation:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-panel-topology-repair-v1/freecad-validation.json`
- Clean validation-only Part re-export; not a fabrication release:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-panel-topology-repair-v1/PROPOSED__RIGHT_TRANSLUCENT_PANEL__VALID_PART_REEXPORT_V1.stl`
- Rejected V4 validation diagnostic — automatic reference conversion remained
  open and invalid; do not use it for spatial approval or production:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_PROPOSED_FLANGE_SHAPE_V4_REJECTED_INVALID_REFERENCE_CONVERSION.FCStd`
- V4 pre-validation checkpoint:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_PROPOSED_FLANGE_SHAPE_V4_PRE_VALIDATION_CHECKPOINT.FCStd`
- Previous V2 flange-shape diagnostic — broken assembly-link display; retain
  only for comparison and do not use its visible links as placement evidence:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_PROPOSED_FLANGE_SHAPE_V2_26MM.FCStd`
- Rejected V1 flange-shape diagnostic — failed A/panel root gate:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/CAT_HEAD_RIGHT_PANEL_PROPOSED_FLANGE_SHAPE_V1.FCStd`
- Reference manifest:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/reference-manifest.json`
- Context screenshot:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/review/01-reference-context-isometric.png`
- Selected pilot panel screenshot:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/review/02-pilot-panel-selected.png`
- Selected receiving-owner screenshot:
  `output/70-freecad-pilots/opposite-side-flange-pilot-v1/review/03-receiving-owner-selected.png`

This is a reference-only right-side placement pilot. It contains exactly the
accepted V3 right translucent body, the exact right upper-head owner, and the
exact right ear as collision context. It contains no connector geometry and
does not supersede or modify the frozen V10 Blender review.

The separate anchor-candidate V3 document adds only two 5 mm-radius
`REVIEW_ONLY__` marker spheres and places each 35 mm inward from its original
panel-boundary extreme along the same owner-supported boundary. Their centers
await user approval and are not flange, fastener, cut, union, or fabrication
geometry. V1 and V2 remain preserved for comparison.

The isolated right-side flange-shape V2 diagnostic preserves those approved
anchors and uses the user-approved `26 x 12 x 4 mm` tabs. Its four diagnostic
root volumes exceed `80 mm3`, but the invalid converted reference solids cannot
clear production validation and report a conservative `1.3988 mm3` A/panel-tab
overlap with the head owner. It contains no holes, integration, mirror, or
fabrication output. V1 remains preserved as the failed `22 mm` comparison.

The V3 display-corrected copy keeps the V2 geometry and numeric contract
unchanged. It hides four assembly links that had dropped their source
placements and stacked at `(13, 6, 2) mm`, and instead shows the correctly
placed source solids. V3 opens with only the translucent-panel owner visible;
toggle that owner off and `REFERENCE__right_upper_head_owner` on for the
matching head-side review. V3 remains undrilled, unintegrated, right-side only,
and not print-ready.

The V4 validation-only conversion attempt is rejected. Separately named copies
of the panel, upper-head owner, and ear were repaired and converted, but every
Part remained open and invalid. V3 is still the active review. Root,
interference, motion, access, drilling, mirroring, integration, and printing
remain held until valid upstream owner topology is produced and verified.

The user approved the isolated right-panel topology proposal on 2026-08-08. It
preserves all `71` existing vertex coordinates and the exact accepted bounding
box, replacing only the ambiguous 35-polygon tessellation with 142 explicit
triangles. Its FreeCAD Part is one closed valid solid, and the FreeCAD
re-exported mesh passes manifold, watertight, and self-intersection checks.
Both panel-side flange roots exceed `80 mm3`. This approval covers only the
panel topology.

The user approved the isolated right-upper-head V3 topology reference on
2026-08-08 after visual review. It preserves all `42` source components and
exact bounds, removes only four redundant vertices within a `0.00001 mm` weld
contract, and deterministically triangulates them. All `42/42` FreeCAD Parts
and the non-unioned validation compound are closed, valid, and pass Part-level
self-intersection checks. Both head-tab roots exceed `80 mm3`. The existing A
panel-side tab still overlaps the repaired head by `1.3988 mm3` and remains
held for a later connector-adjustment bucket. The ear reference, full
motion/access validation, holes, integration, mirror, and printing remain
held.

The user visually approved the isolated right-ear V1 topology reference on
2026-08-08 with “LGTM.” It preserves all `177` source vertices at exactly `0.0 mm`
displacement, both existing source components, and the exact source bounds.
Both component Parts and their non-unioned compound are closed, valid, and
pass Part-level self-intersection checks. The inherited components overlap by
`185.0521 mm3` and remain separate by contract. The ear has no volumetric
interference with the approved panel, upper head, or four A/B connector tabs;
it touches the upper head at inherited source seams and clears the panel by
`0.0761 mm`. The inherited two-component overlap remains unresolved. Mirror, integration,
connector adjustment, holes, aluminum changes, fabrication export, slicing,
and printing remain held.

The isolated right A panel-tab V3 local-relief shape is ready for visual
review. It preserves the approved A anchor, A head tab, `0.300 mm` pair gap,
both B tabs, panel, upper head, ear, and all frozen workstreams. A `1.9 mm`
C001 cutter sweep removes `23.87 mm3` only from the A panel tab, producing
`0.4039 mm` upper-head clearance while retaining `81.4577 mm3` panel-root
overlap. The existing future M3 datum does not retain the required edge
material; a `0.12 mm` inward datum shift passes as feasibility evidence but is
not part of this shape proposal. User approval, the separate hole bucket, B-tab
clearance, integration, mirror, aluminum, fabrication, slicing, and printing
remain held.

## Folder map

- `output/00-current-review/`: the single review currently awaiting user
  approval. Review files are placed directly here.
- `output/10-design-gates/`: Gate 1 through Gate 8 historical design outputs,
  test prints, shells, eye modules, and glow-panel work.
- `output/20-rear-cassette/current-baseline-v5/`: accepted lossless rear-cassette
  repartition used by later reinforcement work.
- `output/20-rear-cassette/history/`: rejected or superseded rear-cassette seam,
  cut, and repartition iterations.
- `output/30-reinforcement-baselines/`: accepted reinforcement baselines and
  their historical ownership/interface reviews.
- `output/40-prototypes/`: independent fabrication experiments.
- `output/50-eye-mount-reviews/`: completed, accepted, or superseded eye-mount
  reviews retained for traceability.
- `output/60-ear-root-reviews/`: isolated ear-root constraints and redesign
  reviews retained independently from eye and aluminum work.
- `output/70-freecad-pilots/`: tightly scoped reference-only FreeCAD pilots.
  These are not integrated CAD baselines or print releases.

## Current decision state

The C001+C003 copied complete-left-owner integration was visually approved on
2026-08-10 with `LGTM - they look similar`; HS-08 is closed. The current active
review is HS-11 V16 right-side owner integration. V15 is rejected because its
legacy upper-head context was incomplete and displayed empty/floating sectors.
V16 reconstructs the right context from complete and hash-locked owners. Its
Blender eye-owner proof passes as one closed manifold component; FreeCAD
already validated the upper- and lower-head owner fusions. Final FreeCAD import
and OCCT validation of the integrated eye OBJ remain pending after the GUI
Boolean crash. No left mirror, export, or print release has occurred.

The requested reinforcement additions were reviewed as “much better” on
2026-08-05. That acceptance applies only to the reinforcement direction; it is
not authorization to print or modify aluminum.

The eye-mount V3 structural-layout baseline was accepted on 2026-08-06: four
broad-base flange candidates per side, covering outer head, outer eye, lower
head, and lower eye. It remains unintegrated review geometry, not a print
release.

The accepted ear-root V2 coverage and V3 fit envelope remain archived under
`output/60-ear-root-reviews/`. V3 preserves the accepted `13/9 mm` saddle
relief, `2.5/1.0 mm` body/cap clearances, and `0.4 mm` exact-ear clearance.

V4, V5, and V6 remain rejected. V6 is preserved at
`output/60-ear-root-reviews/ear-root-standard-paired-flange-review-v6-rejected-exterior-protrusion/`.

V7 established the accepted conceptual direction of two plain internal
rectangular tabs, but was incomplete: it contained only one connector set total
and its roots were too small. It is archived at
`output/60-ear-root-reviews/ear-root-internal-rectangular-flange-placement-review-v7-concept-approved-needs-more-sets-and-stronger-roots/`.

V8's two-set concept was accepted and is archived under
`output/60-ear-root-reviews/ear-root-dual-set-reinforced-rectangular-flange-review-v8-concept-accepted-spacing-superseded-before-holes/`.

V9's screw-hole concept was accepted, but its placement is archived under
`output/60-ear-root-reviews/ear-root-wide-spaced-m3-through-bolt-review-v9-screw-hole-concept-accepted-placement-superseded-by-marked-relocation/`.

The current V10 review implements the user's marked move: the unmarked set is
retained, while the crossed set is relocated to the adjacent forward seam on
both translucent pieces. It has four connector sets and eight plain
`22 × 12 × 4 mm` tabs total with a `0.3 mm` gap. The two centers are
`45.115 mm` apart on each side, versus `36.9166 mm` in V9 and `34.9211 mm` in
V8. The final point is `1.9 mm` inward from the exact corner-mark projection so
the weakest left shell root remains above the `80 mm³` gate.

Every orange/green pair now has one common `3.4 mm` M3 clearance axis: four
fastener paths and eight drilled tab holes total. A `3.2 mm` gauge clears all
four paths, and minimum modeled bore-to-edge material is `4.05 mm`. Intended
hardware is four internal M3 × 16 through-bolts, two 7 mm OD washers per bolt,
and one M3 nyloc per bolt. Hardware is specified but not modeled.

Every actual left/right owner root is proven by a direct Boolean intersection.
The minimum overlap volume is `80.1945 mm³`; all four green roots are
`106.7–112.4 mm³`. Both moving translucent-piece/two-tab composites are manifold.
Actual seated geometry and both 41-sample motion paths are clear. The
conservative `0.4 mm` expanded moving-tab envelopes touch the upper heads and
their intentionally mated green tabs at the seated sample, so tolerance and
physical tool access remain review holds.

Flat single-color exterior occupancy masks are pixel-identical from front,
left, right, and top. Exact Gate 8 meshes and the accepted V3 fit bodies remain
unchanged.

C006 and all aluminum plate/rail geometry remain deferred, preserved, and tied
to `CAT-HEAD-SHELL-ALUMINUM-V0.5`.

## Organization rule

Keep only one active review directly in `00-current-review`. When a later
review becomes current, first move the completed review into its workstream
folder and update its checkpoint and generator paths. Do not delete or reuse
rejected geometry merely to make the directory smaller.
