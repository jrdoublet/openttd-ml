"""Contrat strict de l'analyse prétest B, sans moteur."""
import unittest

from analyse_air_bfail_precheck_shadow import analyze_lines


BASE = ("AIR_FINANCE_TRY date=1970-01-15 path=portfolio outcome=failed reason=BFAIL "
        "new_airports=2 pre_b_ok=0 pre_b_err=100 pre_b_verdict=reject "
        "pre_b_anchor=400 real_b_err=100 actual=26000 c_level_a=9000 c_airport_a=16000\n")


class PassiveBTests(unittest.TestCase):
    def run_logs(self, *logs):
        return analyze_lines(logs, "reference_seed5678_r0.log")

    def test_correct_reject_and_historical_spend(self):
        r = self.run_logs(BASE)
        self.assertEqual(r["status_counts"], {"correct_early_reject": 1})
        self.assertEqual(r["first_reject_eligible_a_spend_gbp"], 25000)
        self.assertEqual(r["warnings"][0]["code"], "missing_real_b_stage")

    def test_real_stage_is_captured(self):
        r = self.run_logs(BASE.replace("real_b_err=100", "real_b_err=100 real_b_stage=level"))
        self.assertEqual(r["rows"][0]["real_b_stage"], "level")
        self.assertFalse(r["warnings"])

    def test_missed_bfail_not_claimed_avoidable(self):
        r = self.run_logs(BASE.replace("pre_b_ok=0", "pre_b_ok=1")
                          .replace("pre_b_verdict=reject", "pre_b_verdict=defer_level"))
        self.assertEqual(r["status_counts"], {"missed_bfail": 1})
        self.assertEqual(r["first_reject_eligible_a_spend_gbp"], 0)

    def test_false_reject_of_built_route(self):
        r = self.run_logs(BASE.replace("outcome=failed reason=BFAIL", "outcome=built reason=OK"))
        self.assertEqual(r["status_counts"], {"false_reject": 1})

    def test_after_b_failure_does_not_prove_b_failed(self):
        r = self.run_logs(BASE.replace("reason=BFAIL", "reason=START"))
        self.assertEqual(r["status_counts"], {"false_reject": 1})

    def test_a_failed_first_never_attributed_to_b(self):
        r = self.run_logs(BASE.replace("reason=BFAIL", "reason=AFAIL"))
        self.assertEqual(r["status_counts"], {"a_failed_first": 1})

    def test_missing_and_duplicate_fields_warn(self):
        r = self.run_logs(BASE.replace(" pre_b_anchor=400", ""),
                          BASE.replace(" pre_b_anchor=400", " pre_b_anchor=400 pre_b_anchor=400"))
        self.assertEqual(r["parsed_two_new_tries"], 0)
        self.assertEqual(r["all_two_new_tries"], 1)  # duplicated fields dropped earlier
        self.assertEqual(len(r["warnings"]), 2)

    def test_unrelated_refusal_not_in_sample(self):
        r = self.run_logs(BASE.replace("outcome=failed", "outcome=refused_margin"))
        self.assertEqual(r["all_two_new_tries"], 0)


if __name__ == "__main__":
    unittest.main()
