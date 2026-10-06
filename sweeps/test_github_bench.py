"""Offline orchestration contracts: unittest/stdlib only, no game or network.

Archive fixtures are synthetic, not copies of AAAHogEx. Only the expected
SHA-256 constant is patched: hashing, archive validation and copying stay real.
"""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

from sweeps import github_bench as bench


VARIANT = "OpexAI[c80_worker_rail=1]"
REFERENCE = "OpexAI[c80_worker_rail=0]"


def environment(**overrides):
    """Never depend on the developer's or CI runner's environment."""
    return {"GITHUB_RUN_ID": "123456", "GITHUB_RUN_ATTEMPT": "2", **overrides}


class OfflineTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.urlopen = self.enterContext(mock.patch.object(
            bench, "urlopen", side_effect=AssertionError("Network forbidden")))
        self.run = self.enterContext(mock.patch.object(
            bench.subprocess, "run", side_effect=AssertionError("Process forbidden")))

    def tearDown(self):
        self.urlopen.assert_not_called()
        self.run.assert_not_called()
        super().tearDown()

    def assert_option(self, command, option, expected):
        self.assertEqual(command.count(option), 1, command)
        self.assertEqual(command[command.index(option) + 1], str(expected))


class MakePlanTests(OfflineTestCase):
    def test_default_smoke_plan(self):
        self.assertEqual(bench.make_plan(environment()), {
            "mode": "solo", "profile": "smoke", "reference": "OpexAI",
            "variant": "", "years": 1, "seeds": [42], "minimum": 50000.0,
            "guard": 5.0, "telemetry": False, "campaign": "gha-123456-2",
            "output": "results/gha-123456-2/bench.json", "expected_games": 1,
        })

    def test_smoke_and_diagnostic_profiles_in_each_mode(self):
        for profile, years, seeds in (
            ("smoke", 1, [42]),
            ("diagnostic", 6, [42, 100, 999, 1234, 5678]),
        ):
            for mode in ("solo", "duel", "paired"):
                with self.subTest(profile=profile, mode=mode):
                    plan = bench.make_plan(environment(
                        BENCH_MODE=mode, BENCH_PROFILE=profile,
                        BENCH_VARIANT=VARIANT if mode == "paired" else ""))
                    self.assertEqual(plan["years"], years)
                    self.assertEqual(plan["seeds"], seeds)
                    self.assertEqual(len(set(plan["seeds"])), len(seeds))
                    self.assertEqual(plan["expected_games"],
                                     len(seeds) * (2 if mode == "paired" else 1))

    def test_adoption_defers_canonical_seeds_to_harness(self):
        plan = bench.make_plan(environment(
            BENCH_MODE="paired", BENCH_PROFILE="adoption", BENCH_VARIANT=VARIANT))
        self.assertEqual(plan["years"], 10)
        self.assertIsNone(plan["seeds"])
        self.assertEqual(plan["expected_games"], 40)

    def test_custom_accepts_mixed_separators_and_uint32_endpoints(self):
        plan = bench.make_plan(environment(
            BENCH_MODE="paired", BENCH_VARIANT=VARIANT, BENCH_PROFILE="custom",
            BENCH_YEARS=" 10 ", BENCH_SEEDS="0, 42\t100\n4294967295"))
        self.assertEqual(plan["years"], 10)
        self.assertEqual(plan["seeds"], [0, 42, 100, 2**32 - 1])
        self.assertEqual(plan["expected_games"], 8)

    def test_custom_count_and_year_boundaries(self):
        for years in (1, 10):
            for count in (1, 20):
                with self.subTest(years=years, count=count):
                    plan = bench.make_plan(environment(
                        BENCH_PROFILE="custom", BENCH_YEARS=str(years),
                        BENCH_SEEDS=",".join(map(str, range(count)))))
                    self.assertEqual(plan["years"], years)
                    self.assertEqual(plan["seeds"], list(range(count)))
                    self.assertEqual(plan["expected_games"], count)

    def test_custom_rejects_invalid_years_and_seeds(self):
        for field, values in (
            ("BENCH_YEARS", ("", "0", "-1", "11", "1.5", "nan", "1;echo x")),
            ("BENCH_SEEDS", ("", " ", ",,,", "42 42", "0 00", "-1",
                             str(2**32), "1.5", "nan", "42;echo x",
                             " ".join(map(str, range(21))))),
        ):
            for value in values:
                with self.subTest(field=field, value=value):
                    env = environment(BENCH_PROFILE="custom", BENCH_YEARS="1",
                                      BENCH_SEEDS="42")
                    env[field] = value
                    with self.assertRaises(ValueError):
                        bench.make_plan(env)

    def test_incompatible_fields_are_rejected(self):
        cases = [
            {"BENCH_MODE": "paired"},
            {"BENCH_MODE": "paired", "BENCH_VARIANT": "OpexAI"},
            {"BENCH_MODE": "paired", "BENCH_REFERENCE": VARIANT,
             "BENCH_VARIANT": VARIANT},
            {"BENCH_MODE": "solo", "BENCH_VARIANT": VARIANT},
            {"BENCH_MODE": "duel", "BENCH_VARIANT": VARIANT},
            {"BENCH_PROFILE": "adoption", "BENCH_MODE": "solo"},
            {"BENCH_PROFILE": "adoption", "BENCH_MODE": "duel"},
        ]
        for profile in ("smoke", "diagnostic", "adoption"):
            for field, value in (("BENCH_YEARS", "1"), ("BENCH_SEEDS", "42")):
                cases.append({"BENCH_PROFILE": profile, "BENCH_MODE": "paired",
                              "BENCH_VARIANT": VARIANT, field: value})
        for overrides in cases:
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                bench.make_plan(environment(**overrides))

    def test_unknown_modes_and_profiles_are_rejected(self):
        for field in ("BENCH_MODE", "BENCH_PROFILE"):
            for value in ("", "unknown", "SOLO", "smoke;echo x"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    bench.make_plan(environment(**{field: value}))

    def test_arms_accept_integer_settings_and_trim_outer_whitespace(self):
        arm = "OpexAI[_flag=-1,setting2=0,another=123]"
        plan = bench.make_plan(environment(
            BENCH_MODE="paired", BENCH_REFERENCE="  OpexAI  ",
            BENCH_VARIANT=f" {arm} "))
        self.assertEqual(plan["reference"], "OpexAI")
        self.assertEqual(plan["variant"], arm)
        self.assertEqual(bench.make_plan(environment(BENCH_REFERENCE=" "))["reference"],
                         "OpexAI")

    def test_malformed_arms_and_shell_injections_are_rejected(self):
        values = (
            "AAAHogEx", "OpexAI[]", "OpexAI[x=1.5]", "OpexAI[x=true]",
            "OpexAI[1x=1]", "OpexAI[x=1,]", "OpexAI[x =1]",
            "OpexAI;echo injected", "OpexAI && echo injected",
            "OpexAI|echo injected", "$(echo injected)", "`echo injected`",
            'OpexAI[x=1]" --out elsewhere', "OpexAI\n--out elsewhere",
            "OpexAI[x=1]\x00", "OpexAI[x=$(echo injected)]",
        )
        for field in ("BENCH_REFERENCE", "BENCH_VARIANT"):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    env = environment(BENCH_MODE="paired", BENCH_VARIANT=VARIANT)
                    env[field] = value
                    bench.make_plan(env)

    def test_run_identifiers_are_required_and_reject_injection(self):
        for field in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
            env = environment()
            del env[field]
            with self.subTest(field=field, missing=True), self.assertRaises(ValueError):
                bench.make_plan(env)
            for value in ("", "-1", "1.0", " 1", "1\n", "../42", "1;echo x", "$(id)"):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    bench.make_plan(environment(**{field: value}))

    def test_effect_size_and_guard_reject_nonfinite_and_invalid_values(self):
        for field, values in (
            ("BENCH_MIN_DELTA", ("nan", "NaN", "inf", "-inf", "1e309", "-1", "", "x")),
            ("BENCH_VALUE_GUARD", ("nan", "NaN", "inf", "-inf", "1e309", "-0.1",
                                   "100.01", "", "5;echo x")),
        ):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    bench.make_plan(environment(**{field: value}))

    def test_effect_size_and_guard_accept_boundaries(self):
        for minimum in ("0", "123.5", "1e6"):
            for guard in ("0", "5.5", "100"):
                with self.subTest(minimum=minimum, guard=guard):
                    plan = bench.make_plan(environment(
                        BENCH_MIN_DELTA=minimum, BENCH_VALUE_GUARD=guard))
                    self.assertEqual(plan["minimum"], float(minimum))
                    self.assertEqual(plan["guard"], float(guard))

    def test_telemetry_is_a_strict_boolean_reserved_for_duels(self):
        for mode in ("solo", "duel", "paired"):
            for value in ("true", "false", "True", "1", "", "false;echo x"):
                with self.subTest(mode=mode, value=value):
                    env = environment(BENCH_MODE=mode, BENCH_LINE_TELEMETRY=value,
                                      BENCH_VARIANT=VARIANT if mode == "paired" else "")
                    if value not in ("true", "false") or (mode == "solo" and value == "true"):
                        with self.assertRaises(ValueError):
                            bench.make_plan(env)
                    else:
                        self.assertIs(bench.make_plan(env)["telemetry"], value == "true")


class CommandForTests(OfflineTestCase):
    def test_solo_docker_command_and_resource_contract(self):
        root = Path("workspace with spaces")
        plan = bench.make_plan(environment(BENCH_REFERENCE=REFERENCE))
        self.assertEqual(bench.command_for(plan, root=root), [
            "docker", "run", "--rm", "--cpus=3", "--memory=2g", "--memory-swap=2g",
            "-v", "openttd-lab-home:/home/lab", "-v", f"{root}:/work", "-w", "/work",
            "openttd-lab:github", "python3", "sweeps/smoke_test.py",
            "--arm", REFERENCE, "--years", "1", "--max-workers", "2",
            "--out", "results/gha-123456-2/bench.json", "--seeds", "42",
        ])

    def test_default_reference_is_omitted_from_duel(self):
        plan = bench.make_plan(environment(BENCH_MODE="duel"))
        self.assertEqual(bench.command_for(plan), [
            sys.executable, "sweeps/run_c66_reference.py", "--image", "openttd-lab:github",
            "--campaign", "gha-123456-2", "--cpus", "3", "--memory", "2g",
            "--engine-timeout", "1800", "--decision-rule", "signs20",
            "--years", "1", "--max-workers", "2", "--out",
            "results/gha-123456-2/bench.json", "--seeds", "42",
        ])

    def test_explicit_duel_reference_and_telemetry(self):
        command = bench.command_for(bench.make_plan(environment(
            BENCH_MODE="duel", BENCH_REFERENCE=REFERENCE, BENCH_LINE_TELEMETRY="true")))
        self.assert_option(command, "--reference", REFERENCE)
        self.assertEqual(command.count("--line-telemetry"), 1)
        self.assertNotIn("--variant", command)
        self.assertNotIn("--min-useful-primary-delta", command)

    def test_paired_arguments_preserve_preregistered_effect_sizes(self):
        for reference in ("OpexAI", REFERENCE):
            with self.subTest(reference=reference):
                command = bench.command_for(bench.make_plan(environment(
                    BENCH_MODE="paired", BENCH_PROFILE="diagnostic",
                    BENCH_REFERENCE=reference, BENCH_VARIANT=VARIANT,
                    BENCH_MIN_DELTA="12345.5", BENCH_VALUE_GUARD="2.5",
                    BENCH_LINE_TELEMETRY="true")))
                for option, value in (
                    ("--variant", VARIANT), ("--variant-policy-id", "variant"),
                    ("--primary-metric", "profit_year"),
                    ("--min-useful-primary-delta", "12345.5"),
                    ("--value-guard-max-loss-pct", "2.5"),
                    ("--decision-rule", "signs20"), ("--years", "6"),
                    ("--cpus", "3"), ("--memory", "2g"), ("--max-workers", "2"),
                ):
                    self.assert_option(command, option, value)
                if reference == "OpexAI":
                    self.assertNotIn("--reference", command)
                else:
                    self.assert_option(command, "--reference", reference)
                start = command.index("--seeds") + 1
                self.assertEqual(command[start:start + 5], ["42", "100", "999", "1234", "5678"])
                self.assertIn("--line-telemetry", command)

    def test_adoption_omits_seeds_and_keeps_two_workers(self):
        command = bench.command_for(bench.make_plan(environment(
            BENCH_MODE="paired", BENCH_PROFILE="adoption", BENCH_VARIANT=VARIANT)))
        self.assertNotIn("--seeds", command)
        self.assertNotIn("--line-telemetry", command)
        self.assert_option(command, "--years", 10)
        self.assert_option(command, "--max-workers", 2)
        self.assert_option(command, "--min-useful-primary-delta", "50000.0")
        self.assert_option(command, "--value-guard-max-loss-pct", "5.0")

    def test_custom_seed_order_is_preserved(self):
        command = bench.command_for(bench.make_plan(environment(
            BENCH_PROFILE="custom", BENCH_YEARS="2", BENCH_SEEDS="4294967295,0,42")))
        self.assertEqual(command[command.index("--seeds") + 1:], ["4294967295", "0", "42"])

    def test_default_variant_is_rejected_at_command_stage(self):
        # Current validation is split: make_plan accepts this, command_for refuses it.
        plan = bench.make_plan(environment(
            BENCH_MODE="paired", BENCH_REFERENCE=REFERENCE, BENCH_VARIANT="OpexAI"))
        with self.assertRaisesRegex(ValueError, "variante doit expliciter"):
            bench.command_for(plan)


class InstallOpponentTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.destination = self.root / "ai" / "AAAHogEx-115"

    @staticmethod
    def fixture_files():
        return {
            "AAAHogEx-115/info.nut": (
                b"\xef\xbb\xbfclass FixtureInfo { function GetVersion () { return 115; } }\n"),
            "AAAHogEx-115/main.nut": b"// Synthetic test source, not upstream code.\n",
            "AAAHogEx-115/license.txt": b"Synthetic fixture license notice.\n",
            "AAAHogEx-115/nested/helper.nut": b"// Preserve nested sources.\n",
        }

    @staticmethod
    def archive(files, extra_members=()):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
            directory = tarfile.TarInfo("AAAHogEx-115")
            directory.type = tarfile.DIRTYPE
            archive.addfile(directory)
            for name, contents in files.items():
                member = tarfile.TarInfo(name)
                member.size = len(contents)
                archive.addfile(member, io.BytesIO(contents))
            for member in extra_members:
                archive.addfile(member)
        return buffer.getvalue()

    def trusted_install(self, data):
        with mock.patch.object(bench, "AAAHOGEX_SHA256", hashlib.sha256(data).hexdigest()):
            bench.install_opponent(data, self.destination)

    def assert_rejected_archive(self, data, message):
        with self.assertRaisesRegex(ValueError, message):
            self.trusted_install(data)
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.destination.parent.iterdir()), [])

    def test_verified_archive_preserves_license_info_and_all_sources(self):
        files = self.fixture_files()
        self.trusted_install(self.archive(files))
        actual = {path.relative_to(self.destination).as_posix(): path.read_bytes()
                  for path in self.destination.rglob("*") if path.is_file()}
        expected = {name.split("/", 1)[1]: contents for name, contents in files.items()}
        self.assertEqual(actual, expected)
        self.assertEqual(list(self.destination.parent.iterdir()), [self.destination])

    def test_bad_sha_is_rejected_before_extraction_or_directory_creation(self):
        data = self.archive(self.fixture_files())
        with mock.patch.object(bench, "AAAHOGEX_SHA256", "0" * 64):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                bench.install_opponent(data, self.destination)
        self.assertFalse(self.destination.parent.exists())

    def test_tampered_payload_is_rejected(self):
        data = self.archive(self.fixture_files())
        with mock.patch.object(bench, "AAAHOGEX_SHA256", hashlib.sha256(data).hexdigest()):
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                bench.install_opponent(data + b"tampered", self.destination)
        self.assertFalse(self.destination.parent.exists())

    def test_path_traversal_absolute_paths_and_backslashes_are_rejected(self):
        for name in ("../escaped.nut", "AAAHogEx-115/../../escaped.nut",
                     "/escaped.nut", "AAAHogEx-115\\escaped.nut",
                     "C:\\escaped.nut"):
            with self.subTest(name=name):
                files = self.fixture_files()
                files[name] = b"must not be extracted"
                self.assert_rejected_archive(self.archive(files), "Entree d'archive refusee")
                self.assertFalse((self.root / "escaped.nut").exists())
                self.assertFalse((self.destination.parent / "escaped.nut").exists())

    def test_symlinks_hardlinks_and_special_files_are_rejected(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE):
            with self.subTest(kind=kind):
                member = tarfile.TarInfo("AAAHogEx-115/link")
                member.type = kind
                member.linkname = "main.nut"
                self.assert_rejected_archive(
                    self.archive(self.fixture_files(), [member]), "Entree d'archive refusee")

    def test_wrong_or_missing_version_is_rejected(self):
        for info in (b"function GetVersion() { return 114; }",
                     b"function GetVersion() { return 1150; }",
                     b"// no version function here"):
            with self.subTest(info=info):
                files = self.fixture_files()
                files["AAAHogEx-115/info.nut"] = info
                self.assert_rejected_archive(self.archive(files), "Version AAAHogEx")

    def test_missing_or_ambiguous_info_is_rejected(self):
        for ambiguous in (False, True):
            with self.subTest(ambiguous=ambiguous):
                files = self.fixture_files()
                if ambiguous:
                    files["another/info.nut"] = files["AAAHogEx-115/info.nut"]
                else:
                    del files["AAAHogEx-115/info.nut"]
                self.assert_rejected_archive(self.archive(files), "Archive AAAHogEx ambigue")

    def test_missing_source_or_license_is_rejected(self):
        for name in ("main.nut", "license.txt"):
            with self.subTest(name=name):
                files = self.fixture_files()
                del files[f"AAAHogEx-115/{name}"]
                self.assert_rejected_archive(self.archive(files), "Source ou licence")

    def test_existing_directory_is_never_overwritten(self):
        self.destination.mkdir(parents=True)
        sentinel = self.destination / "main.nut"
        sentinel.write_bytes(b"existing source")
        with self.assertRaises(FileExistsError):
            self.trusted_install(self.archive(self.fixture_files()))
        self.assertEqual(sentinel.read_bytes(), b"existing source")
        self.assertEqual(list(self.destination.iterdir()), [sentinel])
        self.assertEqual(list(self.destination.parent.iterdir()), [self.destination])

    def test_existing_file_is_never_overwritten(self):
        self.destination.parent.mkdir(parents=True)
        self.destination.write_bytes(b"existing file")
        with self.assertRaises(FileExistsError):
            self.trusted_install(self.archive(self.fixture_files()))
        self.assertEqual(self.destination.read_bytes(), b"existing file")


class SummaryTextTests(OfflineTestCase):
    def test_missing_report_never_claims_validation(self):
        for mode in ("solo", "duel", "paired"):
            with self.subTest(mode=mode):
                plan = bench.make_plan(environment(
                    BENCH_MODE=mode, BENCH_VARIANT=VARIANT if mode == "paired" else ""))
                text = bench.summary_text(plan, None)
                self.assertIn("`gha-123456-2`", text)
                self.assertIn(f"`{mode}` / `smoke`", text)
                self.assertIn(f"Horizon : 1 ans ; parties attendues : {plan['expected_games']}", text)
                self.assertIn("Rapport final absent : campagne non validée", text)
                self.assertNotIn("Verdict économique", text)
                self.assertIn("pas une adoption économique", text)

    def test_solo_status_and_unknown_fallback(self):
        plan = bench.make_plan(environment())
        for report, status in (({}, "UNKNOWN"), ({"smoke_test_status": "PASS"}, "PASS"),
                               ({"smoke_test_status": "FAIL"}, "FAIL")):
            with self.subTest(report=report):
                text = bench.summary_text(plan, report)
                self.assertIn(f"Smoke : `{status}`", text)
                self.assertNotIn("Rapport final absent", text)
                self.assertNotIn("Verdict économique", text)

    def test_duel_counts_games_and_health_failures_without_inventing_verdict(self):
        plan = bench.make_plan(environment(BENCH_MODE="duel"))
        for comparison in (None, {}):
            with self.subTest(comparison=comparison):
                text = bench.summary_text(plan, {
                    "games": [{}, {}, {}], "failed_runs": [{}],
                    "policy_comparison": comparison,
                })
                self.assertIn("Parties rapportées : 3", text)
                self.assertIn("Échecs de santé : 1", text)
                self.assertNotIn("Verdict économique", text)
                self.assertNotIn("Paires complètes", text)

    def test_empty_duel_report_is_distinct_from_absent_report(self):
        plan = bench.make_plan(environment(BENCH_MODE="duel"))
        text = bench.summary_text(plan, {})
        self.assertIn("Parties rapportées : 0", text)
        self.assertIn("Échecs de santé : 0", text)
        self.assertNotIn("Rapport final absent", text)
        self.assertNotIn("Verdict économique", text)

    def test_paired_summary_preserves_harness_verdict_and_coverage(self):
        plan = bench.make_plan(environment(
            BENCH_MODE="paired", BENCH_PROFILE="adoption", BENCH_VARIANT=VARIANT))
        for verdict in ("pass", "fail_primary", "fail_guard", "incomplete"):
            with self.subTest(verdict=verdict):
                text = bench.summary_text(plan, {
                    "games": [{}] * 38, "failed_runs": [{}, {}],
                    "policy_comparison": {
                        "complete_pairs": 18, "planned_pairs": 20, "verdict": verdict,
                    },
                })
                self.assertIn("Horizon : 10 ans ; parties attendues : 40", text)
                self.assertIn("Parties rapportées : 38", text)
                self.assertIn("Échecs de santé : 2", text)
                self.assertIn("Paires complètes : 18/20", text)
                self.assertIn(f"Verdict économique du harnais : **`{verdict}`**", text)
                self.assertIn("Un job vert indique une exécution valide, pas une adoption économique.", text)
                self.assertIn("JSON, JSONL, logs", text)
                self.assertIn("manifeste et bundle", text)
                self.assertTrue(text.endswith("\n"))


class ProfitRatioTests(OfflineTestCase):
    def plan(self, **overrides):
        return bench.make_plan(environment(
            BENCH_MODE="duel", BENCH_PROFILE="custom", BENCH_YEARS="3",
            BENCH_SEEDS="42 100", **overrides))

    @staticmethod
    def record(seed, arm, profit, policy="reference", **overrides):
        record = dict(seed=seed, arm=arm, profit_year=profit, duel_policy_id=policy,
                      repeat=0, run_ok=True, game_ok=True, profit_year_coverage="complete")
        record.update(overrides)
        return record

    def report(self):
        return {"policy_id": "reference", "failed_runs": [], "summary": [
            self.record(42, "OpexAI", 80), self.record(42, "AAAHogEx", 100),
            self.record(100, "OpexAI", 900), self.record(100, "AAAHogEx", 1000),
        ]}

    def test_three_year_command_and_ratio_of_sums_not_mean_percent(self):
        plan = self.plan()
        self.assert_option(bench.command_for(plan), "--years", 3)
        result = bench.profit_ratios(plan, self.report())[0]
        self.assertTrue(result["complete"])
        self.assertEqual(result["valid_ratios"], 2)
        self.assertEqual([r["opex_over_aaa_pct"] for r in result["per_seed"]], [80, 90])
        self.assertAlmostEqual(result["opex_over_aaa_pct"], 100 * 980 / 1100)
        self.assertEqual(result["mean_opex_profit_year"], 490)
        self.assertEqual(result["mean_aaa_profit_year"], 550)

    def test_missing_duplicate_unhealthy_partial_and_invalid_profits_suppress_global(self):
        for field, value in (("run_ok", False), ("game_ok", False),
                             ("profit_year_coverage", "partial"),
                             ("profit_year_coverage", None), ("profit_year", None),
                             ("profit_year", float("nan")), ("profit_year", float("inf")),
                             ("profit_year", True)):
            with self.subTest(field=field, value=value):
                report = self.report()
                report["summary"][0][field] = value
                result = bench.profit_ratios(self.plan(), report)[0]
                self.assertFalse(result["complete"])
                self.assertEqual(result["valid_ratios"], 1)
                self.assertIsNone(result["opex_over_aaa_pct"])
                self.assertIsNotNone(result["per_seed"][0]["reason"])
        for duplicate in (True, False):
            report = self.report()
            if duplicate:
                report["summary"].append(report["summary"][0].copy())
            else:
                report["summary"].pop(0)
            result = bench.profit_ratios(self.plan(), report)[0]
            self.assertIsNone(result["opex_over_aaa_pct"])
            self.assertEqual(result["per_seed"][0]["reason"], "compagnie absente ou doublon")

    def test_nonpositive_aaa_is_not_a_percentage_but_opex_losses_are_preserved(self):
        for profit in (0, -100):
            report = self.report()
            report["summary"][1]["profit_year"] = profit
            result = bench.profit_ratios(self.plan(), report)[0]
            self.assertIsNone(result["opex_over_aaa_pct"])
            self.assertEqual(result["per_seed"][0]["reason"], "profit AAAHogEx nul ou négatif")
        for profit in (0, -50):
            report = self.report()
            report["summary"][0]["profit_year"] = profit
            result = bench.profit_ratios(self.plan(), report)[0]
            self.assertTrue(result["complete"])
            self.assertEqual(result["per_seed"][0]["opex_over_aaa_pct"], profit)

    def test_failed_campaign_has_no_global_even_with_numeric_rows(self):
        report = self.report()
        report["failed_runs"] = [{"reason": "unexpected_game"}]
        self.assertIsNone(bench.profit_ratios(self.plan(), report)[0]["opex_over_aaa_pct"])

    def test_policies_are_never_mixed(self):
        plan = self.plan()
        plan["mode"], plan["expected_games"] = "paired", 4
        report = self.report()
        report["summary"] += [self.record(seed, arm, profit, policy="variant")
                              for seed in (42, 100)
                              for arm, profit in (("OpexAI", 200), ("AAAHogEx", 100))]
        results = bench.profit_ratios(plan, report)
        self.assertEqual([r["policy"] for r in results], ["reference", "variant"])
        self.assertAlmostEqual(results[0]["opex_over_aaa_pct"], 100 * 980 / 1100)
        self.assertEqual(results[1]["opex_over_aaa_pct"], 200)

    def test_summary_explains_period_ratio_and_missing_values(self):
        text = bench.summary_text(self.plan(), self.report())
        self.assertIn("Ratio global : 89.1 %", text)
        self.assertIn("pas le cumul du banc", text)
        self.assertIn("| 42 | 80.0 | 100.0 | 80.0 |", text)
        report = self.report()
        report["summary"] = []
        text = bench.summary_text(self.plan(), report)
        self.assertIn("Ratio global : n/d", text)
        self.assertIn("Ratios exploitables : 0/2", text)


if __name__ == "__main__":
    unittest.main()