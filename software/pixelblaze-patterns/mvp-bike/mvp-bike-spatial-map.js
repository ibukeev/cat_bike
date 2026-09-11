// MVP bike 2D spatial map for Pixelblaze.
//
// Pixel numbering is one-based in the installation notes:
//   Section 1: pixels 1-31   (31 pixels)
//   Section 2: pixels 32-59  (28 pixels)
//   Section 3: pixels 60-111 (52 pixels)
//
// The control points below trace the red arrow centerlines in the annotated
// 1600 x 1205 reference photo. Arrow direction is increasing pixel index.
// Set Settings > Pixels to 111, paste this entire file into the Mapper editor,
// choose Contain, and click Save.

function (pixelCount) {
  if (pixelCount != 111) {
    throw new Error("Set Settings > Pixels to 111");
  }

  var map = [];

  // Add evenly spaced LEDs along a multi-segment physical path.
  function addPolyline(points, count) {
    var lengths = [];
    var totalLength = 0;

    for (var segment = 0; segment < points.length - 1; segment++) {
      var dx = points[segment + 1][0] - points[segment][0];
      var dy = points[segment + 1][1] - points[segment][1];
      var length = Math.sqrt(dx * dx + dy * dy);

      lengths.push(length);
      totalLength += length;
    }

    for (var pixel = 0; pixel < count; pixel++) {
      var target = count == 1 ? 0 : (pixel / (count - 1)) * totalLength;
      var activeSegment = 0;
      var distanceBeforeSegment = 0;

      while (
        activeSegment < lengths.length - 1 &&
        target > distanceBeforeSegment + lengths[activeSegment]
      ) {
        distanceBeforeSegment += lengths[activeSegment];
        activeSegment++;
      }

      var segmentLength = lengths[activeSegment];
      var amount =
        segmentLength == 0
          ? 0
          : (target - distanceBeforeSegment) / segmentLength;
      var start = points[activeSegment];
      var end = points[activeSegment + 1];

      map.push([
        start[0] + (end[0] - start[0]) * amount,
        start[1] + (end[1] - start[1]) * amount
      ]);
    }
  }

  // Section 1: pixels 1-31, upper rear frame toward the rack/basket.
  addPolyline([
    [840, 493],
    [865, 479],
    [895, 470],
    [930, 461],
    [970, 451],
    [1015, 443],
    [1060, 437],
    [1105, 433],
    [1150, 429],
    [1200, 425],
    [1245, 421],
    [1274, 419]
  ], 31);

  // Section 2: pixels 32-59, rear axle/lower frame toward the crank.
  addPolyline([
    [1128, 744],
    [1090, 744],
    [1050, 743],
    [1010, 742],
    [970, 742],
    [930, 740],
    [890, 738],
    [850, 735],
    [814, 731]
  ], 28);

  // Section 3: pixels 60-111, seat/battery edge down through the step-through
  // curve and then upward toward the front stem.
  addPolyline([
    [838, 477],
    [833, 494],
    [826, 515],
    [818, 538],
    [810, 564],
    [801, 592],
    [793, 620],
    [787, 644],
    [767, 650],
    [742, 652],
    [716, 653],
    [690, 654],
    [665, 654],
    [654, 642],
    [645, 627],
    [635, 610],
    [625, 591],
    [615, 572],
    [604, 551],
    [594, 530],
    [584, 509],
    [573, 487],
    [563, 466],
    [553, 448]
  ], 52);

  return map;
}
