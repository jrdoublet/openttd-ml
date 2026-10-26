"""Permanent default-OFF and guarded TRACEX-only MULTI-1 third lever."""
import re
import unittest
from pathlib import Path
from n75_mc_legacy import historical_bytes

ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(file):
    return (ROOT / file).read_text(encoding="utf-8")


class RoadDetourContract(unittest.TestCase):
    def test_unchanged_historical_settings_and_off(self):
        info, settings = read("info.nut"), read("settings.nut")
        decl = re.findall(r'AddSetting\(\{ name = "multi1_road_detour".*?\}\);', info, re.S)
        self.assertEqual(len(decl), 1)
        self.assertIn("min_value = 0, max_value = 2", decl[0])
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(level + "_value = 0", decl[0])
        self.assertEqual(settings.count('AIController.GetSetting("multi1_road_detour")'), 1)
        self.assertIn("MULTI1_ROAD_DETOUR <- 0;", read("globals_pre.nut"))
        for file in ("info.nut", "settings.nut"):
            self.assertNotIn(b'multi1_road_detour', historical_bytes(file, (ROOT / file).read_bytes()))

    def test_historical_planner_unchanged_and_shadow_not_published(self):
        code = read("opcode_exact.nut")
        body = code[code.index("function OpexRoadPlanForActive("):
                    code.index("function OpexAirFleetYieldCompare(")]
        self.assertLess(body.index("for (local shape = 0; shape < 2; shape++)"),
                        body.index("for (local shape = 2; shape < 6; shape++)"))
        self.assertLess(body.index("for (local shape = 2; shape < 6; shape++)"),
                        body.index("if (MULTI1_ROAD_DETOUR > 0"))
        for guard in ("MODE_AIR && MODE_RAIL && MODE_ROAD && noDepot == 0",
                      "year >= 1971 && year <= 1973",
                      "extraTrials >= 64",
                      "shape = 6; shape < 10 && extraTrials < 64",
                      "trace.len() > ROAD_MAX_TRACE_TILES",
                      "OpexRoadTraceHitsStop(", "OpexRoadTraceBuildable(trace)",
                      "OpexRoadFindDepot(trace, siteA, siteB)",
                      'MULTI1_ROAD_DETOUR == 2 ? "rescue" : "shadow"'):
            with self.subTest(guard=guard):
                self.assertIn(guard, body)
        self.assertIn("if (MULTI1_ROAD_DETOUR == 2) {\n              return", body)
        builder = read("builder_road.nut")
        multi = builder[builder.index("function OpexRoadTraceMulti("):
                        builder.index("function OpexRoadPlanPaxVoirie(")]
        self.assertIn("variant >= 6 && variant <= 9", multi)
        self.assertIn("OpexRoadIsFlat(c1)", multi)


if __name__ == "__main__":
    unittest.main()
