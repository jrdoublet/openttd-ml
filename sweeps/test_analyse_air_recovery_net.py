"""R19/V126 signed accounting: never call pending/orphan capital a net loss."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from analyse_air_recovery_net import analyze


class AnalyzeAirRecoveryNetTest(unittest.TestCase):
    def run_fixture(self, text):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reference_seed42_r0.log"
            path.write_text(text, encoding="utf-8")
            return analyze(path)

    def test_completed_deferred_sale_net_is_signed_and_added_once(self):
        result = self.run_fixture("""
AIR_RECOVERY_CREATE id=100_1 date=100 airport_a=30 airport_b=31 vehicles=1 pair=abs
AIR_FINANCE_TRY date=1970-01-01 src_town=1 dst_town=2 new_airports=2 outcome=failed reason=ORDFAIL actual=20000 recovery_id=100_1 orphan_kept=0
AIR_RECOVERY_STEP id=100_1 date=130 delta=-4000 deferred_net=-4000 vehicles_left=0 airports_left=0 done=1
AIR_RECOVERY_COMPLETE id=100_1 deferred_net=-4000
""")
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["states"], {"rollback_completed": 1})
        self.assertEqual(result["accounted_final_net_sum_known"], 16000)
        self.assertEqual(result["failed_records"][0]["recovery_deferred_net"], -4000)

    def test_orphan_and_pending_are_not_assumed_realized_loss(self):
        result = self.run_fixture("""
AIR_FINANCE_TRY date=1970-01-01 new_airports=2 outcome=failed reason=BFAIL actual=15000 orphan_kept=1 recovery_id=none
AIR_RECOVERY_CREATE id=100_2 date=100 airport_a=30 airport_b=31 vehicles=1 pair=abs
AIR_FINANCE_TRY date=1970-01-02 new_airports=2 outcome=failed reason=START actual=20000 orphan_kept=0 recovery_id=100_2
AIR_RECOVERY_STEP id=100_2 date=130 delta=-1000 deferred_net=-1000 vehicles_left=1 airports_left=1 done=0
""")
        self.assertEqual(result["states"], {"retained_asset": 1, "pending_or_unmatched": 1})
        self.assertEqual(result["accounted_final_net_count"], 0)
        self.assertEqual(result["initial_cost_sum_known"], 35000)

    def test_immediate_recovery_is_in_original_accounting(self):
        result = self.run_fixture("""
AIR_RECOVERY_CREATE id=100_1 date=100 airport_a=30 airport_b=31 vehicles=1 pair=abs
AIR_RECOVERY_COMPLETE id=100_1 deferred_net=0 immediate=1
AIR_FINANCE_TRY date=1970-01-01 new_airports=2 outcome=failed reason=START actual=1000 recovery_id=100_1 orphan_kept=0
AIR_FINANCE_TRY date=1970-01-01 new_airports=1 outcome=failed reason=AFAIL actual=300 recovery_id=none orphan_kept=0
""")
        self.assertEqual(result["states"], {"rollback_completed": 1, "no_ticket": 1})
        self.assertEqual(result["accounted_final_net_sum_known"], 1300)

    def test_duplicate_identifiers_ignored(self):
        result = self.run_fixture("""
AIR_RECOVERY_CREATE id=100_1 date=100
AIR_RECOVERY_CREATE id=100_1 date=100
AIR_RECOVERY_COMPLETE id=100_1 deferred_net=-1000
AIR_FINANCE_TRY date=1970-01-01 new_airports=2 outcome=failed reason=ORDFAIL actual=9000 recovery_id=100_1 orphan_kept=0
""")
        self.assertEqual(result["duplicate_ticket_ids"], ["100_1"])
        self.assertEqual(result["accounted_final_net_count"], 0)


if __name__ == "__main__":
    unittest.main()
