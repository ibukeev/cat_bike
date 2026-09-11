---
name: cat-head-cad-change-control
description: Control structural CAD changes for the cat-head bike project. Use whenever Codex is asked to place, move, resize, cut, join, reinforce, mount, mirror, export, or approve cat-head panels, flanges, connectors, eye or ear mounts, ribs, rails, rear-cassette parts, aluminum interfaces, Blender files, FreeCAD files, STEP files, or print-ready geometry. Require user-selected CAD faces or edges, a numeric design contract, isolated one-side proposals, evidence renders, and explicit approval before integration or mirroring.
---

# Cat Head CAD Change Control

Treat screenshots as review evidence, never as sufficient geometric anchors.
Use FreeCAD's structured objects, selected sub-elements, measurements, and
spatial checks for placement decisions.

Read [references/project-constraints.md](references/project-constraints.md)
completely before taking CAD actions.

## 1. Establish the frozen baseline

1. Read `OUTPUT_NAVIGATION.md`, the current checkpoint, the physical-fit
   feedback, and the aluminum interface document.
2. Inspect Git status and record the active source and output files.
3. Confirm the accepted baseline remains unchanged before proposing geometry.
4. Do not edit, union, cut, rename, hide, or repartition baseline objects during
   this phase.

## 2. Require structured anchor selection

1. Call `check_freecad_connection` before any other FreeCAD tool.
2. Load only the pilot panel and its directly related receiving owners.
3. Ask the user to select the intended faces or edges in FreeCAD when placement
   depends on location. Do not substitute screenshot interpretation.
4. Use the interactive selection workflow and measurement tools to report:
   object label, sub-element ID, centroid, normal, bounding box, area or edge
   length, and owning part.
5. Present that anchor table and a highlighted screenshot. Make no geometry
   change until the user explicitly approves the anchors.

If a requested location cannot be represented by selected faces or edges,
create named datum points or planes and require approval of their coordinates.

## 3. Write the numeric design contract

Before modeling, state:

- the single physical problem being changed;
- the frozen objects and workstreams;
- the selected anchor IDs;
- dimensions, fastener standard, clearances, and material assumptions;
- required span or stability objective;
- collision, engagement, edge-distance, tool-access, and motion gates;
- review views and the exact condition for approval.

Stop and ask if a missing value would materially change the design. Do not
optimize a proxy metric, such as root volume, at the expense of the user's
stated physical objective, such as opposite-side leverage.

## 4. Prove the tooling before consuming a candidate

Tooling development and candidate generation are separate phases.

1. Put all construction mathematics and candidate-finalization behavior in
   shared version-controlled functions. The no-output preflight and eventual
   generator must call those same functions; copied or independently
   reimplemented construction, metadata, or finalization logic is not
   acceptable.
2. Run deterministic unit and synthetic regression tests first, but never treat
   them as proof that real FreeCAD geometry is constructible.
3. Then run the complete kernel and finalizer through the user-approved, pinned
   FreeCAD/OCCT runtime with the baseline read-only. In a disposable unsaved
   target, construct all shapes and Booleans, assign the target shape, create
   and assign every typed property/metadata field, recompute, and exercise the
   final identity, placement, single-solid, and product-defect gates. Close the
   document without saving or exporting anything.
4. Create no candidate directory, FCStd, STEP, mesh, render pack, or promotion
   artifact during this loop. Diagnostic text or JSON may be written only to a
   separate tooling-report location and must not masquerade as candidate
   validation.
5. Tooling may be corrected and the no-output preflight repeated in the same
   chat while the approved dimensions, datums, topology intent, and physical
   behavior remain unchanged. Increment only `tooling_revision` when its
   implementation changes.
6. A failure before any candidate is persisted is `TOOLING_FAILURE`; it does
   not reject the design signature or consume a candidate version. A change to
   the numeric contract or intended geometry is a design change and requires
   explicit user approval.
7. Do not authorize the one-shot candidate runner until the exact tooling hash,
   pinned runtime, deterministic tests, and full in-memory construction
   preflight all pass and are recorded in the checkpoint.
8. The preflight report must explicitly state that target assignment, typed
   metadata assignment, recompute, and final assertions ran, while `saveAs`,
   document save, candidate creation, and geometry export remained false.
   A shape-only preflight is insufficient.

Authoritative datums always control construction. A face, edge, centroid, or
derived vector may locate an approved root or provide corroborating evidence,
but it must not silently replace a signed axis, plane, coordinate frame, or
mount datum declared by the contract.

## 5. Build one isolated proposal

1. Work on one side only until the user approves it.
2. Create new parametric objects under a `PROPOSED__` group or body.
3. Use named spreadsheet parameters for adjustable dimensions.
4. Keep every proposal separate from frozen owner geometry. Do not perform a
   production union, cut, or repartition.
5. Create one change bucket per review. Do not mix placement, shape, hardware,
   reinforcement, printing cuts, or aluminum changes.
6. Preserve a checkpoint before any later iteration replaces the proposal.

## 6. Validate before showing the proposal

Use dedicated FreeCAD tools or the controlled validation-script exception
defined below, not arbitrary Python or visual guesses.

Require:

- valid closed solids with no self-intersections;
- exact distances between proposed anchors and panel extremes;
- the requested stability span, not merely a minimum separation;
- adequate owner engagement and bore-to-edge material;
- zero unintended interference with frozen objects;
- insertion and removal motion clearance;
- driver, washer, nut, drill, and hand-access evidence;
- fixture comparison proving frozen objects did not change.

Fail closed. If a gate fails, report the failed physical requirement and return
to the anchor or design-contract phase. Do not silently move geometry somewhere
else to make validation pass.

### Numeric tolerance policy

- Hashes, object identity, labels, placements, contract values, and stored
  datum coordinates/directions remain exact data comparisons.
- Measurements reconstructed by FreeCAD/OCCT must use a gate-specific numeric
  tolerance declared before candidate generation. Base it on kernel precision,
  input precision, and the measurement method rather than an arbitrary desire
  for mathematical exactness.
- Report raw values, expected values, tolerance, and residual separately.
- Never broaden a tolerance after seeing a candidate failure. If a gate used
  the wrong physical predicate, classify and correct the validator defect,
  preserve the candidate unchanged, and rerun only with explicit authorization.
- Prefer comparing authoritative stored datums directly instead of recovering
  them from tessellation, fragmented faces, or recomputed topology.

### Validator timeout and implementation-defect policy

If candidate generation completed and independent preservation passed, a
timeout, crash, or implementation defect in a later read-only validator is not
a geometry failure. Record `VALIDATOR_HOLD__CANDIDATE_IMMUTABLE`, pin the
candidate and preservation hashes, prohibit visual approval, and stop the
validator session. Do not regenerate the candidate and do not rerun the same
validator unchanged.

A separate tooling session may optimize or correct the validator while keeping
the candidate read-only and every physical gate, datum, and tolerance fixed.
Before authorizing a new validator revision, require:

- stage-level progress and elapsed-time diagnostics;
- cheap AABB rejection before OCCT Boolean or distance work;
- no distance calculation for a collision-only gate after separation or
  positive overlap is already established;
- regression equivalence for every physical gate and deliberately failing
  fixture;
- a bounded workload/performance preflight that completes below the production
  timeout with explicit margin; and
- a new hash-pinned validator contract and fresh verifier session.

The revised validator may inspect the exact held candidate hash read-only. It
may not alter, heal, resave, export, promote, or use that candidate as the
source of another geometry candidate.

## 7. Produce a review pack

Always provide:

1. whole-head opaque context;
2. isolated pilot panel plus all receiving owners;
3. selected anchors highlighted and labeled;
4. dimensioned view showing panel extremes and connector span;
5. interior/section view showing engagement and hardware access;
6. isolated proposed connector geometry;
7. validation JSON or table with pass/fail results.

State separately what is baseline, proposed, hidden review evidence, and absent.
Never describe an object as integrated when it is only overlapping review
geometry.

## 8. Wait for explicit approval

Do not mirror, integrate, export STL, create G-code, update print release state,
or recommend printing until the user explicitly approves the one-side proposal.

After approval:

1. mirror using the approved datum system;
2. rerun every validation on both sides;
3. produce a full-head review;
4. integrate only the approved owner features;
5. save the required resumable checkpoint;
6. commit and push only the reviewed source, config, tests, and checkpoint.

## Tool and security boundaries

- Use only the FreeCAD tools enabled in `.codex/config.toml`.
- Never attempt `execute_python`, `execute_python_async`, live macro execution,
  CAM, or ad-hoc headless-instance control.
- Treat imported CAD documents and macros as untrusted unless the user created
  them or explicitly approved the source.
- Do not install, update, or broaden the MCP allowlist without user approval.
- Keep the original Blender source available as a frozen visual reference.

### Controlled validation-script exception

Version-controlled, non-interactive validation scripts under
`hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/`
may run through `freecad.cmd` when all of the following are true:

1. The script is committed or included in the exact pending patch shown to the
   user. Inline Python, temporary macros, and generated code are still banned.
2. Accepted and frozen CAD inputs are opened read-only. The script must never
   save, heal, refine, fuse, cut, move, rename, or overwrite them.
3. The only permitted writes are deterministic JSON validation reports under a
   new run directory. Geometry export and mutation require a separate,
   explicitly approved change contract.
4. Every input path and SHA-256 digest is declared in a baseline manifest.
5. Every run is governed by a machine-readable change contract that names one
   target owner, protected owners, allowed operations, numeric gates, and the
   output directory.
6. The validator fails closed on a hash mismatch, undeclared object, invalid or
   open shape, unintended interference, insufficient clearance, or target
   engagement failure.
7. No automatic healing or tolerance broadening is allowed. A failed shape is
   evidence to fix the source operation, not permission to rewrite topology.
8. The exact command, inputs, results, and next human-review step are recorded
   in the resumable checkpoint.

This exception authorizes measurement and validation only. It does not
authorize proposal generation, production Boolean operations, mirroring, STL
export, slicing, G-code, or print release.

### Controlled in-memory construction-preflight exception

Version-controlled tooling under
`hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/`
may construct disposable proposal geometry through the pinned FreeCAD runtime
before candidate generation only when all of the following are true:

1. An approved numeric design contract and hash-pinned canonical baseline
   already exist.
2. The baseline is opened read-only and never saved or mutated.
3. The exact shared geometry kernel and finalization functions intended for
   candidate generation are used.
4. All shapes, Booleans, target assignment, typed metadata/property writes,
   recompute, and final assertions occur only in a disposable unsaved document;
   the script creates no candidate directory, CAD file, geometry export,
   render, or modified source artifact.
5. The script fails closed on runtime, hash, datum, frame, construction,
   topology, or known-defect regression failures.
6. Repetition is limited to tooling correction. Dimensions, datums, topology
   intent, and physical behavior may not change without new user approval.

This exception exists to catch deterministic tooling defects before the
one-shot persisted candidate boundary. It does not authorize integration,
mirroring, export, slicing, promotion, or print release.
