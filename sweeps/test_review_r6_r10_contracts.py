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
    def test_r6_compat_settings_are_explicitly_documented(self):
        info = _read("ai/OpexAI/info.nut")
        self.assertIn('name = "c80_double_register"', info)
        self.assertIn('ignored: the double-register orchestrator is permanently on', info)
        self.assertIn('name = "c102_air_station_rating_probe"', info)
        self.assertIn('inactive compatibility setting: value is loaded but has no consumer', info)
        self.assertIn('name = "v95_air_targeted_second"', info)
        self.assertIn('name = "v95_air_post73_targeted"', info)

    def test_r6_compat_settings_remain_loaded_without_behavior_toggle(self):
        settings = _read("ai/OpexAI/settings.nut")
        self.assertIn('V95_AIR_TARGETED_SECOND = AIController.GetSetting("v95_air_targeted_second") != 0;', settings)
        self.assertIn('V95_AIR_POST73_TARGETED = AIController.GetSetting("v95_air_post73_targeted") != 0;', settings)
        self.assertIn('C102_AIR_STATION_RATING_PROBE = AIController.GetSetting("c102_air_station_rating_probe") != 0;', settings)
        self.assertIn('C80_DOUBLE_REGISTER = true;', settings)
        self.assertIn('AIController.GetSetting("c80_worker_rail")', settings)
        self.assertNotIn('GetSetting("c80_double_register")', settings)

        # Les trois anciens réglages restent lisibles pour compatibilité de config,
        # mais ne doivent plus piloter aucun chemin métier. C80 est différent : son
        # réglage utilisateur est ignoré et le mécanisme est forcé actif.
        root = ROOT / "ai" / "OpexAI"
        inert = ("V95_AIR_TARGETED_SECOND", "V95_AIR_POST73_TARGETED",
                 "C102_AIR_STATION_RATING_PROBE")
        for path in root.rglob("*.nut"):
            if path.name in ("globals_pre.nut", "settings.nut"):
                continue
            text = path.read_text(encoding="utf-8")
            for symbol in inert:
                self.assertNotIn(symbol, text, f"unexpected R6 consumer {symbol} in {path.name}")

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

        self.assertIn("if (C105_AIR_REPLAY_CHOICE_PHYSICAL_ECONOMICS && C72_PLANE_CHOICE == 0", air)
        self.assertIn("if (C111_AIR_C100_DECISION_SHADOW && C72_PLANE_CHOICE == 0", air)
        self.assertIn("if (C115_AIR_C100_CAPITAL_REPLAY && C72_PLANE_CHOICE == 0", air)
        self.assertIn("if (C104_AIR_C100_COMPARE_PROBE && !C115_AIR_C100_CAPITAL_REPLAY", air)
        self.assertIn("C122_AIR_THREAT_PROBE = AIController.GetSetting(\"c122_air_threat_probe\") != 0 || C122_AIR_THREAT_RETRY;", settings)

    def test_r9_locked_branches_stay_locked_until_opcode_measurement(self):
        # R9 : branches mortes mais conditions evaluees ; leur retrait change
        # les opcodes executes. Verrouillage conserve tant que non mesure.
        settings = _read("ai/OpexAI/settings.nut")
        pre = _read("ai/OpexAI/globals_pre.nut")
        cands = _read("ai/OpexAI/candidates.nut")
        projects = _read("ai/OpexAI/projects.nut")
        self.assertIn("BASIN_SHARE = false;", settings)
        self.assertIn("JOIN_MAX_DISTANCE = 0;", settings)
        self.assertIn("C39_ENGINE_REFRESH = false;", settings)
        self.assertNotIn('GetSetting("basin_share")', settings)
        self.assertIn("OPEX_ECONOMY_OPCODE_COMPAT_FALSE", pre)
        self.assertIn("WATER_OPCODE_COMPAT_FALSE", pre)
        self.assertIn("function OpexShareBasin(", cands)
        # Trois sites existent désormais dans candidates.nut. Deux peuvent devenir
        # sémantiques si BASIN_SHARE est réactivé (reuse fret + génération fret).
        # Le troisième est dans la chaîne goods et reste dominé par `ss != null`
        # juste avant : il ne peut donc jamais appeler OpexShareBasin, mais son test
        # de BASIN_SHARE consomme encore des opcodes sur le chemin historique false.
        self.assertEqual(cands.count("if (BASIN_SHARE && ss != null)"), 3)
        self.assertRegex(
            cands,
            r"local ss = OpexOriginService\(lines, source\.tile\);\s*"
            r"if \(ss != null\) continue;\s*"
            r"local inputMonthly = AIIndustry\.GetLastMonthProduction\(source\.id, cargoIn\);\s*"
            r"if \(BASIN_SHARE && ss != null\)",
        )
        self.assertIn("if (BASIN_SHARE && srcService != null)", projects)


if __name__ == "__main__":
    unittest.main()
