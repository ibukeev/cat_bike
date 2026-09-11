# MVP Bike Ten-Pattern Playa Set v1 Checkpoint

## Current outputs

- Collection guide: `software/pixelblaze-patterns/mvp-bike/README.md`
- Spatial mapper: `software/pixelblaze-patterns/mvp-bike/mvp-bike-spatial-map.js`
- Off-device validator: `tests/automated/validate_mvp_bike_patterns.js`
- Target: current 111-pixel MVP bike body installation

| Pattern source | Character |
|---|---|
| `aurora-front-to-back-2d.js` | Smooth traveling aurora curtains |
| `playa-techno-scanner-2d.js` | Techno scanner and synthetic kick pulses |
| `ukrainian-flag-gentle-wave-2d.js` | Calm blue/yellow fabric motion |
| `bioelectric-fur-2d.js` | Organic filaments and nerve impulses |
| `night-ride-beacon-2d.js` | Restrained continuous riding glow |
| `abyssinian-rosettes-2d.js` | Copper, aqua, and magenta signature rosettes |
| `playa-starfield-2d.js` | Smooth twinkle and traveling comets |
| `low-power-breath-2d.js` | Simple dim reserve breathing |
| `neon-circuit-packets-2d.js` | Beat-quantized circuit lanes and packets |
| `laser-lattice-techno-2d.js` | Crossing laser grid and localized beat punches |

## Accepted behavior and constraints

- Preserve a varied ten-pattern set with smooth, organic, functional, and
  techno choices rather than tuning one effect before hardware review.
- Use the established 111-pixel 2D mapper for physical motion. Low normalized
  `x` is the bike front and high `x` is the rear.
- Keep every source self-contained with Pixelblaze sliders and a 1D editor
  fallback.
- Generate all beat timing internally; no Sensor Expansion Board is required.
- Keep techno impacts spatially localized. Do not add rapid full-frame white
  strobing.
- Treat brightness sliders as visual controls, not calibrated electrical power
  limits.

## Validation performed

- Node module syntax checks passed for all six sources created or recovered in
  this continuation.
- The complete local harness passed the mapper and all ten patterns.
- The mapper returned exactly 111 finite normalized coordinates.
- Each pattern rendered 240 frames at 30 FPS, all 111 mapped pixels, its 1D
  fallback, and every slider at `0`, `0.5`, and `1`.
- Total checked color samples per pattern ranged from 28,749 to 29,748.
- No non-finite colors or out-of-range RGB, saturation, or value outputs were
  detected.
- Pixelblaze preview, physical appearance, current draw, and thermal behavior
  remain unverified.

## Rejected, unsafe, or deferred variants

- No full-frame high-frequency strobe mode was added because it can distract
  the rider and create a photosensitivity hazard.
- No pattern depends on sound input because the current MVP does not require a
  Sensor Expansion Board.
- Cat-head eyes, facets, whiskers, tail, panels, and wheels remain out of this
  mapper; their absolute whole-bike offsets are not yet established.
- These decorative LEDs do not replace the bike's independent headlight,
  taillight, or reflectors.
- No pattern was uploaded to the physical Pixelblaze in this work session.

## Exact validation command

The patterns are hand-authored and have no generation command. From the
repository root, rerun the collection validator with:

```bash
node tests/automated/validate_mvp_bike_patterns.js
```

## Next physical review

1. Configure Pixelblaze for 111 pixels and save the mapper with **Contain**.
2. Run a one-pixel chase to verify all three path directions before evaluating
   the spatial effects.
3. Load the ten sources using the saved names and order in the collection
   README.
4. Start at 15-25% Pixelblaze global brightness.
5. Review the smooth group first, then the three techno patterns, and note which
   effects are too fast, too sparse, or visually confused on the real strip
   geometry.
6. Measure supply current and inspect the converter, injection wiring,
   connectors, and strips for heating before increasing brightness.
7. Record favorite patterns and slider settings for the next tuning pass.
