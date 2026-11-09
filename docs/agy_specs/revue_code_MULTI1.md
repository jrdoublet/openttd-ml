# Revue de Code — MULTI-1 (Conditions de Relance du Multimodal Tardif)

## 1. Périmètre du Diff Inspecté

- **Réglage introduit :** `multi1_relance` (min=0, max=2, défaut 0, 4 difficultés à 0, flags 0).
- **Fichiers modifiés :**
  - `ai/OpexAI/globals_pre.nut` : déclaration `MULTI1_RELANCE <- 0;` et `MULTI1_LAST_BUILD_DATE <- 0;`.
  - `ai/OpexAI/info.nut` : déclaration du réglage public avec description et bornes (0=off, 1=shadow, 2=on).
  - `ai/OpexAI/settings.nut` : chargement unique `MULTI1_RELANCE = AIController.GetSetting("multi1_relance");`.
  - `ai/OpexAI/projects_selection.nut` : implémentation du prédicat `OpexMulti1TriggerActive(ai)` détectant la starvation tardive sous conditions strictes.
  - `ai/OpexAI/task_projects.nut` : mise à jour de `MULTI1_LAST_BUILD_DATE` lors de chaque construction effective (mode air et road).
  - `ai/OpexAI/persist.nut` : persistance de `MULTI1_LAST_BUILD_DATE` sous garde `if (MULTI1_RELANCE)`.
  - `sweeps/test_multi1_restart_conditions.py` : tests unitaires vérifiant déclaration, globales, prédicat d'activation et hygiène.
  - `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/test_v251_inventory.py` : synchronisation mécanique des projections SHA.

---

## 2. Relecture Critique "Œil Neuf" et Vérification des Invariants

1. **Innocuité absolue au défaut 0 :**
   - À `multi1_relance = 0`, `MULTI1_RELANCE` vaut 0.
   - `OpexMulti1TriggerActive` retourne immédiatement `false` sans aucun calcul.
   - Les gardes d'horodatage dans `task_projects.nut` et la persistance dans `persist.nut` sont totalement inactives.
   - Le comportement du moteur est rigoureusement identique au bit près.
2. **Sanctuarisation de la phase 1970–1974 :**
   - La garde `year < 1975` interdit toute altération durant les 5 premières années où OpexAI surperforme déjà (92,67% face à AAAHogEx).
3. **Conditions de déclenchement strictes :**
   - Trésorerie nette $\ge 2\,000\,000$ £ sans dette (`loan == 0`).
   - Starvation de chantiers neufs avérée ($\ge 180$ jours sans construction neuve ou vivier principal vide).
4. **Hygiène Squirrel & Non-rail :**
   - Aucun fichier rail touché.
   - Aucun `.find(`, aucune closure.

---

## 3. Conclusion

Le code est rigoureusement conforme à la spécification `MULTI1_CONDITIONS_RELANCE.md`, inoffensif au défaut 0, et validé par les suites de tests hôte.
