"""RVA-05 fixtures: no engine, no Docker, no downloads."""
import copy
import hashlib
import inspect
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import test_v228_launcher_options
from bench_v2 import make_cfg
from bench_1v1_5y_20seeds import make_experiments_plan, validate_paired_experiments
from campaign_freeze import prepare_frozen_campaign
from frozen_harness import verify_manifest_bundle
from rva_profile import load_profile, freeze_profile, resource_descriptor, resource_directory_wrapper


class Profiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "profile.json"
        self.grfs = []
        for name in ("second", "first"):
            data = ("fixture-not-real-grf:" + name).encode()
            (self.root / (name + ".grf")).write_bytes(data)
            self.grfs.append({"file": name + ".grf", "sha256": hashlib.sha256(data).hexdigest(),
                              "version": None, "parameters": [2, 1]})
        self.profile = {"schema": 1, "settings": {"linkgraph": {"distribution_pax": "symmetric"}},
                        "newgrfs": self.grfs}
        self.write()

    def write(self):
        self.path.write_text(json.dumps(self.profile), encoding="utf-8")

    def test_freeze_order_params_hash_unknown_version_and_local_callbacks(self):
        loaded = load_profile(self.path, self.root)
        bundle = self.root / "bundle"
        bundle.mkdir()
        cfg, metadata = freeze_profile(loaded, bundle / "simulation_profile", make_cfg(1950))
        self.assertIn("starting_year = 1950", cfg)
        self.assertIn("distribution_pax = symmetric", cfg)
        entries = metadata["resources"]
        self.assertLess(cfg.index(entries[0]["filename"]), cfg.index(entries[1]["filename"]))
        self.assertIn(" = 2 1", cfg)
        self.assertIsNone(entries[0]["version"])
        _, callback = resource_descriptor(bundle, entries)
        with callback() as records:
            self.assertEqual(len(records), 2)
            for record, entry in zip(records, entries):
                with record[-1]() as chunks:
                    self.assertEqual(hashlib.sha256(b"".join(chunks)).hexdigest(), entry["sha256"])
        (bundle / "simulation_profile" / entries[0]["filename"]).write_bytes(b"changed")
        with self.assertRaises(ValueError):
            with callback():
                pass

    def test_refuse_missing_changed_duplicate_escape_and_unsafe_config(self):
        variants = []
        for field, value in (("file", "absent.grf"), ("sha256", "0" * 64),
                              ("parameters", [True]), ("version", 2), ("file", "../outside.grf")):
            candidate = copy.deepcopy(self.profile)
            candidate["newgrfs"][0][field] = value
            variants.append(candidate)
        candidate = copy.deepcopy(self.profile)
        candidate["newgrfs"].append(candidate["newgrfs"][0])
        variants.append(candidate)
        for settings in ({"game_creation": {"starting_year": "2000"}},
                         {"ai_players": {}}, {"vehicle": {"x": "1\n[newgrf]"}}):
            variants.append(dict(self.profile, settings=settings))
        for candidate in variants:
            with self.subTest(candidate=candidate):
                self.path.write_text(json.dumps(candidate))
                with self.assertRaises(ValueError):
                    load_profile(self.path, self.root)

    def test_controlled_wrapper_preserves_signature_and_other_arguments(self):
        def original(run_dir, i, final_screenshot_directory):
            self.assertTrue((Path(run_dir) / str(i) / "newgrf").is_dir())
            return final_screenshot_directory
        wrapped = resource_directory_wrapper(original)
        self.assertEqual(inspect.signature(wrapped), inspect.signature(original))
        self.assertEqual(wrapped(self.root, 3, "screens"), "screens")

    def test_actual_campaign_freeze_and_two_arms_use_same_frozen_inputs(self):
        for name in ("OpexAI", "AAAHogEx-115"):
            folder = self.root / "ai" / name
            folder.mkdir(parents=True)
            (folder / "info.nut").write_text('AddSetting({ name = "opt", min_value = 0, max_value = 1, custom_value = 0, flags = 0 });')
            (folder / "main.nut").write_text("// fixture")
        (self.root / "sweeps").mkdir()
        (self.root / "sweeps/dummy.py").write_text("# fixture")
        with mock.patch.dict(os.environ, {"C66_GIT_SHA": "0" * 40,
                "C66_GIT_DIRTY": "0", "C66_GIT_STATUS_B64": ""}):
            frozen = prepare_frozen_campaign(root=self.root, out_path=self.root / "results/test.json",
                campaign_id="rva-profile", policy_id="reference", seeds=(42,), years=1,
                repeats=1, starting_year=1950, config_text=make_cfg(1950),
                simulation_profile=self.path, harness_files=("sweeps/dummy.py",),
                openttd_version="15.3", opengfx_version="7.1", execution_options={})
        verify_manifest_bundle(frozen.manifest_path, frozen.manifest_sha256)
        with mock.patch("openttdlab.local_folder", side_effect=lambda *args: args):
            plan = make_experiments_plan([42], 1, campaign=frozen,
                policies=({"id": "ref"}, {"id": "var"}))
        validate_paired_experiments(plan, ("ref", "var"))
        self.assertEqual(plan[0]["openttd_config"], plan[1]["openttd_config"])
        self.assertIn("[newgrf]", plan[0]["openttd_config"])
        # Modifying live inputs cannot change the frozen plans or resources.
        self.path.write_text("{}"); (self.root / "first.grf").unlink()
        verify_manifest_bundle(frozen.manifest_path, frozen.manifest_sha256)


if __name__ == "__main__":
    unittest.main()
