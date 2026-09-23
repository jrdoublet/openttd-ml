from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CATALOG = (ROOT / "ai" / "OpexAI" / "catalog.nut").read_text(encoding="utf-8")
BUILDER = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")

def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[start:pos + 1]
    raise AssertionError(signature)

def range_covers(a, b):
    ar = a.get("maxOrderDistance", 0)
    br = b.get("maxOrderDistance", 0)
    if ar <= 0:
        return True
    if br <= 0:
        return False
    return ar >= br

def dominates(a, b):
    if a["id"] == b["id"]:
        return False
    if (a["capacity"] < b["capacity"] or a["speed"] < b["speed"] or
        a["price"] > b["price"] or a["runningCost"] > b["runningCost"] or
        not range_covers(a, b)):
        return False
    ar = a.get("maxOrderDistance", 0)
    br = b.get("maxOrderDistance", 0)
    strict_range = (ar <= 0 < br) or (ar > br > 0)
    return (a["capacity"] > b["capacity"] or a["speed"] > b["speed"] or
            a["price"] < b["price"] or a["runningCost"] < b["runningCost"] or strict_range)

class C85AirEquipmentFrontierTests(unittest.TestCase):
    def test_setting_defaults_off(self):
        self.assertIn("C85_AIR_EQUIPMENT_FRONTIER <- false;", GLOBALS)
        start = INFO.index('name = "c85_air_equipment_frontier"')
        block = INFO[start:INFO.index("});", start)]
        for token in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(token, block)
        self.assertIn('C85_AIR_EQUIPMENT_FRONTIER = AIController.GetSetting("c85_air_equipment_frontier") != 0;', SETTINGS)

    def test_catalog_preserves_full_list_and_builds_frontier(self):
        refresh = function_body(CATALOG, "function OpexCatalog::_refreshAir()")
        self.assertIn("this.airPlaneChoicesByAirport = {};", refresh)
        self.assertIn("this.airPlaneFrontierByAirport = {};", refresh)
        self.assertIn("EQUIPMENT_ROI_PROBE || AIR_ROUTE_PLANE_SELECTION || C85_AIR_EQUIPMENT_FRONTIER", refresh)
        self.assertEqual(refresh.count("this.airPlaneChoicesByAirport.rawset(choice.type, probeChoices);"), 2)
        self.assertEqual(refresh.count("this.airPlaneFrontierByAirport.rawset(choice.type, OpexAirEquipmentStaticFrontier(probeChoices));"), 2)

    def test_dominance_contract(self):
        body = function_body(CATALOG, "function OpexAirEquipmentStaticDominates(")
        for expr in ("a.capacity < b.capacity", "a.speed < b.speed", "a.price > b.price",
                     "a.runningCost > b.runningCost", "OpexAirRangeCovers(a, b)",
                     "a.capacity > b.capacity", "a.speed > b.speed", "a.price < b.price",
                     "a.runningCost < b.runningCost"):
            self.assertIn(expr, body)
        base = dict(id=1, capacity=100, speed=500, price=50000, runningCost=5000)
        limited = {**base, "id": 2, "maxOrderDistance": 300}
        unlimited = {**base, "id": 3, "maxOrderDistance": 0}
        longer = {**base, "id": 4, "maxOrderDistance": 500}
        equal = {**base, "id": 5, "maxOrderDistance": 300}
        self.assertTrue(dominates(unlimited, limited))
        self.assertTrue(dominates(longer, limited))
        self.assertFalse(dominates(equal, limited))

    def test_tradeoff_is_not_pruned(self):
        cheap = dict(id=1, capacity=100, speed=500, price=40000, runningCost=4000, maxOrderDistance=0)
        fast = dict(id=2, capacity=100, speed=900, price=80000, runningCost=7000, maxOrderDistance=0)
        self.assertFalse(dominates(cheap, fast))
        self.assertFalse(dominates(fast, cheap))

    def test_chooser_gates_frontier_to_default_c68(self):
        chooser = function_body(BUILDER, "function OpexAirChooseRoutePlaneFull(")
        self.assertIn("local routePlaneChoices = catalog.airPlaneChoicesByAirport[airport.type];", chooser)
        self.assertIn("C85_AIR_EQUIPMENT_FRONTIER && C72_PLANE_CHOICE == 0 && !C82_ENGINE_CALIBRATION", chooser)
        self.assertIn("routePlaneChoices = catalog.airPlaneFrontierByAirport[airport.type];", chooser)
        self.assertIn("foreach (plane in routePlaneChoices)", chooser)
        self.assertIn("if (plane.id == selectedPlane.id) continue;", chooser)
        c82 = function_body(BUILDER, "function OpexC82ChooseRoutePlane(")
        self.assertIn("foreach (plane in catalog.airPlaneChoicesByAirport[airport.type])", c82)
        self.assertNotIn("airPlaneFrontierByAirport", c82)

if __name__ == "__main__":
    unittest.main()
