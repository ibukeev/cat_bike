# Cat Head Lighting Plan

## Purpose

Define the draft lighting architecture for the Phase 2A removable cat head module.

This document covers eyes, illuminated facets, fiber-optic whisker light engines, wiring, and Pixelblaze segment behavior. Mechanical mounting is tracked separately in [Cat Head Mount Plan](../../mechanical/mounts/cat-head-mount-plan.md).

## Current Design Direction

- Cat head is a removable module.
- Cat head rotates with the handlebars.
- Preferred mount point is handlebar center / stem area.
- Head uses faceted copper/rose-gold/mirror visual language.
- Whiskers use side-glow fiber optics lit by hidden LEDs inside the head.
- Lighting should support the Bio-Luminescent Abyssinian identity without becoming harsh or distracting to the rider.

## Lighting Zones

| Zone | Visual Role | Draft Pixel Count | Notes |
|---|---|---:|---|
| Eyes | Strong front identity and character | 8-16 | Bright cyan/aqua glow, possibly behind frosted diffuser. |
| Facet glow panels | Bioluminescent face shimmer | 40-80 | Internal LEDs behind selected translucent facets. Not every facet needs to light. |
| Whisker light engines | Fiber-optic whisker glow | 4-8 nominal, 16 high | Hidden LED clusters drive side-glow fiber bundles. |

Draft nominal head estimate: 52-104 pixels.

## Whisker Architecture

Use fiber optics, not LEDs directly along the whisker length.

Recommended approach:

- Side-glow fiber strands exit through small holes on each side of the face.
- Fiber bundles route back to hidden LED light engines inside the head.
- One light engine can drive multiple fibers.
- Use separate left/right groups if possible.
- Fiber tips should be rounded, sanded smooth, or capped so they are not sharp.
- Whiskers must remain flexible and must not contact hands, brake levers, cables, tire, or pedestrians during normal riding.

Possible control groups:

| Group | Pixel Count | Behavior |
|---|---:|---|
| Left whiskers | 2-4 | Breathing, shimmer, or subtle traveling pulse. |
| Right whiskers | 2-4 | Mirrored or offset from left side. |
| Optional center/nose glow | 1-2 | Can tie whiskers into face lighting. |

## Eye Architecture

Options:

- Small pixel cluster behind frosted acrylic/PETG eye diffuser.
- Short dense strip segment behind each eye.
- Small module/ring only if it fits the faceted style.

Behavior:

- Default riding mode: steady cyan/aqua glow with subtle breathing.
- Show mode: slow blink, shimmer, or gaze-like pulse.
- Avoid fast strobe or high brightness near the rider.

## Facet Glow Architecture

Not every facet should light. The head should mix:

- Opaque mirrored copper/rose-gold facets.
- Translucent frosted facets with internal glow.
- Dark or shadowed facet lines for structure.

Lighting should come from inside the head:

- Short LED strip pieces or small pixel modules.
- Diffused through frosted plastic or translucent film.
- Mounted so individual raw LEDs are not directly visible unless intentionally used as pixel texture.

## Connector and Wiring

Preferred head connector:

- Waterproof 4-pin or 5-pin connector.
- Quick-disconnect near handlebar/stem area.
- Strain relief on both bike-side and head-side wiring.

Minimum pins:

| Pin | Signal |
|---|---|
| 1 | +5V |
| 2 | GND |
| 3 | DATA |
| 4 | Spare / future second data line / extra ground |

Use a capped connector on the bike harness when the head is removed.

## Pixelblaze Segment Draft

| Segment | Physical Zone | Status |
|---|---|---|
| S5A | Eyes | Draft |
| S5B | Facet glow panels | Draft |
| S5C | Fiber-optic whisker light engines | Draft |

If using one Pixelblaze data output, the cat head becomes a reserved range in the main pixel chain. If wiring becomes awkward, the available Pixelblaze Output Expander can be reconsidered, but it is not part of the Phase 1/first-head plan.

## Mode Behavior

| Mode | Eyes | Facets | Whiskers |
|---|---|---|---|
| Riding | Steady/breathing cyan-aqua | Low brightness shimmer | Gentle breathing |
| Parked/show | Brighter glow, slow blink/pulse | Richer aqua/violet shimmer | Traveling pulse or shimmer |
| Low-power reserve | Dim steady eyes | Off or very dim | Off or very dim |

## Safety and Service Notes

- No high-brightness strobe aimed at rider or pedestrians.
- Keep LEDs accessible through a removable back or access panel.
- Keep electronics inside the head protected from dust and moisture.
- Add a safety tether for the head module.
- Bench test head lighting before mounting to the bike.

## Open Questions

- Exact eye shape and diffuser material.
- Which facets are translucent and which are mirrored.
- Exact fiber strand count per side.
- Exact connector family: M8/M12 vs waterproof LED pigtail style.
- Final pixel order inside the head.
