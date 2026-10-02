"""Contracts for the isolated C83 regeneration ablation and its exposure reader."""

from pathlib import Path
import unittest

from c83_reaction import parse_c83_reactions
from test_exp_c83_watch_daily import body


ROOT = Path(__file__).resolve().parents[1]


class ReactionContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "ai/OpexAI/task_projects.nut").read_text(encoding="utf-8")

    def test_current_default_is_kept_and_setting_loaded(self):
        info = (ROOT / "ai/OpexAI/info.nut").read_text(encoding="utf-8")
        setting = info.split('name = "c83_slot_reaction"', 1)[1].split("});", 1)[0]
        for field in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(f"{field} = 1", setting)
        self.assertIn("flags = AICONFIG_BOOLEAN", setting)
        self.assertEqual(info.count('name = "c83_slot_reaction"'), 1)
        self.assertIn("C83_SLOT_REACTION <- true;",
                      (ROOT / "ai/OpexAI/globals_pre.nut").read_text(encoding="utf-8"))
        self.assertIn('C83_SLOT_REACTION = AIController.GetSetting("c83_slot_reaction") != 0;',
                      (ROOT / "ai/OpexAI/settings.nut").read_text(encoding="utf-8"))

    def test_legacy_suppression_follows_transition_and_funding_guards(self):
        watch = body(self.source, "function OpexAI::_c83WatchAirSlotTransitions(")
        gate = watch.index("if (!C83_SLOT_REACTION)")
        self.assertLess(watch.index("this._c83SlotWatch.rawset(town.id, state);"), gate)
        self.assertLess(watch.index("if (state != 1 || previous == 1) continue;"), gate)
        self.assertLess(watch.index("if (alreadyFunded)"), gate)
        self.assertLess(gate, watch.index('this._c77EnqueueEntity(["air"]'))
        suppressed = watch[gate:watch.index('this._c77EnqueueEntity(["air"]')]
        self.assertIn('OpexC83ReactionLog(town.id, "suppressed");', suppressed)
        self.assertIn("continue;", suppressed)
        self.assertNotIn("enqueued++", suppressed)

    def test_fixes_cannot_bypass_suppression_or_record_a_race_receipt(self):
        watch = body(self.source, "function OpexC83WatchOneTown(")
        gate = watch.index("if (!C83_SLOT_REACTION)")
        self.assertLess(watch.index("OpexAirC83FundedRaceCoversTown"), gate)
        self.assertLess(gate, watch.index('ai._c77EnqueueEntity(["air"]'))
        suppressed = watch[gate:watch.index('local raceKey =')]
        self.assertIn("ai._c83SlotWatch.rawset(townId, state);", suppressed)
        self.assertIn("if (previous != 1)", suppressed)
        self.assertIn("return 0;", suppressed)
        self.assertNotIn("_c83SlotRace", suppressed)

    def test_pass_only_stops_for_actual_enqueues_and_priority_stays(self):
        attempt = body(self.source, "function OpexAI::_tryBuildProjects(")
        self.assertIn("if (c83TargetedRegens > 0) return true;", attempt)
        self.assertIn("OpexPromoteLiveDefensiveAir(this._projects, OpexAvailableCapital());", attempt)
        for name in ("air_sites.nut", "task_air.nut", "persist.nut"):
            self.assertNotIn("C83_SLOT_REACTION", (ROOT / "ai/OpexAI" / name).read_text(encoding="utf-8"))

    def test_summary_reads_final_log_and_excludes_competitor(self):
        source = (ROOT / "sweeps/bench_1v1_5y_20seeds.py").read_text(encoding="utf-8")
        self.assertIn('if record["arm"] == "OpexAI":\n                record["c83_reaction"] = c83_reaction', source)
        self.assertIn('Path(log_path).read_text(encoding="utf-8")', source)
        frozen_files = source.split("CAMPAIGN_HARNESS_FILES = (", 1)[1].split(")", 1)[0]
        self.assertIn('"sweeps/c83_reaction.py"', frozen_files)


class ExposureReaderTests(unittest.TestCase):
    def event(self, action="suppressed", enabled=0, stamp="1970-7-9", town=3):
        return f"dbg: [script] [0] OPEX {stamp} C83_REACTION enabled={enabled} town={town} action={action}\n"

    def test_absence_and_malformed_are_unknown(self):
        for output in (None, "", "other log", self.event().replace("town=3", "town=?")):
            self.assertIsNone(parse_c83_reactions(output))

    def test_suppressed_event_exposes_ablation(self):
        result = parse_c83_reactions(self.event())
        self.assertEqual((result["opportunities"], result["suppressed"], result["enqueued"]), (1, 1, 0))
        self.assertEqual(result["events"][0]["date"], "1970-07-09")

    def test_success_and_failure_are_distinct(self):
        result = parse_c83_reactions(self.event("enqueued", 1) + self.event("enqueue_failed", 1, town=4))
        self.assertEqual((result["enqueued"], result["enqueue_failed"], result["suppressed"]), (1, 1, 0))

    def test_invalid_date_setting_change_or_inconsistent_action_are_unknown(self):
        for output in (self.event(stamp="1970-2-30"), self.event(enabled=1),
                       self.event() + self.event("enqueued", 1)):
            self.assertIsNone(parse_c83_reactions(output))

    def test_counts_events_once_from_final_log_preserving_same_day_events(self):
        result = parse_c83_reactions(self.event(town=3) + self.event(town=4))
        self.assertEqual(result["opportunities"], 2)
        self.assertEqual([event["town"] for event in result["events"]], [3, 4])


if __name__ == "__main__":
    unittest.main()
