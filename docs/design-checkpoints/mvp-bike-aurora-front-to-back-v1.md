# MVP Bike Aurora Front-to-Back v1 Checkpoint

## Current output

- Pattern source: `software/pixelblaze-patterns/mvp-bike/aurora-front-to-back-2d.js`
- Spatial map: `software/pixelblaze-patterns/mvp-bike/mvp-bike-spatial-map.js`
- Reference pattern: `~/Projects/BM_personal_LED-projects /LED Hat Small/LED_hat_small/firmware/patterns/Archive/1D Aurora Borealis.epe`

## Accepted behavior

- Aurora curtains move from the bike front at low normalized `x` toward the rear at high normalized `x`.
- The effect uses both `x` and `y`: `x` controls travel and `y` bends and shimmers the curtains.
- The inherited palette character is green, chartreuse, turquoise, pink, and purple.
- Controls cover speed, curtain width, shimmer, brightness, saturation, palette weighting, and curtain count.
- A faint teal ambient floor maintains nighttime bike readability between curtains.

## Validation

- Source was evaluated in a Pixelblaze-compatible local harness.
- The pattern rendered 111 mapped coordinates across repeated frames without non-finite RGB output.
- Direction was checked against the current spatial-map contract: front is low `x`, rear is high `x`.
- On-device appearance and current draw remain unverified.

## Rejected or unsafe variants

- Do not use `index/pixelCount` as the primary position; it follows wiring rather than bike space.
- Do not run initial commissioning at unrestricted global brightness.
- The ambient floor is intentionally dim and is not a substitute for legally required bicycle lighting.

## Regeneration

The source is hand-authored and authoritative; there is no generator command.

## Next physical review

1. Paste the source into a new Pixelblaze pattern and save it as `01 Bike Aurora Front to Back`.
2. Confirm the mapper is saved and Pixelblaze is configured for 111 pixels.
3. Begin with the Pixelblaze global brightness limit at 15-25%.
4. Verify visible travel begins at the front and reaches the rear.
5. Tune speed, curtain width, shimmer, palette, and brightness with the pattern controls.
6. Observe the 5 V supply, wiring, and connectors for heating before increasing brightness.
