# Cat Head Final ASA Candidate Release Checklist

**Date:** 2026-07-28
**Status:** Draft execution checklist; awaiting physical-feedback closure and
rear-architecture decision
**Target:** One production-candidate black-ASA structural head set for the
Prusa MK4S, followed by full physical acceptance before riding

## 1. Authority and scope

This is the execution and go/no-go checklist for the next full structural
print. It consolidates, but does not replace:

- `hardware/mechanical/CAT_HEAD_MOUNT_AND_SHELL_PHYSICAL_FIT_REVIEW_2026-07-28.md`
  — authoritative findings F-01 through F-29 and tests A-01 through A-39;
- `hardware/mechanical/CAT_HEAD_SHELL_ALUMINUM_REAR_INTERFACE_CONTROL_2026-07-28.md`
  — authoritative shared shell/aluminum interface and decisions C-001 through
  C-007; and
- the relevant Gate 3, Gate 5, Gate 8, mirror-panel, and aluminum resumable
  checkpoints.

Checking an item here does not override a more specific acceptance condition
in either authority document. This checklist does not itself authorize CAD
regeneration, metal cutting, or a full ASA print.

## 2. Current decisions and holds

- [x] Use black ASA for the final opaque structural head shell.
- [x] Retain the overall frame-fixed, no-weld V0.2 aluminum architecture.
- [x] Keep the lower rail targets at X `±40` for the first coordinated shell
  revision.
- [x] Keep printed polymer out of the primary bike-connector load path.
- [x] No aluminum plate has been ordered or cut; only rectangular rail stock
  has been purchased.
- [x] Treat current Gate 8 generated outputs and pre-correction upper-head
  G-code as potentially stale or obsolete.
- [x] Do not regenerate while physical feedback remains open.
- [ ] User explicitly declares the physical-feedback pass complete.
- [ ] User selects the rear-shell architecture for the next version.

**Recommended rear-shell choice:** preserve the approved full head scale and
evaluate a rear-loaded cassette/moved rear seam around the V0.2 aluminum
envelope. Do not accept the existing difficult lower-face orientation as the
production solution. Use global scaling only if a documented slicer comparison
shows that a genuinely small reduction solves the problem without compromising
the complete interface set.

## 3. Gate 0 — Close requirements and freeze the shared interface

- [ ] Confirm there are no additional physical defects to record.
- [ ] Select rear cassette/moved seam, retained partition, or uniform scaling.
- [ ] Record the selected architecture in the interface-control change log.
- [ ] Physically measure purchased rail outside width, wall thickness, length,
  corner radius, straightness, and alloy/temper if known.
- [ ] Freeze one shared interface revision containing:
  - rear plane center and normal;
  - aluminum-backplate outline and thickness;
  - adapter-to-backplate hole pattern;
  - lower rail targets and axes;
  - upper socket pitch, yaw, roll, depth, and M4 retention path;
  - rail stock dimensions; and
  - intended assembly and service direction.
- [ ] Give that revision one identifier used by both shell and aluminum
  validation reports.
- [ ] Confirm that neither session is about to order, cut, drill, or regenerate
  shared-interface parts independently.

**Gate 0 pass:** feedback is closed, rear architecture is selected, actual rail
stock is measured, and both sessions share one frozen interface revision.

## 4. Gate 1 — Recover and freeze a trustworthy source state

- [ ] Inventory every current Gate 3, Gate 5, and Gate 8 uncommitted change.
- [ ] Map each retained change to one or more findings F-01 through F-29.
- [ ] Identify the source/config revision and command that produced every
  existing STL, BLEND, report, render, and G-code intended for comparison.
- [ ] Mark outputs with unknown or mismatched provenance as stale; do not use
  them as regeneration inputs or acceptance evidence.
- [ ] Review the incomplete rear-base work and failed regeneration without
  resetting or discarding user/session changes.
- [ ] Select one traceable source baseline for the corrective iteration.
- [ ] Select a new versioned output location for the final-ASA candidate so
  Gate 8 physical-test artifacts remain available for comparison.
- [ ] Record exact generation, rendering, validation, and slicing commands in
  the resumable checkpoint before geometry edits begin.

**Gate 1 pass:** every retained source change and comparison output has known
provenance, and the corrective iteration starts from one traceable state.

## 5. Gate 2 — Lock the global shell and rear architecture

- [ ] Import the accepted V0.2 aluminum review geometry and unchanged approved
  exterior shell into one integration assembly.
- [ ] Generate a collision map for aluminum plate, adapter hardware, lower
  shoes, rails, upper sockets, rear base, and all adjacent shells.
- [ ] Produce review-only comparisons for:
  - existing lower-face partition and difficult orientation;
  - smallest useful uniform scale reduction; and
  - rear cassette/moved rear seam at unchanged exterior scale.
- [ ] For each comparison, report shell part count, bed margin including brim,
  support volume, print time, seam count, assembly order, service access, and
  aluminum-interface changes.
- [ ] User approves the selected exterior scale, shell partition, rear seam,
  rear service opening, and assembly sequence.
- [ ] Verify that the selected rear module itself fits the MK4S bed in a stable,
  support-efficient orientation.
- [ ] Preserve X `±40` lower rail targets unless the collision study proves a
  coordinated rail/plate/socket change is required.

**Gate 2 pass:** the shell architecture is approved visually and mechanically,
and every production section has a credible print orientation before detailed
connectors or reinforcement are added.

## 6. Gate 3 — Repair the geometry-generation foundation

- [ ] Replace append-only overlapping structural meshes with true dependable
  unions or an equivalent single-body construction.
- [ ] Reject every production STL with more than one connected component unless
  a removable part is deliberately exported separately.
- [ ] Retain closed-manifold, boundary-edge, and nonmanifold-edge checks.
- [ ] Add finished-exterior deviation checks against the approved clean faceted
  baseline.
- [ ] Clip all ribs, gussets, pads, flange roots, and connectors to the interior
  envelope before union.
- [ ] Add complete seated-state and insertion-path collision checks.
- [ ] Add slicer checks for floating islands, unsupported first extrusions,
  brim/support boundary fit, and saved production orientation.
- [ ] Fail generation when any required check fails; no report-only warnings
  for production blockers.

**Gate 3 pass:** validation can no longer accept the disconnected, protruding,
colliding geometry classes seen in the PLA prototype.

## 7. Gate 4 — Correct every subsystem

### 7A. Rear shell and aluminum interface

- [ ] Rear structure installs from behind after the main shells are joined.
- [ ] No rail, plate, shoe, bolt, washer, nut, tool, or insertion envelope
  intersects the ASA rear structure or adjacent shells.
- [ ] Backplate holes have real bolt, washer, nut, finger, and tool clearance.
- [ ] Structural pads have broad shell roots and adequate bearing area.
- [ ] Wiring and drainage paths are defined and remain serviceable.
- [ ] Upper sockets match the frozen V0.2 rail axes and socket roll.
- [ ] Requirements A-01 through A-06 and A-38 through A-39 pass digitally.

### 7B. Main shell seams, reinforcement, and exterior

- [ ] Opposing shell reinforcements have complementary non-overlapping
  envelopes.
- [ ] Every shell pair closes to its intended gap without cutting, melting,
  bending, or force.
- [ ] No internal connector or reinforcement protrudes through an exterior or
  mirror-cap landing plane.
- [ ] Each body-shell export is one connected printable component.
- [ ] Requirements A-33 through A-36 pass digitally.

### 7C. Lower-face printability

- [ ] Lower-face or replacement sections use a stable orientation with required
  brim and support entirely inside the printable area.
- [ ] At least 10 mm remains to each XY printable boundary after required brim,
  unless the user approves a different margin from a physical printer test.
- [ ] Support volume, print time, supported exterior area, and removal access
  are reviewed before release.
- [ ] Requirement A-37 passes in the saved PrusaSlicer project.

### 7D. Eyes

- [ ] Eye front frame, bezel, chamber, and structural roots form one dependable
  connected body.
- [ ] No front-frame feature begins as a floating printable island.
- [ ] Remove the long thin eye-mount cantilever and use short broadly rooted
  supported attachments.
- [ ] Eye installs and removes without colliding with any shell, reinforcement,
  glow panel, skirt, fastener, or tool envelope.
- [ ] Retain the eye at separated upper and lower locations.
- [ ] Place one eye back-plate connector high and one low.
- [ ] Requirements A-23 through A-26 and A-28 through A-32 pass digitally.

### 7E. Ears and under-ear insert

- [ ] Replace opposing printed ear pins with two accessible M3 bolt paths using
  one round clearance hole and one tolerance slot.
- [ ] Under-ear insert clears both upper corners and lower center and seats by
  hand without scraping or bending.
- [ ] Insert planes align before fastener tightening and do not slide under
  clamp load.
- [ ] Use two or three short tolerance-friendly retention points.
- [ ] Enlarge and broadly root under-ear flanges with direct hardware/tool
  access.
- [ ] Add the outer anti-flap ear tie without loading an illuminated region.
- [ ] Requirements A-07 through A-12, A-18, and A-27 pass digitally.

### 7F. Glow panels and skirts

- [ ] Preserve useful light-control skirts while relieving every real shell,
  reinforcement, corner, flange, and fastener collision.
- [ ] Central panel has at least three separated retention points, including a
  strong lower connection on the vertical nose-side structure.
- [ ] Front nose-side and side panels each use two larger connectors broadly
  rooted into the panel body, not the skirt.
- [ ] All fasteners and tools remain accessible in the documented sequence.
- [ ] Requirements A-13 through A-22 pass digitally.

## 8. Gate 5 — Digital production-candidate release

- [ ] All findings F-01 through F-29 have an implemented disposition.
- [ ] All acceptance tests A-01 through A-39 have recorded digital results.
- [ ] Every production STL is single-component, closed manifold, and free of
  unintended internal loose bodies.
- [ ] Complete assembly and insertion collision matrices report zero unintended
  intersections.
- [ ] Exterior-deviation report shows zero unintended positive protrusions.
- [ ] Review renders show exterior, interior, seams, eyes, ears, glow panels,
  rear cassette, rails, backplate, hardware, tools, and service sequence.
- [ ] Every production STL has a named saved PrusaSlicer orientation.
- [ ] Slicer preview contains no floating islands or unsupported first
  extrusions.
- [ ] Required brim and supports fit on the bed with the approved margin.
- [ ] Support volumes, print times, filament estimates, and supported visible
  areas are documented.
- [ ] User approves the review package before any full structural part is
  printed.

**Gate 5 pass:** the complete digital candidate is approved and only targeted
physical coupons are authorized.

## 9. Gate 6 — Full-scale physical coupons before the full ASA set

- [ ] Actual rail in revised upper-socket coupon: insertion, clearance, rattle,
  drilling, M4 retention, bridge quality, and removal.
- [ ] Rear interface coupon: aluminum plate, rail pass-through, lower shoe,
  representative ASA structure, M5/M6 hardware, and tool access.
- [ ] Representative upper/lower shell seam coupon: closure, reinforcement
  clearance, round/slot alignment, and fastener access.
- [ ] Ear two-bolt round/slot coupon.
- [ ] Eye bezel/chamber/frame coupon: print continuity and hand-load strength.
- [ ] Under-ear retention and corner-clearance coupon.
- [ ] Representative glow-panel skirt/connector corner coupon.
- [ ] Black-ASA exterior and mirror-cap landing coupon.
- [ ] PETG cap to black-ASA adhesion coupon using selected 3M 9474LE/300LSE:
  surface preparation, 72-hour dwell, heat exposure, and peel/shear check.
- [ ] Repeat or revise every failed coupon; do not waive a failure because the
  full print is expensive or time-sensitive.

**Gate 6 pass:** all high-risk interfaces pass at full scale in production
materials with actual stock and hardware.

## 10. Gate 7 — Final ASA print authorization

- [ ] Black ASA is received, dry, and qualified on the enclosed MK4S.
- [ ] Build sheet, adhesive/release practice, enclosure, ventilation, nozzle,
  and slicer profile are documented and proven by the coupons.
- [ ] All exact fasteners, rails, inserts/nuts, washers, and tools are on hand.
- [ ] Final STLs, 3MFs, validation reports, renders, BOM, and assembly sequence
  share the same version identifier.
- [ ] No source/config file is newer than the released STL/3MF/report package.
- [ ] No known stale G-code is present in the release package.
- [ ] Print the smallest or least expensive structural section first and verify
  dimensions before starting the longest lower/upper section.
- [ ] Inspect every completed part before authorizing the next expensive print.

**Gate 7 pass:** user authorizes the versioned production-candidate ASA print.

## 11. Gate 8 — Physical assembly and ride release

- [ ] Complete shell assembles with no cutting, melting, bending, or forced
  fastener alignment.
- [ ] Eyes, ears, inserts, glow panels, mirror caps, rear cassette, rails, and
  backplate install and remain serviceable in the documented order.
- [ ] All seams close and exterior mirror-panel seats remain clean.
- [ ] Complete head mounts to the bike without steering, lamp, beam, cable,
  control, or rider-sightline interference.
- [ ] Independent metal safety tether is installed.
- [ ] Stationary multidirectional proof load passes with no slip, crack, creep,
  permanent deformation, or fastener movement.
- [ ] Vibration test and progressive low-speed rides pass before normal use.

The first ASA print is a production candidate, not ride approval. Gate 8 must
pass before the assembly is treated as final.

## 12. Exact next step

The next step is **Gate 0**, not CAD regeneration.

The user must confirm:

1. the physical-feedback pass is complete; and
2. the rear cassette/moved-rear-seam direction at unchanged head scale is
   approved for the comparison study.

After those confirmations, the shell session performs Gate 1 as a read-only
audit, then produces the Gate 2 collision and printability comparison package.
No production geometry is edited until the audit establishes a trustworthy
source baseline and the aluminum session confirms the same interface revision.

## 13. Resume checkpoint

Current review files:

- `hardware/mechanical/CAT_HEAD_MOUNT_AND_SHELL_PHYSICAL_FIT_REVIEW_2026-07-28.md`
- `hardware/mechanical/CAT_HEAD_SHELL_ALUMINUM_REAR_INTERFACE_CONTROL_2026-07-28.md`
- `hardware/mechanical/CAT_HEAD_FINAL_ASA_RELEASE_CHECKLIST_2026-07-28.md`

Accepted decisions are recorded in Section 2. No corrective CAD, STL, G-code,
or metal fabrication change was made while creating this checklist.

Next physical-review action: finish any remaining observations, declare the
feedback pass closed, and approve or reject the recommended rear-cassette
comparison direction.
