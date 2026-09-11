# MVP Bike Spatial Map v1 Checkpoint — Superseded

This simplified trace was rejected because it did not follow all bends shown by
the annotated data-direction arrows. Section 3 also started at the wrong
physical location. Use the v2 checkpoint and current mapper source instead.

## Current output

- Mapper source: `software/pixelblaze-patterns/mvp-bike/mvp-bike-spatial-map.js`
- Visual reference: `assets/photos/Original_bike/pixed LAYAOUT.jpg`

## Accepted layout

- Pixelblaze pixel count: 111.
- Section 1 is pixels 1-31 (31 pixels), directed from the seat area toward the rear rack.
- Section 2 is pixels 32-59 (28 pixels), directed from the rear wheel toward the crank.
- Section 3 is pixels 60-111 (52 pixels), directed from the crank/floorboard toward the front stem.
- The map is 2D and uses image-relative coordinates traced approximately from the marked-up reference photograph.
- Select `Contain` in the Mapper normalization control to preserve the bike proportions.

## Validation

- Inclusive section counts sum to 111: 31 + 28 + 52.
- Each section is sampled independently along a polyline in physical wiring order.
- On-device Mapper preview and physical LED direction have not yet been verified.

## Rejected or unsafe variants

- Do not configure 110 pixels: the installation labels are one-based and include pixel 111.
- Do not use `Fill` when physical proportions matter; it stretches both axes independently.
- This photo trace is not a dimensionally measured map and should not be treated as fabrication geometry.

## Regeneration

The mapper is hand-authored; there is no generator command. The checked-in mapper source is the authoritative resumable artifact.

## Next physical review

1. Set `Settings > Pixels` to 111 in Pixelblaze.
2. Paste the mapper source, select `Contain`, and confirm that the preview shows three separate paths.
3. Run a single-pixel chase to verify the direction and endpoints of all three sections.
4. Adjust polyline control points if measured mounting positions differ from the photo trace.
