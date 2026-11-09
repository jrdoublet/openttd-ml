# Revue de Code — FAIR-PLAY / COURTOISIE (Commit e2a2b513)

Date : 2026-11-07  
Branche de travail : `agy-easy` (base `origin/master 7e5ad9d4`)  
Commit révisé : `e2a2b51381e5a23bb2ccebcde2b1378205ecdc32`  

---

## 1. Contexte et Périmètre de la Revue

Cette revue porte sur le commit `e2a2b513` implémentant le mode courtoisie `fair_play_courtesy` (défaut OFF / 0) conformément à la spécification technique `docs/agy_specs/FAIR_PLAY_PARTIES_NORMALES.md`.

Fichiers modifiés dans le commit :
- `ai/OpexAI/difficulty.nut`
- `ai/OpexAI/globals_pre.nut`
- `ai/OpexAI/info.nut`
- `ai/OpexAI/persist.nut`
- `ai/OpexAI/probes.nut`
- `ai/OpexAI/settings.nut`
- `ai/OpexAI/task_report.nut`
- `sweeps/test_fair_play_courtesy.py`
- `sweeps/test_v251_inventory.py`
- `sweeps/road100_off_projection.py`
- `sweeps/rail_open_legacy.py`
- `sweeps/rail_sibling_legacy.py`
- `sweeps/test_road100_merge_projection_20261105.py`
- `sweeps/fixtures/road100_bus_districts_hunks.json`

---

## 2. Grille d'Analyse Ligne à Ligne

### 2.1 Identifiants non déclarés & Portée
- **`globals_pre.nut`** : `FAIR_PLAY_COURTESY <- false;` correctement déclaré dans la table racine.
- **`difficulty.nut`** : Fonctions `OpexSignAllowed(kind)` et `OpexClearBudgetSigns(budgetSignIds)` utilisent des identifiants valides. API NoAI `AISign.IsValidSign` et `AISign.RemoveSign` conformes à l'API NoAI 15.3 (`docs/noai_api_15.3.tsv`).
- **`persist.nut` (DÉFAUT DÉCOUVERT)** :
  Dans `_reconcileAfterLoad()` (ligne 1355) :
  `if (FAIR_PLAY_COURTESY && this._budgetSignIds != null)`
  `_budgetSignIds` est une variable globale de `globals_pre.nut` (`_budgetSignIds <- {};`), et **non** un membre de la classe `OpexAI` (`this`). En Squirrel, tenter d'accéder à `this._budgetSignIds` lève une exception fatale d'exécution `the index '_budgetSignIds' does not exist` si le mode est activé.
  *Correction requise* : Remplacer par `_budgetSignIds != null` (ou `::_budgetSignIds != null`) et `OpexClearBudgetSigns(_budgetSignIds)`.

### 2.2 Chemin à 0 strictement identique
- À `fair_play_courtesy = 0` :
  - `FAIR_PLAY_COURTESY` est `false`.
  - Dans `difficulty.nut`, `OpexSignAllowed` renvoie `OpexLevelAllows("debug_signs")` ou `OpexLevelAllows("budget_sign_overlay")`. Aux niveaux 2 (difficile, défaut des bancs) et 3 (custom), ces fonctionnalités sont autorisées (`2 >= 2` et `3 >= 2`), reproduisant à l'identique la baseline.
  - Dans `persist.nut`, la garde `FAIR_PLAY_COURTESY` court-circuite et n'exécute aucun nettoyage de panneaux.
  - Dans `probes.nut`, `OpexDecide` continue d'enregistrer normalement dès lors que `FAIR_PLAY_COURTESY` est `false`.
  - Dans `settings.nut`, `if (FAIR_PLAY_COURTESY) OPEX_LEVEL_LIMITS = true;` n'est pas exécuté, préservant la valeur exacte de `OPEX_LEVEL_LIMITS`.

### 2.3 Deux chargeurs dans `settings.nut`
- `FAIR_PLAY_COURTESY = AIController.GetSetting("fair_play_courtesy") == 1;` est bien présent à la fois dans `OpexLoadSettings()` (ligne 73) et dans `OpexLoadBusDistrictSettings()` (ligne 733), respectant le patron de chargement anticipé (`ROAD1Y_SPREAD_STOPS`).

### 2.4 Save / Load & Persistance
- Le drapeau `FAIR_PLAY_COURTESY` est relu depuis `AIController.GetSetting()` lors du rechargement et n'est pas persisté dans le flux de sauvegarde, conformément à la politique des réglages statiques.
- Lors de la réconciliation après chargement, `_reconcileAfterLoad()` appelle le nettoyage des panneaux si le mode courtoisie est actif.

### 2.5 Mots réservés Squirrel
- Aucun mot réservé Squirrel (`clone`, `base`, `parent`, `static`, `delegate`, `vargc`, `vargv`, `resume`, `yield`, `constructor`, `instanceof`) n'est utilisé comme identifiant.
- Pas de fermeture anonyme capturant des locales englobantes.
- Pas d'utilisation de `.find(` sur un tableau Squirrel.

### 2.6 Logique d'exécution dans `task_report.nut` (DÉFAUT DÉCOUVERT)
- Dans `OpexAI::_reportYear` (lignes 947-950) :
  ```squirrel
  if (DEBUG_SIGNS) {
    if (!OpexSignAllowed("budget")) {
      OpexClearBudgetSigns(_budgetSignIds);
      return;
    }
  ```
  L'utilisation d'un `return;` direct fait sortir prématurément de `_reportYear`, court-circuitant ainsi les sondes et signaux diagnostics placés plus bas dans la fonction (notamment `if (C69_BOTTLENECK_PROBE) this._reportC78Candidates(year);`).
  *Correction requise* : Remplacer le `return;` par un bloc `else` englobant la création / mise à jour des panneaux budgétaires `BT|` et `BC|`.

---

## 3. Plan des Correctifs à Appliquer (Commit séparé)

1. **`ai/OpexAI/persist.nut`** : Corriger l'accès global à `_budgetSignIds` dans `_reconcileAfterLoad()`.
2. **`ai/OpexAI/task_report.nut`** : Remplacer le `return;` prématuré par une structure `if / else` propre pour préserver la fin de `_reportYear()`.
3. **`sweeps/test_fair_play_courtesy.py`** : Aligner l'assertion de contrat sur l'accès global `_budgetSignIds`.
