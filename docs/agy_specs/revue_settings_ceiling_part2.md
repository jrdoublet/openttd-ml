# Revue de code : Actualisation du plafond des réglages historiques (Famille C-bis)

Date : 2026-11-07
Auteur : Agent agy (tour 2)
Périmètre : `sweeps/test_front_pax2_bounded_overlap.py`, `sweeps/test_n75_multi_cargo.py`, `sweeps/test_p3_air_fleet_yield.py`

## 1. Contexte et objectif
Dans le tour 1 (commit `6fcc21e7`), les assertions relatives au nombre de réglages historiques de base (`historical_info(...).count("AddSetting(")` ou `<= 68`) ont été actualisées de 58 à 68 sur `test_v246`, `test_v259`, `test_v276` et `test_parameter_retirements`.
Trois tests non-rail supplémentaires vérifiaient encore l'ancienne valeur historique stricte de 58 réglages :
- `sweeps/test_front_pax2_bounded_overlap.py`
- `sweeps/test_n75_multi_cargo.py`
- `sweeps/test_p3_air_fleet_yield.py`

(Le test `test_p2_rail_cargo_opportunity.py`, bien que présentant la même assertion, concerne le domaine rail et est conservé intact conformément aux consignes).

## 2. Analyse ligne à ligne du diff
- `sweeps/test_front_pax2_bounded_overlap.py` :
  - `self.assertEqual(historical_info(self.info).count("AddSetting("), 68)` au lieu de 58.
- `sweeps/test_n75_multi_cargo.py` :
  - `self.assertEqual(historical_info(self.info).count("AddSetting("), 68)` au lieu de 58.
- `sweeps/test_p3_air_fleet_yield.py` :
  - `self.assertEqual(historical_info(self.info).count("AddSetting("), 68)` au lieu de 58.

## 3. Contrôles de conformité
- Fichiers `.nut` modifiés : **AUCUN**.
- Identifiants réservés Squirrel : N/A (Python uniquement).
- Respect du comportement économique : inchangé.
- Suites de non-régression obligatoires (`test_road1y*.py`, `test_road100*.py`, `test_v251*.py`) : **317 tests OK**.
- Tests de la famille : **31 tests OK** (0 échec, 0 erreur).
- `git diff --check` : **propre**.

## 4. Risques résiduels
Néant.
