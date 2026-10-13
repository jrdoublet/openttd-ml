#!/usr/bin/env python3
"""Tests pour V149 — débloquer le rail (stock de tracés prêts, worker, réparation, année AIR).

Couvre :
1. Contrats statiques : réglages (info.nut ↔ globals_pre.nut ↔ settings.nut), défaut 0,
   l'interrupteur maître arme la gate et le worker C80 (et la rotation du fret sauf ablation),
   capacité unique du stock, chaque point d'entrée gardé par V149_RAIL_PIPELINE, sauts du
   worker, file et compteur de réparations, retenue pendant l'année AIR, état non persisté.
2. Modèles Python des règles pures (capacité, échecs réparables, séparation des extrémités,
   plafond de réparations).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("unterminated " + name)


def _setting_block(name: str) -> str:
    info = _read("info.nut")
    start = info.index('name = "' + name + '"')
    return info[start:info.index("});", start)]


MIN_SEPARATION = 10


def capacity(pipeline: bool, size: int) -> int:
    """Modèle de OpexRailStockCapacity."""
    return size if pipeline else 1


def repairable(reason):
    """Modèle de OpexV149RepairableBuildFailure."""
    if reason is None:
        return False
    if reason in ("TRKFAIL", "TRACKFAIL", "STNFAIL", "STATIONFAIL", "DEPFAIL", "DEPOTFAIL",
                  "NOPATH", "OVERLAP"):
        return True
    return len(reason) >= 4 and reason[:4] == "SITE"


def manhattan(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def ends_close(a, b):
    """Modèle de OpexV149EndsClose (src/dst en coordonnées)."""
    return any(manhattan(x, y) < MIN_SEPARATION
               for x in (a["src"], a["dst"]) for y in (b["src"], b["dst"]))


def queue_repair(counts, queue, key, abandoned=False):
    """Modèle de _v149QueueRepair : 'cooldown', 'abandoned', 'queued' ou 'already'."""
    if counts.get(key, 0) >= 2:
        return "cooldown"
    if abandoned:
        return "abandoned"
    if key in queue:
        return "already"
    queue.append(key)
    return "queued"


class Settings(unittest.TestCase):
    def test_settings_declared_with_default_off(self):
        block = _setting_block("v149_rail_pipeline")
        self.assertIn("min_value = 0, max_value = 1", block)
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, key + r" = 0\b")
        for name, lo, hi, default in (("v149_stock_size", 1, 12, 4),
                                      ("v149_revalidate_days", 7, 180, 30),
                                      ("v149_freight_rotation", 0, 1, 1),
                                      ("v149_astar_share", 5, 100, 20)):
            block = _setting_block(name)
            self.assertIn("min_value = %d, max_value = %d" % (lo, hi), block, name)
            for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
                self.assertRegex(block, key + r" = %d\b" % default, name)
        globals_pre = _read("globals_pre.nut")
        for line in ("V149_RAIL_PIPELINE <- false;", "V149_STOCK_SIZE <- 4;",
                     "V149_REVALIDATE_DAYS <- 30;", "V149_FREIGHT_ROTATION <- true;",
                     "V149_ASTAR_SHARE <- 20;",
                     "V149_FIRST_YEAR <- -1;"):
            self.assertIn(line, globals_pre)

    def test_master_switch_forces_c80_and_rotation(self):
        settings = _read("settings.nut")
        self.assertIn('V149_RAIL_PIPELINE = AIController.GetSetting("v149_rail_pipeline") > 0;', settings)
        self.assertRegex(settings, r'local v149Size = AIController\.GetSetting\("v149_stock_size"\);\s*'
                                   r'if \(v149Size >= 1\) V149_STOCK_SIZE = v149Size;')
        self.assertRegex(settings, r'local v149Days = AIController\.GetSetting\("v149_revalidate_days"\);\s*'
                                   r'if \(v149Days >= 1\) V149_REVALIDATE_DAYS = v149Days;')
        self.assertRegex(settings, r'local v149Share = AIController\.GetSetting\("v149_astar_share"\);\s*'
                                   r'if \(v149Share >= 1\) V149_ASTAR_SHARE = v149Share;')
        block = settings[settings.index("  if (V149_RAIL_PIPELINE) {"):]
        block = block[:block.index("  }\n") + 4]
        self.assertIn("C80_RAIL_STOCK_GATE = true;", block)
        self.assertIn("C80_RAIL_STOCK_WORKER = true;", block)
        # la rotation C76 n'est plus forcee : V149 regenere lui-meme le vivier rail
        self.assertNotIn("C76_FREIGHT_ROTATION", block)
        # le forcage precede la coupure de V89 par le worker C80
        self.assertLess(settings.index("  if (V149_RAIL_PIPELINE) {"),
                        settings.index("if (C80_RAIL_STOCK_WORKER) V89_RAIL_SEARCH_THROUGHPUT = false;"))
        # et suit les lectures historiques qu'il ecrase
        self.assertGreater(settings.index("  if (V149_RAIL_PIPELINE) {"),
                           settings.index('C76_FREIGHT_ROTATION = C76_REGEN_TARGETED && (AIController.GetSetting("c76_freight_rotation") != 0);'))


class StockCapacity(unittest.TestCase):
    def test_single_capacity_function(self):
        body = _function_body(_read("rail_v149.nut"), "OpexRailStockCapacity")
        self.assertIn("return V149_RAIL_PIPELINE ? V149_STOCK_SIZE : 1;", body)

    def test_no_hardcoded_stock_size_left(self):
        for name in ("task_rail.nut", "orchestrator.nut", "task_projects.nut"):
            src = _read(name)
            self.assertNotRegex(src, r"_railReadyStock\.len\(\) (>= 1|< 1)\b", name)
        self.assertIn("if (this._railReadyStock.len() >= OpexRailStockCapacity()) return false;",
                      _function_body(_read("task_rail.nut"), "OpexAI::_tryStartRailStockWorker"))
        self.assertIn("if (ai._railReadyStock.len() < OpexRailStockCapacity()) {",
                      _function_body(_read("orchestrator.nut"), "OpexWorkerRailStockCancel"))
        self.assertEqual(_read("task_projects.nut").count(
            "this._railReadyStock.len() < OpexRailStockCapacity()"), 2)

    def test_model(self):
        self.assertEqual(capacity(False, 4), 1)
        self.assertEqual(capacity(True, 4), 4)
        self.assertEqual(capacity(True, 12), 12)


class WorkerChoice(unittest.TestCase):
    def test_worker_order_repairs_first_then_skips(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_tryStartRailStockWorker")
        v149 = body.index("if (V149_RAIL_PIPELINE) {")
        self.assertLess(body.index("if (this._railSearch != null) return false;"), v149)
        self.assertIn("if (this._v149AirYearActive() && this._c121RailPrepAirFundableCheap()) return false;", body)
        self.assertIn("if (this._v149StartRepair()) return true;", body)
        self.assertLess(v149, body.index("foreach (candidate in railCandidates)"))
        # le saut V149 vient apres le seuil historique, juste avant la recherche
        skip = body.index("if (V149_RAIL_PIPELINE && this._v149WorkerSkip(candidate)) continue;")
        self.assertLess(body.index("coarseFundScore < threshold"), skip)
        self.assertLess(skip, body.index("return this._startRailStockSearch(candidate, false, null, coarseFundScore);"))

    def test_skip_rules(self):
        src = _read("rail_v149.nut")
        body = _function_body(src, "OpexAI::_v149WorkerSkip")
        self.assertIn("local close = this._tooClose(candidate);", body)
        self.assertIn("if (close.hard >= 0 || close.blocking >= 0) {", body)
        self.assertIn("if (this._v149NearStocked(candidate)) {", body)
        near = _function_body(src, "OpexAI::_v149NearStocked")
        self.assertIn("foreach (pairKey, entry in this._railReadyStock)", near)
        self.assertIn("foreach (item in this._v149RepairQueue)", near)
        close = _function_body(src, "OpexV149EndsClose")
        self.assertEqual(close.count("< MIN_SEPARATION"), 4)

    def test_ends_close_model(self):
        a = {"src": (10, 10), "dst": (60, 10)}
        self.assertTrue(ends_close(a, {"src": (10, 10), "dst": (10, 80)}))    # meme origine
        self.assertTrue(ends_close(a, {"src": (20, 50), "dst": (64, 14)}))    # 8 tuiles
        self.assertFalse(ends_close(a, {"src": (20, 50), "dst": (65, 15)}))   # 10 tuiles
        self.assertFalse(ends_close(a, {"src": (30, 40), "dst": (90, 90)}))


class Repair(unittest.TestCase):
    def test_queue_caps_two_repairs_and_respects_abandon(self):
        body = _function_body(_read("rail_v149.nut"), "OpexAI::_v149QueueRepair")
        self.assertIn("if (count >= 2) {", body)
        self.assertIn("this._railStockCooldown[pairKey] <- AIDate.GetCurrentDate() + 365;", body)
        self.assertIn("(OpexAbandonedPairKey(candidate) in this._abandonedPairs)", body)
        self.assertLess(body.index("if (count >= 2) {"), body.index("this._v149RepairQueue.append("))

    def test_start_repair_counts_and_runs_fresh_astar(self):
        body = _function_body(_read("rail_v149.nut"), "OpexAI::_v149StartRepair")
        self.assertIn("local item = this._v149RepairQueue.remove(0);", body)
        self.assertIn("this._v149RepairCount[item.key] <- count;", body)
        self.assertIn('if ("railPlan" in cand) cand.railPlan = null;', body)
        self.assertIn("if (this._startRailStockSearch(cand, true, item.reason)) return true;", body)
        self.assertLess(body.index("local close = this._tooClose(cand);"),
                        body.index("this._v149RepairCount[item.key] <- count;"))

    def test_repair_model(self):
        counts, queue = {}, []
        self.assertEqual(queue_repair(counts, queue, "k"), "queued")
        self.assertEqual(queue_repair(counts, queue, "k"), "already")
        queue.clear()
        counts["k"] = 2
        self.assertEqual(queue_repair(counts, queue, "k"), "cooldown")
        self.assertEqual(queue_repair({}, [], "s", abandoned=True), "abandoned")

    def test_repairable_build_failures(self):
        body = _function_body(_read("rail_v149.nut"), "OpexV149RepairableBuildFailure")
        for reason in ("TRKFAIL", "TRACKFAIL", "STNFAIL", "STATIONFAIL", "DEPFAIL", "DEPOTFAIL",
                       "NOPATH", "OVERLAP"):
            self.assertIn('"' + reason + '"', body)
        self.assertIn('reason.slice(0, 4) == "SITE"', body)
        for reason in ("TRKFAIL", "SITEA", "SITEAB", "STNFAIL"):
            self.assertTrue(repairable(reason), reason)
        for reason in ("CASH", "ECON", "NOWAGON", "TRAINFAIL", "", None, "SIT"):
            self.assertFalse(repairable(reason), reason)

    def test_build_failure_goes_to_repair_not_cooldown(self):
        body = _function_body(_read("rail_v149.nut"), "OpexAI::_v149AfterBuildAttempt")
        self.assertIn("delete this._railReadyStock[pairKey];", body)
        self.assertIn("if (OpexV149RepairableBuildFailure(reason)) {", body)
        self.assertIn('this._v149QueueRepair(candidate, pairKey, "build_" + reason);', body)
        build = _function_body(_read("task_rail.nut"), "OpexAI::_tryBuildRailProject")
        hook = build.index("if (V149_RAIL_PIPELINE) this._v149AfterBuildAttempt(candidate, result, recorded);")
        self.assertLess(build.index("local recorded = this._recordRailAttempt(candidate, result, posPacked, year);"), hook)
        # avant le nettoyage de preparation C121 et le retrait historique de 365 jours (C80)
        self.assertLess(hook, build.index("if (c121PrepPlan && candidate != null && this._railReadyStock != null"))

    def test_revalidate_at_build_queues_instead_of_immediate_astar(self):
        build = _function_body(_read("task_rail.nut"), "OpexAI::_tryBuildRailProject")
        v149 = build.index("} else if (V149_RAIL_PIPELINE) {")
        rule3 = build.index("local started = this._startRailStockSearch(candidate, true, reval.reason);")
        self.assertLess(v149, rule3)
        self.assertIn("this._v149OnRevalidateFail(candidate, reval.reason);", build[v149:rule3])
        self.assertIn("if (V149_RAIL_PIPELINE) this._v149OnRevalidateFail(candidate, reval.reason);", build)
        self.assertIn('if (V149_RAIL_PIPELINE && reval.reason == "no_vehicle_slot") {', build)
        self.assertEqual(build.count("if (V149_RAIL_PIPELINE) this._v149DropTooClose(candidate);"), 2)


class Revalidation(unittest.TestCase):
    def test_periodic_revalidation_and_safety_ttl(self):
        src = _read("rail_v149.nut")
        body = _function_body(src, "OpexAI::_v149RevalidateStock")
        self.assertIn("if (curDate < this._v149NextRevalidate) return;", body)
        self.assertIn("this._v149NextRevalidate = curDate + V149_REVALIDATE_DAYS;", body)
        self.assertIn("curDate - entry.readyDate > 365", body)
        tiles = _function_body(src, "OpexAI::_v149RevalidateTiles")
        # ni caisse ni place vehicule : testees a la pose
        self.assertNotIn("GetBankBalance", tiles)
        self.assertNotIn("OpexRailVehicleSlotAvailable", tiles)
        for token in ("AITestMode()", "AIRail.BuildRailStation", "OpexTestRailTrack",
                      "AIRail.BuildRailDepot", '"industry_closed"', '"too_close"'):
            self.assertIn(token, tiles)
        drop = _function_body(src, "OpexAI::_v149DropStockEntry")
        self.assertIn('this._v149QueueRepair(cand, pairKey, reason);', drop)
        self.assertIn('reason == "industry_closed" || reason == "too_close"', drop)

    def test_historic_expiry_replaced(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_checkRailStockExpiry")
        lines = body.splitlines()
        self.assertIn("if (V149_RAIL_PIPELINE) return;", lines[3])


class AirYear(unittest.TestCase):
    def test_same_first_year_test_as_prep(self):
        src = _read("rail_v149.nut")
        body = _function_body(src, "OpexV149AirYear")
        self.assertIn("if (C121_CATALOG_FIRST_YEAR_ACTIVE) return true;", body)
        self.assertIn("AIDate.GetYear(AIDate.GetCurrentDate()) == V149_FIRST_YEAR", body)
        self.assertIn("V149_FIRST_YEAR = (this._generationStageMonth - 1) / 12;",
                      _function_body(src, "OpexAI::_v149AirYearActive"))

    def test_held_at_build_and_out_of_selection(self):
        build = _function_body(_read("task_rail.nut"), "OpexAI::_tryBuildRailProject")
        gate = build.index("      if (C80_RAIL_STOCK_GATE) {")
        hold = build.index("if (V149_RAIL_PIPELINE && this._v149AirYearActive()) {")
        self.assertLess(gate, hold)
        self.assertLess(hold, build.index("local pairKey", gate))
        self.assertIn('reason = "v149_air_year_held"', build)
        sel = _function_body(_read("projects_generation.nut"), "OpexFilterRailStockGate")
        self.assertIn("&& !(V149_RAIL_PIPELINE && OpexV149AirYear())) {", sel)

    def test_worker_yields_to_fundable_air(self):
        step = _function_body(_read("orchestrator.nut"), "OpexWorkerRailStockStep")
        self.assertIn("if (V149_RAIL_PIPELINE && !prepSearch && ai._railSearch.phase == \"search\"\n"
                      "      && ai._v149AirYearActive() && ai._c121RailPrepAirFundableCheap()) {", step)
        self.assertLess(step.index("ai._v149AirYearActive()"), step.index("ai._checkRailStockExpiry();"))


class RailRegen(unittest.TestCase):
    def test_rail_only_regen_outside_catalog(self):
        src = _read("rail_v149.nut")
        body = _function_body(src, "OpexAI::_v149MaybeRegenRail")
        self.assertIn("if (!V149_FREIGHT_ROTATION || !this._v149WorkerDry) return;", body)
        self.assertIn("if (ym == this._v149RegenMonth) return;", body)
        self.assertIn("if (this._v149AirYearActive() && month < 10) return;", body)
        self.assertIn('this._projects.rawset("freightCargo", freightCargos[nextCargo]);', body)
        self.assertIn('this._lines, this._abandonedPairs, "rail", null, null, -1);', body)
        self.assertNotIn('"road"', body)
        self.assertIn("this._ranked = this._projects.rail;", body)
        # avant la revalidation et donc avant le demarrage du worker en fin de passe
        after = _function_body(src, "OpexAI::_v149AfterProjectsPass")
        self.assertLess(after.index("this._v149MaybeRegenRail();"), after.index("this._v149RevalidateStock(curDate);"))
        self.assertIn("  _v149RegenMonth = -1;", _read("main.nut"))

    def test_regen_only_when_worker_dry_and_idle(self):
        src = _read("rail_v149.nut")
        body = _function_body(src, "OpexAI::_v149MaybeRegenRail")
        self.assertIn("if (this._activeWorker != null || this._railSearch != null\n"
                      "      || this._railReadyStock.len() >= OpexRailStockCapacity()) return;", body)
        # un vivier remplace depuis (reconstruction complete) doit d'abord etre parcouru
        self.assertIn("if (pool != this._v149DryPool) {\n    this._v149WorkerDry = false;\n    return;", body)
        self.assertLess(body.index("pool != this._v149DryPool"), body.index("this._v149RegenMonth = ym;"))
        # le worker retente sur le vivier neuf
        self.assertLess(body.index("OpexRegenerateModeProjects("), body.index("this._v149WorkerDry = false;\n  if (freightCargos"))
        dry = _function_body(src, "OpexAI::_v149MarkDry")
        self.assertIn("this._v149WorkerDry = true;", dry)
        self.assertIn("this._v149DryPool = ", dry)
        main = _read("main.nut")
        for line in ("  _v149WorkerDry = true;", "  _v149DryPool = null;", "  function _v149MarkDry();"):
            self.assertIn(line, main)

    def test_worker_marks_dry_on_exhaustion_and_clears_on_start(self):
        start = _function_body(_read("task_rail.nut"), "OpexAI::_tryStartRailStockWorker")
        self.assertEqual(start.count("if (V149_RAIL_PIPELINE) this._v149MarkDry();"), 2)
        self.assertIn("if (V149_RAIL_PIPELINE) this._v149WorkerDry = false;\n"
                      "    return this._startRailStockSearch(candidate, false, null, coarseFundScore);", start)
        # le second marquage est apres la boucle des candidats
        self.assertGreater(start.rindex("this._v149MarkDry();"), start.index("foreach (candidate in railCandidates)"))

    def test_regen_without_pax(self):
        body = _function_body(_read("rail_v149.nut"), "OpexAI::_v149MaybeRegenRail")
        on = body.index("V149_REGEN_NO_PAX = true;")
        call = body.index("OpexRegenerateModeProjects(")
        off = body.index("V149_REGEN_NO_PAX = false;")
        self.assertLess(on, call)
        self.assertLess(call, off)
        self.assertIn("V149_REGEN_NO_PAX <- false;", _read("globals_pre.nut"))
        gen = _function_body(_read("projects_generation.nut"), "OpexGenerateModeProjects")
        self.assertIn('local generatePax = (!targeted || entityKind == "town") && !V149_REGEN_NO_PAX;', gen)

    def test_air_minimum_refreshed_weekly(self):
        after = _function_body(_read("rail_v149.nut"), "OpexAI::_v149AfterProjectsPass")
        self.assertIn("curDate >= this._v149NextAirMin", after)
        self.assertLess(after.index("this._v149NextAirMin = curDate + 7;"), after.index("this._c121CheapestLivingAirCap();"))
        self.assertIn("  _v149NextAirMin = -1;", _read("main.nut"))


class AirCatalogShare(unittest.TestCase):
    def test_catalog_continuation_unchanged_at_default(self):
        # le predicat historique et la boucle de main.nut restent intacts ; V149 poursuit apres
        body = _function_body(_read("scheduler_tasks.nut"), "OpexC121CatalogCanContinue")
        self.assertIn("return C121_CATALOG_INCREMENTAL && owner._activeWorker == null", body)
        main = _read("main.nut")
        loop = main.index("while (catalogPending && OpexC121CatalogCanContinue(this, continuationTick))")
        hook = main.index("if (V149_RAIL_PIPELINE) this._v149ContinueCatalog(continuationTick);")
        self.assertLess(loop, hook)
        self.assertLess(hook, main.index("if (spResume != null) OpexSpanEnd(spResume);"))
        v149 = _read("rail_v149.nut")
        pred = _function_body(v149, "OpexV149CatalogCanContinue")
        self.assertIn("if (!C121_CATALOG_INCREMENTAL || owner._railExpansion != null) return false;", pred)
        self.assertIn("&& !OpexV149CatalogMayPassRail(owner)) return false;", pred)
        self.assertIn("AIController.GetOpsTillSuspend() > 2000;", pred)
        cont = _function_body(v149, "OpexAI::_v149ContinueCatalog")
        self.assertIn("while (catalogPending && OpexV149CatalogCanContinue(this, continuationTick)) {", cont)
        self.assertIn("if (catalogPending) this._runOrchestratorTick();", cont)

    def test_only_stock_searches_let_the_catalog_pass(self):
        body = _function_body(_read("rail_v149.nut"), "OpexV149CatalogMayPassRail")
        self.assertIn('if (owner._activeWorker != null && owner._activeWorker.kind != "rail_stock") return false;', body)
        self.assertIn('return search == null || (("isStockSearch" in search) && search.isStockSearch);', body)
        busy = _function_body(_read("rail_v149.nut"), "OpexV149AirCatalogBusy")
        self.assertIn('if (t.name == "catalog") return ("c78AirRebuild" in t) && t.c78AirRebuild != null;', busy)

    def test_no_drain_while_air_catalog_busy(self):
        step = _function_body(_read("orchestrator.nut"), "OpexWorkerRailStockStep")
        self.assertIn("local v149NoDrain = V149_RAIL_PIPELINE && OpexV149AirCatalogBusy(ai);", step)
        self.assertIn("while (!v149NoDrain && ai._railSearch != null", step)
        # la premiere tranche reste jouee
        self.assertLess(step.index("ai._advanceRailSearchSliceWithLedgers();"), step.index("v149NoDrain"))


def next_astar_tick(now, dt, share):
    """Modele du plafond V149 : tick a partir duquel la tranche suivante peut jouer."""
    dt = max(1, dt)
    return now + dt * (100 - share) // share


class AstarShare(unittest.TestCase):
    def test_cap_before_first_slice_after_timeout(self):
        step = _function_body(_read("orchestrator.nut"), "OpexWorkerRailStockStep")
        self.assertIn("local v149Cap = V149_RAIL_PIPELINE && V149_ASTAR_SHARE < 100 && "
                      "ai._railSearch.phase == \"search\"\n      && OpexV149AirCatalogBusy(ai);", step)
        self.assertIn('if (v149Cap && AIController.GetTick() < ai._v149RailNextTick) return "running";', step)
        self.assertIn("ai._v149RailNextTick = v149Now + v149Dt * (100 - V149_ASTAR_SHARE) / V149_ASTAR_SHARE;", step)
        # le delai de 180 jours reste verifie avant le plafond, la tranche suit le plafond
        self.assertLess(step.index("ai._handleRailStockSearchTimeout();"), step.index("local v149Cap"))
        self.assertLess(step.index('ai._v149RailNextTick) return "running";'),
                        step.index("ai._advanceRailSearchSliceWithLedgers();"))
        main = _read("main.nut")
        self.assertIn("_v149RailNextTick = 0;", main)

    def test_model(self):
        # 20 % : une tranche de 10 ticks (finie au tick 1000) en libere 40 ; part = dt / (dt + attente)
        self.assertEqual(next_astar_tick(1000, 10, 20), 1040)
        for share in (5, 10, 20, 50):
            wait = next_astar_tick(0, 10, share)
            self.assertAlmostEqual(10 / (10 + wait), share / 100, places=2)
        self.assertEqual(next_astar_tick(7, 0, 20), 11)
        self.assertEqual(next_astar_tick(7, 3, 100), 7)


class ForcedReselect(unittest.TestCase):
    def test_reselect_only_when_stock_changes(self):
        body = _function_body(_read("projects_selection.nut"), "OpexPromoteLiveDefensiveAirStock")
        self.assertIn("local v149Sig = V149_RAIL_PIPELINE ? OpexV149RailStockSignature(ai._railReadyStock) : null;", body)
        self.assertIn("if (v149Sig != null && v149Sig == ai._v149StockSig) {\n      OpexEnsureSelection(ai);", body)
        self.assertIn("if (v149Sig != null) ai._v149StockSig = v149Sig;", body)
        # hors V149, la reselection forcee historique est intacte
        self.assertIn("      OpexReselectProjects(projects, capitalBudget, ai._abandonedPairs, ai._lines, ai._railReadyStock);", body)
        self.assertIn("_v149StockSig = null;", _read("main.nut"))

    def test_signature_is_order_free(self):
        sig = _function_body(_read("rail_v149.nut"), "OpexV149RailStockSignature")
        self.assertIn('if (stock == null) return "-";', sig)
        self.assertIn("keys.sort();", sig)
        self.assertIn('local sig = "" + keys.len();', sig)


class Pipeline(unittest.TestCase):
    def test_projects_pass_hooks(self):
        src = _read("task_projects.nut")
        self.assertEqual(src.count("if (V149_RAIL_PIPELINE) this._v149AfterProjectsPass();"), 2)
        for m in re.finditer(r"if \(V149_RAIL_PIPELINE\) this\._v149AfterProjectsPass\(\);\n", src):
            nxt = src[m.end():m.end() + 200]
            self.assertTrue(nxt.lstrip().startswith("if (C80_RAIL_STOCK_GATE && C80_RAIL_STOCK_WORKER"))
        consume = _function_body(src, "OpexAI::_consumeResumableRailAtPassStart")
        self.assertIn('if (V149_RAIL_PIPELINE && ("isStockSearch" in this._railSearch) && this._railSearch.isStockSearch) {',
                      consume)
        self.assertLess(consume.index("isStockSearch"), consume.index("this._consumeRailSearch(year)"))

    def test_deposit_expedites_projects(self):
        rail = _read("task_rail.nut")
        done = _function_body(rail, "OpexAI::_handleRailStockSearchCompleted")
        self.assertIn("if (V149_RAIL_PIPELINE) this._v149OnDeposit(candidate, readyFundScore, isRepair);", done)
        src = _read("rail_v149.nut")
        dep = _function_body(src, "OpexAI::_v149OnDeposit")
        self.assertLess(dep.index("if (this._v149AirYearActive()) return;"), dep.index("this._v149ExpediteProjects();"))
        self.assertIn("candidate.capital + OpexCashReserve()", dep)
        exp = _function_body(src, "OpexAI::_v149ExpediteProjects")
        self.assertIn('this._projects.rawset("selectionStale", true);', exp)
        self.assertIn("if (t.enabled && i < this._taskCursor) {", exp)
        self.assertIn("t.dueCycle = this._taskCycle;", exp)

    def test_timeout_does_not_orphan_a_search(self):
        body = _function_body(_read("task_rail.nut"), "OpexAI::_handleRailStockSearchTimeout")
        v149 = body.index("if (V149_RAIL_PIPELINE) {")
        self.assertLess(v149, body.rindex("this._tryStartRailStockWorker();"))
        self.assertIn("return;", body[v149:body.rindex("this._tryStartRailStockWorker();")])

    def test_c77_entity_runs_sync_beside_stock_worker(self):
        src = _read("orchestrator.nut")
        self.assertIn('|| (V149_RAIL_PIPELINE && this._activeWorker.kind == "rail_stock")) {', src)

    def test_state_is_transient(self):
        main = _read("main.nut")
        self.assertIn('require("rail_prep_c121.nut");\nrequire("rail_v149.nut");', main)
        persist = _read("persist.nut")
        for line in ("this._v149RepairQueue = [];", "this._v149RepairCount = {};",
                     "this._v149NextRevalidate = -1;"):
            self.assertIn(line, persist)
            self.assertIn("    " + line, main)
        save = _function_body(persist, "OpexAI::Save")
        self.assertNotIn("v149", save.lower())

    def test_logs_only_under_decision_log(self):
        src = _read("rail_v149.nut")
        log = _function_body(src, "OpexV149Log")
        self.assertIn("if (!DECISION_LOG) return;", log.splitlines()[2])
        self.assertIn('OpexDecide("V149_STOCK", "action="', log)
        month = _function_body(src, "OpexAI::_v149AfterProjectsPass")
        self.assertIn("if (DECISION_LOG) {", month)
        self.assertIn('OpexDecide("V149_STOCK_MONTH", "size="', month)

    def test_every_v149_hook_is_gated(self):
        # hors de rail_v149.nut, chaque appel a une methode V149 est derriere la globale
        # (sur la ligne, ou dans un bloc ouvert par elle au plus 3 lignes plus haut)
        for name in ("task_rail.nut", "task_projects.nut", "orchestrator.nut", "projects_generation.nut"):
            lines = _read(name).splitlines()
            for i, line in enumerate(lines):
                if re.search(r"_v149[A-Z]\w*\(|OpexV149\w*\(", line):
                    window = "\n".join(lines[max(0, i - 3):i + 1])
                    self.assertIn("V149_RAIL_PIPELINE", window, name + ": " + line.strip())


if __name__ == "__main__":
    unittest.main()
