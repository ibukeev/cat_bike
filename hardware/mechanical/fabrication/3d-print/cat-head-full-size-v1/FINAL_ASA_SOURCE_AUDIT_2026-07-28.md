# Cat Head Final-ASA Source Audit and Work Slices

**Date:** 2026-07-28  
**Status:** Gate 1 source audit complete; no CAD regeneration performed  
**Traceable baseline:** commit `02053c43b5cae639965d5b13c66fff3f1dcb6bb3`
on branch `agent/cat-head-fabrication-checkpoint`  
**Recommended corrective output namespace:**
`output/gate9-coordinated-asa-candidate-v1/`

## 1. Outcome

The next work must not begin with isolated eye, ear, glow-panel, or rear-pad
repairs. The Gate 5 / Gate 8 generation foundation can currently export many
closed but disconnected bodies as one STL, while the Gate 8 acceptance block
does not require a production shell to contain exactly one connected
component. This allowed the stored report to treat physically unprintable or
fragile assemblies as acceptable.

The safe order is:

1. preserve this source baseline and reject stale generated evidence;
2. freeze one shared aluminum/shell interface revision;
3. compare the rear-cassette/moved-seam, retained-partition, and smallest-useful
   scale variants using the complete aluminum envelope;
4. fix the single-body generation and validation contract;
5. implement the selected partition and then correct subsystems in dependency
   order; and
6. release full ASA only after digital checks and full-scale interface coupons.

## 2. Authority and scope

This audit is subordinate to:

- `hardware/mechanical/CAT_HEAD_MOUNT_AND_SHELL_PHYSICAL_FIT_REVIEW_2026-07-28.md`
  for findings F-01 through F-29 and acceptance tests A-01 through A-39;
- `hardware/mechanical/CAT_HEAD_SHELL_ALUMINUM_REAR_INTERFACE_CONTROL_2026-07-28.md`
  for shared interface decisions C-001 through C-007; and
- `hardware/mechanical/CAT_HEAD_FINAL_ASA_RELEASE_CHECKLIST_2026-07-28.md`
  for the final release sequence.

This was a read-only CAD/source audit. No Blender generator, renderer,
PrusaSlicer export, or metal fabrication command was run.

## 3. Generated-output provenance

| Artifact | File time | Relevant source/config time | Disposition |
|---|---:|---:|---|
| Gate 3 BLEND | 2026-07-28 15:08 | Gate 3 generator 15:11 | **Stale.** The generator is newer, so Gate 8's own dependency rule would rebuild it. |
| Standalone Gate 5 BLEND/report | 2026-07-20 00:33 | Gate 5 config 2026-07-28 15:04; generator 15:11 | **Stale.** It represents the older 18 mm inward rear frame and M3 rail scheme. |
| Gate 8 `_stage5-structural` BLEND/report | 2026-07-28 09:09 | Gate 5 and Gate 8 sources/configs 15:04–15:11 | **Stale.** It contains no `rear_m5_screw_count` and reports the obsolete rear scheme. |
| Gate 8 review BLEND, report, and shell STLs | 2026-07-28 09:10 | Gate 8 config/source 15:04 | **Stale.** They predate both the rear-base and portal revisions. |
| Aluminum V0.2 review BLEND | 2026-07-28 09:37:34 | Aluminum generator 09:37:31 | Current review artifact, but **review-only** and not a cutting release. |

No existing Gate 8 STL, BLEND, validation JSON, render, 3MF, or G-code is an
approved input or acceptance result for the final-ASA candidate. Existing
physical-test artifacts remain valuable evidence and must not be deleted.

## 4. Source-change classification

### Retain as coordinated design intent

- The frame-fixed, no-weld aluminum V0.2 architecture.
- Full-size approved exterior as the primary target; do not shrink globally
  before the architecture comparison.
- Lower rail targets at head X `±40`, Y `267.336`, Z `147.132` mm for the first
  coordinated comparison.
- V0.2 rail pitch `17.662°`, yaw `5.595°`, and head-X-projected socket roll.
- Rear installation/service from behind rather than an undercut rear part that
  must be trapped during shell assembly.
- Fail-fast component inspection and the saved failure-debug BLEND concept.

These values must move into one shared machine-readable interface revision;
their current duplication between shell and aluminum configs is not a valid
freeze.

### Retain only as prototype code requiring rework

- Gate 3's configurable outward rear-frame direction. It is useful for rear
  comparison geometry, but the present 5 mm frame is not an approved final
  rear cassette or load path.
- Gate 5's rear-loaded pad experiment. The design intent addresses F-04, but
  its failed regeneration means the geometry has not passed union, collision,
  insertion, bearing-area, or tool-access validation.
- Gate 8's dependency-triggered Gate 3 rebuild. Timestamp checks are helpful,
  but production provenance also needs a source/interface revision embedded in
  every report.

### Correct before the next production-candidate regeneration

1. `join_closed_overlapping_mesh()` explicitly performs Blender object join,
   not a geometric union. The docstring says it keeps separate watertight
   meshes in one STL. That behavior is incompatible with A-34.
2. Gate 8 records `connected_components`, but its acceptance dictionary never
   requires exactly one component per production shell.
3. The stored Gate 8 report records:
   - `left_lower_face`: 61 components;
   - `right_lower_face`: 63 components;
   - `left_upper_head`: 41 components;
   - `right_upper_head`: 42 components; and
   - each ear: 2 components.
4. Manifold-edge checks alone are insufficient: multiple separate closed
   bodies can each be manifold while still floating, detaching, protruding, or
   colliding.
5. The current component regression check compares against the already-loaded
   baseline component count rather than requiring one final connected body.
6. Gate 8 hard-codes rear pad dimensions `[28, 30, 10]` mm while the current
   Gate 5 / Gate 8 configuration specifies `[28, 36, 10]` mm.
7. Current orientation acceptance checks only rotated bounding-box fit. It does
   not include brim, supports, Prusa exclusion zones, support efficiency, or a
   minimum XY boundary margin.
8. The stored lower-face bounding-box ratios are `0.969185` left and `0.970400`
   right. Those values confirm the user's observation that the existing
   partition is too close to the bed limit even before brim/support clearance.
9. Stale reports contain acceptance names and values from the obsolete 18 mm
   inward rear base. They must not be merged with current-source results.

## 5. Traceable starting state

The corrective work starts at commit
`02053c43b5cae639965d5b13c66fff3f1dcb6bb3`. The committed Gate 3 / Gate 5 /
Gate 8 source changes are preserved for reference; none is silently reset.

For the corrective iteration:

- source history begins at that commit;
- physical findings F-01 through F-29 remain authoritative;
- existing Gate 8 outputs are comparison evidence only;
- new review and candidate outputs go under
  `output/gate9-coordinated-asa-candidate-v1/`; and
- no old Gate 8 output is overwritten during comparison or validation.

## 6. Work slices and review boundaries

### Slice 1 — Shared-interface freeze

Create one versioned JSON authority consumed by both shell and aluminum
generators. It must contain the rear plane, backplate outline/thickness,
adapter pattern, lower targets, rail axes, socket roll, M4 paths, actual rail
stock dimensions, and installation direction.

**User input needed:** caliper measurements of the purchased rail outside
width, outside height, wall thickness, usable length, and corner radius if it
can be measured. Record alloy/temper only if known.

**Review boundary:** inspect the JSON diff and a numeric interface report. Do
not regenerate shared shell or metal geometry until both sessions reference
the same revision identifier.

### Slice 2 — Rear architecture comparison

Using the approved exterior and the complete V0.2 aluminum/hardware envelopes,
produce three review-only candidates:

1. retained current partition;
2. the smallest global reduction that materially improves real slicer margin;
3. unchanged-scale rear cassette / moved rear seam.

Report part count, real bed margin with brim, supported volume, supported
finished-exterior area, print time, seam length, assembly sequence, service
access, and every metal/shell collision.

**Review boundary:** user selects scale, partition, rear seam, and service
sequence. No eye, ear, or glow-panel detail is rebuilt before this choice.

### Slice 3 — Generation and validation foundation

Replace append-only joins with dependable Boolean unions or equivalent
single-body construction. Add hard failures for:

- production-shell connected component count other than one;
- unintended exterior protrusion;
- shell-to-shell seated or insertion-path collision;
- floating islands and unsupported first extrusion;
- insufficient brim/support bed margin; and
- interface revision mismatch.

**Review boundary:** run the validators first on the known-bad Gate 8 exports
and prove they fail for the correct reasons, then on a minimal synthetic good
coupon and prove it passes.

### Slice 4 — Global shell and rear system

Implement the selected partition/rear cassette, aluminum clearances, rear
attachment, wiring/drainage, upper sockets, and saved production orientations.

**Review boundary:** complete digital assembly plus shell/aluminum collision
matrix and review renders. Print only rear/interface and socket coupons.

### Slice 5 — Dependent subsystems

Correct in this order:

1. body seams and complementary reinforcement;
2. eyes and their shell interfaces;
3. ears and under-ear inserts;
4. glow-panel skirts and retention; and
5. wrapped mirror-panel landing clearances.

Each subsystem gets a small full-scale coupon or local interface print before
the complete head is released.

### Slice 6 — Final ASA release

Run A-01 through A-39, save final PrusaSlicer projects, inspect layer previews,
and release the black-ASA set only when the final checklist has no open blocker.

## 7. Validation performed for this audit

- Verified the Git worktree was clean at the audit start.
- Inspected the exact committed Gate 3 / Gate 5 / Gate 8 source and config
  changes relative to the parent commit.
- Compared source/config and generated-artifact modification times.
- Inspected the stored Gate 5 and Gate 8 validation schemas and results.
- Confirmed the stored Gate 8 connected-component counts listed above.
- Confirmed the stored lower-face orientation ratios listed above.
- Confirmed the aluminum V0.2 review BLEND is newer than its tracked generator
  and remains the current review-only metal artifact.
- Did not treat any stale validation `true` value as current evidence.

## 8. Rejected or unsafe shortcuts

- Do not start by patching the visible eye or ear failures one at a time.
- Do not accept slicer auto-union as the structural topology contract.
- Do not overwrite Gate 8 outputs during the corrective comparison.
- Do not globally scale the complete head without a full interface and slicer
  comparison.
- Do not move the rails inward independently; the X `±35` check left only about
  1.044 mm before shoe, hardware, tolerance, and tool envelopes.
- Do not release the current 5 mm outward frame / six-pad experiment as final.
- Do not cut or drill aluminum while the shared interface is provisional.

## 9. Exact current regeneration commands — recorded, not executed

These reproduce the current tracked generators only after the applicable hold
is lifted. They are not final Gate 9 release commands:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate3_structural_shells.py
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate5_ribs_and_joints.py
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate8_full_size_iteration.py
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/render_gate8_review.py
blender --background --python hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/source/generate_frame_fixed_mount_v0.py
```

The Gate 9 generator/render/validation commands must be added here when those
versioned scripts exist, before any production-candidate output is generated.

## 10. Next physical-review steps

1. Measure the actual purchased aluminum rail stock.
2. Continue reviewing
   `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/output/review-model/frame-fixed-mount-v02-review.blend`
   and record any visible plate, shoe, rail, hardware, or tool-access concern.
3. Review the three rear-architecture comparison renders and slicer metrics.
4. Approve one architecture before detailed corrective CAD begins.
5. Print full-scale rear-interface and upper-socket coupons before any complete
   ASA shell section.

