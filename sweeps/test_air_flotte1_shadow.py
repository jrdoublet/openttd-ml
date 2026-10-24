"""Source contracts and synthetic-event regression for AIR-FLOTTE-1 shadow."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "sweeps") not in sys.path:
    sys.path.insert(0, str(ROOT / "sweeps"))

from sweeps.analyze_air_flotte1_shadow import assess, parse_records

AI = ROOT / "ai" / "OpexAI"


def log(kind, **fields):
    return "OPEX 1973-2-10 AIRF1_" + kind + " " + " ".join(
        f"{name}={value}" for name, value in fields.items()) + "\n"


class ShadowReaderTest(unittest.TestCase):
    def test_cash_crossing_is_only_a_proxy(self):
        logs = [
            log("BUY", id="abc", channel="reinforce", phase="before",
                finance=40000, spend=39000, calibrated_profit=1000,
                rail_search_phase="search"),
            log("LIST", id="abc", rail_remaining=1, search_same_best=1,
                rail_pass_stage="rejected", rail_pass_reason="too_close_no_join"),
            log("RAIL", id="abc", scope="listed_best_remaining",
                key="rail|2|3|0|freight", finance=50000,
                afford_now=1, afford_after=0, roi_c70_finance=700),
            log("POOL", id="abc", truncated=0),
            log("CLOCK", id="abc", same_tick=1),
            log("READY", id="abc", same_tick=1, same_cash=1),
            log("OUTCOME", id="abc", outcome="built"),
        ]
        result = assess(parse_records(logs))
        self.assertEqual(result["counts"]["rail_cash_crossing_proxy"], 1)
        self.assertEqual(result["counts"]["crossing_rail_calibrated_roi_higher"], 1)
        self.assertEqual(result["counts"]["with_rail_search_search"], 1)
        self.assertEqual(result["counts"]["rail_search_matches_best"], 1)
        self.assertEqual(result["counts"]["crossing_rail_reason_too_close_no_join"], 1)
        self.assertEqual(result["counts"]["crossings_with_rail_rejected_in_same_pass"], 1)
        self.assertIsNone(result["proven_buildable_rail_opportunities"])
        self.assertIsNone(result["profit_gain_from_reallocation"])
        self.assertIsNone(result["cash_crossing_examples"][0]["causal_eviction"])

    def test_tick_advance_disqualifies_same_instant(self):
        logs = [
            log("BUY", id="abc", channel="reinforce", phase="before"),
            log("CLOCK", id="abc", same_tick=0),
            log("OUTCOME", id="abc", outcome="built"),
        ]
        result = assess(parse_records(logs))
        self.assertEqual(result["counts"]["unstable_tick_disqualified"], 1)
        self.assertNotIn("rail_cash_crossing_proxy", result["counts"])

    def test_tick_changes_after_scan_are_not_same_instant(self):
        logs = [
            log("BUY", id="abc", channel="reinforce"),
            log("CLOCK", id="abc", same_tick=1),
            log("READY", id="abc", same_tick=0, same_cash=1),
            log("OUTCOME", id="abc", outcome="built"),
        ]
        result = assess(parse_records(logs))
        self.assertEqual(result["counts"]["unmatched_transaction_time_disqualified"], 1)

    def test_failed_and_duplicate_events_not_misidentified(self):
        logs = [
            log("BUY", id="a", channel="renewal"),
            log("CLOCK", id="a", same_tick=1),
            log("OUTCOME", id="a", outcome="start_failed"),
            log("BUY", id="b", channel="reinforce"),
            log("BUY", id="b", channel="reinforce"),
            log("CLOCK", id="b", same_tick=1),
            log("OUTCOME", id="b", outcome="built"),
        ]
        result = assess(parse_records(logs))
        self.assertEqual(result["counts"]["not_built"], 1)
        self.assertEqual(result["counts"]["duplicate_event_disqualified"], 1)


class ShadowSourceContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helper = (AI / "air_flotte1_shadow.nut").read_text(encoding="utf-8")
        cls.projects = (AI / "task_projects.nut").read_text(encoding="utf-8")
        cls.v252 = (AI / "task_v252.nut").read_text(encoding="utf-8")

    def test_shadow_is_guarded_no_policy_mutations(self):
        self.assertIn("if (!AIR_FLOTTE1_SHADOW) return null;", self.helper)
        self.assertIn("AIR_FLOTTE1_SHADOW", self.projects)
        self.assertIn("AIR_FLOTTE1_SHADOW", self.v252)
        info = (AI / "info.nut").read_text(encoding="utf-8")
        settings = (AI / "settings.nut").read_text(encoding="utf-8")
        globals_pre = (AI / "globals_pre.nut").read_text(encoding="utf-8")
        selection = (AI / "projects_selection.nut").read_text(encoding="utf-8")
        self.assertNotIn('name = "air_flotte1_shadow"', info)
        self.assertNotIn('AIController.GetSetting("air_flotte1_shadow")', settings)
        self.assertIn('AIR_FLOTTE1_SHADOW = OpexProbeEnabled(8388608);', settings)
        self.assertIn("AIR_FLOTTE1_SHADOW <- false;", globals_pre)
        self.assertIn("AIR_FLOTTE1_KDEC <- -1;", globals_pre)
        self.assertIn("AIR_FLOTTE1_SHADOW && realSelection", selection)
        self.assertIn("::AIR_FLOTTE1_KDEC = kDec;", selection)
        for forbidden in ("OpexProjectInsertDefensive(", "OpexReselectProjects(",
                          "OpexC69ComputeKDec(", "AIVehicle.BuildVehicle(",
                          "AIVehicle.SellVehicle(", "AISign.BuildSign("):
            self.assertNotIn(forbidden, self.helper)
        self.assertIn("truncated=", self.helper)
        self.assertIn("same_tick=", self.helper)
        self.assertIn("function OpexAirF1Ready(", self.helper)
        self.assertIn("function OpexAirF1RailPath(", self.helper)
        self.assertIn("rail_pass_reason=", self.helper)
        task_rail = (AI / "task_rail.nut").read_text(encoding="utf-8")
        for reason in ("too_close_no_join", "too_close_hard", "abandoned_pair",
                       "vehicle_limit", "insufficient_cash", "search_in_progress"):
            self.assertIn(f'OpexAirF1RailPath(project, i, "rejected", "{reason}")',
                          task_rail)

    def test_hooks_before_purchase_and_outcome_after(self):
        projects = self.projects[self.projects.index("function OpexAI::_tryBuildFleetProject"):
                                 self.projects.index("/* C39.5 :")]
        self.assertLess(projects.index('OpexAirF1Before(this, "reinforce"'),
                        projects.index("OpexAirAddPlane("))
        self.assertIn('OpexAirF1After(airF1Event, "built"', projects)
        self.assertIn("c75BuiltKeys);", self.projects)
        self.assertLess(self.v252.index('OpexAirF1Before(this, "renewal"'),
                        self.v252.index("AIVehicle.BuildVehicleWithRefit("))
        self.assertIn('OpexAirF1After(airF1Event, "build_failed")', self.v252)
        self.assertIn('OpexAirF1After(airF1Event, "order_failed")', self.v252)
        self.assertIn('OpexAirF1After(airF1Event, "start_failed")', self.v252)


if __name__ == "__main__":
    unittest.main()
