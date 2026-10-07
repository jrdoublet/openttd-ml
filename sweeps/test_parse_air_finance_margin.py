import contextlib
import io
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
    FIXTURE_V126,
    V126_COVERAGE_PCTS,
    aggregate_runs,
    calc_median,
    calc_p90,
    calc_percentile,
    clean_log_line,
    collect_log_files,
    compute_group_metrics,
    compute_v126_metrics,
    main,
    parse_first_revenue_line,
    parse_kv_payload,
    parse_log_file,
    parse_log_filename,
    parse_log_stream,
    parse_pending_line,
    parse_try_line,
    render_report_table,
    render_v126_section,
    summarize_distribution,
    v126_residual,
    v126_view,
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


V126_HEADER = "V126 — devis et risque résiduel"


class TestV126QuoteAndResidual(unittest.TestCase):
    """Section V126 : précision du devis, défrichage, arrêts joints, résidu, couverture.

    FIXTURE_V126 compte neuf tentatives, dans cet ordre : quatre builds avec aéroport neuf et
    champs V126 (index 0 à 3, lignes 0 à 3 ; l'index 0 a le réglage à 0, les autres à 1), un
    build sans champ V126 (4), un build `quoted=0` (5), un refus portant les champs (6), un
    échec portant les champs (7) et un build sans aéroport neuf (8). Les valeurs attendues
    ci-dessous sont recalculées à la main, sans passer par le décodeur.
    """

    @classmethod
    def setUpClass(cls):
        run = parse_log_stream(
            FIXTURE_V126.strip().splitlines(),
            seed=7,
            arm="v126_probe",
            filename="v126_probe_seed7_r0.log",
        )
        cls.tries = run.tries
        cls.metrics = compute_v126_metrics(cls.tries)

    def test_fixture_shape(self):
        self.assertEqual(len(self.tries), 9)
        self.assertEqual([t.outcome for t in self.tries[:6]], ["built"] * 6)
        self.assertEqual(self.tries[6].outcome, "refused_margin")
        self.assertEqual(self.tries[7].outcome, "failed")
        self.assertEqual(self.tries[8].new_airports, 0)
        quoted = [i for i, t in enumerate(self.tries) if v126_view(t) is not None]
        self.assertEqual(quoted, [0, 1, 2, 3, 6, 7, 8])

    def test_view_types_the_v126_fields(self):
        view = v126_view(self.tries[2])  # devis A impossible (-1), devis B à 2 000
        self.assertEqual(view["v126"], 1)
        self.assertEqual(view["quote_a"], -1)
        self.assertEqual(view["quote_b"], 2000)
        self.assertEqual(view["quote_fail"], 1)
        self.assertEqual(view["stops_model"], 5400)
        self.assertEqual(view["site_cost"], 34400)
        self.assertEqual(view["extra"], 7400)
        self.assertEqual(view["margin_legacy"], 30000)
        self.assertEqual(view["margin_v126"], 10600)
        self.assertEqual(view["airport_price"], 16200)
        self.assertEqual(view["c_level_a"], 4000)
        self.assertEqual(view["c_stops"], 4000)
        reused = v126_view(self.tries[1])  # extrémité B réutilisée
        self.assertEqual(reused["quote_b"], -2)
        self.assertEqual(v126_view(self.tries[0])["v126"], 0)  # réglage à 0, sonde active

    def test_lines_without_v126_fields_are_ignored(self):
        self.assertIsNone(v126_view(self.tries[4]))  # built sans aucun champ V126
        self.assertIsNone(v126_view(self.tries[5]))  # `quoted=0` : devis non calculés
        self.assertEqual(self.metrics["built_new_airports"], 6)
        self.assertEqual(self.metrics["quoted_built"], 4)
        self.assertEqual(self.metrics["unquoted_built"], 2)
        only_old = compute_v126_metrics([self.tries[4], self.tries[5]])
        self.assertEqual(only_old["quoted_built"], 0)
        self.assertEqual(only_old["unquoted_built"], 2)
        self.assertEqual(only_old["residual_gbp"]["count"], 0)
        self.assertEqual(only_old["coverage"]["count"], 0)
        # Refus, échec et build sans aéroport neuf portent les champs mais restent hors section.
        for index in (6, 7, 8):
            self.assertIsNotNone(v126_view(self.tries[index]))
        only_excluded = compute_v126_metrics(self.tries[6:])
        self.assertEqual(only_excluded["built_new_airports"], 0)
        self.assertEqual(only_excluded["quoted_built"], 0)

    def test_view_needs_every_required_field_to_be_numeric(self):
        kv = {
            "outcome": "built",
            "new_airports": "1",
            "planned": "30000",
            "actual": "31000",
            "quote_a": "0",
            "quote_b": "-2",
            "stops_model": "2700",
            "extra": "2700",
            "margin_legacy": "12000",
            "airport_price": "16200",
        }
        self.assertIsNone(v126_view(parse_try_line(kv, seed=1, arm="")))  # site_cost absent
        kv["site_cost"] = "n/a"
        self.assertIsNone(v126_view(parse_try_line(kv, seed=1, arm="")))  # non numérique
        kv["site_cost"] = "16200"
        view = v126_view(parse_try_line(kv, seed=1, arm=""))
        self.assertIsNotNone(view)
        self.assertIsNone(view["c_level_a"])  # champs c_* optionnels : absents sans erreur
        kv["quoted"] = "0"
        self.assertIsNone(v126_view(parse_try_line(kv, seed=1, arm="")))

    def test_residual_of_each_quoted_build(self):
        # (capital catalogue, devis connu, arrêts modélisés, résidu)
        expected = [
            (41400.0, 3000.0, 5400.0, -800.0),  # 49000 - (41400 + 3000 + 5400)
            (25200.0, 6000.0, 2700.0, 3000.0),  # 36900 - (33900 - 8700 + 6000 + 2700)
            (41400.0, 2000.0, 5400.0, 5300.0),  # devis A à -1 compté 0 : 54100 - 48800
            (25200.0, 0.0, 2700.0, 9900.0),  # site plat, gros défrichage : 37800 - 27900
        ]
        for rec, want in zip(self.tries[:4], expected):
            res = v126_residual(rec, v126_view(rec))
            self.assertEqual(
                (res["capital_catalogue"], res["quote_known"], res["stops_model"], res["residual"]),
                want,
            )

    def test_residual_needs_planned_and_actual(self):
        rec = parse_try_line(
            {"outcome": "built", "new_airports": "1", "planned": "30000"}, seed=1, arm=""
        )
        view = {"extra": 0, "quote_a": 0, "quote_b": -2, "stops_model": 0}
        self.assertIsNone(v126_residual(rec, view))

    def test_cost_breakdown_of_built_lines_sums_to_the_actual_cost(self):
        for rec in self.tries[:4]:
            view = v126_view(rec)
            parts = sum(
                view[key]
                for key in (
                    "c_level_a",
                    "c_airport_a",
                    "c_level_b",
                    "c_airport_b",
                    "c_planes",
                    "c_stops",
                )
            )
            self.assertEqual(parts, rec.actual)

    def test_quote_precision_skips_reused_and_failed_quotes(self):
        # Écarts c_level - devis : T1 A 3500-3000 et B 0-0, T2 A 7600-6000 (B réutilisée),
        # T3 B 2600-2000 (A à -1), T4 A 0-0 (B réutilisée) -> 500, 0, 1600, 600, 0.
        prec = self.metrics["quote_precision"]
        self.assertEqual(prec["count"], 5)
        self.assertEqual(prec["min"], 0.0)
        self.assertEqual(prec["median"], 500.0)
        self.assertEqual(prec["p90"], 1200.0)  # 600 * 0.4 + 1600 * 0.6
        self.assertEqual(prec["max"], 1600.0)
        self.assertEqual(prec["sum"], 2700.0)
        self.assertEqual(prec["gap_threshold_gbp"], 1000)
        self.assertAlmostEqual(prec["share_gt_threshold"], 0.2)
        self.assertAlmostEqual(prec["share_abs_gt_threshold"], 0.2)

    def test_precision_keeps_the_sign_of_the_gap(self):
        # Devis surestimé (réel 3 000 pour un devis de 5 000 : écart -2 000) puis sous-estimé
        # d'exactement 1 000 (le seuil est strict : 1 000 n'est pas un grand écart).
        template = (
            "AIR_FINANCE_TRY date=1971-02-01 rank=0 src_town=1 dst_town=2 new_airports=1 "
            "margin=7550 reserve=5000 capital=33900 need=46450 cash=60000 outcome=built "
            "path=portfolio planned=33900 actual=36000 reason=OK line=%d v126=1 quote_a=%d "
            "quote_b=-2 quote_fail=0 stops_model=2700 site_cost=22200 extra=8700 "
            "margin_legacy=12000 margin_v126=7550 airport_price=16200 c_level_a=3000 "
            "c_airport_a=16200 c_level_b=0 c_airport_b=0 c_planes=9000 c_stops=0"
        )
        run = parse_log_stream([template % (0, 5000), template % (1, 2000)], seed=1, arm="")
        prec = compute_v126_metrics(run.tries)["quote_precision"]
        self.assertEqual(prec["count"], 2)
        self.assertEqual(prec["min"], -2000.0)
        self.assertEqual(prec["median"], -500.0)
        self.assertEqual(prec["max"], 1000.0)
        self.assertAlmostEqual(prec["share_gt_threshold"], 0.0)
        self.assertAlmostEqual(prec["share_abs_gt_threshold"], 0.5)

    def test_clearing_counts_every_new_airport_even_when_its_quote_failed(self):
        # c_airport - prix catalogue 16 200 : T1 800 et 200, T2 1 300, T3 2 300 (devis -1) et 0,
        # T4 10 800 (B réutilisée, non comptée).
        clearing = self.metrics["clearing"]
        self.assertEqual(clearing["count"], 6)
        self.assertEqual(clearing["min"], 0.0)
        self.assertEqual(clearing["median"], 1050.0)  # (800 + 1300) / 2
        self.assertEqual(clearing["p90"], 6550.0)  # 2300 * 0.5 + 10800 * 0.5
        self.assertEqual(clearing["max"], 10800.0)
        self.assertEqual(clearing["sum"], 15400.0)

    def test_joined_stops_are_divided_by_new_airports(self):
        # 3100 / 2, 2600 / 1, 4000 / 2, 1800 / 1
        stops = self.metrics["stops_per_airport"]
        self.assertEqual(stops["count"], 4)
        self.assertEqual(stops["min"], 1550.0)
        self.assertEqual(stops["median"], 1900.0)
        self.assertEqual(stops["p90"], 2420.0)  # 2000 * 0.3 + 2600 * 0.7
        self.assertEqual(stops["max"], 2600.0)

    def test_residual_distributions_in_pounds_and_percent_of_site_cost(self):
        pounds = self.metrics["residual_gbp"]
        self.assertEqual(pounds["count"], 4)
        self.assertEqual(pounds["min"], -800.0)
        self.assertEqual(pounds["median"], 4150.0)  # (3000 + 5300) / 2
        self.assertEqual(pounds["p90"], 8520.0)  # 5300 * 0.3 + 9900 * 0.7
        self.assertEqual(pounds["max"], 9900.0)
        self.assertEqual(pounds["sum"], 17400.0)
        percent = self.metrics["residual_pct_site_cost"]
        self.assertEqual(percent["count"], 4)
        self.assertAlmostEqual(percent["min"], -800 / 35400 * 100)
        self.assertAlmostEqual(percent["max"], 9900 / 16200 * 100)
        self.assertAlmostEqual(
            percent["median"], (3000 / 22200 * 100 + 5300 / 34400 * 100) / 2
        )

    def test_counts_of_flag_and_failed_quotes(self):
        self.assertEqual(self.metrics["flag_on_count"], 3)  # T1 est à v126=0
        self.assertEqual(self.metrics["quote_fail_tries"], 1)  # T3 seul

    def test_coverage_table_against_the_historic_margin(self):
        cov = self.metrics["coverage"]
        self.assertEqual(cov["count"], 4)
        self.assertEqual(cov["margin_floor_gbp"], 2000)
        self.assertEqual([row["pct"] for row in cov["by_pct"]], list(V126_COVERAGE_PCTS))
        # Coûts du site 35 400, 22 200, 34 400 et 16 200 ; résidus -800, 3 000, 5 300, 9 900.
        exceed = {row["pct"]: row["exceed_count"] for row in cov["by_pct"]}
        self.assertEqual(
            exceed, {0: 3, 10: 1, 15: 1, 20: 1, 25: 1, 30: 1, 40: 1, 50: 0, 75: 0, 100: 0}
        )
        margins = {row["pct"]: row["margin_median_gbp"] for row in cov["by_pct"]}
        self.assertEqual(margins[0], 2000.0)
        self.assertEqual(margins[25], 9075.0)  # médiane de 10 850, 7 550, 10 600 et 6 050
        self.assertEqual(margins[100], 30300.0)  # 2 000 + médiane des coûts (28 300 + 2 000)
        shares = {row["pct"]: row["share"] for row in cov["by_pct"]}
        self.assertAlmostEqual(shares[0], 0.75)
        self.assertAlmostEqual(shares[25], 0.25)
        self.assertAlmostEqual(shares[100], 0.0)
        # Régime actuel : réel - capital catalogue contre 30 000 / 12 000 / 30 000 / 12 000 ;
        # seul T4 (12 600 > 12 000) dépasse.
        legacy = cov["legacy"]
        self.assertEqual(legacy["margin_median_gbp"], 21000.0)
        self.assertEqual(legacy["exceed_count"], 1)
        self.assertAlmostEqual(legacy["share"], 0.25)

    def test_coverage_is_monotone_in_the_margin_share(self):
        rows = self.metrics["coverage"]["by_pct"]
        for before, after in zip(rows, rows[1:]):
            self.assertLess(before["pct"], after["pct"])
            self.assertLessEqual(before["margin_median_gbp"], after["margin_median_gbp"])
            self.assertGreaterEqual(before["exceed_count"], after["exceed_count"])

    def test_logged_v126_margin_matches_the_coverage_formula_at_25_percent(self):
        for rec in self.tries[:4]:
            view = v126_view(rec)
            self.assertEqual(view["margin_v126"], 2000 + view["site_cost"] * 25 // 100)

    def test_section_text_for_the_fixture(self):
        text = "\n".join(render_v126_section(self.metrics))
        self.assertIn(V126_HEADER, text)
        self.assertIn("avec champs V126 : 4", text)
        self.assertIn("Réglage air_site_cost_quote actif : 3/4", text)
        self.assertIn("devis impossibles (-1) : 1/4", text)
        self.assertIn("Précision du devis", text)
        self.assertIn("n=5", text)
        self.assertIn("part des écarts > £1,000 : 20.0%", text)
        self.assertIn("Défrichage", text)
        self.assertIn("Arrêts joints", text)
        self.assertIn("Résidu en £", text)
        self.assertIn("Résidu en % du coût du site", text)
        self.assertIn("régime actuel", text)
        self.assertNotIn("aucune donnée :", text)
        for pct in V126_COVERAGE_PCTS:
            self.assertRegex(text, r"\n\s+%d\s+£[\d,]+\s+\d+\s+[\d.]+%%" % pct)

    def test_empty_input_yields_zero_counts_and_a_no_data_section(self):
        for metrics in (compute_v126_metrics([]), None):
            lines = render_v126_section(metrics)
            self.assertEqual(lines[0], V126_HEADER + " :")
            self.assertIn("aucune donnée", lines[1])
        empty = compute_v126_metrics([])
        self.assertEqual(empty["built_new_airports"], 0)
        self.assertEqual(empty["quoted_built"], 0)
        self.assertEqual(empty["quote_precision"]["count"], 0)
        self.assertEqual(empty["coverage"]["count"], 0)
        self.assertEqual(empty["coverage"]["legacy"]["exceed_count"], 0)

    def test_old_fixtures_without_v126_fields_report_no_data(self):
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
        v126 = report["v126"]
        self.assertEqual(v126["quoted_built"], 0)
        self.assertEqual(v126["unquoted_built"], v126["built_new_airports"])
        self.assertEqual(v126["quote_precision"]["count"], 0)
        self.assertEqual(v126["coverage"]["count"], 0)
        rendered = render_report_table(report)
        section = rendered.split(V126_HEADER, 1)[1]
        self.assertIn("aucune donnée", section.splitlines()[1])
        self.assertIn("aucune ne porte les champs V126", section)
        # La section s'ajoute après les sections historiques, qui restent inchangées.
        self.assertLess(rendered.index("AIR FINANCE MARGIN & EXECUTION REPORT"), rendered.index(V126_HEADER))

    def test_cli_json_export_carries_the_v126_aggregates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            log = tmp_path / "v126_probe_seed7_r0.log"
            log.write_text(FIXTURE_V126.strip() + "\n", encoding="utf-8")
            out_json = tmp_path / "out" / "summary.json"

            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                exit_code = main([str(tmp_path), "--json", str(out_json)])
            self.assertEqual(exit_code, 0)
            self.assertIn(V126_HEADER, buffer.getvalue())  # tableau aussi affiché

            data = json.loads(out_json.read_text(encoding="utf-8"))
            v126 = data["v126"]
            self.assertEqual(v126["built_new_airports"], 6)
            self.assertEqual(v126["quoted_built"], 4)
            self.assertEqual(v126["quote_precision"]["median"], 500.0)
            self.assertEqual(v126["residual_gbp"]["median"], 4150.0)
            self.assertEqual(
                [row["pct"] for row in v126["coverage"]["by_pct"]], list(V126_COVERAGE_PCTS)
            )
            self.assertEqual(v126["coverage"]["legacy"]["exceed_count"], 1)
            # Les agrégats existants restent présents à côté de la nouvelle clé.
            self.assertIn("overall", data)
            self.assertIn("by_new_airports", data)

    def test_cli_json_to_stdout_is_json_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log = Path(tmpdir) / "v126_probe_seed7_r0.log"
            log.write_text(FIXTURE_V126.strip() + "\n", encoding="utf-8")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                exit_code = main([str(log), "--json"])
            self.assertEqual(exit_code, 0)
            data = json.loads(buffer.getvalue())
            self.assertEqual(data["v126"]["quoted_built"], 4)

    def test_cli_on_old_campaign_logs_prints_no_data_and_exports_zero_counts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            (tmp_path / "p6_shadow_seed42_r0.log").write_text(
                FIXTURE_SEED42.strip() + "\n", encoding="utf-8"
            )
            (tmp_path / "p6_shadow_seed100_r0.log").write_text(
                FIXTURE_SEED100.strip() + "\n", encoding="utf-8"
            )
            out_json = tmp_path / "summary.json"
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                exit_code = main([str(tmp_path), "--json", str(out_json)])
            self.assertEqual(exit_code, 0)
            self.assertIn("aucune ne porte les champs V126", buffer.getvalue())
            data = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(data["overall"]["attempts"], 8)
            self.assertEqual(data["v126"]["quoted_built"], 0)
            self.assertEqual(data["v126"]["coverage"]["count"], 0)


if __name__ == "__main__":
    unittest.main()
