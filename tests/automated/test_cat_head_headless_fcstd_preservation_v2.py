import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/fcstd_preservation_v2.py"
)
SPEC = importlib.util.spec_from_file_location("headless_preservation_v2", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


DOCUMENT_XML = b'<Document SchemaVersion="4" ProgramVersion="test"/>'


def write_fcstd(path: Path, entries: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("Document.xml", DOCUMENT_XML)
        archive.writestr("Body.Shape.brp", b"shape-bytes")
        for name, payload in entries.items():
            archive.writestr(name, payload)


class HeadlessFcstdPreservationV2Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="headless-fcstd-")
        root = Path(self.temporary.name)
        self.canonical = root / "canonical.FCStd"
        self.target = root / "target.FCStd"
        write_fcstd(self.canonical, {})
        write_fcstd(self.target, {})

    def tearDown(self):
        self.temporary.cleanup()

    def test_default_mode_rejects_missing_gui_document(self):
        with self.assertRaisesRegex(ValueError, "lacks GuiDocument.xml"):
            MODULE.presentation_entry_names(self.canonical)

    def test_headless_mode_accepts_consistent_absence_without_rewrite(self):
        digest_before = MODULE.sha256_file(self.target)
        shape_before = MODULE.raw_shape_digests(self.target)
        result = MODULE.restore_canonical_presentation(
            self.canonical,
            self.target,
            allow_missing_gui_document=True,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["headless_canonical"])
        self.assertFalse(result["target_archive_rewritten"])
        self.assertEqual(MODULE.sha256_file(self.target), digest_before)
        self.assertEqual(MODULE.raw_shape_digests(self.target), shape_before)
        self.assertEqual(
            MODULE.visibility_map(
                self.target,
                allow_missing_gui_document=True,
            ),
            {},
        )

    def test_headless_mode_rejects_unexpected_gui_document(self):
        write_fcstd(
            self.target,
            {"GuiDocument.xml": b"<GuiDocument/>",},
        )
        with self.assertRaisesRegex(ValueError, "headless presentation check failed"):
            MODULE.restore_canonical_presentation(
                self.canonical,
                self.target,
                allow_missing_gui_document=True,
            )

    def test_headless_mode_rejects_unexpected_thumbnail(self):
        write_fcstd(self.target, {"thumbnails/Thumbnail.png": b"png"})
        comparison = MODULE.presentation_comparison(
            self.canonical,
            self.target,
            allow_missing_gui_document=True,
        )
        self.assertEqual(comparison["status"], "FAIL")
        self.assertEqual(
            comparison["unexpected_headless_entries"],
            ["thumbnails/Thumbnail.png"],
        )

    def test_headless_canonical_with_thumbnail_is_invalid(self):
        write_fcstd(self.canonical, {"thumbnails/Thumbnail.png": b"png"})
        with self.assertRaisesRegex(ValueError, "unexpected thumbnails"):
            MODULE.presentation_entry_names(
                self.canonical,
                allow_missing_gui_document=True,
            )


if __name__ == "__main__":
    unittest.main()
