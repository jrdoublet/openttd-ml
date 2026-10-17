"""Selection-light contracts (amortisation shadow removed 17/10). Synthetic traces are not engine fixtures."""
from copy import deepcopy
from pathlib import Path
import re
import unittest

from sweeps import diag_air_selection_light as light
from sweeps.diag_three_lots_integration import LIGHT_ARMS

ROOT = Path(__file__).resolve().parents[1]


def line(tag, text):
    return f"[script:4] [0] OPEX 1971-5-1 {tag} {text}"


class SelectionLightTests(unittest.TestCase):
    def record(self, fields=""):
        return line("SELECTION_LIGHT", "v=1 inv=1 path=full start_day=10 end_day=12 start_tick=1 end_tick=100 ops=0 considered=2 selected=1 " + fields)

    def test_calendar_and_tick_are_distinct(self):
        row = light.audit_text(self.record(), "synthetic")["streams"][0]["selections"][0]
        self.assertEqual((row["days"], row["ticks"], row["ops_proxy"]), (2, 99, 0))

    def test_duplicate_is_not_double_counted(self):
        rows = light.audit_text(self.record() + "\n" + self.record(), "synthetic")["streams"][0]["selections"]
        self.assertEqual(len(rows), 1)

    def test_conflict_is_invalid(self):
        r = light.audit_text(self.record() + "\n" + self.record().replace("ops=0", "ops=1"), "synthetic")
        self.assertFalse(r["streams"][0]["selections"][0]["valid"])

    def test_missing_unit_not_zero(self):
        r = light.audit_text(self.record().replace("end_day=12", ""), "synthetic")
        self.assertIsNone(r["streams"][0]["selections"][0]["days"])


class SourceContracts(unittest.TestCase):
    def source(self, name):
        return (ROOT / "ai/OpexAI" / name).read_text(encoding="utf-8")

    def test_only_diagnostic_arms(self):
        self.assertEqual(LIGHT_ARMS["light"], "OpexAI[catalog_cost_probe=1]")
        self.assertNotIn("fleet_amort_shadow_probe", self.source("info.nut"))

    def test_diagnostics_never_write_decision_fields(self):
        s = self.source("selection_diagnostics.nut")
        self.assertNotRegex(s, r"(?:project|affordable|row\.live)\.\w+\s*(?:=(?!=)|<-)")
        self.assertNotIn("AIController.GetSetting", s)
        self.assertNotIn("AIVehicle.", s)

    def test_three_selection_paths_reuse_existing_ops(self):
        for name in ("projects.nut", "projects_update.nut", "projects_selection.nut"):
            s = self.source(name)
            self.assertEqual(s.count("OpexSelectionLightBegin()"), 1)
            self.assertEqual(s.count("OpexSelectionLightEnd(selectionLight"), 1)
            self.assertEqual(s.count("OpexOpsMeasureEnd(opsMark)"), 1)

    def test_r1_r3_default_stays_copy_only(self):
        self.assertIn("const R1_R3_TEST_ONLY = 0;", self.source("projects_selection.nut"))


if __name__ == "__main__":
    unittest.main()