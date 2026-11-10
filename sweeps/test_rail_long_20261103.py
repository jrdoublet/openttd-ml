"""RAIL-LONG: strict OFF configuration and frozen historical inventory contracts.

The physical/economic rail builder is owned by worker-4. This test module owns
the public setting, its default, and exact byte subtraction for frozen sources.
No OpenTTD, Docker, or WSL process is needed.
"""

import hashlib
import json
import re
import unittest
from pathlib import Path

from n75_mc_legacy import historical_info, rail_long_config_off_bytes
from test_rail_search_prio_20261103 import off_config_bytes as search_prio_off
from rail_long_v2_off import off_source as rail_long_v2_off


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
FIXTURE = json.loads(
    (ROOT / "sweeps" / "fixtures" / "rail_long_off_20261103.json")
    .read_text(encoding="utf-8")
)

# Fusion des sources ROAD1Y de origin/master avec RAIL-LONG : les 3 sources
# projetees conservent volontairement les reglages ROAD1Y. Les empreintes
# historiques de la fixture RAIL-only restent inchangees et verifiees dans
# son chemin historique. Ce second jeu est specifique au bundle fusionne.
MERGED_PRE_INTERVENTION_SHA256 = {
    "globals_pre.nut": "0b7669152183e290256c892350352ce757ef1fc071f71d28990a11c865be6d90",
    "settings.nut": "fcd831d53d86f98d42c5007a9a97b3c8b1066b9677015e067456124fcb635764",
    "info.nut": "746d6afe204f2e91047dda8915de51055bb21b101fe42435abefe4a3156cd596",
}


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def function_body(name, symbol):
    text = source(name)
    start = text.index("function " + symbol + "(")
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start:pos + 1]
    raise AssertionError(f"Unterminated {name}:{symbol}")


class RailLongConfigContracts(unittest.TestCase):
    def test_boolean_global_defaults_to_false_once(self):
        globals_pre = source("globals_pre.nut")
        self.assertEqual(
            len(re.findall(r"(?m)^RAIL_LONG\s*<-\s*false;", globals_pre)), 1
        )
        self.assertNotRegex(globals_pre, r"(?m)^RAIL_LONG\s*<-\s*true;")

    def test_setting_declared_once_with_zero_for_four_difficulties(self):
        info = source("info.nut")
        blocks = re.findall(r"AddSetting\s*\(\s*\{.*?\}\s*\);", info, flags=re.S)
        declared = [block for block in blocks if 'name = "rail_long"' in block]
        self.assertEqual(len(declared), 1)
        block = declared[0]
        self.assertRegex(block, r"\bmin_value\s*=\s*0\b")
        self.assertRegex(block, r"\bmax_value\s*=\s*3\b")
        self.assertIn("flags = 0", block)
        for difficulty in ("easy", "medium", "hard", "custom"):
            with self.subTest(difficulty=difficulty):
                self.assertRegex(block, rf"\b{difficulty}_value\s*=\s*0\b")

    def test_setting_loaded_once_and_boolean(self):
        settings = source("settings.nut")
        getter = 'AIController.GetSetting("rail_long")'
        self.assertEqual(settings.count(getter), 1)
        self.assertIn("local railLongMode = " + getter + ";", settings)
        self.assertIn("RAIL_LONG = railLongMode == 1;", settings)
        self.assertIn("RAIL_LONG_V2 = railLongMode == 2;", settings)
        self.assertEqual(
            sum(path.read_text(encoding="utf-8").count(getter)
                for path in AI.glob("*.nut")), 1
        )

    def test_exact_off_fixture_matches_three_preintervention_hashes(self):
        self.assertEqual(set(FIXTURE["baseline_sha256"]),
                         {"info.nut", "globals_pre.nut", "settings.nut"})
        self.assertEqual(set(FIXTURE["baseline_sha256"]), set(FIXTURE["insertions"]))
        for name, expected in FIXTURE["baseline_sha256"].items():
            with self.subTest(name=name):
                # La fixture v1 est gelée ; soustraire d'abord uniquement v2.
                live = (AI / name).read_bytes()
                current = rail_long_v2_off(name, live.decode("utf-8")).encode("utf-8")
                self.assertEqual(len(FIXTURE["insertions"][name]), 1)
                fragment = FIXTURE["insertions"][name][0].encode("utf-8")
                self.assertEqual(current.count(fragment), 1)
                projected = rail_long_config_off_bytes(name, live)
                self.assertNotEqual(projected, current)
                # Le merge preserve les nouveaux blocs ROAD1Y; on ne
                # compare donc pas ces sources compositees a l'ancien SHA
                # RAIL-only, qui reste gele dans la fixture historique.
                is_merged = 'name = "road1y_load_orders"' in source("info.nut")
                merged_expected = MERGED_PRE_INTERVENTION_SHA256[name]
                self.assertEqual(hashlib.sha256(projected).hexdigest(),
                                 merged_expected if is_merged else expected)
                self.assertEqual(rail_long_config_off_bytes(name, projected), projected)
                self.assertNotIn(b'RAIL_LONG <- false;', projected)
                self.assertNotIn(b'AIController.GetSetting("rail_long")', projected)
                self.assertNotIn(b'name = "rail_long"', projected)

    def test_modified_or_duplicated_opt_in_bytes_fail_closed(self):
        changed = {
            "info.nut": ('name = "rail_long"', 'name = "rail_long_broken"'),
            "settings.nut": ('RAIL_LONG = AIController.GetSetting("rail_long") == 1;',
                             'RAIL_LONG = AIController.GetSetting("rail_long") != 0;'),
            "globals_pre.nut": ('RAIL_LONG <- false;', 'RAIL_LONG <- true;'),
        }
        for name, (before, after) in changed.items():
            with self.subTest(name=name):
                raw = rail_long_v2_off(name, source(name)).encode("utf-8")
                fragment = FIXTURE["insertions"][name][0].encode("utf-8")
                with self.assertRaises(AssertionError):
                    rail_long_config_off_bytes(name, raw + fragment)
                self.assertEqual(raw.count(before.encode("utf-8")), 1)
                damaged = raw.replace(before.encode("utf-8"), after.encode("utf-8"), 1)
                with self.assertRaises(AssertionError):
                    rail_long_config_off_bytes(name, damaged)

    def test_inventory_91_live_90_without_long_89_without_prio_58_historical(self):
        live = (AI / "info.nut").read_bytes()
        long_off = rail_long_config_off_bytes("info.nut", live)
        both_off = search_prio_off("info.nut", live)
        # INVEST-STALL vaut 0 et son bloc est retiré des projections ci-dessous.
        # Fusion ROAD1Y + RAIL : 146 reglages sur master, 96 sur RAIL,
        # 157 dans l'union. Les projecteurs retires les 6 puis 7 reglages
        # du volet rail sans effacer les 61 ajouts propres a ROAD1Y.
        self.assertEqual(live.count(b"AddSetting("), 166)
        self.assertEqual(long_off.count(b"AddSetting("), 160)
        self.assertEqual(both_off.count(b"AddSetting("), 159)
        # Le master ROAD1Y/SIBLING/OPEN de 44d9313e conserve deja 68
        # AddSetting dans sa projection historique, contre 58 dans l'ancien
        # bundle RAIL-only. Cette valeur est verifiee contre origin/master.
        self.assertEqual(historical_info(live.decode("utf-8")).count("AddSetting("), 68)


class RailLongBehaviorContracts(unittest.TestCase):
    """Pin RAIL-LONG intent and the existing physical/fleet safety chain."""

    def test_high_production_only_freight_and_short_capacity_snapshot(self):
        choose = function_body("builder_rail.nut", "OpexRailLongSiteLength")
        self.assertIn('if (!RAIL_LONG || candidate.kind != "freight"', choose)
        self.assertIn("OpexV233LIs(candidate)", choose)
        self.assertIn('!("perTrain" in candidate) || candidate.perTrain <= 0', choose)
        self.assertIn('!("monthly" in candidate) || candidate.monthly <= 0', choose)
        self.assertIn('if (!("railLongShortCapacity" in candidate))', choose)
        self.assertIn("candidate.railLongShortCapacity <- candidate.perTrain;", choose)
        self.assertIn(
            "candidate.monthly.tofloat() < 1.5 * candidate.railLongShortCapacity",
            choose,
        )
        self.assertLess(
            choose.index("candidate.railLongShortCapacity <- candidate.perTrain;"),
            choose.index("1.5 * candidate.railLongShortCapacity"),
        )

    def test_target_is_six_or_seven_only_when_physically_possible(self):
        choose = function_body("builder_rail.nut", "OpexRailLongSiteLength")
        self.assertIn("local limit = catalog.platformLength;", choose)
        self.assertIn("catalog.maxTrainLength > 0 && catalog.maxTrainLength < limit", choose)
        self.assertIn("if (limit < 6) return 0;", choose)
        self.assertIn("if (candidate.platformLength >= 6) return 0;", choose)
        self.assertIn("local upper = limit < 7 ? 6 : 7;", choose)
        self.assertIn("for (local length = upper; length >= 6; length--)", choose)
        self.assertIn("candidate.monthly.tofloat() * 3.0 >= trainCapacity", choose)

    def test_both_stations_tested_at_equal_length_and_failed_long_falls_back(self):
        # V1 garde exactement ce corps quand on retire la couche v2.
        v1 = rail_long_v2_off("builder_rail.nut", source("builder_rail.nut"))
        site = v1[v1.index("function OpexRailPlatformPlans("):v1.index("function OpexRailAstarWeight(")]
        probe = function_body("builder_rail.nut", "OpexRailTryPlatformLength")
        self.assertIn(
            "OpexStationPlans(candidate.src, candidate.dst, STATION_SEARCH_RADIUS, length,",
            probe,
        )
        self.assertIn(
            "OpexStationPlans(candidate.dst, candidate.src, STATION_SEARCH_RADIUS, length,",
            probe,
        )
        self.assertIn("local railLongLength = OpexRailLongSiteLength(catalog, candidate);", site)
        self.assertIn('!("joinPlatform" in candidate) || candidate.joinPlatform == null', site)
        self.assertIn("for (local length = railLongLength; length >= 6; length--)", site)
        self.assertIn("OpexRailTryPlatformLength(catalog, candidate, length, statsA, statsB)", site)
        self.assertIn("if (longer.ok)", site)
        self.assertIn("quote != null && quote.profitAnnual > 0 && quote.roi > 0", site)
        self.assertIn('OpexDecide("RAIL_LONG", "event=fallback', site)
        self.assertIn("for (local length = wanted; length >= floor; length--)", site)
        self.assertLess(
            site.index("for (local length = railLongLength; length >= 6; length--)"),
            site.index("for (local length = wanted; length >= floor; length--)"),
        )

    def test_actual_site_length_requotes_and_bounds_consist(self):
        route = function_body("builder_rail.nut", "OpexPrepareRailRoute")
        econ = function_body("economy.nut", "OpexLineEconomics")
        self.assertIn("local platformPlans = OpexRailPlatformPlans(catalog, candidate);", route)
        self.assertIn("plan.length = platformPlans.length;", route)
        self.assertIn("candidate.monthly, candidate.kind, plan.length,", route)
        self.assertIn("OpexApplyRailEconomics(candidate, economics);", route)
        self.assertIn("OpexRailNominalMaxWagons(fixedPlatformLength)", econ)
        self.assertIn('RAIL_LONG && kind == "freight"', econ)
        self.assertIn("OpexRailNominalMaxWagons(catalog.maxTrainLength)", econ)
        self.assertIn("if (correctedWagons > maxWagons) correctedWagons = maxWagons;", econ)

    def test_vehicle_length_verified_and_future_trains_use_same_consist(self):
        build = function_body("builder_rail.nut", "OpexBuildTrains")
        second = function_body("builder_rail.nut", "OpexBuildSecondTrain")
        task = function_body("task_rail.nut", "OpexAI::_expandRailLines")
        for required in (
            "OpexRailNominalMaxWagons(platformLength)",
            "local trainLengthLimit = platformLength * 16;",
            "AIVehicle.GetLength(train)",
            "AIVehicle.GetLength(car)",
            "if (trainLength + carLength > trainLengthLimit)",
            'failed = true, failure = "LENGTH"',
            "AIVehicle.MoveWagon(car, 0, train, 0)",
        ):
            self.assertIn(required, build)
        self.assertIn("OpexBuildTrains(catalog, line.cargo, line.kind, line.depot2,", second)
        self.assertIn("line.loco, line.wagons, line.platformLength, true,", second)
        self.assertIn("if (newTrains.failed || newTrains.built == 0)", second)
        self.assertIn("OpexRollback(null, null, null, null, newTrains.rollbackVehicles);", second)
        self.assertIn("if (money >= need)", task)
        self.assertIn('if (("v190Independent" in line) && line.v190Independent) continue;', task)


if __name__ == "__main__":
    unittest.main()
