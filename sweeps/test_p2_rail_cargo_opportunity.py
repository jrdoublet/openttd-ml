"""P2 opt-in rail cargo rank: independent threshold fixtures and source contracts.

These checks do not compile Squirrel or establish an economic gain. OpenTTD
smoke, Save/Load, exposure and causal build traces remain separate gates.
"""

import re
import unittest
from pathlib import Path

from campaign_freeze import parse_ai_settings
from n75_mc_legacy import historical_bytes, historical_info


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


def source(name):
    return (ROOT / name).read_text(encoding="utf-8")


def body(s, signature):
    start = s.index(signature)
    brace = s.index("{", start)
    depth = 0
    for end in range(brace, len(s)):
        if s[end] == "{":
            depth += 1
        elif s[end] == "}":
            depth -= 1
            if not depth:
                return s[start:end + 1]
    raise AssertionError("unterminated: " + signature)


def model_promotion(entries, *, ops=49999):
    """Independent one-neighbour rank truth table, not an emulated Squirrel VM."""
    chosen = None
    if ops >= 50000:
        return None
    for i in range(1, len(entries)):
        f, rival = entries[i], entries[i - 1]
        if not (f["mode"] == "rail" and f["kind"] == "freight"
                and f["ready"] and f["fresh"] and f["finance"] > 0
                and f["finance"] <= f["budget"] and f["tier"] == rival["tier"]
                and rival["mode"] in ("rail", "air") and rival["ready"]
                and rival["finance"] > 0 and rival["finance"] <= rival["budget"]
                and f["fund"] >= .93 * rival["fund"]
                and f["profit"] >= .80 * rival["profit"]
                and f["score"] <= rival["score"]
                and f["score"] * 1.08 > rival["score"]):
            continue
        if chosen is None or f["score"] > entries[chosen]["score"]:
            chosen = i
    return chosen


def item(mode="rail", kind="freight", *, score=94, fund=94,
         profit=90, ready=True, fresh=True, tier=0, finance=100, budget=200):
    return dict(mode=mode, kind=kind, score=score, fund=fund,
                profit=profit, ready=ready, fresh=fresh,
                tier=tier, finance=finance, budget=budget)


class TestP2RailCargoOpportunity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = source("info.nut")
        cls.settings = source("settings.nut")
        cls.globals = source("globals_pre.nut")
        cls.selection = source("projects_selection.nut")
        cls.rail = source("task_rail.nut")

    def test_setting_defaults_and_exactly_one_getter(self):
        settings = parse_ai_settings(ROOT / "info.nut")
        self.assertIn("rail_cargo_opportunity_rank", settings)
        decl = re.search(r'AddSetting\(\{ name = "rail_cargo_opportunity_rank",(.*?)\}\);',
                         self.info, flags=re.S).group(1)
        self.assertIn("min_value = 0, max_value = 2", decl)
        for level in ("easy", "medium", "hard", "custom"):
            self.assertRegex(decl, rf"{level}_value\s*=\s*0\b")
        self.assertEqual(self.settings.count('GetSetting("rail_cargo_opportunity_rank")'), 1)
        self.assertIn("P2_RAIL_CARGO_OPPORTUNITY_RANK <- 0;", self.globals)
        self.assertIn("P2_OPPORTUNITY_STAMP <- 0;", self.globals)
        self.assertIn("P2_OPPORTUNITY_STAMP = 0;", self.settings)

    def test_historical_inventory_not_rebased(self):
        self.assertEqual(historical_info(self.info).count("AddSetting("), 58)
        for name in ("info.nut", "settings.nut"):
            original = (ROOT / name).read_bytes()
            self.assertNotIn(b"rail_cargo_opportunity_rank", historical_bytes(name, original))

    def test_off_path_and_shadow_do_not_reorder_or_write_cache(self):
        select = body(self.selection, "function OpexProjectSelectAffordable(")
        self.assertIn("if (realSelection && P2_RAIL_CARGO_OPPORTUNITY_RANK > 0)", select)
        self.assertIn("return affordable;", select)
        topk = body(self.selection, "function OpexP2OpportunityTopK(")
        self.assertIn("if (mode == 2) P2_OPPORTUNITY_STAMP++", topk)
        self.assertIn("chosenIndex >= 0 && mode == 2 && spent < 50000", topk)
        self.assertNotIn('rawset("_bs', topk)
        self.assertNotIn("OpexProjectInsertDefensive(", topk)
        self.assertNotIn("OpexRailPrepMergeAlternatives(", topk)
        self.assertNotIn("OpexQuoteRailCapital(", topk)

    def test_ready_plan_and_finance_requirements_fail_closed(self):
        rail = body(self.selection, "function OpexP2PreparedRailQuote(")
        for invariant in ('project.economicsDate != AIDate.GetCurrentDate()',
                          'plan.ok != true', 'plan.tiles.len() < 2',
                          'project.capital != plan.capital',
                          'finance > capitalBudget', 'OpexCandidateIsAbandoned('):
            self.assertIn(invariant, rail)
        self.assertNotIn("OpexQuoteRailCapital(", rail)
        rival = body(self.selection, "function OpexP2OpportunityRival(")
        self.assertIn("project.mode != \"air\"", rival)
        self.assertIn("plan.decisionEconomics.profitAnnual != project.profitAnnual", rival)

    def test_one_neighbour_valid_promotion_and_thresholds(self):
        rival = item(mode="air", kind="pax", score=100, fund=100, profit=100)
        self.assertEqual(model_promotion([rival, item()]), 1)
        self.assertIsNone(model_promotion([rival, item(fund=92)]))
        self.assertIsNone(model_promotion([rival, item(profit=79)]))
        self.assertIsNone(model_promotion([rival, item(score=92)]))
        self.assertEqual(model_promotion([rival, item(score=100, fund=100)]), 1)
        self.assertIsNone(model_promotion([rival, item()], ops=50000))
        self.assertIsNone(model_promotion([rival, item()], ops=50001))

    def test_tier_budget_stale_plan_and_no_rank0_effect_from_deep_swap(self):
        rival = item(mode="air", kind="pax", score=100, fund=100, profit=100)
        for loser in (item(tier=2), item(finance=201), item(ready=False),
                      item(fresh=False)):
            self.assertIsNone(model_promotion([rival, loser]))
        # A swap at index 2 can change the tail, but never the immediate head.
        head = item(mode="air", kind="pax", score=150, fund=150, profit=120)
        self.assertEqual(model_promotion([head, rival, item()]), 2)

    def test_c77_and_scores_are_not_mutated_by_p2(self):
        topk = body(self.selection, "function OpexP2OpportunityTopK(")
        self.assertIn("OpexProjectDefensiveAirPriority(rival) != OpexProjectDefensiveAirPriority(freight)", topk)
        self.assertIn("freight.fundScore < rival.fundScore * 0.93", topk)
        self.assertIn("freight.profitAnnual < rival.profitAnnual * 0.80", topk)
        self.assertIn("freightScore * 1.08 <= rivalScore", topk)
        self.assertIn("affordable[chosenIndex - 1] = affordable[chosenIndex]", topk)
        self.assertNotIn("fundScore <-", topk)
        self.assertNotIn("fundScore =", topk)

    def test_provenance_traces_prepared_path_and_build(self):
        topk = body(self.selection, "function OpexP2OpportunityTopK(")
        self.assertIn('rawset("p2OpportunityKey",', topk)
        self.assertIn('rawset("p2OpportunityStamp",', topk)
        self.assertIn('OpexDecide("P2_OPPORTUNITY"', topk)
        trace = body(self.rail, "function OpexP2RailTraceKey(")
        self.assertIn("P2_RAIL_CARGO_OPPORTUNITY_RANK != 2", trace)
        self.assertIn("candidate.p2OpportunityStamp != P2_OPPORTUNITY_STAMP", trace)
        self.assertIn("p2_key=", trace)
        selected = body(self.rail, "function OpexAI::_tryBuildRailProject(")
        self.assertIn("local i = rank;", selected)
        self.assertIn("DECISION_LOG && P2_RAIL_CARGO_OPPORTUNITY_RANK == 2", selected)
        self.assertIn('OpexDecide("PROJECT_CHOSEN"', self.rail)
        self.assertIn('OpexDecide("RAIL_ATTEMPT"', self.rail)
        self.assertIn('OpexDecide("RAIL_BUILD"', self.rail)
        # Conserver le schema de RAIL_BUILD historique pour le bras OFF.
        self.assertIn('" cargo=" + cargoStr + " dist=" + candidate.distance', self.rail)
        self.assertNotIn('" cargo=" + cargoStr + " kind="', self.rail)
        self.assertIn('" phases=" + phasesStr + p2Trace', self.rail)
        self.assertIn('" pred_revenue2=" + candidate.revenue2 : "") + p2Trace', self.rail)
        self.assertNotIn("P2_OPPORTUNITY_STAMP", source("persist.nut"))


if __name__ == "__main__":
    unittest.main()
