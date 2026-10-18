"""V252 : contrats statiques de la modernisation de la flotte aerienne.

Reglage entier v252_air_engine_refresh, defaut 2, lu une fois ;
0 = inerte au defaut (aucun opcode supplementaire hors test de globale),
1 = meilleur avion achetable sur renfort et remplacement apres crash,
2 = mode 1 + remplacement actif mensuel quand riche, sans montant fixe en livres (defaut),
3 = mode 2 + economie C121 de flotte reelle, demande courante.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _body(source, signature):
    match = re.search(re.escape(signature) + r"\n\{(.*?)\n\}", source, re.S)
    return match.group(1) if match else ""


class TestV252EngineRefresh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.task = cls.sources["task_v252.nut"]
        cls.dispatch = _body(cls.task, "function OpexAI::_dispatchV252AirEngineRefresh(task, year)")
        cls.fleet = cls.sources["air_fleet.nut"]
        cls.best_engine = _body(cls.fleet, "function OpexAirBestEngineForLine(line, catalog, lines = null)")
        cls.add_plane = _body(cls.fleet, "function OpexAirAddPlane(line, catalog = null, lines = null)")
        cls.refleet = _body(cls.fleet, "function OpexAirRefleetCrashedPlane(line, catalog = null, lines = null)")

    def test_setting_declared_default_two(self):
        block = re.search(
            r'name = "v252_air_engine_refresh",(.*?)\}\);', self.sources["info.nut"], re.S)
        self.assertIsNotNone(block)
        body = block.group(1)
        self.assertIn("min_value = 0", body)
        self.assertIn("max_value = 3", body)
        self.assertIn("step_size = 1", body)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(body, level + r" = 2\b")  # defaut 2 depuis le 18/10 (portes A et B)
        self.assertIn("V252_AIR_ENGINE_REFRESH <- 2;", self.sources["globals_pre.nut"])
        self.assertIn("V252_CASH_STOP <- true;", self.sources["globals_pre.nut"])

    def test_setting_read_once(self):
        reads = [(name, text.count('GetSetting("v252_air_engine_refresh")'))
                 for name, text in self.sources.items()]
        self.assertEqual(sum(count for _, count in reads), 1)
        self.assertIn('AIController.GetSetting("v252_air_engine_refresh")',
                      self.sources["settings.nut"])

    def test_zero_cost_guards(self):
        self.assertTrue(self.dispatch)
        guard = "if (V252_AIR_ENGINE_REFRESH < 2) return false;"
        self.assertIn(guard, self.dispatch)
        guard_at = self.dispatch.index(guard)
        for api in ("AIDate", "AICompany", "AITown", "AIStation", "AIVehicle",
                    "AIAccounting", "AITestMode", "OpexDecide", "V252_CASH_STOP"):
            found = self.dispatch.find(api)
            if found >= 0:
                self.assertGreater(found, guard_at, api)

        # Main queue enqueue guard (modes 2 et 3)
        start = self.sources["main.nut"]
        appended = 'this._taskQueue.append({ name = "v252_air_engine_refresh", dueCycle = 0, enabled = V252_AIR_ENGINE_REFRESH >= 2 });'
        self.assertIn(appended, start)

        # Scheduler dispatch guard
        sched = self.sources["scheduler.nut"]
        self.assertIn('if (task.name == "v252_air_engine_refresh")', sched)

        # air_fleet.nut guards for Mode 1
        self.assertIn("V252_AIR_ENGINE_REFRESH >= 1", self.add_plane)
        self.assertIn("V252_AIR_ENGINE_REFRESH >= 1", self.refleet)

        # Cash stop hook covers modes >= 2
        hook_v249 = 'if (V249_STATUE && c75StopReason == "cash") ::V249_CASH_STOP = true;'
        hook_v252 = 'if (V252_AIR_ENGINE_REFRESH >= 2 && c75StopReason == "cash") ::V252_CASH_STOP = true;'
        self.assertEqual(self.sources["task_projects.nut"].count(hook_v249), 1)
        self.assertEqual(self.sources["task_projects.nut"].count(hook_v252), 1)

    def test_mode_3_guards(self):
        # Recalcul de la demande active seulement au mode 3
        self.assertTrue(self.best_engine)
        self.assertIn("if (V252_AIR_ENGINE_REFRESH >= 3)", self.best_engine)
        guard_pos = self.best_engine.index("if (V252_AIR_ENGINE_REFRESH >= 3)")
        recalc_pos = self.best_engine.index("OpexAirRefreshC121Plan(line, catalog, lines, airportType)")
        self.assertGreater(recalc_pos, guard_pos)

        # settings.nut borne max_value a 3
        self.assertIn("v252Refresh <= 3", self.sources["settings.nut"])

    def test_rich_without_fixed_amount(self):
        loan = self.dispatch.index('reason=loan')
        stop = self.dispatch.index('reason=cash_stop')
        cost = self.dispatch.index('AIEngine.GetPrice(bestNewEngine)')
        self.assertLess(loan, cost)
        self.assertLess(stop, cost)
        self.assertLess(self.dispatch.index("::V252_CASH_STOP = false;"), stop)
        self.assertIn("local threshold = OpexCashReserve() + OpexV249MaxListedCapital(this._projects);",
                      self.dispatch)
        self.assertIn("cash - price < threshold", self.dispatch)
        # Aucun nombre a 4 chiffres ou plus dans task_v252.nut
        self.assertNotRegex(self.task, r"\b\d{4,}\b")

    def test_at_most_one_replacement_per_pass(self):
        self.assertEqual(self.dispatch.count("AIVehicle.BuildVehicleWithRefit"), 1)
        self.assertIn("AIVehicle.SendVehicleToDepot", self.dispatch)
        self.assertIn("this._vehiclesToRetire", self.dispatch)
        self.assertIn("if (this._v252RefreshMonth == ym) return false;", self.dispatch)

    def test_journal_guarded(self):
        for line in self.task.splitlines():
            if "OpexDecide(" in line:
                self.assertIn("DECISION_LOG", line, line)
        self.assertIn('OpexDecide("V252_REPLACE"', self.dispatch)
        self.assertIn('OpexDecide("V252_SKIP"', self.dispatch)

        for line in self.fleet.splitlines():
            if 'OpexDecide("V252_ENGINE"' in line:
                self.assertIn("DECISION_LOG", line, line)

    def test_journal_demand_fields(self):
        # Evenements V252_ENGINE et V252_REPLACE contiennent demand_old= et demand_now=
        self.assertIn('demand_old=" + dOld + " demand_now=" + dNow', self.dispatch)
        self.assertIn('demand_old=" + dOld + " demand_now=" + dNow', self.add_plane)
        self.assertIn('demand_old=" + dOld + " demand_now=" + dNow', self.refleet)

    def test_c121_fleet_contract(self):
        plan = _body(self.fleet, "function OpexAirRefreshC121Plan(line, catalog, lines, airportType)")
        self.assertIn("if (lines == null) return null;", plan)
        self.assertIn("AIStation.GetStationID(tile)", plan)
        self.assertIn("AIStation.IsValidStation(station)", plan)
        self.assertIn("AITown.IsValidTown(town)", plan)
        self.assertIn("OpexFlightDistance(line.stationA, line.stationB)", plan)
        self.assertIn("reuseA = true, reuseB = true", plan)
        self.assertIn("price = 0, maintenance = 0", plan)
        self.assertIn("if (other != line) others.append(other)", plan)
        self.assertIn("OpexAirLiveRoutesAtAirport(tile, lines) - (count > 0 ? 1 : 0)", plan)
        self.assertIn("AIVehicle.IsValidVehicle(vehicle)", plan)
        self.assertIn("AIVehicle.GetVehicleType(vehicle) == AIVehicle.VT_AIR", plan)
        self.assertIn("if (count < 1) count = 1;", plan)
        self.assertIn("OpexC121PrepareDemandShadow(catalog, plan, others)", plan)
        self.assertIn("OpexC121PrepareEngineStatic(catalog, plan)", plan)
        self.assertIn("OpexC121EngineEconomics(catalog, refreshPlan, plane, refreshPlan.refreshPlanes)", self.best_engine)
        self.assertNotIn("rawset", plan)  # aucune mutation de la ligne sauvegardee
        self.assertNotIn("OpexC121ChooseRoutePlane", self.best_engine)  # pas de V96/memo global

    def test_mode_two_economics_unchanged(self):
        self.assertIn("local refreshPlan = null;", self.best_engine)
        self.assertIn("if (refreshPlan == null) return null;", self.best_engine)
        self.assertIn(": OpexAirEconomics(catalog, airportObj, plane, distance, monthlyPax, false, 0, 0, 0, 1)", self.best_engine)
        self.assertIn("economics.profitAnnual > bestEconomics.profitAnnual", self.best_engine)
        self.assertIn("economics.roi > bestEconomics.roi", self.best_engine)
        self.assertEqual(self.sources["info.nut"].count("AddSetting({"), 76)

    def test_replay_low_rating_cost_dominates(self):
        from analyse_v253_chooser import engines_from_code, replay
        engines = engines_from_code()
        dart = replay(engines[217], 156, 214)
        lb10 = replay(engines[223], 156, 214)
        self.assertAlmostEqual(dart['rating'], 12.745098, places=5)
        self.assertEqual(dart['days'], 77)
        self.assertEqual((dart['carried'], lb10['carried']), (27, 27))
        self.assertEqual(dart['revenue'], lb10['revenue'])
        self.assertEqual(dart['profit'] - lb10['profit'], 2052)
        # Le forfait courrier ne departage pas les deux avions de meme vitesse.
        self.assertEqual(replay(engines[217], 156, 214, mail=False)['profit']
                         - replay(engines[223], 156, 214, mail=False)['profit'], 2052)
        # Davantage de demande peut inverser le choix : pas un biais de cout seul.
        self.assertGreater(replay(engines[223], 156, 417)['profit'],
                           replay(engines[217], 156, 417)['profit'])

    def test_replay_headway_and_tariff(self):
        from analyse_v253_chooser import engines_from_code, replay
        from analyse_c119_air_income_shadow import cargo_income, PAX_PAYMENT, MAIL_PAYMENT
        # Tarifs C121_BUILD ligne 0 graine 42 : donnees journalisees, pas synthetiques.
        self.assertEqual(cargo_income(268, 41, PAX_PAYMENT), 97)
        self.assertEqual(cargo_income(268, 41, MAIL_PAYMENT), 148)
        engine = engines_from_code()[217]
        one = replay(engine, 156, 214)
        four = replay(engine, 156, 214, planes=4)
        self.assertGreater(four['rating'], one['rating'])
        self.assertGreater(four['carried'], one['carried'])
        self.assertLess(replay(engine, 156, 214, direct=True)['days'], one['days'])

    def test_no_saved_state(self):
        persist = self.sources["persist.nut"]
        self.assertNotIn("v252", persist.lower())
        self.assertNotIn("_v252RefreshMonth", persist)
        self.assertNotIn("V252_CASH_STOP", persist)
        self.assertIn("_v252RefreshMonth = -1;", self.sources["main.nut"])


if __name__ == "__main__":
    unittest.main()

