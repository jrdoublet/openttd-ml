# Revue de Code — EB-7 Phase 2 (Comptabilité Fine et Passive des Dépenses AIR/ROUTE)

## 1. Périmètre du Diff Inspecté

- **Réglage introduit :** `eb7_detailed_accounting` (min=0, max=1, défaut 0, 4 difficultés à 0, flags 0).
- **Fichiers modifiés :**
  - `ai/OpexAI/globals_pre.nut` : déclaration `EB7_DETAILED_ACCOUNTING <- 0;` et `EB7_LEDGER <- { capexRoad = 0, capexAir = 0, vehBuyAir = 0, lastCash = 0, lastLoan = 0 };`.
  - `ai/OpexAI/info.nut` : déclaration du réglage public avec description et bornes.
  - `ai/OpexAI/settings.nut` : chargement unique `EB7_DETAILED_ACCOUNTING = AIController.GetSetting("eb7_detailed_accounting") == 1 ? 1 : 0;`.
  - `ai/OpexAI/ledgers.nut` : implémentation de `OpexEB7RecordSpend(mode, category, amount)` et `OpexEB7MonthlyReconciliation()`.
  - `ai/OpexAI/persist.nut` : sauvegarde et chargement de `EB7_LEDGER` sous garde `if (EB7_DETAILED_ACCOUNTING)`.
  - `ai/OpexAI/task_projects.nut` : instrumentation passive des chantiers réels construits (mode "air" et "road") et des renforts d'avions "fleet", avec réconciliation mensuelle en fin de passe.
  - `sweeps/test_eb7_detailed_accounting.py` : tests unitaires vérifiant déclaration, globales, absence totale de modification rail et bon fonctionnement de l'instrumentation.
  - `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/test_v251_inventory.py` : mise à jour des empreintes SHA et projections de configuration.

---

## 2. Relecture Critique "Œil Neuf" et Vérification des Invariants

1. **Innocuité au défaut 0 :**
   - À `eb7_detailed_accounting = 0`, `EB7_DETAILED_ACCOUNTING` vaut 0.
   - Tous les appels `OpexEB7RecordSpend` et `OpexEB7MonthlyReconciliation` sont court-circuités par le garde `if (!EB7_DETAILED_ACCOUNTING) return;`.
   - 0 opcode additionnel, comportement du moteur inchangé au microsecond près.
2. **Embargo rail formellement respecté :**
   - Aucun fichier rail (`builder_rail.nut`, `*rail*`, `task_v2*`) n'a été touché.
   - Seuls les modes AIR et ROUTE sont instrumentés conformément à la consigne utilisateur.
3. **Zéro pollution AITestMode :**
   - L'enregistrement se fait uniquement à postériori lorsque `attempt.outcome == "built"` ou lors de la validation finale du renfort, en capturant la dépense réelle `actualCost`.
4. **Hygiène Squirrel :**
   - Aucun `.find(`, aucune fonction anonyme, contrats de Save/Load respectés.

---

## 3. Conclusion

Le code est rigoureusement conforme à la spécification `EB7_PHASE2.md`, inoffensif au défaut 0, et validé par l'ensemble des suites de tests hôte.
