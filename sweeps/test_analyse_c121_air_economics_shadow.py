"""C121 final hub-service estimates must use observed, not build-time, capacity.

Synthetic C117 windows represent the shape of the original 2026-09-28 probe;
its original campaign archive is not locally available for a historical replay.
"""

import math
import unittest

from sweeps.analyse_c121_air_economics_shadow import observed_final_service


def window(live=1, cap=300, mail_per_leg=50, trips=5, headway=10):
    return {"live_avg": live, "cap_avg": cap, "mail_seat_legs": mail_per_leg * trips,
            "trips": trips, "headway_days": headway}


class FinalC121ServiceTests(unittest.TestCase):
    def test_original_one_plane_capacity_is_unchanged(self):
        service = observed_final_service(window())
        self.assertAlmostEqual(service["pickup_rate"], 0.1)
        self.assertAlmostEqual(service["pax_rate"], 30)
        self.assertAlmostEqual(service["mail_rate"], 5)

    def test_mixed_old_new_engines_use_measured_fleet_capacities(self):
        # One 228 (300 PASS/50 MAIL), one 223 (220 PASS/40 MAIL).
        service = observed_final_service(window(live=2, cap=520, mail_per_leg=45))
        self.assertAlmostEqual(service["pax_rate"], 26)
        self.assertAlmostEqual(service["mail_rate"], 4.5)
        # The historical reader incorrectly retained 30/5 from initial 228.
        self.assertLess(service["pax_rate"], 30)

    def test_full_replacement_changes_competing_station_share(self):
        original = observed_final_service(window())
        replaced = observed_final_service(window(live=2, cap=440, mail_per_leg=40))
        self.assertAlmostEqual(replaced["pickup_rate"], original["pickup_rate"])
        self.assertAlmostEqual(replaced["pax_rate"], 22)
        self.assertAlmostEqual(replaced["mail_rate"], 4)
        # At the same hub, a fixed candidate rate competes with this service.
        candidate_pax_rate = 30
        original_share = candidate_pax_rate / (candidate_pax_rate + original["pax_rate"])
        new_share = candidate_pax_rate / (candidate_pax_rate + replaced["pax_rate"])
        self.assertGreater(new_share, original_share)

    def test_missing_or_unobserved_capacity_never_falls_back_to_build(self):
        for changes in ({"cap_avg": None}, {"live_avg": 0},
                        {"trips": 0}, {"mail_seat_legs": None},
                        {"mail_seat_legs": -1}, {"headway_days": -1},
                        {"cap_avg": math.nan}, {"headway_days": math.inf}):
            with self.subTest(changes=changes):
                self.assertIsNone(observed_final_service({**window(), **changes}))
        self.assertAlmostEqual(observed_final_service(window(mail_per_leg=0))["mail_rate"], 0)


if __name__ == "__main__":
    unittest.main()
