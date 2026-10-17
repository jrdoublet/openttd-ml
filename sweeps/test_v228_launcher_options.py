"""Tests pour V228 : options --start-year et --map-size du lanceur de duels.

Vérifie :
1. Défauts identiques :
   - make_cfg(1970, 8) est identique octet pour octet à make_cfg(STARTING_YEAR) et CFG.
   - Défauts de run_c66_reference.py et bench_1v1_5y_20seeds.py = 1970 et 8.
   - prepare_frozen_campaign avec défauts consigne 1970 et 8 dans configuration et execution.options.
2. Valeurs propagées :
   - run_c66_reference transmet --start-year et --map-size à la commande conteneur.
   - bench_1v1_5y_20seeds construit la configuration correspondante (starting_year, map_x, map_y).
   - Les valeurs sont consignées dans le manifeste et payload.
   - frozen_execution_inputs valide les options sans dérive.
3. Bornes refusées :
   - Année : 1920 à 2050 (refus < 1920 et > 2050).
   - Map size : 6 à 12 (refus < 6 et > 12).
   - Rejet CLI dans run_c66_reference.py et bench_1v1_5y_20seeds.py.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import types
from unittest import TestCase, mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))

try:
    import openttdlab
except ImportError:
    fake_lab = types.ModuleType("openttdlab")
    fake_lab.bananas_ai = mock.MagicMock()
    fake_lab.bananas_ai_library = mock.MagicMock()
    fake_lab.local_folder = mock.MagicMock()
    fake_lab.run_experiments = mock.MagicMock()
    sys.modules["openttdlab"] = fake_lab

from bench_v2 import CFG, make_cfg
from campaign_freeze import (
    MIN_MAP_SIZE,
    MAX_MAP_SIZE,
    MIN_START_YEAR,
    MAX_START_YEAR,
    prepare_frozen_campaign,
    validate_simulation_bounds,
)
import bench_1v1_5y_20seeds
from bench_1v1_5y_20seeds import (
    STARTING_YEAR,
    frozen_execution_inputs,
    make_experiments_plan,
)
import run_c66_reference


class TestV228DefaultConfiguration(TestCase):
    """Vérifie l'identité stricte octet pour octet avec la configuration actuelle."""

    def test_default_config_byte_for_byte_identical(self):
        """make_cfg(1970, 8) doit être identique octet pour octet à make_cfg(STARTING_YEAR) et CFG."""
        cfg_default_explicit = make_cfg(1970, 8)
        cfg_default_starting = make_cfg(STARTING_YEAR)
        cfg_bench_v2 = CFG

        # Comparaison des chaînes
        self.assertEqual(cfg_default_explicit, cfg_default_starting)
        self.assertEqual(cfg_default_explicit, cfg_bench_v2)

        # Comparaison octet pour octet
        bytes_explicit = cfg_default_explicit.encode("utf-8")
        bytes_starting = cfg_default_starting.encode("utf-8")
        bytes_cfg = cfg_bench_v2.encode("utf-8")
        self.assertEqual(bytes_explicit, bytes_starting)
        self.assertEqual(bytes_explicit, bytes_cfg)

    def test_cli_parser_defaults(self):
        """Les options CLI dans run_c66_reference et bench_1v1_5y_20seeds ont 1970 et 8 par défaut."""
        # run_c66_reference
        parser_run = argparse.ArgumentParser()
        parser_run.add_argument("--start-year", "--starting-year", dest="start_year", type=int, default=1970)
        parser_run.add_argument("--map-size", type=int, default=8)
        args_run = parser_run.parse_args([])
        self.assertEqual(args_run.start_year, 1970)
        self.assertEqual(args_run.map_size, 8)

        # bench_1v1_5y_20seeds
        parser_bench = argparse.ArgumentParser()
        parser_bench.add_argument("--start-year", "--starting-year", dest="start_year", type=int, default=STARTING_YEAR)
        parser_bench.add_argument("--map-size", type=int, default=8)
        args_bench = parser_bench.parse_args([])
        self.assertEqual(args_bench.start_year, 1970)
        self.assertEqual(args_bench.map_size, 8)

    def test_prepare_frozen_campaign_manifest_defaults(self):
        """Le manifeste généré avec les défauts consigne starting_year=1970 et map_size=8."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            opex = root / "ai" / "OpexAI"
            hogex = root / "ai" / "AAAHogEx-115"
            harness = root / "sweeps"
            opex.mkdir(parents=True)
            hogex.mkdir(parents=True)
            harness.mkdir()
            (opex / "info.nut").write_text("AddSetting({ name = \"opt\", min_value = 0, max_value = 1, custom_value = 0, flags = 0 });\n", encoding="utf-8")
            (opex / "main.nut").write_text("# opex\n", encoding="utf-8")
            (hogex / "info.nut").write_text("AddSetting({ name = \"opt\", min_value = 0, max_value = 1, custom_value = 0, flags = 0 });\n", encoding="utf-8")
            (hogex / "main.nut").write_text("# hogex\n", encoding="utf-8")
            (harness / "dummy.py").write_text("# dummy\n", encoding="utf-8")

            cfg = make_cfg(1970, 8)
            env = {"C66_GIT_SHA": "0" * 40, "C66_GIT_DIRTY": "0", "C66_GIT_STATUS_B64": ""}
            with mock.patch.dict(os.environ, env, clear=False):
                frozen = prepare_frozen_campaign(
                    root=root,
                    out_path=root / "results" / "test_default.json",
                    campaign_id="test-default",
                    policy_id="reference",
                    seeds=(42,),
                    years=1,
                    repeats=1,
                    starting_year=1970,
                    map_size=8,
                    config_text=cfg,
                    harness_files=("sweeps/dummy.py",),
                    openttd_version="15.3",
                    opengfx_version="7.1",
                    execution_options={"seeds": [42], "years": 1, "repeats": 1, "policy_id": "reference"},
                )

            manifest = json.loads(frozen.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["configuration"]["starting_year"], 1970)
            self.assertEqual(manifest["configuration"]["map_size"], 8)
            self.assertEqual(manifest["configuration"]["raw"], cfg)
            self.assertEqual(manifest["execution"]["options"]["start_year"], 1970)
            self.assertEqual(manifest["execution"]["options"]["map_size"], 8)


class TestV228OptionsPropagation(TestCase):
    """Vérifie la transmission des options de bout en bout."""

    def test_run_c66_reference_forwards_options(self):
        """run_c66_reference transmet --start-year et --map-size à la commande conteneur."""
        captured = []

        def fake_run(command, cwd=None):
            captured.append(command)
            res = mock.MagicMock()
            res.returncode = 0
            return res

        def fake_output(cmd):
            if "rev-parse" in cmd:
                return "1" * 40
            if "status" in cmd:
                return ""
            if "inspect" in cmd:
                return "sha256:dummy"
            return ""

        argv = [
            "run_c66_reference.py",
            "--campaign", "c66-propagate-test",
            "--start-year", "1985",
            "--map-size", "10",
        ]

        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(run_c66_reference, "_output", side_effect=fake_output), \
             mock.patch.object(run_c66_reference.subprocess, "run", side_effect=fake_run), \
             mock.patch("sys.stdout"):
            with self.assertRaises(SystemExit) as exc:
                run_c66_reference.main()
            self.assertEqual(exc.exception.code, 0)

        self.assertEqual(len(captured), 1)
        cmd = captured[0]
        self.assertIn("--start-year", cmd)
        idx_yr = cmd.index("--start-year")
        self.assertEqual(cmd[idx_yr + 1], "1985")
        self.assertIn("--map-size", cmd)
        idx_sz = cmd.index("--map-size")
        self.assertEqual(cmd[idx_sz + 1], "10")

    def test_bench_1v1_makes_cfg_with_custom_values(self):
        """make_cfg génère la configuration attendue pour des valeurs hors défaut."""
        cfg = make_cfg(1985, 10)
        self.assertIn("starting_year = 1985\n", cfg)
        self.assertIn("map_x = 10\n", cfg)
        self.assertIn("map_y = 10\n", cfg)

    def test_manifest_and_execution_options_custom_values(self):
        """prepare_frozen_campaign consigne les options personnalisées dans le manifeste."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            opex = root / "ai" / "OpexAI"
            hogex = root / "ai" / "AAAHogEx-115"
            harness = root / "sweeps"
            opex.mkdir(parents=True)
            hogex.mkdir(parents=True)
            harness.mkdir()
            (opex / "info.nut").write_text("AddSetting({ name = \"opt\", min_value = 0, max_value = 1, custom_value = 0, flags = 0 });\n", encoding="utf-8")
            (opex / "main.nut").write_text("# opex\n", encoding="utf-8")
            (hogex / "info.nut").write_text("AddSetting({ name = \"opt\", min_value = 0, max_value = 1, custom_value = 0, flags = 0 });\n", encoding="utf-8")
            (hogex / "main.nut").write_text("# hogex\n", encoding="utf-8")
            (harness / "dummy.py").write_text("# dummy\n", encoding="utf-8")

            cfg = make_cfg(1985, 10)
            env = {"C66_GIT_SHA": "0" * 40, "C66_GIT_DIRTY": "0", "C66_GIT_STATUS_B64": ""}
            with mock.patch.dict(os.environ, env, clear=False):
                frozen = prepare_frozen_campaign(
                    root=root,
                    out_path=root / "results" / "test_custom.json",
                    campaign_id="test-custom",
                    policy_id="reference",
                    seeds=(42,),
                    years=2,
                    repeats=1,
                    starting_year=1985,
                    map_size=10,
                    config_text=cfg,
                    harness_files=("sweeps/dummy.py",),
                    openttd_version="15.3",
                    opengfx_version="7.1",
                    execution_options={
                        "seeds": [42],
                        "years": 2,
                        "repeats": 1,
                        "policy_id": "reference",
                        "variant_policy_id": None,
                        "start_year": 1985,
                        "map_size": 10,
                    },
                )

            manifest = json.loads(frozen.manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["configuration"]["starting_year"], 1985)
            self.assertEqual(manifest["configuration"]["map_size"], 10)
            self.assertEqual(manifest["configuration"]["parsed"]["game_creation"]["starting_year"], "1985")
            self.assertEqual(manifest["configuration"]["parsed"]["game_creation"]["map_x"], "10")
            self.assertEqual(manifest["configuration"]["parsed"]["game_creation"]["map_y"], "10")
            self.assertEqual(manifest["execution"]["options"]["start_year"], 1985)
            self.assertEqual(manifest["execution"]["options"]["map_size"], 10)

            # Vérifier que frozen_execution_inputs valide cette configuration sans rejet
            args_loaded, _ = frozen_execution_inputs(frozen)
            self.assertEqual(args_loaded.start_year, 1985)
            self.assertEqual(args_loaded.map_size, 10)

    def test_frozen_execution_inputs_rejects_map_size_drift(self):
        """frozen_execution_inputs détecte une discordance sur map_size."""
        manifest = {
            "execution": {"options": {"seeds": [42], "years": 1, "repeats": 1,
                                      "policy_id": "ref", "variant_policy_id": None,
                                      "start_year": 1985, "map_size": 10}},
            "configuration": {"seeds": [42], "years": 1, "repeats": 1, "starting_year": 1985, "map_size": 8},
            "versions": {"openttd": "15.3", "opengfx": "7.1"},
            "policy": {"id": "ref"}, "comparison": None,
            "policies": [{"id": "ref", "role": "reference", "settings": {"explicit": {}}}],
        }
        campaign = types.SimpleNamespace(manifest=manifest)
        with self.assertRaises(ValueError) as ctx:
            frozen_execution_inputs(campaign)
        self.assertIn("map_size mismatch", str(ctx.exception))


class TestV228BoundsValidation(TestCase):
    """Vérifie la validation stricte des bornes : année 1920-2050, map_size 6-12."""

    def test_bounds_constants(self):
        self.assertEqual(MIN_START_YEAR, 1920)
        self.assertEqual(MAX_START_YEAR, 2050)
        self.assertEqual(MIN_MAP_SIZE, 6)
        self.assertEqual(MAX_MAP_SIZE, 12)

    def test_validate_simulation_bounds_accepted(self):
        """Les bornes exactes et les valeurs intermédiaires sont acceptées."""
        for yr, sz in ((1920, 6), (2050, 12), (1970, 8), (1985, 10), (1920, 12), (2050, 6)):
            with self.subTest(start_year=yr, map_size=sz):
                validate_simulation_bounds(yr, sz)

    def test_validate_simulation_bounds_rejected_year(self):
        """Année hors bornes 1920-2050 levée en ValueError."""
        for yr in (1919, 2051, 1800, 2100, 0, -1):
            with self.subTest(start_year=yr):
                with self.assertRaises(ValueError) as ctx:
                    validate_simulation_bounds(yr, 8)
                self.assertIn("--start-year doit être compris entre 1920 et 2050", str(ctx.exception))

    def test_validate_simulation_bounds_rejected_map_size(self):
        """Map size hors bornes 6-12 levée en ValueError."""
        for sz in (5, 13, 0, -1, 15):
            with self.subTest(map_size=sz):
                with self.assertRaises(ValueError) as ctx:
                    validate_simulation_bounds(1970, sz)
                self.assertIn("--map-size doit être compris entre 6 et 12", str(ctx.exception))

    def test_run_c66_reference_cli_rejection(self):
        """run_c66_reference.py rejette les arguments hors bornes au niveau CLI."""
        for bad_argv in (
            ["run_c66_reference.py", "--campaign", "test", "--start-year", "1919"],
            ["run_c66_reference.py", "--campaign", "test", "--start-year", "2051"],
            ["run_c66_reference.py", "--campaign", "test", "--map-size", "5"],
            ["run_c66_reference.py", "--campaign", "test", "--map-size", "13"],
        ):
            with self.subTest(argv=bad_argv):
                with mock.patch.object(sys, "argv", bad_argv), mock.patch("sys.stderr"):
                    with self.assertRaises(SystemExit) as exc:
                        run_c66_reference.main()
                    self.assertNotEqual(exc.exception.code, 0)

    def test_bench_1v1_cli_rejection(self):
        """bench_1v1_5y_20seeds.py rejette les arguments hors bornes au niveau CLI."""
        for bad_argv in (
            ["bench_1v1_5y_20seeds.py", "--start-year", "1919"],
            ["bench_1v1_5y_20seeds.py", "--start-year", "2051"],
            ["bench_1v1_5y_20seeds.py", "--map-size", "5"],
            ["bench_1v1_5y_20seeds.py", "--map-size", "13"],
        ):
            with self.subTest(argv=bad_argv):
                with mock.patch.object(sys, "argv", bad_argv), mock.patch("sys.stderr"):
                    with self.assertRaises(SystemExit) as exc:
                        bench_1v1_5y_20seeds.main()
                    self.assertNotEqual(exc.exception.code, 0)
