"""Contrats statiques du catalogue AIR incremental (sans partie OpenTTD)."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from campaign_freeze import parse_ai_settings

AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


class TestC121CatalogIncremental(unittest.TestCase):
    def test_settings_default_off_and_c121_gate(self):
        defaults = parse_ai_settings(AI / "info.nut")
        self.assertEqual(defaults["c121_catalog_incremental"], 0)
        self.assertEqual(defaults["c121_catalog_air_first_year"], 0)
        settings = source("settings.nut")
        self.assertIn('C121_CATALOG_INCREMENTAL = C121_AIR_ECONOMICS\n', settings)
        self.assertIn('AIController.GetSetting("c121_catalog_incremental")', settings)
        self.assertIn('C121_CATALOG_AIR_FIRST_YEAR = C121_CATALOG_INCREMENTAL\n', settings)

    def test_default_chooses_original_function_without_cache_call(self):
        air = source("builder_air.nut")
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
        self.assertIn("C121_CATALOG_AIRPORT_LEARN_REV.rawset(airportType", source("builder_air.nut"))
        self.assertIn("C121_CATALOG_ARM_LEARN_REV.rawset(arm", source("projects.nut"))
        self.assertIn("OpexC121CatalogRefreshStationLines(this._lines)", source("orchestrator.nut"))
        self.assertIn("C121_CATALOG_AIRPORT_REV.rawset(airportType", source("catalog.nut"))
        self.assertNotIn("C121_CATALOG_LINES_REV", source("builder_air.nut"))
        self.assertNotIn("C121_CATALOG_LEARN_REV", source("builder_air.nut"))
        self.assertIn("date - entry.date >= 365", source("builder_air.nut"))
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
        self.assertIn("while (catalogPending && this._activeWorker == null", source("main.nut"))
        self.assertEqual(source("main.nut").count("AIController.GetOpsTillSuspend() > 10000)"), 2)
        self.assertEqual(source("main.nut").count("this._dispatchCatalog(queuedTask,"), 2)
        self.assertNotIn("OpexC121CatalogTownProductionBatch(this._catalog)) this._portfolioInvalidated", scheduler)
        self.assertIn("C121_CATALOG_AIR_FIRST_YEAR", source("projects.nut"))
        self.assertIn("doFreight = false;", source("projects.nut"))

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
        air = source("builder_air.nut")
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
            src = source(name)
            for word in reserved:
                self.assertNotRegex(src, rf"\blocal\s+{word}\b")
                self.assertNotRegex(src, rf"(?<![\w]){word}\s*(?:=|<-)")


if __name__ == "__main__":
    unittest.main()
