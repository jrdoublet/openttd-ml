"""Pin reviewed V233L constructibility guards across origin/master and merge.

The historical V233L fixture retains its original SHA identities.  This test
proves that the ROAD1Y+RAIL merge yields the same V233L-OFF bytes as the frozen
origin/master baseline for three files whose later V233L guards changed.
"""

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
    (ROOT / "sweeps/fixtures/v233_long_good_merge_sha_20261105.json")
    .read_text(encoding="utf-8")
)
EXPECTED = {
    "economy.nut": "a5e75086c455d9b6102a5fc8f2aa0a1210e0b6ec8968314eda191c174e71262c",
    "globals_pre.nut": "320007389a5997fc5d8c52ba06b40966d98644844b27703fd47adb96988df0a0",
    "settings.nut": "f8359098b70e994d4dcafcf037c0c06bfec9c3eccdb323d79fdb14ceae7e7f2f",
}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def merge_source(name):
    return (ROOT / "ai/OpexAI" / name).read_text(encoding="utf-8")


OVERNIGHT_GLOBALS = (
    "FAIR_PLAY_COURTESY <- false; // Mode courtoisie pour parties normales/humaines (defaut OFF).\n"
    "EB10_GUARDS <- false; // EB-10 : garde sentinelle 65535 industrie et acceptation express urbaine >= 8 (defaut OFF).\n"
    "AIR_COVERAGE_STOP <- 0; // AIR-COVERAGE-STOP : mise en veille du scan de villes/sites aeroport apres epuisement (defaut 0).\n"
    "AIR_COVERAGE_EXHAUSTED <- false;\n"
    "AIR_NEW_TOWN_QUEUE <- [];\n"
    "IDLE1_SLACK_WORKER <- 1; // OPCODES/IDLE-1 : valorisation du reliquat de tick pour travail de fond (defaut 1 depuis le 08/11).\n"
    "IDLE1_SLACK_RESERVE <- 2500; // Marge de securite anti-franchissement de tick.\n"
    "IDLE1_TOWN_CURSOR <- 0;\n"
    "PO02_INDEPENDENT_EXPIRY <- 0; // PO-02 : echeance de publication propre a chaque vivier modal (defaut 0).\n"
    "PO02_LAST_PUBLISH_DATE <- { air = 0, rail = 0, road = 0, water = 0, fleet = 0 };\n"
    "EB4_AIR_ROAD_ARBITRAGE <- 0; // EB-4 : arbitrage de caisse 1970-1972 entre air et route (defaut 0).\n"
    "EB7_DETAILED_ACCOUNTING <- 1; // EB-7 : comptabilite fine et passive des depenses reelles AIR/ROUTE (defaut 1 depuis le 08/11).\n"
    "EB7_LEDGER <- { capexRoad = 0, capexAir = 0, vehBuyAir = 0, lastCash = 0, lastLoan = 0 };\n"
    "LATE_GAME_POLICY <- 0; // LATE-GAME-1 : reinvestissement de l'excedent de tresorerie tardif (defaut 0).\n"
    "MULTI1_RELANCE <- 0; // MULTI-1 : conditions de relance du multimodal tardif (0=off, 1=shadow, 2=on).\n"
    "MULTI1_LAST_BUILD_DATE <- 0;\n"
    "MULTI1_ACTIVE_PORTFOLIO <- null;\n"
)
OVERNIGHT_SETTINGS = (
    '  FAIR_PLAY_COURTESY = AIController.GetSetting("fair_play_courtesy") == 1;\n'
    '  if (FAIR_PLAY_COURTESY) OPEX_LEVEL_LIMITS = true;\n'
    '  EB10_GUARDS = AIController.GetSetting("eb10_guards") == 1;\n'
    '  AIR_COVERAGE_STOP = AIController.GetSetting("air_coverage_stop") == 1 ? 1 : 0;\n'
    '  IDLE1_SLACK_WORKER = AIController.GetSetting("idle1_slack_worker") == 1 ? 1 : 0;\n'
    '  PO02_INDEPENDENT_EXPIRY = AIController.GetSetting("po02_independent_expiry") == 1 ? 1 : 0;\n'
    '  EB4_AIR_ROAD_ARBITRAGE = AIController.GetSetting("eb4_air_road_arbitrage") == 1 ? 1 : 0;\n'
    '  EB7_DETAILED_ACCOUNTING = AIController.GetSetting("eb7_detailed_accounting") == 1 ? 1 : 0;\n'
    '  LATE_GAME_POLICY = AIController.GetSetting("late_game_policy");\n'
    '  MULTI1_RELANCE = AIController.GetSetting("multi1_relance");\n'
)
OVERNIGHT_SETTINGS_DISTRICT = '  FAIR_PLAY_COURTESY = AIController.GetSetting("fair_play_courtesy") == 1;\n'


def merged_off(name, text):
    if name == "globals_pre.nut" and OVERNIGHT_GLOBALS in text:
        text = text.replace(OVERNIGHT_GLOBALS, "")
    elif name == "settings.nut":
        if OVERNIGHT_SETTINGS in text:
            text = text.replace(OVERNIGHT_SETTINGS, "")
        if OVERNIGHT_SETTINGS_DISTRICT in text:
            text = text.replace(OVERNIGHT_SETTINGS_DISTRICT, "")
    if name in ("globals_pre.nut", "settings.nut"):
        text = off_config_bytes(name, text.encode("utf-8")).decode("utf-8")
    return v233_off(name, road_off(name, text))


class V233MergedConstructibilityGuards(unittest.TestCase):
    def test_merge_outputs_equal_frozen_master_projection(self):
        self.assertEqual(
            sha((ROOT / "sweeps/fixtures/v233_long_good_off.json").read_text(encoding="utf-8")),
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
