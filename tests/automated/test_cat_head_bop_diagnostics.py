import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / (
    "hardware/mechanical/fabrication/3d-print/cat-head-full-size-v1/"
    "source/cad-change-control/bop_diagnostics.py"
)
SPEC = importlib.util.spec_from_file_location("bop_diagnostics", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class BopDiagnosticTests(unittest.TestCase):
    def test_diagnostics_are_parsed_in_order(self):
        messages = [
            "BOP check found the following errors:\n"
            "Error in Face: BOPAlgo SelfIntersect\n"
            "ignored line\n"
            "Error in Edge: BOPAlgo SelfIntersect\n"
        ]
        self.assertEqual(
            MODULE.parse_bop_diagnostics(messages),
            [
                {
                    "message_index": 1,
                    "line_index": 2,
                    "subshape_type": "Face",
                    "error": "SelfIntersect",
                },
                {
                    "message_index": 1,
                    "line_index": 4,
                    "subshape_type": "Edge",
                    "error": "SelfIntersect",
                },
            ],
        )


if __name__ == "__main__":
    unittest.main()
