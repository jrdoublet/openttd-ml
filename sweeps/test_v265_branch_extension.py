"""V265 : contrats statiques et comportementaux du prolongement de ligne par embranchement.

Réglage booléen v265_branch_extension, défaut 0 à tous les niveaux.
Modèle AAAHogEx TrainRouteExtendBuilder (trainroute.nut:3161), CombineByFork (railbuilder.nut:930)
et anti-blocage (trainroute.nut:2385).
Au défaut 0, aucun calcul nouveau n'est exécuté (coût d'opcodes nul).
"""
from pathlib import Path
import re
import unittest

from campaign_freeze import parse_ai_settings, parse_ai_setting_specs

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _body(source, signature):
    match = re.search(re.escape(signature) + r"\s*\{(.*?)\n\}", source, re.S)
    return match.group(1) if match else ""


class TestV265BranchExtension(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.task = cls.sources["task_v265.nut"]
        cls.dispatch = _body(cls.task, "function OpexAI::_dispatchV265BranchExtension(task, year)")
        cls.scan_and_branch = _body(cls.task, "function OpexAI::_v265ScanAndBranchLine(year)")
        cls.antiblock = _body(cls.task, "function OpexAI::_v265AntiBlockStep()")

    def test_setting_declared_default_zero(self):
        specs = parse_ai_setting_specs(AI / "info.nut")
        self.assertIn("v265_branch_extension", specs)
        spec = specs["v265_branch_extension"]
        self.assertEqual(spec["default"], 0)
        self.assertTrue(spec["boolean"])
        self.assertEqual(spec["min_value"], 0)
        self.assertEqual(spec["max_value"], 1)

        info_text = self.sources["info.nut"]
        block = re.search(r'name = "v265_branch_extension",(.*?)\}\);', info_text, re.S)
        self.assertIsNotNone(block)
        body = block.group(1)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertRegex(body, level + r"\s*=\s*0\b", f"{level} must be 0")

        defaults = parse_ai_settings(AI / "info.nut")
        self.assertEqual(defaults["v265_branch_extension"], 0)

    def test_setting_read_once(self):
        reads = [(name, text.count('GetSetting("v265_branch_extension")'))
                 for name, text in self.sources.items()]
        total_reads = sum(count for _, count in reads)
        self.assertEqual(total_reads, 1, f"Expected 1 GetSetting read, found {total_reads}: {reads}")
        self.assertIn('AIController.GetSetting("v265_branch_extension")', self.sources["settings.nut"])

    def test_globals_declared_with_sources(self):
        pre = self.sources["globals_pre.nut"]
        self.assertIn("V265_BRANCH_EXTENSION <- false;", pre)
        self.assertIn("const V265_MIN_BRANCH_TILES = 12;", pre)
        self.assertIn("const V265_BRANCH_AIR_CAPITAL_GUARD = 50000;", pre)
        self.assertIn("const V265_BRANCH_SCAN_COOLDOWN_DAYS = 90;", pre)

        # Vérification des commentaires de sourçage
        match_min = re.search(r"/\*.*?(station_spread|12).*?\*/\s*const V265_MIN_BRANCH_TILES", pre, re.S)
        self.assertIsNotNone(match_min, "V265_MIN_BRANCH_TILES must be sourced in comment")

        match_guard = re.search(r"/\*.*?(BAC 1-11|Viscount|avion|AIR).*?\*/\s*const V265_BRANCH_AIR_CAPITAL_GUARD", pre, re.S)
        self.assertIsNotNone(match_guard, "V265_BRANCH_AIR_CAPITAL_GUARD must be sourced in comment")

    def test_zero_cost_guards_at_default(self):
        # 1. Dispatch return immédit
        self.assertTrue(self.dispatch)
        self.assertIn("if (!V265_BRANCH_EXTENSION) return false;", self.dispatch)

        # 2. Scan and branch return immédiat
        self.assertTrue(self.scan_and_branch)
        guard_scan = "if (!V265_BRANCH_EXTENSION) return false;"
        self.assertIn(guard_scan, self.scan_and_branch)
        guard_pos = self.scan_and_branch.index(guard_scan)
        for api in ("AICompany", "AIStation", "AIVehicle", "AIRail", "AIMap", "OpexDecide"):
            found = self.scan_and_branch.find(api)
            if found >= 0:
                self.assertGreater(found, guard_pos, f"API {api} called before guard in _v265ScanAndBranchLine")

        # 3. Anti-blocage return immédiat
        self.assertTrue(self.antiblock)
        guard_ab = "if (!V265_BRANCH_EXTENSION) return;"
        self.assertIn(guard_ab, self.antiblock)
        guard_ab_pos = self.antiblock.index(guard_ab)
        for api in ("AICompany", "AIStation", "AIVehicle", "AIRail", "AIMap", "OpexDecide"):
            found = self.antiblock.find(api)
            if found >= 0:
                self.assertGreater(found, guard_ab_pos, f"API {api} called before guard in _v265AntiBlockStep")

        # 4. Garde dans scheduler.nut
        sched = self.sources["scheduler.nut"]
        self.assertIn("if (V265_BRANCH_EXTENSION) this._v265AntiBlockStep();", sched)

        # 5. Garde dans main.nut
        main = self.sources["main.nut"]
        self.assertIn('{ name = "v265_branch_extension", dueCycle = 0, enabled = V265_BRANCH_EXTENSION }', main)

    def test_air_capital_protection_and_solvency_guards(self):
        # Vérifie la protection contre le siphonnement de caisse AIR (V149/V207)
        self.assertIn("OPEX_START_YEAR + 2", self.scan_and_branch, "Must lock extensions during 1970-1971 AIR bootstrap")
        self.assertIn("AICompany.GetLoanAmount()", self.scan_and_branch, "Must forbid extensions with outstanding loan")
        self.assertIn("V265_BRANCH_AIR_CAPITAL_GUARD", self.scan_and_branch, "Must protect capital for aircraft")
        self.assertIn("OpexCashReserve()", self.scan_and_branch, "Must respect cash reserve")

    def test_antiblocking_aaahogex_model(self):
        # Modèle AAAHogEx trainroute.nut:2385 : srcStationStops.len() >= platformNum
        self.assertIn("AIVehicle.VS_AT_STATION", self.antiblock)
        self.assertIn("srcStationStops.len() >= platformNum", self.antiblock)
        self.assertIn("AIVehicle.SendVehicleToDepot", self.antiblock)
        # R22 toggle guard
        self.assertIn("AIOrder.IsGotoDepotOrder", self.antiblock)
        # Reprise quand quai libre
        self.assertIn("AIVehicle.IsStoppedInDepot", self.antiblock)
        self.assertIn("AIVehicle.StartStopVehicle", self.antiblock)

    def test_fork_signaling_and_switch(self):
        # Aiguillage sur voie vive et signaux PBS sur les branches approchant la bifurcation
        self.assertIn("AIRail.BuildRail", self.scan_and_branch)
        self.assertIn("OpexTryBuildSignal", self.scan_and_branch)
        self.assertIn("AIOrder.InsertOrder", self.scan_and_branch)

    def test_decision_logs_properly_guarded(self):
        for tag in ("V265_CANDIDATE", "V265_SKIP", "V265_BUILD", "V265_FORK", "V265_ANTIBLOCK"):
            self.assertIn(f'"{tag}"', self.task)
        # Vérifie que les logs de décision sont sous condition DECISION_LOG
        occurrences = [m.start() for m in re.finditer(r'OpexDecide\("V265_', self.task)]
        self.assertGreater(len(occurrences), 0)
        for pos in occurrences:
            prefix = self.task[max(0, pos - 300):pos]
            self.assertIn("DECISION_LOG", prefix, f"OpexDecide at pos {pos} must be guarded by DECISION_LOG")

    def test_no_reserved_keywords_or_squirrel_pitfalls(self):
        # Les mots clone, base, parent sont interdits comme identifiants
        for word in ("base", "parent"):
            self.assertNotRegex(self.task, r"\b" + word + r"\s*=", f"Reserved word {word} used as identifier")
            self.assertNotRegex(self.task, r"\bfunction\s+" + word + r"\b", f"Reserved word {word} used as function name")
            self.assertNotRegex(self.task, r"\blocal\s+" + word + r"\b", f"Reserved word {word} used as local variable")


if __name__ == "__main__":
    unittest.main()
