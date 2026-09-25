"""Fixtures courtes pour le rapprochement predit / realise des lignes AIR."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyse_air_demand_vs_realized import analyse_bundle, analyse_paths, french_summary


def admitted(town_a, town_b, profit, **extra):
    row = {
        "seed": 42,
        "outcome": "admitted",
        "townA": town_a,
        "townB": town_b,
        "P": profit,
        "year": 1972,
        "arm": "newpair",
    }
    row.update(extra)
    return row


def air_line(towns, profit, **extra):
    row = {
        "mode": "air",
        "towns": towns,
        "towns_raw": [town + 1 for town in towns],
        "vehicles": 2,
        "profit_last_year": profit,
    }
    row.update(extra)
    return row


def snapshot(lines, towns):
    return {
        "seed": 42,
        "year": 1975,
        "airpool": {"towns": {str(town): [idx, pop, 1000 + town] for idx, (town, pop) in enumerate(towns.items())}},
        "companies": {"0": {"lines": lines}, "1": {"lines": []}},
        "airpairs": [],
        "builds": [],
    }


class AirDemandVsRealizedTests(unittest.TestCase):
    def test_joins_unordered_api_towns_and_splits_models(self):
        bundle = {
            "snapshots": [snapshot(
                [
                    air_line([20, 10], 150000),
                    air_line([30, 40], 40000, passengers=15),
                    air_line([50, 60], 200000),
                    air_line([50, 70], 10000),
                ],
                {10: 500, 20: 2000, 30: 800, 40: 900, 50: 2000, 60: 3000, 70: 1800},
            )],
            "admitted": [
                admitted(20, 10, 100000, paxOld=40),
                admitted(30, 40, 80000, paxOld=50, paxNew=30),
                admitted(50, 60, 100000, paxOld=80),
            ],
            "builds": [admitted(10, 20, 100000, mode="air", outcome="built", year=1973)],
            "line_profits": [],
            "files": ["fixture.json"],
            "missing_files": [],
            "parse_notes": [],
        }
        # L'admission est en townA=20 townB=10 : la paire non ordonnee rejoint towns=[20, 10].
        # towns est deja l'identifiant API ; towns_raw = API + 1 ne doit pas servir.
        report = analyse_bundle(bundle)
        self.assertEqual(report["counts"]["observations"], 3)
        by_pair = {tuple(row["pair"]): row for row in report["observations"]}
        self.assertIn((10, 20), by_pair)
        self.assertNotIn((9, 19), by_pair)
        self.assertNotIn((11, 21), by_pair)
        old = report["models"]["old_proxy"]
        prod = report["models"]["production"]
        self.assertEqual(old["n_profit"], 2)
        self.assertEqual(old["profit_ratio_median"], 1.75)
        self.assertEqual(old["profit_ratio_mean"], 1.75)
        self.assertEqual(old["calibration_factor_profit"], 1.75)
        self.assertIsNone(old["calibration_factor_revenue"])
        self.assertEqual(old["by_population_band"]["<600"]["profit_ratio_median"], 1.5)
        self.assertEqual(old["by_population_band"][">1500"]["profit_ratio_median"], 2.0)
        self.assertEqual(old["by_airport_degree"]["1"]["profit_ratio_median"], 1.5)
        self.assertEqual(old["by_airport_degree"]["2"]["profit_ratio_median"], 2.0)
        self.assertEqual(prod["n"], 1)
        self.assertEqual(prod["profit_ratio_median"], 0.5)
        self.assertEqual(prod["pax_ratio_median"], 0.5)
        self.assertEqual(prod["calibration_factor_pax"], 0.5)
        self.assertEqual(prod["by_population_band"]["600-1500"]["profit_ratio_median"], 0.5)
        self.assertIn("LINE_PROFIT", report["missing_inputs"])
        self.assertIn("revenu (predit et realise)", report["missing_inputs"])
        self.assertNotIn("C78_AIRPAIR admises", report["missing_inputs"])
        self.assertNotIn("C78_BUILD", report["missing_inputs"])
        self.assertNotIn("passagers realises", report["missing_inputs"])
        text = french_summary(report)
        self.assertIn("Entrées manquantes", text)
        self.assertIn("médiane", text)
        self.assertIn("Modèle proxy de population", text)
        self.assertIn("Modèle production", text)
        self.assertIn("LINE_PROFIT", text)

    def test_reads_jsonl_logs_and_reports_unjoined_line_profit(self):
        snap = snapshot([air_line([10, 20], 120000)], {10: 700, 20: 800})
        snap["airpairs"] = [admitted(10, 20, 100000, paxOld=22)]
        snap["builds"] = []
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            snap_path = folder / "snap.json"
            snap_path.write_text(json.dumps([snap]), encoding="utf-8")
            log_path = folder / "trace.jsonl"
            log_path.write_text(
                "\n".join([
                    json.dumps({
                        "seed": 42,
                        "grep": "OPEX 1973-1-1 C56_TASK LINE_PROFIT name=4 cycle=- tick=1 opsclk=1 "
                                "year=1973 profit=90000 veh=2 stA=4 stB=8",
                    }),
                    json.dumps({
                        "seed": 42,
                        "grep": "OPEX 1972-1-1 C78_AIRPAIR year=1972 arm=newpair townA=10 townB=20 "
                                "dist=40 outcome=admitted P=100000 C=40000 paxOld=22",
                    }),
                ]) + "\n",
                encoding="utf-8",
            )
            missing = folder / "absent.json"
            report = analyse_paths([snap_path, log_path, missing])
            self.assertEqual(report["counts"]["observations"], 1)
            self.assertEqual(report["models"]["old_proxy"]["profit_ratio_median"], 1.2)
            self.assertIn(str(missing), report["missing_files"])
            self.assertIn("fichiers", report["missing_inputs"])
            self.assertTrue(any("LINE_PROFIT relie" in item for item in report["missing_inputs"]))
            out = folder / "out.json"
            text = french_summary(report)
            out.write_text(json.dumps(report), encoding="utf-8")
            self.assertIn("1.200", text)
            loaded = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(loaded["observations"][0]["pair"], [10, 20])

    def test_empty_inputs_list_what_is_missing(self):
        report = analyse_bundle({
            "snapshots": [],
            "admitted": [],
            "builds": [],
            "line_profits": [],
            "files": [],
            "missing_files": [],
            "parse_notes": [],
        })
        text = french_summary(report)
        for label in (
            "entrees",
            "C78_AIRPAIR admises",
            "C78_BUILD",
            "LINE_PROFIT",
            "lignes realisees (companies)",
            "populations (C78_AIRPOOL)",
            "passagers realises",
        ):
            self.assertIn(label, report["missing_inputs"])
            self.assertIn(label, text)
        self.assertEqual(report["models"]["old_proxy"]["n"], 0)
        self.assertIsNone(report["models"]["production"]["calibration_factor_revenue"])


if __name__ == "__main__":
    unittest.main()
