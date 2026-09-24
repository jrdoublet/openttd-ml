"""Contrats B8 : aucun rearmement pendant rebut et timer de rebut renouvele."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1 : pos]
    raise AssertionError(f"corps non ferme: {signature}")


class TestB8ScrapLifecycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.air = source("task_air.nut")
        cls.report = source("task_report.nut")
        cls.projects = source("task_projects.nut")

    def test_air_scrapping_guard_precedes_crash_refleet_and_growth(self):
        body = function_body(self.air, "function OpexAI::_resizeAirFleets(")
        guard = body.index('if (("scrapping" in line) && line.scrapping)')
        crash = body.index('if (("needsRefleet" in line) && line.needsRefleet)')
        purchase = body.index("local grown = OpexAirAddPlane(line, this._catalog)")
        self.assertLess(guard, crash)
        self.assertLess(guard, purchase)
        self.assertIn('OpexAirFleetRefusal(line, year, "K")', body[guard:crash])
        self.assertIn("continue", body[guard:crash])

    def test_fleet_project_revalidates_scrapping_at_purchase_boundary(self):
        body = function_body(self.projects, "function OpexAI::_tryBuildFleetProject(")
        guard = body.index('line == null || (("scrapping" in line) && line.scrapping)')
        purchase = body.index("local grown = OpexAirAddPlane(line, this._catalog)")
        self.assertLess(guard, purchase)
        self.assertIn('reason = "line_scrapping"', body[guard:purchase])
        self.assertIn('outcome = "rejected"', body[guard:purchase])

    def test_air_scrapping_refusal_is_named_for_diagnostics(self):
        body = function_body(self.air, "function OpexAirFleetRefusal(")
        self.assertIn('code == "K"', body)
        self.assertIn('reasonStr = "scrapping"', body)

    def test_each_new_scrap_cycle_overwrites_start_year(self):
        body = function_body(self.report, "function OpexAI::_triggerScrapLine(")
        self.assertIn('if ("scrapStartYear" in line) line.scrapStartYear = year', body)
        self.assertIn('else line.scrapStartYear <- year', body)
        self.assertLess(body.index("scrapStartYear"), body.index("SendVehicleToDepot"))

    def test_old_save_fallback_still_initialises_missing_start_year(self):
        body = function_body(self.report, "function OpexAI::_scrapDeadLines(")
        self.assertIn('if (!("scrapStartYear" in line)) line.scrapStartYear <- year', body)
        self.assertIn("SCRAP_TIMEOUT_YEARS", body)

    def test_lifecycle_logs_expose_start_and_elapsed(self):
        trigger = function_body(self.report, "function OpexAI::_triggerScrapLine(")
        scrap = function_body(self.report, "function OpexAI::_scrapDeadLines(")
        self.assertIn('" start_year=" + line.scrapStartYear', trigger)
        self.assertIn(
            'local elapsed = ("scrapStartYear" in line) ? year - line.scrapStartYear : -1',
            scrap,
        )
        self.assertIn('" elapsed=" + elapsed', scrap)


if __name__ == "__main__":
    unittest.main()