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


def translate_squirrel(src, integer_div=False):
    """Fonctions pures a une instruction par ligne. La division entiere Squirrel
    n'est demandee que pour l'inverse d'octet, dont tous les operandes sont entiers."""
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"//[^\n]*", "", src)
    lines = []
    for line in src.splitlines():
        statement = line.strip()
        if not statement or statement in ("{", "}"):
            continue
        statement = statement.replace("&&", " and ").replace("||", " or ")
        statement = re.sub(r"(?<![=!<>])!(?!=)", " not ", statement)
        statement = statement.replace("null", "None")
        statement = re.sub(r"\blocal\s+", "", statement)
        statement = re.sub(r"([\w.]+)\.tofloat\(\)", r"float(\1)", statement)
        statement = re.sub(r"([\w.]+)\.tointeger\(\)", r"int(\1)", statement)
        if integer_div:
            statement = statement.replace("/", "//")
        if statement.endswith(";"):
            statement = statement[:-1]
        returned = re.match(r"if \((.*)\) return (.*)$", statement)
        if returned:
            lines.append("if %s: return %s" % (returned.group(1), returned.group(2)))
            continue
        conditional = re.match(r"if \((.*)\) (.*)$", statement)
        if conditional:
            lines.append("if %s: %s" % (conditional.group(1), conditional.group(2)))
            continue
        lines.append(statement)
    if not lines:
        raise AssertionError("empty squirrel body")
    return "\n".join("    " + line for line in lines)


def compile_squirrel(source, signature, namespace, integer_div=False):
    match = re.match(r"function (\w+)\((.*)\)", signature)
    name, args = match.group(1), match.group(2)
    script = "def %s(%s):\n%s\n" % (name, args, translate_squirrel(body(source, signature), integer_div))
    exec(script, namespace)
    return namespace[name]


class RailRefresh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {path.name: path.read_text(encoding="utf-8") for path in AI.glob("*.nut")}
        cls.task = cls.sources["task_v257.nut"]
        cls.step = body(cls.task, "function OpexAI::_v257ReactiveStep()")
        cls.review = body(cls.task, "function OpexAI::_v257Review(line, state, date, force)")
        cls.replace = body(cls.task, "function OpexAI::_v257ReplaceStep()")
        cls.reconcile = body(cls.task, "function OpexV257Reconcile(owner)")
        cls.choice = body(cls.task, "function OpexV257BestPlan(owner, line, monthly, rating, serviceSpeed, railType, wagonLimits)")

    def test_setting_on_at_every_difficulty(self):
        # 19/10 : defaut 1 a tous les niveaux (decision utilisateur apres la porte A 20x10 PC).
        setting = re.search(r'name = "v257_rail_refresh",(.*?)\}\);', self.sources["info.nut"], re.S).group(1)
        for level in ("easy", "medium", "hard", "custom", "default"):
            self.assertRegex(setting, level + r"_value = 1\b")
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
        self.assertIn("cached.monthly == monthly", self.choice)
        self.assertIn("cached.railType == railType", self.choice)
        self.assertIn("cached.platformLength == line.platformLength", self.choice)
        self.assertIn("cached.rating == rating", self.choice)
        self.assertIn("cached.serviceSpeed == serviceSpeed", self.choice)
        self.assertIn("cached.wagonLimits == wagonLimits", self.choice)
        self.assertIn("return cached.target;", self.choice)
        self.assertIn("OpexV257BestPlan(this, line, monthly, planRating, serviceSpeed, railType, wagonLimits)", self.review)

    def test_line_rail_type_and_platform_not_future_catalogue_type(self):
        self.assertIn("AIRail.GetRailType(line.depot)", self.review)
        self.assertIn("AIEngine.CanRunOnRail(engine, railType)", self.choice)
        self.assertIn("AIEngine.HasPowerOnRail(engine, railType)", self.choice)
        self.assertNotIn("this._catalog.railType", self.review)
        self.assertNotIn("this._catalog.railType", self.choice)
        self.assertIn("OpexRailNominalMaxWagons(length)", self.choice)
        self.assertIn('AIGameSettings.GetValue("vehicle.max_train_length")', self.choice)

    def _loco_gate(self, **values):
        """Predicat livre : une locomotive sans cargo entre dans la boucle de plans."""
        condition = re.search(r"else if \((.*?)\) \{", self.choice, re.S).group(1)
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
        self.assertNotRegex(self.choice, r"GetCapacity\(engine\)\s*==\s*0")
        self.assertRegex(self.choice, r"GetCapacity\(engine\)\s*<=\s*0")
        self.assertNotRegex(self.review, r"GetCapacity\(engine\)\s*==\s*0")
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
        plan = body(self.task, "function OpexV257Plan(line, loco, wagon, wagons, monthly, rating, serviceSpeed, wagonLimits)")
        for helper in ("OpexRailEffectiveSpeed", "OpexLoadedTripsPerMonth", "OpexRailStationDwellDays"):
            self.assertIn(helper + "(", plan)
        self.assertIn("OpexV257CapturedMonthly(", plan)
        self.assertIn("if (carried > captured) carried = captured;", plan)
        self.assertNotIn("if (carried > monthly)", plan)
        self.assertIn("loco.runningCost + wagons * wagon.runningCost", plan)
        for physics in ("2048", "512", "746", "OpexRailResistance", "OpexRailForce"):
            self.assertNotIn(physics, plan)
        self.assertNotIn("amortAnnual", plan)
        # Le terme avion convertit les unites ; le modele rail de note neuve
        # ecrase la note observee. Aucun des deux ne remplace le terme source.
        self.assertNotIn("OpexC121SpeedRatingPoints(", self.task)
        self.assertNotIn("OpexStationRatingForHeadway(", self.task)

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
        for reason in ("build_failed", "copy_orders_failed", "skip_order_failed", "start_failed"):
            self.assertIn('reason = "' + reason + '"', self.replace)
        self.assertNotIn("build_order_start_failed", self.task)
        self.assertLess(self.replace.index("if (reason != null)"), self.replace.index("OpexV257Discard(this, vehicle)"))
        self.assertLess(self.replace.index("OpexV257Discard(this, vehicle)"),
                        self.replace.index("AIVehicle.SellVehicle(oldVehicle)"))

    def test_skip_already_current_order_is_success(self):
        """CmdSkipToOrder refuse l'index deja courant. Une rame neuve y est deja."""
        self.assertLess(self.replace.index("here != pending.order"),
                        self.replace.index("AIOrder.SkipToOrder(newVehicle, pending.order)"))
        self.assertIn("AIOrder.ResolveOrderPosition(newVehicle, AIOrder.ORDER_CURRENT)", self.replace)
        self.assertLess(self.replace.index("AIOrder.CopyOrders(newVehicle, oldVehicle)"),
                        self.replace.index("here != pending.order"))

    def test_depot_send_failure_keeps_the_old_train(self):
        """Deja au depot : pas d'envoi, la transaction reste. Sinon journal, sans vente."""
        compact = " ".join(self.review.split())
        self.assertLess(self.review.index("AIVehicle.IsStoppedInDepot(selectedVehicle)"),
                        self.review.index("AIVehicle.SendVehicleToDepot(selectedVehicle)"))
        self.assertIn("!AIVehicle.IsStoppedInDepot(selectedVehicle) && !AIVehicle.SendVehicleToDepot(selectedVehicle)",
                      compact)
        self.assertIn("depot_send_failed", self.review)
        self.assertNotIn("SellVehicle(selectedVehicle)", self.review)
        self.assertNotIn("SellVehicle(oldVehicle)", self.review)
        self.assertIn("lineProfit = lineProfit", self.review)
        for call in ("depot_timeout", "depot_recheck"):
            self.assertIn(call, self.replace)
        self.assertEqual(self.replace.count("lineProfit, waiting, rating, load, delivered"), 3)

    def test_resume_and_purchase_have_gross_cash_and_fresh_payback_guards(self):
        self.assertIn("GetBankBalance(AICompany.COMPANY_SELF) - price < OpexCashReserve()", self.replace)
        self.assertIn("pending.gain * remaining < cost", self.replace)
        self.assertIn("if (newLife < remaining) remaining = newLife", self.replace)
        self.assertLess(self.replace.index("depot_recheck"), self.replace.index("OpexBuildTrains("))
        self.assertIn('if (pending.phase == "resume")', self.replace)

    def test_gain_is_recomputed_after_arrival_not_reused_blindly(self):
        self.assertIn("AIVehicle.GetProfitLastYear(oldVehicle) + AIVehicle.GetRunningCost(oldVehicle)", self.replace)
        self.assertIn("AIStation.GetCargoWaiting", self.replace)
        self.assertIn("AIStation.GetCargoRating", self.replace)
        self.assertIn("OpexV257ConsistLastSpeed(serviceLoco, serviceWagon, wagonLimits)", self.replace)
        self.assertEqual(self.replace.count("OpexV257Plan("), 2)
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
        # 85 et 255 : station_cmd.cpp:4048 (last_speed - 85) et le plafond
        # uint8 de economy.cpp:1764. Le decalage >> 2 reutilise le 2 deja livre.
        self.assertLessEqual(numbers, {"0", "0.0", "1", "1.0", "2", "12", "365", "365.0", "0.036", "85", "255"})

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

    def test_speed_rating_changes_captured_demand_on_the_exposure(self):
        """160 km/h vers 128 km/h perd de la demande captee, donc de la recette
        quand la ligne est plafonnee. Les sept `decision=replace` de
        results/v257rev_expo2_3x4_20261018_engine sont rejoues sur la paire
        journalisee. Les vitesses sont celles de engines.h (1 unite = 1 km-ish/h,
        la meme unite que last_speed avant le plafond uint8) : 23 = 160, 13 = 128,
        14 = 144. Le profit de ligne n'est le profit du train revu que s'il est seul.
        """
        coverage = self.sources["air_coverage.nut"]
        self.assertIn("if (rawMonthly <= 0.0 || rating <= 0) return 0.0;", coverage)
        self.assertIn("return rawMonthly.tofloat() * (rating + 1).tofloat() / 256.0;", coverage)
        captured_src = body(self.task, "function OpexV257CapturedMonthly(monthly, ratingPercent, serviceSpeed, planSpeed)")
        self.assertIn("if (planSpeed == serviceSpeed) return monthly;", captured_src)
        self.assertIn("OpexC121RatingPercentToByteMid(ratingPercent)", captured_src)
        self.assertIn("OpexC121StationAllocatedMonthly(1.0, observed, null)", captured_src)
        self.assertIn("OpexC121StationAllocatedMonthly(1.0, predicted, null)", captured_src)
        self.assertIn("if (predicted <= 0) return 0;", captured_src)
        points_src = body(self.task, "function OpexV257SpeedRatingPoints(lastSpeed)")
        self.assertIn("return (lastSpeed - 85) >> 2;", points_src)
        self.assertIn('IsValid("vehicle.wagon_speed_limits")', self.task)
        self.assertIn("wagon.speed > 0 && wagon.speed < speed", self.task)

        namespace = {"__builtins__": {}, "float": float}
        compile_squirrel(coverage, "function OpexC121RatingPercentToByteMid(pct)", namespace, integer_div=True)
        share = re.search(
            r"return (rawMonthly\.tofloat\(\) \* \(rating \+ 1\)\.tofloat\(\) / 256\.0);",
            coverage).group(1)
        share = re.sub(r"\((rating \+ 1)\)\.tofloat\(\)", r"float(\1)", share)
        share = re.sub(r"([\w.]+)\.tofloat\(\)", r"float(\1)", share)

        def allocated(rawMonthly, rating, competition):
            if competition is not None:
                raise AssertionError("concurrence hors du cas gare seule")
            if rawMonthly <= 0.0 or rating <= 0:
                return 0.0
            return eval(share, {"__builtins__": {}, "float": float},
                        {"rawMonthly": rawMonthly, "rating": rating})

        namespace["OpexC121StationAllocatedMonthly"] = allocated
        compile_squirrel(self.task, "function OpexV257SpeedRatingPoints(lastSpeed)", namespace)
        compile_squirrel(self.task, "function OpexV257CapturedMonthly(monthly, ratingPercent, serviceSpeed, planSpeed)", namespace)
        points = namespace["OpexV257SpeedRatingPoints"]
        captured = namespace["OpexV257CapturedMonthly"]
        byte_mid = namespace["OpexC121RatingPercentToByteMid"]
        for speed, expected in ((85, 0), (128, (128 - 85) >> 2), (144, (144 - 85) >> 2),
                                (160, (160 - 85) >> 2), (255, (255 - 85) >> 2), (300, (255 - 85) >> 2)):
            self.assertEqual(points(speed), expected)
        self.assertEqual(captured(100, 78, 160, 160), 100)

        # Paire journalisee. real_rev/real_prof/real_run/vehs : LINE_REVENUE de
        # l'annee 1973 de la meme ligne rail, pas le journal de decision.
        rows = (
            dict(seed=100, line=10, best=13, gain=1084, cost=-2437, line_profit=56069,
                 rating=78, plan=128, real_rev=61131, real_prof=56069, real_run=5062, vehs=2),
            dict(seed=100, line=12, best=13, gain=1084, cost=-1619, line_profit=45033,
                 rating=55, plan=128, real_rev=47564, real_prof=45033, real_run=2531, vehs=1),
            dict(seed=100, line=15, best=14, gain=703, cost=-598, line_profit=3155,
                 rating=42, plan=144, real_rev=5686, real_prof=3155, real_run=2531, vehs=1),
            dict(seed=100, line=18, best=13, gain=1084, cost=-2899, line_profit=41269,
                 rating=52, plan=128, real_rev=43800, real_prof=41269, real_run=2531, vehs=1),
            dict(seed=42, line=15, best=13, gain=1084, cost=-1952, line_profit=22661,
                 rating=71, plan=128, real_rev=25192, real_prof=22661, real_run=2531, vehs=1),
            dict(seed=42, line=16, best=13, gain=1084, cost=-2032, line_profit=14401,
                 rating=78, plan=128, real_rev=16932, real_prof=14401, real_run=2531, vehs=1),
            dict(seed=7, line=16, best=13, gain=1084, cost=-2738, line_profit=10501,
                 rating=78, plan=128, real_rev=13032, real_prof=10501, real_run=2531, vehs=1),
        )
        stay_replace = set()
        become_keep = set()
        for row in rows:
            self.assertEqual(row["real_prof"], row["line_profit"])
            self.assertEqual(row["real_rev"], row["real_prof"] + row["real_run"])
            self.assertLess(row["cost"], 0)
            ratio = captured(1.0, row["rating"], 160, row["plan"])
            observed = byte_mid(row["rating"])
            predicted = observed + points(row["plan"]) - points(160)
            self.assertGreater(predicted, 0)
            self.assertAlmostEqual(ratio, (predicted + 1) / (observed + 1))
            self.assertLess(ratio, 1.0)
            if row["plan"] == 128:
                self.assertLess(points(row["plan"]), points(160))
            if row["vehs"] != 1:
                per_run = row["real_run"] // row["vehs"]
                self.assertEqual(row["real_run"], per_run * row["vehs"])
                full = (row["line_profit"] + per_run) * (ratio - 1.0) + row["gain"]
                self.assertLess(full, 0)
                threshold_profit = row["gain"] / (1.0 - ratio) - per_run
                just_below = (threshold_profit - 1) + per_run
                just_above = (threshold_profit + 1) + per_run
                self.assertGreater(just_below * (ratio - 1.0) + row["gain"], 0)
                self.assertLess(just_above * (ratio - 1.0) + row["gain"], 0)
                self.assertFalse(((threshold_profit + per_run) * (ratio - 1.0) + row["gain"]) > 0)
                continue
            real = row["real_rev"]
            loss = real * (1.0 - ratio)
            new_gain = real * (ratio - 1.0) + row["gain"]
            self.assertGreater(loss, 0)
            self.assertAlmostEqual(new_gain, row["gain"] - loss)
            # Cout net negatif et vie restante deja positive le jour du replace :
            # un gain encore positif suffit, un gain negatif ou nul ne remplace plus.
            key = (row["seed"], row["line"])
            if new_gain > 0:
                stay_replace.add(key)
            else:
                become_keep.add(key)
        self.assertEqual(stay_replace, {(100, 15), (42, 16), (7, 16)})
        self.assertEqual(become_keep, {(100, 12), (100, 18), (42, 15)})


if __name__ == "__main__":
    unittest.main()
