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
        self.assertGreaterEqual(rail.count('OpexRailFailureAudit("early",'), 5)
        self.assertEqual(rail.count("OpexRailSearchBlockerAudit(candidate, this._railSearch, project, i)"), 2)
        self.assertIn("function OpexRailSearchBlockerAudit(", (ROOT / "probes.nut").read_text(encoding="utf-8"))
        blocker_probe = (ROOT / "probes.nut").read_text(encoding="utf-8")
        self.assertIn('" fund_score=" + score', blocker_probe)
        self.assertIn('" destination=" + destination', blocker_probe)
        self.assertIn('OpexRailFailureAudit("dispatch",', (ROOT / "task_projects.nut").read_text(encoding="utf-8"))
        self.assertIn('function OpexAI::_recordRailAttempt(', rail)
        self.assertIn('if (!RAIL_FAILURE_AUDIT) return;', (ROOT / "probes.nut").read_text(encoding="utf-8"))
        self.assertIn('function OpexRailPortfolioAudit(', (ROOT / "probes.nut").read_text(encoding="utf-8"))
        self.assertIn('OpexRailPortfolioAudit("full",', (ROOT / "projects.nut").read_text(encoding="utf-8"))
        self.assertIn('OpexRailPortfolioAudit("incremental",', (ROOT / "projects_update.nut").read_text(encoding="utf-8"))
        self.assertIn('OpexRailPortfolioAudit("reselect",', (ROOT / "projects_selection.nut").read_text(encoding="utf-8"))

    def test_event_count_and_no_duplicate_failure(self):
        sample = [
            "OPEX 1974-9-1 RAIL_AUDIT stage=precheck kind=freight cargo=GOOD src=10 dst=20 reason=too_close_no_join ok=0 actual=0 ops=0\n",
            "OPEX 1974-9-2 RAIL_AUDIT stage=precheck kind=freight cargo=GOOD src=10 dst=20 reason=too_close_no_join ok=0 actual=0 ops=0\n",
            "OPEX 1974-9-3 RAIL_AUDIT stage=attempt kind=pax cargo=PASS src=10 dst=21 reason=OK ok=1 actual=100 ops=55\n",
            "OPEX 1975-10-1 RAIL_AUDIT stage=attempt kind=freight cargo=GOOD src=10 dst=20 reason=TRKFAIL ok=0 actual=42 ops=99\n",
            "OPEX 1975-10-1 RAIL_AUDIT stage=attempt kind=freight cargo=GOOD src=11 dst=20 reason=ABND ok=0 actual=0 ops=88\n",
            "OPEX 1975-10-1 RAIL_AUDIT stage=dispatch kind=pax cargo=PASS src=10 dst=20 reason=search_in_progress ok=0 actual=0 ops=0 rank=2\n",
            "OPEX bad RAIL_AUDIT kind=pax\n",
        ]
        row = summarize(sample)
        self.assertEqual(row["event_count"], 6)
        self.assertEqual(row["invalid_events"], 1)
        self.assertEqual(row["annual"]["1974"]["counts"]["precheck/freight/too_close_no_join"], 2)
        self.assertEqual(row["annual"]["1974"]["distinct_stage_kind_cargo_od"], 2)
        self.assertEqual(row["annual"]["1974"]["distinct_by_stage_kind"]["precheck/freight"], 1)
        self.assertEqual(row["annual"]["1974"]["distinct_by_stage_kind"]["attempt/pax"], 1)
        self.assertEqual(row["annual"]["1975"]["counts"]["attempt/freight/TOTAL"], 2)
        self.assertEqual(row["annual"]["1975"]["counts"]["money/attempt/freight/TRKFAIL"], 42)
        self.assertEqual(row["annual"]["1975"]["counts"]["dispatch/pax/search_in_progress"], 1)

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

    def test_pool_snapshots_aggregate_by_phase_and_year(self):
        lines = [
            "OPEX 1975-1-1 RAIL_POOL_AUDIT phase=incremental pax=4 freight=2 affordable_pax=2 affordable_freight=1 selected_pax=1 selected_freight=0 selected_air=3 selected_fleet=4 dropped_pax=5 dropped_freight=1 head_mode=air head_kind=pax\n",
            "OPEX 1975-1-3 RAIL_POOL_AUDIT phase=incremental pax=3 freight=2 affordable_pax=2 affordable_freight=1 selected_pax=1 selected_freight=1 selected_air=2 selected_fleet=4 dropped_pax=0 dropped_freight=0 head_mode=rail head_kind=freight\n",
            "OPEX 1975-1-8 RAIL_POOL_AUDIT phase=reselect pax=4 freight=3 affordable_pax=3 affordable_freight=2 selected_pax=2 selected_freight=1 selected_air=2 selected_fleet=1 dropped_pax=1 dropped_freight=0 head_mode=rail head_kind=pax\n",
        ]
        x = summarize(lines)
        y = x["pool_annual"]["1975"]
        self.assertEqual(y["incremental"]["calls"], 2)
        self.assertEqual(y["incremental"]["pax"], 7)
        self.assertEqual(y["incremental"]["dropped_pax"], 5)
        self.assertEqual(y["reselect"]["selected_pax"], 2)
        self.assertEqual(y["incremental"]["head/air"], 1)
        self.assertEqual(y["incremental"]["head/rail/freight"], 1)
        self.assertEqual(x["invalid_pool_events"], 0)

    def test_blocker_counts_and_maxima(self):
        logs = [
            "OPEX 1975-5-2 RAIL_BLOCKER requested_kind=pax requested_src=1 requested_dst=2 blocker=upgrade phase=search src=-1 dst=-1 age_days=-1 spent=400 budget=10000\n",
            "OPEX 1975-6-2 RAIL_BLOCKER requested_kind=pax requested_src=1 requested_dst=2 blocker=upgrade phase=search src=-1 dst=-1 age_days=-1 spent=9400 budget=10000\n",
            "OPEX 1975-6-3 RAIL_BLOCKER requested_kind=freight requested_src=3 requested_dst=4 blocker=primary phase=search src=8 dst=9 age_days=200 spent=5000 budget=10000\n",
        ]
        out = summarize(logs)
        self.assertEqual(out["blocker_annual"]["1975"]["counts"]["pax/upgrade/search"], 2)
        self.assertEqual(out["blocker_annual"]["1975"]["maxima"]["pax/upgrade/search"]["spent"], 9400)
        self.assertEqual(out["blocker_annual"]["1975"]["maxima"]["freight/primary/search"]["age_days"], 200)
        self.assertEqual(out["invalid_blocker_events"], 0)


if __name__ == "__main__":
    unittest.main()
