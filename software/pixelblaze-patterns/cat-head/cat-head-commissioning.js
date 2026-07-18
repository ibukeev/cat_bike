// Cat-head commissioning pattern.
// Assumes an isolated 52-pixel head chain at local indices 0-51.

var HEAD_PIXEL_COUNT = 52
var LEFT_RESERVED = 7
var RIGHT_RESERVED = 51

export var selectedPixel = 0
export var selectedZone = 0
export var testBrightness = 0.2

export function sliderSelectedPixel(v) {
  selectedPixel = floor(v * (HEAD_PIXEL_COUNT - 0.001))
}

export function sliderZone(v) {
  selectedZone = floor(v * 4.999)
}

export function sliderBrightness(v) {
  testBrightness = 0.05 + 0.15 * v
}

export function beforeRender(delta) {
  pulse = 0.7 + 0.3 * wave(time(0.05))
}

function isReserved(index) {
  return index == LEFT_RESERVED || index == RIGHT_RESERVED
}

function isWhisker(index) {
  return index < 7 || (index >= 44 && index < 51)
}

function isEye(index) {
  return (index >= 8 && index < 12) || (index >= 40 && index < 44)
}

function isFacet(index) {
  return index >= 12 && index < 40
}

export function render(index) {
  if (index >= HEAD_PIXEL_COUNT || isReserved(index)) {
    rgb(0, 0, 0)
    return
  }

  enabled = 0
  if (selectedZone == 0) enabled = index == selectedPixel
  if (selectedZone == 1) enabled = isWhisker(index)
  if (selectedZone == 2) enabled = isEye(index)
  if (selectedZone == 3) enabled = isFacet(index)
  if (selectedZone == 4) enabled = 1

  if (enabled) {
    hsv(0.5, 0.9, testBrightness * pulse)
  } else {
    rgb(0, 0, 0)
  }
}
