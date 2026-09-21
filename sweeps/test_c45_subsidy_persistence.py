"""Contrat C45 : persister l'état comportemental, pas les compteurs de sonde."""
from pathlib import Path
import re
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

    def test_probe_counters_are_intentionally_transient(self):
        save = function_body(self.persist, "function OpexAI::Save()")
        load = function_body(self.persist, "function OpexAI::Load(version, data)")

        self.assertNotIn("subsidyStats", save)
        self.assertNotIn("subsidyStats", load)
        self.assertIn("if (EVENT_SUBSIDY_PROBE && this._subsidyStats != null)", self.report)
        self.assertIn("EVENT_SUBSIDY_PROBE = false;", self.settings)


if __name__ == "__main__":
    unittest.main()
