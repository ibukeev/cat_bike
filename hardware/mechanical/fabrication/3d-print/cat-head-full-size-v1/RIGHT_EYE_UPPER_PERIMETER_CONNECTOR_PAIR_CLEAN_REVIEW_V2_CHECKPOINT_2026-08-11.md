# Right Eye Upper-Perimeter Connector Pair Clean Review V2 Checkpoint

Open `output/70-freecad-pilots/opposite-side-flange-pilot-v1/right-eye-upper-perimeter-connector-pair-clean-review-v2/CAT_HEAD_RIGHT_EYE_UPPER_PERIMETER_CONNECTOR_PAIR_CLEAN_REVIEW_V2.FCStd`.

Review only `PROPOSED__RIGHT_EYE_BUCKET__TWO_PAIR_CLEAN_COMPOUND_V2` and
`PROPOSED__RIGHT_EYE_REAR_CAP__TWO_PAIR_CLEAN_COMPOUND_V2`.

The user approved the relocated upper pair on 2026-08-11 and requested removal
of the obsolete third loop. The retained lower pair and approved upper axis
`(72.2476, 78.1286, 175.5293) mm` remain unchanged.

Frozen source STLs were split into exact connected components. Only bucket
`component_05` at `(84.734894, 87.581116, 149.253662) mm` and cap
`component_06` at `(83.570908, 90.492157, 148.612564) mm` were omitted. Their
approved relocated counterparts were inserted one-for-one. The retained lower
pair is bucket `component_01` plus cap `component_03`. Four rectangular cap
diffuser-retainer posts are preserved.

Validation: bucket is valid and closed with 6 solids, 637 faces, 999 edges,
362 vertices, and `6629.69 mm3`; cap is valid and closed with 7 solids,
457 faces, 729 edges, 280 vertices, and `4410.85 mm3`. Exactly two connector
pairs remain. No cutter was used. The FCStd archive passed at `681928` bytes.

Direct Boolean subtraction was rejected after FreeCAD returned an invalid
result; a broader cutter could gouge owner material. This remains an isolated
right-side review, not a production union, mirror, or print release.

Regenerate the audit-only component split with:

```sh
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/split_right_eye_owner_components_for_freecad_review_v1.py
```

It writes temporary review inputs under `/tmp/right-eye-owner-components-v1`.
After visual approval, update the right-eye production generator to emit these
exact two centers and validate the right eye before mirroring.
