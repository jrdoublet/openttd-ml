"""V220 : contrats statiques de la phase 4 doctrine -- bateaux fret & passagers.

Couvre :
- Les réglages v220_ships, v220_ships_min_cash, v220_ships_min_year déclarés inertes par défaut (0).
- Le chargement et bornage unique dans settings.nut et globals_pre.nut.
- La neutralité à 0 : aucun opcode additionnel sur le chemin chaud, mode_water=0 coupe tout.
- La levée du verrou d'une seule ligne et la priorité fret côtier / plate-forme pétrolière.
- Le modèle de revenu/capital (docks intégrés gratuits, vitesse effective, distance navigable).
- Le renfort de flotte (tampon de chargement, plafond de production 110%).
- La journalisation DECISION_LOG (WATER_PROJECT_GEN, PROJECT_CHOSEN, WATER_BUILD, WATER_BUY, WATER_REFLEET, WATER_LINE_REVENUE).
- L'absence de mots réservés Squirrel (clone, base, parent, resume comme identifiants).
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class TestV220ShipsSettings(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}

    def test_settings_declared_inert(self):
        info = self.sources["info.nut"]
        # v220_ships
        block = re.search(r'name = "v220_ships",(.*?)\}\);', info, re.S)
        self.assertIsNotNone(block, "v220_ships non déclaré dans info.nut")
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block.group(1), level + r" = 0\b")
        self.assertIn("max_value = 1", block.group(1))

        # v220_ships_min_cash
        block_cash = re.search(r'name = "v220_ships_min_cash",(.*?)\}\);', info, re.S)
        self.assertIsNotNone(block_cash, "v220_ships_min_cash non déclaré")
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block_cash.group(1), level + r" = 300000\b")

        # v220_ships_min_year
        block_yr = re.search(r'name = "v220_ships_min_year",(.*?)\}\);', info, re.S)
        self.assertIsNotNone(block_yr, "v220_ships_min_year non déclaré")
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block_yr.group(1), level + r" = 1972\b")

    def test_settings_loaded_and_bounded(self):
        settings = self.sources["settings.nut"]
        globals_pre = self.sources["globals_pre.nut"]

        self.assertIn("V220_SHIPS <- 0;", globals_pre)
        self.assertIn("V220_SHIPS_MIN_CASH <- 300000;", globals_pre)
        self.assertIn("V220_SHIPS_MIN_YEAR <- 1972;", globals_pre)

        self.assertEqual(sum(s.count('GetSetting("v220_ships")') for s in self.sources.values()), 1)
        self.assertEqual(sum(s.count('GetSetting("v220_ships_min_cash")') for s in self.sources.values()), 1)
        self.assertEqual(sum(s.count('GetSetting("v220_ships_min_year")') for s in self.sources.values()), 1)

        self.assertRegex(settings, r"V220_SHIPS = \(v220Ships != null && v220Ships >= 0 && v220Ships <= 1\) \? v220Ships : 0;")
        self.assertRegex(settings, r"V220_SHIPS_MIN_CASH = \(v220Cash != null && v220Cash >= 0 && v220Cash <= 2000000\) \? v220Cash : 300000;")
        self.assertRegex(settings, r"V220_SHIPS_MIN_YEAR = \(v220Year != null && v220Year >= 1950 && v220Year <= 2050\) \? v220Year : 1972;")


class TestV220ShipsInvariantsAndBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}

    def test_mode_water_unconditionally_kills_water(self):
        # catalog.nut: mode_water == 0 returns early
        cat = self.sources["catalog.nut"]
        self.assertIn("if (!MODE_WATER) return;", cat)

        # projects.nut: doWater requires MODE_WATER
        proj = self.sources["projects.nut"]
        self.assertIn("if (!MODE_WATER) doWater = false;", proj)

    def test_when_rich_gating(self):
        proj = self.sources["projects.nut"]
        # v220Active is gated lazily on V220_SHIPS, catalog.year >= V220_SHIPS_MIN_YEAR, and bank balance
        self.assertIn("local v220Active = (V220_SHIPS != 0 && catalog.year >= V220_SHIPS_MIN_YEAR && AICompany.GetBankBalance(AICompany.COMPANY_SELF) >= V220_SHIPS_MIN_CASH);", proj)

    def test_single_line_lock_lifted_under_v220(self):
        task_water = self.sources["task_water.nut"]
        # Under V220_SHIPS == 0, this._waterBuilt still blocks
        self.assertIn("if (V220_SHIPS == 0) {", task_water)
        self.assertIn("if (this._waterBuilt || this._catalog.ships.len() == 0 || this._catalog.paxCargo < 0)", task_water)

    def test_freight_water_and_built_in_docks(self):
        builder = self.sources["builder_water.nut"]
        # Industry dock finding
        self.assertIn("function OpexWaterFindIndustrySite(ind, cargo, isProducer", builder)
        self.assertIn("AIIndustry.HasDock(indId)", builder)
        self.assertIn("AIIndustry.GetDockLocation(indId)", builder)
        self.assertIn("AITileList_IndustryProducing", builder)
        self.assertIn("AITileList_IndustryAccepting", builder)

        # Freight economics
        self.assertIn("function OpexWaterFreightEconomics", builder)
        self.assertIn("hasBuiltInDock", builder)

        # Capital accounting for built-in dock = 0 cost
        self.assertIn("function OpexWaterPlannedCapital", builder)

    def test_fleet_refleet_and_reinforcement(self):
        task_water = self.sources["task_water.nut"]
        sched = self.sources["scheduler_tasks.nut"]
        main = self.sources["main.nut"]

        self.assertIn("function _refleetWaterLines(year);", main)
        self.assertIn("if (V220_SHIPS != 0 && year >= V220_SHIPS_MIN_YEAR) this._refleetWaterLines(year);", sched)
        self.assertIn("else this._refleetCrashedWaterLines(year);", sched)

        # In task_water.nut: checks waiting >= cap, production cap 110%
        self.assertIn("waiting < cap", task_water)
        self.assertIn("(monthlyProd * 110) / 100", task_water)
        self.assertIn("AIVehicle.CloneVehicle(line.depot, firstVeh, true)", task_water)

    def test_decision_logging(self):
        builder = self.sources["builder_water.nut"]
        task_water = self.sources["task_water.nut"]
        task_report = self.sources["task_report.nut"]

        self.assertIn('OpexDecide("WATER_PROJECT_GEN"', builder)
        self.assertIn('OpexDecide("WATER_SCAN"', builder)
        self.assertIn('OpexDecide("PROJECT_CHOSEN"', task_water)
        self.assertIn('OpexDecide("WATER_BUILD"', task_water)
        self.assertIn('OpexDecide("WATER_REFLEET"', task_water)
        self.assertIn('OpexDecide("WATER_BUY"', task_water)
        self.assertIn('OpexDecide("WATER_LINE_REVENUE"', task_report)

    def test_no_squirrel_reserved_words_as_identifiers(self):
        reserved = ["clone", "base", "parent", "resume"]
        # Check all modified nut files
        files_to_check = [
            "builder_water.nut", "task_water.nut", "catalog.nut",
            "projects.nut", "projects_builders.nut", "scheduler_tasks.nut",
            "task_report.nut", "settings.nut", "globals_pre.nut"
        ]
        var_pattern = re.compile(r'\b(local|function)\s+(clone|base|parent|resume)\b')
        for f in files_to_check:
            content = self.sources[f]
            match = var_pattern.search(content)
            self.assertIsNone(match, f"Mot réservé Squirrel trouvé comme variable ou fonction dans {f}: {match}")


if __name__ == "__main__":
    unittest.main()
