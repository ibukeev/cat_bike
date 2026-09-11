# Cat-head CAD recovery rules

## Large-head rebuild cleanup — 2026-09-10

The user authorized aggressive filesystem cleanup because the large head will
be rebuilt. README.md is now the curated index. V6/V5/V2 working snapshots,
manual print masters, frozen references, and shared tiny/midsize dependencies
remain byte-identical. Removed history was SHA-verified before retirement; both
archive roots are now permanently deleted. Their inventories are preserved in
docs/cleanup/2026-09-10/ at repository root. The retained working files were
download-verified from GitHub before .cleanup-recovery/ was deleted.
This is not selection or approval of a new canonical rebuild baseline.
No geometry was regenerated and no authorization/hash guards were changed.
Read REBUILD_CHECKPOINT_2026-09-10.md before resuming work.

## Reports cleanup — 2026-09-10

The user authorized emptying reports/ and preserving selected lower-shell
print files in working/. Geometry and release status are unchanged.
Historical report inputs, including V34 baseline images and quarantined
candidates, were retired. The local recovery archive is now permanently deleted;
see ../../../../../docs/PROJECT_CLEANUP_PLAN.md. Do not promise local restoration.
If required evidence is absent, stop until an explicitly approved source is
available and hash-verified; do not bypass missing-input guards.
Midsize contracts received path-only migrations. Their old generator pins
intentionally remain fail-closed pending a fresh authorized preflight.
That reports cleanup was followed by the separately authorized large-head
filesystem cleanup documented above.

These instructions apply to every file under this directory. They override any
older checkpoint that encourages autonomous multi-step CAD iteration.

## Current recovery state

- There is no V2 canonical assembly until the user visually selects one exact
  FCStd and its six-view baseline pack is hash-pinned.
- V40 and V41 are evidence only. They are not approved geometry sources.
- Older review files may be inspected read-only, but no agent may assemble a
  new baseline by mixing objects from multiple review versions.
- While the canonical baseline is unselected, geometry mutation is blocked.
  The only allowed work is read-only comparison, baseline rendering, workflow
  tooling, and asking the user to select the baseline.

Read `source/cad-change-control/WORKFLOW_V2.md` before any CAD work.

## Tooling development boundary

A CAD candidate does not exist until the bounded candidate runner creates a
persisted candidate output. Before that boundary, an agent may iteratively
develop and debug version-controlled tooling in the same chat, provided all of
the following remain true:

- the hash-pinned canonical baseline and approved numeric design contract stay
  unchanged;
- the canonical FCStd is opened read-only and is never saved, healed, refined,
  moved, renamed, or otherwise mutated;
- FreeCAD construction is disposable and in memory only: no `saveAs`, FCStd,
  STEP, mesh, render pack, or candidate iteration directory may be created;
- the in-memory construction uses the exact shared geometry kernel and
  finalization path that the eventual candidate generator will call;
- the disposable in-memory target receives the proposed shape, every typed
  metadata/property assignment, recompute, and final invariant check without
  any document save;
- both synthetic tests and a pinned FreeCAD/OCCT full-construction-and-
  finalization preflight pass before the one-shot candidate runner is
  authorized; and
- every user-reported physical defect in scope has a named, measurable
  regression gate or an explicit manual visual hold.

A failure before this boundary is a tooling-development failure, not a failed
candidate or rejected design. Correct the tooling, increment only its tooling
revision when its implementation changes, and rerun the no-output preflight.
Do not create a new design ID, candidate iteration ID, or fresh chat merely for
a pre-candidate tooling bug. A change to dimensions, datums, topology intent,
or physical behavior is a design change and still requires explicit approval.

A preflight is incomplete if it skips target assignment, property creation,
typed metadata assignment, document recompute, or the final identity,
placement, and shape assertions. Its report must explicitly confirm those
operations ran while `saveAs` and all geometry-output writes remained false.

## Hard iteration boundary

Every persisted candidate must satisfy all of these rules:

1. Start a fresh Codex chat for the persisted candidate run. The preceding
   no-output tooling-development loop may remain in its tooling chat, but that
   chat must stop before the candidate runner is invoked.
2. Start from the one hash-pinned canonical FCStd. Do not reconstruct the head
   from review artifacts, STEP/OBJ fragments, or mixed checkpoints.
3. Use one target object and one explicitly approved mutation. A numeric
   operation may have several parameters, but it is still one mutation.
4. Preserve every non-target object's existence, internal name, label, shape,
   placement, visibility, and group membership exactly.
5. Do not delete, rename, hide, move, cut, shorten, filter, replace, or select
   the largest solid of any object unless that exact object and operation are
   the approved target in the V2 contract.
6. Run the candidate generator only through `run_iteration_v2.py`. Generation
   has a maximum wall time of 300 seconds, one candidate, no retry, and no
   repair loop.
7. A generator failure, generator timeout, partial candidate, missing no-op
   snapshot, or preservation failure quarantines that output. Never repair it
   in place or use it as the source of another candidate. A new persisted
   attempt needs a new iteration ID, fresh chat, and the canonical baseline.
   This rule does not convert a no-output tooling-preflight failure into a
   candidate.

If generation completed and preservation passed, a timeout or implementation
defect in a later read-only validator instead places the exact candidate hash
in `VALIDATOR_HOLD__CANDIDATE_IMMUTABLE`. The candidate remains ineligible for
visual approval, promotion, or use as a geometry source, but a separately
hash-pinned validator revision may inspect that same candidate read-only in a
fresh verifier session after its own bounded tooling preflight. Do not
regenerate the candidate merely to rerun validation.
8. The generator may create a candidate and review images only. It may not
   author its own PASS report or perform release validation.
9. Run the independent preservation comparison before asking for visual
   review. Any unapproved object, placement, visibility, or membership change
   is an automatic rejection.
10. Present six fixed whole-assembly views first: front, rear, left, right, top,
    and bottom. Do not substitute close-ups or hidden-object views.
11. Stop and wait for explicit user visual approval. Silence, numeric checks,
    previous approval, and an agent's judgment are not approval.
12. Only a new verifier chat may run expensive OCCT collision, topology,
    slicing, or manufacturing checks after visual approval.

## Stop conditions

Stop immediately and report the blocker if any of these is true:

- the V2 canonical baseline manifest is missing or not human-approved;
- the baseline hash or any baseline review image hash differs;
- the requested change touches more than one object;
- the request implies an unapproved deletion, cut, move, hide, or replacement;
- output already exists for the iteration ID;
- generation reaches 300 seconds, exits nonzero, or produces a partial file;
- the preservation comparison reports any non-target difference;
- a read-only validator times out or fails internally; in that case hold the
  preserved candidate by exact hash and stop without regenerating it;
- the result cannot be explained from the fixed six-view pack;
- the user has not explicitly approved the exact candidate hash.

Do not respond to a stop condition by broadening scope, searching for another
source version, adding more geometry, or starting another autonomous attempt.

## Promotion and repository hygiene

- Candidate outputs live only under
  `reports/generated/cat-head-cad-iterations/<iteration-id>/` until approved.
- Do not overwrite canonical or production files.
- Do not mirror, union, export STL/3MF, slice, generate G-code, print, commit, or
  promote a candidate unless the user separately authorizes that phase.
- Keep generator and verifier code separate. The session that writes candidate
  geometry may not declare it production-ready.
- Preserve all existing user changes in this dirty worktree.
