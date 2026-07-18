import json
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = (
    REPO_ROOT
    / "software"
    / "pixelblaze-patterns"
    / "cat-head"
    / "cat-head-pixel-map.json"
)
ROLE_PATH = (
    REPO_ROOT
    / "hardware"
    / "mechanical"
    / "fabrication"
    / "3d-print"
    / "cat-head-full-size-v1"
    / "config"
    / "gate1-panel-roles.json"
)


class CatHeadLightingMapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pixel_map = json.loads(MAP_PATH.read_text(encoding="utf-8"))
        cls.panel_roles = json.loads(ROLE_PATH.read_text(encoding="utf-8"))

    def test_locked_power_and_pixel_count(self):
        self.assertEqual(self.pixel_map["pixel_count"], 52)
        calculated_current = (
            self.pixel_map["pixel_count"]
            * self.pixel_map["max_current_per_pixel_ma"]
            / 1000
        )
        self.assertAlmostEqual(calculated_current, 3.12)
        self.assertAlmostEqual(
            self.pixel_map["theoretical_max_current_a"],
            calculated_current,
        )

    def test_segments_cover_every_pixel_once(self):
        covered = []
        for segment in self.pixel_map["segments"]:
            covered.extend(
                range(segment["start"], segment["start"] + segment["count"])
            )

        self.assertEqual(len(covered), len(set(covered)))
        self.assertEqual(sorted(covered), list(range(52)))

    def test_optical_allocations_cover_every_pixel_once(self):
        allocated = []
        whiskers = self.pixel_map["whiskers"]
        allocated.extend(item["pixel"] for item in whiskers["left"])
        allocated.extend(whiskers["reserved_pixels"])
        allocated.extend(pixel for eye in self.pixel_map["eyes"] for pixel in eye["pixels"])
        allocated.extend(
            pixel
            for pair in self.pixel_map["glow_facets"]
            for side in ("left", "right")
            for pixel in pair[side]["pixels"]
        )
        allocated.extend(item["pixel"] for item in whiskers["right"])

        self.assertEqual(len(allocated), 52)
        self.assertEqual(len(allocated), len(set(allocated)))
        self.assertEqual(sorted(allocated), list(range(52)))

    def test_whiskers_are_mirrored_and_reserved_pixels_are_fixed(self):
        whiskers = self.pixel_map["whiskers"]
        expected_lengths = [235, 250, 270, 285, 275, 255, 235]
        expected_angles = [18, 12, 6, 0, -6, -12, -18]

        for side in ("left", "right"):
            self.assertEqual(
                [item["visible_length_mm"] for item in whiskers[side]],
                expected_lengths,
            )
            self.assertEqual(
                [item["fan_angle_deg"] for item in whiskers[side]],
                expected_angles,
            )

        self.assertEqual(whiskers["reserved_pixels"], [7, 51])
        self.assertEqual(whiskers["ordered_length_m"], 9.0)

    def test_gate1_panel_ids_and_pair_order_match(self):
        map_pairs = self.pixel_map["glow_facets"]
        role_pairs = self.panel_roles["glow_pairs"]
        self.assertEqual(len(map_pairs), 7)
        self.assertEqual(len(role_pairs), 7)

        for mapped, source in zip(map_pairs, role_pairs):
            self.assertEqual(mapped["pair_id"], source["pair_id"])
            self.assertEqual(
                mapped["left"]["panel_id"],
                source["left_source_panel_id"],
            )
            self.assertEqual(
                mapped["right"]["panel_id"],
                source["right_source_panel_id"],
            )
            self.assertEqual(len(mapped["left"]["pixels"]), 2)
            self.assertEqual(len(mapped["right"]["pixels"]), 2)

    def test_eye_ids_match_gate1_roles(self):
        mapped_ids = {eye["unit_id"] for eye in self.pixel_map["eyes"]}
        source_ids = {eye["unit_id"] for eye in self.panel_roles["eye_diffusers"]}
        self.assertEqual(mapped_ids, source_ids)
        self.assertTrue(all(len(eye["pixels"]) == 4 for eye in self.pixel_map["eyes"]))

    def test_connector_and_brightness_contract(self):
        connector = self.pixel_map["connector"]
        self.assertEqual(connector["pins"]["1"], "+5V")
        self.assertEqual(connector["pins"]["2"], "RESERVED_ISOLATED")
        self.assertEqual(connector["pins"]["3"], "GND")
        self.assertEqual(connector["pins"]["4"], "DATA")
        self.assertGreaterEqual(connector["minimum_contact_current_a"], 4)

        caps = self.pixel_map["brightness_caps"]
        self.assertEqual(caps["riding"], 0.35)
        self.assertEqual(caps["show"], 0.6)
        self.assertEqual(caps["reserve"], 0.15)
        self.assertLessEqual(max(caps.values()), caps["absolute"])


if __name__ == "__main__":
    unittest.main()
