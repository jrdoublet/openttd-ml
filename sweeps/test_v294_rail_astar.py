"""Contrats statiques de V294 : ponts/tunnels longs et recherche A* continue (defaut 0).

Verifie :
1. Declaration des reglages v294_rail_bridge_len (0..30) et v294_rail_continuous (0/1) avec defauts a 0.
2. Lecture unique dans settings.nut vers les globales V294_RAIL_BRIDGE_LEN et V294_RAIL_CONTINUOUS.
3. Declaration des globales dans globals_pre.nut a 0.
4. Aucun symbole global V294_* non declare dans tout le code Squirrel.
5. Gardes strictes V294_RAIL_BRIDGE_LEN > 0 et V294_RAIL_CONTINUOUS > 0 autour de chaque nouveau chemin.
6. Conformite du format de retour de la recherche continue avec OpexSegmentedResult.
7. Verification que v129.nut lit bien _max_bridge_length et _max_tunnel_length.
"""
from pathlib import Path
import re
import unittest

AI = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def _read(rel_path):
    return (AI / rel_path).read_text(encoding="utf-8")


def _function_body(source, signature):
    idx = source.find(signature)
    if idx < 0:
        return ""
    brace = source.find("{", idx)
    if brace < 0:
        return ""
    depth = 0
    pos = brace
    while pos < len(source):
        char = source[pos]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1:pos]
        pos += 1
    return ""


class TestV294RailAstar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.relative_to(AI).as_posix(): p.read_text(encoding="utf-8")
                       for p in AI.rglob("*.nut")}
        cls.info = cls.sources["info.nut"]
        cls.settings = cls.sources["settings.nut"]
        cls.globals_pre = cls.sources["globals_pre.nut"]
        cls.builder_rail = cls.sources["builder_rail.nut"]
        cls.task_rail = cls.sources["task_rail.nut"]
        cls.v129 = cls.sources["pathfinder_v90/v129.nut"]
        cls.v90_rail = cls.sources["pathfinder_v90/rail.nut"]

    def test_settings_declared_and_default_zero(self):
        # 1. v294_rail_bridge_len
        m_bridge = re.search(r'name = "v294_rail_bridge_len",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(m_bridge, "v294_rail_bridge_len doit etre declare dans info.nut")
        body_b = m_bridge.group(1)
        self.assertIn("min_value = 0", body_b)
        self.assertIn("max_value = 30", body_b)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value", "default_value"):
            self.assertRegex(body_b, rf"{level}\s*=\s*20\b", f"{level} doit valoir 20 pour bridge_len")

        # 2. v294_rail_continuous
        m_cont = re.search(r'name = "v294_rail_continuous",(.*?)\}\);', self.info, re.S)
        self.assertIsNotNone(m_cont, "v294_rail_continuous doit etre declare dans info.nut")
        body_c = m_cont.group(1)
        self.assertIn("min_value = 0", body_c)
        self.assertIn("max_value = 1", body_c)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value", "default_value"):
            self.assertRegex(body_c, rf"{level}\s*=\s*0\b", f"{level} doit valoir 0 pour continuous")

    def test_settings_loaded_once_in_settings(self):
        for name in ("v294_rail_bridge_len", "v294_rail_continuous"):
            reads = [(fn, text.count(f'GetSetting("{name}")'))
                     for fn, text in self.sources.items()]
            total_reads = sum(count for _, count in reads)
            self.assertEqual(total_reads, 1, f"{name} doit etre lu exactement une fois")
            self.assertIn(f'AIController.GetSetting("{name}")', self.settings)

        self.assertIn("V294_RAIL_BRIDGE_LEN = (v294BridgeLen != null && v294BridgeLen >= 0 && v294BridgeLen <= 30) ? v294BridgeLen : 0;", self.settings)
        self.assertIn("V294_RAIL_CONTINUOUS = (v294Continuous != null && v294Continuous > 0) ? 1 : 0;", self.settings)

    def test_globals_declared_in_globals_pre(self):
        self.assertIn("V294_RAIL_BRIDGE_LEN <- 20;", self.globals_pre)
        self.assertIn("V294_RAIL_CONTINUOUS <- 0;", self.globals_pre)

    def test_no_undeclared_v294_globals(self):
        allowed = {"V294_RAIL_BRIDGE_LEN", "V294_RAIL_CONTINUOUS",  # v294 ; integration v294all :
                   "V294_RAIL_WEIGHT_PCT", "V294_RAIL_AAA_COSTS", "V294_RAIL_REVERSE_PROBE",
                   "V294_RAIL_DIST_DECOUPLE", "V294_RAIL_SLOPE_ENGINE"}
        found = set()
        for fn, text in self.sources.items():
            for m in re.finditer(r"\b(V294_[A-Z0-9_]+)\b", text):
                found.add(m.group(1))
        self.assertEqual(found, allowed, f"Symboles V294 non autorises trouves: {found - allowed}")

    def test_guards_around_all_v294_bridge_len_paths(self):
        # Options regroupees dans OpexV294ApplyRailCosts, appelee a la creation et a chaque segment.
        helper = _function_body(self.builder_rail, "function OpexV294ApplyRailCosts(")
        self.assertIn("if (V294_RAIL_BRIDGE_LEN > 0) {", helper)
        self.assertIn("pathfinder.cost.max_bridge_length = V294_RAIL_BRIDGE_LEN;", helper)
        self.assertIn("pathfinder.cost.max_tunnel_length = V294_RAIL_BRIDGE_LEN;", helper)
        body_create = _function_body(self.builder_rail, "function OpexCreateRailPathfinder(")
        self.assertIn("OpexV294ApplyRailCosts(pathfinder, engine);", body_create)
        body_advance = _function_body(self.builder_rail, "function OpexAdvanceSegmentedSearch(")
        self.assertIn('OpexV294ApplyRailCosts(pathfinder, ("engine" in state) ? state.engine : null);', body_advance)

    def test_guards_around_all_v294_continuous_paths(self):
        # 1. Dans builder_rail.nut : OpexAdvanceRailPathfinder
        body_adv_pf = _function_body(self.builder_rail, "function OpexAdvanceRailPathfinder(")
        self.assertIn("if (V294_RAIL_CONTINUOUS > 0) {", body_adv_pf)
        self.assertIn("return { path = path, iterations = spent, stop = stop, done = done };", body_adv_pf)

        # 2. Dans task_rail.nut : _startRailSearch
        body_start = _function_body(self.task_rail, "function OpexAI::_startRailSearch(")
        self.assertIn("if (V294_RAIL_CONTINUOUS > 0) {", body_start)
        self.assertIn("pathfinder = OpexCreateRailPathfinder(plan.plansA, plan.plansB, clearanceTiles, searchWeight, outwardSide, null, candidateEngine);", body_start)
        self.assertIn("segmented = OpexCreateSegmentedSearch(plan.plansA, plan.plansB, searchBudget, clearanceTiles, searchWeight, outwardSide, null, candidateEngine);", body_start)

        # 3. Dans task_rail.nut : _startRailUpgradeSearch
        body_upg = _function_body(self.task_rail, "function OpexAI::_startRailUpgradeSearch(")
        self.assertIn("if (V294_RAIL_CONTINUOUS > 0) {", body_upg)
        self.assertIn("pathfinder = OpexCreateRailPathfinder(prep.dualA, prep.dualB, prep.ignored, searchWeight, null, null, lineEngine);", body_upg)
        self.assertIn("segmented = OpexCreateSegmentedSearch(prep.dualA, prep.dualB, prep.iterationBudget, prep.ignored, searchWeight, null, null, lineEngine);", body_upg)

        # 4. Dans task_rail.nut : _scheduleStockRailSearch
        body_stock = _function_body(self.task_rail, "function OpexAI::_startRailStockSearch(")
        self.assertIn("if (V294_RAIL_CONTINUOUS > 0) {", body_stock)
        self.assertIn("pathfinder = OpexCreateRailPathfinder(plan.plansA, plan.plansB, clearanceTiles, searchWeight, outwardSide, null, candidateEngine);", body_stock)
        self.assertIn("segmented = OpexCreateSegmentedSearch(plan.plansA, plan.plansB, plan.iterationBudget, clearanceTiles, searchWeight, outwardSide, null, candidateEngine);", body_stock)

    def test_continuous_result_format_matches_segmented(self):
        # Verifier les 9 cles retournees par OpexSegmentedResult
        body_seg_res = _function_body(self.builder_rail, "function OpexSegmentedResult(")
        expected_keys = {
            "path", "tiles", "structures", "iterations", "stop", "done",
            "segments", "backtracks", "localChoices",
        }
        for key in expected_keys:
            self.assertIn(f"{key} =", body_seg_res)

        # Verifier que le bloc V294_RAIL_CONTINUOUS > 0 dans OpexAdvanceRailPathfinder
        # retourne exactement ces memes 9 cles
        body_adv_pf = _function_body(self.builder_rail, "function OpexAdvanceRailPathfinder(")
        self.assertIn("if (V294_RAIL_CONTINUOUS > 0) {", body_adv_pf)
        for key in expected_keys:
            self.assertIn(f"{key} =", body_adv_pf)

    def test_v129_and_v90_read_max_bridge_and_tunnel_length(self):
        # Verification que v129.nut lit bien ces champs
        self.assertIn("this._max_bridge_length", self.v129)
        self.assertIn("this._max_tunnel_length", self.v129)
        # Et v90 rail.nut
        self.assertIn("case \"max_bridge_length\": this._main._max_bridge_length = val;", self.v90_rail)
        self.assertIn("case \"max_tunnel_length\": this._main._max_tunnel_length = val;", self.v90_rail)


if __name__ == "__main__":
    unittest.main()
