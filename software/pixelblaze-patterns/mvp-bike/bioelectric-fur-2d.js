// Cat Bike — Bioelectric Fur 2D
//
// Fine cyan/violet filaments ripple over the bike like illuminated fur.
// Periodic nerve impulses travel from the rear (high x) toward the front
// (low x), followed by a brief field of electric sparks.
//
// Requires the 111-pixel MVP bike spatial map. No Sensor Expansion Board is
// required; all motion is generated internally.

export var motionSpeed = 0.42;
export var furDensity = 7.5;
export var furContrast = 0.72;
export var impulseRate = 0.13;
export var impulseStrength = 0.72;
export var impulseWidth = 0.065;
export var baseHue = 0.49;
export var masterBrightness = 0.68;

function scaleBetween(low, high, value) {
  return low + value * (high - low);
}

function smoothstep(edge0, edge1, value) {
  var amount = clamp((value - edge0) / (edge1 - edge0), 0, 1);
  return amount * amount * (3 - 2 * amount);
}

export function sliderMotionSpeed(v) {
  motionSpeed = scaleBetween(0.06, 1.35, v * v);
}

export function sliderFurDensity(v) {
  furDensity = scaleBetween(3.5, 14, v);
}

export function sliderFurContrast(v) {
  furContrast = scaleBetween(0.25, 1, v);
}

export function sliderNerveImpulseRate(v) {
  // Approximately one pulse every 25 seconds at the left and every 2.2
  // seconds at the right.
  impulseRate = scaleBetween(0.04, 0.45, v * v);
}

export function sliderNerveImpulseStrength(v) {
  impulseStrength = scaleBetween(0, 1, v);
}

export function sliderNerveImpulseWidth(v) {
  impulseWidth = scaleBetween(0.025, 0.16, v);
}

export function sliderColor(v) {
  baseHue = v;
}

export function sliderBrightness(v) {
  masterBrightness = scaleBetween(0.08, 1, v);
}

var furClock = 0;
var impulseClock = 0;

export function beforeRender(delta) {
  furClock += delta * 0.001 * motionSpeed;
  impulseClock += delta * 0.001 * impulseRate;

  // Keep the clocks bounded without disturbing their fractional phases.
  if (furClock > 4096) furClock -= 4096;
  if (impulseClock > 4096) impulseClock -= 4096;
}

export function render2D(index, x, y) {
  var impulsePhase = impulseClock - floor(impulseClock);

  // Slowly flex the coordinate field so the filaments look organic instead
  // of reading as fixed diagonal stripes.
  var fieldBend =
    sin(PI2 * (y * 1.35 + furClock * 0.11)) * 0.12 +
    sin(PI2 * (x * 0.7 - furClock * 0.07)) * 0.06;

  var spatialX = x + fieldBend;

  // Two narrow, differently angled fields form the fine illuminated fur.
  // Raising each wave to a high power turns broad sine waves into filaments.
  var primaryFilament = pow(
    wave(
      spatialX * furDensity +
      y * 2.4 -
      furClock * 0.63
    ),
    7
  );

  var crossingFilament = pow(
    wave(
      spatialX * furDensity * 0.63 -
      y * 4.2 +
      furClock * 0.39 +
      sin(PI2 * (x * 1.7 + furClock * 0.09)) * 0.16
    ),
    10
  );

  var softRuffle = wave(
    x * 2.2 -
    y * 1.4 -
    furClock * 0.16 +
    sin(PI2 * (y * 1.1 + furClock * 0.05)) * 0.12
  );

  var fur = primaryFilament * 0.62 + crossingFilament * 0.38;
  fur *= 0.56 + softRuffle * 0.44;

  // Contrast controls both the dim fur floor and filament prominence.
  var furFloor = 0.018 + (1 - furContrast) * 0.055;
  var furValue = furFloor + fur * (0.12 + furContrast * 0.3);

  // Each cycle sends one electrical impulse from the rear to the front. It
  // begins and ends outside the map so the pulse enters and exits cleanly.
  var impulsePosition = 1.14 - impulsePhase * 1.38;
  var distanceFromImpulse = x - impulsePosition;
  var impulse = exp(-pow(distanceFromImpulse / impulseWidth, 2));

  // A winding path keeps the impulse from lighting every strip identically.
  var nerveCenter =
    0.5 +
    0.2 * sin(PI2 * (x * 0.86 + impulsePhase * 0.22)) +
    0.07 * sin(PI2 * (x * 2.7 - impulsePhase * 0.31));
  var pathDistance = abs(y - nerveCenter);
  var nervePath = 0.28 + 0.72 * exp(-pow(pathDistance / 0.24, 2));
  impulse *= nervePath * impulseStrength;

  // Fine sparks flicker only around the traveling nerve pulse.
  var sparkField = pow(
    wave(x * 31 + y * 47 - furClock * 3.7),
    18
  );
  var sparks = sparkField * impulse;

  // A short wake behind the rear-to-front pulse excites the fur filaments.
  var wakeDistance = impulsePosition - x;
  var wake = 0;
  if (wakeDistance > 0 && wakeDistance < 0.34) {
    wake =
      (1 - wakeDistance / 0.34) *
      primaryFilament *
      impulseStrength *
      0.22;
  }

  var value = furValue + impulse * 0.72 + sparks * 0.42 + wake;
  value = clamp(value * masterBrightness, 0, 1);

  // Filaments range from aqua through violet. The pulse shifts farther toward
  // violet, while its smallest sparks briefly approach white.
  var filamentColor =
    crossingFilament * 0.11 +
    softRuffle * 0.025 +
    y * 0.018;
  var hue = baseHue + filamentColor + impulse * 0.13;
  var saturation = clamp(0.93 - sparks * 0.58, 0.32, 0.95);

  // Soften the extreme map boundaries rather than clipping moving texture.
  var edgePresence =
    smoothstep(-0.04, 0.05, x) *
    (1 - smoothstep(0.95, 1.04, x));
  value *= 0.82 + edgePresence * 0.18;

  hsv(hue, saturation, value);
}

// Safe fallback when previewed without a 2D map.
export function render(index) {
  render2D(index, index / pixelCount, 0.5);
}
