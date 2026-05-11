# LED Zone Plan

## Purpose

This document tracks the planned lighting zones for the Bio-Luminescent Abyssinian build. It is the bridge between visual design, wiring, Pixelblaze mapping, and power budgeting.

## Proposed Zones

| Zone | Priority | Visual Role | Notes |
|---|---:|---|---|
| Cat eyes | High | Strong front identity and character | Likely separate small LED elements or short addressable runs. |
| Cat head facets | High | Animated face glow | Use diffused panels, short strips, or pixel clusters behind translucent facets. |
| Whiskers | High | Signature bioluminescent feature | Fiber-optic or LED filament; keep flexible and away from controls. |
| Frame underglow | High | Ground glow and side visibility | Use protected strips along lower frame tubes. |
| Fork glow | High | Front visibility | Keep clear of tire, brake rotor, and cable movement. |
| Rear rack or basket glow | High | Rear and side visibility | Existing rack/basket gives good mounting structure. |
| Tail | Medium | Rear cat identity | Mounted to rear rack or basket; should not block cargo. |
| Body panels | Medium | Organic glowing side silhouette | Optional removable diffusers or ribs. |
| Wheels | Low | High-impact motion effect | Treat as later upgrade because power and durability are harder. |

## Phase Dependency Notes

- Phase 1 should include only independent LED zones and the wiring backbone.
- Cat head LEDs belong with the cat head build because their placement depends on the head geometry.
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
| 5 | Whiskers | Draft |
| 6 | Tail | Draft |
| 7 | Optional wheels | Deferred |

## Pattern Intent

- Riding mode: readable, lower brightness, mostly cyan/aqua with subtle motion.
- Parked mode: richer magenta/violet accents, stronger face and tail animation.
- Low-power mode: reduced brightness with simple pulse or breathing pattern.
- Safety mode: steady front/side/rear visibility with minimal animation.

## Measurements Needed

- Side, front, rear, and top photos with clear views of frame and rack.
- Approximate tube lengths for LED runs.
- Available mounting points on handlebar, head tube, front fork, rear rack, and basket.
- Cable path options from controller to front and rear zones.
