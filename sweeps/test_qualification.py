"""Synthetic qualification gates; standard library only, no network or game."""
import copy
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

import github_qualification as runner
import qualification as q


SHA = "a" * 40
ENV = {"GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "1"}


def spec(category="behavior"):
    return dict(schema_version=2, category=category, reference="OpexAI[sample=0]",
                variant="OpexAI[sample=1]", exposure=dict(field="events", minimum=1,
                meaning="Synthetic count of executions of the changed operation"),
                opcode_component="selection" if category == "opcodes" else None,
                contract_tests=["test_qualification"], budget_minutes=270,
                rationale="Synthetic fixture, not a real qualification")


def fixture(stage="non_erosion", delta=60000, value_change=0):
    years, seeds = q.PROFILES[stage]
    campaign = f"qualification-123-1-{stage}"
    config = "[game_creation]\nstarting_year=1970\nmap_x=8\nmap_y=8\n"
    policies = [dict(id=p, role=p, ai="OpexAI", company_slot=0,
                     settings=dict(defaults={"sample": 0}, explicit={"sample": i}, effective={"sample": i}))
                for i, p in enumerate(("reference", "variant"))]
    manifest = dict(campaign_id=campaign, git=dict(sha=SHA, dirty=False),
                    versions=dict(openttd="15.3", opengfx="7.1", openttdlab="0.0.75"),
                    runtime=dict(docker_image_id_verified=True, docker_image_id="sha256:" + "b" * 64,
                                 docker_cpus=3, docker_memory="2g", docker_memory_swap="2g"),
                    configuration=dict(starting_year=1970, years=years, seeds=list(seeds), repeats=1,
                                       raw=config, sha256=hashlib.sha256(config.encode()).hexdigest(),
                                       parsed={"game_creation": {"starting_year": "1970", "map_x": "8", "map_y": "8"}}),
                    execution=dict(mode="frozen-subprocess", options=dict(max_workers=2,
                                   decision_rule=q.protocol_rule(stage)["rule"], line_telemetry=False,
                                   min_useful_primary_delta=None, min_useful_primary_delta_pct=4,
                                   value_guard_max_loss_pct=5)),
                    policies=policies, adversary=dict(settings=dict(defaults={}, explicit={}, effective={})),
                    comparison=dict(reference_policy_id="reference", variant_policy_id="variant",
                                    intervention_settings=["sample"],
                                    effective_differences={"sample": {"reference": 0, "candidate": 1}},
                                    decision_rule=q.protocol_rule(stage)),
                    source_bundle=dict(sha256="bundle", file_count=4), sources={}, libraries=[], company_slots={}, games=[])
    report = dict(campaign_id=campaign, policy_id="reference", years=years, seeds=list(seeds), repeats=1,
                  source_bundle_sha256="bundle", games=[], summary=[], failed_runs=[],
                  policy_comparison=dict(verdict="diagnostic_only" if stage == "smoke" else "pass",
                       comparison_complete=True, metric_coverage_complete=True,
                       adoption_sample_complete=stage != "smoke", planned_pairs=len(seeds), complete_pairs=len(seeds),
                       primary_metric="profit_year", value_guard_metric="company_value",
                       decision_rule=q.protocol_rule(stage), reference_policy_id="reference", variant_policy_id="variant",
                       per_pair=[dict(seed=s, repeat=0, annual_trajectory=[dict(year=1969 + years,
                           primary_metric="profit_year", reference_opex=100000, variant_opex=100000 + delta)])
                                 for s in seeds]))
    for policy in ("reference", "variant"):
        for seed in seeds:
            game_id = f"{campaign}:policy={policy}:s{seed}:r0"
            game = dict(game_id=game_id, policy_id=policy, seed=seed, repeat=0)
            manifest["games"].append(game)
            report["games"].append(dict(game, game_ok=True))
            for slot, arm in enumerate(("OpexAI", "AAAHogEx")):
                row = dict(campaign_id=campaign, duel_policy_id=policy, seed=seed, repeat=0, arm=arm,
                           game_id=game_id, company_slot=slot, source_bundle_sha256="bundle",
                           run_ok=True, game_ok=True, last_date=f"{1969 + years}-12-01", n_savegames=years * 12,
                           profit_year_coverage="complete", profit_year_quarters_valid=4,
                           profit_year_quarters_available=4,
                           profit_year=100000 + (delta if policy == "variant" and slot == 0 else 0),
                           company_value=1000000 * (1 + value_change / 100 if policy == "variant" and slot == 0 else 1),
                           events=5, observed_opcode_schema="h5.observed-v1",
                           observed_opcode_components={"selection": dict(samples=10, coverage="fixture",
                                opcodes=1000 if policy == "reference" else 500)})
                report["summary"].append(row)
    refresh(report, stage)
    return report, manifest


def refresh(report, stage):
    if stage == "smoke":
        return
    rows = {(r["duel_policy_id"], r["seed"], r["arm"]): r for r in report["summary"]}
    stats = q.economic_stats(rows, q.PROFILES[stage][1])
    report["policy_comparison"]["decision_rule"].update(
        required_pairs=len(q.PROFILES[stage][1]), required_years=q.PROFILES[stage][0],
        confidence_level=.95, bootstrap_resamples=20000, bootstrap_seed=0,
        max_wilcoxon_p_exclusive=.05, reference_terminal_profit_mean=100000,
        min_useful_primary_delta=4000)
    report["policy_comparison"]["aggregates"] = dict(
        profit_year=dict(policy_delta=dict(mean=round(stats["mean"], 6),
            mean_bootstrap_95pct_ci=stats["bootstrap_ci95"], bootstrap_resamples=20000,
            bootstrap_seed=0, wilcoxon_p=stats["wilcoxon_p"])),
        company_value=dict(policy_ratio=dict(ratio_of_means_percent_change=round(stats["value_change_pct"], 6))))
    primary = (stats["mean"] >= stats["reference_mean"] * .04 and
               stats["wilcoxon_p"] is not None and stats["wilcoxon_p"] < .05 and
               stats["bootstrap_ci95"][0] > 0) if stage == "gain_short" else stats["bootstrap_ci95"][1] >= 0
    guard = round(stats["value_change_pct"], 6) >= -5
    report["policy_comparison"]["verdict"] = ("pass" if primary and guard else
         "fail_primary_and_value_guard" if not primary and not guard else
         "fail_primary" if not primary else "fail_value_guard")



def evaluate(report, manifest, stage="non_erosion", category="behavior", **kwargs):
    return q.evaluate(spec(category), stage, report, manifest, expected_sha=SHA,
                      campaign=f"qualification-123-1-{stage}", **kwargs)


class GateTests(unittest.TestCase):
    def test_a_requires_positive_bootstrap_lower_bound_despite_mean_and_wilcoxon(self):
        report, manifest = fixture("gain_short", delta=20000)
        candidates = [r for r in report["summary"] if r["duel_policy_id"] == "variant" and r["arm"] == "OpexAI"]
        candidates[-1]["profit_year"] = -400000
        refresh(report, "gain_short")
        result = evaluate(report, manifest, "gain_short")
        self.assertGreaterEqual(result["statistics"]["mean"], 4000)
        self.assertLess(result["statistics"]["wilcoxon_p"], .05)
        self.assertLessEqual(result["statistics"]["bootstrap_ci95"][0], 0)
        self.assertEqual(result["status"], q.REJECTED)

    def test_value_guard_boundary_matches_harness_rounding(self):
        self.assertEqual(evaluate(*fixture(value_change=-5))["status"], q.ACCEPTED)
        self.assertEqual(evaluate(*fixture(value_change=-5.01))["status"], q.REJECTED)

    def test_b_pass_alone_cannot_qualify_opcode_neutrality(self):
        report, manifest = fixture(delta=-1000)
        candidates = [r for r in report["summary"] if r["duel_policy_id"] == "variant" and r["arm"] == "OpexAI"]
        candidates[-1]["profit_year"] = 130000
        refresh(report, "non_erosion")
        self.assertEqual(report["policy_comparison"]["verdict"], "pass")
        self.assertEqual(evaluate(report, manifest, category="opcodes")["status"], q.REJECTED)

    def test_schema_one_cannot_be_reinterpreted_as_v102(self):
        with self.assertRaises(ValueError):
            q.validate_spec(dict(spec(), schema_version=1))

    def test_a_uses_relative_gain_and_b_requires_no_positive_gain(self):
        self.assertEqual(evaluate(*fixture("gain_short", delta=4000), "gain_short")["status"], q.CONTINUE)
        self.assertEqual(evaluate(*fixture("gain_short", delta=3999), "gain_short")["status"], q.REJECTED)
        self.assertEqual(evaluate(*fixture(delta=0))["status"], q.ACCEPTED)
        self.assertEqual(evaluate(*fixture(delta=-1))["status"], q.REJECTED)

    def test_missing_bootstrap_wrong_rule_and_inadmissible_sample_are_invalid(self):
        mutations = [lambda c: c.update(adoption_sample_complete=False),
                     lambda c: c["decision_rule"].update(rule="signs20"),
                     lambda c: c["decision_rule"].update(required_pairs=5),
                     lambda c: c["aggregates"]["profit_year"]["policy_delta"].pop("mean_bootstrap_95pct_ci"),
                     lambda c: c["aggregates"]["profit_year"]["policy_delta"].update(bootstrap_seed=1)]
        for mutate in mutations:
            report, manifest = fixture("gain_short")
            mutate(report["policy_comparison"])
            self.assertEqual(evaluate(report, manifest, "gain_short")["status"], q.INVALID)

    def test_exposure_missing_at_smoke_stops_before_a(self):
        report, manifest = fixture("smoke")
        next(r for r in report["summary"] if r["duel_policy_id"] == "variant")["events"] = 0
        self.assertEqual(evaluate(report, manifest, "smoke")["status"], q.INVALID)

    def test_opcodes_do_not_require_gain_short_and_need_prior_saving(self):
        self.assertEqual(q.stages_for(spec("opcodes")), ("smoke", "non_erosion"))
        report, manifest = fixture("smoke")
        for row in report["summary"]:
            row["observed_opcode_components"]["selection"]["opcodes"] = 1000
        self.assertEqual(evaluate(report, manifest, "smoke", category="opcodes")["status"], q.INVALID)

    def test_ordinary_pass(self):
        decision = evaluate(*fixture())
        self.assertEqual(decision["status"], q.ACCEPTED)
        self.assertEqual(decision["statistics"]["wins"], 20)
        self.assertAlmostEqual(decision["statistics"]["sign_test_p"], 2 / 2**20)

    def test_economic_rejection_is_not_technical_failure(self):
        for delta, change in ((-49000, 0), (60000, -6), (-60000, -6)):
            with self.subTest(delta=delta, change=change):
                self.assertEqual(evaluate(*fixture(delta=delta, value_change=change))["status"], q.REJECTED)

    def test_health_missing_duplicates_and_nonfinite_are_invalid(self):
        mutations = [lambda r: r["summary"].pop(),
                     lambda r: r["summary"].append(copy.deepcopy(r["summary"][0])),
                     lambda r: r["games"].pop(),
                     lambda r: r["games"][0].update(game_ok=False),
                     lambda r: r["summary"][0].update(run_ok=False),
                     lambda r: r["summary"][0].update(profit_year=float("nan")),
                     lambda r: r["summary"][0].update(profit_year=True),
                     lambda r: r["summary"][0].update(company_value=0),
                     lambda r: r["summary"][0].update(profit_year_coverage="partial"),
                     lambda r: r["summary"][0].update(profit_year_quarters_valid=3),
                     lambda r: r["summary"][0].update(last_date="1979-01-01"),
                     lambda r: r["summary"][0].update(n_savegames=119),
                     lambda r: r["summary"][0].update(source_bundle_sha256="other"),
                     lambda r: r["failed_runs"].append({"reason": "engine"})]
        for mutate in mutations:
            report, manifest = fixture()
            mutate(report)
            self.assertEqual(evaluate(report, manifest)["status"], q.INVALID)

    def test_wrong_protocol_or_provenance_is_invalid(self):
        mutations = [lambda m: m["git"].update(sha="b" * 40), lambda m: m["git"].update(dirty=True),
                     lambda m: m["configuration"].update(years=3),
                     lambda m: m["configuration"].update(seeds=[42] * 20),
                     lambda m: m["configuration"].update(repeats=2),
                     lambda m: m["execution"].update(mode="live"),
                     lambda m: m["runtime"].update(docker_cpus=8),
                     lambda m: m["versions"].update(openttd="13.4"),
                     lambda m: m["comparison"]["decision_rule"].update(min_useful_primary_delta=0),
                     lambda m: m["policies"][0]["settings"]["defaults"].update(sample=1),
                     lambda m: m["policies"][1]["settings"]["explicit"].update(sample=2)]
        for mutate in mutations:
            report, manifest = fixture()
            mutate(manifest)
            self.assertEqual(evaluate(report, manifest)["status"], q.INVALID)

    def test_cross_stage_identity_drift(self):
        report, manifest = fixture()
        previous = q.identity(manifest)
        previous["bundle_sha256"] = "other"
        self.assertEqual(evaluate(report, manifest, previous=previous)["status"], q.INVALID)

    def test_smoke_is_health_only_and_not_acceptance(self):
        report, manifest = fixture("smoke")
        for row in report["summary"]:
            row.update(profit_year_coverage="partial", profit_year_quarters_valid=3)
        result = evaluate(report, manifest, "smoke")
        self.assertEqual(result["status"], q.CONTINUE)
        self.assertTrue(result["proceed"])

    def test_a_pass_and_stop(self):
        self.assertEqual(evaluate(*fixture("gain_short"), "gain_short")["status"], q.CONTINUE)
        self.assertEqual(evaluate(*fixture("gain_short", delta=3000), "gain_short")["status"], q.REJECTED)

    def test_missing_unexposed_or_boolean_probe_never_qualifies(self):
        for value in (None, 0, True, float("inf")):
            report, manifest = fixture()
            next(r for r in report["summary"] if r["duel_policy_id"] == "variant")["events"] = value
            self.assertEqual(evaluate(report, manifest)["status"], q.INVALID)

    def test_inconsistent_harness_verdict_or_aggregate_is_invalid(self):
        report, manifest = fixture()
        report["policy_comparison"]["verdict"] = "fail_primary"
        self.assertEqual(evaluate(report, manifest)["status"], q.INVALID)
        report, manifest = fixture()
        report["policy_comparison"]["aggregates"]["profit_year"]["policy_delta"]["mean"] = 90000
        self.assertEqual(evaluate(report, manifest)["status"], q.INVALID)

    def test_b_has_no_fifteen_win_requirement(self):
        report, manifest = fixture()
        candidates = [r for r in report["summary"] if r["duel_policy_id"] == "variant" and r["arm"] == "OpexAI"]
        for row in candidates[:14]:
            row["profit_year"] = 300000
        for row in candidates[14:]:
            row["profit_year"] = 99000
        refresh(report, "non_erosion")
        self.assertEqual(evaluate(report, manifest)["status"], q.ACCEPTED)

    def test_opcodes_neutrality_keeps_raw_harness_verdict(self):
        result = evaluate(*fixture(delta=0), category="opcodes")
        self.assertEqual(result["status"], q.ACCEPTED)
        self.assertEqual(result["raw_harness_verdict"], "pass")
        self.assertEqual(result["opcode_saving_per_sample"], 50)

    def test_opcodes_economic_loss_or_no_saving_rejected(self):
        self.assertEqual(evaluate(*fixture(delta=-1000), category="opcodes")["status"], q.REJECTED)
        report, manifest = fixture(delta=0)
        for row in report["summary"]:
            row["observed_opcode_components"]["selection"]["opcodes"] = 1000
        self.assertEqual(evaluate(report, manifest, category="opcodes")["status"], q.REJECTED)

    def test_opcodes_missing_or_asymmetric_measurement_invalid(self):
        for change in ({"samples": 0}, {"samples": 11}, {"opcodes": None}, {"coverage": "other"}):
            report, manifest = fixture(delta=0)
            report["summary"][0]["observed_opcode_components"]["selection"].update(change)
            self.assertEqual(evaluate(report, manifest, category="opcodes")["status"], q.INVALID)

    def test_value_guard_is_ratio_of_means_not_mean_of_ratios(self):
        report, _ = fixture("gain_short")
        rows = {(r["duel_policy_id"], r["seed"], r["arm"]): r for r in report["summary"]}
        for seed in q.PROFILES["gain_short"][1]:
            rows[("reference", seed, "OpexAI")]["company_value"] = 100
            rows[("variant", seed, "OpexAI")]["company_value"] = 100
        rows[("reference", 42, "OpexAI")]["company_value"] = 1000
        stats = q.economic_stats(rows, q.PROFILES["gain_short"][1])
        self.assertAlmostEqual(stats["value_change_pct"], 100 * (4000 / 4900 - 1))

    def test_spec_rejects_injection_duplicates_and_relaxed_thresholds(self):
        for change in ({"reference": "OpexAI"}, {"variant": "OpexAI[sample=1]; echo bad"},
                       {"variant": "OpexAI[sample=1,sample=2]"}, {"budget_minutes": 271},
                       {"budget_minutes": True}, {"contract_tests": []},
                       {"contract_tests": ["test_foo;echo"]}, {"min_delta": 0}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                q.validate_spec(dict(spec(), **change))

    def test_json_rejects_nonfinite_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            for text in ('{"x": NaN}', '{"x": 1, "x": 2}'):
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    q.read_json(path)


class ArtifactTests(unittest.TestCase):
    def test_optional_january_checkpoint_is_accepted_but_duplicates_are_rejected(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            output = self.materialize(Path(tmp))
            report = q.read_json(output)
            with output.with_suffix(".jsonl").open("a", encoding="utf-8") as handle:
                for summary in report["summary"]:
                    summary.update(last_date="1973-01-01", n_savegames=37)
                    handle.write(json.dumps(dict(summary, run=[summary["arm"], summary["seed"], 0], date=summary["last_date"])) + "\n")
            q.write_json(output, report)
            q.load_evidence(output)
            with output.with_suffix(".jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(dict(summary, run=[summary["arm"], summary["seed"], 0], date=summary["last_date"])) + "\n")
            with self.assertRaises(ValueError):
                q.load_evidence(output)

    def materialize(self, root):
        report, manifest = fixture("gain_short")
        bundle = root / "bench_bundle"
        for name, relative in (("OpexAI", "ai/OpexAI"), ("AAAHogEx", "ai/AAAHogEx-115"),
                               ("harness", "harness"), ("ai_libraries", "ai_libraries")):
            folder = bundle / relative
            folder.mkdir(parents=True)
            text = ('AddSetting({ name = "sample", custom_value = 0 });' if name == "OpexAI" else "fixture")
            (folder / "info.nut").write_text(text, encoding="utf-8")
            manifest["sources"][name] = q.fingerprint_tree(folder)
        fp = q.fingerprint_tree(bundle)
        manifest["source_bundle"] = dict(path="/work/old/location/bench_bundle", sha256=fp["sha256"], file_count=fp["file_count"])
        report["source_bundle_sha256"] = fp["sha256"]
        output = root / "bench.json"
        (root / "bench_engine").mkdir()
        for game in report["games"]:
            name = f"{game['policy_id']}-{game['seed']}.log"
            game["engine_log_path"] = "/work/old/location/bench_engine/" + name
            (root / "bench_engine" / name).write_text("fixture", encoding="utf-8")
        import json
        with (root / "bench.jsonl").open("w", encoding="utf-8") as handle:
            for summary in report["summary"]:
                summary["source_bundle_sha256"] = fp["sha256"]
                for year in range(1970, 1970 + report["years"]):
                    for month in range(1, 13):
                        row = dict(summary, run=[summary['arm'], summary['seed'], 0], date=f"{year}-{month:02d}-01")
                        handle.write(json.dumps(row) + "\n")
        q.write_json(root / "bench.manifest.json", manifest)
        report["manifest_sha256"] = q.digest(root / "bench.manifest.json")
        q.write_json(output, report)
        return output

    def test_relocated_bundle_and_manifest_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = self.materialize(Path(tmp))
            report, manifest = q.load_evidence(output)
            self.assertEqual(report["source_bundle_sha256"], manifest["source_bundle"]["sha256"])

    def test_tampered_bundle_manifest_or_missing_checkpoints_rejected(self):
        for target in ("bench_bundle/ai/OpexAI/info.nut", "bench.manifest.json", "bench.jsonl"):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                output = self.materialize(root)
                if target.endswith("jsonl"):
                    (root / target).unlink()
                else:
                    with (root / target).open("a", encoding="utf-8") as handle:
                        handle.write("changed")
                with self.assertRaises(ValueError):
                    q.load_evidence(output)

    def test_empty_checkpoints_or_modified_final_summary_rejected(self):
        for empty in (True, False):
            with self.subTest(empty=empty), tempfile.TemporaryDirectory() as tmp:
                output = self.materialize(Path(tmp))
                if empty:
                    output.with_suffix(".jsonl").write_text("", encoding="utf-8")
                else:
                    report = q.read_json(output)
                    report["summary"][0]["profit_year"] += 1
                    q.write_json(output, report)
                with self.assertRaises(ValueError):
                    q.load_evidence(output)


class SequenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(self.tmp)
        self.enterContext(mock.patch.object(runner, "ROOT", self.root))
        self.enterContext(mock.patch.object(runner, "urlopen", side_effect=AssertionError("Network forbidden")))
        self.enterContext(mock.patch.object(runner.subprocess, "Popen", side_effect=AssertionError("Engine forbidden")))

    def setup_request(self, category="behavior"):
        directory = runner.location(ENV)
        directory.mkdir(parents=True)
        plan_path = self.root / "qualifications/test.json"
        plan_path.parent.mkdir()
        q.write_json(plan_path, spec(category))
        request = dict(spec=spec(category), spec_path="qualifications/test.json", spec_sha256=q.digest(plan_path),
                       qualification_id=directory.name, sha=SHA, schema_version=2, run_id="123", attempt="1",
                       stages=[runner.stage_plan(spec(category), stage, ENV) for stage in q.stages_for(spec(category))])
        q.write_json(directory / "request.json", request)
        q.write_json(directory / "contracts.json", dict(exit_code=0, request_sha256=q.digest(directory / "request.json")))
        return directory

    def test_unique_stage_paths_and_fixed_commands(self):
        plans = [runner.stage_plan(spec(), stage, ENV) for stage in q.PROFILES]
        self.assertEqual(len({p["output"] for p in plans}), 3)
        self.assertEqual([p["expected_games"] for p in plans], [2, 80, 40])
        self.assertEqual(plans[2]["seeds"], q.SEEDS)

    def test_opcode_sequence_has_two_stages_and_tampered_stage_request_is_refused(self):
        directory = self.setup_request("opcodes")
        request = runner.request_at(directory)
        self.assertEqual([p["profile"] for p in request["stages"]], ["smoke", "non_erosion"])
        request["stages"][1]["minimum"] = 0
        q.write_json(directory / "request.json", request)
        with self.assertRaises(ValueError):
            runner.request_at(directory)

    def test_initialization_checks_declared_default_and_writes_request(self):
        plan = self.root / "qualifications/test.json"
        plan.parent.mkdir()
        q.write_json(plan, spec())
        info = self.root / "ai/OpexAI/info.nut"
        info.parent.mkdir(parents=True)
        info.write_text('AddSetting({ name = "sample", min_value = 0, max_value = 1, custom_value = 0 });',
                        encoding="utf-8")
        contracts = self.root / "sweeps"
        contracts.mkdir()
        (contracts / "test_qualification.py").write_text("# fixture", encoding="utf-8")
        env = dict(ENV, GITHUB_SHA=SHA, QUALIFICATION_PLAN="qualifications/test.json")
        with mock.patch.object(runner.subprocess, "check_output", side_effect=[SHA, ""]):
            runner.initialize(env)
        request = q.read_json(runner.location(ENV) / "request.json")
        self.assertEqual(request["sha"], SHA)
        self.assertEqual(len(request["stages"]), 3)
        self.assertEqual(q.read_json(runner.location(ENV) / "decision.json")["status"], q.INVALID)

    def test_unvalidated_contracts_cannot_launch_a_game(self):
        directory = self.setup_request()
        (directory / "contracts.json").unlink()
        execute = mock.Mock()
        with self.assertRaises(FileNotFoundError):
            runner.run_sequence(directory, execute=execute)
        execute.assert_not_called()

    def test_complete_sequence_accepts_only_after_three_gates(self):
        directory = self.setup_request()
        evidence = [fixture(stage) for stage in q.PROFILES]
        def execute(command, **kwargs):
            output = self.root / command[command.index("--out") + 1]
            q.write_json(output, {})
            q.write_json(output.with_suffix(".manifest.json"), {})
            return 0
        with mock.patch.object(runner, "load_evidence", side_effect=evidence), mock.patch.object(runner, "summary_text", return_value="fixture"), mock.patch.object(runner, "profit_ratios", return_value=[]):
            code = runner.run_sequence(directory, execute=execute)
        self.assertEqual(code, 0)
        decision = q.read_json(directory / "decision.json")
        self.assertEqual(decision["status"], q.ACCEPTED)
        self.assertEqual(len(decision["stages"]), 3)

    def test_stop_at_failed_engine_or_timeout(self):
        for outcome in (1, subprocess.TimeoutExpired("fixture", 1)):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as tmp:
                with mock.patch.object(runner, "ROOT", Path(tmp)):
                    self.root = Path(tmp)
                    directory = self.setup_request()
                    execute = mock.Mock(side_effect=outcome if isinstance(outcome, Exception) else None,
                                        return_value=outcome)
                    self.assertEqual(runner.run_sequence(directory, execute=execute), 1)
                    execute.assert_called_once()
                    self.assertFalse((directory / "gain_short").exists())
                    self.assertEqual(q.read_json(directory / "decision.json")["status"], q.INVALID)

    def test_stop_at_a_rejection_without_b(self):
        directory = self.setup_request()
        evidence = [fixture("smoke"), fixture("gain_short", delta=0)]
        def execute(command, **kwargs):
            output = self.root / command[command.index("--out") + 1]
            q.write_json(output, {})
            q.write_json(output.with_suffix(".manifest.json"), {})
            return 0
        with mock.patch.object(runner, "load_evidence", side_effect=evidence), mock.patch.object(runner, "summary_text", return_value="fixture"), mock.patch.object(runner, "profit_ratios", return_value=[]):
            self.assertEqual(runner.run_sequence(directory, execute=execute), 2)
        self.assertFalse((directory / "non_erosion").exists())

    def test_contract_receipt_required_and_plan_immutable(self):
        directory = self.setup_request()
        q.write_json(self.root / "qualifications/test.json", dict(spec(), budget_minutes=1))
        with self.assertRaises(ValueError):
            runner.request_at(directory)

    def test_missing_decision_summary_fails_closed(self):
        directory = runner.location(ENV)
        with mock.patch.dict(runner.os.environ, {"GITHUB_STEP_SUMMARY": ""}):
            runner.summarize(directory)
        self.assertEqual(q.read_json(directory / "decision.json")["status"], q.INVALID)


if __name__ == "__main__":
    unittest.main()
