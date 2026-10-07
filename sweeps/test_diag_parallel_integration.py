"""Integration contracts; these tests do not execute OpenTTD."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bench_v2
import diag_cadence_duel as cadence
import diag_parallel_integration as integration


class IntegrationProbeTests(unittest.TestCase):
    def test_c41_logging_prerequisite_is_enabled(self):
        # Counters alone are insufficient: OpexC39Log returns early unless
        # C39_INVALIDATION_PROBE (probe_catalogue) is enabled too.
        self.assertIn("probe_catalogue", integration.PROBES)
        source = (cadence.ROOT / "ai/OpexAI/probes.nut").read_text(encoding="utf-8")
        body = source.split("function OpexC39Log(kind, fields)", 1)[1].split("}", 1)[0]
        self.assertIn("if (!C39_INVALIDATION_PROBE) return;", body)

    def test_declared_settings_differ_only_by_probes(self):
        resolved = bench_v2.resolved_arm_settings(list(integration.ARMS.values()))
        reference = resolved[integration.ARMS["reference"]]["settings"]["effective"]
        profile = resolved[integration.ARMS["profile"]]["settings"]["effective"]
        self.assertEqual({k for k in reference if reference[k] != profile[k]},
                         set(integration.PROBES))
        for key in integration.PROBES:
            self.assertEqual(reference[key], 0)
            self.assertEqual(profile[key], 1)

    def test_delegation_keeps_original_cadence_arms(self):
        original = dict(cadence.ARMS)
        with patch.object(integration, "run_diagnostic") as run:
            integration.main()
        run.assert_called_once_with(arm_specs=integration.ARMS,
                                    purpose=integration.PURPOSE, force_debug=True)
        self.assertEqual(cadence.ARMS, original)

    def test_existing_output_rejected_before_build_or_simulation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "existing.json"
            out.write_text("preserve", encoding="utf-8")
            with patch.object(sys, "argv", ["diag", "--out", str(out)]), \
                    patch.object(cadence.bench_v2, "build_arms") as build, \
                    self.assertRaises(SystemExit):
                integration.main()
            build.assert_not_called()
            self.assertEqual(out.read_text(encoding="utf-8"), "preserve")

    def test_protected_defaults(self):
        resolved = bench_v2.resolved_arm_settings(list(integration.ARMS.values()))
        for spec in resolved.values():
            values = spec["settings"]["effective"]
            self.assertEqual(values["c115_air_c100_capital_replay"], 1)
            for key in ("exp_scheduler_skip_not_due",
                        "exp_air_hub_pair_prefilter", "c121_air_economics",
                        "c84_air_target_fleet", "c85_air_equipment_frontier"):
                self.assertEqual(values[key], 0)


if __name__ == "__main__":
    unittest.main()