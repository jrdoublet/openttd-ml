"""Contrats de non-régression des corrections R01 à R12 (24 octobre 2026)."""

import re
import unittest
from pathlib import Path


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def function_body(filename, name):
    source = (AI / filename).read_text(encoding="utf-8")
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : i]
    raise AssertionError("Unclosed function: " + name)


class ReviewCodeCorrections(unittest.TestCase):
    def test_r01_profiled_loop_projects_before_c117(self):
        normal = function_body("main.nut", "OpexAI::Start")
        profiled = function_body("probes.nut", "OpexAI::_mainLoopProfiled")
        for body in (normal, profiled):
            events = body.index("this._processEvents();")
            projection = body.index("this._refreshSaveProjection();")
            throughput = body.index("OpexC117AirThroughputStep(")
            self.assertLess(events, projection)
            self.assertLess(projection, throughput)
            self.assertIn("this._lines.len() >= SAVE_PROJECTION_MIN_LINES", body)
            self.assertIn("this._saveProjection = null;", body)
            self.assertIn('OpexSpanBegin("loop.save_projection")', body)
        self.assertIn('OpexLoopProfAdd("save_projection", mark);', profiled)

    def test_r02_cargo_cache_rebuilds_on_industry_refresh_and_new_month(self):
        order = function_body("candidates_v276.nut", "OpexV276CargoOrder")
        industries = function_body("catalog.nut", "OpexCatalog::_refreshIndustries")
        settings = (AI / "settings.nut").read_text(encoding="utf-8")
        self.assertIn("V276_CARGO_ORDER = null;", industries)
        self.assertIn("V276_CARGO_MONTH <- -1;", (AI / "candidates_v276.nut").read_text(encoding="utf-8"))
        self.assertIn("V276_CARGO_MONTH = -1;", settings)
        self.assertIn("V276_CARGO_YEAR == year", order)
        self.assertIn("V276_CARGO_MONTH == month", order)
        self.assertIn("V276_CARGO_MONTH = month;", order)
        self.assertIn("V276_CAND_SLICES != 2", order)

    def test_r03_null_projection_rebuilds_during_same_month(self):
        refresh = function_body("persist.nut", "OpexAI::_refreshSaveProjection")
        self.assertIn("month == this._saveProjectionMonth && this._saveProjection != null", refresh)
        self.assertIn("this._saveProjection = cache;", refresh)
        self.assertIn("OpexSaveProjectLine(line)", refresh)

    def test_r04_c83_drops_departed_towns_and_closes_observations(self):
        watch = function_body("task_projects.nut", "OpexAI::_c83WatchAirSlotTransitions")
        self.assertIn("local watchedIds = {};", watch)
        self.assertIn("watchedIds.rawset(town.id, true);", watch)
        self.assertIn("if (!(townId in watchedIds))", watch)
        self.assertIn('OpexC122ThreatCancel(townId, "left_top_k");', watch)
        self.assertIn("delete this._c83SlotWatch[townId];", watch)

    def test_r05_v276_pairs_bounded_before_final_sort(self):
        enumeration = function_body("candidates_v276.nut", "OpexV276Enumerate")
        self.assertIn("s.pairs.KeepTop(V276_EVAL_CAP);", enumeration)
        self.assertIn("s.pairs.Count() >= V276_EVAL_CAP * 2", enumeration)
        self.assertLess(enumeration.index("s.pairs.KeepTop(V276_EVAL_CAP);"),
                        enumeration.rindex("s.pairs.AddItem("))
        self.assertEqual(enumeration.count("s.pairs.Sort(AIList.SORT_BY_VALUE, false);"), 2)

    def test_r06_probe_setting_explains_v309_log_dependency(self):
        info = (AI / "info.nut").read_text(encoding="utf-8")
        probe = info[info.index('name = "probes"'):info.index('name = "save_full_state"')]
        self.assertIn("67108864 V309", probe)
        self.assertIn("67109120", probe)

    def test_r07_dead_compatibility_switches_eliminated(self):
        for path in AI.glob("*.nut"):
            with self.subTest(path=path.name):
                data = path.read_text(encoding="utf-8")
                self.assertFalse("OPEX_ECONOMY_OPCODE_COMPAT_FALSE" in data, path.name)
                self.assertFalse("WATER_OPCODE_COMPAT_FALSE" in data, path.name)

    def test_r08_dead_po01c_cargo_loader_removed(self):
        self.assertFalse("function OpexPO01CCargos(" in (AI / "po01c_generators.nut").read_text(encoding="utf-8"))

    def test_r09_three_unused_helpers_removed(self):
        for file, name in (("air_towns.nut", "OpexAirV95CompetitorSecondSlotOpen"),
                           ("builder_road.nut", "OpexRoadTryJoinStop"),
                           ("task_rail.nut", "OpexV131KeepStructures")):
            with self.subTest(name=name):
                self.assertFalse("function " + name + "(" in (AI / file).read_text(encoding="utf-8"))

    def test_r10_four_unused_declarations_removed(self):
        source = (AI / "main.nut").read_text(encoding="utf-8")
        for name in ("RAIL_EXPAND_STREAK", "RAIL_EXPAND_UTIL_PERMILLE", "CASH_RESERVE_STATIC",
                     "function _logC48IncrementalLedger"):
            self.assertFalse(name in source, name)

    def test_r11_one_native_bridge_sort_implementation_for_nine_call_sites(self):
        builder = (AI / "builder_rail.nut").read_text(encoding="utf-8")
        helper = function_body("builder_rail.nut", "OpexBridgeSortBySpeed")
        self.assertIn("bridges.Valuate(AIBridge.GetMaxSpeed);", helper)
        self.assertIn("bridges.Sort(AIList.SORT_BY_VALUE, false);", helper)
        source = "\n".join((AI / f).read_text(encoding="utf-8")
                           for f in ("builder_rail.nut", "task_rail.nut", "task_v259.nut"))
        self.assertEqual(source.count("bridges.Valuate(AIBridge.GetMaxSpeed);"), 1)
        self.assertEqual(source.count("bridges.Sort(AIList.SORT_BY_VALUE, false);"), 1)
        self.assertEqual(source.count("OpexBridgeSortBySpeed(bridges);"), 9)

    def test_r12_max_railtype_rule_shared_while_po01c_preserves_yield(self):
        helper = function_body("catalog.nut", "OpexRailTypePreferred")
        self.assertIn("candidate > chosen", helper)
        for name, file in (("OpexPO01CRail", "po01c_generators.nut"),
                           ("OpexV307RailType", "probe_v307.nut")):
            body = function_body(file, name)
            self.assertIn("if (OpexRailTypePreferred(t, chosen)) chosen = t;", body)
        self.assertIn("yield null; // PO01C_CHECKPOINT", function_body("po01c_generators.nut", "OpexPO01CRail"))
        self.assertIn("types.Sort(AIList.SORT_BY_ITEM, AIList.SORT_DESCENDING)",
                      function_body("catalog.nut", "OpexCatalog::_refreshRail"))


if __name__ == "__main__":
    unittest.main()
