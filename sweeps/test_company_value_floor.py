"""Plancher de valeur OpenTTD en départ 1950.

Les relevés viennent des smokes rva_smoke_1950_1x1_20261018 et
rva_smoke_1970_1x1_20261018 (graine 42, un an). company_value est la
valeur brute de old_economy[0], pas un recalcul.
"""
from pathlib import Path
import json
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from game_health import assess_game

FIXTURE = ROOT / "sweeps" / "fixtures" / "launcher1950_value_floor.json"
CLEAN_LOG = (ROOT / "sweeps" / "fixtures" / "c66_health" / "clean.log").read_text()
HOGEX_ERROR_LOG = (ROOT / "sweeps" / "fixtures" / "c66_health" / "hogex_error.log").read_text()


def _load():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _rows(payload, year, arm=None):
    rows = payload["campaigns"][year]
    if arm is None:
        return rows
    return [row for row in rows if row["run"][0] == arm]


def _on(rows, date):
    return next(row for row in rows if row["date"] == date)


class TestCompanyValueFloor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payload = _load()

    def test_1950_raw_company_value_is_the_engine_floor(self):
        aaa = _rows(self.payload, "1950", "AAAHogEx")
        first_closed = _on(aaa, "1950-05-01")
        terminal = _on(aaa, "1951-01-01")
        self.assertEqual(first_closed["company_value"], 1)
        self.assertEqual(first_closed["money"], 11544)
        self.assertEqual(first_closed["current_loan"], 130000)
        self.assertEqual(first_closed["primary_vehicles"], 1)
        self.assertEqual(first_closed["n_stations"], 4)
        self.assertEqual(terminal["company_value"], 1)
        self.assertEqual(terminal["money"], 15823)
        self.assertEqual(terminal["current_loan"], 260000)
        self.assertEqual(terminal["primary_vehicles"], 6)
        self.assertEqual(terminal["n_stations"], 7)
        self.assertEqual(terminal["profit_year"], 34835)
        self.assertEqual(terminal["months_of_bankruptcy"], 0)
        floored = [
            row["date"] for row in aaa
            if row["date"] >= "1950-05-01"
        ]
        self.assertTrue(floored)
        self.assertTrue(all(_on(aaa, date)["company_value"] == 1 for date in floored))

        opex = _on(_rows(self.payload, "1950", "OpexAI"), "1951-01-01")
        self.assertEqual(opex["company_value"], 173951)
        self.assertEqual(opex["primary_vehicles"], 11)
        self.assertEqual(opex["profit_year"], 102547)

    def test_1950_active_company_at_value_floor_is_complete(self):
        game = assess_game(
            _rows(self.payload, "1950"),
            starting_year=1950,
            years=1,
            engine_log=CLEAN_LOG,
        )
        self.assertEqual(game["companies"]["AAAHogEx"]["status"], "complete")
        self.assertTrue(game["companies"]["AAAHogEx"]["run_ok"])
        self.assertEqual(game["companies"]["OpexAI"]["status"], "complete")
        self.assertEqual(game["game_status"], "complete")
        self.assertTrue(game["game_ok"])

    def test_1950_company_without_vehicles_stays_inactive(self):
        rows = [dict(row) for row in _rows(self.payload, "1950")]
        terminal = next(
            row for row in rows
            if row["run"][0] == "AAAHogEx" and row["date"] == "1951-01-01"
        )
        terminal["primary_vehicles"] = 0
        self.assertEqual(terminal["company_value"], 1)
        self.assertEqual(terminal["n_stations"], 7)
        game = assess_game(
            rows, starting_year=1950, years=1, engine_log=CLEAN_LOG,
        )
        self.assertEqual(game["companies"]["AAAHogEx"]["status"], "inactive_company")
        self.assertFalse(game["companies"]["AAAHogEx"]["run_ok"])
        self.assertIn("vehicles=0", game["companies"]["AAAHogEx"]["failure_reason"])
        self.assertFalse(game["game_ok"])

    def test_1950_script_crash_stays_a_noai_error(self):
        game = assess_game(
            _rows(self.payload, "1950"),
            starting_year=1950,
            years=1,
            engine_log=HOGEX_ERROR_LOG,
        )
        self.assertEqual(game["companies"]["AAAHogEx"]["status"], "noai_error")
        self.assertFalse(game["companies"]["AAAHogEx"]["run_ok"])
        self.assertEqual(game["companies"]["OpexAI"]["status"], "complete")
        self.assertFalse(game["game_ok"])

    def test_1970_same_reader_stays_complete(self):
        aaa = _rows(self.payload, "1970", "AAAHogEx")
        # Même plancher en cours d'année, puis une valeur positive au dernier relevé.
        for date in ("1970-05-01", "1970-06-01", "1970-07-01"):
            self.assertEqual(_on(aaa, date)["company_value"], 1)
            self.assertGreaterEqual(_on(aaa, date)["primary_vehicles"], 1)
        terminal = _on(aaa, "1971-01-01")
        self.assertEqual(terminal["company_value"], 275619)
        self.assertEqual(terminal["primary_vehicles"], 15)
        self.assertEqual(terminal["n_stations"], 16)
        self.assertEqual(terminal["profit_year"], 300414)
        opex = _on(_rows(self.payload, "1970", "OpexAI"), "1971-01-01")
        self.assertEqual(opex["company_value"], 383085)

        game = assess_game(
            _rows(self.payload, "1970"),
            starting_year=1970,
            years=1,
            engine_log=CLEAN_LOG,
        )
        self.assertEqual(game["companies"]["AAAHogEx"]["status"], "complete")
        self.assertEqual(game["companies"]["OpexAI"]["status"], "complete")
        self.assertEqual(game["game_status"], "complete")
        self.assertTrue(game["game_ok"])


if __name__ == "__main__":
    unittest.main()
