"""Contrats source des correctifs C83 derrière c83_fixes (défaut 0)."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start : idx + 1]
    raise AssertionError(f"unterminated function: {signature}")


class C83FixesContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read("ai/OpexAI/info.nut")
        cls.settings = read("ai/OpexAI/settings.nut")
        cls.globals = read("ai/OpexAI/globals_pre.nut")
        cls.air = read("ai/OpexAI/builder_air.nut")
        cls.projects = read("ai/OpexAI/projects.nut")
        cls.task_projects = read("ai/OpexAI/task_projects.nut")
        cls.main = read("ai/OpexAI/main.nut")
        cls.analyse = read("sweeps/analyse_c78_etape2.py")
        cls.diag = read("sweeps/diag_c78_lines_vs_aaa.py")
        cls.monthly = read("sweeps/diag_1v1_shared_monthly.py")

    def test_setting_is_wired_default_off(self):
        setting = self.info[self.info.index('name = "c83_fixes"') : self.info.index('name = "c83_fixes"') + 500]
        self.assertIn("easy_value = 0", setting)
        self.assertIn("medium_value = 0", setting)
        self.assertIn("hard_value = 0", setting)
        self.assertIn("custom_value = 0", setting)
        self.assertIn("flags = AICONFIG_BOOLEAN", setting)
        self.assertIn("C83_FIXES <- false;", self.globals)
        self.assertIn(
            'C83_FIXES = AIController.GetSetting("c83_fixes") != 0;',
            self.settings,
        )
        self.assertEqual(self.info.count("AddSetting("), 82)
        self.assertIn("_c83SlotRace = null;", self.main)

    def test_watch_list_ranks_contestable_towns_only_when_enabled(self):
        watch = body(self.air, "function OpexAirC83WatchTowns(")
        self.assertIn("if (C83_FIXES) ownCounts = OpexAirOwnSlotTownCounts();", watch)
        self.assertIn("if (!OpexAirC83TownContestable(town, ownCounts)) continue;", watch)
        self.assertIn("} else if (pop < AIR_EARLY_SLOT_MIN_POP) continue;", watch)
        self.assertIn("if (best.len() > AIR_C83_TARGET_TOWNS) best.pop();", watch)
        self.assertNotIn("OpexAirSortedTowns", watch)

        contestable = body(self.air, "function OpexAirC83TownContestable(")
        self.assertIn("OpexAirLargeAirportMinPop()", contestable)
        self.assertIn("AITown.GetAllowedNoise(town.id) < 1", contestable)
        self.assertIn("town.id in ownCounts", contestable)

        floor = body(self.air, "function OpexAirLargeAirportMinPop(")
        self.assertIn("return 600;", floor)

        prepare = body(self.air, "function OpexAirPlansPrepare(")
        # Le second slot proactif (ville deja servie) garde la liste C83.1 adoptee :
        # le filtre « disputable, Opex absent » ne vaut que pour le watcher.
        self.assertNotIn("OpexAirC83TownContestable", prepare)
        self.assertIn("towns[c83i].pop >= AIR_EARLY_SLOT_MIN_POP", prepare)

    def test_race_stays_armed_until_enqueue_succeeds(self):
        legacy = body(self.task_projects, "function OpexAI::_c83WatchAirSlotTransitions(")
        self.assertIn("if (C83_FIXES) return OpexC83WatchAirSlots(this);", legacy)
        self.assertLess(
            legacy.index("this._c83SlotWatch.rawset(town.id, state);"),
            legacy.index("if (state != 1 || previous == 1) continue;"),
        )
        self.assertIn('previous == 11 || previous == 2', legacy)
        self.assertIn("C78_SLOT_INTERCEPT_PROBE", legacy)

        one = body(self.task_projects, "function OpexC83WatchOneTown(")
        enq = one.index('ai._c77EnqueueEntity(["air"], "town", townId, true, "c83_slot_race")')
        receipt = one.index("ai._c83SlotRace.rawset(townId, today);")
        self.assertLess(enq, receipt)
        self.assertIn("OpexAirC83FundedRaceCoversTown", one)
        self.assertIn("action=already_funded", one)
        self.assertIn("action=coalesced", one)
        self.assertIn("action=rearm_capped", one)
        self.assertIn("action=enqueue_failed", one)
        self.assertIn("rearmDays", one)
        self.assertIn('ai._reactiveQueue.has(raceKey)', one)

        slots = body(self.task_projects, "function OpexC83WatchAirSlots(")
        self.assertIn("local rearmDays = 365;", slots)
        self.assertIn("OpexC83WatchDroppedTown", slots)

        funded = body(self.task_projects, "function OpexAirC83FundedRaceCoversTown(")
        self.assertIn("OpexAirBatchPlanStillLive(plan, lines)", funded)
        self.assertIn("OpexAirSlotTownId(plan.siteA.anchor)", funded)
        self.assertIn("OpexAirSlotTownId(plan.siteB.anchor)", funded)
        self.assertIn("!reuseA", funded)
        self.assertIn("!reuseB", funded)

        closure = body(self.task_projects, "function OpexC83LogSlotClosure(")
        self.assertIn("if (!C78_SLOT_INTERCEPT_PROBE || remaining != 0) return;", closure)
        self.assertIn("previous != 11", closure)
        self.assertIn("previous != 2", closure)
        self.assertIn('fields += " jump=1";', closure)
        self.assertIn("ownCount >= 2", closure)

    def test_slot_town_helper_is_shared(self):
        helper = body(self.air, "function OpexAirSlotTownId(")
        self.assertIn("AITile.GetClosestTown(anchor)", helper)
        self.assertNotIn("AIAirport.GetNearestTown", helper)
        self.assertNotIn("AIStation.GetNearestTown", helper)

        early = body(self.projects, "function OpexEarlySlotSelectionState(")
        defensive = body(self.projects, "function OpexDefensiveSlotSelectionState(")
        for state in (early, defensive):
            self.assertIn("if (C83_FIXES)", state)
            self.assertIn("OpexAirSlotTownId(AIStation.GetLocation(st))", state)
            self.assertIn("AIStation.GetNearestTown(st)", state)

        still = body(self.air, "function OpexAirSiteStillBuildable(")
        self.assertIn("if (C83_FIXES)", still)
        self.assertIn("OpexAirSlotTownId(site.anchor)", still)
        self.assertIn('("c83SlotTown" in site)', still)
        self.assertIn("AIAirport.GetNearestTown(site.anchor, airport.type) != site.town.id", still)

        find = body(self.air, "function OpexAirFindSite(")
        self.assertIn("AITile.GetClosestTown(anchor) != requiredSlotTownId", find)
        self.assertIn("C83_FIXES && requiredSlotTownId < 0 && OpexAirSlotTownId(anchor) != town.id", find)
        self.assertIn("C83_FIXES && OpexAirSlotTownId(cachedAnchor) != town.id", find)

        sites = body(self.air, "function OpexAirPlansFindSites(")
        self.assertIn("c83RequiredSlotTown = towns[i].id", sites)
        self.assertIn("site.c83SlotTown <- c83RequiredSlotTown", sites)
        self.assertIn("sites[a].town.pop", body(self.air, "function OpexAirPlansNewPairs("))

    def test_dead_pairs_never_enter_best_when_enabled(self):
        linked = body(self.air, "function OpexAirTownCentersLinked(")
        self.assertIn("line.originA == tileA && line.originB == tileB", linked)
        self.assertIn("line.originA == tileB && line.originB == tileA", linked)

        pairs = body(self.air, "function OpexAirPlansNewPairs(")
        hubs = body(self.air, "function OpexAirPlansHubToSite(")
        for block in (pairs, hubs):
            self.assertIn("if (C83_FIXES && OpexAirTownCentersLinked(", block)
            self.assertIn('OpexC73RecordRejection("air", "batch_plan_dead", 1)', block)

        filt = body(self.projects, "function OpexFilterAirAlternativesStillValid(")
        self.assertIn("C83_FIXES && lines != null && !OpexAirBatchPlanStillLive(plan, lines)", filt)
        self.assertIn("lines = null", filt)
        self.assertIn("OpexFilterAirAlternativesStillValid(alternatives, abandonedPairs, lines)",
                      body(self.projects, "function OpexReselectProjects("))
        self.assertIn("OpexFilterAirAlternativesStillValid(alternatives, abandonedPairs, lines)",
                      body(self.projects, "function OpexBuildProjects("))
        self.assertIn("OpexFilterAirAlternativesStillValid(alternatives, abandonedPairs, lines)",
                      body(self.projects, "function OpexIncrementalUpdateProjects("))

    def test_no_site_outcomes_are_log_only(self):
        sites = body(self.air, "function OpexAirPlansFindSites(")
        self.assertIn('OpexC73RecordRejection("air", "no_site", 1)', sites)
        self.assertIn('local c78Outcome = "no_site_terrain";', sites)
        self.assertIn('c78Outcome = "no_site_slot";', sites)
        self.assertIn("if (c78Gen)", sites)
        note = body(self.air, "function OpexAirC78NoteNoSite(")
        self.assertIn("if (!C69_BOTTLENECK_PROBE || probes == null) return;", note)
        self.assertIn('OpexAirC78NoteNoSite(probes, "no_site_slot")',
                      body(self.air, "function OpexAirRememberTownStationLimit("))
        self.assertIn('OpexAirC78NoteNoSite(probes, "no_site_budget")',
                      body(self.air, "function OpexAirFindSite("))
        for outcome in ("no_site", "no_site_slot", "no_site_budget", "no_site_terrain"):
            self.assertIn(f'"{outcome}"', self.analyse)
        self.assertIn("outcome=no_site_slot", self.diag)
        self.assertIn("outcome=no_site\\n", self.diag)

    def test_targeted_site_scan_is_gated(self):
        sites = body(self.air, "function OpexAirPlansFindSites(")
        self.assertIn("if (C83_FIXES && targetTownId >= 0)", sites)
        self.assertIn("scanEnd = c83Scan + 1", sites)
        self.assertIn("for (local i = scanStart; i < scanEnd; i++)", sites)
        hubs = body(self.air, "function OpexAirPlansDiscoverHubs(")
        self.assertIn("hubScanEnd = c83Scan + 1", hubs)
        self.assertIn("i < hubScanEnd && sites.len() < AIR_HUB_NEW_SITE_POOL", hubs)

    def test_dead_rights_decoder_is_gone(self):
        self.assertNotIn("parse_c83_rights_events", self.monthly)
        self.assertNotIn("summarize_c83_exclusive_rights", self.monthly)
        self.assertNotIn("C83_RIGHTS", self.monthly)
        self.assertFalse((ROOT / "sweeps" / "test_c83_exclusive_rights_probe.py").exists())
        self.assertIn("def parse_c78_slot_events", self.monthly)


if __name__ == "__main__":
    unittest.main()
