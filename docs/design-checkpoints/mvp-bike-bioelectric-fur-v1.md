# MVP Bike Bioelectric Fur v1 Checkpoint

## Current output

- Pattern: `software/pixelblaze-patterns/mvp-bike/bioelectric-fur-2d.js`
- Spatial mapper: `software/pixelblaze-patterns/mvp-bike/mvp-bike-spatial-map.js`
- Target: the current 111-pixel MVP bike installation

## Accepted behavior

- Render fine, organic cyan-to-violet filaments over the whole bike.
- Send periodic electrical impulses from the rear (high x) toward the front
  (low x).
- Keep the effect internally timed; do not require a Sensor Expansion Board.
- Provide controls for motion speed, fur density, fur contrast, impulse rate,
  impulse strength, impulse width, color, and master brightness.
- Include a 1D fallback so the pattern remains visible before a 2D mapper is
  selected.

## Validation

- Static JavaScript syntax check: passed with Node's module parser.
- Render-math harness: passed 79,920 samples across 720 frames and all 111
  normalized mapper coordinates; every HSV output was finite and saturation and
  value remained within 0-1.
- Observed simulated value range with defaults: 0.020329-0.785307.
- 1D fallback render: passed with finite output.
- Pixelblaze 2D preview: pending user review.
- Physical 111-pixel bike review: pending.

## Rejected or deferred variants

- Do not synchronize the cat-head eyes, facets, or whiskers in this version;
  the current output targets only the established 111-pixel MVP bike map.
- Do not require sound input or the Sensor Expansion Board.
- Avoid full-frame white flashes; bright sparks remain localized around the
  traveling impulse.

## Exact regeneration command

This pattern is hand-authored and has no generation step. To perform the local
syntax check from the repository root:

```bash
node --input-type=module --check < software/pixelblaze-patterns/mvp-bike/bioelectric-fur-2d.js
```

## Next physical review

1. Configure Pixelblaze for 111 pixels.
2. Load `mvp-bike-spatial-map.js` as the mapper and select `Contain`.
3. Paste `bioelectric-fur-2d.js` into a new Pixelblaze pattern.
4. Confirm that each impulse travels from the rear toward the front.
5. Start with the default brightness, then tune it against the installed power
   limit and nighttime viewing distance.
6. Report whether the fur should be calmer, sharper, denser, or more colorful
   before starting the next pattern.
