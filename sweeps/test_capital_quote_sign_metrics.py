"""Mesures P0 : un panneau par chantier, depenses des echecs non liquidees."""
import unittest

from sweeps.bench_1v1_5y_20seeds import capital_quote_sign_metrics


class CapitalQuoteSignMetrics(unittest.TestCase):
    def test_success_and_failure_distinct(self):
        chunks = {"SIGN": [
            {"owner": 0, "name": "CQ|A|110328|119105|1|1"},
            {"owner": 0, "name": "CQ|A|128183|0|0|1"},
            {"owner": 0, "name": "CQ|R|50000|65000|1|2"},
            {"owner": 0, "name": "CQ|D|20000|16000|1|1"},
            {"owner": 0, "name": "CQ|W|25000|4000|0|0"},
            {"owner": 1, "name": "CQ|A|999999|999999|1|99"},
        ]}
        metrics = capital_quote_sign_metrics(chunks)
        self.assertEqual(len(metrics["capital_quote_events"]), 5)
        self.assertEqual(metrics["capital_quote_invalid"], 0)
        air = metrics["capital_quote_by_mode"]["air"]
        self.assertEqual(air["quoted_success"], 110328)
        self.assertEqual(air["actual_success"], 119105)
        self.assertEqual(air["failed_events"], 1)
        self.assertEqual(air["actual_failed_at_return"], 0)
        self.assertEqual(air["max_samples_learned"], 1)
        self.assertEqual(metrics["capital_quote_by_mode"]["water"]["failed_events"], 1)

    def test_unknown_vs_empty_vs_corrupt(self):
        self.assertIsNone(capital_quote_sign_metrics({})["capital_quote_events"])
        self.assertEqual(capital_quote_sign_metrics({"SIGN": {}})["capital_quote_events"], [])
        value = capital_quote_sign_metrics({"SIGN": [
            {"name": "CQ|R|xxx|4|1|1"},
            {"name": "CQ|A|1|2|1|1"},
        ]})
        self.assertEqual(value["capital_quote_invalid"], 1)
        self.assertEqual(value["capital_quote_by_mode"]["air"]["actual_success"], 2)

    def test_dict_chunk_and_comparable_sample_counter(self):
        metrics = capital_quote_sign_metrics({"SIGN": {
            "1": {"owner": 0, "name": "CQ|D|21000|12000|1|0"},
            "2": {"owner": 0, "name": "CQ|D|21000|22000|1|1"},
        }})
        self.assertEqual(metrics["capital_quote_by_mode"]["road"]["success_events"], 2)
        self.assertEqual(metrics["capital_quote_by_mode"]["road"]["max_samples_learned"], 1)
        # Succes observe n'implique pas un succes utilise pour apprendre.
        self.assertEqual(metrics["capital_quote_by_mode"]["road"]["quoted_success"], 42000)


if __name__ == "__main__":
    unittest.main()
