"""RVA-04 : fixtures hors moteur, pas de lancement de partie."""
import copy
from types import SimpleNamespace
from pathlib import Path
from unittest import TestCase, mock

# Reuse the existing test environment and frozen fixture builder.
import test_v228_launcher_options  # openttdlab stub for offline fixtures
from bench_v2 import make_cfg, CFG
from bench_1v1_5y_20seeds import (
    make_experiments_plan, validate_paired_experiments, _annual_final_records,
    frozen_execution_inputs,
)
from game_health import (
    expected_checkpoint_dates, expected_last_checkpoint, engine_failure_row,
    checkpoint_reaches,
)


class Epochs(TestCase):
    def test_duel_and_horizon_1950_1970_and_epoch_change(self):
        for year, years in ((1950, 3), (1970, 3), (1966, 3)):
            with self.subTest(year=year):
                with mock.patch("openttdlab.local_folder", side_effect=lambda *args: args):
                    campaign = SimpleNamespace(manifest={"configuration": {"raw": make_cfg(year)}},
                        opex_dir="/fixture/OpexAI", aaahogex_dir=Path("/fixture/AAAHogEx"),
                        campaign_id=f"epoch-{year}", bundle_sha256="fixture")
                    plan = make_experiments_plan([42], years, start_year=year, campaign=campaign,
                        policies=({"id": "ref"}, {"id": "var"}))
                validate_paired_experiments(plan, ("ref", "var"))
                self.assertEqual(len(plan), 2)
                for exp in plan:
                    self.assertIn(f"starting_year = {year}", exp["openttd_config"])
                    self.assertEqual(exp["days"], years * 365)
                    failure = engine_failure_row(exp, "timeout", kind="timeout")
                    self.assertEqual(failure["date"], f"{year}-01-01")
                dates = expected_checkpoint_dates(year, years)
                self.assertEqual(len(dates), years * 12)
                self.assertEqual(expected_last_checkpoint(year, years), f"{year+years-1}-12-01")
                self.assertFalse(checkpoint_reaches(f"{year+years-1}-01-01", expected_last_checkpoint(year, years)))
                self.assertTrue(checkpoint_reaches(dates[-1], expected_last_checkpoint(year, years)))
                rows = [{"run": ["OpexAI", 42, 0], "duel_policy_id": "ref", "date": d}
                        for d in dates]
                annual = _annual_final_records(rows, year, years)
                self.assertEqual(len(annual), years)
                self.assertTrue(all(r["date"].endswith("-12-01") for r in annual.values()))
                drift = copy.deepcopy(plan)
                drift[1]["openttd_config"] = make_cfg(year + 1)
                with self.assertRaises(ValueError):
                    validate_paired_experiments(drift, ("ref", "var"))
        self.assertEqual(make_cfg(), CFG)

    def test_frozen_epoch_and_config_drift(self):
        import os
        import tempfile
        from pathlib import Path
        from campaign_freeze import prepare_frozen_campaign
        for year in (1950, 1970):
            with self.subTest(year=year), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                for name in ("OpexAI", "AAAHogEx-115"):
                    folder = root / "ai" / name
                    folder.mkdir(parents=True)
                    (folder / "info.nut").write_text('AddSetting({ name = "opt", min_value = 0, max_value = 1, custom_value = 0, flags = 0 });')
                    (folder / "main.nut").write_text("// fixture")
                (root / "sweeps").mkdir()
                (root / "sweeps/dummy.py").write_text("# fixture")
                with mock.patch.dict(os.environ, {"C66_GIT_SHA": "0" * 40,
                        "C66_GIT_DIRTY": "0", "C66_GIT_STATUS_B64": ""}):
                    frozen = prepare_frozen_campaign(root=root,
                        out_path=root / "results/fixture.json", campaign_id=f"rva-{year}",
                        policy_id="reference", seeds=(42,), years=3, repeats=1,
                        starting_year=year, map_size=8, config_text=make_cfg(year),
                        harness_files=("sweeps/dummy.py",), openttd_version="15.3",
                        opengfx_version="7.1", execution_options={"seeds": [42], "years": 3,
                            "repeats": 1, "policy_id": "reference", "variant_policy_id": None,
                            "start_year": year, "map_size": 8})
                self.assertEqual(frozen.manifest["configuration"]["starting_year"], year)
                self.assertEqual(frozen.manifest["configuration"]["parsed"]["game_creation"]["starting_year"], str(year))
                args, _ = frozen_execution_inputs(frozen)
                self.assertEqual(args.start_year, year)
                changed = copy.deepcopy(frozen.manifest)
                changed["execution"]["options"]["start_year"] = year + 1
                with self.assertRaises(ValueError):
                    frozen_execution_inputs(SimpleNamespace(manifest=changed))
