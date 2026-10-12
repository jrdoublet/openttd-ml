#!/usr/bin/env python3
"""Contrat V147 (CD07/B) : phases du rebuild AIR comme entrées autonomes de _taskQueue.

Statique : réglage à 0, entrées ajoutées EN FIN de file (indices sauvegardés intacts),
état toujours porté par catalog (index 0), défaut 0 = chemin historique.
Simulation : un modèle Python de l'armement des phases vérifie qu'une seule phase est
active, que l'ordre scan → publish → scan … → apply est celui de l'architecture A, et
que le bootstrap sans portefeuille garde la priorité de la phase courante.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
MAX = 2147483647
PHASES = ("air_cat_scan", "air_cat_publish", "air_cat_apply")


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _body(source: str, signature: str) -> str:
    start = source.index(signature)
    depth = 0
    for pos in range(source.index("{", start), len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start : pos + 1]
    raise AssertionError(signature)


class StaticContract(unittest.TestCase):
    def test_setting_default_zero(self):
        info = _read("info.nut")
        block = info[info.index('name = "v147_air_catalog_tasks"') :][:600]
        for key in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(block, rf"{key} = 0\b")
        self.assertIn("V147_AIR_CATALOG_TASKS <- false;", _read("globals_pre.nut"))
        self.assertIn('GetSetting("v147_air_catalog_tasks")', _read("settings.nut"))

    def test_queue_extended_at_end_only_under_flag(self):
        sched = _read("scheduler_tasks.nut")
        body = _body(sched, "function OpexV147ExtendQueue(owner)")
        self.assertIn("!V147_AIR_CATALOG_TASKS", body)
        self.assertIn("V147_TASK_BASE = owner._taskQueue.len();", body)
        self.assertEqual(body.count(".append("), 3)
        self.assertNotIn(".insert(", body)
        main = _read("main.nut")
        # Après la lecture des réglages, avant toute réconciliation de rechargement.
        load = main.index("  OpexLoadSettings();\n  OpexV147ExtendQueue(this);")
        self.assertLess(load, main.index("this._reconcileAfterLoad();"))
        # La file historique reste inchangée (14 entrées, catalog en tête).
        queue = main[main.index("this._taskQueue = [") : main.index("];", main.index("this._taskQueue = ["))]
        names = re.findall(r'name = "([a-z0-9_]+)"', queue)
        self.assertEqual(names[0], "catalog")
        self.assertEqual(len(names), 14)
        for phase in PHASES:
            self.assertNotIn(phase, names)

    def test_state_stays_on_catalog_entry(self):
        sched = _read("scheduler_tasks.nut")
        self.assertNotIn("_v147AirRebuild", sched)
        phase = _body(sched, "function OpexAI::_dispatchAirCatalogPhase(task, year)")
        self.assertIn("this._taskQueue[0]", phase)
        self.assertIn("V147_IN_PHASE = true;", phase)
        self.assertIn("this._dispatchCatalog(catalogTask, year)", phase)
        self.assertIn("V147_IN_PHASE = false;", phase)

    def test_catalog_slot_yields_only_under_flag(self):
        sched = _read("scheduler_tasks.nut")
        cat = _body(sched, "function OpexAI::_dispatchCatalog(task, year)")
        self.assertIn("if (V147_AIR_CATALOG_TASKS && !V147_IN_PHASE) {", cat)
        requeue = _body(sched, "function OpexC78RequeueInitialCatalogSlice(owner, task)")
        self.assertIn("if (V147_AIR_CATALOG_TASKS) return;", requeue)
        start = _body(sched, "function OpexC78StartCatalogAirRebuild(")
        self.assertIn("if (V147_AIR_CATALOG_TASKS) OpexV147ArmPhases(owner);", start)

    def test_phase_tasks_dispatched_before_projects_null_gate(self):
        sched = _read("scheduler.nut")
        phase = sched.index('task.name == "air_cat_scan"')
        gate = sched.index("if (this._projects == null) {", sched.index('if (task.name == "catalog") {'))
        self.assertLess(phase, gate)

    def test_same_tick_continuation_routes_to_phase(self):
        for name in ("main.nut", "probes.nut"):
            src = _read(name)
            self.assertIn("local phaseTask = OpexV147PhaseTask(this);", src, name)
            self.assertIn("} else this._dispatchCatalog(queuedTask,", src, name)

    def test_c78_state_not_persisted(self):
        self.assertNotIn("c78AirRebuild", _read("persist.nut"))


def current_phase(s):
    if s is None:
        return None
    if s.get("partialPending"):
        return "air_cat_publish"
    if s["phase"] == "apply":
        return "air_cat_apply"
    return "air_cat_scan"


def arm(queue, base, state, projects, cycle, cursor):
    cur = current_phase(state)
    for i in range(base, base + 3):
        t = queue[i]
        if cur is not None and t["name"] == cur:
            t["enabled"] = True
            if projects is None:
                t["due"] = cycle
                cursor = i
            elif t["due"] > cycle + 1:
                t["due"] = cycle + 1
        else:
            t["enabled"] = False
            t["due"] = MAX
    return cursor


class ArmingModel(unittest.TestCase):
    def setUp(self):
        self.queue = [{"name": "catalog", "enabled": True, "due": 0}] + [
            {"name": f"t{i}", "enabled": True, "due": 0} for i in range(13)
        ] + [{"name": n, "enabled": False, "due": MAX} for n in PHASES]
        self.base = 14

    def active(self):
        return [t["name"] for t in self.queue[self.base :] if t["enabled"]]

    def test_single_active_phase_through_lifecycle(self):
        seq = []
        states = [
            {"phase": "primary", "partialPending": False},
            {"phase": "primary", "partialPending": True},
            {"phase": "primary", "partialPending": False},
            {"phase": "fallback", "partialPending": False},
            {"phase": "apply", "partialPending": True},
            {"phase": "apply", "partialPending": False},
            None,
        ]
        for s in states:
            arm(self.queue, self.base, s, projects={}, cycle=10, cursor=0)
            act = self.active()
            self.assertLessEqual(len(act), 1)
            seq.append(act[0] if act else None)
        self.assertEqual(seq, ["air_cat_scan", "air_cat_publish", "air_cat_scan",
                               "air_cat_scan", "air_cat_publish", "air_cat_apply", None])
        self.assertTrue(all(t["due"] == MAX for t in self.queue[self.base :]))

    def test_bootstrap_points_cursor_at_phase(self):
        cursor = arm(self.queue, self.base, {"phase": "primary"}, projects=None, cycle=3, cursor=0)
        self.assertEqual(cursor, self.base)
        self.assertEqual(self.queue[self.base]["due"], 3)

    def test_steady_state_one_step_per_round(self):
        arm(self.queue, self.base, {"phase": "primary"}, projects={}, cycle=7, cursor=0)
        self.assertEqual(self.queue[self.base]["due"], 8)
        # Le scheduler a déjà repoussé la phase exécutée : l'armement ne l'avance pas.
        self.queue[self.base]["due"] = 8
        arm(self.queue, self.base, {"phase": "primary"}, projects={}, cycle=7, cursor=0)
        self.assertEqual(self.queue[self.base]["due"], 8)


if __name__ == "__main__":
    unittest.main()
