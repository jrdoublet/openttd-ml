"""Contrats de lecture des panneaux, sans lancer le moteur."""

import unittest

from smoke_normal_play_signs import capture_snapshot, sign_records, summarize


class NormalPlaySignSmokeTests(unittest.TestCase):
    def _row(self, arm, names, date="1971-01-01", output=""):
        return {
            "experiment": {"bench_run": [arm, 42, 0]}, "date": date,
            "output": output,
            "chunks": {"SIGN": {str(i): {"name": name} for i, name in enumerate(names)},
                       "PLYR": {0: {"money": 12345}}},
        }

    def _samples(self, arm, names, output="", date="1971-01-01"):
        rows = []
        for month in range(1, 13):
            rows.extend(capture_snapshot(self._row(arm, names, date=f"1970-{month:02d}-01")))
        rows.extend(capture_snapshot(self._row(arm, names, date=date, output=output)))
        return rows

    def test_sign_chunk_dict_or_list(self):
        self.assertEqual(len(sign_records({"SIGN": {1: {"name": "A"}}})), 1)
        self.assertEqual(len(sign_records({"SIGN": [{"name": "B"}]})), 1)
        self.assertEqual(sign_records({"SIGN": None}), [])

    def test_normal_zero_control_positive(self):
        rows = self._samples("normal_default", []) + self._samples("benchmark_panels", ["OA|X"])
        summary, passed = summarize(rows)
        self.assertTrue(passed)
        self.assertEqual(summary["normal_default"]["max_sign_count"], 0)
        self.assertEqual(summary["benchmark_panels"]["final_sign_names"], ["OA|X"])
        self.assertEqual(summary["benchmark_panels"]["final_sign_types"], {"OA": 1})

    def test_freight_exposure_requires_both_panels(self):
        rows = self._samples("normal_default", []) + self._samples(
            "benchmark_panels", ["VS|12", "VL|12"])
        self.assertTrue(summarize(rows, require_freight=True)[1])
        no_vl = self._samples("normal_default", []) + self._samples("benchmark_panels", ["VS|12"])
        self.assertFalse(summarize(no_vl, require_freight=True)[1])

    def test_three_years_36_snapshots_ending_december(self):
        rows = []
        for arm, names in (("normal_default", []), ("benchmark_panels", ["VS|12", "VL|12"])):
            for year in range(1970, 1973):
                for month in range(1, 13):
                    rows.extend(capture_snapshot(self._row(arm, names, date=f"{year}-{month:02d}-01")))
        summary, passed = summarize(rows, final_year=1972, years=3, require_freight=True)
        self.assertTrue(passed)
        self.assertEqual(summary["normal_default"]["snapshot_count"], 36)
        self.assertFalse(summarize(rows[:-1], final_year=1972, years=3)[1])

    def test_reject_signs_in_normal(self):
        rows = self._samples("normal_default", ["BT|X"]) + self._samples("benchmark_panels", ["OA|X"])
        self.assertFalse(summarize(rows)[1])

    def test_reject_missing_control_or_script_error(self):
        rows = self._samples("normal_default", [], output="Your script made an error") + self._samples("benchmark_panels", ["OA|X"])
        self.assertFalse(summarize(rows)[1])
        self.assertFalse(summarize(rows[:1])[1])

    def test_reject_premature_end(self):
        # Trois mois seulement dans les deux bras : ne pas confondre la date
        # du dernier releve et une simulation complete de douze mois.
        rows = [r for r in self._samples("normal_default", [])
                + self._samples("benchmark_panels", ["IG|X"])
                if r["date"] <= "1970-03-01"]
        self.assertFalse(summarize(rows)[1])


if __name__ == "__main__":
    unittest.main()
