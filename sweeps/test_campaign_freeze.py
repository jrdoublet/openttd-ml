"""Tests du contrat de réglages et du gel de campagne C66."""
import contextlib
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock


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

from bench_v2 import (
    SEEDS,
    SEEDS_40,
    SEEDS_EXTRA_20,
    comparison_setting_audit,
    observed_opcode_stats,
    paired_comparisons,
    parse_opex_variant,
    portfolio_selection_opcode_stats,
    resolved_arm_settings,
)
from bench_1v1_5y_20seeds import (
    build_policy_comparison,
    project_build_sign_metrics,
    student_t_ci95_critical_value,
)
from campaign_freeze import (
    effective_ai_settings,
    fingerprint_tree,
    git_state,
    parse_ai_setting_specs,
    parse_ai_settings,
    prepare_frozen_campaign,
    validate_policy_settings,
)


INFO = ROOT / "ai" / "OpexAI" / "info.nut"


class TestCampaignFreeze(unittest.TestCase):
    def test_prepare_frozen_campaign_copies_ai_harness_and_libraries(self):
        """Couvre le gel complet sans réseau avec une bibliothèque BaNaNaS synthétique."""
        library_bytes = b"synthetic-library-tar\n"
        library_filename = "testlib-1.tar"

        @contextlib.contextmanager
        def library_data():
            yield iter((library_bytes[:8], library_bytes[8:]))

        @contextlib.contextmanager
        def resolved_library():
            yield ((
                "TEST",
                library_filename,
                "GPL-2.0",
                "public-md5",
                library_data,
            ),)

        fake_openttdlab = types.ModuleType("openttdlab")
        fake_openttdlab.bananas_ai_library = (
            lambda unique_id, name, md5=None: (name, resolved_library)
        )

        info_text = (
            'AddSetting({ name = "sample_setting", min_value = 0, max_value = 1, '
            'custom_value = 0, flags = AICONFIG_BOOLEAN });\n'
        )

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            opex = root / "ai" / "OpexAI"
            hogex = root / "ai" / "AAAHogEx-115"
            harness = root / "sweeps"
            opex.mkdir(parents=True)
            hogex.mkdir(parents=True)
            harness.mkdir()
            (opex / "info.nut").write_text(info_text, encoding="utf-8")
            (opex / "main.nut").write_text("opex snapshot\n", encoding="utf-8")
            (hogex / "info.nut").write_text(info_text, encoding="utf-8")
            (hogex / "main.nut").write_text("hogex snapshot\n", encoding="utf-8")
            (harness / "fixture_harness.py").write_text("HARNESS = True\n", encoding="utf-8")

            env = {
                "C66_GIT_SHA": "a" * 40,
                "C66_GIT_DIRTY": "0",
                "C66_GIT_STATUS_B64": "",
            }
            with mock.patch.dict(os.environ, env, clear=False), mock.patch.dict(
                sys.modules, {"openttdlab": fake_openttdlab}
            ):
                frozen = prepare_frozen_campaign(
                    root=root,
                    out_path=Path("results") / "unit_freeze.json",
                    campaign_id="unit-freeze",
                    policy_id="reference",
                    seeds=(42, 100),
                    years=3,
                    repeats=1,
                    starting_year=1970,
                    config_text="[game]\nstarting_year = 1970\n",
                    library_specs=({
                        "unique_id": "TEST",
                        "name": "TestLib",
                        "md5": None,
                    },),
                    harness_files=("sweeps/fixture_harness.py",),
                    openttd_version="15.3",
                    opengfx_version="7.1",
                )

            self.assertTrue(frozen.manifest_path.is_file())
            self.assertTrue(frozen.engine_log_dir.is_dir())
            self.assertEqual((frozen.opex_dir / "main.nut").read_text(encoding="utf-8"), "opex snapshot\n")
            self.assertEqual(
                (frozen.aaahogex_dir / "main.nut").read_text(encoding="utf-8"),
                "hogex snapshot\n",
            )
            self.assertEqual(
                (frozen.bundle_dir / "harness" / "sweeps" / "fixture_harness.py").read_text(
                    encoding="utf-8"
                ),
                "HARNESS = True\n",
            )

            frozen_library = frozen.bundle_dir / "ai_libraries" / library_filename
            self.assertEqual(frozen_library.read_bytes(), library_bytes)
            library_source = frozen.manifest["sources"]["ai_libraries"]
            self.assertEqual(library_source["file_count"], 1)
            resolved = frozen.manifest["libraries"][0]["resolved"][0]
            self.assertEqual(resolved["filename"], library_filename)
            self.assertEqual(resolved["sha256"], hashlib.sha256(library_bytes).hexdigest())
            self.assertEqual(frozen.manifest["source_bundle"]["sha256"], frozen.bundle_sha256)
            self.assertEqual(len(frozen.manifest["games"]), 2)
            self.assertEqual(frozen.manifest["git"]["source"], "host_environment")

            self.assertEqual(len(frozen.ai_libraries), 1)
            name, copy_func = frozen.ai_libraries[0]
            self.assertEqual(name, "TestLib")
            with copy_func() as entries:
                self.assertEqual(len(entries), 1)
                content_id, filename, license_name, public_md5, get_data = entries[0]
                self.assertEqual(content_id, "TEST")
                self.assertEqual(filename, library_filename)
                self.assertEqual(license_name, "GPL-2.0")
                self.assertEqual(public_md5, "public-md5")
                with get_data() as chunks:
                    self.assertEqual(b"".join(chunks), library_bytes)

    def test_real_info_settings_contract(self):
        defaults = parse_ai_settings(INFO)
        specs = parse_ai_setting_specs(INFO)
        self.assertEqual(
            len(defaults),
            INFO.read_text(encoding="utf-8").count("AddSetting("),
        )
        for name in ("c69_decision_bottleneck", "c69_fleet_exempt", "c70_mode_calibration", "c75_multi_build", "c75_kpass_bypass",
                     "c80_air_hub_index", "town_growth_roi_gate", "c76_regen_targeted",
                     "town_growth_plan_memo", "c80_mode_regen", "v90_fast_pathfinder", "v94_air_site_list"):
            self.assertEqual(defaults[name], 1, name)
        for name in ("c69_fleet_demand_batch", "c72_plane_choice", "c84_air_target_fleet", "c85_air_equipment_frontier", "v88_goods_chain", "v88_chain_force", "v88_step2_plan_immediate", "c80_double_register",
                     "c76_lean_invalidation", "c76_freight_rotation",
                     "c80_worker_rail", "c80_worker_town", "c80_air_choice_memo", "c80_air_eval_fast", "air_full_load",
                     "c82_engine_calibration", "c80_marginal_floor", "rail_depot_cost",
                     "air_hubhub_marginal", "air_hub_max_routes", "v89_rail_search_throughput",
                     "v90_pathfinder_check", "v92_air_service_choice", "c83_fixes",
                     "c83_preempt_open", "air_batch_town_reserve",
                     "v93_airport_no_pop_floor", "v93_air_demand_production", "v95_air_post73_probe",
                     "v94_air_site_check", "c67_terrain_map", "c67_water_exposure_probe"):
            self.assertEqual(defaults[name], 0, name)
        self.assertEqual(defaults["rail_finance_bias_pct"], 100)
        self.assertEqual(defaults["v91_astar_weight_pct"], 120)
        self.assertNotIn("c80_fleet_inject", defaults)
        self.assertNotIn("c80_air_targeted_update", defaults)
        self.assertNotIn("c77_opportunistic_candidates", defaults)
        self.assertNotIn("c77_targeted_build", defaults)
        self.assertNotIn("c77_fixes", defaults)
        self.assertEqual(defaults["probe_events"], 0)
        self.assertEqual(defaults["probe_cost"], 0)
        self.assertEqual(defaults["policy_rail"], 1)
        self.assertEqual(defaults["policy_caches"], 1)
        self.assertEqual(defaults["air_route_plane_selection"], 1)
        self.assertEqual(set(defaults), set(specs))
        self.assertEqual(defaults["debug_signs"], 1)
        self.assertEqual(defaults["road_pax_catchment_pct"], 86)
        self.assertTrue(specs["town_growth_skip_noop"]["boolean"])
        self.assertEqual(specs["air_early_slot_min_pop"]["step_size"], 100)

    def test_every_real_default_is_expressible_by_bench_v2(self):
        defaults = parse_ai_settings(INFO)
        failures = []
        for name, value in defaults.items():
            try:
                parsed = parse_opex_variant(f"OpexAI[{name}={value}]")
            except ValueError as error:
                failures.append((name, str(error)))
                continue
            self.assertEqual(parsed, ((name, value),))
        self.assertEqual(failures, [])

    def test_generic_specs_reject_invalid_boolean_and_range(self):
        with self.assertRaises(ValueError):
            parse_opex_variant("OpexAI[probe_portfolio=2]")
        spec = parse_ai_setting_specs(INFO)["unprofitable_streak_threshold"]
        self.assertIsNotNone(spec["max_value"])
        with self.assertRaises(ValueError):
            parse_opex_variant(
                f"OpexAI[unprofitable_streak_threshold={spec['max_value'] + 1}]"
            )

    def test_effective_settings_merge_and_unknown_rejection(self):
        resolved = effective_ai_settings(
            INFO,
            (("road_pax_build", 1), ("town_growth_skip_noop", 1)),
        )
        self.assertEqual(resolved["defaults"]["road_pax_build"], 0)
        self.assertEqual(resolved["effective"]["road_pax_build"], 1)
        self.assertEqual(resolved["effective"]["town_growth_skip_noop"], 1)
        with self.assertRaises(ValueError):
            effective_ai_settings(INFO, (("does_not_exist", 1),))

    def test_selection_opcode_sign_parser_is_backward_compatible(self):
        chunks = {
            "SIGN": {
                1: {"name": "IG|70|187|187|64|1|0"},
                2: {"name": "IG|70|43|34|37|1|0|28"},
                3: {"name": "OTHER|x"},
                4: {"name": "IG|70|20|20|20|1|0|11"},
            }
        }
        parsed = portfolio_selection_opcode_stats(chunks)
        self.assertEqual(parsed["selection_kopcodes_samples"], 2)
        self.assertEqual(parsed["selection_kopcodes_total"], 39)
        self.assertEqual(parsed["selection_kopcodes_mean"], 19.5)
        self.assertEqual(parsed["selection_kopcodes_max"], 28)
        legacy = portfolio_selection_opcode_stats({
            "SIGN": {1: {"name": "IG|70|187|187|64|1|0"}}
        })
        self.assertEqual(legacy["selection_kopcodes_samples"], 0)
        self.assertIsNone(legacy["selection_kopcodes_total"])

    def test_project_build_sign_parser_reuses_existing_ib_panels(self):
        parsed = project_build_sign_metrics({
            "SIGN": {
                1: {"name": "IB|70|500000|240000|B2"},
                2: {"name": "IB|70|600000|300000|B1"},
                3: {"name": "IB|71|700000|350000|B3"},
                4: {"name": "IB|71|legacy"},
                5: {"name": "OTHER|x"},
            }
        })
        self.assertEqual(parsed["project_build_signs_parsed"], 3)
        self.assertEqual(parsed["project_builds_sign_total"], 6)
        self.assertEqual(parsed["project_builds_sign_by_year"], {"1970": 3, "1971": 3})

    def test_observed_opcode_parser_uses_real_non_overlapping_panels(self):
        chunks = {
            "SIGN": {
                1: {"name": "IG|70|43|34|37|1|0|28"},
                2: {"name": "OB|A|70|4|12345|5000|42"},
                3: {"name": "OB|1970|42|100|999"},  # rapport legacy, pas une tentative
                4: {"name": "RB|70|5|1|100|200"},
                5: {"name": "OA|1970|50|300|OK"},
                6: {"name": "OM|W|1970|60|400"},
            }
        }
        parsed = observed_opcode_stats(chunks)
        self.assertEqual(parsed["observed_opcode_schema"], "h5.observed-v1")
        self.assertFalse(parsed["observed_opcode_complete_cpu"])
        self.assertEqual(parsed["observed_opcode_samples"], 6)
        self.assertEqual(parsed["observed_opcodes_total"], 34000)
        self.assertEqual(parsed["observed_opcode_components"]["selection"]["opcodes"], 28000)
        self.assertEqual(parsed["observed_opcode_components"]["rail_attempt"]["opcodes"], 5000)
        self.assertEqual(parsed["observed_opcode_components"]["road_planning"]["opcodes"], 100)
        self.assertEqual(parsed["observed_opcode_components"]["road_build"]["opcodes"], 200)
        self.assertEqual(parsed["observed_opcode_components"]["air_planning"]["opcodes"], 300)
        self.assertEqual(parsed["observed_opcode_components"]["water_planning"]["opcodes"], 400)

        legacy = observed_opcode_stats({
            "SIGN": {
                1: {"name": "IG|70|43|34|37|1|0"},
                2: {"name": "RB|70|5|1|100|200"},
            }
        })
        self.assertEqual(legacy["observed_opcode_components"]["selection"]["samples"], 0)
        self.assertEqual(legacy["observed_opcodes_total"], 300)

    def test_paired_comparisons_keeps_requested_metric_set(self):
        summary = [
            {"arm": "A", "seed": 1, "run_ok": True, "company_value": 110, "observed_opcodes_total": 10},
            {"arm": "B", "seed": 1, "run_ok": True, "company_value": 100, "observed_opcodes_total": 12},
            {"arm": "A", "seed": 2, "run_ok": True, "company_value": 130, "observed_opcodes_total": 20},
            {"arm": "B", "seed": 2, "run_ok": True, "company_value": 120, "observed_opcodes_total": 25},
        ]
        core = paired_comparisons(summary, ("A", "B"), ("company_value",))[0]
        self.assertEqual(set(core["metrics"]), {"company_value"})
        self.assertEqual(core["metrics"]["company_value"]["mean_difference"], 10)
        observed = paired_comparisons(summary, ("A", "B"), ("observed_opcodes_total",))[0]
        self.assertEqual(set(observed["metrics"]), {"observed_opcodes_total"})
        self.assertEqual(observed["metrics"]["observed_opcodes_total"]["mean_difference"], -3.5)

    def test_policy_guard_rejects_unannounced_and_no_effect(self):
        diff = validate_policy_settings(
            {"c80_mode_regen": 0, "road_mode": 0},
            {"c80_mode_regen": 1, "road_mode": 0},
            intervention_settings=("c80_mode_regen",),
        )
        self.assertEqual(set(diff), {"c80_mode_regen"})
        with self.assertRaises(ValueError):
            validate_policy_settings(
                {"c80_mode_regen": 0, "road_mode": 0},
                {"c80_mode_regen": 1, "road_mode": 1},
                intervention_settings=("c80_mode_regen",),
            )
        with self.assertRaises(ValueError):
            validate_policy_settings(
                {"c80_mode_regen": 0},
                {"c80_mode_regen": 0},
                intervention_settings=("c80_mode_regen",),
            )

    def test_bench_audit_detects_identical_and_shared_nondefault_arms(self):
        identical = comparison_setting_audit(resolved_arm_settings([
            "OpexAI",
            "OpexAI[town_growth_skip_noop=0]",
        ]))
        self.assertEqual(len(identical["identical_effective_arms"]), 1)

        shared = comparison_setting_audit(resolved_arm_settings([
            "OpexAI[road_pax_build=1]",
            "OpexAI[road_pax_build=1,town_growth_skip_noop=1]",
        ]))
        self.assertEqual(
            [item["setting"] for item in shared["shared_nondefault_explicit"]],
            ["road_pax_build"],
        )
        self.assertFalse(shared["transportable_to_shipped_defaults"])

    def test_fingerprint_and_git_state_are_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "b.txt").write_text("two", encoding="utf-8")
            (root / "a.txt").write_text("one", encoding="utf-8")
            first = fingerprint_tree(root)
            second = fingerprint_tree(root)
            self.assertEqual(first["sha256"], second["sha256"])
            self.assertEqual([item["path"] for item in first["files"]], ["a.txt", "b.txt"])

        if shutil.which("git") is None:
            self.skipTest("git absent de ce runtime (ex: image openttd-lab, sans git installe)")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=root, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
            (root / "file.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "file.txt"], cwd=root, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=root, check=True)
            clean = git_state(root)
            self.assertFalse(clean["dirty"])
            self.assertEqual(len(clean["sha"]), 40)
            (root / "file.txt").write_text("changed", encoding="utf-8")
            dirty = git_state(root)
            self.assertTrue(dirty["dirty"])

    def test_seeds_extension_properties(self):
        """Vérifie la reproductibilité et l'absence de chevauchement de SEEDS_EXTRA_20."""
        self.assertEqual(len(SEEDS), 20)
        self.assertEqual(len(SEEDS_EXTRA_20), 20)
        self.assertEqual(len(SEEDS_40), 40)
        self.assertEqual(len(set(SEEDS_40)), 40)
        self.assertEqual(set(SEEDS) & set(SEEDS_EXTRA_20), set())
        for seed in SEEDS_EXTRA_20:
            self.assertIsInstance(seed, int)
            self.assertGreater(seed, 0)

    def test_prepare_frozen_campaign_records_decision_rule(self):
        """Vérifie que prepare_frozen_campaign enregistre decision_rule dans le manifeste."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ai_dir = root / "ai" / "OpexAI"
            ai_dir.mkdir(parents=True)
            (ai_dir / "info.nut").write_text(
                'AddSetting({ name = "test_opt", min_value = 0, max_value = 1, custom_value = 0, flags = 0 });\n',
                encoding="utf-8",
            )
            aaahogex_dir = root / "ai" / "AAAHogEx-115"
            aaahogex_dir.mkdir(parents=True)
            (aaahogex_dir / "info.nut").write_text(
                'AddSetting({ name = "other", min_value = 0, max_value = 1, custom_value = 0, flags = 0 });\n',
                encoding="utf-8",
            )
            harness = root / "harness.py"
            harness.write_text("# harness", encoding="utf-8")

            rule_mean40 = {
                "rule": "mean40",
                "primary_metric": "profit_year",
                "min_useful_primary_delta": 50.0,
                "value_guard_metric": "company_value",
                "value_guard_max_loss_pct": 5.0,
                "all_planned_pairs_required_for_verdict": True,
            }
            env = {
                "C66_GIT_SHA": "b" * 40,
                "C66_GIT_DIRTY": "0",
                "C66_GIT_STATUS_B64": "",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                frozen = prepare_frozen_campaign(
                    root=root,
                    out_path=root / "results" / "test_campaign.json",
                    campaign_id="test_campaign",
                    policy_id="ref",
                    seeds=[42, 100],
                    years=1,
                    repeats=1,
                    starting_year=1970,
                    config_text="[difficulty]\n",
                    opex_explicit_settings=(("test_opt", 0),),
                    library_specs=(),
                    harness_files=("harness.py",),
                    openttd_version="15.3",
                    opengfx_version="7.1",
                    policy_definitions=(
                        {"id": "ref", "role": "reference", "explicit_settings": (("test_opt", 0),)},
                        {"id": "var", "role": "variant", "explicit_settings": (("test_opt", 1),)},
                    ),
                    intervention_settings=("test_opt",),
                    decision_rule=rule_mean40,
                )
                manifest = json.loads(frozen.manifest_path.read_text(encoding="utf-8"))
                self.assertIn("comparison", manifest)
                self.assertEqual(manifest["comparison"]["decision_rule"], rule_mean40)
                self.assertEqual(manifest["comparison"]["decision_rule"]["rule"], "mean40")

    def test_decision_rule_mean40_and_signs20_adoption(self):
        """Vérifie l'évaluation de mean40 (pass, fail_primary, incomplet) et la non-régression de signs20."""
        # 1. student_t_ci95_critical_value
        self.assertEqual(student_t_ci95_critical_value(1), 12.706205)
        self.assertEqual(student_t_ci95_critical_value(19), 2.093024)
        self.assertEqual(student_t_ci95_critical_value(39), 2.022691)
        self.assertEqual(student_t_ci95_critical_value(40), 2.021075)
        self.assertEqual(student_t_ci95_critical_value(100), 1.983972)
        with self.assertRaises(ValueError):
            student_t_ci95_critical_value(0)

        def make_synthetic_case(deltas, decision_rule="signs20", seeds=None):
            summary = []
            rows = []
            if seeds is None:
                seeds = list(range(1, len(deltas) + 1))
            for seed, delta in zip(seeds, deltas):
                for policy, opex_profit, opex_val in (
                    ("ref", 100.0, 1000.0),
                    ("var", 100.0 + delta, 1001.0),
                ):
                    for arm, p_val, c_val in (
                        ("OpexAI", opex_profit, opex_val),
                        ("AAAHogEx", 90.0, 1100.0),
                    ):
                        rec = {
                            "duel_policy_id": policy,
                            "policy_id": policy if arm == "OpexAI" else "AAAHogEx",
                            "arm": arm,
                            "seed": seed,
                            "repeat": 0,
                            "run_ok": True,
                            "game_ok": True,
                            "status": "complete",
                            "failure_reason": None,
                            "profit_year": p_val,
                            "company_value": c_val,
                            "profit": p_val / 4.0,
                            "performance_history": 100,
                            "median_station_rating": 100,
                        }
                        summary.append(rec)
                        rows.append({**rec, "run": [arm, seed, 0], "date": "1970-12-01"})
            return build_policy_comparison(
                summary,
                rows,
                seeds=seeds,
                repeats=1,
                reference_policy_id="ref",
                variant_policy_id="var",
                primary_metric="profit_year",
                min_useful_primary_delta=5.0,
                value_guard_max_loss_pct=5.0,
                starting_year=1970,
                years=1,
                decision_rule=decision_rule,
            )

        # signs20 non-régression
        signs_pass = make_synthetic_case([10.0] * 15 + [-1.0] * 5, decision_rule="signs20")
        self.assertEqual(signs_pass["verdict"], "pass")
        self.assertTrue(signs_pass["sign_pass"])
        self.assertEqual(signs_pass["decision_rule"]["required_pairs"], 20)

        signs_fail = make_synthetic_case([100.0] * 10 + [-1.0] * 10, decision_rule="signs20")
        self.assertEqual(signs_fail["verdict"], "fail_primary")
        self.assertFalse(signs_fail["sign_pass"])

        # mean40 pass
        m40_pass = make_synthetic_case([20.0] * 35 + [5.0] * 5, decision_rule="mean40")
        self.assertEqual(m40_pass["verdict"], "pass")
        self.assertTrue(m40_pass["ci_pass"])
        self.assertTrue(m40_pass["primary_pass"])
        self.assertEqual(m40_pass["decision_rule"]["required_pairs"], 40)
        self.assertEqual(m40_pass["decision_rule"]["rule"], "mean40")

        # mean40 fail_primary (faible moyenne)
        m40_fail_low = make_synthetic_case([3.0] * 40, decision_rule="mean40")
        self.assertEqual(m40_fail_low["verdict"], "fail_primary")
        self.assertTrue(m40_fail_low["ci_pass"])
        self.assertFalse(m40_fail_low["primary_mean_pass"])
        self.assertFalse(m40_fail_low["primary_pass"])

        # mean40 fail_primary (variance élevée, borne basse négative)
        m40_fail_var = make_synthetic_case([100.0] * 22 + [-100.0] * 18, decision_rule="mean40")
        self.assertEqual(m40_fail_var["verdict"], "fail_primary")
        self.assertFalse(m40_fail_var["ci_pass"])
        self.assertFalse(m40_fail_var["primary_pass"])

        # mean40 incomplet
        m40_incomplete = make_synthetic_case([20.0] * 39, decision_rule="mean40", seeds=list(range(1, 41)))
        self.assertEqual(m40_incomplete["verdict"], "incomplete")
        self.assertFalse(m40_incomplete["comparison_complete"])


if __name__ == "__main__":
    unittest.main()
