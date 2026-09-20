from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from bench_v2 import air_equipment_diagnostic_stats
from campaign_freeze import parse_ai_settings


AIR = ROOT / "ai" / "OpexAI" / "builder_air.nut"
GLOBALS = ROOT / "ai" / "OpexAI" / "globals_pre.nut"
INFO = ROOT / "ai" / "OpexAI" / "info.nut"
PROJECTS = ROOT / "ai" / "OpexAI" / "projects.nut"
SETTINGS = ROOT / "ai" / "OpexAI" / "settings.nut"
TASK_AIR = ROOT / "ai" / "OpexAI" / "task_air.nut"
TASK_PROJECTS = ROOT / "ai" / "OpexAI" / "task_projects.nut"
DUEL_BENCH = ROOT / "sweeps" / "bench_1v1_5y_20seeds.py"


def local_pareto(rows):
    ordered = sorted(rows, key=lambda x: (x["capital"], -x["profit"], x["id"]))
    kept = []
    best_profit = None
    for row in ordered:
        if best_profit is not None and row["profit"] <= best_profit:
            continue
        kept.append(row)
        best_profit = row["profit"]
    return kept


def capital_price_relaxation(projects, budget):
    """Reference model for the portfolio shadow price used by projects.nut."""
    groups = {}
    for project in projects:
        finance_capital = project.get("finance_capital", project["capital"])
        shadow_capital = project.get("shadow_capital", project["capital"])
        if finance_capital > budget or project["profit"] <= 0:
            continue
        groups.setdefault(project["group"], []).append({**project, "capital": shadow_capital})

    segments = []
    full_demand = 0
    base_demand = 0
    for rows in groups.values():
        rows = [*rows, {"capital": 0, "profit": 0}]
        rows = sorted(rows, key=lambda row: (row["capital"], -row["profit"]))
        pareto = []
        best = None
        for row in rows:
            if best is not None and row["profit"] <= best:
                continue
            pareto.append((row["capital"], row["profit"]))
            best = row["profit"]

        hull = []
        for point in pareto:
            while len(hull) >= 2:
                a, b = hull[-2], hull[-1]
                slope1 = (b[1] - a[1]) / (b[0] - a[0])
                slope2 = (point[1] - b[1]) / (point[0] - b[0])
                if slope1 > slope2:
                    break
                hull.pop()
            hull.append(point)

        base_demand += hull[0][0]
        full_demand += hull[-1][0]
        for previous, following in zip(hull, hull[1:]):
            delta_capital = following[0] - previous[0]
            delta_profit = following[1] - previous[1]
            segments.append((delta_profit / delta_capital, delta_capital))

    if full_demand <= budget:
        return 0.0

    demand = base_demand
    for slope, delta_capital in sorted(segments, key=lambda row: (-row[0], row[1])):
        if demand + delta_capital > budget:
            return slope
        demand += delta_capital
    return 0.0


def capital_price_score(project, lambda_):
    return project["profit"] - lambda_ * project.get("shadow_capital", project["capital"])


def lifecycle_step_dominated_by_noop(capital_committed, profit_delta_annual):
    return capital_committed >= 0 and profit_delta_annual <= 0


def old_lifecycle_action_kinds(have, target_count, max_planes):
    actions = set()
    for target in range(1, max_planes + 1):
        if target_count < have:
            actions.add("replace" if target_count < target else "retire")
        elif have > target:
            actions.add("retire")
        elif have < target:
            actions.add("grow")
    return actions


def direct_lifecycle_action_kinds(have, target_count, max_planes):
    actions = set()
    if target_count < have:
        if target_count > 0 and max_planes > 0:
            actions.add("retire")
        if max_planes > target_count:
            actions.add("replace")
    else:
        if have > 1 and max_planes > 0:
            actions.add("retire")
        if max_planes > have:
            actions.add("grow")
    return actions



def incumbent_loss_station_key(*station_ids):
    stations = sorted({station for station in station_ids if station is not None and station >= 0})
    if not stations:
        return None
    return "stations|" + "|".join(str(station) for station in stations)


def ordered_exact_upper_prune(rows, budget):
    """Reference for the group-local exact upper-bound certificate."""
    groups = {}
    unaffordable = []
    for row in rows:
        if row.get("finance_capital", row["capital"]) > budget:
            unaffordable.append(row)
            continue
        groups.setdefault(row["group"], []).append(row)

    retained = []
    pruned = []
    for group_rows in groups.values():
        ordered = sorted(
            group_rows,
            key=lambda row: (
                row.get("shadow_capital", row["capital"]),
                -row.get("upper_profit", row["profit"]),
                row["id"],
            ),
        )
        best_profit = None
        best_capital = None
        for row in ordered:
            capital = row.get("shadow_capital", row["capital"])
            upper_profit = row.get("upper_profit", row["profit"])
            dominated = best_profit is not None and (
                best_profit > upper_profit
                or (best_profit == upper_profit and best_capital < capital)
            )
            if dominated:
                pruned.append(row)
                continue
            retained.append(row)
            profit = row["profit"]
            if (
                best_profit is None
                or profit > best_profit
                or (profit == best_profit and capital < best_capital)
            ):
                best_profit = profit
                best_capital = capital
    return retained + unaffordable, pruned


def best_profit_under_budget(rows, budget):
    return max((row["profit"] for row in rows if row["capital"] <= budget), default=0)


class TestAirCapitalFrontier(unittest.TestCase):
    def test_switch_is_explicit_and_off_by_default(self):
        defaults = parse_ai_settings(INFO)
        self.assertEqual(defaults["air_capital_frontier"], 0)
        self.assertEqual(defaults["air_capital_frontier_probe"], 0)
        self.assertEqual(defaults["air_best_equipment"], 0)
        self.assertEqual(defaults["air_route_plane_selection"], 1)
        self.assertEqual(defaults["portfolio_max_batch"], 1)
        self.assertIn("AIR_CAPITAL_FRONTIER <- false", GLOBALS.read_text(encoding="utf-8"))
        self.assertIn("AIR_CAPITAL_FRONTIER_PROBE <- false", GLOBALS.read_text(encoding="utf-8"))
        self.assertIn(
            'AIR_CAPITAL_FRONTIER = AIController.GetSetting("air_capital_frontier") != 0;',
            SETTINGS.read_text(encoding="utf-8"),
        )
        self.assertIn(
            'AIR_CAPITAL_FRONTIER_PROBE = AIController.GetSetting("air_capital_frontier_probe") != 0;',
            SETTINGS.read_text(encoding="utf-8"),
        )

    def test_early_slot_is_neutralized_under_capital_frontier(self):
        src = PROJECTS.read_text(encoding="utf-8")
        select = src[
            src.index("function OpexProjectSelectAffordable"):
            src.index("function OpexProjectSelectionScore")
        ]
        self.assertIn("AIR_EARLY_SLOT && !useCapitalFrontier", select)
        self.assertIn("OpexProjectRefreshEarlySlot(project, earlySlotState)", select)
        self.assertNotIn(
            "OpexProjectInsert(affordable, project, scoreKey, limit,\n                      AIR_EARLY_SLOT, useCapitalFrontier)",
            select,
        )

    def test_local_air_frontier_is_pure_capital_profit_dominance(self):
        rows = [
            {"id": 1, "capital": 40, "profit": 25},
            {"id": 2, "capital": 65, "profit": 32},
            {"id": 3, "capital": 150, "profit": 35},
            {"id": 4, "capital": 170, "profit": 34},
            {"id": 5, "capital": 65, "profit": 30},
        ]
        self.assertEqual([r["id"] for r in local_pareto(rows)], [1, 2, 3])

        src = AIR.read_text(encoding="utf-8")
        self.assertIn("function OpexAirEquipmentFrontier", src)
        self.assertIn("frontierCapital = economics.capital + economics.immobilise", src)
        frontier = src[src.index("function OpexAirEquipmentFrontier"):src.index("function OpexAirRouteChoices")]
        self.assertIn("local capitalOrder = AIList()", frontier)
        self.assertIn("capitalOrder.AddItem(i, choices[i].frontierCapital)", frontier)
        self.assertIn("capitalOrder.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING)", frontier)
        self.assertIn("bucketProfit > bestProfit", frontier)
        self.assertNotIn("choices.sort(function", frontier)
        self.assertNotIn("sqrt(", frontier)

    def test_pareto_pruning_preserves_best_profit_for_every_budget(self):
        rows = [
            {"id": 1, "capital": 20, "profit": 8},
            {"id": 2, "capital": 35, "profit": 12},
            {"id": 3, "capital": 35, "profit": 11},
            {"id": 4, "capital": 60, "profit": 18},
            {"id": 5, "capital": 75, "profit": 17},
            {"id": 6, "capital": 90, "profit": 24},
        ]
        kept = local_pareto(rows)
        for budget in range(0, 111):
            self.assertEqual(
                best_profit_under_budget(rows, budget),
                best_profit_under_budget(kept, budget),
                f"budget={budget}",
            )

    def test_capital_price_matches_fifteen_percent_increment_example(self):
        projects = [
            {"group": "air-a", "capital": 100, "profit": 20},
            {"group": "air-a", "capital": 300, "profit": 50},
            {"group": "other", "capital": 100, "profit": 25},
            {"group": "other", "capital": 200, "profit": 45},
        ]
        lambda_ = capital_price_relaxation(projects, 300)
        self.assertAlmostEqual(lambda_, 0.15)
        cheap = projects[0]
        expensive = projects[1]
        self.assertAlmostEqual(capital_price_score(cheap, lambda_), 5.0)
        self.assertAlmostEqual(capital_price_score(expensive, lambda_), 5.0)

    def test_capital_price_falls_to_zero_when_capital_is_abundant(self):
        projects = [
            {"group": "a", "capital": 100, "profit": 20},
            {"group": "a", "capital": 300, "profit": 50},
            {"group": "b", "capital": 200, "profit": 45},
        ]
        self.assertEqual(capital_price_relaxation(projects, 500), 0.0)
        self.assertGreater(
            capital_price_score(projects[1], 0.0),
            capital_price_score(projects[0], 0.0),
        )

    def test_capital_price_uses_one_concave_local_frontier_per_group(self):
        projects = [
            {"group": "a", "capital": 40, "profit": 10},
            {"group": "a", "capital": 100, "profit": 40},
            {"group": "b", "capital": 80, "profit": 24},
        ]
        # (40,10) is Pareto but below the upper concave hull from (0,0) to (100,40).
        self.assertAlmostEqual(capital_price_relaxation(projects, 100), 0.3)

        src = PROJECTS.read_text(encoding="utf-8")
        price = src[src.index("function OpexCapitalPriceRelaxation"):src.index("function OpexCapitalFrontierAssignScores")]
        self.assertIn("rows.append({ capital = 0, profit = 0 })", price)
        self.assertIn("local pareto = []", price)
        self.assertIn("local baseDemand = 0", price)
        self.assertIn("if (slope1 > slope2) break", price)
        self.assertIn("segments.append({", price)
        self.assertIn("fullDemand <= capitalBudget", price)

    def test_frontier_keeps_engine_and_fleet_depth_as_the_decision_unit(self):
        src = AIR.read_text(encoding="utf-8")
        economics = src[src.index("function OpexAirEconomicsChoices"):src.index("function OpexAirEconomics(")]
        historical = src[
            src.index("function OpexAirEconomics("):
            src.index("function OpexAirEquipmentContext")
        ]
        equipment = src[src.index("function OpexAirEquipmentChoices"):src.index("function OpexAirEquipmentFrontier")]
        self.assertIn("for (local planes = firstPlanes; planes <= targetPlanes; planes++)", economics)
        self.assertIn("choices.append({", economics)
        self.assertIn("planes = planes", economics)
        self.assertNotIn("OpexAirEconomicsChoices(", historical)
        self.assertIn("profitAnnual > best.profitAnnual", historical)
        self.assertIn("local economicsChoices = OpexAirEconomicsChoices", equipment)
        self.assertIn("foreach (economics in economicsChoices)", equipment)

    def test_concorde_pareto_probe_is_passive_and_exact(self):
        src = AIR.read_text(encoding="utf-8")
        section = src[
            src.index("Diagnostic uniquement : expliquer le sort du Concorde"):
            src.index("if (AIR_CAPITAL_FRONTIER_PROBE) AIR_CAPITAL_FRONTIER_LEDGER.routeKept")
        ]
        self.assertIn("choice.plane.id != 218", section)
        self.assertIn("choice.frontierCapital > concorde.frontierCapital", section)
        self.assertIn("choice.economics.profitAnnual < concorde.economics.profitAnnual", section)
        self.assertIn('OpexDecide("AIR_FRONTIER_218"', section)
        self.assertNotIn("rawset", section)
        self.assertNotIn("OpexAirEconomics(", section)

    def test_frontier_equipment_decision_probe_is_logging_only(self):
        src = PROJECTS.read_text(encoding="utf-8")
        equipment = src[
            src.index("function OpexLogAirFrontierEquipmentChoice"):
            src.index("function OpexLogConcordeFrontierScores")
        ]
        concorde = src[
            src.index("function OpexLogConcordeFrontierScores"):
            src.index("function OpexAirFrontierExternalityStations")
        ]
        externality = src[
            src.index("function OpexAirFrontierExternalityStations"):
            src.index("function OpexProjectKeyFor")
        ]
        self.assertIn("if (!DECISION_LOG", equipment)
        self.assertIn('OpexDecide("AIR_FRONTIER_EQUIP"', equipment)
        self.assertIn("selected_engine=", equipment)
        self.assertIn("project.payload.plane.id", equipment)
        self.assertIn("OpexProjectFinanceCapital(project)", equipment)
        self.assertIn("project.frontierCapitalPrice", equipment)
        self.assertIn("project.frontierCapitalCharge", equipment)
        self.assertIn("OpexCapitalFrontierProjectProfit(project)", equipment)
        self.assertIn("project.frontierScore", equipment)
        self.assertIn('OpexDecide("AIR_FRONTIER_218_SCORE"', concorde)
        self.assertIn("sameBest.frontierScore", concorde)
        self.assertNotIn("frontierPrunedTopK", equipment + concorde)
        self.assertIn("function OpexAirFrontierIncumbentLoss", src)
        self.assertIn("OpexAirActualFleetEconomics", externality)
        self.assertIn('OpexDecide("AIR_FRONTIER_EXTERNALITY"', externality)
        self.assertIn("OpexLogConcordeFrontierScores(alternatives, affordable[0], capitalBudget)", src)
        self.assertIn("OpexLogAirFrontierIncumbentExternality(alternatives, affordable[0], capitalBudget, catalog, lines)", src)
        self.assertNotIn("rawset", equipment + concorde)
        self.assertNotIn("OpexProjectInsert", equipment + concorde + externality)

    def test_frontier_uses_exact_air_network_marginal_profit(self):
        src = PROJECTS.read_text(encoding="utf-8")
        context = src[
            src.index("function OpexAirFrontierExternalityStations"):
            src.index("function OpexAirFrontierAffectedStates")
        ]
        state_profit = src[
            src.index("function OpexAirFrontierStateProfit"):
            src.index("function OpexAirFrontierIncumbentLoss")
        ]
        incumbent = src[
            src.index("function OpexAirFrontierIncumbentLoss"):
            src.index("function OpexCapitalFrontierProjectProfit")
        ]
        assign = src[
            src.index("function OpexCapitalFrontierAssignScores"):
            src.index("function OpexProjectIsFreeAirRetirement")
        ]
        self.assertIn("OpexAirActualFleetEconomicsContext(catalog, line, distance)", context)
        self.assertNotIn("OpexAirActualFleetEconomics(", context)
        self.assertIn("OpexAirFleetEconomicsFromContext(state.economicsContext, demand)", state_profit)
        self.assertNotIn("OpexAirActualFleetEconomics(", state_profit)
        self.assertIn("if (key in state.profits) return state.profits[key]", state_profit)
        self.assertIn("state.profits.rawset(key, profit)", state_profit)
        self.assertIn("OpexAirFrontierStateProfit(state, 0, 0)", incumbent)
        self.assertIn("OpexAirFrontierStateProfit(state, incrementA, incrementB)", incumbent)
        self.assertIn("local ownProfit = project.profitAnnual - loss", assign)
        self.assertIn("project.frontierOwnProfit = ownProfit", assign)
        self.assertIn("project.frontierIncumbentLoss = loss", assign)
        self.assertNotIn("project.profitAnnual = ownProfit", assign)

    def test_active_scoring_estimates_one_capital_price_and_no_post_state(self):
        src = PROJECTS.read_text(encoding="utf-8")
        assign = src[
            src.index("function OpexCapitalFrontierAssignScores"):
            src.index("function OpexProjectIsFreeAirRetirement")
        ]
        self.assertIn("local externalityCache = {}", assign)
        self.assertIn("local targetStations = OpexAirFrontierExternalityStations(externalityCandidates, capitalBudget)", assign)
        self.assertIn("OpexAirFrontierExternalityContext(catalog, lines, targetStations)", assign)
        self.assertEqual(assign.count("OpexCapitalPriceRelaxationPrepared("), 1)
        self.assertIn("local prepared = OpexCapitalFrontierPrepare(", assign)
        self.assertIn('project.rawset("frontierCapitalPrice", price.lambda)', assign)
        self.assertIn('project.rawset("frontierCapitalCharge", capitalCharge)', assign)
        self.assertIn("local score = ownProfit.tofloat() - capitalCharge", assign)
        self.assertIn('project.rawset("frontierScore", score)', assign)
        self.assertIn('project.rawset("frontierScoreInt", score.tointeger())', assign)
        self.assertNotIn("OpexCapitalFrontierContinuation(", assign)
        self.assertNotIn("OpexCapitalFrontierInteractionPlan(", assign)
        self.assertNotIn("OpexCapitalFrontierStaticTreeBuild(", assign)
        self.assertNotIn("OpexCapitalFrontierContinuationBuckets(", assign)

    def test_incumbent_loss_is_non_negative_and_cached_per_reused_station_set(self):
        src = PROJECTS.read_text(encoding="utf-8")
        incumbent = src[
            src.index("function OpexAirFrontierIncumbentLoss"):
            src.index("function OpexCapitalFrontierProjectProfit")
        ]
        loss_key = src[
            src.index("function OpexAirFrontierIncumbentLossKey"):
            src.index("function OpexCapitalFrontierNeedsIncumbentLoss")
        ]
        self.assertEqual(incumbent_loss_station_key(7), incumbent_loss_station_key(7, 7))
        self.assertEqual(incumbent_loss_station_key(7, 11), incumbent_loss_station_key(11, 7))
        self.assertNotEqual(incumbent_loss_station_key(7), incumbent_loss_station_key(11))
        self.assertIsNone(incumbent_loss_station_key(-1, None))
        self.assertIn("local key = OpexAirFrontierIncumbentLossKey(project)", incumbent)
        self.assertIn("if (key != null && cache != null && (key in cache)) return cache[key]", incumbent)
        self.assertIn("if (before > after) loss += before - after", incumbent)
        self.assertNotIn("project.payload.plane", incumbent)
        self.assertNotIn("OpexCapitalFrontierAirProjectGeometryKey(project)", incumbent)
        self.assertIn('("reuseA" in plan) && plan.reuseA', loss_key)
        self.assertIn('("reuseB" in plan) && plan.reuseB', loss_key)
        self.assertIn("stationB != first", loss_key)
        self.assertIn("second < first", loss_key)
        self.assertIn('"stations|" + first + "|" + second', loss_key)

    def test_fleet_and_non_air_are_exact_zero_loss_without_incumbent_scan(self):
        src = PROJECTS.read_text(encoding="utf-8")
        loss_key = src[
            src.index("function OpexAirFrontierIncumbentLossKey"):
            src.index("function OpexCapitalFrontierNeedsIncumbentLoss")
        ]
        zero_loss = src[
            src.index("function OpexCapitalFrontierNeedsIncumbentLoss"):
            src.index("function OpexCapitalFrontierStrictUpperDominated")
        ]
        prepare = src[
            src.index("function OpexCapitalFrontierPrepare"):
            src.index("function OpexCapitalFrontierEnvelope")
        ]
        assign = src[
            src.index("function OpexCapitalFrontierAssignScores"):
            src.index("function OpexProjectIsFreeAirRetirement")
        ]
        self.assertIn('project.mode != "air"', loss_key)
        self.assertIn("return OpexAirFrontierIncumbentLossKey(project) != null", zero_loss)
        self.assertIn("needsLoss = OpexCapitalFrontierNeedsIncumbentLoss(project, catalog, lines)", prepare)
        self.assertIn("if (row.needsLoss)", assign)
        self.assertIn("local loss = 0", assign)

    def test_ordered_exact_upper_dominance_preserves_lambda_and_winner(self):
        rows = [
            {"id": "a", "group": "g", "capital": 40, "upper_profit": 100, "profit": 10},
            {"id": "b", "group": "g", "capital": 80, "upper_profit": 90, "profit": 90},
            {"id": "c", "group": "g", "capital": 120, "upper_profit": 80, "profit": 70},
            {"id": "d", "group": "g", "capital": 130, "upper_profit": 90, "profit": 80},
            {"id": "e", "group": "h", "capital": 50, "upper_profit": 40, "profit": 40},
            {"id": "f", "group": "h", "capital": 100, "upper_profit": 35, "profit": 35},
            {"id": "x", "group": "x", "capital": 90, "upper_profit": 25, "profit": 25},
            {"id": "y0", "group": "y", "capital": 100, "upper_profit": 50, "profit": 50},
            {"id": "y1", "group": "y", "capital": 100, "upper_profit": 50, "profit": 40},
        ]
        budget = 260
        kept, pruned = ordered_exact_upper_prune(rows, budget)
        kept_rev, pruned_rev = ordered_exact_upper_prune(list(reversed(rows)), budget)
        self.assertEqual({row["id"] for row in pruned}, {"c", "d", "f"})
        self.assertEqual({row["id"] for row in pruned_rev}, {"c", "d", "f"})
        self.assertIn("y1", {row["id"] for row in kept})

        lambda_full = capital_price_relaxation(rows, budget)
        lambda_kept = capital_price_relaxation(kept, budget)
        self.assertAlmostEqual(lambda_full, lambda_kept)

        def winner(projects, lambda_):
            affordable = [row for row in projects if row["capital"] <= budget]
            return min(
                affordable,
                key=lambda row: (
                    -capital_price_score(row, lambda_),
                    row["capital"],
                    -row["profit"],
                    row["id"],
                ),
            )["id"]

        self.assertEqual(winner(rows, lambda_full), winner(kept, lambda_kept))

    def test_source_exact_upper_pruning_is_group_local_sorted_and_selection_safe(self):
        src = PROJECTS.read_text(encoding="utf-8")
        assign = src[
            src.index("function OpexCapitalFrontierAssignScores"):
            src.index("function OpexProjectIsFreeAirRetirement")
        ]
        price = src[
            src.index("function OpexCapitalPriceRelaxation"):
            src.index("function OpexCapitalFrontierAssignScores")
        ]
        select = src[
            src.index("function OpexProjectSelectAffordable"):
            src.index("function OpexProjectSelectionScore")
        ]
        prepare = src[
            src.index("function OpexCapitalFrontierPrepare"):
            src.index("function OpexCapitalFrontierEnvelope")
        ]
        self.assertIn("function OpexCapitalFrontierStrictUpperDominated", src)
        self.assertIn("function OpexCapitalFrontierRememberBestExact", src)
        self.assertIn("local prepared = { byGroup = {} }", prepare)
        self.assertNotIn("prepared.flat", prepare)
        self.assertIn("if (a.capital < b.capital) return -1", prepare)
        self.assertIn("if (a.upperProfit > b.upperProfit) return -1", prepare)
        self.assertIn("local byGroup = prepared.byGroup", assign)
        self.assertIn("candidateGroups != null", prepare)
        self.assertIn('project.rawset("frontierExactDominated", false)', assign)
        self.assertIn("local externalityCandidates = []", assign)
        self.assertLess(
            assign.index("local externalityCandidates = []"),
            assign.index("OpexAirFrontierExternalityContext(catalog, lines, targetStations)"),
        )
        self.assertIn("frontierExactDominated", price)
        self.assertIn("frontierExactDominated", select)


    def test_portfolio_passes_live_catalog_and_lines_only_to_frontier_scoring(self):
        src = PROJECTS.read_text(encoding="utf-8")
        assign = src[
            src.index("function OpexCapitalFrontierAssignScores"):
            src.index("function OpexProjectIsFreeAirRetirement")
        ]
        select = src[src.index("function OpexProjectSelectAffordable"):src.index("function OpexProjectSelectionScore")]
        self.assertIn("alternatives, capitalBudget, catalog, lines, selectionDiagnostic", select)
        self.assertIn("function OpexCapitalPriceRelaxation", src)
        self.assertIn("OpexCapitalFrontierPrepare(", assign)
        self.assertIn("local price = OpexCapitalPriceRelaxationPrepared(", assign)
        self.assertNotIn("upperPoints", assign)
        self.assertNotIn("exactTop", assign)
        self.assertIn('catalog, lines, "generation", false', src)
    def test_real_selector_instrumentation_is_cause_aware(self):
        src = PROJECTS.read_text(encoding="utf-8")
        globals_src = GLOBALS.read_text(encoding="utf-8")
        self.assertIn("AIR_SELECTION_LEDGER <- {", globals_src)
        self.assertIn("function OpexSelectionLedgerRecordCause", src)
        self.assertIn("function OpexSelectionLedgerRecordPhase", src)
        self.assertIn('OpexSelectionLedgerRecordPhase("prepare"', src)
        self.assertIn('"generation", false', src)
        self.assertIn('"lifecycle", false', src)
        self.assertIn('"dynamic_batch"', src)
        self.assertIn('"diagnostic_counterfactual", true', src)
        task = TASK_PROJECTS.read_text(encoding="utf-8")
        self.assertIn('this._catalog, this._lines, "execution"', task)

    def test_coarse_lambda_uses_one_group_representative_and_native_ailist_sort(self):
        src = PROJECTS.read_text(encoding="utf-8")
        prepare = src[
            src.index("function OpexCapitalFrontierPrepare"):
            src.index("function OpexCapitalFrontierEnvelope")
        ]
        relaxation = src[
            src.index("function OpexCapitalPriceRelaxationPrepared"):
            src.index("/* Prix du capital du portefeuille.")
        ]
        reselect = src[
            src.index("function OpexReselectProjects"):
            src.index("function OpexProjectSelectionStats")
            if "function OpexProjectSelectionStats" in src
            else src.index("function OpexB6", src.index("function OpexReselectProjects"))
        ]
        self.assertIn('("prepared" in selectionCache)', prepare)
        self.assertIn("AIR_SELECTION_LEDGER.preparedHits++", prepare)
        self.assertIn('selectionCache.rawset("prepared", prepared)', prepare)
        self.assertIn("local ratios = AIList()", relaxation)
        self.assertIn("local sampleMax = 32", relaxation)
        self.assertIn("local representative = null", relaxation)
        self.assertIn("local predecessor = null", relaxation)
        self.assertIn("local deltaCapital = representative.capital - priorCapital", relaxation)
        self.assertIn("local deltaProfit = representativeProfit - priorProfit", relaxation)
        self.assertIn(
            "(deltaProfit.tofloat() * 100.0) / deltaCapital",
            relaxation,
        )
        self.assertIn("ratios.AddItem(sampleCount, ratioPct)", relaxation)
        self.assertIn("ratios.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING)", relaxation)
        self.assertIn("local target = (sampleCount - 1) / 8", relaxation)
        self.assertIn('selectionCache.rawset("coarseLambdaPct", lambdaPct)', relaxation)
        self.assertIn('selectionCache.rawset("coarseFullDemand", fullDemand)', relaxation)
        self.assertNotIn("segments.sort(function", relaxation)
        assign = src[
            src.index("function OpexCapitalFrontierAssignScores"):
            src.index("function OpexProjectIsFreeAirRetirement")
        ]
        self.assertIn('local externalityStateKey = OpexAirFrontierExternalityStateKey(lines, targetStations)', assign)
        self.assertIn('selectionCache.externalityContextStateKey == externalityStateKey', assign)
        self.assertIn('row.lossKnown && ("lossStateKey" in row)', assign)
        self.assertIn('row.lossStateKey == externalityStateKey', assign)
        self.assertIn('row.rawset("lossStateKey", externalityStateKey)', assign)
        self.assertIn('projects.rawset("frontierSelectionCache", {})', src)
        self.assertIn("selectionCache = projects.frontierSelectionCache", reselect)
        self.assertIn('projects.rawset("frontierSelectionCache", selectionCache)', src)
        self.assertIn('result.rawset("frontierSelectionCache", selectionCache)', src)

    def test_externality_cache_key_contains_all_live_profit_inputs(self):
        src = PROJECTS.read_text(encoding="utf-8")
        key = src[
            src.index("function OpexAirFrontierExternalityStateKey"):
            src.index("function OpexAirFrontierExternalityContext")
        ]
        self.assertIn("targetIds.sort()", key)
        self.assertIn("routeCounts.rawset", key)
        self.assertIn("AITown.GetPopulation(townA)", key)
        self.assertIn("AITown.GetPopulation(townB)", key)
        self.assertIn("OpexFlightDistance(line.stationA, line.stationB)", key)
        self.assertIn("AIVehicle.GetEngineType(v)", key)
        self.assertIn("item.engines.sort()", key)
        self.assertIn("states.sort()", key)
        self.assertNotIn("hash", key.lower())

    def test_lifecycle_deduplicates_concrete_next_actions_before_pareto(self):
        air = AIR.read_text(encoding="utf-8")
        prepare = air[
            air.index("function OpexAirNextStepPrepare"):
            air.index("function OpexAirNextStepEconomics")
        ]
        step = air[
            air.index("function OpexAirNextStepEconomics"):
            air.index("function OpexAirRemainingTransitionCapital")
        ]
        frontier = air[
            air.index("function OpexAirExistingLineFrontier"):
            air.index("function OpexAirAssessExistingLine")
        ]
        self.assertIn("state.vehicles.append(v)", prepare)
        self.assertIn("currentEconomicsByDemand = {}", prepare)
        self.assertIn("stepCache = {}", prepare)
        self.assertIn('"replace|v=" + releasedVehicle + "|e=" + targetPlane.id', step)
        self.assertIn('"retire|v=" + releasedVehicle', step)
        self.assertIn('"grow|e=" + targetPlane.id', step)
        self.assertIn("if (out.actionKey in state.stepCache)", step)
        self.assertIn("local stepState = OpexAirNextStepPrepare(catalog, line)", frontier)
        self.assertIn("local byAction = {}", frontier)
        self.assertIn("if (!(step.actionKey in byAction))", frontier)
        self.assertIn("option.targetEngine < prior.targetEngine", frontier)
        self.assertIn("local optionOrder = AIList()", frontier)
        self.assertIn("optionOrder.AddItem(i, options[i].capitalCommitted)", frontier)
        self.assertIn("optionOrder.Sort(AIList.SORT_BY_VALUE, AIList.SORT_ASCENDING)", frontier)
        self.assertNotIn("options.sort(function", frontier)
        self.assertLess(frontier.index("foreach (actionKey, option in byAction)"),
                        frontier.index("local optionOrder = AIList()"))

    def test_air_possibility_catalog_is_cash_independent_and_has_no_prescan(self):
        air = AIR.read_text(encoding="utf-8")
        projects = PROJECTS.read_text(encoding="utf-8")
        plans = air[
            air.index("function OpexAirPlans"):
            air.index("function OpexAirProbeSite")
        ]
        make = air[
            air.index("function OpexAirMakePossibility"):
            air.index("function OpexAirRememberPossibility")
        ]
        remember = air[
            air.index("function OpexAirRememberPossibility"):
            air.index("function OpexAirPlans", air.index("function OpexAirRememberPossibility"))
        ]
        self.assertNotIn("OpexAirMinimumFinanceCapital", air)
        self.assertNotIn("minFinanceCapital", air)
        self.assertNotIn("materializeBudget", air)
        self.assertNotIn("OpexAirTechnicalChoiceCount(", make)
        technical = air[
            air.index("function OpexAirTechnicalChoiceCount"):
            air.index("function OpexAirAnyPlaneFitsAirportTypes")
        ]
        self.assertNotIn("stopAtFirst", technical)
        self.assertGreaterEqual(plans.count("OpexAirMakePossibility("), 3)
        self.assertIn("possibilities.append(possibility)", remember)
        self.assertIn("if (possibility.key in possibilitySeen) return false", remember)
        self.assertIn("OpexAirRememberPossibility(possibility, possibilitySeen, possibilities)", plans)
        self.assertNotIn("OpexAirActivateDeferredPossibilities", projects)
        self.assertNotIn("OpexFrontierNextDeferredFinanceCapital", projects)
        self.assertNotIn("selectionNextDeferredFinance", projects)
        self.assertIn("airPossibilities = airPossibilities", projects)
        cache = air[
            air.index("function OpexAirPossibilityRouteChoices"):
            air.index("function OpexAirMakePossibility")
        ]
        self.assertIn('possibility.rawset("routeChoiceCache", choices)', cache)
        self.assertIn(
            "PORTFOLIO_FRESH_BUDGET || PORTFOLIO_CACHE\n      || (AIR_CAPITAL_FRONTIER && AIR_BEST_EQUIPMENT)",
            projects,
        )

    def test_air_generation_does_not_allocate_default_probe_state(self):
        air = AIR.read_text(encoding="utf-8")
        plans = air[
            air.index("function OpexAirPlans"):
            air.index("function OpexAirProbeSite")
        ]
        self.assertNotIn('local proxyState = { rescued = false, compatibleChoices = 0 }', plans)
        self.assertNotIn(': { current = inBand, envelope = false, added = false }', plans)
        self.assertGreaterEqual(plans.count("local bandState = null;"), 3)
        self.assertGreaterEqual(plans.count("local proxyRescued = false;"), 3)
        self.assertGreaterEqual(plans.count("local proxyCompatibleChoices = 0;"), 3)
        self.assertGreaterEqual(plans.count("local proxyState = OpexAirRegretObservePair"), 3)

    def test_project_group_key_is_cached_without_changing_identity(self):
        src = PROJECTS.read_text(encoding="utf-8")
        self.assertIn('if ("frontierProjectGroupKey" in project) return project.frontierProjectGroupKey', src)
        self.assertIn('project.rawset("frontierProjectGroupKey", key)', src)

    def test_capital_price_respects_real_finance_budget(self):
        src = PROJECTS.read_text(encoding="utf-8")
        price = src[src.index("function OpexCapitalPriceRelaxation"):src.index("function OpexCapitalFrontierAssignScores")]
        assign = src[src.index("function OpexCapitalFrontierAssignScores"):src.index("function OpexProjectIsFreeAirRetirement")]
        select = src[src.index("function OpexProjectSelectAffordable"):src.index("function OpexProjectSelectionScore")]
        self.assertIn('("frontierFinanceCapital" in project)', price)
        self.assertIn("project.frontierFinanceCapital : OpexProjectFinanceCapital(project)", price)
        self.assertIn("local cap = OpexProjectShadowCapital(project)", price)
        self.assertIn("financeCap > capitalBudget", price)
        self.assertIn("local cap = OpexProjectShadowCapital(project)", assign)
        self.assertIn("local capitalCharge = price.lambda * cap", assign)
        self.assertIn("if (financeCapital > capitalBudget) continue", select)

    def test_shadow_price_excludes_finance_margin_but_not_affordability(self):
        projects = [
            {"group": "a", "capital": 150, "finance_capital": 150,
             "shadow_capital": 100, "profit": 20},
            {"group": "b", "capital": 100, "finance_capital": 100,
             "shadow_capital": 100, "profit": 15},
            {"group": "c", "capital": 151, "finance_capital": 151,
             "shadow_capital": 20, "profit": 1000},
        ]
        lambda_ = capital_price_relaxation(projects, 150)
        self.assertAlmostEqual(lambda_, 0.15)
        self.assertAlmostEqual(capital_price_score(projects[0], lambda_), 5.0)

        src = PROJECTS.read_text(encoding="utf-8")
        shadow = src[
            src.index("function OpexProjectShadowCapital"):
            src.index("function OpexPrequoteRailCandidates")
        ]
        self.assertIn('project.mode == "road"', shadow)
        self.assertIn("margin = ROAD_CAPITAL_MARGIN", shadow)
        self.assertIn('project.mode == "water"', shadow)
        self.assertIn("margin = WATER_CAPITAL_MARGIN", shadow)
        self.assertIn('project.mode == "air"', shadow)
        self.assertIn("AIR_MARGIN_V2", shadow)
        self.assertIn("cap -= margin", shadow)
        self.assertNotIn("financeMargin =", src)

    def test_shadow_capital_cache_is_prepared_once_per_candidate_revision(self):
        src = PROJECTS.read_text(encoding="utf-8")
        prepare = src[
            src.index("function OpexCapitalFrontierPrepare"):
            src.index("function OpexCapitalFrontierEnvelope")
        ]
        assign = src[
            src.index("function OpexCapitalFrontierAssignScores"):
            src.index("function OpexProjectIsFreeAirRetirement")
        ]
        shadow = src[
            src.index("function OpexProjectShadowCapitalFromFinance"):
            src.index("function OpexPrequoteRailCandidates")
        ]
        self.assertIn("local financeCap = OpexProjectFinanceCapital(project)", prepare)
        self.assertIn(
            "local shadowCap = OpexProjectShadowCapitalFromFinance(project, financeCap)",
            prepare,
        )
        self.assertIn('project.rawset("frontierFinanceCapital", row.financeCap)', assign)
        self.assertIn('project.rawset("frontierShadowCapital", row.capital)', assign)
        self.assertIn('selectionCache.rawset("prepared", prepared)', prepare)
        self.assertIn('if (project != null && ("frontierShadowCapital" in project))', shadow)
        self.assertIn("return project.frontierShadowCapital", shadow)

    def test_capital_price_is_zero_when_max_profit_choices_fit(self):
        projects = [
            {"group": "a", "capital": 100, "profit": 20},
            {"group": "a", "capital": 200, "profit": 35},
            {"group": "b", "capital": 120, "profit": 18},
        ]
        self.assertEqual(capital_price_relaxation(projects, 400), 0.0)

    def test_capital_price_uses_incremental_frontier_yield(self):
        projects = [
            {"group": "a", "capital": 100, "profit": 20},
            {"group": "a", "capital": 300, "profit": 50},
            {"group": "b", "capital": 150, "profit": 30},
        ]
        self.assertAlmostEqual(capital_price_relaxation(projects, 350), 0.15)
        lambda_ = capital_price_relaxation(projects, 350)
        self.assertAlmostEqual(
            capital_price_score(projects[1], lambda_) - capital_price_score(projects[0], lambda_),
            0.0,
        )

    def test_capital_price_uses_upper_concave_envelope(self):
        projects = [
            {"group": "a", "capital": 100, "profit": 20},
            {"group": "a", "capital": 200, "profit": 25},
            {"group": "a", "capital": 300, "profit": 50},
            {"group": "b", "capital": 150, "profit": 30},
        ]
        self.assertAlmostEqual(capital_price_relaxation(projects, 350), 0.15)

        src = PROJECTS.read_text(encoding="utf-8")
        price = src[src.index("function OpexCapitalPriceRelaxation"):src.index("function OpexCapitalFrontierAssignScores")]
        self.assertIn("rows.append({ capital = 0, profit = 0 })", price)
        self.assertIn("local pareto = []", price)
        self.assertIn("if (slope1 > slope2) break", price)
        self.assertIn("if (fullDemand <= capitalBudget)", price)
        self.assertIn("lambda = segment.lambda", price)

    def test_capital_price_uses_zero_capital_choice_as_group_baseline(self):
        projects = [
            {"group": "a", "capital": 0, "profit": 20},
            {"group": "a", "capital": 100, "profit": 30},
            {"group": "b", "capital": 100, "profit": 20},
        ]
        self.assertAlmostEqual(capital_price_relaxation(projects, 150), 0.10)

        src = PROJECTS.read_text(encoding="utf-8")
        price = src[src.index("function OpexCapitalPriceRelaxation"):src.index("function OpexCapitalFrontierAssignScores")]
        self.assertIn("if (financeCap > capitalBudget || profit <= 0) continue", price)
        self.assertIn("rows.append({ capital = 0, profit = 0 })", price)
        self.assertIn("baseDemand += hull[0].capital", price)

    def test_capital_price_ignores_individually_unaffordable_projects(self):
        projects = [
            {"group": "a", "capital": 100, "profit": 20},
            {"group": "b", "capital": 100, "profit": 15},
            {"group": "c", "capital": 151, "profit": 1000},
        ]
        self.assertAlmostEqual(capital_price_relaxation(projects, 150), 0.15)

    def test_capital_price_uses_marginal_segment_crossing_budget(self):
        projects = [
            {"group": "a", "capital": 100, "profit": 20},
            {"group": "a", "capital": 200, "profit": 30},
            {"group": "b", "capital": 100, "profit": 25},
            {"group": "b", "capital": 200, "profit": 45},
        ]
        self.assertAlmostEqual(capital_price_relaxation(projects, 250), 0.20)

    def test_negative_committed_capital_from_retirement_releases_shadow_budget(self):
        projects = [
            # Retirement is executable with no purchase cash and releases 40 of
            # economic capital. It is the high-lambda base state of group A.
            {"group": "a", "capital": -40, "finance_capital": 0, "profit": 5},
            {"group": "a", "capital": 60, "finance_capital": 100, "profit": 20},
            {"group": "b", "capital": 100, "finance_capital": 100, "profit": 20},
        ]
        lambda_ = capital_price_relaxation(projects, 100)
        self.assertAlmostEqual(lambda_, 0.15)
        self.assertAlmostEqual(capital_price_score(projects[0], lambda_), 11.0)

        src = PROJECTS.read_text(encoding="utf-8")
        price = src[
            src.index("function OpexCapitalPriceRelaxation"):
            src.index("function OpexCapitalFrontierAssignScores")
        ]
        self.assertNotIn("cap < 0 ||", price)
        self.assertIn("local baseDemand = 0", price)
        self.assertIn("baseDemand += hull[0].capital", price)
        self.assertIn("local demand = baseDemand", price)

    def test_air_fleet_contract_separates_cash_resale_transit_and_committed_capital(self):
        air = AIR.read_text(encoding="utf-8")
        prepare = air[
            air.index("function OpexAirNextStepPrepare"):
            air.index("function OpexAirNextStepEconomics")
        ]
        step = air[
            air.index("function OpexAirNextStepEconomics"):
            air.index("function OpexAirRemainingTransitionCapital")
        ]
        self.assertIn("cashRequired = 0, safetyMargin = 0, capitalCommitted = 0", step)
        self.assertIn("state.vehicles.append(v)", prepare)
        self.assertIn("local vehiclesList = state.vehicles", step)
        self.assertIn("releasedVehicle = vehiclesList[oldIndex]", step)
        self.assertIn('"replace|v=" + releasedVehicle', step)
        self.assertIn("out.expectedResale = AIVehicle.GetCurrentValue(releasedVehicle)", step)
        self.assertIn("out.transitDelta = nextTransit - currentTransit", step)
        self.assertIn(
            "out.capitalCommitted = out.cashRequired - out.expectedResale + out.transitDelta",
            step,
        )
        self.assertIn(
            "out.profitDeltaAnnual = nextEconomics.profitAnnual - currentEconomics.profitAnnual",
            step,
        )
        # Replacement example: resale lowers economic capital, never pre-funds cash.
        cash_required = 100
        expected_resale = 40
        transit_delta = 10
        self.assertEqual(cash_required, 100)
        self.assertEqual(cash_required - expected_resale + transit_delta, 70)

    def test_lifecycle_frontier_generates_immediate_actions_without_final_depth_enumeration(self):
        air = AIR.read_text(encoding="utf-8")
        equipment = air[
            air.index("function OpexAirEquipmentChoices"):
            air.index("function OpexAirEquipmentFrontier")
        ]
        lifecycle = air[
            air.index("function OpexAirExistingLineFrontier"):
            air.index("function OpexAirAssessExistingLine")
        ]
        self.assertNotIn("requirePositiveProfit", equipment)
        self.assertIn("economics == null || economics.profitAnnual <= 0", equipment)
        self.assertNotIn("OpexAirEquipmentChoices(", lifecycle)
        self.assertIn("OpexAirEquipmentContext(", lifecycle)
        self.assertIn("for (local actionSlot = 0; actionSlot < 2; actionSlot++)", lifecycle)
        self.assertIn("local targetCount =", lifecycle)
        self.assertIn("targetEconomics = step.nextEconomics", lifecycle)
        self.assertNotIn("targetProfitAnnual", lifecycle)
        self.assertNotIn("transactionCapital", lifecycle)
        self.assertNotIn("marginalGainAnnual", lifecycle)

    def test_direct_lifecycle_actions_match_exhaustive_final_depth_actions(self):
        for have in range(1, 7):
            for target_count in range(0, have + 1):
                for max_planes in range(1, 7):
                    self.assertEqual(
                        old_lifecycle_action_kinds(have, target_count, max_planes),
                        direct_lifecycle_action_kinds(have, target_count, max_planes),
                        (have, target_count, max_planes),
                    )

    def test_lifecycle_noop_dominance_is_signed_and_survives_to_execution(self):
        self.assertTrue(lifecycle_step_dominated_by_noop(100, -1))
        self.assertTrue(lifecycle_step_dominated_by_noop(0, 0))
        self.assertFalse(lifecycle_step_dominated_by_noop(-100, -1))
        self.assertFalse(lifecycle_step_dominated_by_noop(-100, 0))
        self.assertFalse(lifecycle_step_dominated_by_noop(100, 1))
        self.assertAlmostEqual(
            capital_price_score({"capital": -100, "profit": -5}, 0.10),
            5.0,
        )

        air = AIR.read_text(encoding="utf-8")
        lifecycle = air[
            air.index("function OpexAirExistingLineFrontier"):
            air.index("function OpexAirAssessExistingLine")
        ]
        self.assertIn(
            "step.capitalCommitted >= 0 && step.profitDeltaAnnual <= 0",
            lifecycle,
        )
        self.assertNotIn("OpexAirFrontierStepDominatedByNoOp", air)

        task_air = TASK_AIR.read_text(encoding="utf-8")
        store = task_air[
            task_air.index("function OpexAirStoreFrontierTransactions"):
            task_air.index("function OpexAirAppendFrontierTransactions")
        ]
        self.assertNotIn("profitDeltaAnnual <= 0", store)
        self.assertIn("if (option == null) continue;", store)

        projects = PROJECTS.read_text(encoding="utf-8")
        fleet = projects[
            projects.index("function OpexProjectFromFleet"):
            projects.index("function OpexProjectFromAir")
        ]
        self.assertIn('local hasProfitDelta = "profitDeltaAnnual" in entry', fleet)
        self.assertIn("? entry.profitDeltaAnnual", fleet)
        self.assertIn("if (!hasProfitDelta && profit <= 0)", fleet)

        task_projects = TASK_PROJECTS.read_text(encoding="utf-8")
        self.assertIn(
            "freshStep.capitalCommitted >= 0 && freshStep.profitDeltaAnnual <= 0",
            task_projects,
        )

    def test_project_contract_uses_cash_for_affordability_and_committed_for_lambda(self):
        src = PROJECTS.read_text(encoding="utf-8")
        finance = src[
            src.index("function OpexProjectFinanceCapital"):
            src.index("function OpexProjectShadowCapitalFromFinance")
        ]
        shadow = src[
            src.index("function OpexProjectShadowCapitalFromFinance"):
            src.index("function OpexProjectShadowCapital(project)")
        ]
        fleet = src[
            src.index("function OpexProjectFromFleet"):
            src.index("function OpexProjectFromAir")
        ]
        air_project = src[
            src.index("function OpexProjectFromAir"):
            src.index("function OpexProjectFromWater")
        ]
        self.assertIn("local explicitFinance = cashRequired + safetyMargin", finance)
        self.assertNotIn("expectedResale", finance)
        self.assertIn('if (project != null && ("capitalCommitted" in project))', shadow)
        self.assertIn("return project.capitalCommitted", shadow)

        self.assertIn("cashRequired = cashRequired, safetyMargin = safetyMargin", fleet)
        self.assertIn("capitalCommitted = capitalCommitted", fleet)
        self.assertIn("budgetCapital = cashRequired + safetyMargin", fleet)
        self.assertIn("profitDeltaAnnual =", fleet)
        self.assertIn("planningOps = planningOps", fleet)
        self.assertIn("executionOps = expectedOps", fleet)

        self.assertIn("local cashRequired = economics.capital", air_project)
        self.assertIn("local safetyMargin = margin", air_project)
        self.assertIn("local capitalCommitted = economics.capital + immobilise", air_project)
        self.assertIn("local budgetCapital = cashRequired + safetyMargin", air_project)
        self.assertIn("capitalCommitted = capitalCommitted", air_project)

    def test_shadow_price_selection_keeps_do_nothing_outside_option(self):
        src = PROJECTS.read_text(encoding="utf-8")
        select = src[src.index("function OpexProjectSelectAffordable"):src.index("function OpexProjectSelectionScore")]
        self.assertIn("if (useCapitalFrontier && project.frontierScore < 0", select)
        self.assertIn("!OpexProjectIsFreeAirRetirement(project)", select)
        self.assertLess(
            select.index("project.frontierScore < 0"),
            select.index("OpexProjectInsert(affordable, project"),
        )
    def test_frontier_reuses_common_air_engine_without_candidate_fallback(self):
        air = AIR.read_text(encoding="utf-8")
        route = air[air.index("function OpexAirRouteChoices"):air.index("function OpexAirPlaneFromEngine")]
        equipment = air[air.index("function OpexAirEquipmentChoices"):air.index("function OpexAirEquipmentFrontier")]
        lifecycle = air[air.index("function OpexAirExistingLineFrontier"):air.index("function OpexAirAssessExistingLine")]
        self.assertIn("return OpexAirEquipmentFrontier", route)
        self.assertIn("OpexAirBestEquipment", route)
        self.assertIn("OpexAirEconomicsChoices", equipment)
        self.assertIn("OpexAirNextStepEconomics", lifecycle)
        self.assertNotIn("catalog.plane", equipment)
        self.assertNotIn("refleetEngine", lifecycle)

        task = TASK_AIR.read_text(encoding="utf-8")
        start = task.index("local frontierOptions = null;")
        frontier_eval = task[start:task.index("if (assessment.ok)", start)]
        self.assertIn("OpexAirExistingLineFrontier", frontier_eval)
        self.assertNotIn("catalog.plane", frontier_eval)
        self.assertNotIn("refleetEngine", frontier_eval)


    def test_equal_shadow_value_uses_capital_then_profit_as_tie_break(self):
        src = PROJECTS.read_text(encoding="utf-8")
        insert = src[src.index("function OpexProjectInsert"):src.index("function OpexLogVivier")]
        self.assertIn("capitalProfitTie = false", insert)
        self.assertIn("local priorCapital = OpexProjectShadowCapital(prior)", insert)
        self.assertIn("local projectCapital = OpexProjectShadowCapital(project)", insert)
        self.assertIn("OpexCapitalFrontierProjectProfit(prior)", insert)
        self.assertIn("OpexCapitalFrontierProjectProfit(project)", insert)
        selection = src[src.index("function OpexProjectSelectAffordable"):src.index("function OpexProjectSelectionScore")]
        self.assertIn("AIR_EARLY_SLOT && !useCapitalFrontier, useCapitalFrontier", selection)

    def test_source_uses_capital_price_only_under_air_flag(self):
        src = PROJECTS.read_text(encoding="utf-8")
        self.assertIn("function OpexCapitalPriceRelaxation", src)
        self.assertIn("function OpexCapitalFrontierAssignScores", src)
        self.assertIn("AIR_CAPITAL_FRONTIER && AIR_BEST_EQUIPMENT", src)
        self.assertIn('local scoreKey = useCapitalFrontier ? "frontierScore"', src)
        self.assertIn("function OpexCapitalFrontierProjectProfit", src)
        assign = src[src.index("function OpexCapitalFrontierAssignScores"):src.index("function OpexProjectIsFreeAirRetirement")]
        self.assertIn("ownProfit.tofloat() - capitalCharge", assign)
        self.assertNotIn("OpexCapitalFrontierContinuation(", assign)
        section = src[
            src.index("function OpexProjectSelectAffordable"):
            src.index("function OpexProjectSelectionScore")
        ]
        self.assertIn("AIR_CAPITAL_FRONTIER && AIR_BEST_EQUIPMENT", section)
        self.assertIn('local scoreKey = useCapitalFrontier ? "frontierScore"', section)
        self.assertIn("if (!useCapitalFrontier && PORTFOLIO_FLOOR_PCT > 0)", section)
        self.assertIn("if (AIR_EARLY_SLOT && !useCapitalFrontier) OpexProjectRefreshEarlySlot", section)
        self.assertIn("AIR_EARLY_SLOT && !useCapitalFrontier", section)
    def test_early_slot_is_neutralized_when_capital_frontier_is_active(self):
        src = PROJECTS.read_text(encoding="utf-8")
        selection = src[
            src.index("function OpexProjectSelectAffordable"):
            src.index("function OpexProjectSelectionScore")
        ]
        scorer = src[
            src.index("function OpexProjectSelectionScore"):
            src.index("function OpexProjectInsert")
        ]
        self.assertIn('local scoreKey = useCapitalFrontier ? "frontierScore"', selection)
        self.assertIn("if (AIR_EARLY_SLOT && !useCapitalFrontier) OpexProjectRefreshEarlySlot", selection)
        self.assertIn("AIR_EARLY_SLOT && !useCapitalFrontier, useCapitalFrontier", selection)
        self.assertIn("local score = project[field]", scorer)
        self.assertIn("return score * factor", scorer)
        self.assertNotIn('project.frontierScore =', scorer)
        self.assertNotIn('project.frontierScore <-', scorer)

    def test_lifecycle_frontier_scores_only_the_next_physical_step(self):
        src = AIR.read_text(encoding="utf-8")
        section = src[
            src.index("function OpexAirExistingLineFrontier"):
            src.index("function OpexAirAssessExistingLine")
        ]
        self.assertIn("OpexAirNextStepEconomics", section)
        self.assertIn("cashRequired = step.cashRequired", section)
        self.assertIn("capitalCommitted = step.capitalCommitted", section)
        self.assertIn("expectedResale = step.expectedResale", section)
        self.assertIn("transitDelta = step.transitDelta", section)
        self.assertIn("profitDeltaAnnual = step.profitDeltaAnnual", section)
        self.assertNotIn("transactionCapital =", section)
        self.assertNotIn("marginalGainAnnual =", section)
        self.assertIn("upgradeRemaining = (step.kind == \"replace\" || retireOnly) ? 1 : 0", section)
        self.assertNotIn("gainAnnual = target.economics.profitAnnual", section)


    def test_lifecycle_frontier_is_cached_before_target_is_persisted(self):
        task = TASK_AIR.read_text(encoding="utf-8")
        section = task[
            task.index("local frontierOptions = null;"):
            task.index("if (assessment.ok)", task.index("local frontierOptions = null;"))
        ]
        self.assertIn("OpexAirExistingLineFrontier", section)
        self.assertIn(
            "OpexAirStoreFrontierTransactions(line, frontierOptions, now, evalReason)",
            section,
        )
        self.assertIn("OpexAirAppendFrontierTransactions(line, plan)", section)
        self.assertNotIn("frontierAssessment = optionAssessment", section)
        self.assertNotIn("OpexAirApplyLineAssessment(line, optionAssessment)", section)

    def test_lifecycle_frontier_cache_is_flat_serializable_and_revisioned(self):
        task = TASK_AIR.read_text(encoding="utf-8")
        store = task[
            task.index("function OpexAirStoreFrontierTransactions"):
            task.index("function OpexAirAppendFrontierTransactions")
        ]
        self.assertIn('line.rawset("airFrontierRevision", revision)', store)
        self.assertIn('line.rawset("airFrontierTransactions", transactions)', store)
        self.assertIn("frontierRevision = revision", store)
        self.assertIn("frontierTransaction = true", store)
        self.assertIn("targetEngine = option.targetEngine", store)
        self.assertIn("targetFleetSize = option.targetFleetSize", store)
        self.assertIn("cashRequired = option.cashRequired", store)
        self.assertIn("capitalCommitted = option.capitalCommitted", store)
        self.assertIn("expectedResale = option.expectedResale", store)
        self.assertIn("transitDelta = option.transitDelta", store)
        self.assertIn("profitAnnual = option.profitDeltaAnnual", store)
        self.assertIn("netCapital = option.capitalCommitted", store)
        self.assertNotIn("assessment =", store)
        self.assertNotIn("currentEconomics", store)
        self.assertNotIn("targetEconomics", store)

    def test_clean_frontier_line_reemits_cache_and_cannot_fall_through_to_legacy_growth(self):
        task = TASK_AIR.read_text(encoding="utf-8")
        cached = task.index("/* Sous la nouvelle politique, une ligne propre ne retombe JAMAIS")
        cadence = task.index("/* C15 : Cadence d'extension de flotte aerienne.", cached)
        section = task[cached:cadence]
        self.assertIn("if (AIR_CAPITAL_FRONTIER)", section)
        self.assertIn('"airFrontierTransactions" in line', section)
        self.assertIn("OpexAirAppendFrontierTransactions(line, plan)", section)
        self.assertIn('line.rawset("airEquipmentDirtyReason", "frontier_stale")', section)
        self.assertIn("continue;", section)

    def test_frontier_preview_uses_common_frontier_instead_of_historical_target_path(self):
        task = TASK_AIR.read_text(encoding="utf-8")
        start = task.index("local frontierOptions = null;")
        end = task.index("if (assessment.ok)", start)
        section = task[start:end]
        self.assertIn('evalReason == "preview"', section)
        use_line = section[
            section.index("local useFrontierEval ="):
            section.index("local assessment = null;")
        ]
        self.assertNotIn("!hasPreviewCommitment", use_line)
        self.assertIn("previewAssessment = option.assessment", section)
        self.assertIn("_resolveAirPreviewCommitment", section)
        self.assertIn("_abandonAirPreviewCommitment", section)

    def test_selected_lifecycle_step_is_revalidated_and_never_auto_continues(self):
        task = TASK_PROJECTS.read_text(encoding="utf-8")
        self.assertIn("local isFrontierTransaction =", task)
        self.assertIn('("frontierRevision" in entry)', task)
        self.assertIn('("airFrontierRevision" in line)', task)
        self.assertIn("entryRevision != lineRevision", task)
        self.assertIn('"airEquipmentDirty" in line', task)
        self.assertIn("OpexAirNextStepEconomics(this._catalog, line, targetPlane", task)
        self.assertIn("OpexAirLineBaseDemand(line, this._lines)", task)
        self.assertIn("OpexAirPlanDemand(freshSiteA, freshSiteB, targetPlane", task)
        self.assertIn('freshStep.kind != expectedStep', task)
        self.assertIn("freshStep.capitalCommitted >= 0 && freshStep.profitDeltaAnnual <= 0", task)
        self.assertIn("frontierAssessment = {", task)
        self.assertIn("OpexAirApplyLineAssessment(line, frontierAssessment)", task)
        self.assertIn('line.rawset("upgradePending", false)', task)
        self.assertIn('line.rawset("upgradeRemaining", 0)', task)
        self.assertIn("OpexAirClearFrontierTransactions(line)", task)
        self.assertIn('line.rawset("airEquipmentDirtyReason", "frontier_step")', task)

    def test_frontier_selection_stamps_exact_execution_state(self):
        projects = PROJECTS.read_text(encoding="utf-8")
        start = projects.index("function OpexCapitalFrontierAssignScores")
        end = projects.index("function OpexProjectIsFreeAirRetirement", start)
        section = projects[start:end]
        self.assertIn('project.rawset("frontierSelectionBudget", capitalBudget)', section)
        self.assertIn('project.rawset("frontierSelectionProfit", ownProfit)', section)
        self.assertIn('project.rawset("frontierSelectionShadowCapital", cap)', section)
        self.assertIn(
            'project.rawset("frontierSelectionFinanceCapital", financeCap)',
            section,
        )

    def test_execution_revalidates_fleet_action_not_exact_numeric_snapshot(self):
        task = TASK_PROJECTS.read_text(encoding="utf-8")
        start = task.index("function OpexAI::_tryBuildFleetProject")
        end = task.index("function OpexAI::_tryBuild", start + 1)
        section = task[start:end]
        self.assertNotIn("liveBudget != selectedBudget", section)
        self.assertNotIn('reselectReason = "budget"', section)
        self.assertNotIn("freshStep.profitDeltaAnnual != selectedProfit", section)
        self.assertNotIn("freshStep.capitalCommitted != selectedShadowCapital", section)
        self.assertNotIn("freshFinanceCapital != selectedFinanceCapital", section)
        self.assertIn("freshStep.kind != expectedStep", section)
        self.assertIn("freshStep.capitalCommitted >= 0 && freshStep.profitDeltaAnnual <= 0", section)
        self.assertIn('reselectReason = "revision"', section)
        self.assertIn('!("needsRefleet" in line) || !line.needsRefleet', section)
        self.assertIn('reselectReason = "economics"', section)
        self.assertIn("refreshEconomics = true", section)

        air = TASK_AIR.read_text(encoding="utf-8")
        air_start = air.index("function OpexAI::_tryBuildAirProject")
        air_end = air.index("function OpexAI::_queueAirRetirement", air_start)
        air_section = air[air_start:air_end]
        self.assertNotIn("liveBudget != selectedBudget", air_section)
        self.assertNotIn('reselectReason = "budget"', air_section)
        self.assertIn("freshSelection.networkProfit != selectedProfit", air_section)
        self.assertIn('reselectReason = "economics"', air_section)

    def test_targeted_reselection_replaces_invalidated_group_then_resorts(self):
        task = TASK_PROJECTS.read_text(encoding="utf-8")
        start = task.index("function OpexAI::_frontierReselectChangedGroup")
        end = task.index("function OpexAI::_tryBuildFleetProject", start)
        section = task[start:end]
        self.assertIn("OpexAirExistingLineFrontier(", section)
        self.assertIn("OpexAirRefreshProjectGroupAlternatives(", section)
        self.assertIn("this._projects.candidateGroups.rawset(groupKey, fresh)", section)
        self.assertIn(
            "this._dynamicBatch.sourceCandidateGroups.rawset(groupKey, fresh)",
            section,
        )
        self.assertIn("delete this._dynamicBatch.attempted[attemptKey]", section)
        self.assertIn("OpexReselectProjects(", section)

        lambda_ = 0.2
        refreshed = 30 - lambda_ * 100
        competitor = 25 - lambda_ * 50
        self.assertGreater(refreshed, 0)
        self.assertGreater(competitor, refreshed)

    def test_first_air_build_revalidates_network_economics_and_physical_liveness(self):
        task = TASK_AIR.read_text(encoding="utf-8")
        start = task.index("function OpexAI::_tryBuildAirProject")
        end = task.index("function OpexAI::_", start + 1)
        section = task[start:end]
        physical = section[: section.index("local townAId")]
        self.assertIn("if (builtCount > 0 || useCapitalFrontier)", physical)
        self.assertIn("OpexAirBatchPlanStillLive(plan, this._lines)", physical)
        self.assertIn("OpexAirBatchSiteStillBuildable(plan.siteA", physical)
        self.assertIn("OpexAirBatchSiteStillBuildable(plan.siteB", physical)
        self.assertIn("OpexAirFreshSelectedProjectEconomics(", section)
        self.assertIn("freshSelection.networkProfit != selectedProfit", section)
        self.assertIn("freshSelection.shadowCapital != selectedShadowCapital", section)
        self.assertIn("freshSelection.financeCapital != selectedFinanceCapital", section)
        self.assertIn('reselectReason = "economics"', section)

    def test_air_execution_refresh_prices_fixed_variant_and_incumbent_loss(self):
        air = AIR.read_text(encoding="utf-8")
        projects = PROJECTS.read_text(encoding="utf-8")
        live_demand = air[
            air.index("function OpexAirLiveCandidateDemand"):
            air.index("function OpexAirDemandCap")
        ]
        start = projects.index("function OpexAirFreshSelectedProjectEconomics")
        end = projects.index("function OpexProjectFromWater", start)
        section = projects[start:end]
        self.assertIn("AITown.GetPopulation(siteA.town.id)", live_demand)
        self.assertIn("AITown.GetPopulation(siteB.town.id)", live_demand)
        self.assertIn("OpexAirLiveRoutesAtAirport(siteA.anchor, lines)", live_demand)
        self.assertIn("OpexAirLiveRoutesAtAirport(siteB.anchor, lines)", live_demand)
        self.assertIn("monthlyA = monthlyA / (routesA + 1)", live_demand)
        self.assertIn("monthlyB = monthlyB / (routesB + 1)", live_demand)
        self.assertIn("OpexAirLiveCandidateDemand(plan.siteA, plan.siteB, reuseA, reuseB, lines)", section)
        self.assertIn("demandCap, fixedPlanes)", section)
        self.assertIn(
            "OpexAirFrontierIncumbentLoss(freshProject, catalog, lines, {})",
            section,
        )
        self.assertIn("networkProfit = freshProject.profitAnnual - loss", section)

    def test_air_possibility_has_no_deferred_materialization_path(self):
        air = AIR.read_text(encoding="utf-8")
        projects = PROJECTS.read_text(encoding="utf-8")
        self.assertNotIn("function OpexAirMaterializePossibility", air)
        self.assertNotIn("function OpexAirActivateDeferredPossibilities", projects)
        self.assertNotIn("function OpexFrontierNextDeferredFinanceCapital", projects)
        self.assertNotIn("function OpexFrontierStampSelectionValidity", projects)

    def test_air_possibility_reuses_only_exact_route_choice_state(self):
        air = AIR.read_text(encoding="utf-8")
        catalog = (ROOT / "ai" / "OpexAI" / "catalog.nut").read_text(encoding="utf-8")
        projects = PROJECTS.read_text(encoding="utf-8")
        signature = air[
            air.index("function OpexAirPossibilityRouteChoiceSignature"):
            air.index("function OpexAirPossibilityRouteChoices")
        ]
        cached = air[
            air.index("function OpexAirPossibilityRouteChoices"):
            air.index("function OpexAirMakePossibility")
        ]
        plans = air[
            air.index("function OpexAirPlans"):
            air.index("function OpexAirProbeSite")
        ]
        incremental = projects[
            projects.index("function OpexIncrementalUpdateProjects"):
            projects.index("function OpexProjectEmptyRoad")
        ]
        build = projects[projects.index("function OpexBuildProjects"):]

        self.assertIn("airRevision = 0", catalog)
        self.assertIn("this.airRevision++", catalog)
        self.assertIn("if (AIR_DEMAND_PLAN", signature)
        self.assertIn("catalog.airRevision", signature)
        self.assertIn('AIGameSettings.GetValue("economy.inflation")', signature)
        self.assertIn("AIDate.GetMonth(date)", signature)
        self.assertIn("demandContext.monthlyDemand", signature)
        self.assertIn("demandContext.demandCap", signature)
        self.assertIn("possibility.routeChoiceCacheSignature == signature", cached)
        self.assertIn('possibility.rawset("routeChoiceCache", choices)', cached)
        self.assertGreaterEqual(
            plans.count("OpexAirPossibilityInheritRouteChoiceCache(possibility, priorPossibilityCache)"),
            3,
        )
        self.assertIn("priorAirPossibilities", incremental)
        self.assertIn("priorAirPossibilities", build)

    def test_cash_deferral_keeps_frontier_while_failed_build_invalidates(self):
        task_air = TASK_AIR.read_text(encoding="utf-8")
        self.assertIn(
            'if (AIR_CAPITAL_FRONTIER && ("airEquipmentDirty" in line) && line.airEquipmentDirty)',
            task_air,
        )
        self.assertNotIn('evalReason == "frontier_cash"', task_air)
        self.assertIn('evalReason == "frontier_failed"', task_air)
        self.assertIn('evalReason == "restore"', task_air)
        self.assertIn('evalReason == "retire_rollback"', task_air)

        task_projects = TASK_PROJECTS.read_text(encoding="utf-8")
        cash_guard = task_projects.index("if (money < need) {")
        apply_target = task_projects.index("OpexAirApplyLineAssessment(line, frontierAssessment)")
        self.assertLess(cash_guard, apply_target)
        cash_block = task_projects[cash_guard:apply_target]
        self.assertIn("AIR_CAPITAL_FRONTIER_LEDGER.cashRejected++", cash_block)
        self.assertNotIn("OpexAirClearFrontierTransactions(line)", cash_block)
        self.assertNotIn('line.rawset("airEquipmentDirty"', cash_block)
        self.assertNotIn('frontier_cash', task_projects)
        self.assertIn('line.rawset("airEquipmentDirtyReason", "frontier_failed")', task_projects)

    def test_crash_recovery_is_explicit_exception_then_invalidates_frontier(self):
        task = TASK_AIR.read_text(encoding="utf-8")
        crash = task[
            task.index('if (("needsRefleet" in line) && line.needsRefleet)'):
            task.index("/* Sous la nouvelle politique, une ligne propre ne retombe JAMAIS")
        ]
        self.assertIn("AIR_LIFECYCLE_LEDGER.crashExecuted++", crash)
        self.assertIn("OpexAirClearFrontierTransactions(line)", crash)
        self.assertIn('line.rawset("airEquipmentDirtyReason", "frontier_step")', crash)

    def test_bench_parser_decodes_legacy_frontier_signs(self):
        stats = air_equipment_diagnostic_stats({"SIGN": {
            1: {"name": "CF0|120|35|40|9"},
            2: {"name": "CF1|7|3|2|2"},
            3: {"name": "CF2|4|5|6|77"},
            4: {"name": "CF3|500|300|55|21"},
            5: {"name": "CF4|123|456|78"},
            6: {"name": "CF5|321|654|9876"},
            7: {"name": "CF6|87|43|912"},
            8: {"name": "CF7|31|17|444"},
            9: {"name": "CF15|12|10|18000|2400|9000|3600"},
            10: {"name": "CF16|20|17|3|3"},
            11: {"name": "CF17|4|5|2|3|3"},
            12: {"name": "CF18|12000|7|3000|2"},
            13: {"name": "CF19|5000|4000|3000"},
            14: {"name": "CF20|2|1|1"},
            15: {"name": "CF21|700|1|4|9"},
            16: {"name": "CF22|6|8|11"},
            17: {"name": "CF23|100|200|300|400"},
            18: {"name": "CF24|1|2|3|4"},
            19: {"name": "CF25|50|20|30|7"},
            20: {"name": "CF26|4|24|64"},
        }})
        self.assertEqual(stats["air_frontier_route_raw"], 120)
        self.assertEqual(stats["air_frontier_route_kept"], 35)
        self.assertEqual(stats["air_frontier_lifecycle_raw"], 40)
        self.assertEqual(stats["air_frontier_lifecycle_kept"], 9)

        self.assertEqual(stats["air_frontier_selected"], 7)
        self.assertEqual(stats["air_frontier_replace_selected"], 3)
        self.assertEqual(stats["air_frontier_grow_selected"], 2)
        self.assertEqual(stats["air_frontier_retire_selected"], 2)
        self.assertEqual(stats["air_frontier_stale_rejected"], 4)
        self.assertEqual(stats["air_frontier_cash_rejected"], 5)
        self.assertEqual(stats["air_frontier_failed_rejected"], 6)
        self.assertEqual(stats["air_frontier_selected_continuation_k"], 77)
        self.assertEqual(stats["air_frontier_portfolio_raw"], 500)
        self.assertEqual(stats["air_frontier_portfolio_affordable"], 300)
        self.assertEqual(stats["air_frontier_portfolio_top_selections"], 55)
        self.assertEqual(stats["air_frontier_portfolio_top_air_selections"], 21)
        self.assertEqual(stats["air_frontier_portfolio_top_continuation_k"], 123)
        self.assertEqual(stats["air_frontier_portfolio_top_capital_k"], 456)
        self.assertEqual(stats["air_frontier_portfolio_top_profit_k"], 78)
        self.assertEqual(stats["air_selection_calls"], 20)
        self.assertEqual(stats["air_selection_production_calls"], 17)
        self.assertEqual(stats["air_selection_diagnostic_calls"], 3)
        self.assertEqual(stats["air_selection_diagnostic_counterfactual_calls"], 3)
        self.assertEqual(stats["air_selection_generation_calls"], 4)
        self.assertEqual(stats["air_selection_lifecycle_calls"], 5)
        self.assertEqual(stats["air_selection_budget_reselect_calls"], 2)
        self.assertEqual(stats["air_selection_dynamic_batch_calls"], 3)
        self.assertEqual(stats["air_selection_execution_calls"], 3)
        self.assertEqual(stats["air_selection_production_ops"], 12000)
        self.assertEqual(stats["air_selection_production_days"], 7)
        self.assertEqual(stats["air_selection_diagnostic_ops"], 3000)
        self.assertEqual(stats["air_selection_diagnostic_days"], 2)
        self.assertEqual(stats["air_selection_externality_ops"], 5000)
        self.assertEqual(stats["air_selection_relaxation_ops"], 4000)
        self.assertEqual(stats["air_selection_ranking_ops"], 3000)
        self.assertEqual(stats["air_selection_externality_days"], 2)
        self.assertEqual(stats["air_selection_relaxation_days"], 1)
        self.assertEqual(stats["air_selection_ranking_days"], 1)
        self.assertEqual(stats["air_selection_prepare_ops"], 700)
        self.assertEqual(stats["air_selection_prepare_days"], 1)
        self.assertEqual(stats["air_selection_prepared_builds"], 4)
        self.assertEqual(stats["air_selection_prepared_hits"], 9)
        self.assertEqual(stats["air_selection_envelope_builds"], 6)
        self.assertEqual(stats["air_selection_envelope_hits"], 8)
        self.assertEqual(stats["air_selection_externality_cache_hits"], 11)
        self.assertEqual(stats["air_selection_diagnostic_prepare_ops"], 100)
        self.assertEqual(stats["air_selection_diagnostic_externality_ops"], 200)
        self.assertEqual(stats["air_selection_diagnostic_relaxation_ops"], 300)
        self.assertEqual(stats["air_selection_diagnostic_ranking_ops"], 400)
        self.assertEqual(stats["air_selection_diagnostic_prepare_days"], 1)
        self.assertEqual(stats["air_selection_diagnostic_externality_days"], 2)
        self.assertEqual(stats["air_selection_diagnostic_relaxation_days"], 3)
        self.assertEqual(stats["air_selection_diagnostic_ranking_days"], 4)
        self.assertEqual(stats["air_frontier_possibility_explored"], 50)
        self.assertEqual(stats["air_frontier_possibility_deferred"], 20)
        self.assertEqual(stats["air_frontier_possibility_materialized"], 30)
        self.assertEqual(stats["air_frontier_possibility_reactivated"], 7)
        self.assertEqual(stats["air_frontier_possibility_technical_rejected"], 4)
        self.assertEqual(stats["air_frontier_exploration_town_pool"], 24)
        self.assertEqual(stats["air_frontier_exploration_site_probe_budget"], 64)
        self.assertEqual(stats["air_frontier_continuation_physical_scans"], 321)
        self.assertEqual(stats["air_frontier_continuation_conflict_rejected"], 654)
        self.assertEqual(stats["air_frontier_continuation_bucket_visits"], 9876)
        self.assertEqual(stats["air_frontier_continuation_economic_revalues"], 87)
        self.assertEqual(stats["air_frontier_continuation_economic_cache_hits"], 43)
        self.assertEqual(stats["air_frontier_continuation_economic_profit_removed_k"], 912)
        self.assertEqual(stats["air_frontier_continuation_fleet_revalues"], 31)
        self.assertEqual(stats["air_frontier_continuation_fleet_cache_hits"], 17)
        self.assertEqual(stats["air_frontier_continuation_fleet_profit_removed_k"], 444)
        self.assertEqual(stats["air_frontier_capital_price_samples"], 12)
        self.assertEqual(stats["air_frontier_capital_price_positive_samples"], 10)
        self.assertEqual(stats["air_frontier_capital_price_bps_sum"], 18000)
        self.assertEqual(stats["air_frontier_capital_price_bps_max"], 2400)
        self.assertEqual(stats["air_frontier_capital_price_full_demand_k"], 9000)
        self.assertEqual(stats["air_frontier_capital_price_budget_k"], 3600)

    def test_selection_telemetry_is_published_with_probe_off(self):
        task_air = TASK_AIR.read_text(encoding="utf-8")
        builder = AIR.read_text(encoding="utf-8")
        projects = PROJECTS.read_text(encoding="utf-8")
        boundary = (
            '+ AIR_CAPITAL_FRONTIER_LEDGER.capitalPriceBudgetK);\n'
            '    }\n'
            '    if (AIR_CAPITAL_FRONTIER && AIR_BEST_EQUIPMENT) {\n'
            '      OpexSign(AIMap.GetTileIndex(28, 8), "CF16|"'
        )
        self.assertIn(boundary, task_air)
        self.assertIn('OpexSign(AIMap.GetTileIndex(38, 8), "CF26|"', task_air)
        self.assertNotIn(
            "if (AIR_CAPITAL_FRONTIER_PROBE)\n"
            "      AIR_CAPITAL_FRONTIER_LEDGER.possibilityExplored++;",
            builder,
        )
        self.assertIn(
            "if (usePossibilityCatalog) {\n"
            "    if (AIR_TOWN_POOL > AIR_CAPITAL_FRONTIER_LEDGER.explorationTownPool)",
            builder,
        )
        self.assertNotIn(
            "if (AIR_CAPITAL_FRONTIER_PROBE) AIR_CAPITAL_FRONTIER_LEDGER.possibilityReactivated++;",
            projects,
        )

    def test_shared_duel_reuses_frontier_and_physical_air_diagnostics(self):
        src = DUEL_BENCH.read_text(encoding="utf-8")
        section = src[src.index("def extract_company_record"):src.index("def keep")]
        self.assertIn("bench_v2.air_equipment_diagnostic_stats(chunks)", section)
        self.assertIn("bench_v2.observed_opcode_stats(chunks)", section)
        self.assertIn('"air_primary_vehicles"', section)
        self.assertIn('"air_airports"', section)
        self.assertIn('"air_passenger_capacity"', section)
        self.assertIn('"air_vehicle_book_value"', section)
        self.assertIn('air_capacities_by_cargo.get("0", 0)', section)
        self.assertIn("airport_slot_metrics(chunks)", src)

    def test_air_variant_identity_is_physical_not_economic(self):
        src = PROJECTS.read_text(encoding="utf-8")
        identity = src[
            src.index("function OpexAirProjectVariantIdentity"):
            src.index("function OpexCapitalFrontierProjectGroupKey")
        ]
        self.assertIn('"air_variant|route|"', identity)
        self.assertIn("stationA", identity)
        self.assertIn("stationB", identity)
        self.assertIn("anchorA", identity)
        self.assertIn("anchorB", identity)
        self.assertIn("airportType", identity)
        self.assertIn("plan.plane.id", identity)
        self.assertIn("plan.economics.planes", identity)
        self.assertIn("project.src > project.dst", identity)
        self.assertNotIn("profitAnnual", identity)
        self.assertNotIn("revenueAnnual", identity)
        self.assertNotIn("economicsDate", identity)
        self.assertNotIn("routesA", identity)
        self.assertNotIn("popA", identity)

    def test_air_variant_newer_economic_revision_replaces_old_object(self):
        src = PROJECTS.read_text(encoding="utf-8")
        remember = src[
            src.index("function OpexProjectRememberAll"):
            src.index("function OpexEarlySlotSelectionState")
        ]
        self.assertIn("local variantIdentity = OpexAirProjectVariantIdentity(project)", remember)
        self.assertIn("OpexAirProjectVariantIdentity(existing) != variantIdentity", remember)
        self.assertIn('local incomingRevision = ("economicsDate" in project)', remember)
        self.assertIn('local existingRevision = ("economicsDate" in existing)', remember)
        self.assertIn("if (incomingRevision >= existingRevision)", remember)
        self.assertIn("list[i] = project", remember)
        self.assertIn("stats.modeReplaced++", remember)
        variant_start = remember.index("if (variantIdentity != null)")
        self.assertLess(remember.index("return;", variant_start), remember.index("stats.modeAlternatives++"))

    def test_frontier_fleet_dispatch_refreshes_only_fleet_groups(self):
        projects = PROJECTS.read_text(encoding="utf-8")
        scheduler = (ROOT / "ai" / "OpexAI" / "scheduler_tasks.nut").read_text(encoding="utf-8")

        self.assertIn("function OpexFrontierRefreshFleetGroups", projects)
        refresh_start = projects.index("function OpexFrontierRefreshFleetGroups")
        refresh_end = projects.index("function OpexReselectProjects", refresh_start)
        refresh = projects[refresh_start:refresh_end]
        self.assertIn('key.slice(0, 6) == "fleet|"', refresh)
        self.assertIn("OpexProjectFromFleet(entry)", refresh)
        self.assertIn(
            "OpexFrontierFleetGroupEquivalent(projects.candidateGroups[key], freshGroups[key], true)",
            refresh,
        )
        equivalent = projects[
            projects.index("function OpexFrontierFleetProjectEquivalent"):
            projects.index("function OpexFrontierRefreshFleetGroups")
        ]
        self.assertNotIn('&& (("frontierRevision" in aa)', equivalent)
        self.assertIn("a.profitAnnual == b.profitAnnual", equivalent)
        self.assertIn("a.capitalCommitted == b.capitalCommitted", equivalent)
        self.assertIn("OpexProjectFinanceCapital(a) == OpexProjectFinanceCapital(b)", equivalent)
        self.assertIn(
            "current[i].payload.frontierRevision = candidate.payload.frontierRevision",
            equivalent,
        )
        self.assertNotIn("OpexAirPlans(", refresh)

        dispatch_start = scheduler.index("function OpexAI::_dispatchAirFleet")
        dispatch = scheduler[dispatch_start:]
        self.assertIn("OpexFrontierRefreshFleetGroups(this._projects, fleetPlan)", dispatch)
        self.assertIn('this._catalog, this._lines, "lifecycle"', dispatch)
        self.assertIn("OpexFrontierDropLambdaIfAbundant(this._projects, budgetNow)", dispatch)
        self.assertIn("OpexFrontierRefilterStoredScores(this._projects, budgetNow)", dispatch)
        budget_start = dispatch.index("} else if (budgetChanged) {")
        budget_end = dispatch.index("        }", budget_start)
        budget_path = dispatch[budget_start:budget_end]
        self.assertNotIn("OpexReselectProjects", budget_path)
        self.assertIn("OpexFrontierRefilterStoredScores", budget_path)
        frontier_start = dispatch.index("if (AIR_CAPITAL_FRONTIER && AIR_BEST_EQUIPMENT")
        frontier_end = dispatch.index("} else if (fleetPlan.len() > 0)", frontier_start)
        frontier = dispatch[frontier_start:frontier_end]
        self.assertNotIn("OpexIncrementalUpdateProjects", frontier)

    def test_frontier_budget_change_keeps_lambda_and_refilters_affordability(self):
        projects = PROJECTS.read_text(encoding="utf-8")
        relaxation = projects[
            projects.index("function OpexCapitalPriceRelaxationPrepared"):
            projects.index("/* Prix du capital du portefeuille.")
        ]
        refilter = projects[
            projects.index("function OpexFrontierRefilterStoredScores"):
            projects.index("function OpexFrontierDropLambdaIfAbundant")
        ]
        abundant = projects[
            projects.index("function OpexFrontierDropLambdaIfAbundant"):
            projects.index("function OpexProjectIsFreeAirRetirement")
        ]
        self.assertIn('selectionCache.rawset("coarseLambdaPct", lambdaPct)', relaxation)
        self.assertIn('selectionCache.rawset("coarseFullDemand", fullDemand)', relaxation)
        self.assertIn("OpexCapitalFrontierRank(alternatives, capitalBudget, PROJECT_TOP_K)", refilter)
        self.assertNotIn("OpexCapitalFrontierAssignScores", refilter)
        rank = projects[
            projects.index("function OpexCapitalFrontierRank"):
            projects.index("function OpexFrontierRefilterStoredScores")
        ]
        self.assertIn("OpexProjectFinanceCapital(project) > capitalBudget", rank)
        self.assertIn("local winners = {}", rank)
        self.assertIn("local group = OpexCapitalFrontierProjectGroupKey(project)", rank)
        self.assertIn("winners.rawset(group, project)", rank)
        self.assertIn("foreach (group, project in winners)", rank)
        self.assertIn("candidates.append(project)", rank)
        self.assertLess(rank.index("foreach (group, project in winners)"), rank.index("order.Sort("))
        self.assertIn("capitalBudget < cache.coarseFullDemand", abundant)
        self.assertIn('project.rawset("frontierCapitalPrice", 0.0)', abundant)
        self.assertIn('project.rawset("frontierScoreInt", ownProfit)', abundant)
        self.assertNotIn("OpexCapitalPriceRelaxationPrepared", abundant)

        task_projects = TASK_PROJECTS.read_text(encoding="utf-8")
        fresh_start = task_projects.index("if (PORTFOLIO_FRESH_BUDGET && this._projects != null)")
        fresh_end = task_projects.index("c49Best =", fresh_start)
        fresh = task_projects[fresh_start:fresh_end]
        self.assertIn("if (AIR_CAPITAL_FRONTIER && AIR_BEST_EQUIPMENT)", fresh)
        self.assertIn("OpexFrontierDropLambdaIfAbundant(this._projects, budgetNow)", fresh)
        self.assertIn("OpexFrontierRefilterStoredScores(this._projects, budgetNow)", fresh)
        frontier_start = fresh.index("if (AIR_CAPITAL_FRONTIER && AIR_BEST_EQUIPMENT)")
        legacy_start = fresh.index("} else {", frontier_start)
        self.assertNotIn("OpexReselectProjects", fresh[frontier_start:legacy_start])
        self.assertIn("OpexFrontierRefilterStoredScores", fresh[frontier_start:legacy_start])

    def test_frontier_generation_materializes_air_independent_of_cash(self):
        projects = PROJECTS.read_text(encoding="utf-8")
        self.assertIn(
            "airPossibilities, priorAirPossibilities",
            projects,
        )
        self.assertNotIn("materializeBudget", projects)
        reselect = projects[
            projects.index("function OpexReselectProjects"):
            projects.index("function OpexProjectSelectionStats")
            if "function OpexProjectSelectionStats" in projects
            else projects.index("function OpexB6", projects.index("function OpexReselectProjects"))
        ]
        self.assertNotIn("OpexAirActivateDeferredPossibilities(", reselect)

    def test_frontier_retire_only_has_no_parallel_priority_policy(self):
        projects = PROJECTS.read_text(encoding="utf-8")
        selector = projects[
            projects.index("function OpexProjectSelectAffordable"):
            projects.index("function OpexProjectSelectionScore")
        ]
        insert = projects[
            projects.index("function OpexProjectInsert"):
            projects.index("function OpexLogVivier")
        ]
        self.assertIn("if (useCapitalFrontier && project.frontierScore < 0) continue", selector)
        self.assertNotIn(
            "project.frontierScore < 0\n        && !OpexProjectIsFreeAirRetirement(project)",
            selector,
        )
        self.assertIn(
            "local projectFreeRetire = !capitalProfitTie && OpexProjectIsFreeAirRetirement(project)",
            insert,
        )
        self.assertIn(
            "local priorFreeRetire = !capitalProfitTie && OpexProjectIsFreeAirRetirement(prior)",
            insert,
        )

    def test_incremental_air_cache_is_fresh_only_and_drops_stale_variants(self):
        src = PROJECTS.read_text(encoding="utf-8")
        incremental = src[
            src.index("function OpexIncrementalUpdateProjects"):
            src.index("function OpexProjectEmptyRoad")
        ]
        skip_old = incremental.index('if (p.mode == "air" && AIR_PORTFOLIO) continue;')
        fresh_gen = incremental.index(
            "OpexAirPlans(catalog, lines, 0, freshAirPlans, abandonedPairs, PAX_BAND_ALL"
        )
        fresh_insert = incremental.index("OpexProjectRememberAll(newWinners, p, stats)", fresh_gen)
        self.assertLess(skip_old, fresh_gen)
        self.assertLess(fresh_gen, fresh_insert)
        self.assertLess(skip_old, incremental.index("OpexIncrementalCandidateStillValid(p, lines"))
        self.assertIn(
            "airPossibilities, priorAirPossibilities",
            incremental,
        )


if __name__ == "__main__":
    unittest.main()
