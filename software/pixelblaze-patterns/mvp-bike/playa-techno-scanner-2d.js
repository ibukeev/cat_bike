// Cat Bike — Playa Techno Scanner 2D
//
// Inspired by the owner's Tunnel Scanner and Riot Pulse hat patterns.
// Requires the 111-pixel MVP bike spatial map.
//
// A hard scanner bounces across the bike while every synthetic kick launches a
// separate pulse from the front (low x) toward the rear (high x). The beat is
// generated internally, so no Sensor Expansion Board is required.

export var bpm = 128;
export var scanRate = 0.25;
export var intensity = 0.78;
export var beamWidth = 0.09;
export var trailLength = 0.36;
export var kickAmount = 0.72;
export var colorHue = 0.48;
export var spatialTilt = 0.08;
export var gritAmount = 0.2;

function scaleBetween(low, high, value) {
  return low + value * (high - low);
}

export function sliderBPM(v) {
  bpm = scaleBetween(80, 180, v);
}

export function sliderScannerSpeed(v) {
  // Scanner cycles per beat. Left is stately; right is high-energy.
  scanRate = scaleBetween(0.08, 0.55, v);
}

export function sliderBeamWidth(v) {
  beamWidth = scaleBetween(0.025, 0.22, v);
}

export function sliderTrail(v) {
  trailLength = scaleBetween(0.03, 0.72, v);
}

export function sliderKickPulse(v) {
  kickAmount = scaleBetween(0, 1, v);
}

export function sliderColor(v) {
  colorHue = v;
}

export function sliderSpatialTilt(v) {
  spatialTilt = scaleBetween(-0.22, 0.22, v);
}

export function sliderGrit(v) {
  gritAmount = scaleBetween(0, 0.5, v);
}

export function sliderBrightness(v) {
  intensity = scaleBetween(0.08, 1, v);
}

var beatClock = 0;
var scanClock = 0;

export function beforeRender(delta) {
  var beatsPerSecond = bpm / 60;

  beatClock += delta * 0.001 * beatsPerSecond;
  scanClock += delta * 0.001 * beatsPerSecond * scanRate;

  // Keep values bounded without disturbing their fractional phase.
  if (beatClock > 4096) beatClock -= 4096;
  if (scanClock > 4096) scanClock -= 4096;
}

export function render2D(index, x, y) {
  var beatPhase = beatClock - floor(beatClock);
  var scanPhase = scanClock - floor(scanClock);

  // triangle() makes the main scanner bounce front-to-rear and back-to-front.
  var scannerPosition = triangle(scanPhase);
  var scannerDirection = scanPhase < 0.5 ? 1 : -1;

  // A slight y-dependent shift prevents the three physical paths from looking
  // like copies of a 1D strip.
  var spatialX = clamp(x + (y - 0.5) * spatialTilt, 0, 1);
  var distance = abs(spatialX - scannerPosition);
  var width = beamWidth;

  var beam = exp(-pow(distance / width, 2));

  var behind = scannerDirection > 0
    ? scannerPosition - spatialX
    : spatialX - scannerPosition;

  var trail = 0;
  if (behind > 0) {
    trail = exp(-behind / (0.025 + trailLength * 0.42));
  }

  // Fast attack and smooth decay synthesize a techno kick envelope.
  var kickEnvelope = exp(-beatPhase * 7.5);

  // Every beat launches a second pulse only from front to rear.
  var kickPosition = beatPhase * 1.24 - 0.08;
  var kickWidth = width * 1.3 + 0.018;
  var kickPulse =
    exp(-pow((spatialX - kickPosition) / kickWidth, 2)) *
    kickEnvelope *
    kickAmount;

  // Fine spatial grit reads as moving points rather than a full-frame strobe.
  var grain =
    sin(
      PI2 * (
        spatialX * 37 +
        y * 17 -
        beatClock * 3.2
      )
    ) * 0.5 + 0.5;

  var grit = 0;
  if (grain > 0.92) {
    grit = (grain - 0.92) / 0.08 * gritAmount;
  }

  // Low glow preserves the bike outline while retaining high contrast.
  var value = 0.008;
  value += beam * (0.3 + 0.7 * kickEnvelope);
  value += trail * (0.1 + 0.34 * (1 - beatPhase));
  value += kickPulse;
  value += grit * (0.25 + 0.75 * kickEnvelope);
  value = clamp(value * intensity, 0, 1);

  // Cyan/acid base with a brief magenta-violet kick accent.
  var accent = clamp(kickPulse * 1.6 + grit * 0.35, 0, 1);
  var hue = colorHue + accent * 0.22 + y * 0.025;

  hsv(hue, 0.94, value);
}

// Safe fallback when previewed without a 2D map.
export function render(index) {
  render2D(index, index / pixelCount, 0.5);
}
