# 330 mm Cat Head Fabrication-Ready Model Plan

## Status

- Current phase: Gate 8 - full-size structural feedback iteration review
- Locked height: 330 mm, chin to highest ear tip
- Target completed head-module mass: at most 1.2 kg
- Hard mass rejection limit: 1.5 kg
- Printer: enclosed Prusa MK4S, 0.4 mm nozzle

## Summary

Create a serviceable, vibration-resistant 330 mm cat head using:

- A hybrid ASA structural shell with integrated opaque facets.
- Four body sections, two detachable ears, and a removable rear service cover.
- Twenty removable illuminated/light-transmitting facets plus two corrected eye diffusers.
- Bolted joints; no glue as a primary structural connection.
- Mechanical provisions for LEDs, wiring, seven whiskers per side, ventilation, and drainage.
- Later integration of an aluminum backplate and two forward-projecting rails.
- A completed head target of at most 1.2 kg, excluding the bike-side clamp.

## Source, Interfaces, and Defaults

- Use `accepted-panels-3d.obj` and `cardboard_panels.csv` as the authoritative geometry and facet-identity sources. Do not segment the solidified 100 mm STL.
- Preserve the approved silhouette by uniformly scaling to 330 mm. Only the rear service plane, wall thickness, joints, and internal structure may change.
- Design against a conservative MK4S envelope of 240 × 200 × 210 mm, allowing room for brim and placement tolerance.
- Use 1.8 mm nominal ASA skin, 3.2 mm plain internal flange tabs where Gate 5
  uses a seam joint, a 0.4 mm nozzle, and 0.20 mm layers.
- Use black M3 through-bolts, washers, and loose M3 nyloc nuts for Gate 5
  shell seams. The matching flange tabs provide the clamped interface; no
  alignment keys are generated in this revision.
- Use M2.5 screws and heat-set inserts for removable lightweight panels and retainers.
- Export removable panels as both printable STL and flat DXF/SVG. Support 1.0–1.5 mm sheet/printed panels using a rear clamp and compressible gasket.
- Keep opaque facets structural. Export their flat outlines for either mirror vinyl or thin non-structural cosmetic overlays.
- Keep the bike-side clamp separate from the head-side backplate through a replaceable adapter interface.

## Implementation Stages

### 1. Freeze the 330 mm master

- [x] Rebuild the surface from the accepted panel mesh while preserving panel IDs, original triangles/quads, eye openings, and zone metadata.
- [x] Scale to 303.8 mm wide × 330 mm tall while retaining the approved proportions.
- [x] Define a rear-service planning plane 10 mm forward of the source rear envelope; Gate 1 intentionally does not cut the exterior yet.
- [x] Generate front, side, top, and isometric panel-role review views from the approved source surface.
- [x] Verify all external vertices match the uniform scale transform exactly (0.0 mm generated residual).

### 2. Assign every facet a fabrication role

Create a versioned panel-role table assigning every source facet to exactly one role:

- `integrated_opaque`
- `removable_glow`
- `eye_diffuser`
- `major_section_seam`
- `ear_seam`
- `rear_service`
- `internal_only`

- [x] Select twenty glow/light-transmitting panels from the purple annotations and completed mirrored side pairs; all former cyan candidates are opaque.
- [x] Keep the eyes visually dominant and avoid illuminated ear panels.
- [x] Record triangulated halves of an original planar quad as one four-corner removable-panel unit when both halves share the glow role.
- [x] Keep each candidate glow unit to one source facet; do not create bent multi-facet cosmetic inserts.
- [x] Review and approve the candidate role map before modeling any section seams or panel retainers. Approved 2026-07-15.

**Approval Gate 1:** approve multiview renders showing opaque, glow, eye, and seam roles before joints are modeled.

**Gate 1 decision:** approved. Freeze the 330 mm exterior, twenty purple
glow/light-transmitting panels, corrected separate eye-material silhouettes,
and two-facet mouth opening. A straight facial center seam is prohibited because
it would cross approved centerline glow panels; the section-layout review must
route around them or introduce a small center-front structural module.

### 3. Create printer-sized structural sections

Start with seven structural pieces. The rear base is separate because the
six-piece candidate left essentially no printer margin on one lower shell and
mixed the future backplate interface into both lower halves:

1. Left upper head
2. Right upper head
3. Left lower face/jaw
4. Right lower face/jaw
5. Rear base/backplate-interface section
6. Left ear
7. Right ear

- [x] Route the candidate center and upper/lower seams along existing facet edges without crossing an eye or removable glow panel.
- [x] Confirm every candidate oriented part fits 240 × 200 × 210 mm using the Gate 2 orientation search; repeat in the slicer after walls/flanges are modeled.
- [x] Visually approve and freeze the seven-section face-level topology. Approved 2026-07-15.
- [x] Generate 1.8 mm inward shell baselines for all seven sections without moving the approved exterior.
- [x] Repair pinched boundary vertex fans and verify every shell baseline is closed manifold.
- [x] Re-run the printer-envelope orientation search after wall generation; all seven baselines fit.
- [x] Close the two inherited bottom/throat openings integrally in the lower shells; reserve ventilation for protected rear-facing features.
- [ ] If a part fails, move the belt seam to the next existing edge chain; do not distort the head or introduce an arbitrary visible planar cut.
- [x] Generate 16 pairs of matching 8 mm-deep, 3.2 mm-thick plain rectangular
  internal flange tabs with M3 through-bolts, washers, loose nyloc nuts, and
  shared-inner-bisector axes that recess every tab behind both exterior face
  planes across every approved source-section interface. Add four continuous
  concealed connector rails and six parallel through-bolt paths to attach the
  rear base to all four adjacent body shells.
- [x] Give each ear root a paired flange-tab connection with two internal M3 screws; no alignment dowel in this revision.
- [x] Add paired triangular gussets to both panel sides of every source-panel
  connection internal to the four body shells: 55 main 2.5 mm-foot by 3 mm-high
  gussets with at least 1.3 mm exterior recess and 55 compact 1.2 mm by 1.5 mm
  opposing-side gussets with at least 0.4 mm exterior skin. Exclude flange
  seams, exterior edges, rear base, and ears. Add 38 triangulated hubs at
  every shared internal main-gusset endpoint, with full end-section overlap.
- [x] Integrate center-split rear panels into both lower shells and replace the
  massive rear frame with a compact 60 mm-top / 120 mm-bottom closed trapezoidal
  rear-base frame on the sloped upper-head rear plane. Its 20 mm surround and
  18 mm inward depth form a load-spreading ring around an approximately
  20 mm-top / 80 mm-bottom / 39 mm-high wiring-and-fastener opening. Four
  continuous hidden shell-side rails carry six M3 paths through the rear frame
  and attach it to all four adjacent body shells. No isolated connector tabs
  remain along the inner opening; the
  lower rear panels are continuous and joined by their own hidden flange
  modules. The old lower service cut, rectangular rim, and tie rails are
  removed.
- [ ] Confirm every nut, screw, and panel retainer is reachable in the documented assembly order.

### 4. Validate assembly before full-size printing

- [ ] Generate a 100 mm mechanical assembly model using the same seven-section topology, regenerated miniature joints, M2 hardware, and color-coded dummy panels.
- [ ] Generate full-size ASA/PETG coupons for the M3 matching-tab body seam,
  washer/nut access, ear root, M2.5 panel retainer, and gasketed rabbet.
- [ ] Test clearance variants of 0.2, 0.3, 0.4, and 0.5 mm.
- [ ] Select the smallest clearance that assembles by hand after cooling without sanding and has no more than 0.25 mm perceptible play.
- [ ] Assemble and disassemble the miniature three times without damage.
- [ ] Confirm rear access to all retained hardware and no trapped nuts or impossible tool angles.

**Approval Gate 2:** physically approve the 100 mm assembly and full-size joint coupons before internal reinforcement is finalized.

### 5. Design panels, lighting provisions, and service features

Before freezing internal geometry, purchase or select and measure:

- Addressable LED strip/modules.
- Diffuser sheet or PETG print thickness.
- Side-glow fiber diameter.
- Whisker light-engine components.
- Head electrical connector and strain relief.

Then add:

- [x] Represent all twenty approved glow facets with nine removable windows:
  one combined twelve-facet centerline insert and eight isolated inserts.
- [x] Add two corrected 1.5 mm eye diffusers in independent opaque 14 mm-deep
  lightboxes, each reserving four addressable pixels and an 11 mm diffuser gap.
- [ ] Four to six removable internal LED cassettes serving groups of adjacent windows.
- [x] Add replaceable eye-light carriers with opaque removable rear caps, four
  diffuser-retaining posts, two M2.5 cap fasteners, a sealed 4 mm wire port,
  and two recessed internal M2.5 head-mount flanges per eye, centered on the
  outer-side and lower eye edges.
- [ ] Seven rounded whisker ports per side and removable light-engine carriers.
- [ ] Wire channels, tie points, service loops, and strain relief.
- [ ] Overlapping dust seams, gasketed removable panels, downward-facing drains, and protected vents.
- [ ] A rear service cover removable without separating the major shell sections.
- [ ] Full-size lit panel samples that avoid unacceptable LED hotspots at riding brightness.

### 6. Integrate reinforcement, backplate, and rails

Do this only after the head shell, panel map, and assembly joints are approved.

- [ ] Measure the CAD and prototype center of gravity.
- [ ] Compare 6061 aluminum rail candidates at the actual 180–220 mm cantilever length: ½ × ⅛ inch flat bar mounted on edge and ½ inch square tube with approximately 1⁄16 inch wall.
- [ ] Select the lighter option that passes vertical and lateral load tests with at most 2 mm elastic tip deflection and no permanent deformation.
- [ ] Use a simple flat 3 mm 6061 backplate with rounded corners and drillable DXF/paper templates.
- [ ] Join rails to the plate using off-the-shelf metal 90° clevis/angle brackets and through-bolts. An angled rail-end cut alone is not a structural joint.
- [ ] Clamp the rails into printed rear, middle, and front cross-ribs using replaceable rubber/TPU shims.
- [ ] Route mounting loads through rails, cross-ribs, and backplate—not through cosmetic panels.
- [ ] Provide a separate replaceable adapter for the eventual commercial or fabricated bike clamp.
- [ ] Include an independent metal safety-tether point.

**Approval Gate 3:** approve the full head/backplate/rail assembly, center of gravity, and bike clearances before final structural sections are printed.

### 7. Produce the fabrication release

Generate a reproducible release containing:

- Full-scale ASA structural STLs/3MFs with intended orientations.
- PETG panel STLs and matching DXF/SVG cut files.
- Opaque-facet vinyl/overlay templates.
- Backplate and rail drilling templates.
- Full hardware, material, and cut-list BOM.
- Exploded views and numbered assembly instructions.
- Print profiles, estimated filament mass, and print time.
- Panel map, wiring routes, and LED cassette map.
- Validation report and release manifest.

Generated build artifacts belong under `output/release-v1/`; source scripts, configuration, documentation, and tests remain the tracked source of truth.

**Approval Gate 4:** approve the release renders, BOM, predicted mass, and assembly guide before committing to the complete full-size print.

## Test and Acceptance Plan

### Automated CAD checks

- [ ] Manifold, watertight structural meshes with no degenerate faces.
- [ ] Every part fits the conservative MK4S envelope in its documented orientation.
- [ ] Minimum wall, flange, and fastener-edge distances are satisfied.
- [ ] Symmetric panel roles and ear geometry remain symmetric.
- [ ] Every source facet has exactly one fabrication role.
- [ ] No glow panel or eye is crossed by a major seam.
- [ ] Fasteners have tool access and do not collide with rails, LEDs, or wiring.
- [ ] Predicted completed mass is at most 1.2 kg; stop and redesign above 1.5 kg.

### Physical validation

- [ ] Assemble/disassemble the miniature three times without damage.
- [ ] Assemble full-size coupons without sanding or forced insertion.
- [ ] Apply a combined 60 N vertical and lateral proof load to the rail test fixture for 60 seconds.
- [ ] Apply five times completed-head weight to the assembled mount in vertical and lateral directions; allow no cracks, loosened hardware, or permanent visible deformation.
- [ ] Perform a controlled vibration test, then verify witness marks and fastener torque.
- [ ] Heat-test ASA/PETG coupons at approximately 65°C without electronics or batteries; reject visible creep or panel release.
- [ ] Perform dust and gentle splash tests; water must drain without pooling around electronics.
- [ ] Verify full steering lock, brakes, cables, hands, rider sightline, and headlight clearance.
- [ ] Complete progressive stationary, low-speed, and mixed-surface bike tests before playa use.
- [ ] Proof-test the independent tether and include spare panel screws, inserts, nuts, and one replacement diffuser in the field kit.

## Assumptions

- Final size remains locked at 330 mm chin-to-ear-tip.
- Printing uses an enclosed and ventilated Prusa MK4S workflow for ASA.
- The head rotates with the handlebars.
- Major sections are bolted for occasional disassembly; routine service uses the rear cover and removable panels.
- The enclosure is dust- and splash-resistant, not waterproof.
- Lighting software and final animation programming are outside this mechanical fabrication plan.
- Exact opaque finish remains open; structural ASA facets support either vinyl or thin cosmetic overlays.
