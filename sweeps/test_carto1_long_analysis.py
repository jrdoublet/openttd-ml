"""Synthetic protocol fixtures for the independent CARTO-1 long-run analyzer."""

from contextlib import redirect_stdout
from contextlib import redirect_stderr
import gzip
import io
import json
from pathlib import Path
import tempfile
import unittest

from sweeps.analyze_carto1_long import (
    analyze_paths, analyze_sources, auc, confusion, decode_line, main,
    render_markdown, train_threshold, validate_campaign,
)


def event(tag, *, when="1971-7-12", **values):
    return ("[script:4] [0] [I] OPEX " + when + " " + tag + " "
            + " ".join(f"{key}={value}" for key, value in values.items()) + "\n")


def game_lines(seed, failures, *, sites=0, samples=30, scores=None,
               site_value="missing_virtual_endpoint", when="1971-7-12"):
    """Thirty independently identified candidate episodes, no reused src/dst join."""
    lines = [
        event("RLW04B_ENUM", phase="start", stock=samples, sample_seed=seed + 1000),
        event("RLW04B_ENUM", phase="done", stock=samples, sample_seed=seed + 1000,
              overruns=0, ticks=0),
    ]
    costs = []
    astars = []
    for sample in range(samples):
        key = f"freight:1:{seed * 1000 + sample}:{seed * 1000 + sample + 500}"
        lines.append(event("CARTO1_LONG_SAMPLE", sample=sample, key=key,
                           src=sample + 50, dst=sample + 500, distance=224 + sample))
        is_site = sample >= samples - sites
        is_failure = sample < failures
        score = (scores[sample] if scores is not None else 25 if is_failure else 5)
        costs.append(event("CARTO1_LONG_COST", sample=sample, key=key,
                           route=score * 4, route_blocks=4, ops=10, valid=1, ticks=0))
        astars.append(event("CARTO1_LONG_ASTAR", sample=sample, key=key, phase="end",
                            started=0 if is_site else 1,
                            site=site_value if is_site else "virtual",
                            outcome="NOPA" if is_site else "ABND" if is_failure else "OK",
                            search_ops=0 if is_site else 2000 if is_failure else 500,
                            iters=0 if is_site else 5000 if is_failure else 20,
                            overruns=0))
    # Real CARTO-1 long logs emit all costs before the A* results.
    lines += costs + astars
    lines.append(event("CARTO1_LONG_SUMMARY", phase="done", samples=samples,
                       completed=samples, failures=failures + sites,
                       costs=samples, map_ops=samples * 10,
                       search_ops=(failures * 2000 + (samples - failures - sites) * 500),
                       mapx=1024, mapy=1024, cap=5000, overruns=0))
    return [line.replace("OPEX 1971-7-12 ", f"OPEX {when} ") for line in lines]


def three_games(failures=(8, 9, 7), *, sites=(0, 0, 0),
                when="1971-7-12"):
    return [(f"reference_seed{seed}_r0.log",
             game_lines(seed, count, sites=site, when=when))
            for seed, count, site in zip((42, 100, 999), failures, sites)]


def campaign_evidence(campaign="carto1_long", *, years=3, map_size=10):
    games = [
        {"policy_id": "reference", "seed": seed, "repeat": 0,
         "game_ok": True, "game_status": "complete",
         "engine_log_path": f"/work/results/{campaign}_engine/reference_seed{seed}_r0.log",
         "unattributed_errors": [],
         "companies": {"OpexAI": {"horizon_complete": True}}}
        for seed in (42, 100, 999)
    ]
    result = {
        "campaign_id": campaign, "years": years, "map_size": map_size,
        "seeds": [42, 100, 999], "repeats": 1,
        "start_year": 1970, "expected_last_year": 1970 + years - 1, "games": games,
    }
    manifest = {
        "campaign_id": campaign,
        "git": {"sha": "fixture-git-sha"},
        "execution": {"options": {
            "reference": "OpexAI[probes=50331650]",
            "script_debug": True,
            "docker_image_id": "sha256:fixture",
        }},
        "configuration": {"years": years, "map_size": map_size,
                          "seeds": [42, 100, 999], "repeats": 1,
                          "starting_year": 1970},
        "games": [{"policy_id": "reference", "seed": seed, "repeat": 0}
                  for seed in (42, 100, 999)],
    }
    return result, manifest


class CARTO1LongAnalysisTests(unittest.TestCase):
    def test_parser_accepts_decorated_opex_date_and_ignores_other_tags(self):
        parsed = decode_line(event("CARTO1_LONG_SAMPLE", when="1972-2-4",
                                   sample=3, key="freight:0:10:20"))
        self.assertEqual(parsed[0].isoformat(), "1972-02-04")
        self.assertEqual(parsed[1], "CARTO1_LONG_SAMPLE")
        self.assertEqual(parsed[2]["sample"], "3")
        self.assertIsNone(decode_line("OPEX 1972-14-20 CARTO1_LONG_SAMPLE sample=0"))
        self.assertIsNone(decode_line("OPEX 1972-1-1 OTHER sample=0"))
        self.assertIsNone(decode_line("CARTO1_LONG_SAMPLE sample=0"))

    def test_three_seed_loso_no_test_leak_and_aggregate_ops(self):
        report = analyze_sources(three_games())
        policy = report["policies"]["reference"]
        self.assertTrue(policy["complete"], policy["errors"])
        self.assertTrue(policy["predictive_validated"])
        self.assertEqual((policy["samples"], policy["failures"], policy["successes"]),
                         (90, 24, 66))
        self.assertEqual(policy["pooled_auc"], 1.0)
        self.assertEqual(policy["cartography_ops"], 900)
        self.assertEqual(policy["cartography_ops_scope"], "all_probe")
        self.assertEqual(policy["potential_astar_ops_saved"], 48000)
        self.assertEqual(policy["potential_net_ops"], 47100)
        self.assertEqual(policy["out_of_fold_confusion"],
                         {"tp": 24, "fp": 0, "tn": 66, "fn": 0,
                          "sensitivity": 1.0, "specificity": 1.0})
        for fold in policy["folds"]:
            self.assertEqual(fold["threshold"], 25)
            self.assertEqual(fold["auc"], 1.0)
            self.assertNotIn(fold["test_seed"], fold["train_seeds"])
            self.assertEqual(len(fold["train_seeds"]), 2)
            self.assertEqual(fold["train_n"], 60)
            self.assertEqual(fold["test_n"], 30)
        self.assertIn("hors graine", render_markdown(report))
        self.assertFalse(report["protocol"]["horizon_verified_from_logs"])

    def test_exact_youden_tie_chooses_conservative_highest_threshold(self):
        train = [{"score": 10.0, "failed": bool(i % 2)} for i in range(8)]
        # Either class is indistinguishable: predicting none gives J=0.
        cutoff = train_threshold(train)
        self.assertGreater(cutoff, 10)
        self.assertEqual(confusion(train, cutoff)["tp"], 0)
        self.assertEqual(confusion(train, cutoff)["fp"], 0)
        self.assertEqual(auc(train), 0.5)

    def test_site_failure_is_separate_and_not_a_real_astar_failure(self):
        # One NOPA without any A* cannot contribute a positive label or saved ops.
        report = analyze_sources(three_games((8, 9, 7), sites=(1, 0, 0)))
        policy = report["policies"]["reference"]
        self.assertTrue(policy["complete"], policy["errors"])
        self.assertEqual(policy["samples"], 90)
        self.assertEqual(policy["real_astar"], 89)
        self.assertEqual(policy["site_failures"], 1)
        self.assertEqual(policy["failures"], 24)
        self.assertEqual(policy["successes"], 65)
        self.assertEqual(policy["games"][0]["summary"]["failures"], "9")
        self.assertEqual(policy["out_of_fold_confusion"]["tn"], 65)
        self.assertEqual(policy["potential_astar_ops_saved"], 48000)

    def test_true_nopa_started_is_a_genuine_failure(self):
        sources = three_games()
        file, lines = sources[0]
        sources[0] = (file, [line.replace("outcome=ABND", "outcome=NOPA", 1)
                             for line in lines])
        report = analyze_sources(sources)
        self.assertTrue(report["policies"]["reference"]["complete"])
        self.assertEqual(report["policies"]["reference"]["failures"], 24)

    def test_fail_closed_if_less_than_20_true_astar_failures(self):
        report = analyze_sources(three_games((5, 5, 5)))
        policy = report["policies"]["reference"]
        self.assertFalse(policy["data_complete"])
        self.assertFalse(policy["complete"])
        self.assertIsNone(policy["pooled_auc"])
        self.assertIsNone(policy["out_of_fold_confusion"])
        self.assertIn("15/20", "\n".join(policy["errors"]))

    def test_tick_crossings_disqualify_even_perfect_predictor(self):
        def replace_one(lines, tag, original, replacement):
            replaced = False
            updated = []
            for line in lines:
                if not replaced and tag in line and original in line:
                    line = line.replace(original, replacement, 1)
                    replaced = True
                updated.append(line)
            self.assertTrue(replaced, (tag, original))
            return updated

        cases = (
            ("CARTO1_LONG_ASTAR", "overruns=0", "overruns=1", "sample=0"),
            ("CARTO1_LONG_COST", "ticks=0", "ticks=1", "sample=0"),
            ("CARTO1_LONG_SUMMARY", "overruns=0", "overruns=1", "SUMMARY"),
            ("RLW04B_ENUM phase=done", "ticks=0", "ticks=1", "RLW04B_ENUM"),
            ("CARTO1_LONG_SUMMARY", "phase=done", "phase=unsafe", "SUMMARY"),
        )
        for tag, old, new, diagnostic in cases:
            with self.subTest(source=tag):
                sources = three_games()
                sources[0] = (
                    sources[0][0], replace_one(sources[0][1], tag, old, new)
                )
                policy = analyze_sources(sources)["policies"]["reference"]
                self.assertFalse(policy["complete"])
                self.assertFalse(policy["data_complete"])
                self.assertIsNone(policy["pooled_auc"])
                self.assertIsNone(policy["potential_astar_ops_saved"])
                self.assertIn(diagnostic, " ".join(policy["errors"]))

    def test_pre_registration_order_and_safety_abort_fail_closed(self):
        # Labels are never usable if an A* starts before the entire fixed
        # reservoir has both SAMPLE and COST, even if all 90 finally arrive.
        sources = three_games()
        lines = sources[0][1]
        first_cost = next(i for i, line in enumerate(lines) if "CARTO1_LONG_COST" in line)
        first_astar = next(i for i, line in enumerate(lines) if "CARTO1_LONG_ASTAR" in line)
        reordered = lines.copy()
        reordered.insert(first_cost, reordered.pop(first_astar))
        sources[0] = sources[0][0], reordered
        policy = analyze_sources(sources)["policies"]["reference"]
        self.assertFalse(policy["complete"])
        self.assertIsNone(policy["pooled_auc"])
        self.assertIn("avant pré-enregistrement complet", " ".join(policy["errors"]))

        sources = three_games()
        sources[0] = sources[0][0], sources[0][1] + [
            event("CARTO1_LONG_SAFETY", phase="abort",
                  reason="astar_slice_tick_cross", sample=29)
        ]
        policy = analyze_sources(sources)["policies"]["reference"]
        self.assertFalse(policy["complete"])
        self.assertIsNone(policy["out_of_fold_confusion"])
        self.assertIn("arrêt de sécurité", " ".join(policy["errors"]))

    def test_real_astar_distance_and_findpath_provenance(self):
        cases = (
            ("distance=224", "distance=223"),
            ("iters=5000", "iters=0"),
        )
        for previous, replacement in cases:
            with self.subTest(field=previous):
                sources = three_games()
                lines = sources[0][1]
                changed = False
                altered = []
                for line in lines:
                    if not changed and previous in line:
                        line = line.replace(previous, replacement, 1)
                        changed = True
                    altered.append(line)
                self.assertTrue(changed)
                sources[0] = sources[0][0], altered
                policy = analyze_sources(sources)["policies"]["reference"]
                self.assertFalse(policy["complete"])
                self.assertIsNone(policy["pooled_auc"])

    def test_missing_safety_counters_fail_closed(self):
        cases = (
            ("CARTO1_LONG_ASTAR", "overruns=0"),
            ("CARTO1_LONG_COST", "ticks=0"),
            ("CARTO1_LONG_SUMMARY", "overruns=0"),
            ("RLW04B_ENUM phase=done", "overruns=0"),
        )
        for tag, field in cases:
            with self.subTest(tag=tag):
                sources = three_games()
                original = sources[0][1]
                changed = False
                altered = []
                for line in original:
                    if not changed and tag in line and field in line:
                        line = line.replace(" " + field, "", 1)
                        changed = True
                    altered.append(line)
                self.assertTrue(changed, (tag, field))
                sources[0] = sources[0][0], altered
                policy = analyze_sources(sources)["policies"]["reference"]
                self.assertFalse(policy["complete"])
                self.assertIsNone(policy["pooled_auc"])

    def test_only_one_class_in_test_fold_has_null_auc_and_sensitivity(self):
        report = analyze_sources(three_games((0, 11, 12)))
        policy = report["policies"]["reference"]
        self.assertTrue(policy["complete"])
        self.assertFalse(policy["predictive_validated"])
        empty = policy["folds"][0]
        self.assertIsNone(empty["auc"])
        self.assertIsNone(empty["confusion"]["sensitivity"])
        self.assertIsNotNone(empty["confusion"]["specificity"])
        self.assertIsNotNone(policy["pooled_auc"])

    def test_only_one_class_in_train_fold_blocks_full_loso(self):
        report = analyze_sources(three_games((22, 0, 0)))
        policy = report["policies"]["reference"]
        self.assertTrue(policy["data_complete"])
        self.assertFalse(policy["complete"])
        self.assertIsNone(policy["folds"][0]["threshold"])
        self.assertIsNone(policy["folds"][0]["confusion"])
        self.assertIsNone(policy["out_of_fold_confusion"])
        self.assertIn("n'a qu'une classe", " ".join(policy["errors"]))

    def test_missing_sample_refuses_all_statistical_metrics(self):
        report = analyze_sources(three_games((8, 9, 7))[:2]
                                 + [("reference_seed999_r0.log",
                                     game_lines(999, 7, samples=29))])
        policy = report["policies"]["reference"]
        self.assertFalse(policy["complete"])
        self.assertEqual(policy["samples"], 89)
        self.assertIsNone(policy["pooled_auc"])
        self.assertEqual(policy["folds"], [])
        self.assertIn("sample=29", " ".join(policy["errors"]))

    def test_discordant_keys_duplicate_and_bad_cost_are_rejected(self):
        cases = (
            lambda lines: lines + [event("CARTO1_LONG_SAMPLE",
                                         sample=0, key="freight:1:1:2")],
            lambda lines: [line.replace("route=100 ", "route=-1 ", 1)
                           if "CARTO1_LONG_COST" in line else line for line in lines],
            lambda lines: [line.replace("key=freight:1:42000:42500",
                                        "key=freight:1:999:1000")
                           if "CARTO1_LONG_COST" in line else line for line in lines],
        )
        for mutate in cases:
            with self.subTest(mutator=mutate):
                sources = three_games()
                sources[0] = (sources[0][0], mutate(sources[0][1]))
                policy = analyze_sources(sources)["policies"]["reference"]
                self.assertFalse(policy["complete"])
                self.assertIsNone(policy["pooled_auc"])
                self.assertTrue(policy["errors"])

    def test_absent_enum_or_summary_and_wrong_map_are_incomplete(self):
        for removed in ("RLW04B_ENUM", "CARTO1_LONG_SUMMARY"):
            sources = three_games()
            sources[0] = (sources[0][0],
                          [line for line in sources[0][1] if removed not in line])
            report = analyze_sources(sources)
            self.assertFalse(report["policies"]["reference"]["complete"])
        sources = three_games()
        sources[0] = (sources[0][0],
                      [line.replace("mapx=1024", "mapx=256") for line in sources[0][1]])
        self.assertFalse(analyze_sources(sources)["policies"]["reference"]["complete"])

    def test_filenames_repetitions_duplicate_seed_and_extra_seed(self):
        with self.assertRaisesRegex(ValueError, "Nom de fichier"):
            analyze_sources([("no_seed.log", [])])
        sources = three_games()
        report = analyze_sources(sources + [(sources[0][0], sources[0][1])])
        self.assertFalse(report["policies"]["reference"]["complete"])
        report = analyze_sources(sources + [("reference_seed11_r0.log",
                                            game_lines(11, 9))])
        self.assertFalse(report["policies"]["reference"]["complete"])
        sources[1] = ("reference_seed100_r1.log", sources[1][1])
        self.assertFalse(analyze_sources(sources)["policies"]["reference"]["complete"])

    def test_gzip_directory_and_cli_json_require_complete(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            for filename, lines in three_games():
                with gzip.open(directory / (filename + ".gz"), "wt", encoding="utf-8") as handle:
                    handle.writelines(lines)
            policy = analyze_paths([directory])["policies"]["reference"]
            self.assertTrue(policy["complete"], policy["errors"])
            result, manifest = campaign_evidence()
            result_path = directory / "campaign.json"
            manifest_path = directory / "campaign.manifest.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            out = directory / "summary.json"
            self.assertEqual(main([str(directory), "--result-json", str(result_path),
                                   "--manifest", str(manifest_path),
                                   "--format", "json", "--out", str(out),
                                   "--require-complete"]), 0)
            self.assertTrue(json.loads(out.read_text(encoding="utf-8"))["policies"]
                            ["reference"]["complete"])
            (directory / "reference_seed999_r0.log.gz").unlink()
            with redirect_stdout(io.StringIO()) as output:
                status = main([str(directory), "--require-complete",
                               "--result-json", str(result_path),
                               "--manifest", str(manifest_path)])
            self.assertEqual(status, 1)
            self.assertIn("Incomplétude", output.getvalue())

    def test_campaign_scope_fails_closed_on_horizon_map_and_game_health(self):
        for change in ("years", "map", "game"):
            with self.subTest(change=change):
                report = analyze_sources(three_games())
                result, manifest = campaign_evidence()
                if change == "years":
                    result["years"] = 2
                elif change == "map":
                    manifest["configuration"]["map_size"] = 8
                else:
                    result["games"][0]["companies"]["OpexAI"]["horizon_complete"] = False
                validate_campaign(report, result, manifest)
                policy = report["policies"]["reference"]
                self.assertFalse(policy["complete"])
                self.assertFalse(policy["campaign_verified"])
                self.assertTrue(policy["campaign_errors"])

    def test_preregistered_horizons_3_8_10_verify_expected_terminal_year(self):
        for years, when in ((3, "1972-12-1"), (8, "1977-12-1"),
                            (10, "1979-12-1")):
            with self.subTest(years=years):
                report = analyze_sources(three_games(when=when), years=years)
                self.assertEqual(report["protocol"]["years"], years)
                result, manifest = campaign_evidence(years=years)
                validate_campaign(report, result, manifest)
                policy = report["policies"]["reference"]
                self.assertTrue(policy["complete"], policy.get("campaign_errors"))
                self.assertTrue(policy["campaign_verified"])
                self.assertEqual((policy["samples"], policy["failures"]), (90, 24))
                self.assertEqual(policy["games"][0]["samples"], 30)
                scope = report["protocol"]["campaign_scope_evidence"]
                self.assertEqual(scope["expected_years"], years)
                self.assertEqual(scope["result_years"], years)
                self.assertEqual(scope["manifest_years"], years)
                self.assertEqual(scope["expected_last_year"], 1970 + years - 1)
                self.assertEqual(scope["result_expected_last_year"], 1970 + years - 1)
                self.assertIn(f"{years} ans", render_markdown(report))

    def test_extended_horizon_must_match_both_json_and_manifest(self):
        for years in (8, 10):
            with self.subTest(years=years):
                cases = ("wrong_result_years", "wrong_manifest_years",
                         "wrong_expected_last_year", "event_outside")
                for kind in cases:
                    with self.subTest(kind=kind):
                        when = f"{1970 + years}-1-1" if kind == "event_outside" else "1977-1-1"
                        report = analyze_sources(three_games(when=when), years=years)
                        result, manifest = campaign_evidence(years=years)
                        if kind == "wrong_result_years":
                            result["years"] = 3
                        elif kind == "wrong_manifest_years":
                            manifest["configuration"]["years"] = 3
                        elif kind == "wrong_expected_last_year":
                            result["expected_last_year"] = 1972
                        validate_campaign(report, result, manifest)
                        policy = report["policies"]["reference"]
                        self.assertFalse(policy["campaign_verified"])
                        self.assertFalse(policy["complete"])
                        self.assertTrue(policy["campaign_errors"])

    def test_longer_healthy_game_cannot_hide_missing_cost_or_astar(self):
        for years in (8, 10):
            for missing_tag in ("CARTO1_LONG_COST", "CARTO1_LONG_ASTAR"):
                with self.subTest(years=years, missing=missing_tag):
                    sources = three_games(when=f"{1970 + years - 1}-6-1")
                    file, lines = sources[0]
                    sources[0] = (file, [line for line in lines
                                         if not (missing_tag in line and "sample=29 " in line)])
                    report = analyze_sources(sources, years=years)
                    result, manifest = campaign_evidence(years=years)
                    validate_campaign(report, result, manifest)
                    policy = report["policies"]["reference"]
                    self.assertTrue(policy["campaign_verified"])
                    self.assertFalse(policy["complete"])
                    self.assertFalse(policy["data_complete"])
                    self.assertIsNone(policy["pooled_auc"])
                    self.assertEqual(policy["folds"], [])
                    self.assertIn("sample=29", " ".join(policy["errors"]))

    def test_years_validation_rejects_short_non_integer_and_wrong_seed_set(self):
        for invalid in (2, 1, 0, -1, 3.5, "8", True):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "N >= 3"):
                    analyze_sources(three_games(), years=invalid)
        for seeds in ((42, 100, 7), (100, 42, 999), (42, 100), (42, 42, 999)):
            with self.subTest(seeds=seeds):
                with self.assertRaisesRegex(ValueError, "42 100 999"):
                    analyze_sources(three_games(), seeds=seeds)

    def test_cli_explicit_8_and_10_years_and_default_3(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            for filename, lines in three_games():
                (folder / filename).write_text("".join(lines), encoding="utf-8")
            result_path, manifest_path = folder / "campaign.json", folder / "manifest.json"
            evidence_args = ["--result-json", str(result_path),
                             "--manifest", str(manifest_path),
                             "--format", "json"]
            for years in (3, 8, 10):
                with self.subTest(years=years):
                    result, manifest = campaign_evidence(years=years)
                    result_path.write_text(json.dumps(result), encoding="utf-8")
                    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                    opts = [] if years == 3 else ["--years", str(years)]
                    with redirect_stdout(io.StringIO()) as output:
                        code = main([str(folder), *evidence_args,
                                     *opts, "--require-complete"])
                    self.assertEqual(code, 0)
                    report = json.loads(output.getvalue())
                    self.assertEqual(report["protocol"]["years"], years)
                    self.assertTrue(report["policies"]["reference"]["complete"])
            # The caller must supply a matching N; implicit default=3 is not 8.
            result, manifest = campaign_evidence(years=8)
            result_path.write_text(json.dumps(result), encoding="utf-8")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(folder), *evidence_args,
                                       "--require-complete"]), 1)
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main([str(folder), "--years", "2"])
            self.assertEqual(error.exception.code, 2)
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main([str(folder), "--years", "10", "--seeds", "42", "100", "7"])
            self.assertEqual(error.exception.code, 2)

    def test_scope_proof_does_not_need_years_or_game_seed_in_runtime_summary(self):
        report = analyze_sources(three_games())
        policy = report["policies"]["reference"]
        self.assertTrue(policy["complete"])
        self.assertNotIn("years", policy["games"][0]["summary"])
        self.assertNotIn("seed", policy["games"][0]["summary"])
        self.assertFalse(policy["campaign_verified"])
        result, manifest = campaign_evidence()
        validate_campaign(report, result, manifest)
        self.assertTrue(policy["complete"])
        self.assertTrue(policy["campaign_verified"])

    def test_summary_sample_seed_must_match_rlw04b_if_emitted(self):
        sources = three_games()
        lines = [line.replace("cap=5000", "cap=5000 sample_seed=1") for line in sources[0][1]]
        sources[0] = (sources[0][0], lines)
        self.assertFalse(analyze_sources(sources)["policies"]["reference"]["complete"])


if __name__ == "__main__":
    unittest.main()
