"""Review and guard the opt-in RAIL-OPEN historical OFF projection."""

# Compare historical contracts after the exact outer FLEET-ARB projection.
from fleet_arb_off import historical_read_text as fleet_read_text

import unittest
from pathlib import Path

from rail_open_legacy import FIXTURE, off_source, off_bytes
from rail_pair_legacy import off_source as rail_pair_off
from rail_long_source_off import off_source as rail_long_off

AI = Path(__file__).resolve().parents[1] / "ai/OpexAI"


class RailOpenOffProjectionContracts(unittest.TestCase):
    def test_all_reviewed_hunks_reconstruct_prior_bundle(self):
        self.assertEqual(set(FIXTURE["files"]), {
            "builder_rail.nut", "candidates.nut", "globals_pre.nut",
            "info.nut", "po01c_generators.nut", "settings.nut",
        })
        for name, edits in FIXTURE["files"].items():
            with self.subTest(name=name):
                live = rail_pair_off(name, fleet_read_text(AI / name, encoding="utf-8"))
                projected = off_source(name, live)
                self.assertEqual(projected, off_source(name, projected))
                self.assertEqual(off_bytes(name, live.encode("utf-8")), projected.encode("utf-8"))
                self.assertEqual(len(edits), sum(live.count(e["new"]) for e in edits))
                for edit in edits:
                    self.assertEqual(live.count(edit["new"]), 1)
                    self.assertNotIn(edit["new"], projected)
                self.assertNotIn("RAIL_OPEN", projected)

    def test_partial_changed_hunk_rejected(self):
        for name, edits in FIXTURE["files"].items():
            with self.subTest(name=name):
                live = rail_pair_off(name, fleet_read_text(AI / name, encoding="utf-8"))
                changed = edits[0]["new"].replace("\n", " /* mutated */\n", 1)
                with self.assertRaises(AssertionError):
                    off_source(name, live.replace(edits[0]["new"], changed, 1))

    def test_concurrent_consist_survives_off(self):
        for name in ("economy.nut", "globals_pre.nut", "info.nut", "settings.nut"):
            with self.subTest(name=name):
                live = fleet_read_text(AI / name, encoding="utf-8")
                projected = off_source(name, live)
                self.assertIn("RAIL_CONSIST", projected.upper())
        live = fleet_read_text(AI / "economy.nut", encoding="utf-8")
        # RAIL-OPEN's shared entry point projects the newer RAIL-LONG layer
        # first; the concurrent RAIL-CONSIST edits themselves must survive.
        self.assertEqual(off_source("economy.nut", live), rail_long_off("economy.nut", live))


if __name__ == "__main__":
    unittest.main()
