"""Contrats V275 (Étape 1 V275_AIRTOWN & Étape 2 v275_air_town_free)."""
import gzip
from pathlib import Path
import re
import tempfile
import unittest

import diag_v275_airtowns
from po01c_generate import generated
from test_v261_forum_behaviours import body, source, uncomment

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class TestV275AirTownFree(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.info = cls.sources["info.nut"]
        cls.settings = cls.sources["settings.nut"]
        cls.globals_pre = cls.sources["globals_pre.nut"]
        cls.probes = cls.sources["probes.nut"]
        cls.candidates = cls.sources["candidates.nut"]
        cls.generators = cls.sources["po01c_generators.nut"]
        cls.regen = cls.sources["po01c_regen.nut"]
        cls.builder_rail = cls.sources["builder_rail.nut"]
        cls.persist = cls.sources["persist.nut"]

    def test_setting_default_zero_everywhere_and_read_once(self):
        match = re.search(
            r'AddSetting\(\{\s*name = "v275_air_town_free",(.*?)\}\);',
            self.info,
            re.S,
        )
        self.assertIsNotNone(match, "v275_air_town_free must be declared in info.nut")
        block = match.group(1)
        self.assertIn("min_value = 0, max_value = 100", block)
        self.assertIn("step_size = 5", block)
        self.assertIn("flags = 0", block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(block, rf"\b{level}_value\s*=\s*0\b")
        self.assertIn("V275_AIR_TOWN_FREE <- 0;", self.globals_pre)
        self.assertIn("V275_AIRTOWN_LAST_QUARTER <- -1;", self.globals_pre)

        reads = sum(
            text.count('GetSetting("v275_air_town_free")')
            for text in self.sources.values()
        )
        self.assertEqual(reads, 1)
        self.assertIn(
            'local v275AirFree = AIController.GetSetting("v275_air_town_free");',
            self.settings,
        )
        self.assertIn(
            "V275_AIR_TOWN_FREE = (v275AirFree != null && v275AirFree >= 0 && v275AirFree <= 100) ? v275AirFree : 0;",
            self.settings,
        )
        self.assertEqual(self.info.count("AddSetting("), 59)

    def test_no_saved_state_added(self):
        for symbol in ("V275_AIR_TOWN_FREE", "V275_AIRTOWN_LAST_QUARTER"):
            self.assertNotIn(symbol, self.persist)

    def test_step1_quarterly_log_gated_under_decision_log(self):
        c117 = body("probes.nut", "OpexC117AirThroughputStep")
        self.assertIn(
            "if (DECISION_LOG) OpexV275AirTownQuarterlyTick(lines, catalog, now);",
            c117,
        )
        self.assertIn("if (DECISION_LOG || V275_AIR_TOWN_FREE > 0)", c117)

        qtick = body("probes.nut", "OpexV275AirTownQuarterlyTick")
        guard = "if (!DECISION_LOG) return;"
        self.assertIn(guard, qtick)
        self.assertLess(qtick.index(guard), qtick.index("AIDate.GetYear"))
        self.assertIn(
            "local quarter = AIDate.GetYear(now) * 4 + (AIDate.GetMonth(now) - 1) / 3;",
            qtick,
        )
        self.assertIn("if (quarter == V275_AIRTOWN_LAST_QUARTER) return;", qtick)
        self.assertIn('OpexDecide("V275_AIRTOWN"', qtick)
        for field in (
            "town=",
            "pop=",
            "pax_prod=",
            "pax_air_transported=",
            "share_air=",
            "air_load_pct=",
            "our_stations=",
            "catchment_tiles=",
        ):
            self.assertIn(field, qtick)

    def test_step2_dual_condition_and_airport_catchment_api(self):
        free_fn = body("probes.nut", "OpexV275AirTownFreeOrigin")
        self.assertIn("if (V275_AIR_TOWN_FREE <= 0) return false;", free_fn)
        self.assertIn("if (m.shareAir >= V275_AIR_TOWN_FREE) return false;", free_fn)
        self.assertIn(
            "if (m.airLoadPct < 0 || m.airLoadPct >= V275_AIR_TOWN_FREE) return false;",
            free_fn,
        )
        self.assertIn(
            "if (!OpexV275TownHasFreeRailSite(townTile, paxCargo, railCoverage)) return false;",
            free_fn,
        )

        rect_fn = body("probes.nut", "OpexV275RectInOurAirportCatchment")
        self.assertIn("AIStationList(AIStation.STATION_AIRPORT)", rect_fn)
        self.assertIn("AITileList_StationCoverage(st)", rect_fn)
        self.assertIn("railCatch.KeepList(AITileList_StationCoverage(st));", rect_fn)
        self.assertIn("if (!railCatch.IsEmpty()) return true;", rect_fn)

        metrics_fn = body("probes.nut", "OpexV275AirTownMetrics")
        for api_call in (
            "AITown.GetPopulation(townId)",
            "AITown.GetLastMonthProduction(townId, paxCargo)",
            "AITown.GetLastMonthSupplied(townId, paxCargo)",
            "AITileList_StationCoverage(st)",
            "C117_AIR_LINE_STATE",
        ):
            self.assertIn(api_call, metrics_fn)

    def test_same_rules_in_both_generators_and_zero_guard(self):
        self.assertEqual(self.generators, generated())
        pax_sync = body("candidates.nut", "OpexPaxCandidates")
        pax_async = body("po01c_generators.nut", "OpexPO01CPaxCandidates")
        expected_fragment = (
            "if (V275_AIR_TOWN_FREE <= 0\n"
            "          || !OpexV275AirTownFreeOrigin(line.originA, lines, cargo, catalog.railCoverage)) {\n"
            "        airTowns.rawset(line.originA, true);\n"
            "      }\n"
            "      if (V275_AIR_TOWN_FREE <= 0\n"
            "          || !OpexV275AirTownFreeOrigin(line.originB, lines, cargo, catalog.railCoverage)) {\n"
            "        airTowns.rawset(line.originB, true);\n"
            "      }"
        )
        self.assertIn(expected_fragment, pax_sync)
        self.assertIn(expected_fragment, pax_async)

        sitable_sync = body("candidates.nut", "OpexRailOriginSitable")
        sitable_async = body("po01c_generators.nut", "OpexPO01CRailOriginSitable")
        sitable_guard = "if (V275_AIR_TOWN_FREE > 0 && OpexV275TileInOurAirportCatchment(t, coverage)) continue;"
        self.assertIn(sitable_guard, sitable_sync)
        self.assertIn(sitable_guard, sitable_async)

        for fn_name in (
            "OpexV307SiteTry",
            "OpexV307SpiralPlanCandidates",
            "OpexStationPlans",
        ):
            fn_body = body("builder_rail.nut", fn_name)
            self.assertRegex(
                fn_body,
                r"if \(V275_AIR_TOWN_FREE > 0 && OpexV275PlatformInOurAirportCatchment\(anchor, step, (?:ctx\.)?length, (?:ctx\.)?coverage\)\) continue;",
            )

    def test_po01c_regen_invalidation_coherent(self):
        line_state = body("po01c_regen.nut", "OpexPO01CLineState")
        self.assertIn("if (V275_AIR_TOWN_FREE > 0", line_state)
        self.assertIn("OpexV275AirTownFreeOrigin(line.originA", line_state)
        self.assertIn("OpexV275AirTownFreeOrigin(line.originB", line_state)
        affect = body("po01c_regen.nut", "OpexPO01CLinesAffect")
        self.assertIn("((V275_RAIL_PAX_MM & 1) && old.airRail != state.airRail)", affect)

    def test_squirrel_safety_invariants(self):
        new_fns = [
            uncomment(body("probes.nut", "OpexV275RectInOurAirportCatchment")),
            uncomment(body("probes.nut", "OpexV275TileInOurAirportCatchment")),
            uncomment(body("probes.nut", "OpexV275AirTownMetrics")),
            uncomment(body("probes.nut", "OpexV275TownHasFreeRailSite")),
            uncomment(body("probes.nut", "OpexV275AirTownFreeOrigin")),
            uncomment(body("probes.nut", "OpexV275AirTownQuarterlyTick")),
            uncomment(body("builder_rail.nut", "OpexV275PlatformInOurAirportCatchment")),
        ]
        checked_bodies = [
            uncomment(source("po01c_regen.nut")),
            uncomment(source("po01c_generators.nut")),
            uncomment(body("candidates.nut", "OpexPaxCandidates")),
            uncomment(body("candidates.nut", "OpexRailOriginSitable")),
        ] + new_fns
        for clean in checked_bodies:
            self.assertNotIn(".find(", clean)
            self.assertNotRegex(
                clean,
                r"\blocal\s+(clone|base|parent|static|delegate|vargc|vargv|resume|yield|constructor|instanceof)\b",
            )
            self.assertNotRegex(clean, r"=\s*function\s*\(")
        for clean in new_fns:
            self.assertNotIn(".Valuate(", clean)

    def test_diag_v275_airtowns_parser_and_gzip(self):
        diag_v275_airtowns._selftest()
        log_content = (
            "[0] [I] OPEX 1974-1-1 V275_AIRTOWN town=5 pop=2800 pax_prod=350 "
            "pax_air_transported=70 share_air=20 air_load_pct=18 our_stations=1 catchment_tiles=64\n"
            "[0] [I] OPEX 1974-4-1 V275_AIRTOWN town=5 pop=2900 pax_prod=360 "
            "pax_air_transported=180 share_air=50 air_load_pct=15 our_stations=1 catchment_tiles=64\n"
            "[0] [I] OPEX 1974-4-1 V275_AIRTOWN town=9 pop=4100 pax_prod=500 "
            "pax_air_transported=50 share_air=10 air_load_pct=35 our_stations=1 catchment_tiles=64\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plain = tmp_path / "run1.log"
            plain.write_text(log_content, encoding="utf-8")
            gz = tmp_path / "run2.log.gz"
            with gzip.open(gz, "wt", encoding="utf-8") as fh:
                fh.write(log_content)
            files = list(diag_v275_airtowns.iter_log_files([tmp_path]))
            self.assertEqual(len(files), 2)
            records = []
            for f in files:
                records.extend(diag_v275_airtowns.read_log_file(f))
            self.assertEqual(len(records), 6)
            summary = diag_v275_airtowns.summarize_records(records)
            self.assertEqual(summary["distinct_towns"], 2)
            # Only the first row (share=20, load=18) has both < 25%. Across 2 files => 2 rows.
            self.assertEqual(summary["thresholds"][25]["both_below"], 2)
            # Rows 1 (20,18) and 3 (10,35) have both < 40%. Across 2 files => 4 rows.
            self.assertEqual(summary["thresholds"][40]["both_below"], 4)


if __name__ == "__main__":
    unittest.main()
