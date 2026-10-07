from __future__ import annotations

from pathlib import Path
import re
import unittest
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air
from opex_projects_source import read_projects_source


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    if rel == "ai/OpexAI/projects.nut":
        return read_projects_source()
    return (ROOT / rel).read_text(encoding="utf-8")


class ReviewR6R10ContractsTest(unittest.TestCase):
    def test_r6_worker_settings_remain_loaded(self):
        settings = _read("ai/OpexAI/settings.nut")
        self.assertIn('AIController.GetSetting("c80_worker_rail")', settings)
        self.assertIn('AIController.GetSetting("c80_worker_town")', settings)

    def test_r7_defensive_floor_remains_protected_and_neutralized(self):
        settings = _read("ai/OpexAI/settings.nut")
        projects = _read("ai/OpexAI/projects.nut")
        info = _read("ai/OpexAI/info.nut")

        self.assertIn('name = "c121_air_defensive_floor"', info)
        self.assertIn('global zero floor', info)
        self.assertIn('C121_AIR_DEFENSIVE_FLOOR = AIController.GetSetting("c121_air_defensive_floor") != 0;', settings)
        self.assertIn('PORTFOLIO_FLOOR_PCT = 0;', settings)
        self.assertIn('if (PORTFOLIO_FLOOR_PCT > 0)', projects)
        self.assertRegex(projects, r"c121DefensivePrepared\s*=\s*C121_AIR_ECONOMICS\s*&&\s*C121_AIR_DEFENSIVE_FLOOR")

    def test_r8_removed_dead_helpers_are_not_defined_anymore(self):
        rail = _read("ai/OpexAI/builder_rail.nut")
        road = _read("ai/OpexAI/builder_road.nut")
        self.assertNotIn("function OpexPlaceCapacitySignals(", rail)
        self.assertNotIn("function OpexRoadFindOrBuildTruckStop(", road)
        self.assertIn("function OpexPlaceJoinSignals(", rail)
        self.assertIn("function OpexBuildRoadRoute(", road)

    def test_r8_c102_rating_helpers_are_not_defined_anymore(self):
        root = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
        for path in root.rglob("*.nut"):
            text = path.read_text(encoding="utf-8")
            for name in ("OpexC102WaitingRatingPoints", "OpexC102AgeRatingPoints",
                         "OpexC102SpeedRatingPoints"):
                self.assertNotIn(name, text, f"{name} in {path.name}")

    def test_r10_gate_contracts_for_air_chooser_composition(self):
        air = read_builder_air()
        settings = _read("ai/OpexAI/settings.nut")

        self.assertIn("if (C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS && C72_PLANE_CHOICE == 0", air)
        self.assertIn("if (C111_AIR_C100_DECISION_SHADOW && C72_PLANE_CHOICE == 0", air)
        self.assertIn("if (C115_AIR_C100_CAPITAL_REPLAY && C72_PLANE_CHOICE == 0", air)
        self.assertIn("if (C104_AIR_C100_COMPARE_PROBE && !C115_AIR_C100_CAPITAL_REPLAY", air)
        self.assertIn("C122_AIR_THREAT_PROBE = AIController.GetSetting(\"c122_air_threat_probe\") != 0 || C122_AIR_THREAT_RETRY;", settings)

    def test_r9_opcode_compat_slots_remain(self):
        settings = _read("ai/OpexAI/settings.nut")
        pre = _read("ai/OpexAI/globals_pre.nut")
        self.assertNotIn('GetSetting("basin_share")', settings)
        self.assertIn("OPEX_ECONOMY_OPCODE_COMPAT_FALSE", pre)
        self.assertIn("WATER_OPCODE_COMPAT_FALSE", pre)


if __name__ == "__main__":
    unittest.main()
