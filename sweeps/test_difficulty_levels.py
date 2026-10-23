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

    def test_default_is_two(self):
        """2. Le defaut est 2 (difficile : sans geste anticoncurrentiel)."""
        block = _extract_setting_block(self.info, "opex_difficulty")
        for level in ("easy_value", "medium_value", "hard_value", "custom_value", "default_value"):
            self.assertRegex(block, level + r"\s*=\s*2\b")

        # Initialisation par defaut de la variable globale a 2
        self.assertIn("OPEX_DIFFICULTY <- 2;", self.difficulty)

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

    def test_difficulty_table_syntax_no_json(self):
        """8. Syntaxe Squirrel 2 sans JSON dans difficulty.nut (cle = valeur)."""
        # Aucune syntaxe JSON "cle": ou 'cle':
        self.assertNotRegex(self.difficulty, r'"[a-zA-Z0-9_]+"\s*:',
                            "Syntaxe JSON interdite dans difficulty.nut")
        self.assertNotRegex(self.difficulty, r"'[a-zA-Z0-9_]+'\s*:",
                            "Syntaxe JSON interdite dans difficulty.nut")

        # Entrees requises dans OPEX_DIFFICULTY_MIN_LEVEL
        expected_entries = [
            ("v250_rights", 3),
            ("anticompetitive", 3),
            ("preempt_last_airport_slot", 2),
            ("compete_primary_industry", 2),
            ("airport_rival_town", 1),
            ("encroach_rival_catchment", 1),
        ]
        for key, level in expected_entries:
            pattern = rf'{key}\s*=\s*{level}\b'
            self.assertRegex(self.difficulty, pattern,
                             f"Entree {key} = {level} manquante dans OPEX_DIFFICULTY_MIN_LEVEL")

    def test_guards_presence_and_call_sites(self):
        """9. Presence des fonctions de gardes et de leurs sites d'appel."""
        # Helpers Levier A dans air_towns.nut
        self.assertIn("function OpexTownPopulationTopQuartileThreshold", self.sources["air_towns.nut"])
        self.assertIn("function OpexTownRivalAirports", self.sources["air_towns.nut"])
        self.assertIn("function OpexTownAirportAllowedByLevel", self.sources["air_towns.nut"])

        # Sites d'appel Levier A
        self.assertIn("OpexTownAirportAllowedByLevel(towns[i]", self.sources["air_planning.nut"])
        self.assertNotIn("air_c83_repair.nut", self.sources)  # retired C83 repair path
        self.assertIn("OpexTownAirportAllowedByLevel(town)", self.sources["air_sites.nut"])

        # Helpers Levier B dans spatial.nut
        self.assertIn("function OpexIndustryPrimaryRivalServed", self.sources["spatial.nut"])
        self.assertIn("function OpexStationEncroachesRival", self.sources["spatial.nut"])

        # Sites d'appel Levier B (Niveau 1 : industrie primaire)
        self.assertIn("OpexIndustryPrimaryRivalServed(source.id, source.tile)", self.sources["candidates.nut"])
        self.assertIn("OpexIndustryPrimaryRivalServed(sub.srcId, srcTile)", self.sources["candidates.nut"])
        self.assertIn("OpexIndustryPrimaryRivalServed(indId, center, coverage)", self.sources["builder_rail.nut"])
        self.assertIn("OpexIndustryPrimaryRivalServed(indId, center, coverage)", self.sources["builder_road.nut"])

        # Sites d'appel Levier B (Niveau 0 : chevauchement de captage)
        self.assertIn("OpexStationEncroachesRival(minX, minY, maxX, maxY, coverage)", self.sources["builder_rail.nut"])
        self.assertIn("OpexStationEncroachesRival(tx, ty, tx, ty, coverage)", self.sources["builder_road.nut"])

    def test_level_check_precedes_tile_scans(self):
        """10. Niveau 3 et 2 : zero opcode, le test de niveau vient AVANT tout scan de tuiles."""
        # Dans OpexTownAirportAllowedByLevel : test OpexLevelAllows avant scan ou comptage rival
        airport_body = _extract_function_body(self.sources["air_towns.nut"], "OpexTownAirportAllowedByLevel")
        self.assertTrue(airport_body)
        self.assertIn('OpexLevelAllows("airport_rival_town")', airport_body)
        self.assertIn('OpexLevelAllows("preempt_last_airport_slot")', airport_body)
        self.assertLess(airport_body.index('OpexLevelAllows("airport_rival_town")'),
                        airport_body.index("OpexTownRivalAirports"),
                        "Le test de niveau doit preceder le calcul des aéroports rivaux")

        # Dans OpexIndustryPrimaryRivalServed : test OpexLevelAllows avant AITileList
        primary_body = _extract_function_body(self.sources["spatial.nut"], "OpexIndustryPrimaryRivalServed")
        self.assertTrue(primary_body)
        self.assertIn('OpexLevelAllows("compete_primary_industry")', primary_body)
        self.assertLess(primary_body.index('OpexLevelAllows("compete_primary_industry")'),
                        primary_body.index("AITileList_IndustryProducing("),
                        "Le test compete_primary_industry doit preceder AITileList_IndustryProducing")

        # Dans OpexStationEncroachesRival : test OpexLevelAllows avant AITileList
        encroach_body = _extract_function_body(self.sources["spatial.nut"], "OpexStationEncroachesRival")
        self.assertTrue(encroach_body)
        self.assertIn('OpexLevelAllows("encroach_rival_catchment")', encroach_body)
        self.assertLess(encroach_body.index('OpexLevelAllows("encroach_rival_catchment")'),
                        encroach_body.index("AITileList()"),
                        "Le test encroach_rival_catchment doit preceder AITileList")

        # Dans OpexStationPlans : le test de niveau vient avant OpexStationEncroachesRival et avant BuildRailStation
        rail_body = _extract_function_body(self.sources["builder_rail.nut"], "OpexStationPlans")
        self.assertTrue(rail_body)
        self.assertIn('!OpexLevelAllows("encroach_rival_catchment")', rail_body)
        self.assertLess(rail_body.index('!OpexLevelAllows("encroach_rival_catchment")'),
                        rail_body.index("AIRail.BuildRailStation"),
                        "La garde de niveau doit preceder le test de construction AIRail.BuildRailStation")

    def test_decision_log_on_level_skip(self):
        """11. Journalisation DECISION_LOG d'un OpexDecide LEVEL_SKIP a chaque refus."""
        self.assertIn('OpexDecide("LEVEL_SKIP", "feature=airport_rival_town', self.sources["air_towns.nut"])
        self.assertIn('OpexDecide("LEVEL_SKIP", "feature=preempt_last_airport_slot', self.sources["air_towns.nut"])
        self.assertIn('OpexDecide("LEVEL_SKIP", "feature=compete_primary_industry', self.sources["spatial.nut"])
        self.assertIn('OpexDecide("LEVEL_SKIP", "feature=encroach_rival_catchment', self.sources["spatial.nut"])


if __name__ == "__main__":
    unittest.main()


class TestLevelLimitsGlobal(unittest.TestCase):
    """18/10 relecture : les niveaux 2-3 ne paient qu'une lecture de globale aux sites d'appel."""

    def test_call_sites_guarded(self):
        import re as _re
        ai = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
        for p in ai.glob("*.nut"):
            text = p.read_text(encoding="utf-8")
            for line in text.splitlines():
                for fn in ("OpexTownAirportAllowedByLevel(", "OpexIndustryPrimaryRivalServed("):
                    if fn in line and "function " not in line and "indId >= 0" not in line:
                        self.assertIn("OPEX_LEVEL_LIMITS", line, p.name + ": " + line)
        settings = (ai / "settings.nut").read_text(encoding="utf-8")
        self.assertLess(settings.index("OPEX_DIFFICULTY = OpexResolveDifficulty();"),
                        settings.index("OPEX_LEVEL_LIMITS = "))

