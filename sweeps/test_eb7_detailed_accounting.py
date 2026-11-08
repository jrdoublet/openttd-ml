"""Tests de contrat pour EB-7 Phase 2 (comptabilité fine et passive AIR/ROUTE)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def read_nut(name):
    return (AI / name).read_text(encoding="utf-8")


class TestEB7DetailedAccounting(unittest.TestCase):
    def test_setting_declaration_and_defaults(self):
        info = read_nut("info.nut")
        self.assertIn('"eb7_detailed_accounting"', info)
        block = re.search(r'AddSetting\(\{\s*name = "eb7_detailed_accounting"(.*?)\}\);', info, re.S)
        self.assertIsNotNone(block, "Bloc AddSetting eb7_detailed_accounting manquant")
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 1", body)
        self.assertIn("easy_value = 1", body)
        self.assertIn("medium_value = 1", body)
        self.assertIn("hard_value = 1", body)
        self.assertIn("custom_value = 1", body)

    def test_globals_and_loader(self):
        globals_pre = read_nut("globals_pre.nut")
        self.assertIn("EB7_DETAILED_ACCOUNTING <- 1;", globals_pre)
        self.assertIn("EB7_LEDGER <- { capexRoad = 0, capexAir = 0, vehBuyAir = 0, lastCash = 0, lastLoan = 0 };", globals_pre)
        settings = read_nut("settings.nut")
        self.assertIn('EB7_DETAILED_ACCOUNTING = AIController.GetSetting("eb7_detailed_accounting") == 1 ? 1 : 0;', settings)

    def test_ledgers_accounting_methods(self):
        ledgers = read_nut("ledgers.nut")
        self.assertIn("OpexEB7RecordSpend", ledgers)
        self.assertIn("OpexEB7MonthlyReconciliation", ledgers)
        self.assertIn("EB7_MONTHLY_REPORT", ledgers)
        self.assertIn("EB7_ACCOUNTING", ledgers)

    def test_task_projects_instrumentation(self):
        task_projects = read_nut("task_projects.nut")
        self.assertIn('OpexEB7RecordSpend("air", "capex", spent)', task_projects)
        self.assertIn('OpexEB7RecordSpend("road", "capex", spent)', task_projects)
        self.assertIn('OpexEB7RecordSpend("air", "vehBuy", plannedAdded)', task_projects)
        self.assertIn("OpexEB7MonthlyReconciliation()", task_projects)

    def test_persist_support(self):
        persist = read_nut("persist.nut")
        self.assertIn("eb7Ledger", persist)
        self.assertIn("EB7_DETAILED_ACCOUNTING", persist)

    def test_hygiene_no_rail_modifications(self):
        # Vérification formelle : builder_rail.nut ne contient pas EB7
        builder_rail = read_nut("builder_rail.nut")
        self.assertNotIn("EB7_", builder_rail)
