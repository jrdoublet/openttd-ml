"""Tests de contrat pour MULTI-1 (conditions de relance du multimodal tardif)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read_nut(name):
    return (AI / name).read_text(encoding="utf-8")


class TestMulti1RestartConditions(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info = read_nut("info.nut")
        self.assertIn('"multi1_relance"', info)
        block = re.search(r'AddSetting\(\{\s*name = "multi1_relance"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(block, "Bloc AddSetting multi1_relance manquant")
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 2", body)
        self.assertIn("easy_value = 0", body)
        self.assertIn("medium_value = 0", body)
        self.assertIn("hard_value = 0", body)
        self.assertIn("custom_value = 0", body)

    def test_globals_and_loader(self):
        globals_pre = read_nut("globals_pre.nut")
        self.assertIn("MULTI1_RELANCE <- 0;", globals_pre)
        self.assertIn("MULTI1_LAST_BUILD_DATE <- 0;", globals_pre)
        settings = read_nut("settings.nut")
        self.assertIn('MULTI1_RELANCE = AIController.GetSetting("multi1_relance");', settings)

    def test_multi1_trigger_predicate(self):
        proj_sel = read_nut("projects_selection.nut")
        self.assertIn("OpexMulti1TriggerActive", proj_sel)
        self.assertIn("MULTI1_RELANCE == 0", proj_sel)
        self.assertIn("year < 1975", proj_sel)
        self.assertIn("cash < 2000000 || loan > 0", proj_sel)
        self.assertIn("daysSinceBuild >= 180 || portfolioEmpty", proj_sel)
        self.assertIn("MULTI1_TRIGGER", proj_sel)

    def test_task_projects_build_tracking(self):
        task_proj = read_nut("task_projects.nut")
        self.assertIn("if (MULTI1_RELANCE) MULTI1_LAST_BUILD_DATE = AIDate.GetCurrentDate();", task_proj)

    def test_persist_support(self):
        persist = read_nut("persist.nut")
        self.assertIn("multi1LastBuildDate", persist)
        self.assertIn("MULTI1_RELANCE", persist)

    def test_predicate_is_called_and_full_save_loads_ungated(self):
        """Contrat : le predicteur est appele, le save complet ecrit la cle,
        Load ne depend pas de MULTI1_RELANCE, la grace est apres les reglages."""
        selection = read_nut("projects_selection.nut")
        self.assertGreaterEqual(selection.count("OpexMulti1TriggerActive("), 2)
        projects = read_nut("projects.nut")
        self.assertIn("OpexMulti1AppendRoadFeeders(", projects)
        self.assertIn("MULTI1_ACTIVE_PORTFOLIO = priorProjects", projects)
        air = read_nut("air_planning.nut")
        self.assertIn("OpexMulti1WidenAirForStep(ctx, airport)", air)
        self.assertIn("AT_COMMUTER", selection)
        self.assertIn("AT_LARGE", selection)
        self.assertIn("1000000", selection)
        self.assertIn("cash / 4", selection)
        persist = read_nut("persist.nut")
        self.assertIn("saveObj.multi1LastBuildDate <- MULTI1_LAST_BUILD_DATE;", persist)
        self.assertNotIn(
            'if (MULTI1_RELANCE && ("multi1LastBuildDate" in data)',
            persist,
        )
        reconcile = persist.split("function OpexAI::_reconcileAfterLoad", 1)[1]
        self.assertIn("MULTI1_LAST_BUILD_DATE = AIDate.GetCurrentDate();", reconcile)
        self.assertNotIn(
            "else if (MULTI1_RELANCE)",
            persist.split("function OpexAI::Load", 1)[1].split("function OpexAI::_reconcileAfterLoad", 1)[0],
        )

    def test_hygiene_no_rail_modifications(self):
        builder_rail = read_nut("builder_rail.nut")
        self.assertNotIn("MULTI1_", builder_rail)
