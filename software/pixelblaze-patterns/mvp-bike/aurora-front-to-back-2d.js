// Cat Bike — Aurora Front to Back 2D
//
// Requires the 111-pixel MVP bike spatial map.
// Pixelblaze normalizes the map so the front of the bike is low x and the rear
// is high x. Every aurora curtain therefore travels in the +x direction.
//
// Adapted from the owner's archived "1D Aurora Borealis" hat pattern.

var colorPalettes = [
  [17, 177, 13],
  [148, 242, 5],
  [25, 173, 121],
  [250, 77, 127],
  [171, 101, 221]
];

var paletteWeights = [
  [20, 20, 20, 20, 20], // Balanced
  [11, 11, 12, 33, 33], // Pink and purple
  [6, 6, 6, 2, 1]       // Green and turquoise
];

function scaleBetween(low, high, value) {
  return low + value * (high - low);
}

function randomBetween(low, high) {
  return scaleBetween(low, high, random(1));
}

function getRandomColorIndex(whichPreset) {
  var weights = paletteWeights[whichPreset];
  var total = 0;
  var choice;
  var i;

  for (i = 0; i < weights.length; i++) total += weights[i];
  choice = random(total);

  for (i = 0; i < weights.length; i++) {
    if (choice < weights[i]) return i;
    choice -= weights[i];
  }

  return 0;
}

var CENTER = 0;
var WIDTH_SCALE = 1;
var COLOR = 2;
var ALPHA = 3;
var SPEED_SCALE = 4;
var BEND = 5;
var FREQUENCY = 6;
var PHASE = 7;
var WAVE_SIZE = 8;

var maxWaves = 8;
var waves = array(maxWaves);
var i;

for (i = 0; i < maxWaves; i++) waves[i] = array(WAVE_SIZE);

export var speedFactor = 1;
export var widthFactor = 0.14;
export var shimmerAmount = 0.55;
export var masterBrightness = 0.75;
export var masterSaturation = 0.9;
export var whichPalette = 2;
export var numWaves = 5;

export function sliderSpeed(v) {
  // Wide nonlinear range: precise slow motion on the left, energetic on right.
  speedFactor = 0.15 + v * v * 2.85;
}

export function sliderCurtainWidth(v) {
  widthFactor = scaleBetween(0.035, 0.26, v);
}

export function sliderShimmer(v) {
  shimmerAmount = scaleBetween(0.05, 1, v);
}

export function sliderBrightness(v) {
  masterBrightness = scaleBetween(0.08, 1, v);
}

export function sliderSaturation(v) {
  masterSaturation = scaleBetween(0.35, 1, v);
}

export function sliderPalette(v) {
  whichPalette = floor(scaleBetween(0, paletteWeights.length - 0.01, v));

  // Make palette changes visible immediately instead of waiting for respawns.
  for (i = 0; i < maxWaves; i++) {
    waves[i][COLOR] = getRandomColorIndex(whichPalette);
  }
}

export function sliderNumberOfCurtains(v) {
  numWaves = floor(scaleBetween(2, maxWaves + 0.99, v));
}

function spawnWave(waveData, fillBikeImmediately) {
  var width = widthFactor * randomBetween(0.55, 1);

  waveData[WIDTH_SCALE] = randomBetween(0.55, 1);
  waveData[CENTER] = fillBikeImmediately
    ? randomBetween(-width, 1 + width)
    : -width - randomBetween(0.02, 0.3);
  waveData[COLOR] = getRandomColorIndex(whichPalette);
  waveData[ALPHA] = randomBetween(0.45, 0.95);
  waveData[SPEED_SCALE] = randomBetween(0.7, 1.35);
  waveData[BEND] = randomBetween(0.025, 0.11);
  waveData[FREQUENCY] = randomBetween(0.7, 2.4);
  waveData[PHASE] = random(1);
}

var shimmerClock = 0;

export function beforeRender(delta) {
  shimmerClock += delta * 0.000025 * (0.25 + shimmerAmount);
  shimmerClock -= floor(shimmerClock);

  for (i = 0; i < numWaves; i++) {
    var waveData = waves[i];

    if (waveData[SPEED_SCALE] == 0) {
      spawnWave(waveData, true);
    } else {
      // Positive motion is always from the front (low x) to rear (high x).
      waveData[CENTER] +=
        delta * 0.001 * 0.055 * waveData[SPEED_SCALE] * speedFactor;

      var width = widthFactor * waveData[WIDTH_SCALE];
      if (waveData[CENTER] - width > 1) spawnWave(waveData, false);
    }
  }
}

export function render2D(index, x, y) {
  var mixedR = 0;
  var mixedG = 0;
  var mixedB = 0;

  for (i = 0; i < numWaves; i++) {
    var waveData = waves[i];
    var width = widthFactor * waveData[WIDTH_SCALE];

    // Use y to bend and shimmer each curtain, making the effect spatial rather
    // than merely replacing index/pixelCount with x.
    var bend =
      sin(
        PI2 * (
          y * waveData[FREQUENCY] +
          waveData[PHASE] +
          shimmerClock * (0.7 + i * 0.09)
        )
      ) *
      waveData[BEND] *
      shimmerAmount;

    var curtainCenter = waveData[CENTER] + bend;
    var offset = abs(x - curtainCenter);

    if (offset <= width) {
      var edge = 1 - offset / width;
      edge *= edge;

      var verticalShimmer =
        0.58 +
        0.42 * wave(
          y * (waveData[FREQUENCY] + 0.6) +
          shimmerClock * (1.1 + i * 0.07) +
          waveData[PHASE]
        );

      // Fade curtains smoothly at the front and rear world boundaries.
      var travelFade =
        clamp((waveData[CENTER] + width) / (width * 2), 0, 1) *
        clamp((1 + width - waveData[CENTER]) / (width * 2), 0, 1);

      var alpha =
        edge *
        verticalShimmer *
        travelFade *
        waveData[ALPHA];

      var color = colorPalettes[waveData[COLOR]];
      var red = color[0] / 255;
      var green = color[1] / 255;
      var blue = color[2] / 255;
      var gray = (red + green + blue) / 3;

      red = gray + (red - gray) * masterSaturation;
      green = gray + (green - gray) * masterSaturation;
      blue = gray + (blue - gray) * masterSaturation;

      // Alpha blend overlapping curtains.
      mixedR = red * alpha + mixedR * (1 - alpha);
      mixedG = green * alpha + mixedG * (1 - alpha);
      mixedB = blue * alpha + mixedB * (1 - alpha);
    }
  }

  // A dim teal floor keeps the bike readable between aurora curtains.
  var ambient = 0.008 + 0.018 * wave(y * 1.7 + shimmerClock * 0.35);
  mixedG += ambient;
  mixedB += ambient * 1.35;

  rgb(
    clamp(mixedR * masterBrightness, 0, 1),
    clamp(mixedG * masterBrightness, 0, 1),
    clamp(mixedB * masterBrightness, 0, 1)
  );
}

// Safe fallback when the pattern is previewed without a 2D map.
export function render(index) {
  render2D(index, index / pixelCount, 0.5);
}
