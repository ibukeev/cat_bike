#!/usr/bin/env python3
"""Shared V2 helpers for runtime pinning and FCStd archive preservation."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree


SHAPE_SUFFIX = ".Shape.brp"
GUI_DOCUMENT = "GuiDocument.xml"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def unique_zip_infos(archive: zipfile.ZipFile) -> dict[str, zipfile.ZipInfo]:
    result: dict[str, zipfile.ZipInfo] = {}
    for info in archive.infolist():
        if info.filename in result:
            raise ValueError(f"duplicate FCStd archive entry: {info.filename}")
        result[info.filename] = info
    return result


def document_program_version(path: Path) -> str:
    with zipfile.ZipFile(path, "r") as archive:
        document_xml = archive.read("Document.xml")
    root = ElementTree.fromstring(document_xml)
    value = root.attrib.get("ProgramVersion")
    if not value:
        raise ValueError(f"{path}: Document.xml lacks ProgramVersion")
    return value


def visibility_map(
    path: Path,
    allow_missing_gui_document: bool = False,
) -> dict[str, bool]:
    with zipfile.ZipFile(path, "r") as archive:
        infos = unique_zip_infos(archive)
        if GUI_DOCUMENT not in infos:
            if not allow_missing_gui_document:
                raise ValueError(f"{path}: FCStd lacks {GUI_DOCUMENT}")
            thumbnails = sorted(
                name for name in infos if name.startswith("thumbnails/")
            )
            if thumbnails:
                raise ValueError(
                    f"{path}: headless FCStd has unexpected thumbnails: {thumbnails}"
                )
            return {}
        gui_xml = archive.read(GUI_DOCUMENT)
    root = ElementTree.fromstring(gui_xml)
    result: dict[str, bool] = {}
    for provider in root.findall(".//ViewProvider"):
        name = provider.attrib.get("name")
        if not name:
            continue
        for prop in provider.findall("./Properties/Property"):
            if prop.attrib.get("name") != "Visibility":
                continue
            value = prop.find("Bool")
            if value is None or value.attrib.get("value") not in {"true", "false"}:
                raise ValueError(f"{path}: invalid visibility for {name}")
            result[name] = value.attrib["value"] == "true"
            break
    return result


def raw_shape_digests(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path, "r") as archive:
        infos = unique_zip_infos(archive)
        return {
            name[: -len(SHAPE_SUFFIX)]: sha256_bytes(archive.read(name))
            for name in sorted(infos)
            if "/" not in name and name.endswith(SHAPE_SUFFIX)
        }


def raw_shape_comparison(
    reference_path: Path,
    candidate_path: Path,
    excluded_objects: Iterable[str] = (),
) -> dict[str, Any]:
    excluded = set(excluded_objects)
    reference = raw_shape_digests(reference_path)
    candidate = raw_shape_digests(candidate_path)
    reference_names = set(reference) - excluded
    candidate_names = set(candidate) - excluded
    checked_names = sorted(reference_names & candidate_names)
    mismatches = {
        name: {
            "reference_sha256": reference[name],
            "candidate_sha256": candidate[name],
        }
        for name in checked_names
        if reference[name] != candidate[name]
    }
    return {
        "reference_shape_count": len(reference),
        "candidate_shape_count": len(candidate),
        "checked_count": len(checked_names),
        "checked_objects": checked_names,
        "missing_shape_entries": sorted(reference_names - candidate_names),
        "added_shape_entries": sorted(candidate_names - reference_names),
        "mismatches": mismatches,
        "status": (
            "PASS"
            if not mismatches
            and reference_names == candidate_names
            else "FAIL"
        ),
    }


def presentation_entry_names(
    path: Path,
    allow_missing_gui_document: bool = False,
) -> tuple[str, ...]:
    with zipfile.ZipFile(path, "r") as archive:
        infos = unique_zip_infos(archive)
        if GUI_DOCUMENT not in infos:
            if not allow_missing_gui_document:
                raise ValueError(f"{path}: canonical FCStd lacks {GUI_DOCUMENT}")
            thumbnails = sorted(
                name for name in infos if name.startswith("thumbnails/")
            )
            if thumbnails:
                raise ValueError(
                    f"{path}: headless canonical FCStd has unexpected thumbnails: "
                    f"{thumbnails}"
                )
            return ()
        gui_root = ElementTree.fromstring(archive.read(GUI_DOCUMENT))
        referenced = {
            element.attrib["file"]
            for element in gui_root.iter()
            if element.attrib.get("file")
        }
        referenced.update(
            name for name in infos if name.startswith("thumbnails/")
        )
        names = {GUI_DOCUMENT, *referenced}
        missing = sorted(names - set(infos))
        if missing:
            raise ValueError(
                f"{path}: {GUI_DOCUMENT} references missing entries: {missing}"
            )
        return tuple(info.filename for info in archive.infolist() if info.filename in names)


def presentation_comparison(
    canonical_path: Path,
    candidate_path: Path,
    allow_missing_gui_document: bool = False,
) -> dict[str, Any]:
    expected_names = presentation_entry_names(
        canonical_path,
        allow_missing_gui_document=allow_missing_gui_document,
    )
    with zipfile.ZipFile(canonical_path, "r") as canonical_archive:
        canonical_infos = unique_zip_infos(canonical_archive)
        canonical = {
            name: sha256_bytes(canonical_archive.read(name))
            for name in expected_names
        }
    with zipfile.ZipFile(candidate_path, "r") as candidate_archive:
        candidate_infos = unique_zip_infos(candidate_archive)
        candidate = {
            name: sha256_bytes(candidate_archive.read(name))
            for name in expected_names
            if name in candidate_infos
        }
    unexpected_headless_entries = (
        sorted(
            name
            for name in candidate_infos
            if name == GUI_DOCUMENT or name.startswith("thumbnails/")
        )
        if allow_missing_gui_document and not expected_names
        else []
    )
    missing = sorted(set(expected_names) - set(candidate))
    mismatches = {
        name: {
            "canonical_sha256": canonical[name],
            "candidate_sha256": candidate[name],
        }
        for name in sorted(set(expected_names) & set(candidate))
        if canonical[name] != candidate[name]
    }
    return {
        "canonical_entry_count": len(canonical_infos),
        "candidate_entry_count": len(candidate_infos),
        "expected_presentation_entry_count": len(expected_names),
        "missing_entries": missing,
        "mismatches": mismatches,
        "headless_canonical": bool(
            allow_missing_gui_document and not expected_names
        ),
        "unexpected_headless_entries": unexpected_headless_entries,
        "status": (
            "PASS"
            if not missing and not mismatches and not unexpected_headless_entries
            else "FAIL"
        ),
    }


def restore_canonical_presentation(
    canonical_path: Path,
    target_path: Path,
    allow_missing_gui_document: bool = False,
) -> dict[str, Any]:
    expected_names = presentation_entry_names(
        canonical_path,
        allow_missing_gui_document=allow_missing_gui_document,
    )
    if allow_missing_gui_document and not expected_names:
        result = presentation_comparison(
            canonical_path,
            target_path,
            allow_missing_gui_document=True,
        )
        if result["status"] != "PASS":
            raise ValueError(f"headless presentation check failed: {result}")
        result["target_archive_rewritten"] = False
        return result
    expected_set = set(expected_names)
    original_mode = target_path.stat().st_mode
    temporary_path: Path | None = None
    try:
        with zipfile.ZipFile(canonical_path, "r") as canonical_archive:
            canonical_infos = unique_zip_infos(canonical_archive)
            with zipfile.ZipFile(target_path, "r") as target_archive:
                target_infos = unique_zip_infos(target_archive)
                with tempfile.NamedTemporaryFile(
                    prefix=f".{target_path.name}.",
                    suffix=".tmp",
                    dir=target_path.parent,
                    delete=False,
                ) as temporary:
                    temporary_path = Path(temporary.name)
                with zipfile.ZipFile(
                    temporary_path,
                    "w",
                    allowZip64=True,
                ) as output_archive:
                    output_archive.comment = target_archive.comment
                    for info in target_archive.infolist():
                        if info.filename not in expected_set:
                            output_archive.writestr(info, target_archive.read(info.filename))
                    for name in expected_names:
                        output_archive.writestr(
                            canonical_infos[name],
                            canonical_archive.read(name),
                        )
        os.chmod(temporary_path, original_mode)
        os.replace(temporary_path, target_path)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    result = presentation_comparison(
        canonical_path,
        target_path,
        allow_missing_gui_document=allow_missing_gui_document,
    )
    result["target_archive_rewritten"] = True
    if result["status"] != "PASS":
        raise ValueError(f"presentation restoration failed: {result}")
    return result


def freecad_environment(appdir: Path) -> dict[str, str]:
    environment = os.environ.copy()
    freecad_lib = appdir / "usr/lib"
    old_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        f"{freecad_lib}:{old_pythonpath}" if old_pythonpath else str(freecad_lib)
    )
    return environment


def verify_runtime(
    appdir: Path,
    repository_root: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    observed_artifacts: list[dict[str, Any]] = []
    for artifact in manifest["artifacts"]:
        relative = Path(artifact["path"])
        path = appdir / relative
        observed_digest = sha256_file(path) if path.is_file() else None
        matches = observed_digest == artifact["sha256"]
        observed_artifacts.append(
            {
                "path": artifact["path"],
                "expected_sha256": artifact["sha256"],
                "observed_sha256": observed_digest,
                "matches": matches,
            }
        )
        if not matches:
            errors.append(f"runtime artifact mismatch: {artifact['path']}")

    probe = manifest["probe"]
    probe_path = repository_root / probe["script_path"]
    command = [str(appdir / "AppRun"), "python", str(probe_path)]
    observed_probe: dict[str, Any] | None = None
    if not errors:
        try:
            completed = subprocess.run(
                command,
                cwd=repository_root,
                env=freecad_environment(appdir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            errors.append(f"runtime probe could not complete: {exc}")
            completed = None
        if completed is None:
            pass
        elif completed.returncode != 0:
            errors.append(
                f"runtime probe failed with exit {completed.returncode}: "
                f"{completed.stdout.strip()}"
            )
        else:
            try:
                observed_probe = json.loads(completed.stdout)
            except json.JSONDecodeError as exc:
                errors.append(f"runtime probe returned invalid JSON: {exc}")

    expected_probe = {
        "freecad_version": manifest["freecad"]["version_record"],
        "freecad_program_version": manifest["freecad"]["program_version"],
        "occt_version": manifest["occt"]["version"],
        "python_version": manifest["python"]["version"],
        "platform_machine": manifest["platform"]["machine"],
    }
    if observed_probe is not None and observed_probe != expected_probe:
        errors.append("runtime probe does not match the approved manifest")
    return {
        "runtime_id": manifest["runtime_id"],
        "status": "PASS" if not errors else "FAIL",
        "probe_command": command,
        "expected_probe": expected_probe,
        "observed_probe": observed_probe,
        "artifacts": observed_artifacts,
        "errors": errors,
    }


def capture_single_no_op_backup(
    candidate_path: Path,
    snapshot_path: Path,
) -> dict[str, Any]:
    backups = sorted(
        candidate_path.parent.glob(f"{candidate_path.stem}.*.FCBak")
    )
    if len(backups) != 1:
        raise ValueError(
            "expected exactly one pre-mutation saveAs backup, found "
            f"{len(backups)}: {[path.name for path in backups]}"
        )
    if snapshot_path.exists():
        raise ValueError(f"no-op snapshot already exists: {snapshot_path}")
    shutil.copyfile(backups[0], snapshot_path)
    return {
        "source_backup": backups[0],
        "snapshot": snapshot_path,
        "sha256": sha256_file(snapshot_path),
    }
