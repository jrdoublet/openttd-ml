"""V289 : contrats statiques des travailleurs sur reliquat d'opcodes (slack workers).

Vérifie :
1. Réglage v289_slack_workers dans info.nut (4 *_value = 0, min 0, max 7, flags 0).
2. Lecture unique dans settings.nut bornée à [0..7].
3. Globale V289_SLACK_WORKERS <- 0 et constante V289_SLACK_MIN = 2500 dans globals_pre.nut.
4. Appel dans les deux boucles (main.nut et probes.nut), après V89 et C67, avant Sleep(1).
5. Inertie stricte au défaut 0 (retour immédiat sans travail ni appel API).
6. Seuil V289_SLACK_MIN vérifié AVANT tout travail et avant chaque tranche.
7. Contrôle des 3 travailleurs :
   - bit 1 : worker rail (A* de préparation sans pose, respect de _c121RailPrepHold).
   - bit 2 : cartographie (un pas de _c67TerrainSlackStep).
   - bit 4 : croissance urbaine (TOWN_ACTION_FUND_BUILDINGS en AITestMode, garde de richesse).
8. Journal mensuel V289_SLACK sous DECISION_LOG et spans PROBE_SPAN_TRACE.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _function_body(source, signature):
    match = re.search(re.escape(signature) + r"\s*\n\{(.*?)\n\}", source, re.S)
    return match.group(1) if match else ""


class TestV289SlackWorkers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.info = cls.sources["info.nut"]
        cls.settings = cls.sources["settings.nut"]
        cls.globals_pre = cls.sources["globals_pre.nut"]
        cls.main = cls.sources["main.nut"]
        cls.probes = cls.sources["probes.nut"]
        cls.persist = cls.sources["persist.nut"]
        cls.task = cls.sources.get("task_v289.nut", "")
        cls.body_slack = _function_body(cls.task, "function OpexAI::_v289SlackWorkers()")
        cls.body_rail = _function_body(cls.task, "function OpexAI::_v289StepRail()")
        cls.body_map = _function_body(cls.task, "function OpexAI::_v289StepMap()")
        cls.body_town = _function_body(cls.task, "function OpexAI::_v289StepTown()")

    def test_setting_declaration(self):
        block = re.search(r'name = "v289_slack_workers",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(block, "v289_slack_workers doit être déclaré dans info.nut")
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 7", body)
        self.assertIn("default_value = 0", body)
        self.assertIn("flags = 0", body)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(body, level + r"\s*=\s*0\b")

    def test_setting_read_once(self):
        reads = [(name, text.count('GetSetting("v289_slack_workers")'))
                 for name, text in self.sources.items()]
        self.assertEqual(sum(count for _, count in reads), 1, "v289_slack_workers doit être lu une seule fois")
        self.assertIn('local v289Slack = AIController.GetSetting("v289_slack_workers");', self.settings)
        self.assertIn("V289_SLACK_WORKERS = (v289Slack != null && v289Slack >= 0 && v289Slack <= 7) ? v289Slack : 0;", self.settings)

    def test_globals_declared(self):
        self.assertIn("V289_SLACK_WORKERS <- 0;", self.globals_pre)
        self.assertIn("const V289_SLACK_MIN = 2500;", self.globals_pre)

    def test_call_in_both_loops(self):
        # 1. main.nut loop order: throughput -> c67 -> v289 -> Sleep
        self.assertIn("this._v289SlackWorkers();", self.main)
        main_thru = self.main.index("this._advanceRailSearchThroughput();")
        main_c67 = self.main.index("this._c67SlackHook();")
        main_v289 = self.main.index("this._v289SlackWorkers();")
        main_sleep = self.main.index("AIController.Sleep(1);")
        self.assertLess(main_thru, main_c67)
        self.assertLess(main_c67, main_v289)
        self.assertLess(main_v289, main_sleep)

        # 2. probes.nut profiled loop order: throughput -> c67 -> v289 -> Sleep
        self.assertIn("this._v289SlackWorkers();", self.probes)
        prof_thru = self.probes.index("this._advanceRailSearchThroughput();")
        prof_c67 = self.probes.index("this._c67SlackHook();")
        prof_v289 = self.probes.index("this._v289SlackWorkers();")
        prof_sleep = self.probes.index("AIController.Sleep(1);")
        self.assertLess(prof_thru, prof_c67)
        self.assertLess(prof_c67, prof_v289)
        self.assertLess(prof_v289, prof_sleep)

    def test_default_zero_inert(self):
        self.assertTrue(self.body_slack)
        first_guard = "if (V289_SLACK_WORKERS == 0) return;"
        self.assertIn(first_guard, self.body_slack)
        # La garde est la première instruction de la fonction
        lines = [line.strip() for line in self.body_slack.strip().splitlines() if line.strip() and not line.strip().startswith("/*") and not line.strip().startswith("*")]
        self.assertEqual(lines[0], first_guard)

    def test_threshold_checked_before_work(self):
        guard_ops = "if (AIController.GetOpsTillSuspend() < V289_SLACK_MIN)"
        self.assertIn(guard_ops, self.body_slack)
        guard_idx = self.body_slack.index(guard_ops)
        # Aucune étape worker ne doit être exécutée avant cette vérification
        for worker_call in ("_v289StepRail", "_v289StepMap", "_v289StepTown"):
            idx = self.body_slack.find(worker_call)
            self.assertGreater(idx, guard_idx, f"{worker_call} doit être appelé après la vérification de seuil")

    def test_rail_worker_contract(self):
        self.assertTrue(self.body_rail)
        # L'annee AIR de C121 garde le creneau principal
        self.assertIn("if (!MODE_RAIL || C121_CATALOG_FIRST_YEAR_ACTIVE) { this._v289RailWhy.year1++; return false; }", self.body_rail)
        # Creneau dedie : _railSearch n'est echange que le temps de la tranche, puis restaure
        self.assertIn("this._railSearch = slot;", self.body_rail)
        self.assertEqual(self.body_rail.count("this._railSearch = savedSearch;"), 2)
        self.assertEqual(self.body_rail.count("this._activeWorker = savedWorker;"), 2)
        self.assertIn("this._continueRailSearch();", self.body_rail)
        self.assertNotIn("_advanceRailSearchSliceWithLedgers", self.body_rail)
        self.assertNotIn("_ensureSelection", self.task)
        self.assertNotIn("_v89EstimatedSliceOps = ", self.task)
        self.assertIn("this._startRailStockSearch(candidate)", self.body_rail)
        self.assertIn("this._handleRailStockSearchCompleted();", self.body_rail)
        # Ne pose JAMAIS de rail
        self.assertNotIn("OpexBuildLine", self.body_rail)
        self.assertNotIn("BuildRail", self.body_rail)

    def test_map_worker_contract(self):
        self.assertTrue(self.body_map)
        self.assertIn("this._c67TerrainSlackStep();", self.body_map)

    def test_town_worker_contract(self):
        self.assertTrue(self.body_town)
        self.assertIn("AITown.TOWN_ACTION_FUND_BUILDINGS", self.body_town)
        self.assertIn("AITestMode()", self.body_town)
        self.assertIn("AIAccounting()", self.body_town)
        # Garde de richesse : réserve + max project capital
        self.assertIn("OpexCashReserve()", self.body_town)
        self.assertIn("OpexV249MaxListedCapital(this._projects)", self.body_town)
        # Cadence 6 mois (182 jours) par ville, une tentative par mois
        self.assertIn("182", self.body_town)
        self.assertIn("if (this._v289TownMonth == stamp) return false;", self.body_town)

    def test_decision_log_and_spans(self):
        # Decision log mensuel
        self.assertIn('OpexDecide("V289_SLACK",', self.task)
        self.assertIn("month=", self.task)
        self.assertIn("calls=", self.task)
        self.assertIn("ops_rail=", self.task)
        self.assertIn("ops_map=", self.task)
        self.assertIn("ops_town=", self.task)
        self.assertIn("skipped_low=", self.task)
        # Spans sous PROBE_SPAN_TRACE
        self.assertIn('"slack.rail"', self.task)
        self.assertIn('"slack.map"', self.task)
        self.assertIn('"slack.town"', self.task)

    def test_persist_reconstruction(self):
        # Les structures transitoires sont réinitialisées au rechargement
        self.assertIn("this._v289TownFundDate = {};", self.persist)
        self.assertIn("this._v289EstOps = ", self.persist)
        self.assertIn("this._v289WorkerCursor = 0;", self.persist)


if __name__ == "__main__":
    unittest.main()
