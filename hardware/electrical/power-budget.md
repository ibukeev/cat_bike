# Power Budget

## Purpose

Estimate LED current, battery needs, fuse sizing, and runtime for the Cat Bike LED installation.

## Current Assumptions

- Controller: Pixelblaze or Pixelblaze-compatible setup.
- Main visual palette: cyan/aqua/magenta/violet with brightness limits.
- Bike use case: Burning Man night riding with a lower-power riding mode and brighter parked/show mode.
- Final LED type and count are not selected yet.

## LED Count Estimate

| Zone | Estimated Pixels | Notes |
|---|---:|---|
| Frame underglow | TBD | Measure frame tubes before selecting density. |
| Fork/front frame | TBD | Must preserve brake and tire clearance. |
| Rear rack or basket | TBD | Existing structure may support longer runs. |
| Cat head facets | TBD | Depends on head size and panel design. |
| Eyes | TBD | Likely small but bright. |
| Whiskers | TBD | Depends on fiber or LED filament choice. |
| Tail | TBD | Depends on rigid/flexible tail design. |
| Optional wheels | TBD | Deferred until fixed zones are designed. |

## Current Estimate Formula

For WS2812-style 5 V pixels, worst-case current is commonly estimated as:

```text
max_current_amps = pixel_count * 0.06
```

For practical animation use, plan a brightness-limited estimate:

```text
typical_current_amps = max_current_amps * brightness_limit * pattern_factor
```

Initial planning values:

- `brightness_limit`: 0.25 to 0.50
- `pattern_factor`: 0.35 to 0.70

## Design Targets

- Fuse the LED supply close to the battery.
- Include a reachable master switch or emergency disconnect.
- Keep controller power separate from high-current LED injection paths where practical.
- Use power injection for long LED runs.
- Document voltage drop assumptions before final wiring.

## Runtime Planning

| Mode | Brightness | Runtime Target | Notes |
|---|---:|---:|---|
| Riding | Low/medium | TBD | Prioritize visibility and battery life. |
| Parked/show | Medium/high | TBD | Higher brightness is acceptable for shorter duration. |
| Low power | Low | TBD | Backup mode for end-of-night riding. |

## Decisions Needed

- LED voltage: 5 V vs 12 V addressable LEDs.
- Battery source: dedicated LED battery vs bike battery tap.
- Target runtime.
- Maximum acceptable LED brightness.
- Whether wheel lighting is in the first electrical design.
