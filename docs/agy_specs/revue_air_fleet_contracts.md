# Revue de code : Modernisation des contrats statiques flotte aérienne (Famille H)

Date : 2026-11-07
Auteur : Agent agy (tour 2)
Périmètre : `sweeps/test_v252_engine_refresh.py`, `sweeps/test_b8_scrap_lifecycle.py`, `sweeps/test_c121_visible_target.py`, `sweeps/test_v147_air_catalog_tasks.py`

## 1. Contexte et objectif
Plusieurs tests statiques du sous-système aérien échouaient suite à des évolutions du code de l'IA intervenues lors des chantiers récents :
1. Dans `air_fleet.nut`, la fonction `OpexAirAddPlane` a reçu un 4e paramètre optionnel `forcedEngine = null` pour permettre le choix forcé d'un moteur (`test_v252_engine_refresh.py`).
2. Les deux sites d'appel d'achat/renfort dans `task_air.nut` et `task_projects.nut` passent le paramètre `locked` : `OpexAirAddPlane(line, this._catalog, this._lines, locked)`. Les tests `test_b8_scrap_lifecycle.py` et `test_c121_visible_target.py` cherchaient l'ancienne chaîne à 3 arguments.
3. Dans `main.nut`, l'initialisation du délai d'inactivité de réparation rail (`RAIL_REPAIR_IDLE`) a été insérée entre `OpexLoadSettings();` et `OpexV147ExtendQueue(this);`. Le test `test_v147_air_catalog_tasks.py` exigeait qu'ils soient immédiatement contigus.

## 2. Analyse ligne à ligne du diff
- `sweeps/test_v252_engine_refresh.py` :
  - Signature de `OpexAirAddPlane` dans `_body` mise à jour avec `forcedEngine = null`.
  - Condition `catalog != null && forcedEngine == null` prise en compte dans `test_always_on`.
- `sweeps/test_b8_scrap_lifecycle.py` :
  - Recherche du site d'appel `OpexAirAddPlane` avec son 4e argument `locked`.
- `sweeps/test_c121_visible_target.py` :
  - Comptage des sites d'appel réels `OpexAirAddPlane(..., locked)` dans `task_air.nut` et `task_projects.nut`.
- `sweeps/test_v147_air_catalog_tasks.py` :
  - Assertion de précédence découplée : `settings_idx < load < reconcile_idx` (respecte l'ordre sans imposer une contiguïté stricte).

## 3. Contrôles de conformité
- Fichiers `.nut` modifiés : **AUCUN**.
- Identifiants réservés Squirrel : N/A (Python uniquement).
- Respect du comportement économique : inchangé.
- Suites de non-régression obligatoires (`test_road1y*.py`, `test_road100*.py`, `test_v251*.py`) : **317 tests OK**.
- Tests de la famille : **27 tests OK** (0 échec, 0 erreur).
- `git diff --check` : **propre**.

## 4. Risques résiduels
Néant.
