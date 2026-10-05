"""Accounting/source contracts and synthetic snapshots; NO Squirrel VM."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import re
import unittest
from unittest.mock import patch

from sweeps import parallel_fleet_amort_shadow as audit

ROOT = Path(__file__).resolve().parents[1]


def project(q=1, price=30019, profit=2000, observed=True):
    return {"mode": "fleet", "profitAnnual": profit, "profitIsObserved": observed,
            "capital": price * q, "budgetCapital": price * q + 1000,
            "revenueAnnual": profit, "roi": 123, "fundScore": 99,
            "payload": {"want": q, "planePrice": price, "line": {"mode": "air"}}}


def snapshot():
    p = project()
    context = {"budget": 100000, "finance_capital": 31019, "denominator": 31019,
               "calibration_factor": 1, "priority": 0, "early_slot_bonus_pct": 0,
               "revenue_annual": 2000, "admitted": True, "stable_index": 0, "quantity": 1}

    def values(profit, ctx):
        return {"context": deepcopy(ctx), "profitAnnual": profit,
                "calibratedProfitAnnual": profit,
                "score": max(0, profit) * 1000.0 / ctx["denominator"]}

    fleet = {"id": "fleet:1:r1", "category": "fleet_legacy", "mode": "fleet", "project": p,
             "baseline": values(2000, context), "alternative": values(500, context)}
    context.update(finance_capital=60000, denominator=60000, revenue_annual=3000, stable_index=1)
    air = {"id": "air:7:r3", "category": "new_link", "mode": "air",
           "baseline": values(3000, context), "alternative": values(3000, context)}
    return {"campaign": "synthetic", "arm": "shadow", "seed": 42, "repeat": 0,
            "company": 0, "phase": "fresh", "decision_id": "d1", "revision": 1,
            "date": "1971-05-01", "complete": True, "candidate_count": 2,
            "order_source": "selector", "comparison_scope": "fixed_admission",
            "all_admitted_before_limit": True,
            "settings": {"c84": False, "c85": False, "c121": False, "c122": False,
                         "c115": 1, "v92": False, "calibrated": True, "cadence_off": True},
            "candidates": [fleet, air], "baseline_order": [fleet["id"], air["id"]],
            "alternative_order": [air["id"], fleet["id"]]}


class ArithmeticTests(unittest.TestCase):
    def test_disabled_returns_none_even_for_missing_input(self):
        self.assertIsNone(audit.estimate_shadow(None))
        self.assertIsNone(audit.estimate_shadow(project()))

    def test_price_life_and_quantities_one_four(self):
        for q, expected in ((1, 1500), (4, 6003)):
            row = audit.estimate_shadow(project(q=q, profit=q * 2000), enabled=True)
            self.assertEqual(row["addedAmortAnnual"], expected)
            self.assertEqual(row["lifeYears"], 20)
            self.assertEqual(row["netProfitAnnual"], q * 2000 - expected)

    def test_v92_life_is_conditional_like_air_model(self):
        for enabled, age, life in ((False, 25, 20), (True, 25, 25), (True, 1, 20),
                                   (True, 0, 20), (True, -1, 20), (True, None, 20)):
            row = audit.estimate_shadow(project(), enabled=True, service_choice=enabled,
                                        plane={} if age is None else {"ageYears": age})
            self.assertEqual(row["lifeYears"], life)
            self.assertEqual(row["addedAmortAnnual"], 30019 // life)
        self.assertIsNone(audit.estimate_shadow(project(), enabled=True, service_choice=True))

    def test_reduction_four_to_one_recomputes_not_scales_net(self):
        full = project(q=4, profit=8000)
        first = audit.estimate_shadow(full, enabled=True)
        fitted = deepcopy(full)
        fitted["payload"]["want"] = 1
        # Exact legacy R1 division, after the already rounded per-plane estimate.
        fitted["profitAnnual"] = full["profitAnnual"] // full["payload"]["want"]
        reduced = audit.estimate_shadow(fitted, enabled=True)
        self.assertEqual(reduced["addedAmortAnnual"], 1500)
        self.assertEqual(reduced["netProfitAnnual"], 500)
        self.assertNotEqual(first["netProfitAnnual"] // 4, reduced["netProfitAnnual"])
        self.assertEqual(full["payload"]["want"], 4)

    def test_net_can_be_negative_or_zero(self):
        for profit, net in ((10, -1490), (1500, 0)):
            row = audit.estimate_shadow(project(profit=profit), enabled=True)
            self.assertEqual(row["netProfitAnnual"], net)

    def test_observation_r2_factors_half_one_one_and_half(self):
        for factor in (0.5, 1, 1.5, None):
            row = audit.estimate_shadow(project(), enabled=True, calibrated=True, factor=factor)
            self.assertEqual(row["profitSource"], "observed")
            self.assertEqual(row["calibratedProfitAnnual"], 500)

    def test_predictive_fallback_is_calibrated_after_subtracting_amort(self):
        for factor in (0, 0.5, 1, 1.5):
            row = audit.estimate_shadow(project(observed=False), enabled=True, calibrated=True, factor=factor)
            self.assertEqual(row["profitSource"], "predictive_fallback")
            self.assertEqual(row["calibratedProfitAnnual"], 500 * factor)
        self.assertIsNone(audit.estimate_shadow(project(observed=False), enabled=True, calibrated=True))

    def test_disabled_calibration_uses_no_factor(self):
        row = audit.estimate_shadow(project(observed=False), enabled=True, factor=1.5)
        self.assertEqual(row["calibratedProfitAnnual"], 500)

    def test_c84_c121_are_out_of_scope(self):
        for flags in ({"c84": True}, {"c121": True}, {"c84": True, "c121": True}):
            self.assertIsNone(audit.estimate_shadow(project(), enabled=True, **flags))

    def test_missing_bad_values_are_not_zero(self):
        for field, value in (("profitAnnual", None), ("profitAnnual", float("nan")),
                             ("profitAnnual", float("inf")), ("profitIsObserved", None),
                             ("profitIsObserved", 1), ("mode", "air")):
            p = project(); p[field] = value
            self.assertIsNone(audit.estimate_shadow(p, enabled=True))
        for field in ("want", "planePrice"):
            for value in (None, 0, -1, True, 1.5):
                p = project(); p["payload"][field] = value
                self.assertIsNone(audit.estimate_shadow(p, enabled=True))

    def test_no_effect_on_decision_fields_or_line(self):
        p = project()
        p["payload"]["line"].update(lastProfit=999999, predRunning=500000, predAmort=900000)
        old = deepcopy(p)
        row = audit.estimate_shadow(p, enabled=True)
        self.assertEqual(p, old)
        self.assertEqual(row["grossProfitAnnual"], 2000)
        self.assertEqual(row["addedAmortAnnual"], 1500)  # no airport / second running charge


class SnapshotTests(unittest.TestCase):
    def assert_blocked(self, e):
        row = audit.analyse_election(e)
        self.assertEqual(row["status"], "not_measurable", row)
        self.assertIsNone(row["inversions"])
        self.assertIsNone(row["winner_changed"])
        return row

    def test_complete_snapshot_consumes_selector_orders(self):
        e = snapshot(); old = deepcopy(e)
        row = audit.analyse_election(e)
        self.assertEqual(row["status"], "measured_selector_snapshot")
        self.assertEqual(row["inversions"], [["fleet:1:r1", "air:7:r3"]])
        self.assertEqual(row["fleet_vs_new_link_inversions"], row["inversions"])
        self.assertTrue(row["winner_changed"])
        self.assertEqual(e, old)

    def test_no_inversion_is_distinct_from_missing(self):
        e = snapshot()
        # C77 can keep the new link first in both orders despite fleet raw ROI.
        for side in ("baseline", "alternative"):
            e["candidates"][1][side]["context"]["priority"] = 2
        e["baseline_order"] = e["alternative_order"][:]
        row = audit.analyse_election(e)
        self.assertEqual(row["inversions"], [])
        self.assertFalse(row["winner_changed"])

    def test_truncated_unknown_or_missing_candidates(self):
        for key, value in (("complete", False), ("candidate_count", 3),
                           ("all_admitted_before_limit", False), ("baseline_order", ["fleet:1:r1"]),
                           ("order_source", "python_reconstruction"), ("candidates", None),
                           ("alternative_order", ["fleet:1:r1", "unknown"])):
            e = snapshot(); e[key] = value
            self.assert_blocked(e)

    def test_every_context_field_must_be_present_and_identical(self):
        for field in audit.CONTEXT:
            e = snapshot(); del e["candidates"][0]["alternative"]["context"][field]
            self.assert_blocked(e)
            e = snapshot(); e["candidates"][0]["alternative"]["context"][field] = None
            self.assert_blocked(e)

    def test_missing_id_or_duplicate_candidates(self):
        for field in audit.IDENTITY:
            e = snapshot(); del e[field]
            self.assert_blocked(e)
        e = snapshot(); e["candidates"][1]["id"] = e["candidates"][0]["id"]
        self.assert_blocked(e)

    def test_r2_wrong_effective_factor_rejected(self):
        e = snapshot()
        for side in ("baseline", "alternative"):
            e["candidates"][0][side]["context"]["calibration_factor"] = 0.5
        self.assertIn("r2_or_disabled_calibration_violation", self.assert_blocked(e)["blockers"])

    def test_stale_full_lot_value_rejected_after_r1(self):
        e = snapshot(); e["candidates"][0]["project"]["payload"]["want"] = 4
        self.assertIn("accounting_or_r1_mismatch", self.assert_blocked(e)["blockers"])

    def test_unchanged_new_link_and_score_validation(self):
        e = snapshot(); e["candidates"][1]["alternative"]["profitAnnual"] -= 1
        self.assertIn("non_legacy_candidate_changed", self.assert_blocked(e)["blockers"])
        e = snapshot(); e["candidates"][0]["alternative"]["score"] = 9999
        self.assertIn("inconsistent_score", self.assert_blocked(e)["blockers"])

    def test_protected_settings_and_marginal_categories(self):
        for name in ("c84", "c85", "c121", "c122"):
            e = snapshot(); e["settings"][name] = True
            self.assert_blocked(e)
        e = snapshot(); e["settings"]["c115"] = 0
        self.assert_blocked(e)
        e = snapshot(); e["settings"]["cadence_off"] = False
        self.assert_blocked(e)
        e = snapshot(); e["candidates"][0]["category"] = "fleet_c121"
        self.assert_blocked(e)

    def test_same_election_not_counted_twice_and_phases_not_merged(self):
        e = snapshot()
        payload = {"schema": audit.SCHEMA, "elections": [e, deepcopy(e)]}
        result = audit.analyse_payload(payload)
        self.assertEqual(result["coverage"]["measurable"], 0)
        payload["elections"][1]["phase"] = "reload"
        result = audit.analyse_payload(payload)
        self.assertEqual(result["coverage"]["measurable"], 2)
        self.assertNotIn("inversions", result)  # no pooled total across phases

    def test_legacy_uses_existing_collector_without_inventing_election(self):
        payload = {"phase_a": {"openttd_output_raw": "no election here"}}
        with patch.object(audit, "fleet_coverage", wraps=audit.fleet_coverage) as collector:
            result = audit.analyse_payload(payload)
            collector.assert_called_once_with(payload)
        self.assertIsNone(result["inversions"])
        self.assertEqual(result["reason"], "no_complete_election_snapshots")

    def test_file_hash_json_jsonl_and_stdout_only_cli(self):
        payload = {"schema": audit.SCHEMA, "elections": [snapshot()]}
        raw = json.dumps(payload).encode()
        with patch.object(Path, "read_bytes", return_value=raw):
            result = audit.analyse_file(ROOT / "results/fleet_amort_shadow/synthetic.json")
            self.assertEqual(result["sha256"], hashlib.sha256(raw).hexdigest())
            result = audit.analyse_file(ROOT / "results/fleet_amort_shadow/synthetic.jsonl")
            self.assertEqual(result["records"][0]["record"], 1)
            with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                audit.main([str(ROOT / "results/fleet_amort_shadow/synthetic.json")])
                self.assertEqual(json.loads(stdout.getvalue())[0]["analysis"]["coverage"]["measurable"], 1)


class SourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "ai/OpexAI/projects_builders.nut").read_text(encoding="utf-8")
        cls.helper = cls.source.split("function OpexFleetAmortShadow(", 1)[1]

    def test_preexisting_builder_entirely_preserved(self):
        original = re.sub(r"\n/\* FLEET_AMORT_SHADOW_BEGIN.*?/\* FLEET_AMORT_SHADOW_END \*/\n?", "", self.source, flags=re.S)
        # Empreinte reprise apres 9e29951 (champs portfolio* du split C121,
        # defaut 0), puis V107 : refus de densification rail dans
        # OpexProjectFromFleet, derriere v107_densify_portfolio a defaut 0,
        # puis retrait du repli N=1 (air0310_n1_fallback, code mort a defaut 0)
        # de OpexProjectFromAir le 05/10.
        self.assertEqual(hashlib.sha256(original.encode()).hexdigest(),
                         "05f7bf1e9cd138ca59386b968a6e9b7d36aa4ee456aa2f9a83cdf551e6a1c1ef")

    def test_integrated_caller_is_diagnostic_helper_stays_explicit_opt_in(self):
        occurrences = sum(p.read_text(encoding="utf-8").count("OpexFleetAmortShadow(")
                          for p in (ROOT / "ai/OpexAI").glob("*.nut"))
        self.assertEqual(occurrences, 2)  # definition + central diagnostic caller
        selector = (ROOT / "ai/OpexAI/projects_selection.nut").read_text(encoding="utf-8")
        self.assertIn("FLEET_AMORT_SHADOW_PROBE > 0 ? OpexAmortProbeBegin", selector)
        self.assertTrue(self.helper.startswith("project, enabled = false, plane = null)"))
        self.assertLess(self.helper.index("if (!enabled) return null;"), self.helper.index("C84_AIR_TARGET_FLEET"))
        self.assertNotIn("GetSetting", self.helper)
        self.assertNotIn("AILog", self.helper)
        self.assertNotIn("OpexDecide", self.helper)

    def test_calibration_on_clone_only_and_no_project_payload_write(self):
        self.assertIn("local diagnostic = clone project;", self.helper)
        self.assertIn("diagnostic.profitAnnual = netProfitAnnual;", self.helper)
        self.assertIn("OpexCalibratedProfit(diagnostic)", self.helper)
        self.assertNotRegex(self.helper, r"(?:project|entry|plane)\.\w+\s*(?:<\-|=(?!=))")
        self.assertNotIn("profitIsObserved = false", self.helper)
        self.assertNotIn("lastProfit", self.helper)

    def test_life_and_batch_rounding_match_source_air_convention(self):
        source = (ROOT / "ai/OpexAI/air_route_economics.nut").read_text(encoding="utf-8")
        for text in (source, self.helper):
            self.assertIn("local lifeYears = 20;", text)
            self.assertIn('if (V92_AIR_SERVICE_CHOICE && ("ageYears" in plane) && plane.ageYears > 1) lifeYears = plane.ageYears;', text)
        self.assertIn("planes * plane.price / lifeYears + airportAmortAnnual", source)
        self.assertIn("entry.want * entry.planePrice / lifeYears", self.helper)
        self.assertNotIn("airportAmortAnnual", self.helper)
        self.assertNotIn("predRunning", self.helper)


if __name__ == "__main__":
    unittest.main()