# Post-PLA issue closure checklist V2

This is the execution checklist for the physical problems reported after the
full-size PLA assembly. It preserves the original `F-01` through `F-29` IDs
from `hardware/mechanical/CAT_HEAD_MOUNT_AND_SHELL_PHYSICAL_FIT_REVIEW_2026-07-28.md`.

**Release state: HOLD.** No unchecked item is implied to be fixed by an old
isolated review, a numerical pass, or a visually reasonable V34 baseline.

## Controlled baseline

- Canonical recovery assembly: V34.
- Baseline manifest:
  `source/cad-change-control/v2/approved-baseline-v34.json`.
- V34 is a recovery baseline, not print-ready geometry.
- Previous review files are evidence only. Do not copy their objects into V34.
  Reproduce an accepted correction as a bounded V2 operation on the current
  canonical baseline.

## How to close one item

For the one active finding, complete every applicable step before checking its
top-level box:

- [ ] Confirm the failure, or the accepted correction, in the current canonical
      assembly using fixed whole-assembly and focused views.
- [ ] Identify one exact FreeCAD target object and one exact operation.
- [ ] Approve a V2 iteration contract with a unique iteration ID.
- [ ] Generate one candidate from the canonical baseline; do not retry or repair.
- [ ] Pass independent non-target preservation comparison.
- [ ] Receive explicit user visual approval of the candidate hash.
- [ ] Pass the applicable independent geometry, topology, assembly, and slicer
      checks.
- [ ] Pass the applicable real hardware, hand-fit, service, or structural test.
- [ ] Record the evidence and only then check the finding below.

If a finding needs several object changes, use several serial V2 iterations.
The finding remains unchecked until the complete physical acceptance condition
passes.

## A. Rear shell and aluminum interface

- [ ] **F-01 — Rail path blocked by shell.** Prior digital route is frozen;
      V34 presence and real insertion are unproven. Close with A-05, A-38, and
      A-39.
- [ ] **F-02 — Portal axis does not match the rail axis.** Pitch, yaw, roll, and
      targets have prior digital evidence; verify the same revision in V34 and
      with actual 19.05 mm rails. Close with A-05 and A-38.
- [ ] **F-03 — Existing lamp/steering interference.** Still open because the
      measured lamp, beam, cable, and steering envelopes are missing. Close
      with A-06.
- [ ] **F-04 — Rear base cannot install without cutting.** Lossless rear-cassette
      V5 was an accepted direction only. Integrate a rear-loaded cassette around
      the aluminum envelope and close with A-01, A-02, and A-39.
- [ ] **F-05 — Backplate holes too close to corners.** Inward hole placement has
      digital evidence; real bolt, washer, nut, finger, and tool access remain
      unproven. Close with A-03 and A-39.
- [ ] **F-06 — Rear mounting flanges too small/flimsy.** Final cassette-owned M5
      structural pads are not complete. Close with A-04 and A-39.

## B. Under-ear insert and ear attachment

- [ ] **F-07 — Under-ear insert upper-corner collisions.** V3 relief direction
      was accepted digitally; verify it exists in V34/future canonical geometry
      and pass the real hand-fit test. Close with A-07.
- [ ] **F-08 — Under-ear insert lower-center collision.** Prior insertion-path
      evidence exists, but final reinforced-shell fit is open. Close with A-07.
- [ ] **F-09 — Under-ear insert globally too snug.** Prior deep-body/cap clearance
      direction exists; final material tolerance and hand fit are open. Close
      with A-07 and A-08.
- [ ] **F-10 — Plane mismatch and lateral sliding under clamp load.** Bilateral
      A/B owner reviews were accepted, but presence in V34 and physical seating
      behavior must be confirmed. Close with A-08 and A-09.
- [ ] **F-11 — One long connector over-constrains the insert.** Separated A/B
      retention direction was accepted; full-context and physical retention are
      open. Close with A-10.
- [ ] **F-12 — Under-ear flange access and weakness.** Hole/tool paths and broad
      roots have accepted digital evidence; exact production orientation,
      hardware installation, and strength remain open. Close with A-18.
- [ ] **F-13 — Outer ear flaps.** Anti-flap layout direction exists, but the final
      full-context joint and physical hand-load result are open. Close with A-11.
- [ ] **F-14 — Outer ear grounding point through the insert.** Accepted direction
      must be verified in the canonical assembly and tested without loading the
      diffuser skin as a primary structure. Close with A-11 and A-12.
- [ ] **F-22 — Ear interface has pin against pin.** The bilateral two-bolt
      round-hole/slot CAD was visually approved in primary-ear V2 and HS-09, but
      it must be confirmed in the canonical full context and physically mated
      with specified M3 hardware. Close with A-27.

## C. Central, nose, and side glow panels

- [ ] **F-15 — Central-panel back skirt collides internally.** Exact V34 owner and
      collision faces are still unidentified. Preserve the continuous skirt,
      add only local relief, and close with A-13 and A-14.
- [ ] **F-16 — Central panel flaps with only two upper connectors.** Add a broad,
      lower retention point on the correct vertical nose-side owner after exact
      owner selection. Close with A-15, A-16, and A-17.
- [ ] **F-17 — Front nose-panel skirt interferes and connector detached.** Exact
      owner selection remains open. Keep the skirt non-structural and use two
      broad-rooted connectors. Close with A-19 and A-20.
- [ ] **F-18 — Side-panel skirt collides and single connector is weak.** Confirm
      the side and exact owner first; relieve all affected corners and use two
      broad-rooted connectors. Close with A-21 and A-22.

## D. Eye socket, module, and cap

- [ ] **F-19 — Eye collides with multiple internal elements.** V34 visibly has a
      known eye/shell conflict. Audit the complete insertion and seated envelope
      before choosing the first target. Close with A-23 and A-31.
- [ ] **F-20 — Eye-to-head retention lacks an upper connection.** Prior flange
      layouts exist, but final head-owner integration, access, and strength are
      open. Close with A-24 and A-25.
- [ ] **F-21 — Both eye rear-cap connectors were lower.** Bilateral V9 records an
      accepted upper/lower layout; confirm it is present in the canonical
      geometry and physically serviceable. Close with A-26.
- [ ] **F-23 — Eye front frame was a disconnected floating island.** Prior V9
      one-solid bucket evidence is accepted, while the canonical and eventual
      production export must independently pass connected-body and slicer-layer
      checks. Close with A-28 and A-29.
- [ ] **F-24 — Eye head-mount tab was a fragile interfering cantilever.** A broad
      base direction was accepted and C002 remains rejected; final canonical
      integration and service testing are open. Close with A-31 and A-32.
- [ ] **F-28 — Eye bezel separated from the chamber.** Prior full-thickness wall
      continuation evidence exists; verify the canonical owner, true union, and
      physical joint strength. Close with A-30.

## E. Whole-shell systemic failures and fabrication

- [ ] **F-25 — Internal features protrude through the exterior.** Run an exterior
      deviation audit on every canonical shell owner, then correct one offending
      target per iteration. Close with A-33 and A-36.
- [ ] **F-26 — Shell exports contain many disconnected parts.** Build explicit
      production owners without loose or duplicate solids. Close with A-34.
- [ ] **F-27 — Opposing reinforcements collide across seams.** Assign
      complementary seam ownership and validate real assembly paths. Close with
      A-35.
- [ ] **F-29 — Lower shells lack usable build-plate margin.** Repartition without
      changing the approved exterior scale and validate the actual brim/support
      job. Close with A-37.

## Recommended execution order

1. Audit V34 object ownership and the exact presence of previously accepted
   ear and eye corrections; do not mutate geometry.
2. Close the eye workstream one finding at a time, beginning with F-19's visible
   eye/shell interference.
3. In parallel, perform read-only aluminum/rear measurements for F-01 through
   F-06; integrate those geometry changes serially.
4. Verify and finish the ear/under-ear findings, reusing old reviews only as
   dimensional and visual evidence.
5. Resolve F-15 through F-18 after selecting the exact panel owners and
   collision regions.
6. Close the systemic owner, exterior, seam, and bed-fit findings F-25 through
   F-27 and F-29.
7. Run the full physical acceptance set before any structural ASA release.

## Active item

- [ ] **Current:** F-19 read-only V34 eye/socket conflict audit.
- [ ] Exact target object selected.
- [ ] First mutation contract approved.

