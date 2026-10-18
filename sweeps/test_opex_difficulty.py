"""Niveau technique OPEX_DIFFICULTY : infrastructure seule.

OpenTTD 15.3 n'applique plus easy/medium/hard/custom. Le reglage
opex_difficulty vaut donc 2 (difficile) aux quatre niveaux et dans default_value, pour
que le harnais (qui lit custom_value) et le moteur (qui lit default_value,
sinon medium_value) restent d'accord sans allonger la ligne [ai_players].
A l'etape 1 aucune decision ne le lisait. V250 est le premier lecteur :
mode 1 seulement, dans la tache, le crochet caisse et l'activation de la file.
"""
from pathlib import Path
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
ALLOWED = {
    "info.nut", "difficulty.nut", "settings.nut",
}


class TestOpexDifficulty(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.info = cls.sources["info.nut"]
        cls.settings = cls.sources["settings.nut"]

    def test_setting_declared_equal_at_four_levels(self):
        block = self.info[self.info.index('name = "opex_difficulty"'):]
        block = block[:block.index("});") + 3]
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 3", block)
        self.assertIn("flags = 0", block)
        self.assertNotIn("CONFIG_DEVELOPER", block)
        self.assertNotIn("AICONFIG_BOOLEAN", block)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value", "default_value"):
            self.assertIn(level + " = 2", block)
        labels = self.info[self.info.index('AddLabels("opex_difficulty"'):]
        labels = labels[:labels.index("});") + 3]
        self.assertIn('_0 = "easy"', labels)
        self.assertIn('_1 = "medium"', labels)
        self.assertIn('_2 = "hard"', labels)
        self.assertIn('_3 = "custom"', labels)
        self.assertIn("OPEX_DIFFICULTY <- 2;", self.sources["difficulty.nut"])

    def test_read_once_with_legacy_profile_fallback(self):
        reads = [name for name, text in self.sources.items()
                 if 'GetSetting("opex_difficulty")' in text]
        self.assertEqual(reads, ["settings.nut"])
        self.assertEqual(self.settings.count('GetSetting("opex_difficulty")'), 1)
        self.assertEqual(self.settings.count("OPEX_DIFFICULTY = OpexResolveDifficulty();"), 1)
        self.assertEqual(self.settings.count("function OpexResolveDifficulty()"), 1)
        self.assertIn('AIGameSettings.IsValid("script.settings_profile")', self.settings)
        self.assertIn('AIGameSettings.GetValue("script.settings_profile")', self.settings)
        resolver = self.settings[self.settings.index("function OpexResolveDifficulty()"):]
        resolver = resolver[:resolver.index("\nfunction ") if "\nfunction " in resolver else len(resolver)]
        self.assertLess(
            resolver.index('IsValid("script.settings_profile")'),
            resolver.index('GetSetting("opex_difficulty")'))

    def test_no_decision_reads_difficulty(self):
        for name, text in self.sources.items():
            if name in ALLOWED:
                continue
            self.assertNotIn("OPEX_DIFFICULTY", text, name)
            self.assertNotIn("opex_difficulty", text, name)
            self.assertNotIn("OpexResolveDifficulty", text, name)


if __name__ == "__main__":
    unittest.main()
