from pathlib import Path
import shutil
import tempfile
import unittest

from sweeps.diag_c121_investment import ROOT, instrument, parse_trace


def event(seq, body, owner=0):
    return f"[script:4] [{owner}] [I] C121_INVEST v=1 seq={seq} day=1 tick={seq} {body}"


class InvestmentProbeTests(unittest.TestCase):
    def test_instrumentation_is_copy_only_and_targeted(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "OpexAI"
            shutil.copytree(ROOT / "ai/OpexAI", target)
            before = {p.name: p.read_bytes() for p in target.glob("*.nut")}
            instrument(target)
            changed = sorted(name for name, value in before.items()
                             if (target / name).read_bytes() != value)
            self.assertEqual(changed, ["main.nut", "task_air.nut", "task_projects.nut", "task_report.nut"])
            self.assertTrue((target / "c121_investment_probe.nut").exists())
            self.assertEqual(before["info.nut"], (target / "info.nut").read_bytes())
            self.assertEqual(before["settings.nut"], (target / "settings.nut").read_bytes())
            self.assertIn("C121InvestSource();", (target / "main.nut").read_text(encoding="utf-8"))
            self.assertIn('C121InvestProject(project, i, "built", "built"',
                          (target / "task_projects.nut").read_text(encoding="utf-8"))
            self.assertIn('C121InvestFleetSnapshot(line, year, "refuse", code)',
                          (target / "task_air.nut").read_text(encoding="utf-8"))
            self.assertIn("C121InvestAnnual(line, year, vehCount, profit, currentRevenue",
                          (target / "task_report.nut").read_text(encoding="utf-8"))

    def test_reader_preserves_unknown_and_links_line(self):
        text = "\n".join([
            event(1, "event=source econ=1 catalog=1 initial=0"),
            event(2, "event=project phase=built key=air|1|2|0|pax rank=0 outcome=built line=7 "
                     "arm=newpair initial_n=1 target_n=4 decision_n=1 initial_profit=100 target_profit=300 "
                     "decision_profit=100 finance_now=50000 finance_score=120000 available=70000 fund_score=3"),
            event(3, "event=fleet phase=refuse line=7 reason=O year=1971 age=1 have=1 target=4 after=na added=0 "
                     "last_profit=na cash=80000 reserve=30000 plane_price=20000 need=52000 wait_a=na wait_b=9"),
            event(4, "event=annual line=7 report_year=1972 profit_year=1971 age=2 full_year=1 vehs=1 profit=5000 "
                     "revenue=12000 wait_a=3 wait_b=9 rating_a=100 rating_b=110"),
        ])
        parsed = parse_trace(text)
        self.assertEqual(parsed["issues"], [])
        self.assertEqual(parsed["builds"][0]["line"], 7)
        self.assertEqual(parsed["builds"][0]["target_n"], 4)
        refusal = parsed["lines"][7]["fleet"][0]
        self.assertIsNone(refusal["last_profit"])
        self.assertIsNone(refusal["wait_a"])
        self.assertEqual(refusal["wait_b"], 9)
        self.assertEqual(parsed["full_year_observations"], 1)
        self.assertEqual(parsed["refusal_reasons"], {"O": 1})

    def test_wrong_source_or_foreign_owner_fails_closed(self):
        parsed = parse_trace(event(1, "event=source econ=1 catalog=0 initial=0"))
        self.assertIn("wrong_effective_settings", parsed["issues"])
        parsed = parse_trace(event(1, "event=source econ=1 catalog=1 initial=0", owner=1))
        self.assertEqual(parsed["foreign_events"], 1)
        self.assertIn("missing_source_marker", parsed["issues"])


if __name__ == "__main__":
    unittest.main()
