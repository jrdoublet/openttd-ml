"""Source contracts for V288; compilation/execution require the real smoke."""
from pathlib import Path
import re
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def body(name, function):
    text = read(name)
    start = text.index("function " + function + "(")
    end = text.find("\nfunction ", start + 1)
    return text[start:end if end >= 0 else len(text)]


class PoolStaleness(unittest.TestCase):
    def test_setting_off_all_difficulties_read_once(self):
        setting = re.search(r'AddSetting\(\{\s*name = "v288_pool_staleness".*?\}\);',
                            read("info.nut"), re.S)[0]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{level}_value = 0", setting)
        self.assertIn("min_value = 0, max_value = 365", setting)
        self.assertEqual(sum(p.read_text().count('GetSetting("v288_pool_staleness")')
                             for p in AI.glob("*.nut")), 1)
        self.assertIn('V288_POOL_STALENESS <- 0;', read("globals_pre.nut"))

    def test_age_is_completion_date_not_request_date(self):
        begin = body("pool_staleness.nut", "OpexV288Begin")
        self.assertNotIn("date =", begin)
        self.assertIn("state.pending = true", begin)
        finish = body("pool_staleness.nut", "OpexV288Complete")
        self.assertIn("date = AIDate.GetCurrentDate()", finish)
        self.assertIn("revisions = ticket.revisions", finish)
        self.assertNotIn("OpexV288Snapshot", finish)

    def test_empty_pool_is_independent_of_requesting_event(self):
        begin = body("pool_staleness.nut", "OpexV288Begin")
        self.assertIn("OpexV288Insufficient(projects, mode)", begin)
        empty = body("pool_staleness.nut", "OpexV288Insufficient")
        self.assertIn('mode == "rail" ? 2 : 1', empty)
        self.assertIn("OpexStagedCandidateStillValid", empty)
        self.assertIn("OpexAirBatchPlanStillLive", empty)

    def test_c78_continuation_never_regated(self):
        self.assertIn('OpexV288Begin("air"', body("scheduler_tasks.nut", "OpexC78StartCatalogAirRebuild"))
        self.assertNotIn("OpexV288Begin", body("scheduler_tasks.nut", "OpexC78ContinueCatalogAirRebuild"))
        self.assertNotIn("OpexV288Complete", body("scheduler_tasks.nut", "OpexC78PublishPartialAir"))
        apply = body("scheduler_tasks.nut", "OpexC78ApplyAir")
        self.assertLess(apply.index("_rebuildProjects"), apply.index("OpexV288Complete"))

    def test_bootstrap_nonair_not_advanced_by_age(self):
        build = body("projects.nut", "OpexBuildProjects")
        self.assertIn("V288_POOL_STALENESS > 0 && generationStage == OPEX_STAGE_COMPLETE", build)
        self.assertIn("if (MODE_AIR && C121_CATALOG_FIRST_YEAR_ACTIVE)", build)
        self.assertIn("priorProjects = V288_OWNER._projects", build)
        self.assertIn("OpexStagedCandidateStillValid", build)

    def test_targeted_generation_does_not_freshen_entire_mode(self):
        mode = body("projects_generation.nut", "OpexRegenerateModeProjects")
        self.assertIn("entityKind == null && !V217_REGEN_NO_PAX", mode)
        self.assertIn('"freight_rotation"', mode)
        sliced = body("projects_generation.nut", "OpexRegenerateAirProjectsSlice")
        self.assertIn('!("v288Ticket" in sliceState)', sliced)
        self.assertIn("V288_POOL_STALENESS > 0 && entityKind == null", sliced)

    def test_empty_selection_guard_before_filter_after_stock_merge(self):
        select = body("projects_selection.nut", "OpexReselectProjects")
        self.assertLess(select.index("OpexRailPrepMergeAlternatives"), select.index("OpexV288EmptySelection"))
        self.assertLess(select.index("OpexV288EmptySelection"), select.index("OpexFilterAirAlternatives"))
        guard = body("pool_staleness.nut", "OpexV288EmptySelection")
        self.assertIn("projects.best.len() != 0", guard)
        self.assertIn("previous.key != OpexProjectKeyFor(p) || previous.capital != cap", guard)
        self.assertIn("projects.v288PoolRevision != V288_PUBLICATION_REV", guard)
        self.assertIn("capitalBudget >= cheapest", guard)
        self.assertIn("p.payload.planePrice + 1000", guard)

    def test_load_discards_dates_and_still_forces_rebuild(self):
        start = body("main.nut", "OpexAI::Start")
        self.assertIn("V288_OWNER = this; V288_POOLS = {};", start)
        persist = read("persist.nut")
        self.assertIn("this._projects = null", persist)
        self.assertIn("this._c76ForceReloadRegen = true", persist)
        self.assertNotIn("V288_POOLS", persist)

    def test_fleet_demand_and_subsidies_are_not_time_gated(self):
        fleet = body("projects_update.nut", "OpexInjectFleetProjects")
        self.assertIn('"fleet_demand"', fleet)
        for function in ("OpexAI::_c77InjectSubsidy",):
            self.assertNotIn("OpexV288Begin", body("orchestrator.nut", function))

    def test_production_thresholds_and_revision_snapshots(self):
        snapshots = body("pool_staleness.nut", "OpexV288Snapshot")
        self.assertIn("_c76GetModeDeps(mode)", snapshots)
        self.assertIn("OPEX_ABANDON_REVISION", snapshots)
        self.assertIn("OPEX_AIR_ROLLBACK_REVISION", snapshots)
        self.assertIn("previous * 20", body("pool_staleness.nut", "OpexV288IndustryProduction"))

    def test_v276_only_stamps_finished_scan(self):
        step = body("candidates_v276.nut", "OpexV276Continue")
        self.assertIn("s.v288Tickets[u.mode] == null", step)
        self.assertGreater(step.index("OpexV288Complete"), step.index("s.unit++"))
        self.assertNotIn("OpexV288Complete", body("candidates_v276.nut", "OpexV276Publish"))

    def test_log_contract(self):
        log = body("pool_staleness.nut", "OpexV288Log")
        for field in ('"V288_POOL"', '"mode="', '" action="', '" cause="', '" age="', '" ops="'):
            self.assertIn(field, log)
        self.assertIn("if (DECISION_LOG)", log)


if __name__ == "__main__":
    unittest.main()
