"""PO-01 : contrats source et modèles de transitions, sans moteur OpenTTD.

Les modèles ne compilent pas Squirrel. Les copies générateurs doivent rester
identiques aux producteurs synchrones, aux checkpoints et retours eau près.
"""
from pathlib import Path
import re
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def read(name):
    return (AI / name).read_text(encoding="utf-8")


def body(source, signature):
    start = source.index(signature)
    depth = 0
    for pos in range(source.index("{", start), len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start:pos + 1]
    raise AssertionError(signature)


class SourceContract(unittest.TestCase):
    def test_boolean_off_setting_loaded_once(self):
        info = body(read("info.nut"), 'AddSetting({ name = "po01_reactive_split"')
        for key in ("min_value", "default_value", "easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(info, rf"{key} = 0\b")
        self.assertIn("max_value = 1", info)
        self.assertIn("AICONFIG_BOOLEAN", info)
        self.assertEqual(read("settings.nut").count('GetSetting("po01_reactive_split")'), 1)
        self.assertIn("PO01_REACTIVE_SPLIT <- false;", read("globals_pre.nut"))
        self.assertLessEqual(read("info.nut").count("AddSetting("), 100)

    def test_default_dispatch_retains_master_calls(self):
        dispatch = body(read("orchestrator.nut"), "function OpexAI::_dispatchReactiveIntention(")
        guard = body(dispatch, "if (PO01_REACTIVE_SPLIT)")
        self.assertIn("this._po01Pending = true;", guard)
        self.assertNotIn("OpexPO01Step", guard)
        self.assertIn("return true;", guard)
        legacy = dispatch[dispatch.index('      sp = PROBE_SPAN_TRACE'):dispatch.index('  /* C77')]
        self.assertIn('this._c76DoFullRegen("reactive", year);', legacy)
        self.assertIn('this._c80DoModeRegen(modes, "reactive", year);', legacy)
        self.assertIn('local modes = (this._projects != null) ? this._c80ModeRegenModes() : null;', legacy)
        self.assertLess(dispatch.index("if (PO01_REACTIVE_SPLIT)"), dispatch.index("this._c80ModeRegenModes()"))

    def test_no_new_default_calls_at_integration_sites(self):
        self.assertIn("if (PO01_REACTIVE_SPLIT) OpexPO01ExtendQueue(this);", read("main.nut"))
        self.assertIn('if (PO01_REACTIVE_SPLIT && task.name == "po01_reactive") return OpexPO01Step(this);', read("scheduler.nut"))
        self.assertIn('if (PO01_REACTIVE_SPLIT && this._po01Job != null) return false;', read("scheduler_tasks.nut"))

    def test_snapshot_precedes_work_and_ack_is_snapshot_only(self):
        step = body(read("po01_reactive.nut"), "function OpexPO01Step(")
        self.assertLess(step.index("OpexAC06CaptureRevisionNumbers(owner)"), step.index("owner._po01Job = {"))
        publish = body(read("po01_reactive.nut"), "function OpexPO01Publish(")
        self.assertIn("OpexAC06AcknowledgeSnapshot(owner, s.snapshot);", publish)
        self.assertNotIn("_c76AcknowledgeAllLayers", publish)
        self.assertNotIn("_c76GetLayerRevision", publish)
        self.assertLess(publish.index("owner._projects = nextProjects;"), publish.index("OpexAC06AcknowledgeSnapshot"))
        self.assertIn("if (owner._c76AnyLayerChanged()) owner._po01Pending = true;", publish)

    def test_coalescence_is_single_transient_job(self):
        src = read("po01_reactive.nut")
        step = body(src, "function OpexPO01Step(")
        start = body(step, "if (owner._po01Job == null)")
        self.assertIn("if (!owner._po01Pending) return false;", start)
        self.assertIn("owner._po01Pending = false;", start)
        self.assertNotIn("_enqueueReactive", step)
        self.assertIn("owner._po01LastTick == tick", step)
        self.assertIn("OpexOpsMeasureEnd(mark) < 4000", step)
        self.assertIn("AIController.GetTick() == tick", step)
        self.assertIn("AIController.GetOpsTillSuspend() > 2000", step)
        self.assertNotIn("Sleep(", src)

    def test_air_order_and_no_v143(self):
        src = read("po01_reactive.nut")
        step = body(src, "function OpexPO01Step(")
        self.assertLess(step.index("OpexPO01AirPending(owner)"), step.index("owner._po01Job = {"))
        self.assertIn('task.name == "catalog"', body(src, "function OpexPO01AirPending("))
        self.assertIn('task.c78AirRebuild != null', src)
        self.assertIn("owner._generationStage < OPEX_STAGE_COMPLETE", step)
        self.assertNotIn("_c76RotateFreight", src)
        self.assertNotIn("_c76LastRegenQuarter =", src)
        self.assertIn("OpexRegenerateAirProjectsSlice", step)
        self.assertNotIn("OpexAirPlans(", step)

    def test_only_finished_generation_published_on_current_capital(self):
        src = read("po01_reactive.nut")
        publish = body(src, "function OpexPO01Publish(")
        self.assertIn("local nextProjects = clone owner._projects;", publish)
        self.assertIn("nextProjects.stats = clone owner._projects.stats;", publish)
        self.assertIn("OpexRegenerateModeProjects(nextProjects", publish)
        self.assertIn("s.outputs[mode]", publish)
        self.assertIn("OpexReselectProjects(nextProjects, OpexAvailableCapital()", publish)
        self.assertIn("OpexInjectFleetProjects", publish)
        step = body(src, "function OpexPO01Step(")
        self.assertNotRegex(step, r"owner\._projects\s*=(?!=)")
        generate = body(read("projects_generation.nut"), "function OpexRegenerateModeProjects(")
        self.assertIn("completedGeneration != null ? completedGeneration", generate)
        self.assertIn("OpexApplyGeneratedModeProjects", generate)

    def test_load_discards_generators_before_null_data_and_keeps_safety(self):
        persist = read("persist.nut")
        load = body(persist, "function OpexAI::Load(")
        for line in ("this._po01Job = null;", "this._po01Pending = false;", "this._po01LastTick = -1;"):
            self.assertIn(line, load)
            self.assertLess(load.index(line), load.index("if (data == null) return;"))
        save = body(persist, "function OpexAI::Save(")
        self.assertNotIn("_po01", save)
        reconcile = body(persist, "function OpexAI::_reconcileAfterLoad(")
        self.assertIn("this._c76ForceReloadRegen = true;", reconcile)

    def test_air_returns_raw_generation_before_any_selection(self):
        sliced = body(read("projects_generation.nut"), "function OpexRegenerateAirProjectsSlice(")
        raw = body(sliced, "if (completedResult != null)")
        self.assertIn("completedResult.generated <- generated;", raw)
        self.assertNotIn("OpexApplyGeneratedModeProjects", raw)
        self.assertLess(sliced.index("if (completedResult != null)"), sliced.index("OpexApplyGeneratedModeProjects"))
        step = body(read("po01_reactive.nut"), "function OpexPO01Step(")
        self.assertIn('s.outputs.rawset("air", s.airResult.generated);', step)
        self.assertNotIn("OpexReselectProjects", step)

    def test_invalidation_cannot_deadlock_catalog(self):
        step = body(read("po01_reactive.nut"), "function OpexPO01Step(")
        invalid = body(step, "if (owner._c76ForceReloadRegen || owner._portfolioInvalidated)")
        self.assertIn("owner._po01Job = null;", invalid)
        self.assertIn("owner._po01Pending = true;", invalid)
        self.assertIn("return false;", invalid)
        self.assertLess(step.index("owner._c76Revisions == null"), step.index("OpexAC06CaptureRevisionNumbers"))

    def test_instrumentation_guarded_and_cause_uses_real_deps(self):
        orch = read("orchestrator.nut")
        self.assertIn("if (C39_INVALIDATION_PROBE || DECISION_LOG) OpexPO01ProbeBegin(this);", orch)
        desc = body(read("po01_reactive.nut"), "function OpexPO01Describe(")
        self.assertIn("owner._c76GetModeDeps(mode)", desc)
        self.assertIn("r.engines[mode] > a.engines[mode]", desc)
        for mode in ("rail", "road", "air", "water", "assembly_selection_fleet_subsidies"):
            self.assertIn(f'"mode", "{mode}"', read("projects.nut"))
        for layer in ("towns", "industries", "engines.air", "engines.rail", "engines.road", "engines.water", "cargos"):
            self.assertIn(f'"layer", "{layer}"', read("catalog.nut"))

    def test_generator_copies_are_mechanical(self):
        copied = read("po01_generators.nut")
        for file, name in (("candidates.nut", "OpexPaxCandidates"), ("candidates.nut", "OpexFreightCandidates"),
                           ("candidates.nut", "OpexRoadFreightCandidates"), ("builder_water.nut", "OpexWaterPlans")):
            with self.subTest(function=name):
                original = body(read(file), "function " + name + "(")
                variant_name = "OpexPO01" + name[4:]
                variant = body(copied, "function " + variant_name + "(")
                self.assertIn("yield null; // PO01_CHECKPOINT", variant)
                variant = variant.replace("\n    yield null; // PO01_CHECKPOINT", "")
                variant = variant.replace("function " + variant_name, "function " + name, 1)
                if name == "OpexWaterPlans":
                    original = original.replace("    return null;", "    return;", 1).replace("  return best;", "  return;", 1)
                self.assertEqual(variant, original)

    def test_no_reserved_identifiers_or_captured_local_closures(self):
        for name in ("po01_reactive.nut", "po01_generators.nut"):
            src = re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"', "", read(name), flags=re.S)
            self.assertNotRegex(src, r"\blocal\s+(?:clone|base|parent)\b")
            self.assertNotRegex(src, r"=\s*function\s*\(")


DEPS = {
    "air": {"towns", "engines.air", "lines"},
    "rail": {"towns", "industries", "engines.rail", "lines"},
    "road": {"towns", "industries", "engines.road", "lines"},
    "water": {"towns", "engines.water", "lines"},
    "fleet": {"lines", "engines.air", "engines.rail", "engines.road", "engines.water"},
}


def affected(layers):
    return {mode for mode, deps in DEPS.items() if deps.intersection(layers)}


class TransitionModel(unittest.TestCase):
    def test_air_engine_does_not_regenerate_land_modes(self):
        self.assertEqual(affected({"engines.air"}), {"air", "fleet"})

    def test_simultaneous_towns_lines_engine_requests_union_once(self):
        requests = ["towns", "lines", "engines.air", "towns"]
        self.assertEqual(affected(set(requests)), set(DEPS))
        self.assertEqual(len(affected(set(requests))), 5)

    def test_late_revision_is_not_acknowledged(self):
        current = {"towns": 4, "lines": 7, "engines.air": 2}
        snapshot = current.copy()
        current["lines"] += 2
        ack = {k: max(0, v) for k, v in snapshot.items()}
        self.assertEqual(ack["lines"], 7)
        self.assertGreater(current["lines"], ack["lines"])
        next_dirty = {k for k in current if current[k] > ack[k]}
        self.assertEqual(affected(next_dirty), set(DEPS))

    def test_publication_merges_latest_unaffected_mode(self):
        latest = {"air": ["old"], "rail": ["v217_new", "alternative"], "subsidy": ["new"]}
        finished = {"air": ["replacement"]}
        merged = {**latest, **finished}
        self.assertEqual(merged["rail"], latest["rail"])
        self.assertEqual(merged["subsidy"], ["new"])
        self.assertEqual(merged["air"], ["replacement"])

    def test_coalesced_late_intentions_form_next_generation(self):
        pending = True
        job = {"snapshot": 3} if pending else None
        pending = False
        for _ in range(10):
            pending = True
        self.assertEqual(job["snapshot"], 3)
        self.assertTrue(pending)

    def test_acknowledgement_cannot_go_backwards(self):
        # Une publication concurrente C77 peut avoir deja acquitte plus recent.
        snapshot = {"towns": 3, "lines": 7}
        acknowledged = {"towns": 5, "lines": 6}
        result = {key: max(acknowledged[key], snapshot[key]) for key in snapshot}
        self.assertEqual(result, {"towns": 5, "lines": 7})


if __name__ == "__main__":
    unittest.main()
