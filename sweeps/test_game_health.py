"""Contrôles négatifs C66.2 : attribution NoAI, horizon, compagnie absente, stagnation."""
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from game_health import (
    DUEL_SLOT_MAP,
    activity_from_series,
    annotate_summary,
    assess_game,
    capture_engine_failure,
    expected_last_checkpoint,
    expected_last_year,
    parse_script_errors,
    reconcile_assessment,
    wrap_engine_failure_capture,
    write_engine_log,
)

FIXTURES = ROOT / "sweeps" / "fixtures" / "c66_health"


def _rec(arm, seed, date, **fields):
    row = {
        "run": [arm, seed, 0],
        "date": date,
        "company_value": fields.pop("company_value", 1000),
        "primary_vehicles": fields.pop("primary_vehicles", 4),
        "n_vehicles": fields.pop("n_vehicles", 4),
        "n_stations": fields.pop("n_stations", 2),
        "months_of_bankruptcy": fields.pop("months_of_bankruptcy", 0),
        "company_present": fields.pop("company_present", True),
        "performance_history": 100,
        "income_last_year": 50,
        "expenses_last_year": -10,
        "profit": 40,
        "profit_year": 40,
        "median_station_rating": 160,
        "n_station_ratings": 2,
        "money": 500,
        "current_loan": 0,
        "vehs_chunk_valid": True,
        "stnn_chunk_valid": True,
    }
    row.update(fields)
    return row


def _monthly_pair(seed, last="1974-12-01", start="1970-01-01"):
    """Série mensuelle minimale jusqu'à `last` pour les deux compagnies."""
    year, month, _day = (int(part) for part in last.split("-"))
    start_y, start_m, _ = (int(part) for part in start.split("-"))
    records = []
    y, m = start_y, start_m
    step = 0
    while (y, m) <= (year, month):
        date = f"{y:04d}-{m:02d}-01"
        records.append(_rec("OpexAI", seed, date, primary_vehicles=2 + step, n_stations=2 + step // 3,
                            company_value=1000 + 50 * step))
        records.append(_rec("AAAHogEx", seed, date, primary_vehicles=3 + step, n_stations=3 + step // 2,
                            company_value=2000 + 80 * step))
        step += 1
        m += 1
        if m == 13:
            m = 1
            y += 1
    return records


class TestGameHealth(unittest.TestCase):
    def test_expected_horizon_rejects_january_of_last_year(self):
        self.assertEqual(expected_last_year(1970, 5), 1974)
        self.assertEqual(expected_last_checkpoint(1970, 5), "1974-12-01")
        self.assertEqual(expected_last_checkpoint(1970, 6), "1975-12-01")

    def test_opex_error_is_not_attributed_to_hogex(self):
        log = (FIXTURES / "opex_error.log").read_text()
        parsed = parse_script_errors(log, slot_map=DUEL_SLOT_MAP)
        self.assertEqual([item["attributed_to"] for item in parsed["attributed"]], ["OpexAI"])
        self.assertFalse(parsed["unattributed"])
        records = _monthly_pair(42)
        game = assess_game(records, starting_year=1970, years=5, engine_log=log)
        self.assertEqual(game["companies"]["OpexAI"]["status"], "noai_error")
        self.assertFalse(game["companies"]["OpexAI"]["run_ok"])
        self.assertEqual(game["companies"]["AAAHogEx"]["status"], "complete")
        self.assertTrue(game["companies"]["AAAHogEx"]["run_ok"])
        self.assertFalse(game["game_ok"])
        self.assertEqual(game["companies"]["OpexAI"]["script_errors"][0]["marker"],
                         "Your script made an error")

    def test_hogex_error_is_not_attributed_to_opex(self):
        log = (FIXTURES / "hogex_error.log").read_text()
        records = _monthly_pair(7)
        game = assess_game(records, starting_year=1970, years=5, engine_log=log)
        self.assertEqual(game["companies"]["AAAHogEx"]["status"], "noai_error")
        self.assertFalse(game["companies"]["AAAHogEx"]["run_ok"])
        self.assertEqual(game["companies"]["OpexAI"]["status"], "complete")
        self.assertTrue(game["companies"]["OpexAI"]["run_ok"])
        self.assertFalse(game["game_ok"])
        names = {item["attributed_to"] for item in game["companies"]["AAAHogEx"]["script_errors"]}
        self.assertEqual(names, {"AAAHogEx"})

    def test_ambiguous_log_is_unattributed(self):
        log = (FIXTURES / "ambiguous.log").read_text()
        parsed = parse_script_errors(log)
        self.assertFalse(parsed["attributed"])
        self.assertGreaterEqual(len(parsed["unattributed"]), 2)
        self.assertTrue(all(item["attributed_to"] is None for item in parsed["unattributed"]))
        records = _monthly_pair(99)
        game = assess_game(records, starting_year=1970, years=5, engine_log=log)
        self.assertFalse(game["game_ok"])
        self.assertEqual(game["companies"]["OpexAI"]["status"], "noai_error")
        self.assertEqual(game["companies"]["AAAHogEx"]["status"], "noai_error")
        self.assertIn("unattributed_noai_error", game["companies"]["OpexAI"]["failure_reason"])
        self.assertIn("unattributed_noai_error", game["companies"]["AAAHogEx"]["failure_reason"])
        self.assertFalse(game["companies"]["OpexAI"]["script_errors"])
        self.assertFalse(game["companies"]["AAAHogEx"]["script_errors"])

    def test_missing_company_is_missing_data_not_healthy(self):
        records = [row for row in _monthly_pair(1) if row["run"][0] == "OpexAI"]
        game = assess_game(
            records, starting_year=1970, years=5,
            engine_log=(FIXTURES / "clean.log").read_text(),
        )
        self.assertEqual(game["companies"]["AAAHogEx"]["status"], "missing_data")
        self.assertFalse(game["companies"]["AAAHogEx"]["run_ok"])
        self.assertFalse(game["game_ok"])
        self.assertIn("AAAHogEx", game["checkpoint_report"]["missing_companies"])

    def test_january_of_last_year_is_truncated(self):
        records = _monthly_pair(2, last="1974-01-01")
        game = assess_game(
            records, starting_year=1970, years=5,
            engine_log=(FIXTURES / "clean.log").read_text(),
        )
        self.assertEqual(game["expected_last_checkpoint"], "1974-12-01")
        self.assertEqual(game["companies"]["OpexAI"]["status"], "horizon_truncated")
        self.assertEqual(game["companies"]["AAAHogEx"]["status"], "horizon_truncated")
        self.assertFalse(game["game_ok"])
        self.assertIn("1974-01-01", game["companies"]["OpexAI"]["failure_reason"])

    def test_december_of_last_year_is_complete(self):
        records = _monthly_pair(3, last="1974-12-01")
        game = assess_game(
            records, starting_year=1970, years=5,
            engine_log=(FIXTURES / "clean.log").read_text(),
        )
        self.assertTrue(game["game_ok"])
        self.assertEqual(game["game_status"], "complete")
        self.assertEqual(game["companies"]["OpexAI"]["status"], "complete")
        self.assertTrue(game["companies"]["OpexAI"]["include_in_economic_stats"])

    def test_bankruptcy_stays_in_economic_stats(self):
        records = _monthly_pair(4, last="1974-12-01")
        for row in records:
            if row["run"][0] == "OpexAI" and row["date"] == "1974-12-01":
                row["months_of_bankruptcy"] = 3
                row["company_value"] = 0
        game = assess_game(
            records, starting_year=1970, years=5,
            engine_log=(FIXTURES / "clean.log").read_text(),
        )
        self.assertEqual(game["companies"]["OpexAI"]["status"], "bankrupt")
        self.assertTrue(game["companies"]["OpexAI"]["include_in_economic_stats"])
        self.assertTrue(game["companies"]["OpexAI"]["run_ok"])
        self.assertTrue(game["game_ok"])
        self.assertEqual(game["companies"]["AAAHogEx"]["status"], "complete")

    def test_earning_without_expansion_is_not_freeze(self):
        series = [
            _rec("OpexAI", 5, "1974-08-01", primary_vehicles=10, n_stations=8, company_value=1000),
            _rec("OpexAI", 5, "1974-09-01", primary_vehicles=10, n_stations=8, company_value=1100),
            _rec("OpexAI", 5, "1974-10-01", primary_vehicles=10, n_stations=8, company_value=1250),
            _rec("OpexAI", 5, "1974-11-01", primary_vehicles=10, n_stations=8, company_value=1400),
            _rec("OpexAI", 5, "1974-12-01", primary_vehicles=10, n_stations=8, company_value=1600),
        ]
        activity = activity_from_series(series)
        self.assertEqual(activity["signal"], "earning_without_expansion")
        self.assertEqual(activity["fleet_changes"], 0)
        self.assertGreater(activity["value_changes"], 0)

    def test_no_signal_on_complete_horizon_fails_closed(self):
        records = []
        for month in range(1, 13):
            date = f"1974-{month:02d}-01"
            records.append(_rec("OpexAI", 6, date, primary_vehicles=4, n_stations=2, company_value=900))
            records.append(_rec("AAAHogEx", 6, date, primary_vehicles=8, n_stations=4, company_value=2000))
        game = assess_game(
            records, starting_year=1974, years=1,
            engine_log=(FIXTURES / "clean.log").read_text(),
        )
        self.assertEqual(game["companies"]["OpexAI"]["status"], "stagnation_suspect")
        self.assertFalse(game["companies"]["OpexAI"]["include_in_economic_stats"])
        self.assertFalse(game["companies"]["OpexAI"]["run_ok"])
        self.assertFalse(game["game_ok"])
        self.assertIn("stagnation_suspect", game["companies"]["OpexAI"]["failure_reason"])

    def test_declining_value_without_expansion_is_stagnation(self):
        records = []
        for month in range(1, 13):
            date = f"1974-{month:02d}-01"
            records.append(_rec(
                "OpexAI", 61, date,
                primary_vehicles=4, n_stations=2, company_value=1200 - 25 * month,
            ))
            records.append(_rec(
                "AAAHogEx", 61, date,
                primary_vehicles=8 + month, n_stations=4 + month,
                company_value=2000 + 50 * month,
            ))
        activity = activity_from_series([row for row in records if row["run"][0] == "OpexAI"])
        self.assertEqual(activity["signal"], "declining_without_expansion")
        self.assertEqual(activity["fleet_changes"], 0)
        self.assertGreater(activity["value_decreases"], 0)
        game = assess_game(
            records, starting_year=1974, years=1,
            engine_log=(FIXTURES / "clean.log").read_text(),
        )
        self.assertEqual(game["companies"]["OpexAI"]["status"], "stagnation_suspect")
        self.assertFalse(game["game_ok"])

    def test_recent_one_point_uptick_does_not_hide_net_decline(self):
        values = [1200, 1160, 1120, 1080, 1040, 1000, 960, 920, 901, 899, 900, 900]
        records = []
        for month, value in enumerate(values, start=1):
            date = f"1974-{month:02d}-01"
            records.append(_rec(
                "OpexAI", 77, date,
                primary_vehicles=4, n_stations=2, company_value=value,
            ))
            records.append(_rec(
                "AAAHogEx", 77, date,
                primary_vehicles=8 + month, n_stations=4 + month,
                company_value=2000 + 50 * month,
            ))

        opex = [row for row in records if row["run"][0] == "OpexAI"]
        activity = activity_from_series(opex)
        self.assertEqual(activity["value_increases"], 1)
        self.assertGreater(activity["value_decreases"], 0)
        self.assertEqual(activity["net_company_value_change"], -300)
        self.assertEqual(activity["signal"], "declining_without_expansion")

        game = assess_game(
            records, starting_year=1974, years=1,
            engine_log=(FIXTURES / "clean.log").read_text(),
        )
        self.assertEqual(game["companies"]["OpexAI"]["status"], "stagnation_suspect")
        self.assertFalse(game["companies"]["OpexAI"]["run_ok"])
        self.assertFalse(game["game_ok"])

    def test_missing_internal_month_is_protocol_failure(self):
        records = [
            row for row in _monthly_pair(62, last="1970-12-01")
            if not (row["run"][0] == "OpexAI" and row["date"] == "1970-07-01")
        ]
        game = assess_game(
            records, starting_year=1970, years=1,
            engine_log=(FIXTURES / "clean.log").read_text(),
        )
        self.assertEqual(game["companies"]["OpexAI"]["status"], "missing_data")
        self.assertFalse(game["companies"]["OpexAI"]["run_ok"])
        self.assertEqual(
            game["checkpoint_report"]["missing_checkpoints"]["OpexAI"],
            ["1970-07-01"],
        )

    def test_company_without_physical_activity_fails_closed(self):
        records = _monthly_pair(63, last="1970-12-01")
        for row in records:
            if row["run"][0] == "AAAHogEx" and row["date"] == "1970-12-01":
                row["primary_vehicles"] = 0
        game = assess_game(
            records, starting_year=1970, years=1,
            engine_log=(FIXTURES / "clean.log").read_text(),
        )
        self.assertEqual(game["companies"]["AAAHogEx"]["status"], "inactive_company")
        self.assertFalse(game["companies"]["AAAHogEx"]["run_ok"])
        self.assertFalse(game["game_ok"])

    def test_missing_engine_log_is_protocol_failure(self):
        records = _monthly_pair(64, last="1970-12-01")
        game = assess_game(records, starting_year=1970, years=1)
        self.assertEqual(game["game_status"], "engine_error")
        self.assertEqual(game["engine_error"], "missing_engine_log:unspecified")
        self.assertFalse(game["game_ok"])

    def test_duplicate_checkpoint_is_protocol_failure(self):
        records = _monthly_pair(8, last="1974-12-01")
        records.append(_rec("OpexAI", 8, "1974-12-01", primary_vehicles=99))
        game = assess_game(
            records, starting_year=1970, years=5,
            engine_log=(FIXTURES / "clean.log").read_text(),
        )
        self.assertEqual(game["companies"]["OpexAI"]["status"], "duplicate_checkpoint")
        self.assertFalse(game["game_ok"])
        self.assertFalse(game["companies"]["OpexAI"]["run_ok"])

    def test_engine_fatal_is_not_a_company_bug(self):
        log = (FIXTURES / "engine_fatal.log").read_text()
        records = _monthly_pair(9)
        game = assess_game(records, starting_year=1970, years=5, engine_log=log)
        self.assertEqual(game["game_status"], "engine_error")
        self.assertEqual(game["companies"]["OpexAI"]["status"], "engine_error")
        self.assertEqual(game["companies"]["AAAHogEx"]["status"], "engine_error")
        self.assertFalse(game["game_ok"])

    def test_engine_log_written_once_and_annotate_drops_shared_output(self):
        records = _monthly_pair(10)
        with tempfile.TemporaryDirectory() as tmp:
            path = write_engine_log(Path(tmp) / "seed10_r0.log", (FIXTURES / "hogex_error.log").read_text())
            game = assess_game(
                records, starting_year=1970, years=5, engine_log_path=path,
            )
            self.assertEqual(Path(path).read_text().count("Your script made an error"), 1)
            self.assertEqual(game["engine_log_path"], path)
            summary = [
                {
                    "arm": "OpexAI", "seed": 10, "repeat": 0, "run_ok": True,
                    "failure_reason": None, "openttd_output": "SHOULD_NOT_LEAK",
                    "last_date": "1974-12-01",
                },
                {
                    "arm": "AAAHogEx", "seed": 10, "repeat": 0, "run_ok": True,
                    "failure_reason": None, "openttd_output": "",
                    "last_date": "1974-12-01",
                },
            ]
            annotated = annotate_summary(summary, records, game)
            self.assertNotIn("openttd_output", annotated[0])
            self.assertNotIn("openttd_output", annotated[1])
            self.assertTrue(annotated[0]["run_ok"])
            self.assertFalse(annotated[1]["run_ok"])
            self.assertEqual(annotated[1]["status"], "noai_error")
            self.assertEqual(annotated[0]["engine_log_path"], path)

    def test_physical_failure_is_not_rehabilitated_to_complete(self):
        records = _monthly_pair(11)
        game = assess_game(
            records, starting_year=1970, years=5,
            engine_log=(FIXTURES / "clean.log").read_text(),
        )
        self.assertTrue(game["game_ok"])
        summary = [
            {
                "arm": "OpexAI", "seed": 11, "repeat": 0, "run_ok": False,
                "failure_reason": "physical_decode_failure: missing_base",
                "physical_ok": False,
            },
            {
                "arm": "AAAHogEx", "seed": 11, "repeat": 0, "run_ok": True,
                "failure_reason": None, "physical_ok": True,
            },
        ]
        annotated = annotate_summary(summary, records, game)
        self.assertFalse(annotated[0]["run_ok"])
        self.assertEqual(annotated[0]["status"], "missing_data")
        self.assertIn("physical_decode_failure", annotated[0]["failure_reason"])
        self.assertFalse(annotated[0]["include_in_economic_stats"])
        self.assertFalse(annotated[0]["game_ok"])
        self.assertFalse(annotated[1]["game_ok"])
        self.assertNotEqual(annotated[0]["status"], "complete")
        self.assertTrue(game["game_ok"])
        reconciled = reconcile_assessment(game, annotated)
        self.assertFalse(reconciled["game_ok"])
        self.assertEqual(reconciled["game_status"], annotated[0]["game_status"])
        self.assertEqual(reconciled["companies"]["OpexAI"]["status"], "missing_data")
        self.assertFalse(reconciled["companies"]["OpexAI"]["run_ok"])
        self.assertIn("physical_decode_failure", reconciled["companies"]["OpexAI"]["failure_reason"])
        self.assertEqual(reconciled["companies"]["AAAHogEx"]["status"], annotated[1]["status"])

    def test_disappeared_company_at_last_checkpoint_is_missing_data(self):
        records = _monthly_pair(12, last="1974-12-01")
        for row in records:
            if row["run"][0] == "OpexAI" and row["date"] == "1974-12-01":
                row["company_present"] = False
                row["company_value"] = None
                row["months_of_bankruptcy"] = 0
        game = assess_game(
            records, starting_year=1970, years=5,
            engine_log=(FIXTURES / "clean.log").read_text(),
        )
        self.assertEqual(game["companies"]["OpexAI"]["status"], "missing_data")
        self.assertFalse(game["companies"]["OpexAI"]["run_ok"])
        self.assertFalse(game["game_ok"])
        self.assertIn("1974-12-01", game["companies"]["OpexAI"]["failure_reason"])
        self.assertEqual(game["companies"]["AAAHogEx"]["status"], "complete")

    def test_disappeared_after_bankruptcy_stays_economic(self):
        records = _monthly_pair(13, last="1974-12-01")
        for row in records:
            if row["run"][0] == "OpexAI" and row["date"] == "1974-11-01":
                row["months_of_bankruptcy"] = 2
            if row["run"][0] == "OpexAI" and row["date"] == "1974-12-01":
                row["company_present"] = False
                row["months_of_bankruptcy"] = 0
        game = assess_game(
            records, starting_year=1970, years=5,
            engine_log=(FIXTURES / "clean.log").read_text(),
        )
        self.assertEqual(game["companies"]["OpexAI"]["status"], "bankrupt")
        self.assertTrue(game["companies"]["OpexAI"]["include_in_economic_stats"])
        self.assertTrue(game["game_ok"])

    def test_stale_value_change_is_not_earning_without_expansion(self):
        series = [_rec("OpexAI", 14, "1974-01-01", primary_vehicles=4, n_stations=2, company_value=1000)]
        series.append(_rec("OpexAI", 14, "1974-02-01", primary_vehicles=4, n_stations=2, company_value=1500))
        for month in range(3, 13):
            series.append(_rec(
                "OpexAI", 14, f"1974-{month:02d}-01",
                primary_vehicles=4, n_stations=2, company_value=1500,
            ))
        activity = activity_from_series(series)
        self.assertGreater(activity["months_since_value_change"], 3)
        self.assertEqual(activity["signal"], "no_signal")

    def test_capture_engine_failure_from_nonzero_exit(self):
        import subprocess

        def processor(row):
            return ({
                "run": ["OpexAI", row["experiment"]["seed"], 0],
                "date": row["date"],
                "engine_failure": row["engine_failure"],
                "company_present": False,
            }, {
                "run": ["AAAHogEx", row["experiment"]["seed"], 0],
                "date": row["date"],
                "engine_failure": row["engine_failure"],
                "company_present": False,
            })

        exc = subprocess.CalledProcessError(1, ["openttd"], output=b"Fatal error: Aborted")
        rows = capture_engine_failure(exc, {"seed": 15, "repeat": 0}, processor)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["engine_failure"]["kind"], "nonzero_exit")
        self.assertEqual(rows[0]["engine_failure"]["returncode"], 1)
        game = assess_game(rows, starting_year=1970, years=5, engine_log=rows[0].get("output"))
        self.assertEqual(game["game_status"], "engine_error")
        self.assertEqual(game["engine_error"], "nonzero_exit:1")
        self.assertFalse(game["game_ok"])

    def test_capture_engine_failure_from_timeout(self):
        import subprocess
        exc = subprocess.TimeoutExpired(["openttd"], 30, output="still running")
        rows = capture_engine_failure(exc, {"seed": 16}, lambda row: (row,))
        self.assertEqual(rows[0]["engine_failure"]["kind"], "timeout")
        game = assess_game(
            [{
                "run": ["OpexAI", 16, 0], "date": "1970-01-01",
                "engine_failure": rows[0]["engine_failure"],
                "company_present": False,
            }, {
                "run": ["AAAHogEx", 16, 0], "date": "1970-01-01",
                "engine_failure": rows[0]["engine_failure"],
                "company_present": False,
            }],
            starting_year=1970, years=5,
        )
        self.assertEqual(game["engine_error"], "timeout")
        self.assertEqual(game["companies"]["OpexAI"]["status"], "engine_error")

    def test_capture_wrapper_keeps_run_experiment_signature_for_cleanup(self):
        import inspect

        def original(
            opengfx_binary, openttd_binary, final_screenshot_directory,
            openttd_version, opengfx_version, result_processor,
            run_dir, i, experiment, ai_and_library_filenames,
            xvfb_run_available, data_extraction_mode,
        ):
            return "ok"

        wrapped = wrap_engine_failure_capture(original)
        required = {"run_dir", "i", "final_screenshot_directory"}
        self.assertTrue(required <= set(inspect.signature(wrapped).parameters))

        saved = inspect.signature(wrapped)
        missing = required - saved.parameters.keys()
        self.assertFalse(missing)

        def cleanup(*args, **kwargs):
            bound = saved.bind(*args, **kwargs)
            bound.apply_defaults()
            lost = required - bound.arguments.keys()
            if lost:
                raise RuntimeError(f"OpenTTDLab _run_experiment signature no longer exposes: {lost}")
            assert bound.arguments["final_screenshot_directory"] is None
            return wrapped(*args, **kwargs)

        import functools
        functools.update_wrapper(cleanup, wrapped)
        cleanup.__signature__ = saved
        composed = inspect.signature(cleanup)
        self.assertTrue(required <= set(composed.parameters))
        bound = composed.bind(
            "gfx", "bin", None, "15.3", "7.1", b"proc",
            "/tmp/run", 0, b"exp", (), False, "console-script",
        )
        bound.apply_defaults()
        self.assertEqual(bound.arguments["run_dir"], "/tmp/run")
        self.assertEqual(bound.arguments["i"], 0)
        self.assertIsNone(bound.arguments["final_screenshot_directory"])
        self.assertEqual(
            cleanup(
                "gfx", "bin", None, "15.3", "7.1", b"proc",
                "/tmp/run", 0, b"exp", (), False, "console-script",
            ),
            "ok",
        )

    def test_timeout_patch_is_scoped_to_run_experiment(self):
        import subprocess

        seen = []
        real_check = subprocess.check_output

        def sentinel(*args, **kwargs):
            seen.append(kwargs.get("timeout"))
            return "ok"

        def original(
            opengfx_binary, openttd_binary, final_screenshot_directory,
            openttd_version, opengfx_version, result_processor,
            run_dir, i, experiment, ai_and_library_filenames,
            xvfb_run_available, data_extraction_mode,
        ):
            return subprocess.check_output(["openttd"])

        try:
            subprocess.check_output = sentinel
            wrapped = wrap_engine_failure_capture(original, timeout_sec=17)
            result = wrapped(
                "gfx", "openttd", None, "15.3", "7.1", b"processor",
                "run", 0, b"experiment", (), False, "autosave",
            )
            self.assertEqual(result, "ok")
            self.assertEqual(seen, [17])
            self.assertIs(subprocess.check_output, sentinel)
        finally:
            subprocess.check_output = real_check


if __name__ == "__main__":
    unittest.main()
