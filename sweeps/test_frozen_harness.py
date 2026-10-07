"""R26 provenance regressions: real child interpreters, no engine or network."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from campaign_freeze import fingerprint_tree, prepare_frozen_campaign
from frozen_harness import (
    frozen_command, launch_frozen_campaign, restore_campaign, restore_installed_user_site,
    verify_manifest_bundle,
)


FIXTURE_COLLECTOR = '''import json
import multiprocessing
from pathlib import Path
import frozen_dependency

def collect():
    return {"collector": "A", "dependency": frozen_dependency.VALUE,
            "source": __file__, "dependency_source": frozen_dependency.__file__}

def execute_frozen_campaign(campaign):
    with multiprocessing.get_context("spawn").Pool(1) as pool:
        worker = pool.apply(collect)
    result = {"parent": collect(), "worker": worker,
              "options": campaign.manifest["execution"]["options"]}
    campaign.out_path.write_text(json.dumps(result), encoding="utf-8")
    print(json.dumps(result))
'''


class TestFrozenHarness(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "live checkout with spaces"
        self.sweeps = self.root / "sweeps"
        self.sweeps.mkdir(parents=True)
        for name in ("OpexAI", "AAAHogEx-115"):
            folder = self.root / "ai" / name
            folder.mkdir(parents=True)
            (folder / "info.nut").write_text(
                'AddSetting({ name = "sample", custom_value = 0 });\n', encoding="utf-8",
            )
        for name in ("frozen_harness.py", "campaign_freeze.py"):
            shutil.copy2(Path(__file__).with_name(name), self.sweeps / name)
        (self.sweeps / "bench_1v1_5y_20seeds.py").write_text(FIXTURE_COLLECTOR, encoding="utf-8")
        (self.sweeps / "frozen_dependency.py").write_text('VALUE = "A"\n', encoding="utf-8")
        self.options = {"seeds": [42], "years": 1, "repeats": 1, "line_telemetry": True}
        self.campaign = self.freeze("provenance")

    def freeze(self, campaign_id):
        def local_libraries(specs, destination):
            destination.mkdir()
            (destination / "fixture-1.tar").write_bytes(b"frozen-library")
            return (), [{"requested_name": "Fixture", "resolved": [{
                "content_id": "TEST", "filename": "fixture-1.tar", "license": "GPL-2.0",
                "public_md5": None,
            }]}]

        with mock.patch("campaign_freeze.git_state", return_value={"sha": "test-fixture"}), \
                mock.patch("campaign_freeze.freeze_bananas_libraries", side_effect=local_libraries):
            return prepare_frozen_campaign(
                root=self.root, out_path=Path("results") / f"{campaign_id}.json",
                campaign_id=campaign_id, policy_id="reference", seeds=[42], years=1,
                repeats=1, starting_year=1970, config_text="[game_creation]\nstarting_year=1970\n",
                harness_files=tuple(f"sweeps/{path.name}" for path in self.sweeps.glob("*.py")),
                openttd_version="15.3", opengfx_version="7.1",
                execution_options=self.options,
            )

    def run_child(self):
        # Deliberately hostile import locations: neither cwd nor PYTHONPATH may win.
        env = dict(os.environ, PYTHONPATH=str(self.sweeps))
        return subprocess.run(frozen_command(self.campaign), cwd=self.sweeps, env=env,
                              capture_output=True, text=True, encoding="utf-8", timeout=60)

    def test_live_mutation_does_not_change_collector_dependency_or_spawn_worker(self):
        (self.sweeps / "bench_1v1_5y_20seeds.py").write_text(
            'raise RuntimeError("live collector B executed")\n', encoding="utf-8",
        )
        (self.sweeps / "frozen_dependency.py").write_text('VALUE = "B"\n', encoding="utf-8")
        before = fingerprint_tree(self.campaign.bundle_dir)
        child = self.run_child()
        self.assertEqual(child.returncode, 0, child.stderr)
        result = json.loads(child.stdout)
        for key in ("parent", "worker"):
            self.assertEqual(result[key]["collector"], "A")
            self.assertEqual(result[key]["dependency"], "A")
            for field in ("source", "dependency_source"):
                self.assertTrue(Path(result[key][field]).is_relative_to(self.campaign.bundle_dir))
        self.assertEqual(result["options"], self.options)
        self.assertEqual(fingerprint_tree(self.campaign.bundle_dir), before)
        self.assertFalse(list(self.campaign.bundle_dir.rglob("__pycache__")))

    def test_modified_manifest_fails_before_collector(self):
        self.campaign.manifest_path.write_bytes(self.campaign.manifest_path.read_bytes() + b"\n")
        child = self.run_child()
        self.assertNotEqual(child.returncode, 0)
        self.assertIn("manifest fingerprint mismatch", child.stderr)
        self.assertFalse(self.campaign.out_path.exists())

    def test_modified_bundle_fails_before_collector(self):
        dependency = self.campaign.bundle_dir / "harness/sweeps/frozen_dependency.py"
        dependency.write_text('VALUE = "tampered"\n', encoding="utf-8")
        child = self.run_child()
        self.assertNotEqual(child.returncode, 0)
        self.assertIn("bundle fingerprint mismatch", child.stderr)
        self.assertFalse(self.campaign.out_path.exists())

    def test_added_or_deleted_bundle_file_is_detected(self):
        path = self.campaign.bundle_dir / "extra.py"
        path.write_text("# not in fingerprint\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "bundle fingerprint mismatch"):
            verify_manifest_bundle(self.campaign.manifest_path, self.campaign.manifest_sha256)
        path.unlink()
        (self.campaign.bundle_dir / "ai/OpexAI/info.nut").unlink()
        with self.assertRaisesRegex(ValueError, "bundle fingerprint mismatch"):
            verify_manifest_bundle(self.campaign.manifest_path, self.campaign.manifest_sha256)

    def test_restore_uses_local_library_bytes_and_original_artifact_paths(self):
        manifest = verify_manifest_bundle(self.campaign.manifest_path, self.campaign.manifest_sha256)
        restored = restore_campaign(self.campaign.manifest_path, self.campaign.manifest_sha256, manifest)
        for name in ("out_path", "checkpoint_path", "engine_log_dir", "opex_dir", "aaahogex_dir",
                     "manifest_sha256", "bundle_sha256"):
            self.assertEqual(getattr(restored, name), getattr(self.campaign, name))
        name, copy_func = restored.ai_libraries[0]
        self.assertEqual(name, "Fixture")
        with copy_func() as entries:
            with entries[0][4]() as chunks:
                self.assertEqual(b"".join(chunks), b"frozen-library")

    def test_existing_results_or_checkpoints_are_not_overwritten(self):
        for path in (self.campaign.out_path, self.campaign.checkpoint_path):
            with self.subTest(path=path):
                path.write_text("preserve", encoding="utf-8")
                child = self.run_child()
                self.assertNotEqual(child.returncode, 0)
                self.assertIn("refusing to replay", child.stderr)
                self.assertEqual(path.read_text(encoding="utf-8"), "preserve")
                path.unlink()

    def test_launcher_propagates_exit_code_and_isolated_command(self):
        with mock.patch("frozen_harness.subprocess.run") as run:
            run.return_value.returncode = 7
            self.assertEqual(launch_frozen_campaign(self.campaign), 7)
            self.assertEqual(run.call_args.args[0], frozen_command(self.campaign))
            self.assertEqual(run.call_args.kwargs["cwd"], self.campaign.bundle_dir / "harness")
            self.assertIn("-I", run.call_args.args[0])
            self.assertIn("-B", run.call_args.args[0])

    def test_restore_installed_user_site_readds_existing_directory_under_isolation(self):
        user_site = self.root / "python-user-site"
        user_site.mkdir()
        original = list(sys.path)
        try:
            with mock.patch("frozen_harness.site.getusersitepackages", return_value=str(user_site)):
                added = restore_installed_user_site()
                self.assertEqual(added, [str(user_site)])
                self.assertIn(str(user_site), sys.path)
                self.assertEqual(restore_installed_user_site(), [])
        finally:
            sys.path[:] = original

    def test_child_failure_is_not_hidden(self):
        # Prepare a second, deliberately failing snapshot (never rewrite a frozen bundle).
        (self.sweeps / "bench_1v1_5y_20seeds.py").write_text(
            'raise RuntimeError("fixture failure")\n', encoding="utf-8",
        )
        self.campaign = self.freeze("failure")
        child = self.run_child()
        self.assertNotEqual(child.returncode, 0)
        self.assertIn("fixture failure", child.stderr)
        self.assertFalse(self.campaign.out_path.exists())

    def test_existing_engine_logs_are_not_reused(self):
        log = self.campaign.engine_log_dir / "previous.log"
        log.write_text("preserve", encoding="utf-8")
        child = self.run_child()
        self.assertNotEqual(child.returncode, 0)
        self.assertIn("existing engine logs", child.stderr)
        self.assertEqual(log.read_text(encoding="utf-8"), "preserve")

    def test_actual_harness_reaches_mocked_engine_with_frozen_collector(self):
        # Exercise the real production import/preparation path, but stop at the
        # engine boundary. No OpenTTD binary, network, game, or real AI is needed.
        for name in ("bench_1v1_5y_20seeds.py", "bench_v2.py", "paired_statistics.py", "game_health.py", "physical_counters.py", "c83_reaction.py"):
            shutil.copy2(Path(__file__).with_name(name), self.sweeps / name)
        (self.sweeps / "openttdlab.py").write_text('''import inspect
import json

def local_folder(*args):
    return args
bananas_ai = bananas_ai_library = local_folder

def _run_experiment(*args, **kwargs):
    raise AssertionError("no engine permitted")

def run_experiments(**kwargs):
    import bench_v2
    import game_health
    import physical_counters
    import c83_reaction
    result = {"collector": inspect.getfile(kwargs["result_processor"]),
              "modules": [module.__file__ for module in (bench_v2, game_health, physical_counters, c83_reaction)],
              "experiments": kwargs["experiments"]}
    print("ENGINE_BOUNDARY=" + json.dumps(result))
    raise RuntimeError("fixture stopped before engine")
''', encoding="utf-8")
        self.options.update({"policy_id": "reference", "variant_policy_id": None,
                             "script_debug": False, "engine_timeout": 30,
                             "docker_image_id": None, "max_workers": 1})
        self.campaign = self.freeze("actual-harness")
        for name in ("bench_1v1_5y_20seeds.py", "bench_v2.py", "paired_statistics.py", "game_health.py", "physical_counters.py", "c83_reaction.py"):
            (self.sweeps / name).write_text('raise RuntimeError("live code executed")\n', encoding="utf-8")
        child = self.run_child()
        self.assertNotEqual(child.returncode, 0)
        self.assertIn("fixture stopped before engine", child.stderr)
        line = next(line for line in child.stdout.splitlines() if line.startswith("ENGINE_BOUNDARY="))
        boundary = json.loads(line.split("=", 1)[1])
        for path in [boundary["collector"], *boundary["modules"]]:
            self.assertTrue(Path(path).is_relative_to(self.campaign.bundle_dir))
        experiment, = boundary["experiments"]
        self.assertEqual(experiment["openttd_config"], self.campaign.manifest["configuration"]["raw"])
        self.assertEqual(experiment["ais"][0][0], str(self.campaign.opex_dir))
        self.assertEqual(experiment["ais"][1][0], str(self.campaign.aaahogex_dir))
        self.assertFalse(self.campaign.out_path.exists())


if __name__ == "__main__":
    unittest.main()
