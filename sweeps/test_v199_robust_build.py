"""Tests statiques et de contrat pour V199 : robustesse de pose rail a la maniere d'AAAHogEx.

Verifie :
- Declaration des reglages v199_robust_build (bool, defaut 0) et v199_level_budget_k (defaut 20)
  dans info.nut, globals_pre.nut, settings.nut
- Fonction de verification de demolition OpexV199CanDemolishTile (arbres, maisons, hors rail adverse)
- Fonction de reprise locale OpexV199RetryToBuild (A* bornee <= 20%, tuile fautive interdite, rollback propre)
- Fonction de nivellement OpexV199RebuildForHomeward (bande laterale cote retour, plafond de budget, skip cotes/ponts/tunnels)
- Integration dans OpexBuildTrack (demolition ERR_AREA_NOT_CLEAR, retry max 3, signaux en ligne)
- Integration dans OpexV198ExecuteRailPlan et OpexV190ExecuteRailPlan
- Journalisation de decision OpexDecide("V199", "step=retry|level|signal|demolish ok=.. n=.. cost=..")
- Invariance stricte au defaut (v199_robust_build = 0)
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI_DIR = ROOT / "ai" / "OpexAI"


def read_file(rel_path):
    return (AI_DIR / rel_path).read_text(encoding="utf-8")


def function_body(source, name):
    pattern = rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{"
    match = re.search(pattern, source)
    if not match:
        raise AssertionError(f"Function {name} not found")
    start = match.end() - 1
    depth = 0
    for pos in range(start, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:pos]
    raise AssertionError(f"Unclosed function {name}")


class TestV199Settings(unittest.TestCase):
    def setUp(self):
        self.info = read_file("info.nut")
        self.globals_pre = read_file("globals_pre.nut")
        self.settings = read_file("settings.nut")

    def test_info_settings_declared(self):
        self.assertIn('"v199_robust_build"', self.info)
        self.assertIn('"v199_level_budget_k"', self.info)
        # Check default value 0 for v199_robust_build
        match_robust = re.search(r'name\s*=\s*"v199_robust_build"[^}]+flags\s*=\s*AICONFIG_BOOLEAN', self.info, re.S)
        self.assertIsNotNone(match_robust, "v199_robust_build must be AICONFIG_BOOLEAN")
        self.assertIn("easy_value = 0", match_robust.group(0))

        # Check default value 20 for v199_level_budget_k
        match_level = re.search(r'name\s*=\s*"v199_level_budget_k"[^}]+easy_value\s*=\s*20', self.info, re.S)
        self.assertIsNotNone(match_level, "v199_level_budget_k must default to 20")

    def test_globals_pre_declared(self):
        self.assertIn("V199_ROBUST_BUILD <- false;", self.globals_pre)
        self.assertIn("V199_LEVEL_BUDGET_K <- 20;", self.globals_pre)

    def test_settings_loaded(self):
        self.assertIn('V199_ROBUST_BUILD = AIController.GetSetting("v199_robust_build") != 0;', self.settings)
        self.assertIn('AIController.GetSetting("v199_level_budget_k")', self.settings)


class TestV199Helpers(unittest.TestCase):
    def setUp(self):
        self.builder = read_file("builder_rail.nut")

    def test_demolish_helper_structure(self):
        self.assertIn("function OpexV199CanDemolishTile(tile)", self.builder)
        body = function_body(self.builder, "OpexV199CanDemolishTile")
        # Rail non a nous exclu
        self.assertIn("AITile.TRANSPORT_RAIL", body)
        self.assertIn("!AICompany.IsMine", body)
        # Ne pas demolir nos gares ou depots
        self.assertIn("AIRail.IsRailStationTile", body)
        self.assertIn("AIRail.IsRailDepotTile", body)
        # Pas d'eau
        self.assertIn("AITile.IsWaterTile", body)
        # Test mode pour verifier autorisation
        self.assertIn("AITestMode()", body)
        self.assertIn("AITile.DemolishTile(tile)", body)

    def test_retry_helper_structure(self):
        self.assertIn("function OpexV199RetryToBuild(tiles, failIdx, initialBudget, retriesCount", self.builder)
        body = function_body(self.builder, "OpexV199RetryToBuild")
        # Interdiction de la tuile fautive
        self.assertIn("ignored = [faultyTile]", body)
        # Budget borne <= 20%
        self.assertIn("(budgetCap * 20) / 100", body)
        # Cible 5 a 15 tuiles plus loin ou la fin
        self.assertIn("failIdx + 10", body)
        self.assertIn("L - 1", body)
        # Raccordement via A*
        self.assertIn("OpexCreateRailPathfinder", body)
        self.assertIn("OpexAdvanceRailPathfinder", body)
        # Rollback propre en cas d'echec de reprise
        self.assertIn("AITile.DemolishTile", body)
        self.assertIn("step=retry ok=0", body)
        self.assertIn("step=retry ok=1", body)

    def test_homeward_leveling_helper_structure(self):
        self.assertIn("function OpexV199RebuildForHomeward(tiles1, side = 1, budgetK = 20)", self.builder)
        body = function_body(self.builder, "OpexV199RebuildForHomeward")
        # Guard sur V199_ROBUST_BUILD
        self.assertIn("if (!V199_ROBUST_BUILD) return 0;", body)
        # Saut des ponts et tunnels
        self.assertIn("AIBridge.IsBridgeTile", body)
        self.assertIn("AITunnel.IsTunnelTile", body)
        # Saut des cotes et tuiles non constructibles
        self.assertIn("AITile.IsCoastTile", body)
        self.assertIn("!AITile.IsBuildable", body)
        # Saut du rail
        self.assertIn("AITile.TRANSPORT_RAIL", body)
        # Plafond de depense
        self.assertIn("budgetK * 1000", body)
        # Nivellement rectangle ou LowerTile/RaiseTile
        self.assertIn("AITile.LevelTiles", body)
        self.assertIn("AITile.LowerTile", body)
        self.assertIn("AITile.RaiseTile", body)
        # Journal de decision
        self.assertIn('step=level ok=', body)


class TestV199OpexBuildTrackIntegration(unittest.TestCase):
    def setUp(self):
        self.builder = read_file("builder_rail.nut")
        self.body = function_body(self.builder, "OpexBuildTrack")

    def test_signature_accepts_options(self):
        self.assertIn("function OpexBuildTrack(tiles, structures = null, failure = null, options = null)", self.builder)

    def test_demolish_on_err_area_not_clear(self):
        self.assertIn("AIError.ERR_AREA_NOT_CLEAR", self.body)
        self.assertIn("OpexV199CanDemolishTile", self.body)
        self.assertIn('step=demolish ok=', self.body)

    def test_retry_on_failure(self):
        self.assertIn("OpexV199RetryToBuild", self.body)
        self.assertIn("retriesCount < 3", self.body)
        # Rollback si > 3 reprises
        self.assertIn("AITile.DemolishTile", self.body)

    def test_online_signals(self):
        self.assertIn("SIGNALTYPE_PBS_ONEWAY", self.body)
        # N = max(4, trainLength + 1)
        self.assertIn("max(4, trainLen + 1)", self.body)
        # Sommet de rampe
        self.assertIn("AITile.GetMaxHeight(cur) > AITile.GetMaxHeight(prev)", self.body)
        self.assertIn("AITile.GetMaxHeight(cur) >= AITile.GetMaxHeight(next)", self.body)
        # Restreint aux lignes doubles / boucles
        self.assertIn("isDouble", self.body)
        # Journal signal
        self.assertIn('step=signal ok=1', self.body)


class TestV199DoubleTrackIntegration(unittest.TestCase):
    def setUp(self):
        self.templates = read_file("rail_templates.nut")
        self.builder = read_file("builder_rail.nut")

    def test_v198_uses_v199_robustness(self):
        exec_v198 = function_body(self.templates, "OpexV198ExecuteRailPlan")
        # Track options passed to OpexBuildTrack
        self.assertIn("trackOpt1", exec_v198)
        self.assertIn("trackOpt2", exec_v198)
        # RebuildForHomeward called after track 1 succeeds
        self.assertIn("OpexV199RebuildForHomeward(tiles1, 1, V199_LEVEL_BUDGET_K);", exec_v198)
        # Accounting shield protection for retrySearchCost
        self.assertIn("searchCostV198 += trackOpt1.retrySearchCost", exec_v198)
        self.assertIn("searchCostV198 += trackOpt2.retrySearchCost", exec_v198)

    def test_v190_uses_v199_robustness(self):
        exec_v190 = function_body(self.builder, "OpexV190ExecuteRailPlan")
        self.assertIn("trackOpt1", exec_v190)
        self.assertIn("trackOpt2", exec_v190)
        self.assertIn("OpexV199RebuildForHomeward(tiles, side, V199_LEVEL_BUDGET_K);", exec_v190)


class TestV199CodeRules(unittest.TestCase):
    def setUp(self):
        self.files = ["info.nut", "globals_pre.nut", "settings.nut", "builder_rail.nut", "rail_templates.nut"]

    def test_no_reserved_keywords(self):
        pattern = re.compile(r"\b(clone|parent|base)\b")
        for fn in self.files:
            content = read_file(fn)
            # Find V199 sections
            v199_lines = [line for line in content.splitlines() if "V199" in line or "v199" in line]
            for line in v199_lines:
                # Disallow reserved words in V199 lines
                m = pattern.search(line)
                self.assertIsNone(m, f"Reserved word '{m.group(0) if m else ''}' in {fn}: {line}")

    def test_decision_log_format(self):
        builder = read_file("builder_rail.nut")
        steps = ["retry", "level", "signal", "demolish"]
        for s in steps:
            pattern = rf'OpexDecide\("V199",\s*"step={s}\s+ok='
            self.assertTrue(re.search(pattern, builder), f"Decision log for step={s} missing or incorrect")


if __name__ == "__main__":
    unittest.main()
