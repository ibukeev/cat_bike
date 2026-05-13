# LED Zone Plan

## Purpose

This document tracks the planned lighting zones for the Bio-Luminescent Abyssinian build. It is the bridge between visual design, wiring, Pixelblaze mapping, and power budgeting.

## Proposed Zones

| Zone | Priority | Visual Role | Notes |
|---|---:|---|---|
| Cat eyes | High | Strong front identity and character | Likely separate small LED elements or short addressable runs. |
| Cat head facets | High | Animated face glow | Use diffused panels, short strips, or pixel clusters behind translucent facets. |
| Whiskers | High | Signature bioluminescent feature | Side-glow fiber optics lit by hidden LEDs inside the cat head; keep flexible and away from controls. |
| Frame underglow | High | Ground glow and side visibility | Use protected strips along lower frame tubes. |
| Fork glow | High | Front visibility | Keep clear of tire, brake rotor, and cable movement. |
| Rear rack or basket glow | High | Rear and side visibility | Existing rack/basket gives good mounting structure. |
| Tail | Medium | Rear cat identity | Mounted to rear rack or basket; should not block cargo. |
| Body panels | Medium | Organic glowing side silhouette | Optional removable diffusers or ribs. |
| Wheels | Low | High-impact motion effect | Treat as later upgrade because power and durability are harder. |

## Photo References

Detailed layout notes are tracked in [Photo Layout Analysis](photo-layout-analysis.md).

| Photo | Use |
|---|---|
| [01-bike-front-straight.jpg](../../assets/photos/Original_bike/front_back/01-bike-front-straight.jpg) | Front visibility, fork clearance, headlight alignment. |
| [02-bike-side-profile-wide.jpg](../../assets/photos/Original_bike/front_back/02-bike-side-profile-wide.jpg) | Whole side profile and frame-zone planning. |
| [03-bike-rear-rack-left-closeup.jpg](../../assets/photos/Original_bike/front_back/03-bike-rear-rack-left-closeup.jpg) | Rear rack, basket, and tail mount planning. |
| [04-bike-rear-straight.jpg](../../assets/photos/Original_bike/front_back/04-bike-rear-straight.jpg) | Rear visibility and tail symmetry. |
| [05-bike-side-profile-close.jpg](../../assets/photos/Original_bike/front_back/05-bike-side-profile-close.jpg) | Side-frame LED routes and panel candidates. |
| [06-bike-rear-three-quarter-close.jpg](../../assets/photos/Original_bike/front_back/06-bike-rear-three-quarter-close.jpg) | Rear three-quarter mounting and wiring paths. |
| [07-bike-rear-three-quarter-wide.jpg](../../assets/photos/Original_bike/front_back/07-bike-rear-three-quarter-wide.jpg) | Whole-bike rear/side silhouette. |
| [08-bike-front-top-handlebar-head-tube.jpg](../../assets/photos/Original_bike/front_back/08-bike-front-top-handlebar-head-tube.jpg) | Cat head mount envelope, handlebar, head tube, cables. |

## Phase 1 Visual References

These AI-assisted references are not build drawings. Use them only to preserve the current visual direction for Phase 1 LED zone planning.

| Reference | Use | Notes |
|---|---|---|
| [phase1-led-reference-v1-too-busy.png](../../assets/photos/Concepts/Bio-Luminescent%20Abyssinian/Phase_1_LED_References/phase1-led-reference-v1-too-busy.png) | Rejected iteration | Too busy; includes wheel/handlebar/basket lighting ideas that are not Phase 1 targets. |
| [phase1-led-reference-v2-simplified.png](../../assets/photos/Concepts/Bio-Luminescent%20Abyssinian/Phase_1_LED_References/phase1-led-reference-v2-simplified.png) | Simplified direction | Useful for lower frame, fork, rack, and underglow restraint. |
| [phase1-led-reference-v3-current.png](../../assets/photos/Concepts/Bio-Luminescent%20Abyssinian/Phase_1_LED_References/phase1-led-reference-v3-current.png) | Current Phase 1 reference | Best current reference for clean Phase 1 lighting: no wheel lights, no handlebar lights, unlit flag post, restrained basket underside glow. |

Current Phase 1 visual rules:

- Use the reference direction from `phase1-led-reference-v3-current.png`.
- Keep the flag post unlit.
- Do not include wheel, tire, spoke, handlebar, grip, brake lever, or dense basket-face lighting.
- Keep lighting restrained enough that future cat head, tail, and body panel phases still have visual room.
- Translate the image into real, serviceable LED zones rather than copying hallucinated geometry literally.

## Phase 1 LED Placement Plan

These are the starter zones for the first buildable lighting layer. The goal is to install useful, independent lighting now while reserving power/data interfaces for later sculpture phases.

| Zone ID | Zone | Physical Location | LED Style | Rough Length / Count | Power/Data Need | Mounting Idea | Risk / Constraint | Status |
|---|---|---|---|---:|---|---|---|---|
| P1-Z01 | Lower frame segmented spine | Lower frame curve from front lower frame toward crank/rear lower frame | Addressable strip in short diffused segments | 60-120 pixels | Active Phase 1 output | Protected channel or silicone diffuser mounted inboard on frame | Must avoid pedals, kickstand, chain, battery access, and foot strike | Draft |
| P1-Z02 | Fork gill accents | Both front fork legs | Short addressable strip segments or small diffused bars | 24-60 pixels | Active Phase 1 output | Short vertical/diagonal protected segments on outer or forward fork faces | Must avoid tire, brake rotor, brake cable, and fork movement | Draft |
| P1-Z03 | Rear rack rib accents | Rear rack support bars below basket | Short repeated addressable segments | 40-100 pixels | Active Phase 1 output | Diffused strip sections on rack supports with service loops | Must avoid rear wheel, cargo straps, basket removal, and rider leg clearance | Draft |
| P1-Z04 | Basket underside glow | Under basket bottom edge, mostly hidden | Hidden strip or side-emitting strip | 30-80 pixels | Active Phase 1 output | Mounted under basket lip or bottom rail | Basket must remain usable; no basket-face string lights | Draft |
| P1-Z05 | Ground underglow | Downward-facing lower frame/rack area | Diffused strip or shared output with lower frame | 30-80 pixels | Active Phase 1 output or tied to P1-Z01/P1-Z03 | Inboard/downward protected channel | Must not be lowest point or exposed to curb/transport impacts | Draft |
| P1-R01 | Cat head reserved interface | Head tube/stem area | Connector only | 0 installed pixels | Reserved power/data | Weather-resistant quick disconnect with strain relief | Head geometry not defined yet | Draft |
| P1-R02 | Tail reserved interface | Rear rack/basket area | Connector only | 0 installed pixels | Reserved power/data | Weather-resistant quick disconnect and tether path | Tail geometry not defined yet | Draft |
| P1-R03 | Body panel reserved interface | Side frame/rear rack area | Connector only | 0 installed pixels | Reserved power/data | Capped branch connector near future panel zones | Panel geometry not defined yet | Draft |

Phase 1 installed estimate: 184-440 pixels before any head, tail, body panel, or wheel LEDs.

## Phase Dependency Notes

- Phase 1 should include only independent LED zones and the wiring backbone.
- Cat head LEDs belong with the cat head build because their placement depends on the head geometry.
- Whiskers are planned as fiber optics driven by hidden LEDs, so their electrical load should be counted as a small hidden LED cluster inside the cat head rather than LEDs along each whisker.
- Tail LEDs belong with the tail build because their placement depends on the tail structure.
- Body panel LEDs belong with the panel build because they may mount to the internal side of the panels.
- Future zones should get reserved power/data interfaces before their final LEDs are installed.

## Pixelblaze Segment Draft

| Segment | Planned Physical Zone | Status |
|---|---|---|
| 0 | Frame underglow | Draft |
| 1 | Fork and front frame | Draft |
| 2 | Rear rack or basket | Draft |
| 3 | Cat head facets | Draft |
| 4 | Eyes | Draft |
| 5 | Fiber-optic whisker light engines | Draft |
| 6 | Tail | Draft |
| 7 | Optional wheels | Deferred |

## Pattern Intent

- Riding mode: readable, lower brightness, mostly cyan/aqua with subtle motion.
- Parked mode: richer magenta/violet accents, stronger face and tail animation.
- Low-power mode: reduced brightness with simple pulse or breathing pattern.
- Safety mode: steady front/side/rear visibility with minimal animation.

## Measurements Needed

- Actual lower frame tube LED path length.
- Fork leg usable straight length.
- Rear rack and basket dimensions.
- Basket hole spacing and usable clamp locations.
- Battery removal path and required clearance.
- Headlight beam envelope.
- Full steering sweep with cables.
- Tail mount envelope and cargo clearance.
