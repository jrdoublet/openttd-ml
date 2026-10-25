"""Offline contracts for bounded freight attrition, including PO01C generator provenance."""
import io
import unittest
from pathlib import Path
from contextlib import redirect_stdout

from po01c_generate import generated
from diag_freight_attrition import decode_lines, summarize, render, read_paths


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(filename):
    return (AI / filename).read_text(encoding="utf-8")


class FreightAttritionContracts(unittest.TestCase):
    def test_off_and_v276_do_not_allocate_or_observe(self):
        code = source("candidates.nut")
        self.assertIn("!DECISION_LOG || V276_CAND_SLICES > 0", code)
        self.assertIn("AIMap.GetMapSizeX() != 256", code)
        self.assertIn("AIMap.GetMapSizeY() != 256", code)
        self.assertIn("targetKind != null || targetId >= 0", code)
        self.assertIn('if (attrition != null) OpexFreightAttritionFlush(attrition, "legacy")', code)
        # No new candidate policy: existing guard remains authoritative.
        self.assertIn("if (ss != null || st != null) {", code)
        self.assertIn("stats.pairsOriginServed++;", code)
        self.assertIn("if (attritionTrack && monthly > 0)", code)
        self.assertIn("return left == 0 && distance <= 200 ? distance : -1;", code)
        self.assertIn("attrition.sourceSampleOrder.len() >= 8", code)
        self.assertIn('OpexDecide("FREIGHT_ATTRITION_SOURCE",', code)
        self.assertIn('" source_samples=" + attrition.sourceSampleOrder.len()', code)
        self.assertIn('" truncated_sources=" + attrition.truncatedSources', code)
        sample = code.split("function OpexFreightAttritionSource(", 1)[1].split(
            "function OpexFreightAttritionFlush(", 1)[0]
        for banned in ("AIIndustry.", "AITown.", "AICargo.", "AIMap.",
                       "OpexMakeCandidate(", "OpexOriginService(", "AStar", "FindPath"):
            self.assertNotIn(banned, sample)
        self.assertIn("local band = distance <= 78 ? 0 : (distance <= 160 ? 1 : 2);", code)
        self.assertIn("attrition.bins[band * 12 + side * 4 + relation]++;", code)
        observation = code.split("function OpexFreightAttritionTown(", 1)[1].split(
            "function OpexFreightAttritionFlush(", 1)[0]
        self.assertNotIn("AIIndustry.", observation)
        self.assertNotIn("AITown.", observation)
        self.assertNotIn("AICargo.", observation)
        self.assertNotIn("AIMap.", observation)
        self.assertNotIn("OpexMakeCandidate(", observation)

    def test_po01c_is_generated_and_not_written_by_hand(self):
        self.assertEqual(source("po01c_generators.nut"), generated())
        self.assertIn('OpexFreightAttritionFlush(attrition, "po01c")',
                      source("po01c_generators.nut"))
        self.assertIn('OpexFreightAttritionSource(attrition, source.id, source.tile, ss,',
                      source("po01c_generators.nut"))
        flow = source("po01c_regen.nut")
        self.assertIn("if (all.len() > previousCount) { generated.freightCargo = cargo; break; }", flow)
        self.assertLess(source("po01c_generators.nut").index(
            'OpexFreightAttritionFlush(attrition, "po01c")'),
            source("po01c_generators.nut").index(
                'OpexPO01CWhere("OpexPO01CFreightCandidates", "after_last_yield"'))
        self.assertEqual(source("candidates.nut").count("OpexFreightAttritionTown("), 2)
        self.assertIn('if (attrition != null) OpexFreightAttritionFlush(attrition, "legacy")', source("candidates.nut"))
        self.assertNotIn("OpexFreightAttritionTown(", source("candidates_v276.nut"))


class FreightAttritionReader(unittest.TestCase):
    def test_rollover_fixture_contiguous_opex_block_crosses_day_and_year(self):
        fixture = Path(__file__).resolve().parent / "fixtures" / "freight_attrition_source_rollover_seed42_r0.log"
        rows = read_paths([fixture])
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["year"] for row in rows], [1974, 1980])
        self.assertEqual([len(row["samples"]) for row in rows], [2, 2])
        self.assertEqual([s["accounting_year"] for s in rows[0]["samples"]], [1974, 1974])
        self.assertEqual([s["accounting_year"] for s in rows[1]["samples"]], [1980, 1980])
        self.assertEqual(rows[1]["samples"][0]["year"], 1979)  # emission vs accounting
        self.assertEqual(rows[1]["samples"][1]["year"], 1980)
        result = summarize(rows)
        self.assertEqual([item["year"] for item in result["source_years"]], [1974, 1980])
        self.assertEqual([item["distinct_sources_sampled"] for item in result["source_years"]], [2, 2])
        self.assertEqual(result["coverage"]["source_probe_invocations"], 2)

    def test_strict_rollover_block_rejects_intervening_opex_or_mismatched_dates(self):
        fixture = Path(__file__).resolve().parent / "fixtures" / "freight_attrition_source_rollover_seed42_r0.log"
        lines = fixture.read_text(encoding="utf-8").splitlines()
        cases = [
            # Opponent logs are fine, but an unrelated OPEX emission is NOT.
            [*lines[:2], "OPEX 1974-4-2 VIVIER_GEN mode=rail", *lines[2:]],
            # No old-style summary can interrupt a pending SOURCE block.
            [*lines[:2], self.line([0] * 36, cargo="OTHER", good=0,
                positive=0, rejected=0, zero=0, kept=0, filtered=0), *lines[2:]],
            [lines[0].replace("path=legacy", "path=po01c"), *lines[1:]],
            [lines[0].replace("1974-4-2", "1974-2-1"), *lines[1:]],
            [*lines[:2], lines[2].replace("1974-4-3", "1974-4-1"), *lines[3:]],
            [*lines[:4], lines[4].replace("1979-12-31", "1980-1-2"), *lines[5:]],
            [lines[0].replace("1974-4-2", "1974-2-30"), *lines[1:]],
            [*lines[:3], lines[3].replace("1974-4-3", "1974-4-2"), *lines[4:]],
            [*lines[:3], lines[3].replace("source_samples=2", "source_samples=1"), *lines[4:]],
        ]
        for index, malformed in enumerate(cases):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    decode_lines(malformed, "rollover_seed42_r0.log")

    def test_source_flush_window_inclusive_thirty_days(self):
        fixture = Path(__file__).resolve().parent / "fixtures" / "freight_attrition_source_rollover_seed42_r0.log"
        lines = fixture.read_text(encoding="utf-8").splitlines()
        allowed = [lines[0].replace("1974-4-2", "1974-3-4"), *lines[1:]]
        self.assertEqual(len(decode_lines(allowed, "rollover_seed42_r0.log")), 2)
        refused = [lines[0].replace("1974-4-2", "1974-3-3"), *lines[1:]]
        with self.assertRaisesRegex(ValueError, "flush window"):
            decode_lines(refused, "rollover_seed42_r0.log")

    def test_source_fixture_deduplicates_within_seed_year_and_leaves_unknown_station(self):
        fixture = Path(__file__).resolve().parent / "fixtures" / "freight_attrition_source_seed42_r0.log"
        result = summarize(read_paths([fixture]))
        self.assertEqual(result["coverage"]["source_probe_invocations"], 2)
        self.assertEqual(result["coverage"]["historical_no_source_probe"], 0)
        self.assertEqual(result["coverage"]["source_probe_zero_sample_invocations"], 0)
        year = result["source_years"][0]
        self.assertEqual((year["seed"], year["year"]), (42, 1977))
        self.assertEqual((year["distinct_sources_sampled"], year["sample_rows"]), (2, 3))
        self.assertEqual(year["distinct_towns_at_extremes"], 5)
        self.assertEqual(year["monthly_max_per_source"]["median"], 60)
        self.assertEqual(year["longest_per_source"]["max"], 152)
        self.assertEqual(year["shortest_per_source"]["min"], 46)
        self.assertEqual(year["source_details"][1]["station_ids"], [-1])
        self.assertEqual(year["source_details"][0]["monthly_min"], 80)
        self.assertEqual(year["source_details"][0]["monthly_max"], 100)

    def test_source_probe_exposure_zero_is_not_historical_absence(self):
        bins = [0] * 36
        record = self.line(bins, good=0, positive=0, rejected=0, zero=0, kept=0,
                           filtered=0, cargo="OTHER")
        record = record.replace(" bins=", " source_samples=0 truncated_sources=0 bins=")
        result = summarize(decode_lines([record], "reference_seed7_r0.log"))
        self.assertEqual(result["coverage"]["source_probe_invocations"], 1)
        self.assertEqual(result["coverage"]["source_probe_zero_sample_invocations"], 1)
        self.assertEqual(result["coverage"]["good_unvisited_generations"], 1)

    def test_source_decoder_rejects_partial_mismatch_overflow_and_duplicate(self):
        fixture = Path(__file__).resolve().parent / "fixtures" / "freight_attrition_source_seed42_r0.log"
        lines = fixture.read_text(encoding="utf-8").splitlines()
        cases = [
            lines[:2],
            [lines[0], lines[2]],
            [lines[0], lines[0], lines[2]],
            [lines[0].replace("station=5", "station=-2"), *lines[1:]],
            [lines[0].replace("monthly=80", "monthly=0"), *lines[1:]],
            [lines[0].replace("max_dist=125", "max_dist=201"), *lines[1:]],
            [*lines[:2], lines[2].replace("source_samples=2", "source_samples=0"), *lines[3:]],
            [*lines[:2], lines[2].replace("truncated_sources=0", "truncated_sources=1"), *lines[3:]],
            [lines[0].replace("1977-5-3", "1977-5-4"), *lines[1:]],
            [*lines[:2], lines[2].replace("good_served=3", "good_served=2"), *lines[3:]],
        ]
        for index, case in enumerate(cases):
            with self.subTest(index=index):
                with self.assertRaises(ValueError):
                    decode_lines(case, "reference_seed42_r0.log")

    def test_old_engine_log_without_probe_is_unknown_coverage(self):
        rows = decode_lines(["OPEX 1973-4-9 VIVIER_REJECT reason=origin_served n=42"],
                            "old_seed42_r0.log")
        self.assertEqual(rows, [])
        buf = io.StringIO()
        with redirect_stdout(buf):
            render(summarize(rows))
        self.assertIn("couverture inconnue", buf.getvalue())

    def test_committed_fixture_covers_early_break_and_good(self):
        path = Path(__file__).resolve().parent / "fixtures" / "freight_attrition_v1.log"
        rows = read_paths([path])
        self.assertEqual(len(rows), 2)
        result = summarize(rows)
        self.assertEqual(result["coverage"]["good_unvisited_generations"], 1)
        self.assertEqual(result["coverage"]["good_visited_generations"], 1)
        self.assertEqual(result["total"]["good_served"], 2)
        self.assertEqual(result["total"]["good_qpos"], 4)

    @staticmethod
    def line(bins, *, day="1973-4-9", path="po01c", good=5, positive=4,
             rejected=2, zero=1, kept=1, filtered=1, trunc=0, cargo="GOOD"):
        visited = 1 if cargo == "GOOD" else 0
        return (f"[engine] OPEX {day} FREIGHT_ATTRITION schema=1 path={path} "
                f"scope=invocation cargo={cargo} visited_cargos=1 visited_good={visited} "
                f"total=9 good={good} good_qpos={positive} "
                f"good_served={rejected} good_zero={zero} good_kept={kept} "
                f"good_other={filtered} truncated={trunc} bins="
                + ",".join(str(v) for v in bins))

    def test_strict_roundtrip_and_bins(self):
        bins = [0] * 36
        bins[0] = 1  # <=78, source, same cargo
        bins[17] = 1  # 79..160, destination, other cargo
        rows = decode_lines([self.line(bins)], "seed42_r0.log")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["bins"][0], 1)
        self.assertEqual(rows[0]["bins"][17], 1)
        result = summarize(rows)
        self.assertEqual(result["total"]["good_served"], 2)
        self.assertEqual(result["by_band"]["le78"]["source"]["same"], 1)
        self.assertEqual(result["by_band"]["79_160"]["destination"]["other"], 1)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            render(result)
        self.assertIn("GOOD positif", buffer.getvalue())

    def test_reject_partial_malformed_or_incoherent(self):
        bins = [0] * 36
        bins[0] = 1
        bins[17] = 1
        good = self.line(bins)
        bad = [good.replace("schema=1", "schema=2"),
               good.replace("bins=", "bins=1,"),
               good.replace("path=po01c", "path=v276"),
               good.replace("good_served=2", "good_served=3"),
               good.replace("truncated=0", "truncated=9"),
               good.replace("good_qpos=4", "good_qpos=-1"),
               good.replace("good_zero=1", "good_zero=6"),
               good.replace("cargo=GOOD", "cargo=COAL")]
        for line in bad:
            with self.subTest(line=line[:90]):
                with self.assertRaises(ValueError):
                    decode_lines([line], "seed42_r0.log")

    def test_distinct_generations_are_not_deduplicated(self):
        bins = [0] * 36
        bins[0] = 1
        bins[17] = 1
        lines = [self.line(bins), self.line(bins)]
        rows = decode_lines(lines, "seed42_r0.log")
        self.assertEqual(len(rows), 2)
        self.assertEqual(summarize(rows)["total"]["good_served"], 4)

    def test_po01c_early_cargo_stop_is_missing_good_exposure(self):
        bins = [0] * 36
        row = self.line(bins, cargo="OTHER", good=0, positive=0, rejected=0,
                        zero=0, kept=0, filtered=0)
        result = summarize(decode_lines([row], "seed7_r0.log"))
        self.assertEqual(result["coverage"]["good_unvisited_generations"], 1)
        self.assertEqual(result["coverage"]["good_visited_generations"], 0)
        self.assertEqual(result["total"]["good_served"], 0)
        self.assertNotEqual(result["coverage"]["good_unvisited_generations"], 0)


if __name__ == "__main__":
    unittest.main()
