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
        self.assertNotIn('AIController.GetSetting("c80_worker_rail")', settings)
        self.assertNotIn('GetSetting("c80_double_register")', settings)
        self.assertNotIn('AIController.GetSetting("c80_worker_town")', settings)

        # Le nettoyage distant retire les symboles inertes, y compris leur chargement.
        root = ROOT / "ai" / "OpexAI"
        inert = ("V95_AIR_TARGETED_SECOND", "V95_AIR_POST73_TARGETED",
                 "C102_AIR_STATION_RATING_PROBE")
        for path in root.rglob("*.nut"):
            text = path.read_text(encoding="utf-8")
            for symbol in inert:
                self.assertNotIn(symbol, text, f"unexpected R6 consumer {symbol} in {path.name}")

    def test_r7_defensive_floor_removed_and_zero_floor_kept(self):
        settings = _read("ai/OpexAI/settings.nut")
        projects = _read("ai/OpexAI/projects.nut")
        info = _read("ai/OpexAI/info.nut")

        self.assertNotIn('name = "c121_air_defensive_floor"', info)
        self.assertNotIn("C121_AIR_DEFENSIVE_FLOOR", settings)
        self.assertIn('PORTFOLIO_FLOOR_PCT = 0;', settings)
        # V258 : constante figee a 0, la branche if (PORTFOLIO_FLOOR_PCT > 0) est retiree
        self.assertNotIn('if (PORTFOLIO_FLOOR_PCT > 0)', projects)
        self.assertNotIn("C121_AIR_DEFENSIVE_FLOOR", projects)

    def test_r8_removed_dead_helpers_are_not_defined_anymore(self):
        rail = _read("ai/OpexAI/builder_rail.nut")
        road = _read("ai/OpexAI/builder_road.nut")
        projects = _read("ai/OpexAI/projects.nut")
        self.assertNotIn("function OpexPlaceCapacitySignals(", rail)
        self.assertNotIn("function OpexRoadFindOrBuildTruckStop(", road)
        self.assertNotIn("function OpexCloneCandidateGroups(", projects)
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

        self.assertNotIn("C115_AIR_C100_CAPITAL_REPLAY", air)
        self.assertIn("C122_AIR_THREAT_PROBE = OpexProbeSetting(\"c122_air_threat_probe\") != 0 || C122_AIR_THREAT_RETRY;", settings)

    def test_r9_opcode_compat_slots_remain(self):
        settings = _read("ai/OpexAI/settings.nut")
        pre = _read("ai/OpexAI/globals_pre.nut")
        self.assertNotIn('GetSetting("basin_share")', settings)
        self.assertIn("OPEX_ECONOMY_OPCODE_COMPAT_FALSE", pre)
        self.assertIn("WATER_OPCODE_COMPAT_FALSE", pre)
        cands = _read("ai/OpexAI/candidates.nut")
        projects = _read("ai/OpexAI/projects.nut")
        self.assertNotIn("function OpexShareBasin(", cands)
        self.assertNotIn("BASIN_SHARE", cands)
        self.assertNotIn("BASIN_SHARE", projects)


if __name__ == "__main__":
    unittest.main()
