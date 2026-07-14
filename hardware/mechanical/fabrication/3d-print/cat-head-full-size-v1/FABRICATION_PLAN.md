# 330 mm Cat Head Fabrication-Ready Model Plan

## Status

- Current phase: Gate 1 — master geometry and panel-role review
- Locked height: 330 mm, chin to highest ear tip
- Target completed head-module mass: at most 1.2 kg
- Hard mass rejection limit: 1.5 kg
- Printer: enclosed Prusa MK4S, 0.4 mm nozzle

## Summary

Create a serviceable, vibration-resistant 330 mm cat head using:

- A hybrid ASA structural shell with integrated opaque facets.
- Four body sections, two detachable ears, and a removable rear service cover.
- Fourteen removable illuminated PETG facets plus two eye diffusers.
- Bolted joints; no glue as a primary structural connection.
- Mechanical provisions for LEDs, wiring, seven whiskers per side, ventilation, and drainage.
- Later integration of an aluminum backplate and two forward-projecting rails.
- A completed head target of at most 1.2 kg, excluding the bike-side clamp.

## Source, Interfaces, and Defaults

- Use `accepted-panels-3d.obj` and `cardboard_panels.csv` as the authoritative geometry and facet-identity sources. Do not segment the solidified 100 mm STL.
- Preserve the approved silhouette by uniformly scaling to 330 mm. Only the rear service plane, wall thickness, joints, and internal structure may change.
- Design against a conservative MK4S envelope of 240 × 200 × 210 mm, allowing room for brim and placement tolerance.
- Use 1.8 mm nominal ASA skin, 2.4–3.0 mm seam flanges/ribs, a 0.4 mm nozzle, and 0.20 mm layers.
- Use black M3 screws with captive square nuts for major shell seams. Alignment keys carry shear; screws provide clamping.
- Use M2.5 screws and heat-set inserts for removable lightweight panels and retainers.
- Export removable panels as both printable STL and flat DXF/SVG. Support 1.0–1.5 mm sheet/printed panels using a rear clamp and compressible gasket.
- Keep opaque facets structural. Export their flat outlines for either mirror vinyl or thin non-structural cosmetic overlays.
- Keep the bike-side clamp separate from the head-side backplate through a replaceable adapter interface.

## Implementation Stages

### 1. Freeze the 330 mm master

- [ ] Rebuild the surface from the accepted panel mesh while preserving panel IDs, original triangles/quads, eye openings, and zone metadata.
- [ ] Scale to 303.8 mm wide × 330 mm tall while retaining the approved proportions.
- [ ] Move the existing rear opening forward by no more than 10 mm if required to keep structural print sections within the safe printer envelope.
- [ ] Generate front, side, top, and three-quarter comparison renders against the approved 100 mm proof.
- [ ] Require all non-rear external vertices to match uniform scaling within 0.25 mm.

### 2. Assign every facet a fabrication role

Create a versioned panel-role table assigning every source facet to exactly one role:

- `integrated_opaque`
- `removable_glow`
- `eye_diffuser`
- `major_section_seam`
- `ear_seam`
- `rear_service`
- `internal_only`

- [ ] Select fourteen glow facets, primarily symmetric pairs around the center forehead, cheeks, and lower muzzle.
- [ ] Keep the eyes visually dominant and avoid illuminated ear panels.
- [ ] Restore triangulated halves of an original planar quad to one four-corner insert when both halves share the same role.
- [ ] Do not create bent multi-facet cosmetic inserts; multiple windows may share one internal LED cassette.

**Approval Gate 1:** approve multiview renders showing opaque, glow, eye, and seam roles before joints are modeled.

### 3. Create printer-sized structural sections

Start with six structural pieces:

1. Left upper head
2. Right upper head
3. Left lower face/jaw
4. Right lower face/jaw
5. Left ear
6. Right ear

- [ ] Route the center and upper/lower seams along existing facet edges without crossing an eye or removable glow panel.
- [ ] Confirm every oriented part fits 240 × 200 × 210 mm.
- [ ] If a part fails, move the belt seam to the next existing edge chain; do not distort the head or introduce an arbitrary visible planar cut.
- [ ] Give body seams 12–15 mm internal flanges, keyed alignment, and M3 fasteners approximately every 50–70 mm.
- [ ] Attach each ear with two tapered alignment features, an anti-rotation tongue, and two internally accessible M3 screws.
- [ ] Reserve a rear service opening of at least 100 × 80 mm and a surrounding structural rim.
- [ ] Confirm every nut, screw, and panel retainer is reachable in the documented assembly order.

### 4. Validate assembly before full-size printing

- [ ] Generate a 100 mm mechanical assembly model using the same six-section topology, regenerated miniature joints, M2 hardware, and color-coded dummy panels.
- [ ] Generate full-size ASA/PETG coupons for the M3 body seam, captive nut pocket, ear root, M2.5 panel retainer, gasketed rabbet, and alignment keys.
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

- [ ] Fourteen independent glow windows and two eye diffusers.
- [ ] Four to six removable internal LED cassettes serving groups of adjacent windows.
- [ ] Replaceable eye-light carriers.
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
