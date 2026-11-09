# Revue de code : correction import numpy optionnel (Famille A)

## 1. Contexte et objectif
- Fichier modifié : `sweeps/analyse_roi_predictors_20261021.py`
- Test impacté : `sweeps/test_demo_frontieres_temps_20261025.py` (8 tests, dont 7 en erreur faute de numpy sur le VPS/harnais hôte).
- Objectif : permettre l'exécution des tests de contrats et d'analyse sans exiger `numpy` pour les fonctions de base (`parse`), conformément aux invariants AGENTS.md §3 ("Le VPS n'a ni pytest ni numpy").

## 2. Analyse détaillée du diff
- Diff relu ligne par ligne :
  - Remplacement de `import numpy as np` direct par un bloc `try ... import numpy as np except (ImportError, ModuleNotFoundError): np = None`.
  - Aucun mot réservé Squirrel touché, aucun fichier `.nut` touché.
  - Sauvegarde et chargement intacts.
  - Fixtures intactes.
  - Aucun fichier parasite.

## 3. Résultats de tests
- `python3 -m unittest discover -s sweeps -p 'test_road1y*.py'` : 74/74 OK
- `python3 -m unittest discover -s sweeps -p 'test_road100*.py'` : 236/236 OK (3 skipped)
- `python3 -m unittest discover -s sweeps -p 'test_v251*.py'` : 7/7 OK
- `python3 -m unittest discover -s sweeps -p 'test_demo_frontieres_temps_20261025.py'` : 8/8 OK (0 erreur, au lieu de 7 erreurs).

## 4. Risques résiduels
- Si les fonctions statistiques de régression de `analyse_roi_predictors_20261021.py` sont appelées sans numpy, elles échoueront à l'usage de `np.<method>`. C'est le comportement attendu sur environnement sans numpy.
