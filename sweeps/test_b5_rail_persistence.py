"""Contrats statiques B5 : expansion rail et persistance/reload.

Ces tests ne simulent pas le moteur OpenTTD. Ils verrouillent les propriétés de structure que le
round-trip réel ne peut pas forcer à une frontière d'instruction précise : projection sérialisable,
frontière de commit, abandon fail-closed des objets VM et réarmement des files C41.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def source(name):
    return (AI / name).read_text(encoding="utf-8")


def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1 : pos]
    raise AssertionError(f"corps non fermé: {signature}")


class TestB5RailPersistence(unittest.TestCase):
    def setUp(self):
        self.main = source("main.nut")
        self.persist = source("persist.nut")
        self.rail = source("task_rail.nut")
        self.info = source("info.nut")

    def test_approach_radius_is_defined_from_existing_local_window(self):
        self.assertIn("const RAIL_EXPAND_APPROACH_TILES = 8;", self.main)
        self.assertEqual(self.rail.count("RAIL_EXPAND_APPROACH_TILES"), 2)
        self.assertIn("maxDistance=8", self.main)

    def test_default_path_still_has_expansion_disabled(self):
        setting = re.search(
            r'name\s*=\s*"rail_expand".*?custom_value\s*=\s*(\d+)',
            self.info,
            re.S,
        )
        self.assertIsNotNone(setting)
        self.assertEqual(setting.group(1), "0")

    def test_expansion_descriptor_is_projected_and_contains_no_live_pathfinder(self):
        save_projection = function_body(self.persist, "function OpexSaveRailExpansion(state)")
        for field in (
            "lineId", "vehicle", "wagonId", "oldWagons", "newWagons",
            "oldTrainLength", "oldExpansionCount", "decisionYear",
            "newSpeedMilli", "newOneWayMilliDays", "decisionDate", "waitDays",
            "startDate", "phase", "dispatchAttempts", "resumeAttempts",
            "temporaryOrder", "temporaryOrderPosition", "commitStage",
            "pendingWagon", "ops", "cost",
        ):
            self.assertIn(field, save_projection)
        self.assertNotIn("pathfinder", save_projection)
        self.assertNotIn("segmented", save_projection)
        self.assertNotIn("newSpeed =", save_projection)
        self.assertNotIn("newOneWayDays =", save_projection)

    def test_save_marks_only_presence_of_live_search(self):
        save = function_body(self.persist, "function OpexAI::Save()")
        self.assertIn("railSearchPending = this._railSearch != null", save)
        self.assertNotIn("dynamicBatchPending", save)
        self.assertNotIn("railSearch = this._railSearch", save)
        self.assertNotIn("dynamicBatch = this._dynamicBatch", save)
        self.assertIn("stateVersion = 2", save)

    def test_old_state_version_load_is_field_guarded(self):
        load = function_body(self.persist, "function OpexAI::Load(version, data)")
        for field in (
            "railExpansion", "railSearchPending", "dynamicBatchPending",
            "c41RailSignalLines", "c41RailJunctionLines",
        ):
            self.assertIn(f'"{field}" in data', load)
        self.assertNotIn('if ("stateVersion" in data)', load)
        self.assertNotIn("data.stateVersion", load)

    def test_commit_stages_surround_build_and_move(self):
        cont = function_body(self.rail, "function OpexAI::_continueRailExpansion()")
        positions = [
            cont.index('state.commitStage = "build_started"'),
            cont.index("AIVehicle.BuildVehicle"),
            cont.index('state.commitStage = "wagon_built"'),
            cont.index("AIVehicle.MoveWagon"),
            cont.index('state.commitStage = "wagon_moved"'),
            cont.index('state.commitStage = "metadata_done"'),
            cont.index('state.phase = "resume"'),
        ]
        self.assertEqual(positions, sorted(positions))

    def test_ambiguous_build_never_rebuilds_on_reload(self):
        reconcile = function_body(
            self.persist, "function OpexAI::_reconcileRailExpansionAfterLoad()"
        )
        marker = 'if (!physicalCommitted && state.commitStage == "build_started")'
        start = reconcile.index(marker)
        branch = reconcile[start : reconcile.index("\n  }", start) + 4]
        self.assertIn("_abortPersistedRailExpansion", branch)
        executable = "\n".join(
            line for line in reconcile.splitlines()
            if not line.lstrip().startswith(("*", "/*"))
        )
        self.assertNotIn("AIVehicle.BuildVehicle(", executable)

    def test_known_pending_wagon_is_reused_not_rebuilt(self):
        reconcile = function_body(
            self.persist, "function OpexAI::_reconcileRailExpansionAfterLoad()"
        )
        self.assertIn('state.commitStage == "wagon_built"', reconcile)
        self.assertIn("AIVehicle.MoveWagon(pending, 0, state.vehicle, 0)", reconcile)
        self.assertIn("result.pending_recovered++", reconcile)

    def test_resume_does_not_toggle_already_running_train(self):
        reconcile = function_body(
            self.persist, "function OpexAI::_reconcileRailExpansionAfterLoad()"
        )
        completed = reconcile[
            reconcile.index("if (physicalCommitted)") :
            reconcile.index("if (state.temporaryOrder)")
        ]
        self.assertIn("if (!AIVehicle.IsStoppedInDepot(state.vehicle))", completed)
        self.assertIn("this._railExpansion = null", completed)
        executable = "\n".join(
            line for line in completed.splitlines()
            if not line.lstrip().startswith(("*", "/*"))
        )
        self.assertNotIn("AIVehicle.StartStopVehicle(", executable)

    def test_transient_search_forces_clean_portfolio_rebuild(self):
        reconcile = function_body(self.persist, "function OpexAI::_reconcileAfterLoad()")
        self.assertIn("this._railSearch = null", reconcile)
        self.assertNotIn("_dynamicBatch", reconcile)
        self.assertIn("this._projects = null", reconcile)
        self.assertIn("this._portfolioInvalidated = true", reconcile)
        self.assertIn('task.name == "catalog"', reconcile)
        self.assertIn("task.dueCycle = this._taskCycle", reconcile)

    def test_c41_queues_are_persisted_filtered_and_rearmed(self):
        save = function_body(self.persist, "function OpexAI::Save()")
        reconcile = function_body(self.persist, "function OpexAI::_reconcileAfterLoad()")
        filter_queue = function_body(
            self.persist, "function OpexAI::_filterPersistedRailRepairQueue(source)"
        )
        rearm = function_body(
            self.persist, "function OpexAI::_rearmPersistedRailRepairTasks()"
        )
        self.assertIn("c41RailSignalLines = OpexCopyBoolTable", save)
        self.assertIn("c41RailJunctionLines = OpexCopyBoolTable", save)
        self.assertIn('line.mode == "rail"', filter_queue)
        self.assertIn("line.doubleTrack == 1", filter_queue)
        self.assertIn("_filterPersistedRailRepairQueue", reconcile)
        self.assertIn('task.name == "c41_rail_signals"', rearm)
        self.assertIn('task.name == "c41_rail_junction"', rearm)
        self.assertIn("task.enabled = active", rearm)
        self.assertIn("active ? this._taskCycle : 2147483647", rearm)


if __name__ == "__main__":
    unittest.main()
