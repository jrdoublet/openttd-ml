"""Contrats C75 bis : bypass K_pass cible sur une nouvelle ligne finançable."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def body(source, signature):
    start = source.index(signature)
    brace = source.index("{", start)
    depth = 0
    for idx in range(brace, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start : idx + 1]
    raise AssertionError(f"unterminated function: {signature}")


class C75KPassBypassContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = read("ai/OpexAI/info.nut")
        cls.settings = read("ai/OpexAI/settings.nut")
        cls.globals = read("ai/OpexAI/globals_pre.nut")
        cls.projects = read("ai/OpexAI/task_projects.nut")
        cls.probes = read("ai/OpexAI/probes.nut")
        cls.report = read("ai/OpexAI/task_report.nut")
        cls.bench = read("sweeps/bench_1v1_5y_20seeds.py")
        cls.build = body(cls.projects, "function OpexAI::_tryBuildProjects(")

    def test_setting_is_adopted_default_on(self):
        start = self.info.index('name = "c75_kpass_bypass"')
        setting = self.info[start:self.info.index("});", start)]
        self.assertIn("easy_value = 1", setting)
        self.assertIn("medium_value = 1", setting)
        self.assertIn("hard_value = 1", setting)
        self.assertIn("custom_value = 1", setting)
        self.assertIn("flags = AICONFIG_BOOLEAN", setting)
        self.assertIn("C75_KPASS_BYPASS <- false;", self.globals)
        self.assertIn("C75_KPASS_BYPASS_LEDGER_YEAR <- -1;", self.globals)
        self.assertEqual(
            self.settings.count('AIController.GetSetting("c75_kpass_bypass")'),
            1,
        )

    def test_financeable_new_line_can_bypass_kpass(self):
        gate = body(self.projects, "function OpexC75KPassBypassIsNewLine(")
        for mode in ("air", "rail", "road", "water"):
            self.assertIn(f'project.mode == "{mode}"', gate)
        self.assertIn("C75_KPASS_BYPASS && OpexC75KPassBypassIsNewLine(project)", self.build)
        self.assertIn("OpexC75KPassBypassIsNewLine(project)", self.build)
        self.assertIn("projCap <= availCap", self.build)
        self.assertIn("OpexC75BypassRecordEligible(", self.build)
        self.assertIn("if (!c75BypassConsumed)", self.build)
        self.assertIn("c75BypassThisProject = true;", self.build)
        self.assertIn("OpexC75BypassRecordConsumed(", self.build)

    def test_cash_insufficient_never_consumes_bypass(self):
        threshold = self.build[self.build.index("if (projCap >= c75KPass)"):]
        consume = threshold.index("c75BypassConsumed = true;")
        affordability = threshold.index("if (projCap <= availCap)")
        self.assertLess(affordability, consume)
        self.assertIn(
            'c75StopReason = (availCap >= 0 && projCap > availCap) ? "cash" : "k_pass";',
            threshold,
        )

    def test_fleet_is_never_a_new_line_bypass(self):
        gate = body(self.projects, "function OpexC75KPassBypassIsNewLine(")
        self.assertNotIn('"fleet"', gate)
        telemetry = body(self.probes, "function OpexC75BypassRecordConsumed(")
        self.assertIn('local isFleet = mode == "fleet" ? 1 : 0;', telemetry)
        self.assertIn('" fleet=" + isFleet', telemetry)

    def test_at_most_one_bypass_is_consumed_per_pass(self):
        self.assertIn("local c75BypassConsumed = false;", self.build)
        self.assertEqual(self.build.count("c75BypassConsumed = true;"), 1)
        self.assertIn("!c75BypassConsumed", self.build)
        self.assertLess(
            self.build.index("!c75BypassConsumed"),
            self.build.index("c75BypassConsumed = true;"),
        )

    def test_default_off_keeps_historical_kpass_stop_path(self):
        threshold = self.build[self.build.index("if (projCap >= c75KPass)"):]
        self.assertIn("if (C75_KPASS_BYPASS &&", threshold)
        self.assertIn('c75StopReason = (availCap >= 0 && projCap > availCap) ? "cash" : "k_pass";', threshold)
        self.assertIn("if (!c75BypassThisProject)", threshold)
        self.assertIn("break;", threshold)
        self.assertIn("if (availCap < 0) availCap = OpexAvailableCapital();", threshold)

    def test_telemetry_exposes_required_fields_and_year_summary(self):
        eligible = body(self.probes, "function OpexC75BypassRecordEligible(")
        for token in (
            "mode=",
            "kind=",
            "capital=",
            "cash=",
            "available=",
            "k_pass=",
            "already_consumed=",
            "fleet=",
        ):
            self.assertIn(token, eligible)
        consumed = body(self.probes, "function OpexC75BypassRecordConsumed(")
        for token in (
            "mode=",
            "kind=",
            "capital=",
            "cash=",
            "available=",
            "k_pass=",
            "fleet=",
        ):
            self.assertIn(token, consumed)
        yearly = body(self.probes, "function OpexC75BypassFlushYear(")
        for token in (
            "eligible=",
            "consumed=",
            "fleet_consumed=",
            "stop_k_pass=",
            "stop_cash=",
            "stop_rail_search=",
            "stop_list_end=",
        ):
            self.assertIn(token, yearly)

    def test_yearly_telemetry_does_not_require_portfolio_probe(self):
        self.assertIn("if (C75_KPASS_BYPASS) {", self.report)
        self.assertIn("OpexC75BypassFlushYear(c75BypassYear);", self.report)
        self.assertIn("C75_KPASS_BYPASS_LEDGER_YEAR == c75BypassYear", self.report)
        historical = body(self.probes, "function OpexC75FlushYear(")
        self.assertNotIn("OpexC75BypassFlushYear", historical)
        self.assertEqual(self.report.count("OpexC75BypassFlushYear(c75BypassYear);"), 1)

    def test_year_boundary_flushes_before_first_pass_of_new_year(self):
        ensure = body(self.probes, "function OpexC75BypassEnsureYear(")
        self.assertIn("C75_KPASS_BYPASS_LEDGER_YEAR != year", ensure)
        self.assertIn("OpexC75BypassFlushYear(C75_KPASS_BYPASS_LEDGER_YEAR);", ensure)
        self.assertIn("C75_KPASS_BYPASS_LEDGER_YEAR = year;", ensure)
        self.assertLess(
            self.build.index("OpexC75BypassEnsureYear(year);"),
            self.build.index("if (C75_TRACK_PASSES)"),
        )

    def test_durable_signs_cover_consumption_year_and_stops(self):
        consumed = body(self.probes, "function OpexC75BypassRecordConsumed(")
        self.assertIn('"C7C|"', consumed)
        self.assertIn("OpexC75BypassModeCode(project)", consumed)
        self.assertIn("OpexC75BypassKindCode(project)", consumed)
        self.assertIn("(financeCapital / 1000)", consumed)
        self.assertIn("(availableCapital / 1000)", consumed)
        self.assertIn("(kPass / 1000)", consumed)
        yearly = body(self.probes, "function OpexC75BypassFlushYear(")
        self.assertIn('"C7Y|"', yearly)
        self.assertIn('"C7S|"', yearly)

    def test_causal_harness_decodes_durable_signs(self):
        self.assertIn("def c75_bypass_sign_metrics(chunks):", self.bench)
        for marker in ("C7C|", "C7Y|", "C7S|"):
            self.assertIn(marker, self.bench)
        self.assertIn('"c75_bypass_consumed_by_mode"', self.bench)
        self.assertIn('"c75_bypass_consumed_by_kind"', self.bench)
        self.assertIn('"c75_bypass_consumed_by_year"', self.bench)
        self.assertIn("structural.update(c75_bypass_sign_metrics(chunks))", self.bench)


if __name__ == "__main__":
    unittest.main()
