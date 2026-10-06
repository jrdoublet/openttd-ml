"""Central integration contracts. Synthetic traces are not engine fixtures."""
from copy import deepcopy
from pathlib import Path
import re
import unittest

from sweeps import diag_air_selection_light as light
from sweeps import fleet_amort_probe_adapter as adapter
from sweeps.diag_three_lots_integration import LIGHT_ARMS, SHADOW_ARMS
from sweeps.test_parallel_fleet_amort_shadow import snapshot

ROOT = Path(__file__).resolve().parents[1]


def line(tag, text):
    return f"[script:4] [0] OPEX 1971-5-1 {tag} {text}"


def fixture():
    e = snapshot()
    e["candidates"][1]["baseline"]["context"]["quantity"] = 0
    e["candidates"][1]["alternative"]["context"]["quantity"] = 0
    lines = [line("FLEET_AMORT", "v=1 phase=begin id=1 revision=1 day=720012 count=2 budget=100000 supported=1 calibrated=1")]
    for i, row in enumerate(e["candidates"]):
        b, a = row["baseline"], row["alternative"]
        c = b["context"]
        fields = {"v": 1, "phase": "candidate", "id": 1, "candidate": row["id"], "index": i,
                  "mode": row["mode"], "category": row["category"], "profit": b["profitAnnual"],
                  "net": a["profitAnnual"], "calibrated": b["calibratedProfitAnnual"],
                  "net_calibrated": a["calibratedProfitAnnual"], "score": b["score"], "net_score": a["score"],
                  "finance": c["finance_capital"], "denominator": c["denominator"],
                  "factor": 1, "priority": 0, "bonus": 0, "revenue": c["revenue_annual"],
                  "original": 4 if i == 0 else 0, "quantity": c["quantity"]}
        if i == 0:
            fields.update(price=30019, observed=1, line=10, line_mode="air")
        lines.append(line("FLEET_AMORT", " ".join(f"{k}={v}" for k, v in fields.items())))
    lines.append(line("FLEET_AMORT", "v=1 phase=end id=1 count=2 complete=1 baseline="
                      + ",".join(e["baseline_order"]) + " alternative=" + ",".join(e["alternative_order"])))
    return lines


def decode(lines):
    return adapter.audit("\n".join(lines), "synthetic.log", campaign="synthetic", arm="snapshot", seed=42, repeat=1)


class ShadowAdapterTests(unittest.TestCase):
    def test_complete_vm_orders(self):
        r = decode(fixture())
        self.assertFalse(r["rejected_blocks"])
        self.assertEqual(r["analysis"]["coverage"]["measurable"], 1)
        self.assertTrue(r["analysis"]["elections"][0]["winner_changed"])
        self.assertEqual(r["snapshot"]["elections"][0]["candidates"][0]["original_quantity"], 4)

    def test_absence_is_unknown(self):
        r = decode([])
        self.assertEqual(r["coverage"], "absent")
        self.assertIsNone(r["inversions_if_absent"])

    def test_every_truncation_fails_closed(self):
        rows = fixture()
        for i in range(len(rows)):
            r = decode(rows[:i] + rows[i+1:])
            self.assertEqual(r["analysis"]["coverage"]["measurable"], 0)
            self.assertTrue(r["rejected_blocks"])

    def test_duplicate_block_is_not_two_elections(self):
        r = decode(fixture() * 2)
        self.assertEqual(r["analysis"]["coverage"]["measurable"], 0)

    def test_duplicate_candidate_is_rejected(self):
        rows = fixture()
        rows.insert(2, rows[1])
        self.assertTrue(decode(rows)["rejected_blocks"])

    def test_unsupported_is_not_false_zero(self):
        rows = fixture()
        rows[0] = rows[0].replace("supported=1", "supported=0")
        self.assertTrue(decode(rows)["rejected_blocks"])

    def test_bad_score_is_not_rank_inference(self):
        rows = fixture()
        rows[1] = re.sub(r" score=\S+", " score=999", rows[1])
        self.assertEqual(decode(rows)["analysis"]["coverage"]["measurable"], 0)

    def test_missing_owner_is_not_opex(self):
        rows = [s.replace("[script:4] [0] ", "") for s in fixture()]
        self.assertTrue(decode(rows)["rejected_blocks"])

    def test_reload_separates_same_id(self):
        rows = fixture() + [line("LOAD_RECONCILE", "saved=1 kept=1 dropped=0")] + fixture()
        r = decode(rows)
        self.assertEqual(r["analysis"]["coverage"]["measurable"], 2)

    def test_reordered_candidates_not_assumed_complete(self):
        rows = fixture()
        rows[1], rows[2] = rows[2], rows[1]
        self.assertTrue(decode(rows)["rejected_blocks"])

    def test_nonfinite_is_rejected(self):
        rows = fixture()
        rows[1] = rows[1].replace("factor=1", "factor=nan")
        self.assertTrue(decode(rows)["rejected_blocks"])


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
        self.assertEqual(SHADOW_ARMS["calculate"], "OpexAI[fleet_amort_shadow_probe=1]")
        self.assertEqual(SHADOW_ARMS["snapshot"], "OpexAI[fleet_amort_shadow_probe=2]")

    def test_setting_off_and_loaded_once(self):
        info = self.source("info.nut").split('name = "fleet_amort_shadow_probe"', 1)[1].split("});", 1)[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{difficulty}_value = 0", info)
        self.assertIn("min_value = 0, max_value = 2", info)
        self.assertEqual(self.source("settings.nut").count('GetSetting("fleet_amort_shadow_probe")'), 1)

    def test_shadow_collects_both_admission_paths_before_compaction(self):
        s = self.source("projects_selection.nut")
        self.assertEqual(s.count("OpexAmortProbeCandidate(amortProbe, project"), 2)
        self.assertLess(s.index("OpexAmortProbeEnd(amortProbe, affordable)"), s.index("OpexC120ReorderAffordableAir(affordable)"))
        self.assertIn("amortProbe.rows = []", s)

    def test_diagnostics_never_write_decision_fields(self):
        s = self.source("selection_diagnostics.nut")
        self.assertNotRegex(s, r"(?:project|affordable|row\.live)\.\w+\s*(?:=(?!=)|<-)")
        self.assertNotIn("AIController.GetSetting", s)
        self.assertNotIn("AIVehicle.", s)
        self.assertIn("state.rows[rowIndex].live != affordable[i]", s)

    def test_three_selection_paths_reuse_existing_ops(self):
        for name in ("projects.nut", "projects_update.nut", "projects_selection.nut"):
            s = self.source(name)
            self.assertEqual(s.count("OpexSelectionLightBegin()"), 1)
            self.assertEqual(s.count("OpexSelectionLightEnd(selectionLight"), 1)
            self.assertEqual(s.count("OpexOpsMeasureEnd(opsMark)"), 1)

    def test_r1_r3_default_stays_copy_only(self):
        self.assertIn("const R1_R3_TEST_ONLY = 0;", self.source("projects_selection.nut"))

    def test_no_unavailable_format_library(self):
        code = re.sub(r"/\*.*?\*/", "", self.source("selection_diagnostics.nut"), flags=re.S)
        self.assertNotRegex(code, r"\bformat\s*\(")
        self.assertIn('"e" + (exponent - 8)', code)


if __name__ == "__main__":
    unittest.main()