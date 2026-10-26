"""Preuves conservatrices FRONT-PAX-1, aucune simulation OpenTTD."""

import gzip
from pathlib import Path
import tempfile
import unittest

from sweeps.diag_front_pax_clamp_bounds import analyse, classify


BASE = dict(roadMin="7", roadMax="7", railAir="200", railMax="200",
            vRail="115.88227", vAir="144", tFixe="26", tpd="74")


class FrontPaxBoundedAudit(unittest.TestCase):
    def test_numeric_seed_spelling_cannot_inflate_independent_games(self):
        line = "OPEX 1970-1-2 EPOCH_BOUNDS " + " ".join(
            f"{key}={value}" for key, value in BASE.items()) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reference_seed1_r0.log").write_text(line, encoding="utf-8")
            (root / "reference_seed01_r0.log").write_text(line, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identite de partie FRONT-PAX ambigue"):
                analyse([root])

    def test_numeric_repeat_spelling_cannot_inflate_independent_games(self):
        line = "OPEX 1970-1-2 EPOCH_BOUNDS " + " ".join(
            f"{key}={value}" for key, value in BASE.items()) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reference_seed42_r0.log").write_text(line, encoding="utf-8")
            (root / "reference_seed42_r00.log").write_text(line, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "identite de partie FRONT-PAX ambigue"):
                analyse([root])

    def test_distinct_arms_seeds_and_repeats_stay_distinct(self):
        line = "OPEX 1970-1-2 EPOCH_BOUNDS " + " ".join(
            f"{key}={value}" for key, value in BASE.items()) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("reference_seed42_r0.log", "variant_seed42_r0.log",
                         "reference_seed100_r0.log", "reference_seed42_r1.log"):
                (root / name).write_text(line, encoding="utf-8")
            report = analyse([root])
            self.assertEqual(report["games"], 4)
            self.assertEqual(report["events"], 4)

    def test_real_epoch_exposes_provable_upper_clamp(self):
        out = classify(BASE)
        self.assertEqual(out["reason"], "proven_upper_rail_clamp")
        self.assertGreater(out["raw_distance_lower"], 200)
        self.assertLess(out["raw_distance_lower"], out["raw_distance_upper"])

    def test_no_synthetic_cause_of_road_min_is_claimed(self):
        # Same final roadMax=7 with arbitrarily different causes.
        self.assertEqual(classify(BASE)["road_max_equals_min"], True)
        self.assertNotIn("road_reason", classify(BASE))
        for field in ("vRail", "vAir", "tFixe", "tpd"):
            invalid = dict(BASE, **{field: "bad"})
            self.assertEqual(classify(invalid)["reason"], "missing_or_invalid")

    def test_lower_clamp_must_be_consistent_with_final(self):
        low = dict(BASE, railAir="7", railMax="200", vRail="80", vAir="320", tFixe="1")
        self.assertEqual(classify(low)["reason"], "proven_lower_road_clamp")
        low["railAir"] = "200"
        self.assertEqual(classify(low)["reason"], "conflict_with_final_bound")

    def test_close_interval_remains_unknown_not_falsely_qualified(self):
        # A threshold extremely close to railMax could move across it when
        # vAir and tFixe's hidden fractional parts change.
        case = dict(BASE, vRail="100", vAir="200", tFixe="17", railMax="101", railAir="101")
        self.assertNotEqual(classify(case)["reason"], "proven_upper_rail_clamp")

    def test_exact_duplicate_log_gzip_does_not_inflate_counts(self):
        line = "OPEX 1970-1-2 EPOCH_BOUNDS " + " ".join(
            f"{key}={value}" for key, value in BASE.items()) + "\n"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "reference_seed42_r0.log").write_text(line, encoding="utf-8")
            with gzip.open(root / "reference_seed42_r0.log.gz", "wt", encoding="utf-8") as stream:
                stream.write(line)
            report = analyse([root])
            self.assertEqual(report["events"], 1)
            self.assertEqual(report["games"], 1)
            with gzip.open(root / "reference_seed42_r0.log.gz", "wt", encoding="utf-8") as stream:
                stream.write(line.replace("vAir=144", "vAir=143"))
            with self.assertRaisesRegex(ValueError, "copies contradictoires"):
                analyse([root])

    def test_source_contract_calendar_and_logged_truncations(self):
        source = (Path(__file__).resolve().parents[1] / "ai/OpexAI/candidates.nut").read_text(encoding="utf-8")
        self.assertIn("return 74.0;", source)
        self.assertIn('" vAir=" + vAirEff.tointeger()', source)
        self.assertIn('" tFixe=" + tFixe.tointeger()', source)
        self.assertIn("local d = tFixe / (tauRail - tauAir);", source)
        self.assertIn("if (railAir > railMax) railAir = railMax;", source)


if __name__ == "__main__":
    unittest.main()
