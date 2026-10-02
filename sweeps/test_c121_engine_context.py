from pathlib import Path
import json
import tempfile
import unittest
from sweeps.c121_context_fixtures import ROOT, stage_context, markers
from sweeps.campaign_freeze import parse_ai_setting_specs
from sweeps.run_c121_winner_integration import compare_measurements


class ContextTests(unittest.TestCase):
    def test_gate_off_and_prior_fusion_on(self):
        specs = parse_ai_setting_specs(ROOT / "ai/OpexAI/info.nut")
        self.assertTrue(specs["c121_air_engine_context"]["boolean"])
        text = (ROOT / "ai/OpexAI/info.nut").read_text(encoding="utf-8")
        block = text.split('name = "c121_air_engine_context",')[1].split("});")[0]
        for field in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(field + " = 0", block)

    def test_fixture_keeps_production_exact_and_only_hooks_copy(self):
        source = (ROOT / "ai/OpexAI/air_economics_c121.nut").read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            staged = stage_context(Path(folder))
            self.assertEqual((staged / "air_economics_c121.nut").read_bytes(), source)
            self.assertIn("FxCtxStart(this)", (staged / "main.nut").read_text(encoding="utf-8"))
            self.assertIn("[1, 6, 13]", (staged / "c121_winner_vm.nut").read_text(encoding="utf-8"))
        self.assertEqual((ROOT / "ai/OpexAI/air_economics_c121.nut").read_bytes(), source)

    def test_missing_vm_evidence_fail_closed(self):
        self.assertFalse(all(markers("")["checks"].values()))

    def test_context_comparison_requires_only_context_change_and_fusion_on(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = [Path(folder) / side for side in ("off", "on")]
            plans = []
            for value, path in enumerate(paths):
                path.mkdir()
                plan = dict(mode="measure", seed=42, configuration={}, source_hashes={},
                            libraries={}, image="pinned-image", resolved_settings={
                                "c121_air_economics": 1, "c121_air_winner_fusion": 1,
                                "c121_air_engine_context": value})
                plans.append(plan)
                (path / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
                report = {"pass": True, "evidence": {"totals": {
                    "c121_calls": 10, "c121_scan_ops": 100 - value,
                    "c121_winner_ops": 30 - value, "air_ops": 150 - value,
                    "total_ops": 200 - value}}}
                (path / "report.json").write_text(json.dumps(report), encoding="utf-8")
            result = compare_measurements(*paths, setting="c121_air_engine_context")
            self.assertTrue(result["comparable"])
            self.assertEqual(result["annual_deltas"]["c121_scan_ops"]["delta"], -1)
            self.assertFalse(compare_measurements(*paths)["comparable"])
            plans[1]["resolved_settings"]["c121_air_winner_fusion"] = 0
            (paths[1] / "plan.json").write_text(json.dumps(plans[1]), encoding="utf-8")
            self.assertFalse(compare_measurements(*paths, setting="c121_air_engine_context")["comparable"])

    def test_matrix_rejects_partial_domain_and_unstable_samples(self):
        log = "C121_CONTEXT_START fusion=1 witness=0 pass=1\nC121_CONTEXT_GUARDS checks=12 reused=1 restored=1 pass=1\n"
        log += "C121_CONTEXT_LIVE arm=newpair checked=1 old_ops=10 new_ops=8 pass=1\n"
        log += "C121_WINNER_MATRIX case=1 cap=1 mail=0 mode=0 aaa=0 stable=0 eligible=1 old_ops=10 new_ops=8 pass=1\n"
        evidence = markers(log)
        self.assertFalse(evidence["checks"]["matrix_domain"])
        self.assertFalse(evidence["checks"]["matrix_stable"])
        self.assertEqual(evidence["checked_count"], 1)
        self.assertEqual((evidence["old_ops"], evidence["new_ops"]), (10, 8))


if __name__ == "__main__":
    unittest.main()
