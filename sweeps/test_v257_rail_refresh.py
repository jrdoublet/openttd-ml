"""V257 : contrats source et fixtures arithmetiques, sans moteur ni VM NoAI.

Les expressions de gain et de remboursement sont extraites du Squirrel livre.
Ces tests ne remplacent ni compilation NoAI, ni smoke, ni Save/Load moteur.
"""
from pathlib import Path
import re
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def body(source, signature):
    match = re.search(re.escape(signature) + r"\n\{(.*?)\n\}", source, re.S)
    if match is None:
        raise AssertionError(signature)
    return match.group(1)


def expression(source, variable, **values):
    """Sous-ensemble arithmetique : executer l'expression livree, pas sa copie."""
    code = re.search(r"local " + variable + r" = (.*?);", source, re.S).group(1)
    code = re.sub(r"([\w.]+)\.tofloat\(\)", r"float(\1)", code)
    code = code.replace("&&", " and ").replace("||", " or ")
    code = " ".join(code.split())
    return eval(code, {"__builtins__": {}, "float": float}, values)


class RailRefresh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {path.name: path.read_text(encoding="utf-8") for path in AI.glob("*.nut")}
        cls.task = cls.sources["task_v257.nut"]
        cls.step = body(cls.task, "function OpexAI::_v257ReactiveStep()")
        cls.review = body(cls.task, "function OpexAI::_v257Review(line, state, date, force)")
        cls.replace = body(cls.task, "function OpexAI::_v257ReplaceStep()")
        cls.reconcile = body(cls.task, "function OpexV257Reconcile(owner)")

    def test_setting_off_at_every_difficulty(self):
        setting = re.search(r'name = "v257_rail_refresh",(.*?)\}\);', self.sources["info.nut"], re.S).group(1)
        for level in ("easy", "medium", "hard", "custom", "default"):
            self.assertRegex(setting, level + r"_value = 0\b")
        self.assertIn("min_value = 0, max_value = 1", setting)
        self.assertIn("V257_RAIL_REFRESH <- false;", self.sources["globals_pre.nut"])
        self.assertEqual(sum(s.count('GetSetting("v257_rail_refresh")') for s in self.sources.values()), 1)
        self.assertIn('GetSetting("v257_rail_refresh") == 1', self.sources["settings.nut"])

    def test_only_one_hot_path_guard(self):
        orchestrator = self.sources["orchestrator.nut"]
        self.assertEqual(orchestrator.count("V257_RAIL_REFRESH"), 1)
        self.assertEqual(orchestrator.count("this._v257ReactiveStep()"), 1)
        self.assertIn("if (V257_RAIL_REFRESH) this._v257ReactiveStep();", orchestrator)
        for name in ("scheduler.nut", "scheduler_tasks.nut", "catalog.nut", "event_handlers.nut"):
            self.assertNotIn("V257", self.sources[name])

    def test_one_line_per_reactive_pass_without_search_loop(self):
        self.assertNotRegex(self.step, r"\b(foreach|while|for)\s*\(")
        self.assertIn("this._lines[this._v257Cursor++]", self.step)
        self.assertEqual(self.step.count("this._v257Review("), 1)
        self.assertIn("this._v257PriorityRemaining--", self.step)
        self.assertIn("if (this._v257Pending != null)", self.step)
        self.assertIn("} else if (this._lines", self.step)
        self.assertNotIn("_findLineById", self.replace)
        self.assertIn("local line = this._v257PendingLine", self.replace)

    def test_catalogue_and_event_invalidate_lazily(self):
        self.assertIn('this._c76GetLayerRevision("engines.rail")', self.step)
        self.assertIn("this._v257CatalogRef != this._catalog.railLocos", self.step)
        self.assertIn("this._v257Cursor = 0;", self.step)
        self.assertIn("this._v257Cache = {};", self.step)
        self.assertIn("this._v257PriorityRemaining =", self.step)
        self.assertIn("cached.monthly == monthly", self.review)
        self.assertIn("cached.railType == railType", self.review)
        self.assertIn("cached.platformLength == line.platformLength", self.review)
        self.assertIn("best = cached.target;", self.review)

    def test_line_rail_type_and_platform_not_future_catalogue_type(self):
        self.assertIn("AIRail.GetRailType(line.depot)", self.review)
        self.assertIn("AIEngine.CanRunOnRail(engine, railType)", self.review)
        self.assertIn("AIEngine.HasPowerOnRail(engine, railType)", self.review)
        self.assertNotIn("this._catalog.railType", self.review)
        self.assertIn("OpexRailNominalMaxWagons(length)", self.review)
        self.assertIn('AIGameSettings.GetValue("vehicle.max_train_length")', self.review)

    def _loco_gate(self, **values):
        """Predicat livre : une locomotive sans cargo entre dans la boucle de plans."""
        condition = re.search(r"else if \((.*?)\) \{", self.review, re.S).group(1)
        for source, name in (
            ("AIEngine.HasPowerOnRail(engine, railType)", "has_power"),
            ("AIEngine.GetCapacity(engine)", "capacity"),
            ("AIEngine.GetPower(engine)", "power"),
            ("AIEngine.GetMaxSpeed(engine)", "speed"),
            ("AIEngine.GetMaxTractiveEffort(engine)", "tractive"),
        ):
            condition = condition.replace(source, name)
        condition = " ".join(condition.replace("&&", " and ").replace("||", " or ").split())
        return eval(condition, {"__builtins__": {}}, values)

    def test_pure_locomotive_capacity_sentinel_produces_a_candidate(self):
        """GetCapacity renvoie -1, jamais 0, quand aucune partie articulee n'a de cargo.

        OpenTTD 15.3 src/script/api/script_engine.cpp, ScriptEngine::GetCapacity :
        la boucle rend la premiere capacite non nulle, sinon -1. Le filtre == 0
        laissait donc locos vide, la boucle loco x wagon x nombre ne creait aucun
        plan, et best restait null (reason=catalogue) sur des lignes en service.
        """
        self.assertNotRegex(self.review, r"GetCapacity\(engine\)\s*==\s*0")
        self.assertRegex(self.review, r"GetCapacity\(engine\)\s*<=\s*0")
        powered = {"has_power": True, "power": 600, "speed": 112, "tractive": 120}
        self.assertTrue(self._loco_gate(capacity=-1, **powered))
        self.assertTrue(self._loco_gate(capacity=0, **powered))
        self.assertFalse(self._loco_gate(capacity=40, **powered))
        self.assertFalse(self._loco_gate(capacity=-1, has_power=False, power=600, speed=112, tractive=120))
        self.assertFalse(self._loco_gate(capacity=-1, has_power=True, power=0, speed=112, tractive=120))
        # Le catalogue retient les non-wagons sans tester la capacite.
        refresh = body(self.sources["catalog.nut"], "function OpexCatalog::_refreshRail()")
        loco_branch = refresh.split("} else {", 1)[1].split("this.railLocos.append(entry);", 1)[0]
        self.assertNotIn("GetCapacity", loco_branch)
        self.assertIn("HasPowerOnRail(e, chosen)", loco_branch)

    def test_replacement_branch_stays_open_for_a_pure_locomotive(self):
        """Apres un plan non nul, une locomotive de capacite -1 n'est pas une automotrice.

        Le remboursement peut alors loguer decision=replace : gain strictement
        positif, vie restante strictement positive, gain * vie >= cout net.
        """
        skip = re.search(r"if \((AIEngine\.GetCapacity\(currentEngine\) > 0)\)", self.review).group(1)
        skip = skip.replace("AIEngine.GetCapacity(currentEngine)", "capacity")
        self.assertFalse(eval(skip, {"__builtins__": {}}, {"capacity": -1}))
        self.assertTrue(eval(skip, {"__builtins__": {}}, {"capacity": 40}))
        self.assertIn('pays ? "replace" : "keep"', self.review)
        self.assertTrue(expression(self.review, "pays", gain=8000, remaining=12, cost=90000))
        self.assertFalse(expression(self.review, "pays", gain=8000, remaining=12, cost=96001))

    def test_physics_reused_and_running_costs_include_wagons(self):
        plan = body(self.task, "function OpexV257Plan(line, loco, wagon, wagons, monthly)")
        for helper in ("OpexRailEffectiveSpeed", "OpexLoadedTripsPerMonth", "OpexRailStationDwellDays"):
            self.assertIn(helper + "(", plan)
        self.assertIn("loco.runningCost + wagons * wagon.runningCost", plan)
        for physics in ("2048", "512", "746", "OpexRailResistance", "OpexRailForce"):
            self.assertNotIn(physics, plan)
        self.assertNotIn("amortAnnual", plan)

    def test_real_profit_waiting_ratings_and_unloading(self):
        for api in ("AIVehicle.GetProfitLastYear", "AIVehicle.GetRunningCost", "AIVehicle.GetCargoLoad",
                    "AIStation.GetCargoWaiting", "AIStation.GetCargoRating"):
            self.assertIn(api + "(", self.review)
        self.assertIn("atStation == stationB", self.review)
        self.assertIn('line.kind == "pax" && atStation == stationA', self.review)
        self.assertIn("state.delivered += state.loads[vehicle] - amount", self.review)
        self.assertIn("state.annualDelivered <= 0", self.review)
        self.assertIn("partial_profit_year", self.review)
        self.assertNotIn("line.monthly", self.review)

    def test_backlog_is_annual_not_monthly(self):
        monthly = expression(self.review, "monthly", state=SimpleNamespace(annualDelivered=1200, annualDays=365),
                             waiting=120, count=2)
        self.assertEqual(monthly, 55)

    def test_yearly_observations_survive_new_model_review(self):
        self.assertIn("state.annualDelivered = state.delivered", self.review)
        self.assertIn("state.delivered = 0", self.review)
        self.assertIn("(!force && date < state.nextDate)", self.review)
        self.assertIn("AIDate.GetDate(year + 1, AIDate.GetMonth(date), 1)", self.review)
        self.assertNotIn("1970", self.task)

    def test_gain_is_anchored_to_cash_profit_and_not_amortization(self):
        gain = expression(self.review, "gain", realRevenue=12000,
                          best=SimpleNamespace(revenue=150, running=1500),
                          current=SimpleNamespace(revenue=120),
                          AIVehicle=SimpleNamespace(GetRunningCost=lambda vehicle: 2000), vehicle=7)
        self.assertEqual(gain, 3500)
        self.assertIn("GetProfitLastYear(vehicle) + AIVehicle.GetRunningCost(vehicle)", self.review)

    def test_payback_exact_boundary(self):
        self.assertTrue(expression(self.review, "pays", gain=3500, remaining=3, cost=10500))
        self.assertFalse(expression(self.review, "pays", gain=3500, remaining=2.99, cost=10500))

    def test_no_replacement_with_loss_or_expired_vehicle(self):
        for gain, remaining, cost in ((0, 3, -1), (-100, 3, -1000), (100, 0, 0), (100, -1, 0)):
            with self.subTest(gain=gain, remaining=remaining, cost=cost):
                self.assertFalse(expression(self.review, "pays", gain=gain, remaining=remaining, cost=cost))

    def test_positive_gain_with_net_resale_credit(self):
        self.assertTrue(expression(self.review, "pays", gain=1, remaining=1, cost=-100))

    def test_resale_is_whole_consist_tested_in_depot(self):
        sale = body(self.task, "function OpexV257SaleValue(vehicle)")
        self.assertIn("AIVehicle.GetCurrentValue(vehicle)", sale)  # borne prudente hors depot
        self.assertLess(sale.index("AIAccounting()"), sale.index("AITestMode()"))
        self.assertLess(sale.index("AITestMode()"), sale.index("AIVehicle.SellVehicle(vehicle)"))
        self.assertIn("return -accounting.GetCosts()", sale)
        self.assertIn("local cost = best.price - sale;", self.review)
        self.assertIn("OpexV257SaleValue(oldVehicle)", self.replace)

    def test_one_train_build_and_orders_preserved_before_sale(self):
        self.assertEqual(self.replace.count("OpexBuildTrains("), 1)
        self.assertIn("line.stationA, line.stationB, 1, loco", self.replace)
        self.assertIn("line.platformLength, false)", self.replace)
        for action in ("AIOrder.CopyOrders(newVehicle, oldVehicle)", "AIOrder.SkipToOrder(newVehicle, pending.order)",
                       "AIVehicle.StartStopVehicle(newVehicle)"):
            self.assertLess(self.replace.index(action), self.replace.index("AIVehicle.SellVehicle(oldVehicle)"))
        self.assertIn("AIVehicle.GetLocation(oldVehicle)", self.replace)
        self.assertIn("depot_timeout", self.replace)
        self.assertIn('pending.phase = "resume"', self.replace)

    def test_failed_build_keeps_old_and_cleans_partial_consist(self):
        self.assertIn("foreach (vehicle in built.rollbackVehicles)", self.replace)
        self.assertIn("OpexV257Discard(this, vehicle)", self.replace)
        discard = body(self.task, "function OpexV257Discard(owner, vehicle)")
        self.assertIn("AIVehicle.IsStoppedInDepot(vehicle)", discard)
        self.assertIn("AIVehicle.SellVehicle(vehicle)", discard)
        self.assertIn("lineId = -1", discard)
        self.assertIn("AIVehicle.StartStopVehicle(oldVehicle)", self.replace)
        self.assertIn("this._vehiclesToRetire.rawset(oldVehicle", self.replace)

    def test_resume_and_purchase_have_gross_cash_and_fresh_payback_guards(self):
        self.assertIn("GetBankBalance(AICompany.COMPANY_SELF) - price < OpexCashReserve()", self.replace)
        self.assertIn("pending.gain * remaining < cost", self.replace)
        self.assertIn("if (newLife < remaining) remaining = newLife", self.replace)
        self.assertLess(self.replace.index("depot_recheck"), self.replace.index("OpexBuildTrains("))
        self.assertIn('if (pending.phase == "resume")', self.replace)

    def test_gain_is_recomputed_after_arrival_not_reused_blindly(self):
        self.assertIn("AIVehicle.GetProfitLastYear(oldVehicle) + AIVehicle.GetRunningCost(oldVehicle)", self.replace)
        self.assertIn("AIStation.GetCargoWaiting", self.replace)
        self.assertIn("local target = OpexV257Plan(", self.replace)
        self.assertLess(self.replace.index("pending.gain = gain.tointeger()"),
                        self.replace.index("pending.gain * remaining < cost"))
        self.assertIn("pending.gain <= 0", self.replace)

    def test_short_save_does_not_open_an_unrecoverable_transaction(self):
        self.assertLess(self.step.index("if (!SAVE_FULL_STATE) return;"), self.step.index("OpexOpsMeasureBegin"))
        self.assertIn("!SAVE_FULL_STATE", self.reconcile)

    def test_no_magic_money_age_or_profit_threshold(self):
        code = re.sub(r"/\*.*?\*/|//[^\n]*|\"[^\"]*\"", "", self.task, flags=re.S)
        numbers = set(re.findall(r"(?<![\w.])\d+(?:\.\d+)?(?![\w.])", code))
        self.assertLessEqual(numbers, {"0", "0.0", "1", "1.0", "2", "12", "365", "365.0", "0.036"})

    def test_persistence_outside_monthly_projection_and_after_live_lines(self):
        persist = self.sources["persist.nut"]
        self.assertIn("saveObj.v257RailRefresh <-", persist)
        self.assertIn('"v257RailRefresh" in data', persist)
        for field in ("cursor", "state", "pending", "engineRevision", "priorityRemaining"):
            self.assertRegex(persist, r"\b" + field + r" = this\._v257")
        self.assertLess(persist.index("this._lines = liveLines;"), persist.index("OpexV257Reconcile(this)"))
        self.assertIn("owner._v257Cursor = 0", self.reconcile)
        self.assertIn("states.rawset(line.lineId, state)", self.reconcile)
        self.assertIn("owner._v257Cache = null", self.reconcile)
        self.assertIn("owner._saveProjection = null", self.reconcile)

    def test_interrupted_purchase_reconciles_or_rolls_back_by_identity(self):
        self.assertIn('pending.phase = "building"', self.replace)
        self.assertIn("pending.before.append(vehicle)", self.replace)
        self.assertIn("local vehicles = AIVehicleList()", self.reconcile)
        self.assertIn("pending.before.find(vehicle) == null", self.reconcile)
        self.assertIn("line.vehicles[index] = newVehicle", self.reconcile)
        self.assertIn("if (!mapped) line.vehicles.append(newVehicle)", self.reconcile)
        self.assertIn('pending.phase != "depot"', self.reconcile)
        self.assertIn("if (!keepResume)", self.reconcile)

    def test_no_nested_closure_or_reserved_identifiers(self):
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", self.task, flags=re.S)
        self.assertNotRegex(code, r"\blocal\s+(clone|base|parent)\b")
        self.assertNotRegex(code, r"=\s*function\s*\(")
        self.assertEqual(code.count("{"), code.count("}"))
        self.assertEqual(code.count("("), code.count(")"))
        for signature in ("_v257ReactiveStep();", "_v257Review(line, state, date, force);", "_v257ReplaceStep();"):
            self.assertIn("function " + signature, self.sources["main.nut"])
        self.assertIn('require("task_v257.nut")', self.sources["main.nut"])

    def test_log_and_opcode_instrumentation(self):
        for line in self.task.splitlines():
            if "OpexDecide(" in line:
                self.assertIn("DECISION_LOG", line)
        for event in ("V257_REVIEW", "V257_REPLACE", "V257_OPS"):
            self.assertIn('OpexDecide("' + event + '"', self.task)
        self.assertIn("OpexOpsMeasureBegin()", self.step)
        self.assertIn("OpexOpsMeasureEnd(mark)", self.step)
        self.assertIn('OpexSpanBegin("task.v257_rail_refresh")', self.step)


if __name__ == "__main__":
    unittest.main()
