# Gate 6 Isolated Eye Lightbox Modules

Status: generated and automatically validated. This is a test-print and visual
review candidate, not a production release. Print and light one full-size eye
before committing to diffuser material or LED-strip pitch.

## Construction

Each eye is a separate three-part lightbox:

1. An opaque ASA bucket combines the exterior eye surround, a 14 mm-deep
   light-blocking baffle, and two recessed internal head-mount flanges.
2. A 1.5 mm frosted or milky PETG diffuser preserves the corrected annotated
   eye silhouette. It overlaps the visible aperture by 1.2 mm and sits behind
   a 0.3 mm black light-blocking gasket.
3. An opaque ASA rear cap provides a flat adhesive LED-carrier surface, a 4 mm
   wire exit, two external cap-fastener ears, and four posts that hold the
   diffuser against the front bezel.

The chamber leaves 11 mm between the diffuser rear surface and the LED-carrier
plane. Four addressable 5 V RGB pixels are reserved per eye. The two eyes can
therefore use colors and brightness independent of the twenty head glow
panels. Print the bucket and cap black or otherwise opaque; add a white
reflective liner inside the chamber rather than printing the entire bucket
white.

## Head attachment

The bucket is located by its fitted four-sided opening and opaque bezel. Two
recessed internal flange connections retain each module and resist rotation:

- matching 12 mm-long, 8 mm-deep, 2.4 mm-thick tabs on the bucket and lower
  head shell;
- a hidden 4 mm-wide by 2 mm-thick internal bridge from each outer-side head
  tab to the structural lower-face shell; the generated right and left bridge
  spans are 21.4169 mm and 20.9853 mm respectively;
- one tab centered and aligned along the outer-side eye edge and one centered
  and aligned along the lower eye edge;
- 0.6 mm setback behind the exterior eye plane so neither tab reaches the
  visible silhouette;
- 0.3 mm tab-face gap;
- two M2.5 through-bolts, four washers, and two loose nyloc nuts per eye;
- bolt axis parallel to the eye plane;
- no exterior screw hole.

Use the Gate 6 versions of `left_lower_face.stl` and
`right_lower_face.stl`; they contain the new matching head tabs. The other
five shell exports are carried forward so `shells/` remains a complete print
set.

## Rear-cap hardware

Each cap uses two M2.5 through-bolts, four washers, and two loose nyloc nuts.
The screw bosses sit beneath the broad opaque eye-surround wedge and are not
visible from the front. Seal the cap perimeter with thin black closed-cell foam
or a removable black silicone gasket after the light test.

Gate 6 hardware total:

- eight M2.5 through-bolts;
- sixteen M2.5 washers;
- eight M2.5 nyloc nuts;
- eight independently addressable 5 V RGB pixels.

Choose exact screw lengths from the physical print. Start with M2.5 x 8-10 mm
for both the head flange and cap ears, then confirm washer and nyloc engagement.

## Assembly order

1. Apply a white reflective liner to the bucket chamber without covering the
   diffuser pocket or gasket seat.
2. Attach four pixels or a four-pixel strip to the inside face of the rear cap
   and route its cable through the 4 mm port. Seal around the cable.
3. Place the black perimeter gasket and slide the diffuser through the rear of
   the bucket until it seats behind the front bezel.
4. Fit the rear cap. Its four posts retain the diffuser; install the two cap
   bolts and tighten only enough to compress the gasket.
5. Insert the complete module into the eye opening from the exterior. The bezel
   controls location and rotation.
6. From inside the head, install both M2.5 flange bolts, washers, and nyloc
   nuts.

## Generated files

Run:

~~~bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_gate6_eye_modules.py
~~~

Review `output/gate6-eye-modules/gate6-eye-modules-review.blend` first.

- `eyes/` contains the six full-size bucket, diffuser, and rear-cap STLs.
- `shells/` contains the complete seven-shell Gate 6 set with eye-mount tabs.
- `small-model-100mm/` contains 30.303% scale eye parts and one combined
  visual assembly STL per eye.
- `gate6-eye-module-validation.json` records topology, printer fit, aperture,
  mounting, LED-gap, and export checks. It also requires triangle overlap from
  every head tab to its shell and from every module tab to its bucket.

The 100 mm-head-scale parts are visual-fit models. Their walls and M2.5 holes
are scaled and are not valid hardware coupons. For a small model, use the
combined visual eye STL or the three color-separated parts and retain them with
a temporary adhesive. Use the full-size parts for hardware, diffusion,
temperature, and light-leak testing.

## Required physical checks

- Verify that the diffuser slides through the rear pocket without sanding.
- Confirm the four cap posts hold the lens without bowing it.
- Check that both separated head flanges seat without stressing the bucket and
  prevent rocking after the bezel is seated.
- Run cyan, red, green, and white eye patterns while the surrounding head LEDs
  are active; inspect for light mixing in both directions.
- Check hotspots at normal riding brightness and after a 30-minute heat soak.
- Confirm driver and nut access before printing both full-size eyes.
