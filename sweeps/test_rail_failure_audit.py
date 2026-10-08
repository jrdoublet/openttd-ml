import tempfile
from pathlib import Path
import unittest

from analyse_rail_failure_audit import compare, summarize

ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class RailFailureAuditTest(unittest.TestCase):
    def test_required_setting_and_log_sites(self):
        info = (ROOT / "info.nut").read_text(encoding="utf-8")
        block = info.split('name = "rail_failure_audit",', 1)[1].split("});", 1)[0]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"\b{level}_value\s*=\s*0\b")
        self.assertIn('RAIL_FAILURE_AUDIT <- false;', (ROOT / "globals_pre.nut").read_text(encoding="utf-8"))
        self.assertIn('RAIL_FAILURE_AUDIT = AIController.GetSetting("rail_failure_audit") != 0;',
                      (ROOT / "settings.nut").read_text(encoding="utf-8"))
        rail = (ROOT / "task_rail.nut").read_text(encoding="utf-8")
        self.assertEqual(rail.count('OpexRailFailureAudit("precheck",'), 4)
        self.assertEqual(rail.count('OpexRailFailureAudit("attempt",'), 1)
        self.assertIn('function OpexAI::_recordRailAttempt(', rail)
        self.assertIn('if (!RAIL_FAILURE_AUDIT) return;', (ROOT / "probes.nut").read_text(encoding="utf-8"))

    def test_event_count_and_no_duplicate_failure(self):
        sample = [
            "OPEX 1974-9-1 RAIL_AUDIT stage=precheck kind=freight cargo=GOOD src=10 dst=20 reason=too_close_no_join ok=0 actual=0 ops=0\n",
            "OPEX 1974-9-2 RAIL_AUDIT stage=precheck kind=freight cargo=GOOD src=10 dst=20 reason=too_close_no_join ok=0 actual=0 ops=0\n",
            "OPEX 1974-9-3 RAIL_AUDIT stage=attempt kind=pax cargo=PASS src=10 dst=21 reason=OK ok=1 actual=100 ops=55\n",
            "OPEX 1975-10-1 RAIL_AUDIT stage=attempt kind=freight cargo=GOOD src=10 dst=20 reason=TRKFAIL ok=0 actual=42 ops=99\n",
            "OPEX 1975-10-1 RAIL_AUDIT stage=attempt kind=freight cargo=GOOD src=11 dst=20 reason=ABND ok=0 actual=0 ops=88\n",
            "OPEX bad RAIL_AUDIT kind=pax\n",
        ]
        row = summarize(sample)
        self.assertEqual(row["event_count"], 5)
        self.assertEqual(row["invalid_events"], 1)
        self.assertEqual(row["annual"]["1974"]["counts"]["precheck/freight/too_close_no_join"], 2)
        self.assertEqual(row["annual"]["1974"]["distinct_stage_kind_cargo_od"], 2)
        self.assertEqual(row["annual"]["1974"]["distinct_by_stage_kind"]["precheck/freight"], 1)
        self.assertEqual(row["annual"]["1974"]["distinct_by_stage_kind"]["attempt/pax"], 1)
        self.assertEqual(row["annual"]["1975"]["counts"]["attempt/freight/TOTAL"], 2)
        self.assertEqual(row["annual"]["1975"]["counts"]["money/attempt/freight/TRKFAIL"], 42)

    def test_compare_arms(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            for arm, reason in [("reference", "TRKFAIL"), ("variant", "OK")]:
                (p / f"{arm}_seed42_r0.log").write_text(
                    f"OPEX 1975-1-2 RAIL_AUDIT stage=attempt kind=freight cargo=GOOD src=1 dst=2 reason={reason} ok={int(reason == 'OK')} actual=10 ops=9\n",
                    encoding="utf-8")
            result = compare(p)
            self.assertEqual(result["annual_totals"]["reference"]["1975"]["attempt/freight/TRKFAIL"], 1)
            self.assertEqual(result["annual_totals"]["variant"]["1975"]["attempt/freight/OK"], 1)


if __name__ == "__main__":
    unittest.main()
