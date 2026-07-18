# 330 mm Cat Head Lighting Development Plan

## Document Status

- Status: approved development baseline
- Scope: Phase 2A removable cat-head lighting
- Mechanical envelope: 330 mm chin-to-ear height, 303.8 mm width
- Physical validation status: not started
- Source geometry: [Cat Head Full-Size V1](../../mechanical/fabrication/3d-print/cat-head-full-size-v1/README.md)

This is the formal implementation and validation plan for the cat-head lighting
subsystem. It is the source of truth for whisker optics, eyes, glow facets,
head-local wiring, Pixelblaze mapping, and lighting-specific acceptance tests.

The plan deliberately separates approved design inputs from results that must be
measured on physical coupons. A component or dimension described as a baseline is
not fabrication-released until it passes the applicable approval gate.

## Goal and Completion Criteria

Develop a serviceable 5 V RGB lighting system that reinforces the
Bio-Luminescent Abyssinian identity while remaining safe for night riding.

Development is complete when:

- Fourteen individually controlled side-glow whiskers are secure, flexible, and
  visible at riding brightness.
- Both eyes glow evenly and remain the dominant facial lighting feature.
- Fourteen approved glow facets read as separate illuminated surfaces without
  raw LED hotspots.
- The complete 52-pixel head passes electrical, thermal, vibration, dust,
  splash, steering-clearance, and night-visibility tests.
- The head disconnects through one capped M12 connector and every internal light
  carrier remains serviceable through the rear access opening.
- The measured BOM, wiring diagram, pixel map, Pixelblaze patterns, CAD
  interfaces, and validation results are released together.

## Scope Boundaries

Included:

- Whisker fibers, optical couplers, ports, and replaceable light carriers.
- Eye light carriers and diffuser validation.
- LED cassettes for the fourteen Gate 1 glow panels.
- Head-local power distribution, data routing, disconnect, and strain relief.
- Pixelblaze commissioning and operating patterns for the head.
- Bench, installed-head, and bike-mounted validation.

Excluded:

- Main battery, buck converter, and whole-bike distribution procurement except
  for the cat-head branch interface.
- Tail, body-panel, frame, rack, underglow, and wheel lighting.
- Changes to the approved exterior silhouette or approved Gate 1 panel roles.
- Final fabrication claims before physical coupons and the complete head pass
  their gates.


## Immediate Owner Action

Procurement status as of 2026-07-14:

- 9 m of 2.0 mm side-glow fiber is ordered for delivery on 2026-07-16.
- Existing LEDs, wire, power, and temporary connectors should be reused when
  their voltage and protocol pass the inventory check.
- M12 hardware is intentionally deferred until after the optical coupons and
  head-routing measurements.

Before the fiber arrives, identify the existing LED voltage, protocol, package,
and pixel spacing and prepare a current-limited 5 V supply, temporary 5 V/data/
ground leads, opaque coupling tube, and a fresh cutting blade. Use one sacrificial
350 mm fiber coupon to establish cutting, polishing, coupling, and tip treatment
before cutting the fourteen 320 mm development blanks.

## Locked Design Inputs

| Input | Decision |
|---|---|
| Head scale | 330 mm chin-to-ear height, 303.8 mm width |
| Eye treatment | Two uniform frosted-glow eyes; no physical pupil or outline light guide |
| Glow panels | Fourteen removable illuminated facets; no illuminated ear panels |
| Whisker count | Seven per side, fourteen total |
| Whisker control | One independently addressable pixel per fiber |
| LED family | 5 V RGB WS2812/SK6812-compatible pixels |
| Head pixel count | 52 physical pixels |
| Controller | One central Pixelblaze V3 Standard-compatible controller and one initial data output |
| Head connector | IP67 M12 A-coded four-pin, at least 4 A per contact |
| Normal caps | 35% riding, 60% parked/show, 15% reserve, 60% absolute |

The fourteen glow panel IDs and two eye insert IDs come from
`gate1-panel-roles.json` in the full-size head package. The machine-readable
lighting allocation is maintained in
`software/pixelblaze-patterns/cat-head/cat-head-pixel-map.json`.

## Lighting Architecture

### Pixel Allocation and Power Envelope

| Zone | Physical Pixels | Active Optical Outputs | Maximum Current at 60 mA/pixel |
|---|---:|---:|---:|
| Left and right whisker carriers | 16 | 14 fibers; one masked pixel per carrier | 0.96 A |
| Left and right eyes | 8 | 8 | 0.48 A |
| Fourteen glow facets | 28 | 28; two per facet | 1.68 A |
| **Head total** | **52** | **50 illuminated outputs** | **3.12 A** |

The two masked whisker-carrier pixels remain part of the addressable chain but
must render black during normal operation. The 3.12 A value is a conservative
100% full-white test case, not an operating target.

### Whisker Optical System

Baseline material:

- 2.0 mm bare side-emitting PMMA fiber.
- Procurement status: 9 m ordered, which covers the sacrificial optical coupon,
  fourteen 320 mm development cuts, iteration, and repair stock.
- Minimum internal bend radius: 12 mm until the purchased fiber is measured and
  its manufacturer data is recorded.

Visible lengths, ordered from top to bottom on each cheek:

| Whisker | Visible Length | Initial Fan Angle |
|---|---:|---:|
| W1 | 235 mm | +18 degrees |
| W2 | 250 mm | +12 degrees |
| W3 | 270 mm | +6 degrees |
| W4 | 285 mm | 0 degrees |
| W5 | 275 mm | -6 degrees |
| W6 | 255 mm | -12 degrees |
| W7 | 235 mm | -18 degrees |

The right side mirrors the left. Cut all development strands to 320 mm before
final coupling and clearance trimming. Preserve the visible-length ratios. If a
strand needs more than 10% shortening, revise the port position or fan angle and
repeat the bike-clearance review.

Each cheek uses one eight-pixel 5050 RGB stick in a removable, opaque carrier:

- Seven pixels couple directly to seven individual fibers.
- The eighth pixel is enclosed and reserved.
- Each fiber terminates square and polished, with a 0-0.5 mm coupling gap.
- Opaque cells prevent light leakage between pixels.
- A two-piece clamp retains fibers without adhesive on the optical faces.
- Rounded shell exits use replaceable TPU or silicone grommets.
- External tips are rounded and fitted with soft transparent caps.
- One strand can be replaced without removing the other six or desoldering the
  pixel stick.

Single-end injection changes the color and brightness of an entire strand. The
software may animate across the seven whiskers, but it must not describe an
effect as traveling along one fiber.

### Eye Lighting

Each eye uses four densely spaced RGB pixels on a replaceable carrier behind its
approved eye insert.

Initial optical stack:

1. Opaque black light cup that prevents spill into adjacent facets.
2. Reflective white inner surface behind and around the pixels.
3. Four-pixel light source arranged along the eye's long axis.
4. 20, 25, or 30 mm coupon-controlled setback.
5. 1.0 or 1.5 mm frosted PETG diffuser candidate.

The coupon gate selects printed versus sheet PETG and the shallowest tested
setback that meets the uniformity requirement. Both eyes must use the same
material, print/cut process, setback, and software calibration.

### Facet Lighting

The seven approved symmetric panel pairs receive two pixels per panel. Four to
six removable cassettes may serve adjacent panels, but every panel requires:

- An opaque perimeter baffle.
- A reflective inner light cavity.
- A documented two-pixel allocation.
- A removable diffuser and gasket/retainer compatible with the mechanical plan.
- No direct view of a raw LED from one metre at riding brightness.

The eyes remain visually dominant. Facets support the face with lower-intensity
aqua, cyan, violet, and magenta motion; ear panels remain opaque.

## Electrical and Data Interfaces

### Bike-to-Head Connector

Use an IP67 M12 A-coded four-pin connector rated for at least 4 A per contact.
The powered bike side must use recessed/female contacts and receive a tethered
cap when the head is removed.

| M12 Pin | Typical Wire Color | Assignment |
|---:|---|---|
| 1 | Brown | +5 V |
| 2 | White | Reserved; leave isolated at both ends |
| 3 | Blue | Ground |
| 4 | Black | Pixel data |

Use 18 AWG conductors for the 5 V and ground path. Route data with its ground
reference and add strain relief on both sides of the steering interface.

### Head Distribution

- Protect the branch with a 4 A fuse at the fused 5 V distribution point.
- Place at least 1,000 uF of bulk capacitance across 5 V and ground immediately
  inside the head connector.
- Feed carrier power in parallel from a passive head backplane or equivalent
  serviceable harness; do not carry the whole head current through LED-strip
  copper.
- Route pixel data serially through keyed internal module connectors.
- Give every removable module a documented `+5V`, `GND`, `DIN`, and `DOUT`
  interface.
- Keep the central Pixelblaze at the rear distribution area. The cat head is the
  terminating module on the initial single output.
- Add a 5 V data buffer near the front connector only if the full-length harness
  fails the data-integrity test.

### Head-Local Pixel Map

| Local Range | Zone | Order |
|---|---|---|
| H00-H06 | Left whiskers | Top to bottom |
| H07 | Left carrier reserved pixel | Always black |
| H08-H11 | Left eye | Inner to outer |
| H12-H39 | Fourteen glow facets | Two pixels per approved panel |
| H40-H43 | Right eye | Inner to outer |
| H44-H50 | Right whiskers | Top to bottom |
| H51 | Right carrier reserved pixel | Always black |

The whole-bike segment map assigns this local range an absolute S5 offset after
the preceding physical zones are finalized. Commissioning patterns operate with
the head isolated at indices 0-51.

## Development Gates

### Gate L0: Documentation and Configuration

Deliver:

- This approved development plan.
- A 52-pixel machine-readable map tied to all fourteen Gate 1 panel IDs.
- Reconciled lighting, power, wiring, controller, BOM, and mechanical references.
- Pixelblaze commissioning and operating-pattern scaffolds.
- Automated configuration validation and manual test checklists.

Pass condition: automated validation succeeds and the repository contains no
conflicting bundled-whisker, variable-count, or undecided head-connector claims.

### Gate L1: Optical Coupons

Build:

- One complete seven-whisker cheek coupon.
- One complete four-pixel eye coupon.
- One representative two-pixel full-size glow-facet coupon.

Record purchased part numbers, measured dimensions, fiber preparation, coupling
gap, diffuser material, diffuser thickness, LED setback, current, temperature,
and fixed-exposure photographs.

Pass condition: all coupon-level optical and retention criteria pass. Lock the
measured components before production ports, carriers, or cassettes are modeled.

### Gate L2: CAD Integration

Add to the 330 mm mechanical model:

- Fourteen symmetric rounded whisker ports.
- Two removable whisker carriers and two replaceable eye carriers.
- Four to six facet cassettes.
- Passive backplane/harness retention, service loops, tie points, and strain
  relief.
- Lighting-compatible vents, downward drains, and rear-cover access.

Pass condition: all lighting parts are accessible through the rear service
opening, clear shell joints/rails/fasteners, preserve the approved exterior, and
keep the complete head within its 1.2 kg target.

### Gate L3: Complete Head Bench Test

Assemble all 52 pixels, diffusers, fibers, backplane, M12 interface, and final
software in the full-size head.

Pass condition: optical, full-load electrical, thermal, data-integrity,
serviceability, dust, splash, and controlled-vibration criteria pass.

### Gate L4: Bike Integration

Install the head using the final mount, connector, strain relief, and safety
tether. Perform stationary, walking-speed, and low-speed tests before normal
riding.

Pass condition: full steering, controls, cables, rider sightline, headlight beam,
and pedestrian-clearance criteria pass, followed by an outdoor night review.

### Gate L5: Fabrication Release

Release the measured BOM, carrier/cassette CAD, wiring diagram, pixel map,
Pixelblaze patterns, assembly/service instructions, coupon report, and final
validation report as one versioned package.

Pass condition: no result remains recorded as assumed, and every failed or
conditional test has a resolved design change and repeat result.

## Test and Acceptance Criteria

### Optical

- At the 35% riding cap, every 285 mm test fiber is visibly illuminated over its
  full length from 3 m in darkness.
- Far-end whisker brightness is at least 40% of root brightness using fixed
  camera exposure or a documented light-meter method.
- Calibrated whisker-to-whisker brightness differs by no more than 20%.
- No individual eye pixel is distinguishable from 1 m; eye minimum-to-maximum
  surface brightness is at least 0.70 and left/right average differs by no more
  than 10%.
- No raw facet LED is visible from 1 m, and opaque neighboring panels remain
  visibly dark.

### Mechanical and Service

- Each fiber and external tip cap withstands a 5 N pull for 10 seconds.
- Each whisker port survives 200 controlled flex cycles without slip, crack,
  sharp edge, or visible optical failure.
- Every carrier, cassette, and backplane connector is replaceable through the
  rear opening without separating major shell sections.
- Final whisker span is no more than 50 mm wider than the handlebars.
- At full steering lock, no strand can contact hands, levers, control cables,
  headlight, tire, rider, or fixed bike structure.

### Electrical, Thermal, and Data

- At 100% full white, head current is no more than 3.2 A.
- Voltage at the farthest module remains at least 4.5 V under full load.
- M12 connector temperature rise is no more than 15 degrees C after 30 minutes
  at full load.
- One hour of show mode causes no discoloration, diffuser deformation, fiber
  damage, or internal temperature above 60 degrees C.
- A 30-minute full-harness test with steering movement and connector handling
  produces no pixel corruption, reset, or dropout.
- Removing the head leaves capped, touch-safe bike-side contacts and does not
  disable earlier whole-bike pixel segments.

### Environmental and Ride

- Controlled dust and gentle splash tests produce no connector fault, trapped
  water, short circuit, or loss of optical performance.
- Lighting remains stable after the mechanical vibration test and all fasteners,
  clamps, and fibers retain their witness positions.
- Riding mode contains no rapid strobe and does not create distracting glare for
  the rider.
- Front, side, and three-quarter night photographs confirm the brightness order:
  eyes first, whiskers second, facets third.

## Pixelblaze Behavior

| Mode | Eyes | Facets | Whiskers | Cap |
|---|---|---|---|---:|
| Commissioning | Selected zone or selected pixel | Selected zone or selected pixel | Selected zone or selected pixel | 20% default |
| Riding | Steady aqua with low-amplitude breathing | Slow low-level aqua/violet shimmer | Slow mirrored fan wave | 35% |
| Parked/show | Slow whole-eye blink | Richer aqua/magenta/violet motion | Mirrored or offset fan sweep | 60% |
| Reserve | Dim steady aqua | Off | Off | 15% |

Software must always mask H07 and H51. The initial patterns target the isolated
head; whole-bike patterns apply the documented S5 offset without changing the
head-local ordering.

## Reference Components and Sources

- [Adafruit 8 x 5050 RGB NeoPixel Stick](https://www.adafruit.com/product/1426):
  51.1 x 10.2 x 3.2 mm reference whisker light source.
- [FiberFin FF-HSN2.0 side-emitting PMMA fiber](https://fiberfin.com/product/ff-hsn2-0/):
  2.0 mm reference fiber and 12 mm published minimum bend radius.
- [ElectroMage Pixelblaze hardware guide](https://electromage.com/docs/hardware-getting-started/):
  WS2812/SK6812 compatibility and head data-interface reference.
- [TE Connectivity M12 Value Line](https://www.te.com/content/dam/te-com/documents/channel/marketing-materials/m12valueline-ecard.pdf):
  4 A and IP67 reference for four-pin A-coded M12 hardware.

Equivalent parts may replace a reference component only when their measured
dimensions, electrical ratings, protocol, optical performance, environmental
rating, and service interface satisfy the same gate criteria. Record the actual
purchased manufacturer and part number in the measured BOM.
