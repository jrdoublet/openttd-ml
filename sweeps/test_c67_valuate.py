"""Host unit tests for C67 Valuate fixture staging, sign decoding and contract checks."""
from pathlib import Path
import hashlib
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from bench_c67_valuate import (
    NAME, PASS_SIGN, assess, keep, parse_logs, parse_signs, stage_fixture,
)


class TestC67Valuate(unittest.TestCase):
    def records(self, s5_err=0, s10_err=0, max_call=120, passed=True, log_extra=""):
        signs = {
            "S5": {"BLOCKS": 64, "ERR": s5_err, "REF": 2800, "VAL": 390, "MAX": max_call, "BMAX": 420, "PCT": 86},
            "S10": {"BLOCKS": 64, "ERR": s10_err, "REF": 11200, "VAL": 1180, "MAX": max_call, "BMAX": 1250, "PCT": 89},
        }
        log_text = (
            f"C67V_SUMMARY side=5 blocks=64 errors={s5_err} ref_total=179200 val_total=24960 "
            f"ref_mean=2800 val_mean=390 max_single={max_call} max_block=420 saving_pct=86\n"
            f"C67V_SUMMARY side=10 blocks=64 errors={s10_err} ref_total=716800 val_total=75520 "
            f"ref_mean=11200 val_mean=1180 max_single={max_call} max_block=1250 saving_pct=89\n"
            f"{log_extra}"
        )
        rec = [
            {
                "run": [NAME, 42, 0],
                "date": f"1970-{m:02d}-01",
                "signs": signs,
                "passed": False,
                "output": "",
                "engine_failure": None,
                "error": False,
            }
            for m in range(1, 13)
        ]
        rec.append({
            "run": [NAME, 42, 0],
            "date": "1971-01-01",
            "signs": signs,
            "passed": passed,
            "output": log_text,
            "engine_failure": None,
            "error": False,
        })
        return rec

    def test_stage_fixture_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "fixture"
            manifest = stage_fixture(target)
            expected_files = {
                "main.nut", "info.nut", "terrain_valuate.nut", "terrain_map.nut", "budget.nut",
            }
            self.assertEqual(set(manifest.keys()), expected_files)
            for fname in expected_files:
                fpath = target / fname
                self.assertTrue(fpath.is_file())
                self.assertEqual(manifest[fname], hashlib.sha256(fpath.read_bytes()).hexdigest())

            with self.assertRaises(FileExistsError):
                stage_fixture(target)

    def test_parse_signs_and_exact_pass(self):
        chunks = {
            "SIGN": {
                1: {"name": "C67V|S5|ERR|0"},
                2: {"name": "C67V|S5|REF|2800"},
                3: {"name": "C67V|S5|VAL|390"},
                4: {"name": "C67V|S10|ERR|0"},
                5: {"name": "C67V|PASS"},
            }
        }
        signs, passed = parse_signs(chunks)
        self.assertTrue(passed)
        self.assertEqual(signs["S5"]["ERR"], 0)
        self.assertEqual(signs["S5"]["VAL"], 390)
        self.assertEqual(signs["S10"]["ERR"], 0)

        row = {"experiment": {"bench_run": [NAME, 42, 0]}, "date": "1971-01-01", "chunks": chunks}
        k = keep(row)[0]
        self.assertTrue(k["passed"])
        self.assertEqual(k["signs"]["S5"]["VAL"], 390)

    def test_parse_logs(self):
        text = (
            "C67V_SUMMARY side=5 blocks=64 errors=0 ref_total=179200 val_total=24960 "
            "ref_mean=2800 val_mean=390 max_single=120 max_block=420 saving_pct=86\n"
        )
        logs = parse_logs(text)
        self.assertIn(5, logs)
        self.assertEqual(logs[5]["blocks"], 64)
        self.assertEqual(logs[5]["errors"], 0)
        self.assertEqual(logs[5]["saving_pct"], 86)

    def test_assess_passing_run(self):
        records = self.records()
        res = assess(records, years=1)
        self.assertTrue(res["ok"])
        self.assertTrue(res["exactitude"]["pass"])
        self.assertEqual(res["exactitude"]["s5_errors"], 0)
        self.assertEqual(res["exactitude"]["s10_errors"], 0)
        self.assertTrue(res["opcodes"]["pass"])
        self.assertTrue(res["non_suspendable_bound"]["pass"])
        self.assertLessEqual(res["non_suspendable_bound"]["s5_max_single_call_ops"], 10000)

    def test_assess_rejects_errors(self):
        records = self.records(s5_err=1)
        res = assess(records, years=1)
        self.assertFalse(res["ok"])
        self.assertFalse(res["exactitude"]["pass"])

    def test_assess_rejects_missing_pass_sign(self):
        records = self.records(passed=False)
        res = assess(records, years=1)
        self.assertFalse(res["ok"])
        self.assertFalse(res["fixture_pass"])

    def test_assess_rejects_bound_violation(self):
        records = self.records(max_call=12000)
        res = assess(records, years=1)
        self.assertFalse(res["ok"])
        self.assertFalse(res["non_suspendable_bound"]["pass"])

    def test_assess_rejects_script_and_engine_errors(self):
        records = self.records(log_extra="[script:0] [0] [E] Your script made an error")
        res = assess(records, years=1)
        self.assertFalse(res["ok"])

    def test_squirrel_invariants(self):
        sources = [
            ROOT / "ai/OpexAI/terrain_valuate.nut",
            ROOT / "sweeps/fixtures/TerrainValuateProbe/main.nut",
            ROOT / "sweeps/fixtures/TerrainValuateProbe/info.nut",
        ]
        forbidden_identifiers = [r"\bclone\s*=", r"\bbase\s*=", r"\bparent\s*=", r"\bresume\s*="]
        for src in sources:
            text = src.read_text(encoding="utf-8")
            for pat in forbidden_identifiers:
                self.assertIsNone(re.search(pat, text), f"Forbidden identifier pattern {pat} in {src.name}")
            # Verify no closure capturing outer local variables (function (...) { ... })
            # All functions are method definitions: function ClassName::... or function method() { ... }
            lines = text.splitlines()
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("const "):
                    self.assertTrue(
                        re.match(r"^const\s+[A-Za-z0-9_]+\s*=\s*([0-9]+|\"[^\"]*\");", stripped),
                        f"Non-literal const in {src.name}: {stripped}",
                    )

    def test_geometric_contract_bounds(self):
        # Spec docs/c67_cartographie_contrat.md:
        # W=256, H=256, S=5 -> nx=52, ny=52, total=2704
        # S=10 -> nx=26, ny=26, total=676
        for w, h, s, exp_nx, exp_ny, exp_total in [
            (256, 256, 5, 52, 52, 2704),
            (256, 256, 10, 26, 26, 676),
            (2048, 2048, 5, 410, 410, 168100),
            (2048, 2048, 10, 205, 205, 42025),
        ]:
            nx = (w + s - 1) // s
            ny = (h + s - 1) // s
            self.assertEqual(nx, exp_nx)
            self.assertEqual(ny, exp_ny)
            self.assertEqual(nx * ny, exp_total)


if __name__ == "__main__":
    unittest.main()
