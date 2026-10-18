"""V265 : contrats statiques du prolongement d'une ligne fret rail (modèle AAAHogEx
SearchAndBuildAdditionalDest / TrainRouteExtendBuilder).

Réglage booléen v265_branch_extension, défaut 0 : tâche désactivée dans la file, aucun
crochet hors file. La voie passe par l'A* V129 segmenté (créneau _railSearch, kind "v265"),
jamais par une pose en ligne droite ; aucune constante propre (réserve = meilleur projet AIR).
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
        cls.try_line = _body(cls.task, "function OpexAI::_v265TryLine(line, date)")
        cls.consume = _body(cls.task, "function OpexAI::_v265ConsumeSearch()")
        cls.reserve = _body(cls.task, "function OpexAI::_v265AirReserve()")

    def test_setting_declared_default_zero(self):
        spec = parse_ai_setting_specs(AI / "info.nut")["v265_branch_extension"]
        self.assertEqual(spec["default"], 0)
        self.assertTrue(spec["boolean"])
        self.assertEqual((spec["min_value"], spec["max_value"]), (0, 1))
        self.assertEqual(parse_ai_settings(AI / "info.nut")["v265_branch_extension"], 0)

    def test_setting_read_once(self):
        total = sum(t.count('GetSetting("v265_branch_extension")') for t in self.sources.values())
        self.assertEqual(total, 1)
        self.assertIn('AIController.GetSetting("v265_branch_extension")', self.sources["settings.nut"])

    def test_inert_at_default(self):
        self.assertIn('{ name = "v265_branch_extension", dueCycle = 0, enabled = V265_BRANCH_EXTENSION }',
                      self.sources["main.nut"])
        self.assertTrue(self.dispatch.lstrip().startswith("if (!V265_BRANCH_EXTENSION) return false;"))
        # Aucun crochet hors file (l'ancien anti-blocage tournait à chaque tour).
        self.assertNotIn("_v265AntiBlockStep", "".join(self.sources.values()))
        rail = self.sources["task_rail.nut"]
        self.assertIn('V265_BRANCH_EXTENSION && state.kind == "v265"', rail)
        self.assertEqual(rail.count('state.kind == "v265"'), 2)

    def test_no_arbitrary_constants(self):
        pre = self.sources["globals_pre.nut"]
        self.assertIn("V265_BRANCH_EXTENSION <- false;", pre)
        for gone in ("V265_MIN_BRANCH_TILES", "V265_BRANCH_AIR_CAPITAL_GUARD",
                     "V265_BRANCH_SCAN_COOLDOWN_DAYS"):
            self.assertNotIn(gone, "".join(self.sources.values()))
        self.assertNotIn("OPEX_START_YEAR", self.task)
        self.assertNotIn("GetLoanAmount", self.task)
        # Seuls littéraux numériques admis : indices, 0/1, et les bornes de boucle du tracé.
        numbers = set(re.findall(r"(?<![\w.])\d+(?![\w.])", re.sub(r"/\*.*?\*/", "", self.task, flags=re.S)))
        # 12 = mois par an ; 100 = RAIL_TERRAIN_FACTOR est en pourcentage (economy.nut) ;
        # 365 = jours par an (GetMaxAge en jours, comme catalog.nut).
        self.assertLessEqual(numbers, {"0", "1", "2", "4", "12", "100", "365"}, numbers)

    def test_reserve_is_best_fundable_air_project(self):
        for needle in ("OpexC121AutopsyIsAirRelated", "OpexProjectFinanceCapital", "OpexCashReserve()",
                       "candidateGroups"):
            self.assertIn(needle, self.reserve)
        self.assertIn("this._v265AirReserve()", self.try_line)
        self.assertIn("this._v265AirReserve()", self.consume)

    def test_track_through_astar(self):
        self.assertIn("OpexCreateSegmentedSearch(", self.try_line)
        self.assertIn('kind = "v265"', self.try_line)
        self.assertIn("this._railSearch != null || this._railExpansion != null", self.dispatch)
        self.assertIn("OpexBuildTrack(tiles, structures)", self.consume)
        self.assertNotIn("OpexV265BuildBranchTrack", self.task)

    def test_live_line_touched_last_and_rolled_back(self):
        st = self.consume.index("AIRail.BuildRailStation")
        trk = self.consume.index("OpexBuildTrack(")
        junc = self.consume.index("AIRail.BuildRail(fork.prev, fork.fork, tiles[1])")
        orders = self.consume.index("AIOrder.InsertOrder")
        self.assertLess(st, trk)
        self.assertLess(trk, junc)
        self.assertLess(junc, orders)
        self.assertGreaterEqual(self.consume.count("AIRail.RemoveRail(fork.prev, fork.fork, tiles[1])"), 2)

    def test_decisions_logged_under_decision_log(self):
        for tag in ("V265_SEARCH", "V265_FAIL", "V265_SKIP", "V265_BUILD"):
            self.assertIn(f'"{tag}"', self.task)
        for m in re.finditer(r'OpexDecide\("V265_', self.task):
            self.assertIn("DECISION_LOG", self.task[max(0, m.start() - 200):m.start()])

    def test_no_reserved_identifiers(self):
        for word in ("base", "parent", "clone"):
            self.assertNotRegex(self.task, r"\blocal\s+" + word + r"\b")


if __name__ == "__main__":
    unittest.main()
