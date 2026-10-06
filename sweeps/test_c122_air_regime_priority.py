from pathlib import Path
import unittest
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air
from opex_projects_source import read_projects_source


ROOT = Path(__file__).resolve().parents[1]
PROJECTS = read_projects_source()
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
AIR = read_builder_air()
TASK_AIR = (ROOT / "ai" / "OpexAI" / "task_air.nut").read_text(encoding="utf-8")
TASK_PROJECTS = (ROOT / "ai" / "OpexAI" / "task_projects.nut").read_text(encoding="utf-8")


def body(text: str, start: str, end: str) -> str:
    i = text.index(start)
    return text[i:text.index(end, i)]


class TestC122AirRegimePriority(unittest.TestCase):
    def test_toggle_is_default_off_and_loaded(self):
        self.assertIn("C122_AIR_REGIME_PRIORITY <- false;", GLOBALS)
        self.assertIn("C122_AIR_REGIME_SHADOW <- false;", GLOBALS)
        self.assertIn("C122_AIR_THREAT_PROBE <- false;", GLOBALS)
        self.assertIn("C122_AIR_THREAT_RETRY <- false;", GLOBALS)
        self.assertIn(
            'C122_AIR_REGIME_PRIORITY = AIController.GetSetting("c122_air_regime_priority") != 0;',
            SETTINGS,
        )
        self.assertIn(
            'C122_AIR_REGIME_SHADOW = AIController.GetSetting("c122_air_regime_shadow") != 0;',
            SETTINGS,
        )
        self.assertIn('C122_AIR_THREAT_RETRY = AIController.GetSetting("c122_air_threat_retry") != 0;', SETTINGS)
        self.assertIn('C122_AIR_THREAT_PROBE = AIController.GetSetting("c122_air_threat_probe") != 0 || C122_AIR_THREAT_RETRY;', SETTINGS)
        pos = INFO.index('name = "c122_air_regime_priority"')
        block = INFO[pos:pos + 850]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, block)
        shadow_pos = INFO.index('name = "c122_air_regime_shadow"')
        shadow_block = INFO[shadow_pos:shadow_pos + 700]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, shadow_block)
        threat_pos = INFO.index('name = "c122_air_threat_probe"')
        threat_block = INFO[threat_pos:threat_pos + 850]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, threat_block)
        retry_pos = INFO.index('name = "c122_air_threat_retry"')
        retry_block = INFO[retry_pos:retry_pos + 900]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, retry_block)

    def test_c122_reuses_locked_pressure_classifier_without_new_scan(self):
        pressure = body(
            PROJECTS,
            "function OpexC121PressureNewAccum",
            "/* C78 / course defensive",
        )
        self.assertIn("C122_AIR_REGIME_PRIORITY", pressure)
        self.assertIn(
            "if (C121_AIR_PROJECT_REALIZATION_ADAPTIVE || C122_AIR_REGIME_PRIORITY",
            pressure,
        )
        self.assertIn("|| C122_AIR_REGIME_SHADOW", pressure)
        self.assertIn("state.slotRemaining", pressure)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_REGIME = efficiency ? 1 : 0", pressure)
        self.assertNotIn("AITownList", pressure)
        self.assertNotIn("AIStationList", pressure)
        self.assertNotIn("GetAllowedNoise", pressure)

    def test_priority_is_existing_territorial_annotation_only_and_race_only(self):
        priority = body(
            PROJECTS,
            "function OpexC122AirRegimeTier",
            "function OpexC122TracePromotion",
        )
        self.assertIn("C121_AIR_PROJECT_REALIZATION_REGIME != 0", priority)
        self.assertIn('("defensiveNewTownClaims" in project)', priority)
        self.assertIn("newTownClaims > 0", priority)
        self.assertIn("return 1;", priority)
        self.assertNotIn('arm == "newpair"', priority)
        self.assertNotIn('arm == "hubsite"', priority)
        for forbidden in (
            "profitAnnual =",
            "revenueAnnual =",
            "capital =",
            "roi =",
            "fundScore =",
            "decisionScore",
            "AIEngineList",
            "AITownList",
            "AITileList",
            "OpexAirFindSite",
            "OpexAirPlans(",
            "OpexC118",
            "OpexC120",
        ):
            self.assertNotIn(forbidden, priority)

    def test_regime_key_only_compares_air_to_air_after_defensive_tier(self):
        insert = body(
            PROJECTS,
            "function OpexProjectInsertDefensive",
            "function OpexPromoteLiveDefensiveAir",
        )
        defensive_at = insert.index("if (priorTier > projectTier) break;")
        regime_at = insert.index("OpexC122AirRegimeTier(project)")
        score_at = insert.index("local priorScore =")
        self.assertLess(defensive_at, regime_at)
        self.assertLess(defensive_at, score_at)
        self.assertLess(score_at, regime_at)
        self.assertIn("C122_AIR_REGIME_PRIORITY || C122_AIR_REGIME_SHADOW", insert)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_REGIME == 0", insert)
        self.assertIn("&& projectAir && priorAir", insert)
        self.assertIn("if (priorRegimeTier > projectRegimeTier) {", insert)
        self.assertIn("if (priorRegimeTier < projectRegimeTier)", insert)

    def test_c77_stays_primary_and_c122_logs_only_real_promotions(self):
        insert = body(
            PROJECTS,
            "function OpexProjectInsertDefensive",
            "function OpexPromoteLiveDefensiveAir",
        )
        c77_at = insert.index("if (priorTier > projectTier) break;")
        c122_at = insert.index("OpexC122AirRegimeTier(project)")
        promote_at = insert.index("OpexC122TracePromotion(")
        score_at = insert.index("local priorScore =")
        self.assertLess(c77_at, c122_at)
        self.assertLess(score_at, c122_at)
        self.assertLess(c122_at, promote_at)
        self.assertIn('OpexC122TracePromotion("prior"', insert)
        self.assertIn('OpexC122TracePromotion("project"', insert)
        self.assertIn("economicKeepsPrior", insert)
        self.assertNotIn("C78_SLOT_INTERCEPT_PROBE", insert)

        trace = body(
            PROJECTS,
            "function OpexC122TracePromotion",
            "/* Villes de slot",
        )
        self.assertNotIn("C78_SLOT_INTERCEPT_PROBE", trace)
        self.assertIn('AILog.Info("C122_PROMOTE', trace)
        self.assertIn('field != "fundScore"', trace)
        self.assertIn("C122_AIR_PROMOTION_COUNT", trace)
        self.assertIn("C122_AIR_PROMOTION_LOG_MAX", trace)
        self.assertIn('reason=new_opex_slot_town', trace)
        for field in (
            "projectC77Tier",
            "priorC77Tier",
            "earlySlotClaims",
            "defensiveNewTownClaims",
            "defensiveCompetitorClaims",
            "defensiveOwnClaims",
            "preemptClaims",
            "project[field]",
            "prior[field]",
        ):
            self.assertIn(field, trace)

        shadow = body(
            PROJECTS,
            "function OpexC122TraceShadow",
            "/* C122.3 diagnostic",
        )
        self.assertIn('AILog.Info("C122_SHADOW', shadow)
        self.assertIn("!C122_AIR_REGIME_SHADOW", shadow)
        self.assertIn("C122_AIR_REGIME_PRIORITY", shadow)

    def test_new_town_annotation_reuses_defensive_state_without_new_scan(self):
        refresh = body(PROJECTS, "function OpexProjectRefreshDefensiveSlot", "function OpexProjectDefensiveAirPriority")
        self.assertIn("local newTownClaims = 0;", refresh)
        self.assertIn("C121_AIR_PRESSURE_PROBE || C122_AIR_REGIME_PRIORITY", refresh)
        self.assertIn("|| C122_AIR_REGIME_SHADOW", refresh)
        self.assertIn("local newTowns = observeNewTowns ? {} : null;", refresh)
        self.assertIn("!(townA in state.servedTowns)", refresh)
        self.assertIn("!(townB in state.servedTowns)", refresh)
        self.assertIn("if (observeNewTowns) {", refresh)
        self.assertIn('OpexProjectSetEarlySlotField(project, "defensiveNewTownClaims", newTownClaims);', refresh)
        for forbidden in ("AIStationList", "AITownList", "AITileList", "OpexAirFindSite", "AIEngineList"):
            self.assertNotIn(forbidden, refresh)

    def test_passive_exposure_probe_never_enables_c122_priority(self):
        probe = body(PROJECTS, "function OpexC122ProbeExposure", "/* Villes de slot")
        self.assertIn("!C121_AIR_PRESSURE_PROBE", probe)
        self.assertNotIn("return OpexC122AirRegimePriority", probe)
        self.assertIn('("defensiveNewTownClaims" in project)', probe)
        self.assertIn("potentialInversions", probe)
        self.assertIn("same_tier_blockers", probe)
        self.assertIn('AILog.Info("C122_EXPOSURE', probe)
        for forbidden in ("AITownList", "AIStationList", "AITileList", "OpexAirFindSite", "AIEngineList"):
            self.assertNotIn(forbidden, probe)

        select = body(PROJECTS, "function OpexProjectSelectAffordable", "/* Early-slot")
        probe_at = select.index("OpexC122ProbeExposure(affordable);")
        reorder_at = select.index("OpexC120ReorderAffordableAir(affordable);")
        self.assertLess(probe_at, reorder_at)

    def test_exact_shadow_compares_without_reordering(self):
        insert = body(
            PROJECTS,
            "function OpexProjectInsertDefensive",
            "function OpexPromoteLiveDefensiveAir",
        )
        self.assertIn("C122_AIR_REGIME_PRIORITY || C122_AIR_REGIME_SHADOW", insert)
        self.assertIn("C122_AIR_REGIME_SHADOW && !C122_AIR_REGIME_PRIORITY", insert)
        self.assertIn('OpexC122TraceShadow("prior"', insert)
        self.assertIn('OpexC122TraceShadow("project"', insert)
        shadow_branch = insert[insert.index("if (C122_AIR_REGIME_SHADOW && !C122_AIR_REGIME_PRIORITY)"):]
        shadow_branch = shadow_branch[:shadow_branch.index("} else if (priorRegimeTier > projectRegimeTier)")]
        self.assertNotIn("pos--;", shadow_branch)
        self.assertNotIn("break;", shadow_branch)

    def test_c122_4_threat_probe_is_local_passive_and_tracks_real_slot_closure(self):
        match = body(
            TASK_PROJECTS,
            "function OpexC122ThreatFundedMatch",
            "function OpexC122ThreatLog",
        )
        self.assertIn("projects.best", match)
        self.assertIn("PROJECT_TOP_K", match)
        self.assertIn("OpexAirBatchPlanStillLive", match)
        self.assertIn("OpexAirSlotTownId(plan.siteA.anchor)", match)
        self.assertIn("OpexAirSlotTownId(plan.siteB.anchor)", match)
        for forbidden in ("AITownList", "AIStationList", "AITileList", "AIEngineList", "OpexAirFindSite"):
            self.assertNotIn(forbidden, match)

        register = body(
            TASK_PROJECTS,
            "function OpexC122ThreatRegister",
            "function OpexC122ThreatClose",
        )
        self.assertIn("OpexC122ThreatFundedMatch", register)
        self.assertIn("rank > 0", register)
        self.assertIn("blockerMode", register)
        self.assertIn('phase=detected', register)
        self.assertIn("function OpexC122ThreatRefreshFunded", register)
        self.assertIn('phase=funded', register)
        self.assertIn("if (watch.funded) return;", register)

        close = body(
            TASK_PROJECTS,
            "function OpexC122ThreatClose",
            "function OpexC83LogSlotClosure",
        )
        self.assertIn('competitor_monopoly', close)
        self.assertIn('opex_claimed', close)
        self.assertIn("today - watch.detected", close)
        self.assertIn("delete C122_AIR_THREAT_WATCH[townId]", close)

        c83_one = body(
            TASK_PROJECTS,
            "function OpexC83WatchOneTown",
            "function OpexC83WatchAirSlots",
        )
        self.assertIn("OpexC122ThreatRegister(ai, townId, previous);", c83_one)
        self.assertIn("OpexC122ThreatRefreshFunded(ai, townId);", c83_one)
        self.assertLess(
            c83_one.index("OpexC122ThreatRegister(ai, townId, previous);"),
            c83_one.index("OpexAirC83FundedRaceCoversTown"),
        )

        closure = body(
            TASK_PROJECTS,
            "function OpexC83LogSlotClosure",
            "function OpexC83WatchDroppedTown",
        )
        self.assertIn("OpexC122ThreatClose(townId, previous, ownPresent, ownCount);", closure)
        self.assertIn("if (!C78_SLOT_INTERCEPT_PROBE) return;", closure)

        retry = body(
            TASK_PROJECTS,
            "function OpexC122ThreatRetryUnbuildable",
            "function OpexC83LogSlotClosure",
        )
        self.assertIn('discard.reason == "siteA_unbuildable"', retry)
        self.assertIn('discard.reason == "siteB_unbuildable"', retry)
        self.assertIn('ai._c77EnqueueEntity(["air"], "town", townId, true, "c122_threat_retry")', retry)
        self.assertIn("watch.retries >= 1", retry)
        self.assertIn("C122_AIR_THREAT_RETRY_COUNT++", retry)
        for forbidden in ("AITownList", "AIStationList", "AITileList", "AIEngineList", "OpexAirFindSite"):
            self.assertNotIn(forbidden, retry)

        attempts = body(
            TASK_PROJECTS,
            "function OpexC122ThreatNoteAttempt",
            "function OpexC83LogSlotClosure",
        )
        self.assertIn('phase=attempt', attempts)
        self.assertIn('phase=outcome', attempts)
        self.assertIn("OpexC122ThreatProjectTowns", attempts)

    def test_efficiency_has_no_separate_policy_branch(self):
        priority = body(
            PROJECTS,
            "function OpexC122AirRegimeTier",
            "function OpexC122TracePromotion",
        )
        self.assertIn("C121_AIR_PROJECT_REALIZATION_REGIME != 0", priority)
        self.assertNotIn("C121_AIR_PROJECT_REALIZATION_REGIME == 1", priority)
        self.assertNotIn("hubhub", priority)

    def test_economics_engine_and_build_paths_do_not_reference_c122(self):
        from_air = body(PROJECTS, "function OpexProjectFromAir", "function OpexProjectFromWater")
        score = body(PROJECTS, "function OpexProjectSelectionScore", "/* V88 test")
        realization = body(PROJECTS, "function OpexC121RealizationFactor", "function OpexC121EngineDecisionRealizationFactor")
        for block in (from_air, score, realization, AIR, TASK_AIR):
            self.assertNotIn("C122_AIR_REGIME_PRIORITY", block)
            self.assertNotIn("OpexC122AirRegimePriority", block)


if __name__ == "__main__":
    unittest.main()
