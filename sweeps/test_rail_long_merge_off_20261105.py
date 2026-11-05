"""RAIL-LONG v1/v2/v3: frozen ROAD1Y+RAIL OFF witnesses.

These contracts DO NOT rebaseline the 03/11 RAIL-only snapshots.  Composite
SHA transitions are pinned independently and feature edits remain fail-closed.
"""

import hashlib
import json
import unittest
from pathlib import Path

from rail_long_merged_off import MANIFEST, ROOT, _manifest, sha, platform_after_v3
from rail_long_source_off import off_source as v1_off
from rail_long_v2_off import off_source as v2_off
from rail_long_v3_off import off_source as v3_off


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class RailLongMergeContracts(unittest.TestCase):
    def test_immutable_historical_fixture_bytes(self):
        manifest = _manifest()
        for key, filename in (("v1", "rail_long_off_20261103.json"),
                              ("v2", "rail_long_v2_off_20261103.json"),
                              ("invest_stall_platform", "invest_stall_platform_off_20261104.json")):
            with self.subTest(name=key):
                self.assertEqual(
                    hashlib.sha256((ROOT / filename).read_bytes()).hexdigest(),
                    manifest["original_fixture_sha256"][key],
                )
        self.assertEqual(manifest["parents"]["master"],
                         "44d9313eab12e08685ac1bf0cc6254fe0257ba4d")

    def test_merged_v3_all_fourteen_sha_and_idempotence(self):
        manifest = _manifest()
        self.assertEqual(len(manifest["v3"]), 14)
        for name, witness in manifest["v3"].items():
            with self.subTest(name=name):
                live = source(name)
                self.assertEqual(sha(live), witness["on_sha256"])
                off = v3_off(name, live)
                self.assertEqual(sha(off), witness["off_sha256"])
                self.assertEqual(v3_off(name, off), off)

    def test_merged_v2_all_nine_sha_and_idempotence(self):
        manifest = _manifest()
        self.assertEqual(len(manifest["v2"]), 9)
        for name, witness in manifest["v2"].items():
            with self.subTest(name=name):
                live = source(name)
                self.assertEqual(sha(live), witness["on_sha256"])
                self.assertEqual(sha(v3_off(name, live)), witness["post_v3_sha256"])
                off = v2_off(name, live)
                self.assertEqual(sha(off), witness["off_sha256"])
                self.assertEqual(v2_off(name, off), off)
                self.assertEqual(v2_off(name, v3_off(name, live)), off)

    def test_merged_v1_all_three_sha_and_idempotence(self):
        manifest = _manifest()
        self.assertEqual(len(manifest["v1"]), 3)
        for name, witness in manifest["v1"].items():
            with self.subTest(name=name):
                live = source(name)
                self.assertEqual(sha(live), witness["on_sha256"])
                self.assertEqual(sha(v2_off(name, live)), witness["post_v2_sha256"])
                off = v1_off(name, live)
                self.assertEqual(sha(off), witness["off_sha256"])
                self.assertEqual(v1_off(name, off), off)
                self.assertEqual(v1_off(name, v2_off(name, live)), off)
                self.assertNotEqual(witness["off_sha256"],
                                    witness["historical_off_sha256"])

    def test_rejects_partial_v1_v2_v3_hunks_and_platform_corruption(self):
        cases = (
            (v1_off, "economy.nut", "  /* RAIL-LONG : le site 6/7"),
            (v2_off, "builder_rail.nut", "function OpexRailLongV2SiteLength("),
            (v3_off, "builder_rail.nut",
             "  local railLongLength = RAIL_LONG_V3 ? OpexRailLongV3SiteLength("),
            (v3_off, "main.nut", 'require("rail_long_v3.nut");'),
        )
        for projector, name, hunk in cases:
            with self.subTest(name=name, projector=projector.__module__):
                live = source(name)
                self.assertEqual(live.count(hunk), 1)
                with self.assertRaises(AssertionError):
                    projector(name, live.replace(hunk, "/* BROKEN */", 1))
                with self.assertRaises(AssertionError):
                    projector(name, live + hunk + "\n")
        # Cross-feature, v3-stripped task_rail platform hunk is not allowed
        # to bypass its independent pre/post SHA.
        name = "task_rail.nut"
        v3 = v3_off(name, source(name))
        self.assertEqual(sha(v3), _manifest()["platform_after_v3"][name]["on_sha256"])
        projected = platform_after_v3(name, v3)
        self.assertEqual(sha(projected),
                         _manifest()["platform_after_v3"][name]["off_sha256"])
        with self.assertRaises(AssertionError):
            platform_after_v3(name, v3.replace(
                "Une intention INVEST-STALL bloque", "Une intention BROKEN bloque", 1))

    def test_search_prio_after_v1_is_a_separate_exact_witness(self):
        from test_rail_search_prio_source_off import OFF_EDITS

        name = "task_rail.nut"
        off = v1_off(name, source(name))
        for active, prior, count in sorted(OFF_EDITS[name],
                                            key=lambda row: -len(row[0])):
            self.assertEqual(off.count(active), count)
            off = off.replace(active, prior)
        self.assertEqual(
            sha(off),
            _manifest()["v1"][name]["search_prio_after_v1_sha256"],
        )
        self.assertEqual(v1_off(name, off), off)


if __name__ == "__main__":
    unittest.main()
