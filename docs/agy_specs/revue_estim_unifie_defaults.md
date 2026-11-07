# Revue de code : Alignement des assertions estim_unifie sur le défaut promu 31 et les priors calibrés (Famille E-bis)

Date : 2026-11-07
Auteur : Agent agy (tour 2)
Périmètre : `sweeps/test_estim_unifie.py`

## 1. Contexte et objectif
Lors de la qualification d'ESTIM-31 (commit `11f29b13`), le réglage `estim_unifie` a été promu par défaut à 31 (activant les cinq composantes), et les priors de `ESTIM_K_R_PRIOR` dans `globals_pre.nut` ont été calibrés à `{ rail = 1.00, road = 0.57, air = 1.50, water = 1.0 }` avec un poids de 15.0.
Deux tests de `test_estim_unifie.py` vérifiaient encore les constantes initiales pré-promotion (`estim_unifie=0` et priors `{ rail = 0.92, air = 0.40 }` avec poids 10.0).

## 2. Analyse ligne à ligne du diff
- `sweeps/test_estim_unifie.py` :
  - `test_setting_default_zero_everywhere_and_single_read` : assertion mise à jour pour vérifier que les valeurs d'`info.nut` pour chaque niveau sont bien fixées au défaut public adopté `= 31`.
  - `test_priors_match_corpus_rounding` : assertion mise à jour sur les priors calibrés réels de `globals_pre.nut` (`rail = 1.00`, `air = 1.50`, `weight = 15.0`).

## 3. Contrôles de conformité
- Fichiers `.nut` modifiés : **AUCUN**.
- Identifiants réservés Squirrel : N/A (Python uniquement).
- Respect du comportement économique : inchangé.
- Suites de non-régression obligatoires (`test_road1y*.py`, `test_road100*.py`, `test_v251*.py`) : **317 tests OK**.
- `git diff --check` : **propre**.

## 4. Risques résiduels
Néant.
