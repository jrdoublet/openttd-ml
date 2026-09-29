import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AIR = (ROOT / "ai" / "OpexAI" / "builder_air.nut").read_text(encoding="utf-8")
INFO = (ROOT / "ai" / "OpexAI" / "info.nut").read_text(encoding="utf-8")
GLOBALS = (ROOT / "ai" / "OpexAI" / "globals_pre.nut").read_text(encoding="utf-8")
DIAG = (ROOT / "sweeps" / "diag_c104_air_c100_compare.py").read_text(encoding="utf-8")


class C104AirC100CompareProbeTests(unittest.TestCase):
    def test_setting_is_passive_and_off_by_default(self):
        self.assertIn("C104_AIR_C100_COMPARE_PROBE <- false;", GLOBALS)
        start = INFO.index('name = "c104_air_c100_compare_probe"')
        snippet = INFO[start:start + 620]
        for field in ("easy_value = 0", "medium_value = 0", "hard_value = 0", "custom_value = 0"):
            self.assertIn(field, snippet)

    def test_probe_evaluates_all_three_models(self):
        match = re.search(r"function OpexC104BestAirEngine\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("0, false, false, false, true", body)
        self.assertIn("0, false, false, true, false", body)
        self.assertIn("economics.profitAnnual > bestEconomics.profitAnnual", body)

    def test_probe_is_observational(self):
        full = AIR[AIR.index("function OpexAirChooseRoutePlaneFull("):]
        self.assertIn("OpexC104ProbeAirEngineCompare", full)
        self.assertIn("C104_AIR_C100_COMPARE_PROBE && !C115_AIR_C100_CAPITAL_REPLAY && C72_PLANE_CHOICE == 0",
                      " ".join(full.split()))
        probe = re.search(r"function OpexC104ProbeAirEngineCompare\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(probe)
        self.assertIn('AILog.Warning("C104_COMPARE', probe.group(1))
        self.assertIn('" kdec=" + kDec', probe.group(1))
        self.assertIn("OpexC106MarginalPhysicalChoice", probe.group(1))
        self.assertIn('OpexC104FormatAirChoice("marginal", marginal)', probe.group(1))
        self.assertIn("OpexC107OneStepMarginalPhysicalChoice", probe.group(1))
        self.assertIn('OpexC104FormatAirChoice("onestep", oneStep)', probe.group(1))
        self.assertIn("OpexC108PhysicalSpeedPowerChoice", probe.group(1))
        self.assertIn('OpexC104FormatAirChoice("s4", speed4)', probe.group(1))
        self.assertIn("OpexC109OneStepSpeedElasticityChoice", probe.group(1))
        self.assertIn('OpexC104FormatAirChoice("e100", elastic100)', probe.group(1))
        self.assertNotIn("return { plane =", probe.group(1))

    def test_marginal_candidate_is_relative_and_physical(self):
        match = re.search(r"function OpexC106MarginalPhysicalChoice\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("0, false, false, true, false", body)
        self.assertIn("marginalRoi * 1000.0 >= runner.economics.roi * relativeRoiPermille", body)
        self.assertNotIn("AICompany.GetBankBalance", body)

    def test_onestep_candidate_is_relative_physical_and_non_recursive(self):
        match = re.search(r"function OpexC107OneStepMarginalPhysicalChoice\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("0, false, false, true, false", body)
        self.assertIn("marginalRoi * 1000.0 >= runner.economics.roi * relativeRoiPermille", body)
        self.assertNotIn("while (true)", body)
        self.assertNotIn("AICompany.GetBankBalance", body)

    def test_c69_physical_candidate_uses_dynamic_decision_capital(self):
        match = re.search(r"function OpexC106PhysicalC69Choice\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("OpexC69CachedKDec()", body)
        self.assertIn("financeCapital > kDec ? financeCapital : kDec", body)
        self.assertIn("OpexProjectScore(economics.profitAnnual, denom)", body)
        self.assertIn("0, false, false, true, false", body)
        self.assertNotIn("AICompany.GetBankBalance", body)

    def test_power_candidate_is_physical_and_has_no_cash_threshold(self):
        match = re.search(r"function OpexC106PhysicalPowerChoice\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("0, false, false, true, false", body)
        self.assertIn("local r16 = sqrt(r8);", body)
        self.assertIn("economics.profitAnnual.tofloat() / denom", body)
        self.assertNotIn("AICompany.GetBankBalance", body)

    def test_speed_power_candidate_is_relative_physical_and_has_no_cash_threshold(self):
        match = re.search(r"function OpexC108PhysicalSpeedPowerChoice\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("0, false, false, true, false", body)
        self.assertIn("local v = plane.speed.tofloat();", body)
        self.assertIn("local r4 = sqrt(r2);", body)
        self.assertIn("economics.profitAnnual.tofloat() / denom", body)
        self.assertNotIn("AICompany.GetBankBalance", body)

    def test_speed_elasticity_candidate_is_dimensionless_and_physical(self):
        match = re.search(r"function OpexC109OneStepSpeedElasticityChoice\(.*?\)(.*?)\n\}", AIR, re.S)
        self.assertIsNotNone(match)
        body = match.group(1)
        self.assertIn("0, false, false, true, false", body)
        self.assertIn("profitGainPermille", body)
        self.assertIn("speedGainPermille", body)
        self.assertIn("speedGainPermille * relativeElasticityPermille", body)
        self.assertNotIn("AICompany.GetBankBalance", body)
        self.assertNotIn(".price", body)
        self.assertNotIn(".capital", body)

    def test_diagnostic_deduplicates_cumulative_openttd_output(self):
        self.assertIn("C104_KEEP_SEEN = set()", DIAG)
        self.assertIn("if event_key in C104_KEEP_SEEN", DIAG)
        self.assertIn("C104_KEEP_SEEN.add(event_key)", DIAG)
        self.assertIn("if not events:", DIAG)
        self.assertNotIn('"raw_output_tail": raw_output[-20000:]', DIAG)


if __name__ == "__main__":
    unittest.main()
