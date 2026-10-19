"""Contracts for the disabled V274 dual-endpoint reinforcement gate.

These checks do not compile Squirrel or establish economic benefit.
"""
from pathlib import Path
import re
import unittest

from test_v248_mechanism_fixtures_static import strip_code


AI = Path(__file__).resolve().parents[1] / "ai/OpexAI"


class GrowthStockTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        fleet = cls.sources["air_fleet.nut"]
        cls.helper = fleet.split("function OpexV274AirGrowthStock(line, phase, lines, routesIndex = null)", 1)[1].split("\nfunction ", 1)[0]

    def test_setting_and_single_read(self):
        block = re.search(r'name = "v274_air_growth_stock",(.*?)\}\);', self.sources["info.nut"], re.S)[1]
        for field in ("easy_value", "medium_value", "hard_value", "custom_value", "min_value"):
            self.assertRegex(block, field + r" = 0\b")
        self.assertIn("max_value = 1", block)
        self.assertIn("step_size = 1", block)
        self.assertIn("V274_AIR_GROWTH_STOCK <- 0;", self.sources["globals_pre.nut"])
        self.assertEqual(sum(s.count('GetSetting("v274_air_growth_stock")') for s in self.sources.values()), 1)

    def test_only_two_guarded_entries_before_growth_and_purchase(self):
        task = self.sources["task_air.nut"]
        fleet = self.sources["air_fleet.nut"]
        for text, phase in ((task, "plan"), (fleet, "buy")):
            self.assertIn("if (V274_AIR_GROWTH_STOCK == 1)", text)
            self.assertIn('if (!OpexV274AirGrowthStock(line, "' + phase + '",', text)
        self.assertLess(task.index('OpexV274AirGrowthStock(line, "plan",'), task.index('local c121BelowTarget'))
        add = fleet.split("function OpexAirAddPlane(", 1)[1].split("function OpexAirRefleetCrashedPlane", 1)[0]
        self.assertLess(add.index('OpexV274AirGrowthStock(line, "buy",'), add.index('OpexAirBestEngineForLine'))
        self.assertLess(add.index('OpexV274AirGrowthStock(line, "buy",'), add.index('CloneVehicle'))
        self.assertEqual(sum(s.count("if (V274_AIR_GROWTH_STOCK == 1)") for s in self.sources.values()), 2)

    def test_capacity_observed_both_sides_no_new_state_or_orders(self):
        for code in ("capacity > 0 && routesA > 0 && routesB > 0", "AIVehicle.GetCapacity(v, line.cargo)",
                     "waitA >= capacity * routesA && waitB >= capacity * routesB",
                     'if (DECISION_LOG) OpexDecide("V274"', 'AIStation.GetCargoWaiting(stationA, line.cargo)',
                     'AIStation.GetCargoWaiting(stationB, line.cargo)'):
            self.assertIn(code, self.helper)
        self.assertNotIn("planeCapacity", self.helper)
        for mutation in ("line.",):
            self.assertNotRegex(strip_code(self.helper), r"line\.\w+\s*(?:<-|=(?!=))")
        self.assertNotIn("AIOrder.", self.helper)
        self.assertNotIn("Sleep", self.helper)

    def test_new_function_locals_declared_and_no_closures_or_reserved_names(self):
        code = strip_code(self.helper)
        locals_ = set(re.findall(r"\blocal\s+(\w+)", code)) | {"line", "phase", "v", "lines", "routesIndex"}
        tokens = re.findall(r"(?<![.\w])([A-Za-z_]\w*)", code)
        keywords = {"local", "if", "in", "null", "foreach", "continue", "return", "true", "false"}
        externals = {"AIVehicle", "AIStation", "OpexAirLineStationId", "DECISION_LOG", "OpexDecide",
                     "OpexAirRoutesIndexAt", "OpexAirLiveRoutesAtAirport"}
        self.assertEqual(set(tokens) - locals_ - keywords - externals, set())
        self.assertNotRegex(code, r"\b(?:clone|base|parent)\b|\.(?:find|map|filter|reduce)\s*\(|\bfunction\b")

    def test_stock_predicate_boundaries_and_shared_airport(self):
        # Execute only the scalar expression extracted from the Squirrel source.
        # This checks the delivered inequalities without emulating the NoAI API.
        expression = re.search(r"local allow = (.*?);", self.helper, re.S)[1].replace("&&", "and")
        expression = " ".join(expression.split())
        cases = [
            (90, 1, 1, 90, 90, True),
            (90, 1, 1, 89, 90, False),
            (90, 1, 1, 900, 0, False),
            (90, 3, 1, 90, 90, False),
            (90, 3, 1, 270, 90, True),
            (0, 1, 1, 900, 900, False),
            (90, 0, 1, 900, 900, False),
            (90, 1, 1, -1, 900, False),
        ]
        for capacity, routesA, routesB, waitA, waitB, expected in cases:
            values = dict(capacity=capacity, routesA=routesA, routesB=routesB, waitA=waitA, waitB=waitB)
            self.assertEqual(eval(expression, {"__builtins__": {}}, values), expected, values)

    def test_new_helper_is_loaded_and_has_exactly_two_calls(self):
        code = "\n".join(strip_code(s) for s in self.sources.values())
        self.assertEqual(len(re.findall(r"\bOpexV274AirGrowthStock\s*\(", code)), 3)
        # Existing module is already required transitively by builder_air.
        self.assertIn('require("air_fleet.nut")', self.sources["builder_air.nut"])

    def test_modified_modules_have_balanced_delimiters(self):
        for name in ("air_fleet.nut", "task_air.nut", "info.nut", "settings.nut", "globals_pre.nut"):
            stack = []
            for token in re.findall(r"[{}\[\]()]", strip_code(self.sources[name])):
                if token in "{[(":
                    stack.append(token)
                else:
                    self.assertTrue(stack, name)
                    self.assertEqual(stack.pop(), {"}": "{", "]": "[", ")": "("}[token], name)
            self.assertEqual(stack, [], name)


if __name__ == "__main__":
    unittest.main()
