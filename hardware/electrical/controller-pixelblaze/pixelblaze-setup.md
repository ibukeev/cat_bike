# Pixelblaze Setup

## Purpose

Define the draft Pixelblaze controller setup for the Cat Bike LED installation.

## Current Decisions

- Use the in-hand Pixelblaze V3 Pico as the Phase 1 controller.
- Keep the ordered Pixelblaze V3 Standard boards as hot spares/future upgrades.
- Do not use multiple controllers for this bike unless future complexity forces it.
- Mount the controller near the battery/power distribution enclosure, protected from dust, moisture, vibration, and cargo impacts.
- Use one data output initially.
- Keep the Pixelblaze Output Expander available as a future option, but do not include it in Phase 1.
- Power either controller from one dedicated Magnolora 12 V to 5 V, 3 A converter.
- Reserve a Standard-sized tray area; the insulated Pico may lie loose for the MVP.
- Keep all LED load current out of the Pixelblaze power path.

## Physical Location

Preferred controller location:

- In or near the rear power distribution area.
- Protected enclosure near the under-rack / behind-seat / basket-area power box.
- Close to the protected 12 V distribution and dedicated 5 V controller converter.
- Accessible enough for service, reset, and Wi-Fi setup.

Avoid:

- Front/head tube area as the main controller location.
- Exposed mounting on the frame.
- Locations that block battery removal, rider movement, cargo use, or future tail/head mounting.

## Segment Concept

Pixelblaze sees LEDs as one indexed pixel chain:

```text
pixel 0, pixel 1, pixel 2, ... pixel N
```

A segment map documents which index ranges correspond to physical bike zones.

Example:

```text
pixels 0-89    = lower frame spine
pixels 90-129  = fork accents
pixels 130-199 = rear rack/basket
```

This allows patterns to treat physical zones differently even when the LEDs are wired as one data chain.

## Initial Output Strategy

Use one Pixelblaze data output for Phase 1.

Initial physical data order can be chosen for clean wiring, not visual order. For example:

```text
Pixelblaze data out
  -> rear rack/basket
  -> lower frame spine
  -> fork/front accents
```

The final order must be documented in the LED segment map before writing zone-specific patterns.

## Draft Logical Segments

| Segment | Physical Zone | Phase | Status |
|---|---|---|---|
| S0 | Lower frame segmented spine | Phase 1 | Draft |
| S1 | Fork gill accents | Phase 1 | Draft |
| S2 | Rear rack rib accents | Phase 1 | Draft |
| S3 | Basket underside glow | Phase 1 | Draft |
| S4 | Ground underglow | Phase 1 | Draft |
| S5 | 52-pixel cat head: whiskers, eyes, and fourteen glow facets | Phase 2A | Local map locked; absolute offset pending |
| S6 | Tail | Phase 2B | Reserved |
| S7 | Body panels | Phase 3 | Reserved |
| S8 | Optional wheels | Phase 4 | Deferred |

## Output Expander

An output expander is available in-house, but it is not part of the Phase 1 plan.

Use it later only if:

- The physical data wiring becomes awkward with one output.
- Body panels need separate data paths.
- A measured full-harness test shows that the terminating 52-pixel cat head cannot run reliably on the initial output.
- Refresh rate or pixel count becomes a real limitation.

## Mode Plan

| Mode | Intent | Brightness Cap |
|---|---|---:|
| Riding | Clear visibility with restrained motion | 25-35% |
| Parked/show | Brighter bioluminescent effects | 50-60% |
| Low-power reserve | End-of-night safe visibility | 10-15% |

## Open Items

- Identify the Pico antenna end and insulate the board without covering it.
- Measure a Standard board when it arrives and finalize its interchangeable carrier.
- Configure the Pico and verify the dedicated 5 V controller power connector polarity.
- Assign the absolute S5 start offset after preceding whole-bike zones are measured.
- Integrate the locked head-local 0-51 map into the whole-bike segment map.
- Bench test current draw and brightness caps before bike installation.
