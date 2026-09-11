#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "../..");
const mapperPath = path.join(root, "software/pixelblaze-patterns/mvp-bike/mvp-bike-spatial-map.js");
const photoPath = path.join(root, "assets/photos/Original_bike/pixed LAYAOUT.jpg");
const outputPath = path.join(root, "software/pixelblaze-patterns/mvp-bike/mvp-bike-spatial-map-review.svg");

const mapper = eval("(" + fs.readFileSync(mapperPath, "utf8") + ")");
const points = mapper(111);
if (points.length !== 111) throw new Error("Expected exactly 111 mapped pixels");

const photo = fs.readFileSync(photoPath).toString("base64");
const sections = [
  { label: "Section 1: pixels 1-31", start: 0, end: 30, color: "#00e5ff" },
  { label: "Section 2: pixels 32-59", start: 31, end: 58, color: "#ffe600" },
  { label: "Section 3: pixels 60-111", start: 59, end: 110, color: "#66ff66" }
];

let svg = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>";
svg += "<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"1600\" height=\"1205\" viewBox=\"0 0 1600 1205\">";
svg += "<image width=\"1600\" height=\"1205\" href=\"data:image/jpeg;base64," + photo + "\"/>";

sections.forEach(function (section) {
  const part = points.slice(section.start, section.end + 1);
  const line = part.map(function (point) { return point.join(","); }).join(" ");

  svg += "<polyline points=\"" + line + "\" fill=\"none\" stroke=\"#000\" stroke-opacity=\"0.7\" stroke-width=\"11\"/>";
  svg += "<polyline points=\"" + line + "\" fill=\"none\" stroke=\"" + section.color + "\" stroke-width=\"5\"/>";

  part.forEach(function (point, localIndex) {
    const absoluteIndex = section.start + localIndex + 1;
    const endpoint = localIndex === 0 || localIndex === part.length - 1;
    svg += "<circle cx=\"" + point[0] + "\" cy=\"" + point[1] + "\" r=\"" + (endpoint ? 8 : 3.5) + "\" fill=\"" + section.color + "\"><title>Pixel " + absoluteIndex + "</title></circle>";
  });

  const start = part[0];
  const end = part[part.length - 1];
  svg += "<g font-family=\"sans-serif\" font-weight=\"700\" font-size=\"20\" paint-order=\"stroke\" stroke=\"#000\" stroke-width=\"5\" fill=\"" + section.color + "\">";
  svg += "<text x=\"" + (start[0] + 10) + "\" y=\"" + (start[1] - 12) + "\">" + section.label + " START</text>";
  svg += "<text x=\"" + (end[0] + 10) + "\" y=\"" + (end[1] - 12) + "\">" + section.label + " END</text></g>";
});

svg += "</svg>\n";
fs.writeFileSync(outputPath, svg);
console.log(outputPath);
