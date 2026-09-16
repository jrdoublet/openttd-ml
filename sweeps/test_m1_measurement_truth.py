"""Contrats M1 : les canaux publies decrivent ce qu'ils mesurent sans changer le metier."""
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"
SWEEPS = ROOT / "sweeps"


def source(path):
    return path.read_text(encoding="utf-8")


def function_body(text, signature):
    start = text.index(signature)
    brace = text.index("{", start)
    depth = 0
    for pos in range(brace, len(text)):
        if text[pos] == "{":
            depth += 1
        elif text[pos] == "}":
            depth -= 1
            if depth == 0:
                return text[brace + 1 : pos]
    raise AssertionError(f"corps non ferme: {signature}")


class TestM1MeasurementTruth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledgers = source(AI / "ledgers.nut")
        cls.candidates = source(AI / "candidates.nut")
        cls.projects = source(AI / "projects.nut")
        cls.probes = source(AI / "probes.nut")
        cls.task_projects = source(AI / "task_projects.nut")
        cls.scheduler = source(AI / "scheduler_tasks.nut")
        cls.town = source(AI / "task_town.nut")
        cls.parser = source(SWEEPS / "opex_full_campaign.py")

    def test_c50_uses_current_quarter_company_value(self):
        body = function_body(self.ledgers, "function OpexAI::_logC50AnnualReport(")
        self.assertIn("AICompany.GetQuarterlyCompanyValue", body)
        self.assertIn("AICompany.CURRENT_QUARTER", body)
        self.assertNotIn("local val = 0", body)

    def test_road_profit_reject_and_retained_are_separate(self):
        make = function_body(self.candidates, "function OpexMakeRoadCandidate(")
        self.assertIn("stats.profitNonPositive++", make)
        self.assertIn("stats.profitBelowFloorKept++", make)
        build = function_body(self.candidates, "function OpexBuildRoadCandidates(")
        self.assertIn('VIVIER_REJECT", "reason=road_profit_non_positive', build)
        self.assertIn('VIVIER_RETAINED", "reason=road_profit_below_floor', build)
        self.assertNotIn('VIVIER_REJECT", "reason=road_profit_too_low', build)

    def test_empty_pool_probe_counts_only_real_road_profit_rejects(self):
        body = function_body(self.probes, "function OpexC63ClassifyAbsent(")
        self.assertIn(
            'if ("profitNonPositive" in rdst) unprofitable += rdst.profitNonPositive',
            body,
        )

    def test_vivier_has_honest_canonical_pool_labels_and_legacy_aliases(self):
        body = function_body(self.projects, "function OpexLogVivier(")
        for field in (
            '" pool_selected="',
            '" not_selected="',
            '" selection_pool_capital="',
            '" next_capital="',
            '" pool_headroom="',
        ):
            self.assertIn(field, body)
        self.assertIn('" rejected="', body)
        self.assertIn('" remaining="', body)

    def test_selected_capital_value_is_preserved_for_growth_policy(self):
        town = function_body(self.town, "function OpexAI::_tryTownGrowth(")
        self.assertIn("this._projects.stats.selectedCapital", town)
        self.assertGreaterEqual(self.projects.count(".selectedCapital = selectedCap"), 3)
        self.assertGreaterEqual(self.projects.count("selectionPoolCapital"), 5)
        self.assertGreaterEqual(self.projects.count("nextProjectCapital"), 5)

    def test_portfolio_rank_exposes_actual_rank_channel(self):
        for signature in (
            "function OpexLogPortfolioRank(projects)",
            "function OpexLogPortfolioRankWithTension(projects)",
        ):
            body = function_body(self.projects, signature)
            self.assertIn('"fundScore"', body)
            self.assertIn("OpexProjectFinanceCapital(p)", body)
            self.assertIn('" score=" + legacyScore', body)
            self.assertIn('" rank_score="', body)
            self.assertIn('" budget_score="', body)
            self.assertIn('" finance_capital="', body)

    def test_ib_schema_keeps_legacy_positions_and_has_b_suffix_on_both_paths(self):
        self.assertIn(
            '"IB|" + yy + "|" + this._projects.capitalBudget + "|"',
            self.task_projects,
        )
        self.assertIn(
            '+ this._projects.stats.selectedCapital + "|B" + batchBuilt',
            self.task_projects,
        )
        self.assertIn(
            '+ this._projects.stats.selectedCapital + "|B0"',
            self.scheduler,
        )
        self.assertRegex(
            self.parser,
            r'RE_IB\s*=\s*re\.compile\(r"\^IB\\\|',
        )
        match = re.search(r'RE_IB\s*=\s*re\.compile\(r"([^"]+)"\)', self.parser)
        self.assertIsNotNone(match)
        ib = re.compile(match.group(1))
        old = ib.fullmatch("IB|70|100000|250000")
        current = ib.fullmatch("IB|70|100000|250000|B1")
        self.assertIsNotNone(old)
        self.assertIsNone(old.group(4))
        self.assertIsNotNone(current)
        self.assertEqual(current.group(4), "1")
        self.assertIn('"selection_pool_capital": selection_pool_capital', self.parser)
        self.assertIn('"selected_capital": selection_pool_capital', self.parser)

    def test_knapsack_compatibility_slot_remains_false(self):
        self.assertGreaterEqual(self.projects.count("knapsackExact = false"), 3)
        self.assertIn("Aucun solveur knapsack/B&B n'existe", self.scheduler)


if __name__ == "__main__":
    unittest.main()
