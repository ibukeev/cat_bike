# Cat-head CAD change-control tooling

The 2026-09-10 large-head cleanup retained shared safety tooling, schemas,
selected print-source helpers, final midsize Rev112/113 tooling, and dependencies
read by the existing regression tests. Obsolete one-off macros and unrelated
iteration scripts/configs were retired with their output history.

Before CAD work read [the scoped rules](../../AGENTS.md) and
[WORKFLOW_V2.md](WORKFLOW_V2.md). Cleanup did not authorize a new baseline,
construction, rendering, integration, export, slicing, or print release.

Many retained regression contracts are historical and still name retired inputs.
The local cleanup-recovery archives are now permanently deleted. Preservation of
the code does not make those old workflows runnable. If required evidence is
absent, stop until an explicitly approved source is available and hash-verified;
never invent replacement input geometry, repin stale PASS reports, or bypass
missing-file guards. Workflow redesign remains a separate user-aligned task.

The final midsize head/mouth wrappers remain deliberately fail-closed following
the earlier path-only contract migration. Their geometry and all authorization
pins are unchanged by this large-head cleanup.

The plain-Python safety and final-head checks can be run without FreeCAD:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.automated.test_small_v1_final_user_cutter_holes_rev112_contract tests.automated.test_small_v1_merged_mouth_pane_rev113_contract tests.automated.test_cat_head_visible_freecad_review_copy
```

The broad historical suite has known pre-existing failures; see
[the rebuild checkpoint](../../REBUILD_CHECKPOINT_2026-09-10.md) for the
before/after comparison. Do not claim it is all green.
