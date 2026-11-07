# Revue de Code — LATE-GAME-1 (Réinvestissement de l'Excédent de Trésorerie Tardif)

## 1. Périmètre du Diff Inspecté

- **Réglage introduit :** `late_game_policy` (min=0, max=2, défaut 0, 4 difficultés à 0, flags 0).
- **Fichiers modifiés :**
  - `ai/OpexAI/globals_pre.nut` : déclaration `LATE_GAME_POLICY <- 0;`.
  - `ai/OpexAI/info.nut` : déclaration du réglage public avec description et bornes (0=off, 1=urbain, 2=industries).
  - `ai/OpexAI/settings.nut` : chargement unique `LATE_GAME_POLICY = AIController.GetSetting("late_game_policy");`.
  - `ai/OpexAI/task_v249.nut` : implémentation de `OpexLateGameDispatch(ai, ym, year)` et intégration dans `OpexAI::_dispatchV249Statue`.
  - `sweeps/test_late_game.py` : tests unitaires vérifiant déclaration, globales, conditions strictes de déclenchement et hygiène.
  - `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/test_v251_inventory.py` : synchronisation mécanique des projections SHA.

---

## 2. Relecture Critique "Œil Neuf" et Vérification des Invariants

1. **Innocuité au défaut 0 :**
   - À `late_game_policy = 0`, `LATE_GAME_POLICY` vaut 0.
   - La méthode `OpexLateGameDispatch` retourne immédiatement `false` sans aucun calcul.
   - `_dispatchV249Statue` conserve son flux historique inchangé.
2. **Conditions de déclenchement ultra-strictes (anti-cannibalisation) :**
   - Année $\ge 1976$ (aucun déclenchement précoce).
   - Emprunt nul (`loan == 0`).
   - Vivier principal vide ou épuisé (`ai._projects.best.len() == 0`).
   - Trésorerie $> 2 \times \text{coût renouvellement V252} + 5\,000\,000$ £ (sanctuarisation absolue de la flotte vivante et marge de sécurité massive).
3. **Hygiène Squirrel & Non-rail :**
   - Aucun fichier rail touché.
   - Aucun `.find(`, aucune closure.

---

## 3. Conclusion

Le code est rigoureusement conforme à la spécification `LATE_GAME_1.md`, inoffensif au défaut 0, et validé par les suites de tests hôte.
