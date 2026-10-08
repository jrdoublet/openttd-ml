import unittest
from pathlib import Path
from analyse_c121_station_flux import decode_balance

ROOT = Path(__file__).resolve().parents[1] / "ai/OpexAI"


def row():
    return {"station": 0, "cargo": 0, "start_date": 100, "end_date": 130, "period_days": 30,
            "pickups_lower": 100, "queue_start": 20, "queue_end": 70, "lower_pm": 152,
            "exact_pm": -1, "losses": -1, "qualified_bound": 1, "risk_samples": 0,
            "skew_samples": 0, "samples": 15, "max_gap": 2}


class StationProbeTests(unittest.TestCase):
    def test_balance_is_lower_bound_never_exact(self):
        r = decode_balance(row())
        self.assertEqual(r["status"], "lower_bound")
        self.assertEqual(r["lower_bound_monthly"], 152)
        self.assertIsNone(r["monthly"])

    def test_unsafe_skew_and_missing_are_unknown(self):
        for field, value in (("risk_samples", 1), ("skew_samples", 1), ("queue_end", None),
                             ("losses", 0), ("end_date", 131), ("lower_pm", 200)):
            r = row()
            r[field] = value
            self.assertEqual(decode_balance(r)["status"], "unknown", field)

    def test_negative_balance_is_zero_bound_not_zero_demand(self):
        r = row()
        r.update(pickups_lower=10, queue_start=100, queue_end=0, lower_pm=0)
        result = decode_balance(r)
        self.assertEqual(result["lower_bound_monthly"], 0)
        self.assertIsNone(result["monthly"])

    def test_setting_off_transient_and_both_loop_paths(self):
        info = (ROOT / "info.nut").read_text(encoding="utf8")
        block = info.split('name = "c121_station_flux_probe"', 1)[1].split("});", 1)[0]
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(level + "_value = 0", block)
        for file in ("main.nut", "probes.nut"):
            self.assertIn("if (C121_STATION_FLUX_PROBE) OpexC121StationFluxStep(this._catalog);",
                          (ROOT / file).read_text(encoding="utf8"))
        self.assertNotIn("C121_STATION_FLUX_STATE", (ROOT / "persist.nut").read_text(encoding="utf8"))


if __name__ == "__main__":
    unittest.main()
