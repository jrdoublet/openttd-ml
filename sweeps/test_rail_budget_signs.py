"""Annual RAIL budget sign extraction must fail closed and never double-count."""

import unittest

from rail_budget_signs import rail_budget_sign_metrics


class RailBudgetSignsTest(unittest.TestCase):
    def test_two_years_and_owner(self):
        chunks = {"SIGN": {
            0: {"owner": 0, "name": "OP|1973|1200|300"},
            1: {"owner": 0, "name": "OS|1973|540|31"},
            2: {"owner": 0, "name": "OP|1974|5600|900"},
            3: {"owner": 0, "name": "OS|1974|2000|30"},
            4: {"owner": 1, "name": "OS|1974|123456|990"},
        }}
        result = rail_budget_sign_metrics(chunks)
        self.assertEqual(result["rail_budget_sign_by_year"]["1973"]["cand_rank"], 540)
        self.assertEqual(result["rail_budget_sign_by_year"]["1974"]["cand_pax"], 5600)
        self.assertEqual(result["rail_budget_sign_by_year"]["1974"]["cand_rank"], 2000)
        self.assertTrue(result["rail_budget_sign_by_year"]["1974"]["complete"])
        self.assertEqual(result["rail_budget_sign_conflicts"], 0)

    def test_missing_truncated_duplicate_and_missing_counter(self):
        missing = rail_budget_sign_metrics({})
        self.assertEqual(missing["rail_budget_sign_coverage"], "missing_SIGN")
        self.assertIsNone(missing["rail_budget_sign_by_year"])
        result = rail_budget_sign_metrics({"SIGN": [
            {"name": "OS|1974|120|70"}, {"name": "OS|1974|121|70"},
            {"name": "OP|1974|100|20"}, {"name": "OP|1973|100"},
            {"name": "OS|1975|123456789012345678901234"},
        ]})
        self.assertEqual(result["rail_budget_sign_conflicts"], 1)
        self.assertEqual(result["rail_budget_sign_invalid"], 2)
        self.assertIsNone(result["rail_budget_sign_by_year"]["1974"]["cand_rank"])
        self.assertFalse(result["rail_budget_sign_by_year"]["1974"]["complete"])
        self.assertEqual(result["rail_budget_sign_by_year"]["1974"]["cand_pax"], 100)

    def test_cumulative_values_are_not_summed(self):
        result = rail_budget_sign_metrics({"SIGN": [
            {"name": "OP|1971|10|20"}, {"name": "OS|1971|30|1"},
            {"name": "OP|1972|20|30"}, {"name": "OS|1972|40|2"},
        ]})
        self.assertEqual(result["rail_budget_sign_by_year"]["1972"]["cand_rank"], 40)
        self.assertNotEqual(result["rail_budget_sign_by_year"]["1972"]["cand_rank"], 70)


if __name__ == "__main__":
    unittest.main()
