"""Tests de jointure prudente score → construction → exercice P2."""
import unittest

from analyse_score_cold_execution_p2 import analyse_one


def log(message):
    return "[2026-10-13] dbg: [script:4] [0] [I] " + message + "\n"


def evidence(with_growth=False, mismatch=False):
    rows = [
        log("SCORE_COLD_P2_CAND pass=1 ordinal=1 phase=main mode=air kind=pax "
            "arm=newpair src=1 dst=2 cargo=0 line=-1 engine=223 raw_profit=100 "
            "score=1000 rank_score=2000"),
        log("SCORE_COLD_P2_HEAD pass=1 year=1970 month=1 day=2 budget=300000 "
            "head_mode=air head_src=1 head_dst=2 head_arm=newpair head_engine=223"),
        log("OPEX 1970-1-3 PROJECT_CHOSEN mode=air src=1 dst=2 profit=100"),
        log("OPEX 1970-1-3 AIR_BUILD arm=newpair line=0 src=1 dst=2 "
            "profit=100 planes=1 engine=223"),
        log("C121_BUILD line=0 arm=newpair engine=223 decision_profit=100 actual_n=1"),
    ]
    if with_growth:
        rows.append(log("OPEX 1971-1-4 FLEET_PROJECT action=grow line=0 added=1"))
    rows.append(log("OPEX 1972-1-3 LINE_REVENUE line=0 mode=air year=1972 "
                    f"age=2 pred_prof={'90' if mismatch else '100'} real_prof=80 vehs=1"))
    return rows


class P2ExecutionJoin(unittest.TestCase):
    def test_exact_event_chain(self):
        result = analyse_one(evidence())
        self.assertEqual(result["counts"]["construction_strict"], 1)
        self.assertEqual(result["counts"]["candidate_head_join"], 1)
        self.assertEqual(result["counts"]["provisional_comparable"], 1)
        self.assertFalse(result["calibration_ready"])

    def test_mutation_or_prediction_drift_fail_closed(self):
        for rows in (evidence(with_growth=True), evidence(mismatch=True)):
            with self.subTest(lines=rows):
                result = analyse_one(rows)
                self.assertNotIn("provisional_comparable", result["counts"])
                self.assertEqual(result["counts"]["mature_annual_rows"], 1)

    def test_aaahogex_ignored(self):
        rows = evidence() + ["[2026-10-13] dbg: [script:4] [1] [I] "
                             "OPEX 1973-1-3 LINE_REVENUE line=0 mode=air year=1973 "
                             "age=3 pred_prof=100 real_prof=999 vehs=1\n"]
        result = analyse_one(rows)
        self.assertEqual(len(result["mature_annual"]), 1)


if __name__ == "__main__":
    unittest.main()
