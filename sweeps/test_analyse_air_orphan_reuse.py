"""Fixtures moteur indépendantes : appariement AIR orphelin et premier hub."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from analyse_air_orphan_reuse import analyse_files, main, parse_stream


def orphan(date=100, anchor=300, station=31, cost=12000, **overrides):
    fields = {
        "date": date, "anchor": anchor, "station": station, "town": 18,
        "pair": "air|300|400", "reason": "BFAIL", "cost_a": cost,
        "cost_b": 200, "total": cost + 200, "reuse_a": 0, "reuse_b": 0,
    }
    fields.update(overrides)
    return "x OPEX AIR_ORPHAN_RETAIN " + " ".join(
        f"{k}={v}" for k, v in fields.items())


def reuse(date=145, anchor=300, station=31, line=9, prior=0, side="B",
          **overrides):
    fields = {
        "date": date, "line": line, "anchor": anchor, "station": station,
        "side": side, "prior_line_refs": prior, "src_town": 22,
        "dst_town": 18, "reuse_a": int(side == "A"),
        "reuse_b": int(side == "B"),
    }
    fields.update(overrides)
    return "x OPEX AIR_HUB_REUSE " + " ".join(
        f"{k}={v}" for k, v in fields.items())


def parse(*lines, end_date=None, filename="reference_seed42_r0.log"):
    return parse_stream(lines, filename, end_date=end_date)


class OrphanReuseTests(unittest.TestCase):
    def test_confirmed_first_use_exact_anchor_station_and_signed_accounting(self):
        report = parse(orphan(), reuse(), reuse(date=180, line=10, prior=1))
        record = report["orphans"][0]
        self.assertEqual(record["status"], "first_use_confirmed")
        self.assertEqual(record["first_reuse_line"], 9)
        self.assertEqual(record["delay_days"], 45)
        self.assertEqual(record["productive_cost_a_gbp"], 12000)
        self.assertEqual(record["immobilization_gbp_days"], 540000)
        self.assertEqual(report["summary"]["first_use_confirmed"], 1)
        self.assertEqual(report["summary"]["later_reuse_count"], 1)
        self.assertEqual(report["summary"]["unmatched_reuse_count"], 0)
        self.assertEqual(report["summary"]["productive_cost_a_gbp_confirmed"], 12000)
        # Le coût A n'est pas un remboursement de cash.
        self.assertEqual(record["total_build_cost_gbp"], 12200)

    def test_same_day_uses_stream_order_as_tie_breaker(self):
        report = parse(orphan(date=100), reuse(date=100))
        self.assertEqual(report["orphans"][0]["status"], "first_use_confirmed")
        self.assertEqual(report["orphans"][0]["delay_days"], 0)
        early = parse(reuse(date=100), orphan(date=100))
        self.assertEqual(early["orphans"][0]["status"], "ambiguous_station_recycled")

    def test_town_is_not_a_station_or_anchor_match(self):
        report = parse(orphan(), reuse(anchor=301, station=31),
                       reuse(anchor=300, station=32))
        self.assertEqual(report["orphans"][0]["status"], "ambiguous_station_recycled")
        self.assertEqual(report["summary"]["first_use_confirmed"], 0)
        self.assertEqual(report["summary"]["unmatched_reuse_count"], 2)
        self.assertIsNone(report["orphans"][0]["productive_cost_a_gbp"])

    def test_absent_end_never_imputed_from_last_event(self):
        report = parse(orphan(), "AIR_FINANCE_PENDING date=9999 line=2")
        item = report["orphans"][0]
        self.assertEqual(item["status"], "censored")
        self.assertIsNone(item["censored_days"])
        self.assertIsNone(item["censored_immobilization_gbp_days"])
        self.assertEqual(report["summary"]["censored_duration_unknown_count"], 1)
        known = parse(orphan(), end_date=160)
        self.assertEqual(known["orphans"][0]["censored_days"], 60)
        self.assertEqual(known["orphans"][0]["censored_immobilization_gbp_days"], 720000)
        invalid = parse(orphan(), reuse(date=190, station=100), end_date=150)
        self.assertIsNone(invalid["end_date"])
        self.assertIsNone(invalid["orphans"][0]["censored_days"])
        self.assertIn("invalid_end_date", invalid["summary"]["warning_counts"])

    def test_prior_references_refuse_first_service_assertion(self):
        report = parse(orphan(), reuse(prior=2))
        item = report["orphans"][0]
        self.assertEqual(item["status"], "prior_service_unverified")
        self.assertIsNone(item["productive_cost_a_gbp"])
        self.assertIsNone(item["delay_days"])

    def test_duplicate_origin_duplicate_reuse_and_recycled_station(self):
        duplicated = parse(orphan(), orphan(), reuse())
        self.assertTrue(all(r["status"] == "ambiguous_duplicate"
                            for r in duplicated["orphans"]))
        two_reuses = parse(orphan(), reuse(), reuse())
        self.assertEqual(two_reuses["orphans"][0]["status"], "ambiguous_duplicate")
        recycled = parse(orphan(), reuse(), orphan(date=190, anchor=301),
                         reuse(date=200, anchor=301, line=20))
        self.assertTrue(all(r["status"] == "ambiguous_station_recycled"
                            for r in recycled["orphans"]))

    def test_invalid_fields_rejected_without_false_join(self):
        missing = orphan().replace(" station=31", "")
        bad_side = reuse().replace("reuse_b=1", "reuse_b=0")
        negative = orphan().replace("cost_a=12000", "cost_a=-1")
        report = parse(missing, bad_side, negative, reuse())
        self.assertEqual(report["summary"]["orphan_count"], 0)
        self.assertEqual(report["summary"]["first_use_confirmed"], 0)
        self.assertEqual(report["summary"]["warning_counts"]["missing_fields"], 1)
        self.assertEqual(report["summary"]["warning_counts"]["invalid_numeric"], 1)
        self.assertEqual(report["summary"]["warning_counts"]["inconsistent_reuse_side"], 1)
        self.assertEqual(report["summary"]["unmatched_reuse_count"], 1)

    def test_reversed_dates_and_unknown_filename_are_untrusted(self):
        backwards = parse(orphan(date=190), reuse(date=140), reuse(date=200, line=30))
        self.assertEqual(backwards["orphans"][0]["status"], "ambiguous_chronology")
        self.assertIn("date_regression", backwards["summary"]["warning_counts"])
        unknown = parse(orphan(), reuse(), filename="engine.log")
        self.assertEqual(unknown["summary"]["orphan_count"], 0)
        self.assertIn("unknown_run_metadata", unknown["summary"]["warning_counts"])

    def test_multiple_runs_are_isolated_by_seed_arm_repeat(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            files = [
                root / "reference_seed42_r0.log",
                root / "variant_seed42_r0.log",
                root / "reference_seed42_r1.log",
                root / "reference_seed100_r0.log",
            ]
            for p in files:
                p.write_text(orphan() + "\n", encoding="utf-8")
            # Réemploi variant ne valide pas l'actif du bras reference.
            files[1].write_text(reuse() + "\n", encoding="utf-8")
            files[2].write_text(orphan() + "\n" + reuse() + "\n",
                                encoding="utf-8")
            result = analyse_files(files)
            per_run = {(r["arm"], r["seed"], r["repeat"]): r
                       for r in result["runs"]}
            self.assertEqual(len(per_run), 4)
            self.assertEqual(per_run["reference", 42, 0]["summary"]["first_use_confirmed"], 0)
            self.assertEqual(per_run["variant", 42, 0]["summary"]["first_use_confirmed"], 0)
            self.assertEqual(per_run["reference", 42, 1]["summary"]["first_use_confirmed"], 1)
            self.assertEqual(per_run["reference", 100, 0]["summary"]["first_use_confirmed"], 0)
            self.assertEqual(result["summary"]["first_use_confirmed"], 1)
            self.assertEqual(result["by_arm"]["reference"]["first_use_confirmed"], 1)
            self.assertEqual(result["by_arm"]["variant"]["first_use_confirmed"], 0)

    def test_duplicate_run_rejected_and_cli_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for suffix in ("", "_engine"):
                (root / f"reference_seed42_r0{suffix}.log").write_text(
                    orphan() + "\n" + reuse() + "\n", encoding="utf-8")
            data = analyse_files(root.glob("*.log"))
            self.assertTrue(all("duplicate_run" in r["summary"]["warning_counts"]
                                for r in data["runs"]))
            self.assertTrue(all(not r["orphans"] for r in data["runs"]))
            output = root / "report.json"
            with redirect_stdout(io.StringIO()):
                rc = main([str(root), "--json", str(output)])
            self.assertEqual(rc, 0)
            self.assertEqual(len(json.loads(output.read_text(encoding="utf-8"))["runs"]), 2)


if __name__ == "__main__":
    unittest.main()
