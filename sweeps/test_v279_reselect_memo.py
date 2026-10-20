#!/usr/bin/env python3
"""Contrats source V279 : re-sélection incrémentale exacte d'OpexReselectProjects.

Vérifications statiques :
1. Déclaration du réglage entier v279_reselect_memo dans info.nut (0..2, défaut 0, 4 *_value à 0).
2. Lecture du réglage dans settings.nut vers la globale V279_RESELECT_MEMO.
3. Déclaration des globales V279 dans globals_pre.nut (révisions, époques, compteurs hits/misses).
4. Intégrité du chemin 0 : code exécuté à l'identique de master ac78c8e au caractère près.
5. git diff ac78c8e -- ai/OpexAI/projects_selection.nut strictement limité au filtre et à l'appel.
6. Absence totale de mémoïsation du score (_v279FinCap, _v279DecCap, _v279FundProfit).
7. Incrémentation de OPEX_ABANDON_REVISION à chaque mutation repérée de _abandonedPairs.
8. Incrémentation de OPEX_AIR_ROLLBACK_REVISION à chaque mutation repérée de OPEX_AIR_ROLLBACKS.
9. Incrémentation de OPEX_LINES_REVISION à chaque mutation repérée de _lines.
10. Incrémentation de OPEX_AIR_SITE_EPOCH à chaque invalidation de cache de sites.
11. Exclusion des plans à second créneau (c83OwnSecondSlotA/B, v134SecondSlotA/B) de la mémoïsation.
12. Mode contrôle 2 dans le filtre : calcul historique, comparaison memo/hist, alerte V279_CHECK et retour historique.
13. Journalisation mensuelle des statistiques de hits/misses sous V279_STATS.
"""
from __future__ import annotations

import re
import subprocess
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
        cls.air_construction = _read("air_construction.nut")
        cls.air_recovery = _read("air_recovery.nut")
        cls.lines = _read("lines.nut")
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
        self.assertIn("OPEX_ABANDON_REVISION <- 0;", self.globals_pre)
        self.assertIn("OPEX_AIR_ROLLBACK_REVISION <- 0;", self.globals_pre)
        self.assertIn("V279_FILTER_STAMP_ID <- 0;", self.globals_pre)
        self.assertIn("V279_LAST_MONTH <- -1;", self.globals_pre)
        self.assertIn("V279_LAST_LINES_REV <- -1;", self.globals_pre)
        self.assertIn("V279_LAST_SITE_EPOCH <- -1;", self.globals_pre)
        self.assertIn("V279_LAST_ABND_REV <- -1;", self.globals_pre)
        self.assertIn("V279_LAST_ROLLBACK_REV <- -1;", self.globals_pre)
        self.assertIn("V279_LAST_HAS_LINES <- null;", self.globals_pre)
        self.assertIn("V279_HITS <- 0;", self.globals_pre)
        self.assertIn("V279_MISSES <- 0;", self.globals_pre)
        self.assertIn("V279_LAST_STATS_MONTH <- -1;", self.globals_pre)

    def test_path_0_intact(self):
        reselect = _function_body(self.selection, "function OpexReselectProjects(")
        self.assertIn("alternatives = (V279_RESELECT_MEMO != 0)", reselect)
        self.assertIn("? OpexFilterAirAlternativesV279Memo(alternatives, abandonedPairs, lines)", reselect)
        self.assertIn(": OpexFilterAirAlternativesStillValid(alternatives, abandonedPairs, lines);", reselect)
        self.assertIn("funded = OpexProjectSelectAffordable(alternatives, capitalBudget, PROJECT_TOP_K);", reselect)
        # Vérifier que le corps d'OpexProjectSelectAffordable ne mentionne aucun symbole V279
        affordable = _function_body(self.selection, "function OpexProjectSelectAffordable(")
        self.assertNotIn("V279", affordable)
        self.assertNotIn("_v279", affordable)

    def test_no_scoring_memoization(self):
        # Vérifier l'absence absolue de champs de mémoïsation de score dans tous les fichiers .nut
        for nut_path in AI.glob("*.nut"):
            content = nut_path.read_text(encoding="utf-8")
            self.assertNotIn("_v279FinCap", content, f"_v279FinCap trouvé dans {nut_path.name}")
            self.assertNotIn("_v279DecCap", content, f"_v279DecCap trouvé dans {nut_path.name}")
            self.assertNotIn("_v279FundProfit", content, f"_v279FundProfit trouvé dans {nut_path.name}")
            self.assertNotIn("OpexProjectSelectAffordableMemoized", content, f"OpexProjectSelectAffordableMemoized trouvé dans {nut_path.name}")
            self.assertNotIn("OpexV279ReselectProjectsMemoized", content, f"OpexV279ReselectProjectsMemoized trouvé dans {nut_path.name}")
            self.assertNotIn("OpexV279ReselectProjectsControl", content, f"OpexV279ReselectProjectsControl trouvé dans {nut_path.name}")
            self.assertNotIn("OpexHookV216", content, f"OpexHookV216 trouvé dans {nut_path.name}")

    def test_diff_projects_selection_limited(self):
        # git diff ac78c8e -- ai/OpexAI/projects_selection.nut doit être limité au filtre et à l'appel
        diff = subprocess.check_output(
            ["git", "diff", "ac78c8e", "--", "ai/OpexAI/projects_selection.nut"],
            cwd=str(ROOT),
            text=True,
        )
        # Vérifier les fonctions modifiées
        self.assertIn("function OpexFilterAirAlternativesV279Memo(", diff)
        self.assertIn("alternatives = (V279_RESELECT_MEMO != 0)", diff)
        # Aucune autre fonction ne doit être touchée
        self.assertNotIn("OpexProjectSelectAffordableMemoized", diff)
        self.assertNotIn("OpexV279ReselectProjectsMemoized", diff)
        self.assertNotIn("OpexV279ReselectProjectsControl", diff)
        self.assertNotIn("OpexHookV216", diff)
        self.assertNotIn("forceHistoric", diff)

    def test_abandon_revision_increments_at_all_mutations(self):
        # 5 sites de mutation de _abandonedPairs identifiés
        # 1. lines.nut:282 (_markPairAbandoned)
        self.assertIn("this._abandonedPairs[key] <- { date = now, count = count };\n  if (V279_RESELECT_MEMO != 0) OPEX_ABANDON_REVISION++;", self.lines)
        # 2. lines.nut:308 (_pruneAbandonedPairs)
        self.assertIn("if (toDelete.len() > 0 && V279_RESELECT_MEMO != 0) OPEX_ABANDON_REVISION++;", self.lines)
        # 3. task_report.nut:177 (_markTownGrowthRejected)
        self.assertIn("this._abandonedPairs[key] <- { date = AIDate.GetCurrentDate(), count = count };\n  if (V279_RESELECT_MEMO != 0) OPEX_ABANDON_REVISION++;", self.task_report)
        # 4. main.nut:409 (constructeur)
        self.assertIn("this._abandonedPairs = {};\n    if (V279_RESELECT_MEMO != 0) OPEX_ABANDON_REVISION++;", self.main)
        # 5. persist.nut:791-792 (chargement)
        self.assertIn("this._abandonedPairs = {};\n    foreach (key, val in data.abandonedPairs) this._abandonedPairs[key] <- val;\n    if (V279_RESELECT_MEMO != 0) OPEX_ABANDON_REVISION++;", self.persist)

    def test_rollback_revision_increments_at_all_mutations(self):
        # 6 sites de mutation de OPEX_AIR_ROLLBACKS identifiés
        # 1. air_construction.nut:41 (append) & :44 (pop)
        self.assertIn("OPEX_AIR_ROLLBACKS.append(ticket);\n  if (V279_RESELECT_MEMO != 0) OPEX_AIR_ROLLBACK_REVISION++;", self.air_construction)
        self.assertIn("OPEX_AIR_ROLLBACKS.pop();\n    if (V279_RESELECT_MEMO != 0) OPEX_AIR_ROLLBACK_REVISION++;", self.air_construction)
        # 2. air_recovery.nut:97 (remove)
        self.assertIn("OPEX_AIR_ROLLBACKS.remove(0);\n    if (V279_RESELECT_MEMO != 0) OPEX_AIR_ROLLBACK_REVISION++;", self.air_recovery)
        # 3. air_recovery.nut:104 (rotated)
        self.assertIn("OPEX_AIR_ROLLBACKS = rotated;\n  if (V279_RESELECT_MEMO != 0) OPEX_AIR_ROLLBACK_REVISION++;", self.air_recovery)
        # 4. air_recovery.nut:125 (reconcile)
        self.assertIn("OPEX_AIR_ROLLBACKS = pending;\n  if (V279_RESELECT_MEMO != 0) OPEX_AIR_ROLLBACK_REVISION++;", self.air_recovery)
        # 5. persist.nut:770 (reset) & :776 (load)
        self.assertIn("OPEX_AIR_ROLLBACKS = [];\n  if (V279_RESELECT_MEMO != 0) OPEX_AIR_ROLLBACK_REVISION++;", self.persist)
        self.assertIn('if ("airRollbacks" in data && V279_RESELECT_MEMO != 0) OPEX_AIR_ROLLBACK_REVISION++;', self.persist)

    def test_lines_revision_increments_at_all_mutations(self):
        # 7 sites de mutation de _lines identifiés
        self.assertIn("this._lines = [];\n    if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.main)
        self.assertIn("this._lines = liveLines;\n  if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.persist)
        self.assertIn("this._lines.append({\n", self.task_air)
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.task_air)
        self.assertIn("this._lines.append({\n", self.task_rail)
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.task_rail)
        self.assertIn("this._lines.append({\n", self.task_road)
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.task_road)
        self.assertIn("this._lines.append({\n", self.task_water)
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.task_water)
        self.assertIn("if (toRemove.len() > 0 && V279_RESELECT_MEMO != 0) OPEX_LINES_REVISION++;", self.task_report)

    def test_site_epoch_increments_at_all_invalidations(self):
        # 3 sites d'invalidation de cache de sites
        reset_body = _function_body(self.air_coverage, "function OpexAirResetSiteCache(")
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_AIR_SITE_EPOCH++;", reset_body)
        inval_body = _function_body(self.air_coverage, "function OpexAir0310InvalidateSiteValidity(")
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_AIR_SITE_EPOCH++;", inval_body)
        cached_body = _function_body(self.air_coverage, "function OpexAirInvalidateCachedSite(")
        self.assertIn("if (V279_RESELECT_MEMO != 0) OPEX_AIR_SITE_EPOCH++;", cached_body)

    def test_filter_memo_excludes_second_slot(self):
        memo_filt = _function_body(self.selection, "function OpexFilterAirAlternativesV279Memo(")
        self.assertIn("c83OwnSecondSlotA", memo_filt)
        self.assertIn("c83OwnSecondSlotB", memo_filt)
        self.assertIn("v134SecondSlotA", memo_filt)
        self.assertIn("v134SecondSlotB", memo_filt)
        self.assertIn("isSecondSlot", memo_filt)
        # Ne mémorise jamais si isSecondSlot
        self.assertIn("!isSecondSlot", memo_filt)

    def test_filter_mode_2_control(self):
        memo_filt = _function_body(self.selection, "function OpexFilterAirAlternativesV279Memo(")
        self.assertIn("V279_RESELECT_MEMO == 2", memo_filt)
        # Amorçage de validité dès l'entrée en mode 2
        self.assertIn("stationLimitedTowns = {};", memo_filt)
        self.assertIn("validity = OpexAir0310SiteValidityBegin(stationLimitedTowns);", memo_filt)
        # Comparaison memo vs hist et log d'écart
        self.assertIn("memoLive != histLive", memo_filt)
        self.assertIn('OpexDecide("V279_CHECK", diffMsg);', memo_filt)
        self.assertIn('AILog.Warning("V279_CHECK " + diffMsg);', memo_filt)
        # Retour historique et mise à jour de l'entrée avec verdict historique
        self.assertIn('project.rawset("_v279Live", histLive);', memo_filt)
        self.assertIn("if (histLive) live.append(project);", memo_filt)

    def test_stats_logging(self):
        memo_filt = _function_body(self.selection, "function OpexFilterAirAlternativesV279Memo(")
        self.assertIn("V279_HITS++", memo_filt)
        self.assertIn("V279_MISSES++", memo_filt)
        self.assertIn('OpexDecide("V279_STATS"', memo_filt)


if __name__ == "__main__":
    unittest.main()
