#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sweeps/test_v268_c70_early.py — Tests de contrat et validation statique V268.

V268 — C70 « apprentissage precoce » : estimer le rendement realise des lignes a 3, 6, 12, 24 mois.
Etape 1 : shadow / observation seule, aucune decision modifiee.
"""

from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from campaign_freeze import parse_ai_settings
import analyze_v268_early

AI = ROOT / "ai" / "OpexAI"


class TestV268C70Early(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.info = cls.sources["info.nut"]
        cls.settings = cls.sources["settings.nut"]
        cls.globals = cls.sources["globals_pre.nut"]
        cls.main = cls.sources["main.nut"]
        cls.task = cls.sources.get("task_v268_early.nut", "")
        cls.probes = cls.sources.get("probes.nut", "")
        cls.persist = cls.sources.get("persist.nut", "")

    def test_setting_contract(self):
        """1. Reglage v268_c70_early (0/1, defaut 0 partout)."""
        defaults = parse_ai_settings(AI / "info.nut")
        self.assertIn("v268_c70_early", defaults)
        self.assertEqual(defaults["v268_c70_early"], 0)

        # Verification AddSetting dans info.nut
        self.assertIn('name = "v268_c70_early"', self.info)
        idx = self.info.index('name = "v268_c70_early"')
        block = self.info[idx:self.info.index("});", idx)]
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 1", block)
        for lvl in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(lvl, block)
        self.assertIn("AICONFIG_BOOLEAN", block)

        # Globale dans globals_pre.nut
        self.assertIn("V268_C70_EARLY <- false;", self.globals)
        self.assertIn("V268_VEHICLE_STATE <- {};", self.globals)
        self.assertIn("V268_LAST_SAMPLE_DATE <- -1;", self.globals)

        # Lecture dans settings.nut
        self.assertIn('V268_C70_EARLY = AIController.GetSetting("v268_c70_early") != 0;', self.settings)
        self.assertIn("V268_VEHICLE_STATE = {};", self.settings)
        self.assertIn("V268_LAST_SAMPLE_DATE = -1;", self.settings)

    def test_zero_api_call_and_zero_cost_at_default_zero(self):
        """2. A 0, aucun appel API ni etat nouveau : un seul test booleen en tete."""
        self.assertTrue(self.task, "task_v268_early.nut manquant")

        # Dans main.nut : appel garde par if (V268_C70_EARLY)
        self.assertIn("if (V268_C70_EARLY)", self.main)
        self.assertIn("OpexV268Step(this._lines, this._catalog);", self.main)

        # En tete de OpexV268Step dans task_v268_early.nut
        fn_match = re.search(r"function\s+OpexV268Step\s*\([^)]*\)\s*\{([^}]+)\}", self.task)
        self.assertIsNotNone(fn_match)
        body = fn_match.group(1).strip()
        lines = [line.strip() for line in body.splitlines() if line.strip() and not line.strip().startswith("/*")]
        self.assertEqual(lines[0], "if (!V268_C70_EARLY) return;")
        self.assertEqual(lines[1], "if (!DECISION_LOG) return;")

        # En tete de OpexV268MonthlyReport
        monthly_match = re.search(r"function\s+OpexV268MonthlyReport\s*\([^)]*\)\s*\{([^}]+)\}", self.task)
        self.assertIsNotNone(monthly_match)
        monthly_body = monthly_match.group(1).strip()
        monthly_lines = [l.strip() for l in monthly_body.splitlines() if l.strip() and not l.strip().startswith("/*")]
        self.assertEqual(monthly_lines[0], "if (!V268_C70_EARLY) return;")

    def test_static_squirrel_hygiene(self):
        """3. Controles statiques : pas de reserved words, pas de nested closure, pas de forbidden array methods."""
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", self.task, flags=re.S)

        # Delimiteurs
        self.assertEqual(code.count("{"), code.count("}"), "Accolades desequilibrees")
        self.assertEqual(code.count("("), code.count(")"), "Parentheses desequilibrees")
        self.assertEqual(code.count("["), code.count("]"), "Crochets desequilibres")

        # Mots reserves clone, base, parent
        self.assertNotRegex(code, r"\blocal\s+(clone|base|parent)\b")
        self.assertNotRegex(code, r"\bfunction\s+(clone|base|parent)\b")

        # Pas de closures imbriquees capturant des locals
        self.assertNotRegex(code, r"=\s*function\s*\(")

        # Pas de array.find, array.map, array.filter
        self.assertNotRegex(code, r"\.find\s*\(")
        self.assertNotRegex(code, r"\.map\s*\(")
        self.assertNotRegex(code, r"\.filter\s*\(")

        # Pas de AICargoMonitor
        self.assertNotIn("AICargoMonitor", code)

        # OpexDecide garde sous DECISION_LOG
        self.assertIn('OpexDecide("V268_EST"', self.task)
        for line in self.task.splitlines():
            if 'OpexDecide("V268_EST"' in line:
                # La fonction est gardee par DECISION_LOG en tete
                self.assertIn("DECISION_LOG", self.task)

    def test_c117_intact_and_not_broken(self):
        """4. La generalisation de la logique C117 ne casse pas C117 lui-meme."""
        self.assertIn("C117_AIR_LAST_DATE <- -1;", self.globals)
        self.assertIn("C117_AIR_LINE_STATE <- {};", self.globals)
        self.assertIn("C117_AIR_VEHICLE_STATE <- {};", self.globals)
        self.assertIn("OpexC117AirThroughputStep(this._lines, this._catalog);", self.main)
        self.assertIn("function OpexC117AirThroughputStep(", self.probes)
        self.assertIn("function OpexC117FlushLine(", self.probes)

    def test_formula_and_event_contract(self):
        """5. Champs journalises dans V268_EST et formule d'amortissement."""
        # Champs requis : ligne, mode, kind (pax/fret), vehicule, jours, trajets, profit_obs, p_annual, pred_amort, predicted
        expected_fields = (
            "palier=", "line=", "mode=", "kind=", "veh=", "days=",
            "trips=", "profit_obs=", "p_annual=", "pred_amort=", "predicted="
        )
        for f in expected_fields:
            self.assertIn(f, self.task)

        # Formule : 365.25 / days * profitObs - predAmort
        self.assertIn("365.25 / daysObs.tofloat() * vehicleState.profitObs - predAmort", self.task)

        # Paliers 3, 6, 12, 24
        self.assertIn("[3, 90]", self.task)
        self.assertIn("[6, 180]", self.task)
        self.assertIn("[12, 365]", self.task)
        self.assertIn("[24, 730]", self.task)

    def test_save_load_contract(self):
        """6. V268 non sauvegarde : la version de sauvegarde et persist.nut restent inchanges."""
        self.assertNotIn("V268_VEHICLE_STATE", self.persist)
        self.assertNotIn("V268_C70_EARLY", self.persist)

    def test_offline_analyzer_selftest(self):
        """7. Selftest de l'analyseur hors ligne analyze_v268_early.py."""
        self.assertTrue(analyze_v268_early.run_self_test())

    def test_offline_analyzer_jsonl_parsing(self):
        """8. L'analyseur gere aussi des lignes JSONL."""
        jsonl_lines = [
            '{"message": "OPEX 1970-04-01 V268_EST palier=3 line=1 mode=air kind=pax veh=1 days=90 trips=20 profit_obs=3000 p_annual=11000 pred_amort=1000 predicted=10000"}',
            '{"message": "OPEX 1971-01-01 V268_EST palier=12 line=1 mode=air kind=pax veh=1 days=365 trips=80 profit_obs=10000 p_annual=9000 pred_amort=1000 predicted=10000"}',
        ]
        records, results = analyze_v268_early.process_lines(jsonl_lines)
        self.assertEqual(len(records), 2)
        self.assertEqual(results["MODE_AIR"]["3m_vs_12m"]["n"], 1)
        self.assertEqual(results["MODE_AIR"]["3m_vs_12m"]["bias"], 2000.0)


if __name__ == "__main__":
    unittest.main()
