"""V249 : contrats statiques des statues de ville.

Reglage entier v249_statue (0..2, defaut 0), lu une fois ; riche sans montant fixe.
Mode 0 = desactive. Mode 1 = profit historique de ligne, reserve de caisse + capital max.
Mode 2 = V249a (gain marginal capturable) + V249b (horizon 5 ans > cout mesure) + V249c (cout d'opportunite).
A 0 la tache ne touche aucune API de jeu. Un passage pose au plus une statue. Le journal est garde
par DECISION_LOG avant le formatage des champs. Aucun etat n'est sauvegarde.
"""
from pathlib import Path
import re
import unittest

from estim_unifie_legacy import estim_off


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"
ROOT = Path(__file__).resolve().parents[1]


def _body(source, signature):
    match = re.search(re.escape(signature) + r"\n\{(.*?)\n\}", source, re.S)
    return match.group(1) if match else ""


class TestV249Statues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.task = cls.sources["task_v249.nut"]
        cls.dispatch = _body(cls.task, "function OpexAI::_dispatchV249Statue(task, year)")
        cls.dispatch_m2 = _body(cls.task, "function OpexV249DispatchMode2(ai, ym, year)")
        cls.measure = _body(cls.task, "function OpexV249MeasureStatueCost(townId)")
        # Les contrats V249 historiques s'evaluent sur le code OFF exact de
        # ESTIM-1. Les branches bit 4 et bit 2 ont leurs propres assertions.
        cls.off_task = estim_off("task_v249.nut", cls.task)
        cls.off_dispatch = _body(cls.off_task, "function OpexAI::_dispatchV249Statue(task, year)")
        cls.off_dispatch_m2 = _body(cls.off_task, "function OpexV249DispatchMode2(ai, ym, year)")

    def test_setting_declared_default_two(self):
        block = re.search(
            r'name = "v249_statue",(.*?)\}\);', self.sources["info.nut"], re.S)
        self.assertIsNotNone(block)
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 2", body)
        self.assertIn("flags = 0", body)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(body, level + r" = 2\b")
        self.assertIn("V249_STATUE <- 2;", self.sources["globals_pre.nut"])
        self.assertIn("V249_CASH_STOP <- true;", self.sources["globals_pre.nut"])
        joined = "".join(self.sources.values())
        self.assertNotIn("v249_statue_cash", joined)
        self.assertNotIn("V249_STATUE_CASH", joined)

    def test_setting_read_once(self):
        reads = [(name, text.count('GetSetting("v249_statue")'))
                 for name, text in self.sources.items()]
        self.assertEqual(sum(count for _, count in reads), 1)
        self.assertIn('local v249Val = AIController.GetSetting("v249_statue");',
                      self.sources["settings.nut"])
        self.assertIn('V249_STATUE = v249Val;', self.sources["settings.nut"])

    def test_zero_cost_guard(self):
        self.assertTrue(self.dispatch)
        guard = "if (!V249_STATUE) return false;"
        self.assertIn(guard, self.dispatch)
        guard_at = self.dispatch.index(guard)
        for api in ("AIDate", "AICompany", "AITown", "AIStation", "AIVehicle",
                    "AIAccounting", "AITestMode", "OpexDecide", "V249_CASH_STOP"):
            found = self.dispatch.find(api)
            if found >= 0:
                self.assertGreater(found, guard_at, api)
        start = self.sources["main.nut"]
        appended = 'this._taskQueue.append({ name = "v249_statue", dueCycle = 0, enabled = V249_STATUE });'
        self.assertIn(appended, start)
        self.assertLess(start.index("OpexV147ExtendQueue(this);"), start.index(appended))
        hook = 'if (V249_STATUE && c75StopReason == "cash") ::V249_CASH_STOP = true;'
        self.assertEqual(self.sources["task_projects.nut"].count(hook), 1)

    def test_rich_without_fixed_amount(self):
        loan = self.dispatch.index('reason=loan')
        stop = self.dispatch.index('reason=cash_stop')
        cost = self.dispatch.index('OpexV249MeasureStatueCost(bestTown)')
        self.assertLess(loan, cost)
        self.assertLess(stop, cost)
        self.assertLess(self.dispatch.index("::V249_CASH_STOP = false;"), stop)
        self.assertIn("local threshold = OpexV249MaxListedCapital(this._projects);",
                      self.dispatch)
        self.assertIn("cash - cost < threshold", self.dispatch)
        self.assertNotRegex(self.task, r"\b\d{4,}\b")
        # M5 remplace sous bit 2 le seuil d'opportunite historique.
        self.assertIn(
            "local threshold = OpexV249MaxListedCapital(this._projects);",
            self.off_dispatch)
        compact = " ".join(self.dispatch.split())
        self.assertIn("if ((ESTIM_UNIFIE & 2) != 0)", compact)
        self.assertIn(
            'threshold = 0;', compact)

    def test_at_most_one_statue_per_pass(self):
        self.assertEqual(self.dispatch.count("AITown.PerformTownAction"), 1)
        call = self.dispatch.index("AITown.PerformTownAction")
        self.assertNotIn("foreach", self.dispatch[call:])
        self.assertNotIn("while", self.dispatch[call:])
        self.assertLess(self.dispatch.rfind("return true;"), len(self.dispatch))
        self.assertIn("local built = AITown.PerformTownAction", self.dispatch)
        self.assertIn("if (!built)", self.dispatch)
        self.assertEqual(self.measure.count("AITown.PerformTownAction"), 1)
        self.assertLess(self.measure.index("local test = AITestMode();"),
                        self.measure.index("AITown.PerformTownAction"))
        self.assertIn("if (this._v249StatueMonth == ym) return false;", self.dispatch)
        self.assertIn('this._taskQueue.append({ name = "v249_statue"', self.sources["main.nut"])
        self.assertIn('task.name == "v249_statue"', self.sources["scheduler.nut"])

    def test_journal_guarded_and_aggregated(self):
        for line in self.off_task.splitlines():
            if "OpexDecide(" in line:
                self.assertIn("DECISION_LOG", line, line)
        # ESTIM-1 publie un log sur plusieurs lignes : son helper verifie
        # DECISION_LOG avant l'appel, y compris lorsque le bit 4 est actif.
        helper = _body(self.task, "function OpexEstimVLog(kind, id, project)")
        self.assertIn("if (!DECISION_LOG || project == null) return;", helper)
        self.assertIn('OpexDecide("ESTIM_VPROJECT",', helper)
        self.assertLess(helper.index("if (!DECISION_LOG || project == null) return;"),
                        helper.index('OpexDecide("ESTIM_VPROJECT",'))
        self.assertIn('OpexEstimVLog("V249", bestTown, project);', self.dispatch_m2)
        self.assertIn(
            'OpexDecide("V249_STATUE", "town=" + bestTown + " cost=" + cost + " cash=" + cash'
            ' + " threshold=" + threshold + " lines=" + bestLines + " profit=" + bestProfit)',
            self.dispatch)
        self.assertIn('OpexDecide("V249_SKIP", "reason=cash_stop")', self.dispatch)
        self.assertIn(
            '"reason=no_town statue=" + nStatue + " unavailable=" + nUnavail',
            self.dispatch)
        loop = self.dispatch[self.dispatch.index("foreach (townId, info in byTown)"):
                             self.dispatch.index("if (!found)")]
        self.assertNotIn("OpexDecide", loop)

    def test_no_saved_state(self):
        persist = self.sources["persist.nut"]
        self.assertNotIn("v249", persist.lower())
        self.assertNotIn("_v249StatueMonth", persist)
        self.assertNotIn("V249_CASH_STOP", persist)
        self.assertIn("_v249StatueMonth = -1;", self.sources["main.nut"])

    def test_mode2_dispatch_branch(self):
        self.assertIn("if (V249_STATUE == 2) {", self.off_dispatch)
        self.assertIn("if (V249_STATUE == 2 || (ESTIM_UNIFIE & 4) != 0) {", self.dispatch)
        self.assertIn("return OpexV249DispatchMode2(this, ym, year);", self.dispatch)
        self.assertTrue(self.dispatch_m2)

    def test_mode2_v249a_capturable_and_loading_stations(self):
        # Freight loads only at station A, never receiving station B
        self.assertIn('local isFreight = (("kind" in line) && line.kind == "freight");', self.dispatch_m2)
        self.assertIn('loadingEnds.append("A");', self.dispatch_m2)
        self.assertIn('loadingEnds.append("B");', self.dispatch_m2)

        # Rating target bonus +26 clamped to 255
        self.assertIn("curByte = OpexC121RatingPercentToByteMid(ratingPct);", self.dispatch_m2)
        self.assertIn("targetByte = curByte + 26;", self.dispatch_m2)
        self.assertIn("if (targetByte > 255) targetByte = 255;", self.dispatch_m2)

        # Production per cargo type: town for PASS/MAIL, industry for freight
        self.assertIn("AITown.GetLastMonthProduction(townId, cg)", self.dispatch_m2)
        self.assertIn("AIIndustry.GetLastMonthProduction(ind, cg)", self.dispatch_m2)

        # Town anti-double counting: capped at maxTownExtra
        self.assertIn("maxTownExtra = (annualProd * 26) / 256;", self.dispatch_m2)
        self.assertIn("cargoExtraTotal < maxTownExtra ? cargoExtraTotal : maxTownExtra", self.dispatch_m2)

    def test_mode2_v249b_saturation_and_payback(self):
        # Saturated check
        self.assertIn("waiting > totalVehCap * 2", self.task)
        self.assertIn("annualCapacity - currentCarried", self.task)

        # Horizon constant (5 years)
        self.assertIn("const V249_HORIZON_YEARS = 5;", self.task)

        # Payback condition
        self.assertIn("if (bestGain * V249_HORIZON_YEARS <= cost)", self.off_dispatch_m2)
        self.assertIn(
            "if ((ESTIM_UNIFIE & 4) == 0 && bestGain * V249_HORIZON_YEARS <= cost)",
            self.dispatch_m2)
        self.assertIn('OpexEstimVProject("mixed", townGain, 0, 0, statueCost,',
                      self.dispatch_m2)
        self.assertIn("statueProject.deltaP <= 0 || statueProject.deltaC <= 0",
                      self.dispatch_m2)
        self.assertIn('reason=payback', self.dispatch_m2)

    def test_mode2_v249c_treasury_and_v252(self):
        # Mode 2 historique : seulement le cout d'opportunite.
        # Lot 2 M5 : capital financier commun, sous son bit.
        self.assertNotIn("OpexCashReserve", self.off_dispatch_m2)
        self.assertIn("threshold = bestProjCap + v252Cost;", self.off_dispatch_m2)
        compact = " ".join(self.dispatch_m2.split())
        self.assertIn("if ((ESTIM_UNIFIE & 2) != 0)", compact)
        self.assertIn(
            'threshold = 0;', compact)

        # Preserves best admissible project and pending V252 fleet renewal
        self.assertIn("OpexV249BestAdmissibleCapital", self.dispatch_m2)
        self.assertIn("OpexV249GetPendingV252Cost", self.dispatch_m2)
        self.assertIn("threshold = bestProjCap + v252Cost;", self.dispatch_m2)
        self.assertIn("cash - cost < threshold", self.dispatch_m2)

        # Best admissible capital helper checks vehicle room and air live plan
        best_body = _body(self.task, "function OpexV249BestAdmissibleCapital(projects, lines, currentCash)")
        self.assertIn("OpexModeVehicleRoom", best_body)
        self.assertIn("OpexAirBatchPlanStillLive", best_body)
        self.assertIn("cap <= currentCash", best_body)

        # Pending V252 helper checks profitable air lines and candidate engine
        v252_body = _body(self.task, "function OpexV249GetPendingV252Cost(ai)")
        self.assertIn("OpexAirBestEngineForLine", v252_body)
        self.assertIn("AIEngine.GetPrice", v252_body)

    def test_mode2_decision_log_format(self):
        self.assertIn(
            'OpexDecide("V249_STATUE", "town=" + bestTown + " station=" + bestStation + " cargo=" + bestCargoLabel'
            ' + " rating=" + bestRating + " prod=" + bestProd + " gain=" + bestGain + " cost=" + cost'
            ' + " cash=" + cash + " threshold=" + threshold + " horizon=" + V249_HORIZON_YEARS)',
            self.dispatch_m2)
        self.assertIn('reason=payback', self.dispatch_m2)
        self.assertIn('reason=cost', self.dispatch_m2)
        self.assertIn('reason=no_town', self.dispatch_m2)
        self.assertIn('reason=failed', self.dispatch_m2)

    def test_all_apis_in_noai_tsv(self):
        tsv_path = ROOT / "docs" / "noai_api_15.3.tsv"
        with open(tsv_path, encoding="utf-8") as f:
            valid_api = set(line.strip().split("\t")[-1] for line in f if line.strip())

        # Extract all AI API calls and constants from task_v249.nut
        calls = set(re.findall(r"\b(AI[A-Za-z0-9_]+)\b", self.task))
        for item in calls:
            # item could be class name or constant/method
            parts = item.split(".")
            for part in parts:
                with self.subTest(api=part):
                    self.assertIn(part, valid_api)


class V249CarriedUnits(unittest.TestCase):
    def test_pred_carried_is_annualised(self):
        # predCarried est mensuel : le revenu par unite et la capacite libre sont annuels.
        import pathlib
        code = pathlib.Path(__file__).resolve().parents[1].joinpath("ai", "OpexAI", "task_v249.nut").read_text()
        self.assertIn("line.predCarried * 12 : 0", code)
        self.assertNotIn("/ line.predCarried;", code)


class V249NoRootTable(unittest.TestCase):
    def test_no_getroottable(self):
        # getroottable() n'existe pas dans le Squirrel d'OpenTTD (erreur au smoke du 20/10).
        import pathlib
        for path in pathlib.Path(__file__).resolve().parents[1].joinpath("ai", "OpexAI").glob("*.nut"):
            self.assertNotIn("getroottable", path.read_text(encoding="utf-8", errors="replace"), path.name)


if __name__ == "__main__":
    unittest.main()
