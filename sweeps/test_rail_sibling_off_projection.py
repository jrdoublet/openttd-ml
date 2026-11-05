"""The reviewed RAIL-SIBLING additions must disappear from historical OFF bytes."""

# Compare historical contracts after the exact outer FLEET-ARB projection.
from fleet_arb_off import historical_read_text as fleet_read_text

import unittest
from pathlib import Path

from estim_unifie_legacy import estim_off
from rail_sibling_legacy import FIXTURE, off_source, off_bytes
from rail_open_legacy import off_source as rail_open_off


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class RailSiblingOffProjectionContracts(unittest.TestCase):
    def test_fixture_matches_all_seven_reviewed_sources(self):
        self.assertEqual({name: len(edits) for name, edits in FIXTURE["files"].items()}, {
            "builder_rail.nut": 1,
            "candidates.nut": 4,
            "economy.nut": 1,
            "globals_pre.nut": 1,
            "info.nut": 1,
            "po01c_generators.nut": 3,
            "settings.nut": 1,
        })
        for name, edits in FIXTURE["files"].items():
            with self.subTest(name=name):
                live = rail_open_off(name, fleet_read_text(AI / name, encoding="utf-8"))
                projected = off_source(name, live)
                self.assertEqual(projected, off_source(name, projected))
                self.assertEqual(off_bytes(name, live.encode("utf-8")), projected.encode("utf-8"))
                self.assertEqual(off_source(name, "/* unrelated */\n" + live),
                                 "/* unrelated */\n" + projected)
                for edit in edits:
                    self.assertEqual(live.count(edit["new"]), 1)
                    self.assertNotIn(edit["new"], projected)

    def test_a_modified_guard_fails_instead_of_rebasing_history(self):
        for name, edits in FIXTURE["files"].items():
            with self.subTest(name=name):
                live = rail_open_off(name, fleet_read_text(AI / name, encoding="utf-8"))
                guarded = edits[0]["new"]
                damaged = guarded.replace("\n", " /* changed */\n", 1)
                self.assertNotEqual(guarded, damaged)
                with self.assertRaises(AssertionError):
                    off_source(name, live.replace(guarded, damaged, 1))

    def test_estim_projection_keeps_sibling_additions_intact(self):
        live = rail_open_off("candidates.nut", fleet_read_text(AI / "candidates.nut", encoding="utf-8"))
        projected = estim_off("candidates.nut", live)
        for edit in FIXTURE["files"]["candidates.nut"]:
            self.assertIn(edit["new"], projected)
        self.assertEqual(estim_off("candidates.nut", projected), projected)


if __name__ == "__main__":
    unittest.main()
