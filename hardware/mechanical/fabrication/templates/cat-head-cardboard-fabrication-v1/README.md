# Cat Head Cardboard Fabrication V1

This folder contains fabrication artifacts for the first 100% scale cardboard assembly test.

## Source Version

- Frozen source: `../cat-head-wireframe-prototype/versions/v1-cardboard-test-2026-06-29/`
- Intended prototype size:
  - Width: 203 mm
  - Height: 220 mm
  - Depth: 180 mm
- Scale: 100%

## Goal

Build a fast cardboard proof of the faceted cat-head shell to check:

- Overall proportions
- Panel fit
- Edge labeling
- Assembly order
- Ear placement
- Whether the current model is physically buildable before investing in final materials

## Recommended Fabrication Strategy

Use a panel shell with a minimal alignment jig.

Do not build the full rod skeleton first. The final object is a faceted skin, so a full 162-rod carcass would take too long and may fight the panels. Also do not cut all 95 panels blindly without alignment aids, because the shell can drift during assembly.

The first prototype should use:

- Flattened cardboard panel templates
- Edge labels on every panel side
- Zone labels on every panel
- A matching edge table
- A small set of key alignment rods/gauges
- Tape-first assembly, glue only after fit is confirmed

## Material Assumption

Use thin cardboard or poster board around 0.5-1.0 mm thick.

For the first test, masking tape is preferred over permanent glue. Tape makes it easier to reopen seams, correct panel order, and mark model errors.

## Artifacts To Generate

Generated artifacts:

- `data/key_alignment_rods.csv`: minimal alignment rod/gauge list for the cardboard jig.
- `assembly/key-alignment-rod-assembly-guide.html`: visual step-by-step rod assembly guide with front, side, and top views.
- `generate_key_alignment_rods.py`: reproducible generator for the rod CSV and visual guide.
- `data/panel_edge_matching.csv`: edge labels and matching candidate panel edges.
- `data/first_batch_panels.csv`: first cut batch panel list and sheet placement.
- `templates/first-batch-panels.svg`: all first-batch templates in one overview SVG.
- `templates/first-batch-panels-sheet-01.svg` through `sheet-05.svg`: printable US Letter landscape sheets.
- `assembly/first-batch-panel-guide.html`: visual guide for the first panel batch.
- `generate_panel_fabrication_pack.py`: reproducible generator for panel CSV/SVG/HTML artifacts.

### Panel Templates

Output folder: `templates/`

Generate full-scale flat patterns from:

- `panel-candidates/candidate_panels.csv`
- `panel-candidates/candidate-panels-3d.obj`

Each panel template should include:

- Panel ID
- Node IDs
- Edge labels
- Zone label
- Edge length in mm
- Optional simple tape-tab marks

Current first-batch panel set:

- First-batch panels: 37
- Printable sheets: 5
- Center-face panels: 13
- Right-cheek panels: 10
- Left-cheek panels: 10
- Forehead panels: 4
- Quads flagged `split_or_test_fit`: 5

Print the sheet SVGs at 100% scale. If a panel is flagged `split_or_test_fit`, tape it as one piece for the quick test only if it bends cleanly; otherwise split it along the dashed diagonal.

### Edge Matching Table

Output folder: `data/`

Generate a CSV/table that tells which panel edge joins which other panel edge.

Required columns:

- panel_id
- edge_index
- node_a
- node_b
- edge_length_mm
- matching_panel_id
- matching_edge_index
- zone

### Assembly Guide

Output folder: `assembly/`

Recommended assembly order:

1. Nose and center-face cluster
2. Cheeks
3. Forehead
4. Side planes
5. Back planes
6. Ear bases
7. Ear tips and final closing seams

### Key Alignment Rods

Output folder: `data/`

Generated file: `data/key_alignment_rods.csv`

This is a small rod/gauge list, not the full rod graph.

Use these rods to prevent shape drift while assembling panels:

- Centerline height gauge
- Front width gauge
- Mid-face width gauge
- Back width gauge
- Chin-to-forehead depth gauge
- Back plane depth gauge
- Left ear base anchor
- Right ear base anchor
- Left ear tip anchor
- Right ear tip anchor
- A few cross-body diagonals if needed to lock twist

The key rods can be temporary cardboard strips, skewers, foam-board spacers, or printed paper gauges. They are not the final structure unless the physical test shows they are useful.

Visual assembly guide: `assembly/key-alignment-rod-assembly-guide.html`

Current key-rod set:

- Key rods/gauges: 20
- Existing wireframe edges: 7
- Temporary gauges: 13
- Longest gauge: 201.36 mm
- Shortest gauge: 30.10 mm

## First Physical Test Batch

Do not cut all 95 panels first.

Start with a smaller batch:

- Nose / center face panels
- Cheek panels around both eyes
- Forehead panels adjacent to the centerline

If edge labels and curvature work on this first batch, continue with the sides, back, and ears.

## Acceptance Criteria

The cardboard prototype is useful if:

- The front view reads as the intended cat head
- The side profile is not too boxy
- The ears attach cleanly without floating corners
- The panel labels are sufficient for assembly without guessing
- No major holes or impossible seams appear
- The model can stand as a taped shell before final glue

## Current Counts

From frozen source version:

- Nodes: 69
- Rods: 162
- Candidate cardboard panels: 95
