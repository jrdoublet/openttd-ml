"""Contrats de c83_preempt_open : une ville vide, defaut 0, chemin historique intact."""
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


class C83PreemptContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read("ai/OpexAI/info.nut")
        cls.settings = read("ai/OpexAI/settings.nut")
        cls.globals = read("ai/OpexAI/globals_pre.nut")
        cls.air = read("ai/OpexAI/builder_air.nut")
        cls.projects = read("ai/OpexAI/projects.nut")
        cls.task_projects = read("ai/OpexAI/task_projects.nut")
        cls.persist = read("ai/OpexAI/persist.nut")
        cls.main = read("ai/OpexAI/main.nut")

    def test_setting_is_wired_default_off(self):
        start = self.info.index('name = "c83_preempt_open"')
        setting = self.info[start:self.info.index("});", start)]
        self.assertIn("easy_value = 0", setting)
        self.assertIn("medium_value = 0", setting)
        self.assertIn("hard_value = 0", setting)
        self.assertIn("custom_value = 0", setting)
        self.assertIn("flags = AICONFIG_BOOLEAN", setting)
        self.assertIn("C83_PREEMPT_OPEN <- false;", self.globals)
        self.assertIn("C83_PREEMPT_TOWN <- -1;", self.globals)
        self.assertIn("C83_PREEMPT_STOPPED <- false;", self.globals)
        self.assertIn(
            'C83_PREEMPT_OPEN = AIController.GetSetting("c83_preempt_open") != 0;',
            self.settings,
        )
        self.assertEqual(self.info.count("AddSetting("), 82)
        self.assertIn("_c83PreemptRace = null;", self.main)
        self.assertIn("this._c83PreemptQueued = -1;", self.main)

    def test_floor_helper_follows_v93_only_for_preempt(self):
        floor = body(self.air, "function OpexAirLargeAirportMinPop(")
        self.assertIn("return 600;", floor)
        self.assertNotIn("V93_AIRPORT_NO_POP_FLOOR", floor)
        helper = body(self.air, "function OpexAirPreemptMinPop(")
        self.assertIn("if (V93_AIRPORT_NO_POP_FLOOR) return V93_AIRPORT_MIN_POP;", helper)
        self.assertIn("return OpexAirLargeAirportMinPop();", helper)
        pick = body(self.air, "function OpexAirPreemptPickTown(")
        self.assertIn("if (!C83_PREEMPT_OPEN || !OpexAirC83SlotSignalEnabled()", pick)
        self.assertIn("OpexAirPreemptMinPop()", pick)
        self.assertIn("AITown.GetAllowedNoise(town.id) != 2", pick)
        self.assertIn("town.id in ownCounts", pick)

    def test_one_target_stops_and_reuses_the_c83_enqueue_path(self):
        watch = body(self.task_projects, "function OpexC83PreemptWatch(")
        self.assertIn("if (!C83_PREEMPT_OPEN || C83_PREEMPT_STOPPED || !OpexAirC83SlotSignalEnabled()) return 0;", watch)
        self.assertIn("OpexAirOwnSlotTownCounts()", watch)
        self.assertIn("OpexAirPreemptPickTown(ai._catalog.towns, ownCounts)", watch)
        self.assertIn("OpexAirC83FundedRaceCoversTown(ai._projects, ai._lines, townId)", watch)
        self.assertIn("phase=c83_preempt_target", watch)
        self.assertIn("phase=c83_preempt_built", watch)
        self.assertIn("phase=c83_preempt_lost", watch)
        self.assertIn("C78_SLOT_INTERCEPT_PROBE", watch)
        self.assertIn("::C83_PREEMPT_STOPPED = true;", watch)
        self.assertIn('ai._reactiveQueue.has(raceKey)', watch)
        self.assertIn('action = "coalesced"', watch)
        self.assertIn('action = "rearm_capped"', watch)
        self.assertIn("if (C83_FIXES)", watch)
        self.assertIn("today - lastEnqueue < 365", watch)
        self.assertIn(
            'ai._c77EnqueueEntity(["air"], "town", townId, true, "c83_preempt")',
            watch,
        )
        legacy = body(self.task_projects, "function OpexAI::_c83WatchAirSlotTransitions(")
        self.assertIn("if (C83_PREEMPT_OPEN) this._c83PreemptEnqueued = OpexC83PreemptWatch(this);", legacy)
        self.assertIn("if (C83_FIXES) return OpexC83WatchAirSlots(this);", legacy)
        attempt = body(self.task_projects, "function OpexAI::_tryBuildProjects(")
        self.assertLess(
            attempt.index("this._c83WatchAirSlotTransitions();"),
            attempt.index("OpexPromoteLiveDefensiveAir(this._projects, OpexAvailableCapital());"),
        )
        self.assertIn("if (C83_PREEMPT_OPEN && this._c83PreemptEnqueued > 0)", attempt)

    def test_priority_stays_behind_the_profit_test_and_uses_the_slot_town(self):
        priority = body(self.projects, "function OpexProjectDefensiveAirPriority(")
        self.assertLess(priority.index("project.profitAnnual <= 0"), priority.index("C83_PREEMPT_OPEN"))
        self.assertLess(
            priority.index("if (competitorClaims > 0) return 2;"),
            priority.index('("preemptClaims" in project) && project.preemptClaims > 0) return 2;'),
        )
        self.assertIn("if (ownClaims > 0) return 1;", priority)
        refresh = body(self.projects, "function OpexProjectRefreshDefensiveSlot(")
        gate = refresh.index("if (C83_PREEMPT_OPEN && C83_PREEMPT_TOWN >= 0)")
        self.assertIn("!reuseA", refresh[gate:])
        self.assertIn("!reuseB", refresh[gate:])
        self.assertIn("OpexAirSlotTownId(plan.siteA.anchor) == C83_PREEMPT_TOWN", refresh[gate:])
        self.assertIn("OpexAirSlotTownId(plan.siteB.anchor) == C83_PREEMPT_TOWN", refresh[gate:])
        find = body(self.air, "function OpexAirFindSite(")
        self.assertIn("AITile.GetClosestTown(anchor) != requiredSlotTownId", find)
        plans = body(self.projects, "function OpexGenerateModeProjects(")
        self.assertIn('entityKind == "town" ? entityId : -1', plans)

    def test_save_adds_fields_only_when_the_setting_is_on(self):
        save = body(self.persist, "function OpexAI::Save(")
        self.assertEqual(save.count("if (C83_PREEMPT_OPEN) OpexSaveC83Preempt("), 2)
        helper = body(self.persist, "function OpexSaveC83Preempt(")
        self.assertIn("if (!C83_PREEMPT_OPEN || saveObj == null || ai == null) return;", helper)
        self.assertIn("saveObj.c83PreemptTown <- C83_PREEMPT_TOWN;", helper)
        self.assertIn("saveObj.c83PreemptStopped <- C83_PREEMPT_STOPPED ? 1 : 0;", helper)
        load = body(self.persist, "function OpexAI::Load(")
        self.assertIn('if ("c83PreemptTown" in data)', load)
        self.assertNotIn("data.c83PreemptTown;", load.split('if ("c83PreemptTown" in data)', 1)[0])
        reconcile = body(self.persist, "function OpexAI::_reconcileAfterLoad(")
        self.assertIn("if (C83_PREEMPT_OPEN)", reconcile)
        self.assertIn("::C83_PREEMPT_TOWN = this._reloadC83PreemptTown;", reconcile)
        self.assertIn("::C83_PREEMPT_STOPPED = this._reloadC83PreemptStopped != 0;", reconcile)


if __name__ == "__main__":
    unittest.main()
