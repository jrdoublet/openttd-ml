"""Pin reviewed V233L constructibility guards across origin/master and merge.

The historical V233L fixture retains its original SHA identities.  This test
proves that the ROAD1Y+RAIL merge yields the same V233L-OFF bytes as the frozen
origin/master baseline for three files whose later V233L guards changed.
"""

# Compare historical contracts after the exact outer FLEET-ARB projection.
from fleet_arb_off import historical_read_text as fleet_read_text

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from road100_off_projection import off_source as road_off
from test_rail_search_prio_20261103 import off_config_bytes
from v233_long_good_legacy import off_source as v233_off


MANIFEST = json.loads(
    fleet_read_text(ROOT / "sweeps/fixtures/v233_long_good_merge_sha_20261105.json", encoding="utf-8")
)
EXPECTED = {
    "economy.nut": "a5e75086c455d9b6102a5fc8f2aa0a1210e0b6ec8968314eda191c174e71262c",
    "globals_pre.nut": "320007389a5997fc5d8c52ba06b40966d98644844b27703fd47adb96988df0a0",
    "settings.nut": "f8359098b70e994d4dcafcf037c0c06bfec9c3eccdb323d79fdb14ceae7e7f2f",
}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def merge_source(name):
    return fleet_read_text(ROOT / "ai/OpexAI" / name, encoding="utf-8")


def merged_off(name, text):
    if name in ("globals_pre.nut", "settings.nut"):
        text = off_config_bytes(name, text.encode("utf-8")).decode("utf-8")
    return v233_off(name, road_off(name, text))


class V233MergedConstructibilityGuards(unittest.TestCase):
    def test_merge_outputs_equal_frozen_master_projection(self):
        self.assertEqual(
            sha(fleet_read_text(ROOT / "sweeps/fixtures/v233_long_good_off.json", encoding="utf-8")),
            MANIFEST["historical_v233_fixture_sha256"],
        )
        for name, expected_sha in EXPECTED.items():
            with self.subTest(name=name):
                current = merged_off(name, merge_source(name))
                old = subprocess.check_output(
                    ["git", "show", f"{MANIFEST['origin_master_commit']}:ai/OpexAI/{name}"],
                    cwd=ROOT,
                ).decode("utf-8")
                baseline = v233_off(name, road_off(name, old))
                self.assertEqual(sha(current), expected_sha)
                self.assertEqual(sha(baseline), expected_sha)
                self.assertEqual(current, baseline)
                self.assertNotIn("monoLong", current)
                self.assertNotIn("V233L_CONSTRUCT", current)

    def test_changed_constructibility_guards_fail_closed(self):
        variants = {
            "economy.nut": ("v233Single = false", "v233Single = true"),
            "globals_pre.nut": ("V233L_CONSTRUCT <- 0;", "V233L_CONSTRUCT <- 2;"),
            "settings.nut": (
                'AIController.GetSetting("v233l_constructibilite")',
                'AIController.GetSetting("v233l_constructibilite_changed")',
            ),
        }
        for name, (before, after) in variants.items():
            with self.subTest(name=name):
                source = merge_source(name)
                self.assertEqual(source.count(before), 1)
                with self.assertRaises(AssertionError):
                    merged_off(name, source.replace(before, after, 1))


if __name__ == "__main__":
    unittest.main()
