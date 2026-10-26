"""Contrats de dépouillement tardif : clôture 1979 et dépenses distinctes."""
import unittest

try:
    from sweeps.analyse_multi1_late_c63 import analyse_log, aggregate
except ImportError:
    from analyse_multi1_late_c63 import analyse_log, aggregate


def _closed_1979_log():
    parts = [
        "OPEX 1980-1-1 C63_INVEST phase=opp year=1979 absent_n=2 absent_d=100 "
        "invalid_n=1 invalid_d=30 unaffordable_n=0 unaffordable_d=0 "
        "demand_n=0 demand_d=0 waiting_compute_n=3 waiting_compute_d=180 "
        "launched_n=2 launched_d=50",
        "OPEX 1980-1-1 C63_INVEST phase=opp_absent year=1979 "
        "empty_pool_n=2 empty_pool_d=100",
        "OPEX 1979-12-2 C50_CHRONO phase=treasury_monthly year=1979 "
        "month=12 cash=1200000 loan=0 available=1175000",
        "OPEX 1980-1-1 C63_INVEST phase=line year=1979 "
        "line=21 mode=rail age=4 pred_p=30000 real_p=-1000 pred_r=50000 real_r=19000 vehs=2",
        "OPEX 1980-1-1 C63_INVEST phase=line year=1979 "
        "line=22 mode=air age=1 pred_p=80000 real_p=50000 pred_r=100000 real_r=72000 vehs=4",
    ]
    for mode in ("rail", "road", "air", "water", "fleet"):
        cost = 40000 if mode == "rail" else 0
        parts.append(
            "OPEX 1980-1-1 C63_INVEST phase=spend year=1979 mode="
            + mode + " planned_ok=" + str(cost) + " actual_ok=" + str(cost + 500 if cost else 0)
            + " n_ok=" + str(int(bool(cost)))
            + " planned_fail=0 actual_fail=0 n_fail=0"
        )
    return "\n".join(parts)


class TestMulti1LateC63(unittest.TestCase):
    def test_1979_flush_emitted_in_1980_and_mature_profit(self):
        actual = analyse_log(_closed_1979_log(), 1979, 1979)
        self.assertEqual(actual["warnings"], [])
        y = actual["years"]["1979"]
        self.assertEqual(y["modes"]["rail"]["actual_ok"], 40500)
        self.assertEqual(y["modes"]["rail"]["mature_losing_n"], 1)
        self.assertEqual(y["modes"]["rail"]["mature_real_profit"], -1000)
        self.assertEqual(y["modes"]["air"]["mature_n"], 0)
        self.assertEqual(y["opp_days"]["waiting_compute"], 180)
        self.assertEqual(y["opp_annual_total_days"], 360)
        self.assertEqual(y["cash_december"]["cash"], 1200000)
        means = aggregate({"42": actual, "100": actual}, 1979, 1979)
        self.assertEqual(means["1979"]["n_seeds"], 2)
        self.assertEqual(means["1979"]["avg_modes"]["rail"]["actual_ok"], 40500)

    def test_partial_flush_detected_and_cannot_aggregate_missing_seed(self):
        incomplete = _closed_1979_log().replace(
            "C63_INVEST phase=spend year=1979 mode=road",
            "C63_INVEST phase=spend year=1978 mode=road",
        )
        incomplete = analyse_log(incomplete, 1979, 1979)
        self.assertIn("spend_flush_count:1979:road=0", incomplete["warnings"])
        self.assertEqual(aggregate({"42": incomplete}, 1979, 1979), {})
        missing = analyse_log("", 1979, 1979)
        self.assertIn("missing_ledger:1979", missing["warnings"])
        self.assertEqual(aggregate({"42": incomplete, "100": missing}, 1979, 1979), {})


if __name__ == "__main__":
    unittest.main()
