import unittest
from analyse_town_flux import production_features, qualified_town_rows


class TownFluxTests(unittest.TestCase):
    def test_bad_other_town_or_cargo_does_not_discard_valid_row(self):
        valid = {"town": 9, "cargo": 5, "production": 200, "supplied_all_companies": 80}
        snapshot = {"ok": False, "reason": "invalid_month", "towns": [valid,
                    {**valid, "town": 10, "supplied_all_companies": 201},
                    {**valid, "production": -1}, {**valid, "cargo": True}, None]}
        self.assertEqual(list(qualified_town_rows(snapshot)), [valid])
        self.assertEqual(list(qualified_town_rows({"ok": False})), [])

    def history(self):
        return [{"closed_month": m, "available_month": m + 2, "production": m,
                 "supplied_all_companies": m / 2} for m in range(100, 112)]

    def test_real_months_and_no_future_leakage(self):
        h = self.history()
        a = production_features(h, 114)
        self.assertEqual(a["production_mean12"], 105.5)
        self.assertEqual(a["production_last"], 111)
        h.append({"closed_month": 112, "available_month": 114, "production": 99999,
                  "supplied_all_companies": 99999})
        self.assertEqual(production_features(h, 114), a)

    def test_missing_month_is_unknown_not_zero(self):
        h = self.history()
        del h[5]
        self.assertIsNone(production_features(h, 114))
        self.assertIsNone(production_features([], 114))

    def test_duplicate_observations_not_extra_month(self):
        h = self.history()[:-1]
        h.append(dict(h[-1]))
        self.assertIsNone(production_features(h, 114))


if __name__ == "__main__":
    unittest.main()
