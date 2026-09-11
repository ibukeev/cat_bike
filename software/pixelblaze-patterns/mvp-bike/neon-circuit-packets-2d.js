// Cat Bike — Neon Circuit Packets 2D
//
// A beat-quantized techno pattern for the 111-pixel MVP bike spatial map.
// Neon data packets switch between three spatial lanes and alternate travel
// direction in three-step phrases. Four-on-the-floor bass pulses launch from
// the front. Timing is synthetic; no Sensor Expansion Board is required.

export var bpm = 132;
export var stepsPerBeat = 2;
export var packetWidth = 0.055;
export var laneWidth = 0.11;
export var trailLength = 0.3;
export var bassPulse = 0.62;
export var circuitGrit = 0.24;
export var colorHue = 0.48;
export var masterBrightness = 0.78;

function scaleBetween(low, high, value) {
  return low + value * (high - low);
}

export function sliderBPM(v) {
  bpm = scaleBetween(84, 180, v);
}

export function sliderBeatSubdivision(v) {
  stepsPerBeat = floor(scaleBetween(1, 4.99, v));
}

export function sliderPacketWidth(v) {
  packetWidth = scaleBetween(0.018, 0.15, v);
}

export function sliderLaneWidth(v) {
  laneWidth = scaleBetween(0.045, 0.24, v);
}

export function sliderTrail(v) {
  trailLength = scaleBetween(0.06, 0.68, v);
}

export function sliderBassPulse(v) {
  bassPulse = v;
}

export function sliderCircuitGrit(v) {
  circuitGrit = scaleBetween(0, 0.5, v);
}

export function sliderColor(v) {
  colorHue = v;
}

export function sliderBrightness(v) {
  masterBrightness = scaleBetween(0.08, 1, v);
}

var beatClock = 0;

export function beforeRender(delta) {
  beatClock += delta * 0.001 * bpm / 60;
  if (beatClock > 4096) beatClock -= 4096;
}

export function render2D(index, x, y) {
  var beatPhase = beatClock - floor(beatClock);
  var stepClock = beatClock * stepsPerBeat;
  var stepNumber = floor(stepClock);
  var stepPhase = stepClock - stepNumber;

  var laneNumber = stepNumber - floor(stepNumber / 3) * 3;
  var laneCenter = 0.32 + laneNumber * 0.18;
  var lane = exp(-pow((y - laneCenter) / laneWidth, 2));

  // Alternate direction after each three-lane phrase.
  var phraseNumber = floor(stepNumber / 3);
  var reverse = phraseNumber - floor(phraseNumber / 2) * 2;
  var packetPosition = reverse
    ? 1.14 - stepPhase * 1.28
    : stepPhase * 1.28 - 0.14;
  var packetHead = exp(-pow((x - packetPosition) / packetWidth, 2));

  var behind = reverse ? x - packetPosition : packetPosition - x;
  var packetTrail = 0;
  if (behind > 0 && behind < trailLength) {
    packetTrail = exp(-behind / (0.025 + trailLength * 0.28));
  }

  // Quantized circuit traces and tiny node sparks fill the space between the
  // main packets without producing a full-frame flash.
  var trace = pow(
    wave(
      y * 5.4 +
      floor(x * 7) * 0.19 +
      stepNumber * 0.065
    ),
    12
  );
  var node = pow(
    wave(x * 19 + y * 29 - beatClock * 2.4),
    20
  );

  var kickEnvelope = exp(-beatPhase * 8.5);
  var bassPosition = beatPhase * 1.24 - 0.1;
  var bass =
    exp(-pow((x - bassPosition) / 0.085, 2)) *
    kickEnvelope *
    bassPulse;

  var value = 0.004;
  value += packetHead * lane * 0.95;
  value += packetTrail * lane * 0.4;
  value += trace * circuitGrit * (0.12 + 0.3 * kickEnvelope);
  value += node * circuitGrit * lane * 0.5;
  value += bass;
  value = clamp(value * masterBrightness, 0, 1);

  // Lanes step through cyan, violet, and acid. Reverse phrases get a magenta
  // shift, while bass pulses pull briefly toward blue-white.
  var hue =
    colorHue +
    laneNumber * 0.12 +
    reverse * 0.16 -
    bass * 0.08;
  var saturation = clamp(0.95 - bass * 0.42, 0.42, 0.96);

  hsv(hue, saturation, value);
}

// Safe fallback when previewed without a 2D map.
export function render(index) {
  render2D(index, index / pixelCount, 0.5);
}
