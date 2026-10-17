"""Contrats de fusion : les correctifs de sauvegarde C69 et C76 coexistent."""
from pathlib import Path
import unittest
from test_c45_subsidy_persistence import function_body


class TestC69ReloadContract(unittest.TestCase):
    def test_saved_dates_survive_line_projection_change(self):
        root = Path(__file__).resolve().parents[1] / "ai/OpexAI"
        text = (root / "persist.nut").read_text(encoding="utf-8")
        save = function_body(text, "function OpexAI::Save()")
        load = function_body(text, "function OpexAI::Load(version, data)")
        reconcile = function_body(text, "function OpexAI::_reconcileAfterLoad()")
        for prefix in ("C69Build", "C75Pass"):
            key = prefix[0].lower() + prefix[1:] + "Dates"
            field = "_reload" + prefix + "Dates"
            self.assertIn(key + " = ", save)
            self.assertIn("this." + field, load)
            self.assertIn("this." + field, reconcile)
        self.assertLess(load.index("if (data == null) return;"), load.index('"c69BuildDates" in data'))
        self.assertIn("OpexC70RecomputeFactors(this._lines)", reconcile)
        self.assertLess(reconcile.index("this._lines = liveLines;"),
                        reconcile.index("OpexC70RecomputeFactors(this._lines);"))
        self.assertNotIn("C70_MODE_CALIBRATION", reconcile)
        for prefix, global_name in (("C69Build", "C69_BUILD_DATES"),
                                    ("C75Pass", "C75_PASS_DATES")):
            key = prefix[0].lower() + prefix[1:] + "Dates"
            field = "this._reload" + prefix + "Dates"
            self.assertIn(f'{field} = ("{key}" in data) ? data.{key} : null;', load)
            self.assertIn(f'if ({field} != null && typeof {field} == "array")', reconcile)
            self.assertIn(f"{global_name} = {field};", reconcile)
            self.assertIn(f"{field} = null;", reconcile)
        self.assertNotIn("C69_TRACK_BUILDS", text)
        self.assertNotIn("C75_TRACK_PASSES", text)
        self.assertNotIn("needsProjection", save)
        self.assertIn("saveLines = projectedLines;", save)

    def test_c80_restore_does_not_require_unloaded_settings(self):
        text = (Path(__file__).resolve().parents[1] / "ai/OpexAI/persist.nut").read_text(encoding="utf-8")
        load = function_body(text, "function OpexAI::Load(version, data)")
        self.assertIn("OpexLoadReactiveQueue(data.c80ReactiveQueue)", load)
        self.assertIn("OpexLoadActiveWorker(data.c80ActiveWorker)", load)

    def test_c76_saved_in_both_formats_and_restored_without_setting(self):
        root = Path(__file__).resolve().parents[1] / "ai/OpexAI"
        text = (root / "persist.nut").read_text(encoding="utf-8")
        save = function_body(text, "function OpexAI::Save()")
        load = function_body(text, "function OpexAI::Load(version, data)")
        reconcile = function_body(text, "function OpexAI::_reconcileAfterLoad()")
        self.assertNotIn("C76_REGEN_TARGETED", text)
        for obj in ("shortSave", "saveObj"):
            self.assertIn(f"{obj}.c76Revisions <- this._c76SaveRevisions();", save)
        self.assertIn('if ("c76Revisions" in data && data.c76Revisions != null)', load)
        self.assertIn("this._c76LoadRevisions(data.c76Revisions);", load)
        self.assertIn("this._c76ForceReloadRegen = true;", reconcile)
        orch = (root / "orchestrator.nut").read_text(encoding="utf-8")
        write = function_body(orch, "function OpexAI::_c76SaveRevisions()")
        read = function_body(orch, "function OpexAI::_c76LoadRevisions(data)")
        keys = ("towns", "industries", "lines", "engines_rail", "engines_road",
                "engines_air", "engines_water")
        for key in (*keys, *("ack_" + key for key in keys),
                    "modeConsumed", "modeConsumedRev", "lastRegenQuarter"):
            self.assertIn(key + " = ", write)
            self.assertIn('"' + key + '" in data', read)
        self.assertIn('if (data == null || typeof data != "table") return;', read)

    def test_retired_switches_absent_and_probe_guards_retained(self):
        root = Path(__file__).resolve().parents[1] / "ai/OpexAI"
        names = ("c69_decision_bottleneck", "c70_mode_calibration", "c75_multi_build",
                 "c76_regen_targeted", "v184_rail_search_slots")
        for path in root.glob("*.nut"):
            text = path.read_text(encoding="utf-8")
            for name in names:
                self.assertNotIn(name, text, str(path))
                self.assertNotIn(name.upper(), text, str(path))
        settings = (root / "settings.nut").read_text(encoding="utf-8")
        self.assertIn("if (C69_BOTTLENECK_PROBE)", settings)
        self.assertIn("OpexC73ResetLedger();", settings)
