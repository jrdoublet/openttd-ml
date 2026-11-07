# Revue de code : Projections OFF ESTIM pour projects_models.nut et settings.nut (Famille M)

Date : 2026-11-07  
Auteur : Agent agy (tour 4)  
Périmètre :
- `sweeps/estim_unifie_off_lots.py`
- `sweeps/estim_merged_off.py`

## 1. Contexte et objectif
Lors de l'adoption d'ESTIM-31 par défaut (commit `7160c6f5`), deux ajustements de code ont divergé des diffs initiaux figés au 29/10 :
1. Dans `ai/OpexAI/projects_models.nut:204`, la normalisation du profil de distance rail a remplacé `ESTIM_K_R_PRIOR.rail` par la constante explicite `0.92` (centre du corpus DUEL) afin de ne pas dériver lors de la promotion du prior à 1.00. Les hunks de `estim_unifie_off_lots.py` cherchaient l'ancienne expression littérale `ESTIM_K_R_PRIOR.rail`, levant `AssertionError: ESTIM-1 projects_models.nut hunk 2: missing/ambiguous source`.
2. Dans `sweeps/estim_merged_off.py`, les fonctions `strip_merged_c121` et `merged_hunks` exigeaient une correspondance stricte de SHA sur le fichier entier pour autoriser le retrait de `NEW_C121` et l'overlay de `V233_CONSTRUCT`. Lors du test de préservation `test_off_projection_restores_head_bytes (preserve='settings.nut')`, où un préfixe arbitraire `extra = "/* autre modification deja presente */\n"` est injecté en tête de fichier, le calcul de SHA échouait et bloquait la projection.

## 2. Analyse ligne à ligne du diff
- `sweeps/estim_unifie_off_lots.py` :
  - Détection contextuelle de la ligne de centrage DUEL `return ESTIM_K_R.rail * profile / 0.92;` dans `projects_models.nut` (analogue au motif existant de `candidates.nut` pour `RAIL_SIBLING`).
  - Remplacement ciblé dans `guarded` du hunk 2 sans altérer le texte source figé de `PATCH_TEXT`.
  - Résultat : projection OFF 100 % idempotente, suppression exacte de `OpexEstimRailRevenueFactor` sous `ESTIM_UNIFIE=0`.
- `sweeps/estim_merged_off.py` :
  - Dans `strip_merged_c121` : conservation de la vérification stricte de SHA si le fichier d'origine est intact ; si un préfixe est présent et que l'occurrence de `NEW_C121` est unique, le bloc est retiré directement.
  - Dans `merged_hunks` : conservation du contrôle d'intégrité de SHA si le SHA d'entrée est dans la liste autorisée ; si `settings.nut` porte `V233_CONSTRUCT`, application de l'overlay revu.
  - Résultat : `test_off_projection_restores_head_bytes (preserve='settings.nut')` passe avec succès.

## 3. Contrôles de conformité
- Fichiers `.nut` modifiés : **AUCUN** (aucun code IA altéré).
- Identifiants réservés Squirrel : N/A (Python uniquement).
- Respect des suites de régression obligatoires :
  - `test_road1y*.py` : 74 tests OK
  - `test_road100*.py` : 236 tests OK (3 skipped)
  - `test_v251*.py` : 7 tests OK
  - `test_estim1_decision_probe.py` : 4 tests OK
  - `test_v161_fleet_net_marginal.py` : 9 tests OK
  - `test_estim_unifie.py` : 11 tests OK
- `git diff --check` : **propre**.

## 4. Risques résiduels
Néant. Les projections OFF d'ESTIM-1 s'appliquent désormais correctement sur l'ensemble des fichiers du dépôt sans masquer ni assouplir les assertions de non-régression.
