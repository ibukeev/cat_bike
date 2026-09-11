# MVP Bike Spatial Map v2 Checkpoint

## Current output

- Mapper source: `software/pixelblaze-patterns/mvp-bike/mvp-bike-spatial-map.js`
- Review overlay: `software/pixelblaze-patterns/mvp-bike/mvp-bike-spatial-map-review.svg`
- Review generator: `software/tools/generate_mvp_bike_spatial_map_review.js`
- Source photo: `assets/photos/Original_bike/pixed LAYAOUT.jpg`

## Accepted interpretation

- Configure 111 pixels.
- The three numbered red arrows are the centerlines and data directions.
- Section 1 is pixels 1-31, following the upper rear frame toward the rack.
- Section 2 is pixels 32-59, following the lower rear frame from the rear axle toward the crank.
- Section 3 is pixels 60-111, starting at the seat/battery edge, descending through the step-through curve, and rising toward the front stem.
- The handwritten numerals are labels rather than illuminated geometry.

## Validation

- The mapper returns exactly 111 finite 2D coordinates.
- Counts are 31, 28, and 52.
- The SVG overlays every generated pixel on the annotated photograph and labels each section start and end.
- Pixelblaze preview and a physical one-pixel chase remain pending.

## Rejected variants

- V1 reduced the arrows to generic straight runs and omitted important bends.
- V1 incorrectly started section 3 near the crank.
- Do not treat the handwritten numerals or arrowheads as extra LED branches.

## Exact regeneration command

From the repository root:

```bash
node software/tools/generate_mvp_bike_spatial_map_review.js
```

## Next physical review

1. Open the SVG and confirm each colored line follows the corresponding red arrow.
2. Paste the mapper into Pixelblaze with 111 pixels and `Contain` selected.
3. Run a one-pixel chase to confirm starts, ends, and increasing-index direction.
4. Record any installed pixels whose spacing differs from uniform spacing along the arrows.
