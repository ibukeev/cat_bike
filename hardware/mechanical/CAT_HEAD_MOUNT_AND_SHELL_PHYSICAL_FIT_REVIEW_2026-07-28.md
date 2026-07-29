# Cat Head Mount and Shell Physical-Fit Review

**Review date:** 2026-07-28
**Status:** Open — physical feedback collection in progress; corrective CAD and
regeneration on hold
**Review basis:** Physical bike measurements, bike photographs, printed-part test
fitting, and direct user feedback
**Affected designs:** Gate 8 full-size cat head and frame-fixed aluminum bike
mount V0.2

## 1. Purpose

This document is the formal source of truth for the user’s feedback on the
current cat-head body shells, seams and reinforcement, rear base,
under-left-ear translucent insert, ear attachment, glow panels, eye assemblies,
and bike connector. It distinguishes measured inputs from observed physical
failures and from proposed engineering responses. This merged revision records
findings F-01 through F-29 and acceptance tests A-01 through A-39.

No affected STL, G-code, or fabrication drawing is approved for another
production print or metal cut until the user closes the feedback pass and the
applicable acceptance tests in Section 11 pass.

## 2. Accepted interface decisions and measured inputs

| ID | Requirement or measurement | Status |
|---|---|---|
| D-01 | The cat head is frame-fixed and does not rotate with handlebar steering. | Accepted |
| D-02 | A purchased front rack is not required. The frame connector may be custom manufactured. | Accepted |
| D-03 | Retain the existing fork-mounted front light; relocation is not assumed. | Accepted |
| D-04 | Use a no-weld aluminum mount. | Accepted |
| D-05 | Head-tube boss pattern is 30 mm horizontal center-to-center and 90 mm vertical center-to-center. | User measured |
| D-06 | Boss outside diameter is 18 mm. | User measured |
| D-07 | Available bolt dimension under the head is 14 mm. | User measured |
| D-08 | Raise the head approximately 60 mm relative to the earlier concept to clear the existing light. | User direction; final lamp-envelope check still required |

## 3. Bike-to-head connector feedback

### F-01 — Rail path is blocked by the head shell

**User observation:** The proposed rails cannot connect to the front/top head
portals because the plastic shell lies in the path.

**Failure:** The concept showed a load path that was not physically insertable
through the finished shell.

**Required correction:** The rail/socket interface must be accessible from
inside the shell or through a deliberately modeled opening. The finished shell
must not require cutting to reach or install the rail ends.

### F-02 — Portal axis is not aligned with the conceptual rail axis

**User observation:** The portal angle is visibly unusual and must be rotated or
explicitly accounted for.

**Failure:** A nominal straight or orthogonal rail assumption does not match the
actual portal direction.

**Required correction:** Derive and document the socket pitch and yaw from the
head geometry. Validate rail insertion along the complete socket axis, not only
at the endpoint. The final upper/front sockets must match the coordinated V0.2
aluminum baseline: lower rail targets at head X `±40`, Y `267.336`, Z `147.132`
mm, rail pitch `17.662°`, yaw `5.595°`, and socket roll that leaves the M4 axes
approximately `5.333°` from head-horizontal. These are shared interface values
and may not be changed by the shell or aluminum session independently.

**Output-state warning:** Gate 8 source contains the V0.2 portal revision, but
the current source/configuration are newer than the generated upper-shell STLs.
Upper-head G-code produced before the socket-axis and roll correction is
explicitly obsolete. No existing STL or G-code is approved as the final shared
portal geometry until both sessions regenerate and validate from one frozen
interface revision.

### F-03 — Existing light interference

**User observation:** The earlier head/mount concept interfered with the front
light.

**Required correction:** Preserve the existing light and raise the head by
roughly 60 mm as the initial correction. Final approval requires a measured
three-dimensional light-housing envelope and steering-sweep check.

## 4. Rear base and aluminum backplate feedback

### F-04 — Rear base is not installable without cutting printed material

**User observation:** Flanges and reinforcement connecting the upper and lower
head sections blocked the rear base. Printed material had to be cut away to
install it. The later full-shell assembly confirmed the same failure:
`rear_base.stl` collided with surrounding reinforcement and could not seat
until reinforcement material was cut away.

**Severity:** Blocking.

**Failure:** The rear base was modeled as a deep undercut component whose
installation sequence conflicts with the already assembled shell and internal
reinforcement.

**Required correction:** The rear base must load from the rear after the four
main body shells are assembled. Installation and removal must not require
cutting, bending, or destructive modification of the shell, flanges, or ribs.
The complete rear-base insertion sweep must include all adjacent shell
reinforcement, not only the nominal rear opening.

**Cross-session update:** The user accepts the V0.2 aluminum mount concept but
observes that its backplate/rail assembly conflicts with the current printed
rear base and may conflict with adjacent shell geometry. The printed ASA rear
structure must be redesigned around the coordinated aluminum envelope. Moving
the lower rail targets inward remains a shared TBD and is not an approved
substitute for correcting the shell.

### F-05 — Horizontal backplate holes are too close to corners

**User observation:** The holes in the horizontal pieces are too close to the
corners, preventing the bolt from being fitted. This clearance problem had been
reported previously and must not recur.

**Severity:** Blocking.

**Failure:** Hole-center placement was checked geometrically but not against the
real bolt-head, washer, nut, finger, and tool envelope.

**Required correction:** Move the lower horizontal attachment holes away from
the corners and validate the complete hardware/tool envelope. The current
engineering response moves the lower pair from `x = ±30 mm` to `x = ±15 mm`;
this remains subject to physical-fit approval.

### F-06 — Rear-base mounting flanges are too small and flimsy

**User observation:** The mounting flanges are too small to place a nut and are
too weak for a primary structural connection.

**Severity:** Blocking and structural.

**Failure:** The original tabs did not provide adequate bearing area, nut
seating area, washer clearance, wrench/socket access, or load distribution.

**Required correction:** Replace the small tabs with large structural pads
sized around the actual fastener and tool envelope. The current engineering
response uses six rear-loaded M5 paths, a minimum 14 mm nut/tool envelope, and
nominal 28 × 36 × 10 mm shell-side pads. These dimensions are provisional until
CAD validation and a physical coupon pass.

## 5. Under-left-ear translucent insert feedback

**Likely affected part:** `glow_insert_left_ear_root_cluster.stl`, also described
in the print set as the left under-ear panel. Confirm against the physical part
label or a photo before releasing a replacement print.

### F-07 — Upper corner collisions

**User observation:** Both corners of the translucent piece fight shell
material, including reinforcement.

**Failure:** The insert perimeter and/or hidden return occupies the same volume
as the shell rim, reinforcement, or flange-root geometry.

**Required correction:** Add explicit local relief at both reported corner
regions and validate the insert against the final reinforced shell, not against
the nominal exterior surface alone.

### F-08 — Lower-center collision

**User observation:** The lower center of the translucent piece also fights the
head.

**Failure:** The lower insert body, cap, flange, or connector does not have a
valid insertion/seating path.

**Required correction:** Add local lower-center relief and verify the complete
insertion sweep. The visible illuminated area should be preserved where
possible, but assembly clearance takes priority over a hidden overlap.

### F-09 — Insert is globally too snug

**User observation:** The translucent piece is too snug to the head and cannot
be seated reliably.

**Failure:** Nominal CAD clearance does not cover printed-part tolerance, shell
distortion, reinforced-edge variation, and the non-planar insertion path.

**Required correction:** Increase the deep-body perimeter clearance while
keeping any tight visual seam limited to a shallow, non-structural cap. Do not
use force-fitting as the assembly method.

### F-10 — Plane mismatch and lateral sliding under flange clamping

**User observation:** When the connecting flanges are brought together, the
overall planes of the translucent piece do not align with the rest of the head
and the part slides to one side. The lower part appears misaligned and fights
the head.

**Severity:** Blocking.

**Failure:** The current retention geometry over-constrains a multi-plane part
and converts fastener clamping into lateral displacement/twist.

**Required correction:** The seated exterior planes must be defined by broad,
repeatable datum surfaces. Fasteners must retain the already seated part rather
than pull it into position. Add lead-in and lateral tolerance so tightening
cannot cam the insert sideways.

### F-11 — One long connector over-constrains the insert

**User observation:** Two or three smaller connectors would be preferable to
one connector that prevents force fitting.

**Required correction:** Replace any continuous or long constraining connector
with two or three short, spatially separated retention points. Each point must
permit assembly tolerance; together they must prevent rattle without forcing
the insert out of plane.

### F-12 — Under-ear flange access and structural weakness

**User observation:** The under-ear connecting flanges are difficult to access
with the bolt and are too flimsy.

**Failure:** A nominally aligned fastener hole is not sufficient when the bolt,
washer, nut, fingers, or installation tool cannot approach and engage it. The
small flange body and narrow shell connection also create a likely flexing and
breakage point.

**Required correction:** Enlarge the under-ear flange body, connect it to the
main printed piece with a broad continuous root, and reposition the fastener as
needed to provide a direct installation path. Validate the complete bolt,
washer/nut, hand, and tool-access envelope against the final reinforced shell.

## 6. Left ear attachment feedback

### F-13 — Outer ear remains unsupported and flaps

**User observation:** After the main connecting flanges are screwed together,
the outside portion of the ear flaps and appears partly disconnected.

**Failure:** The existing ear flange concentrates restraint near one region and
does not control rotation at the outer ear root.

**Required correction:** Add a small, separated anti-flap connection near the
outer edge of the under-ear translucent region.

### F-14 — Requested outer grounding point through the under-ear insert

**User request:** Add a relatively small connector to the semi-transparent
piece to ground the ear on the outer side, because adding another direct
connection to the main head shell is difficult.

**Engineering interpretation:** Add a reinforced hidden lug beneath the opaque
border of the translucent insert and a matching short tab inside the ear shell,
retained by one internal M2.5 bolt with washers and a nyloc nut. This is an
anti-flap locator only; the primary ear loads must remain on the larger M3 ear
flange connection. The illuminated 1.5 mm diffuser skin must not be treated as
the primary structural load path.

## 7. Central glow-panel feedback

**Affected part:** Central translucent/glowing panel, including its continuous
rear skirt and shell-side retention features.

### F-15 — Continuous back-skirt collides with the head interior

**Positive feedback:** Adding a continuous rear skirt is a good design
direction because it closes the former holes/gaps.

**User observation:** The skirt fights the head interior, including
reinforcement pieces and other surrounding shell material. Installation
required cutting both the printed head and the skirt.

**Severity:** Blocking.

**Failure:** The back-skirt was evaluated as an isolated panel feature rather
than against the final reinforced head and its real insertion path. A
closed-manifold or visually gap-free result does not establish physical
installability.

**Required correction:** Preserve the useful continuous back-skirt concept, but
reshape and locally relieve it against the final shell, reinforcement, flange,
and fastener geometry. Validate the entire insertion sweep and final seated
position. Installation must not require cutting either the head or the panel.

### F-16 — Two upper connecting flanges do not prevent panel flapping

**User observation:** The central panel has only two connecting flanges at the
top and remains free to flap.

**Failure:** Two retention points concentrated along the same upper region do
not adequately constrain the lower portion of the panel.

**Required correction:** Add at least one spatially separated lower retention
point. The preferred location is the lower vertical piece near the nose. The
adjacent horizontal piece is too small and must not be used merely for
geometric convenience.

**Engineering interpretation:** The additional point should retain an already
seated panel rather than pull it into shape. Its flange, nut/washer area, tool
access, and surrounding shell clearance must be checked against the final
reinforced assembly.

**Additional structural requirement:** Make the new flange substantially larger
and connect it to the main printed piece through a broad, continuous root. It
must not be a small cantilevered tab or depend on a narrow neck.

**Failure risk:** An undersized or weakly rooted flange is likely to crack or
tear away during tightening, vibration, panel movement, or repeated service.

## 8. Front nose-side glow-panel feedback

**Affected part:** Front translucent/glowing panel near the nose. Confirm the
exact STL identifier against the physical part before revising or releasing a
replacement.

### F-17 — Skirt interference and immediate connector detachment

**Positive feedback:** The rear-skirt concept is useful and should be preserved
because it closes unwanted openings and light gaps.

**User observation:** The skirt does not physically fit the surrounding head
geometry. The attachment is also flimsy and detached almost immediately.

**Severity:** Blocking and structural.

**Failure:** The connector load appears to enter through a thin skirt or another
weak secondary feature rather than the main structural body of the glow panel.
The skirt is simultaneously over-sized for its available internal envelope and
under-strength for use as an attachment root.

**Required correction:** Treat the skirt only as a non-structural light-control
feature. Root the attachment geometry directly into the main structural body of
the glow panel. Use two larger, spatially separated connectors instead of one
small or weakly rooted connector.

**Fit requirement:** Reshape and locally relieve the skirt against the complete
final head, reinforcement, flange, and fastener geometry. Validate both the
insertion path and final seated position without cutting or force-fitting.

**Structural requirement:** Each connector must have a larger load-bearing body
and broad continuous root into the main glow-panel structure. Connector
tightening must not bend, peel, or load the skirt.

## 9. Side glow-panel feedback

**Affected part:** Side translucent/glowing panel. The exact side and STL
identifier must be confirmed against the physical part before revision.

### F-18 — Single weak connector and skirt collision around the perimeter

**User observation:** The side glow panel has one flimsy connector. Its skirt
fights the head around all corners and collides with reinforcement and flange
geometry.

**Severity:** Blocking and structural.

**Failure:** One small attachment point does not adequately constrain the panel
or distribute service loads. The skirt was not validated against the complete
internal corner, reinforcement, flange, and fastener envelope.

**Required correction:** Use two larger, spatially separated connectors rooted
directly into the main structural body of the side glow panel. The skirt must
remain non-structural. Add local relief at every affected corner and around all
reinforcement and flange regions.

**Validation requirement:** Check the complete insertion path and final seated
position against the finished reinforced shell. The panel must install without
cutting, scraping, bending, force-fitting, or using connector tension to pull it
into position.

## 10. Eye socket and eye back-plate feedback

**Affected parts:** Eye socket/module, its head-side mounting flanges, and its
back plate/rear cap. Confirm the eye side and exact STL identifiers against the
physical parts before revision.

### F-19 — Eye assembly collides with multiple internal head elements

**User observation:** The eye fights multiple elements inside the head and
cannot be installed without severe cutting.

**Severity:** Blocking.

**Failure:** The eye was not validated against the complete final internal
assembly or through its real insertion path. Shell reinforcement, flange roots,
glow-panel skirts/connectors, or other internal features occupy the required
installation and seated envelopes.

**Required correction:** Validate the complete eye assembly, not only its visible
front boundary, against every final internal head feature. Reshape or relocate
the conflicting hidden features and verify a non-destructive insertion path.
Installation must not require cutting the eye or head.

### F-20 — Eye-to-head retention lacks an upper connection

**Positive feedback:** The existing lower connecting flange is acceptable in
principle.

**User request:** Enlarge the lower flange for improved strength and add a
separate connection between the upper side of the eye and the head.

**Failure:** A lower-only attachment leaves the upper eye edge free to separate,
rotate, or flap. An undersized lower flange also concentrates load at its root.

**Required correction:** Retain the lower attachment location but enlarge its
load-bearing body and structural root. Add a spatially separated upper
eye-to-head connector with usable fastener and tool access. The connectors must
retain an already seated eye rather than pull it through interference.

### F-21 — Both eye back-plate connectors are on the lower side

**User observation:** The eye back plate is connected by two connectors, but
both sit on the lower side.

**Required correction:** Relocate one of the two back-plate connectors to the
top so the back plate is retained at separated upper and lower positions. Keep
both connectors attached to structurally substantial portions of the eye
module, with usable fastener and tool access.

**Failure risk:** Two lower connectors provide poor rotational and peel
restraint at the top of the back plate even when both fasteners are tight.

## 10A. Additional full-size PLA shell findings from the active review

The following findings merge the physical feedback captured in the active
full-size PLA assembly review. They are requirements only; they do not
authorize regeneration while the user is still providing feedback.

### F-22 — Ear connector presents printed pin against printed pin

**User observation:** On the printed left-side ear connection, both mating
parts carry male alignment pins. Assembly therefore presents pin against pin
rather than pin into a receiving hole.

**Severity:** Blocking.

**Failure:** The two sides of the interface are not complementary. No print
tolerance or assembly force can make two opposing solid pins occupy the same
space.

**Required correction:** Remove the printed alignment pins and use two
accessible M3 bolt paths through the mating flanges. Use one nominal 3.4 mm
round clearance hole and one short nominal 3.4 × 5 mm tolerance slot, subject
to a printed coupon, so the joint is constrained without over-constraining
normal print variation. Use washers and either locking nuts or captive threaded
hardware. Audit the mirrored ear interface before release.

### F-23 — Eye front frame is a disconnected printable island

**User observation:** The top/front eye frame disintegrated during printing.
PrusaSlicer preview showed the front frame disconnected from the rest of the
eye bucket and beginning in mid-air.

**Severity:** Blocking and printability-critical.

**Failure:** The STL can be manifold while still containing multiple closed,
disconnected components. The current generation path appends overlapping
objects without creating a true boolean union, and validation did not reject
multiple connected components. Inspection reported six slicer parts for each
of the left and right eye-bucket exports.

**Required correction:** Rebuild the eye bucket as one true geometric union.
The selected print orientation must provide layer-by-layer support from the
build plate into the entire front frame; no front-frame extrusion may begin as
a floating island. Manifold status alone is not an adequate pass condition.

### F-24 — Eye head-mount tab is a long, fragile, interfering cantilever

**User observation:** A thin flying connector on `left_lower_face` immediately
fought the neighboring pieces, had to be cut off to assemble the shells, and
was visibly too flimsy for Burning Man service. The mirrored side must be
treated as suspect until checked.

**Severity:** Blocking and structural.

**Failure:** The head-side eye attachment uses an approximately 21 mm bridge
with a nominal 4 × 2 mm section. It is simultaneously inside the neighboring
assembly envelope and cantilevered far enough to flex or snap under assembly
and vibration loads.

**Required correction:** Remove the long cantilever. Carry the eye load through
a short, broad, supported ledge or flange rooted directly into substantial
shell structure. The complete eye must install and be serviced without cutting
the mount, colliding with adjacent shells, or using a fastener to pull the eye
through interference.

### F-25 — Internal connectors and reinforcement protrude through the exterior

**User observation:** Connector and reinforcement features visibly stick out
on the exterior surface of `left_lower_face`. The same exterior contamination
is present on `left_upper_head`.

**Severity:** Blocking for appearance, mirror-panel fit, and shell assembly.

**Failure:** Geometry intended to remain internal crosses the approved faceted
outer surface. It creates visible bumps and obstructs the landing surface for
wrapped mirror panels. Mathematical offsets in the generator were not
validated against the actual finished exterior mesh.

**Required correction:** Restore the original clean faceted exterior. Clip all
ribs, flange roots, pads, and connectors to the interior envelope before true
union with the shell. Audit the right-side mirror parts as well. No hidden
feature may create an unintended positive deviation on a visible or panel-seat
surface.

### F-26 — Production shell exports contain many disconnected components

**Observed evidence:** PrusaSlicer reported 61 parts in `left_lower_face`, 61
in `right_lower_face`, and 41 in `left_upper_head`. This is consistent with
ribs, gussets, tabs, or pads being appended as separate closed meshes instead
of becoming one printable shell body.

**Severity:** Blocking and systemic.

**Failure:** Existing validation can accept boundary-clean meshes without
checking that each production STL is one connected body. Disconnected internal
objects can print poorly, detach, poke through an exterior plane, or occupy a
mating part envelope.

**Required correction:** Each production shell STL must contain exactly one
connected printable component unless a removable part is deliberately exported
as its own separately named STL. Boolean-union reinforcement into its parent
shell and add connected-component count to generation validation.

### F-27 — Opposing shell reinforcements occupy the same assembly volume

**User observation:** The left lower and left upper shell sections could not be
joined because reinforcement on the opposing shells collided before the
flanges met. Considerable PLA had to be cut or melted away. The rear-base joint
showed the same class of conflict, as recorded in F-04.

**Severity:** Blocking.

**Failure:** Both sides of a mating seam were reinforced independently without
reserving complementary, non-overlapping envelopes for the other side or for
the assembly motion.

**Required correction:** Assign one explicit reinforcement envelope to every
seam and build complementary geometry on the opposite shell. Digitally assemble
every pair and the complete shell at final coordinates, then test both the
seated state and the actual insertion path for collision. No seam may require
cutting, bending, or melting printed structure.

### F-28 — Eye bezel and chamber have an inadequate structural connection

**User observation:** The eye-socket front section separated completely from
the lower chamber/body because the connection surface between them was very
small.

**Severity:** Blocking and structural.

**Failure:** The nominal front bezel is only weakly overlapped with the chamber
geometry and was not made into a dependable continuous union. A tiny local
intersection is not an acceptable structural root even after the floating-part
failure in F-23 is corrected.

**Required correction:** Join the bezel to the chamber with a broad continuous
perimeter shoulder and a true boolean union. Provide enough overlap depth and
root thickness, with fillets or gussets where appropriate, to survive printing,
handling, assembly, and vibration. Validate the joint as both a single
connected body and a physical structural coupon.

### F-29 — Lower-face shell sections leave inadequate build-plate margin

**User observation:** One of the full-size shell pieces barely fit the Prusa
build plate and was extremely difficult to place and print successfully.

**Severity:** Blocking for repeatable fabrication.

**Observed evidence:** The existing automated orientation report marks both
lower-face sections as fitting, but reports a limiting-envelope utilization of
approximately 97.0% for `right_lower_face` and 96.9% for `left_lower_face`.
That binary result does not reserve practical space for the required brim,
supports, placement tolerance, slicer exclusion zones, or a safe distance from
the plate edge.

**Failure:** Printer-envelope validation treated a barely contained bounding
box as a fabrication pass. It did not validate the complete sliced job in its
documented orientation or require a usable XY margin after brim and support
generation. A part that fits only with exact edge placement is not a robust
production part.

**Required correction:** Repartition the affected lower-face shell geometry or
move its structural seam without changing the approved full-head exterior
scale. Every resulting production STL must have a documented PrusaSlicer
orientation in which the complete object, brim, supports, and travel-safe
placement fit comfortably inside the printable area. Target at least 10 mm
clearance from every XY printable-area boundary after the required brim unless
a later physical printer test establishes a different approved margin.

**Cross-session dependency:** A rear-cassette solution would change the shared
shell/aluminum interface and must follow
`hardware/mechanical/CAT_HEAD_SHELL_ALUMINUM_REAR_INTERFACE_CONTROL_2026-07-28.md`.
It is a coordinated proposal, not an accepted CAD change.

## 11. Required acceptance tests

| ID | Acceptance test | Pass condition |
|---|---|---|
| A-01 | Rear-base insertion sweep | Rear base installs from behind after the four body shells are joined, with zero geometric collision and no cutting. |
| A-02 | Rear-base service test | Rear base can be removed without separating the main shell sections or damaging reinforcement. |
| A-03 | Backplate hardware access | Every bolt, washer, and nut can be placed; the intended hand tool can fully engage without corner interference. |
| A-04 | Structural-pad check | Each rear mounting pad is integral to the shell, closed-manifold, and provides the documented bearing and tool clearances. |
| A-05 | Portal/rail insertion | Both rails enter their sockets along the modeled pitch/yaw without intersecting the shell. |
| A-06 | Lamp and steering clearance | Existing light and all steering positions clear the complete head/mount assembly with a documented margin. |
| A-07 | Under-ear insert hand fit | Insert seats by hand without force, scraping, bending, or shell disassembly; both upper corners and lower center remain clear. |
| A-08 | Under-ear plane alignment | All exterior insert planes sit flush with their intended head planes before fasteners are tightened. |
| A-09 | Retention behavior | Tightening retainers does not move the insert laterally, twist it, or pull any plane out of alignment. |
| A-10 | Discrete connector check | Two or three short retention points provide tolerance and stable seating; no single long feature controls the entire fit. |
| A-11 | Ear anti-flap check | With the main ear flange and outer anti-flap tie installed, no visible separation or perceptible outer-edge flapping occurs under normal hand loading. |
| A-12 | Service sequence | Ear and under-ear insert can be installed and removed in a documented, non-destructive order using accessible fasteners. |
| A-13 | Central back-skirt insertion | Complete central panel and skirt install without collision against any final shell, reinforcement, flange, or fastener geometry and without cutting either part. |
| A-14 | Central back-skirt seated clearance | The useful continuous skirt remains intact and gap-closing while maintaining clearance from the reinforced head in its final seated position. |
| A-15 | Central panel retention | At least three spatially separated retention points prevent perceptible flapping without pulling the panel out of alignment. |
| A-16 | Lower nose-side flange access | The additional flange fits on the lower vertical nose-side piece with usable fastener, washer/nut, and tool access; the undersized horizontal piece is not used. |
| A-17 | Retention-flange structural root | The added flange has a large hardware-bearing body and broad continuous connection to the main piece, with no fragile narrow neck. |
| A-18 | Under-ear flange access and strength | Under-ear bolts, washers/nuts, hands, and tools have a direct usable path, and each enlarged flange has a broad structural root into the main part. |
| A-19 | Front nose-side skirt fit | The complete front panel and skirt install and seat without collision, cutting, bending, or force-fitting against the final reinforced head. |
| A-20 | Front nose-side connector retention | Two larger, separated connectors are rooted into the main panel structure; neither connector loads the skirt, and neither detaches or visibly flexes during installation and normal hand loading. |
| A-21 | Side glow-panel skirt fit | The complete side panel and skirt clear every corner, reinforcement, flange, and fastener throughout insertion and in the seated position without cutting or force-fitting. |
| A-22 | Side glow-panel connector retention | Two larger, separated connectors are broadly rooted into the main panel structure; the skirt carries no connector load and the panel does not flap, peel, or detach. |
| A-23 | Eye assembly insertion | The complete eye assembly installs through a verified path and reaches its seated position without colliding with final reinforcement, flanges, skirts, connectors, or other internal features and without cutting. |
| A-24 | Lower eye-flange strength | The enlarged lower flange has a broad structural root, adequate hardware-bearing area, and usable bolt/nut/tool access. |
| A-25 | Upper eye retention | A separated upper connector positively retains the seated eye and prevents upper-edge separation, rotation, or flapping without pulling the eye through interference. |
| A-26 | Eye back-plate retention distribution | The back plate has one upper and one lower structural connector, remains seated under normal hand loading, and provides usable access to both fasteners. |
| A-27 | Ear-interface complementarity | Both ear interfaces mate by hand with no pin-to-pin collision; each uses two accessible bolt paths, one round clearance hole and one tolerance slot, and accepts the specified washers and locking hardware. |
| A-28 | Eye-bucket connected topology | Each left and right eye-bucket production STL contains exactly one connected component after true union. |
| A-29 | Eye print-layer continuity | In the documented print orientation, slicer preview contains no non-bed-connected island or unsupported first extrusion in the front frame; every frame layer is carried by earlier material or deliberately configured support. |
| A-30 | Eye bezel/chamber structural joint | The bezel has a broad continuous union to the chamber and does not crack, peel, or separate during printing, cleanup, normal hand loading, or the documented service test. |
| A-31 | Eye head-mount fit and service | The complete eye installs, seats, fastens, and removes without cutting, bending, or colliding with adjacent shells or reinforcement. |
| A-32 | Eye head-mount stiffness | Eye mount loads are carried by short, broadly rooted, supported features; no long thin cantilever visibly flexes, flaps, or cracks under normal hand loading and the vibration-equivalent coupon test. |
| A-33 | Exterior surface preservation | Every final body shell matches the approved clean faceted exterior with zero unintended outward protrusion from internal reinforcement, pads, connectors, or flange roots. |
| A-34 | Body-shell connected topology | Every production body-shell STL contains exactly one connected printable component; deliberately removable parts are exported as separately named files. |
| A-35 | Complete shell seam closure | Every mating shell pair and the fully assembled shell reach the intended seam gap through the documented assembly path with zero unintended collision and no cutting, melting, bending, or force-fitting. |
| A-36 | Mirror-panel landing surfaces | All wrapped-panel landing faces and adhesive clearances are continuous and unobstructed by internal reinforcement or connector geometry. |
| A-37 | Production build-plate fit | Every production STL has a saved PrusaSlicer orientation in which the complete object, required brim, supports, and placement clear the printable-area boundary by at least 10 mm on every XY side; no scaling, edge overhang, brim reduction, or exclusion-zone override is required. |
| A-38 | Portal/backplate revision lock | Shell and aluminum validation reports identify the same rear plane, lower rail targets, rail axes, socket roll, tube size, and interface revision; both actual 19.05 mm rails pass the printed socket coupon and complete insertion test before upper-shell printing or metal drilling. |
| A-39 | Aluminum/rear-shell integration | The complete aluminum backplate, adapter hardware, lower shoes, rails, bolts, washers, nuts, tools, and installation paths clear the final ASA rear cassette and every adjacent shell in inserted, seated, fastened, and removal states. |

## 12. Proposed corrective direction

The following items are analysis and proposed directions for later approval.
They do not authorize CAD, STL, or fabrication changes:

1. Replace the deep rear undercut frame with a shallow, rear-loaded frame.
2. Use six rear-facing M5 fasteners and substantially larger shell-side
   structural pads.
3. Move the lower horizontal backplate holes inward to improve corner, washer,
   nut, and tool clearance.
4. Preserve the corrected angled rail/socket route through the shell.
5. Increase under-ear insert clearance specifically at both upper corners and
   the lower center.
6. Replace over-constraining insert retention with two or three short,
   tolerance-friendly points.
7. Add one hidden outer ear anti-flap tie at a reinforced, non-illuminated
   insert border.
8. Preserve the central panel continuous back-skirt while relieving it against
   the complete reinforced-head envelope and insertion path.
9. Add at least one lower central-panel retention point on the vertical
   nose-side piece rather than the undersized horizontal piece.
10. Make every new central-panel flange larger and integrate it into the main
    printed piece with a broad structural root.
11. Enlarge and broadly root the under-ear flanges, and provide a direct usable
    bolt and tool-access path.
12. Preserve the front nose-side panel skirt as a non-structural light-control
    feature, relieve it for real assembly clearance, and replace its attachment
    with two larger connectors rooted into the main panel body.
13. Apply the same correction to the affected side glow panel: relieve the skirt
    at all corners, reinforcements, and flanges, and use two larger connectors
    rooted into the main panel body.
14. Clear and validate the complete eye installation envelope against every
    final internal head feature so installation requires no cutting.
15. Enlarge and broadly root the lower eye-to-head flange, then add a separated
    upper eye-to-head connector.
16. Redistribute the two eye back-plate connectors so one is lower and one is
    upper.
17. Replace the opposing printed ear pins with two M3 bolt paths using one
    round clearance hole and one short tolerance slot.
18. Rebuild each eye bucket as a true single-body union and verify both
    connected-component count and layer-by-layer print continuity.
19. Remove the approximately 21 mm cantilevered eye-mount bridges and replace
    them with short, broad, supported seats rooted into substantial shell
    structure.
20. Clip all shell reinforcement to the interior envelope, union it into its
    parent shell, and preserve the approved clean exterior and mirror-panel
    landing faces.
21. Give every mating seam complementary, non-overlapping reinforcement
    envelopes and collision-test each pair plus the complete shell through the
    real assembly sequence.
22. Add generator gates for connected-component count, finished-exterior
    deviation, assembly collision, and slicer floating islands, backed by small
    physical fit and structural coupons.
23. Repartition the lower-face shells as necessary so the unchanged full-size
    exterior prints with a documented brim-and-support-inclusive bed margin,
    rather than merely passing a bounding-box containment test.
24. Rebuild the upper/front rail sockets from the same frozen interface revision
    as the aluminum V0.2 backplate and rails, then validate the actual tube and
    cross-bolt geometry with a coupon before releasing upper-shell prints.
25. Preserve the accepted V0.2 aluminum architecture while redesigning the ASA
    rear structure around its complete envelope. Treat any lower rail-target
    movement as a coordinated optimization with the adapter holes, backplate
    edge, shoe hardware, upper sockets, and shell clearances.

## 13. Release hold

The current four body-shell sections, rear base, backplate, ear interfaces,
central glow panel, front nose-side glow panel, affected side glow panel, eye
socket/module and back plate, under-left-ear insert, and left-ear attachment
outputs must be treated as superseded test artifacts. Do not regenerate,
reprint, or fabricate replacements until:

1. the user explicitly confirms that this physical-feedback pass is complete;
2. the revised CAD passes every applicable geometric, topology, collision,
   exterior-surface, and slicer check above;
3. review renders clearly show all changed interfaces and clean exterior faces;
4. small fit and structural coupons validate the rear hardware envelope,
   under-ear retention, ear bolt interface, eye joint, and shell seams; and
5. the user approves the resulting physical fit.

## 14. Traceability to direct user feedback

- “Back base plate and flanges connecting top and bottom head … are … blocking.
  I needed to cut them to install base.”
- “Base plate holes — horizontal pieces — they are too close to the corner. I
  can’t fit the bolt.”
- “Flanges to mount to base plate — they are too tiny/flimsy. I can’t put a nut
  there. Also there is the structural connection. Make these flanges larger.”
- “Under the left ear semi-transparent piece … I cannot fit it.”
- “Corners are fighting some head shell material (reinforcement, etc.).”
- “Same fighting in lower center.”
- “Overall planes of the piece do not align with the rest of the head and it is
  sliding off to one side.”
- “The semi-transparent [piece] is too snug … it would be much better to have
  2–3 connectors instead of one.”
- “When I screw connecting flanges, outside part of the ear [is] flapping and a
  bit disconnected.”
- “Can we add a relatively small connector to the semi-transparent piece to
  ground the ear on the outer side?”
- “Central [glowing] panel — it is a great idea to add back-skirt; there are no
  holes, but it fights with the head [and] some reinforcement pieces.”
- “I needed to cut the head again [and] cut this back-skirt. We need to make
  sure that this skirt actually fits.”
- “There are only two connecting flanges on the top — it is flapping.”
- “We need to add at least one more connecting flange, ideally on the lower
  vertical piece near the nose. Horizontal is too small.”
- “I would also make flanges larger and more connected to the main piece;
  otherwise they will get destroyed.”
- “Same feedback to under-ear flanges — they are hard to access with the bolt
  and too flimsy.”
- “Front glowing panel near the nose — same: skirt is [an] awesome idea, but it
  does not fit and it is flimsy.”
- “It detached almost immediately.”
- “Make connectors attach to the main structure of the glowing panel, make two
  connectors, and make them a bit larger.”
- “Same feedback to side glowing panel — flimsy single connector.”
- “Skirt [is] fighting all corners, reinforcements, [and] flanges.”
- “You have pins exactly on both sides — pin against the pin but not pin against
  the hole.”
- “Top layer is completely disintegrated because it is not even connected on
  the 3D piece.”
- “Front frame is disconnected.”
- “This flying connector … immediately fights/conflicts with other pieces. I
  needed to cut it to connect shells.”
- “It is also very flimsy — it will break immediately on BM.”
- “There are still examples of connectors/enforcements sticking out on the
  surface of the head … `left_lower_face`.”
- “There is the same issue with left upper head.”
- “I was not able to connect shells without cutting these reinforcement
  elements because they were fighting each other.”
- “There is the same problem with connecting `rear_base.stl` to the rest of the
  shell — it fights reinforcement elements that I need to cut.”
- “Eye socket … these pieces completely disconnected because there was very
  little connection surface.”
- “The head was VERY difficult to print because one of the pieces barely fit
  the print bed.”
- “We also need to modify front/top head portals because angles changed.”
- “I am OK with the aluminum concept. It definitely conflicts [with] the
  printed base plate and maybe other shell pieces … maybe move rails on the
  aluminum plate a bit to the center — TBD.”
- “Feedback one by one — no need to rebuild before I am done with feedback.”

## 15. Worktree and generated-output state warning

This review is the authoritative requirements source for the next corrective
pass. Before the instruction changed to document-only feedback collection, a
different session began incomplete rear-base and related Gate 3, Gate 5, and
Gate 8 changes, then encountered a failed regeneration. Consequently, current
CAD sources, generated STLs, BLEND files, reports, and renders may represent
different design states.

Known potentially partial areas include the Gate 3 structural-shell config and
generator, the Gate 5 ribs-and-joints config and generator, and the Gate 8
full-size-iteration config, generator, review tooling, and documentation. The
presence of an output file must not be treated as evidence that it was generated
successfully from the current source or that it satisfies this review.

Before any corrective CAD work or regeneration:

1. preserve all existing user and session changes;
2. inventory and review the affected uncommitted diffs without resetting them;
3. establish which source revision produced each existing output;
4. reconcile every retained change against F-01 through F-29 and A-01 through
   A-39;
5. regenerate from one traceable source state only after the user declares the
   feedback pass complete; and
6. record the exact regeneration command and validation results in the relevant
   resume checkpoint.
