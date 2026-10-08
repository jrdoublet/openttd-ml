from pathlib import Path
import unittest
from campaign_freeze import parse_ai_settings

AI = Path(__file__).resolve().parents[1] / "ai/OpexAI"


class FusedPortContracts(unittest.TestCase):
    def test_default_and_scope(self):
        settings = parse_ai_settings(AI / "info.nut")
        self.assertEqual(settings["c121_air_visible_fused"], 0)
        self.assertEqual(settings["c121_air_visible_competition"], 0)
        text = (AI / "settings.nut").read_text(encoding="utf8")
        self.assertIn("C121_AIR_VISIBLE_FUSED = C121_AIR_VISIBLE_COMPETITION", text)
        self.assertNotIn("C121_AIR_VISIBLE_FUSED", (AI / "persist.nut").read_text(encoding="utf8"))

    def test_single_model_and_fallback(self):
        text = (AI / "air_economics_c121.nut").read_text(encoding="utf8")
        self.assertEqual(text.count("function OpexC121AirEconomics("), 1)
        self.assertNotIn("FxVRFused", text)
        self.assertIn("engineContext = null, marginalOut = null", text)
        self.assertIn("if (!(n in captured.values))", text)
        self.assertIn("before = captured.values[have], after = captured.values[have+1]", text)
        fleet = (AI / "air_fleet.nut").read_text(encoding="utf8")
        self.assertIn("if (C121_AIR_VISIBLE_FUSED)", fleet)
        self.assertIn("if (target == null || before == null || after == null) return", fleet)
        self.assertIn("if (samples <= 0)", fleet)


if __name__ == "__main__":
    unittest.main()
