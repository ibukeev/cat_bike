# MVP Bike Pixelblaze Pattern Set

This folder contains ten playa-riding patterns for the current 111-pixel bike
installation. Every visual pattern uses the same physical 2D mapper and also
includes a 1D fallback for editor preview.

## One-time Pixelblaze setup

1. Set **Settings > Pixels** to `111`.
2. Open the Mapper editor and paste `mvp-bike-spatial-map.js`.
3. Select **Contain** so the photographed bike proportions are preserved.
4. Save the mapper, then create one Pixelblaze pattern for each `*-2d.js` file.

The current mapper covers only the three established MVP body runs. It does not
yet include the later cat-head, whisker, eye, tail, panel, or wheel zones.

## Suggested saved order

| Order | Pixelblaze name | Source | Feel | Role |
|---:|---|---|---|---|
| 01 | Bike Aurora Front to Back | `aurora-front-to-back-2d.js` | Smooth | Flowing ambient color |
| 02 | Playa Techno Scanner | `playa-techno-scanner-2d.js` | Techno | Bouncing scanner and synthetic kick pulses |
| 03 | Ukrainian Flag Gentle Wave | `ukrainian-flag-gentle-wave-2d.js` | Smooth | Calm flag colors with restrained motion |
| 04 | Bioelectric Fur | `bioelectric-fur-2d.js` | Organic | Fine filaments and rear-to-front nerve impulses |
| 05 | Night Ride Beacon | `night-ride-beacon-2d.js` | Smooth | Continuous riding visibility and spatial orientation |
| 06 | Abyssinian Rosettes | `abyssinian-rosettes-2d.js` | Organic | Signature copper, aqua, and magenta cat identity |
| 07 | Playa Starfield | `playa-starfield-2d.js` | Smooth/show | Twinkling field with front-to-rear comets |
| 08 | Low Power Breath | `low-power-breath-2d.js` | Smooth | Simple continuously visible reserve mode |
| 09 | Neon Circuit Packets | `neon-circuit-packets-2d.js` | Techno | Beat-quantized, lane-switching data packets |
| 10 | Laser Lattice Techno | `laser-lattice-techno-2d.js` | Techno | Sliding laser grid with localized beat punches |

Each source exports its own Pixelblaze sliders. Defaults are starting points,
not calibrated electrical limits.

## Bench and bike testing

- Start physical commissioning with Pixelblaze global brightness at 15-25%.
- Verify the mapper with a one-pixel chase before judging spatial direction.
- Confirm that low `x` is the front and high `x` is the rear.
- Watch the 5 V supply, injection wiring, connectors, and strips for heating.
- Measure actual current before raising the global brightness limit.
- Keep the bike's independent headlight, taillight, and reflectors in service;
  these decorative patterns are not replacements for required safety lighting.

Run the off-device syntax and render-math check from the repository root:

```bash
node tests/automated/validate_mvp_bike_patterns.js
```

The local check catches parse errors, missing render entry points, non-finite
color output, out-of-range RGB/SV output, mapper count errors, and failures at
slider endpoints. Pixelblaze preview, visual quality, current draw, and thermal
behavior still require physical review.
