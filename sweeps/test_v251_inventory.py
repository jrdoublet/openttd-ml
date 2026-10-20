"""V251 etape 1 : inventaire lecture seule des types d'industrie finançables.

Au demarrage, sous DECISION_LOG, une passe journalise le reglage de jeu
construction.raw_industry_construction et chaque type (CanBuildIndustry,
CanProspectIndustry, GetConstructionCost, IsRawIndustry, IsProcessingIndustry,
cargos). Aucun achat, aucun nouveau reglage public, aucun GetSetting nouveau.
"""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def _read(name):
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source, name):
    start = source.index("function " + name + "(")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("unterminated " + name)


class TestV251Inventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.probes = cls.sources["probes.nut"]
        cls.main = cls.sources["main.nut"]
        cls.log = _function_body(cls.probes, "OpexV251LogIndustryTypes")
        cls.labels = _function_body(cls.probes, "OpexV251CargoLabels")

    def test_no_new_public_setting(self):
        info = self.sources["info.nut"]
        self.assertLessEqual(info.count("AddSetting("), 73)  # V263b : 81 moins 11 retraits approuves le 20/10 ; +1 V275, +1 V269 (fusions du 20/10) ; +1 PO-01 (branche).
        self.assertNotIn('name = "v251', info)
        settings = self.sources["settings.nut"]
        self.assertNotIn('GetSetting("v251', settings)
        joined = "".join(self.sources.values())
        self.assertEqual(joined.count('AIController.GetSetting("v251'), 0)
        self.assertNotIn("V251_", self.sources["globals_pre.nut"])

    def test_decision_log_guard_before_any_api(self):
        guard = "if (!DECISION_LOG) return;"
        self.assertIn(guard, self.log)
        guard_at = self.log.index(guard)
        for token in (
            "AIIndustryType",
            "AIIndustryTypeList",
            "AIGameSettings",
            "OpexDecide",
            "GetName",
            "GetConstructionCost",
        ):
            found = self.log.find(token)
            self.assertGreater(found, guard_at, token)

    def test_opexdecide_on_same_line_as_decision_log(self):
        count = 0
        for line in self.log.splitlines():
            if "OpexDecide(" in line:
                self.assertIn("DECISION_LOG", line, line)
                self.assertIn('OpexDecide("V251_INDUSTRY_TYPE"', line)
                count += 1
        self.assertEqual(count, 2)

    def test_logs_setting_and_type_fields(self):
        self.assertIn('AIGameSettings.IsValid("construction.raw_industry_construction")', self.log)
        self.assertIn('AIGameSettings.GetValue("construction.raw_industry_construction")', self.log)
        self.assertIn("scope=setting raw_industry_construction=", self.log)
        self.assertIn("scope=type type=", self.log)
        for field in (
            " name=",
            " can_build=",
            " can_prospect=",
            " cost=",
            " raw=",
            " proc=",
            " produced=",
            " accepted=",
            " raw_industry_construction=",
        ):
            self.assertIn(field, self.log, field)
        self.assertIn("AIIndustryType.CanBuildIndustry(type)", self.log)
        self.assertIn("AIIndustryType.CanProspectIndustry(type)", self.log)
        self.assertIn("AIIndustryType.GetConstructionCost(type)", self.log)
        self.assertIn("AIIndustryType.IsRawIndustry(type)", self.log)
        self.assertIn("AIIndustryType.IsProcessingIndustry(type)", self.log)
        self.assertIn("AIIndustryType.GetProducedCargo(type)", self.log)
        self.assertIn("AIIndustryType.GetAcceptedCargo(type)", self.log)
        self.assertIn("AIIndustryType.GetName(type)", self.log)
        self.assertIn("AIIndustryTypeList()", self.log)

    def test_no_build_or_prospect(self):
        for blob in (self.log, self.labels):
            self.assertNotIn("AIIndustryType.BuildIndustry", blob)
            self.assertNotIn("AIIndustryType.ProspectIndustry", blob)
        for name, text in self.sources.items():
            self.assertNotIn("AIIndustryType.BuildIndustry", text, name)
            self.assertNotIn("AIIndustryType.ProspectIndustry", text, name)

    def test_called_once_from_start_after_settings(self):
        start = _function_body(self.main, "OpexAI::Start")
        self.assertEqual(start.count("OpexV251LogIndustryTypes()"), 1)
        self.assertLess(start.index("OpexLoadSettings();"), start.index("OpexV251LogIndustryTypes()"))
        self.assertLess(
            start.index('OpexDecide("SETTINGS"'),
            start.index("OpexV251LogIndustryTypes()"),
        )
        self.assertLess(
            start.index("OpexV251LogIndustryTypes()"),
            start.index("while (true)"),
        )
        joined_calls = sum(text.count("OpexV251LogIndustryTypes(") for text in self.sources.values())
        self.assertEqual(joined_calls, 2)

    def test_no_new_getsetting(self):
        self.assertNotIn("GetSetting", self.log)
        self.assertNotIn("GetSetting", self.labels)
        self.assertNotIn("AIController.GetSetting", self.log)


if __name__ == "__main__":
    unittest.main()
