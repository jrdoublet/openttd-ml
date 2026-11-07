# Revue de code : modernisation des plafonds AddSetting obsolètes (Famille C)

## 1. Contexte et objectif
- Fichiers modifiés :
  - `sweeps/test_v246_fixed_policies.py`
  - `sweeps/test_v259_bridge_renew.py`
  - `sweeps/test_v276_candidate_slices.py`
  - `sweeps/test_parameter_retirements_20261023.py`
- Référence : sur `master`, la projection d'inventaire historique via `historical_info(info)` compte 68 réglages déclarés (documenté dans `sweeps/test_v251_inventory.py` lignes 68-70 : `origin/master 44d9313e already projects to 68 settings (not 58)`). Les tests plus anciens avaient des assertions figées sur l'ancien plafond 58 d'octobre 2026.
- Objectif : actualiser ces assertions sur le plafond de 68 réglages projetés de `master`, en accord avec l'inventaire autoritaire de `test_v251_inventory.py`.

## 2. Analyse détaillée du diff
- Diff relu ligne par ligne :
  - `test_v246_fixed_policies.py` : assertion mise à jour de `<= 58` à `<= 68`.
  - `test_v259_bridge_renew.py` : assertion mise à jour de `== 58` à `== 68`, et reflet dans le test de chaîne de `test_v246`.
  - `test_v276_candidate_slices.py` : assertion mise à jour de `<= 58` à `<= 68`.
  - `test_parameter_retirements_20261023.py` : assertion mise à jour de `== 58` à `== 68`.
  - Aucun fichier `.nut` touché.
  - Sauvegarde et chargement intacts.
  - Fixtures intactes.
  - Aucun fichier parasite.

## 3. Résultats de tests
- `python3 -m unittest discover -s sweeps -p 'test_road1y*.py'` : 74/74 OK
- `python3 -m unittest discover -s sweeps -p 'test_road100*.py'` : 236/236 OK (3 skipped)
- `python3 -m unittest discover -s sweeps -p 'test_v251*.py'` : 7/7 OK
- `test_v246_fixed_policies.py` : 6/6 OK
- `test_v259_bridge_renew.py` : 14/14 OK
- `test_v276_candidate_slices.py` : 26/26 OK
- `test_parameter_retirements_20261023.py` : 4/4 OK

## 4. Risques résiduels
- Aucun : ce plafond de 68 est déjà l'invariant central vérifié par `test_v251_inventory.py`.
