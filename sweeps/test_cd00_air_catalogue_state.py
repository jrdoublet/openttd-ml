"""CD-00: executable reference traces and source contracts for the AIR catalogue.

No Squirrel VM is executed. The deterministic model fixes *control flow* and
publication ordering; source checks bind its assumptions to production. It is
not evidence of economic or opcode equivalence on a moving OpenTTD map.

The tests deliberately do not depend on the location of phase calls inside
OpexAirPlans: CD01-CD05 may extract the driver into further helpers.
"""

from dataclasses import dataclass, field
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


AIR = read("air_planning.nut")
C83 = read("air_c83_repair.nut")
SCHED = read("scheduler_tasks.nut")
UPDATE = read("projects_update.nut")
ORCH = read("orchestrator.nut")
PERSIST = read("persist.nut")
MAIN = read("main.nut")


def function(source, signature):
    """Read a Squirrel function, avoiding unrelated top-level code.

    The contracts below use exact semantic guards but do not pin line numbers
    or the relative position of individual phase calls in the AIR driver.
    """
    start = source.index("function " + signature + "(")
    opening = source.index("{", start)
    level = 0
    for i in range(opening, len(source)):
        if source[i] == "{":
            level += 1
        elif source[i] == "}":
            level -= 1
            if level == 0:
                return source[start:i + 1]
    raise AssertionError("unterminated function " + signature)


@dataclass(frozen=True)
class Step:
    combo: int
    phase: str
    item: str
    plan: str = ""


@dataclass
class ContractMachine:
    """Deterministic C78 transactional shell around an opaque AIR phase stream.

    'budget' is number of fixture steps, *not* a prediction of VM opcodes.
    The fixture assumes each step produces one deterministic visible effect.
    """
    streams: dict
    stage: str = "complete"
    phase: str = "primary"
    cursor: int = 0
    plans: list = field(default_factory=list)
    best_plan: str = ""
    published_prefix: int = 0
    partial_pending: bool = False
    published: bool = False
    publications: list = field(default_factory=list)
    final_count: int = 0
    revision_snapshot: dict = field(default_factory=lambda: dict(
        towns=1, industries=2, lines=3, rail=4, road=5, air=6, water=7))
    revisions: dict = field(default_factory=dict)
    ack: dict = field(default_factory=dict)
    completed: bool = False
    origin_ym: int = 1970 * 12 + 1
    last_catalog_month: int = -1
    events: list = field(default_factory=list)

    def __post_init__(self):
        self.revisions = dict(self.revision_snapshot)
        self.ack = {key: 0 for key in self.revision_snapshot}

    def event(self, layer):
        self.revisions[layer] += 1
        self.events.append(("event", layer))

    def tick(self, budget=1):
        if self.completed:
            raise AssertionError("completed scan must be removed from C78 task")
        if self.partial_pending:
            self.publications.append(("partial", tuple(self.plans)))
            self.published_prefix = len(self.plans)
            self.partial_pending = False
            self.published = True
            self.events.append(("partial", self.published_prefix))
            return "partial"
        if self.phase == "apply":
            self.publications.append(("apply", tuple(self.plans)))
            self.final_count += 1
            for key, snap_rev in self.revision_snapshot.items():
                self.ack[key] = max(self.ack[key], snap_rev)
            self.last_catalog_month = self.origin_ym
            self.completed = True
            self.events.append(("apply", len(self.plans)))
            return "apply"
        units = self.streams[self.phase]
        for _ in range(budget):
            if self.cursor >= len(units):
                break
            unit = units[self.cursor]
            self.cursor += 1
            self.events.append(("visit", unit.combo, unit.phase, unit.item))
            if unit.plan:
                self.plans.append(unit.plan)
                self.best_plan = unit.plan  # fixture imposes strict descending ranking
        if self.cursor < len(units):
            if len(self.plans) > self.published_prefix:
                self.partial_pending = True
            self.events.append(("yield", self.cursor))
            return "yield"
        if self.phase == "primary" and self.stage == "air_only" and not self.plans:
            self.phase = "fallback"
            self.cursor = 0
            self.best_plan = ""
            self.events.append(("fallback", 0))
            return "fallback"
        self.phase = "apply"
        self.events.append(("done", self.cursor))
        return "done"

    def roundtrip(self):
        """Save/Load drops all transient scan data, retaining C76 revisions."""
        return dict(revisions=self.revisions, ack=self.ack,
                    last_catalog_month=self.last_catalog_month)


def run_to_apply(machine, budget):
    for _ in range(120):
        if machine.tick(budget) == "apply":
            return machine
    raise AssertionError("fixture does not terminate")


def v93_combo_visit_order(kinds, big_won_after=-1, allow_small=True):
    """Frozen projection of the V93 loop break/next-small rule."""
    visited = []
    i = 0
    while i < len(kinds):
        visited.append(i)
        if i >= big_won_after and big_won_after >= 0:
            if not allow_small:
                break
            if kinds[i] != "small":
                next_small = next((j for j in range(i + 1, len(kinds))
                                   if kinds[j] == "small"), -1)
                if next_small < 0:
                    break
                i = next_small
                continue
        i += 1
    return visited


class CD00SourceContracts(unittest.TestCase):
    def test_phase_interfaces_and_resumption_boundaries(self):
        for name in ("OpexAirPlansPrepare", "OpexAirPlansFindSites",
                     "OpexAirPlansNewPairs", "OpexAirPlansDiscoverHubs",
                     "OpexAirPlansHubToSite", "OpexAirPlansHubToHub",
                     "OpexAirPlansFinalize"):
            self.assertIn("function " + name + "(", AIR)
        prepare = function(AIR, "OpexAirPlansPrepare")
        sites = function(AIR, "OpexAirPlansFindSites")
        pairs = function(AIR, "OpexAirPlansNewPairs")
        hubsite = function(AIR, "OpexAirPlansHubToSite")
        hubhub = function(AIR, "OpexAirPlansHubToHub")
        finalize = function(AIR, "OpexAirPlansFinalize")
        self.assertIn("resumeState.done", prepare)
        self.assertIn("resumeState.bestPlan", prepare)
        self.assertIn("resumeState.scanIndex = i + 1;", sites)
        self.assertIn("resumeState.rankIndex = rankIndex + 1;", sites)
        self.assertIn("resumeState.sites = sites;", sites)
        self.assertIn("resumeState.a = nextA;", pairs)
        self.assertIn("resumeState.b = nextB;", pairs)
        self.assertIn("if (pairProgress &&", pairs)
        self.assertIn("ctx.resumeState.hubSiteI <- hi;", hubsite)
        self.assertIn("ctx.resumeState.hubSiteJ <- sj;", hubsite)
        self.assertIn("ctx.resumeState.hubHubI <- i;", hubhub)
        self.assertIn("ctx.resumeState.hubHubJ <- j;", hubhub)
        self.assertIn("if (progressed &&", hubsite)
        self.assertIn("if (progressed &&", hubhub)
        self.assertIn("resumeState.done = true;", finalize)
        self.assertIn("resumeState.sites = null;", finalize)

    def test_v93_c83_and_hub_snapshot_decision_contract(self):
        # All phase guards must remain present even if the driver is extracted.
        self.assertIn("OpexAirV93NextSmallCombo", AIR)
        self.assertIn('combo.kind == "small"', AIR)
        self.assertIn("V93_AIRPORT_NO_POP_FLOOR", AIR)
        self.assertIn("resumeState.hubPhase <- 0;", AIR)
        self.assertIn("resumeState.hubHubJ <- 1;", AIR)
        snap = function(AIR, "OpexAir0310HubSnapshotPrepare")
        self.assertIn('return "reuse";', snap)
        self.assertIn('return "invalidate";', snap)
        self.assertIn('return "discover";', snap)
        self.assertIn("snap.sig == sig", snap)
        self.assertIn("OpexAir0310RememberPublishedHubPairs", snap)
        store = function(AIR, "OpexAir0310HubSnapshotStore")
        for key in ("combo = comboIndex", "sig = sig",
                    "hubs = OpexAir0310CopyHubList(ctx.hubs)",
                    "sites = OpexAir0310CopySiteList(ctx.sites)",
                    "orphan = orphanCopy"):
            self.assertIn(key, store)
        self.assertIn("OpexC83RepairFindSites(ctx, comboIndex", AIR)
        self.assertIn("scan.index++;", C83)
        self.assertIn("scan.fallback = scan.partners == 0;", C83)

    def test_c78_transaction_and_opcode_boundaries(self):
        start = function(SCHED, "OpexC78StartCatalogAirRebuild")
        proceed = function(SCHED, "OpexC78ContinueCatalogAirRebuild")
        can_continue = function(SCHED, "OpexC121CatalogCanContinue")
        dispatch = function(SCHED, "OpexAI::_dispatchCatalog")
        for key in ('phase = "primary"', "cursor = {}", "plans = []",
                    "partialPending = false", "lastPublishedCount = 0",
                    "c76StartRevisions = AC06_C76_SNAPSHOT_ACK && c76Full"):
            self.assertIn(key, start)
        self.assertLess(proceed.index("s.partialPending)"),
                        proceed.index('if (s.phase == "apply")'))
        self.assertLess(proceed.index('if (s.phase == "apply")'),
                        proceed.index("local liveOps = AIController.GetOpsTillSuspend();"))
        partial = function(SCHED, "OpexC78PublishPartialAir")
        applied = function(SCHED, "OpexC78ApplyAir")
        for key in ("s.plans.len() > s.lastPublishedCount",
                    "s.partialPending = true;",
                    's.phase = "fallback";', "s.cursor = {};",
                    's.phase = "apply";'):
            self.assertIn(key, proceed)
        self.assertIn("s.lastPublishedCount = s.plans.len();", partial)
        self.assertIn("delete task.c78AirRebuild;", applied)
        self.assertIn("owner._rebuildProjects(s.fleetPlan, airOverride);", applied)
        self.assertIn("sliceBudget = AIR_PLAN_SLICE_OPS", proceed)
        self.assertIn("sliceBudget = 150000", proceed)
        self.assertIn("sliceBudget, AIController.GetTick() + BUILD_TICK_MARGIN", proceed)
        self.assertIn("GetOpsTillSuspend() > 2000", can_continue)
        self.assertIn("owner._activeWorker == null", can_continue)
        self.assertIn("AIController.GetTick() == continuationTick", can_continue)
        self.assertLess(dispatch.index("OpexC78ContinueCatalogAirRebuild(this, task, year)"),
                        dispatch.index("local stale = false;"))
        self.assertIn('name = "catalog", dueCycle = 0, enabled = true', MAIN)
        self.assertIn("owner._taskCursor = 0;", SCHED)

    def test_v141_ack_and_save_load_boundaries(self):
        proceed = function(SCHED, "OpexC78ContinueCatalogAirRebuild")
        partial = function(SCHED, "OpexC78PublishPartialAir")
        applied = function(SCHED, "OpexC78ApplyAir")
        publish = function(UPDATE, "OpexAir0310PublishIncremental")
        snapshot = function(ORCH, "OpexAC06CaptureRevisionNumbers")
        ack = function(ORCH, "OpexAC06AcknowledgeSnapshot")
        self.assertIn("OpexC78PublishPartialAir(owner, s)", proceed)
        self.assertIn("OpexC78ApplyAir(owner, task, year, s)", proceed)
        self.assertIn("OpexAir0310PublishIncremental(owner, s.plans, s.lastPublishedCount", partial)
        self.assertIn("lastPublishedCount > 0", partial)
        self.assertIn("owner._rebuildProjects(s.fleetPlan, partialAir, false);", partial)
        self.assertIn("V141_CATALOG_INCREMENTAL && !C111_AIR_C100_DECISION_SHADOW", publish)
        self.assertIn("projects.candidateGroups = rebuilt;", publish)
        self.assertIn("OpexReselectProjects(projects, publishCapital", publish)
        self.assertIn("owner._rebuildProjects(s.fleetPlan, airOverride);", applied)
        self.assertIn("OpexAC06AcknowledgeSnapshot(owner, s.c76StartRevisions)", applied)
        self.assertIn("owner._c76AcknowledgeAllLayers();", applied)  # toggle OFF
        for layer in ("towns", "industries", "lines"):
            self.assertIn("current." + layer, snapshot)
        for mode in ("rail", "road", "air", "water"):
            self.assertIn("current.engines." + mode, snapshot)
        self.assertIn("covered > previous ? covered : previous", ack)
        self.assertNotIn("c78AirRebuild", function(PERSIST, "OpexAI::Save"))
        self.assertNotIn("c78AirRebuild", function(PERSIST, "OpexAI::Load"))
        self.assertIn("this._c76ForceReloadRegen = true;", PERSIST)
        self.assertIn("if (this._loadedFromSave) this._reconcileAfterLoad();", MAIN)


class CD00FrozenTraces(unittest.TestCase):
    # Reference visit order for 2 combos, seven internal boundaries, and a
    # plan emitted during the first truncated slice.
    STREAM = (
        Step(0, "sites", "town-A"),
        Step(0, "sites", "town-B"),
        Step(0, "pairs", "A-B", "newpair-A-B"),
        Step(0, "hub_discover", "H0"),
        Step(0, "hub_site", "H0-B", "hubsite-H0-B"),
        Step(0, "hub_hub", "H0-H1"),
        Step(1, "sites", "town-C"),
        Step(1, "pairs", "B-C", "newpair-B-C"),
        Step(1, "hub_site", "H1-C"),
        Step(1, "hub_hub", "H1-H2"),
    )

    def test_every_budget_has_same_order_and_final_candidates(self):
        expected_visits = [(s.combo, s.phase, s.item) for s in self.STREAM]
        expected_plans = ("newpair-A-B", "hubsite-H0-B", "newpair-B-C")
        for quota in range(1, len(self.STREAM) + 3):
            with self.subTest(quota=quota):
                m = run_to_apply(ContractMachine({"primary": self.STREAM}), quota)
                visits = [event[1:] for event in m.events if event[0] == "visit"]
                self.assertEqual(visits, expected_visits)
                self.assertEqual(tuple(m.plans), expected_plans)
                self.assertEqual(m.best_plan, expected_plans[-1])
                self.assertEqual(m.final_count, 1)
                self.assertEqual(m.last_catalog_month, 1970 * 12 + 1)
                self.assertEqual(m.publications[-1], ("apply", expected_plans))
                self.assertLessEqual(m.published_prefix, len(m.plans))

    def test_fallback_only_when_primary_air_only_has_no_plans(self):
        m = ContractMachine({
            "primary": (Step(0, "sites", "none"),),
            "fallback": (Step(0, "pairs", "A-B", "airrail-A-B"),),
        }, stage="air_only")
        run_to_apply(m, 1)
        self.assertEqual([event[0] for event in m.events if event[0] == "fallback"], ["fallback"])
        self.assertEqual(m.plans, ["airrail-A-B"])
        self.assertEqual(m.final_count, 1)
        # Productive primary never triggers the fallback, even with AIR_ONLY.
        m = ContractMachine({"primary": (Step(0, "pairs", "X", "aironly-X"),),
                             "fallback": (Step(0, "pairs", "Y", "airrail-Y"),)},
                            stage="air_only")
        run_to_apply(m, 1)
        self.assertEqual(m.plans, ["aironly-X"])
        self.assertNotIn("fallback", [event[0] for event in m.events])

    def test_partial_is_next_dispatch_and_precedes_apply(self):
        m = ContractMachine({"primary": self.STREAM})
        self.assertEqual(m.tick(3), "yield")
        self.assertTrue(m.partial_pending)
        self.assertEqual(m.publications, [])
        self.assertEqual(m.tick(1), "partial")
        self.assertEqual(m.published_prefix, 1)
        self.assertEqual(m.tick(7), "done")
        self.assertEqual(m.tick(1), "apply")
        self.assertEqual([event[0] for event in m.publications], ["partial", "apply"])
        self.assertEqual(m.final_count, 1)

    def test_multiple_partial_publishes_keep_monotonic_prefix(self):
        m = run_to_apply(ContractMachine({"primary": self.STREAM}), 1)
        partials = [plans for kind, plans in m.publications if kind == "partial"]
        self.assertEqual(partials, [
            ("newpair-A-B",),
            ("newpair-A-B", "hubsite-H0-B"),
            ("newpair-A-B", "hubsite-H0-B", "newpair-B-C"),
        ])
        self.assertEqual(m.publications[-1], ("apply", partials[-1]))
        self.assertEqual(m.final_count, 1)

    def test_v93_large_winner_checks_first_big_after_each_small(self):
        kinds = ("large", "large", "small", "large", "small", "large")
        # The loop skips forward when *leaving* a large combo. It therefore
        # still VISITS the first large following each processed small combo.
        self.assertEqual(v93_combo_visit_order(kinds, 0, True), [0, 2, 3, 4, 5])
        self.assertEqual(v93_combo_visit_order(kinds, 0, False), [0])
        self.assertEqual(v93_combo_visit_order(kinds, -1, True), list(range(6)))
        self.assertEqual(v93_combo_visit_order(("large", "large"), 0, True), [0])

    def test_late_event_does_not_ack_its_revision(self):
        for layer in ("towns", "industries", "lines", "rail", "road", "air", "water"):
            with self.subTest(layer=layer):
                m = ContractMachine({"primary": self.STREAM})
                self.assertEqual(m.tick(3), "yield")
                m.event(layer)
                self.assertEqual(m.tick(1), "partial")
                run_to_apply(m, 2)
                self.assertEqual(m.ack[layer] + 1, m.revisions[layer])
                for other in set(m.ack) - {layer}:
                    self.assertEqual(m.ack[other], m.revisions[other])

    def test_save_load_drops_cursor_and_partial(self):
        m = ContractMachine({"primary": self.STREAM})
        self.assertEqual(m.tick(3), "yield")
        saved = m.roundtrip()
        self.assertEqual(set(saved), {"revisions", "ack", "last_catalog_month"})
        fresh = ContractMachine({"primary": self.STREAM},
                                revision_snapshot=saved["revisions"])
        run_to_apply(fresh, 2)
        self.assertEqual(fresh.plans, run_to_apply(
            ContractMachine({"primary": self.STREAM}), 20).plans)
        self.assertEqual(fresh.final_count, 1)


if __name__ == "__main__":
    unittest.main()
