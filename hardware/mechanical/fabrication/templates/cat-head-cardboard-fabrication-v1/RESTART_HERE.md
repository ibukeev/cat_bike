# Restart Here: Cat Head Cardboard Prototype

Last updated: 2026-07-01

## Current Goal

Build the first 100% scale cardboard prototype of the faceted cat head.

This is not the final fabrication method. The goal is to validate:

- Overall cat-head proportions
- Panel fit
- Edge labels
- Assembly order
- Ear placement
- Whether the shell can be built physically before moving to final materials

## Frozen Source Version

Use this frozen geometry source:

`../cat-head-wireframe-prototype/versions/v1-cardboard-test-2026-06-29/`

Verified frozen model:

- Nodes: 69
- Rods: 162
- Candidate panels: 95
- Intended prototype size: 203 mm wide x 220 mm tall x 180 mm deep
- Scale for cardboard test: 100%

Do not overwrite this frozen version during the first cardboard test.

## Active Fabrication Folder

`hardware/mechanical/fabrication/templates/cat-head-cardboard-fabrication-v1/`

Important files:

- `README.md`: overview and fabrication plan
- `data/key_alignment_rods.csv`: minimal alignment jig rods/gauges
- `assembly/key-alignment-rod-assembly-guide.html`: visual guide for assembling the key jig
- `data/first_batch_panels.csv`: first panel cut batch
- `data/panel_edge_matching.csv`: edge labels and matching panel edges
- `templates/first-batch-panels-sheet-01.svg` through `first-batch-panels-sheet-05.svg`: printable panel sheets
- `templates/first-batch-panels.svg`: all first-batch templates in one SVG
- `assembly/first-batch-panel-guide.html`: visual guide for first panel batch

## Generated Artifacts Status

Key alignment jig:

- Key rods/gauges: 20
- Existing wireframe edges: 7
- Temporary gauges: 13
- Length range: 30.10 mm to 201.36 mm

First panel batch:

- First-batch panels: 37
- Printable sheets: 5
- Center-face panels: 13
- Right-cheek panels: 10
- Left-cheek panels: 10
- Forehead panels: 4
- Quads flagged `split_or_test_fit`: 5

## What To Do Next Physically

1. Cut the key rods/gauges first.
   - Use `data/key_alignment_rods.csv`.
   - For the first test, use cardboard strips, foam-board strips, skewers, or similar.
   - Cut each strip to `cardboard_strip_cut_length_mm`.
   - Mark the true node-to-node `gauge_length_mm` on the strip.
   - Leave the extra length for tape tabs.

2. Assemble only the key jig.
   - Use `assembly/key-alignment-rod-assembly-guide.html`.
   - Do not build a full 162-rod carcass.
   - Keep temporary gauges removable.
   - Use masking tape, not permanent glue.

3. Print panel sheet 1 at 100% scale.
   - Start with `templates/first-batch-panels-sheet-01.svg`.
   - This is mostly center-face / nose geometry.

4. Cut and tape sheet 1 panels.
   - Match edges by `E###` labels.
   - Use `data/panel_edge_matching.csv` when an edge match is unclear.
   - Tape first; do not glue until the shape is confirmed.

5. Continue with sheets 2-5 only if sheet 1 fits.

## Regeneration Commands

Run these from repository root:

```bash
python3 hardware/mechanical/fabrication/templates/cat-head-cardboard-fabrication-v1/generate_key_alignment_rods.py
python3 hardware/mechanical/fabrication/templates/cat-head-cardboard-fabrication-v1/generate_panel_fabrication_pack.py
```

These commands regenerate:

- `data/key_alignment_rods.csv`
- `assembly/key-alignment-rod-assembly-guide.html`
- `data/panel_edge_matching.csv`
- `data/first_batch_panels.csv`
- `templates/first-batch-panels*.svg`
- `assembly/first-batch-panel-guide.html`

## How To Resume With Codex

After restarting the laptop, open this repository and tell Codex:

`Continue from hardware/mechanical/fabrication/templates/cat-head-cardboard-fabrication-v1/RESTART_HERE.md`

The next likely task is either:

- generate PDFs from the SVG sheets, or
- review/adjust the first-batch panel selection before printing.
