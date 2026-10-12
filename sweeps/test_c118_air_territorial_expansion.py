from pathlib import Path
import unittest
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air
from opex_projects_source import read_projects_source


ROOT = Path(__file__).resolve().parents[1]
PROJECTS = read_projects_source()
AIR = read_builder_air()
TASK = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
BENCH = (ROOT / "sweeps" / "bench_1v1_5y_20seeds.py").read_text(encoding="utf-8")


def body(text: str, start: str, end: str) -> str:
    i = text.index(start)
    j = text.index(end, i)
    return text[i:j]


class TestC118SharedCoverage(unittest.TestCase):
    def test_policy_removed_and_probe_defaults_off(self):
        self.assertNotIn("C118_AIR_TERRITORIAL_EXPANSION", GLOBALS + AIR + PROJECTS + TASK)
        self.assertNotIn('name = "c118_air_territorial_expansion"', INFO)
        self.assertIn("C118_AIR_COVERAGE_PROBE <- false;", GLOBALS)
        start = INFO.index('name = "c118_air_coverage_probe"')
        snippet = INFO[start:start + 600]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)

    def test_coverage_uses_real_catchment_without_townlist(self):
        station = body(AIR, "function OpexC118StationCoverageTowns", "function OpexC118EndpointCoverageTowns")
        endpoint = body(AIR, "function OpexC118EndpointCoverageTowns", "function OpexC118PlanCoverageTowns")
        coverage = station + endpoint
        self.assertIn("AITileList_StationCoverage", station)
        self.assertIn("OpexC118StationCoverageTowns", endpoint)
        self.assertIn("AITile.GetClosestTown", coverage)
        self.assertIn("AITile.GetCargoProduction", coverage)
        self.assertNotIn("AITownList", coverage)
        self.assertNotIn("AITownList()", coverage)

    def test_new_site_coverage_cache_depends_on_airport_type(self):
        self.assertIn('"c118AirportCoverageTowns_" + airportType', AIR)

    def test_durable_sign_probe_is_parsed_by_harness(self):
        for prefix in ("C8D|", "C8R|", "C8E|", "C8C|", "C8F|", "C8T|", "C8V|"):
            self.assertIn(prefix, BENCH)
        self.assertIn("C118_COVERAGE", TASK)
        self.assertIn("C8V|", TASK)
        self.assertIn("def c118_sign_metrics(chunks):", BENCH)
        self.assertIn("structural.update(c118_sign_metrics(chunks))", BENCH)
        for field in ("c118_coverage_events", "c118_decisions", "c118_decision_count"):
            self.assertIn(field, BENCH)


if __name__ == "__main__":
    unittest.main()
