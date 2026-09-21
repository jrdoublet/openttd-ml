"""Après retrait des subventions : préserver la persistance des retraites actives."""
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
    raise AssertionError(f"corps non fermé: {signature}")


class TestC45SubsidyPersistence(unittest.TestCase):
    def setUp(self):
        self.persist = source("persist.nut")
        self.report = source("task_report.nut")
        self.settings = source("settings.nut")
        self.info = source("info.nut")

    def test_retired_state_is_ignored_on_save_and_load(self):
        for field in ("activeSubsidies", "vehiclesToScrap", "subsidyStats"):
            self.assertNotIn(field, self.persist)
            self.assertNotIn(field, source("main.nut"))

    def test_live_retirement_state_still_round_trips(self):
        save = function_body(self.persist, "function OpexAI::Save()")
        load = function_body(self.persist, "function OpexAI::Load(version, data)")
        self.assertIn("vehiclesToRetire = this._vehiclesToRetire", save)
        self.assertIn("this._vehiclesToRetire = data.vehiclesToRetire", load)
        self.assertIn("unprofitableStreaks = this._unprofitableStreaks", save)
        self.assertIn("this._unprofitableStreaks = data.unprofitableStreaks", load)


if __name__ == "__main__":
    unittest.main()
