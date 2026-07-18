# Repository Guidelines

## Project Structure & Module Organization

This is a hardware-first repository for a Burning Man electric bike LED installation. Keep work organized by purpose:

- `hardware/electrical/` for battery, Pixelblaze controller, LEDs, and wiring.
- `hardware/mechanical/` for mounts, enclosures, and bike attachment parts.
- `software/pixelblaze-patterns/` for Pixelblaze patterns and exports.
- `software/tools/` for helper scripts.
- `docs/` for assembly notes, BOMs, safety notes, and design logs.
- `assets/` for photos, diagrams, datasheets, and references.
- `tests/` for manual checklists and automated validation.

Prefer descriptive filenames that communicate the hardware or feature they affect, such as `docs/bom/led-strip-options.md` or `hardware/electrical/wiring/rear-harness.md`.

## Build, Test, and Development Commands

No project-specific build system is committed yet. When adding one, document exact commands in `README.md` and keep this guide in sync:

- `make test`: run automated validation for tools or generated files.
- `make lint`: run formatters, linters, or static checks.
- `make export-patterns`: export Pixelblaze patterns, if tooling is added.

Avoid commands that depend on local absolute paths. Use environment variables for machine-specific configuration.

## Coding Style & Naming Conventions

Follow the conventions of the language introduced for each module. Use consistent indentation within a file, descriptive names, and small functions that map to a clear hardware or behavior concern. Prefer names like `rear_harness_power_budget.md` or `export_pixelblaze_patterns.py` over abbreviations.

Keep generated files, build outputs, caches, and local configuration out of version control. Add `.gitignore` entries as soon as toolchains are introduced.

## Testing Guidelines

Place automated tests under `tests/automated/` using filenames that identify the unit or behavior under test, such as `test_pixel_map.py`. Place manual checklists under `tests/manual/`. Cover logic that can be tested off-device, especially LED mapping, generated configuration, timing assumptions, and power-budget calculations.

For hardware-dependent behavior, document manual verification steps until automated hardware-in-the-loop tests exist.

## Commit & Pull Request Guidelines

This repository has no commit history yet, so use a simple imperative commit style: `Add LED pattern controller`, `Document wiring layout`, or `Fix battery cutoff threshold`.

Pull requests should include a short summary, testing performed, any hardware used for verification, and photos or screenshots when visual output, wiring, or enclosure changes are involved. Link related issues when available and call out any required setup, calibration, or flashing steps.

## Agent-Specific Instructions

Before making file changes, align on intended behavior, scope, and constraints when the request is ambiguous. Keep edits focused, preserve user changes, and update this guide when repository tooling or structure changes.

## Progress Preservation

After each meaningful hardware-design, CAD, or generated-asset change, save a
short resumable checkpoint to disk before handing off. Put it with the relevant
design documentation and include: the current review/output files, accepted
decisions and dimensions, validation performed and results, rejected or unsafe
variants, the exact regeneration command, and the next physical-review steps.
Update the checkpoint again whenever later work changes any of those facts.
