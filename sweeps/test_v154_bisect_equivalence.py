#!/usr/bin/env python3
"""Test d'equivalence stricte entre insertion lineaire et par dichotomie (V154).

Simule fidelement le comparateur d'OpexProjectInsertDefensive dans ses deux
variantes (historique lineaire et V154 dichotomie sur cles en cache) pour
prouver mathematiquement et empiriquement l'equivalence exacte des positions
d'insertion et du maintien de la stabilite des rangs.
"""

import random
import unittest
from typing import List, Optional


class Project:
    def __init__(self, pid: int, tier: int, score: float, revenueAnnual: int, field: str = "fundScore"):
        self.pid = pid
        self.tier = tier
        self.score = score
        self.revenueAnnual = revenueAnnual
        self.field = field

        # Champs de cache V154
        self._bsTier: Optional[int] = None
        self._bsScore: Optional[float] = None
        self._bsRevenue: Optional[int] = None
        self._bsField: Optional[str] = None
        self._bsEarly: Optional[bool] = None
        self._bsStamp: Optional[int] = None

    def __repr__(self):
        return f"P({self.pid}, t={self.tier}, s={self.score}, r={self.revenueAnnual})"

    def __eq__(self, other):
        if not isinstance(other, Project):
            return False
        return self.pid == other.pid


def insert_defensive_historic(best: List[Project], project: Project, limit: int, applyEarlySlot: bool = False) -> None:
    """Transcription fidele du chemin historique d'OpexProjectInsertDefensive (sans C118/C122)."""
    projectTier = project.tier
    projectScore = project.score
    pos = len(best)
    while pos > 0:
        prior = best[pos - 1]
        priorTier = prior.tier
        if priorTier > projectTier:
            break
        if priorTier < projectTier:
            pos -= 1
            continue
        priorScore = prior.score
        if priorScore > projectScore:
            break
        if priorScore == projectScore and prior.revenueAnnual >= project.revenueAnnual:
            break
        pos -= 1
    best.insert(pos, project)
    if len(best) > limit:
        best.pop()


def insert_defensive_bisect(
    best: List[Project],
    project: Project,
    limit: int,
    applyEarlySlot: bool = False,
    current_stamp: int = 1,
) -> None:
    """Transcription fidele du chemin V154 avec dichotomie et cache de cles."""
    projectTier = project.tier
    projectScore = project.score
    projectRevenue = project.revenueAnnual

    project._bsTier = projectTier
    project._bsScore = projectScore
    project._bsRevenue = projectRevenue
    project._bsField = project.field
    project._bsEarly = applyEarlySlot
    project._bsStamp = current_stamp

    lo = 0
    hi = len(best)
    while lo < hi:
        mid = (lo + hi) // 2
        prior = best[mid]

        if (
            prior._bsStamp == current_stamp
            and prior._bsField == project.field
            and prior._bsEarly == applyEarlySlot
        ):
            priorTier = prior._bsTier
            priorScore = prior._bsScore
            priorRevenue = prior._bsRevenue
        else:
            priorTier = prior.tier
            priorScore = prior.score
            priorRevenue = prior.revenueAnnual
            prior._bsTier = priorTier
            prior._bsScore = priorScore
            prior._bsRevenue = priorRevenue
            prior._bsField = project.field
            prior._bsEarly = applyEarlySlot
            prior._bsStamp = current_stamp

        keepsPrior = False
        if priorTier > projectTier:
            keepsPrior = True
        elif priorTier == projectTier:
            if priorScore > projectScore:
                keepsPrior = True
            elif priorScore == projectScore:
                keepsPrior = (priorRevenue >= projectRevenue)

        if keepsPrior:
            lo = mid + 1
        else:
            hi = mid

    best.insert(lo, project)
    if len(best) > limit:
        best.pop()


class TestV154BisectEquivalence(unittest.TestCase):

    def test_empty_and_single(self):
        best_hist = []
        best_bis = []
        p1 = Project(1, 0, 100.0, 500)
        insert_defensive_historic(best_hist, p1, 10)
        insert_defensive_bisect(best_bis, p1, 10)
        self.assertEqual(best_hist, best_bis)

    def test_strict_ordering(self):
        projects = [
            Project(1, 2, 500.0, 1000),
            Project(2, 2, 300.0, 1000),
            Project(3, 1, 900.0, 2000),
            Project(4, 0, 100.0, 500),
        ]
        best_hist = []
        best_bis = []
        for p in projects:
            insert_defensive_historic(best_hist, p, 10)
            insert_defensive_bisect(best_bis, p, 10)
            self.assertEqual(best_hist, best_bis)

    def test_exact_ties_stability(self):
        """Les projets avec exactement memes tier, score et revenue doivent preserver l'ordre FIFO."""
        best_hist = []
        best_bis = []
        for pid in range(10):
            p = Project(pid, 1, 100.0, 500)
            insert_defensive_historic(best_hist, p, 10)
            insert_defensive_bisect(best_bis, p, 10)
            self.assertEqual(best_hist, best_bis)
        # Verifier que l'ordre est strictement l'ordre d'insertion
        self.assertEqual([p.pid for p in best_bis], list(range(10)))

    def test_tie_breaking_hierarchy(self):
        """Verifie tier > score > revenue > insertion order."""
        projects = [
            Project(1, 1, 100.0, 500),
            Project(2, 2, 50.0, 100),    # Tier superieur gagne malgre score inferieur
            Project(3, 1, 100.0, 600),   # Meme tier/score mais revenue superieur : insere devant 1 ?
                                         # Attention : 1 a revenue 500. Quand 3 arrive, 1 a priorRevenue (500) < 600.
                                         # Donc 1 ne garde PAS la priorite sur 3 ! 3 passe devant 1 !
            Project(4, 1, 100.0, 500),   # Meme tier/score/revenue que 1 : 1 garde priorite, 4 est derriere 1
        ]
        best_hist = []
        best_bis = []
        for p in projects:
            insert_defensive_historic(best_hist, p, 10)
            insert_defensive_bisect(best_bis, p, 10)
            self.assertEqual(best_hist, best_bis)

    def test_limit_one(self):
        """Teste limit=1 qui correspond aux insertions pairBest de deduplication."""
        rng = random.Random(123)
        for _ in range(500):
            best_hist = []
            best_bis = []
            for pid in range(10):
                t = rng.randint(0, 2)
                s = rng.choice([0.0, 10.0, 20.0, 20.0, 50.0])
                r = rng.choice([0, 100, 200, 500])
                p_h = Project(pid, t, s, r)
                p_b = Project(pid, t, s, r)
                insert_defensive_historic(best_hist, p_h, 1)
                insert_defensive_bisect(best_bis, p_b, 1)
                self.assertEqual([p.pid for p in best_hist], [p.pid for p in best_bis])

    def test_random_fuzzing_massive(self):
        """Fuzzing massif sur des milliers de sequences avec egalites frequentes."""
        rng = random.Random(42)
        tiers = [0, 1, 2]
        scores = [-100.0, -1.0, 0.0, 0.0, 10.0, 10.5, 10.50001, 50.0, 100.0, 100.0, 200.0]
        revenues = [-500, 0, 0, 100, 500, 1000, 1000, 5000]

        for seq_idx in range(5000):
            seq_len = rng.randint(1, 100)
            limit = rng.randint(1, 64)
            stamp = rng.randint(1, 100)

            best_hist = []
            best_bis = []

            for pid in range(seq_len):
                t = rng.choice(tiers)
                s = rng.choice(scores)
                r = rng.choice(revenues)
                p_hist = Project(pid, t, s, r)
                p_bis = Project(pid, t, s, r)

                insert_defensive_historic(best_hist, p_hist, limit)
                insert_defensive_bisect(best_bis, p_bis, limit, current_stamp=stamp)

                self.assertEqual(
                    [p.pid for p in best_hist],
                    [p.pid for p in best_bis],
                    f"Mismatch at seq {seq_idx}, pid {pid}, limit {limit}"
                )

    def test_stale_stamp_and_field_invalidation(self):
        """Verifie que le cache est correctement reevalue lors d'un changement de stamp ou field."""
        best = []
        p1 = Project(1, 1, 100.0, 500, field="fundScore")
        insert_defensive_bisect(best, p1, 10, current_stamp=1)

        self.assertEqual(p1._bsStamp, 1)
        self.assertEqual(p1._bsTier, 1)

        # Modifier le projet pour simuler une nouvelle vague / nouveau stamp
        p1.score = 300.0
        p2 = Project(2, 1, 200.0, 500, field="fundScore")

        # Insertion avec nouveau stamp 2 : le cache de p1 doit etre rafraichi
        insert_defensive_bisect(best, p2, 10, current_stamp=2)

        self.assertEqual(p1._bsStamp, 2)
        self.assertEqual(p1._bsScore, 300.0)
        # p1 (score 300) doit etre devant p2 (score 200)
        self.assertEqual([p.pid for p in best], [1, 2])


class TestV154Contract(unittest.TestCase):
    """Verifications contractuelles des fichiers Squirrel du depot."""

    @classmethod
    def setUpClass(cls):
        from pathlib import Path
        cls.root = Path(__file__).resolve().parents[1]
        cls.info = (cls.root / "ai/OpexAI/info.nut").read_text(encoding="utf-8")
        cls.globals_pre = (cls.root / "ai/OpexAI/globals_pre.nut").read_text(encoding="utf-8")
        cls.settings = (cls.root / "ai/OpexAI/settings.nut").read_text(encoding="utf-8")
        cls.selection = (cls.root / "ai/OpexAI/projects_selection.nut").read_text(encoding="utf-8")
        cls.diagnostics = (cls.root / "ai/OpexAI/selection_diagnostics.nut").read_text(encoding="utf-8")

    def test_setting_in_info_nut(self):
        self.assertEqual(self.info.count('name = "select_bisect_insert"'), 1)
        start = self.info.index('name = "select_bisect_insert"')
        block = self.info[start:self.info.index("});", start)]
        for token in ("easy_value = 1", "medium_value = 1", "hard_value = 1", "custom_value = 1"):
            self.assertIn(token, block)
        self.assertIn("flags = AICONFIG_BOOLEAN", block)

    def test_globals_in_globals_pre(self):
        self.assertIn("SELECT_BISECT_INSERT <- false;", self.globals_pre)
        self.assertIn("SELECT_BISECT_STAMP <- 0;", self.globals_pre)

    def test_settings_nut_loading(self):
        self.assertEqual(self.settings.count('AIController.GetSetting("select_bisect_insert")'), 1)
        self.assertIn('SELECT_BISECT_INSERT = AIController.GetSetting("select_bisect_insert") != 0;', self.settings)

    def test_projects_selection_hooks(self):
        # Verification de la signature et des gardes
        self.assertIn("function OpexProjectInsertDefensive(best, project, field, limit, applyEarlySlot = false, forceHistoric = false)", self.selection)
        self.assertIn("local useBisect = SELECT_BISECT_INSERT && !forceHistoric", self.selection)
        self.assertIn("!(C122_AIR_REGIME_SHADOW && C121_AIR_PROJECT_REALIZATION_REGIME == 0)", self.selection)
        # Verification de l'incrementation du tampon
        self.assertIn("SELECT_BISECT_STAMP++;", self.selection)
        # Verification que l'appel diagnostic passe forceHistoric = true
        self.assertIn('OpexProjectInsertDefensive(shadowOrder, shadowProject, "fundScore", limit, AIR_EARLY_SLOT, true);', self.selection)

    def test_selection_diagnostics_hooks(self):
        self.assertIn("SELECT_BISECT_STAMP++;", self.diagnostics)
        self.assertIn('OpexProjectInsertDefensive(originalOrder, row.before, "fundScore", state.rows.len(), AIR_EARLY_SLOT, true);', self.diagnostics)
        self.assertIn('OpexProjectInsertDefensive(shadowOrder, row.after, "fundScore", state.rows.len(), AIR_EARLY_SLOT, true);', self.diagnostics)


if __name__ == "__main__":
    unittest.main()
