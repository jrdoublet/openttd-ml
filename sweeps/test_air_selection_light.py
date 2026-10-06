"""Lecteur/contrats source seulement : ces tests ne compilent pas Squirrel."""
import contextlib
import io
import json
from pathlib import Path
import re
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diag_air_selection_light as light


def log(body, stamp="1970-1-1", owner=0):
    return f"dbg: [script:4] [{owner}] [I] OPEX {stamp} {body}"


def edge(kind, inv=1, gen=1, index=1, day=10, tick=100, extra="", owner=0, stamp="1970-1-1"):
    return log(f"AIR_LIGHT v=1 inv={inv} gen={gen} slice={index} origin=1 "
               f"sliced=1 target=-1 band=0 edge={kind} day={day} tick={tick} {extra}", stamp, owner)


def pair(inv=1, gen=1, index=1, start=10, stop=12, tick=100, end_tick=174,
         extra="complete=1 ops=123 sites_ops=100 sites_ticks=60 sites_days=2 sites_calls=1"):
    return [edge("enter", inv, gen, index, start, tick),
            edge("exit", inv, gen, index, stop, end_tick, extra)]


def analyze(*lines):
    return light.audit_text("\n".join(lines), "fixture.log")


class ReaderTests(unittest.TestCase):
    def test_empty_is_missing_not_zero(self):
        result = analyze("no telemetry")
        self.assertEqual(result["streams"], [])
        self.assertEqual(result["raw_legacy_publications"], [])

    def test_absent_measures_are_null(self):
        r = analyze(*pair(extra="complete=1"))["streams"][0]
        self.assertIsNone(r["slices"][0]["ops_proxy"])
        self.assertIsNone(r["slices"][0]["phases"]["sites"]["ops_proxy"])
        self.assertIsNone(r["generations"][0]["slice_ops_sum"])

    def test_explicit_zero_preserved(self):
        r = analyze(*pair(start=10, stop=10, tick=0, end_tick=0,
                          extra="complete=1 ops=0 sites_ops=0 sites_ticks=0 sites_days=0 sites_calls=1"))
        rec = r["streams"][0]["slices"][0]
        self.assertEqual([rec[k] for k in ("days", "ticks", "ops_proxy")], [0, 0, 0])
        self.assertEqual(rec["phases"]["sites"]["ops_proxy"], 0)

    def test_truncated_and_negative_measures_not_zero(self):
        r = analyze(*pair(extra="complete=1 ops=12x sites_ops=-1"))["streams"][0]
        self.assertIsNone(r["slices"][0]["ops_proxy"])
        self.assertIsNone(r["slices"][0]["phases"]["sites"]["ops_proxy"])

    def test_unclosed_enter(self):
        r = analyze(edge("enter"))["streams"][0]
        self.assertEqual(r["coverage"]["paired"], 0)
        self.assertFalse(r["generations"][0]["complete"])
        self.assertIsNone(r["generations"][0]["days"])

    def test_orphan_exit(self):
        r = analyze(edge("exit", extra="complete=1 ops=99"))["streams"][0]
        self.assertIsNone(r["slices"][0]["ops_proxy"])
        self.assertFalse(r["generations"][0]["complete"])

    def test_exact_replay_not_double_counted(self):
        r = analyze(*pair(), *pair())["streams"][0]
        self.assertEqual(r["coverage"]["duplicate_lines"], 2)
        self.assertEqual(r["coverage"]["complete_generations"], 1)
        self.assertEqual(r["generations"][0]["slice_ops_sum"], 123)

    def test_conflicting_repeat_rejected(self):
        r = analyze(*pair(), *pair(start=13, stop=14, tick=200, end_tick=220))["streams"][0]
        self.assertEqual(r["coverage"]["paired"], 0)
        self.assertFalse(r["generations"][0]["complete"])

    def test_different_invocations_not_deduplicated(self):
        r = analyze(*pair(), *pair(inv=2, gen=2))["streams"][0]
        self.assertEqual(r["coverage"]["complete_generations"], 2)

    def test_different_generations_cannot_pair(self):
        r = analyze(edge("enter"), edge("exit", gen=2, extra="complete=1 ops=5"))["streams"][0]
        self.assertEqual(r["coverage"]["paired"], 0)

    def test_conflicting_pair_taints_both_generations(self):
        r = analyze(edge("enter"), edge("exit", gen=2, extra="complete=1 ops=5"),
                    *pair(inv=2, gen=2))["streams"][0]
        self.assertTrue(all(not g["complete"] for g in r["generations"]))

    def test_missing_clocks_do_not_use_envelope_date(self):
        lines = [re.sub(r" day=\d+ tick=\d+", "", line) for line in pair()]
        rec = analyze(*lines)["streams"][0]["slices"][0]
        self.assertIsNone(rec["days"])
        self.assertIsNone(rec["ticks"])
        self.assertEqual(rec["ops_proxy"], 123)

    def test_tick_rewind_inside_invocation_rejected(self):
        r = analyze(*pair(tick=100, end_tick=1))["streams"][0]
        self.assertFalse(r["generations"][0]["complete"])
        self.assertIsNone(r["slices"][0]["ops_proxy"])

    def test_overlapping_slices_censor_generation(self):
        r = analyze(*pair(extra="complete=0 ops=4"), *pair(inv=2, index=2))["streams"][0]
        self.assertFalse(r["generations"][0]["complete"])

    def test_lifetime_is_not_sum_of_slices(self):
        a = pair(stop=11, end_tick=110, extra="complete=0 ops=30")
        b = pair(inv=2, index=2, start=20, stop=21, tick=200, end_tick=215,
                 extra="complete=1 ops=40")
        gen = analyze(*a, *b)["streams"][0]["generations"][0]
        self.assertTrue(gen["complete"])
        self.assertEqual((gen["days"], gen["ticks"]), (11, 115))
        self.assertEqual((gen["slice_days_sum"], gen["slice_ticks_sum"], gen["slice_ops_sum"]), (2, 25, 70))

    def test_missing_middle_slice_censors_generation(self):
        r = analyze(*pair(extra="complete=0 ops=5"), *pair(inv=3, index=3))["streams"][0]
        self.assertEqual(r["coverage"]["paired"], 2)
        self.assertFalse(r["generations"][0]["complete"])
        self.assertIsNone(r["generations"][0]["slice_ops_sum"])

    def test_missing_start_and_finish_censor(self):
        for lines in (pair(index=2), pair(extra="complete=0 ops=5")):
            self.assertFalse(analyze(*lines)["streams"][0]["generations"][0]["complete"])

    def test_origin_unknown_censors(self):
        lines = [s.replace("origin=1", "origin=0") for s in pair()]
        self.assertFalse(analyze(*lines)["streams"][0]["generations"][0]["complete"])

    def test_reload_and_rewind_are_barriers(self):
        for marker in (log("LOAD_RECONCILE saved=1"), log("TASK name=catalog", "1969-12-31")):
            r = analyze(edge("enter"), marker, edge("exit", extra="complete=1 ops=1"))
            self.assertEqual(len(r["streams"]), 2)
            self.assertTrue(all(s["coverage"]["paired"] == 0 for s in r["streams"]))

    def test_reload_reused_invocation_id_is_new_session(self):
        r = analyze(*pair(), log("LOAD_RECONCILE saved=1"), *pair())
        self.assertEqual(len(r["streams"]), 2)
        self.assertTrue(all(s["coverage"]["complete_generations"] == 1 for s in r["streams"]))

    def test_companies_never_join(self):
        r = analyze(edge("enter", owner=0), edge("exit", owner=1, extra="complete=1 ops=1"))
        self.assertEqual(len(r["streams"]), 2)
        self.assertTrue(all(s["coverage"]["paired"] == 0 for s in r["streams"]))

    def test_source_namespaces_are_distinct(self):
        a = light.audit_text(pair()[0], "save#phase_a")
        b = light.audit_text(pair()[1], "save#phase_b")
        self.assertEqual(a["streams"][0]["coverage"]["paired"], 0)
        self.assertEqual(b["streams"][0]["coverage"]["paired"], 0)

    def test_units_never_derive_days_from_ticks_or_ops(self):
        rec = analyze(*pair())["streams"][0]["slices"][0]
        self.assertEqual((rec["days"], rec["ticks"], rec["ops_proxy"]), (2, 74, 123))
        self.assertEqual(light.UNITS["ops_proxy"], "OpexOpsMeasure_convention_not_CPU_time")

    def test_legacy_both_channels_kept_unjoined(self):
        r = analyze(log("AIR_PLAN_PERF scan=1 total_ops=100 ticks=148 days=2"),
                    "dbg: [script:4] [0] [I] AIR_PLAN_PERF: total_ops=100 ticks=148 days=2")
        self.assertEqual(r["streams"][0]["coverage"]["complete_generations"], 0)
        self.assertIsNone(r["raw_legacy_publications"][0]["days"])
        self.assertEqual(r["raw_legacy_publications"][0]["legacy_days_tick74"], 2)

    def test_parent_and_child_costs_not_summed(self):
        rec = analyze(*pair())["streams"][0]
        self.assertEqual(rec["generations"][0]["slice_ops_sum"], 123)
        self.assertEqual(rec["slices"][0]["phases"]["sites"]["ops_proxy"], 100)

    def test_selection_coverage_depends_on_path(self):
        r = analyze(*(log(f"CATALOG_COST path={p} selection_ops=0 reselect_ops=50")
                      for p in ("full", "mode", "reselect")))["streams"][0]
        self.assertEqual([c["selection_ops_proxy"] for c in r["catalog_publications"]], [0, None, None])
        self.assertEqual(r["coverage"]["complete_generations"], 0)

    def test_invalid_schema_and_identity(self):
        r = analyze(edge("enter").replace("v=1", "v=2"), edge("enter", inv=0))["streams"][0]
        self.assertEqual(r["coverage"]["invocations"], 0)
        self.assertEqual(len(r["issues"]), 2)

    def test_output_scope_and_no_overwrite(self):
        with self.assertRaises(ValueError):
            light.run([], light.ROOT / "outside")
        with self.assertRaises(ValueError):
            light.run([], light.OUTPUT_ROOT)
        with patch.object(Path, "exists", return_value=True):
            with self.assertRaises(FileExistsError):
                light.run([], light.OUTPUT_ROOT / "existing")

    def test_plan_no_engine_or_output(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            light.main(["--plan"])
        plan = json.loads(out.getvalue())
        self.assertEqual(plan["arms"], {"reference": "OpexAI", "light": "OpexAI[catalog_cost_probe=1]"})
        self.assertTrue(plan["harness_kwargs"]["force_debug"])
        self.assertIn("--probe", plan["forbidden_cli"])


class SourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (light.ROOT / "ai/OpexAI/air_planning.nut").read_text(encoding="utf-8")
        cls.wrapper = cls.source[cls.source.index("function OpexAirPlans(catalog,"):]

    def test_gate_declared_and_loaded_existing_default_off(self):
        root = light.ROOT / "ai/OpexAI"
        self.assertIn("CATALOG_COST_PROBE <- false;", (root / "globals_pre.nut").read_text())
        self.assertIn('CATALOG_COST_PROBE = AIController.GetSetting("catalog_cost_probe") != 0;',
                      (root / "settings.nut").read_text())
        self.assertIn("CATALOG_COST_PROBE ? OpexAirLightBegin", self.wrapper)
        self.assertIn("OPEX_AIR_LIGHT_SEQ <- 0;", self.source)

    def test_no_candidate_or_physical_work_in_probe_helpers(self):
        block = self.source[self.source.index("OPEX_AIR_LIGHT_SEQ <-"):self.source.index("function OpexAirPlansPrepare")]
        for forbidden in ("OpexDecide(", "OpexAirEconomics(", "OpexAirFindSite(", "Sleep(",
                          "DECISION_LOG", "C121_AIR_ECONOMICS", "GetSetting("):
            self.assertNotIn(forbidden, block)
        self.assertEqual(block.count("OpexAirLightLog(light.identity"), 1)
        self.assertEqual(block.count("OpexAirLightLog(fields);"), 1)

    def test_business_helpers_called_once_and_in_order(self):
        funcs = ("Prepare", "FindSites", "NewPairs", "DiscoverHubs", "HubToSite", "HubToHub", "Finalize")
        indices = []
        for name in funcs:
            call = "OpexAirPlans" + name + "(ctx"
            self.assertEqual(self.wrapper.count(call), 1)
            indices.append(self.wrapper.index(call))
        self.assertEqual(indices, sorted(indices))
        self.assertEqual(set(re.findall(r'OpexAirLightPhaseEnd\(light, "([a-z_]+)"', self.wrapper)), set(light.PHASES))

    def test_all_early_returns_close_measure(self):
        self.assertEqual(self.wrapper.count("return ctx.bestPlan;"), 5)
        for reason in ("prepare_return", "sites_yield", "pairs_yield", "hub_site_yield", "hub_hub_yield", "done"):
            self.assertRegex(self.wrapper, r'OpexAirLightEnd\(light, [^;]+"' + reason + r'"\);')

    def test_existing_selection_measure_not_reimplemented(self):
        source = (light.ROOT / "ai/OpexAI/projects.nut").read_text(encoding="utf-8")
        self.assertIn("stats.selectionOpcodes <- OpexOpsMeasureEnd(opsMark);", source)
        self.assertIn("cost.selectionOps += stats.selectionOpcodes;", source)
        self.assertNotIn("selectionOpcodes", self.wrapper)


if __name__ == "__main__":
    unittest.main()