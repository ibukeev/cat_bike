// Cat-head operating-mode scaffold.
// Mode 0: riding, mode 1: parked/show, mode 2: reserve.
// Assumes an isolated 52-pixel head chain at local indices 0-51.

var HEAD_PIXEL_COUNT = 52
var LEFT_RESERVED = 7
var RIGHT_RESERVED = 51

export var mode = 0

export function sliderMode(v) {
  mode = floor(v * 2.999)
}

export function beforeRender(delta) {
  slowClock = time(0.06)
  showClock = time(0.1)
  fanClock = time(0.045)
  breath = 0.82 + 0.18 * wave(slowClock)

  blink = 1
  if (showClock < 0.08) {
    blink = 0.15 + 0.85 * abs(showClock - 0.04) / 0.04
  }
}

function isReserved(index) {
  return index == LEFT_RESERVED || index == RIGHT_RESERVED
}

function isLeftWhisker(index) {
  return index >= 0 && index < 7
}

function isRightWhisker(index) {
  return index >= 44 && index < 51
}

function isEye(index) {
  return (index >= 8 && index < 12) || (index >= 40 && index < 44)
}

function isFacet(index) {
  return index >= 12 && index < 40
}

function whiskerPosition(index) {
  if (isLeftWhisker(index)) return index
  return 50 - index
}

function renderRiding(index) {
  if (isEye(index)) {
    hsv(0.5, 0.9, 0.26 * breath)
    return
  }

  if (isFacet(index)) {
    facetPhase = index / 28
    hsv(0.56 + 0.12 * wave(slowClock + facetPhase), 0.9,
      0.08 + 0.06 * wave(slowClock + facetPhase))
    return
  }

  if (isLeftWhisker(index) || isRightWhisker(index)) {
    w = whiskerPosition(index)
    hsv(0.49 + 0.03 * wave(fanClock + w / 14), 0.95,
      0.14 + 0.13 * wave(fanClock + w / 7))
    return
  }

  rgb(0, 0, 0)
}

function renderShow(index) {
  if (isEye(index)) {
    hsv(0.5, 0.88, 0.48 * blink)
    return
  }

  if (isFacet(index)) {
    facetPhase = index / 14
    hsv(0.5 + 0.38 * wave(showClock + facetPhase), 0.92,
      0.18 + 0.22 * wave(slowClock + facetPhase))
    return
  }

  if (isLeftWhisker(index) || isRightWhisker(index)) {
    w = whiskerPosition(index)
    sideOffset = isRightWhisker(index) ? 0.18 : 0
    hsv(0.48 + 0.38 * wave(fanClock + w / 12 + sideOffset), 0.95,
      0.2 + 0.35 * wave(fanClock + w / 7 + sideOffset))
    return
  }

  rgb(0, 0, 0)
}

export function render(index) {
  if (index >= HEAD_PIXEL_COUNT || isReserved(index)) {
    rgb(0, 0, 0)
    return
  }

  if (mode == 0) {
    renderRiding(index)
    return
  }

  if (mode == 1) {
    renderShow(index)
    return
  }

  if (isEye(index)) {
    hsv(0.5, 0.85, 0.1)
  } else {
    rgb(0, 0, 0)
  }
}
