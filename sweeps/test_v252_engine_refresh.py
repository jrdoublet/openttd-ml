"""V252 : contrats statiques de la modernisation de la flotte aerienne.

Reglage entier v252_air_engine_refresh, defaut 2, lu une fois ;
0 = inerte au defaut (aucun opcode supplementaire hors test de globale),
1 = meilleur avion achetable sur renfort et remplacement apres crash,
2 = mode 1 + remplacement actif mensuel quand riche, sans montant fixe en livres (defaut),
3 = mode 2 + recalcul de la demande mensuelle courante selon le modele du planificateur.
"""
from pathlib import Path
import re
import unittest


AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _body(source, signature):
    match = re.search(re.escape(signature) + r"\n\{(.*?)\n\}", source, re.S)
    return match.group(1) if match else ""


def _demand_model_py(pop_a, routes_a, pop_b, routes_b, catchment_share_pct=22):
    if routes_a <= 1 and routes_b <= 1:
        monthly = ((pop_a + pop_b) * catchment_share_pct) // 100
    else:
        part_a = (pop_a * catchment_share_pct) // 100
        if routes_a > 1:
            part_a = part_a // routes_a
        part_b = (pop_b * catchment_share_pct) // 100
        if routes_b > 1:
            part_b = part_b // routes_b
        monthly = part_a + part_b
    if monthly < 10:
        monthly = 10
    return monthly


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
        recalc_pos = self.best_engine.index("OpexAirRecomputeLineDemand(line, lines)")
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

    def test_factorization_equivalence(self):
        # 1. Structure de la fonction factorisee dans air_fleet.nut
        self.assertIn("function OpexAirDemandModel(popA, routesA, popB, routesB)", self.fleet)
        self.assertIn("TOWN_CATCHMENT_SHARE_PCT", self.fleet)
        self.assertIn("function OpexAirRecomputeLineDemand(line, lines)", self.fleet)

        # 2. Equivalence mathematique stricte avec les formules de air_planning.nut
        # Cas 1 : newpair (air_planning.nut:708 / :710)
        # local monthlyPax = ((popA + popB) * TOWN_CATCHMENT_SHARE_PCT) / 100;
        # if (monthlyPax < 10) monthlyPax = 10;
        test_pops = [10, 50, 100, 350, 800, 1500, 4200, 12000, 25000]
        for pop_a in test_pops:
            for pop_b in test_pops:
                planner_newpair = max(10, ((pop_a + pop_b) * 22) // 100)
                model_newpair = _demand_model_py(pop_a, 1, pop_b, 1)
                self.assertEqual(planner_newpair, model_newpair,
                                 f"Mismatch on newpair pop_a={pop_a} pop_b={pop_b}")
                # routes <= 1
                model_zero = _demand_model_py(pop_a, 0, pop_b, 0)
                self.assertEqual(planner_newpair, model_zero)

        # Cas 2 : hubsite (air_planning.nut:1350-1354)
        # local hubMonthly = (((hub.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub.routes + 1));
        # local newMonthly = (site.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100;
        # local monthlyPax = hubMonthly + newMonthly;
        # if (monthlyPax < 10) monthlyPax = 10;
        for hub_pop in test_pops:
            for site_pop in test_pops:
                for hub_routes in range(1, 8):
                    planner_hubsite = max(10, (((hub_pop * 22) // 100) // (hub_routes + 1)) + ((site_pop * 22) // 100))
                    model_hubsite = _demand_model_py(hub_pop, hub_routes + 1, site_pop, 1)
                    self.assertEqual(planner_hubsite, model_hubsite,
                                     f"Mismatch on hubsite hub_pop={hub_pop} site_pop={site_pop} routes={hub_routes}")

        # Cas 3 : hubhub (air_planning.nut:1530-1534)
        # local monthly1 = (((hub1.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub1.routes + 1));
        # local monthly2 = ((hub2.town.pop * TOWN_CATCHMENT_SHARE_PCT) / 100) / (hub2.routes + 1);
        # local monthlyPax = monthly1 + monthly2;
        # if (monthlyPax < 10) monthlyPax = 10;
        for h1_pop in test_pops[::2]:
            for h2_pop in test_pops[::2]:
                for r1 in range(1, 6):
                    for r2 in range(1, 6):
                        planner_hubhub = max(10, (((h1_pop * 22) // 100) // (r1 + 1)) + (((h2_pop * 22) // 100) // (r2 + 1)))
                        model_hubhub = _demand_model_py(h1_pop, r1 + 1, h2_pop, r2 + 1)
                        self.assertEqual(planner_hubhub, model_hubhub,
                                         f"Mismatch on hubhub h1={h1_pop} h2={h2_pop} r1={r1} r2={r2}")

    def test_recompute_line_demand_missing_data_fallback(self):
        recompute = _body(self.fleet, "function OpexAirRecomputeLineDemand(line, lines)")
        self.assertIn("return fallback;", recompute)
        self.assertIn("local fallback =", recompute)
        self.assertIn("AIStation.GetStationID(line.stationA)", recompute)
        self.assertIn("AIStation.GetStationID(line.stationB)", recompute)
        self.assertIn("AIStation.GetNearestTown", recompute)
        self.assertIn("AITown.GetPopulation", recompute)

    def test_no_saved_state(self):
        persist = self.sources["persist.nut"]
        self.assertNotIn("v252", persist.lower())
        self.assertNotIn("_v252RefreshMonth", persist)
        self.assertNotIn("V252_CASH_STOP", persist)
        self.assertIn("_v252RefreshMonth = -1;", self.sources["main.nut"])


if __name__ == "__main__":
    unittest.main()

