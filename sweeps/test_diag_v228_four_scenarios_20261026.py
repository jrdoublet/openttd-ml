"""Host-only V228 four-world contracts; no engine and no historical verdicts."""

import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_v228_four_scenarios_20261026 import compare_four, main
from sweeps.diag_v228_map_coverage_20261025 import compare
from sweeps.test_v228_map_coverage_20261025 import _reference


class FourScenarioContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.inputs = {
            "y1950": root / "1950_256.json",
            "y1970": root / "1970_256.json",
            "y1990": root / "1990_256.json",
            "map1024": root / "1970_1024.json",
        }
        self.data = {
            "y1950": _reference(8, 1950),
            "y1970": _reference(8, 1970),
            "y1990": _reference(8, 1990),
            "map1024": _reference(10, 1970),
        }
        self.output = root / "reports" / "four.json"

    def write(self):
        for key, path in self.inputs.items():
            path.write_text(json.dumps(self.data[key]), encoding="utf-8")

    def compare(self):
        self.write()
        return compare_four(**self.inputs)

    def test_four_healthy_scenarios_20x10_and_descriptive_stats(self):
        report = self.compare()
        self.assertEqual(len(report["seeds"]), 20)
        self.assertEqual(set(report["scenarios"]), set(self.inputs))
        for key, start, exponent in (
            ("y1950", 1950, 8), ("y1970", 1970, 8),
            ("y1990", 1990, 8), ("map1024", 1970, 10),
        ):
            with self.subTest(key=key):
                values = report["scenarios"][key]
                self.assertEqual(values["pairs"], 20)
                self.assertEqual(values["paired_ratios_eligible"], 20)
                self.assertEqual(values["start_year"], start)
                self.assertEqual(values["last_year"], start + 9)
                self.assertEqual(values["last_checkpoint"], f"{start + 9}-12-01")
                self.assertEqual(values["map_size_exponent"], exponent)
                self.assertEqual(values["profit_year_median_opex"], 118050)
                self.assertEqual(values["profit_year_median_aaahogex"], 177075)
                self.assertEqual(values["median_opex_vehicles"], 5)
                self.assertEqual(values["median_aaa_vehicles"], 12)
                self.assertEqual(values["profit_year_mean_opex"],
                                 report["scenarios"]["y1970"]["profit_year_mean_opex"])
        self.assertIn("independantes", report["interpretation"])
        self.assertIn("Aucun appariement contrefactuel", report["interpretation"])
        self.assertEqual(len(report["sources"]), 4)

    def test_1970_256_vs_1024_old_results_unchanged(self):
        self.write()
        former = compare(self.inputs["y1970"], self.inputs["map1024"])
        extended = compare_four(**self.inputs)
        for key, old_key in (("y1970", "map256"), ("map1024", "map1024")):
            for field, value in former[old_key].items():
                self.assertEqual(extended["scenarios"][key][field], value)
        self.assertEqual(former["map256"]["opex_to_aaa_ratio_of_means_pct"], 66.667)

    def test_all_scenarios_must_share_bundle(self):
        self.data["y1990"]["source_bundle_sha256"] = "another-bundle"
        for row in self.data["y1990"]["summary"] + self.data["y1990"]["games"]:
            row["source_bundle_sha256"] = "another-bundle"
        with self.assertRaisesRegex(ValueError, "bundle ou reglage divergent"):
            self.compare()

    def test_policies_aaa_settings_runtime_must_match(self):
        cases = (
            ("policies", [{"id": "reference", "role": "reference",
                           "explicit_settings": [["probes", 2]]}]),
            ("aaahogex_settings", ["different"]),
            ("openttd_version", "16.0"),
            ("opengfx_version", "8.0"),
            ("design", "not the same duel"),
        )
        for field, value in cases:
            with self.subTest(field=field):
                self.data["y1990"] = _reference(8, 1990)
                self.data["y1990"][field] = value
                with self.assertRaisesRegex(ValueError, "bundle ou reglage divergent"):
                    self.compare()

    def test_reject_wrong_year_terminal_checkpoint_and_date(self):
        for key, field, value, reason in (
            ("y1950", "start_year", 1970, "horizon"),
            ("y1990", "expected_last_year", 1979, "horizon"),
            ("y1950", "expected_last_checkpoint", "1979-12-01", "manifeste"),
        ):
            with self.subTest(key=key, field=field):
                self.data[key] = _reference(8, 1950 if key == "y1950" else 1990)
                self.data[key][field] = value
                with self.assertRaisesRegex(ValueError, reason):
                    self.compare()
        self.data["y1950"] = _reference(8, 1950)
        self.data["y1950"]["summary"][0]["last_date"] = "1959-11-01"
        with self.assertRaisesRegex(ValueError, "jeu incomplet ou malsain"):
            self.compare()

    def test_reject_bad_game_even_if_summary_healthy(self):
        self.data["y1950"]["games"][0]["game_ok"] = False
        with self.assertRaisesRegex(ValueError, "partie manquante ou malsaine"):
            self.compare()
        self.data["y1950"] = _reference(8, 1950)
        self.data["y1950"]["games"].pop()
        with self.assertRaisesRegex(ValueError, "20 parties moteur manquantes"):
            self.compare()

    def test_reject_failed_or_incomplete_company_summary(self):
        self.data["y1990"]["summary"][0]["script_errors"] = ["script error"]
        with self.assertRaisesRegex(ValueError, "jeu incomplet ou malsain"):
            self.compare()
        self.data["y1990"] = _reference(8, 1990)
        self.data["y1990"]["summary"][0]["profit_year_quarters_valid"] = 3
        with self.assertRaisesRegex(ValueError, "jeu incomplet ou malsain"):
            self.compare()
        self.data["y1990"] = _reference(8, 1990)
        self.data["y1990"]["failed_runs"] = ["seed42"]
        with self.assertRaisesRegex(ValueError, "failed_runs"):
            self.compare()

    def test_reject_swapped_map_dimensions(self):
        self.data["y1990"]["map_size"] = 10
        with self.assertRaisesRegex(ValueError, "y1990 map_size doit valoir 8"):
            self.compare()
        self.data["y1990"] = _reference(8, 1990)
        self.data["map1024"]["map_size"] = 8
        with self.assertRaisesRegex(ValueError, "map1024 map_size doit valoir 10"):
            self.compare()

    def test_reject_reused_campaign_identity_or_missing_runtime(self):
        self.data["map1024"]["campaign_id"] = self.data["y1970"]["campaign_id"]
        for row in self.data["map1024"]["games"] + self.data["map1024"]["summary"]:
            row["campaign_id"] = self.data["map1024"]["campaign_id"]
            row["game_id"] = row["game_id"].replace(
                "fixture-1970-map10", "fixture-1970-map8"
            )
        with self.assertRaisesRegex(ValueError, "campaign_id reutilise"):
            self.compare()
        self.data["map1024"] = _reference(10, 1970)
        for row in self.data.values():
            row.pop("openttd_version")
        with self.assertRaisesRegex(ValueError, "runtime incomplete"):
            self.compare()

    def test_cli_creates_json_and_never_overwrites_existing_output(self):
        self.write()
        args = [part for flag, key in (
            ("--y1950", "y1950"), ("--y1970", "y1970"),
            ("--y1990", "y1990"), ("--map1024", "map1024"),
        ) for part in (flag, str(self.inputs[key]))]
        args.extend(("--out", str(self.output)))
        console = io.StringIO()
        with contextlib.redirect_stdout(console):
            main(args)
        self.assertTrue(self.output.is_file())
        created = self.output.read_text(encoding="utf-8")
        payload = json.loads(created)
        self.assertEqual(set(payload["scenarios"]), set(self.inputs))
        self.assertEqual(set(json.loads(console.getvalue())), set(self.inputs))
        with self.assertRaises(SystemExit) as raised:
            main(args)
        self.assertNotEqual(raised.exception.code, 0)
        self.assertEqual(self.output.read_text(encoding="utf-8"), created)

    def test_missing_1950_json_does_not_write_report_or_infer_data(self):
        self.write()
        self.inputs["y1950"].unlink()
        with self.assertRaises(FileNotFoundError):
            compare_four(**self.inputs)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
