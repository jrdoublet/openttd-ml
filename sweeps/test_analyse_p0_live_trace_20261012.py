"""Guard semantic limits of diagnostic project rejection and active services."""
import unittest

from analyse_p0_live_trace_20261012 import active_services, parse_log


class LiveTraceTest(unittest.TestCase):
    def test_counts_calls_not_unique_project_builds(self):
        lines = [
            "[I] OPEX 1973-7-1 SELECT_REJECT pair=3|4 type=hubhub reason=cash rank=0",
            "[I] OPEX 1973-7-2 SELECT_REJECT pair=3|4 type=hubhub reason=cash rank=0",
            "[I] OPEX 1973-7-2 SELECT_REJECT pair=4|5 type=hubhub reason=topk rank=64",
            "[I] OPEX 1973-7-3 P2_PASS in_best=0 n_built=0",
            "[I] OPEX 1973-7-4 P2_PASS in_best=64 n_built=1",
        ]
        row = parse_log(lines)["1973"]
        self.assertEqual({"cash": 2, "topk": 1}, row["select_reject"])
        self.assertEqual(1, row["reject_unique_pair_month"]["cash"])
        self.assertEqual(2, row["p2_passes"])
        self.assertEqual(1, row["p2_start_empty"])
        self.assertEqual(1, row["p2_with_progress"])

    def test_reconstruct_services_by_mode(self):
        payload = {"line_telemetry": {"snapshots": [
            {"seed": 42, "repeat": 0, "arm": arm, "year": 1973,
             "ok": True, "unresolved_vehicles": [], "lines": [{"mode": "air"}, {"mode": mode}]}
            for arm, mode in (("OpexAI", "rail"), ("AAAHogEx", "road"))]}}
        row = active_services(payload, [42])["42/1973"]
        self.assertEqual({"air": 1, "rail": 1}, row["opex"])
        self.assertEqual({"air": 1, "road": 1}, row["aaa"])

    def test_unresolved_is_not_silently_zero(self):
        payload = {"line_telemetry": {"snapshots": [{"seed": 42, "repeat": 0,
            "arm": "OpexAI", "year": 1973, "ok": True,
            "unresolved_vehicles": [12], "lines": []}]}}
        with self.assertRaisesRegex(ValueError, "unresolved"):
            active_services(payload, [42])


if __name__ == "__main__":
    unittest.main()
