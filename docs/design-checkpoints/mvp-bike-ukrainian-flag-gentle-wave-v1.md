# MVP Bike Ukrainian Flag Gentle Wave v1 Checkpoint

## Current output

- Pattern source: `software/pixelblaze-patterns/mvp-bike/ukrainian-flag-gentle-wave-2d.js`
- Spatial map: `software/pixelblaze-patterns/mvp-bike/mvp-bike-spatial-map.js`
- Hat reference: `Ukrainian Flag.epe` in the LED Hat Small archive.

## Accepted behavior

- The visual remains predominantly a static Ukrainian flag: blue above and yellow below.
- A small boundary ripple and mild fabric shading move from the bike front toward the rear.
- No strobe, blink, or Sensor Expansion Board behavior is included.
- Controls cover band boundary, boundary softness, ripple amount, motion speed, fabric shading, and brightness.
- Default motion is intentionally slow and restrained.

## Validation

- Source was evaluated in a Pixelblaze-compatible local harness.
- The pattern rendered 111 mapped coordinates across repeated frames without non-finite or out-of-range RGB output.
- On-device color appearance and current draw remain unverified.

## Rejected or unsafe variants

- The hat pattern's strobe and blink modes are intentionally omitted.
- Do not use rapid full-frame flashes during riding.
- Do not commission at unrestricted global brightness.

## Regeneration

The source is hand-authored and authoritative; there is no generator command.

## Next physical review

1. Paste the source into Pixelblaze and save it as `03 Ukrainian Flag Gentle Wave`.
2. Start with global brightness limited to 15-25%.
3. Confirm upper spatial pixels are blue and lower spatial pixels are yellow.
4. Confirm the gentle fold motion travels from front to rear.
5. Adjust the blue/yellow boundary if the sparse bike geometry favors one band.
