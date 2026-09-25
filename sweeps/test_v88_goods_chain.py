"""Tests de contrat pour la variante V88 (chaînes industrielles complètes de biens)."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class V88GoodsChainContractTest(unittest.TestCase):
    def test_settings_contract(self):
        """Vérifie la déclaration du réglage v88_goods_chain, son repli et son chargement."""
        info = _read("ai/OpexAI/info.nut")
        self.assertIn('name = "v88_goods_chain"', info)
        block = info[info.index('name = "v88_goods_chain"'):]
        block = block[:block.index("});")]
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("custom_value = 0", block)

        globals_pre = _read("ai/OpexAI/globals_pre.nut")
        self.assertIn("V88_GOODS_CHAIN <- false;", globals_pre)

        settings = _read("ai/OpexAI/settings.nut")
        self.assertIn('V88_GOODS_CHAIN = AIController.GetSetting("v88_goods_chain") != 0;', settings)

    def test_conversion_constant_and_downstream_valuation(self):
        """Vérifie la constante de conversion nommée sans nombre magique et son usage dans candidates.nut."""
        main_nut = _read("ai/OpexAI/main.nut")
        self.assertIn("const OPEX_GOODS_CHAIN_OUTPUT_PER_INPUT = 1.0;", main_nut)

        candidates = _read("ai/OpexAI/candidates.nut")
        self.assertIn("function OpexGoodsChainCandidates(", candidates)
        self.assertIn("OPEX_GOODS_CHAIN_OUTPUT_PER_INPUT", candidates)
        self.assertIn("AICargo.TE_GOODS", candidates)
        self.assertIn("isTransformer", candidates)

        # Vérifie la formule de production mensuelle aval basée sur l'intrant livré
        self.assertIn("(candInput.carried * OPEX_GOODS_CHAIN_OUTPUT_PER_INPUT).tointeger()", candidates)

        # Agrégation du profit et capital d'ensemble de la chaîne
        self.assertIn("local totalProfit = candInput.profitAnnual + candGoods.profitAnnual;", candidates)
        self.assertIn("local totalCapital = candInput.capital + candGoods.capital;", candidates)
        self.assertIn("isChain = true", candidates)

        # Vérifie l'activation sous le drapeau V88_GOODS_CHAIN
        self.assertIn("if (V88_GOODS_CHAIN)", candidates)

    def test_abandon_key_format(self):
        """Vérifie le format des clés d'abandon pour la chaîne et le préfixe 't' pour la ville acceptatrice."""
        lines = _read("ai/OpexAI/lines.nut")
        self.assertIn("function OpexAbandonedPairKey(candidate)", lines)
        key_start = lines.index("function OpexAbandonedPairKey(candidate)")
        key_body = lines[key_start:key_start + 1200]

        # Clé pour ville : '|t' + townId
        self.assertIn('"|t" + candidate.dstTown', key_body)
        self.assertIn('"t" + candidate.dstTown', lines)

        # projects.nut key
        projects = _read("ai/OpexAI/projects.nut")
        self.assertIn('"chain|" + project.payload.inputCargo', projects)
        self.assertIn('+ project.payload.factoryId + "|t" + project.payload.dstTown', projects)

    def test_joined_station_contract(self):
        """Vérifie le quai joint à l'usine et l'exemption de collision _tooClose."""
        lines = _read("ai/OpexAI/lines.nut")
        self.assertIn("joinLineId", lines)

        builder = _read("ai/OpexAI/builder_rail.nut")
        self.assertIn("joinPlatform", builder)
        self.assertIn("joinStationId", builder)
        self.assertIn("OpexJoinPlatformPlans", builder)

    def test_persistence_contract(self):
        """Vérifie la sérialisation sans floats, Save/Load et réconciliation de la chaîne."""
        persist = _read("ai/OpexAI/persist.nut")
        self.assertIn("function OpexSaveGoodsChain(chain)", persist)
        self.assertIn("function OpexLoadGoodsChain(data, catalog = null)", persist)

        save_start = persist.index("function OpexSaveGoodsChain(chain)")
        save_body = persist[save_start:save_start + 2200]
        # Tous les calculs sont convertis en entiers (.tointeger()), aucun float stocké
        self.assertIn(".tointeger()", save_body)
        self.assertNotIn(".tofloat()", save_body)

        # Présence dans Save (court et long)
        self.assertIn("activeGoodsChain", persist)
        self.assertIn("OpexSaveGoodsChain(this._activeGoodsChain)", persist)

        # Présence dans Load
        self.assertIn("this._activeGoodsChain = OpexLoadGoodsChain(data.activeGoodsChain, this._catalog);", persist)

        # Réconciliation dans _reconcileAfterLoad
        reconcile_start = persist.index("function OpexAI::_reconcileAfterLoad()")
        reconcile_body = persist[reconcile_start:]
        self.assertIn("this._activeGoodsChain != null", reconcile_body)
        self.assertIn("AIIndustry.IsValidIndustry(this._activeGoodsChain.factoryId)", reconcile_body)
        self.assertIn("AITown.IsValidTown(this._activeGoodsChain.townId)", reconcile_body)
        self.assertIn("AIStation.IsValidStation(this._activeGoodsChain.factoryStationId)", reconcile_body)

    def test_two_step_construction_and_instrumentation(self):
        """Vérifie la construction en 2 étapes et les sondes OpexSign/OpexDecide (longueur <= 31)."""
        main_nut = _read("ai/OpexAI/main.nut")
        self.assertIn("_activeGoodsChain = null;", main_nut)
        self.assertIn("function _tryBuildGoodsChainStep2(year, passDiscards, anchor, yy);", main_nut)

        task_rail = _read("ai/OpexAI/task_rail.nut")
        self.assertIn("function OpexAI::_tryBuildGoodsChainStep2(year, passDiscards, anchor, yy)", task_rail)
        self.assertIn("isChainStep1", task_rail)
        self.assertIn("isChainStep2", task_rail)

        # Reprise de l'étape 2 dans task_projects.nut
        task_proj = _read("ai/OpexAI/task_projects.nut")
        self.assertIn("this._activeGoodsChain != null && this._activeGoodsChain.step == 2", task_proj)
        self.assertIn("this._tryBuildGoodsChainStep2(year, passDiscards, anchor, yy)", task_proj)

        # Sondes OpexSign <= 31 caractères
        self.assertIn('"C1|" + yy + "|" + inputLine.lineId + "|" + candidate.factoryId', task_rail)
        self.assertIn('"C2|" + yy + "|" + goodsLine.lineId + "|" + chain.townId', task_rail)
        self.assertIn('"CF|" + yy + "|', task_rail)

        # Sondes OpexDecide et OpexV88Log
        self.assertIn('OpexV88Log("CHAIN_STEP1"', task_rail)
        self.assertIn('OpexV88Log("CHAIN_STEP2"', task_rail)
        self.assertIn('OpexV88Log("CHAIN_FAIL"', task_rail)

    def test_v88_step2_plan_immediate_contract(self):
        """Vérifie la déclaration et l'effet du réglage v88_step2_plan_immediate."""
        info = _read("ai/OpexAI/info.nut")
        self.assertIn('name = "v88_step2_plan_immediate"', info)
        block = info[info.index('name = "v88_step2_plan_immediate"'):]
        block = block[:block.index("});")]
        self.assertIn("flags = AICONFIG_BOOLEAN", block)
        self.assertIn("custom_value = 0", block)

        globals_pre = _read("ai/OpexAI/globals_pre.nut")
        self.assertIn("V88_STEP2_PLAN_IMMEDIATE <- false;", globals_pre)

        settings = _read("ai/OpexAI/settings.nut")
        self.assertIn('V88_STEP2_PLAN_IMMEDIATE = V88_GOODS_CHAIN && (AIController.GetSetting("v88_step2_plan_immediate") != 0);', settings)

        task_proj = _read("ai/OpexAI/task_projects.nut")
        self.assertIn("V88_STEP2_PLAN_IMMEDIATE", task_proj)
        self.assertIn("step2CanRun", task_proj)

    def test_trace_timestamps_contract(self):
        """Vérifie la présence de tous les horodatages sous OpexV88Log (décision, recherche, mise en service, livraison)."""
        task_rail = _read("ai/OpexAI/task_rail.nut")
        self.assertIn('OpexV88Log("CHAIN_CHOSEN"', task_rail)
        self.assertIn('OpexV88Log("CHAIN_STEP1_SEARCH"', task_rail)
        self.assertIn('OpexV88Log("CHAIN_SEARCH_END"', task_rail)
        self.assertIn('OpexV88Log("CHAIN_STEP1"', task_rail)
        self.assertIn('OpexV88Log("CHAIN_STEP2_SEARCH"', task_rail)
        self.assertIn('OpexV88Log("CHAIN_STEP2"', task_rail)

        task_report = _read("ai/OpexAI/task_report.nut")
        self.assertIn('OpexV88Log("CHAIN_DELIVERY"', task_report)
        self.assertIn("AICargo.TE_GOODS", task_report)


if __name__ == "__main__":
    unittest.main()
