"""Passive OR/OB|A rail attempt sign decoding (no OpenTTD engine required)."""
from pathlib import Path
import sys
import types
import unittest
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import openttdlab
except ImportError:
    fake_lab = types.ModuleType("openttdlab")
    fake_lab.bananas_ai = mock.MagicMock()
    fake_lab.bananas_ai_library = mock.MagicMock()
    fake_lab.local_folder = mock.MagicMock()
    fake_lab.run_experiments = mock.MagicMock()
    sys.modules["openttdlab"] = fake_lab

import bench_1v1_5y_20seeds as bench


class TestRailAttemptSignMetrics(unittest.TestCase):
    def test_retained_reasons_iterations_opcodes_and_years(self):
        decoded = bench.rail_attempt_sign_metrics({"SIGN": {
            0: {"owner": 0, "name": "OR|71|4|123|NSK|10000|300"},
            1: {"owner": 0, "name": "OB|A|71|4|123|2500000|50"},
            2: {"owner": 0, "name": "OR|72|4|124|CST|10000|10000"},
            3: {"owner": 0, "name": "OB|A|72|4|124|12000000|41"},
            4: {"owner": 0, "name": "OR|72|4|125|FSA|5000|4999"},
            5: {"owner": 1, "name": "OR|72|99|20|NSK|1|1"},
            6: {"owner": 0, "name": "OB|1970|42|100|999"},  # legacy, not OB|A
        }}, current_year=1975)
        self.assertEqual(decoded["rail_attempt_sign_coverage"], "retained_signs_only")
        self.assertEqual([(event["year"], event["reason"], event["iterations"])
                          for event in decoded["rail_attempt_sign_or"]],
                         [(1971, "OK", 300), (1972, "TRKFAIL", 10000), (1972, "ABND", 4999)])
        self.assertEqual(decoded["rail_attempt_sign_by_year"]["1971"], {
            "or_signs": 1, "reasons": {"OK": 1}, "iterations": 300,
            "iteration_budget": 10000, "ob_signs": 1, "opcodes": 2500000,
        })
        self.assertEqual(decoded["rail_attempt_sign_by_year"]["1972"], {
            "or_signs": 2, "reasons": {"TRKFAIL": 1, "ABND": 1}, "iterations": 14999,
            "iteration_budget": 15000, "ob_signs": 1, "opcodes": 12000000,
        })
        self.assertEqual(decoded["rail_attempt_sign_key_coverage"], {
            "unique_one_to_one_keys": 2, "or_without_ob": 1,
            "ob_without_or": 0, "ambiguous_keys": 0,
        })

    def test_missing_chunk_distinct_from_observed_empty_chunk(self):
        missing = bench.rail_attempt_sign_metrics({})
        self.assertEqual(missing["rail_attempt_sign_coverage"], "missing_sign_chunk")
        self.assertIsNone(missing["rail_attempt_sign_by_year"])
        self.assertIsNone(missing["rail_attempt_sign_or"])
        empty = bench.rail_attempt_sign_metrics({"SIGN": {}})
        self.assertEqual(empty["rail_attempt_sign_coverage"], "retained_signs_only")
        self.assertEqual(empty["rail_attempt_sign_by_year"], {})
        self.assertEqual(empty["rail_attempt_sign_or"], [])

    def test_invalid_and_length_limit_reported_without_false_values(self):
        clipped = "OR|71|4|1|NSK|10000|" + "9" * 11
        self.assertEqual(len(clipped), 31)
        decoded = bench.rail_attempt_sign_metrics({"SIGN": [
            {"name": clipped},
            {"name": "OR|71|5|6|NSK|1000|broken"},
            {"name": "OR|71|5|6|NSZ|1000|50"},
            {"name": "OB|A|71|5|6|1000|bogus"},
            {"name": "OB|A|71|5|6|1000|40"},
            {"name": "IR|71|5|6|NSK|1000|50"},
        ]}, current_year=1975)
        self.assertEqual(decoded["rail_attempt_sign_length_limit"], {"OR": 1, "OB": 0})
        self.assertEqual(decoded["rail_attempt_sign_invalid"], {"OR": 2, "OB": 1})
        self.assertEqual(decoded["rail_attempt_sign_or"], [])
        self.assertEqual(decoded["rail_attempt_sign_by_year"]["1971"]["opcodes"], 1000)
        self.assertEqual(decoded["rail_attempt_sign_key_coverage"]["ob_without_or"], 1)

    def test_reused_line_and_position_are_ambiguous_and_century_is_resolved(self):
        decoded = bench.rail_attempt_sign_metrics({"SIGN": [
            {"name": "OR|99|3|40|ZSA|10000|10000"},
            {"name": "OR|99|3|40|ZST|10000|20"},
            {"name": "OB|A|99|3|40|30000|40"},
            {"name": "OB|A|99|3|41|44000|41"},
        ]}, current_year=2001)
        self.assertEqual(decoded["rail_attempt_sign_by_year"]["1999"]["or_signs"], 2)
        self.assertEqual(decoded["rail_attempt_sign_key_coverage"], {
            "unique_one_to_one_keys": 0, "or_without_ob": 1,
            "ob_without_or": 1, "ambiguous_keys": 1,
        })

    def test_keep_attaches_opex_signs_only_to_opex_record(self):
        row = {"chunks": {"SIGN": [
            {"owner": 0, "name": "OR|71|4|123|NSK|10000|300"},
            {"owner": 0, "name": "OB|A|71|4|123|2500000|50"},
        ]}, "date": "1971-12-01", "output": "",
               "experiment": {"seed": 42, "repeat": 0, "policy_id": "reference"}}
        with mock.patch.object(bench, "extract_company_record", side_effect=lambda *args: {}), \
             mock.patch.object(bench, "append_checkpoint"):
            records = bench.keep(row)
        self.assertIsInstance(records, tuple)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["rail_attempt_sign_by_year"]["1971"]["opcodes"], 2500000)
        self.assertNotIn("rail_attempt_sign_by_year", records[1])
        self.assertEqual(records[0]["company_slot"], 0)
        self.assertEqual(records[1]["company_slot"], 1)


if __name__ == "__main__":
    unittest.main()
