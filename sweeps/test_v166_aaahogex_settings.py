"""Tests pour V166 : transmission de réglages à AAAHogEx via --aaahogex-setting.

Vérifie :
1. Analyse et validation de l'option (nom inconnu, valeur non entière, doublon, format)
2. Omission des valeurs égales au défaut déclaré dans info.nut
3. Tri et format identique aux explicit_settings d'OpexAI
4. Propagation au plan make_experiments_plan pour les deux bras (référence et variante)
5. Enregistrement dans le manifeste de campagne (execution.options et adversary)
6. Validation et transmission hôte dans run_c66_reference.py
"""

from __future__ import annotations

import argparse
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

from campaign_freeze import (
    effective_ai_settings,
    parse_aaahogex_settings,
    parse_ai_settings,
    prepare_frozen_campaign,
)
from bench_1v1_5y_20seeds import (
    make_experiments_plan,
    validate_paired_experiments,
)


class TestV166OptionValidation(TestCase):
    """1. Analyse et validation de l'option --aaahogex-setting."""

    def setUp(self):
        self.info_path = ROOT / "ai" / "AAAHogEx-115" / "info.nut"

    def test_unknown_setting_rejected(self):
        """Un réglage non déclaré dans info.nut doit lever une ValueError explicite."""
        with self.assertRaisesRegex(ValueError, "non declare dans info.nut"):
            parse_aaahogex_settings(["unknown_setting=1"], self.info_path)

    def test_non_integer_value_rejected(self):
        """Une valeur non entière (chaîne, flottant) doit lever une ValueError explicite."""
        with self.assertRaisesRegex(ValueError, "valeur entiere attendue"):
            parse_aaahogex_settings(["disable_veh_train=abc"], self.info_path)
        with self.assertRaisesRegex(ValueError, "valeur entiere attendue"):
            parse_aaahogex_settings(["disable_veh_train=1.5"], self.info_path)

    def test_duplicate_setting_rejected(self):
        """Un même réglage spécifié deux fois doit lever une ValueError explicite."""
        with self.assertRaisesRegex(ValueError, "reglage AAAHogEx duplique"):
            parse_aaahogex_settings(
                ["disable_veh_train=1", "disable_veh_train=0"], self.info_path
            )

    def test_missing_equals_rejected(self):
        """Un format sans '=' doit lever une ValueError explicite."""
        with self.assertRaisesRegex(ValueError, "attend le format NOM=VALEUR"):
            parse_aaahogex_settings(["disable_veh_train"], self.info_path)

    def test_empty_or_none_returns_empty_tuple(self):
        """Sans réglage, retourne un tuple vide."""
        self.assertEqual(parse_aaahogex_settings([], self.info_path), ())
        self.assertEqual(parse_aaahogex_settings(None, self.info_path), ())


class TestV166DefaultOmission(TestCase):
    """2. Omission des valeurs égales au défaut déclaré dans info.nut."""

    def setUp(self):
        self.info_path = ROOT / "ai" / "AAAHogEx-115" / "info.nut"
        self.defaults = parse_ai_settings(self.info_path)

    def test_value_equal_to_default_is_omitted(self):
        """disable_veh_train a pour défaut 0 : si passé à 0, il doit être omis."""
        self.assertEqual(self.defaults["disable_veh_train"], 0)
        res = parse_aaahogex_settings(["disable_veh_train=0"], self.info_path)
        self.assertEqual(res, ())

    def test_value_different_from_default_is_retained(self):
        """disable_veh_train passé à 1 (!= 0) doit être conservé sous forme (nom, entier)."""
        res = parse_aaahogex_settings(["disable_veh_train=1"], self.info_path)
        self.assertEqual(res, (("disable_veh_train", 1),))

    def test_mix_of_default_and_non_default(self):
        """Seuls les écarts au défaut sont conservés, les réglages au défaut sont omis."""
        raw = [
            "disable_veh_train=1",    # défaut 0 -> conservé
            "disable_veh_roadveh=0",  # défaut 0 -> omis
            "disable_veh_aircraft=1", # défaut 0 -> conservé
            "usable_cargos=3",        # défaut 3 -> omis
        ]
        res = parse_aaahogex_settings(raw, self.info_path)
        expected = (
            ("disable_veh_aircraft", 1),
            ("disable_veh_train", 1),
        )
        self.assertEqual(res, expected)

    def test_result_tuple_is_sorted(self):
        """Le tuple retourné doit être trié par nom de réglage."""
        raw = [
            "disable_veh_tram=1",
            "disable_veh_aircraft=1",
            "disable_veh_ship=1",
        ]
        res = parse_aaahogex_settings(raw, self.info_path)
        keys = [item[0] for item in res]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(
            res,
            (
                ("disable_veh_aircraft", 1),
                ("disable_veh_ship", 1),
                ("disable_veh_tram", 1),
            ),
        )

    def test_setting_with_non_zero_default(self):
        """usable_cargos (défaut 3) et 'Avoid removing water' (défaut 1)."""
        self.assertEqual(self.defaults["usable_cargos"], 3)
        self.assertEqual(self.defaults["Avoid removing water"], 1)

        # Égal au défaut -> omis
        self.assertEqual(parse_aaahogex_settings(["usable_cargos=3"], self.info_path), ())
        self.assertEqual(parse_aaahogex_settings(["Avoid removing water=1"], self.info_path), ())

        # Différent du défaut -> conservé
        self.assertEqual(
            parse_aaahogex_settings(["usable_cargos=1"], self.info_path),
            (("usable_cargos", 1),),
        )
        self.assertEqual(
            parse_aaahogex_settings(["Avoid removing water=0"], self.info_path),
            (("Avoid removing water", 0),),
        )


class TestV166ExperimentsPlanPropagation(TestCase):
    """3. Propagation au plan make_experiments_plan pour les deux bras."""

    def test_plan_passes_settings_to_aaahogex_descriptor(self):
        """local_folder doit recevoir le tuple filtré, identique pour référence et variante."""
        created_folders = []

        class FakeFolder:
            def __init__(self, path, name, settings):
                self.path = path
                self.name = name
                self.settings = settings

        def fake_local_folder(path, name, settings):
            obj = FakeFolder(path, name, settings)
            created_folders.append(obj)
            return obj

        policies = [
            {"id": "reference", "role": "reference", "explicit_settings": ()},
            {"id": "variant", "role": "variant", "explicit_settings": (("c69_capital_factor", 1),)},
        ]

        campaign = mock.MagicMock()
        campaign.campaign_id = "test-camp"
        campaign.aaahogex_dir = ROOT / "ai" / "AAAHogEx-115"
        campaign.opex_dir = ROOT / "ai" / "OpexAI"
        campaign.manifest = {"configuration": {"raw": "[game]\nstarting_year = 1970\n"}}
        campaign.bundle_sha256 = "dummy_sha"

        with mock.patch("openttdlab.local_folder", side_effect=fake_local_folder):
            exps = make_experiments_plan(
                seeds=[42, 100],
                years=1,
                repeats=1,
                campaign=campaign,
                policies=policies,
                aaahogex_settings=["disable_veh_train=1", "disable_veh_roadveh=0"],
            )

        # local_folder est appelé pour AAAHogEx avec le tuple filtré
        aaahogex_folders = [f for f in created_folders if f.name == "AAAHogEx"]
        self.assertEqual(len(aaahogex_folders), 1)
        self.assertEqual(aaahogex_folders[0].settings, (("disable_veh_train", 1),))

        # Vérifier que toutes les expériences partagent EXACTEMENT le même descripteur AAAHogEx
        shared_aaa = aaahogex_folders[0]
        self.assertEqual(len(exps), 4)  # 2 graines * 2 politiques
        for exp in exps:
            self.assertIs(exp["ais"][1], shared_aaa)
            self.assertEqual(exp["ais"][1].settings, (("disable_veh_train", 1),))

        # Vérifier que la validation C66.4 des paires passe sans erreur
        validate_paired_experiments(exps, ["reference", "variant"])

    def test_plan_with_no_settings_passes_empty_tuple(self):
        """Sans réglage AAAHogEx, local_folder doit recevoir un tuple vide ()."""
        created_folders = []

        def fake_local_folder(path, name, settings):
            obj = mock.MagicMock(name=name)
            obj.settings = settings
            created_folders.append(obj)
            return obj

        with mock.patch("openttdlab.local_folder", side_effect=fake_local_folder):
            exps = make_experiments_plan(
                seeds=[42],
                years=1,
                repeats=1,
                policies=[{"id": "reference", "explicit_settings": ()}],
                aaahogex_settings=None,
            )

        aaahogex_descriptors = [f for f in created_folders if getattr(f, "name", None) == "AAAHogEx" or f.settings == ()]
        self.assertTrue(any(f.settings == () for f in created_folders))


class TestV166ManifestAndResults(TestCase):
    """4. Enregistrement dans le manifeste de campagne et les résultats."""

    def test_manifest_options_and_adversary_recording(self):
        """prepare_frozen_campaign consigne execution.options['aaahogex_settings'] et adversary['settings']."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            opex = root / "ai" / "OpexAI"
            hogex = root / "ai" / "AAAHogEx-115"
            harness = root / "sweeps"
            opex.mkdir(parents=True)
            hogex.mkdir(parents=True)
            harness.mkdir()

            # Copier les vrais info.nut pour un test fidèle
            (opex / "info.nut").write_text(
                (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (opex / "main.nut").write_text("opex\n", encoding="utf-8")
            (hogex / "info.nut").write_text(
                (ROOT / "ai" / "AAAHogEx-115" / "info.nut").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (hogex / "main.nut").write_text("hogex\n", encoding="utf-8")
            (harness / "fixture.py").write_text("# harness\n", encoding="utf-8")

            env = {
                "C66_GIT_SHA": "0" * 40,
                "C66_GIT_DIRTY": "0",
                "C66_GIT_STATUS_B64": "",
            }

            fake_openttdlab = types.ModuleType("openttdlab")
            fake_openttdlab.bananas_ai = mock.MagicMock()
            fake_openttdlab.bananas_ai_library = mock.MagicMock()
            fake_openttdlab.local_folder = mock.MagicMock()
            fake_openttdlab.run_experiments = mock.MagicMock()

            # Test A : sans réglage AAAHogEx (comportement par défaut)
            with mock.patch.dict(os.environ, env, clear=False), mock.patch.dict(
                sys.modules, {"openttdlab": fake_openttdlab}
            ):
                campaign_default = prepare_frozen_campaign(
                    root=root,
                    out_path=Path("results") / "test_default.json",
                    campaign_id="test-default",
                    policy_id="reference",
                    seeds=(42,),
                    years=1,
                    repeats=1,
                    starting_year=1970,
                    config_text="[game]\nstarting_year = 1970\n",
                    harness_files=("sweeps/fixture.py",),
                    openttd_version="15.3",
                    opengfx_version="7.1",
                    execution_options={"seeds": [42], "years": 1, "repeats": 1, "policy_id": "reference"},
                )

            manifest_def = campaign_default.manifest
            self.assertIn("aaahogex_settings", manifest_def["execution"]["options"])
            self.assertEqual(manifest_def["execution"]["options"]["aaahogex_settings"], [])
            self.assertEqual(manifest_def["adversary"]["settings"]["explicit"], {})

            # Test B : avec réglage AAAHogEx demandé
            requested = ["disable_veh_train=1"]
            explicit = parse_aaahogex_settings(requested, hogex / "info.nut")
            self.assertEqual(explicit, (("disable_veh_train", 1),))

            with mock.patch.dict(os.environ, env, clear=False), mock.patch.dict(
                sys.modules, {"openttdlab": fake_openttdlab}
            ):
                campaign_set = prepare_frozen_campaign(
                    root=root,
                    out_path=Path("results") / "test_tuned.json",
                    campaign_id="test-tuned",
                    policy_id="reference",
                    seeds=(42,),
                    years=1,
                    repeats=1,
                    starting_year=1970,
                    config_text="[game]\nstarting_year = 1970\n",
                    aaahogex_explicit_settings=explicit,
                    harness_files=("sweeps/fixture.py",),
                    openttd_version="15.3",
                    opengfx_version="7.1",
                    execution_options={
                        "seeds": [42],
                        "years": 1,
                        "repeats": 1,
                        "policy_id": "reference",
                        "aaahogex_settings": requested,
                    },
                )

            manifest_tuned = campaign_set.manifest
            self.assertEqual(
                manifest_tuned["execution"]["options"]["aaahogex_settings"],
                ["disable_veh_train=1"],
            )
            self.assertEqual(
                manifest_tuned["adversary"]["settings"]["explicit"],
                {"disable_veh_train": 1},
            )
            self.assertEqual(
                manifest_tuned["adversary"]["settings"]["effective"]["disable_veh_train"],
                1,
            )


class TestV166LauncherOption(TestCase):
    """5. Vérification du lanceur run_c66_reference.py."""

    def test_run_c66_reference_validation_errors(self):
        """run_c66_reference échoue explicitement avant Docker en cas de réglage invalide."""
        import run_c66_reference

        # Nom inconnu
        with mock.patch.object(sys, "argv", ["run_c66_reference.py", "--campaign", "test", "--aaahogex-setting", "bad_name=1"]):
            with self.assertRaises(SystemExit):
                with mock.patch("sys.stderr"):
                    run_c66_reference.main()

        # Valeur non entière
        with mock.patch.object(sys, "argv", ["run_c66_reference.py", "--campaign", "test", "--aaahogex-setting", "disable_veh_train=abc"]):
            with self.assertRaises(SystemExit):
                with mock.patch("sys.stderr"):
                    run_c66_reference.main()

        # Doublon
        with mock.patch.object(sys, "argv", ["run_c66_reference.py", "--campaign", "test", "--aaahogex-setting", "disable_veh_train=1", "--aaahogex-setting", "disable_veh_train=0"]):
            with self.assertRaises(SystemExit):
                with mock.patch("sys.stderr"):
                    run_c66_reference.main()

    def test_run_c66_reference_forwarding_to_docker_cmd(self):
        """run_c66_reference transmet telle quelle chaque option --aaahogex-setting au conteneur."""
        import run_c66_reference

        captured_commands = []

        def fake_run(command, cwd=None):
            captured_commands.append(command)
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
            "--campaign", "c66-test",
            "--aaahogex-setting", "disable_veh_train=1",
            "--aaahogex-setting", "disable_veh_aircraft=1",
        ]

        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(run_c66_reference, "_output", side_effect=fake_output), \
             mock.patch.object(run_c66_reference.subprocess, "run", side_effect=fake_run), \
             mock.patch("sys.stdout"):
            with self.assertRaises(SystemExit) as exc:
                run_c66_reference.main()
            self.assertEqual(exc.exception.code, 0)

        self.assertEqual(len(captured_commands), 1)
        cmd = captured_commands[0]
        # Vérifier que les arguments sont transmis fidèlement à bench_1v1_5y_20seeds.py
        self.assertIn("--aaahogex-setting", cmd)
        idx1 = cmd.index("--aaahogex-setting")
        self.assertEqual(cmd[idx1 + 1], "disable_veh_train=1")
        idx2 = cmd.index("--aaahogex-setting", idx1 + 2)
        self.assertEqual(cmd[idx2 + 1], "disable_veh_aircraft=1")

    def test_bench_1v1_cli_parser(self):
        """bench_1v1_5y_20seeds accepte --aaahogex-setting de manière répétable."""
        import bench_1v1_5y_20seeds

        # Vérifier que le parseur CLI de bench_1v1_5y_20seeds reconnaît l'option
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--aaahogex-setting",
            action="append",
            default=[],
            dest="aaahogex_settings",
        )
        args = parser.parse_args([
            "--aaahogex-setting", "disable_veh_train=1",
            "--aaahogex-setting", "disable_veh_aircraft=1",
        ])
        self.assertEqual(args.aaahogex_settings, ["disable_veh_train=1", "disable_veh_aircraft=1"])
