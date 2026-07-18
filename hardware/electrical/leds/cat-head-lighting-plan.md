# Cat Head Lighting Plan

## Purpose

Define the locked lighting architecture for the Phase 2A removable 330 mm cat
head module.

This document covers eyes, illuminated facets, fiber-optic whisker light
engines, wiring, and Pixelblaze segment behavior. Mechanical mounting is tracked
separately in [Cat Head Mount Plan](../../mechanical/mounts/cat-head-mount-plan.md).

The implementation sequence, physical approval gates, and acceptance criteria
are controlled by the [330 mm Cat Head Lighting Development Plan](cat-head-lighting-development-plan.md).

## Current Design Direction

- Cat head is a removable module that rotates with the handlebars.
- Head exterior is 330 mm chin-to-ear and 303.8 mm wide.
- Head uses faceted copper/rose-gold/mirror visual language.
- Fourteen removable facets and two eye inserts illuminate.
- Seven side-glow fiber whiskers per side use one directly coupled pixel per
  fiber.
- Lighting supports the Bio-Luminescent Abyssinian identity without becoming
  harsh or distracting to the rider.

## Lighting Zones

| Zone | Visual Role | Physical Pixels | Notes |
|---|---|---:|---|
| Eyes | Strong front identity and character | 8 | Four RGB pixels behind each uniform frosted diffuser. |
| Facet glow panels | Bioluminescent face shimmer | 28 | Two RGB pixels behind each of fourteen approved removable facets. |
| Whisker light engines | Fiber-optic whisker glow | 16 | Two eight-pixel sticks; fourteen fibers illuminate and two pixels remain masked. |

Locked head total: 52 physical pixels, with a conservative 3.12 A maximum at
5 V and 60 mA per pixel.

## Whisker Architecture

Use fiber optics, not LEDs installed along the whisker length.

Locked baseline:

- Use 2.0 mm bare side-emitting PMMA fiber, subject to the optical coupon gate.
- Cut fourteen 320 mm development strands before final coupling and trimming.
- Final visible lengths per side, top to bottom, are 235, 250, 270, 285, 275,
  255, and 235 mm.
- Initial fan angles are +18, +12, +6, 0, -6, -12, and -18 degrees.
- Use one opaque eight-pixel carrier per cheek. Seven pixels couple directly to
  seven fibers; the eighth pixel stays masked and renders black.
- Hold polished fiber ends 0-0.5 mm from the LED surface in isolated optical
  cells. Retain fibers mechanically without adhesive on their optical faces.
- Use rounded, grommeted shell exits, at least a 12 mm internal bend radius, and
  rounded soft-capped external tips.
- Whiskers must not contact hands, brake levers, cables, tire, headlight, rider,
  or pedestrians during normal riding.

One-end injection changes a whole strand at once. Patterns may sweep across the
seven independently controlled whiskers but cannot produce a traveling pulse
along a single fiber.

## Eye Architecture

Each eye uses four densely spaced 5 V RGB pixels on a replaceable carrier behind
a uniform frosted PETG diffuser. A black light cup prevents spill into adjacent
facets and a reflective inner surface improves mixing. Full-size coupons compare
1.0 and 1.5 mm diffuser material at 20, 25, and 30 mm LED setbacks.

Behavior:

- Riding mode: steady cyan/aqua glow with subtle breathing.
- Parked/show mode: brighter glow with a slow whole-eye blink.
- Reserve mode: dim steady aqua.
- Avoid fast strobe or high brightness near the rider.

## Facet Glow Architecture

Exactly fourteen Gate 1 facets illuminate. The head mixes:

- Opaque mirrored copper/rose-gold facets.
- Translucent frosted facets with internal glow.
- Dark or shadowed facet lines for structure.

Lighting uses:

- Two-pixel sections on four to six removable internal cassettes.
- Frosted PETG selected through full-size optical coupons.
- Opaque baffles so each approved panel remains visually distinct.
- Enough LED setback that raw pixels are not visible from one metre.

## Connector and Wiring

Use one IP67 M12 A-coded four-pin quick-disconnect rated for at least 4 A per
contact near the handlebar/stem area. Use recessed/female powered contacts on
the bike side, a tethered cap, and strain relief on both sides.

| M12 Pin | Typical Wire Color | Signal |
|---:|---|---|
| 1 | Brown | +5 V |
| 2 | White | Reserved and isolated |
| 3 | Blue | Ground |
| 4 | Black | Pixel data |

Use an 18 AWG 5 V/ground path, a 4 A branch fuse, at least 1,000 uF of bulk
capacitance at the head entrance, parallel module power, and serial pixel data.

## Pixelblaze Segment Map

| Local Range | Physical Zone | Order |
|---|---|---|
| H00-H06 | Left whiskers | Top to bottom |
| H07 | Left reserved carrier pixel | Always black |
| H08-H11 | Left eye | Inner to outer |
| H12-H39 | Fourteen glow facets | Two pixels per Gate 1 panel |
| H40-H43 | Right eye | Inner to outer |
| H44-H50 | Right whiskers | Top to bottom |
| H51 | Right reserved carrier pixel | Always black |

The machine-readable allocation is stored in
`software/pixelblaze-patterns/cat-head/cat-head-pixel-map.json`. The complete
head remains the S5 range and terminating module on the initial single
Pixelblaze output. Its absolute whole-bike offset is assigned after preceding
zones are finalized.

## Mode Behavior

| Mode | Eyes | Facets | Whiskers |
|---|---|---|---|
| Riding | Steady/breathing cyan-aqua | Low brightness shimmer | Slow mirrored fan wave |
| Parked/show | Brighter glow and slow whole-eye blink | Richer aqua/violet/magenta shimmer | Mirrored or offset fan sweep |
| Low-power reserve | Dim steady eyes | Off | Off |

Brightness caps remain 35% riding, 60% parked/show, 15% reserve, and 60%
absolute.

## Safety and Service Notes

- No high-brightness strobe aimed at rider or pedestrians.
- Keep every carrier and cassette accessible through the removable rear cover.
- Protect electronics from dust and moisture and preserve downward drainage.
- Add a safety tether for the complete head module.
- Bench test the complete head before mounting it to the bike.
- Do not mark a lighting gate complete until its measurements and photographs
  are recorded in the validation report.

## Remaining Measurement Gates

- Record purchased fiber and LED part numbers and measured dimensions.
- Select final eye/facet diffuser material and setback from full-size coupons.
- Validate fiber preparation, coupling efficiency, retention, and tip treatment.
- Verify full-white current, voltage drop, connector heating, and data integrity.
- Verify complete-head service access, environmental performance, night
  appearance, steering clearance, and whisker span on the bike.
