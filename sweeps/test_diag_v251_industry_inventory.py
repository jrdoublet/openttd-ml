"""Host-only V251 log reader fixtures; never starts OpenTTD or edits the AI."""

import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from diag_v251_industry_inventory import analyse_campaign, main, read_inventory


SETTING = "scope=setting raw_industry_construction=0 valid=1"
FACTORY = (
    "scope=type type=6 name=Factory can_build=1 can_prospect=0 cost=609375 "
    "raw=0 proc=1 produced=GOOD accepted=STEL,GRAI,LVST raw_industry_construction=0"
)
MINE = (
    "scope=type type=0 name=Coal_Mine can_build=0 can_prospect=0 cost=-1 "
    "raw=1 proc=0 produced=COAL accepted=- raw_industry_construction=0"
)


def log(*records):
    return "".join(
        "[2026-10-20 12:31:23] dbg: [script:4] [0] [I] "
        "OPEX 1970-1-1 V251_INDUSTRY_TYPE " + record + "\n"
        for record in records
    )


def write_log(directory, name, content):
    target = Path(directory) / name
    if name.endswith(".gz"):
        with gzip.open(target, "wt", encoding="utf-8") as stream:
            stream.write(content)
    else:
        target.write_text(content, encoding="utf-8")
    return target


class V251IndustryInventoryTest(unittest.TestCase):
    def test_parses_setting_capabilities_cargos_and_type_cost_not_site(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_log(folder, "reference_seed42_r0.log", log(SETTING, FACTORY, MINE))
            actual = read_inventory(path)
            report = analyse_campaign(folder)
        factory = actual["types"]["6"]
        mine = actual["types"]["0"]
        self.assertEqual(actual["setting"], {"valid": True, "raw_industry_construction": 0})
        self.assertEqual(factory["produced"], ["GOOD"])
        self.assertEqual(factory["accepted"], ["STEL", "GRAI", "LVST"])
        self.assertTrue(factory["proc"])
        self.assertEqual(factory["cost"], 609375)
        self.assertEqual(factory["cost_valid"], True)
        self.assertEqual(mine["accepted"], [])
        self.assertFalse(mine["can_build"])
        self.assertEqual(mine["cost_reported"], -1)
        self.assertFalse(mine["cost_valid"])
        self.assertIsNone(mine["cost"])
        run = report["runs"][0]
        self.assertEqual(run["status"], "observed")
        self.assertEqual((run["arm"], run["seed"], run["repetition"]), ("reference", 42, 0))
        self.assertEqual(run["counts"]["n_types_observed"], 2)
        self.assertEqual(run["counts"]["n_types_can_build"], 1)
        self.assertEqual(run["counts"]["n_types_can_prospect"], 0)
        self.assertEqual(run["counts"]["build_allowed_type_costs"], {
            "n": 1, "min": 609375, "median": 609375, "max": 609375,
        })
        self.assertIsNone(run["physical_site_buildable"])
        self.assertIsNone(run["profitability"])
        self.assertIsNone(report["physical_sites_verified"])
        json.dumps(report, allow_nan=False)

    def test_unobserved_log_does_not_mean_zero_buildable_types(self):
        with tempfile.TemporaryDirectory() as folder:
            write_log(folder, "reference_seed42_r0.log", "OPEX 1970-1-1 SETTINGS xxx=0\n")
            report = analyse_campaign(folder)
        run = report["runs"][0]
        self.assertEqual(report["n_runs_unobserved"], 1)
        self.assertEqual(run["status"], "unobserved")
        self.assertIsNone(run["setting"])
        self.assertIsNone(run["counts"])
        self.assertIsNone(run["types"])
        self.assertIsNone(report["type_observations_can_build"])

    def test_partial_missing_fields_and_missing_setting_remain_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            write_log(folder, "reference_seed3_r0.log",
                      log("scope=type type=17 name=Unknown can_build=1"))
            report = analyse_campaign(folder)
        run = report["runs"][0]
        item = run["types"]["17"]
        self.assertEqual(run["status"], "partial")
        self.assertIsNone(run["setting"])
        self.assertIsNone(item["can_prospect"])
        self.assertIsNone(item["cost"])
        self.assertIsNone(item["cost_valid"])
        self.assertIsNone(item["produced"])
        self.assertIsNone(item["accepted"])
        self.assertIsNone(item["raw_industry_construction"])
        self.assertEqual(run["counts"]["n_types_can_build"], 1)
        self.assertEqual(run["counts"]["n_types_valid_cost"], 0)
        self.assertEqual(run["counts"]["n_types_build_allowed_with_valid_cost"], 0)

    def test_present_setting_does_not_hide_partial_type_record(self):
        with tempfile.TemporaryDirectory() as folder:
            write_log(folder, "reference_seed3_r0.log",
                      log(SETTING, "scope=type type=17 name=Unknown can_build=1"))
            run = analyse_campaign(folder)["runs"][0]
        self.assertEqual(run["status"], "partial")
        self.assertIn("can_prospect", run["missing_type_fields"]["17"])
        self.assertIn("produced", run["missing_type_fields"]["17"])
        self.assertEqual(run["counts"]["n_types_can_build"], 1)
        self.assertEqual(run["counts"]["n_types_can_prospect"], 0)
        self.assertEqual(run["counts"]["n_types_can_prospect_unknown"], 1)
        self.assertEqual(run["counts"]["n_types_valid_cost_unknown"], 1)

    def test_setting_only_is_partial_and_zero_cost_is_observed_not_positive(self):
        with tempfile.TemporaryDirectory() as folder:
            write_log(folder, "reference_seed4_r0.log", log(SETTING))
            write_log(folder, "reference_seed5_r0.log",
                      log(SETTING, "scope=type type=2 name=Free can_build=1 "
                          "can_prospect=1 cost=0 produced=- accepted=- "
                          "raw_industry_construction=0"))
            report = analyse_campaign(folder)
        partial, free = report["runs"]
        self.assertEqual(partial["status"], "partial")
        self.assertEqual(partial["counts"]["n_types_observed"], 0)
        self.assertEqual(free["counts"]["n_types_can_prospect"], 1)
        self.assertEqual(free["types"]["2"]["cost_reported"], 0)
        self.assertFalse(free["types"]["2"]["cost_valid"])
        self.assertIsNone(free["types"]["2"]["cost"])
        self.assertEqual(free["counts"]["n_types_can_build"], 1)
        self.assertEqual(free["counts"]["n_types_valid_cost"], 0)
        self.assertEqual(free["counts"]["n_types_build_allowed_with_valid_cost"], 0)
        self.assertEqual(free["counts"]["build_allowed_type_costs"], {
            "n": 0, "min": None, "median": None, "max": None,
        })
        self.assertEqual(free["types"]["2"]["produced"], [])

    def test_missing_setting_value_is_unknown_not_a_contradiction(self):
        with tempfile.TemporaryDirectory() as folder:
            write_log(folder, "reference_seed42_r0.log",
                      log("scope=setting valid=1", FACTORY))
            report = analyse_campaign(folder)
        run = report["runs"][0]
        self.assertIsNone(run["setting"]["raw_industry_construction"])
        self.assertEqual(run["types"]["6"]["raw_industry_construction"], 0)

    def test_invalid_setting_never_makes_complete_type_inventory_observed(self):
        with tempfile.TemporaryDirectory() as folder:
            write_log(folder, "reference_seed42_r0.log",
                      log("scope=setting valid=0 raw_industry_construction=0",
                          FACTORY, MINE))
            report = analyse_campaign(folder)
        run = report["runs"][0]
        self.assertEqual(run["status"], "partial")
        self.assertEqual(report["n_runs_partial"], 1)
        self.assertEqual(run["setting"], {
            "valid": False, "raw_industry_construction": None,
        })
        self.assertEqual(run["counts"]["n_types_observed"], 2)
        self.assertEqual(run["counts"]["n_types_can_build"], 1)
        self.assertIsNone(run["physical_site_buildable"])

    def test_text_and_gzip_duplicate_are_one_run_and_gzip_only_works(self):
        with tempfile.TemporaryDirectory() as folder:
            plain = write_log(folder, "reference_seed42_r1.log", log(SETTING, FACTORY))
            write_log(folder, "reference_seed42_r1.log.gz", log(SETTING, FACTORY))
            report = analyse_campaign(folder)
            self.assertEqual(report["n_runs"], 1)
            self.assertEqual(len(report["runs"][0]["source_files"]), 2)
            plain.unlink()
            zipped_only = analyse_campaign(folder)
        self.assertEqual(zipped_only["n_runs"], 1)
        self.assertEqual(zipped_only["runs"][0]["seed"], 42)
        self.assertEqual(zipped_only["runs"][0]["counts"]["n_types_observed"], 1)

    def test_conflicting_text_gzip_is_fatal_even_with_same_event_count(self):
        with tempfile.TemporaryDirectory() as folder:
            plain = write_log(folder, "reference_seed42_r0.log", log(SETTING, FACTORY))
            zipped = write_log(folder, "reference_seed42_r0.log.gz",
                               log(SETTING, FACTORY.replace("609375", "999999")))
            with self.assertRaisesRegex(ValueError, "conflicting V251 inventories") as caught:
                analyse_campaign(folder)
            self.assertIn(str(plain), str(caught.exception))
            self.assertIn(str(zipped), str(caught.exception))

    def test_same_v251_events_but_different_other_log_bytes_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            write_log(folder, "reference_seed42_r0.log",
                      log(SETTING, FACTORY) + "PROJECT_SELECTED YES\n")
            write_log(folder, "reference_seed42_r0.log.gz",
                      log(SETTING, FACTORY) + "PROJECT_SELECTED NO\n")
            with self.assertRaisesRegex(ValueError, "conflicting V251 inventories"):
                analyse_campaign(folder)

    def test_alias_seed_spelling_is_ambiguous_even_with_equal_events(self):
        with tempfile.TemporaryDirectory() as folder:
            write_log(folder, "reference_seed1_r0.log", log(SETTING, FACTORY))
            write_log(folder, "reference_seed01_r0.log", log(SETTING, FACTORY))
            with self.assertRaisesRegex(ValueError, "ambiguous V251 game identity"):
                analyse_campaign(folder)

    def test_missing_v251_in_one_copy_conflicts_with_observed_copy(self):
        with tempfile.TemporaryDirectory() as folder:
            write_log(folder, "reference_seed42_r0.log", log(SETTING, FACTORY))
            write_log(folder, "reference_seed42_r0.log.gz", "no events\n")
            with self.assertRaisesRegex(ValueError, "conflicting V251 inventories"):
                analyse_campaign(folder)

    def test_arms_repetitions_and_seeds_are_distinct_not_deduplicated(self):
        with tempfile.TemporaryDirectory() as folder:
            for name in (
                "reference_seed42_r0.log", "variant_seed42_r0.log",
                "reference_seed42_r1.log", "reference_seed100_r0.log",
            ):
                write_log(folder, name, log(SETTING, FACTORY))
            report = analyse_campaign(folder)
        self.assertEqual(report["n_runs"], 4)
        self.assertEqual(report["distinct_seeds"], [42, 100])
        self.assertEqual(report["type_observations_can_build"], 4)
        self.assertEqual({
            (r["arm"], r["seed"], r["repetition"]) for r in report["runs"]
        }, {
            ("reference", 42, 0), ("variant", 42, 0),
            ("reference", 42, 1), ("reference", 100, 0),
        })

    def test_conflicting_setting_or_type_within_one_log_fails_closed(self):
        cases = (
            log(SETTING, SETTING.replace("=0 valid", "=1 valid")),
            log(SETTING, FACTORY, FACTORY.replace("can_build=1", "can_build=0")),
            log(SETTING, FACTORY.replace("raw_industry_construction=0",
                                        "raw_industry_construction=2")),
            log(SETTING, "scope=type type=6 type=7 can_build=1"),
        )
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reference_seed42_r0.log"
            for content in cases:
                with self.subTest(content=content[-100:]):
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        read_inventory(path)

    def test_malformed_values_and_unidentified_logs_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_log(folder, "reference_seed42_r0.log", log(SETTING, FACTORY))
            for wrong in ("cost=nonsense", "can_build=7", "type=none"):
                with self.subTest(wrong=wrong):
                    faulty = FACTORY.replace("cost=609375", "cost=nonsense") if wrong.startswith("cost") else (
                        FACTORY.replace("can_build=1", wrong) if wrong.startswith("can_build")
                        else FACTORY.replace("type=6", wrong)
                    )
                    path.write_text(log(SETTING, faulty), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        analyse_campaign(folder)
            path.unlink()
            write_log(folder, "unidentified.log", log(SETTING, FACTORY))
            with self.assertRaisesRegex(ValueError, "cannot establish arm/seed/repetition"):
                analyse_campaign(folder)

    def test_unknown_v251_fields_and_broken_tokens_are_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "reference_seed42_r0.log"
            for record in (
                FACTORY + " other=42",
                FACTORY + " unexpected",
                SETTING + " extra=1",
            ):
                with self.subTest(record=record):
                    path.write_text(log(SETTING, record), encoding="utf-8")
                    with self.assertRaises(ValueError):
                        read_inventory(path)

    def test_other_company_ignored_malformed_opex_event_refused(self):
        other = "[1] [I] OPEX 1970-1-1 V251_INDUSTRY_TYPE " + FACTORY + "\n"
        with tempfile.TemporaryDirectory() as folder:
            path = write_log(folder, "reference_seed42_r0.log", other + log(SETTING))
            self.assertEqual(read_inventory(path)["types"], {})
            path.write_text(log(SETTING) + "[0] [I] V251_INDUSTRY_TYPE broken\n",
                            encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "malformed company-0"):
                read_inventory(path)

    def test_cli_prints_json_and_never_writes_an_output_file(self):
        with tempfile.TemporaryDirectory() as folder:
            write_log(folder, "reference_seed42_r0.log", log(SETTING, FACTORY))
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["--campaign", f"smoke={folder}"]), 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result["campaigns"]["smoke"]["n_runs"], 1)
            self.assertEqual(sorted(p.name for p in Path(folder).iterdir()),
                             ["reference_seed42_r0.log"])


if __name__ == "__main__":
    unittest.main()
