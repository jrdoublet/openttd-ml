import unittest
from c121_station_flux_estimator import station_arrivals, calibrated_station_forecast, allocate_station_forecast


class StationFluxTests(unittest.TestCase):
    def test_backlog_growth_is_demand_even_when_planes_full(self):
        r = station_arrivals(days=30.4, pickups=100, queue_start=20, queue_end=70, losses=0)
        self.assertEqual(r["monthly"], 150)

    def test_draining_old_stock_is_not_new_demand(self):
        r = station_arrivals(days=30.4, pickups=100, queue_start=90, queue_end=20, losses=0)
        self.assertEqual(r["monthly"], 30)

    def test_unknown_losses_and_incomplete_pickups_are_not_exact(self):
        r = station_arrivals(days=30.4, pickups=100, queue_start=20, queue_end=30)
        self.assertIsNone(r["monthly"])
        self.assertEqual(r["lower_bound_monthly"], 110)
        self.assertEqual(station_arrivals(days=30, pickups=100, queue_start=0, queue_end=0,
                                         losses=0, complete=False)["status"], "unknown")

    def test_transfers_do_not_become_locally_generated_passengers(self):
        r = station_arrivals(days=30.4, pickups=100, queue_start=20, queue_end=20,
                             losses=0, external_deliveries=60)
        self.assertEqual(r["monthly"], 40)

    def test_capture_uses_local_flux_and_excludes_censored_samples(self):
        h = [{"status": "measured", "monthly": 40, "reference_monthly": 100,
              "capacity_censored": False, "days": 30} for _ in range(12)]
        h.append({"status": "measured", "monthly": 1000, "reference_monthly": 100,
                  "capacity_censored": True, "days": 30})
        self.assertEqual(calibrated_station_forecast(150, h)["monthly"], 60)
        self.assertIsNone(calibrated_station_forecast(150, h[:3])["monthly"])

    def test_shared_airport_conserves_total(self):
        self.assertEqual(allocate_station_forecast(120, {1: 1, 2: 3}), {1: 30, 2: 90})
        self.assertIsNone(allocate_station_forecast(120, {1: 0}))


if __name__ == "__main__":
    unittest.main()
