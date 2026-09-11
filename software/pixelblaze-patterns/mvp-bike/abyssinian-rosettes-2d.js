// Cat Bike — Abyssinian Rosettes 2D
//
// The signature Bio-Luminescent Abyssinian look for the 111-pixel MVP bike
// map: a dim copper undercoat with organic aqua and magenta rosettes that flex
// across the physical frame. A broad prowling highlight travels from the bike
// front (low x) toward the rear (high x).

export var motionSpeed = 0.2;
export var rosetteScale = 5.4;
export var rosetteSharpness = 0.11;
export var fieldWarp = 0.09;
export var magentaAmount = 0.3;
export var copperUndercoat = 0.15;
export var masterBrightness = 0.64;

function scaleBetween(low, high, value) {
  return low + value * (high - low);
}

export function sliderMotionSpeed(v) {
  motionSpeed = scaleBetween(0.035, 0.72, v * v);
}

export function sliderRosetteScale(v) {
  rosetteScale = scaleBetween(2.8, 10.5, v);
}

export function sliderRosetteSharpness(v) {
  // Small values make thin rings; large values make softer patches.
  rosetteSharpness = scaleBetween(0.045, 0.23, v);
}

export function sliderOrganicWarp(v) {
  fieldWarp = scaleBetween(0, 0.2, v);
}

export function sliderMagentaAccent(v) {
  magentaAmount = v;
}

export function sliderCopperUndercoat(v) {
  copperUndercoat = scaleBetween(0, 0.34, v);
}

export function sliderBrightness(v) {
  masterBrightness = scaleBetween(0.08, 1, v);
}

var fieldClock = 0;
var prowlClock = 0;

export function beforeRender(delta) {
  fieldClock += delta * 0.001 * motionSpeed;
  prowlClock += delta * 0.001 * motionSpeed * 0.11;

  if (fieldClock > 4096) fieldClock -= 4096;
  prowlClock -= floor(prowlClock);
}

export function render2D(index, x, y) {
  // Two gently deformed coordinate fields create broken rings instead of
  // regular stripes or a wiring-order chase.
  var warpedX =
    x +
    sin(PI2 * (y * 1.55 + fieldClock * 0.12)) * fieldWarp +
    sin(PI2 * (x * 0.72 - fieldClock * 0.07)) * fieldWarp * 0.35;
  var warpedY =
    y +
    sin(PI2 * (x * 1.18 - fieldClock * 0.1)) * fieldWarp * 0.7;

  var fieldA = wave(
    warpedX * rosetteScale + warpedY * 1.7 - fieldClock * 0.31
  );
  var fieldB = wave(
    warpedY * rosetteScale * 0.82 - warpedX * 1.25 + fieldClock * 0.23
  );
  var cellField = fieldA * fieldB;

  // Select a narrow band through the cellular field to form luminous rings,
  // then add a few bright centers so the sparse strip layout still reads.
  var ring = exp(-pow((cellField - 0.39) / rosetteSharpness, 2));
  var center = pow(cellField, 8) * 0.7;
  var brokenEdge =
    0.55 +
    0.45 * wave(x * 7.3 - y * 5.1 + fieldClock * 0.44);
  var rosette = clamp(ring * brokenEdge + center, 0, 1);

  var prowlPosition = prowlClock * 1.36 - 0.18;
  var prowl = exp(-pow((x - prowlPosition) / 0.2, 2));
  var glow = rosette * (0.34 + prowl * 0.38);

  // Magenta appears in alternate ring fragments while aqua remains dominant.
  var magentaField =
    wave(x * 2.1 + y * 1.6 - fieldClock * 0.09) * magentaAmount;
  var glowR = 0.015 + (0.95 - 0.015) * magentaField;
  var glowG = 0.95 + (0.045 - 0.95) * magentaField;
  var glowB = 1 + (0.72 - 1) * magentaField;

  // Copper undercoat stays dim; its purpose is to connect the LED effect to
  // the gold/copper daytime sculpture, not to compete with the rosettes.
  var coatTexture =
    copperUndercoat *
    (0.62 + 0.38 * wave(x * 1.3 + y * 0.8 + fieldClock * 0.04));
  var red = 0.66 * coatTexture + glowR * glow;
  var green = 0.16 * coatTexture + glowG * glow;
  var blue = 0.025 * coatTexture + glowB * glow;

  rgb(
    clamp(red * masterBrightness, 0, 1),
    clamp(green * masterBrightness, 0, 1),
    clamp(blue * masterBrightness, 0, 1)
  );
}

// Safe fallback when previewed without a 2D map.
export function render(index) {
  render2D(index, index / pixelCount, 0.5);
}
