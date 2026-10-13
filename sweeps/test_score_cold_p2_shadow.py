"""Tests for the off-by-default P2 selection trace and its exact rank replay."""
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "sweeps"))
from analyse_score_cold_p2 import audit_lines  # noqa: E402


def candidate(pass_id, ordinal, family, score, *, observed=False, source="none",
              engine=-1, tier=0, src=None):
    mode, kind, arm = family
    if src is None:
        src = ordinal
    return (f"[debug] SCORE_COLD_P2_CAND pass={pass_id} ordinal={ordinal} phase=main "
            f"mode={mode} kind={kind} arm={arm} src={src} dst=9 cargo=3 line=-1 engine={engine} "
            f"c77={tier} tier={tier} raw_profit=400 fund_profit=400 factor=1 observed={int(observed)} "
            f"c121_real=0 realization_factor=unknown v161_source={source} "
            f"finance=120 decision_finance=110 score_denom=200 budget_capital=125 "
            f"capital=100 budget=300 k_dec=200 bonus=0 score={score} "
            f"rank_score={score} revenue=500")


def head(pass_id, eligible, first, *, fallback=0, dedupe=0):
    mode, kind, arm = first
    return (f"[debug] SCORE_COLD_P2_HEAD pass={pass_id} year=1971 month=6 day=11 "
            f"budget=300 k_dec=200 floor=0 top_k=64 eligible={eligible} retained=2 "
            f"fallback={fallback} dedupe={dedupe} head_mode={mode} head_kind={kind} "
            f"head_arm={arm} head_src=1 head_dst=9 head_cargo=3 head_engine=-1 "
            f"head_line=-1 head_tier=0 head_score=500")


class ScoreColdP2Contract(unittest.TestCase):
    def test_default_off_and_runtime_guard(self):
        info = (ROOT / "ai/OpexAI/info.nut").read_text(encoding="utf-8")
        settings = (ROOT / "ai/OpexAI/settings.nut").read_text(encoding="utf-8")
        global_code = (ROOT / "ai/OpexAI/globals_pre.nut").read_text(encoding="utf-8")
        source = (ROOT / "ai/OpexAI/projects_selection.nut").read_text(encoding="utf-8")
        cfg = info.split('name = "score_cold_prior_shadow",', 1)[1].split("});", 1)[0]
        for difficulty in ("easy", "medium", "hard", "custom"):
            self.assertRegex(cfg, rf"\b{difficulty}_value\s*=\s*0\b")
        self.assertIn("SCORE_COLD_PRIOR_SHADOW <- false;", global_code)
        self.assertIn('SCORE_COLD_PRIOR_SHADOW = AIController.GetSetting("score_cold_prior_shadow") != 0;', settings)
        self.assertRegex(source, r"if \(SCORE_COLD_PRIOR_SHADOW && realSelection\s+&& AIDate.GetYear\(AIDate.GetCurrentDate\(\)\) <= 1971\)")
        self.assertIn('"main", capitalBudget, kDec, scoreDecisionFinanceCapital', source)
        self.assertIn('"fallback", capitalBudget, kDec, scoreDecisionFinanceCapital', source)
        self.assertEqual(source.count("if (coldPriorPass > 0) OpexScoreColdPriorTrace(project"), 2)
        self.assertTrue(source.index('if (coldPriorPass > 0) OpexScoreColdPriorTraceHead(')
                        > source.index("if (AIR_BATCH_TOWN_RESERVE) OpexAirBatchTownReserveCompact(affordable)"))

    def test_a_c77_equal_priority_head_flip_is_replayed(self):
        air = ("air", "pax", "newpair")
        rail = ("rail", "freight", "none")
        log = [candidate(4, 1, air, 500), candidate(4, 2, rail, 480), head(4, 2, air)]
        result = audit_lines(log, {"air:newpair": 0.8})
        self.assertEqual(result["counts"]["complete_passes"], 1)
        self.assertEqual(result["counts"]["head_flips"], 1)
        self.assertEqual(result["flips"][0]["after"], "rail:freight")

    def test_observed_profit_stays_exempt_and_incomplete_pass_is_rejected(self):
        air = ("air", "pax", "hubsite")
        rail = ("rail", "freight", "none")
        log = [candidate(1, 1, air, 500, observed=True),
               candidate(1, 2, rail, 480), head(1, 2, air),
               candidate(2, 1, air, 500), head(2, 2, air)]
        result = audit_lines(log, {"air:hubsite": 0.1})
        self.assertEqual(result["counts"].get("head_flips", 0), 0)
        self.assertEqual(result["counts"]["incomplete_passes"], 1)

    def test_deduplicated_pass_is_not_falsely_replayed(self):
        air = ("air", "pax", "newpair")
        rail = ("rail", "freight", "none")
        log = [candidate(2, 1, air, 500), candidate(2, 2, rail, 480),
               head(2, 2, air, dedupe=1)]
        result = audit_lines(log, {"air:newpair": 0.1})
        self.assertEqual(result["counts"]["deduplicated_unsupported"], 1)
        self.assertEqual(result["counts"].get("head_flips", 0), 0)

    def test_change_of_aircraft_on_same_od_is_not_a_useful_od_flip(self):
        air = ("air", "pax", "newpair")
        other = ("air", "pax", "hubsite")
        log = [candidate(1, 1, air, 500, src=1),
               candidate(1, 2, other, 490, src=1), head(1, 2, air)]
        # Different plan scoring, but same served origin/destination.
        result = audit_lines(log, {"air:newpair": 0.9})
        self.assertEqual(result["counts"]["head_flips"], 1)
        self.assertEqual(result["counts"]["same_service_head_changes"], 1)
        self.assertEqual(result["counts"].get("actionable_same_tier_od_flips", 0), 0)

    def test_replayed_head_priority_and_score_must_match_actual_head(self):
        air = ("air", "pax", "newpair")
        rail = ("rail", "freight", "none")
        log = [candidate(7, 1, air, 500), candidate(7, 2, rail, 480),
               head(7, 2, air).replace("head_tier=0", "head_tier=2")]
        result = audit_lines(log, {"air:newpair": 0.8})
        self.assertEqual(result["counts"], {"baseline_mismatch": 1})


if __name__ == "__main__":
    unittest.main()
