from pathlib import Path
import unittest
from campaign_freeze import parse_ai_settings

AI = Path(__file__).resolve().parents[1] / "ai/OpexAI"


class FusedPortContracts(unittest.TestCase):
    def test_default_and_scope(self):
        settings = parse_ai_settings(AI / "info.nut")
        self.assertNotIn("c121_air_visible_fused", settings)
        self.assertNotIn("c121_air_visible_competition", settings)
        text = (AI / "settings.nut").read_text(encoding="utf8")
        self.assertNotIn("C121_AIR_VISIBLE_FUSED", text)
        self.assertNotIn("C121_AIR_VISIBLE_FUSED", (AI / "globals_pre.nut").read_text(encoding="utf8"))
        self.assertNotIn("C121_AIR_VISIBLE_FUSED", (AI / "persist.nut").read_text(encoding="utf8"))

    def test_single_model_and_fallback(self):
        text = (AI / "air_economics_c121.nut").read_text(encoding="utf8")
        self.assertEqual(text.count("function OpexC121AirEconomics("), 1)
        self.assertNotIn("FxVRFused", text)
        self.assertNotIn("marginalOut", text)
        fleet = (AI / "air_fleet.nut").read_text(encoding="utf8")
        self.assertNotIn("C121_AIR_VISIBLE_FUSED", fleet)
        self.assertNotIn("OpexC121RefreshVisibleFleet", fleet)


if __name__ == "__main__":
    unittest.main()
