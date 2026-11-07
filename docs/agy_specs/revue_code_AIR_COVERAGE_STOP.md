# Revue de Code — AIR-COVERAGE-STOP (Mise en veille du vivier de prospection aéroportuaire)

## 1. Périmètre du Diff Inspecté

- **Réglage introduit :** `air_coverage_stop` (min=0, max=1, défaut 0, 4 difficultés à 0, flags 0).
- **Fichiers modifiés :**
  - `ai/OpexAI/globals_pre.nut` : déclaration `AIR_COVERAGE_STOP <- 0;`, `AIR_COVERAGE_EXHAUSTED <- false;`, `AIR_NEW_TOWN_QUEUE <- [];`.
  - `ai/OpexAI/info.nut` : déclaration du réglage public avec description et bornes.
  - `ai/OpexAI/settings.nut` : lecture unique `AIR_COVERAGE_STOP = AIController.GetSetting("air_coverage_stop") == 1 ? 1 : 0;`.
  - `ai/OpexAI/air_planning.nut` :
    - Dans `OpexAirPlans` : court-circuit immédiat si `AIR_COVERAGE_STOP && AIR_COVERAGE_EXHAUSTED && AIR_NEW_TOWN_QUEUE.len() == 0`, évitant les scans $O(N^2)$ répétés en fin de partie.
    - Dans `OpexAirPlansFinalize` : détection d'épuisement physique complet (`perfSitesFound == 0`) et purge de la file des nouvelles villes traitées.
  - `ai/OpexAI/event_handlers.nut` : réveil automatique et ajout dans `AIR_NEW_TOWN_QUEUE` lors de la fondation d'une nouvelle ville (`AIEvent.ET_TOWN_FOUNDED`).
  - `ai/OpexAI/persist.nut` : persistance de `airCoverageExhausted` et `airNewTownQueue` dans Save/Load avec fallback `false`/`[]` pour les sauvegardes historiques.
  - `sweeps/test_air_coverage_stop.py` : suite de tests de contrat unitaire hôte.
  - `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/test_v251_inventory.py` : maintien strict des empreintes SHA et compteurs de configuration.

---

## 2. Relecture Critique "Œil Neuf" et Vérification des Invariants

1. **Innocuité au défaut 0 :**
   - À `air_coverage_stop = 0`, `AIR_COVERAGE_STOP` vaut 0.
   - Le garde d'endormissement dans `OpexAirPlans` est totalement inerte (`if (AIR_COVERAGE_STOP ...)`).
   - Dans `OpexAirPlansFinalize`, aucun drapeau d'épuisement n'est positionné.
   - Dans `_onTownFounded`, aucun événement n'est enfilé dans la file.
   - Les scans aéroportuaires et formations de paires s'exécutent de façon rigoureusement identique au comportement historique.
2. **Gestion du risque de faux positif précoce :**
   - L'épuisement n'est prononcé que si `perfSitesFound == 0` (incapacité physique de placer un aéroport sur aucune ville) et non pour manque de cash.
   - Tout événement de fondation de ville réveille immédiatement le balayage.
3. **Hygiène Squirrel & Découpage :**
   - Pas de `.find(`, pas de closure / capture de variable locale.
   - Aucun module rail impacté.
   - Save / Load symétrique et résilient aux chargements d'anciennes versions.

---

## 3. Conclusion

Le code est rigoureusement conforme à la spécification `AIR_COVERAGE_STOP.md`, inoffensif au défaut 0, et passe avec succès l'intégralité des 323 tests hôte.
