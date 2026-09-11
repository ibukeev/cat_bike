// Cat Bike — Playa Starfield 2D
//
// A parked/show pattern for the 111-pixel MVP bike spatial map. Individually
// seeded cyan and violet stars twinkle over a dim night field while an
// occasional comet crosses from the bike front (low x) to rear (high x).
// All timing is internal; no Sensor Expansion Board is required.

export var starDensity = 0.32;
export var twinkleSpeed = 0.18;
export var twinkleContrast = 0.72;
export var cometRate = 0.055;
export var cometStrength = 0.82;
export var cometTrail = 0.42;
export var colorHue = 0.51;
export var masterBrightness = 0.72;

function scaleBetween(low, high, value) {
  return low + value * (high - low);
}

function smoothstep(edge0, edge1, value) {
  var amount = clamp((value - edge0) / (edge1 - edge0), 0, 1);
  return amount * amount * (3 - 2 * amount);
}

export function sliderStarDensity(v) {
  starDensity = scaleBetween(0.1, 0.72, v);
}

export function sliderTwinkleSpeed(v) {
  twinkleSpeed = scaleBetween(0.035, 0.65, v * v);
}

export function sliderTwinkleContrast(v) {
  twinkleContrast = scaleBetween(0.15, 1, v);
}

export function sliderCometRate(v) {
  // Approximately one crossing every 40 seconds to every 5 seconds.
  cometRate = scaleBetween(0.025, 0.2, v * v);
}

export function sliderCometStrength(v) {
  cometStrength = v;
}

export function sliderCometTrail(v) {
  cometTrail = scaleBetween(0.08, 0.72, v);
}

export function sliderColor(v) {
  colorHue = v;
}

export function sliderBrightness(v) {
  masterBrightness = scaleBetween(0.08, 1, v);
}

var twinkleClock = 0;
var cometClock = 0;

export function beforeRender(delta) {
  twinkleClock += delta * 0.001 * twinkleSpeed;
  cometClock += delta * 0.001 * cometRate;

  if (twinkleClock > 4096) twinkleClock -= 4096;
  cometClock -= floor(cometClock);
}

export function render2D(index, x, y) {
  // Golden-ratio-like index steps provide stable pseudo-random star placement
  // without calling random() once per pixel and frame.
  var starSeed = wave(index * 0.6180339 + 0.137);
  var rateSeed = wave(index * 0.4142136 + 0.731);
  var colorSeed = wave(index * 0.7548777 + 0.293);
  var starGate = smoothstep(
    1 - starDensity,
    1 - starDensity + 0.07,
    starSeed
  );
  var twinkle = pow(
    wave(
      twinkleClock * (0.42 + rateSeed * 1.25) +
      starSeed * 2.7
    ),
    5
  );
  var starValue =
    starGate *
    (0.025 + twinkle * (0.12 + twinkleContrast * 0.38));

  var cometPhase = cometClock - floor(cometClock);
  var cometX = cometPhase * 1.42 - 0.21;
  var cometY =
    0.5 +
    0.15 * sin(PI2 * (cometX * 0.72 + 0.12));
  var dx = x - cometX;
  var dy = y - cometY;
  var cometHead = exp(-pow(dx / 0.055, 2) - pow(dy / 0.12, 2));

  var behind = cometX - x;
  var cometTailValue = 0;
  if (behind > 0 && behind < cometTrail) {
    var tailCenterY =
      0.5 +
      0.15 * sin(PI2 * (x * 0.72 + 0.12));
    cometTailValue =
      exp(-behind / (0.035 + cometTrail * 0.32)) *
      exp(-pow((y - tailCenterY) / 0.14, 2));
  }

  var comet =
    (cometHead + cometTailValue * 0.55) * cometStrength;
  var value = clamp(
    (0.004 + starValue + comet) * masterBrightness,
    0,
    1
  );

  // Comet heads approach white; stars range across aqua and violet.
  var hue = colorHue + colorSeed * 0.18 + cometTailValue * 0.08;
  var saturation = clamp(0.9 - cometHead * 0.76, 0.12, 0.92);
  hsv(hue, saturation, value);
}

// Safe fallback when previewed without a 2D map.
export function render(index) {
  render2D(index, index / pixelCount, 0.5);
}
