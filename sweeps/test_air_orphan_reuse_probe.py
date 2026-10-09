"""Contrats passifs des traces de provenance des aéroports orphelins."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class AirOrphanReuseProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.builder = (ROOT / "air_construction.nut").read_text(encoding="utf-8")
        cls.task = (ROOT / "task_air.nut").read_text(encoding="utf-8")

    def test_orphan_only_after_cost_and_reason_with_new_a(self):
        failed_b = self.builder.split("if (airportB == null) {", 1)[1].split(
            "local stationA =", 1
        )[0]
        self.assertLess(failed_b.index("result.actualCost ="), failed_b.index("AIR_ORPHAN_RETAIN"))
        self.assertLess(failed_b.index("result.reason = reuseB ?"), failed_b.index("AIR_ORPHAN_RETAIN"))
        self.assertIn("PROBE_AIR_FINANCE_MARGIN && result.orphanRetained", failed_b)
        self.assertIn('result.reason = reuseB ? "HUBB" : "BFAIL"', failed_b)
        self.assertIn('" cost_a=" + (brk.levelA + brk.airportA)', failed_b)
        self.assertIn('" station=" +', failed_b)

    def test_reuse_log_only_after_success_before_line_append_on_both_paths(self):
        self.assertEqual(self.task.count("OpexAirHubReuseObserve(this._lines, "), 2)
        for marker in (
            "OpexAirHubReuseObserve(this._lines, plan, result, this._nextLineId)",
            "OpexAirHubReuseObserve(this._lines, buildPlan, result, this._nextLineId)",
        ):
            point = self.task.index(marker)
            nearby = self.task[point - 180 : point + 120]
            self.assertIn("if (PROBE_AIR_FINANCE_MARGIN)", nearby)
            self.assertLess(point, self.task.index("this._lines.append({", point))

    def test_prior_lines_are_counted_by_physical_station_identity(self):
        helper = self.task.split("function OpexAirHubPriorLineRefs", 1)[1].split(
            "function OpexAirHubReuseObserve", 1
        )[0]
        self.assertIn('line.mode != "air"', helper)
        self.assertIn("AIStation.GetStationID(line.stationA) == station", helper)
        self.assertIn("AIStation.GetStationID(line.stationB) == station", helper)
        self.assertIn("if (found) refs++", helper)


if __name__ == "__main__":
    unittest.main()
