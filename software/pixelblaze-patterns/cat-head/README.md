# Cat Head Pixelblaze Development Files

These files implement the head-local 52-pixel map defined by the formal
cat-head lighting development plan.

## Files

- cat-head-pixel-map.json: machine-readable wiring and optical allocation.
- cat-head-commissioning.js: isolated-head pixel and zone test pattern.
- cat-head-modes.js: riding, parked/show, and reserve behavior scaffold.

## Bench Setup

Configure Pixelblaze for 52 WS2812/SK6812-compatible RGB pixels and connect the
head or coupon as an isolated chain starting at pixel zero.

The physical data order is:

1. Left whisker carrier, including masked pixel H07.
2. Left eye.
3. Fourteen glow panels in Gate 1 pair order, left then right.
4. Right eye.
5. Right whisker carrier, including masked pixel H51.

Power the modules in parallel. Do not route the complete head current through
the first pixel module or through a long strip-copper path.

## Whole-Bike Integration

The patterns in this folder use head-local indices 0-51. When the head is
integrated into the whole-bike S5 range, apply the final S5 start offset before
using the same segment logic. Keep the head last on the initial single
Pixelblaze data output so removing it does not interrupt earlier zones.

The two reserved carrier pixels, H07 and H51, must remain black in every normal
pattern.

## Physical Calibration

These patterns are development scaffolds, not evidence that an optical gate has
passed. After Gate L1:

- Calibrate per-whisker brightness only if measured coupling variation requires
  it.
- Tune eye brightness after diffuser material and setback are locked.
- Tune each facet pair after the production cassettes are installed.
- Record measured current and final brightness caps in the validation report.
