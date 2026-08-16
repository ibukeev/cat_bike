#!/usr/bin/env python3
"""Create a clean, non-moving archive view for superseded pilot reviews.

Every canonical review directory remains at its exact existing path so CAD
configs, checkpoints, hashes, and regeneration commands stay valid. Nautilus
hides superseded names through its supported ``.hidden`` index. Categorized
directory symlinks under ``90-archive`` provide the navigable archive view.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import date
from pathlib import Path


PROJECT_REL = Path(
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1"
)
PILOT_REL = PROJECT_REL / "output/70-freecad-pilots/opposite-side-flange-pilot-v1"
ARCHIVE_DATE = "2026-08-16"
ARCHIVE_REL = PILOT_REL / "90-archive" / ARCHIVE_DATE

# These are accepted/current sources, directly useful physical-review packs, or
# inputs needed to regenerate the next controlled C009-removal proposal.
KEEP = {
    "bilateral-ab-mirror-review-v1",
    "eye-bilateral-exact-mirror-review-v9",
    "left-owner-reference-v1",
    "left-upper-head-c001-topology-repair-v2",
    "left-upper-head-c003-topology-repair-v1",
    "left-upper-head-deterministic-topology-repair-v1",
    "left-upper-head-full-owner-c001-c003-integration-v1",
    "primary-ear-bilateral-exact-mirror-review-v2",
    "primary-ear-bilateral-through-channel-review-v1",
    "reference",
    "right-a-surface-open-insert-correction-v1",
    "right-ab-owner-integration-review-v1",
    "right-ab-under-ear-opening-print-orientation-review-v2",
    "right-b-hole-access-review-v1",
    "right-ear-deterministic-topology-repair-v1",
    "right-eye-exact-owner-integration-review-v17",
    "right-eye-full-context-review-v18",
    "right-eye-production-owner-review-v8",
    "right-eye-topology-repaired-full-context-review-v5",
    "right-eye-v17-full-topology-repair-step-review-v4",
    "right-lower-face-owner-integration-review-v14",
    "right-lower-face-topology-repair-review-v12",
    "right-lower-face-topology-repair-review-v13",
    "right-panel-topology-repair-v1",
    "right-primary-ear-integrated-through-channel-review-v3",
    "right-upper-approved-c027-c012-context-review-v25",
    "right-upper-c001-eye-clearance-review-v26",
    "right-upper-c012-eye-clearance-review-v24",
    "right-upper-c027-eye-clearance-review-v19",
    "right-upper-head-deterministic-topology-repair-v3",
}

# Preserve known user-modified files in place. They must not be hidden in a
# mechanical archive move or included in this cleanup commit.
PRESERVE_DIRTY = {
    "right-eye-one-body-serviceable-module-review-v1",
    "right-eye-upper-rim-structural-root-review-v1",
}


def run(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=repo,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def category(name: str) -> str:
    lower = name.lower()
    if "primary-ear" in lower or lower.startswith("right-ear"):
        return "60-ear-history"
    if "eye" in lower:
        return "50-eye-history"
    if "lower-face" in lower:
        return "40-lower-face-history"
    if "upper-head" in lower or lower.startswith("right-upper") or lower.startswith("left-upper"):
        return "30-upper-head-history"
    if any(token in lower for token in ("panel", "right-a", "right-b", "right-ab", "bilateral-ab")):
        return "20-panel-ab-history"
    return "10-legacy-and-duplicate-history"


def directory_inventory(path: Path) -> dict[str, object]:
    digest = hashlib.sha256()
    count = 0
    total = 0
    for item in sorted((p for p in path.rglob("*") if p.is_file()), key=lambda p: p.as_posix()):
        rel = item.relative_to(path).as_posix()
        size = item.stat().st_size
        count += 1
        total += size
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(str(size).encode("ascii"))
        digest.update(b"\0")
        with item.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        digest.update(b"\0")
    return {
        "file_count": count,
        "total_bytes": total,
        "content_inventory_sha256": digest.hexdigest(),
    }


def tracked(repo: Path, path: Path) -> bool:
    result = run(repo, "git", "ls-files", "--", path.as_posix())
    return bool(result.stdout.strip())


def dirty(repo: Path, path: Path) -> bool:
    result = run(repo, "git", "status", "--porcelain=v1", "--", path.as_posix())
    return bool(result.stdout.strip())


def build_plan(repo: Path) -> tuple[list[dict[str, object]], list[str]]:
    pilot = repo / PILOT_REL
    moves: list[dict[str, object]] = []
    preserved: list[str] = []
    navigation_directories = {"00-current", "90-archive"}
    for source in sorted(
        p
        for p in pilot.iterdir()
        if p.is_dir() and p.name not in navigation_directories
    ):
        name = source.name
        if name in KEEP:
            preserved.append(name)
            continue
        if name in PRESERVE_DIRTY or dirty(repo, source.relative_to(repo)):
            preserved.append(name)
            continue
        destination_rel = ARCHIVE_REL / category(name) / name
        moves.append(
            {
                "name": name,
                "canonical_path": source.relative_to(repo).as_posix(),
                "archive_link_path": destination_rel.as_posix(),
                "category": category(name),
                "tracked": tracked(repo, source.relative_to(repo)),
                **directory_inventory(source),
            }
        )
    return moves, preserved


def write_archive_docs(
    repo: Path, moves: list[dict[str, object]], preserved: list[str]
) -> None:
    archive = repo / ARCHIVE_REL
    archive.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": "cat-head-review-archive-manifest-v1",
        "archive_date": ARCHIVE_DATE,
        "policy": (
            "Non-moving archive view. No files moved or deleted and no CAD geometry "
            "modified. Canonical paths, hashes, configs, checkpoints, and dirty work remain unchanged."
        ),
        "pilot_root": PILOT_REL.as_posix(),
        "archive_root": ARCHIVE_REL.as_posix(),
        "preserved_top_level_directories": sorted(preserved),
        "archive_entries": moves,
    }
    (archive / "ARCHIVE_MANIFEST_2026-08-16.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    counts: dict[str, int] = {}
    for move in moves:
        counts[str(move["category"])] = counts.get(str(move["category"]), 0) + 1
    lines = [
        "# Opposite-Side Flange Pilot Archive",
        "",
        f"Archived on {date.fromisoformat(ARCHIVE_DATE).isoformat()}.",
        "",
        "This is a non-moving archive view. No review artifact was moved or deleted and no CAD geometry was changed.",
        "The original top-level directories remain canonical so all configs and checkpoints keep working. Nautilus hides superseded names using `../../.hidden`; these category folders contain links back to the canonical directories.",
        "Use `ARCHIVE_MANIFEST_2026-08-16.json` to verify each canonical path, archive-view link, and content-inventory SHA-256.",
        "",
        "## Categories",
        "",
    ]
    for key in sorted(counts):
        lines.append(f"- `{key}/`: {counts[key]} archived review directories")
    lines.extend(
        [
            "",
            "## Preserved at the pilot root",
            "",
            "Accepted/current source chains remain visible at their original paths. Two locally modified historical FreeCAD reviews also remain visible and were deliberately excluded from the archive view.",
            "",
        ]
    )
    (archive / "README.md").write_text("\n".join(lines), encoding="utf-8")

    current = repo / PILOT_REL / "00-current"
    current.mkdir(exist_ok=True)
    (current / "README.md").write_text(
        "# Current working set\n\n"
        "The V33 C009 reposition preview is rejected because it floats in the translucent under-ear panel region.\n\n"
        "Next controlled CAD bucket: start from the accepted pre-V33 upper-head baseline, remove C009 entirely on the right side, add no replacement geometry, and validate the full head/eye/under-ear context before any mirror or integration.\n\n"
        "Accepted source directories remain at this pilot root. Superseded and rejected iterations are under `../90-archive/2026-08-16/`.\n",
        encoding="utf-8",
    )


def apply_archive_view(repo: Path, moves: list[dict[str, object]]) -> None:
    for move in moves:
        source = repo / str(move["canonical_path"])
        destination = repo / str(move["archive_link_path"])
        if destination.exists():
            if destination.is_symlink() and destination.resolve() == source.resolve():
                continue
            raise SystemExit(f"Refusing to overwrite archive-view destination: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        relative_target = Path(os.path.relpath(source, start=destination.parent))
        destination.symlink_to(relative_target, target_is_directory=True)
        if destination.resolve() != source.resolve():
            raise SystemExit(f"Archive-view link verification failed: {destination}")

    hidden = repo / PILOT_REL / ".hidden"
    hidden.write_text(
        "\n".join(sorted(str(move["name"]) for move in moves)) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="create the verified archive view")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[6]
    moves, preserved = build_plan(repo)
    print(f"archive candidates: {len(moves)}")
    print(f"preserved top-level directories: {len(preserved)}")
    for move in moves:
        print(f"{move['canonical_path']} -> {move['archive_link_path']}")
    if not args.apply:
        print("dry run only; rerun with --apply")
        return
    apply_archive_view(repo, moves)
    write_archive_docs(repo, moves, preserved)
    print("non-moving archive view and link verification complete")


if __name__ == "__main__":
    main()
