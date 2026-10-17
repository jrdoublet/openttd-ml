import unittest
from pathlib import Path
from pathlib import Path as _AirSrcPath
import sys as _air_src_sys
_air_src_sys.path.insert(0, str(_AirSrcPath(__file__).resolve().parent))
from air_source import read_builder_air


ROOT = Path(__file__).resolve().parents[1]
AIR = read_builder_air()
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
SETTINGS = (ROOT / "ai" / "OpexAI" / "settings.nut").read_text(encoding="utf-8")


class C115CapitalReplayTests(unittest.TestCase):
    def test_setting_removed_under_c121_default(self):
        self.assertNotIn("C115_AIR_C100_CAPITAL_REPLAY", GLOBALS)
        self.assertNotIn('name = "c115_air_c100_capital_replay"', INFO)
        self.assertNotIn("c115_air_c100_capital_replay", SETTINGS)
        self.assertNotIn("C115_AIR_C100_CAPITAL_REPLAY", SETTINGS)
        self.assertNotIn("C115_AIR_C100_CAPITAL_REPLAY", AIR)
        self.assertNotIn("function OpexC115ChooseRoutePlane(", AIR)


if __name__ == "__main__":
    unittest.main()
