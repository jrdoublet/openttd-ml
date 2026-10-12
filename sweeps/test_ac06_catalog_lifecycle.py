"""AC-06: C78 catalogue scheduler / C76 acknowledgements / Save-Load.

Source contracts plus a deliberately limited deterministic transition model.
No Squirrel VM is executed and no economic/opcode parity is claimed.
"""

from dataclasses import dataclass, field
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
def read(name):
    return (ROOT / "ai/OpexAI" / name).read_text(encoding="utf-8")


SCHED = read("scheduler_tasks.nut")
PERSIST = read("persist.nut")
MAIN = read("main.nut")
ORCH = read("orchestrator.nut")


def fn(source, signature):
    start = source.index(signature)
    begin = source.index("{", start)
    level = 0
    for pos in range(begin, len(source)):
        if source[pos] == "{":
            level += 1
        elif source[pos] == "}":
            level -= 1
            if level == 0:
                return source[start:pos + 1]
    raise AssertionError(f"Unterminated function: {signature}")


START = fn(SCHED, "function OpexC78StartCatalogAirRebuild(")
CONTINUE = fn(SCHED, "function OpexC78ContinueCatalogAirRebuild(")
PARTIAL = fn(SCHED, "function OpexC78PublishPartialAir(")
APPLY = fn(SCHED, "function OpexC78ApplyAir(")
DISPATCH = fn(SCHED, "function OpexAI::_dispatchCatalog(")
TICK = fn(MAIN, "function OpexAI::Start(")
SAVE = fn(PERSIST, "function OpexAI::Save()")
LOAD = fn(PERSIST, "function OpexAI::Load(")
RECONCILE = fn(PERSIST, "function OpexAI::_reconcileAfterLoad(")
ACK = fn(ORCH, "function OpexAI::_c76AcknowledgeAllLayers(")
CHANGED = fn(ORCH, "function OpexAI::_c76AnyLayerChanged(")
BUMPL = fn(ORCH, "function OpexAI::_c76BumpLayer(")


@dataclass
class Scan:
    ym: int
    stage: str = "complete"
    phase: str = "primary"
    band: str = "primary"
    cursor: dict = field(default_factory=dict)
    plans: list = field(default_factory=list)
    partial_pending: bool = False
    last_published: int = 0
    published: bool = False
    c76_full: bool = True
    c76_quarter: int = 1970
    start_rev: int = 0


@dataclass
class Model:
    snapshot_ack: bool = True
    catalog_month: int = -1
    scan: Scan | None = None
    projects: bool = False
    invalidated: bool = False
    revisions: int = 0
    acknowledged: int = 0
    c76_last_quarter: int = -1
    reload_due: bool = False
    started: int = 0
    partial_publishes: int = 0
    final_publishes: int = 0
    produced: list = field(default_factory=list)

    def start(self, ym, stage="complete", year=1970):
        assert self.scan is None
        self.scan = Scan(ym=ym, stage=stage, c76_quarter=year,
                         start_rev=self.revisions)
        self.started += 1

    def event(self):
        self.revisions += 1
        self.invalidated = True

    def tick(self, ym, *, plans=(), done=False):
        """Implement C78's branch priority; planned outputs are a frozen stub."""
        if self.scan is None:
            self.start(ym, year=(ym - 1) // 12)
        s = self.scan
        if s.partial_pending:
            self.projects = True
            self.invalidated = False
            s.published = True
            s.last_published = len(s.plans)
            s.partial_pending = False
            self.partial_publishes += 1
            return "partial"
        if s.phase == "apply":
            self.projects = True
            self.invalidated = False
            self.final_publishes += 1
            self.catalog_month = s.ym
            if s.c76_full:
                # AC06 v2: cap acknowledgement at start-of-scan revision.
                # OFF preserves the original (unsafe) ACK-all path.
                self.acknowledged = (max(self.acknowledged, s.start_rev)
                                     if self.snapshot_ack else self.revisions)
                self.c76_last_quarter = s.c76_quarter
                self.reload_due = False
            self.scan = None
            return "apply"
        s.plans.extend(plans)
        self.produced.extend(plans)
        if not done:
            if len(s.plans) > s.last_published:
                s.partial_pending = True
            return "yield"
        if s.phase == "primary" and s.stage == "air_only" and not s.plans:
            s.phase, s.band, s.cursor = "fallback", "air_rail", {}
            return "fallback"
        s.phase = "apply"
        return "done"

    def save_load(self):
        """C78 cursor/projects not persisted; C76 revisions and dates persist."""
        persisted = (self.catalog_month, self.revisions, self.acknowledged)
        self.scan = None
        self.projects = False
        self.invalidated = True
        self.catalog_month, self.revisions, self.acknowledged = persisted
        self.reload_due = True


class AC06LifecycleTests(unittest.TestCase):
    def test_active_scan_precedes_cadence_capital_month_and_invalidation(self):
        self.assertLess(DISPATCH.index('if (("c78AirRebuild" in task)'),
                        DISPATCH.index("local date = AIDate.GetCurrentDate();"))
        self.assertLess(DISPATCH.index("OpexC78ContinueCatalogAirRebuild(this, task, year)"),
                        DISPATCH.index("local stale = false;"))
        self.assertIn("if (C121_CATALOG_INCREMENTAL && task.c78AirRebuild.published)", DISPATCH)
        self.assertIn("this._portfolioInvalidated = false;", DISPATCH)
        self.assertNotIn("delete task.c78AirRebuild;", DISPATCH)
        self.assertEqual(APPLY.count("delete task.c78AirRebuild;"), 1)
        self.assertIn("if (s.phase == \"apply\")", CONTINUE)
        self.assertIn("return OpexC78ApplyAir(owner, task, year, s);", CONTINUE)
        self.assertLess(APPLY.index("owner._lastCatalogMonth = s.ym;"),
                        APPLY.index("delete task.c78AirRebuild;"))

    def test_phases_partials_fallback_and_apply_are_disjoint(self):
        for token in (
            'if (("partialPending" in s) && s.partialPending)',
            'if (s.phase == "apply")',
            's.phase = "fallback";',
            's.cursor = {};',
            's.phase = "apply";',
        ):
            self.assertIn(token, CONTINUE)
        for token in ('s.lastPublishedCount = s.plans.len();',
                      's.partialPending = false;'):
            self.assertIn(token, PARTIAL)
        for token in ('owner._c76AcknowledgeAllLayers();',
                      'owner._c76LastRegenQuarter = s.c76Quarter;',
                      'owner._c76ForceReloadRegen = false;'):
            self.assertIn(token, APPLY)
        self.assertIn("return OpexC78PublishPartialAir(owner, s);", CONTINUE)
        self.assertLess(CONTINUE.index('if (("partialPending" in s) && s.partialPending)'),
                        CONTINUE.index('if (s.phase == "apply")'))
        self.assertLess(CONTINUE.index('if (s.phase == "apply")'),
                        CONTINUE.index('local liveOps = AIController.GetOpsTillSuspend();'))
        self.assertLess(CONTINUE.index('s.phase = "fallback";'),
                        CONTINUE.rindex('s.phase = "apply";'))

    def test_partial_scan_and_month_change_do_not_restart(self):
        for ym, event, partial in ((1970 * 12 + 1, False, False),
                                   (1970 * 12 + 1, True, True),
                                   (1970 * 12 + 12, True, True)):
            with self.subTest(ym=ym, event=event, partial=partial):
                m = Model()
                self.assertEqual(m.tick(ym, plans=[11] if partial else []), "yield")
                if event:
                    m.event()
                if partial:
                    self.assertEqual(m.tick(ym + 1), "partial")
                self.assertEqual(m.tick(ym + 1, plans=[12], done=True), "done")
                # New month/event still cannot create a competing C78 cursor.
                self.assertEqual(m.started, 1)
                self.assertEqual(m.tick(ym + 2), "apply")
                self.assertEqual(m.started, 1)
                self.assertEqual(m.final_publishes, 1)
                self.assertEqual(m.catalog_month, ym)
                self.assertEqual(m.produced, [11, 12] if partial else [12])

    def test_fallback_uses_new_cursor_exactly_once(self):
        m = Model()
        m.start(1970 * 12 + 1, "air_only")
        self.assertEqual(m.tick(m.scan.ym, done=True), "fallback")
        self.assertEqual(m.scan.band, "air_rail")
        self.assertEqual(m.scan.cursor, {})
        self.assertEqual(m.tick(m.scan.ym + 1, plans=[91]), "yield")
        self.assertEqual(m.tick(m.scan.ym + 1), "partial")
        self.assertEqual(m.tick(m.scan.ym + 1, done=True), "done")
        self.assertEqual(m.tick(m.scan.ym + 1), "apply")
        self.assertEqual(m.started, 1)
        self.assertEqual(m.partial_publishes, 1)
        self.assertEqual(m.final_publishes, 1)

    def test_missed_c76_revision_if_event_arrives_after_scan_snapshot(self):
        """Reproduction of the ACK-all race at transition level, NOT a VM trace."""
        m = Model()
        ym = 1970 * 12 + 1
        m.start(ym, year=1970)
        self.assertEqual(m.tick(ym, plans=[21]), "yield")
        self.assertEqual(m.tick(ym), "partial")
        m.event()  # e.g. industry/town/engine change after catalog.refresh
        self.assertGreater(m.revisions, m.acknowledged)
        self.assertEqual(m.tick(ym, done=True), "done")
        self.assertEqual(m.tick(ym), "apply")
        # AC06 v2: late revision stays pending after apply.
        self.assertGreater(m.revisions, m.acknowledged)
        self.assertFalse(m.invalidated)
        self.assertEqual(m.c76_last_quarter, 1970)
        # Historical ACK-all code remains reachable when the feature is OFF.
        self.assertIn("this._c76AckRevisions.towns = this._c76Revisions.towns;", ACK)
        self.assertIn("this._c76AckRevisions.industries = this._c76Revisions.industries;", ACK)
        self.assertIn("this._c76AckRevisions.lines = this._c76Revisions.lines;", ACK)
        self.assertIn("this._c76Revisions.towns > this._c76AckRevisions.towns", CHANGED)
        self.assertIn('this._c76BumpLayer("towns", true);', read("events.nut"))
        self.assertIn("c76StartRevisions = AC06_C76_SNAPSHOT_ACK && c76Full", START)
        self.assertIn("OpexAC06AcknowledgeSnapshot(owner, s.c76StartRevisions);", APPLY)
        legacy = Model(snapshot_ack=False)
        legacy.start(ym, year=1970)
        legacy.event()
        legacy.tick(ym, done=True)
        legacy.tick(ym)
        self.assertEqual(legacy.revisions, legacy.acknowledged)

    def test_save_load_recreates_without_serializing_partial_or_floats(self):
        for token in ("lastCatalogMonth = this._lastCatalogMonth",
                      "saveObj.c76Revisions <- this._c76SaveRevisions();",
                      "shortSave.c76Revisions <- this._c76SaveRevisions();"):
            self.assertIn(token, SAVE)
        self.assertNotIn("c78AirRebuild", SAVE)
        self.assertNotIn("c78AirRebuild", LOAD)
        self.assertIn("this._c76LoadRevisions(data.c76Revisions);", LOAD)
        self.assertIn("this._c76ForceReloadRegen = true;", RECONCILE)
        self.assertIn("if (this._loadedFromSave) this._reconcileAfterLoad();", MAIN)
        m = Model()
        ym = 1970 * 12 + 5
        m.start(ym)
        m.tick(ym, plans=[77])
        m.tick(ym)
        m.save_load()
        self.assertIsNone(m.scan)
        self.assertFalse(m.projects)
        self.assertTrue(m.reload_due)
        self.assertEqual(m.tick(ym + 1), "yield")
        self.assertEqual(m.started, 2)
        self.assertEqual(m.tick(ym + 1, done=True), "done")
        self.assertEqual(m.tick(ym + 1), "apply")
        self.assertFalse(m.reload_due)
        self.assertEqual(m.catalog_month, ym + 1)

    def test_town_growth_or_build_events_do_not_cancel_active_generation(self):
        m = Model()
        m.start(1970 * 12 + 1)
        m.tick(m.scan.ym, plans=[1])
        for _ in range(4):
            m.event()
            m.tick(m.scan.ym + 1)
            m.tick(m.scan.ym + 1, plans=[2])
        self.assertEqual(m.started, 1)
        self.assertIsNotNone(m.scan)
        self.assertIn("this._processEvents();", MAIN)
        self.assertIn("if (C121_CATALOG_INCREMENTAL && task.c78AirRebuild.published)", DISPATCH)
        self.assertIn("owner._portfolioInvalidated = false;", PARTIAL)

    def test_same_tick_chain_has_worker_rail_and_tick_budget_guards(self):
        gate = fn(SCHED, "function OpexC121CatalogCanContinue(")
        for needle in ('owner._activeWorker == null', 'owner._railSearch == null',
                       'owner._railExpansion == null', 'AIController.GetTick() == continuationTick',
                       'AIController.GetOpsTillSuspend() > 2000;'):
            self.assertIn(needle, gate)
        self.assertIn("while (catalogPending && OpexC121CatalogCanContinue(this, continuationTick))", TICK)
        self.assertIn("this._runOrchestratorTick();", TICK)


if __name__ == "__main__":
    unittest.main()
