from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


class TestLegacyTensionRemoved(unittest.TestCase):
    def test_legacy_tension_and_shadow_pricing_are_gone(self):
        self.assertFalse((AI / "tension.nut").exists())

        forbidden = (
            "TENSION_SCORING",
            "SHADOW_PRICING",
            "TENSION_PROBE",
            "TENSION_DECISION_FRICTION",
            "OpexTension",
            "tensionScore",
            "tensionRegime",
            "tension_scoring",
            "shadow_pricing",
            "decision_friction_permille",
            "tension_probe",
            "tension_ctx",
        )
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in AI.glob("*.nut")
        )
        for token in forbidden:
            self.assertNotIn(token, source, token)


if __name__ == "__main__":
    unittest.main()
