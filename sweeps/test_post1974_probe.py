"""Fixture contracts for non-invasive post-1974 instrumented-log parsing."""
import json
from pathlib import Path
import tempfile
import unittest

try:
    from sweeps.post1974_probe import parse_log
except ImportError:
    from post1974_probe import parse_log


class TestPost1974Probe(unittest.TestCase):
    def test_unique_od_lower_bound_and_paid_not_quote(self):
        sample = "\n".join([
            "INFO: OPEX 1979-5-1 PROJECT_CHOSEN mode=rail kind=freight cargo=7 src=12 dst=28 cost=90000 profit=15000",
            "INFO: OPEX 1979-5-1 RAIL_ATTEMPT src=12 dst=28 kind=freight pred_profit=15000 quote=90000 actual=7000 ok=0 reason=SITEAB",
            "INFO: OPEX 1979-5-2 RAIL_ATTEMPT src=12 dst=28 kind=freight pred_profit=15000 quote=90000 actual=0 ok=0 reason=SITEAB",
            "INFO: OPEX 1979-5-2 RAIL_ATTEMPT src=12 dst=30 kind=freight pred_profit=18000 quote=140000 actual=120000 ok=1 reason=OK",
            "INFO: OPEX 1979-5-2 AIR_BUILD src=54 dst=42 cost=300000 profit=15000",
            "INFO: OPEX 1979-5-2 AIR_BUILD src=42 dst=54 cost=300000 profit=15000",
            "INFO: OPEX 1979-6-3 V284 action=reject reason=waiting",
            "INFO: OPEX 1980-1-1 C63_INVEST phase=spend year=1979 mode=rail planned_ok=140000 actual_ok=120000 n_ok=1 planned_fail=180000 actual_fail=7000 n_fail=2",
            "INFO: OPEX 1980-1-1 C63_INVEST phase=opp year=1979 absent_n=1 absent_d=20 invalid_n=0 invalid_d=0",
        ])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "probe.log"
            path.write_text(sample, encoding="utf-8")
            data = parse_log(path)
        year = data["years"]["1979"]
        self.assertEqual(year["event_counts"]["RAIL_ATTEMPT"], 3)
        self.assertEqual(year["rail_min_distinct_od_kind"], 2)
        self.assertEqual(year["rail_reason_counts"], {"SITEAB": 2, "OK": 1})
        self.assertEqual(year["rail_success_actual_paid_observed"], 120000)
        self.assertEqual(year["air_min_distinct_od"], 1)
        self.assertEqual(year["chosen_events_by_mode"]["rail"], 1)
        self.assertEqual(year["v284_events_by_action"]["reject"], 1)
        self.assertEqual(year["c63_spend_by_mode"]["rail"]["actual_fail"], 7000)
        self.assertEqual(data["years"]["1978"]["c63_spend_by_mode"], None)


if __name__ == "__main__":
    unittest.main()
