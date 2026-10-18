"""Contrats statiques des quatre niveaux de difficulte (facile, moyen, difficile, personnalise).

Exigences :
- Le reglage opex_difficulty est visible (flags = 0), avec labels easy, medium, hard, custom.
- Le defaut est 3 (custom, profil des bancs).
- La lecture du reglage est unique dans settings.nut::OpexResolveDifficulty (avec repli 13.4).
- Aucun OPEX_DIFFICULTY n'apparait hors settings.nut et difficulty.nut.
- La V250 est coupee sous le niveau 3 (niveaux 0, 1, 2) via la table centrale.
- Le niveau 3 n'a aucun bridage (OpexLevelAllows renvoie inconditionnellement true).
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _extract_setting_block(info_text, setting_name):
    match = re.search(r'name\s*=\s*"' + re.escape(setting_name) + r'",(.*?)\}\);', info_text, re.S)
    return match.group(1) if match else ""


def _extract_function_body(source_text, function_name):
    pattern = r'function\s+' + re.escape(function_name) + r'\s*\([^)]*\)\s*\{(.*?)\n\}'
    match = re.search(pattern, source_text, re.S)
    return match.group(1) if match else ""


class TestDifficultyLevels(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.relative_to(AI).as_posix(): p.read_text(encoding="utf-8")
                       for p in AI.rglob("*.nut")}
        cls.info = cls.sources["info.nut"]
        cls.settings = cls.sources["settings.nut"]
        cls.difficulty = cls.sources["difficulty.nut"]
        cls.main = cls.sources["main.nut"]

    def test_setting_is_visible(self):
        """1. Le niveau opex_difficulty devient un reglage visible (flags = 0)."""
        block = _extract_setting_block(self.info, "opex_difficulty")
        self.assertTrue(block, "Reglage opex_difficulty introuvable dans info.nut")
        self.assertIn("flags = 0", block)
        self.assertNotIn("flags = 8", block)
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 3", block)

        # Labels explicites
        labels_match = re.search(r'AddLabels\("opex_difficulty",\s*\{(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(labels_match, "AddLabels(opex_difficulty) manquant")
        labels_body = labels_match.group(1)
        self.assertIn('_0 = "easy"', labels_body)
        self.assertIn('_1 = "medium"', labels_body)
        self.assertIn('_2 = "hard"', labels_body)
        self.assertIn('_3 = "custom"', labels_body)

        # Description pour un joueur humain en anglais
        self.assertIn("description =", block)
        self.assertIn("AI difficulty level:", block)
        self.assertIn("Easy", block)
        self.assertIn("Medium", block)
        self.assertIn("Hard", block)
        self.assertIn("Custom", block)

    def test_default_is_three(self):
        """2. Le defaut est 3 (personnalise, profil des bancs)."""
        block = _extract_setting_block(self.info, "opex_difficulty")
        for level in ("easy_value", "medium_value", "hard_value", "custom_value", "default_value"):
            self.assertRegex(block, level + r"\s*=\s*3\b")

        # Initialisation par defaut de la variable globale a 3
        self.assertIn("OPEX_DIFFICULTY <- 3;", self.difficulty)

    def test_read_is_unique(self):
        """3. Lecture unique dans settings.nut et compatibilite OpenTTD <= 13.4."""
        occurrences = []
        for file_name, text in self.sources.items():
            count = text.count('GetSetting("opex_difficulty")')
            if count > 0:
                occurrences.append((file_name, count))

        self.assertEqual(len(occurrences), 1, f"Lectures multiples: {occurrences}")
        self.assertEqual(occurrences[0], ("settings.nut", 1))

        # Verification de la fonction OpexResolveDifficulty
        self.assertIn("function OpexResolveDifficulty()", self.settings)
        body = _extract_function_body(self.settings, "OpexResolveDifficulty")
        self.assertIn('AIGameSettings.IsValid("script.settings_profile")', body)
        self.assertIn('AIGameSettings.GetValue("script.settings_profile")', body)
        self.assertIn('AIController.GetSetting("opex_difficulty")', body)
        self.assertLess(body.index("script.settings_profile"),
                        body.index("opex_difficulty"),
                        "Le profil 13.4 doit etre tente en priorite avant opex_difficulty")

        # Affectation unique de la globale
        self.assertEqual(self.settings.count("OPEX_DIFFICULTY = OpexResolveDifficulty();"), 1)

    def test_no_opex_difficulty_outside_settings_and_difficulty(self):
        """4. Aucun OPEX_DIFFICULTY n'apparait hors settings.nut et difficulty.nut."""
        allowed_files = {"settings.nut", "difficulty.nut"}
        violations = {}
        for file_name, text in self.sources.items():
            if file_name in allowed_files:
                continue
            if "OPEX_DIFFICULTY" in text:
                matches = [line.strip() for line in text.splitlines() if "OPEX_DIFFICULTY" in line]
                violations[file_name] = matches

        self.assertEqual(violations, {},
                         f"Symboles OPEX_DIFFICULTY detectes hors settings.nut et difficulty.nut: {violations}")

    def test_v250_cut_below_level_three(self):
        """5. La V250 est coupee sous le niveau 3."""
        # Garde dans settings.nut au chargement des parametres
        gate = 'if (!OpexLevelAllows("v250_rights")) rights = 0;'
        self.assertIn(gate, self.settings)
        self.assertLess(self.settings.index("OPEX_DIFFICULTY = OpexResolveDifficulty();"),
                        self.settings.index(gate))
        self.assertLess(self.settings.index(gate), self.settings.index("V250_RIGHTS = rights;"))

        # Table des capacites dans difficulty.nut
        self.assertIn('v250_rights = 3', self.difficulty)
        self.assertIn('anticompetitive = 3', self.difficulty)

        # Garde dans le dispatch de la tache V250
        dispatch_body = _extract_function_body(self.sources["task_v250.nut"], "OpexAI::_dispatchV250Rights")
        self.assertIn('if (!OpexLevelAllows("v250_rights")) return false;', dispatch_body)

    def test_level_three_has_no_restriction(self):
        """6. Le niveau 3 (personnalise) n'a aucun bridage (profil de reference)."""
        body = _extract_function_body(self.difficulty, "OpexLevelAllows")
        self.assertTrue(body, "Fonction OpexLevelAllows introuvable dans difficulty.nut")
        self.assertIn("if (OPEX_DIFFICULTY >= 3) return true;", body)

    def test_loading_order_requires_difficulty(self):
        """7. difficulty.nut est inclus des l'amorcage dans main.nut."""
        self.assertIn('require("difficulty.nut");', self.main)
        self.assertLess(self.main.index('require("globals_pre.nut");'),
                        self.main.index('require("difficulty.nut");'))


if __name__ == "__main__":
    unittest.main()
