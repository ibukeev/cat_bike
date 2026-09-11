#!/usr/bin/env node

// Off-device validation for the 111-pixel MVP bike Pixelblaze collection.
// This is a small compatibility harness, not a complete Pixelblaze emulator.

var fs = require("fs");
var path = require("path");
var vm = require("vm");

var repositoryRoot = path.resolve(__dirname, "../..");
var patternDirectory = path.join(
  repositoryRoot,
  "software/pixelblaze-patterns/mvp-bike"
);
var mapperPath = path.join(patternDirectory, "mvp-bike-spatial-map.js");
var expectedPatternCount = 10;

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function normalizeContain(points) {
  var minX = Infinity;
  var minY = Infinity;
  var maxX = -Infinity;
  var maxY = -Infinity;

  points.forEach(function (point) {
    minX = Math.min(minX, point[0]);
    minY = Math.min(minY, point[1]);
    maxX = Math.max(maxX, point[0]);
    maxY = Math.max(maxY, point[1]);
  });

  var width = maxX - minX;
  var height = maxY - minY;
  var scale = Math.max(width, height);
  var xMargin = (scale - width) / 2;
  var yMargin = (scale - height) / 2;

  return points.map(function (point) {
    return [
      (point[0] - minX + xMargin) / scale,
      (point[1] - minY + yMargin) / scale
    ];
  });
}

function loadMapper() {
  var source = fs.readFileSync(mapperPath, "utf8");
  var mapper = vm.runInNewContext("(" + source + ")", {
    Error: Error,
    Math: Math
  });
  var rawPoints = mapper(111);

  assert(rawPoints.length === 111, "Mapper must return exactly 111 points");
  rawPoints.forEach(function (point, index) {
    assert(
      point.length === 2 && point.every(Number.isFinite),
      "Mapper point " + index + " is not a finite 2D coordinate"
    );
  });

  return normalizeContain(rawPoints);
}

function deterministicRandom() {
  var state = 0x12345678;
  return function (maximum) {
    state = (1664525 * state + 1013904223) >>> 0;
    return (state / 0x100000000) * maximum;
  };
}

function createHarness(fileName) {
  var colorCalls = 0;
  var lastColorMode = "none";
  var random = deterministicRandom();

  function checkUnit(value, channel) {
    assert(Number.isFinite(value), fileName + ": non-finite " + channel);
    assert(
      value >= -1e-9 && value <= 1 + 1e-9,
      fileName + ": out-of-range " + channel + " = " + value
    );
  }

  var context = {
    PI2: Math.PI * 2,
    pixelCount: 111,
    array: function (length) {
      return Array.from({ length: length }, function () { return 0; });
    },
    random: random,
    sin: Math.sin,
    abs: Math.abs,
    exp: Math.exp,
    pow: Math.pow,
    floor: Math.floor,
    clamp: function (value, low, high) {
      return Math.min(high, Math.max(low, value));
    },
    wave: function (value) {
      return 0.5 + 0.5 * Math.sin(Math.PI * 2 * value);
    },
    triangle: function (value) {
      var phase = value - Math.floor(value);
      return 1 - Math.abs(phase * 2 - 1);
    },
    rgb: function (red, green, blue) {
      checkUnit(red, "red");
      checkUnit(green, "green");
      checkUnit(blue, "blue");
      lastColorMode = "rgb";
      colorCalls++;
    },
    hsv: function (hue, saturation, value) {
      assert(Number.isFinite(hue), fileName + ": non-finite hue");
      checkUnit(saturation, "saturation");
      checkUnit(value, "value");
      lastColorMode = "hsv";
      colorCalls++;
    }
  };

  context.__validation = {
    calls: function () { return colorCalls; },
    mode: function () { return lastColorMode; }
  };
  return context;
}

function loadPattern(filePath) {
  var fileName = path.basename(filePath);
  var source = fs.readFileSync(filePath, "utf8");
  var executableSource = source.replace(
    /\bexport\s+(?=(?:var|function)\b)/g,
    ""
  );
  var context = createHarness(fileName);

  vm.createContext(context);
  new vm.Script(executableSource, { filename: fileName }).runInContext(context);

  assert(
    typeof context.beforeRender === "function",
    fileName + ": missing beforeRender(delta)"
  );
  assert(
    typeof context.render2D === "function",
    fileName + ": missing render2D(index, x, y)"
  );
  assert(
    typeof context.render === "function",
    fileName + ": missing 1D fallback render(index)"
  );

  return context;
}

function exercisePattern(filePath, points) {
  var context = loadPattern(filePath);
  var frames = 240;

  for (var frame = 0; frame < frames; frame++) {
    context.beforeRender(1000 / 30);
    points.forEach(function (point, index) {
      context.render2D(index, point[0], point[1]);
    });
  }

  // Test the map-free preview path once for every pixel.
  for (var index = 0; index < 111; index++) context.render(index);

  // Pixelblaze sliders must also remain numerically safe at both endpoints and
  // the midpoint. This catches risky width=0 and count-boundary mistakes.
  Object.keys(context)
    .filter(function (name) {
      return name.indexOf("slider") === 0 && typeof context[name] === "function";
    })
    .forEach(function (sliderName) {
      [0, 0.5, 1].forEach(function (value) {
        context[sliderName](value);
        context.beforeRender(1000 / 30);
        points.forEach(function (point, pointIndex) {
          context.render2D(pointIndex, point[0], point[1]);
        });
      });
    });

  assert(
    context.__validation.calls() > frames * 111,
    path.basename(filePath) + ": render functions did not emit colors"
  );

  return {
    name: path.basename(filePath),
    calls: context.__validation.calls(),
    mode: context.__validation.mode()
  };
}

var points = loadMapper();
var patternFiles = fs.readdirSync(patternDirectory)
  .filter(function (name) { return name.endsWith("-2d.js"); })
  .sort();

assert(
  patternFiles.length === expectedPatternCount,
  "Expected " + expectedPatternCount + " patterns, found " + patternFiles.length
);

var results = patternFiles.map(function (name) {
  return exercisePattern(path.join(patternDirectory, name), points);
});

console.log(
  "Validated mapper and " + results.length + " Pixelblaze patterns:"
);
results.forEach(function (result) {
  console.log(
    "- " + result.name + ": " + result.calls + " color samples (" + result.mode + ")"
  );
});
