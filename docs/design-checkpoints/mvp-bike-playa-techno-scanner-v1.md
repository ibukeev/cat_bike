# MVP Bike Playa Techno Scanner v1 Checkpoint

## Current output

- Pattern source: `software/pixelblaze-patterns/mvp-bike/playa-techno-scanner-2d.js`
- Spatial map: `software/pixelblaze-patterns/mvp-bike/mvp-bike-spatial-map.js`
- Hat references: `Tunnel Scanner.epe` and `Riot Pulse.epe` in the LED Hat Small archive.

## Accepted behavior

- A hard scanner bounces across normalized bike space.
- Each internally generated techno kick launches an additional pulse from front to rear.
- The effect uses `y` for spatial tilt and moving grit, preventing the three physical runs from behaving as duplicated 1D strips.
- No audio sensor is required.
- Controls cover BPM, scanner speed, width, trail, kick strength, color, spatial tilt, grit, and brightness.
- Beat energy remains spatially localized rather than using continuous full-frame strobing.

## Validation

- Source was evaluated in a Pixelblaze-compatible local harness.
- The pattern rendered 111 mapped coordinates across repeated frames without non-finite color output.
- On-device appearance and current draw remain unverified.

## Rejected or unsafe variants

- The original hat references rely on Sensor Expansion Board data; this MVP version does not.
- Avoid continuous full-frame high-frequency strobing because of rider distraction and photosensitivity risk.
- Do not commission at unrestricted global brightness.

## Regeneration

The source is hand-authored and authoritative; there is no generator command.

## Next physical review

1. Paste the source into Pixelblaze and save it as `02 Playa Techno Scanner`.
2. Start with global brightness limited to 15-25%.
3. Confirm the kick pulse always travels from the bike front toward the rear.
4. Tune BPM near 120-135 for the intended techno feel.
5. Verify wiring and connectors remain cool before increasing brightness.
