import unittest
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
from analyse_station_supply import analyse, metrics, rate


class SupplyAnalysisTests(unittest.TestCase):
    def test_rate_weights_real_duration(self):
        rows = [{"arrivals": 100, "period_days": 10}, {"arrivals": 100, "period_days": 30}]
        self.assertEqual(rate(rows), 152)
        self.assertIsNone(rate([]))

    def test_metrics_do_not_treat_empty_as_zero_error(self):
        self.assertIsNone(metrics([], "prediction")["wape"])
        cases = [{"actual": 100, "prediction": 120, "seed": 1, "station": 2, "game_id": "a"},
                 {"actual": 200, "prediction": 160, "seed": 1, "station": 2, "game_id": "a"}]
        m = metrics(cases, "prediction")
        self.assertEqual(m["stations"], 1)
        self.assertEqual(m["n"], 2)
        self.assertAlmostEqual(m["wape"], .2)
        self.assertAlmostEqual(m["bias_pct"], -20 / 3)

    def test_future_changes_labels_not_past_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = root / "bench.manifest.json"
            manifest.write_text("{}", encoding="utf8")
            (root / "bench_engine").mkdir()
            (root / "bench_engine" / "game.log").write_text(
                "[1] [I] id:5 name:Passengers label:PASS\n"
                "[0] [I] C121_BUILD new_airports=2 station_id_a=0 station_id_b=1 "
                "pax_raw_a=100 pax_raw_b=100 rating_pax_a=127 rating_pax_b=127\n",
                encoding="utf8")
            bench = {"campaign_id": "fixture", "source_bundle_sha256": "fixture",
                     "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                     "station_supply_telemetry": True,
                     "games": [{"game_id": "g", "seed": 73, "engine_log_path": "game.log",
                                "expected_last_checkpoint": "1972-12-01",
                                "game_ok": True, "game_status": "complete"}]}
            path = root / "bench.json"
            path.write_text(json.dumps(bench), encoding="utf8")
            def write_checkpoints(future_arrivals):
                records = []
                supply = 0
                for i in range(25):
                    d = date(1971 + i // 12, i % 12 + 1, 1)
                    if i:
                        supply += 40 if i <= 12 else future_arrivals
                    records.append({"company_slot": 0, "game_id": "g", "date": str(d),
                                    "station_supply": {"ok": True, "economy_date": d.toordinal(),
                                        "nodes": [{"station": 0, "cargo": 5, "graph": "7",
                                                   "compression": 700000, "membership": [[0, 42]],
                                                   "xy": 42, "build_date": 700000,
                                                   "supply": supply, "last_update": d.toordinal()}]},
                                    "line_telemetry": {"lines": [{"endpoint_cargo_stats": [
                                        {"station_id": 0, "cargo": {"5": {"rated": True,
                                            "rating": 127 if i < 12 else 255}}}]}]}})
                path.with_suffix(".jsonl").write_text("\n".join(map(json.dumps, records)), encoding="utf8")
            write_checkpoints(80)
            a = analyse(path)["cases"]
            write_checkpoints(160)
            b = analyse(path)["cases"]
            self.assertEqual(len(a), 1)
            self.assertEqual(a[0]["past_months"], 12)
            self.assertEqual(a[0]["future_months"], 12)
            for field in ("initial_offered_proxy", "past_rating_proxy", "past_supply_oracle"):
                self.assertEqual(a[0][field], b[0][field])
            self.assertEqual(b[0]["actual"], 2 * a[0]["actual"])


if __name__ == "__main__":
    unittest.main()
