// Cat Bike — Laser Lattice Techno 2D
//
// Crossing neon planes slide through the 111-pixel MVP bike spatial map. Their
// intersections punch on a synthetic four-on-the-floor beat while a slower
// scanner reveals different parts of the lattice. The effect is energetic but
// keeps the beat boost spatially localized instead of flashing the whole bike.

export var bpm = 126;
export var motionSpeed = 0.48;
export var gridDensity = 5.8;
export var gridAngle = 0.72;
export var lineSharpness = 9;
export var beatPunch = 0.72;
export var scannerWidth = 0.18;
export var colorHue = 0.52;
export var masterBrightness = 0.76;

function scaleBetween(low, high, value) {
  return low + value * (high - low);
}

export function sliderBPM(v) {
  bpm = scaleBetween(80, 180, v);
}

export function sliderGridMotion(v) {
  motionSpeed = scaleBetween(0.08, 1.4, v * v);
}

export function sliderGridDensity(v) {
  gridDensity = scaleBetween(2.2, 11, v);
}

export function sliderGridAngle(v) {
  gridAngle = scaleBetween(0.2, 1.35, v);
}

export function sliderLineSharpness(v) {
  lineSharpness = scaleBetween(3, 20, v);
}

export function sliderBeatPunch(v) {
  beatPunch = v;
}

export function sliderScannerWidth(v) {
  scannerWidth = scaleBetween(0.045, 0.4, v);
}

export function sliderColor(v) {
  colorHue = v;
}

export function sliderBrightness(v) {
  masterBrightness = scaleBetween(0.08, 1, v);
}

var beatClock = 0;
var gridClock = 0;

export function beforeRender(delta) {
  var beatsPerSecond = bpm / 60;
  beatClock += delta * 0.001 * beatsPerSecond;
  gridClock += delta * 0.001 * beatsPerSecond * motionSpeed;

  if (beatClock > 4096) beatClock -= 4096;
  if (gridClock > 4096) gridClock -= 4096;
}

export function render2D(index, x, y) {
  var beatPhase = beatClock - floor(beatClock);
  var kickEnvelope = exp(-beatPhase * 7.5);

  var lineA = pow(
    wave(
      x * gridDensity +
      y * gridDensity * gridAngle -
      gridClock
    ),
    lineSharpness
  );
  var lineB = pow(
    wave(
      x * gridDensity * 0.83 -
      y * gridDensity * gridAngle +
      gridClock * 0.73 +
      0.19
    ),
    lineSharpness
  );
  var intersection = lineA * lineB;

  var scannerPosition = triangle(gridClock * 0.17);
  var scanner = exp(-pow((x - scannerPosition) / scannerWidth, 2));

  // Quantized color changes occur once per four-beat bar, while the geometry
  // itself continues to slide smoothly.
  var barNumber = floor(beatClock / 4);
  var barColor = wave(barNumber * 0.173) * 0.16;

  var value = 0.005;
  value += lineA * 0.19;
  value += lineB * 0.16;
  value += intersection * (0.28 + kickEnvelope * beatPunch * 0.68);
  value += scanner * (lineA + lineB) * 0.16;
  value = clamp(value * masterBrightness, 0, 1);

  var hue =
    colorHue +
    barColor +
    lineB * 0.2 -
    lineA * 0.045 +
    y * 0.035;
  var saturation = clamp(
    0.94 - intersection * kickEnvelope * 0.48,
    0.38,
    0.95
  );

  hsv(hue, saturation, value);
}

// Safe fallback when previewed without a 2D map.
export function render(index) {
  render2D(index, index / pixelCount, 0.5);
}
