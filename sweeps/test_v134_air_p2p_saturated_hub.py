from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
TOWNS = (ROOT / "ai" / "OpexAI" / "air_towns.nut").read_text(encoding="utf-8")
PLANNING = (ROOT / "ai" / "OpexAI" / "air_planning.nut").read_text(encoding="utf-8")
TASK_AIR = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")


class V134AirP2PSaturatedHubTests(unittest.TestCase):
    def test_setting_defaults_off_and_loads_once(self):
        self.assertIn("V134_AIR_P2P_SATURATED_HUB <- false;", GLOBALS)
        self.assertEqual(INFO.count('name = "v134_air_p2p_saturated_hub"'), 1)
        start = INFO.index('name = "v134_air_p2p_saturated_hub"')
        block = INFO[start:INFO.index("});", start)]
        for token in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(token, block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertEqual(SETTINGS.count('AIController.GetSetting("v134_air_p2p_saturated_hub")'), 1)
        self.assertIn('V134_AIR_P2P_SATURATED_HUB = AIController.GetSetting("v134_air_p2p_saturated_hub") != 0;', SETTINGS)

    def test_helper_requires_second_slot_and_saturated_hub(self):
        self.assertIn("function OpexAirV134SaturatedHubState(town, lines, hubIndex = null)", TOWNS)
        start = TOWNS.index("function OpexAirV134SaturatedHubState")
        end = TOWNS.index("function OpexAirV95CompetitorSecondSlotOpen", start)
        body = TOWNS[start:end]
        self.assertIn("if (!V134_AIR_P2P_SATURATED_HUB", body)
        self.assertIn("if (!OpexAirC83SecondSlotOpen(town)) return state;", body)
        self.assertIn("AIStationList(AIStation.STATION_AIRPORT)", body)
        self.assertIn("OpexAirSlotTownId(loc) != town.id", body)
        self.assertIn("AIR_HUB_MAX_ROUTES", body)
        self.assertIn("if (routes >= capRoutes)", body)

    def test_site_finding_admits_v134_eligible_town(self):
        start = PLANNING.index("function OpexAirPlansFindSites")
        end = PLANNING.index("function OpexAirPlansNewPairs", start)
        body = PLANNING[start:end]
        self.assertIn("OpexAirV134SaturatedHubState(towns[i], lines, ctx.hubIndex)", body)
        self.assertIn("skipServed = !v134Eligible", body)
        self.assertIn("if (c83RequiredSlotTown < 0 && v134Eligible)", body)
        self.assertIn("site.v134SecondSlot <- true;", body)
        self.assertIn("site.v134HubRoutes <- v134State.hubRoutes;", body)

    def test_newpair_requires_free_town_endpoint_and_logs(self):
        start = PLANNING.index("function OpexAirPlansNewPairs")
        body = PLANNING[start:]
        self.assertIn('local v134A = V134_AIR_P2P_SATURATED_HUB && ("v134SecondSlot" in sites[a]) && sites[a].v134SecondSlot;', body)
        self.assertIn('local v134B = V134_AIR_P2P_SATURATED_HUB && ("v134SecondSlot" in sites[b]) && sites[b].v134SecondSlot;', body)
        self.assertIn("if (v134A && (v134B || servedOtherB)) continue;", body)
        self.assertIn("if (v134B && (v134A || servedOtherA)) continue;", body)
        self.assertIn("v134SecondSlotA = v134A,", body)
        self.assertIn("v134SecondSlotB = v134B,", body)
        self.assertIn('OpexDecide("V134_P2P", "town=" + sites[a].town.id + " hubRoutes=" + sites[a].v134HubRoutes);', body)
        self.assertIn('OpexDecide("V134_P2P", "town=" + sites[b].town.id + " hubRoutes=" + sites[b].v134HubRoutes);', body)

    def test_batch_plan_liveliness_guard_allows_v134_second_slot(self):
        start = TASK_AIR.index("function OpexAirBatchPlanStillLive")
        end = TASK_AIR.index("function OpexAI::_tryBuildAirProject", start)
        body = TASK_AIR[start:end]
        self.assertIn('local v134SecondA = V134_AIR_P2P_SATURATED_HUB && ("v134SecondSlotA" in plan) && plan.v134SecondSlotA;', body)
        self.assertIn('local v134SecondB = V134_AIR_P2P_SATURATED_HUB && ("v134SecondSlotB" in plan) && plan.v134SecondSlotB;', body)
        self.assertIn("if (c83OwnSecondA || v134SecondA)", body)
        self.assertIn("if (c83OwnSecondB || v134SecondB)", body)


if __name__ == "__main__":
    unittest.main()
