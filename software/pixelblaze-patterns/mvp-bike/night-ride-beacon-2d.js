// Cat Bike — Night Ride Beacon 2D
//
// A restrained, continuously visible riding pattern for the 111-pixel MVP
// bike spatial map. The center of the bike stays aqua, the front is cool pale
// cyan, and the rear is warm red-orange. A slow route pulse adds motion without
// making the bike disappear between beats.
//
// This decorative pattern does not replace the bike's required headlight,
// taillight, or reflectors.

export var masterBrightness = 0.34;
export var motionAmount = 0.13;
export var routeSpeed = 0.045;
export var breathingSpeed = 0.055;
export var frontAccent = 0.58;
export var rearAccent = 0.78;

function scaleBetween(low, high, value) {
  return low + value * (high - low);
}

function smoothstep(edge0, edge1, value) {
  var amount = clamp((value - edge0) / (edge1 - edge0), 0, 1);
  return amount * amount * (3 - 2 * amount);
}

export function sliderBrightness(v) {
  masterBrightness = scaleBetween(0.08, 0.62, v);
}

export function sliderMotion(v) {
  motionAmount = scaleBetween(0, 0.32, v);
}

export function sliderRoutePulseSpeed(v) {
  // Approximately one crossing every 50 seconds to every 5 seconds.
  routeSpeed = scaleBetween(0.02, 0.2, v * v);
}

export function sliderBreathingSpeed(v) {
  breathingSpeed = scaleBetween(0.018, 0.16, v * v);
}

export function sliderFrontAccent(v) {
  frontAccent = v;
}

export function sliderRearAccent(v) {
  rearAccent = v;
}

var routeClock = 0;
var breathClock = 0;

export function beforeRender(delta) {
  routeClock += delta * 0.001 * routeSpeed;
  breathClock += delta * 0.001 * breathingSpeed;

  routeClock -= floor(routeClock);
  breathClock -= floor(breathClock);
}

export function render2D(index, x, y) {
  var frontMask =
    (1 - smoothstep(0.08, 0.36, x)) * frontAccent;
  var rearMask =
    smoothstep(0.66, 0.93, x) * rearAccent;

  // Base aqua side glow.
  var red = 0.025;
  var green = 0.72;
  var blue = 0.9;

  // Pale cyan at the front improves visual orientation without imitating the
  // independent white headlight.
  red += (0.58 - red) * frontMask;
  green += (0.9 - green) * frontMask;
  blue += (1 - blue) * frontMask;

  // Blend the rear toward warm red-orange. Keep this subordinate to the
  // independent taillight.
  red += (1 - red) * rearMask;
  green += (0.075 - green) * rearMask;
  blue += (0.012 - blue) * rearMask;

  var routePhase = routeClock - floor(routeClock);
  var routePosition = routePhase * 1.3 - 0.15;
  var routePulse = exp(-pow((x - routePosition) / 0.075, 2));

  // Slow breathing never approaches blackout. A small y offset prevents the
  // three installed paths from appearing as identical copies.
  var breathing =
    0.84 +
    0.16 * wave(breathClock + x * 0.09 + y * 0.045);
  var spatialTexture = 0.94 + 0.06 * wave(x * 1.2 - y * 0.7 + routeClock);
  var value =
    masterBrightness *
    breathing *
    spatialTexture *
    (1 + routePulse * motionAmount);

  rgb(
    clamp(red * value, 0, 1),
    clamp(green * value, 0, 1),
    clamp(blue * value, 0, 1)
  );
}

// Safe fallback when previewed without a 2D map.
export function render(index) {
  render2D(index, index / pixelCount, 0.5);
}
