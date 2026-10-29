"""Reader fixtures, fail-closed comparability, OFF projection and syntax checks."""
import gzip
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest

from diag_air_site_probe import METHODS, analyse, parse_text, read_log, probe_health
from test_air_site_funnel import body
from test_v261_forum_behaviours import uncomment

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "sweeps/fixtures"
AI = ROOT / "ai/OpexAI"


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.texts = {method: (FIXTURES / "air_site_probe_v3" / f"seed42_{method}.log").read_text() for method in METHODS}

    def streams(self, texts=None, seed=42):
        return [parse_text(text, f"seed{seed}_{method}.log", seed) for method, text in (texts or self.texts).items()]

    def result(self, texts=None):
        return analyse(self.streams(texts))

    def test_metrics_and_pairing_include_misses(self):
        result = self.result()
        self.assertTrue(result["comparisons"][0]["valid"])
        stats = result["valid"]["by_method"]
        self.assertEqual(stats["spiral"]["ratio_median"], .5)
        self.assertEqual(stats["initial"]["error_263"], 1)
        self.assertEqual(stats["initial"]["ratio_median"], 1.5)
        self.assertEqual(stats["initial"]["feasible_ratio_median"], 1.5)
        self.assertEqual(stats["bands"]["miss_with_oracle"], 1)
        self.assertEqual(stats["bands"]["ratio_median"], 0)
        self.assertEqual(stats["oracle"]["ratio_equal_one"], 1)
        pair = next(r for r in result["valid"]["paired"] if r["method"] == "hybrid")
        self.assertEqual(pair["ops_delta"], -20)
        self.assertEqual(pair["score_delta"], 0)
        self.assertNotEqual(pair["source"], pair["reference_source"])
        self.assertTrue(all(p["end"]["stable"] == 0 for p in result["passes"]))

    def test_plain_and_gzip(self):
        with tempfile.TemporaryDirectory() as directory:
            plain = Path(directory) / "seed42_spiral.log"
            zipped = plain.with_suffix(".log.gz")
            plain.write_text(self.texts["spiral"])
            with gzip.open(zipped, "wt") as stream:
                stream.write(self.texts["spiral"])
            a, b = read_log(plain), read_log(zipped)
            self.assertEqual(len(a["rows"]), len(b["rows"]))
            self.assertEqual(a["rows"][0]["seed"], 42)

    def test_invalid_passes_never_enter_primary_table(self):
        original = self.texts["spiral"]
        cases = [original.replace("fingerprint=2:400", "fingerprint=2:401"),
                 original.replace("date=719529", "date=719530", 1),
                 original.replace("vehicles=0", "vehicles=1"),
                 original.replace("stations=0", "stations=1"),
                 original.replace("rows=1", "rows=8"),
                 original.replace("cases=1", "cases=0"),
                 original.replace("loan=100000", "loan=90000", 1),
                 original.replace("town=0", "town=1"),
                 original.replace("truncated=0", "truncated=1"),
                 original[:original.index("AIR_PROBE_PASS v=4 edge=end")],
                 original + original.splitlines()[2] + "\n"]
        for text in cases:
            with self.subTest(text=text[-120:]):
                result = self.result({**self.texts, "spiral": text})
                self.assertFalse(result["comparisons"][0]["valid"])
                self.assertEqual(result["valid"]["by_method"]["spiral"]["n"], 0)

    def test_zero_oracle_is_unknown(self):
        result = self.result({**self.texts, "oracle": self.texts["oracle"].replace("score=20", "score=0")})
        self.assertTrue(result["comparisons"][0]["valid"])
        self.assertIsNone(result["valid"]["by_method"]["spiral"]["ratio_median"])
        self.assertEqual(result["valid"]["by_method"]["spiral"]["ratio_n"], 0)

    def test_missing_oracle_or_duplicate_game_invalidates(self):
        parsed = self.streams()
        self.assertFalse(analyse(parsed[:-1])["comparisons"][0]["valid"])
        self.assertFalse(analyse(parsed + [parsed[0]])["comparisons"][0]["valid"])

    def test_native_squirrel_null_and_malformed_score(self):
        texts = {k: v.replace("=null", "=(null : 0x00000000)") for k, v in self.texts.items()}
        self.assertTrue(self.result(texts)["comparisons"][0]["valid"])
        result = self.result({**texts, "spiral": texts["spiral"].replace("score=10", "score=garbage", 1)})
        self.assertFalse(result["comparisons"][0]["valid"])
        self.assertTrue(result["issues"])

    def test_old_protocol_rejected(self):
        old = (FIXTURES / "air_site_probe.log").read_text()
        self.assertTrue(parse_text(old, seed=42)["issues"])

    def test_truncated_pass_retains_explicit_flag(self):
        text = self.texts["oracle"].split("AIR_PROBE_PASS v=4 edge=end")[0]
        result = self.result({**self.texts, "oracle": text})
        self.assertEqual(next(p for p in result["passes"] if p["method"] == "oracle")["truncated"], 1)
        self.assertFalse(result["comparisons"][0]["valid"])

    def test_engine_health_does_not_override_invalid_pass(self):
        health = {f"42:{method}": {"companies": {"OpexAI": {"horizon_complete": True, "company_present": True,
                    "bankrupt": False, "script_errors": []}}} for method in METHODS}
        result = self.result({**self.texts, "spiral": self.texts["spiral"].replace("fingerprint=2:400", "fingerprint=2:401")})
        verdict = probe_health(health, result, [42], 1)
        self.assertTrue(verdict["engine_script_horizon_ok"])
        self.assertFalse(verdict["smoke_ok"])
        self.assertTrue(probe_health(health, self.result(), [42], 1)["smoke_ok"])
        self.assertFalse(probe_health(health, self.result(), [42], 6)["comparison_coverage_complete"])

    def test_seeds_never_cross_pair(self):
        texts = {**self.texts, "spiral": self.texts["spiral"].replace("ops=100", "ops=200")}
        result = analyse(self.streams() + self.streams(texts, 100))
        pairs = [r for r in result["valid"]["paired"] if r["method"] == "hybrid"]
        self.assertEqual([r["ops_delta"] for r in pairs], [-20, -120])

    def test_health_normalizes_method_to_company_without_mutating_source(self):
        from run_air_site_probe import company_records
        from game_health import inspect_checkpoints
        rows = [{"run": ["spiral", 42, 0], "date": "1970-01-01"},
                {"run": ["hybrid", 42, 0], "date": "1970-01-01"}]
        normalized = company_records(rows, 42, "spiral")
        report = inspect_checkpoints(normalized, expected_companies=("OpexAI",), expected_dates=["1970-01-01"])
        self.assertEqual(report["missing_companies"], [])
        self.assertEqual(report["missing_checkpoints"], {"OpexAI": []})
        self.assertEqual(rows[0]["run"][0], "spiral")


class ProbeContracts(unittest.TestCase):
    def test_off_hashes(self):
        expected = json.loads((FIXTURES / "air_site_probe_off_hashes.json").read_text())
        # V161: keep the original pin, plus the reviewed six-line prior removal.
        self.assertEqual(expected["globals_pre.nut"],
                         "3c203d53468b16eeb81abe1dd2894cc74ac2bdabcd01fd4647c135884b502f07")
        v161_digest = "0610c2699fd71875bb2720c196120cf11fa9ab312b52156747633a3b086698ea"
        for name, digest in expected.items():
            from air_site_ranked_legacy import off_source
            text = off_source(name, (AI / name).read_text())
            if name == "main.nut":
                gate = '  OpexLoadAirSiteProbeSetting();\n  if (AIR_SITE_PROBE > 0) {\n    require("air_site_probe.nut");\n    OpexAirSiteProbeRun(this);\n    return;\n  }\n'
                self.assertEqual(text.count(gate), 1)
                text = text.replace(gate, "")
            elif name == "settings.nut":
                fn = body(text, "function OpexLoadAirSiteProbeSetting(") + "\n\n"
                text = text.replace(fn, "")
            elif name == "globals_pre.nut":
                text = text.replace("AIR_SITE_PROBE <- 0; // Read once at Start; no probe code loaded when OFF.\n", "")
                self.assertNotIn("V161_PRIOR_OWN", text)
                self.assertNotIn("V161_PRIOR_NEIGHBOUR", text)
                digest = v161_digest
            elif name == "info.nut":
                text, n = re.subn(r'    AddSetting\(\{\n      name = "air_site_probe",.*?    \}\);\n', '', text, flags=re.S)
                self.assertEqual(n, 1)
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(), digest, name)

    def test_no_command_before_probe_and_no_game_loop_hook(self):
        main = (AI / "main.nut").read_text()
        start = body(main, "function OpexAI::Start(")
        self.assertLess(start.index("if (AIR_SITE_PROBE > 0)"), start.index("AICompany.SetName"))
        self.assertNotIn("OpexAirSiteProbeRun", (AI / "probes.nut").read_text())
        settings = (AI / "settings.nut").read_text()
        self.assertEqual(settings.count('GetSetting("air_site_probe")'), 1)
        info = (AI / "info.nut").read_text()
        block = re.search(r'name = "air_site_probe",.*?\}\);', info, re.S)[0]
        self.assertIn("min_value = 0, max_value = 10", block)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertIn(f"{level}_value = 0", block)

    def test_probe_testmode_caches_and_cost(self):
        code = (AI / "air_site_probe.nut").read_text()
        run = body(code, "function OpexAirSiteProbeRun(")
        self.assertLess(run.index("local test = AITestMode();"), run.index("OpexLoadSettings();"))
        self.assertNotIn("_mainLoop", run)
        measure = body(code, "function OpexAirProbeMethod(")
        self.assertLess(measure.index("OpexAirProbeClear(owner)"), measure.index("OpexOpsMeasureBegin()"))
        self.assertIn("OpexOpsMeasureEnd(mark)", measure)
        oracle = body(code, "function OpexAirProbeOracle(")
        self.assertNotIn("CheapOk", oracle)
        self.assertNotIn("probes.left", oracle)
        self.assertIn("OpexAirProbeBuild(anchor, airport, bestScore)", oracle)
        clear = body(code, "function OpexAirProbeClear(")
        for cache in ("DEAD", "LIST", "RAW", "PEN"):
            self.assertIn(f"AIR_PROBE_FUNNEL_{cache}.clear()", clear)
        self.assertIn("owner._po01cJob = null", clear)

    def test_delimiters_reserved_names_closures_and_api_symbols(self):
        api = {f"{c}.{member}" for kind, c, member in (line.split("\t") for line in (ROOT / "docs/noai_api_15.3.tsv").read_text().splitlines()) if kind in ("static", "const")}
        api.update(symbol.replace("AIBaseStation.", "AIStation.") for symbol in tuple(api) if symbol.startswith("AIBaseStation."))
        for path in list(AI.glob("air_site_probe*.nut")) + [AI / "air_site_ranked.nut"]:
            code = uncomment(path.read_text())
            self.assertNotRegex(code, r"\blocal\s+(clone|base|parent|static|delegate|vargc|vargv|resume|yield|constructor|instanceof)\b")
            self.assertNotRegex(code, r"function\s*\(")
            self.assertNotIn(".find(", code)
            for symbol in re.findall(r"\b(AI[A-Z][a-z]\w*\.\w+)", code):
                self.assertTrue(symbol in api, (path.name, symbol))
            stripped = re.sub(r'"(?:\\.|[^"\\])*"', '""', code)
            stack = []
            for char in stripped:
                if char in "({[":
                    stack.append(char)
                elif char in ")}]":
                    self.assertTrue(stack, path.name)
                    self.assertEqual(stack.pop(), dict(zip(")}]", "({["))[char], path.name)
            self.assertEqual(stack, [], path.name)


if __name__ == "__main__":
    unittest.main()
