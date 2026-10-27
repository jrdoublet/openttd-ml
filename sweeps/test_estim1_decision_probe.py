"""Contrats de la sonde passive ESTIM-1 sur le portefeuille 1973-1975."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1] / "ai" / "OpexAI"


class EstimDecisionProbeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.probe = (ROOT / "probes.nut").read_text(encoding="utf-8")
        cls.selection = (ROOT / "projects_selection.nut").read_text(encoding="utf-8")
        cls.dispatch = (ROOT / "task_projects.nut").read_text(encoding="utf-8")
        cls.settings = (ROOT / "settings.nut").read_text(encoding="utf-8")
        cls.info = (ROOT / "info.nut").read_text(encoding="utf-8")

    def test_opt_in_only_and_1973_to_1975(self):
        active = self.probe.split("function OpexEstimDTraceActive()", 1)[1].split("function ", 1)[0]
        self.assertIn("if (!DECISION_LOG) return false;", active)
        self.assertIn("yr >= 1973 && yr <= 1975", active)
        self.assertIn("DECISION_LOG = (probes & 508) != 0;", self.settings)
        self.assertRegex(self.info, r'name = "probes",(?s:.*?)easy_value = 2')
        self.assertIn("if (DECISION_LOG)\n    OpexEstimDTraceTopK(", self.selection)

    def test_topk_fields_and_volume_bound(self):
        top = self.probe.split("function OpexEstimDTraceTopK(", 1)[1].split("function ", 1)[0]
        for token in ("ESTIM_DTRACE_LAST_MONTH", "top_k=10", "i < 10",
                      '["air", "rail", "fleet"]', "n < top.len()"):
            self.assertIn(token, top)
        fields = self.probe.split("function OpexEstimDTraceProject(", 1)[1].split("function ", 1)[0]
        for token in ("mode=", "type=", "id=", "rank=", "dist=", "raw_r=",
                      "k_r=", " e=", " a=", " c_quote=", " c_score=",
                      " p=", " k_dec=", " score=", " finance=", " available=",
                      " reason="):
            self.assertIn(token, fields)

    def test_outcomes_and_spend(self):
        outcome = self.probe.split("function OpexEstimDTraceOutcome(", 1)[1].split("function ", 1)[0]
        for token in ("ESTIM_OUTCOME", "outcome=", "cash_before=", "cash_after=",
                      "paid_accounting=", "ESTIM_DTRACE_OUT_COUNT >= 60"):
            self.assertIn(token, outcome)
        for reason in ("already_built_in_pass", "mode_vehicle_limit",
                       "batch_plan_dead", "k_pass",
                       "c80_marginal_floor"):
            self.assertIn(reason, self.dispatch)
        self.assertNotIn("dtraceCost.GetCosts()", self.dispatch)
        self.assertNotIn("dtraceRailCosts.GetCosts()", self.dispatch)
        for name in ("task_air.nut", "task_rail.nut"):
            code = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn('OpexDecide("ESTIM_SPEND"', code)
            self.assertIn("actual_paid=", code)

    def test_not_in_estim_off_patch_hunks(self):
        from estim_unifie_off_lots import ESTIM_FILES, estim_off
        for name in ESTIM_FILES:
            source = (ROOT / name).read_text(encoding="utf-8")
            self.assertIsInstance(estim_off(name, source), str, name)


if __name__ == "__main__":
    unittest.main()
