"""SHA-reviewed merge views, without rewriting historical OPEN/SIBLING fixtures."""

# Compare historical contracts after the exact outer FLEET-ARB projection.
from fleet_arb_off import historical_read_text as fleet_read_text

import hashlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

import rail_open_legacy as rail_open
import rail_sibling_legacy as rail_sibling
from rail_pair_legacy import off_source as rail_pair_off


def _live(name):
    return fleet_read_text(ROOT / "ai" / "OpexAI" / name, encoding="utf-8")


class RailOpenSiblingMergeContracts(unittest.TestCase):
    def test_historical_fixture_files_remain_original(self):
        for module, filename in (
            (rail_open, "rail_open_off.json"),
            (rail_sibling, "rail_sibling_lot1_off.json"),
        ):
            with self.subTest(filename=filename):
                original = json.loads(
                    fleet_read_text(ROOT / "sweeps" / "fixtures" / filename, encoding="utf-8")
                )
                self.assertEqual(module.HISTORICAL_FIXTURE, original)
                self.assertEqual(set(module.FIXTURE["files"]), set(original["files"]))

    def test_live_sha_authorizes_only_reviewed_merge_inputs(self):
        for module in (rail_open, rail_sibling):
            for name, sha in module._MERGE_SHA.items():
                with self.subTest(policy=module.__name__, name=name):
                    self.assertEqual(hashlib.sha256(_live(name).encode("utf-8")).hexdigest(), sha)
                    self.assertIsNot(module.FIXTURE, module.HISTORICAL_FIXTURE)

    def test_rail_open_merge_keeps_repair_and_removes_all_open_branches(self):
        name = "builder_rail.nut"
        ready = rail_pair_off(name, _live(name))
        projected = rail_open.off_source(name, ready)
        for marker in ("railOpenCooldown", "railOpenSibling", "railOpenJoin", "railOpenFallback",
                       "RAIL_OPEN_SITE", "OpexRailOpenNewStationFunded"):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, projected)
        self.assertEqual(projected.count("OpexRailRepairJoinSite"), 3)
        self.assertEqual(rail_open.off_source(name, projected), projected)

    def test_sibling_merge_settings_project_idempotently_with_unrelated_prefix(self):
        for name, marker in (("globals_pre.nut", "RAIL_SIBLING <-"),
                             ("info.nut", 'name = "rail_sibling"')):
            with self.subTest(name=name):
                without_open = rail_open.off_source(name, _live(name))
                projected = rail_sibling.off_source(name, without_open)
                self.assertNotIn(marker, projected)
                self.assertEqual(rail_sibling.off_source(name, projected), projected)
                self.assertEqual(
                    rail_sibling.off_source(name, "/* unrelated */\n" + without_open),
                    "/* unrelated */\n" + projected,
                )

    def test_merge_context_mutations_fail_closed(self):
        for module, name in (
            (rail_open, "globals_pre.nut"),
            (rail_open, "info.nut"),
            (rail_sibling, "globals_pre.nut"),
            (rail_sibling, "info.nut"),
        ):
            with self.subTest(policy=module.__name__, name=name):
                source = _live(name)
                insertion = module.FIXTURE["files"][name][0]["new"]
                self.assertEqual(source.count(insertion), 1)
                damaged = source.replace(insertion, insertion.replace("\n", " /* mutated */\n", 1), 1)
                self.assertNotEqual(damaged, source)
                with self.assertRaises(AssertionError):
                    module.off_source(name, damaged)


if __name__ == "__main__":
    unittest.main()
