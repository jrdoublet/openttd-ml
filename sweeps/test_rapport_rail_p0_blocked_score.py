"""Pair-level summaries must not inflate repeated refusals into extra projects."""
import unittest

from rapport_rail_p0_blocked_score import summarize


def event(day, src, dst, score="100", *, self_pair=False):
    return {"day": day, "year": 1973, "kind": "freight", "cargo": "COAL",
            "src": str(src), "dst": str(dst), "requested_rank": "1",
            "link_status": "adjacent_exact_kind_src_dst", "blocker": "primary",
            "blocker_src": "50", "blocker_dst": "60",
            "same_od_as_primary_search": self_pair, "score_at_block": score,
            "profit_predicted_at_block": "25000", "budget_capital_at_block": "50000",
            "destination_at_block": "industry"}


class BlockedScoreSummaryTest(unittest.TestCase):
    def test_revisits_self_pair_and_later_success_are_separate(self):
        blocked = {"runs": [{"arm": "a", "seed": 42, "repeat": 0,
                   "blocked_visits": [event("1973-03-02", 10, 20), event("1973-04-02", 10, 20),
                                      event("1973-05-01", 50, 60, self_pair=True)]}]}
        attempt = {"arm": "a", "seed": 42, "repeat": 0, "mode": "primary", "kind": "freight",
                   "cargo": "COAL", "src": 50, "dst": 60, "rid": "older",
                   "start_date": "1973-02-01", "end_date": "1973-06-01", "stop": "OK",
                   "build_status": "failed", "build_ok": 0}
        new = {**attempt, "src": 10, "dst": 20, "rid": "later", "start_date": "1973-07-01",
               "end_date": "1973-07-10", "build_status": "built", "build_ok": 1}
        result = summarize(blocked, {"attempts": [attempt, new], "summary": {}})
        self.assertEqual(result["coverage"]["freight_blocker_visits"], 3)
        self.assertEqual(result["coverage"]["self_pair_visits"], 1)
        self.assertEqual(result["annual"]["1973"]["freight_distinct_od_excluding_self"], 1)
        pair = result["pairs_by_year"][0]
        self.assertEqual(pair["visits"], 2)
        self.assertEqual((pair["occupant_rid"], pair["later_same_OD_build_RIDs"]), ("older", ["later"]))

    def test_different_cargo_and_unknown_occupant_stay_unlinked(self):
        blocked = {"runs": [{"arm": "a", "seed": 1, "repeat": 0,
                   "blocked_visits": [event("1973-05-01", 10, 20)]}]}
        wrong_cargo = {"arm": "a", "seed": 1, "repeat": 0, "mode": "primary",
                       "kind": "freight", "cargo": "WOOD", "src": 10, "dst": 20,
                       "start_date": "1973-06-01", "end_date": "1973-07-01",
                       "rid": "wrong", "build_status": "built", "build_ok": 1}
        pair = summarize(blocked, {"attempts": [wrong_cargo], "summary": {}})["pairs_by_year"][0]
        self.assertEqual(pair["occupant_link"], "unmatched")
        self.assertEqual(pair["later_same_OD_built"], 0)


if __name__ == "__main__":
    unittest.main()
