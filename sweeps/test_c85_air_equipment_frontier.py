"""Contrat de retrait C85 — c85_air_equipment_frontier (defaut 0, caduc sous V96).

Au defaut la frontiere n'etait jamais construite ni lue. Le choix d'avion
parcourt la liste complete airPlaneChoicesByAirport.
"""
from pathlib import Path
import unittest
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
CATALOG = (AI / "catalog.nut").read_text(encoding="utf-8")
BUILDER = read_builder_air()
GLOBALS = (AI / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (AI / "info.nut").read_text(encoding="utf-8")
SETTINGS = (AI / "settings.nut").read_text(encoding="utf-8")

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

class C85AirEquipmentFrontierRemoved(unittest.TestCase):
    def test_setting_global_and_loader_are_gone(self):
        self.assertNotIn("C85_AIR_EQUIPMENT_FRONTIER", GLOBALS)
        self.assertNotIn('name = "c85_air_equipment_frontier"', INFO)
        self.assertNotIn('GetSetting("c85_air_equipment_frontier")', SETTINGS)
        for path in AI.glob("*.nut"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("C85_AIR_EQUIPMENT_FRONTIER", text, path.name)
            self.assertNotIn("c85_air_equipment_frontier", text, path.name)
            self.assertNotIn("airPlaneFrontierByAirport", text, path.name)
            self.assertNotIn("OpexAirEquipmentStaticFrontier", text, path.name)
            self.assertNotIn("OpexAirEquipmentStaticDominates", text, path.name)
            self.assertNotIn("OpexAirRangeCovers", text, path.name)

    def test_catalog_keeps_the_full_choice_list(self):
        refresh = function_body(CATALOG, "function OpexCatalog::_refreshAir()")
        self.assertIn("this.airPlaneChoicesByAirport = {};", refresh)
        self.assertNotIn("airPlaneFrontierByAirport", refresh)
        self.assertIn("local keepPlaneChoices = true;", refresh)
        self.assertEqual(
            refresh.count("this.airPlaneChoicesByAirport.rawset(choice.type, probeChoices);"),
            2,
        )
        self.assertNotIn("OpexAirEquipmentStaticFrontier", refresh)

    def test_chooser_uses_the_full_list(self):
        chooser = function_body(BUILDER, "function OpexAirChooseRoutePlaneFull(")
        self.assertIn(
            "local routePlaneChoices = catalog.airPlaneChoicesByAirport[airport.type];",
            chooser,
        )
        self.assertNotIn("C85_AIR_EQUIPMENT_FRONTIER", chooser)
        self.assertNotIn("airPlaneFrontierByAirport", chooser)
        self.assertIn("foreach (plane in routePlaneChoices)", chooser)
        self.assertIn("if (plane.id == selectedPlane.id) continue;", chooser)
        c82 = function_body(BUILDER, "function OpexC82ChooseRoutePlane(")
        self.assertIn("foreach (plane in catalog.airPlaneChoicesByAirport[airport.type])", c82)
        self.assertNotIn("airPlaneFrontierByAirport", c82)

if __name__ == "__main__":
    unittest.main()
