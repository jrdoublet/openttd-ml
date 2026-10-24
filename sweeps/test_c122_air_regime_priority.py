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
    def test_remaining_diagnostics_are_default_off_and_loaded(self):
        self.assertIn("C122_AIR_REGIME_SHADOW <- false;", GLOBALS)
        self.assertIn("C122_AIR_THREAT_PROBE <- false;", GLOBALS)
        self.assertNotIn("C122_AIR_THREAT_RETRY", GLOBALS)
        self.assertIn(
            "C122_AIR_REGIME_SHADOW = OpexProbeEnabled(262144, 16);",
            SETTINGS,
        )
        self.assertIn("C122_AIR_THREAT_PROBE = OpexProbeEnabled(524288, 16);", SETTINGS)
        self.assertNotIn("C122_AIR_THREAT_RETRY", SETTINGS)
        for name in ("c122_air_regime_shadow", "c122_air_threat_probe", "c122_air_threat_retry"):
            self.assertNotIn(f'name = "{name}"', INFO)
        probe_pos = INFO.index('name = "probes"')
        self.assertIn("easy_value = 0", INFO[probe_pos:probe_pos + 950])

    def test_c122_reuses_locked_pressure_classifier_without_new_scan(self):
        pressure = body(
            PROJECTS,
            "function OpexC121PressureNewAccum",
            "/* C78 / course defensive",
        )
        self.assertIn(
            "if (C121_AIR_PROJECT_REALIZATION_ADAPTIVE || C122_AIR_REGIME_SHADOW)",
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
            "function OpexC122TraceShadow",
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
        # V157 conserve le parcours historique quand le shadow C122 est actif.
        self.assertIn("&& !(C122_AIR_REGIME_SHADOW && C121_AIR_PROJECT_REALIZATION_REGIME == 0)", insert)
        insert = insert[insert.index("  } else {\n    local projectC77Tier"):]
        defensive_at = insert.index("if (priorTier > projectTier) break;")
        regime_at = insert.index("OpexC122AirRegimeTier(project)")
        score_at = insert.index("local priorScore =")
        self.assertLess(defensive_at, regime_at)
        self.assertLess(defensive_at, score_at)
        self.assertLess(score_at, regime_at)
        self.assertIn("if (C122_AIR_REGIME_SHADOW", insert)
        self.assertIn("C121_AIR_PROJECT_REALIZATION_REGIME == 0", insert)
        self.assertIn("&& projectAir && priorAir", insert)
        self.assertIn("if (priorRegimeTier > projectRegimeTier && !economicKeepsPrior) {", insert)
        self.assertIn("else if (priorRegimeTier < projectRegimeTier && economicKeepsPrior)", insert)

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

        close = body(TASK_PROJECTS, "function OpexC122ThreatClose", "function OpexC122ThreatCancel")
        self.assertIn('competitor_monopoly', close)
        self.assertIn('opex_claimed', close)
        self.assertIn("today - watch.detected", close)
        self.assertIn("delete C122_AIR_THREAT_WATCH[townId]", close)

        c83_one = body(TASK_PROJECTS, "function OpexAI::_c83WatchAirSlotTransitions",
                       "function OpexAI::_recordPortfolioProjectBuilt")
        self.assertIn("OpexC122ThreatRegister(this, town.id, previous);", c83_one)
        self.assertIn("OpexC122ThreatRefreshFunded(this, town.id);", c83_one)
        self.assertIn("OpexC122ThreatClose(town.id, previous, ownPresent, ownCountForThreat);", c83_one)
        self.assertLess(c83_one.index("OpexC122ThreatRegister(this, town.id, previous);"),
                        c83_one.index("OpexC122ThreatRefreshFunded(this, town.id);"))
        # Active retry was not adopted: probe records attempts/outcomes only.
        self.assertNotIn("function OpexC122ThreatRetryUnbuildable", TASK_PROJECTS)
        self.assertNotIn("C122_AIR_THREAT_RETRY_COUNT++", TASK_PROJECTS)
        attempts = body(TASK_PROJECTS, "function OpexC122ThreatNoteAttempt",
                        "/* Trace rare, commune aux deux bras")
        self.assertIn('phase=attempt', attempts)
        self.assertIn('phase=outcome', attempts)
        self.assertIn("OpexC122ThreatProjectTowns", attempts)
        self.assertIn("OpexC122ThreatNoteAttempt(project, i, liveBuiltCount);", TASK_PROJECTS)
        self.assertIn("OpexC122ThreatNoteOutcome(project, i, attempt);", TASK_PROJECTS)

    def test_efficiency_has_no_separate_policy_branch(self):
        priority = body(
            PROJECTS,
            "function OpexC122AirRegimeTier",
            "function OpexC122TraceShadow",
        )
        self.assertIn("C121_AIR_PROJECT_REALIZATION_REGIME != 0", priority)
        self.assertNotIn("C121_AIR_PROJECT_REALIZATION_REGIME == 1", priority)
        self.assertNotIn("hubhub", priority)

    def test_economics_engine_and_build_paths_do_not_reference_c122(self):
        from_air = body(PROJECTS, "function OpexProjectFromAir", "function OpexProjectFromWater")
        score = body(PROJECTS, "function OpexProjectSelectionScore", "/* Insertion bornee et stable")
        realization = body(PROJECTS, "function OpexC121RealizationFactor", "function OpexC121RealizationSums")
        for block in (from_air, score, realization, AIR, TASK_AIR):
            self.assertNotIn("C122_AIR_REGIME_PRIORITY", block)
            self.assertNotIn("OpexC122AirRegimePriority", block)


if __name__ == "__main__":
    unittest.main()
