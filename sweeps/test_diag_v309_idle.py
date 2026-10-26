"""Contrats du lecteur V309 sur journaux synthétiques, sans moteur."""

import gzip
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_v309_idle import read_idle_logs, read_regen_logs


def idle_line(date="1970-1-1", **overrides):
    """Une valeur None omet le champ pour représenter un ancien journal."""
    fields = {
        "loops": 10, "useless": 2, "useless_ops": 300, "sleep_ops": 430,
        "blocks": 1, "wait_days": 0, "cash_below_days": 0,
        "unknown_cost_loops": 0, "unfunded_cost_loops": 0,
        "stable_unfunded_loops": 0, "stable_unfunded_ops": 0,
    }
    fields.update(overrides)
    payload = " ".join(f"{key}={value}" for key, value in fields.items()
                       if value is not None)
    return f"OPEX {date} V309_IDLE {payload}\n"


def regen_line(ops=100, top1=1):
    keys = " ".join(f"cand_{mode}_same_keys_pct=100" for mode in
                    ("rail", "road", "air", "water", "fleet"))
    return (f"OPEX 1970-1-1 C76_REGEN phase=regen ops={ops} "
            f"{keys} best_same_top1={top1}\n")


class TestV309RegenReader(unittest.TestCase):
    def test_text_gzip_copy_counts_one_game_but_real_repeated_regens_survive(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            text = regen_line() + regen_line(ops=40)
            log = directory / "reference_seed42_r0.log"
            log.write_text(text, encoding="utf-8")
            with gzip.open(str(log) + ".gz", "wt", encoding="utf-8") as stream:
                stream.write(text)
            (directory / "reference_seed7_r0.log").write_text(
                regen_line(ops=50, top1=0), encoding="utf-8")
            n_logs, years = read_regen_logs(directory)
        self.assertEqual(n_logs, 2)
        self.assertEqual(years[1970]["regens"], 3)
        self.assertEqual(years[1970]["regen_ops"], 190)
        self.assertEqual(years[1970]["fully_same_keys_and_top1"], 2)
        self.assertEqual(years[1970]["fully_same_ops"], 140)
        self.assertEqual(years[1970]["measured_keys"], 3)

    def test_contradictory_text_gzip_copy_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "reference_seed42_r0.log"
            log.write_text(regen_line(), encoding="utf-8")
            with gzip.open(str(log) + ".gz", "wt", encoding="utf-8") as stream:
                stream.write(regen_line(ops=101))
            with self.assertRaisesRegex(ValueError, "copies de partie contradictoires"):
                read_regen_logs(tmp)


class TestV309IdleReader(unittest.TestCase):
    def test_invalid_first_flush_is_not_a_copy_conflict(self):
        """Copy comparison must use the same accepted months as aggregation."""
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "reference_seed42_r0.log"
            valid = idle_line("1970-1-2", loops=12, useless=3)
            invalid = idle_line("1970-1-1", loops="bad")
            for bad_in_text in (True, False):
                with self.subTest(bad_in_text=bad_in_text):
                    log.write_text(invalid + valid if bad_in_text else valid,
                                   encoding="utf-8")
                    with gzip.open(str(log) + ".gz", "wt", encoding="utf-8") as stream:
                        stream.write(valid if bad_in_text else invalid + valid)
                    row = read_idle_logs(tmp)["reference"][1970]
                    self.assertEqual(row["months"], 1)
                    self.assertEqual(row["loops"], 12)
                    self.assertEqual(row["useless"], 3)

    def test_one_copy_can_contain_additional_consistent_monthly_flushes(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "reference_seed42_r0.log"
            jan = idle_line("1970-1-1")
            feb = idle_line("1970-2-1", loops=20, useless=4)
            log.write_text(jan, encoding="utf-8")
            with gzip.open(str(log) + ".gz", "wt", encoding="utf-8") as stream:
                stream.write(jan + feb)
            actual = read_idle_logs(tmp)["reference"][1970]
            self.assertEqual(actual["months"], 2)
            self.assertEqual(actual["loops"], 30)
            self.assertEqual(actual["useless"], 6)

    def test_contradictory_copies_cannot_create_a_hybrid_monthly_series(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "reference_seed42_r0.log"
            log.write_text(idle_line("1970-1-1"), encoding="utf-8")
            for changed in (idle_line("1970-1-1", loops=20), idle_line("1970-2-1")):
                with self.subTest(changed=changed):
                    with gzip.open(str(log) + ".gz", "wt", encoding="utf-8") as stream:
                        stream.write(changed)
                    with self.assertRaisesRegex(ValueError, "copies de partie contradictoires"):
                        read_idle_logs(tmp)

    def test_each_game_month_counts_once_and_loop_percentage_is_weighted(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            first = idle_line(useless_ops=300, sleep_ops=400, wait_days=30)
            text = first + first + idle_line(
                "1971-1-1", loops=5, useless=0, useless_ops=0,
                sleep_ops=0, blocks=0, wait_days=-1)
            log = directory / "reference_seed42_r0.log"
            log.write_text(text, encoding="utf-8")
            with gzip.open(str(log) + ".gz", "wt", encoding="utf-8") as stream:
                stream.write(text)
            (directory / "reference_seed7_r0.log").write_text(
                idle_line(loops=30, useless=15, useless_ops=600,
                          sleep_ops=900, blocks=3, wait_days=60), encoding="utf-8")
            with gzip.open(directory / "reference_seed42_r1.log.gz", "wt",
                           encoding="utf-8") as stream:
                stream.write(idle_line(loops=60, useless=3, useless_ops=100,
                                       sleep_ops=300, blocks=0))
            (directory / "v309_idle_seed42_r0.log").write_text(
                idle_line(loops=40, useless=20, wait_days=120), encoding="utf-8")
            result = read_idle_logs(directory)

        row = result["reference"][1970]
        self.assertEqual(row["months"], 3)  # Trois parties, même mois civil.
        self.assertEqual(row["loops"], 100)
        self.assertEqual(row["useless"], 20)
        self.assertEqual(row["useless_pct"], 20.0)  # Moyenne des taux : 25 %.
        self.assertEqual(row["useless_ops"], 1000)
        self.assertEqual(row["sleep_ops"], 1600)
        self.assertEqual(row["blocks"], 4)
        self.assertEqual(row["wait_days_mean"], 30)
        later = result["reference"][1971]
        self.assertEqual(later["months"], 1)
        self.assertEqual(later["loops"], 5)
        self.assertEqual(later["useless_pct"], 0.0)
        self.assertIsNone(later["wait_days_mean"])
        self.assertEqual(later["unavailable_waits"], 1)
        variant = result["v309_idle"][1970]
        self.assertEqual(variant["months"], 1)
        self.assertEqual(variant["loops"], 40)
        self.assertEqual(variant["useless_pct"], 50.0)
        self.assertEqual(variant["wait_days_mean"], 120)

    def test_invalid_core_row_does_not_hide_a_later_valid_month(self):
        required = ("loops", "useless", "useless_ops", "sleep_ops", "blocks")
        invalid = [{key: value} for key in required for value in (None, "bad", -1)]
        invalid.append({"useless": 11})  # Plus de tours inutiles que de tours.
        for overrides in invalid:
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory() as tmp:
                log = Path(tmp) / "reference_seed42_r0.log"
                broken = idle_line(**overrides)
                log.write_text(broken, encoding="utf-8")
                self.assertEqual(read_idle_logs(tmp), {})
                log.write_text(broken + idle_line("1970-1-2"), encoding="utf-8")
                row = read_idle_logs(tmp)["reference"][1970]
                self.assertEqual(row["months"], 1)
                self.assertEqual(row["loops"], 10)
                self.assertEqual(row["useless"], 2)
                self.assertEqual(row["useless_ops"], 300)
                self.assertEqual(row["sleep_ops"], 430)
                self.assertEqual(row["blocks"], 1)
                self.assertEqual(row["unavailable_waits"], 0)

    def test_partial_optional_coverage_stays_unknown_instead_of_zero(self):
        groups = (
            ("cash_below_days",),
            ("unknown_cost_loops", "unfunded_cost_loops"),
            ("stable_unfunded_loops", "stable_unfunded_ops"),
        )
        keys = tuple(key for group in groups for key in group)
        cases = [({key: value}, group) for group in groups for key in group
                 for value in (None, "bad")]
        cases.extend([
            ({"unknown_cost_loops": -1}, groups[1]),
            ({"unfunded_cost_loops": -1}, groups[1]),
            ({"unknown_cost_loops": 7, "unfunded_cost_loops": 4}, groups[1]),
            ({"stable_unfunded_loops": -1}, groups[2]),
            ({"stable_unfunded_loops": 11}, groups[2]),
            ({"stable_unfunded_ops": -1}, groups[2]),
        ])
        for overrides, unknown in cases:
            with self.subTest(overrides=overrides), tempfile.TemporaryDirectory() as tmp:
                log = Path(tmp) / "reference_seed42_r0.log"
                log.write_text(idle_line(), encoding="utf-8")
                complete = read_idle_logs(tmp)["reference"][1970]
                for key in keys:
                    self.assertEqual(complete[key], 0, key)
                # Janvier et décembre observés ne constituent pas une année complète.
                text = idle_line() + idle_line("1970-12-1", wait_days=None, **overrides)
                log.write_text(text, encoding="utf-8")
                row = read_idle_logs(tmp)["reference"][1970]
                self.assertEqual(row["months"], 2)
                self.assertEqual(row["loops"], 20)
                self.assertEqual(row["useless_ops"], 600)
                self.assertEqual(row["sleep_ops"], 860)
                self.assertEqual(row["blocks"], 2)
                for key in keys:
                    if key in unknown:
                        self.assertIsNone(row[key], key)
                    else:
                        self.assertEqual(row[key], 0, key)
                self.assertEqual(row["wait_days_mean"], 0)
                self.assertEqual(row["unavailable_waits"], 1)


if __name__ == "__main__":
    unittest.main()
