import unittest

from analyse_projects_passes_early4 import distribution, parse_events, summarize


class ProjectPassAnalysisTests(unittest.TestCase):
    def test_distribution_interpolates_quantiles_and_preserves_zero(self):
        self.assertEqual(distribution([])["median"], None)
        self.assertEqual(distribution([0, 10, 30, 60, 100])["p95"], 92)
        self.assertEqual(distribution([0, 0, 0])["total"], 0)

    def test_separate_measurement_families_and_incomplete_early_return(self):
        log = [
            "[script:4] [0] [I] OPEX 1973-1-2 PROJECTS_COST build_ops=100 fleet_ops=20 regen_ops=300 regen=incremental built=1 stop=list_end",
            "[script:4] [0] [I] OPEX 1973-1-2 SELECTION_LIGHT path=incremental ops=200 considered=4 selected=2",
            "[script:4] [0] [I] OPEX 1973-1-2 SCHED_IDLE t=projects w=1 r=projects_useful op=1000",
            "[script:4] [0] [I] OPEX 1973-1-3 SCHED_IDLE t=projects w=0 r=projects_empty op=200",
        ]
        report = summarize(parse_events(log))["1973"]
        self.assertEqual(report["projects_cost"]["built_count"], 1)
        self.assertEqual(report["projects_cost"]["cost_all_components_non_exclusive_vs_c39"]["total"], 420)
        self.assertEqual(report["selection"]["incremental"]["ops"]["total"], 200)
        self.assertEqual(report["scheduler"]["projects_empty"]["ops"]["total"], 200)
        self.assertFalse(report["completeness"]["same_count"])


if __name__ == "__main__":
    unittest.main()
