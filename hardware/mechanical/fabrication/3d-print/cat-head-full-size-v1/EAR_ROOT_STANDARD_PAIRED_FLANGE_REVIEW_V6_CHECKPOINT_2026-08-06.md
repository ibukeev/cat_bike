# Ear-root standard paired-flange review V6 checkpoint — 2026-08-06

## Status

**Rejected and archived on 2026-08-07.** V6 is not the current review and must
not be printed, mirrored, replicated, integrated, or used as the basis for
hardware placement.

Although V6 contained two nominal flange objects, its construction interpreted
the root direction incorrectly. The orange tapered/broad root visibly
protruded beyond the head exterior, while the green member/owner relationship
was buried or obscured. This is the ugly exterior geometry rejected in user
review; it is not an acceptable standard-flange solution.

## Archived files

- Blender review:
  `output/60-ear-root-reviews/ear-root-standard-paired-flange-review-v6-rejected-exterior-protrusion/ear-root-standard-paired-flange-review-v6.blend`
- Validation:
  `output/60-ear-root-reviews/ear-root-standard-paired-flange-review-v6-rejected-exterior-protrusion/ear-root-standard-paired-flange-review-v6-validation.json`
- Renders:
  `output/60-ear-root-reviews/ear-root-standard-paired-flange-review-v6-rejected-exterior-protrusion/renders/`

## Source and archival regeneration

- Generator: `source/generate_ear_root_standard_paired_flange_review_v6.py`
- Config: `config/ear-root-standard-paired-flange-review-v6.json`
- Required metal interface: `CAT-HEAD-SHELL-ALUMINUM-V0.5`

Exact archival regeneration command from repository root:

```bash
blender --background --python hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/generate_ear_root_standard_paired_flange_review_v6.py -- --config hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/config/ear-root-standard-paired-flange-review-v6.json --output-dir hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/output/60-ear-root-reviews/ear-root-standard-paired-flange-review-v6-rejected-exterior-protrusion
```

## Rejected construction

- one right-side prototype with orange and green nominal tabs;
- tapered broad owner bases on the wrong exterior-normal placement;
- M3 hole/fastener/access proposal introduced before placement was trusted;
- orange exterior protrusion and an unreadable green owner root;
- conservative moving-flange and tool-access margins unresolved.

Do not recover the V6 broad bases, hardware, access envelopes, or exterior
placement. V7 intentionally restarted with two plain internal rectangular tabs
and no holes or hardware.

## Preserved workstreams

Archiving V6 does not change the accepted V3 ear fit body, exact ears, exact
upper-head source geometry, eyes, lower-face/rear-cassette ownership,
reinforcement direction, C006, or aluminum plate/rail
`CAT-HEAD-SHELL-ALUMINUM-V0.5` work.
