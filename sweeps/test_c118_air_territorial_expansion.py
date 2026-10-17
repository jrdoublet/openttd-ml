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
    def test_station_coverage_cache_follows_generation_lifetime(self):
        reset = body(AIR, "function OpexAirResetSiteCache", "function OpexAirResetStationCoverageTownCache")
        prepare = body(AIR, "function OpexAirPlansPrepare", "function OpexAirPlansFindSites")
        self.assertIn("AIR_STATION_COVERAGE_TOWN_CACHE.clear()", reset)
        self.assertIn("AIR_C121_STATION_COVERAGE_CACHE.clear()", reset)
        self.assertIn("OpexAirResetStationCoverageTownCache()", prepare)
        self.assertIn("stationCoverageTownCacheInit", prepare)

if __name__ == "__main__":
    unittest.main()
