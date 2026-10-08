"""Contrats statiques de v133_air_build_retry. Aucune partie."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
GLOBALS = (AI / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (AI / "info.nut").read_text(encoding="utf-8")
SETTINGS = (AI / "settings.nut").read_text(encoding="utf-8")
TOWNS = (AI / "air_towns.nut").read_text(encoding="utf-8")
PLANNING = (AI / "air_planning.nut").read_text(encoding="utf-8")
SITES = (AI / "air_sites.nut").read_text(encoding="utf-8")
TASK_AIR = (AI / "task_air.nut").read_text(encoding="utf-8")
TASK_PROJECTS = (AI / "task_projects.nut").read_text(encoding="utf-8")
PERSIST = (AI / "persist.nut").read_text(encoding="utf-8")
REPAIR = (AI / "air_c83_repair.nut").read_text(encoding="utf-8")

RESERVED = ("resume", "clone", "base", "parent", "yield", "static", "enum", "const")


def _body(source, start_token, end_token=None):
    start = source.index(start_token)
    if end_token is None:
        return source[start:]
    end = source.index(end_token, start)
    return source[start:end]


class V133AirBuildRetryTests(unittest.TestCase):
    def test_setting_defaults_off_and_loads_once(self):
        self.assertIn("V133_AIR_BUILD_RETRY <- false;", GLOBALS)
        self.assertIn("V133_AIR_QUARANTINE <- {};", GLOBALS)
        self.assertIn("V133_AIR_BATCH_FAILED <- {};", GLOBALS)
        self.assertEqual(INFO.count('name = "v133_air_build_retry"'), 1)
        start = INFO.index('name = "v133_air_build_retry"')
        block = INFO[start:INFO.index("});", start)]
        for token in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(token, block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertEqual(SETTINGS.count('AIController.GetSetting("v133_air_build_retry")'), 1)
        self.assertIn(
            'V133_AIR_BUILD_RETRY = AIController.GetSetting("v133_air_build_retry") != 0;',
            SETTINGS,
        )

    def test_quarantine_lasts_730_days_and_logs(self):
        body = _body(TOWNS, "function OpexV133OnAirSiteFailed", "function OpexV133SalvageDeadPlan")
        self.assertIn("AIDate.GetCurrentDate() + 730", body)
        self.assertIn("V133_AIR_QUARANTINE.rawset(townId, untilDate);", body)
        self.assertIn(
            '"V133_QUARANTINE town=" + townId + " reason=" + reason + " until=" + untilDate',
            body,
        )
        self.assertIn("OpexV133Log(", body)
        log_body = _body(TOWNS, "function OpexV133Log(", "function OpexV133AirTownQuarantined")
        self.assertIn("AILog.Info(message);", log_body)
        self.assertIn('OpexC56TaskLog("V133", "air", "-", message);', log_body)
        skip = _body(TOWNS, "function OpexV133LogAirSkip", "function OpexV133AirTownSkip")
        self.assertIn('"V133_SKIP town=" + townId', skip)
        expiry = _body(TOWNS, "function OpexV133AirTownQuarantined", "function OpexV133TownIdOf")
        self.assertIn("delete V133_AIR_QUARANTINE[townId];", expiry)
        self.assertIn("AIDate.GetCurrentDate() >= untilDate", expiry)

    def test_failure_reasons_cover_authority_terrain_footprint_and_station_cap(self):
        body = _body(TOWNS, "function OpexV133AirBuildReason", "function OpexV133AirPlanUsesTown")
        self.assertIn("ERR_LOCAL_AUTHORITY_REFUSES", body)
        self.assertIn('return "authority"', body)
        self.assertIn("ERR_STATION_TOO_MANY_STATIONS_IN_TOWN", body)
        self.assertIn('return "station_limit"', body)
        self.assertIn("ERR_FLAT_LAND_REQUIRED", body)
        self.assertIn("ERR_LAND_SLOPED_WRONG", body)
        self.assertIn('return "terrain"', body)
        self.assertIn("invalid airport footprint", body)
        self.assertIn('return "footprint"', body)
        self.assertIn("ERR_AREA_NOT_CLEAR", body)
        self.assertIn("ERR_SITE_UNSUITABLE", body)
        self.assertIn('return "unbuildable"', body)
        self.assertIn('errorText.find("recovery")', body)
        self.assertIn("return null", body)

    def test_generation_skips_quarantine_only_when_flag_is_on(self):
        find_sites = _body(PLANNING, "function OpexAirPlansFindSites", "function OpexAirPlansNewPairs")
        new_pairs = _body(PLANNING, "function OpexAirPlansNewPairs", "function OpexAirPlansDiscoverHubs")
        discover = _body(PLANNING, "function OpexAirPlansDiscoverHubs", "function OpexAirPlansHubToSite")
        hub_site = _body(PLANNING, "function OpexAirPlansHubToSite", "function OpexAirPlansHubToHub")
        hub_hub = _body(PLANNING, "function OpexAirPlansHubToHub", "function OpexAirPlans(")
        for body in (find_sites, new_pairs, discover, hub_site, hub_hub, REPAIR):
            self.assertIn("V133_AIR_BUILD_RETRY", body)
            self.assertIn("OpexV133AirTownSkip(", body)
        self.assertIn("ctx.v133Skip <- {};", TOWNS)
        # Le helper n'est pas appele si le drapeau est faux.
        for body in (find_sites, discover, REPAIR):
            self.assertIn("V133_AIR_BUILD_RETRY && OpexV133AirTownSkip(", body)
        for body in (new_pairs, hub_site, hub_hub):
            self.assertIn("if (V133_AIR_BUILD_RETRY) {", body)

    def test_build_failure_hooks_are_guarded(self):
        build = _body(TASK_AIR, "function OpexAI::_tryBuildAirProject", "function OpexAirFleetRefusal")
        self.assertIn("if (!OpexAirBatchPlanStillLive(plan, this._lines))", build)
        self.assertIn('reason = "siteA_unbuildable"', build)
        self.assertIn('reason = "siteB_unbuildable"', build)
        self.assertIn("if (!result.ok)", build)
        self.assertEqual(build.count("if (V133_AIR_BUILD_RETRY)"), 3)
        self.assertEqual(build.count("OpexV133NoteUnbuildableEndpoint("), 2)
        self.assertEqual(build.count("OpexV133NoteBuildFailure("), 1)
        sites = _body(SITES, "function OpexAirSiteStillBuildable")
        self.assertIn("if (V133_AIR_BUILD_RETRY) V133_AIR_LAST_SITE_ERROR = 0;", sites)
        self.assertIn("if (V133_AIR_BUILD_RETRY) V133_AIR_LAST_SITE_ERROR = error;", sites)

    def test_batch_salvage_keeps_pairs_that_do_not_use_the_failed_town(self):
        uses = _body(TOWNS, "function OpexV133AirPlanUsesTown", "function OpexV133CountBatchSalvage")
        self.assertIn('("reuseA" in plan) && plan.reuseA', uses)
        self.assertIn('("reuseB" in plan) && plan.reuseB', uses)
        count = _body(TOWNS, "function OpexV133CountBatchSalvage", "function OpexV133LogBatchSalvage")
        self.assertIn("dropped++", count)
        self.assertIn("kept++", count)
        self.assertIn("OpexV133AirPlanUsesTown(other.payload, townA)", count)
        self.assertIn("OpexV133AirPlanUsesTown(other.payload, townB)", count)
        self.assertIn("tally.kept <- kept;", count)
        self.assertIn("tally.dropped <- dropped;", count)
        log = _body(TOWNS, "function OpexV133LogBatchSalvage", "function OpexV133OnAirSiteFailed")
        self.assertIn('"V133_BATCH_SALVAGE kept=" + tally.kept + " dropped=" + tally.dropped', log)
        projects = _body(TASK_PROJECTS, "function OpexAI::_tryBuildProjects", "function OpexAI::_rebuildProjects")
        self.assertIn("if (V133_AIR_BUILD_RETRY) {\n    V133_AIR_BATCH_FAILED = {};\n", projects.replace("  if (", "if (", 1))
        self.assertIn("OpexV133AirPlanBlocked(project.payload)", projects)
        self.assertIn("!OpexAirBatchPlanStillLive(project.payload, this._lines)", projects)
        # Le salvage d'un plan mort ne court-circuite pas le rejet historique.
        dead = projects.index("OpexV133SalvageDeadPlan(")
        still = projects.index("!OpexAirBatchPlanStillLive(project.payload, this._lines)", dead - 200)
        cont = projects.index("continue;", dead)
        self.assertLess(still, dead)
        self.assertLess(dead, cont)

    def test_save_adds_the_key_only_when_the_flag_is_on(self):
        save = _body(TOWNS, "function OpexV133SaveQuarantine", "function OpexV133LoadQuarantine")
        self.assertIn("if (!V133_AIR_BUILD_RETRY || V133_AIR_QUARANTINE.len() == 0", save)
        self.assertIn("target.v133AirQuarantine <- flat;", save)
        self.assertEqual(PERSIST.count("OpexV133SaveQuarantine("), 2)
        self.assertEqual(PERSIST.count("if (V133_AIR_BUILD_RETRY) OpexV133SaveQuarantine("), 2)
        load = _body(TOWNS, "function OpexV133LoadQuarantine")
        self.assertIn('!("v133AirQuarantine" in data)', load)
        self.assertIn("V133_AIR_QUARANTINE.rawset(flat[i], flat[i + 1]);", load)
        self.assertIn("OpexV133LoadQuarantine(data);", PERSIST)

    def test_new_helpers_do_not_use_reserved_identifiers(self):
        body = TOWNS[TOWNS.index("function OpexV133Log("):]
        # Retirer chaines et commentaires pour ne juger que les identifiants.
        stripped = re.sub(r'"[^"\n]*"', '""', body)
        stripped = re.sub(r"/\*.*?\*/", "", stripped, flags=re.S)
        for word in RESERVED:
            self.assertIsNone(
                re.search(r"\b" + word + r"\b", stripped),
                word,
            )


if __name__ == "__main__":
    unittest.main()
