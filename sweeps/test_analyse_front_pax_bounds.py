"""Tests contractuels du marqueur Squirrel FRONT_PAX_BOUNDS (sans Docker)."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyse_front_pax_bounds import (
    analyze_files,
    expand_log_patterns,
    parse_log_lines,
    render_markdown,
    source_identity,
)


# Copie textuelle de l'ordre et des noms de champs du OpexDecide FRONT_PAX_BOUNDS
# r3, y compris sentinelle -1 et les trois nouveaux champs rail.
PAYLOAD = (
    "road_reason=delta_nonpositive road_raw=-1 road_delta=0 road_num=6100 "
    "road_denom=0 road_M=100 rail_raw=512 rail_clamp=rail_max "
    "rail_model=rail_faster rail_bound=v294 rail_source=200 "
    "rail_road_floor=0 rail_map_cap=0 rail_max=200 train=13 plane=19 "
    "airport=2 air_div=4 rail_tau100=32 air_tau100=70 "
    "rail_dwell100=54 air_fixed100=2619"
)
OTHER_PAYLOAD = PAYLOAD.replace(
    "road_reason=delta_nonpositive", "road_reason=minimum"
).replace(
    "road_raw=-1", "road_raw=78"
).replace("rail_raw=512", "rail_raw=78").replace(
    "rail_clamp=rail_max", "rail_clamp=none"
).replace("rail_model=rail_faster", "rail_model=crossing").replace(
    "rail_tau100=32 air_tau100=70", "rail_tau100=77 air_tau100=20"
).replace("air_fixed100=2619", "air_fixed100=1513")


def log_line(day="1970-01-02", payload=PAYLOAD, company=0):
    return f"[script:4] [{company}] [I] OPEX {day} FRONT_PAX_BOUNDS {payload}\n"


class FrontPaxBoundsTest(unittest.TestCase):
    def test_realistic_engine_prefix_dates_and_numeric_fields(self):
        lines = [
            "[script:4] [0] [I] OPEX 1970-1-2 EPOCH_BOUNDS roadMin=7\n",
            log_line("1970-1-2"),
            log_line("1971-12-31", OTHER_PAYLOAD),
        ]
        rows, errors, markers = parse_log_lines(lines, "reference_seed42_r0.log")
        self.assertEqual((len(rows), len(errors), markers), (2, 0, 2))
        first, second = rows
        self.assertEqual((first["seed"], first["run"], first["date"]),
                         (42, "reference:r0", "1970-01-02"))
        self.assertEqual(first["road_reason"], "delta_nonpositive")
        self.assertEqual(first["rail_clamp"], "rail_max")
        self.assertEqual(first["rail_model"], "rail_faster")
        self.assertEqual(first["rail_bound"], "v294")
        self.assertEqual(first["road_raw"], -1)
        self.assertEqual(first["road_denom"], 0)
        self.assertEqual(first["rail_raw"], 512)
        self.assertEqual(first["rail_source"], 200)
        self.assertEqual(first["rail_road_floor"], 0)
        self.assertEqual(first["rail_map_cap"], 0)
        self.assertEqual(first["rail_max"], 200)
        self.assertEqual(first["rail_tau100"], 32)
        self.assertEqual(first["air_tau100"], 70)
        self.assertEqual(first["rail_dwell100"], 54)
        self.assertEqual(first["air_fixed100"], 2619)
        self.assertEqual(second["rail_model"], "crossing")
        self.assertEqual(second["air_fixed100"], 1513)

    def test_malformed_prefix_date_fields_and_values_are_rejected(self):
        malformed = [
            "OPEX NOT_A_DATE FRONT_PAX_BOUNDS " + PAYLOAD,
            "OPEX 1970-02-30 FRONT_PAX_BOUNDS " + PAYLOAD,
            log_line(payload=PAYLOAD + " road_raw=9"),
            log_line(payload=PAYLOAD.replace("rail_max=200 ", "")),
            log_line(payload=PAYLOAD.replace("rail_raw=512", "rail_raw=7.5")),
            log_line(payload=PAYLOAD.replace("air_div=4", "air_div=NaN")),
            log_line(payload=PAYLOAD + " garbage"),
            log_line(payload=PAYLOAD.replace("rail_model=rail_faster",
                                              "rail_model=unknown")),
            log_line(payload=PAYLOAD.replace("rail_source=200", "rail_source=-2")),
            log_line(payload=PAYLOAD.replace("rail_road_floor=0", "rail_road_floor=2")),
            log_line(payload=PAYLOAD.replace("rail_map_cap=0", "rail_map_cap=-1")),
            log_line(payload=PAYLOAD.replace("road_raw=-1", "road_raw=-2")),
            log_line(payload=PAYLOAD.replace("rail_source=200 ", "")),
            log_line(payload=PAYLOAD.replace("rail_clamp=rail_max",
                                              "rail_clamp=rail_max+map_span")),
            log_line(payload=PAYLOAD.replace("rail_clamp=rail_max",
                                              "rail_clamp=none+road_max")),
            log_line(payload=PAYLOAD.replace("road_reason=delta_nonpositive",
                                              "road_reason=minimum+road_max")),
        ]
        rows, errors, markers = parse_log_lines(malformed, "reference_seed42_r0.log")
        self.assertEqual((len(rows), markers, len(errors)), (0, 16, 16))
        codes = [error["code"] for error in errors]
        self.assertIn("bad_prefix", codes)
        self.assertIn("invalid_date", codes)
        self.assertTrue(all(error["line"] > 0 for error in errors))
        self.assertTrue(any("duplicate_field:road_raw" in e["detail"] for e in errors))
        self.assertTrue(any("missing:rail_max" in e["detail"] for e in errors))
        self.assertTrue(any("invalid_number:rail_raw" in e["detail"] for e in errors))
        self.assertTrue(any("invalid_number:rail_source" in e["detail"] for e in errors))
        self.assertTrue(any("invalid_number:road_raw" in e["detail"] for e in errors))
        self.assertTrue(any("missing:rail_source" in e["detail"] for e in errors))
        self.assertTrue(any("invalid_category:rail_model" in e["detail"] for e in errors))
        self.assertTrue(any("invalid_category:rail_clamp" in e["detail"] for e in errors))

    def test_duplicate_exact_event_ignored_different_event_same_day_kept(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "reference_seed42_r0.log"
            file.write_text(log_line() + log_line() +
                            log_line(payload=OTHER_PAYLOAD), encoding="utf-8")
            report = analyze_files([file], expected_years=range(1970, 1972))
        self.assertEqual(report["files"], 1)
        self.assertEqual(report["events"], 3)
        self.assertEqual(report["unique_events"], 2)
        self.assertEqual(report["duplicates"], 1)
        self.assertEqual(report["parse_errors"], 0)
        self.assertTrue(any(i["code"] == "duplicate_event" for i in report["issues"]))
        row, = report["by_seed_year"]
        self.assertEqual((row["seed"], row["year"], row["n"]), (42, 1970, 2))
        self.assertEqual(row["distinct_dates"], 1)
        self.assertEqual(row["motives"]["road_reason"],
                         {"delta_nonpositive": 1, "minimum": 1})
        self.assertEqual(row["motives"]["rail_clamp"], {"none": 1, "rail_max": 1})
        self.assertEqual(row["causes"]["road_reason"],
                         {"delta_nonpositive": 1, "minimum": 1})
        self.assertEqual(row["causes"]["rail_clamp"], {"rail_max": 1})
        self.assertEqual(row["rail_raw_above_max"], 1)
        self.assertEqual(row["road_raw_unavailable"], 1)
        self.assertEqual(row["road_raw_known"]["median"], 78)
        self.assertEqual(row["values"]["rail_raw"]["median"], 295)
        self.assertEqual(row["values"]["rail_raw_minus_max"]["median"], 95)
        self.assertEqual(row["values"]["rail_tau_gap100"]["median"], 9.5)
        self.assertEqual(report["seed_coverage"][0]["missing_expected_years"], [1971])
        self.assertFalse(report["seed_coverage"][0]["full_year_coverage_proven"])

    def test_reference_variant_and_repeats_never_mix(self):
        with tempfile.TemporaryDirectory() as folder:
            a = Path(folder) / "reference_seed42_r0.log"
            b = Path(folder) / "variant_seed42_r0.log"
            c = Path(folder) / "reference_seed42_r1.log"
            a.write_text(log_line(), encoding="utf-8")
            b.write_text(log_line(), encoding="utf-8")
            c.write_text(log_line(payload=OTHER_PAYLOAD), encoding="utf-8")
            report = analyze_files([a, b, c], expected_years=[1970])
        self.assertEqual(report["duplicates"], 0)
        self.assertEqual(report["unique_events"], 3)
        self.assertEqual(len(report["by_seed_year"]), 3)
        self.assertEqual({row["run"] for row in report["by_seed_year"]},
                         {"reference:r0", "reference:r1", "variant:r0"})
        self.assertTrue(all(row["n"] == 1 for row in report["by_seed_year"]))

    def test_coverage_year_gaps_and_unidentified_seeds(self):
        with tempfile.TemporaryDirectory() as folder:
            known = Path(folder) / "reference_seed100_r0.log"
            unknown = Path(folder) / "custom_engine.log"
            known.write_text(log_line("1970-03-02") + log_line("1972-04-15"),
                             encoding="utf-8")
            unknown.write_text(log_line("1971-01-01"), encoding="utf-8")
            report = analyze_files([known, unknown], expected_years=range(1970, 1974))
        self.assertEqual(report["unidentified_seed_files"], 1)
        self.assertTrue(any(issue["code"] == "unidentified_seed" for issue in report["issues"]))
        covered = next(row for row in report["seed_coverage"] if row["seed"] == 100)
        self.assertEqual(covered["observed_years"], [1970, 1972])
        self.assertEqual(covered["gaps_between_observed_years"], [1971])
        self.assertEqual(covered["missing_expected_years"], [1971, 1973])
        self.assertEqual(sum(r["n"] for r in report["by_seed_year"]), 3)

    def test_source_identity_and_glob_dedup(self):
        self.assertEqual(source_identity("reference_seed42_r0.log"), (42, "reference:r0"))
        self.assertEqual(source_identity("variant_seed100_r1.log"), (100, "variant:r1"))
        self.assertEqual(source_identity("OpexAI_c121_42.log"), (42, "OpexAI_c121:r?"))
        self.assertEqual(source_identity("engine.log"), (None, "engine:r?"))
        with tempfile.TemporaryDirectory() as folder:
            one = Path(folder) / "reference_seed42_r0.log"
            one.write_text(log_line(), encoding="utf-8")
            paths, unmatched = expand_log_patterns([str(one), str(Path(folder) / "*.log")])
        self.assertEqual(len(paths), 1)
        self.assertEqual(unmatched, [])

    def test_empty_log_has_no_fake_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "reference_seed42_r0.log"
            file.write_text("OPEX 1970-01-01 EPOCH_BOUNDS roadMin=7\n", encoding="utf-8")
            report = analyze_files([file], expected_years=[1970])
        self.assertEqual((report["unique_events"], report["parse_errors"]), (0, 0))
        self.assertEqual(report["by_seed_year"], [])
        self.assertEqual(report["file_coverage"][0]["observed_years"], [])
        self.assertIn("Aucune.", render_markdown(report))

    def test_cli_json_markdown_expected_years_and_refuse_overwrite(self):
        script = Path(__file__).with_name("analyse_front_pax_bounds.py")
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "reference_seed7_r0.log"
            source.write_text(log_line(), encoding="utf-8")
            json_out = Path(folder) / "report.json"
            md_out = Path(folder) / "report.md"
            command = [
                sys.executable, "-B", str(script), str(Path(folder) / "*.log"),
                "--start-year", "1970", "--end-year", "1972",
                "--json-out", str(json_out), "--markdown-out", str(md_out),
            ]
            run = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            data = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(data["expected_years"], [1970, 1971, 1972])
            self.assertEqual(data["seed_coverage"][0]["missing_expected_years"], [1971, 1972])
            md = md_out.read_text(encoding="utf-8")
            self.assertIn("FRONT-PAX-1", md)
            self.assertIn("rail_tau100", md)
            self.assertIn("delta_nonpositive", md)
            self.assertIn("rail_source", md)
            rerun = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertNotEqual(rerun.returncode, 0)
            self.assertIn("refus", rerun.stderr)

    def test_cli_strict_exits_nonzero_on_malformed_logs(self):
        script = Path(__file__).with_name("analyse_front_pax_bounds.py")
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "reference_seed42_r0.log"
            source.write_text(log_line() + log_line() +
                              "OPEX bad-date FRONT_PAX_BOUNDS something\n",
                              encoding="utf-8")
            run = subprocess.run([sys.executable, "-B", str(script), str(source),
                                  "--strict"], capture_output=True, text=True)
            self.assertEqual(run.returncode, 1)
            self.assertIn("doublons exacts : 1", run.stdout)
            self.assertIn("Erreurs de parsing : 1", run.stdout)
            # Un second recalcul identique le meme jour est benin pour
            # --strict : l'identifiant de refresh manque dans les logs.
            source.write_text(log_line() + log_line(), encoding="utf-8")
            valid = subprocess.run([sys.executable, "-B", str(script), str(source),
                                    "--strict"], capture_output=True, text=True)
            self.assertEqual(valid.returncode, 0, valid.stderr)
            self.assertIn("doublons exacts : 1", valid.stdout)
            # Un fichier dont la graine est impossible a reconstituer n'est
            # en revanche pas admissible au mode strict.
            unknown = Path(folder) / "unknown_engine.log"
            unknown.write_text(log_line(), encoding="utf-8")
            unmatched = subprocess.run([sys.executable, "-B", str(script),
                                        str(unknown), "--strict"],
                                       capture_output=True, text=True)
            self.assertEqual(unmatched.returncode, 1, unmatched.stderr)
            self.assertIn("fichiers sans graine : 1", unmatched.stdout)

    def test_sequential_composites_keep_exact_and_elementary_counts(self):
        compound = PAYLOAD.replace(
            "road_reason=delta_nonpositive", "road_reason=delta_nonpositive+map_span"
        ).replace("rail_clamp=rail_max", "rail_clamp=map_span+rail_max"
        ).replace("rail_source=200", "rail_source=600"
        ).replace("rail_road_floor=0", "rail_road_floor=1"
        ).replace("rail_map_cap=0", "rail_map_cap=1")
        second = OTHER_PAYLOAD.replace(
            "rail_clamp=none", "rail_clamp=map_span+road_max+rail_max"
        ).replace("road_reason=minimum", "road_reason=minimum+map_span"
        ).replace("rail_source=200", "rail_source=900"
        ).replace("rail_map_cap=0", "rail_map_cap=1")
        rows, errors, markers = parse_log_lines(
            [log_line(payload=compound), log_line(payload=second)],
            "reference_seed42_r0.log",
        )
        self.assertEqual((len(rows), len(errors), markers), (2, 0, 2))
        with tempfile.TemporaryDirectory() as folder:
            file = Path(folder) / "reference_seed42_r0.log"
            file.write_text(log_line(payload=compound) + log_line(payload=second),
                            encoding="utf-8")
            report = analyze_files([file], expected_years=[1970])
        row, = report["by_seed_year"]
        self.assertEqual(row["motives"]["rail_clamp"],
                         {"map_span+rail_max": 1, "map_span+road_max+rail_max": 1})
        self.assertEqual(row["causes"]["rail_clamp"],
                         {"map_span": 2, "rail_max": 2, "road_max": 1})
        self.assertEqual(row["motives"]["road_reason"],
                         {"delta_nonpositive+map_span": 1, "minimum+map_span": 1})
        self.assertEqual(row["causes"]["road_reason"],
                         {"delta_nonpositive": 1, "minimum": 1, "map_span": 2})
        self.assertEqual(row["rail_road_floor_applied"], 1)
        self.assertEqual(row["rail_map_cap_applied"], 2)
        self.assertEqual(row["values"]["rail_source"]["median"], 750)
        self.assertEqual(row["values"]["rail_source_minus_max"]["median"], 550)
        self.assertEqual(report["schema"], "front_pax_bounds_v2")
        markdown = render_markdown(report)
        self.assertIn("Causes élémentaires", markdown)
        self.assertIn("map_span+rail_max", markdown)
        self.assertIn("| rail_clamp | map_span | 2 |", markdown)


if __name__ == "__main__":
    unittest.main()
