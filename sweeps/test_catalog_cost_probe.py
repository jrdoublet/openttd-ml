"""Contrat statique de la sonde passive du passage catalogue."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from campaign_freeze import parse_ai_settings

AI = ROOT / "ai" / "OpexAI"


class TestCatalogCostProbe(unittest.TestCase):
    def test_setting_and_transient_gate(self):
        self.assertEqual(parse_ai_settings(AI / "info.nut")["catalog_cost_probe"], 0)
        settings = (AI / "settings.nut").read_text(encoding="utf-8")
        globals_src = (AI / "globals_pre.nut").read_text(encoding="utf-8")
        self.assertIn('CATALOG_COST_PROBE = AIController.GetSetting("catalog_cost_probe") != 0;', settings)
        self.assertIn("CATALOG_COST_PROBE <- false;", globals_src)
        self.assertIn("CATALOG_COST_ACTIVE <- null;", globals_src)

    def test_log_and_measurements_are_guarded(self):
        task = (AI / "scheduler_tasks.nut").read_text(encoding="utf-8")
        projects = (AI / "projects.nut").read_text(encoding="utf-8")
        air = (AI / "builder_air.nut").read_text(encoding="utf-8")
        probes = (AI / "probes.nut").read_text(encoding="utf-8")
        self.assertIn("if (CATALOG_COST_PROBE) {\n    task.catalogCost", task)
        self.assertIn("if (CATALOG_COST_ACTIVE != null) {\n    OpexCatalogCostLog", task)
        self.assertIn("local costMark = cost != null ? OpexOpsMeasureBegin() : null;", projects)
        self.assertIn("if (CATALOG_COST_ACTIVE != null) {\n    local cost = CATALOG_COST_ACTIVE;", air)
        self.assertIn('" CATALOG_COST reason="', probes)
        for field in ("engine_refresh_ops", "rail_ops", "road_ops", "air_ops",
                      "water_ops", "air_towns", "air_new_pairs", "air_sites",
                      "c121_demand_ops", "c121_static_ops", "c121_scan_ops",
                      "c121_winner_ops", "selection_ops"):
            self.assertIn(field, probes)


if __name__ == "__main__":
    unittest.main()
