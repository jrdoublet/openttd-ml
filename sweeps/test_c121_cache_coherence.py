"""Source/reader contracts. Behavioural assertions run in the NoAI fixture."""
from datetime import date
from pathlib import Path
import tempfile
import unittest

from sweeps.run_c121_cache_fixtures import checks_for_logs, scan_checkpoint, stage
from sweeps.campaign_freeze import parse_ai_settings

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai/OpexAI"


class CacheSourceContracts(unittest.TestCase):
    def test_complete_snapshot_roundtrip_fields(self):
        text = (AI / "air_catalog_c121.nut").read_text(encoding="utf-8")
        for stored, field in (("demand", "c121Demand"), ("serviceA", "c121ServiceA"),
                              ("serviceB", "c121ServiceB"), ("engineStatic", "c121EngineStatic"),
                              ("shadowMonthly", "b9ShadowMonthly")):
            self.assertIn(f"plan.{field} <- entry.{stored};", text)
            self.assertIn(f'{stored} = ("{field}" in plan) ? plan.{field} : null', text)
        self.assertLess(text.index("OpexC121CatalogClearPlanSnapshot(plan);", text.index('reason == "new"')),
                        text.index("choice = OpexC121ChooseRoutePlane"))
        self.assertIn("throw error;", text)
        self.assertEqual(text.count("delete plan.c121CatalogRefreshEndpoints;"), 2)

    def test_child_revision_replaces_entry_not_key(self):
        text = (AI / "air_coverage.nut").read_text(encoding="utf-8")
        self.assertIn("old.town == stamp.town && old.station == stamp.station", text)
        self.assertIn("old.geometry == stamp.geometry", text)
        self.assertIn("stamp.date - old.date < 365", text)
        self.assertIn("C121_AIR_ENDPOINT_CACHE.rawset(cacheKey, result)", text)
        self.assertIn("if (cacheStamp != null) result.catalogStamp <- cacheStamp;", text)
        self.assertIn("cacheStamp == null || OpexC121EndpointCacheFresh", text)

    def test_no_default_or_persistence_extension(self):
        settings = parse_ai_settings(AI / "info.nut")
        for name in ("c121_air_economics", "c121_catalog_incremental", "c121_catalog_air_first_year",
                     "c121_fleet_stock_growth", "c121_territory_first", "c121_aaa_line"):
            self.assertEqual(settings[name], 0, name)
        self.assertEqual(settings["c115_air_c100_capital_replay"], 1)
        persist = (AI / "persist.nut").read_text(encoding="utf-8")
        for field in ("C121_CATALOG_ENDPOINT_EPOCH", "catalogStamp", "c121CatalogRefreshEndpoints"):
            self.assertNotIn(field, persist)

    def test_staging_only_copied_main_and_persist(self):
        with tempfile.TemporaryDirectory() as temp:
            copy = stage(Path(temp), True)
            changed = [p.relative_to(AI).as_posix() for p in AI.rglob("*.nut")
                       if p.read_bytes() != (copy / p.relative_to(AI)).read_bytes()]
            self.assertEqual(sorted(changed), ["main.nut", "persist.nut"])
            self.assertTrue((copy / "c121_cache_vm.nut").is_file())
            self.assertIn("FxCSaveBoundary(this);", (copy / "persist.nut").read_text(encoding="utf-8"))


class CacheReaderContracts(unittest.TestCase):
    def test_checkpoint_requires_explicit_nonempty_active_scan(self):
        rows = [{"date": "1970-02-01"}, {"date": "1970-03-01"}]
        n = (date(1970, 3, 1) - date(1, 1, 1)).days + 365
        self.assertIsNone(scan_checkpoint(rows, ""))
        self.assertIsNone(scan_checkpoint(rows, f"C121_CACHE_BOUNDARY active=1 entries=0 date={n}"))
        log = f"C121_CACHE_BOUNDARY active=1 entries=2 date={n}"
        self.assertIs(scan_checkpoint(rows, log), rows[1])
        with self.assertRaises(ValueError):
            scan_checkpoint(rows + [rows[1]], log)

    def test_missing_reload_or_vm_is_not_success(self):
        self.assertFalse(any(checks_for_logs([""]).values()))
        log = "C121_CACHE_VM complete=1 checks=30 restored=1\nC121_CACHE_LIVE arm=newpair pass=1"
        checks = checks_for_logs([log])
        self.assertTrue(checks["synthetic_vm"])
        self.assertFalse(checks["reload_empty_cache"])
        self.assertFalse(checks["reload_rebuild_hit"])
        self.assertTrue(all(checks_for_logs([log, "C121_CACHE_RELOAD empty=1\nLOAD_RECONCILE\n"
                                              "C121_CACHE_LIVE arm=hubsite pass=1"]).values()))


if __name__ == "__main__":
    unittest.main()