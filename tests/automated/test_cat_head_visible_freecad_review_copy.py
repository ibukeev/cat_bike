import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CAD_CONTROL = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control"
)
MODULE_PATH = CAD_CONTROL / "create_editable_base_v1_visible_freecad_review.py"
SPEC = importlib.util.spec_from_file_location("visible_freecad_review", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def write_candidate(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "Document.xml",
            b'<Document SchemaVersion="4" ProgramVersion="test"/>',
        )
        archive.writestr("Body.Shape.brp", b"exact-shape")


def write_presentation(path: Path) -> None:
    gui = (
        b'<GuiDocument><ViewProviderData Count="0"/>'
        b'<Camera settings="camera"/></GuiDocument>'
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "Document.xml",
            b'<Document SchemaVersion="4" ProgramVersion="test"/>',
        )
        archive.writestr("Body.Shape.brp", b"reserialized-shape")
        archive.writestr("GuiDocument.xml", gui)


class VisibleFreecadReviewCopyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="visible-fcstd-")
        root = Path(self.temporary.name)
        self.candidate = root / "candidate.FCStd"
        self.presentation = root / "presentation.FCStd"
        self.output = root / "visible.FCStd"
        write_candidate(self.candidate)
        write_presentation(self.presentation)

    def tearDown(self):
        self.temporary.cleanup()

    def test_adds_only_presentation_and_preserves_shape_payload(self):
        result = MODULE.write_visible_review_archive(
            self.candidate,
            self.presentation,
            self.output,
        )
        self.assertTrue(result["candidate_payloads_unchanged"])
        self.assertTrue(result["raw_shape_payloads_unchanged"])
        self.assertEqual(
            result["presentation_entries_added"],
            ["GuiDocument.xml"],
        )
        self.assertEqual(
            MODULE.preservation.raw_shape_digests(self.output),
            {"Body": MODULE.preservation.sha256_bytes(b"exact-shape")},
        )

    def test_refuses_overwrite(self):
        self.output.write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            MODULE.write_visible_review_archive(
                self.candidate,
                self.presentation,
                self.output,
            )


if __name__ == "__main__":
    unittest.main()
