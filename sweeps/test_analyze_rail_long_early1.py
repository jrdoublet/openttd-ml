"""Synthetic contracts for passive RAIL-LONG-EARLY-1 decision-log analysis."""

from contextlib import redirect_stdout
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest

from sweeps.analyze_rail_long_early1 import (
    analyze_paths, analyze_sources, decode_line, distance_bin, find_logs,
    main, render_markdown,
)


def event(year, tag, **fields):
    values = " ".join(f"{key}={value}" for key, value in fields.items())
    return f"[script:4] [0] [I] OPEX {year}-7-12 {tag} {values}\n"


def detailed(report, policy="reference", year=None, mode=None, dist=None,
             cargo=None, kind=None):
    rows = report["policies"][policy]["by_year_distance_cargo_kind"]
    expected = {"year": year, "mode": mode, "distance_bin": dist,
                "cargo": cargo, "kind": kind}
    matching = [row for row in rows if all(row[key] == value for key, value in expected.items()
                                              if value is not None)]
    if len(matching) != 1:
        raise AssertionError(f"Expected one row for {expected}, found {matching}")
    return matching[0]


class RailLongEarlyAnalysisTests(unittest.TestCase):
    def test_distance_boundaries_and_unknown(self):
        boundaries = {
            "1": "<=200", "200": "<=200", "201": "201-250",
            "250": "201-250", "251": "251-350", "350": "251-350",
            "351": "351-400", "400": "351-400", "401": ">400",
            "512": ">400", "-1": "unknown", "0": "unknown",
            "abc": "unknown", None: "unknown",
        }
        for value, expected in boundaries.items():
            with self.subTest(value=value):
                self.assertEqual(distance_bin(value), expected)

    def test_decode_prefix_and_ignore_other_lines(self):
        self.assertEqual(
            decode_line(event("1974", "RAIL_LONG_SCREEN", cargo="COAL", kind="freight",
                              dist=350, reason="accepted")),
            (1974, "RAIL_LONG_SCREEN", {"cargo": "COAL", "kind": "freight",
                                        "dist": "350", "reason": "accepted"}),
        )
        self.assertIsNone(decode_line("[0] [I] 1974-7-12 RAIL_LONG_SCREEN cargo=COAL"))
        self.assertIsNone(decode_line(event(1974, "OTHER", dist=400)))
        self.assertIsNone(decode_line("OPEX 1974-13-1 AIR_BUILD dist=50"))

    def test_screen_by_reason_without_double_counting_candidate(self):
        report = analyze_sources([("reference_seed42_r0.log", [
            event(1971, "RAIL_LONG_SCREEN", cargo="GOOD", kind="freight", dist=201,
                  reason="distance_long"),
            event(1971, "RAIL_LONG_SCREEN", cargo="GOOD", kind="freight", dist=201,
                  reason="economics"),
            event(1971, "RAIL_LONG_SCREEN", cargo="GOOD", kind="freight", dist=250,
                  reason="profit"),
            event(1971, "RAIL_LONG_SCREEN", cargo="GOOD", kind="freight", dist=250,
                  reason="ratio"),
            event(1971, "RAIL_LONG_SCREEN", cargo="GOOD", kind="freight", dist=250,
                  reason="accepted"),
            event(1971, "RAIL_LONG_CANDIDATE", cargo="GOOD", kind="freight", dist=250,
                  cap=400, roi=800, profit=12000),
            event(1971, "RAIL_LONG_CANDIDATE", cargo="COAL", kind="freight", dist=400,
                  cap=400),
        ])])
        good = detailed(report, year=1971, mode="rail", dist="201-250",
                        cargo="GOOD", kind="freight")
        self.assertEqual(good["screened"], 5)
        self.assertEqual(good["candidates"], 1)
        self.assertEqual(good["screen_reasons"], {
            "accepted": 1, "distance_long": 1, "economics": 1,
            "profit": 1, "ratio": 1,
        })
        self.assertEqual(good["candidate_caps"], {"400": 1})
        self.assertEqual(detailed(report, year=1971, mode="rail", dist="351-400",
                                  cargo="COAL")["candidates"], 1)
        self.assertEqual(report["policies"]["reference"]["event_coverage"]["RAIL_LONG_SCREEN"], 5)

    def test_year_kind_cargo_and_missing_schema_are_not_imputed(self):
        lines = [
            event(1973, "PROJECT_CHOSEN", mode="rail", kind="freight", cargo="COAL",
                  src=11, dst=22, dist=251),
            event(1973, "RAIL_ATTEMPT", kind="freight", src=11, dst=22,
                  manh=251, ok=0, reason="ABND", iters=4000, search_ops=6200000, ops=7200000),
            event(1973, "RAIL_ATTEMPT", kind="freight", manh=251,
                  ok=1, reason="-", iters=100, search_ops=-1, ops=-1),
            event(1973, "RAIL_ATTEMPT", kind="pax", manh=200,
                  reason="unknown", iters=-1, search_ops=-1),
            event(1973, "RAIL_BUILD", cargo="COAL", dist=251, line=9),
            event(1973, "PROJECT_CHOSEN", mode="air", cargo="PASS", dist=220),
            event(1973, "AIR_BUILD", dist=220, line=10),
            event(1974, "PROJECT_CHOSEN", mode="rail", cargo="GOOD", kind="freight", dist=401),
            event(1974, "PROJECT_CHOSEN", mode="road", cargo="GOOD", kind="freight", dist=401),
        ]
        report = analyze_sources([("reference_seed42_r0.log", lines)])
        rail_chosen = detailed(report, year=1973, mode="rail", dist="251-350",
                               cargo="COAL", kind="freight")
        attempt = detailed(report, year=1973, mode="rail", dist="251-350",
                           cargo="unknown", kind="freight")
        built = detailed(report, year=1973, mode="rail", dist="251-350",
                         cargo="COAL", kind="unknown")
        self.assertEqual(rail_chosen["chosen"], 1)
        self.assertEqual(rail_chosen["attempts"], 0)
        self.assertEqual(attempt["attempts"], 2)
        self.assertEqual(attempt["attempt_failed"], 1)
        self.assertEqual(attempt["attempt_ok"], 1)
        self.assertEqual(attempt["failure_reasons"], {"ABND": 1})
        self.assertEqual(attempt["iters"], {"n": 2, "sum": 4100, "mean": 2050, "median": 2050.0})
        self.assertEqual(attempt["search_ops"], {
            "n": 1, "sum": 6200000, "mean": 6200000, "median": 6200000,
        })
        self.assertEqual(attempt["ops"]["sum"], 7200000)
        self.assertEqual(built["built"], 1)
        air_chosen = detailed(report, year=1973, mode="air", dist="201-250", cargo="PASS")
        air_built = detailed(report, year=1973, mode="air", dist="201-250", cargo="unknown")
        self.assertEqual(air_chosen["chosen"], 1)
        self.assertEqual(air_built["built"], 1)
        self.assertEqual(detailed(report, year=1974, mode="rail", dist=">400")["chosen"], 1)
        self.assertEqual(report["policies"]["reference"]["ignored_other_mode_events"], {"road": 1})
        pax = detailed(report, year=1973, mode="rail", dist="<=200", kind="pax")
        self.assertEqual(pax["attempt_unknown_outcome"], 1)
        self.assertEqual(pax["iters"]["n"], 0)

    def test_refills_by_year_and_cargo(self):
        report = analyze_sources([("reference_seed42_r0.log", [
            event(1975, "V217_RAIL_REFILL", month=23705, cargo="COAL", cash=1000000,
                  startable=0, candidates=2, ops=9000, v269=1, freight_cap=400),
            event(1975, "V217_RAIL_REFILL", month=23706, cargo="COAL", cash=2000000,
                  startable=1, candidates=-1, ops=-1, v269=0, freight_cap=250),
            event(1975, "V217_RAIL_REFILL", month=23707, cargo="GOOD", cash=4000000,
                  startable=0, candidates=3, ops=15000, v269=1, freight_cap=400),
        ])])
        rows = report["policies"]["reference"]["refills_by_year_cargo"]
        self.assertEqual(len(rows), 2)
        coal = next(row for row in rows if row["cargo"] == "COAL")
        self.assertEqual(coal["calls"], 2)
        self.assertEqual(coal["v269_active"], 1)
        self.assertEqual(coal["freight_caps"], {"250": 1, "400": 1})
        self.assertEqual(coal["ops"], {"n": 1, "sum": 9000, "mean": 9000, "median": 9000})
        self.assertEqual(coal["candidates"]["n"], 1)

    def test_air_coranking_is_descriptive_and_separated_by_file(self):
        lines = [
            event(1974, "PORTFOLIO_RANK", rank=0, mode="rail", kind="freight",
                  cargo="GOOD", dist=300),
            event(1974, "PORTFOLIO_RANK", rank=1, mode="air", kind="pax",
                  cargo="PASS", dist=120),
            event(1974, "PORTFOLIO_RANK", rank=0, mode="rail", kind="freight",
                  cargo="COAL", dist=190),
            event(1974, "PORTFOLIO_RANK", rank=1, mode="air", kind="pax",
                  cargo="PASS", dist=230),
            event(1974, "PORTFOLIO_RANK", rank=0, mode="air", kind="pax",
                  cargo="PASS", dist=125),
            event(1974, "PORTFOLIO_RANK", rank=1, mode="rail", kind="freight",
                  cargo="COAL", dist=290),
            event(1974, "PORTFOLIO_RANK", rank=0, mode="rail", kind="freight",
                  cargo="GOOD", dist=351),
            event(1974, "PROJECT_CHOSEN", mode="rail", kind="freight",
                  cargo="GOOD", dist=351),
            event(1974, "PORTFOLIO_RANK", rank=1, mode="air", kind="pax",
                  cargo="PASS", dist=120),
        ]
        report = analyze_sources([
            ("reference_seed42_r0.log", lines),
            ("reference_seed100_r0.log", [
                event(1974, "PORTFOLIO_RANK", rank=1, mode="air", dist=100),
            ]),
        ])
        ranking = report["policies"]["reference"]["ranked_lists_by_year"][0]
        self.assertEqual(ranking["lists"], 4)
        self.assertEqual(ranking["rail_heads"], 3)
        self.assertEqual(ranking["air_heads"], 1)
        self.assertEqual(ranking["long_rail_heads"], 2)
        self.assertEqual(ranking["rail_head_with_air_ranked"], 2)
        self.assertEqual(ranking["long_rail_head_with_air_ranked"], 1)
        text = render_markdown(report)
        self.assertIn("AIR derrière une tête RAIL", text)
        self.assertIn("ni éviction causale", text)

    def test_gz_and_policy_separation_and_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ref = root / "reference_seed42_r0.log"
            var = root / "variant_seed42_r0.log.gz"
            ref.write_text(event(1970, "PROJECT_CHOSEN", mode="air", cargo="PASS", dist=250),
                           encoding="utf-8")
            with gzip.open(var, "wt", encoding="utf-8") as handle:
                handle.write(event(1970, "AIR_BUILD", dist=250))
            (root / "other.txt").write_text("ignore", encoding="utf-8")
            self.assertEqual(len(find_logs([root, ref])), 2)
            report = analyze_paths([root, ref])
            self.assertEqual(set(report["policies"]), {"reference", "variant"})
            self.assertEqual(len(report["policies"]["reference"]["files"]), 1)
            self.assertEqual(report["policies"]["reference"]["by_year_mode"][0]["chosen"], 1)
            self.assertEqual(report["policies"]["variant"]["by_year_mode"][0]["built"], 1)
            only_var = analyze_paths([root], policy="variant")
            self.assertEqual(list(only_var["policies"]), ["variant"])
            out = root / "report.json"
            main([str(root), "--format", "json", "--out", str(out)])
            self.assertIn("passive_decision_log_event_counts", out.read_text(encoding="utf-8"))
            with io.StringIO() as output, redirect_stdout(output):
                main([str(root), "--policy", "reference"])
                self.assertIn("Politique `reference`", output.getvalue())
                self.assertNotIn("Politique `variant`", output.getvalue())

    def test_no_inputs_matching_is_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "Aucun journal"):
                analyze_paths([Path(directory)])
            with self.assertRaises(FileNotFoundError):
                analyze_paths([Path(directory) / "missing.log"])


if __name__ == "__main__":
    unittest.main()
