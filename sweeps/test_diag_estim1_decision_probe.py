"""Contrats du lecteur ESTIM-1 : identité, provenance et valeurs manquantes."""

import gzip
import json
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_estim1_decision_probe import (
    analyze, decode_fields, discover_logs, markdown,
)


CAMPAIGN = "fixture_estim1_dtrace"


def event(day, tag, fields, slot=0):
    return f"[{slot}] [I] OPEX {day} {tag} {fields}\n"


class DecisionProbeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.prefix = self.root / CAMPAIGN
        self.engine = self.root / (CAMPAIGN + "_engine")
        self.engine.mkdir()

    def write_log(self, arm, text, seed=42, repeat=0, suffix=".log"):
        path = self.engine / f"{arm}_seed{seed}_r{repeat}{suffix}"
        if suffix == ".log.gz":
            with gzip.open(path, "wt", encoding="utf-8") as output:
                output.write(text)
        else:
            path.write_text(text, encoding="utf-8")
        return path

    def result(self):
        self.prefix.with_suffix(".json").write_text(json.dumps({
            "campaign_id": CAMPAIGN, "seeds": [42], "repeats": 1,
            "start_year": 1970, "years": 6,
            "policy_comparison": {"comparison_complete": True},
            "policies": [
                {"id": "reference", "role": "reference"},
                {"id": "estim1_diag15", "role": "variant"},
            ],
        }), encoding="utf-8")

    def snapshots(self):
        rows = []
        for arm, value in (("reference", 1000), ("estim1_diag15", 800)):
            rows.append({
                "campaign_id": CAMPAIGN, "run": ["OpexAI", 42, 0],
                "duel_policy_id": arm, "date": "1973-12-01",
                "company_value": value, "profit_year": 250, "money": 80,
                "primary_vehicles_by_mode": {"air": 2, "rail": 3},
            })
            rows.append({
                "campaign_id": CAMPAIGN, "run": ["AAAHogEx", 42, 0],
                "duel_policy_id": arm, "date": "1973-12-01",
                "company_value": 12345,
            })
        self.prefix.with_suffix(".jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )

    def test_monthly_trace_costs_and_equal_age_profit(self):
        self.result()
        self.snapshots()
        reference = (
            event("1972-1-1", "RAIL_BUILD",
                  "line=5 src=11 dst=22 trains=2 cost=300")
            + event("1973-2-10", "ESTIM_PASS",
                    "month=23678 budget=0 k_dec=100 alternatives=4 selected=1 top_k=10")
            + event("1973-2-10", "ESTIM_DECISION",
                    "stage=mode_top_0 mode=rail type=open id=rail|11|22|6|freight "
                    "rank=-1 e=-1 r=0 a=-1 raw_r=-1 p=120 score=0 "
                    "cash=0 reason=cash_selection")
            + event("1973-2-10", "ESTIM_SPEND",
                    "mode=rail id=rail|11|22|6|freight line=5 rank=-1 "
                    "actual_paid=150 quote=130 ok=1 reason=OK")
            + event("1973-2-10", "RAIL_ATTEMPT",
                    "src=11 dst=22 kind=freight actual=140 ok=1 reason=OK")
            + event("1973-2-11", "ESTIM_OUTCOME",
                    "id=rail|11|22|6|freight mode=rail rank=0 line=5 outcome=built "
                    "reason=OK paid_accounting=-1 cash_before=1000 cash_after=850")
            + event("1973-2-11", "ESTIM_OUTCOME",
                    "id=rail|11|22|6|freight mode=rail rank=0 line=-1 outcome=skipped "
                    "reason=already_built_in_pass paid_accounting=-1 cash_before=850 cash_after=850")
            + event("1973-2-11", "ESTIM_OUTCOME",
                    "id=air|7|8|0|pax mode=air rank=1 line=6 outcome=built "
                    "reason=OK paid_accounting=0 cash_before=800 cash_after=400")
            + event("1973-3-2", "RAIL_ATTEMPT",
                    "src=33 dst=44 kind=freight actual=0 ok=0 reason=SITEAB")
            + event("1973-3-2", "ESTIM_OUTCOME",
                    "id=rail|33|44|6|freight mode=rail rank=0 line=-1 "
                    "outcome=failed reason=SITEAB paid_accounting=0 "
                    "cash_before=400 cash_after=400")
            + event("1974-1-4", "LINE_REVENUE",
                    "line=5 mode=rail year=1974 age=2 real_prof=900 "
                    "pred_prof=400 real_rev=1000 real_run=100 vehs=3")
            + event("1974-1-4", "LINE_REVENUE",
                    "line=6 mode=air year=1974 age=1 real_prof=1000 vehs=2")
            + event("1973-1-4", "LINE_REVENUE",
                    "line=5 mode=rail year=1973 age=2 real_prof=99999 vehs=3")
            + event("1973-2-10", "ESTIM_PASS",
                    "month=23678 budget=999 selected=999", slot=1)
        )
        variant = (
            event("1972-1-1", "RAIL_BUILD",
                  "line=88 src=11 dst=22 trains=3 cost=450")
            + event("1973-2-11", "ESTIM_PASS",
                    "month=23678 budget=0 k_dec=100 alternatives=1 selected=1 top_k=10")
            + event("1973-2-12", "ESTIM_OUTCOME",
                    "id=rail|11|22|6|freight mode=rail rank=0 line=88 outcome=built "
                    "reason=OK paid_accounting=0 cash_before=10 cash_after=10")
            + event("1973-2-11", "RAIL_ATTEMPT",
                    "src=11 dst=22 kind=freight actual=0 ok=1 reason=OK")
            + event("1974-1-5", "LINE_REVENUE",
                    "line=88 mode=rail year=1974 age=2 real_prof=600 "
                    "pred_prof=300 real_rev=700 vehs=3")
        )
        self.write_log("reference", reference)
        self.write_log("estim1_diag15", variant)
        report = analyze(str(self.prefix))
        self.assertEqual(len(report["games"]), 2)
        pair = report["pairs"][0]
        self.assertEqual(pair["annual"][0]["delta_company_value_gbp"], -200)
        game = next(g for g in report["games"] if g["arm"] == "reference")
        february = game["years"]["1973"]["months"][1]
        self.assertEqual(february["pass_count"], 1)
        self.assertEqual(february["top_k_status"]["air"], "no_mode_top_trace")
        self.assertEqual(february["top_k"]["rail"][0]["fields"]["r"], 0)
        self.assertIsNone(february["top_k"]["rail"][0]["fields"]["e"])
        self.assertIn("e", february["top_k"]["rail"][0]["na_sentinel"])
        self.assertEqual(february["top_k"]["rail"][0]["fields"]["rank"], -1)
        self.assertEqual(february["construction_costs"]["by_mode"]["rail"]["builder_exact_total_gbp"], 150)
        self.assertEqual(february["construction_costs"]["by_mode"]["air"]["cash_proxy_total_gbp"], 400)
        self.assertEqual(len(february["spend_events"]), 1)
        self.assertEqual(len(february["rail_attempts"]), 1)
        built = next(e for e in february["outcomes"] if e["fields"].get("line") == 5)
        self.assertEqual(built["cost_observation"]["lag_days"], 1)
        self.assertEqual(built["cost_observation"]["source"], "ESTIM_SPEND")
        self.assertEqual(february["paid_accounting"]["zero_events"], 1)
        self.assertEqual(february["paid_accounting"]["na_or_missing_events"], 2)
        self.assertEqual(game["years"]["1973"]["months"][0]["status"], "no_ESTIM_PASS_trace")
        march = game["years"]["1973"]["months"][2]
        self.assertEqual(march["construction_costs"]["by_mode"]["rail"]["builder_exact_total_gbp"], 0)
        self.assertEqual(march["outcomes"][0]["cost_observation"]["source"], "RAIL_ATTEMPT")
        match = next(x for x in pair["equal_age_line_profit"]
                     if x["accounting_year"] == 1973 and x["mode"] == "rail" and x["age"] == 2)
        self.assertEqual(match["delta_median_gbp"], -300)
        self.assertEqual(match["reference"]["normalized_profit_median_gbp"], 600)
        self.assertEqual(match["variant"]["normalized_profit_median_gbp"], 600)
        self.assertFalse(any(x["accounting_year"] == 1972 for x in pair["equal_age_line_profit"]))
        self.assertIn("Graine 42", markdown(report))

    def test_missing_json_and_log_representations(self):
        content = event("1973-1-2", "ESTIM_PASS", "month=23677 budget=0")
        self.write_log("reference", content)
        self.write_log("reference", content, suffix=".log.gz")
        self.write_log("estim1_diag15", content)
        logs, _ = discover_logs(self.engine)
        self.assertEqual(len(logs), 2)
        report = analyze(str(self.prefix))
        self.assertIsNone(report["campaign_complete"])
        self.assertFalse(report["campaign_jsonl_present"])
        self.assertIsNone(report["pairs"][0]["annual"][0]["delta_company_value_gbp"])
        self.write_log("reference", content + "contradictory\n", suffix=".log.gz")
        with self.assertRaisesRegex(ValueError, "contradictoires"):
            discover_logs(self.engine)

    def test_nonfinite_unknown_and_zero(self):
        fields, na, bad = decode_fields("ESTIM_OUTCOME",
                                        "paid_accounting=-1 cash_before=0 cash_after=nan "
                                        "paid_cash_delta=inf")
        self.assertIsNone(fields["paid_accounting"])
        self.assertEqual(fields["cash_before"], 0)
        self.assertIsNone(fields["cash_after"])
        self.assertIsNone(fields["paid_cash_delta"])
        self.assertEqual(na, ["paid_accounting"])
        self.assertEqual(len(bad), 2)


if __name__ == "__main__":
    unittest.main()
