"""Host-only V253 AIR_BUILD / V252_REPLACE lifecycle fixtures."""

import gzip
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

    def test_different_engine_at_replacement_is_not_silently_equated(self):
        path = self.write("reference_seed42_r0.log", build(engine=228) + replace(old=223))
        row = analyze([path])["games"][0]
        self.assertEqual(row["first_replacement_old_disagrees_initial"], 1)
        self.assertEqual(row["first_replacement_initial_to_new"], {"228->217": 1})
        self.assertEqual(row["first_replacement_old_to_new"], {"223->217": 1})

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


if __name__ == "__main__":
    unittest.main()
