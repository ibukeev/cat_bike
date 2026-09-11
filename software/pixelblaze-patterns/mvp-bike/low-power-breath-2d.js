// Cat Bike — Low Power Breath 2D
//
// A deliberately simple reserve pattern for the 111-pixel MVP bike map. The
// bike remains continuously visible in a dim aqua glow with slow breathing and
// a very small spatial drift. There are no flashes, random events, or blackouts.

export var masterBrightness = 0.14;
export var breathSpeed = 0.045;
export var breathDepth = 0.2;
export var visibilityFloor = 0.76;
export var spatialDrift = 0.055;
export var baseHue = 0.49;
export var saturation = 0.88;

function scaleBetween(low, high, value) {
  return low + value * (high - low);
}

export function sliderReserveBrightness(v) {
  // Intentionally capped at 35% inside the pattern.
  masterBrightness = scaleBetween(0.04, 0.35, v);
}

export function sliderBreathingSpeed(v) {
  breathSpeed = scaleBetween(0.012, 0.13, v * v);
}

export function sliderBreathingDepth(v) {
  breathDepth = scaleBetween(0, 0.38, v);
}

export function sliderVisibilityFloor(v) {
  visibilityFloor = scaleBetween(0.5, 1, v);
}

export function sliderSpatialDrift(v) {
  spatialDrift = scaleBetween(0, 0.12, v);
}

export function sliderColor(v) {
  baseHue = v;
}

export function sliderSaturation(v) {
  saturation = scaleBetween(0.35, 1, v);
}

var breathClock = 0;

export function beforeRender(delta) {
  breathClock += delta * 0.001 * breathSpeed;
  breathClock -= floor(breathClock);
}

export function render2D(index, x, y) {
  var breath = wave(breathClock);
  var level =
    visibilityFloor +
    (1 - visibilityFloor) * breath * breathDepth;
  var drift =
    1 -
    spatialDrift * 0.5 +
    spatialDrift * 0.5 * wave(x * 0.85 - breathClock * 0.2 + y * 0.24);
  var value = clamp(masterBrightness * level * drift, 0, 0.35);
  var hue = baseHue + (x - 0.5) * 0.035;

  hsv(hue, saturation, value);
}

// Safe fallback when previewed without a 2D map.
export function render(index) {
  render2D(index, index / pixelCount, 0.5);
}
