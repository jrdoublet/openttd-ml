#!/usr/bin/env python3
"""Contrats source V279 : re-sélection incrémentale exacte d'OpexReselectProjects.

Vérifications statiques :
1. Déclaration du réglage entier v279_reselect_memo dans info.nut (0..2, défaut 0, 4 *_value à 0).
2. Lecture du réglage dans settings.nut vers la globale V279_RESELECT_MEMO.
3. Déclaration des globales V279_RESELECT_MEMO, OPEX_LINES_REVISION, OPEX_AIR_SITE_EPOCH dans globals_pre.nut.
4. Intégrité du chemin 0 : code historique exécuté à l'identique au caractère près hors condition.
5. Mode contrôle (2) : calcul des deux chemins, comparaison complète (best, fundScore, capitalRemaining, stats)
   et retour du résultat historique intact, avec signalement V279_CHECK via OpexDecide et AILog.Warning.
6. Incrémentation de la révision des lignes OPEX_LINES_REVISION à chaque mutation repérée de _lines.
7. Incrémentation de l'époque des sites OPEX_AIR_SITE_EPOCH à chaque invalidation de cache de sites.
8. Présence de la mémoïsation du filtre AIR (OpexFilterAirAlternativesV279Memo) et du scoring (OpexProjectSelectAffordableMemoized).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AI = ROOT / "ai" / "OpexAI"


def _read(name: str) -> str:
    return (AI / name).read_text(encoding="utf-8")


def _function_body(source: str, signature: str) -> str:
    start = source.index(signature)
    nxt = source.find("\nfunction ", start + 1)
    if nxt < 0:
        nxt = len(source)
    return source[start:nxt]


class TestV279ReselectMemo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.info = _read("info.nut")
        cls.settings = _read("settings.nut")
        cls.globals_pre = _read("globals_pre.nut")
        cls.selection = _read("projects_selection.nut")
        cls.air_coverage = _read("air_coverage.nut")
        cls.main = _read("main.nut")
        cls.persist = _read("persist.nut")
        cls.task_air = _read("task_air.nut")
        cls.task_rail = _read("task_rail.nut")
        cls.task_road = _read("task_road.nut")
        cls.task_water = _read("task_water.nut")
        cls.task_report = _read("task_report.nut")

    def test_setting_declaration(self):
        self.assertIn('name = "v279_reselect_memo"', self.info)
        match = re.search(
            r'AddSetting\(\{\s*name\s*=\s*"v279_reselect_memo"[^}]+\}\);',
            self.info,
            re.S,
        )
        self.assertIsNotNone(match, "Bloc AddSetting v279_reselect_memo introuvable dans info.nut")
        block = match.group(0)
        self.assertIn("min_value = 0", block)
        self.assertIn("max_value = 2", block)
        self.assertIn("easy_value = 0", block)
        self.assertIn("medium_value = 0", block)
        self.assertIn("hard_value = 0", block)
        self.assertIn("custom_value = 0", block)
        self.assertIn("flags = 0", block)

    def test_setting_load(self):
        self.assertIn('V279_RESELECT_MEMO = AIController.GetSetting("v279_reselect_memo");', self.settings)

    def test_globals_declared(self):
        self.assertIn("V279_RESELECT_MEMO <- 0;", self.globals_pre)
        self.assertIn("OPEX_LINES_REVISION <- 0;", self.globals_pre)
        self.assertIn("OPEX_AIR_SITE_EPOCH <- 0;", self.globals_pre)
        self.assertIn("V279_FILTER_STAMP_ID <- 0;", self.globals_pre)
        self.assertIn("V279_LAST_MONTH <- -1;", self.globals_pre)
        self.assertIn("V279_LAST_LINES_REV <- -1;", self.globals_pre)
        self.assertIn("V279_LAST_SITE_EPOCH <- -1;", self.globals_pre)
        self.assertIn("V279_LAST_ABND_COUNT <- -1;", self.globals_pre)
        self.assertIn("V279_LAST_HAS_LINES <- null;", self.globals_pre)

    def test_path_0_intact(self):
        reselect = _function_body(self.selection, "function OpexReselectProjects(")
        self.assertIn("if (!forceHistoric) {", reselect)
        self.assertIn("if (V279_RESELECT_MEMO == 1) {", reselect)
        self.assertIn("return OpexV279ReselectProjectsMemoized(", reselect)
        self.assertIn("if (V279_RESELECT_MEMO == 2) {", reselect)
        self.assertIn("return OpexV279ReselectProjectsControl(", reselect)
        # Vérifier que le corps historique suit immédiatement sans altération
        self.assertIn("projects.selectionStale = false;", reselect)
        self.assertIn("OpexFilterAirAlternativesStillValid(alternatives, abandonedPairs, lines);", reselect)
        self.assertIn("funded = OpexProjectSelectAffordable(alternatives, capitalBudget, PROJECT_TOP_K);", reselect)

    def test_control_mode_behavior(self):
        control = _function_body(self.selection, "function OpexV279ReselectProjectsControl(")
        # 1. Sauvegarde d'état mutable
        self.assertIn("savedScores", control)
        self.assertIn("savedCatalogScores", control)
        self.assertIn("origBisectStamp", control)
        # 2. Exécution mémoïsée
        self.assertIn("OpexV279ReselectProjectsMemoized(projects, capitalBudget, abandonedPairs, lines, railReadyStock);", control)
        # 3. Restauration d'état
        self.assertIn("p.fundScore = savedScores[p];", control)
        self.assertIn("delete p.fundScore;", control)
        self.assertIn("entry.lastScore = savedCatalogScores[k];", control)
        self.assertIn("SELECT_BISECT_STAMP = origBisectStamp;", control)
        # 4. Exécution historique
        self.assertIn("OpexReselectProjects(projects, capitalBudget, abandonedPairs, lines, railReadyStock, true);", control)
        # 5. Comparaisons exigées
        self.assertIn("best_len", control)
        self.assertIn("best_order", control)
        self.assertIn("fund_score", control)
        self.assertIn("capital_remaining", control)
        self.assertIn("selected_capital", control)
        self.assertIn("selected_revenue", control)
        self.assertIn("next_project_capital", control)
        # 6. Journalisation en cas de divergence
        self.assertIn('OpexDecide("V279_CHECK", diffMsg);', control)
        self.assertIn('AILog.Warning("V279_CHECK " + diffMsg);', control)
        # 7. Retour du résultat historique
        self.assertIn("return projects;", control)

    def test_lines_revision_increments_at_all_mutations(self):
        # 7 sites de mutation identifiés
        # 1. main.nut (Constructor: this._lines = [])
        self.assertIn("this._lines = [];\n    if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.main)
        # 2. persist.nut (Load: this._lines = liveLines)
        self.assertIn("this._lines = liveLines;\n  if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.persist)
        # 3. task_air.nut (air line append)
        self.assertIn("this._lines.append({\n", self.task_air)
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.task_air)
        # 4. task_rail.nut (rail line append)
        self.assertIn("this._lines.append({\n", self.task_rail)
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.task_rail)
        # 5. task_road.nut (road line append)
        self.assertIn("this._lines.append({\n", self.task_road)
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.task_road)
        # 6. task_water.nut (water line append)
        self.assertIn("this._lines.append({\n", self.task_water)
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.task_water)
        # 7. task_report.nut (scrap line remove)
        self.assertIn("if (toRemove.len() > 0 && V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.task_report)

    def test_site_epoch_increments_at_all_invalidations(self):
        # 1. air_coverage.nut: OpexAirResetSiteCache
        reset_body = _function_body(self.air_coverage, "function OpexAirResetSiteCache(")
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_AIR_SITE_EPOCH++;", reset_body)
        # 2. air_coverage.nut: OpexAir0310InvalidateSiteValidity
        inval_body = _function_body(self.air_coverage, "function OpexAir0310InvalidateSiteValidity(")
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_AIR_SITE_EPOCH++;", inval_body)
        # 3. air_coverage.nut: OpexAirInvalidateCachedSite
        cached_body = _function_body(self.air_coverage, "function OpexAirInvalidateCachedSite(")
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_AIR_SITE_EPOCH++;", cached_body)

    def test_filter_memo_logic(self):
        memo_filt = _function_body(self.selection, "function OpexFilterAirAlternativesV279Memo(")
        self.assertIn("OpexAir0310SiteValidityMonth()", memo_filt)
        self.assertIn("OPEX_LINES_REVISION", memo_filt)
        self.assertIn("OPEX_AIR_SITE_EPOCH", memo_filt)
        self.assertIn("abandonedPairs.len()", memo_filt)
        self.assertIn("V279_FILTER_STAMP_ID++", memo_filt)
        self.assertIn('project.rawset("_v279Stamp", V279_FILTER_STAMP_ID);', memo_filt)
        self.assertIn('project.rawset("_v279Live", isLive);', memo_filt)
        self.assertIn("OpexAirBatchPlanStillLive(plan, lines)", memo_filt)
        self.assertIn("OpexAir0310SiteValidityOk(", memo_filt)

    def test_scoring_memo_logic(self):
        memo_score = _function_body(self.selection, "function OpexProjectSelectAffordableMemoized(")
        self.assertIn('_v279FinCap', memo_score)
        self.assertIn('_v279DecCap', memo_score)
        self.assertIn('_v279FundProfit', memo_score)
        self.assertIn("OpexProjectFitFleetToBudget(project, capitalBudget)", memo_score)
        self.assertIn("OpexProjectRefreshEarlySlot(project, earlySlotState)", memo_score)
        self.assertIn("OpexProjectRefreshDefensiveSlot(project, defensiveSlotState)", memo_score)
        self.assertIn("OpexProjectInsertDefensive(affordable, project, scoreKey, limit, true)", memo_score)


if __name__ == "__main__":
    unittest.main()
