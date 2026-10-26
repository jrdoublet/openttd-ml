"""Host-only V253 AIR_BUILD / V252_REPLACE lifecycle fixtures."""

import gzip
from datetime import date
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_v253_initial_engine_lifecycle import analyze


def build(line=3, engine=223, year=1970, arm=0, extra=""):
    return (f"[0] [I] OPEX {year}-2-5 AIR_BUILD arm=hubsite line={line} "
            f"src=1 dst=2 dist=80 cost=50000 profit=70000 planes=1 "
            f"engine={engine}{extra}\n").replace("[0] [I]", f"[{arm}] [I]")


def replace(line=3, old=223, new=217, year=1974, arm=0):
    return (f"[0] [I] OPEX {year}-5-1 V252_REPLACE line={line} "
            f"old_engine={old} new_engine={new} price=5000 age=1200 profit=1000\n"
            ).replace("[0] [I]", f"[{arm}] [I]")


class V253EngineLifecycleTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def write(self, name, body, root=None):
        path = (root or self.root) / name
        if name.endswith(".gz"):
            with gzip.open(path, "wt", encoding="utf-8") as stream:
                stream.write(body)
        else:
            path.write_text(body, encoding="utf-8")
        return path

    def test_first_replacement_per_line_and_multiple_events(self):
        path = self.write("reference_seed42_r0.log", build() + replace() +
                          replace(old=217, new=218, year=1976))
        row = analyze([path])["games"][0]
        self.assertEqual(row["replacement_events"], 2)
        self.assertEqual(row["replacements_with_prior_build"], 2)
        self.assertEqual(row["distinct_built_lines_with_replacement"], 1)
        self.assertEqual(row["first_replacement_initial_to_new"], {"223->217": 1})
        self.assertEqual(row["first_replacement_old_to_new"], {"223->217": 1})
        expected = (date(1974, 5, 1) - date(1970, 2, 5)).days
        self.assertEqual(row["first_replacement_delay_days_by_initial_engine"], {
            "223": {"n": 1, "min": expected, "median": expected, "max": expected},
        })
        self.assertEqual(row["distinct_built_lines_without_observed_replacement"], 0)

    def test_unmatched_and_missing_line_are_separate(self):
        missing = replace().replace("line=3", "line=bad")
        path = self.write("reference_seed42_r0.log", build() + replace(line=4) + missing)
        row = analyze([path])["games"][0]
        self.assertEqual(row["replacements_without_prior_build"], 1)
        self.assertEqual(row["replacements_missing_line"], 1)
        self.assertEqual(row["replacements_with_prior_build"], 0)

    def test_built_after_replacement_cannot_join(self):
        path = self.write("reference_seed42_r0.log", build(year=1978) + replace(year=1974))
        self.assertEqual(analyze([path])["games"][0]["replacements_without_prior_build"], 1)

    def test_same_year_replacement_before_build_is_not_a_prior_build(self):
        path = self.write("reference_seed42_r0.log", replace(year=1974) + build(year=1974))
        row = analyze([path])["games"][0]
        self.assertEqual(row["replacements_without_prior_build"], 1)
        self.assertEqual(row["replacements_with_prior_build"], 0)

    def test_timestamp_backward_same_year_fails_even_when_logs_are_in_order(self):
        built_late = build(year=1974).replace("1974-2-5", "1974-10-5")
        path = self.write("reference_seed42_r0.log", built_late + replace(year=1974))
        row = analyze([path])["games"][0]
        self.assertEqual(row["replacements_without_prior_build"], 1)
        self.assertEqual(row["distinct_built_lines_without_observed_replacement"], 1)
        self.assertEqual(row["first_replacement_delay_days_by_initial_engine"], {})

    def test_different_engine_at_replacement_is_not_silently_equated(self):
        path = self.write("reference_seed42_r0.log", build(engine=228) + replace(old=223))
        row = analyze([path])["games"][0]
        self.assertEqual(row["first_replacement_old_disagrees_initial"], 1)
        self.assertEqual(row["first_replacement_initial_to_new"], {"228->217": 1})
        self.assertEqual(row["first_replacement_old_to_new"], {"223->217": 1})
        differences = analyze([path])["by_arm"]["reference"]["first_replacement_disagreements"]
        self.assertEqual(len(differences), 1)
        self.assertEqual((differences[0]["seed"], differences[0]["line"]), (42, 3))
        self.assertEqual((differences[0]["initial_engine"], differences[0]["old_engine"]),
                         (228, 223))
        self.assertEqual((differences[0]["build_date"], differences[0]["replacement_date"]),
                         ("1970-02-05", "1974-05-01"))

    def test_unreplaced_built_lines_have_unknown_fate(self):
        path = self.write("reference_seed42_r0.log", build(line=3) + build(line=4) +
                          replace(line=3))
        arm = analyze([path])["by_arm"]["reference"]
        self.assertEqual(arm["distinct_built_lines_with_replacement"], 1)
        self.assertEqual(arm["distinct_built_lines_without_observed_replacement"], 1)
        self.assertEqual(arm["first_replacement_delay_days_by_initial_engine"]["223"]["n"], 1)

    def test_invalid_engine_retains_build_and_unknown_engine(self):
        path = self.write("reference_seed42_r0.log", build(engine="garbled") + replace())
        row = analyze([path])["games"][0]
        self.assertEqual(row["builds_missing_engine"], 1)
        self.assertEqual(row["first_replacement_initial_to_new"], {})

    def test_duplicate_build_line_or_field_is_rejected(self):
        p = self.write("reference_seed42_r0.log", build() + build())
        with self.assertRaisesRegex(ValueError, "ligne locale repetee"):
            analyze([p])
        self.write("reference_seed42_r0.log", build(extra=" engine=217"))
        with self.assertRaisesRegex(ValueError, "champ duplique"):
            analyze([p])

    def test_game_identity_and_arm_counts_are_not_collapsed(self):
        self.write("reference_seed42_r0.log", build() + replace())
        self.write("reference_seed42_r1.log", build() + replace())
        self.write("variant_seed42_r0.log", build(engine=228) + replace())
        row = analyze([self.root])
        self.assertEqual(row["logical_games"], 3)
        self.assertEqual(row["by_arm"]["reference"]["distinct_built_lines_with_replacement"], 2)
        self.assertEqual(row["by_arm"]["variant"]["builds_by_initial_engine"], {"228": 1})

    def test_copies_identical_and_conflicting_fail_closed(self):
        body = build() + replace()
        a = self.write("reference_seed42_r0.log", body)
        b = self.write("reference_seed42_r0.log.gz", body)
        self.assertEqual(analyze([a, b, self.root])["logical_games"], 1)
        self.write("reference_seed42_r0.log.gz", build(engine=228) + replace())
        with self.assertRaisesRegex(ValueError, "contradictoires"):
            analyze([self.root])

    def test_other_company_and_skips_are_ignored(self):
        p = self.write("reference_seed42_r0.log", build(arm=1) + replace(arm=1) +
                       "[0] [I] OPEX 1973-1-1 V252_SKIP reason=loan\n")
        row = analyze([p])["games"][0]
        self.assertEqual(row["replacement_events"], 0)
        self.assertEqual(row["build_events"], 0)

    def test_uninstrumented_active_game_has_unknown_lifecycle_coverage(self):
        path = self.write("reference_seed42_r0.log",
                          "[0] [I] OPEX 1971-1-1 AIR_LINE_REVENUE line=9 profit=1000\n")
        report = analyze([path])
        game = report["games"][0]
        self.assertEqual(game["build_events"], 0)
        self.assertEqual(game["replacement_events"], 0)
        self.assertFalse(game["air_build_marker_observed"])
        self.assertFalse(game["v252_marker_observed"])
        self.assertEqual(game["lifecycle_coverage"], "unknown_no_markers")
        self.assertEqual(report["by_arm"]["reference"]["lifecycle_coverage"], "unknown")

    def test_observed_creation_and_v252_skip_are_both_markers_without_replacement(self):
        path = self.write("reference_seed42_r0.log", build() +
                          "[0] [I] OPEX 1974-1-1 V252_SKIP reason=loan\n")
        report = analyze([path])
        game = report["games"][0]
        self.assertEqual(game["build_events"], 1)
        self.assertEqual(game["replacement_events"], 0)
        self.assertTrue(game["v252_marker_observed"])
        self.assertEqual(game["lifecycle_coverage"], "both_markers_observed")
        self.assertEqual(report["by_arm"]["reference"]["lifecycle_coverage"],
                         "both_markers_observed")

    def test_mixed_instrumented_and_uninstrumented_games_are_partial(self):
        self.write("reference_seed42_r0.log", build() + replace())
        self.write("reference_seed7_r0.log", "[0] [I] OPEX 1971-1-1 C121_HUB_DELAY n=1\n")
        self.write("reference_seed100_r0.log", build(line=4))
        report = analyze([self.root])
        arm = report["by_arm"]["reference"]
        self.assertEqual(arm["logical_games"], 3)
        self.assertEqual(arm["build_events"], 2)
        self.assertEqual(arm["replacement_events"], 1)
        self.assertEqual(arm["games_with_both_lifecycle_markers"], 1)
        self.assertEqual(arm["games_with_partial_lifecycle_markers"], 1)
        self.assertEqual(arm["games_without_lifecycle_markers"], 1)
        self.assertEqual(arm["lifecycle_coverage"], "partial")


if __name__ == "__main__":
    unittest.main()
