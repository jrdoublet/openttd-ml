import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "sweeps") not in sys.path:
    sys.path.insert(0, str(ROOT / "sweeps"))

from sweeps.parse_air_finance_margin import (
    FIXTURE_SEED42,
    FIXTURE_SEED100,
    aggregate_runs,
    calc_median,
    calc_p90,
    calc_percentile,
    clean_log_line,
    collect_log_files,
    compute_group_metrics,
    main,
    parse_first_revenue_line,
    parse_kv_payload,
    parse_log_file,
    parse_log_filename,
    parse_log_stream,
    parse_pending_line,
    parse_try_line,
    render_report_table,
    summarize_distribution,
)


class TestFilenameParsing(unittest.TestCase):
    """Vérifie la robustesse de l'extraction arm, seed et repeat depuis le nom."""

    def test_standard_pattern(self):
        meta = parse_log_filename("p6_shadow_seed100_r0.log")
        self.assertEqual(meta["arm"], "p6_shadow")
        self.assertEqual(meta["seed"], 100)
        self.assertEqual(meta["repeat"], 0)

    def test_arm_and_seed_without_repeat(self):
        meta = parse_log_filename("/path/to/results/ref_arm_seed42.log")
        self.assertEqual(meta["arm"], "ref_arm")
        self.assertEqual(meta["seed"], 42)
        self.assertEqual(meta["repeat"], 0)

    def test_seed_only(self):
        meta = parse_log_filename("seed999_r2.log")
        self.assertEqual(meta["arm"], "")
        self.assertEqual(meta["seed"], 999)
        self.assertEqual(meta["repeat"], 2)

    def test_arbitrary_filename_with_seed(self):
        meta = parse_log_filename("experiment_v102_seed5678_diag.log")
        self.assertEqual(meta["seed"], 5678)
        self.assertEqual(meta["arm"], "experiment_v102")

    def test_fallback(self):
        meta = parse_log_filename("engine_output.log")
        self.assertEqual(meta["seed"], 0)
        self.assertEqual(meta["arm"], "")


class TestLineAndKVParsing(unittest.TestCase):
    """Vérifie le parsing des tokens et des paires clé=valeur."""

    def test_clean_line_and_ansi_strip(self):
        raw = "\x1b[32m[2026-10-06] AIR_FINANCE_TRY outcome=built\x1b[0m\r\n"
        cleaned = clean_log_line(raw)
        self.assertEqual(cleaned, "[2026-10-06] AIR_FINANCE_TRY outcome=built")

    def test_parse_kv_payload(self):
        payload = 'path=0 rank=1 src_town="New Town" margin=15000 outcome=refused_margin'
        kv = parse_kv_payload(payload)
        self.assertEqual(kv["path"], "0")
        self.assertEqual(kv["rank"], "1")
        self.assertEqual(kv["src_town"], "New Town")
        self.assertEqual(kv["margin"], "15000")
        self.assertEqual(kv["outcome"], "refused_margin")

    def test_parse_try_line_types(self):
        kv = {
            "path": "air_0",
            "rank": "0",
            "src_town": "10",
            "dst_town": "20",
            "new_airports": "2",
            "margin": "15000",
            "reserve": "10000",
            "capital": "40000",
            "need": "65000",
            "cash": "55000",
            "outcome": "refused_margin",
            "date": "1971-05-12",
            "unknown_extra": "foo_bar",
        }
        rec = parse_try_line(kv, seed=42, arm="test_arm")
        self.assertEqual(rec.seed, 42)
        self.assertEqual(rec.arm, "test_arm")
        self.assertEqual(rec.new_airports, 2)
        self.assertEqual(rec.margin, 15000.0)
        self.assertEqual(rec.reserve, 10000.0)
        self.assertEqual(rec.capital, 40000.0)
        self.assertEqual(rec.need, 65000.0)
        self.assertEqual(rec.cash, 55000.0)
        self.assertEqual(rec.outcome, "refused_margin")
        self.assertEqual(rec.date, "1971-05-12")
        self.assertIn("unknown_extra", rec.raw_kv)

    def test_parse_try_negative_cost_normalization(self):
        kv = {
            "outcome": "built",
            "planned": "-30000",
            "actual": "-35000",
            "line": "5",
        }
        rec = parse_try_line(kv, seed=1, arm="")
        self.assertEqual(rec.planned, 30000.0)
        self.assertEqual(rec.actual, 35000.0)

    def test_parse_first_revenue_and_pending(self):
        fr_kv = {
            "line": "3",
            "build_date": "1972-01-01",
            "first_date": "1972-04-15",
            "days": "105",
            "cash_min": "12500",
        }
        fr = parse_first_revenue_line(fr_kv, seed=42, arm="arm")
        self.assertEqual(fr.line, 3)
        self.assertEqual(fr.days, 105.0)
        self.assertEqual(fr.cash_min, 12500.0)

        p_kv = {
            "line": "4",
            "build_date": "1972-05-01",
            "days": "200",
        }
        p = parse_pending_line(p_kv, seed=42, arm="arm")
        self.assertEqual(p.line, 4)
        self.assertEqual(p.days, 200.0)


class TestStatisticsHelpers(unittest.TestCase):
    """Vérifie le calcul des statistiques (médiane, p90, percentiles)."""

    def test_empty_statistics(self):
        self.assertIsNone(calc_percentile([], 0.5))
        self.assertIsNone(calc_median([]))
        self.assertIsNone(calc_p90([]))
        summary = summarize_distribution([])
        self.assertEqual(summary["count"], 0)
        self.assertIsNone(summary["median"])

    def test_single_value(self):
        self.assertEqual(calc_percentile([42.0], 0.9), 42.0)
        self.assertEqual(calc_median([42.0]), 42.0)

    def test_linear_percentile(self):
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        # p90: (5 - 1) * 0.9 = 3.6 -> 40 * 0.4 + 50 * 0.6 = 46.0
        self.assertEqual(calc_p90(vals), 46.0)
        self.assertEqual(calc_median(vals), 30.0)


class TestStreamAndLinking(unittest.TestCase):
    """Vérifie la liaison entre TRY (built), FIRST_REVENUE et PENDING."""

    def test_link_reserve_and_new_airports(self):
        lines = [
            "AIR_FINANCE_TRY outcome=built line=1 new_airports=2 margin=10000 reserve=15000 planned=20000 actual=22000",
            "AIR_FINANCE_FIRST_REVENUE line=1 days=90 cash_min=12000",
            "AIR_FINANCE_PENDING line=1 days=30",
        ]
        run = parse_log_stream(lines, seed=42, arm="test")
        self.assertEqual(len(run.tries), 1)
        self.assertEqual(len(run.first_revenues), 1)
        self.assertEqual(len(run.pendings), 1)

        fr = run.first_revenues[0]
        self.assertEqual(fr.new_airports, 2)
        self.assertEqual(fr.reserve, 15000.0)

        p = run.pendings[0]
        self.assertEqual(p.new_airports, 2)


class TestGroupMetricsCalculations(unittest.TestCase):
    """Vérifie les formules spécifiques demandées par la spécification."""

    def test_refused_margin_binding_and_shortfall(self):
        # 1 binding refused_margin, 1 non-binding or refused_capital, 1 built
        tries = [
            parse_try_line(
                {
                    "outcome": "refused_margin",
                    "capital": "30000",
                    "reserve": "10000",
                    "margin": "10000",
                    "need": "50000",
                    "cash": "45000",
                },
                seed=1,
                arm="",
            ),
            parse_try_line(
                {
                    "outcome": "refused_capital",
                    "capital": "30000",
                    "reserve": "10000",
                    "margin": "10000",
                    "need": "50000",
                    "cash": "35000",
                },
                seed=1,
                arm="",
            ),
            parse_try_line(
                {
                    "outcome": "built",
                    "capital": "30000",
                    "reserve": "10000",
                    "margin": "10000",
                    "need": "50000",
                    "cash": "60000",
                    "planned": "30000",
                    "actual": "30000",
                    "line": "1",
                },
                seed=1,
                arm="",
            ),
        ]
        metrics = compute_group_metrics(tries, [], [])
        self.assertEqual(metrics["attempts"], 3)
        ref_m = metrics["refused_margin"]
        self.assertEqual(ref_m["count"], 1)
        self.assertAlmostEqual(ref_m["share_of_attempts"], 1 / 3)
        self.assertAlmostEqual(ref_m["share_of_refused"], 1 / 2)
        self.assertEqual(ref_m["shortfall_median"], 5000.0)  # 50000 - 45000
        self.assertEqual(ref_m["binding_verified_count"], 1)

    def test_overrun_gt_margin(self):
        tries = [
            # Overrun = 15000 > margin 10000
            parse_try_line(
                {
                    "outcome": "built",
                    "margin": "10000",
                    "planned": "20000",
                    "actual": "35000",
                    "line": "1",
                },
                seed=1,
                arm="",
            ),
            # Overrun = 5000 <= margin 10000
            parse_try_line(
                {
                    "outcome": "built",
                    "margin": "10000",
                    "planned": "20000",
                    "actual": "25000",
                    "line": "2",
                },
                seed=1,
                arm="",
            ),
            # Failed: overrun = -10000 <= margin 10000
            parse_try_line(
                {
                    "outcome": "failed",
                    "margin": "10000",
                    "planned": "20000",
                    "actual": "10000",
                    "line": "3",
                    "reason": "ERR_TERRAIN",
                },
                seed=1,
                arm="",
            ),
        ]
        metrics = compute_group_metrics(tries, [], [])
        bf = metrics["built_failed"]
        self.assertEqual(bf["count"], 3)
        self.assertEqual(bf["overrun_gt_margin_count"], 1)
        self.assertAlmostEqual(bf["overrun_gt_margin_share"], 1 / 3)
        self.assertEqual(bf["count_actual_gt_planned"], 2)  # lines 1 & 2
        self.assertAlmostEqual(bf["share_actual_gt_planned"], 2 / 3)

    def test_first_revenue_reserve_breach(self):
        first_revs = [
            parse_first_revenue_line(
                {"line": "1", "days": "100", "cash_min": "8000", "reserve": "10000"},
                seed=1,
                arm="",
            ),
            parse_first_revenue_line(
                {"line": "2", "days": "120", "cash_min": "15000", "reserve": "10000"},
                seed=1,
                arm="",
            ),
        ]
        metrics = compute_group_metrics([], first_revs, [])
        frev = metrics["first_revenue"]
        self.assertEqual(frev["count"], 2)
        diff_info = frev["cash_min_minus_reserve"]
        self.assertEqual(diff_info["breached_count"], 1)  # line 1: 8000 - 10000 = -2000
        self.assertAlmostEqual(diff_info["breached_share"], 0.5)


class TestFullPipelineAndCLI(unittest.TestCase):
    """Vérifie l'agrégation globale, le rendu et l'interface en ligne de commande."""

    def test_aggregate_fixtures(self):
        run42 = parse_log_stream(
            FIXTURE_SEED42.strip().splitlines(),
            seed=42,
            arm="p6_shadow",
            filename="p6_shadow_seed42_r0.log",
        )
        run100 = parse_log_stream(
            FIXTURE_SEED100.strip().splitlines(),
            seed=100,
            arm="p6_shadow",
            filename="p6_shadow_seed100_r0.log",
        )
        report = aggregate_runs([run42, run100])
        rendered = render_report_table(report)

        self.assertIn("AIR FINANCE MARGIN & EXECUTION REPORT", rendered)
        self.assertIn("42", report["by_seed"])
        self.assertIn("100", report["by_seed"])

    def test_cli_selftest(self):
        exit_code = main(["--selftest"])
        self.assertEqual(exit_code, 0)

    def test_cli_file_and_json_export(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            log1 = tmp_path / "p6_shadow_seed42_r0.log"
            log2 = tmp_path / "p6_shadow_seed100_r0.log"
            out_json = tmp_path / "summary.json"

            log1.write_text(FIXTURE_SEED42.strip() + "\n", encoding="utf-8")
            log2.write_text(FIXTURE_SEED100.strip() + "\n", encoding="utf-8")

            # Lance main avec le dossier en argument et --json
            exit_code = main([str(tmp_path), "--json", str(out_json)])
            self.assertEqual(exit_code, 0)
            self.assertTrue(out_json.exists())

            data = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(data["overall"]["attempts"], 8)
            self.assertEqual(data["metadata"]["seeds_count"], 2)


if __name__ == "__main__":
    unittest.main()
