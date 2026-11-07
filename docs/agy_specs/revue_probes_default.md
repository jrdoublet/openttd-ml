# Revue de code : modernisation tests de sondes sous probes=2 (Famille B)

## 1. Contexte et objectif
- Fichiers modifiés :
  - `sweeps/test_v167_probes.py`
  - `sweeps/test_signs_default_off.py`
  - `sweeps/test_b9_air_catchment.py`
  - `sweeps/test_publication_probes_default.py`
- Référence : V167 / ESTIM-31 promotion (commit `7160c6f5` et `docs/taches.md` ligne 1184). Le nouveau défaut public validé de `probes` dans `info.nut` est `2` (activation des panneaux de diagnostic, sans sondes verbeuses de journalisation).
- Objectif : aligner les assertions des tests sur le défaut public `probes=2` dans `info.nut` et vérifier que les bits de sondes profondes (bit 20 B9, journal 256, etc.) restent bien inactifs par défaut (`defaults["probes"] & (1048576 | 128) == 0`).

## 2. Analyse détaillée du diff
- Diff relu ligne par ligne :
  - `test_v167_probes.py` : vérifie `spec["probes"]["default"] == 2` et `key = 2` pour les 4 niveaux de difficulté.
  - `test_signs_default_off.py` : vérifie `key = 2` pour les 4 niveaux de difficulté dans `info.nut`.
  - `test_b9_air_catchment.py` : vérifie `defaults["probes"] == 2`, et confirme que la sonde B9 reste désactivée (`defaults["probes"] & (1048576 | 128) == 0`).
  - `test_publication_probes_default.py` : vérifie `level_value = 2` et `automatic["defaults"]["probes"] == 2`.
  - Aucun fichier `.nut` touché.
  - Sauvegarde et chargement intacts.
  - Fixtures intactes.
  - Aucun fichier parasite.

## 3. Résultats de tests
- `python3 -m unittest discover -s sweeps -p 'test_road1y*.py'` : 74/74 OK
- `python3 -m unittest discover -s sweeps -p 'test_road100*.py'` : 236/236 OK (3 skipped)
- `python3 -m unittest discover -s sweeps -p 'test_v251*.py'` : 7/7 OK
- `test_v167_probes.py` : 13/13 OK
- `test_signs_default_off.py` : 4/4 OK
- `test_publication_probes_default.py` : 5/5 OK
- Tous les tests de la famille passent à 100%.

## 4. Risques résiduels
- Aucun : reflète exactement le statut validé dans `info.nut` (`probes=2`) issu du pack de promotion ESTIM-31.
