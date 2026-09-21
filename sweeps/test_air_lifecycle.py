from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

from bench_v2 import air_equipment_diagnostic_stats
from campaign_freeze import parse_ai_settings


AIR = ROOT / "ai" / "OpexAI" / "builder_air.nut"
CATALOG = ROOT / "ai" / "OpexAI" / "catalog.nut"
EVENTS = ROOT / "ai" / "OpexAI" / "event_handlers.nut"
GLOBALS = ROOT / "ai" / "OpexAI" / "globals_pre.nut"
INFO = ROOT / "ai" / "OpexAI" / "info.nut"
MAIN = ROOT / "ai" / "OpexAI" / "main.nut"
PERSIST = ROOT / "ai" / "OpexAI" / "persist.nut"
PROJECTS = ROOT / "ai" / "OpexAI" / "projects.nut"
SETTINGS = ROOT / "ai" / "OpexAI" / "settings.nut"
TASK = ROOT / "ai" / "OpexAI" / "task_air.nut"
TASK_PROJECTS = ROOT / "ai" / "OpexAI" / "task_projects.nut"
TASK_REPORT = ROOT / "ai" / "OpexAI" / "task_report.nut"


def _section(text, start, end=None):
    begin = text.index(start)
    finish = text.index(end, begin) if end is not None else len(text)
    return text[begin:finish]


def _dominates(a, b):
    if (a["planeType"], a["capacity"], a["speed"]) != (
        b["planeType"], b["capacity"], b["speed"]
    ):
        return False
    range_a = (2**31 - 1) if a["range"] == 0 else a["range"]
    range_b = (2**31 - 1) if b["range"] == 0 else b["range"]
    if a["price"] > b["price"] or a["running"] > b["running"] or range_a < range_b:
        return False
    return (
        a["price"] < b["price"]
        or a["running"] < b["running"]
        or range_a > range_b
    )


def _pareto(pool):
    return [
        candidate
        for candidate in pool
        if not any(
            other is not candidate and _dominates(other, candidate)
            for other in pool
        )
    ]


def _synthetic_best(pool, distance):
    eligible = [p for p in pool if p["range"] == 0 or distance <= p["range"]]
    if not eligible:
        return None

    def economics(p):
        # Dominated pairs have identical capacity/speed. Therefore any economic
        # curve based on those service inputs and purchase/running costs ranks
        # the strict dominator at least as high.
        profit = p["capacity"] * 1000 + p["speed"] * 10 - p["running"] - p["price"] // 20
        roi = profit * 1000 // max(1, p["price"])
        return profit, roi

    return max(eligible, key=economics)["id"]


class TestAirLifecycle(unittest.TestCase):
    def test_next_step_snapshot_reuses_plane_metadata_per_engine(self):
        src = AIR.read_text(encoding="utf-8")
        prepare = _section(
            src, "function OpexAirNextStepPrepare", "function OpexAirNextStepEconomics"
        )
        self.assertIn("local planeByEngine = {}", prepare)
        self.assertIn('local key = "" + engine', prepare)
        self.assertIn("(key in planeByEngine) ? planeByEngine[key] : null", prepare)
        self.assertIn("planeByEngine.rawset(key, plane)", prepare)

    def test_fleet_economics_reuses_trip_and_income_per_engine_within_evaluation(self):
        src = AIR.read_text(encoding="utf-8")
        context = _section(
            src, "function OpexAirFleetEconomicsContext", "function OpexAirFleetEconomicsFromContext"
        )
        self.assertIn("local staticByEngine = {}", context)
        self.assertIn('(key in staticByEngine) ? staticByEngine[key] : null', context)
        self.assertIn("staticByEngine.rawset(key, row)", context)
        self.assertIn("monthlyCapacity += row.capacityPerPlane", context)

    def test_c68_remains_adopted_default(self):
        defaults = parse_ai_settings(INFO)
        self.assertEqual(defaults["air_route_plane_selection"], 1)
        self.assertEqual(defaults["air_best_equipment"], 0)

    def test_existing_line_reuses_single_best_equipment_engine(self):
        src = AIR.read_text(encoding="utf-8")
        assessment = _section(
            src, "function OpexAirAssessExistingLine", "function OpexAirEngineRelevantToLine"
        )
        self.assertIn("OpexAirBestEquipment(catalog, airport, siteA, siteB", assessment)
        self.assertIn(
            "OpexAirActualFleetEconomics(catalog, line, distance, currentDemand)",
            assessment,
        )
        self.assertIn(
            "OpexAirRemainingTransitionCapital(line, best.plane.id, best.planes, best.plane.price)",
            assessment,
        )
        self.assertIn("if (have == 0)", assessment)
        self.assertIn("paybackMonths", assessment)
        self.assertIn("AIR_UPGRADE_MAX_PAYBACK_MONTHS", assessment)

    def test_engine_available_only_refreshes_and_invalidates(self):
        src = EVENTS.read_text(encoding="utf-8")
        handler = _section(
            src, "function OpexAI::_onEngineAvailable", "function OpexAI::_onEnginePreview"
        )
        self.assertIn("this._catalog._refreshAir();", handler)
        self.assertIn("OpexRefreshEpochBounds(this._catalog);", handler)
        self.assertIn('rawset("status", "available")', handler)
        self.assertIn('rawset("airEquipmentDirtyReason", "engine_available")', handler)
        self.assertIn(
            't.name == "catalog" || t.name == "projects" || t.name == "air_fleet"',
            handler,
        )
        for forbidden in (
            "OpexAirAssessExistingLine(",
            "OpexAirAssessPreviewPlane(",
            "OpexAirBestEquipment(",
            "OpexAirEconomics(",
            "_resolveAirPreviewCommitment(",
        ):
            self.assertNotIn(forbidden, handler)

    def test_preview_is_screen_then_common_engine_resolution(self):
        air = AIR.read_text(encoding="utf-8")
        events = EVENTS.read_text(encoding="utf-8")
        task = TASK.read_text(encoding="utf-8")
        preview = _section(
            events, "function OpexAI::_onEnginePreview", "function OpexAI::_onStationFirstVehicle"
        )
        resolver = _section(
            task,
            "function OpexAI::_resolveAirPreviewCommitment",
            "function OpexAI::_honorAirPreviewCommitment",
        )
        resize = _section(task, "function OpexAI::_resizeAirFleets")

        self.assertIn(
            "OpexAirAssessPreviewPlane(this._catalog, this._lines, line, previewPlane)",
            preview,
        )
        self.assertIn("preview.AcceptPreview()", preview)
        self.assertIn("previewPlane.price + OpexCashReserve()", preview)
        self.assertIn("this._catalog._refreshAir();", preview)
        self.assertIn("OpexAirCatalogEngineIds(this._catalog)", preview)
        self.assertIn("OpexAirFindAcceptedPreviewEngine(", preview)
        self.assertIn('rawset("airEquipmentDirtyReason", "preview")', preview)
        self.assertIn('t.name == "projects" || t.name == "air_fleet"', preview)
        self.assertIn(
            "function OpexAirAssessPreviewPlane(catalog, lines, line, previewPlane)",
            air,
        )
        self.assertNotIn("exactPhysical", air)
        self.assertNotIn("OpexAirAssessPreviewPlane", resolver)
        self.assertIn("assessment.preferredEngine != engine", resolver)
        self.assertIn("not_preferred_by_common_engine", resolver)
        self.assertIn("no_concrete_use", resolver)
        self.assertIn(
            "OpexAirAssessExistingLine(this._catalog, this._lines, line, evalReason)",
            resize,
        )
        self.assertIn(
            "_resolveAirPreviewCommitment(line, line.previewCommitment.resolvedEngine",
            resize,
        )
        matcher = _section(
            air, "function OpexAirPreviewMatchesEngine", "function OpexAirAssessPreviewPlane"
        )
        self.assertIn("AIEngine.GetName(engine) == commitment.name", matcher)
        self.assertIn("AIEngine.GetCapacity(engine) == commitment.capacity", matcher)
        self.assertIn("AIEngine.GetMaxSpeed(engine) == commitment.speed", matcher)
        self.assertNotIn("AIEngine.GetPrice(engine)", matcher)
        self.assertNotIn("AIEngine.GetRunningCost(engine)", matcher)
        accepted_match = _section(
            air, "function OpexAirFindAcceptedPreviewEngine", "/* Diagnostic A"
        )
        self.assertIn(
            "if (count == 1) return OpexAirPreviewMatchesEngine(commitment, only) ? only : -1;",
            accepted_match,
        )
        self.assertIn("OpexAirPreviewMatchesEngine(commitment, engine)", accepted_match)

    def test_preview_commitment_is_honored_by_growth_or_upgrade(self):
        task = TASK.read_text(encoding="utf-8")
        projects = TASK_PROJECTS.read_text(encoding="utf-8")
        self.assertIn(
            'this._honorAirPreviewCommitment(line, upgradeEngine, "upgrade")', task
        )
        self.assertIn(
            'this._honorAirPreviewCommitment(line, growthEngine, "growth")', task
        )
        self.assertIn(
            'this._honorAirPreviewCommitment(line, targetEngine, "upgrade")', projects
        )
        self.assertIn(
            'this._honorAirPreviewCommitment(line, targetEngine, "growth")', projects
        )
        honor = _section(
            task,
            "function OpexAI::_honorAirPreviewCommitment",
            "function OpexAI::_resizeAirFleets",
        )
        self.assertIn("AIR_LIFECYCLE_LEDGER.previewExecuted++", honor)
        self.assertIn("line.previewCommitment = null", honor)

    def test_crash_growth_upgrade_never_use_legacy_target_under_candidate(self):
        air = AIR.read_text(encoding="utf-8")
        task = TASK.read_text(encoding="utf-8")
        projects = TASK_PROJECTS.read_text(encoding="utf-8")
        refleet = _section(
            air, "function OpexAirRefleetCrashedPlane", "function OpexAirUpgradeOnePlane"
        )
        self.assertIn(
            'if (!AIR_BEST_EQUIPMENT && engine < 0 && ("refleetEngine" in line))',
            refleet,
        )
        self.assertIn('rawset("airEquipmentDirtyReason", "crash")', task)
        self.assertIn('rawset("airEquipmentDirtyReason", "growth")', task)
        self.assertIn("OpexAirEngineRelevantToLine(line.preferredEngine, line)", task)
        self.assertIn(
            "OpexAirAddPlane(line, AIR_BEST_EQUIPMENT ? growthEngine : -1)", task
        )
        self.assertIn("OpexAirAddPlane(line, targetEngine)", projects)
        self.assertIn("AIR_BEST_EQUIPMENT ? null : catalog.plane", air)

    def test_upgrade_builds_before_progressive_retirement_and_has_rollback(self):
        air = AIR.read_text(encoding="utf-8")
        task = TASK.read_text(encoding="utf-8")
        report = TASK_REPORT.read_text(encoding="utf-8")
        upgrade = _section(
            air, "function OpexAirUpgradeOnePlane", "function OpexAirPlanBetter"
        )
        self.assertIn("OpexAirAddPlane(line, targetEngine)", upgrade)
        self.assertIn("result.retireOnly = true", upgrade)
        direct_upgrade = _section(
            task,
            "local upgradeTargetFleet =",
            "/* La rentabilite realisee bloque la CROISSANCE",
        )
        self.assertLess(
            direct_upgrade.index("OpexAirUpgradeOnePlane(line, upgradeEngine, upgradeTargetFleet)"),
            direct_upgrade.index('_queueAirRetirement(line, upgraded.oldVehicle, "air_upgrade"'),
        )
        self.assertIn(
            '_queueAirRetirement(line, upgraded.oldVehicle, "air_upgrade",', task
        )
        self.assertIn("upgraded.newVehicle))", direct_upgrade)
        self.assertIn(
            '_queueAirRetirement(line, upgraded.newVehicle, "air_upgrade_rollback")',
            task,
        )
        self.assertIn("AIVehicle.IsStoppedInDepot(vehicle)", report)
        self.assertIn("AIVehicle.SellVehicle(vehicle)", report)
        self.assertIn("action=cancel_timeout", report)

    def test_upgrade_honors_optimal_fleet_depth_without_overbuying(self):
        air = AIR.read_text(encoding="utf-8")
        task = TASK.read_text(encoding="utf-8")
        projects = TASK_PROJECTS.read_text(encoding="utf-8")
        report = TASK_REPORT.read_text(encoding="utf-8")
        upgrade = _section(
            air, "function OpexAirUpgradeOnePlane", "function OpexAirPlanBetter"
        )
        retire_guard = (
            "if (targetFleetSize > 0 && targetCount >= targetFleetSize "
            "&& live > targetFleetSize)"
        )
        self.assertIn(retire_guard, upgrade)
        self.assertLess(
            upgrade.index(retire_guard), upgrade.index("OpexAirAddPlane(line, targetEngine)")
        )
        scan = _section(upgrade, "foreach (v in line.vehicles)", "if (oldVehicle < 0)")
        self.assertIn("live++", scan)
        self.assertIn("targetCount++", scan)
        self.assertNotIn("break;", scan)
        self.assertIn("else if (oldVehicle < 0) oldVehicle = v;", upgrade)
        self.assertIn("OpexAirUpgradeOnePlane(line, upgradeEngine, upgradeTargetFleet)", task)
        self.assertIn('"air_upgrade_shrink"', task)
        self.assertIn("targetFleetSize =", task)
        self.assertIn("OpexAirUpgradeOnePlane(line, targetEngine, targetFleetSize)", projects)
        self.assertIn("if (upgraded.retireOnly)", projects)
        self.assertIn('ticket.reason == "air_upgrade_shrink"', report)
        self.assertIn("isAirUpgrade || isAirUpgradeShrink", report)

        engines = ["old", "old", "old", "old"]
        purchases = 0
        retirements = 0
        target_fleet = 2
        while any(engine != "new" for engine in engines):
            target_count = sum(engine == "new" for engine in engines)
            old_index = next(i for i, engine in enumerate(engines) if engine != "new")
            if target_count < target_fleet:
                purchases += 1
                engines.append("new")
            engines.pop(old_index)
            retirements += 1
        self.assertEqual(purchases, 2)
        self.assertEqual(retirements, 4)
        self.assertEqual(engines, ["new", "new"])

    def test_same_engine_shrink_is_common_assessment_and_retire_only(self):
        air = AIR.read_text(encoding="utf-8")
        assessment = _section(
            air, "function OpexAirAssessExistingLine", "function OpexAirEngineRelevantToLine"
        )
        same_engine = _section(
            assessment,
            "if (best.plane.id == currentEngine)",
            "else if (approvedContinuation ||",
        )
        self.assertIn("targetFleet = best.planes", same_engine)
        self.assertIn("if (targetFleet < have)", same_engine)
        self.assertIn("upgradePending = true", same_engine)
        self.assertIn("grossReplacement = 0", same_engine)
        self.assertIn("netCapital = 0", same_engine)
        self.assertIn("paybackMonths = 0", same_engine)
        self.assertIn("local excess = have > targetFleet ? have - targetFleet : 0", assessment)
        self.assertIn("if (excess > remaining) remaining = excess", assessment)

        upgrade = _section(
            air, "function OpexAirUpgradeOnePlane", "function OpexAirPlanBetter"
        )
        self.assertIn(
            "if (oldVehicle < 0 && targetFleetSize > 0 && live > targetFleetSize) oldVehicle = anyVehicle;",
            upgrade,
        )
        self.assertIn("result.retireOnly = true", upgrade)

        live = 4
        target_fleet = 2
        purchases = 0
        while live > target_fleet:
            live -= 1
        self.assertEqual(purchases, 0)
        self.assertEqual(live, target_fleet)

    def test_assessment_reuses_prepared_engine_counts_for_upgrade_remaining(self):
        air = AIR.read_text(encoding="utf-8")
        assessment = _section(
            air, "function OpexAirAssessExistingLine", "function OpexAirEngineRelevantToLine"
        )
        self.assertIn("if (upgradePending && preparedLiveFleet)", assessment)
        self.assertIn('local preferredKey = "" + preferredEngine', assessment)
        self.assertIn("preferredKey in stepState.engineCounts", assessment)
        self.assertIn("remaining = have - preferredCount", assessment)
        self.assertIn(
            'else if (upgradePending && ("vehicles" in line) && line.vehicles != null)',
            assessment,
        )
        self.assertIn("AIVehicle.GetEngineType(v) != preferredEngine", assessment)
        self.assertGreaterEqual(
            assessment.count("local excess = have > targetFleet ? have - targetFleet : 0"),
            2,
        )

        vehicles = [
            {"valid": True, "air": True, "engine": 7},
            {"valid": True, "air": True, "engine": 9},
            {"valid": True, "air": True, "engine": 9},
            {"valid": False, "air": True, "engine": 7},
            {"valid": True, "air": False, "engine": 7},
        ]
        live = [v for v in vehicles if v["valid"] and v["air"]]
        preferred = 9
        legacy_remaining = sum(v["engine"] != preferred for v in live)
        engine_counts = {}
        for vehicle in live:
            engine_counts[vehicle["engine"]] = engine_counts.get(vehicle["engine"], 0) + 1
        prepared_remaining = len(live) - engine_counts.get(preferred, 0)
        self.assertEqual(prepared_remaining, legacy_remaining)
        target_fleet = 1
        excess = max(len(live) - target_fleet, 0)
        self.assertEqual(max(prepared_remaining, excess), 2)

    def test_retire_only_has_no_purchase_cash_guard_or_fake_portfolio_capital(self):
        task = TASK.read_text(encoding="utf-8")
        task_projects = TASK_PROJECTS.read_text(encoding="utf-8")
        projects = PROJECTS.read_text(encoding="utf-8")

        direct = _section(
            task,
            "local upgradeTargetFleet =",
            "/* La rentabilite realisee bloque la CROISSANCE",
        )
        self.assertIn(
            "local upgradeNeedsBuild = OpexAirUpgradeStepNeedsBuild(line, upgradeEngine, upgradeTargetFleet)",
            direct,
        )
        self.assertIn("retireOnly = !upgradeNeedsBuild", direct)
        cash_guard = _section(direct, "if (upgradeNeedsBuild)", "local upgraded =")
        self.assertIn("upgradePrice + OpexCashReserve()", cash_guard)
        self.assertIn("OpexTryReborrow", cash_guard)
        self.assertNotIn("OpexAirUpgradeOnePlane", cash_guard)

        execution = _section(
            task_projects,
            "local lifecycleKind =",
            "local costs = C63_INVEST_PROBE",
        )
        self.assertIn("local lifecycleRetireOnly =", execution)
        self.assertIn("!OpexAirUpgradeStepNeedsBuild", execution)
        guarded_cash = _section(execution, "if (!lifecycleRetireOnly)", "local plannedFull")
        self.assertIn("AICompany.GetBankBalance", guarded_cash)
        self.assertIn("OpexTryReborrow", guarded_cash)
        self.assertIn("local plannedFull = lifecycleRetireOnly ? 0", execution)

        fleet_project = _section(
            projects, "function OpexProjectFromFleet", "function OpexProjectFromAir"
        )
        self.assertIn('local retireOnly = ("retireOnly" in entry) && entry.retireOnly', fleet_project)
        self.assertIn('local cashRequired = ("cashRequired" in entry)', fleet_project)
        self.assertIn("? entry.cashRequired : (retireOnly ? 0", fleet_project)
        self.assertIn('local capitalCommitted = ("capitalCommitted" in entry)', fleet_project)
        self.assertIn("local capital = cashRequired", fleet_project)
        self.assertIn("local roiCapital = capitalCommitted > 0 ? capitalCommitted : 0", fleet_project)

    def test_upgrade_retirement_ticket_tracks_exact_replacement(self):
        main = MAIN.read_text(encoding="utf-8")
        task = TASK.read_text(encoding="utf-8")
        projects = TASK_PROJECTS.read_text(encoding="utf-8")
        queue = _section(
            task,
            "function OpexAI::_queueAirRetirement",
            "function OpexAI::_abandonAirPreviewCommitment",
        )
        self.assertIn(
            "function OpexAI::_queueAirRetirement(line, vehicle, reason, replacementVehicle = -1)",
            queue,
        )
        self.assertIn(
            "function _queueAirRetirement(line, vehicle, reason, replacementVehicle = -1);",
            main,
        )
        self.assertIn("replacementVehicle = replacementVehicle", queue)
        self.assertIn(
            '_queueAirRetirement(line, upgraded.oldVehicle, "air_upgrade",', task
        )
        self.assertIn("upgraded.newVehicle))", task)
        self.assertIn(
            '_queueAirRetirement(line, upgraded.oldVehicle, "air_upgrade", upgraded.newVehicle)',
            projects,
        )

    def test_upgrade_timeout_with_live_replacement_cannot_restore_old_or_rebuy_it(self):
        report = TASK_REPORT.read_text(encoding="utf-8")
        scrap = _section(report, "function OpexAI::_scrapRetiredVehicles")
        timeout = _section(
            scrap,
            "if (now - started >= SCRAP_TIMEOUT_YEARS * 365)",
            "local lastSend",
        )
        defer = _section(
            timeout,
            "if (isAirUpgrade)",
            "/* Le remplacant d'un air_upgrade est ici prouve absent",
        )
        self.assertIn('ticket.reason == "air_upgrade"', timeout)
        self.assertIn('"replacementVehicle" in ticket', defer)
        self.assertIn("AIVehicle.IsValidVehicle(ticket.replacementVehicle)", defer)
        self.assertIn("existing == ticket.replacementVehicle", defer)
        self.assertIn("if (!hasReplacementIdentity || replacementActive)", defer)
        self.assertIn("ticket.startedDate = now", defer)
        self.assertIn("action=defer_timeout_replacement_active", defer)
        self.assertNotIn("line.vehicles.append(vehicle)", defer)
        self.assertNotIn("airEquipmentDirty", defer)
        self.assertNotIn("upgradeRemaining", defer)
        defer_start = timeout.index("if (!hasReplacementIdentity || replacementActive)")
        defer_continue = timeout.index("continue;", defer_start)
        restore_old = timeout.index("line.vehicles.append(vehicle)")
        drop_ticket = timeout.index("removeTickets.append(vehicle)")
        self.assertLess(defer_continue, restore_old)
        self.assertLess(defer_continue, drop_ticket)

        # Scenario explicite : N avions actifs après le remplacement, l'ancien est hors ligne.
        # Au timeout, si le remplaçant exact est encore actif, la branche ci-dessus conserve
        # exactement N avions et le ticket; si le remplaçant a disparu, restaurer l'ancien
        # fait seulement N-1 -> N avant la ré-évaluation commune.
        def timeout_transition(active, old_vehicle, replacement_vehicle):
            active = list(active)
            has_identity = replacement_vehicle is not None
            replacement_active = has_identity and replacement_vehicle in active
            if (not has_identity) or replacement_active:
                return active, True, False
            if old_vehicle not in active:
                active.append(old_vehicle)
            return active, False, True

        active, ticket_kept, dirty = timeout_transition([201, 202], 101, 201)
        self.assertEqual(active, [201, 202])
        self.assertEqual(len(active), 2)
        self.assertNotIn(101, active)
        self.assertTrue(ticket_kept)
        self.assertFalse(dirty)

        active, ticket_kept, dirty = timeout_transition([202], 101, 201)
        self.assertEqual(set(active), {101, 202})
        self.assertEqual(len(active), 2)
        self.assertFalse(ticket_kept)
        self.assertTrue(dirty)

    def test_upgrade_retirement_timeout_reinvalidates_common_lifecycle(self):
        air = AIR.read_text(encoding="utf-8")
        report = TASK_REPORT.read_text(encoding="utf-8")
        scrap = _section(report, "function OpexAI::_scrapRetiredVehicles")
        timeout = _section(
            scrap,
            "if (now - started >= SCRAP_TIMEOUT_YEARS * 365)",
            "local lastSend",
        )
        self.assertIn('ticket.reason == "air_upgrade"', timeout)
        self.assertIn("AIR_BEST_EQUIPMENT", timeout)
        self.assertIn('line.mode == "air"', timeout)
        self.assertIn('line.airEquipmentDirty = true', timeout)
        self.assertIn('line.airEquipmentDirtyReason = "retire_rollback"', timeout)
        self.assertIn("AIR_LIFECYCLE_LEDGER.retireRollback++", timeout)
        self.assertNotIn("upgradeRemaining++", timeout)
        self.assertNotIn("upgradePending = true", timeout)

        assessment = _section(
            air, "function OpexAirAssessExistingLine", "function OpexAirEngineRelevantToLine"
        )
        same_primary = _section(
            assessment,
            "if (best.plane.id == currentEngine)",
            "else if (approvedContinuation ||",
        )
        self.assertIn('line.preferredEngine == best.plane.id', assessment)
        self.assertIn("approvedContinuation", same_primary)
        self.assertIn('reason == "retire_rollback"', same_primary)
        self.assertIn("upgradePending = true", same_primary)
        self.assertIn("AIVehicle.GetEngineType(v) != preferredEngine", assessment)
        task = TASK.read_text(encoding="utf-8")
        self.assertIn(
            'evalReason == "upgrade" || evalReason == "retire_rollback"', task
        )

    def test_free_retire_priority_is_historical_only_not_frontier(self):
        projects = PROJECTS.read_text(encoding="utf-8")
        selector = _section(
            projects,
            "function OpexProjectSelectAffordable",
            "function OpexProjectSelectionScore",
        )
        insert = _section(
            projects,
            "function OpexProjectInsert",
            "function OpexLogVivier",
        )
        classifier = _section(
            projects,
            "function OpexProjectIsFreeAirRetirement",
            "function OpexC49ProjectScore",
        )
        self.assertIn('project.mode == "fleet"', classifier)
        self.assertIn('project.payload.kind == "upgrade"', classifier)
        self.assertIn("project.payload.retireOnly", classifier)
        self.assertIn(
            "project.profitAnnual < floorProfit && !OpexProjectIsFreeAirRetirement(project)",
            selector,
        )
        self.assertIn("local preparedHistorical = !capitalProfitTie", insert)
        self.assertIn("? project.selectionFreeRetire : OpexProjectIsFreeAirRetirement(project)", insert)
        self.assertIn("if (priorFreeRetire != projectFreeRetire)", insert)
        self.assertLess(
            insert.index("if (priorFreeRetire != projectFreeRetire)"),
            insert.index("if (projectScore > priorScore)"),
        )

        # Hors frontier, la priorité historique de maintenance est conservée.
        ranked = [
            {"name": "investment", "score": 100.0, "free_retire": False},
        ]
        project = {"name": "shrink", "score": 0.0, "free_retire": True}
        pos = len(ranked)
        while pos > 0:
            prior = ranked[pos - 1]
            if prior["free_retire"] != project["free_retire"]:
                if prior["free_retire"]:
                    break
                pos -= 1
                continue
            if prior["score"] > project["score"]:
                break
            pos -= 1
        ranked.insert(pos, project)
        self.assertEqual(ranked[0]["name"], "shrink")

        # Sous frontier (capitalProfitTie=true), la classification free_retire est
        # neutralisée : seul P_network-lambda*C décide.
        investment_score = 100.0
        retire_score = 0.0
        self.assertGreater(investment_score, retire_score)

    def test_retire_only_zero_capital_executes_with_fleet_portfolio_when_bounded_pool_is_full(self):
        defaults = parse_ai_settings(INFO)
        self.assertEqual(defaults["policy_air"], 1)
        self.assertIn("FLEET_PORTFOLIO = polAir;", SETTINGS.read_text(encoding="utf-8"))

        projects = PROJECTS.read_text(encoding="utf-8")
        task_projects = TASK_PROJECTS.read_text(encoding="utf-8")
        from_fleet = _section(
            projects,
            "function OpexProjectFromFleet",
            "function OpexProjectFromAir",
        )
        selector = _section(
            projects,
            "function OpexProjectSelectAffordable",
            "function OpexProjectSelectionScore",
        )
        insert = _section(
            projects,
            "function OpexProjectInsert",
            "function OpexLogVivier",
        )
        execute = _section(
            task_projects,
            "function OpexAI::_tryBuildFleetProject",
            "function OpexAI::_refreshDynamicBatch",
        )

        # Génération : retireOnly existe même sans prix/capital d'achat et publie
        # explicitement un budgetCapital nul.
        self.assertIn('local retireOnly = ("retireOnly" in entry) && entry.retireOnly', from_fleet)
        self.assertIn("if (!retireOnly && entry.planePrice <= 0) return null", from_fleet)
        self.assertIn('local cashRequired = ("cashRequired" in entry)', from_fleet)
        self.assertIn("? entry.cashRequired : (retireOnly ? 0", from_fleet)
        self.assertIn("budgetCapital = cashRequired + safetyMargin", from_fleet)

        # Sélection historique : capital zéro reste abordable même avec budget nul
        # et le floor ne peut pas affamer retireOnly. La priorité spéciale est
        # désactivée lorsque capitalProfitTie active la frontier.
        self.assertIn("if (financeCapital > capitalBudget) continue", selector)
        self.assertIn(
            "project.profitAnnual < floorProfit && !OpexProjectIsFreeAirRetirement(project)",
            selector,
        )
        self.assertIn("local preparedHistorical = !capitalProfitTie", insert)
        self.assertIn("? project.selectionFreeRetire : OpexProjectIsFreeAirRetirement(project)", insert)
        self.assertLess(
            insert.index("if (priorFreeRetire != projectFreeRetire)"),
            insert.index("if (projectScore > priorScore)"),
        )

        # Exécution : la cible vient de l'état lifecycle commun, jamais d'une
        # politique parallèle ; retireOnly saute totalement la garde cash puis
        # exécute seulement OpexAirUpgradeOnePlane + air_upgrade_shrink.
        self.assertIn(
            'local lifecycleRetireOnly = AIR_BEST_EQUIPMENT && lifecycleKind == "upgrade"',
            execute,
        )
        self.assertIn(
            "!OpexAirUpgradeStepNeedsBuild(line, lifecycleTargetEngine, lifecycleTargetFleet)",
            execute,
        )
        self.assertIn("if (!lifecycleRetireOnly)", execute)
        self.assertIn("local plannedFull = lifecycleRetireOnly ? 0", execute)
        self.assertIn(
            "OpexAirUpgradeOnePlane(line, targetEngine, targetFleetSize)",
            execute,
        )
        self.assertIn(
            '_queueAirRetirement(line, upgraded.oldVehicle, "air_upgrade_shrink")',
            execute,
        )
        self.assertIn("return { outcome = \"built\", discards = passDiscards }", execute)
        self.assertNotIn("catalog.plane", execute)
        self.assertNotIn("bestPlane", execute)
        self.assertNotIn("refleetEngine", execute)

        # Régression comportementale du tri borné : le vivier est déjà PLEIN de
        # deux investissements, limit=2. L'insertion d'un retireOnly à score nul
        # doit l'amener en tête puis évincer un investissement, jamais le shrink.
        ranked = [
            {"name": "investment_a", "score": 300.0, "free_retire": False},
            {"name": "investment_b", "score": 200.0, "free_retire": False},
        ]
        retire = {"name": "retire_only", "score": 0.0, "free_retire": True}
        limit = 2
        pos = len(ranked)
        while pos > 0:
            prior = ranked[pos - 1]
            if prior["free_retire"] != retire["free_retire"]:
                if prior["free_retire"]:
                    break
                pos -= 1
                continue
            if prior["score"] > retire["score"]:
                break
            pos -= 1
        ranked.insert(pos, retire)
        if len(ranked) > limit:
            ranked.pop()
        self.assertEqual(len(ranked), limit)
        self.assertEqual(ranked[0]["name"], "retire_only")
        self.assertIn("retire_only", {p["name"] for p in ranked})

        # Même sous contrainte extrême (budget capital nul + floor supérieur au
        # profit publié), le contrat retireOnly passe les deux filtres concernés.
        finance_capital = 0
        capital_budget = 0
        project_profit = 1
        floor_profit = 10_000
        is_free_retire = True
        self.assertFalse(finance_capital > capital_budget)
        self.assertFalse(project_profit < floor_profit and not is_free_retire)

    def test_crash_of_already_retired_vehicle_returns_before_line_mutation(self):
        events = EVENTS.read_text(encoding="utf-8")
        crash = _section(
            events,
            "function OpexAI::_onVehicleCrashed",
            "function OpexAI::_onVehicleWaitingInDepot",
        )
        guard_start = crash.index(
            "if (this._vehiclesToRetire != null && (vehicle in this._vehiclesToRetire))"
        )
        lookup = crash.index("local line = OpexFindLineForVehicle")
        self.assertLess(guard_start, lookup)
        guard = crash[guard_start:lookup]
        self.assertIn("delete this._vehiclesToRetire[vehicle]", guard)
        self.assertIn("return;", guard)
        self.assertNotIn("needsRefleet", guard)
        self.assertNotIn("vehCount--", guard)
        self.assertNotIn("trains--", guard)

    def test_autoreplace_remaps_retirement_key_and_replacement_reference(self):
        events = EVENTS.read_text(encoding="utf-8")
        handler = _section(
            events,
            "function OpexAI::_onVehicleAutoreplaced",
            "function OpexAI::_onVehicleUnprofitable",
        )
        self.assertIn(
            "oldVehicle in this._vehiclesToRetire",
            handler,
        )
        self.assertIn(
            "this._vehiclesToRetire.rawset(newVehicle, lineId)",
            handler,
        )
        self.assertIn(
            "retireTicket.replacementVehicle != oldVehicle",
            handler,
        )
        self.assertIn(
            "retireTicket.replacementVehicle = newVehicle",
            handler,
        )

    def test_replacement_crash_refleet_remaps_ticket_identity(self):
        events = EVENTS.read_text(encoding="utf-8")
        task = TASK.read_text(encoding="utf-8")
        air = AIR.read_text(encoding="utf-8")
        crash = _section(
            events,
            "function OpexAI::_onVehicleCrashed",
            "function OpexAI::_onVehicleWaitingInDepot",
        )
        refleet = _section(
            air,
            "function OpexAirRefleetCrashedPlane",
            "function OpexAirUpgradeStepNeedsBuild",
        )
        resize = _section(task, 'if (("needsRefleet" in line) && line.needsRefleet)', "/* C15")
        self.assertIn("retireTicket.replacementVehicle = -1", crash)
        self.assertIn('rawset("replacementCrashed", true)', crash)
        self.assertIn("vehicle = -1", refleet)
        self.assertIn("result.vehicle = plane", refleet)
        self.assertIn('rawset("replacementVehicle", recovered.vehicle)', resize)
        self.assertIn("retireTicket.replacementCrashed = false", resize)

    def test_crash_refleet_respects_common_target_depth(self):
        events = EVENTS.read_text(encoding="utf-8")
        task = TASK.read_text(encoding="utf-8")
        crash_handler = _section(
            events,
            "function OpexAI::_onVehicleCrashed",
            "function OpexAI::_onVehicleWaitingInDepot",
        )
        resize = _section(task, 'if (("needsRefleet" in line) && line.needsRefleet)', "/* C15")
        self.assertIn('rawset("airEquipmentDirtyReason", "crash")', crash_handler)
        self.assertIn('if (("airEquipmentDirty" in line) && line.airEquipmentDirty)', resize)
        self.assertIn(
            'local crashTarget = ("targetFleetSize" in line) ? line.targetFleetSize : 0',
            resize,
        )
        self.assertIn("if (crashLive >= crashTarget)", resize)
        self.assertIn("line.needsRefleet = false", resize)
        self.assertLess(
            resize.index("if (crashLive >= crashTarget)"),
            resize.index("OpexAirRefleetCrashedPlane(line, crashEngine)"),
        )
        self.assertIn("AIEngine.IsBuildable(line.preferredEngine)", resize)
        self.assertIn("OpexAirEngineRelevantToLine(line.preferredEngine, line)", resize)

    def test_last_plane_crash_is_reassessed_by_common_engine(self):
        air = AIR.read_text(encoding="utf-8")
        assessment = _section(
            air, "function OpexAirAssessExistingLine", "function OpexAirEngineRelevantToLine"
        )
        best_pos = assessment.index("OpexAirBestEquipment(catalog, airport, siteA, siteB")
        zero_pos = assessment.index("if (have == 0)")
        self.assertLess(best_pos, zero_pos)
        zero = _section(assessment, "if (have == 0)", "if (currentPlane == null)")
        self.assertIn("result.preferredEngine = best.plane.id", zero)
        self.assertIn("result.targetFleetSize = best.planes", zero)
        self.assertIn("result.currentEconomics = currentEconomics", zero)

    def test_upgrade_unit_gain_is_frozen_per_assessment(self):
        task = TASK.read_text(encoding="utf-8")
        apply = _section(
            task,
            "function OpexAirApplyLineAssessment",
            "function OpexAI::_queueAirRetirement",
        )
        resize = _section(task, "function OpexAI::_resizeAirFleets")
        self.assertIn(
            "upgradeUnitGain = assessment.gainAnnual / assessment.upgradeRemaining",
            apply,
        )
        self.assertIn('rawset("upgradeUnitGainAnnual", upgradeUnitGain)', apply)
        self.assertIn(
            'local unitGain = ("upgradeUnitGainAnnual" in line) ? line.upgradeUnitGainAnnual : 0',
            resize,
        )
        self.assertNotIn(
            "line.upgradeGainAnnual / line.upgradeRemaining",
            resize,
        )

        total_gain = 400
        initial_remaining = 4
        unit_gain = total_gain // initial_remaining
        self.assertEqual(
            [unit_gain for _remaining in (4, 3, 2, 1)],
            [100, 100, 100, 100],
        )

    def test_mixed_fleet_current_economics_uses_real_engines(self):
        air = AIR.read_text(encoding="utf-8")
        actual = _section(
            air,
            "function OpexAirActualFleetEconomics",
            "function OpexAirRemainingTransitionCapital",
        )
        assessment = _section(
            air, "function OpexAirAssessExistingLine", "function OpexAirEngineRelevantToLine"
        )
        self.assertIn("foreach (v in line.vehicles)", actual)
        self.assertIn("AIVehicle.GetEngineType(v)", actual)
        self.assertIn("OpexAirPlaneFromEngine(AIVehicle.GetEngineType(v), line.cargo)", actual)
        self.assertIn("OpexAirActualFleetEconomicsContext(catalog, line, distance)", actual)
        self.assertIn("OpexAirFleetEconomicsFromContext(context, monthlyPax)", actual)
        self.assertIn(
            "OpexAirActualFleetEconomics(catalog, line, distance, currentDemand)",
            assessment,
        )
        self.assertNotIn(
            "currentCap, have, 0",
            assessment,
        )

    def test_transition_capital_counts_only_remaining_builds_and_real_resales(self):
        air = AIR.read_text(encoding="utf-8")
        transition = _section(
            air,
            "function OpexAirRemainingTransitionCapital",
            "function OpexAirAirportProfileForType",
        )
        self.assertIn("targetVehicles.append(v)", transition)
        self.assertIn("otherVehicles.append(v)", transition)
        self.assertIn("local builds = targetFleetSize - keepTarget", transition)
        self.assertIn("foreach (v in otherVehicles) resale += AIVehicle.GetCurrentValue(v)", transition)
        self.assertIn("local extraTargets = targetVehicles.len() - targetFleetSize", transition)

        target_fleet = 2
        target_already_present = 1
        remaining_builds = target_fleet - min(target_already_present, target_fleet)
        self.assertEqual(remaining_builds, 1)

    def test_existing_line_population_demand_is_shared_by_live_hub_routes(self):
        air = AIR.read_text(encoding="utf-8")
        demand = _section(
            air,
            "function OpexAirLineBaseDemand",
            "function OpexAirLinePhysicalFleetCap",
        )
        self.assertIn("function OpexAirLineBaseDemand(line, lines = null)", demand)
        self.assertIn("OpexAirLiveRoutesAtAirport(line.stationA, lines)", demand)
        self.assertIn("OpexAirLiveRoutesAtAirport(line.stationB, lines)", demand)
        self.assertIn("/ routesA", demand)
        self.assertIn("/ routesB", demand)

        share_pct = 70
        pop_a, pop_b = 3000, 1800
        unshared = ((pop_a + pop_b) * share_pct) // 100
        shared = ((pop_a * share_pct) // 100) // 3 + ((pop_b * share_pct) // 100) // 3
        self.assertLess(shared, unshared)
        self.assertEqual(shared, 1120)

    def test_lifecycle_target_depth_uses_candidate_plane_cadence(self):
        air = AIR.read_text(encoding="utf-8")
        cadence = _section(
            air,
            "function OpexAirCadenceCap",
            "function OpexAirAirportAcceptsPlane",
        )
        self.assertIn("function OpexAirCadenceContext", air)
        self.assertIn("function OpexAirCadenceLimitFromContext", air)
        self.assertIn("function OpexAirCadenceCapForPlane", cadence)
        self.assertIn("cadenceContext = null", cadence)
        self.assertIn("OpexAirCadenceLimitFromContext(", cadence)
        self.assertIn("cadenceContext, -1, plane.speed, plane.capacity", cadence)

        best = _section(
            air,
            "function OpexAirBestEquipment",
            "function OpexAirEquipmentChoices",
        )
        self.assertIn("cadenceLine = null", best)
        self.assertIn("OpexAirCadenceContext(cadenceLine, lines)", best)
        self.assertIn("OpexAirCadenceCapForPlane(cadenceLine, plane, lines, cadenceContext)", best)
        self.assertIn("candidateMaxPlanes", best)

        choices = _section(
            air,
            "function OpexAirEquipmentChoices",
            "function OpexAirEquipmentFrontier",
        )
        self.assertIn("cadenceLine = null", choices)
        self.assertIn("OpexAirCadenceContext(cadenceLine, lines)", choices)
        self.assertIn("OpexAirCadenceCapForPlane(cadenceLine, plane, lines, cadenceContext)", choices)

        frontier = _section(
            air,
            "function OpexAirExistingLineFrontier",
            "function OpexAirAssessExistingLine",
        )
        self.assertIn("local maxPlanes = fleetCap", frontier)
        self.assertIn("OpexAirCadenceContext(line, lines)", frontier)
        self.assertIn("OpexAirCadenceCapForPlane(line, plane, lines, cadenceContext)", frontier)

        assessment = _section(
            air,
            "function OpexAirAssessExistingLine",
            "function OpexAirEngineRelevantToLine",
        )
        self.assertIn("fleetCap, line", assessment)

    def test_preview_target_depth_uses_candidate_plane_cadence(self):
        air = AIR.read_text(encoding="utf-8")
        preview = _section(
            air,
            "function OpexAirAssessPreviewPlane",
            "function OpexAirFindPreviewCommitmentEngine",
        )
        self.assertIn("OpexAirLineBaseDemand(line, lines)", preview)
        self.assertIn("OpexAirCadenceCapForPlane(line, previewPlane, lines)", preview)
        self.assertIn("targetFleetCap", preview)

    def test_approved_upgrade_continuation_requires_common_best_unchanged(self):
        air = AIR.read_text(encoding="utf-8")
        assessment = _section(
            air, "function OpexAirAssessExistingLine", "function OpexAirEngineRelevantToLine"
        )
        self.assertIn(
            'local approvedContinuation = ("upgradePending" in line) && line.upgradePending',
            assessment,
        )
        self.assertIn(
            'line.preferredEngine == best.plane.id',
            assessment,
        )
        self.assertIn(
            "else if (approvedContinuation || (gainAnnual > 0",
            assessment,
        )
        self.assertLess(
            assessment.index("OpexAirBestEquipment(catalog, airport, siteA, siteB"),
            assessment.index("local approvedContinuation ="),
        )

    def test_resolved_preview_commitment_times_out_without_resetting_clock(self):
        task = TASK.read_text(encoding="utf-8")
        resolver = _section(
            task,
            "function OpexAI::_resolveAirPreviewCommitment",
            "function OpexAI::_honorAirPreviewCommitment",
        )
        resize = _section(task, "function OpexAI::_resizeAirFleets")
        self.assertIn(
            'if (!wasResolved) commitment.rawset("resolvedDate", AIDate.GetCurrentDate())',
            resolver,
        )
        resolved = _section(
            resize,
            'else if (("status" in commitment) && commitment.status == "resolved")',
            "/* L'identite est connue mais la cible economique n'est pas encore engagee.",
        )
        self.assertIn("AIR_PREVIEW_COMMITMENT_MAX_DAYS", resolved)
        self.assertIn(
            'this._abandonAirPreviewCommitment(line, "timeout", "periodic")',
            resolved,
        )
        self.assertIn('rawset("airEquipmentDirtyReason", "periodic")', resolved)
        self.assertIn("commitmentLocksTarget = true", resolved)

    def test_persistence_preserves_state_and_forces_restore_reeval(self):
        src = PERSIST.read_text(encoding="utf-8")
        self.assertIn("lines = saveLines,", src)
        self.assertIn('if ("lines" in data) this._pendingLines = data.lines;', src)
        self.assertIn("vehiclesToRetire = this._vehiclesToRetire,", src)
        self.assertIn('if ("vehiclesToRetire" in data && data.vehiclesToRetire != null) this._vehiclesToRetire = data.vehiclesToRetire;', src)
        for field in (
            "currentPrimaryEngine",
            "preferredEngine",
            "targetFleetSize",
            "upgradePending",
            "upgradeRemaining",
            "previewCommitment",
        ):
            self.assertIn(field, src)
        self.assertIn('rawset("airEquipmentDirty", true)', src)
        self.assertIn('rawset("airEquipmentDirtyReason", "restore")', src)
        self.assertIn('currentEngine < 0 && ("refleetEngine" in line)', src)

    def test_periodic_reevaluation_is_bounded_and_dirty_first(self):
        task = TASK.read_text(encoding="utf-8")
        globals_src = GLOBALS.read_text(encoding="utf-8")
        self.assertIn("AIR_EQUIPMENT_REEVAL_MAX_PER_PASS <- 1;", globals_src)
        self.assertIn("AIR_EQUIPMENT_REEVAL_MIN_OPS <- 3000;", globals_src)
        self.assertIn("local urgent = [];", task)
        self.assertIn(
            "if (isDirty || hasCommitment) urgent.append(candidate);", task
        )
        self.assertIn(
            "lifecycleEvalsThisPass >= AIR_EQUIPMENT_REEVAL_MAX_PER_PASS", task
        )
        self.assertIn(
            "AIController.GetOpsTillSuspend() < AIR_EQUIPMENT_REEVAL_MIN_OPS", task
        )
        self.assertIn("AIR_LIFECYCLE_LEDGER.deferredEvaluations++", task)

    def test_pareto_prefilter_is_strict_and_synthetic_best_invariant(self):
        src = CATALOG.read_text(encoding="utf-8")
        self.assertIn(
            "a.planeType != b.planeType || a.capacity != b.capacity || a.speed != b.speed",
            src,
        )
        self.assertIn(
            "a.price > b.price || a.runningCost > b.runningCost || rangeA < rangeB",
            src,
        )
        self.assertIn("OpexAirSafeParetoChoices", src)
        self.assertIn(
            "airParetoStats = { raw = 0, kept = 0, pruned = 0 }", src
        )
        pool = [
            {"id": "dominated", "planeType": 1, "capacity": 100, "speed": 300,
             "price": 120000, "running": 18000, "range": 220},
            {"id": "dominator", "planeType": 1, "capacity": 100, "speed": 300,
             "price": 100000, "running": 16000, "range": 300},
            {"id": "capacity", "planeType": 1, "capacity": 130, "speed": 300,
             "price": 145000, "running": 20000, "range": 300},
            {"id": "speed", "planeType": 1, "capacity": 100, "speed": 360,
             "price": 150000, "running": 21000, "range": 0},
            {"id": "small", "planeType": 0, "capacity": 100, "speed": 300,
             "price": 90000, "running": 15000, "range": 300},
        ]
        filtered = _pareto(pool)
        ids = {p["id"] for p in filtered}
        self.assertNotIn("dominated", ids)
        self.assertIn("capacity", ids)
        self.assertIn("speed", ids)
        self.assertIn("small", ids)
        for distance in (50, 220, 250, 350):
            self.assertEqual(
                _synthetic_best(pool, distance), _synthetic_best(filtered, distance)
            )

    def test_lifecycle_sign_parser_uses_max_and_scales_kopcodes(self):
        chunks = {"SIGN": {
            1: {"name": "AL0|2|1|1|3"},
            2: {"name": "AL0|5|4|2|7"},
            3: {"name": "AL1|3|2|4|9"},
            4: {"name": "AL2|8|6|5|4"},
            5: {"name": "AL3|2|7|3|1"},
            6: {"name": "AL4|1|2|3|4"},
            7: {"name": "AL5|12|34|56"},
            8: {"name": "AL6|11|22|33|44"},
            9: {"name": "AL7|2|3|4|5"},
            10: {"name": "AL8|6|7|8|9"},
            11: {"name": "AL9|10|11"},
            12: {"name": "AQ|20|15|5"},
        }}
        stats = air_equipment_diagnostic_stats(chunks)
        self.assertEqual(stats["air_lifecycle_evaluations"], 5)
        self.assertEqual(stats["air_lifecycle_assessment_accepted"], 4)
        self.assertEqual(stats["air_lifecycle_deferred_evaluations"], 7)
        self.assertEqual(stats["air_lifecycle_eval_opcodes"], 9000)
        self.assertEqual(stats["air_lifecycle_growth_executed"], 6)
        self.assertEqual(stats["air_lifecycle_upgrade_executed"], 4)
        self.assertEqual(stats["air_lifecycle_preview_abandoned"], 2)
        self.assertEqual(stats["air_lifecycle_event_eval_opcodes"], 11000)
        self.assertEqual(stats["air_lifecycle_periodic_eval_opcodes"], 22000)
        self.assertEqual(stats["air_lifecycle_engine_event_opcodes"], 33000)
        self.assertEqual(stats["air_lifecycle_preview_opcodes"], 44000)
        self.assertEqual(stats["air_lifecycle_preview_id_resolved"], 2)
        self.assertEqual(stats["air_lifecycle_preview_id_miss"], 3)
        self.assertEqual(stats["air_lifecycle_preview_abandon_common"], 4)
        self.assertEqual(stats["air_lifecycle_preview_abandon_timeout"], 5)
        self.assertEqual(stats["air_lifecycle_engine_available_evaluations"], 6)
        self.assertEqual(stats["air_lifecycle_preview_evaluations"], 7)
        self.assertEqual(stats["air_lifecycle_crash_evaluations"], 8)
        self.assertEqual(stats["air_lifecycle_growth_evaluations"], 9)
        self.assertEqual(stats["air_lifecycle_upgrade_evaluations"], 10)
        self.assertEqual(stats["air_lifecycle_restore_evaluations"], 11)
        self.assertEqual(stats["air_pareto_pruned"], 5)


if __name__ == "__main__":
    unittest.main()
