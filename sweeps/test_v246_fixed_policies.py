"""V246 : retrait des paquets, sans couper les modes ni l'amorcage plat."""
from pathlib import Path
import re
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
PACKAGES = ("policy_rail", "policy_road", "policy_air", "policy_abandon", "policy_portfolio")
REMOVED = """
RAIL_DEVIS RAIL_SEARCH_RESUMABLE RAIL_MICRO_DEADLINE RAIL_SEGMENTED_SEARCH
RAIL_REFLEET DYNAMIC_PATHFINDER_CAP PAX_FULL_LOAD ORIGIN_SITABLE
ROAD_REFLEET ROAD_FLEET_FIX PRICING_ROAD_OPS ROAD_PAX_OVERLAP ROAD_PAX_VOIRIE
AIR_PORTFOLIO FLEET_PORTFOLIO AIR_CADENCE_CAP AIR_FLEET_LINE_PRICE AIR_ROI_ORDER
AIR_ABANDON AIR_MARGIN AIR_CHEAP_SITE AIR_JOINED_STOPS AIR_HUB AIR_HUB_FIX
ABANDON_MEMORY ABANDON_GEN_FILTER ABANDON_MEMORY_TRANSIENT_GUARD
ECONOMY_FIX CLEAN_DENSITY_SCORE VIVIER_RATIO_FILTER COMPLEX_CARGO
CAPITAL_CALIBRATION DYNAMIC_CASH_RESERVE C53_ORDER_NONSTOP EVENT_CATALOG_INVALIDATE
""".split()


def read(name):
    return (AI / name).read_text(encoding="utf-8")


class FixedPolicies(unittest.TestCase):
    def test_exactly_five_public_settings_retired(self):
        info, settings = read("info.nut"), read("settings.nut")
        self.assertLessEqual(info.count("AddSetting("), 86)  # V263b : 81 moins 11 retraits approuves le 20/10 ; +1 V275, +1 V269 (fusions du 20/10) ; +1 V276, +1 V284 (branche v287) ; +1 V284 (fusion du 20/10) ; +2 V294, +1 V294h, +5 V294c/d/f/i/j, +1 V295, +1 V294c adaptatif ; +1 V294g.
        for name in PACKAGES:
            with self.subTest(name=name):
                self.assertNotIn(f'name = "{name}"', info)
                self.assertNotIn(f'GetSetting("{name}")', settings)
        for local in ("polRail", "polRoad", "polAir", "polAbandon", "polPort"):
            self.assertNotIn(local, settings)

    def test_no_removed_global_read_or_write_remains(self):
        # A missed read compiles but crashes at runtime in Squirrel. Exclude
        # comments and log tags, and include the pathfinder subdirectory.
        noncode = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"', re.S)
        for path in AI.rglob("*.nut"):
            tokens = set(re.findall(r"\b\w+\b", noncode.sub("", path.read_text(encoding="utf-8"))))
            with self.subTest(file=path.name):
                self.assertFalse(tokens.intersection(REMOVED), tokens.intersection(REMOVED))

    def test_road_alias_and_all_mode_switches_remain(self):
        settings = read("settings.nut")
        self.assertIn("ROAD_BUILD_ENABLED <- true;", read("globals_pre.nut"))
        self.assertIn("ROAD_BUILD_ENABLED = MODE_ROAD;", settings)
        for mode in ("air", "rail", "road", "water"):
            self.assertIn(f'name = "mode_{mode}"', read("info.nut"))
            self.assertIn(f'MODE_{mode.upper()} = AIController.GetSetting("mode_{mode}") != 0;', settings)

    def test_mutable_bootstrap_preserves_flat_override(self):
        settings = read("settings.nut")
        self.assertIn("STAGED_BOOTSTRAP <- true;", read("globals_pre.nut"))
        self.assertEqual(settings.count("STAGED_BOOTSTRAP = true;"), 1)
        self.assertEqual(settings.count("STAGED_BOOTSTRAP = false;"), 1)
        self.assertLess(settings.index("STAGED_BOOTSTRAP = true;"), settings.index("STAGED_BOOTSTRAP = false;"))
        self.assertIn("if (!STAGED_BOOTSTRAP) this._generationStage = OPEX_STAGE_COMPLETE;", read("main.nut"))

    def test_blocking_executors_removed_and_resumable_upgrade_kept(self):
        self.assertNotIn("function _tryBuildAir(year);", read("main.nut"))
        self.assertNotIn("function OpexAI::_tryBuildAir(", read("task_air.nut"))
        self.assertNotIn("this._tryBuildAir(year)", read("scheduler_tasks.nut"))
        self.assertNotIn("OpexUpgradeRailLineToDoubleTrack", read("builder_rail.nut"))
        self.assertIn("this._startRailUpgradeSearch(line, prep);", read("task_rail.nut"))
        self.assertIn("OpexExecuteUpgradeAfterSearch", read("task_rail.nut"))

    def test_nonstop_and_full_load_orders_are_permanent(self):
        rail = read("builder_rail.nut")
        self.assertIn("local flagsA = AIOrder.OF_FULL_LOAD_ANY | nonstopFlag;", rail)
        self.assertIn('local flagsB = ((kind == "freight") ? AIOrder.OF_NONE : AIOrder.OF_FULL_LOAD_ANY) | nonstopFlag;', rail)
        for name in ("builder_rail.nut", "builder_road.nut"):
            self.assertIn("local nonstopFlag = AIOrder.OF_NON_STOP_INTERMEDIATE;", read(name))
