"""R18 source contracts, NOT Squirrel execution or engine failure injection."""
from pathlib import Path
import re
import unittest
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air

ROOT = Path(__file__).resolve().parents[1]


class TestAirLevelFailure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = read_builder_air()
        cls.level = cls.source.split("function OpexAirLevelFootprint(", 1)[1].split("\nfunction ", 1)[0]
        cls.build = cls.source.split("function OpexBuildAirRoute(", 1)[1].split("\nfunction ", 1)[0]

    def test_level_returns_explicit_result_instead_of_boolean(self):
        self.assertNotRegex(self.level, r"return\s+(?:true|false|OpexAirFootprintIsFlat\([^;]+\));")
        self.assertIn("ok = false, error = err, errorText = errorText", self.level)
        self.assertIn('ok = true, error = 0, errorText = ""', self.level)

    def test_geometric_failures_do_not_inherit_stale_engine_error(self):
        self.assertIn("AIError.ERR_PRECONDITION_FAILED", self.level)
        self.assertIn("AIError.ERR_FLAT_LAND_REQUIRED", self.level)
        self.assertIn("if (!OpexAirFootprintIsFlat(anchor, airport))", self.level)

    def test_local_authority_retry_recaptures_its_own_failure(self):
        retry = self.level.split("OpexBoostTownRating(townId, 800, 40);", 1)[1]
        self.assertRegex(retry, r"if \(!AITile.LevelTiles\(anchor, end\)\)\s*\{\s*"
                               r"err = AIError.GetLastError\(\);\s*errorText = AIError.GetLastErrorString\(\);")
        self.assertIn("err != AITile.ERR_AREA_ALREADY_FLAT", retry)

    def test_both_airports_short_circuit_build_and_authority_retry(self):
        for side in ("A", "B"):
            with self.subTest(side=side):
                self.assertIn(f"local ok{side} = level{side}.ok && AIAirport.BuildAirport(", self.build)
                self.assertRegex(self.build, rf"if \(!level{side}.ok\)\s*\{{\s*"
                                 rf"airportError{side} = level{side}.error;\s*"
                                 rf"airportErrorText{side} = level{side}.errorText;\s*"
                                 rf"\}} else if \(!ok{side}\)")
        # No forgotten caller still interprets a table as a boolean.
        all_source = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "ai/OpexAI").glob("*.nut"))
        calls = re.findall(r"(?m)^\s*.*OpexAirLevelFootprint\([^\n]*", all_source)
        self.assertEqual(len(calls), 3)  # definition + two guarded call sites

    def test_failure_path_preserves_accounting_and_reused_hub(self):
        self.assertIn('result.opcodes += budget.end("build_airports");', self.build)
        self.assertIn("result.actualCost = costs != null ? costs.GetCosts() : 0;", self.build)
        failure_b = self.build.split("if (airportB == null)", 1)[1].split("local stationA", 1)[0]
        self.assertLess(failure_b.index("result.error = airportErrorB;"), failure_b.index("OpexAirRollback("))
        self.assertIn("OpexAirRollback(reuseA ? null : airportA, null, []);", failure_b)
        self.assertIn("if (!keepOrphan)", failure_b)  # existing orphan reuse policy unchanged

    def test_cash_error_still_reaches_existing_abandon_guard(self):
        task = (ROOT / "ai/OpexAI/task_air.nut").read_text(encoding="utf-8")
        lines = (ROOT / "ai/OpexAI/lines.nut").read_text(encoding="utf-8")
        self.assertIn("OpexBuildFailureIsAbandonable(result)", task)
        self.assertIn('result.error == AIError.ERR_NOT_ENOUGH_CASH) return false;', lines)
        for side in ("A", "B"):
            self.assertIn(f"result.error = airportError{side};", self.build)


if __name__ == "__main__":
    unittest.main()