"""Contrats statiques du catalogue AIR incremental (sans partie OpenTTD)."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from campaign_freeze import parse_ai_settings
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air
from opex_projects_source import read_projects_source

AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def squirrel_code(text):
    """Mask literals/comments, not identifiers; preserve line boundaries."""
    return re.sub(r'@"(?:""|[^"])*"|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/',
                  lambda m: re.sub(r'[^\n]', ' ', m.group()), text, flags=re.S)


class TestC121CatalogIncremental(unittest.TestCase):
    def test_settings_default_off_and_c121_gate(self):
        defaults = parse_ai_settings(AI / "info.nut")
        self.assertEqual(defaults["c121_catalog_incremental"], 0)
        # Decision utilisateur du 2026-10-02 : 1 par defaut, inerte hors C121 incremental.
        self.assertEqual(defaults["c121_catalog_air_first_year"], 1)
        settings = source("settings.nut")
        self.assertIn('C121_CATALOG_INCREMENTAL = C121_AIR_ECONOMICS\n', settings)
        self.assertIn('AIController.GetSetting("c121_catalog_incremental")', settings)
        self.assertIn('C121_CATALOG_AIR_FIRST_YEAR = C121_CATALOG_INCREMENTAL\n', settings)

    def test_default_chooses_original_function_without_cache_call(self):
        air = read_builder_air()
        self.assertEqual(air.count("? OpexC121CatalogChoice(catalog, plan,"), 3)
        self.assertEqual(air.count(": OpexC121ChooseRoutePlane(catalog, plan,"), 3)
        self.assertIn("if (C121_CATALOG_INCREMENTAL)", source("catalog.nut"))
        self.assertIn("if (C121_CATALOG_INCREMENTAL)", source("orchestrator.nut"))

    def test_invalidation_and_transient_cache(self):
        self.assertIn('reason == "town_founded"', source("events.nut"))
        self.assertIn('reason == "engine_available"', source("events.nut"))
        self.assertIn("AIEvent.ET_ENGINE_PREVIEW", source("events.nut"))
        self.assertIn('layer == "lines"', source("orchestrator.nut"))
        self.assertIn("C121_CATALOG_TOWN_REV.rawset", source("catalog.nut"))
        self.assertIn("C121_CATALOG_HUB_LEARN_REV.rawset(stationId", source("probes.nut"))
        self.assertIn("C121_CATALOG_AIRPORT_LEARN_REV.rawset(airportType", read_builder_air())
        self.assertIn("C121_CATALOG_ARM_LEARN_REV.rawset(arm", read_projects_source())
        self.assertIn("OpexC121CatalogRefreshStationLines(this._lines)", source("orchestrator.nut"))
        self.assertIn("C121_CATALOG_AIRPORT_REV.rawset(airportType", source("catalog.nut"))
        self.assertNotIn("C121_CATALOG_LINES_REV", read_builder_air())
        self.assertNotIn("C121_CATALOG_LEARN_REV", read_builder_air())
        self.assertIn("date - entry.date >= 365", read_builder_air())
        save = source("persist.nut").split("function OpexAI::Save()", 1)[1].split(
            "function OpexAI::Load(", 1)[0]
        self.assertNotIn("C121_CATALOG_CACHE", save)

    def test_slices_and_first_year_gate(self):
        scheduler = source("scheduler_tasks.nut")
        self.assertIn("C121_CATALOG_INCREMENTAL && sliceBudget > 150000", scheduler)
        self.assertIn("s.partialPending = true", scheduler)
        self.assertIn("s.plans.len() > s.lastPublishedCount", scheduler)
        self.assertIn("owner._portfolioInvalidated = false", scheduler)
        self.assertIn("OpexCatalogCostSliceLog", scheduler)
        self.assertIn("C121_CATALOG_TOWN_BATCH_DATE != AIDate.GetCurrentDate()", scheduler)
        self.assertIn("this._runOrchestratorTick();", source("main.nut"))
        self.assertEqual(source("main.nut").count(
            "while (catalogPending && OpexC121CatalogCanContinue(this, continuationTick))"), 1)
        self.assertNotIn("AIController.GetOpsTillSuspend() > 10000", source("main.nut"))
        self.assertIn("AIController.GetTick() == continuationTick", scheduler)
        self.assertEqual(source("main.nut").count("this._dispatchCatalog(queuedTask,"), 1)
        self.assertNotIn("OpexC121CatalogTownProductionBatch(this._catalog)) this._portfolioInvalidated", scheduler)
        self.assertIn("C121_CATALOG_AIR_FIRST_YEAR", read_projects_source())
        self.assertIn("doFreight = false;", read_projects_source())

    def test_material_town_change_and_first_year_cash_gate(self):
        catalog = source("catalog.nut")
        self.assertIn("abs(pax - old.pax) >= 10", catalog)
        self.assertIn("abs(mail - old.mail) >= 10", catalog)
        self.assertIn("abs(pax - old.pax) * 100 >= old.pax * 20", catalog)
        projects = source("task_projects.nut")
        self.assertIn("local c121FirstYearAirBatch = C121_CATALOG_AIR_FIRST_YEAR", projects)
        self.assertIn("year == this._generationStageMonth / 12", projects)
        self.assertIn('c121FirstYearAirBatch && project.mode == "air"', projects)
        self.assertLess(projects.index("!OpexAirBatchPlanStillLive(project.payload"),
                        projects.index("local projCap = OpexProjectFinanceCapital(project);"))
        self.assertIn("if (projCap <= availCap)", projects)
        self.assertIn("if (c121ChainAttempt) c121AirChained++;", projects)
        self.assertIn("C121_AIR_CHAIN_PASS built_air=", projects)
        self.assertIn("reuse_pct=", source("probes.nut"))
        self.assertIn("chained_slices=", source("probes.nut"))

    def test_added_cache_fields_avoid_squirrel_keywords(self):
        air = read_builder_air()
        block = air.split("function OpexC121CatalogChoice(", 1)[1].split(
            "function OpexC121ReplayEngineChoice(", 1)[0]
        reserved = ("static", "class", "base", "delegate", "clone", "resume",
                    "yield", "const", "enum", "constructor", "instanceof", "typeof",
                    "in", "local", "function", "this", "null")
        field = re.compile(r"(?:\.|\b)(?:" + "|".join(reserved) + r")\s*(?:=|<-|:)")
        self.assertIsNone(field.search(block))
        self.assertIn("engineStatic =", block)

    def test_new_squirrel_identifiers_avoid_keywords(self):
        reserved = ("static", "class", "base", "clone", "resume", "yield", "const",
                    "enum", "delegate", "in", "typeof", "instanceof")
        for name in ("catalog.nut", "main.nut", "task_projects.nut", "probes.nut"):
            src = squirrel_code(source(name))
            for word in reserved:
                self.assertNotRegex(src, rf"\blocal\s+{word}\b")
                self.assertNotRegex(src, rf"(?<![\w]){word}\s*(?:=|<-)")

    def test_keyword_check_ignores_logs_but_keeps_real_identifiers(self):
        text = 'AILog.Info(" base=1 \\\" clone=2"); /* local base = 3 */\nlocal base = 4;'
        code = squirrel_code(text)
        self.assertEqual(code.count("base"), 1)
        self.assertRegex(code, r"\blocal\s+base\s*=")
        self.assertEqual(code.count("\n"), text.count("\n"))


if __name__ == "__main__":
    unittest.main()
