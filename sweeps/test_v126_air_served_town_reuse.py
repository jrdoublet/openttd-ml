from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
TOWNS = (ROOT / "ai" / "OpexAI" / "air_towns.nut").read_text(encoding="utf-8")
PLANNING = (ROOT / "ai" / "OpexAI" / "air_planning.nut").read_text(encoding="utf-8")


class V126AirServedTownReuseTests(unittest.TestCase):
    def test_setting_defaults_off_and_loads_once(self):
        self.assertIn("V126_AIR_SERVED_TOWN_REUSE <- false;", GLOBALS)
        self.assertEqual(INFO.count('name = "v126_air_served_town_reuse"'), 1)
        start = INFO.index('name = "v126_air_served_town_reuse"')
        block = INFO[start:INFO.index("});", start)]
        for token in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(token, block)
        self.assertEqual(SETTINGS.count('AIController.GetSetting("v126_air_served_town_reuse")'), 1)

    def test_helper_requires_noise_and_fewer_than_two_routes(self):
        start = TOWNS.index("function OpexAirV126ServedTownState")
        end = TOWNS.index("function OpexAirV95CompetitorSecondSlotOpen", start)
        body = TOWNS[start:end]
        self.assertIn("AITown.GetAllowedNoise(town.id)", body)
        self.assertIn("if (state.noise < 1) return state;", body)
        self.assertIn("AIStationList(AIStation.STATION_AIRPORT)", body)
        self.assertIn("OpexAirSlotTownId(loc) != town.id", body)
        self.assertIn("if (routes < 2)", body)
        self.assertIn("stationA == st || stationB == st", body)

    def test_origin_served_filter_allows_only_v126_eligible_towns(self):
        start = PLANNING.index("function OpexAirPlansFindSites")
        end = PLANNING.index("function OpexAirPlansNewPairs", start)
        body = PLANNING[start:end]
        self.assertIn("OpexAirV126ServedTownState(towns[i], lines)", body)
        self.assertIn("if (isServed && !c83OwnSecondSlot && !v126Reuse)", body)
        self.assertIn("site.v126ServedTown <- true;", body)
        self.assertIn('OpexDecide("V126_AIR_TOWN"', body)

    def test_pair_log_counts_formed_pairs_with_served_endpoint(self):
        start = PLANNING.index("function OpexAirPlansNewPairs")
        body = PLANNING[start:]
        self.assertIn('OpexDecide("V126_AIR_PAIR"', body)
        self.assertIn("servedA=", body)
        self.assertIn("servedB=", body)
        self.assertIn("routesA=", body)
        self.assertIn("routesB=", body)


if __name__ == "__main__":
    unittest.main()
