# Revue de code — Tâche 1 : LOAN-1 (`road1y_loan_floor`)

**Date :** 8 novembre 2026  
**Auteur :** Antigravity  
**Réglage :** `road1y_loan_floor` (0 = inerte / repli `LOAN_REPAY_FLOOR=300000`, >0 = plancher en k£, ex. 50 pour 50 000 £)  
**Fichiers modifiés :**
- `ai/OpexAI/capital.nut` : calcul de `floor = (ROAD1Y_LOAN_FLOOR > 0) ? (ROAD1Y_LOAN_FLOOR * 1000) : LOAN_REPAY_FLOOR;` et utilisation dans `_tryRepayLoan`, logs `OpexDecide` sous `DECISION_LOG`.
- `ai/OpexAI/globals_pre.nut` : déclaration `ROAD1Y_LOAN_FLOOR <- 0;` hors des blocs historiques B2.
- `ai/OpexAI/info.nut` : déclaration du réglage dans `GetSettings()` aux 4 difficultés à 0, plage 0..500.
- `ai/OpexAI/settings.nut` : lecture dans `OpexLoadSettings`, clamping 0..500 et forçage à 0 si `!road1yRoadOnly`.
- `sweeps/test_road1y_loan_floor.py` : test de contrat dédié (déclaration, valeurs par défaut, clamping, comportement de calcul, respect des gardes).
- `sweeps/test_road1y_multimodal_gate.py` : intégration dans les inventaires de validation route seule.
- `sweeps/test_v251_inventory.py` : ajustement du plafond des réglages à 69 avec justification.
- `sweeps/road100_off_projection.py`, `sweeps/rail_open_legacy.py`, `sweeps/rail_sibling_legacy.py`, `sweeps/test_road100_merge_projection_20261105.py` : maintien de l'intégrité des projections multi-époques.

---

## 1. Examen ligne à ligne et vérification des règles Squirrel

- **Identifiants réservés :** Aucun usage de `clone`, `base`, `parent`, `static`, `delegate`, `vargc`, `vargv`, `resume`, `yield`, `constructor`, `instanceof`.
- **Fonctions anonymes et closures :** Aucune closure capturant des variables englobantes ; pas de `function(`.
- **Recherche dans les tableaux :** Pas d'appel à `.find(` sur les tableaux.
- **Chemin par défaut (valeur 0) :**
  Quand `road1y_loan_floor == 0`, `floor` vaut strictement `LOAN_REPAY_FLOOR` (300 000). Le calcul `minNewLoan = loan - (cash - floor)` et `newLoan` est rigoureusement identique au code historique de master.
- **Réserve de sécurité :**
  Après remboursement d'un montant `repaid = loan - newLoan`, la trésorerie résiduelle est `cash - repaid = cash - loan + newLoan >= floor`. La réserve est garantie par construction.
- **Portée multimodale :**
  Forcé à 0 si `!road1yRoadOnly`. Hors mode route seule, aucun changement de comportement.
- **Journalisation :**
  Tous les appels `OpexDecide` sont gardés par `if (DECISION_LOG)`.

---

## 2. Validation des tests

- `test_road1y*.py` : 78/78 tests OK (y compris `test_road1y_loan_floor` et `test_road1y_multimodal_gate`).
- `test_v251*.py` : 7/7 tests OK (plafond 69 AddSetting respecté et justifié).
- `test_road100*.py` : 236/236 tests OK (3 sautés autorisés).
- `git diff --check` : 0 anomalie.

---

## 3. Défauts trouvés et corrigés avant commit

1. *Défaut d'ancrage historique :* Placer le réglage au milieu des anciens hunks B2 cassait l'invariance des fixtures historiques figées. Corrigé en positionnant les déclarations après les blocs figés, préservant la compatibilité avec toutes les époques.
2. *Clamping de borne négative :* Sécurisation stricte à `0 <= ROAD1Y_LOAN_FLOOR <= 500`.

---

## 4. Risques résiduels

Aucun risque fonctionnel identifié : à 0, le code exécuté est strictement celui de master.
Valeur candidate recommandée pour qualification : `road1y_loan_floor=50` (plancher de 50 k£).
