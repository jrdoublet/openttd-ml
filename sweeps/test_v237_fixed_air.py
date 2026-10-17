"""V237: adopted AIR paths are permanent; diagnostic controls remain separate."""
from pathlib import Path
import re
import unittest
from v237_contracts import AI, RETIRED, assert_retired



class FixedAirContracts(unittest.TestCase):
    def test_every_retired_setting_is_absent(self):
        assert_retired(self, RETIRED)
        # No runtime reference may survive removal of its global declaration.
        for path in AI.glob("*.nut"):
            source = path.read_text(encoding="utf-8")
            code = re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"', '', source, flags=re.S)
            for name in RETIRED:
                with self.subTest(path=path.name, setting=name):
                    self.assertNotRegex(code, rf"\b{re.escape(name.upper())}\b")

    def test_mode_and_c76_dependencies_remain(self):
        projects = (AI / "projects.nut").read_text(encoding="utf-8")
        prep = (AI / "rail_prep_c121.nut").read_text(encoding="utf-8")
        scheduler = (AI / "scheduler_tasks.nut").read_text(encoding="utf-8")
        self.assertIn("if (MODE_AIR && C121_CATALOG_FIRST_YEAR_ACTIVE)", projects)
        self.assertIn("if (!(MODE_AIR && MODE_RAIL)) return false;", prep)
        self.assertIn("c76StartRevisions = C76_REGEN_TARGETED && c76Full", scheduler)
        self.assertIn("if (C76_REGEN_TARGETED &&", scheduler)

    def test_payment_and_fused_winner_have_no_legacy_fallback(self):
        economics = (AI / "air_economics_c121.nut").read_text(encoding="utf-8")
        self.assertNotIn("OpexC119AirIncomeDays", economics)
        self.assertIn("return OpexC121OneOrTwoFused(catalog, plan, plane);", economics)
        self.assertIn("OpexC121GameEngineTryShortcut(catalog, plan, geState.engine)", economics)
        self.assertIn("OpexC121PhysicalPaymentDays(ctx.trip)", economics)
        self.assertIn("OpexC121ScanRoutePlaneEngines(catalog, plan)", economics)

    def test_constructor_preserves_pre_settings_geometry_epoch(self):
        main = (AI / "main.nut").read_text(encoding="utf-8")
        coverage = (AI / "air_coverage.nut").read_text(encoding="utf-8")
        self.assertIn("OpexAirResetSiteCache(false);", main)
        self.assertIn("function OpexAirResetSiteCache(invalidateGeometry = true)", coverage)
        self.assertIn("if (invalidateGeometry) OpexC121InvalidateEndpointGeometry();", coverage)
        self.assertIn("if (invalidateGeometry) OpexAir0310InvalidateSiteValidity();", coverage)

    def test_checkers_and_persisted_strategy_switch_remain(self):
        info = (AI / "info.nut").read_text(encoding="utf-8")
        update = (AI / "projects_update.nut").read_text(encoding="utf-8")
        sites = (AI / "air_sites.nut").read_text(encoding="utf-8")
        for name in ("v94_air_site_check", "v141_catalog_incremental_check", "c121_air_project_realization_adaptive"):
            self.assertIn(f'name = "{name}"', info)
        self.assertIn("if (V94_AIR_SITE_CHECK)", sites)
        self.assertIn("v141Oracle = OpexProjectFromAir", update)
        self.assertIn("V141_CATALOG_INCREMENTAL_CHECK && C56_TASK_TRACE", update)
        self.assertNotIn("local refreshed = OpexProjectFromAir", update)

    def test_sampler_and_fleet_keep_adopted_paths(self):
        probes = (AI / "probes.nut").read_text(encoding="utf-8")
        task = (AI / "task_air.nut").read_text(encoding="utf-8")
        self.assertIn("local skipUnused = !C117_AIR_THROUGHPUT_PROBE;", probes)
        self.assertIn("OpexC121FirstLiveObserve(line, state, ageDaysLean)", probes)
        self.assertNotIn("leanView", probes)
        self.assertNotIn("FLEET_ROUTES_MISMATCH", task)
        self.assertIn("OpexAirCadenceCapIndexed(line, this._catalog, this._lines, routesIndex)", task)
        self.assertIn("fleetEntry.v161Neighbours", task)


if __name__ == "__main__":
    unittest.main()
