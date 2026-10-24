"""Unit tests for full-loop (as far as instrumentable) AC opcode report."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "sweeps") not in sys.path:
    sys.path.insert(0, str(ROOT / "sweeps"))

from sweeps.analyse_ac_loop_opcode import analyse, logfile_stats


class TestACLoopOpcode(unittest.TestCase):
    def test_disjoint_annual_loop_posts_and_air_phase(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "o.log"
            file.write_text(
                "OPEX 1971-3-1 AIR_LIGHT v=1 inv=2 gen=1 slice=1 origin=1 sliced=1 "
                "edge=exit complete=0 reason=hub_hub_yield hub_hub_ops=80 "
                "hub_hub_calls=1 hub_site_ops=100 hub_site_calls=1\n"
                "LOOP_OPS y=1971 post=orchestrator n=20 ops=400 tk=1 max=60\n"
                "LOOP_OPS y=1971 post=catalog_continuation n=3 ops=800 tk=1 max=300\n"
                "LOOP_OPS y=1971 post=sleep_left n=20 ops=999 tk=0 max=50\n"
                "LOOP_OPS y=1971 post=_year n=1 ops=0 tk=1 max=0\n",
                encoding="utf-8",
            )
            result = logfile_stats(file)
        self.assertEqual(result["1971"]["loop_executed_ops"], 1200)
        self.assertEqual(result["1971"]["sleep_left_ops"], 999)
        self.assertEqual(result["1971"]["phase_ops"]["hub_hub"], 80)
        self.assertEqual(result["1971"]["phase_calls"]["hub_site"], 1)
        self.assertEqual(result["1971"]["airlight_slices"], 1)

    def test_pair_only_same_year_and_log_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            for name, ops in (("off", 100), ("on", 120)):
                (base / f"{name}.log").write_text(
                    f"LOOP_OPS y=1972 post=orchestrator n=1 ops={ops} tk=0 max={ops}\n",
                    encoding="utf-8",
                )
            report = {
                "complete": True, "sources_unchanged": True,
                "years": 3, "seeds": [42],
                "games": [
                    {"arm": "reference", "seed": 42, "log_path": str(base / "off.log")},
                    {"arm": "variant", "seed": 42, "log_path": str(base / "on.log")},
                ],
            }
            input_path = base / "r.json"
            input_path.write_text(json.dumps(report), encoding="utf-8")
            value = analyse(input_path)
        self.assertTrue(value["valid"])
        self.assertEqual(value["final_year_paired_count"], 1)
        self.assertEqual(value["mean_final_year_loop_executed_ops_delta"], 20)
        self.assertIsNone(value.get("full_hardware_cpu"))

    def test_frozen_benchmark_log_paths_and_bundle_health(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            engine = base / "results" / "example_engine"
            engine.mkdir(parents=True)
            for name, ops in (("ref", 100), ("var", 90)):
                (engine / f"{name}.log").write_text(
                    f"LOOP_OPS y=1972 post=orchestrator n=1 ops={ops} tk=0 max={ops}\n",
                    encoding="utf-8",
                )
            report = {
                "source_bundle_sha256": "frozenhash", "years": 3,
                "seeds": [42], "failed_runs": [],
                "policies": [{"id": "off"}, {"id": "on"}],
                "games": [
                    {"policy_id": "off", "seed": 42, "game_ok": True,
                     "source_bundle_sha256": "frozenhash",
                     "engine_log_path": "/work/results/example_engine/ref.log"},
                    {"policy_id": "on", "seed": 42, "game_ok": True,
                     "source_bundle_sha256": "frozenhash",
                     "engine_log_path": "/work/results/example_engine/var.log"},
                ],
            }
            path = base / "results" / "report.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            value = analyse(path)
        self.assertTrue(value["valid"])
        self.assertTrue(value["source_frozen"])
        self.assertEqual(value["mean_final_year_loop_executed_ops_delta"], -10)


if __name__ == "__main__":
    unittest.main()
