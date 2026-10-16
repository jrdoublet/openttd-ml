"""V218 : greffe biens→ville sur une ligne fret existante (défaut 0).

Phase 3 de la doctrine V106. Relance de V88 sans les trois défauts confirmés
(score gonflé, builtCount après simple lancement A*, arrêt de passe).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


class TestV218GoodsChain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {p.name: p.read_text(encoding="utf-8") for p in AI.glob("*.nut")}
        cls.candidates = cls.sources["candidates.nut"]
        cls.task_rail = cls.sources["task_rail.nut"]
        cls.info = cls.sources["info.nut"]
        m = re.search(
            r"function OpexV218GoodsGraftCandidates\(.*?\n\{(.*?)\n\}\n\n/\*",
            cls.candidates,
            re.S,
        )
        cls.graft_body = m.group(1) if m else ""
        m2 = re.search(
            r"function OpexAI::_v218PrepareGraft\(candidate, rank\)\n\{(.*?)\n\}\n",
            cls.task_rail,
            re.S,
        )
        cls.prepare_body = m2.group(1) if m2 else ""

    def test_setting_declared_inert(self):
        self.assertIn('name = "v218_goods_chain"', self.info)
        block = self.info[self.info.index('name = "v218_goods_chain"'):]
        block = block[:block.index("});")]
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        for level in ("easy_value", "medium_value", "hard_value", "custom_value"):
            self.assertIn(level + " = 0", block)

    def test_setting_read_once(self):
        self.assertIn("V218_GOODS_CHAIN <- false;", self.sources["globals_pre.nut"])
        self.assertEqual(
            sum(s.count('GetSetting("v218_goods_chain")') for s in self.sources.values()),
            1,
        )
        self.assertIn(
            'V218_GOODS_CHAIN = AIController.GetSetting("v218_goods_chain") != 0;',
            self.sources["settings.nut"],
        )

    def test_method_declared_in_main(self):
        self.assertIn("function _v218PrepareGraft(candidate, rank);", self.sources["main.nut"])

    def test_generation_gated_and_graft_only(self):
        self.assertIn("function OpexV218GoodsGraftCandidates(", self.candidates)
        self.assertIn("if (V218_GOODS_CHAIN) {", self.candidates)
        self.assertIn("OpexV218GoodsGraftCandidates(", self.candidates)
        self.assertTrue(self.graft_body)
        self.assertIn("isV218Graft <- true", self.graft_body)
        self.assertNotIn("isChain = true", self.graft_body)
        self.assertIn("joinPlatform <-", self.graft_body)
        self.assertIn("joinStationId <-", self.graft_body)
        self.assertIn("joinLineId <-", self.graft_body)
        self.assertIn('joinEnd <- "A"', self.graft_body)
        self.assertIn("TE_GOODS", self.graft_body)
        self.assertIn("isTransformer", self.graft_body)
        self.assertIn("OPEX_GOODS_CHAIN_OUTPUT_PER_INPUT", self.graft_body)
        self.assertIn("if (rankedTowns.len() > 3) rankedTowns.pop();", self.graft_body)

    def test_graft_not_two_step_chain(self):
        """La greffe n'emprunte pas le chemin isChain (étape 1 + finance gonflée)."""
        builders = self.sources["projects_builders.nut"]
        self.assertIn("V218 greffe", builders)
        self.assertIn("pas isChain", builders)
        self.assertNotIn("isV218Graft", builders.split("V88_CHAIN_STEP1_FINANCE")[1][:400])

    def test_prepare_never_returns_pending_as_built(self):
        self.assertTrue(self.prepare_body)
        self.assertIn('return "requested"', self.prepare_body)
        self.assertIn('return "ready"', self.prepare_body)
        self.assertIn('return "busy"', self.prepare_body)
        self.assertIn("_startRailSearch", self.prepare_body)
        self.assertIn("_startRailStockSearch", self.prepare_body)
        self.assertIn("_railReadyStock", self.prepare_body)
        self.assertNotIn('outcome = "pending"', self.prepare_body)
        self.assertNotIn("return true", self.prepare_body)

    def test_try_build_rejects_instead_of_pending(self):
        rail = self.task_rail
        start = rail.index("function OpexAI::_tryBuildRailProject")
        body = rail[start:rail.index("function OpexAI::_setActiveGoodsChain")]
        self.assertIn("this._v218PrepareGraft(candidate, i)", body)
        self.assertIn('reason = "v218_route_wait"', body)
        prepare_idx = body.index("this._v218PrepareGraft(candidate, i)")
        reject_idx = body.index('outcome = "rejected"', prepare_idx)
        pending_idx = body.index('outcome = "pending"')
        self.assertLess(prepare_idx, reject_idx)
        self.assertLess(prepare_idx, pending_idx)
        wait_return = body[prepare_idx:prepare_idx + 600]
        self.assertIn('outcome = "rejected"', wait_return)
        self.assertNotIn('outcome = "pending"', wait_return)

    def test_v88_step2_pending_false_under_v218(self):
        step2 = self.task_rail[
            self.task_rail.index("function OpexAI::_tryBuildGoodsChainStep2") :
        ]
        self.assertIn("if (V218_GOODS_CHAIN) return false;", step2)
        self.assertIn("if (start.pending)", step2)

    def test_score_uses_goods_step_only(self):
        self.assertNotIn("inputCandidate.capital + candGoods.capital", self.graft_body)
        self.assertNotIn("candInput.profitAnnual + candGoods.profitAnnual", self.graft_body)
        self.assertIn("isV218Graft <- true", self.graft_body)
        self.assertIn("OpexMakeCandidate(catalog, \"freight\", goodsCargo", self.graft_body)

    def test_logging_chain_chosen_step2_delivery(self):
        self.assertIn('OpexV88Log("CHAIN_CHOSEN"', self.task_rail)
        self.assertIn("v218=1 graft=1", self.task_rail)
        self.assertIn('OpexV88Log("CHAIN_STEP2"', self.task_rail)
        self.assertIn('OpexV88Log("CHAIN_STEP2_SEARCH"', self.task_rail)
        report = self.sources["task_report.nut"]
        self.assertIn("V88_GOODS_CHAIN || V218_GOODS_CHAIN", report)
        self.assertIn('OpexV88Log("CHAIN_DELIVERY"', report)

    def test_persist_no_new_state(self):
        persist = self.sources["persist.nut"]
        self.assertIn("V218 ne cree pas d'etat dedie", persist)
        self.assertNotIn("_v218", persist)
        self.assertIn("function OpexSaveGoodsChain(chain)", persist)

    def test_stock_worker_allows_town_dest(self):
        worker = self.task_rail[
            self.task_rail.index("function OpexAI::_tryStartRailStockWorker") :
        ]
        self.assertIn("V218_GOODS_CHAIN", worker)
        self.assertIn("dstTown", worker)
        self.assertIn("AITown.IsValidTown", worker)

    def test_default_hot_path_gated(self):
        call = "OpexV218GoodsGraftCandidates(catalog, lines, all"
        self.assertIn(call, self.candidates)
        preamble = self.candidates[:self.candidates.index(call)].rstrip()
        self.assertTrue(preamble.endswith("if (V218_GOODS_CHAIN) {"))
        self.assertIn("this._v218PrepareGraft(candidate, i)", self.task_rail)
        self.assertIn("if (V218_GOODS_CHAIN && candidate != null", self.task_rail)

    def test_no_squirrel_reserved_identifiers(self):
        for blob in (self.graft_body, self.prepare_body):
            self.assertNotRegex(blob, r"\bclone\b")
            self.assertNotRegex(blob, r"\bparent\b")
            self.assertNotRegex(blob, r"\bbase\b")
            self.assertNotRegex(blob, r"\bresume\b")


if __name__ == "__main__":
    unittest.main()
