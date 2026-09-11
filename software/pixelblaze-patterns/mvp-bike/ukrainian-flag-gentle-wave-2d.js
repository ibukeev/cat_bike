// Cat Bike — Ukrainian Flag Gentle Wave 2D
//
// Mostly static Ukrainian flag colors with a mild spatial fabric ripple.
// Requires the 111-pixel MVP bike spatial map.
//
// Coordinate convention: y=0 is the top of the bike map and y=1 is the bottom.
// Wind ripples travel from the bike front (low x) toward the rear (high x).

// Ukrainian flag colors: blue #0057B8 and yellow #FFD700.
var blueR = 0;
var blueG = 0.341;
var blueB = 0.722;

var yellowR = 1;
var yellowG = 0.843;
var yellowB = 0;

export var bandSplit = 0.5;
export var bandSoftness = 0.025;
export var rippleAmount = 0.028;
export var motionSpeed = 0.016;
export var masterBrightness = 0.72;
export var fabricShading = 0.1;

function scaleBetween(low, high, value) {
  return low + value * (high - low);
}

function smoothstep(edge0, edge1, value) {
  var amount = clamp((value - edge0) / (edge1 - edge0), 0, 1);
  return amount * amount * (3 - 2 * amount);
}

export function sliderBlueYellowBoundary(v) {
  bandSplit = scaleBetween(0.35, 0.65, v);
}

export function sliderBoundarySoftness(v) {
  bandSoftness = scaleBetween(0.004, 0.12, v);
}

export function sliderGentleRipple(v) {
  rippleAmount = scaleBetween(0, 0.085, v);
}

export function sliderMotionSpeed(v) {
  // Approximately one spatial cycle every 200 seconds at the far left and
  // every 12 seconds at the far right.
  motionSpeed = scaleBetween(0.005, 0.08, v * v);
}

export function sliderFabricShading(v) {
  fabricShading = scaleBetween(0, 0.22, v);
}

export function sliderBrightness(v) {
  masterBrightness = scaleBetween(0.08, 1, v);
}

var motionPhase = 0;

export function beforeRender(delta) {
  motionPhase += delta * 0.001 * motionSpeed;
  motionPhase -= floor(motionPhase);
}

export function render2D(index, x, y) {
  // x-motion is x - phase, so the subtle folds travel front to rear.
  var primaryFold = sin(PI2 * (x * 1.15 - motionPhase));
  var secondaryFold =
    sin(PI2 * (x * 2.35 - motionPhase * 1.43 + y * 0.3));

  // Move only the boundary slightly; the two broad flag bands remain dominant.
  var wavingBoundary =
    bandSplit +
    rippleAmount * (primaryFold * 0.72 + secondaryFold * 0.28);

  // blueMix=1 above the boundary; blueMix=0 below it.
  var blueMix =
    1 -
    smoothstep(
      wavingBoundary - bandSoftness,
      wavingBoundary + bandSoftness,
      y
    );

  var red = yellowR + (blueR - yellowR) * blueMix;
  var green = yellowG + (blueG - yellowG) * blueMix;
  var blue = yellowB + (blueB - yellowB) * blueMix;

  // Very mild traveling illumination suggests fabric without obscuring color.
  var foldLight =
    1 -
    fabricShading * 0.5 +
    fabricShading * 0.5 *
      wave(x * 1.7 - motionPhase + y * 0.22);

  rgb(
    clamp(red * foldLight * masterBrightness, 0, 1),
    clamp(green * foldLight * masterBrightness, 0, 1),
    clamp(blue * foldLight * masterBrightness, 0, 1)
  );
}

// Safe fallback when previewed without a 2D map.
export function render(index) {
  render2D(index, index / pixelCount, 0.5);
}
