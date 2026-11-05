"""RAIL-DEPOT-SIGNAL strict ROAD+RAIL merge identities, no fixture rewrites."""

# Compare historical contracts after the exact outer FLEET-ARB projection.
from fleet_arb_off import historical_read_text as fleet_read_text

import hashlib
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from rail_depot_signal_legacy import (
    FIXTURE, _REVIEWED_MERGE_RDS_SHA, off_sha256, off_source,
)
from test_rail_search_prio_20261103 import off_config_bytes
from test_rail_search_prio_source_off import off_search_prio_source


def _sha(source):
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


class RailDepotSignalMergedProjection(unittest.TestCase):
    def test_frozen_historical_fixture_is_untouched(self):
        fixture = json.loads(fleet_read_text(ROOT / "sweeps" / "fixtures" / "rail_depot_signal_off.json", encoding="utf-8"))
        self.assertEqual(FIXTURE, fixture)
        self.assertEqual(set(FIXTURE["baseline_sha256"]), set(_REVIEWED_MERGE_RDS_SHA))

    def test_actual_merged_bytes_have_distinct_reviewed_sha(self):
        for name, approved in _REVIEWED_MERGE_RDS_SHA.items():
            current = fleet_read_text(ROOT / "ai" / "OpexAI" / name, encoding="utf-8")
            before = off_search_prio_source(name, current)
            if name in ("info.nut", "globals_pre.nut", "settings.nut"):
                before = off_config_bytes(name, before.encode("utf-8")).decode("utf-8")
            for label, source in (("live", current), ("legacy-pre", before)):
                with self.subTest(name=name, stage=label):
                    self.assertIn(_sha(source), approved)
                    expected_real_sha = approved[_sha(source)]
                    projected = off_source(name, source)
                    self.assertEqual(_sha(projected), expected_real_sha)
                    self.assertEqual(off_source(name, projected), projected)
                    # off_sha256 reports the frozen *historic witness*.  The
                    # true augmented merge digest is explicitly distinct.
                    self.assertEqual(off_sha256(name, source), FIXTURE["baseline_sha256"][name])
                    self.assertNotEqual(_sha(projected), off_sha256(name, source))

    def test_modified_merge_hunks_rejected_instead_of_rebaselining(self):
        mutations = {
            "info.nut": ('name = "rail_depot_signal"', 'name = "rail_depot_signal_modified"'),
            "globals_pre.nut": ("RAIL_DEPOT_SIGNAL <- false;", "RAIL_DEPOT_SIGNAL <- true;"),
            "settings.nut": ('GetSetting("rail_depot_signal")', 'GetSetting("rail_depot_signal_bad")'),
            "builder_rail.nut": ("RAIL_DEPOT_SIGNAL ? OpexRailDepotSignalBuildPrimary", "RAIL_DEPOT_SIGNAL ? OpexBrokenPrimary"),
            "task_rail.nut": ('"depotEndB2" in upgrade', '"depotEndB2_bad" in upgrade'),
            "main.nut": ('require("rail_depot_signal.nut");', 'require("broken_rail_depot_signal.nut");'),
        }
        for name, (before, after) in mutations.items():
            with self.subTest(name=name):
                source = fleet_read_text(ROOT / "ai" / "OpexAI" / name, encoding="utf-8")
                self.assertIn(before, source)
                damaged = source.replace(before, after, 1)
                self.assertNotEqual(source, damaged)
                with self.assertRaises(AssertionError):
                    off_source(name, damaged)


if __name__ == "__main__":
    unittest.main()
