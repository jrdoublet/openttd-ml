# Revue de code : Découplage du test C121 FullScan suite à l'éclatement du fichier (Famille F-bis)

Date : 2026-11-07
Auteur : Agent agy (tour 2)
Périmètre : `sweeps/test_estim31_c121_dispatch.py`

## 1. Contexte et objectif
Lors de l'implémentation d'ESTIM-31, les fonctions expérimentales d'exploration exhaustive de la flotte aérienne (`OpexC121ChooseRoutePlaneFullScan`, etc.) ont été extraites de `air_economics_c121.nut` vers leur propre module `air_economics_c121_fullscan.nut`, chargé conditionnellement par `require()` dans `settings.nut`.
Le test `test_estim31_c121_dispatch.py` supposait que ces fonctions résidaient encore dans le même fichier, séparées par le commentaire `/* ESTIM C121 experimental full-scan functions. */`, générant 2 erreurs `IndexError` et 2 échecs d'assertion.

## 2. Analyse ligne à ligne du diff
- `sweeps/test_estim31_c121_dispatch.py` :
  - Lecture séparée de `air_economics_c121.nut` (historique) et `air_economics_c121_fullscan.nut` (expérimental).
  - Validation que les fonctions historiques conservent le `BAD_BREAK` (borne supérieure) et que les fonctions FullScan ne l'utilisent pas.
  - Vérification de l'activation opt-in dans `settings.nut` et des égalités de bris d'égalité de score.

## 3. Contrôles de conformité
- Fichiers `.nut` modifiés : **AUCUN**.
- Identifiants réservés Squirrel : N/A (Python uniquement).
- Respect du comportement économique : inchangé.
- Suites de non-régression obligatoires (`test_road1y*.py`, `test_road100*.py`, `test_v251*.py`) : **317 tests OK**.
- Tests de la famille : **4 tests OK** (0 échec, 0 erreur).
- `git diff --check` : **propre**.

## 4. Risques résiduels
Néant.
