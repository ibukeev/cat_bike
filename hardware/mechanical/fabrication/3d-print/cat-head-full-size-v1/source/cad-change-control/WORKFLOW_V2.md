# Cat-head CAD iteration workflow V2

V2 is a recovery workflow for short, visually grounded CAD changes. It replaces
the long chain of review versions as the default process. V1 remains useful for
read-only BREP diagnostics, but a V1 PASS never authorizes a V2 candidate.

## Why V2 exists

The failed process optimized local proxies such as zero collision volume while
losing the intended head. It also mixed sources from different reviews and let
one long-running chat create, repair, and validate its own geometry. V2 removes
those degrees of freedom.

The workflow has one invariant:

> The candidate is the canonical assembly with exactly one approved object
> changed. Everything else is byte-for-byte or shape-for-shape preserved.

## Phase 0: retire contaminated sessions

For the old CAD chat:

1. Press `Esc` until the active task reports that it was interrupted.
2. Run `/ps`; if the task left a background terminal, run `/stop`.
3. Run `/rename cad-v41-aborted-do-not-resume`.
4. Run `/archive` and relaunch Codex in the repository.

Do not use `/delete`; the old transcript is useful forensic evidence. `/clear`
also starts a fresh chat, but archiving makes accidental resumption less likely.

## Phase 1: choose one canonical baseline

This is a human visual decision, not an agent inference.

1. Select one existing FCStd that is closest to the last visually acceptable
   whole head.
2. Render that exact file from front, rear, left, right, top, and bottom with
   all intended production objects visible.
3. Reject it if any element is missing, hidden, displaced, or visibly damaged.
4. Copy `v2/baseline.template.json` to a new baseline manifest, fill the exact
   FCStd and six image paths, record their SHA-256 digests, and set the state and
   approval fields only after the user explicitly approves those images.
5. Run the V2 preflight validator with `--verify-files`.

There must be exactly one FCStd assembly in the manifest. A compound assembled
from V18, V34, OBJ components, or other review versions is not a baseline.

Until this phase passes, all geometry work remains blocked.

## Phase 2: approve one mutation contract

Copy `v2/iteration.template.json` and fill in:

- one internal FreeCAD target object name;
- one mutation kind and its exact numeric parameters;
- the user's exact instruction approving that scope;
- one new output directory and candidate FCStd path;
- one generator script and its SHA-256 digest;
- one user-approved FreeCAD/OCCT runtime manifest and its SHA-256 digest;
- one deterministic no-op snapshot path inside the new iteration directory;
- the fixed review image paths.
For a geometry replacement, also record a stable `design_id`, an independent
`tooling_revision`, and a canonical design signature computed from the
construction algorithm ID, normalized geometry parameters, aperture/LCS, and
mount datums. Check that signature against the rejected-design registry before
opening FreeCAD or creating output. A tooling correction increments only the
tooling revision; it must not invent a new design-version number or allow a
rejected geometry to return under a new iteration ID.


The contract is invalid if it permits more than one persisted candidate, repair
of a persisted candidate, a persisted run from a resumed CAD-mutation chat,
generator-authored validation, or deep OCCT release validation before visual
review. Iterative no-output tooling correction is governed separately by Phase
2A. The bounded target-fit checks in Phase 4 remain mandatory before visual
review.

Run preflight before writing geometry:

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/validate_iteration_v2.py \
  --baseline path/to/approved-baseline-v2.json \
  --contract path/to/iteration-v2.json \
  --verify-files \
  --require-new-output
```

## Phase 2A: develop and prove tooling without creating a candidate

The one-shot boundary starts only when `run_iteration_v2.py` creates the
persisted candidate output directory. Tooling development before that boundary
is an iterative engineering loop, not a sequence of disposable CAD candidates.

Keep the approved baseline, numeric geometry parameters, signed datums,
topology intent, and physical behavior fixed throughout this phase. A tooling
correction may increment `tooling_revision`; it must not invent a new design ID
or reject a design that was never constructed and persisted. Any proposed
change to the fixed design contract stops this phase for explicit user review.

The tooling loop has two mandatory test tiers:

1. **Deterministic and synthetic tests.** Exercise parameter normalization,
   coordinate frames, datum direction and handedness, root projections,
   bounds, metadata schemas and value types, semantic key/identifier
   collisions, known rejected signatures, and deliberately failing regressions.
2. **Pinned-runtime construction preflight.** Open the canonical FCStd
   read-only in the approved FreeCAD/OCCT runtime and invoke the exact shared
   geometry kernel and finalization functions used by the eventual generator.
   In a disposable unsaved target, construct the complete replacement and all
   Booleans, assign the target shape, create and assign every typed metadata
   property, recompute, and then run identity, placement, constructability,
   valid/closed/single-solid, datum-frame, and determinable product-defect
   checks before closing without saving.

During Phase 2A:

- do not call `saveAs()` or save any opened document;
- do not create the candidate iteration directory, FCStd/STEP/mesh output,
  review render, preservation snapshot, or promotion artifact;
- keep construction and finalization logic in shared version-controlled
  functions used by both the preflight and generator; the preflight must not
  skip or copy shape assignment, property creation, typed metadata assignment,
  recompute, or final assertions;
- allow repeat executions only to correct tooling while the design contract is
  unchanged;
- record every user-reported defect in scope as a named measurable regression
  or explicit manual visual hold; and
- distinguish `UNIT_TEST_PASS`, `IN_MEMORY_CONSTRUCTION_PASS`,
  `IN_MEMORY_FINALIZATION_PASS`, and `CANDIDATE_READY`; none implies the next
  one.

The pinned-runtime report must explicitly record:

- `target_assignment_performed=true`;
- `metadata_assignment_performed=true`;
- `recompute_performed=true`;
- `final_assertions_performed=true`;
- `save_as_called=false` and `document_save_called=false`; and
- `candidate_exists=false` and `geometry_export_created=false`.

A report with `target_assignment_performed=false`, a shape-only construction
result, or unexecuted metadata/finalization code does not satisfy Phase 2A.

A tooling report may contain logs and deterministic JSON under a separate
`reports/generated/cat-head-cad-tooling/` run directory, but it must contain no
persisted geometry and must never be presented as candidate validation.

If either tier fails, classify it as `TOOLING_FAILURE__NO_CANDIDATE_CREATED`,
correct the version-controlled tooling, and rerun Phase 2A. Do not quarantine a
nonexistent candidate, consume a candidate iteration ID, start a design
version, or move to visual review. Only a recorded pass from both tiers permits
Phase 3.

## Phase 3: generate one disposable candidate

Enter this phase only after Phase 2A passes for the exact generator, shared
kernel/finalizer, contract, baseline, and runtime-manifest hashes that the
runner will use. Changing any of those invalidates the construction preflight.

Run only through the bounded runner:

```bash
python3 hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/run_iteration_v2.py \
  --baseline path/to/approved-baseline-v2.json \
  --contract path/to/iteration-v2.json \
  --freecad-appdir /path/to/verified/FreeCAD-AppDir
```

The runner:

- revalidates all pinned inputs;
- verifies the approved runtime probe plus the pinned AppRun, FreeCAD, Part,
  TKernel, and TKBRep artifact hashes before launching the generator;
- refuses an existing output directory;
- invokes the pinned generator once;
- terminates the process group at the contract timeout, capped at 300 seconds;
- verifies that the canonical baseline hash is unchanged afterward;
- records success or quarantine status independently of the generator;
- captures the generator's single pre-mutation `saveAs` backup as
  `no-op-snapshot.FCStd`;
- restores the canonical `GuiDocument.xml`, thumbnail, and every presentation
  payload referenced by the GUI document to both snapshot and candidate,
  while proving that no `Shape.brp` payload changed;
- never retries or repairs.

The generator must open the canonical FCStd, save a candidate copy, modify the
existing target object in place, perform one final save, and preserve all other
internal object names. This exact `open -> saveAs -> mutate target -> save`
sequence is required because the first save is the same-session, same-runtime
no-op reference. It must not rebuild a new document from selected source
objects.

## Phase 4: cheap preservation, target-fit, and visual gates

First run the independent FCStd comparison through the same FreeCAD runtime:

```bash
CAT_HEAD_FREECAD_APPDIR=/path/to/verified/FreeCAD-AppDir
timeout 300s env PYTHONPATH="$CAT_HEAD_FREECAD_APPDIR/usr/lib" \
  "$CAT_HEAD_FREECAD_APPDIR/AppRun" python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/compare_fcstd_preservation_v2.py \
  --baseline path/to/approved-baseline-v2.json \
  --contract path/to/iteration-v2.json \
  --report reports/generated/cat-head-cad-iterations/<iteration-id>/preservation-report.json
```

The comparison requires identical object sets and exact preservation of every
non-target object's internal name, label, type, property schema, placement,
visibility, and group membership. Protected Part shape identity is the SHA-256
of each raw `<ObjectName>.Shape.brp` archive entry compared between the
same-runtime pre-mutation snapshot and candidate. It is not a hash of
`exportBrepToString()` from the differently-authored canonical file.

The candidate and snapshot must retain every canonical GUI/presentation entry
byte-for-byte. The runner, snapshot, candidate, and comparator must all match
the user-approved FreeCAD/OCCT runtime manifest. An unapproved runtime,
missing no-op backup, changed presentation payload, or changed protected BREP
is a preservation failure. The target is compared to the no-op snapshot for
shape and to the canonical file for metadata and placement.

### Exact data versus geometric measurement

Use exact comparison for hashes, archive payloads, object sets, labels,
property schemas, placements, visibility, group membership, contract values,
and stored datum coordinates/directions. Do not infer those values back from
faces or tessellation when authoritative data exists.

FreeCAD/OCCT intersection volumes, face-derived axes, distances, and angular
measurements require gate-specific tolerances fixed in the contract before the
candidate run. Each report must include raw measurement, expected value,
tolerance, and residual. A failed predicate may be adjudicated as a validator
defect, but its tolerance may not be widened after seeing the result and the
candidate must remain unchanged.

After preservation passes, run the mutation-specific independent pre-visual
validator. It must be separate from the generator, read-only, fail closed, and
write only its report in the already-created iteration directory. For the V4
right-eye serviceable-fit lineage, the proposed command is:

```bash
CAT_HEAD_FREECAD_APPDIR=/path/to/verified/FreeCAD-AppDir
timeout 300s env PYTHONPATH="$CAT_HEAD_FREECAD_APPDIR/usr/lib" \
  "$CAT_HEAD_FREECAD_APPDIR/AppRun" python \
  hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/validate_right_eye_serviceable_fit_previsual_v4.py \
  --baseline hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/v2/approved-baseline-v34.json \
  --contract hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/source/cad-change-control/v2/right-eye-serviceable-fit-prototype-v4.json \
  --preservation-report reports/generated/cat-head-cad-iterations/right-eye-serviceable-fit-prototype-v4/preservation-report.json \
  --report reports/generated/cat-head-cad-iterations/right-eye-serviceable-fit-prototype-v4/previsual-validation.json
```

Before any image is presented for approval, this bounded validator must prove:

- one valid, closed, connected target solid with no self-intersection;
- exact preservation of every protected object;
- the complete target-versus-shell component matrix and every named historical
  contact regression;
- target containment, allowed aperture-plane occupancy, and the contracted
  non-mating clearances;
- zero mount, chamber, or cap occupancy in the straight-on and angular aperture
  viewing frustum;
- collision-free eye insertion/removal and rear-cap seating/removal sweeps;
- collision-free bolt, washer, nyloc, and straight tool paths at both fixed
  mount datums; and
- numeric root engagement, bore-edge material, aperture/LCS, cap/diffuser fit,
  and minimum-wall preservation.

This stage may use bounded OCCT intersection and distance operations because
they directly gate known target-fit, containment, access, and service defects.
It is not the deep release-validation phase. Any failure sets
`approval_presentation_allowed=false`; no approval pack may be shown. If a
preserved mount datum cannot pass access or containment, stop with
`BLOCKED__MOUNT_DATUM_CONFLICT` and do not move it automatically.

If this read-only validator times out, crashes, or fails internally after the
runner and preservation comparison passed, classify the result as
`VALIDATOR_HOLD__CANDIDATE_IMMUTABLE`. Pin the candidate and preservation
hashes and keep the candidate ineligible for review, but do not quarantine,
regenerate, repair, or replace its geometry. The failed validator invocation
must not be repeated unchanged.

Develop any validator correction in a separate tooling session. Keep all gates,
datums, tolerances, and expected physical outcomes fixed; add stage timing and
progress diagnostics; short-circuit collision-only work with AABB tests; and
prove regression equivalence plus bounded runtime before authorizing one new
hash-pinned validator invocation in a fresh verifier session. That verifier may
open the exact held candidate read-only and must never save it.

Only after preservation and every pre-visual gate pass may the review pack be
presented. Whole-head images must be opaque and show baseline and candidate
side-by-side. Include exterior close-ups of every aperture corner, an interior
view of both flange backs, separately colored bolt/washer/nut/tool envelopes,
a rear-cap installation/removal view, and a section through the chamber and
both mounts. Red geometry is reserved for failed-overlap evidence, which is
never an approval presentation. The agent stops after presenting the passing
pack.

Approval must identify the candidate, for example:

```text
APPROVE VISUAL <iteration-id> <candidate-sha256>
```

Any requested correction rejects the candidate. Do not repair it in the same
chat; start a new iteration from the canonical baseline.

## Phase 5: independent deep release verification

After explicit visual approval, archive the generator chat and start a fresh
verifier chat. The verifier may run the expensive checks relevant to the one
mutation: OCCT health, collision/clearance, union, slicer, or manufacturing
checks. It must not alter the candidate.

A technical PASS remains evidence, not promotion. Promotion, mirroring,
production union, STL/3MF export, slicing, G-code, printing, and committing are
separate user-authorized actions.

## Failure policy

- A deterministic, synthetic, or pinned-runtime in-memory failure before any
  candidate output exists is a tooling-development failure. Keep the design
  contract fixed, correct the tooling, and repeat Phase 2A; do not consume a
  candidate or reject the design.
- Generator timeout/crash, partial output, runtime mismatch, missing no-op
  snapshot, presentation loss, preservation failure, or visual rejection:
  quarantine the output and stop.
- A timeout/crash/implementation defect in a read-only validator after
  successful generation and preservation places the exact candidate in
  `VALIDATOR_HOLD__CANDIDATE_IMMUTABLE`. Do not regenerate it; correct and
  preflight only the validator, then use a fresh verifier session.
- Never create V42 as a repair of V41. New attempts use descriptive iteration
  IDs and restart from the canonical baseline.
- Never source geometry from a failed candidate.
- Never solve a failed local metric by deleting or moving unrelated geometry.
- Report the smallest blocker in plain language; do not manufacture another
  candidate automatically.

## Clean-session starter prompt

Use this only after the baseline, mutation contract, deterministic tests, and
full pinned-runtime in-memory construction-and-finalization preflight all pass:

```text
Read the cat-head AGENTS.md and WORKFLOW_V2.md. This is one disposable CAD
candidate, not an autonomous repair loop. Verify the recorded no-output tooling
and full in-memory construction-and-finalization preflight matches the exact
pinned generator/finalizer, contract, baseline, and runtime hashes. Generate
exactly one candidate through
run_iteration_v2.py.
Modify only the contract's target object and operation. Stop on any timeout or
error; do not retry or repair. Run the independent preservation comparison,
then run every mutation-specific pre-visual target-fit, containment, access,
service-motion, and known-defect regression gate. Present the opaque review pack
only if all gates pass, then stop for my explicit visual approval. Do not run
deep release checks, promote, mirror, export, slice, commit, or use any failed
review as a source.
If the read-only validator times out or fails internally after preservation
passes, hold the exact candidate hash and stop; do not regenerate it or rerun
the same validator unchanged.
```
