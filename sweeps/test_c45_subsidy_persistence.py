"""Contrat C45 : subventions portées par C77 seul, état persistant sans drapeau dédié."""
from pathlib import Path
import re
import unittest
from opex_projects_source import read_projects_source


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
    raise AssertionError(f"corps non fermé: {signature}")


class TestC45SubsidyPersistence(unittest.TestCase):
    def setUp(self):
        self.persist = source("persist.nut")
        self.report = source("task_report.nut")
        self.settings = source("settings.nut")
        self.info = source("info.nut")

    def test_active_subsidies_round_trip_in_full_state(self):
        save = function_body(self.persist, "function OpexAI::Save()")
        load = function_body(self.persist, "function OpexAI::Load(version, data)")
        setting = re.search(
            r'name\s*=\s*"save_full_state".*?custom_value\s*=\s*(\d+)',
            self.info,
            re.S,
        )

        self.assertIsNotNone(setting)
        self.assertEqual(setting.group(1), "1")
        self.assertIn("activeSubsidies = this._activeSubsidies", save)
        self.assertIn(
            'if ("activeSubsidies" in data && data.activeSubsidies != null) '
            "this._activeSubsidies = data.activeSubsidies",
            load,
        )

    def test_subsidies_have_no_dedicated_flag_or_probe(self):
        for name in ("C42_SUBSIDIES", "EVENT_SUBSIDY_PROBE", "C42_SUBSIDY_LOG", "_subsidyStats"):
            for path in sorted(AI.glob("*.nut")):
                self.assertNotIn(name, path.read_text(encoding="utf-8"), path.name)

    def test_c77_is_the_only_subsidy_producer(self):
        handlers = source("event_handlers.nut")
        for handler in ("_onSubsidyOffer", "_onSubsidyOfferExpired",
                        "_onSubsidyAwarded", "_onSubsidyExpired"):
            body = function_body(handlers, f"function OpexAI::{handler}(event)")
            self.assertNotIn("C77_OPPORTUNISTIC_CANDIDATES", body)
        rebuild = function_body(source("task_projects.nut"), "function OpexAI::_rebuildProjects(")
        self.assertIn("freightCargo, freightCargos, this._activeSubsidies,", rebuild)
        self.assertNotIn("C77_OPPORTUNISTIC_CANDIDATES", rebuild)

    def test_c77_subsidy_offer_reaches_the_reactive_register(self):
        handlers = source("event_handlers.nut")
        orchestrator = source("orchestrator.nut")
        main = source("main.nut")
        offer = function_body(handlers, "function OpexAI::_onSubsidyOffer(event)")
        dispatch = function_body(orchestrator, "function OpexAI::_dispatchReactiveIntention(intention)")

        self.assertIn('"c77_subsidy"', offer)
        self.assertIn('intention.kind == "c77_subsidy"', dispatch)
        self.assertIn("function OpexAI::_c77InjectSubsidy(subId)", orchestrator)
        self.assertIn("function OpexAI::_c77RemoveSubsidy(subId)", handlers)
        self.assertIn("function _c77InjectSubsidy(subId);", main)
        self.assertIn("function _c77RemoveSubsidy(subId);", main)
        self.assertIn('entityKind == "subsidy"', read_projects_source())

    def test_retired_scrap_state_is_ignored_on_save_and_load(self):
        self.assertNotIn("vehiclesToScrap", self.persist)
        self.assertNotIn("vehiclesToScrap", source("main.nut"))

    def test_live_retirement_state_still_round_trips(self):
        save = function_body(self.persist, "function OpexAI::Save()")
        load = function_body(self.persist, "function OpexAI::Load(version, data)")
        self.assertIn("vehiclesToRetire = this._vehiclesToRetire", save)
        self.assertIn("this._vehiclesToRetire = data.vehiclesToRetire", load)
        self.assertIn("unprofitableStreaks = this._unprofitableStreaks", save)
        self.assertIn("this._unprofitableStreaks = data.unprofitableStreaks", load)

if __name__ == "__main__":
    unittest.main()
