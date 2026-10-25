"""Static scope, OFF identity, platform safety and provenance of N75-GSP."""

import hashlib
from pathlib import Path
import re
import unittest
from n75_good_spread_legacy import historical_bytes

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def src(name):
    return (AI / name).read_text(encoding="utf-8")


class GoodOriginSpread(unittest.TestCase):
    def test_setting_modes_default_zero(self):
        info = src("info.nut")
        setting = re.search(r'AddSetting\(\{ name = "good_source_rail_join".*?\}\);', info, re.S)
        self.assertIsNotNone(setting)
        self.assertIn("min_value = 0, max_value = 2", setting.group())
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(level + "_value = 0", setting.group())
        settings = src("settings.nut")
        self.assertEqual(settings.count('AIController.GetSetting("good_source_rail_join")'), 1)
        self.assertIn("N75_GOOD_SOURCE_SPREAD = goodSourceJoinMode == 2;", settings)
        self.assertIn("N75_GOOD_SOURCE_SPREAD <- false;", src("globals_pre.nut"))
        self.assertIn("GOOD_SOURCE_RAIL_JOIN = goodSourceJoinMode >= 1", settings)

    def test_conditional_fallback_and_good_production_guard(self):
        builder = src("builder_rail.nut")
        start = builder.index("/* N75-GSP mode 2")
        end = builder.index("\n      }", start)
        block = builder[start:end]
        self.assertIn("N75_GOOD_SOURCE_SPREAD && jointPlansA.len() == 0", block)
        self.assertIn("OpexV264SpreadJoinPlans(candidate.joinPlatform,", block)
        self.assertIn("candidate.joinStationId, statsA", block)
        self.assertIn("OpexRailPlatformCargoValue(", block)
        self.assertIn("catalog.railCoverage, true) > 0", block)
        self.assertIn('OpexDecide("N75_GOOD_SPREAD"', block)
        self.assertIn("jointPlansA = producingSpread;", block)
        self.assertIn('OpexGoodSourceStationLive(candidate)', builder)
        self.assertIn("strictOriginReuseJoin", builder)
        self.assertIn("p.stationId <- candidate.joinStationId", builder)

    def test_v264_spread_enforces_real_station_limits_and_test_mode(self):
        builder = src("builder_rail.nut")
        for fragment in (
            'AIGameSettings.GetValue("station.distant_join_stations")',
            'AIGameSettings.GetValue("station.station_spread")',
            'AIStation.IsValidStation(stationId)',
            'AIStation.HasStationType(stationId, AIStation.STATION_TRAIN)',
            'local probe = AITestMode();',
            'AIRail.BuildRailStation(anchor, platform.direction, 1, length, stationId)',
        ):
            self.assertIn(fragment, builder)

    def test_exact_predecessor_good_sha_without_rebaselining(self):
        known_good_frozen_sha = {
            "builder_rail.nut": "faf32608a0c7cc52e920f6c82e41409378297808fcdaf6fa03cf5f2db97e3d6c",
            "info.nut": "8850c1379f2cd2dac0c15ca632d24065d64eb016f936b1bffd27a81fcb7f7cba",
            "settings.nut": "259532f2b0e4c59947c30988dd919031fa78c3210eefc8be4a19ebf7fd64cf40",
        }
        for name, frozen in known_good_frozen_sha.items():
            with self.subTest(name=name):
                historical = historical_bytes(name, (AI / name).read_bytes())
                self.assertEqual(hashlib.sha256(historical).hexdigest(), frozen)


if __name__ == "__main__":
    unittest.main()
