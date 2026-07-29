# Cat Head Shell / Aluminum Rear Interface Control

**Date:** 2026-07-28
**Status:** V0.4-M2 ordered-angle aluminum handoff generated for shell integration;
receipt, coupon, shell reintegration, fabrication, and riding release gates remain held
**Integration authority:** User

## 1. Purpose

This document coordinates the separate cat-head shell and aluminum-mount work
sessions. It is the authority for geometry or behavior shared by those two
workstreams. It does not replace either workstream checkpoint:

- Shell defects and required validation:
  `hardware/mechanical/CAT_HEAD_MOUNT_AND_SHELL_PHYSICAL_FIT_REVIEW_2026-07-28.md`
- Aluminum V0.4-M2 ordered-angle interface state:
  `hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/V04_M2_ORDERED_ANGLE_CHECKPOINT_2026-07-29.md`

The aluminum V0.4-M2 files are the tracked handoff authority. The shell session must consume but not edit the aluminum-owned config, generator, summary, or checkpoint. The aluminum session must not edit Gate 3,
Gate 5, or Gate 8 shell sources while their existing partial state is under
review.

## 2. Coordination rule

No session may independently change or release a shared-interface parameter.
A proposed change must be recorded here with its affected shell and metal
files, reviewed in both workstreams, and approved by the user before either
session regenerates shared geometry or releases material for fabrication.

This coordination freeze is not a fabrication approval. It preserves a common
reference while the physical-feedback pass remains open.

## 3. Workstream ownership

| Area | Primary workstream | Coordination requirement |
|---|---|---|
| Bike boss plate, side webs, compact adapter, metal tether | Aluminum mount | May not move the head rear plane without shared approval. |
| Aluminum head backplate and lower angle connectors | Aluminum mount | M2 owns the retained plate centers, angle bases, uprights, cheeks, plugs, taper pads, compound rail cuts, and lower M5 stack; the shell must consume their exact envelope. |
| Exterior head shape, shell partitioning, reinforcement, mirror-panel seats | Printed shell | Must preserve the coordinated rear plane and rail system unless a shared change is approved. |
| Upper/front printed rail sockets and M4 retention paths | Shared | Must be generated from the same rail-axis and socket-roll revision as the aluminum backplate and rails. |
| Rear ASA frame, rear shell facets, removable rear cassette | Printed shell | Proposed architecture only; attachment and load transfer are shared. |
| Backplate perimeter fasteners, rail pass-throughs, wiring, drainage, tool access | Shared | Neither session may finalize independently. |
| Final assembly and service sequence | Shared | Must be validated with complete shell, aluminum, rail, fastener, and tool envelopes. |

## 4. Retained shared geometry baseline

The following values are the current V0.2 coordination baseline. They are
frozen against unilateral changes but remain review-only and are not released
for cutting:

**Active aluminum integration review artifact:**
`hardware/mechanical/fabrication/metal/cat-head-frame-fixed-mount-v0/output/review-model/frame-fixed-mount-v02-review.blend`

The user is currently reviewing this BLEND and confirmed that the aluminum
work remains review-only. No physical backplate has been ordered or cut. The
parallel aluminum work began under the assumption that the printed ASA rear
structure would not be redesigned; that assumption is now explicitly open
because physical findings F-04 and F-29 require a rear-interface and
printability correction.

The user accepts the overall V0.2 aluminum architecture as the direction to
retain. This is concept acceptance, not a cutting release. The current printed
ASA rear base conflicts with that metal envelope and must be revised. Possible
movement of the lower rail targets toward center remains TBD.

| Interface parameter | Provisional baseline |
|---|---|
| Mount architecture | Frame-fixed, no weld, and no printed polymer in the primary bike-connector load path. |
| Head coordinate bounds | X `-151.915..151.915`, Y `0..269.345`, Z `0..330` mm. |
| Rear interface plane center | Head coordinates `[0, 264.01125, 171.74025]` mm. |
| Rear interface outward normal | `[0, 0.990996, 0.133894]`. |
| Rear-plane mating pitch | `-18.894665°` relative to the estimated boss plane. |
| Aluminum head backplate | 3 mm 6061 trapezoid; 60 mm top, 120 mm bottom, 79.663819 mm high. |
| Adapter-to-backplate pattern | Four 6.6 mm paths at X `±22` mm and local V `±20` mm. |
| Internal rail stock | Nominal 19.05 mm square aluminum tube. |
| Lower rail targets | Head coordinates `[-40, 267.336, 147.132]` and `[40, 267.336, 147.132]` mm. |
| Rail orientation | Pitch `17.662°`, yaw `5.595°`; upper M4 axes approximately `5.333°` from head-horizontal. |
| Upper retention | One transverse M4 bolt per blind printed upper socket. |

Any need to change one of these values must be raised here before either model
is edited.

### 4A. Lower rail-target inward-shift assessment

At the current lower target, local backplate V is approximately `-24.832` mm
and the trapezoid half-width is approximately `54.351` mm. With a 19.05 mm
tube centered at X `±40`, the nominal tube/pass-through envelope leaves about
`4.826` mm to the sloped plate edge. The nearest lower 6.6 mm adapter-hole
center is about `18.637` mm away.

Moving a rail center to X `±35` improves nominal edge clearance to about
`9.826` mm, but reduces center distance to the lower adapter hole to about
`13.869` mm. The raw tube half-width plus M6-hole radius already consume about
`12.825` mm of that distance, leaving only about `1.044` mm before accounting
for the rail shoe, bolt head, washer, nut, manufacturing tolerance, or tool
access.

Therefore a simple inward shift is not approved. The user accepted X `±40` as
the baseline for the first coordinated ASA rear-structure revision. If rail
movement is still needed after full collision review, optimize rail X/V
position, adapter holes, backplate outline, lower-shoe envelope, and upper
socket axes as one shared interface change.

## 5. V0.4-M2 closed and open shared interfaces

The user ordered Randall Manufacturing `1.5 x 1.5 x 0.125 inch` 6063-T6
equal angle and authorized the aluminum workstream to incorporate it without
changing the accepted rail axes, X `+/-40` targets, 21 mm sockets, backplate
outline, adapter holes, or six-plus-six M5 plate-hole centers. The M2 authority
is `hardware/mechanical/interfaces/cat-head-shell-aluminum-interface-v04.json`
and the M2 checkpoint dated 2026-07-29. No plate is ordered or cut. The angle
is ordered but not yet received or measured.

Closed for shell integration, but not released for fabrication:

1. six backplate-to-shell M5 centers: local X/V `(-10,30)`, `(10,30)`,
   `(-20,0)`, `(20,0)`, `(-10,-30)`, and `(10,-30)` mm;
2. six angle-base M5 centers, three per side, using right centers `(36,-30)`,
   `(47.4,-30)`, `(38,-9)` mm and mirrored left X;
3. one 45 mm primary angle per rail with full 38.1 mm upright and 29 mm
   trimmed base, plus one `45 x 25 x 3.175 mm` outer cheek per rail;
4. a matched 14.7 mm nominal solid plug, two hand-fit aluminum taper pads, and
   two M5 x 40 lower crossbolts per rail at 14 and 29 mm from the compound
   bearing centerline;
5. rail centerline length `152.476123 +/-0.25 mm`, 160 mm rough cuts,
   compound edge range `147.0677..157.8845 mm`, and upper M4 station
   133.776123 mm from the lower bearing datum; and
6. no backplate rail cutout and no external shell pass-through; service remains
   through the open rear aperture.

The M1 monolithic CNC shoes and 149.672 mm square-ended rails are superseded.
The generator plate-local V basis was also corrected to match the shared
interface; the earlier reversed M1 visualization must not be used for shell
integration.

Still open and held:

1. receipt inspection of the ordered angle's leg widths, thickness, inside
   radius, straightness, and alloy/temper marking;
2. actual rail inside dimensions/corner radii and fitted-plug machining;
3. one physical rear-interface/angle coupon proving flush countersinks,
   compound bearing contact, taper pads, M5 access, clamp behavior, and repeatable
   assembly;
4. shell/rear-cassette and six ASA pad integration around the exact M2 metal
   and tool envelope, followed by complete A-39 validation;
5. rear cassette seam, overlap, sealing, removal, wiring, and drainage;
6. actual headlight housing, beam, steering, and cable clearance; and
7. tether, proof-load, vibration, and progressive ride validation.

The regenerated M2 collision matrix records no intersection between the nine
checked metal parts and the current V6.1 fixed shells, bezel, or bottom keel.
This is a useful baseline, not a shell release: any new shell revision must
preserve or improve that clearance and rerun the complete assembly/service
matrix.

## 6. Rear cassette proposal C-001

**Status:** Proposed for coordinated evaluation; not accepted and not modeled.

To correct physical-fit findings F-04 and F-29 without shrinking the complete
head, evaluate a removable rear cassette that:

- moves the lower-face shell seams forward and transfers the aft shell facets
  to a rear-loaded printed module;
- incorporates or attaches to the shallow printed rear frame around the
  aluminum backplate;
- preserves the current rear plane, adapter hole pattern, and rail targets if
  practical;
- installs and removes from behind after the front and side shells are joined;
- makes each lower-face STL comfortably printable with its required brim and
  supports;
- leaves the aluminum backplate and rail structure as the primary mount load
  path; and
- treats the exterior rear facets as replaceable shell/finish parts rather
  than primary bike-mount structure.

The preferred implementation is not a permanent fusion of cosmetic ASA to the
aluminum plate. It is a mechanically attached printed rear module that may be
removed with, or separately from, the aluminum backplate according to the
approved service sequence.

## 7. Required comparison before accepting C-001

After the user closes the feedback pass, compare at least these three variants
without releasing fabrication:

| Variant | Required evidence |
|---|---|
| Existing lower-face partition and difficult rotation | Saved PrusaSlicer orientation, brim/support footprint, support volume, print time, and surface-risk review. |
| Uniform head scale reduction | Smallest scale that creates an acceptable orientation, plus impact on every mount, fastener, eye, insert, panel, and rear-plane interface. |
| Rear cassette / moved seam | Lower-face and cassette bed margins, support volumes, complete assembly collision test, backplate/rail integration, and service sequence. |

Acceptance of a variant requires the user to review the exterior appearance,
assembly sequence, printer evidence, and aluminum-interface impact together.

## 8. Shared release gates

No rear-interface metal or replacement structural shell is released until:

1. the user declares the physical-feedback pass complete;
2. both workstreams use the same rear-plane and rail-target revision;
3. the full shell and aluminum assembly has zero collision through insertion,
   seated, fastened, and removal states;
4. the rear cassette or retained partition passes the complete build-plate test
   in A-37;
5. all backplate, angle-connector, cassette, washer, nut, and tool envelopes are validated;
6. a physical rear-interface and angle-connector coupon passes;
7. actual headlight and steering clearance is validated;
8. an independent metal safety tether is specified; and
9. the stationary proof-load, vibration, and progressive ride-test plan is
   approved.

## 9. Cross-session change log

| ID | Date | Proposal or change | Status | Affected workstreams |
|---|---|---|---|---|
| C-001 | 2026-07-28 | Evaluate rear-loaded cassette incorporating aft shell facets to improve lower-face printability and rear service. | Proposed; no CAD action | Shell and aluminum |
| C-002 | 2026-07-28 | Use `frame-fixed-mount-v02-review.blend` as the active aluminum integration-review artifact. | User review in progress; no fabrication approval inferred | Shell and aluminum |
| C-005 | 2026-07-28 | Record aluminum fabrication commitment state: no plates ordered; only rectangular aluminum rail stock purchased. | Confirmed by user; rail dimensions still require physical verification | Shell and aluminum |
| C-003 | 2026-07-28 | Preserve the V0.2 aluminum rear-plane pose, plate outline, adapter pattern, and rail targets where practical while redesigning the printed ASA rear structure around that baseline. | Preferred coordination target; integrated validation required | Shell and aluminum |
| C-004 | 2026-07-28 | Rebuild the upper/front printed sockets to the coordinated V0.2 compound rail axes and socket roll; do not reuse pre-correction upper-shell G-code. | Required shared correction; regeneration held until feedback closes | Shell and aluminum |
| C-006 | 2026-07-28 | Retain the overall V0.2 aluminum architecture and redesign the conflicting printed ASA rear base/shell around its complete envelope. | Concept accepted by user; interface details and fabrication remain open | Shell and aluminum |
| C-007 | 2026-07-28 | Keep lower rail targets at X `±40` for the first ASA rear redesign; evaluate inward movement only if the complete collision review still requires it, including adapter-hole, backplate-edge, shoe/tool, upper-socket, and shell impacts. | Accepted baseline; conditional study deferred | Shell and aluminum |
| C-008 | 2026-07-29 | Authorize the aluminum workstream to finalize lower shoes, anti-crush paths, rail cut/drill stations, and backplate perimeter/shoe holes from V0.4 without changing the 21 mm socket geometry. | Authorized and completed as V0.4-M1 | Aluminum, then shell integration |
| C-009 | 2026-07-29 | Adopt the V0.4-M1 six-plus-six plate pattern and CNC-shoe handoff. | Superseded by C-010 before metal fabrication | Shell and aluminum |
| C-010 | 2026-07-29 | Use the ordered Randall 38.1 x 38.1 x 3.175 mm 6063-T6 angle for hand-fabricated M2 lower connectors; retain the six-plus-six plate centers, frozen axes/targets/sockets, add compound-cut 152.476123 mm rails, solid plugs, taper pads, outer cheeks, and matched M5 x 40 crossbolts. | M2 digital preflight passed; angle ordered but not received; no plate ordered or cut; coupon and shell A-39 pending | Aluminum, then shell integration |

## 10. Next synchronization action

No backplate is ordered or cut. The rectangular 19 x 19 x 2 mm rail stock is
purchased. The Randall 6063-T6 equal angle is ordered but not received; its
actual section remains a receipt gate.

The next synchronization action is for the shell workstream to consume the
V0.4-M2 shared JSON, tracked summary, checkpoint, BLEND, and complete angle,
cheek, spacer, plug, rail, and hardware envelope before changing the rear
cassette, bezel, or six ASA pads. It must rerun A-39 after that integration and
must not alter the plate-hole centers, compound rail cut datums, accepted
axes/targets, or 21 mm sockets independently.

When the angle arrives, the aluminum workstream records the received dimensions
before cutting even a coupon. Final plate or bracket cutting remains held until
the receipt inspection, shell integration review, and physical angle-interface
coupon plan are accepted.
