import copy
import unittest
import tempfile
import json
from unittest.mock import patch, Mock
from pathlib import Path
from run_c121_night_queue import healthy, gate_pass, resource_args, exposed, save, wait_artifact, wait_docker_idle


class GateTests(unittest.TestCase):
    def test_recovery_waits_for_exact_live_container_without_relaunch(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "result.json"
            result.write_text("{}", encoding="utf-8")
            running = Mock(returncode=0, stdout=json.dumps([{"Name": "/owned", "State": {"Running": True}}]), stderr="")
            gone = Mock(returncode=1, stdout="", stderr="error: no such object: owned")
            with patch("run_c121_night_queue.subprocess.run", side_effect=[running, gone]) as calls, patch("run_c121_night_queue.time.sleep"), patch("run_c121_night_queue.time.monotonic", return_value=0):
                wait_artifact(result, "owned", {}, 100)
            self.assertEqual([c.args[0] for c in calls.call_args_list],
                             [["docker", "inspect", "owned"], ["docker", "inspect", "owned"]])

    def test_wait_for_other_campaign_does_not_stop_it(self):
        with patch("run_c121_night_queue.subprocess.check_output", side_effect=["other", ""]) as ps, patch("run_c121_night_queue.subprocess.run") as mutation, patch("run_c121_night_queue.time.sleep"), patch("run_c121_night_queue.time.monotonic", return_value=0):
            wait_docker_idle({}, 100)
        mutation.assert_not_called()
        self.assertEqual(ps.call_count, 2)

    def test_wait_for_other_campaign_keeps_original_deadline(self):
        with patch("run_c121_night_queue.subprocess.check_output", return_value="other"), patch("run_c121_night_queue.subprocess.run") as mutation, patch("run_c121_night_queue.time.monotonic", return_value=100):
            with self.assertRaises(TimeoutError):
                wait_docker_idle({}, 100)
        mutation.assert_not_called()

    def test_recovery_rejects_missing_result_or_unavailable_docker(self):
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory) / "result.json"
            for error in ("No such object: owned", "Cannot connect to Docker daemon"):
                failed = Mock(returncode=1, stdout="", stderr=error)
                with patch("run_c121_night_queue.subprocess.run", return_value=failed), patch("run_c121_night_queue.time.monotonic", return_value=0):
                    with self.assertRaises(RuntimeError):
                        wait_artifact(result, "owned", {}, 100)

    def test_status_save_recovers_transient_destination_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "status.json"
            target.write_text('{"old": true}', encoding="utf-8")
            replace = Path.replace
            calls = []
            def locked_once(source, destination):
                calls.append(destination)
                if len(calls) == 1:
                    self.assertEqual(json.loads(target.read_text()), {"old": True})
                    raise PermissionError("locked")
                return replace(source, destination)
            with patch.object(Path, "replace", locked_once), patch("run_c121_night_queue.time.sleep"):
                save(target, {"state": "running"})
            self.assertEqual(json.loads(target.read_text()), {"state": "running"})
            self.assertEqual(len(calls), 2)
            self.assertFalse(target.with_suffix(".tmp").exists())

    def test_status_save_persistent_lock_is_not_silenced(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "status.json"
            with patch.object(Path, "replace", side_effect=PermissionError("locked")) as replace, patch("run_c121_night_queue.time.sleep"):
                with self.assertRaises(PermissionError):
                    save(target, {"state": "running"})
            self.assertEqual(replace.call_count, 21)

    def test_resource_override_is_explicit_and_bounded(self):
        self.assertEqual(resource_args({}),
                         ["--cpus", "3", "--memory", "2g", "--max-workers", "3"])
        self.assertEqual(resource_args({"cpus": 10, "memory": "8g", "max_workers": 10}),
                         ["--cpus", "10", "--memory", "8g", "--max-workers", "10"])
        with self.assertRaises(ValueError):
            resource_args({"cpus": 10, "max_workers": 11})
        with self.assertRaises(ValueError):
            resource_args({"memory": "0g"})

    def setUp(self):
        self.data = {"failed_runs": [], "games": [
            {"game_ok": True, "unattributed_errors": [], "companies": {
                name: {"horizon_complete": True, "run_ok": True}
                for name in ("OpexAI", "AAAHogEx")}} for _ in range(80)],
            "policy_comparison": {"comparison_complete": True, "complete_pairs": 40,
                "adoption_sample_complete": True, "metric_coverage_complete": True,
                "decision_rule": {"rule": "gain_short"}, "verdict": "pass",
                "primary_pass": True, "value_guard_pass": True}}

    def test_complete_gate(self):
        self.assertTrue(gate_pass(self.data, "gain_short", 40))

    def test_economic_failure_does_not_authorize_B(self):
        self.data["policy_comparison"]["verdict"] = "fail_primary"
        self.assertTrue(healthy(self.data, 40))
        self.assertFalse(gate_pass(self.data, "gain_short", 40))

    def test_coverage_and_rule_are_required(self):
        for field in ("adoption_sample_complete", "metric_coverage_complete"):
            data = copy.deepcopy(self.data)
            data["policy_comparison"][field] = False
            self.assertFalse(gate_pass(data, "gain_short", 40))
        self.assertFalse(gate_pass(self.data, "non_erosion", 40))

    def test_adversary_and_unknown_errors_stop_queue(self):
        for change in ("adversary", "errors", "missing_game"):
            data = copy.deepcopy(self.data)
            if change == "adversary":
                data["games"][0]["companies"]["AAAHogEx"]["horizon_complete"] = False
            elif change == "errors":
                data["games"][0]["unattributed_errors"] = ["unknown fatal"]
            else:
                data["games"].pop()
            self.assertFalse(healthy(data, 40))

    def test_exposure_is_owned_and_effective_not_a_control_log(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "engine.log"
            log.write_text("\n".join([
                "[script:4] [1] [I] QUAL_EXPOSURE mechanism=n1 applied=1",
                "[script:4] [0] [I] QUAL_EXPOSURE mechanism=n1 applied=0",
                "[script:4] [0] [I] QUAL_EXPOSURE mechanism=n1 applied=1",
                "[script:4] [0] [I] C121_FIRST_LIVE_PRIORITY_DEFER line=2",
            ]), encoding="utf-8")
            data = {"games": [{"seed": 42, "policy_id": "reference", "engine_log_path": "/work/engine.log"},
                              {"seed": 42, "policy_id": "candidate", "engine_log_path": "/work/engine.log"}]}
            self.assertEqual(exposed(data, root, "n1")[0]["events"], 1)
            self.assertEqual(len(exposed(data, root, "n1")), 1)
            self.assertEqual(exposed(data, root, "priority")[0]["events"], 1)
            self.assertEqual(exposed(data, root, "hubcap"), [])

    def test_numeric_exposure_requires_affected_variant_and_opex_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            log = root / "engine.log"
            for kind in ("num_target", "num_bonus", "num_pop", "num_phase", "num_cadence"):
                log.write_text("\n".join([
                    f"[script:4] [1] [I] QUAL_NUMERIC mechanism={kind} affected=1 value=8",
                    f"[script:4] [0] [I] QUAL_NUMERIC mechanism={kind} affected=0 value=8",
                    f"[script:4] [0] [I] QUAL_NUMERIC mechanism={kind} affected=1 value=8",
                ]), encoding="utf-8")
                data = {"games": [{"seed": 42, "policy_id": policy, "engine_log_path": "/work/engine.log"}
                                  for policy in ("reference", "candidate")]}
                self.assertEqual(exposed(data, root, kind)[0]["events"], 1)
                self.assertEqual(len(exposed(data, root, kind)), 1)


if __name__ == "__main__":
    unittest.main()
